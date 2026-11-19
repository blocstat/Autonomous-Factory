"""Standard-library tests. They do not need pytest, NumPy, or SciPy."""

from __future__ import annotations

import math
import unittest
from pathlib import Path

from af_signal.host_report import (
    CommandResult,
    build_report,
    default_probe_commands,
    environment_path_status,
    idf_path_status,
    probe_tool,
    render_report,
)
from af_signal.window_stats import synthetic_sine, window_stats


class SyntheticWindowStatsTest(unittest.TestCase):
    def test_bin_centered_sine_matches_analytical_rms(self) -> None:
        window = synthetic_sine(
            sample_rate_hz=1000.0,
            duration_s=1.0,
            tone_hz=50.0,
            amplitude=1.0,
        )
        self.assertEqual(window.data_origin, "synthetic")
        self.assertEqual(len(window.samples), 1000)

        stats = window_stats(window.samples, window.sample_rate_hz, window.data_origin)
        self.assertEqual(stats.data_origin, "synthetic")
        self.assertEqual(stats.sample_count, 1000)
        self.assertAlmostEqual(stats.duration_s, 1.0)
        self.assertAlmostEqual(stats.mean, 0.0, delta=1e-12)
        self.assertAlmostEqual(stats.rms, 1.0 / math.sqrt(2.0), delta=1e-12)
        self.assertAlmostEqual(stats.peak_abs, 1.0, delta=1e-12)
        self.assertAlmostEqual(stats.crest_factor, math.sqrt(2.0), delta=1e-12)

    def test_same_arguments_repeat(self) -> None:
        first = synthetic_sine(sample_rate_hz=1000.0, duration_s=1.0, tone_hz=50.0)
        second = synthetic_sine(sample_rate_hz=1000.0, duration_s=1.0, tone_hz=50.0)
        self.assertEqual(first.samples, second.samples)

    def test_constant_crest_factor_is_one(self) -> None:
        stats = window_stats((2.0, 2.0, 2.0, 2.0), 100.0, "synthetic")
        self.assertAlmostEqual(stats.mean, 2.0)
        self.assertAlmostEqual(stats.rms, 2.0)
        self.assertAlmostEqual(stats.peak_abs, 2.0)
        self.assertAlmostEqual(stats.crest_factor, 1.0)
        self.assertAlmostEqual(stats.duration_s, 0.04)

    def test_zero_signal_has_undefined_crest_factor(self) -> None:
        window = synthetic_sine(
            sample_rate_hz=100.0,
            duration_s=0.1,
            tone_hz=10.0,
            amplitude=0.0,
        )
        with self.assertRaisesRegex(ValueError, "RMS is zero"):
            window_stats(window.samples, window.sample_rate_hz, window.data_origin)

    def test_rejects_measured_and_unlabeled_origin(self) -> None:
        samples = (0.0, 1.0, 0.0, -1.0)
        for origin in ("measured", "Measured", "Synthetic", "", "phone"):
            with self.assertRaisesRegex(ValueError, "synthetic"):
                window_stats(samples, 100.0, origin)

    def test_rejects_bad_samples_and_rates(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 2"):
            window_stats((), 100.0, "synthetic")
        with self.assertRaisesRegex(ValueError, "at least 2"):
            window_stats((1.0,), 100.0, "synthetic")
        with self.assertRaisesRegex(ValueError, "finite"):
            window_stats((1.0, float("nan")), 100.0, "synthetic")
        with self.assertRaisesRegex(ValueError, "finite"):
            window_stats((1.0, float("inf")), 100.0, "synthetic")
        with self.assertRaisesRegex(ValueError, "real numbers"):
            window_stats((1.0, True), 100.0, "synthetic")  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "positive"):
            window_stats((1.0, 1.0), 0.0, "synthetic")

    def test_generator_rejects_nyquist_and_empty_window(self) -> None:
        with self.assertRaisesRegex(ValueError, "Nyquist"):
            synthetic_sine(sample_rate_hz=1000.0, duration_s=1.0, tone_hz=500.0)
        with self.assertRaisesRegex(ValueError, "at least 2"):
            synthetic_sine(sample_rate_hz=1.0, duration_s=1.0, tone_hz=0.4)
        with self.assertRaisesRegex(ValueError, "non-negative"):
            synthetic_sine(
                sample_rate_hz=1000.0,
                duration_s=1.0,
                tone_hz=50.0,
                amplitude=-0.1,
            )


class HostReportTest(unittest.TestCase):
    def test_default_probes_do_not_configure_or_flash(self) -> None:
        forbidden = {"build", "flash", "set-target", "menuconfig", "install"}
        names = []
        for name, argv in default_probe_commands():
            names.append(name)
            self.assertTrue(forbidden.isdisjoint(argv))
        self.assertEqual(
            names, ["python3", "git", "cmake", "ninja", "idf.py", "pytest"]
        )

    def test_missing_executable_is_absent(self) -> None:
        def fail_if_called(_argv: object) -> CommandResult:
            raise AssertionError("run should not be called")

        status = probe_tool(
            "idf.py",
            ["idf.py", "--version"],
            which=lambda _name: None,
            run=fail_if_called,
        )
        self.assertFalse(status.present)
        self.assertEqual(status.detail, "not found")

    def test_failed_module_uses_stderr_and_is_absent(self) -> None:
        status = probe_tool(
            "pytest",
            ["python3", "-m", "pytest", "--version"],
            which=lambda _name: "/usr/bin/python3",
            run=lambda _argv: CommandResult(
                returncode=1,
                stdout="",
                stderr="/usr/bin/python3: No module named pytest\n",
            ),
        )
        self.assertFalse(status.present)
        self.assertEqual(status.detail, "/usr/bin/python3: No module named pytest")

    def test_present_tool_keeps_the_first_line(self) -> None:
        status = probe_tool(
            "cmake",
            ["cmake", "--version"],
            which=lambda _name: "/usr/bin/cmake",
            run=lambda _argv: CommandResult(
                returncode=0,
                stdout="cmake version 3.28.3\n\nCMake suite maintained and supported by Kitware\n",
                stderr="",
            ),
        )
        self.assertTrue(status.present)
        self.assertEqual(status.detail, "cmake version 3.28.3")

    def test_idf_path_status(self) -> None:
        self.assertFalse(idf_path_status({}).present)
        self.assertEqual(idf_path_status({}).detail, "unset")
        self.assertEqual(idf_path_status({"IDF_PATH": "  "}).detail, "unset")
        self.assertTrue(idf_path_status({"IDF_PATH": "/opt/esp-idf"}).present)

    def test_environment_path_status_uses_the_directory(self) -> None:
        directory = self._tmpdir()
        present = environment_path_status("espressif_tools", directory)
        missing = environment_path_status("esp_directory", directory / "missing")
        self.assertTrue(present.present)
        self.assertFalse(missing.present)
        self.assertEqual(missing.detail, str(directory / "missing"))

    def test_render_marks_firmware_build_as_not_run(self) -> None:
        report = build_report(
            platform="Linux test x86_64",
            tools=(idf_path_status({}),),
            environment_paths=(),
        )
        text = render_report(report)
        self.assertIn("platform: Linux test x86_64", text)
        self.assertIn("IDF_PATH: absent: unset", text)
        self.assertIn("firmware_build: not_run", text)
        self.assertNotIn("idf.py build", text)
        self.assertNotIn("pyproject.toml", text)

    def _tmpdir(self) -> Path:
        import tempfile

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        return Path(directory.name)


if __name__ == "__main__":
    unittest.main()

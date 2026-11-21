"""Tests for the phyphox loader and phone analysis script.

The CSV files here are SYNTHETIC fixtures written in phyphox's export format,
generated inside a temporary directory. They exercise the parser and the
analysis path; they are not phone measurements.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from af_signal.phone import (
    DATA_ORIGIN_PHONE,
    load_phyphox_csv,
    resample_uniform,
    sample_rate_stats,
)

ROOT = Path(__file__).resolve().parents[1]


def _fixture_signal(rate_hz=400.0, seconds=10.0, tone_hz=20.0, jitter=0.1, seed=0):
    rng = np.random.default_rng(seed)
    dt = (1.0 / rate_hz) * (1.0 + jitter * rng.uniform(-1, 1, int(rate_hz * seconds)))
    t = np.cumsum(dt)
    x = 0.05 * rng.normal(size=t.size)
    y = 0.05 * rng.normal(size=t.size)
    z = 9.81 + 0.3 * np.sin(2 * np.pi * tone_hz * t) + 0.05 * rng.normal(size=t.size)
    return t, x, y, z


def _write(path: Path, delimiter=",", decimal=".", with_absolute=True, **kwargs):
    t, x, y, z = _fixture_signal(**kwargs)
    header = ["Time (s)", "Acceleration x (m/s^2)", "Acceleration y (m/s^2)",
              "Acceleration z (m/s^2)"]
    if with_absolute:
        header.append("Absolute acceleration (m/s^2)")
    lines = [delimiter.join(f'"{h}"' for h in header)]
    for row in zip(t, x, y, z, np.sqrt(x**2 + y**2 + z**2)):
        cells = [f"{v:.9E}".replace(".", decimal) for v in row[: len(header)]]
        lines.append(delimiter.join(cells))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "delimiter,decimal", [(",", "."), (";", ","), ("\t", "."), ("\t", ",")]
)
def test_loads_phyphox_export_formats(tmp_path, delimiter, decimal):
    path = _write(tmp_path / "f.csv", delimiter=delimiter, decimal=decimal)
    capture = load_phyphox_csv(path)
    assert capture.data_origin == DATA_ORIGIN_PHONE
    assert set(capture.axes) == {"x", "y", "z"}
    assert capture.time_s.size == 4000
    assert np.mean(capture.axes["z"]) == pytest.approx(9.81, abs=0.01)


def test_absolute_column_is_not_taken_as_an_axis(tmp_path):
    capture = load_phyphox_csv(_write(tmp_path / "f.csv", with_absolute=True))
    assert len(capture.axes) == 3


def test_rejects_file_without_time_column(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text('"t","Acceleration x (m/s^2)"\n1,2\n2,3\n', encoding="utf-8")
    with pytest.raises(ValueError, match="Time"):
        load_phyphox_csv(path)


def test_rejects_non_increasing_timestamps(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text('"Time (s)","Acceleration x (m/s^2)"\n1,2\n1,3\n0.5,1\n',
                    encoding="utf-8")
    with pytest.raises(ValueError, match="increasing"):
        load_phyphox_csv(path)


def test_sample_rate_stats_on_regular_and_jittered_timing():
    regular = np.arange(1000) / 500.0
    stats = sample_rate_stats(regular)
    assert stats["median_rate_hz"] == pytest.approx(500.0)
    assert stats["jitter_pct"] == pytest.approx(0.0, abs=1e-6)
    jittered, *_ = _fixture_signal(rate_hz=400.0, jitter=0.2)
    assert sample_rate_stats(jittered)["jitter_pct"] > 5.0


def test_resampling_recovers_tone_from_jittered_samples():
    t, _, _, z = _fixture_signal(rate_hz=400.0, tone_hz=20.0, jitter=0.2)
    grid, uniform = resample_uniform(t, z, 400.0)
    assert np.allclose(np.diff(grid), 1.0 / 400.0)
    spectrum = np.abs(np.fft.rfft((uniform - uniform.mean()) * np.hanning(uniform.size)))
    freqs = np.fft.rfftfreq(uniform.size, d=1.0 / 400.0)
    assert freqs[int(np.argmax(spectrum))] == pytest.approx(20.0, abs=0.2)


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "analyze_phone", ROOT / "scripts" / "analyze_phone.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_writes_phone_labelled_summary(tmp_path):
    script = _load_script()
    capture = _write(tmp_path / "20261119-1030_phone_baseline_high_tape-mark_r1.csv")
    out = tmp_path / "out"
    assert script.main([str(capture), "--shaft-hz", "20", "--out", str(out)]) == 0
    text = (out / "summary.csv").read_text(encoding="utf-8")
    assert text.startswith("# data_origin: phone")
    assert ",baseline,high,tape-mark,1," in text
    header = text.splitlines()[2].split(",")
    values = text.splitlines()[3].split(",")
    row = dict(zip(header, values))
    assert float(row["z_peak_hz"]) == pytest.approx(20.0, abs=0.5)
    assert float(row["z_1x_rms"]) == pytest.approx(0.3 / np.sqrt(2), rel=0.1)
    assert (out / "20261119-1030_phone_baseline_high_tape-mark_r1.png").stat().st_size > 0


def test_script_flags_unlabelled_file_names(tmp_path, capsys):
    script = _load_script()
    capture = _write(tmp_path / "Accelerometer.csv")
    script.main([str(capture), "--out", str(tmp_path / "out")])
    assert "naming convention" in capsys.readouterr().err
    assert "UNLABELLED" in (tmp_path / "out" / "summary.csv").read_text(encoding="utf-8")


def test_script_refuses_synthetic_output_folder(tmp_path):
    script = _load_script()
    capture = _write(tmp_path / "f.csv")
    with pytest.raises(SystemExit):
        script.main([str(capture), "--out", str(tmp_path / "synthetic" / "out")])

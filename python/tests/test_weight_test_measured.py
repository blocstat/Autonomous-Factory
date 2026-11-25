"""Regression: the weight-test script on the real 24 Nov 2026 captures.

These use MEASURED data (data_origin adxl355, data/measured/adxl355/raw/),
a USB cooling pad on the bench, not a machine. The expected results are the
conclusions written in docs/PHASE1_WEIGHT_TEST_2026-11-24.md; the script must
keep agreeing with them. Skipped if the captures are not in the checkout.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from af_signal.weight_test import INCONCLUSIVE, NOT_DETECTED, analyse, capture_from_file

RAW = Path(__file__).resolve().parents[2] / "data" / "measured" / "adxl355" / "raw"


def _files(*prefixes: str) -> list[Path]:
    files = sorted(p for prefix in prefixes for p in RAW.glob(f"{prefix}_adxl355_*.csv"))
    if not files:
        pytest.skip(f"captures {prefixes} not in this checkout")
    return files


def _run(off1, on, off2, rule="auto"):
    captures = (
        [capture_from_file(p, "off") for p in _files(*off1)]
        + [capture_from_file(p, "on") for p in _files(*on)]
        + [capture_from_file(p, "off") for p in _files(*off2)]
    )
    return analyse(captures, axis="y", rule=rule)


def _grown(report) -> bool:
    return "-> grown" in " ".join(report.notes)


def test_first_weights_rub_detected_imbalance_untested():
    report = _run(["20261124-0711", "20261124-0712"], ["20261124-0731", "20261124-0732",
                  "20261124-0733"], ["20261124-0742", "20261124-0743", "20261124-0744"])
    assert report.rub_verdict == "DETECTED"
    assert report.rub_ratio > 5
    assert report.verdict == INCONCLUSIVE
    assert not _grown(report)


@pytest.mark.parametrize(
    "off1, on, off2",
    [
        # tape on the middle fan
        (["20261124-0742", "20261124-0743", "20261124-0744"], ["20261124-0813", "20261124-0814"],
         ["20261124-0820", "20261124-0821"]),
        # small screw on the middle fan
        (["20261124-0820", "20261124-0821"], ["20261124-0837", "20261124-0838"],
         ["20261124-0849", "20261124-0850"]),
        # taped screw on the middle fan, steady fans
        (["20261124-1032", "20261124-1033"], ["20261124-1047", "20261124-1048"],
         ["20261124-1109", "20261124-1110"]),
    ],
    ids=["tape-middle", "screw-middle", "screw-middle-steady"],
)
def test_middle_fan_weights_no_1x_growth_and_speeds_moved(off1, on, off2):
    report = _run(off1, on, off2)
    assert report.rub_verdict == NOT_DETECTED
    assert report.verdict == INCONCLUSIVE  # fan speeds moved more than 1 % between baselines
    assert not _grown(report)


def test_left_fan_screw_1x_grows_but_inconclusive_by_drift():
    report = _run(["20261124-1109", "20261124-1110"], ["20261124-1143", "20261124-1144"],
                  ["20261124-1152", "20261124-1153"])
    assert report.rub_verdict == NOT_DETECTED
    assert report.verdict == INCONCLUSIVE
    assert _grown(report)
    weighted = report.groups[1]
    assert weighted.level > 3 * report.groups[0].level
    # The line sits at 26.3-26.6 Hz in the two clear captures (r1, r3).
    assert sorted(c.level_freq_hz for c in weighted.captures)[0] == pytest.approx(26.3, abs=0.2)


def test_frame_mount_night_fixed_band_dry_run():
    """25 Nov frame-mount captures (MEASURED). The 13-19 Hz band was chosen after seeing
    these captures, so this PASS is a dry run of the code, not evidence; the evidence must
    come from a fresh session analysed with the same command."""
    off1 = _files("20261125-0052", "20261125-0053")
    on1 = _files("20261125-0102", "20261125-0103")
    off2 = _files("20261125-0112", "20261125-0113", "20261125-0129", "20261125-0130")
    on2 = _files("20261125-0149", "20261125-0150")
    off3 = _files("20261125-0201", "20261125-0202")
    captures = (
        [capture_from_file(p, "off") for p in off1]
        + [capture_from_file(p, "on") for p in on1]
        + [capture_from_file(p, "off") for p in off2]
        + [capture_from_file(p, "on") for p in on2]
        + [capture_from_file(p, "off") for p in off3]
    )
    report = analyse(captures, axis="z", band=(13.0, 19.0))
    assert report.groups[0].level * 1e6 == pytest.approx(653, abs=5)
    assert report.verdict == "PASS"
    assert report.rub_verdict == NOT_DETECTED

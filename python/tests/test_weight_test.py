"""Known-answer tests for af_signal.weight_test.

Every capture here is SYNTHETIC (data_origin "synthetic"): three made-up fans
with lines at 1x, 2x, 4x, 6x and 9x their speed, plus white noise of about the
board's measured floor. Passing shows the code finds what was put into the
signals and applies the rules as written. It says nothing about real fans,
sensors or machines.
"""

from __future__ import annotations

import numpy as np
import pytest

from af_signal import DATA_ORIGIN_SYNTHETIC
from af_signal.weight_test import (
    INCONCLUSIVE,
    NOT_DETECTED,
    PASS,
    CaptureInput,
    analyse,
    format_report,
    group_runs,
    quality_problems,
    state_for_condition,
)

RATE = 4010.3
DURATION_S = 30.0
SPEEDS = (20.0, 24.5, 28.0)  # Hz, synthetic fans
NOISE_ASD_G = 20e-6  # g/sqrt(Hz), about the board's floor
LINE_AMPLITUDE_G = {2: 300e-6, 4: 300e-6, 6: 300e-6, 9: 300e-6}
ONE_X_BASE_G = 15e-6  # a 1x line near the floor
ONE_X_WEIGHT_G = 200e-6  # a clear 1x line


def synthetic_capture(
    name: str,
    state: str,
    seed: int,
    speeds=SPEEDS,
    one_x_g=(ONE_X_BASE_G,) * 3,
    rub_g: float = 0.0,
    problems: tuple[str, ...] = (),
    z_tone: tuple[float, float] | None = None,
    bump_g: float = 0.0,
) -> CaptureInput:
    rng = np.random.default_rng(seed)
    n = int(DURATION_S * RATE)
    t = np.arange(n) / RATE
    sigma = NOISE_ASD_G * np.sqrt(RATE / 2.0)
    g = rng.normal(0.0, sigma, size=(n, 3))
    for speed, one in zip(speeds, one_x_g):
        phases = rng.uniform(0, 2 * np.pi, size=6)
        g[:, 1] += one * np.sin(2 * np.pi * speed * t + phases[0])  # 1x on y
        g[:, 2] += 0.5 * one * np.sin(2 * np.pi * speed * t + phases[1])
        for j, (k, amp) in enumerate(LINE_AMPLITUDE_G.items()):
            for axis in range(3):
                g[:, axis] += amp * np.sin(2 * np.pi * k * speed * t + phases[2 + j] + axis)
    if rub_g:
        # Knocks: decaying 1.1 kHz bursts repeating 13.7 times a second.
        phase = (t * 13.7) % 1.0
        burst = np.exp(-phase / 0.2) * np.sin(2 * np.pi * 1100.0 * t)
        g += rub_g * burst[:, None]
    if z_tone:
        g[:, 2] += z_tone[1] * np.sin(2 * np.pi * z_tone[0] * t)
    if bump_g:
        # One knock on the desk at 10 s: a short 1 kHz burst.
        start = int(10 * RATE)
        tt = t[start : start + 400] - t[start]
        g[start : start + 400, :] += (bump_g * np.exp(-tt / 0.01) * np.sin(2 * np.pi * 1000 * tt))[
            :, None
        ]
    g[:, 2] += 1.0  # gravity
    return CaptureInput(
        name=name,
        g=g,
        rate_hz=RATE,
        state=state,
        data_origin=DATA_ORIGIN_SYNTHETIC,
        quality_problems=problems,
    )


def round_of(state, seed0, repeats=3, **kwargs):
    return [synthetic_capture(f"{state}{seed0 + i}", state, seed0 + i, **kwargs)
            for i in range(repeats)]


def test_tracks_synthetic_fan_speeds_within_0_05_hz():
    captures = round_of("off", 1) + round_of("on", 10) + round_of("off", 20)
    report = analyse(captures)
    for group in report.groups:
        assert len(group.speeds_hz) == 3
        for found, true in zip(group.speeds_hz, SPEEDS):
            assert found == pytest.approx(true, abs=0.05)


def test_1x_follows_a_fan_that_changed_speed():
    # The weighted fan runs 2 % faster; its 1x is still found at its new speed.
    faster = (SPEEDS[0], SPEEDS[1] * 1.02, SPEEDS[2])
    weighted = (ONE_X_BASE_G, ONE_X_WEIGHT_G, ONE_X_BASE_G)
    captures = (
        round_of("off", 1)
        + round_of("on", 10, speeds=faster, one_x_g=weighted)
        + round_of("off", 20)
    )
    report = analyse(captures)
    for capture in report.groups[1].captures:
        assert capture.level_freq_hz == pytest.approx(faster[1], abs=0.15)
    assert report.verdict == PASS


def test_detect_rule_passes_when_1x_grows():
    weighted = (ONE_X_BASE_G, ONE_X_WEIGHT_G, ONE_X_BASE_G)
    captures = round_of("off", 1) + round_of("on", 10, one_x_g=weighted) + round_of("off", 20)
    report = analyse(captures)
    assert report.rule == "detect"
    assert report.rub_verdict == NOT_DETECTED
    assert report.verdict == PASS


def test_detect_rule_not_detected_without_change():
    captures = round_of("off", 1) + round_of("on", 10) + round_of("off", 20)
    assert analyse(captures).verdict == NOT_DETECTED


def test_speed_drift_over_1_percent_is_inconclusive():
    weighted = (ONE_X_BASE_G, ONE_X_WEIGHT_G, ONE_X_BASE_G)
    drifted = tuple(s * 1.02 for s in SPEEDS)  # baseline-after 2 % faster
    captures = (
        round_of("off", 1)
        + round_of("on", 10, one_x_g=weighted)
        + round_of("off", 20, speeds=drifted)
    )
    report = analyse(captures)
    assert report.verdict == INCONCLUSIVE
    assert report.drifts[0].worst == pytest.approx(0.02, abs=0.003)


def test_speed_drift_under_1_percent_is_allowed():
    weighted = (ONE_X_BASE_G, ONE_X_WEIGHT_G, ONE_X_BASE_G)
    drifted = tuple(s * 1.004 for s in SPEEDS)
    captures = (
        round_of("off", 1)
        + round_of("on", 10, one_x_g=weighted)
        + round_of("off", 20, speeds=drifted)
    )
    assert analyse(captures).verdict == PASS


def test_rub_is_detected_and_blocks_the_1x_rule():
    weighted = (ONE_X_BASE_G, ONE_X_WEIGHT_G, ONE_X_BASE_G)
    captures = (
        round_of("off", 1)
        + round_of("on", 10, one_x_g=weighted, rub_g=5e-3)
        + round_of("off", 20)
    )
    report = analyse(captures)
    assert report.rub_verdict == "DETECTED"
    assert report.rub_ratio > 1.5
    assert report.verdict == INCONCLUSIVE


def test_bad_data_path_is_inconclusive():
    weighted = (ONE_X_BASE_G, ONE_X_WEIGHT_G, ONE_X_BASE_G)
    captures = (
        round_of("off", 1)
        + round_of("on", 10, one_x_g=weighted, problems=("missing_sets=3",))
        + round_of("off", 20)
    )
    report = analyse(captures)
    assert report.verdict == INCONCLUSIVE
    assert "missing_sets=3" in " ".join(report.reasons)


def test_confirm_rule_passes_when_every_round_agrees():
    # With these seeds, 3 of the 6 later unweighted captures are slightly above the
    # highest first-baseline capture (noise only). The literal "no higher than the
    # baseline's highest" reading would call this NOT DETECTED; the rule as coded
    # ("below the 3x threshold") does not.
    weighted = (ONE_X_BASE_G, ONE_X_WEIGHT_G, ONE_X_BASE_G)
    captures = (
        round_of("off", 1)
        + round_of("on", 10, one_x_g=weighted)
        + round_of("off", 20)
        + round_of("on", 30, one_x_g=weighted)
        + round_of("off", 40)
    )
    report = analyse(captures)
    assert report.rule == "confirm"
    assert report.verdict == PASS


def test_confirm_rule_fails_if_one_weighted_capture_is_weak():
    weighted = (ONE_X_BASE_G, ONE_X_WEIGHT_G, ONE_X_BASE_G)
    weak = synthetic_capture("on-weak", "on", 99, one_x_g=(ONE_X_BASE_G,) * 3)
    captures = (
        round_of("off", 1)
        + round_of("on", 10, one_x_g=weighted)
        + round_of("off", 20)
        + round_of("on", 30, repeats=2, one_x_g=weighted)
        + [weak]
        + round_of("off", 40)
    )
    report = analyse(captures)
    assert report.verdict == NOT_DETECTED
    assert any("on-weak" in reason for reason in report.reasons)


def test_confirm_rule_fails_if_line_does_not_go_away():
    weighted = (ONE_X_BASE_G, ONE_X_WEIGHT_G, ONE_X_BASE_G)
    captures = (
        round_of("off", 1)
        + round_of("on", 10, one_x_g=weighted)
        + round_of("off", 20, one_x_g=weighted)  # weight "removed" but the line stays
        + round_of("on", 30, one_x_g=weighted)
        + round_of("off", 40)
    )
    assert analyse(captures).verdict == NOT_DETECTED


def test_report_labels_synthetic_data():
    captures = round_of("off", 1) + round_of("on", 10) + round_of("off", 20)
    text = format_report(analyse(captures))
    assert "SYNTHETIC -- NOT A MEASUREMENT" in text


def test_rejects_mixed_origins_and_bad_order():
    off = round_of("off", 1)
    on = round_of("on", 10)
    with pytest.raises(ValueError, match="start|starting"):
        analyse(on + off)
    real_looking = CaptureInput("x", off[0].g, RATE, "off", "adxl355")
    with pytest.raises(ValueError, match="mix data origins"):
        analyse(off + on + [real_looking])


def test_grouping_and_header_helpers():
    assert state_for_condition("baseline") == "off"
    assert state_for_condition("baseline-after") == "off"
    assert state_for_condition("screw-left") == "on"
    assert state_for_condition("sham-restart") == "off"
    for name in ("steady-check", "fans-off", ""):
        with pytest.raises(ValueError, match="not part of a weight round"):
            state_for_condition(name)
    states = ["off", "off", "on", "on", "off"]
    caps = [CaptureInput(str(i), np.zeros((10, 3)), RATE, s, DATA_ORIGIN_SYNTHETIC)
            for i, s in enumerate(states)]
    assert [len(run) for run in group_runs(caps)] == [2, 2, 1]
    clean = {k: "0" for k in ("missing_sets", "crc_errors", "sequence_gaps", "restarts",
                              "frames_flagged_overrun", "frames_flagged_dropped")}
    assert quality_problems(clean) == ()
    assert quality_problems({**clean, "crc_errors": "2"}) == ("crc_errors=2",)
    assert "restarts not recorded" in quality_problems(
        {k: v for k, v in clean.items() if k != "restarts"}
    )


# ---- fixed band (pre-registered frame-mount test: z, 13-19 Hz) -- SYNTHETIC ----

BAND = (13.0, 19.0)
LOW_LINE = (15.0, 2e-3)  # a 2 mg line at 15 Hz on z, made up


def test_fixed_band_passes_when_low_line_comes_and_goes():
    captures = (
        round_of("off", 1)
        + round_of("on", 10, z_tone=LOW_LINE)
        + round_of("off", 20)
        + round_of("on", 30, z_tone=LOW_LINE)
        + round_of("off", 40)
    )
    report = analyse(captures, axis="z", band=BAND)
    assert report.rule == "confirm"
    assert report.verdict == PASS
    for capture in report.groups[1].captures:
        assert capture.level_freq_hz == pytest.approx(15.0, abs=0.15)


def test_fixed_band_one_round_uses_confirm_rule():
    captures = round_of("off", 1) + round_of("on", 10, z_tone=LOW_LINE) + round_of("off", 20)
    report = analyse(captures, axis="z", band=BAND)
    assert report.rule == "confirm"
    assert report.verdict == PASS


def test_fixed_band_not_detected_if_line_stays_after_removal():
    captures = (
        round_of("off", 1)
        + round_of("on", 10, z_tone=LOW_LINE)
        + round_of("off", 20, z_tone=LOW_LINE)
        + round_of("on", 30, z_tone=LOW_LINE)
        + round_of("off", 40)
    )
    assert analyse(captures, axis="z", band=BAND).verdict == NOT_DETECTED


def test_fixed_band_ignores_lines_outside_the_band():
    # The same line at 21 Hz is outside 13-19 Hz, so nothing is detected.
    captures = round_of("off", 1) + round_of("on", 10, z_tone=(21.0, 2e-3)) + round_of("off", 20)
    assert analyse(captures, axis="z", band=BAND).verdict == NOT_DETECTED


def test_bumped_capture_is_left_out_of_the_confirm_rule():
    # A desk knock in one screw-off capture that also carries the line: it is reported
    # and left out, so the remaining captures decide.
    knocked = synthetic_capture("off-knock", "off", 77, z_tone=LOW_LINE, bump_g=0.3)
    captures = (
        round_of("off", 1)
        + round_of("on", 10, z_tone=LOW_LINE)
        + round_of("off", 20, repeats=2)
        + [knocked]
        + round_of("on", 30, z_tone=LOW_LINE)
        + round_of("off", 40)
    )
    report = analyse(captures, axis="z", band=BAND)
    bumped = [c for g in report.groups for c in g.captures if c.name == "off-knock"][0]
    assert bumped.kurtosis_z > 5
    assert any("off-knock" in note and "bump" in note for note in report.notes)
    assert report.verdict == PASS


def test_rejects_bad_band():
    captures = round_of("off", 1) + round_of("on", 10) + round_of("off", 20)
    with pytest.raises(ValueError, match="band"):
        analyse(captures, axis="z", band=(19.0, 13.0))
    with pytest.raises(ValueError, match="confirm rule"):
        analyse(captures, axis="z", rule="detect", band=BAND)

"""Known-answer tests for af_signal.rotor (floor-fan session 1 measures).

Every signal here is SYNTHETIC (data_origin "synthetic"): a made-up single
3-blade rotor with lines at 1x, 2x, 3x and 6x its speed, a 120 Hz line and
white noise near the board's floor. Passing shows the code recovers what was
put in. It says nothing about real fans, sensors or machines.
"""

from __future__ import annotations

import numpy as np
import pytest

from af_signal.rotor import block_spreads, measure_capture, spread, warmup

RATE = 4010.3
NOISE_ASD_G = 20e-6


def rotor_signal(speed_hz, seconds=30.0, seed=0, one_x=400e-6, blade=800e-6, mains=300e-6,
                 speed_profile=None):
    rng = np.random.default_rng(seed)
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    if speed_profile is None:
        phase = 2 * np.pi * speed_hz * t
    else:
        phase = 2 * np.pi * np.cumsum(speed_profile(t)) / RATE
    g = rng.normal(0, NOISE_ASD_G * np.sqrt(RATE / 2), size=(n, 3))
    g[:, 1] += one_x * np.sin(phase)
    g[:, 0] += 0.3 * one_x * np.sin(2 * phase + 0.4)
    g[:, 2] += blade * np.sin(3 * phase + 1.1)
    g[:, 2] += 0.5 * blade * np.sin(6 * phase + 0.2)
    g[:, 2] += mains * np.sin(2 * np.pi * 120.0 * t)
    g[:, 2] += 1.0  # gravity
    return g


@pytest.mark.parametrize("speed", [12.4, 19.7, 23.15, 27.6])
def test_speed_recovered_within_0p1_hz(speed):
    m = measure_capture("synthetic", rotor_signal(speed), RATE)
    assert m.speed_hz == pytest.approx(speed, abs=0.1)


def test_levels_scale_with_the_lines_within_5_percent():
    a = measure_capture("a", rotor_signal(21.0, seed=1), RATE)
    b = measure_capture("b", rotor_signal(21.0, seed=2, one_x=800e-6, blade=1600e-6,
                                          mains=600e-6), RATE)
    assert b.one_x_g[1] / a.one_x_g[1] == pytest.approx(2.0, rel=0.05)
    assert b.blade_pass_g[2] / a.blade_pass_g[2] == pytest.approx(2.0, rel=0.05)
    assert b.mains_line_g[2] / a.mains_line_g[2] == pytest.approx(2.0, rel=0.05)


def test_broadband_matches_the_signal_rms():
    g = rotor_signal(21.0, seed=3, mains=0.0)
    m = measure_capture("c", g, RATE)
    # z: blade pass 800 ug and 6x 400 ug sines plus noise from 10 to 1000 Hz
    expected = np.sqrt(800e-6**2 / 2 + 400e-6**2 / 2 + NOISE_ASD_G**2 * 990)
    assert m.broadband_g[2] == pytest.approx(expected, rel=0.05)


def test_no_knock_in_steady_signal():
    m = measure_capture("d", rotor_signal(21.0, seed=4), RATE)
    assert not m.bumped


def test_warmup_settles_when_the_ramp_ends():
    # speed rises 19 -> 21 Hz over the first 4 minutes, then holds (10 min in all)
    profile = lambda t: np.where(t < 240, 19.0 + 2.0 * t / 240, 21.0)  # noqa: E731
    g = rotor_signal(None, seconds=600.0, seed=5, speed_profile=profile)
    pieces, settled = warmup(g, RATE)
    assert len(pieces) == 20
    assert pieces[-1].speed_hz == pytest.approx(21.0, abs=0.1)
    # within 0.5 % (0.105 Hz) of 21 Hz once the speed passes ~20.9 Hz, i.e. by about 3.5-4 min
    assert settled is not None and 180 <= settled <= 240


def test_spreads_and_bad_data_left_out():
    good = [measure_capture(f"r{i}", rotor_signal(21.0 + 0.02 * i, seed=10 + i), RATE)
            for i in range(3)]
    bad = measure_capture("bad", rotor_signal(25.0, seed=20, one_x=4e-3), RATE,
                          quality=("missing_sets=3",))
    out = block_spreads(good + [bad])
    assert out["n"] == 3
    assert out["speed_range_pct"] < 0.5
    assert 1.0 <= out["one_x_g_y"] < 1.2
    assert np.isnan(spread([1.0]))

"""Known-answer tests for af_signal.fan_change (floor-fan session 2 rule).

Every signal is SYNTHETIC (data_origin "synthetic"), from test_rotor's made-up
3-blade rotor. A "cardboard" effect here is just broadband noise added on y.
Passing shows the rule does what it says. It says nothing about real fans.
"""

from __future__ import annotations

import numpy as np

from af_signal.fan_change import compare, fold, session2_verdict
from af_signal.rotor import measure_capture
from tests.test_rotor import RATE, rotor_signal


def captures(tag, speed=22.4, n=3, extra_y_noise=0.0, seed=0, quality=()):
    out = []
    for i in range(n):
        g = rotor_signal(speed + 0.01 * i, seconds=20.0, seed=seed + i)
        if extra_y_noise:
            g[:, 1] += np.random.default_rng(seed + 100 + i).normal(0, extra_y_noise, g.shape[0])
        out.append(measure_capture(f"{tag}{i}", g, RATE, quality))
    return out


def session(cardboard_noise=0.0, cardboard_speed=22.4, sham_noise=0.0, seed=0):
    return {
        "baseline": captures("b", seed=seed),
        "cardboard-1": captures("c1", cardboard_speed, extra_y_noise=cardboard_noise, seed=seed + 10),
        "after-1": captures("a1", seed=seed + 20),
        "sham": captures("s", extra_y_noise=sham_noise, seed=seed + 30),
        "cardboard-2": captures("c2", cardboard_speed, extra_y_noise=cardboard_noise, seed=seed + 40),
        "after-2": captures("a2", seed=seed + 50),
    }


# Without the change, y broadband (10-1000 Hz) is about 690 ug: the 1x sine
# (283 ug RMS) plus the 20 ug/rtHz floor (630 ug). 2 mg of extra white noise
# over 0-2 kHz adds about 1.4 mg in the band, so about 2.3x. Sham noise the same.
def test_big_change_is_detected():
    assert session2_verdict(session(cardboard_noise=2e-3)).verdict == "DETECTED"


def test_no_change_is_not_detected():
    assert session2_verdict(session()).verdict == "NOT DETECTED"


def test_speed_shift_blocks_the_comparison():
    v = session2_verdict(session(cardboard_noise=2e-3, cardboard_speed=23.0))  # +2.7 %
    assert v.verdict == "SPEED SHIFTED"


def test_sham_that_moves_makes_it_inconclusive():
    v = session2_verdict(session(cardboard_noise=2e-3, sham_noise=2e-3))
    assert v.verdict == "INCONCLUSIVE"
    assert any("sham" in r for r in v.reasons)


def test_bad_data_left_out_and_too_few_is_inconclusive():
    s = session()
    s["baseline"] = captures("b", n=3, quality=("missing_sets=4",))
    v = session2_verdict(s)
    assert v.verdict == "INCONCLUSIVE"


def test_ratio_and_fold():
    ref = captures("r", seed=1)
    c = compare("same", ref, captures("t", seed=5))
    assert 0.9 < c.primary_ratio < 1.1 and c.n_test == 3
    assert fold(0.5) == fold(2.0) == 2.0

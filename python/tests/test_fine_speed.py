"""Known-answer tests for af_signal.fine_speed (floor-fan speed test).

All signals are SYNTHETIC (data_origin "synthetic"): test_rotor's made-up
3-blade rotor. Passing shows the code recovers what was put in; it says
nothing about real fans.
"""

from __future__ import annotations

import numpy as np
import pytest

from af_signal.fine_speed import fine_speed, speed_verdict
from tests.test_rotor import RATE, rotor_signal


@pytest.mark.parametrize("speed", [17.13, 19.9431, 22.837, 23.0])
def test_fine_speed_within_2_mhz(speed):
    r = fine_speed(rotor_signal(speed, seed=3), RATE)
    assert r.speed_hz == pytest.approx(speed, abs=0.002)
    assert len(r.harmonics_used) >= 2


def test_resolves_a_quarter_percent_step():
    a = fine_speed(rotor_signal(22.80, seed=1), RATE).speed_hz
    b = fine_speed(rotor_signal(22.857, seed=2), RATE).speed_hz  # +0.25 %
    assert 100 * (b - a) / a == pytest.approx(0.25, abs=0.02)


def blocks(effect_pct, drift_hz=0.0, scatter_hz=0.0, seed=0):
    """Block fine speeds (3 per block) for N0 C1 N1 ... C4 N4, base 22.8 Hz."""
    rng = np.random.default_rng(seed)
    no, ca = [], []
    for k in range(9):
        base = 22.8 + drift_hz * k + rng.normal(0, scatter_hz)
        if k % 2:
            base *= 1 + effect_pct / 100
        caps = list(base + rng.normal(0, 0.005, 3))
        (ca if k % 2 else no).append(caps)
    return no, ca


def test_clear_speed_up_is_detected_even_with_drift():
    v = speed_verdict(*blocks(0.8, drift_hz=0.02))
    assert v.verdict == "DETECTED"
    assert all(x == pytest.approx(0.8, abs=0.05) for x in v.d_pct)


def test_no_change_is_not_detected():
    assert speed_verdict(*blocks(0.0, drift_hz=0.02)).verdict == "NOT DETECTED"


def test_wild_restart_scatter_makes_it_inconclusive():
    no, ca = blocks(0.8)
    no[2] = [x * 1.01 for x in no[2]]  # one no-carton block 1 % high: d = .8 .3 .3 .8, e_2 = 1 %
    v = speed_verdict(no, ca)
    assert v.verdict == "INCONCLUSIVE"


def test_too_few_captures_is_inconclusive():
    no, ca = blocks(0.8)
    ca[1] = [22.9]
    assert speed_verdict(no, ca).verdict == "INCONCLUSIVE"

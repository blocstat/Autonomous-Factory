"""Floor-fan session 2 rule: did cardboard on the rear intake change the vibration?

Fixed before session 2's data (docs/PHASE1_FLOOR_FAN_SESSION2_PREREG.md), from
session 1's spreads (docs/PHASE1_FLOOR_FAN_RESULTS_2026-11-27.md). A household
fan, not a machine: a result says what this sensor sees on this fan, nothing
about faults or prediction.

Blocks, in order, all at knob setting 3:
  baseline r1-r3 | cardboard r1-r3 | baseline-after r1-r3 |
  sham-restart r1-r3 | cardboard r4-r6 | baseline-after r4-r6

Each cardboard round is compared with the no-cardboard block just before it
(round 1: baseline; round 2: sham-restart). Ratios are of block medians.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from af_signal.rotor import RotorMeasure

PASS_RATIO = 1.25  # primary: 10-1000 Hz RMS, y axis (session 1 largest no-change spread 1.11x)
SECONDARY_RATIO = 1.5  # 1x line, y axis (session 1 largest 1.34x); reported, does not decide
SPEED_TOLERANCE = 0.01  # a capture counts only within +/-1 % of its reference block's median speed
MIN_CAPTURES = 2
Y = 1

PRIMARY = ("broadband_g", Y)
SECONDARY = ("one_x_g", Y)


def usable(measures: Sequence[RotorMeasure]) -> list[RotorMeasure]:
    return [m for m in measures if not m.bumped and not m.quality_problems]


def median_speed(measures: Sequence[RotorMeasure]) -> float:
    return float(np.median([m.speed_hz for m in measures]))


def speed_matched(measures: Sequence[RotorMeasure], reference_hz: float) -> list[RotorMeasure]:
    return [m for m in measures if abs(m.speed_hz - reference_hz) <= SPEED_TOLERANCE * reference_hz]


def level(measures: Sequence[RotorMeasure], key: tuple[str, int]) -> float:
    name, axis = key
    return float(np.median([getattr(m, name)[axis] for m in measures]))


def fold(ratio: float) -> float:
    """Size of a change regardless of direction (1.3 and 1/1.3 are both 1.3)."""
    return max(ratio, 1.0 / ratio)


@dataclass
class Comparison:
    name: str
    n_reference: int
    n_test: int  # speed-matched, clean
    n_test_all: int  # clean, any speed
    speed_change_pct: float  # median test speed vs reference, all clean test captures
    primary_ratio: float = float("nan")
    secondary_ratio: float = float("nan")

    @property
    def enough(self) -> bool:
        return self.n_reference >= MIN_CAPTURES and self.n_test >= MIN_CAPTURES


def compare(name: str, reference: Sequence[RotorMeasure], test: Sequence[RotorMeasure]) -> Comparison:
    ref, tst = usable(reference), usable(test)
    if len(ref) < MIN_CAPTURES or not tst:
        return Comparison(name, len(ref), 0, len(tst), float("nan"))
    ref_speed = median_speed(ref)
    matched = speed_matched(tst, ref_speed)
    c = Comparison(name, len(ref), len(matched), len(tst),
                   100.0 * (median_speed(tst) - ref_speed) / ref_speed)
    if len(matched) >= MIN_CAPTURES:
        c.primary_ratio = level(matched, PRIMARY) / level(ref, PRIMARY)
        c.secondary_ratio = level(matched, SECONDARY) / level(ref, SECONDARY)
    return c


@dataclass
class Verdict:
    verdict: str  # DETECTED / NOT DETECTED / SPEED SHIFTED / INCONCLUSIVE
    reasons: list[str] = field(default_factory=list)
    comparisons: list[Comparison] = field(default_factory=list)


def session2_verdict(blocks: dict[str, Sequence[RotorMeasure]]) -> Verdict:
    """``blocks`` keys: baseline, cardboard-1, after-1, sham, cardboard-2, after-2."""
    rounds = [compare("round 1: cardboard vs baseline", blocks["baseline"], blocks["cardboard-1"]),
              compare("round 2: cardboard vs sham restart", blocks["sham"], blocks["cardboard-2"])]
    guards = [compare("sham restart vs baseline-after 1", blocks["after-1"], blocks["sham"]),
              compare("baseline-after 1 vs baseline", blocks["baseline"], blocks["after-1"]),
              compare("baseline-after 2 vs sham restart", blocks["sham"], blocks["after-2"])]
    out = Verdict("INCONCLUSIVE", comparisons=rounds + guards)

    # 1. Enough clean data in every block.
    for c in rounds + guards:
        if c.n_reference < MIN_CAPTURES or c.n_test_all < MIN_CAPTURES:
            out.reasons.append(f"{c.name}: fewer than {MIN_CAPTURES} clean captures")
    if out.reasons:
        return out

    # 2. Cardboard moved the speed out of the window: no speed-matched comparison.
    shifted = [c for c in rounds if c.n_test < MIN_CAPTURES]
    if shifted:
        out.verdict = "SPEED SHIFTED"
        out.reasons += [f"{c.name}: speed changed {c.speed_change_pct:+.2f} %, "
                        f"{c.n_test} of {c.n_test_all} captures within +/-1 %" for c in shifted]
        return out

    # 3. Guards: nothing-changed comparisons must stay under the pass mark.
    for c in guards:
        if not c.enough:
            out.reasons.append(f"{c.name}: speed outside +/-1 % ({c.speed_change_pct:+.2f} %)")
        elif fold(c.primary_ratio) >= PASS_RATIO:
            out.reasons.append(f"{c.name}: {c.primary_ratio:.2f}x with no cardboard")
    if out.reasons:
        return out

    # 4. The rule.
    big = [fold(c.primary_ratio) >= PASS_RATIO for c in rounds]
    same_direction = np.sign(np.log(rounds[0].primary_ratio)) == np.sign(np.log(rounds[1].primary_ratio))
    if all(big) and same_direction:
        out.verdict = "DETECTED"
    elif not any(big):
        out.verdict = "NOT DETECTED"
    else:
        out.reasons.append("the two cardboard rounds disagree")
    return out

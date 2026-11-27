"""Describe a single-rotor fan from ADXL355 captures: speed, line levels, spreads.

Written for floor-fan session 1 (docs/PHASE1_FLOOR_FAN_PLAN.md), with the
definitions fixed there before the data. It measures and reports; it does not
decide PASS / FAIL. Bench test on a household fan, not a machine.

Per capture (Welch, Hann, 32,768 points, first 0.5 s skipped, as in weight_test):

- speed f0: for every candidate f in 8-30 Hz, the geometric mean over the lines
  1x, 2x, 3x and 6x f of the x+y+z spectrum divided by its running median
  (10 Hz wide); the best candidate, refined to the 1x peak within +/-0.3 Hz.
- 1x level: peak within +/-0.3 Hz of f0, per axis.
- blade-pass level: peak within +/-0.5 Hz of 3 f0, per axis (3 blades).
- 120 Hz level: peak between 119 and 121 Hz, per axis (twice the mains frequency).
- broadband: RMS from 10 to 1,000 Hz, per axis, from the spectrum.
- knocks: 800-1500 Hz z kurtosis (above 5 = a bump).

Warm-up: the long capture is cut into 30 s pieces; f0 and the 1x level are
measured in each. "Settled" is the start of the first piece from which every
later piece's f0 is within 0.5 % of the final value (median f0 of the last
2 minutes).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from scipy import ndimage

from af_signal.weight_test import (
    AXES,
    BUMP_KURTOSIS,
    COMB_FLOOR_WIDTH_HZ,
    NPERSEG,
    SETTLE_S,
    rub_level,
    spectrum,
)

BLADES = 3
HARMONICS = (1, 2, BLADES, 2 * BLADES)
SPEED_RANGE_HZ = (8.0, 30.0)
SPEED_STEP_HZ = 0.01
ONE_X_HALF_WIDTH_HZ = 0.3
BLADE_PASS_HALF_WIDTH_HZ = 0.5
MAINS_LINE_HZ = (119.0, 121.0)
BROADBAND_HZ = (10.0, 1000.0)
WARMUP_PIECE_S = 30.0
SETTLED_TOLERANCE = 0.005
SETTLED_TAIL_S = 120.0


@dataclass
class RotorMeasure:
    name: str
    speed_hz: float
    comb_score: float
    one_x_g: tuple[float, float, float]  # peak ASD per axis, g/sqrt(Hz)
    blade_pass_g: tuple[float, float, float]
    mains_line_g: tuple[float, float, float]
    broadband_g: tuple[float, float, float]  # RMS, g
    kurtosis_z: float
    quality_problems: tuple[str, ...] = ()

    @property
    def bumped(self) -> bool:
        return self.kurtosis_z > BUMP_KURTOSIS


def _peak(freqs: np.ndarray, asd: np.ndarray, low: float, high: float) -> tuple[float, ...]:
    sel = (freqs >= low) & (freqs <= high)
    if not sel.any():
        raise ValueError(f"no spectrum bins between {low} and {high} Hz")
    return tuple(float(v) for v in asd[sel].max(axis=0))


def speed_comb(freqs: np.ndarray, asd: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Candidate speeds and their comb score over the 1x, 2x, 3x and 6x lines."""
    summed = asd.sum(axis=1)
    step = float(freqs[1] - freqs[0])
    width = int(COMB_FLOOR_WIDTH_HZ / step) | 1
    floor = ndimage.median_filter(summed, size=width, mode="nearest")
    log_ratio = np.log(np.maximum(summed, 1e-30) / np.maximum(floor, 1e-30))
    log_ratio = ndimage.maximum_filter1d(log_ratio, size=3)  # allow +/-1 bin
    speeds = np.arange(SPEED_RANGE_HZ[0], SPEED_RANGE_HZ[1], SPEED_STEP_HZ)
    score = np.exp(np.mean([np.interp(k * speeds, freqs, log_ratio) for k in HARMONICS], axis=0))
    return speeds, score


def rotor_speed(freqs: np.ndarray, asd: np.ndarray) -> tuple[float, float]:
    """(f0 in Hz, comb score): best comb candidate, refined to the 1x peak +/-0.3 Hz."""
    speeds, score = speed_comb(freqs, asd)
    best = int(np.argmax(score))
    guess = float(speeds[best])
    sel = np.flatnonzero(np.abs(freqs - guess) <= ONE_X_HALF_WIDTH_HZ)
    refined = float(freqs[sel[np.argmax(asd[sel].sum(axis=1))]])
    return refined, float(score[best])


def measure_spectrum(freqs: np.ndarray, asd: np.ndarray) -> dict:
    f0, score = rotor_speed(freqs, asd)
    band = (freqs >= BROADBAND_HZ[0]) & (freqs <= BROADBAND_HZ[1])
    step = float(freqs[1] - freqs[0])
    return {
        "speed_hz": f0,
        "comb_score": score,
        "one_x_g": _peak(freqs, asd, f0 - ONE_X_HALF_WIDTH_HZ, f0 + ONE_X_HALF_WIDTH_HZ),
        "blade_pass_g": _peak(
            freqs, asd, BLADES * f0 - BLADE_PASS_HALF_WIDTH_HZ, BLADES * f0 + BLADE_PASS_HALF_WIDTH_HZ
        ),
        "mains_line_g": _peak(freqs, asd, *MAINS_LINE_HZ),
        "broadband_g": tuple(float(v) for v in np.sqrt((asd[band] ** 2).sum(axis=0) * step)),
    }


def measure_capture(name: str, g: np.ndarray, rate_hz: float,
                    quality: tuple[str, ...] = ()) -> RotorMeasure:
    freqs, asd = spectrum(g, rate_hz)
    _, kurt = rub_level(g, rate_hz)
    return RotorMeasure(name=name, kurtosis_z=kurt, quality_problems=quality,
                        **measure_spectrum(freqs, asd))


@dataclass
class WarmupPiece:
    start_s: float
    speed_hz: float
    one_x_g: tuple[float, float, float]


def warmup(g: np.ndarray, rate_hz: float) -> tuple[list[WarmupPiece], float | None]:
    """Pieces of WARMUP_PIECE_S and the settled time (s), or None if it never settles."""
    piece = int(round(WARMUP_PIECE_S * rate_hz))
    pieces: list[WarmupPiece] = []
    for i in range(g.shape[0] // piece):
        chunk = g[i * piece : (i + 1) * piece]
        if chunk.shape[0] - int(round(SETTLE_S * rate_hz)) < NPERSEG:
            break
        freqs, asd = spectrum(chunk, rate_hz)
        m = measure_spectrum(freqs, asd)
        pieces.append(WarmupPiece(i * WARMUP_PIECE_S, m["speed_hz"], m["one_x_g"]))
    tail = max(1, int(round(SETTLED_TAIL_S / WARMUP_PIECE_S)))
    if len(pieces) <= tail:
        return pieces, None
    final = float(np.median([p.speed_hz for p in pieces[-tail:]]))
    within = [abs(p.speed_hz - final) <= SETTLED_TOLERANCE * final for p in pieces]
    settled = None
    for i in range(len(pieces)):
        if all(within[i:]):
            settled = pieces[i].start_s
            break
    return pieces, settled


def spread(values: Sequence[float]) -> float:
    """max / min (1.0 = no spread); NaN for fewer than two values."""
    vals = [v for v in values if np.isfinite(v) and v > 0]
    if len(vals) < 2:
        return float("nan")
    return max(vals) / min(vals)


def speed_range_pct(speeds: Sequence[float]) -> float:
    if len(speeds) < 2:
        return float("nan")
    return 100.0 * (max(speeds) - min(speeds)) / float(np.median(speeds))


MEASURE_NAMES = ("one_x_g", "blade_pass_g", "mains_line_g", "broadband_g")


def block_spreads(measures: Sequence[RotorMeasure]) -> dict:
    """Spreads in one block, leaving out bumped and bad-data captures."""
    use = [m for m in measures if not m.bumped and not m.quality_problems]
    out: dict = {"n": len(use), "speed_range_pct": speed_range_pct([m.speed_hz for m in use])}
    for key in MEASURE_NAMES:
        for i, axis in enumerate(AXES):
            out[f"{key}_{axis}"] = spread([getattr(m, key)[i] for m in use])
    return out

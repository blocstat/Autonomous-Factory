"""Fine rotor speed for a 30 s capture: sub-bin estimate from several harmonics.

Written on 28 November 2026 for the floor-fan speed test
(docs/PHASE1_FLOOR_FAN_SPEED_PREREG.md), before its data. The session 1/2
speed (af_signal.rotor) is read off a 0.12 Hz Welch grid; this one is about
50x finer, so a speed change of a few tenths of a percent can be seen.

Method (fixed):
1. Coarse f0 from af_signal.rotor (comb over 1x, 2x, 3x, 6x).
2. Skip the first 0.5 s, remove each axis's mean, apply one Hann window to the
   whole capture and take an FFT zero-padded to 2**21 points (bins ~0.002 Hz).
   Magnitudes of x, y and z are added.
3. For each harmonic k in (1, 2, 3, 6): the largest bin within
   +/-(0.2 + 0.15 k) Hz of k * coarse f0, refined by a parabola through the log
   magnitude of that bin and its two neighbours. Its SNR is that peak over the
   median magnitude from k f0 - 3 Hz to k f0 + 3 Hz.
4. Harmonics with SNR >= 10 are kept. Fine f0 is the mean of f_k / k weighted
   by k**2 (a higher harmonic pins f0 more tightly). At least 2 harmonics must
   be kept, otherwise the result is NaN.
5. "spread" is the largest minus the smallest f_k / k among the kept
   harmonics: a check that they agree, reported but not used by the rule.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from af_signal.rotor import HARMONICS, rotor_speed
from af_signal.weight_test import SETTLE_S, spectrum

NFFT = 2**21
MIN_SNR = 10.0
FLOOR_HALF_WIDTH_HZ = 3.0


@dataclass
class FineSpeed:
    speed_hz: float
    coarse_hz: float
    harmonics_used: tuple[int, ...]
    spread_hz: float
    per_harmonic_hz: dict[int, float]


def _interp_peak(freqs: np.ndarray, mag: np.ndarray, centre: float, half: float) -> tuple[float, float]:
    sel = np.flatnonzero(np.abs(freqs - centre) <= half)
    i = int(sel[np.argmax(mag[sel])])
    a, b, c = np.log(mag[i - 1 : i + 2] + 1e-30)
    denom = a - 2 * b + c
    shift = 0.5 * (a - c) / denom if denom != 0 else 0.0
    step = float(freqs[1] - freqs[0])
    return float(freqs[i] + shift * step), float(mag[i])


def fine_speed(g: np.ndarray, rate_hz: float) -> FineSpeed:
    freqs_w, asd = spectrum(g, rate_hz)
    coarse, _ = rotor_speed(freqs_w, asd)
    data = np.asarray(g[int(round(SETTLE_S * rate_hz)) :], dtype=np.float64)
    data = data - data.mean(axis=0)
    win = np.hanning(data.shape[0])[:, None]
    mag = np.abs(np.fft.rfft(data * win, n=NFFT, axis=0)).sum(axis=1)
    freqs = np.fft.rfftfreq(NFFT, d=1.0 / rate_hz)
    per: dict[int, float] = {}
    for k in HARMONICS:
        centre = k * coarse
        f_k, peak = _interp_peak(freqs, mag, centre, 0.2 + 0.15 * k)
        band = np.abs(freqs - centre) <= FLOOR_HALF_WIDTH_HZ
        if peak / float(np.median(mag[band])) >= MIN_SNR:
            per[k] = f_k / k
    if len(per) < 2:
        return FineSpeed(float("nan"), coarse, tuple(per), float("nan"), per)
    ks = np.array(list(per))
    vals = np.array([per[k] for k in ks])
    w = ks.astype(float) ** 2
    return FineSpeed(float(np.sum(w * vals) / np.sum(w)), coarse, tuple(int(k) for k in ks),
                     float(vals.max() - vals.min()), per)


# ---------------------------------------------------------------------------
# The speed rule (docs/PHASE1_FLOOR_FAN_SPEED_PREREG.md), fixed before its data.
#
# Blocks in time order: N0 C1 N1 C2 N2 C3 N3 C4 N4 (N = no carton, C = carton),
# each after its own restart. A block's value is the median fine speed of its
# clean captures. Each carton block is compared with the mean of the two
# no-carton blocks around it (this cancels a steady drift):
#     d_i = 100 * (C_i - (N_{i-1} + N_i) / 2) / ((N_{i-1} + N_i) / 2)      [%]
# Each inner no-carton block is checked the same way against its no-carton
# neighbours, as a control for restart scatter and uneven drift:
#     e_j = 100 * (N_j - (N_{j-1} + N_{j+1}) / 2) / ((N_{j-1} + N_{j+1}) / 2)  [%]
# The lead from session 2 says the carton raises the speed, so the test is
# one-sided.

PASS_PCT = 0.4
MIN_CAPTURES = 2
CARTON_ROUNDS = 4


@dataclass
class SpeedVerdict:
    verdict: str  # DETECTED / NOT DETECTED / INCONCLUSIVE
    d_pct: list[float]
    e_pct: list[float]
    block_hz: list[float]
    reasons: list[str]


def block_speed(speeds: list[float]) -> float:
    vals = [s for s in speeds if np.isfinite(s)]
    return float(np.median(vals)) if len(vals) >= MIN_CAPTURES else float("nan")


def speed_verdict(no_carton: list[list[float]], carton: list[list[float]]) -> SpeedVerdict:
    """``no_carton``: N0..N4 fine speeds of clean captures; ``carton``: C1..C4."""
    if len(no_carton) != CARTON_ROUNDS + 1 or len(carton) != CARTON_ROUNDS:
        raise ValueError("need 5 no-carton and 4 carton blocks")
    n = [block_speed(b) for b in no_carton]
    c = [block_speed(b) for b in carton]
    order = [n[0]]
    for i in range(CARTON_ROUNDS):
        order += [c[i], n[i + 1]]
    reasons: list[str] = []
    if not all(np.isfinite(order)):
        reasons.append(f"a block has fewer than {MIN_CAPTURES} clean captures with a fine speed")
        return SpeedVerdict("INCONCLUSIVE", [], [], order, reasons)

    def pct(x: float, a: float, b: float) -> float:
        ref = (a + b) / 2
        return 100.0 * (x - ref) / ref

    d = [pct(c[i], n[i], n[i + 1]) for i in range(CARTON_ROUNDS)]
    e = [pct(n[j], n[j - 1], n[j + 1]) for j in range(1, CARTON_ROUNDS)]
    mean_d = float(np.mean(d))
    if mean_d < PASS_PCT:
        reasons.append(f"mean carton change {mean_d:+.2f} % is below +{PASS_PCT} %")
        return SpeedVerdict("NOT DETECTED", d, e, order, reasons)
    if not all(x > 0 for x in d):
        reasons.append("not every carton round raised the speed")
    largest_e = max(abs(x) for x in e)
    if mean_d <= largest_e:
        reasons.append(f"mean carton change {mean_d:+.2f} % is not above the largest "
                       f"no-carton control {largest_e:.2f} %")
    return SpeedVerdict("INCONCLUSIVE" if reasons else "DETECTED", d, e, order, reasons)

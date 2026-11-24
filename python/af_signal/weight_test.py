"""Decide a fan weight test (off / on / off ...) with rules fixed in code.

The decision rules were agreed in the project thread on 24 Nov 2026, before
the next session's data exists. They decide one bench test on a USB laptop
cooling pad. This is not a fault classifier and not predictive maintenance.

What is measured, per capture (about 30 s, three axes):

* **Fan speeds.** Each fan makes a family of lines at 2x, 4x, 6x and 9x its
  speed (9x = blade pass, 9 blades; family seen on 23 Nov 2026). For every
  candidate speed from 18 to 32 Hz the code takes the geometric mean of the
  x+y+z spectrum over its running median at those four lines (the "comb
  score"). Peaks of the score of at least 2.0 are fan speeds, the 3 strongest
  kept (the pad has 3 fans). The 1x line is left out of the score on purpose,
  so the line being tested does not steer its own search.
* **1x level per fan per axis**: the spectrum's peak within +/-0.3 Hz of every
  speed tracked in any group of the test. Every capture uses the same windows,
  so on and off captures are compared like for like. The decision uses the
  strongest on one axis chosen before the data (default y), so it does not
  matter which window belongs to which fan.
* **Rub band**: RMS of 800-1500 Hz (4th-order band-pass), the median of 1 s
  pieces after the first 0.5 s, so a single bump does not move it.

Decision rules (constants below):

* Data: every capture must have 0 missing sets, CRC errors, sequence gaps,
  restarts, overrun frames and dropped-word frames, else INCONCLUSIVE.
* Rub: DETECTED when every weighted group's rub band is more than 1.5x every
  unweighted group's.
* One weighted round (off / on / off), the "detect" rule:
  INCONCLUSIVE if a matched fan speed differs by more than 1 % between the two
  unweighted groups, or fewer than 2 fans could be matched, or a rub is
  detected. Otherwise PASS when the weighted group's 1x level (median of its
  captures) minus the first baseline's is larger than the largest difference
  between a baseline capture and a baseline-after capture; else NOT DETECTED.
* Two or more weighted rounds (off / on / off / on / off), the "confirm"
  rule: PASS when **every** weighted capture's 1x level is at least 3x the
  first baseline's median and **every** later unweighted capture is below that
  same threshold (the line is gone again); else NOT DETECTED.
  The note written before the data said "back within the baseline range".
  Read literally (no higher than the highest of 3 baseline captures) it fails
  about 2 times in 3 on noise alone, because each new capture has a 1-in-4
  chance of beating the highest of 3 (see tests/test_weight_test.py). So
  "back" is read here as "below the 3x line-present threshold".
  INCONCLUSIVE only for bad data or a rub. Speed drift between baselines is
  printed as a warning: the rule written before the data has no drift limit,
  and restarts move the fans 1-3 %.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import numpy as np
from scipy import ndimage, signal

from af_signal.adxl355_stream import DATA_ORIGIN_ADXL355, LSB_PER_G, load_capture_csv

ODR_FALLBACK_HZ = 4010.3  # measured on the board 23 Nov 2026; used if a file has no estimate
SETTLE_S = 0.5
NPERSEG = 32768  # 0.12 Hz bins at 4010 Hz; a 30 s capture gives 6 half-overlapped segments

# Fan-speed tracking (measurement method; set from the 23-24 Nov captures).
BLADES = 9
HARMONICS = (2, 4, 6, BLADES)
SPEED_RANGE_HZ = (18.0, 32.0)
SPEED_STEP_HZ = 0.01
COMB_FLOOR_WIDTH_HZ = 10.0
COMB_MIN_SCORE = 2.0
FAN_MIN_SEP_HZ = 0.6
MAX_FANS = 3
ONE_X_HALF_WIDTH_HZ = 0.3
ONE_X_FLOOR_HALF_WIDTH_HZ = 3.0
SPEED_MATCH_LIMIT = 0.05  # speeds further apart than 5 % are not the same fan
RUB_BAND_HZ = (800.0, 1500.0)

# Decision rules agreed before the data (project thread, 24 Nov 2026).
DRIFT_LIMIT = 0.01
RUB_LIMIT = 1.5
CONFIRM_FACTOR = 3.0

AXES = ("x", "y", "z")
QUALITY_KEYS = (
    "missing_sets",
    "crc_errors",
    "sequence_gaps",
    "restarts",
    "frames_flagged_overrun",
    "frames_flagged_dropped",
)
OFF_CONDITIONS = ("baseline", "baseline-after", "off", "screw-off", "weight-off", "sham-restart")
# Captures that belong to no weight round; give them with --off/--on if really wanted.
NOT_A_ROUND = ("steady-check", "fans-off", "rest", "warmup", "unplug-test")

PASS = "PASS"
NOT_DETECTED = "NOT DETECTED"
INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True)
class CaptureInput:
    """One capture's samples, ready to analyse."""

    name: str
    g: np.ndarray  # (N, 3) acceleration in g
    rate_hz: float
    state: str  # "off" (no weight) or "on" (weight on)
    data_origin: str
    quality_problems: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.state not in ("off", "on"):
            raise ValueError(f"{self.name}: state must be 'off' or 'on'")
        if self.g.ndim != 2 or self.g.shape[1] != 3:
            raise ValueError(f"{self.name}: g must have shape (N, 3)")


@dataclass
class CaptureResult:
    name: str
    state: str
    quality_problems: tuple[str, ...]
    freqs: np.ndarray
    asd: np.ndarray  # (F, 3) in g/sqrt(Hz)
    rub_g: tuple[float, float, float]  # x, y, z
    one_x: list[dict] = field(default_factory=list)  # one entry per tracked speed
    level: float = float("nan")  # strongest 1x on the decision axis, g/sqrt(Hz)
    level_freq_hz: float = float("nan")


@dataclass
class Group:
    state: str
    captures: list[CaptureResult]
    speeds_hz: list[float] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)

    @property
    def level(self) -> float:
        return float(np.median([c.level for c in self.captures]))

    @property
    def rub_z(self) -> float:
        return float(np.median([c.rub_g[2] for c in self.captures]))


@dataclass
class Drift:
    first: int  # group indexes
    second: int
    pairs: list[tuple[float, float, float]]  # (speed in first, speed in second, change)
    unmatched: list[float]

    @property
    def worst(self) -> float:
        return max((abs(p[2]) for p in self.pairs), default=float("nan"))


@dataclass
class Report:
    data_origin: str
    axis: str
    rule: str
    groups: list[Group]
    drifts: list[Drift]
    rub_ratio: float
    rub_verdict: str
    verdict: str
    reasons: list[str]
    notes: list[str]


# ---------------------------------------------------------------- loading


def quality_problems(header: dict[str, str]) -> tuple[str, ...]:
    """Non-zero data-path counters from a capture header (a missing counter counts too)."""
    problems = []
    for key in QUALITY_KEYS:
        value = header.get(key)
        if value is None:
            problems.append(f"{key} not recorded")
        elif value.strip() != "0":
            problems.append(f"{key}={value.strip()}")
    return tuple(problems)


def state_for_condition(condition: str) -> str:
    name = condition.strip().lower()
    if name in NOT_A_ROUND or not name:
        raise ValueError(
            f"condition '{condition}' is not part of a weight round; leave the file out or "
            "name the groups with --off/--on"
        )
    return "off" if name in OFF_CONDITIONS else "on"


def capture_from_file(path: Path, state: str | None = None) -> CaptureInput:
    """Load a capture saved by capture_adxl355.py. ``state`` overrides the header."""
    loaded = load_capture_csv(Path(path))
    try:
        rate = float(loaded.header.get("odr_estimate_hz", ""))
    except ValueError:
        rate = ODR_FALLBACK_HZ
    if state is None:
        state = state_for_condition(loaded.header.get("condition", ""))
    return CaptureInput(
        name=loaded.source_file,
        g=loaded.counts.astype(np.float64) / LSB_PER_G,
        rate_hz=rate,
        state=state,
        data_origin=loaded.data_origin,
        quality_problems=quality_problems(loaded.header),
    )


def group_runs(captures: Sequence[CaptureInput]) -> list[list[CaptureInput]]:
    """Split captures, in the order given, into runs of the same state."""
    runs: list[list[CaptureInput]] = []
    for capture in captures:
        if runs and runs[-1][0].state == capture.state:
            runs[-1].append(capture)
        else:
            runs.append([capture])
    return runs


# ---------------------------------------------------------------- measuring


def spectrum(g: np.ndarray, rate_hz: float) -> tuple[np.ndarray, np.ndarray]:
    """One-sided ASD per axis in g/sqrt(Hz) (Welch, Hann, linear detrend)."""
    start = int(round(SETTLE_S * rate_hz))
    data = np.asarray(g[start:], dtype=np.float64)
    if data.shape[0] < NPERSEG:
        raise ValueError(f"capture too short: {data.shape[0]} sets after settling")
    freqs, psd = signal.welch(
        data, fs=rate_hz, window="hann", nperseg=NPERSEG, detrend="linear", axis=0
    )
    return freqs, np.sqrt(psd)


def rub_level(g: np.ndarray, rate_hz: float) -> tuple[float, float, float]:
    """Median over 1 s pieces of the 800-1500 Hz RMS, per axis, in g."""
    sos = signal.butter(4, RUB_BAND_HZ, btype="bandpass", fs=rate_hz, output="sos")
    filtered = signal.sosfiltfilt(sos, np.asarray(g, dtype=np.float64), axis=0)
    filtered = filtered[int(round(SETTLE_S * rate_hz)) :]
    piece = int(round(rate_hz))
    count = filtered.shape[0] // piece
    if count < 3:
        raise ValueError("capture too short for the rub band (need 3 s)")
    pieces = filtered[: count * piece].reshape(count, piece, 3)
    rms = np.sqrt(np.mean(pieces**2, axis=1))
    return tuple(float(v) for v in np.median(rms, axis=0))


def comb_score(freqs: np.ndarray, asd: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Candidate speeds and their comb score (geometric mean of line / running median)."""
    summed = asd.sum(axis=1)
    step = float(freqs[1] - freqs[0])
    width = int(COMB_FLOOR_WIDTH_HZ / step) | 1
    floor = ndimage.median_filter(summed, size=width, mode="nearest")
    log_ratio = np.log(np.maximum(summed, 1e-30) / np.maximum(floor, 1e-30))
    log_ratio = ndimage.maximum_filter1d(log_ratio, size=3)  # allow +/-1 bin
    speeds = np.arange(SPEED_RANGE_HZ[0], SPEED_RANGE_HZ[1], SPEED_STEP_HZ)
    score = np.exp(np.mean([np.interp(k * speeds, freqs, log_ratio) for k in HARMONICS], axis=0))
    return speeds, score


def fan_speeds(freqs: np.ndarray, asd: np.ndarray) -> tuple[list[float], list[float]]:
    """Tracked fan speeds (Hz) and their comb scores, strongest MAX_FANS, sorted by speed."""
    speeds, score = comb_score(freqs, asd)
    peaks, _ = signal.find_peaks(
        score, height=COMB_MIN_SCORE, distance=int(FAN_MIN_SEP_HZ / SPEED_STEP_HZ)
    )
    peaks = sorted(sorted(peaks, key=lambda i: -score[i])[:MAX_FANS])
    return [float(speeds[i]) for i in peaks], [float(score[i]) for i in peaks]


def one_x(freqs: np.ndarray, asd: np.ndarray, speed_hz: float) -> dict:
    """The 1x peak per axis within +/-ONE_X_HALF_WIDTH_HZ of a speed, with its local floor."""
    window = (freqs >= speed_hz - ONE_X_HALF_WIDTH_HZ) & (freqs <= speed_hz + ONE_X_HALF_WIDTH_HZ)
    around = (freqs >= speed_hz - ONE_X_FLOOR_HALF_WIDTH_HZ) & (
        freqs <= speed_hz + ONE_X_FLOOR_HALF_WIDTH_HZ
    )
    result = {"speed_hz": speed_hz}
    for k, axis in enumerate(AXES):
        i = int(np.argmax(np.where(window, asd[:, k], -np.inf)))
        result[axis] = float(asd[i, k])
        result[f"{axis}_hz"] = float(freqs[i])
        result[f"{axis}_floor"] = float(np.median(asd[around, k]))
    return result


def match_speeds(first: Sequence[float], second: Sequence[float]) -> tuple[list, list]:
    """Pair speeds one-to-one, closest first, within SPEED_MATCH_LIMIT."""
    candidates = sorted(
        (abs(b - a) / a, a, b) for a in first for b in second if abs(b - a) / a <= SPEED_MATCH_LIMIT
    )
    used_a: set[float] = set()
    used_b: set[float] = set()
    pairs = []
    for _, a, b in candidates:
        if a in used_a or b in used_b:
            continue
        used_a.add(a)
        used_b.add(b)
        pairs.append((a, b, (b - a) / a))
    unmatched = [a for a in first if a not in used_a] + [b for b in second if b not in used_b]
    return sorted(pairs), sorted(unmatched)


def _mean_spectrum(results: list[CaptureResult]) -> tuple[np.ndarray, np.ndarray]:
    grid = results[0].freqs
    mean = np.mean(
        [
            np.column_stack([np.interp(grid, r.freqs, r.asd[:, k]) for k in range(3)])
            for r in results
        ],
        axis=0,
    )
    return grid, mean


# ---------------------------------------------------------------- deciding


def measure_group(run: Sequence[CaptureInput]) -> Group:
    results = []
    for c in run:
        freqs, asd = spectrum(c.g, c.rate_hz)
        r = CaptureResult(
            name=c.name,
            state=c.state,
            quality_problems=c.quality_problems,
            freqs=freqs,
            asd=asd,
            rub_g=rub_level(c.g, c.rate_hz),
        )
        results.append(r)
    group = Group(state=run[0].state, captures=results)
    group.speeds_hz, group.scores = fan_speeds(*_mean_spectrum(results))
    return group


def measure_one_x(group: Group, windows: Sequence[float], axis: str) -> None:
    for r in group.captures:
        r.one_x = [one_x(r.freqs, r.asd, s) for s in windows]
        if r.one_x:
            best = max(r.one_x, key=lambda m: m[axis])
            r.level = best[axis]
            r.level_freq_hz = best[f"{axis}_hz"]


def analyse(
    captures: Sequence[CaptureInput], axis: str = "y", rule: str = "auto"
) -> Report:
    """Measure every capture, then apply the fixed rules. Captures in time order."""
    if axis not in AXES:
        raise ValueError(f"axis must be one of {AXES}")
    if rule not in ("auto", "detect", "confirm"):
        raise ValueError("rule must be auto, detect or confirm")
    if not captures:
        raise ValueError("no captures")
    origins = {c.data_origin for c in captures}
    if len(origins) != 1:
        raise ValueError(f"captures mix data origins {sorted(origins)}; analyse them separately")
    runs = group_runs(captures)
    states = [run[0].state for run in runs]
    on_count = states.count("on")
    if on_count < 1 or states[0] != "off" or states[-1] != "off":
        raise ValueError(
            "need off / on / off (or off / on / off / on / off ...), starting and ending "
            f"without the weight; got {' / '.join(states)}"
        )
    if rule == "auto":
        rule = "detect" if on_count == 1 else "confirm"
    if rule == "detect" and on_count != 1:
        raise ValueError("the detect rule takes exactly one weighted group")

    groups = [measure_group(run) for run in runs]
    # Every capture is measured over the same windows: each speed tracked in any group of
    # this test. On and off captures are then compared like for like.
    windows = sorted({s for g in groups for s in g.speeds_hz})
    if not windows:
        raise ValueError("no fan speed could be tracked in any group; check the captures")
    for g in groups:
        measure_one_x(g, windows, axis)
    off_idx = [i for i, g in enumerate(groups) if g.state == "off"]
    on_idx = [i for i, g in enumerate(groups) if g.state == "on"]
    drifts = []
    for a, b in zip(off_idx, off_idx[1:]):
        pairs, unmatched = match_speeds(groups[a].speeds_hz, groups[b].speeds_hz)
        drifts.append(Drift(a, b, pairs, unmatched))

    reasons: list[str] = []
    notes: list[str] = []
    bad = [
        f"{r.name}: {', '.join(r.quality_problems)}"
        for g in groups
        for r in g.captures
        if r.quality_problems
    ]
    if bad:
        reasons.append("data path not clean: " + "; ".join(bad))

    off_rub = [groups[i].rub_z for i in off_idx]
    on_rub = [groups[i].rub_z for i in on_idx]
    rub_ratio = min(on_rub) / max(off_rub)
    rub_detected = rub_ratio > RUB_LIMIT
    rub_verdict = "DETECTED" if rub_detected else NOT_DETECTED
    if rub_detected:
        reasons.append(
            f"rub band {rub_ratio:.1f}x the unweighted level (limit {RUB_LIMIT}x), so the 1x "
            "rule does not apply"
        )

    first = groups[off_idx[0]]
    if rule == "detect":
        second = groups[off_idx[1]]
        drift = drifts[0]
        weighted = groups[on_idx[0]]
        spread = max(
            abs(a.level - b.level) for a in first.captures for b in second.captures
        )
        growth = weighted.level - first.level
        grown = growth > spread
        one_x_note = (
            f"1x ({axis}) medians: baseline {_ug(first.level)}, weighted {_ug(weighted.level)}, "
            f"baseline-after {_ug(second.level)} ug/rtHz; growth {_ug(growth)} vs largest "
            f"baseline/baseline-after capture difference {_ug(spread)} -> "
            f"{'grown' if grown else 'not grown'}"
        )
        notes.append(one_x_note)
        if len(drift.pairs) < 2:
            reasons.append(
                f"fan speeds not tracked: {len(drift.pairs)} fan(s) matched between the two "
                "baselines (need 2)"
            )
        elif drift.worst > DRIFT_LIMIT:
            reasons.append(
                f"a fan's speed moved {drift.worst:.1%} between the baselines "
                f"(limit {DRIFT_LIMIT:.0%})"
            )
        if reasons:
            verdict = INCONCLUSIVE
        else:
            verdict = PASS if grown else NOT_DETECTED
            reasons.append(one_x_note)
    else:
        threshold = CONFIRM_FACTOR * first.level
        weak = [r for i in on_idx for r in groups[i].captures if not r.level >= threshold]
        high = [r for i in off_idx[1:] for r in groups[i].captures if not r.level < threshold]
        notes.append(
            f"1x ({axis}): weighted captures need >= {_ug(threshold)} ug/rtHz "
            f"({CONFIRM_FACTOR:g}x the first baseline's median {_ug(first.level)}); later "
            f"unweighted captures need < {_ug(threshold)}"
        )
        for d in drifts:
            if d.pairs and d.worst > DRIFT_LIMIT:
                notes.append(
                    f"warning: a fan's speed moved {d.worst:.1%} between unweighted groups "
                    f"[{d.first + 1}] and [{d.second + 1}] (no limit in the confirm rule)"
                )
        if reasons:
            verdict = INCONCLUSIVE
        elif weak or high:
            verdict = NOT_DETECTED
            for r in weak:
                reasons.append(f"{r.name}: 1x {_ug(r.level)} < {_ug(threshold)} (weighted, too low)")
            for r in high:
                reasons.append(f"{r.name}: 1x {_ug(r.level)} >= {_ug(threshold)} (unweighted, not back)")
        else:
            verdict = PASS
            reasons.append(
                f"every weighted capture >= {CONFIRM_FACTOR:g}x the baseline and every later "
                f"unweighted capture below it"
            )

    return Report(
        data_origin=captures[0].data_origin,
        axis=axis,
        rule=rule,
        groups=groups,
        drifts=drifts,
        rub_ratio=rub_ratio,
        rub_verdict=rub_verdict,
        verdict=verdict,
        reasons=reasons,
        notes=notes,
    )


# ---------------------------------------------------------------- reporting


def _ug(value_g: float) -> str:
    return f"{value_g * 1e6:.0f}"


def format_report(report: Report) -> str:
    out = []
    if report.data_origin == DATA_ORIGIN_ADXL355:
        out.append(
            "data_origin: adxl355 (real measurement, uncalibrated +/-8 %). Bench test on a USB "
            "cooling pad, not an industrial machine."
        )
    else:
        out.append(
            f"data_origin: {report.data_origin.upper()} -- NOT A MEASUREMENT. Results describe "
            "generated signals only."
        )
    out.append(
        f"rule: {report.rule}   decision axis: {report.axis}   1x = strongest peak within "
        f"+/-{ONE_X_HALF_WIDTH_HZ} Hz of a tracked fan speed"
    )
    out.append("")
    for n, group in enumerate(report.groups, start=1):
        label = "weight ON " if group.state == "on" else "weight off"
        speeds = ", ".join(
            f"{s:.2f} Hz ({s * 60:.0f} rpm, blade pass {s * BLADES:.1f})"
            for s in group.speeds_hz
        ) or "none tracked"
        out.append(f"[{n}] {label}  fans: {speeds}")
        out.append(
            f"    rub z median {group.rub_z * 1e3:.2f} mg   1x {report.axis} median "
            f"{_ug(group.level)} ug/rtHz"
        )
        for r in group.captures:
            flag = "" if not r.quality_problems else "  DATA: " + ", ".join(r.quality_problems)
            per_axis = " ".join(
                f"{a}={_ug(max((m[a] for m in r.one_x), default=float('nan')))}" for a in AXES
            )
            out.append(
                f"    {r.name}: 1x {per_axis} ug/rtHz ({report.axis} peak at "
                f"{r.level_freq_hz:.2f} Hz); rub x/y/z "
                + "/".join(f"{v * 1e3:.2f}" for v in r.rub_g)
                + f" mg{flag}"
            )
    out.append("")
    for d in report.drifts:
        moved = ", ".join(f"{a:.2f}->{b:.2f} Hz ({c:+.1%})" for a, b, c in d.pairs) or "none matched"
        extra = f"; unmatched {', '.join(f'{u:.2f}' for u in d.unmatched)}" if d.unmatched else ""
        out.append(f"fan speed change [{d.first + 1}]->[{d.second + 1}]: {moved}{extra}")
    out.append(
        f"rub (800-1500 Hz, z): lowest weighted / highest unweighted = {report.rub_ratio:.2f}x "
        f"-> RUB {report.rub_verdict}"
    )
    out.extend(report.notes)
    out.append("")
    out.append(f"IMBALANCE (1x) VERDICT: {report.verdict}")
    out.extend(f"  - {reason}" for reason in report.reasons)
    return "\n".join(out)

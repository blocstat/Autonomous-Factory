"""Describe a single-rotor fan session: speed, line levels, warm-up and spreads.

Measures only; no PASS / FAIL. Definitions: python/af_signal/rotor.py and
docs/PHASE1_FLOOR_FAN_PLAN.md (fixed before the data).

Usage, from the repository root, captures in time order:

    python python/scripts/fan_characterise.py data/measured/adxl355/raw/2026MMDD-*_fan-box-top_*.csv

Files whose condition is "warmup" are also cut into 30 s pieces. Files whose
condition is "fan-off" or "tap-test" are listed but not measured for speed.
Consecutive files with the same condition form one block; spreads are given per
block, and for all files of a condition together (e.g. speed-3 r1-r6).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from af_signal.adxl355_stream import LSB_PER_G, load_capture_csv  # noqa: E402
from af_signal.rotor import MEASURE_NAMES, block_spreads, measure_capture, warmup  # noqa: E402
from af_signal.weight_test import ODR_FALLBACK_HZ, quality_problems, rub_level  # noqa: E402

NOT_RUNNING = ("fan-off", "fans-off", "tap-test")
WEAK_COMB = 2.0  # below this, no clear rotor line was found
LABELS = {"one_x_g": "1x", "blade_pass_g": "blade pass", "mains_line_g": "120 Hz",
          "broadband_g": "10-1000 Hz RMS"}


def _ug(v: float) -> str:
    return f"{v * 1e6:,.0f}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path)
    args = ap.parse_args(argv)

    print("data_origin: adxl355 (real measurement, uncalibrated +/-8 %). Household fan, not a machine.")
    print("Measures only, no verdict. Levels: peak ASD in ug/rtHz; broadband RMS in ug.\n")
    blocks: list[tuple[str, list]] = []
    by_condition: dict[str, list] = {}
    for path in args.files:
        loaded = load_capture_csv(path)
        header = loaded.header
        condition = header.get("condition", "?")
        try:
            rate = float(header.get("odr_estimate_hz", ""))
        except ValueError:
            rate = ODR_FALLBACK_HZ
        g = loaded.counts.astype(np.float64) / LSB_PER_G
        quality = quality_problems(header)
        flag = f"  BAD DATA: {', '.join(quality)}" if quality else ""
        if condition in NOT_RUNNING:
            _, kurt = rub_level(g, rate)
            print(f"{path.name}: {condition}, kurtosis z {kurt:.1f}{flag}")
            continue
        m = measure_capture(path.name, g, rate, quality)
        bump = "  BUMP (kurtosis > 5)" if m.bumped else ""
        weak = "  WEAK: no clear rotor line" if m.comb_score < WEAK_COMB else ""
        print(f"{path.name}: speed {m.speed_hz:.2f} Hz ({m.speed_hz * 60:.0f} rpm, "
              f"comb {m.comb_score:.1f}){weak}")
        for key in MEASURE_NAMES:
            vals = getattr(m, key)
            print(f"    {LABELS[key]:>15}: x {_ug(vals[0])}  y {_ug(vals[1])}  z {_ug(vals[2])}")
        print(f"    kurtosis z {m.kurtosis_z:.1f}{bump}{flag}")
        if condition == "warmup":
            pieces, settled = warmup(g, rate, loaded.index)
            print("    warm-up, 30 s pieces: start s / speed Hz / 1x y ug/rtHz")
            for p in pieces:
                print(f"      {p.start_s:5.0f}  {p.speed_hz:6.2f}  {_ug(p.one_x_g[1])}")
            print(f"    settled (within 0.5 % of final speed) from: "
                  f"{'never' if settled is None else f'{settled:.0f} s'}")
            continue
        if blocks and blocks[-1][0] == condition:
            blocks[-1][1].append(m)
        else:
            blocks.append((condition, [m]))
        by_condition.setdefault(condition, []).append(m)

    def show(title: str, measures: list) -> None:
        s = block_spreads(measures)
        speeds = [m.speed_hz for m in measures]
        print(f"{title}: n={s['n']}, speed {min(speeds):.2f}-{max(speeds):.2f} Hz "
              f"(range {s['speed_range_pct']:.2f} %)")
        for key in MEASURE_NAMES:
            vals = "  ".join(f"{a} {s[f'{key}_{a}']:.2f}x" for a in "xyz")
            print(f"    {LABELS[key]:>15} max/min: {vals}")

    print("\nSpreads per block (bumped and bad-data captures left out):")
    for condition, measures in blocks:
        show(f"[{condition}]", measures)
    print("\nSpreads per condition, all blocks together:")
    for condition, measures in by_condition.items():
        if len(measures) > len(next(b for c, b in blocks if c == condition)):
            show(f"[{condition}, all]", measures)
    return 0


if __name__ == "__main__":
    sys.exit(main())

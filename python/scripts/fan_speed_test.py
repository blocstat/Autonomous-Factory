"""Floor-fan speed test: does carton on the rear intake raise the speed?

Applies the pre-registered rule (python/af_signal/fine_speed.py,
docs/PHASE1_FLOOR_FAN_SPEED_PREREG.md) to the captures.

Usage, from the repository root (the shell glob sorts files in time order):

    python python/scripts/fan_speed_test.py data/measured/adxl355/raw/2026MMDD-*_fan-box-top_*

Files with condition fan-off, tap-test, warmup or stream-check are listed and
skipped. The others must form, in time order, 9 blocks alternating no-carton /
carton, starting and ending with no-carton. Captures with bad data or a bump
(800-1500 Hz z kurtosis above 5) are left out.
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
from af_signal.fine_speed import PASS_PCT, fine_speed, speed_verdict  # noqa: E402
from af_signal.weight_test import BUMP_KURTOSIS, ODR_FALLBACK_HZ, quality_problems, rub_level  # noqa: E402

SKIP = ("fan-off", "tap-test", "warmup", "stream-check")
ORDER = ("no-carton", "carton") * 4 + ("no-carton",)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path)
    args = ap.parse_args(argv)

    print("data_origin: adxl355 (real measurement). Household fan, not a machine.\n")
    blocks: list[tuple[str, list[float]]] = []
    for path in args.files:
        loaded = load_capture_csv(path)
        condition = loaded.header.get("condition", "?")
        if condition in SKIP:
            print(f"{path.name}: {condition}, skipped")
            continue
        try:
            rate = float(loaded.header.get("odr_estimate_hz", ""))
        except ValueError:
            rate = ODR_FALLBACK_HZ
        g = loaded.counts.astype(np.float64) / LSB_PER_G
        problems = list(quality_problems(loaded.header))
        _, kurt = rub_level(g, rate)
        if kurt > BUMP_KURTOSIS:
            problems.append(f"bump (kurtosis {kurt:.1f})")
        r = fine_speed(g, rate)
        flag = f"  LEFT OUT: {', '.join(problems)}" if problems else ""
        print(f"{path.name}: {condition}, fine speed {r.speed_hz:.4f} Hz (coarse {r.coarse_hz:.2f}, "
              f"harmonics {r.harmonics_used}, spread {r.spread_hz * 1000:.1f} mHz){flag}")
        speed = float("nan") if problems else r.speed_hz
        if blocks and blocks[-1][0] == condition:
            blocks[-1][1].append(speed)
        else:
            blocks.append((condition, [speed]))

    found = tuple(c for c, _ in blocks)
    if found != ORDER:
        print(f"\nBlocks found {found}, expected {ORDER}. No verdict.")
        return 2
    no = [b for c, b in blocks if c == "no-carton"]
    ca = [b for c, b in blocks if c == "carton"]
    v = speed_verdict(no, ca)
    print("\nBlock median fine speed, in order (Hz): " + "  ".join(f"{x:.4f}" for x in v.block_hz))
    if v.d_pct:
        print("Carton rounds d (%):        " + "  ".join(f"{x:+.3f}" for x in v.d_pct)
              + f"   mean {np.mean(v.d_pct):+.3f}")
        print("No-carton controls e (%):   " + "  ".join(f"{x:+.3f}" for x in v.e_pct))
    print(f"Pass mark: mean d >= +{PASS_PCT} %, every d > 0, mean d above every |e|.")
    print(f"\nVERDICT: {v.verdict}")
    for r in v.reasons:
        print(f"  - {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Floor-fan session 2: apply the pre-registered cardboard rule to the captures.

Rule and blocks: python/af_signal/fan_change.py and
docs/PHASE1_FLOOR_FAN_SESSION2_PREREG.md (fixed before the data).

Usage, from the repository root (files in time order; the shell glob sorts them):

    python python/scripts/fan_change_test.py data/measured/adxl355/raw/2026MMDD-*_fan-box-top_*

Files with condition fan-off, tap-test or warmup are listed and skipped. The
others must form, in time order, the blocks baseline, cardboard, baseline-after,
sham-restart, cardboard, baseline-after.
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
from af_signal.fan_change import PASS_RATIO, SECONDARY_RATIO, session2_verdict  # noqa: E402
from af_signal.rotor import measure_capture  # noqa: E402
from af_signal.weight_test import ODR_FALLBACK_HZ, quality_problems  # noqa: E402

SKIP = ("fan-off", "tap-test", "warmup")
ORDER = ("baseline", "cardboard", "baseline-after", "sham-restart", "cardboard", "baseline-after")
KEYS = ("baseline", "cardboard-1", "after-1", "sham", "cardboard-2", "after-2")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path)
    args = ap.parse_args(argv)

    print("data_origin: adxl355 (real measurement, uncalibrated +/-8 %). Household fan, not a machine.\n")
    blocks: list[tuple[str, list]] = []
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
        m = measure_capture(path.name, g, rate, quality_problems(loaded.header))
        flags = (" BUMP" if m.bumped else "") + (f" BAD DATA: {', '.join(m.quality_problems)}"
                                                if m.quality_problems else "")
        print(f"{path.name}: {condition}, speed {m.speed_hz:.2f} Hz, "
              f"RMS y {m.broadband_g[1] * 1e6:,.0f} ug, 1x y {m.one_x_g[1] * 1e6:,.0f} ug/rtHz{flags}")
        if blocks and blocks[-1][0] == condition:
            blocks[-1][1].append(m)
        else:
            blocks.append((condition, [m]))

    found = tuple(c for c, _ in blocks)
    if found != ORDER:
        print(f"\nBlocks found {found}, expected {ORDER}. No verdict.")
        return 2
    v = session2_verdict({k: b for k, (_, b) in zip(KEYS, blocks)})
    print(f"\nPrimary: 10-1000 Hz RMS on y, pass mark {PASS_RATIO}x either way, both rounds.")
    print(f"Secondary (reported only): 1x line on y, {SECONDARY_RATIO}x.")
    for c in v.comparisons:
        print(f"  {c.name}: n {c.n_reference} vs {c.n_test}/{c.n_test_all} speed-matched, "
              f"speed {c.speed_change_pct:+.2f} %, RMS y {c.primary_ratio:.2f}x, 1x y {c.secondary_ratio:.2f}x")
    print(f"\nVERDICT: {v.verdict}")
    for r in v.reasons:
        print(f"  - {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

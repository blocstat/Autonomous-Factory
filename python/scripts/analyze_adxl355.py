"""Check ADXL355 captures taken at rest: data path, rate, gravity, noise floor.

Every result is labelled data_origin=adxl355: a real measurement from the
product sensor, uncalibrated (+/-8 % in g). Nothing here describes a machine.

Usage, from the repository root:

    python python/scripts/analyze_adxl355.py data/measured/adxl355/raw/*_adxl355_*.csv

Prints PASS/FAIL/CHECK per capture and writes data/measured/adxl355/out/
summary.csv plus one noise-density PNG per capture.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from af_signal.adxl355_noise import (  # noqa: E402
    checks,
    format_report,
    overall,
    plot_noise,
    summarize,
)
from af_signal.adxl355_stream import load_capture_csv  # noqa: E402

DEFAULT_OUT = ROOT.parent / "data" / "measured" / "adxl355" / "out"


def analyse(path: Path, out_dir: Path) -> dict[str, object]:
    capture = load_capture_csv(path)
    row = summarize(capture)
    results = checks(capture, row)
    print(format_report(row, results))
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_noise(capture, out_dir / f"{path.name.split('.')[0]}_noise.png")
    row["overall"] = overall(results)
    for check in results:
        row[f"check_{check.name.replace(' ', '_')}"] = check.result
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    rows = []
    for path in args.files:
        try:
            rows.append(analyse(path, args.out_dir))
        except ValueError as error:
            print(f"SKIP {path.name}: {error}")
        print()
    if not rows:
        return 1
    summary = args.out_dir / "summary.csv"
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {summary} and {len(rows)} noise plot(s).")
    return 0 if all(row["overall"] != "FAIL" for row in rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())

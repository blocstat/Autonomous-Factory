"""Decide a fan weight test from ADXL355 captures: PASS / NOT DETECTED / INCONCLUSIVE.

The rules are fixed in af_signal/weight_test.py (agreed 24 Nov 2026, before the
data). Bench test on a USB cooling pad; not fault detection on machines.

Usage, from the repository root. Give the captures in time order.

Grouped by each file's "condition" header (baseline / baseline-after = no
weight, anything else = weight on); consecutive files with the same state form
one group:

    python python/scripts/weight_test.py data/measured/adxl355/raw/20261125-09*.csv

Or name the groups yourself, in order (needed when a baseline is reused):

    python python/scripts/weight_test.py \\
        --off  data/measured/adxl355/raw/20261124-1109_*.csv data/measured/adxl355/raw/20261124-1110_*.csv \\
        --on   data/measured/adxl355/raw/20261124-114[34]_*.csv \\
        --off  data/measured/adxl355/raw/20261124-115[23]_*.csv

One weighted group uses the "detect" rule; two or more use the "confirm" rule.
Exit code: 0 PASS, 1 NOT DETECTED, 2 INCONCLUSIVE, 3 bad input.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from af_signal.weight_test import (  # noqa: E402
    INCONCLUSIVE,
    PASS,
    analyse,
    capture_from_file,
    format_report,
)

EXIT_CODES = {PASS: 0, INCONCLUSIVE: 2}


class _Group(argparse.Action):
    """--off / --on keep their order on the command line."""

    def __call__(self, parser, namespace, values, option_string=None):
        groups = getattr(namespace, "groups", None) or []
        groups.append((self.const, list(values)))
        namespace.groups = groups


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="*", type=Path, help="captures, grouped by header")
    parser.add_argument("--off", nargs="+", type=Path, action=_Group, const="off", dest="groups",
                        help="a group of captures without the weight")
    parser.add_argument("--on", nargs="+", type=Path, action=_Group, const="on", dest="groups",
                        help="a group of captures with the weight on")
    parser.add_argument("--axis", choices=("x", "y", "z"), default="y",
                        help="axis the decision uses (fix it before the data; default y)")
    parser.add_argument("--rule", choices=("auto", "detect", "confirm"), default="auto",
                        help="auto: detect for one weighted group, confirm for two or more")
    args = parser.parse_args(argv)

    if args.files and args.groups:
        parser.error("give either plain files or --off/--on groups, not both")
    try:
        if args.groups:
            captures = [capture_from_file(p, state) for state, paths in args.groups for p in paths]
        elif args.files:
            captures = [capture_from_file(p) for p in sorted(args.files, key=lambda p: p.name)]
        else:
            parser.error("no captures given")
        report = analyse(captures, axis=args.axis, rule=args.rule)
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 3
    print(format_report(report))
    return EXIT_CODES.get(report.verdict, 1)


if __name__ == "__main__":
    raise SystemExit(main())

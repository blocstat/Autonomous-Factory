"""Print a host-tool report. Does not install packages or build firmware."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from af_signal.host_report import collect_live_report, render_report


def main() -> None:
    report = collect_live_report()
    sys.stdout.write(render_report(report))


if __name__ == "__main__":
    main()

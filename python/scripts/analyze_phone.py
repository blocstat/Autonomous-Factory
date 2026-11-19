"""Summarise phone accelerometer captures (phyphox CSV exports).

Every result is labelled data_origin=phone: a real measurement from the
phone's own accelerometer, NOT the product sensor and NOT synthetic.

Usage, from the repository root:

    python python/scripts/analyze_phone.py data/measured/phone/raw/*.csv
    python python/scripts/analyze_phone.py data/measured/phone/raw/*.csv --shaft-hz 20

Writes data/measured/phone/out/summary.csv and one spectrum PNG per capture.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from af_signal.features import band_rms, kurtosis, time_domain_features  # noqa: E402
from af_signal.phone import (  # noqa: E402
    DATA_ORIGIN_PHONE,
    load_phyphox_csv,
    resample_uniform,
    sample_rate_stats,
)

# YYYYMMDD-HHMM_phone_<condition>_<speed>_<mount>_r<N>.csv
NAME_PATTERN = re.compile(
    r"^(?P<stamp>\d{8}-\d{4})_phone_(?P<condition>[a-z0-9-]+)_(?P<speed>[a-z0-9-]+)"
    r"_(?P<mount>[a-z0-9-]+)_r(?P<repeat>\d+)\.csv$"
)
MIN_FREQ_HZ = 3.0  # ignore handling drift and very slow motion


def parse_name(name: str) -> dict[str, str]:
    match = NAME_PATTERN.match(name)
    if not match:
        return {"stamp": "", "condition": "UNLABELLED", "speed": "", "mount": "", "repeat": ""}
    return match.groupdict()


def peak_above(values: np.ndarray, rate_hz: float, min_hz: float) -> float:
    centered = values - np.mean(values)
    magnitude = np.abs(np.fft.rfft(centered * np.hanning(centered.size)))
    freqs = np.fft.rfftfreq(centered.size, d=1.0 / rate_hz)
    magnitude[freqs < min_hz] = 0.0
    return float(freqs[int(np.argmax(magnitude))])


def analyse(path: Path, shaft_hz: float | None, out_dir: Path) -> dict[str, object]:
    capture = load_phyphox_csv(path)
    stats = sample_rate_stats(capture.time_s)
    rate_hz = float(np.floor(stats["median_rate_hz"]))
    row: dict[str, object] = {
        "data_origin": DATA_ORIGIN_PHONE,
        "file": capture.source_file,
        **parse_name(capture.source_file),
        "median_rate_hz": round(stats["median_rate_hz"], 2),
        "jitter_pct": round(stats["jitter_pct"], 2),
        "max_gap_s": round(stats["max_gap_s"], 4),
        "duration_s": round(stats["duration_s"], 2),
        "resampled_hz": rate_hz,
    }
    spectra = {}
    for axis, values in capture.axes.items():
        _, uniform = resample_uniform(capture.time_s, values, rate_hz)
        centered = uniform - np.mean(uniform)
        feats = time_domain_features(centered)
        row[f"{axis}_rms"] = round(feats["rms"], 5)
        row[f"{axis}_crest"] = round(feats["crest_factor"], 3)
        row[f"{axis}_kurtosis"] = round(kurtosis(centered), 3)
        row[f"{axis}_peak_hz"] = round(peak_above(centered, rate_hz, MIN_FREQ_HZ), 2)
        if shaft_hz:
            row[f"{axis}_1x_rms"] = round(
                band_rms(centered, rate_hz, shaft_hz - 1.0, shaft_hz + 1.0), 5
            )
        spectra[axis] = (rate_hz, centered)
    _plot(out_dir / f"{path.stem}.png", capture.source_file, spectra, shaft_hz)
    return row


def _plot(path: Path, title: str, spectra: dict, shaft_hz: float | None) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(9, 4.5))
    for name, (rate_hz, values) in spectra.items():
        magnitude = np.abs(np.fft.rfft(values * np.hanning(values.size))) / values.size
        freqs = np.fft.rfftfreq(values.size, d=1.0 / rate_hz)
        axis.semilogy(freqs[1:], magnitude[1:], label=f"{name} axis", linewidth=0.8)
    if shaft_hz:
        axis.axvline(shaft_hz, color="gray", linestyle="--", label=f"expected 1x {shaft_hz} Hz")
    axis.set_xlabel("frequency (Hz)")
    axis.set_ylabel("magnitude (m/s², Hann-windowed)")
    axis.set_title(f"PHONE accelerometer (data_origin=phone), not the product sensor\n{title}")
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=110)
    plt.close(figure)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", type=Path, help="phyphox CSV exports")
    parser.add_argument("--shaft-hz", type=float, default=None,
                        help="fan shaft speed in Hz (RPM / 60), to report the 1x level")
    parser.add_argument("--out", type=Path,
                        default=ROOT.parent / "data" / "measured" / "phone" / "out")
    args = parser.parse_args(argv)

    if "synthetic" in args.out.resolve().parts:
        parser.error("refusing to write phone results under a synthetic data folder")
    args.out.mkdir(parents=True, exist_ok=True)

    rows = []
    for path in args.files:
        row = analyse(path, args.shaft_hz, args.out)
        if row["condition"] == "UNLABELLED":
            print(f"WARNING: {path.name} does not follow the naming convention", file=sys.stderr)
        rows.append(row)

    columns = list(dict.fromkeys(key for row in rows for key in row))
    summary = args.out / "summary.csv"
    with summary.open("w", encoding="utf-8") as handle:
        handle.write("# data_origin: phone\n")
        handle.write("# phone accelerometer, not the product sensor; not synthetic\n")
        handle.write(",".join(columns) + "\n")
        for row in rows:
            handle.write(",".join(str(row.get(c, "")) for c in columns) + "\n")

    shown = ["file", "condition", "speed", "median_rate_hz", "jitter_pct", "z_rms", "z_peak_hz"]
    if args.shaft_hz:
        shown.append("z_1x_rms")
    print("data_origin=phone")
    print("  ".join(shown))
    for row in rows:
        print("  ".join(str(row.get(c, "")) for c in shown))
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

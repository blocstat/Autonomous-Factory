"""Load and summarise phone accelerometer captures exported from phyphox.

Data loaded here is a real measurement from a phone's built-in accelerometer,
labelled ``data_origin: phone``. It is NOT data from the product sensor
(ADXL355) and must never be presented as such. Phone sensors are sampled at a
rate the phone chooses, with irregular timestamps, and are filtered by the
phone; treat results as a rehearsal of the analysis, not as product evidence.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

DATA_ORIGIN_PHONE = "phone"

_AXIS_PATTERN = re.compile(r"(?:^|\s)([xyz])(?:\s|\(|$)", re.IGNORECASE)


@dataclass(frozen=True)
class PhoneCapture:
    """One phyphox export: raw timestamps and per-axis acceleration in m/s^2."""

    time_s: np.ndarray
    axes: dict[str, np.ndarray]
    source_file: str
    column_names: tuple[str, ...]
    data_origin: str = DATA_ORIGIN_PHONE
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.data_origin != DATA_ORIGIN_PHONE:
            raise ValueError("PhoneCapture.data_origin must stay 'phone'")
        if self.time_s.ndim != 1 or self.time_s.size < 2:
            raise ValueError("need at least 2 timestamps")
        for name, values in self.axes.items():
            if values.shape != self.time_s.shape:
                raise ValueError(f"axis {name} length does not match timestamps")


def load_phyphox_csv(path: Path) -> PhoneCapture:
    """Read a phyphox CSV export (comma, tab or semicolon; decimal point or comma).

    Expects a time column whose header starts with "Time" and acceleration
    columns whose headers name the axis, e.g. "Acceleration x (m/s^2)".
    Rows with missing values are dropped. Timestamps must increase.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig")
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        raise ValueError(f"{path.name}: expected a header and at least 2 rows")

    delimiter = _sniff_delimiter(lines[0])
    decimal_comma = delimiter != "," and _uses_decimal_comma(lines[1], delimiter)
    rows = list(csv.reader(lines, delimiter=delimiter))
    header = [cell.strip().strip('"') for cell in rows[0]]

    time_index = next(
        (i for i, name in enumerate(header) if name.lower().startswith("time")), None
    )
    if time_index is None:
        raise ValueError(f"{path.name}: no column starting with 'Time' in {header}")
    axis_index: dict[str, int] = {}
    for i, name in enumerate(header):
        if i == time_index or "absolute" in name.lower():
            continue
        match = _AXIS_PATTERN.search(name)
        if match and match.group(1).lower() not in axis_index:
            axis_index[match.group(1).lower()] = i
    if not axis_index:
        raise ValueError(f"{path.name}: no x/y/z acceleration columns in {header}")

    wanted = [time_index, *axis_index.values()]
    parsed: list[list[float]] = []
    for row in rows[1:]:
        try:
            parsed.append([_to_float(row[i], decimal_comma) for i in wanted])
        except (IndexError, ValueError):
            continue  # incomplete or non-numeric row
    data = np.asarray(parsed, dtype=np.float64)
    if data.shape[0] < 2:
        raise ValueError(f"{path.name}: fewer than 2 numeric rows")
    time_s = data[:, 0]
    if np.any(np.diff(time_s) <= 0):
        raise ValueError(f"{path.name}: timestamps are not strictly increasing")

    axes = {axis: data[:, col] for col, axis in enumerate(axis_index, start=1)}
    return PhoneCapture(
        time_s=time_s,
        axes=axes,
        source_file=path.name,
        column_names=tuple(header),
    )


def sample_rate_stats(time_s: np.ndarray) -> dict[str, float]:
    """Describe how regular the phone's sampling was.

    Phones do not sample at a fixed rate. Report this with every result:
    a large jitter or long gaps make spectra less trustworthy.
    """
    dt = np.diff(np.asarray(time_s, dtype=np.float64))
    if dt.size < 1 or np.any(dt <= 0):
        raise ValueError("timestamps must be strictly increasing")
    median_dt = float(np.median(dt))
    return {
        "samples": float(dt.size + 1),
        "duration_s": float(time_s[-1] - time_s[0]),
        "mean_rate_hz": float(dt.size / (time_s[-1] - time_s[0])),
        "median_rate_hz": 1.0 / median_dt,
        "jitter_pct": float(100.0 * np.std(dt) / np.mean(dt)),
        "max_gap_s": float(np.max(dt)),
        "gaps_over_2x_median": float(np.count_nonzero(dt > 2.0 * median_dt)),
    }


def resample_uniform(
    time_s: np.ndarray, values: np.ndarray, rate_hz: float
) -> tuple[np.ndarray, np.ndarray]:
    """Linearly interpolate irregular samples onto a uniform grid at `rate_hz`.

    Use a rate at or below the phone's median rate. Interpolation cannot add
    information above the phone's own Nyquist frequency.
    """
    if rate_hz <= 0:
        raise ValueError("rate_hz must be positive")
    time_s = np.asarray(time_s, dtype=np.float64)
    count = int(np.floor((time_s[-1] - time_s[0]) * rate_hz)) + 1
    if count < 2:
        raise ValueError("capture is too short for this rate")
    grid = time_s[0] + np.arange(count, dtype=np.float64) / rate_hz
    return grid, np.interp(grid, time_s, np.asarray(values, dtype=np.float64))


def _sniff_delimiter(header_line: str) -> str:
    counts = {d: header_line.count(d) for d in (",", "\t", ";")}
    best = max(counts, key=counts.get)
    if counts[best] == 0:
        raise ValueError("could not detect the CSV delimiter")
    return best


def _uses_decimal_comma(data_line: str, delimiter: str) -> bool:
    return any("," in cell for cell in data_line.split(delimiter))


def _to_float(cell: str, decimal_comma: bool) -> float:
    cell = cell.strip().strip('"')
    if decimal_comma:
        cell = cell.replace(",", ".")
    value = float(cell)
    if not np.isfinite(value):
        raise ValueError("non-finite value")
    return value

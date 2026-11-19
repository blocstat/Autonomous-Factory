"""Standard-library statistics for one synthetic sample window.

This module does not import NumPy or SciPy. ``features.py`` remains the
NumPy/SciPy implementation. Nothing here reads a serial port, a GPIO line,
or ``data/measured``. The numbers describe the sequence you pass in. They
are not a fault classification and not a predictive-maintenance result.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

SYNTHETIC_ORIGIN = "synthetic"


@dataclass(frozen=True)
class SyntheticWindow:
    """A computed sine window. ``samples`` are dimensionless synthetic units."""

    samples: tuple[float, ...]
    sample_rate_hz: float
    tone_hz: float
    amplitude: float
    description: str
    data_origin: str = SYNTHETIC_ORIGIN

    def __post_init__(self) -> None:
        if self.data_origin != SYNTHETIC_ORIGIN:
            raise ValueError("SyntheticWindow.data_origin must stay 'synthetic'")
        if len(self.samples) < 2:
            raise ValueError("samples must contain at least 2 values")


@dataclass(frozen=True)
class WindowStats:
    """Descriptive stats for one window. ``duration_s`` is ``count / sample_rate_hz``."""

    data_origin: str
    sample_count: int
    sample_rate_hz: float
    duration_s: float
    mean: float
    rms: float
    peak_abs: float
    crest_factor: float


def synthetic_sine(
    *,
    sample_rate_hz: float,
    duration_s: float,
    tone_hz: float,
    amplitude: float = 1.0,
    description: str = "synthetic single tone",
) -> SyntheticWindow:
    """Return ``amplitude * sin(2π f t)`` with no noise.

    Amplitude is a dimensionless synthetic unit, not calibrated acceleration,
    velocity, or voltage. The sample count is ``round(sample_rate_hz * duration_s)``.
    """
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive")
    if duration_s <= 0:
        raise ValueError("duration_s must be positive")
    if tone_hz <= 0 or tone_hz >= sample_rate_hz / 2:
        raise ValueError("tone_hz must be positive and below the Nyquist rate")
    if amplitude < 0:
        raise ValueError("amplitude must be non-negative")

    sample_count = int(round(sample_rate_hz * duration_s))
    if sample_count < 2:
        raise ValueError("duration and sample rate must yield at least 2 samples")

    samples = tuple(
        amplitude * math.sin(2.0 * math.pi * tone_hz * (index / sample_rate_hz))
        for index in range(sample_count)
    )
    return SyntheticWindow(
        samples=samples,
        sample_rate_hz=float(sample_rate_hz),
        tone_hz=float(tone_hz),
        amplitude=float(amplitude),
        description=description,
    )


def window_stats(
    samples: Sequence[float],
    sample_rate_hz: float,
    data_origin: str,
) -> WindowStats:
    """Return mean, RMS, absolute peak, and crest factor.

    ``data_origin`` must be the exact string ``synthetic``. Any other label,
    including ``measured``, is rejected so this function cannot be pointed at
    an unlabeled or recorded series by accident.
    """
    if data_origin != SYNTHETIC_ORIGIN:
        raise ValueError("data_origin must be 'synthetic'")
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive")

    values = _as_finite_floats(samples)
    mean = sum(values) / len(values)
    mean_square = sum(value * value for value in values) / len(values)
    rms = math.sqrt(mean_square)
    if rms == 0.0:
        raise ValueError("RMS is zero; crest factor is undefined")
    peak_abs = max(abs(value) for value in values)
    return WindowStats(
        data_origin=SYNTHETIC_ORIGIN,
        sample_count=len(values),
        sample_rate_hz=float(sample_rate_hz),
        duration_s=len(values) / float(sample_rate_hz),
        mean=mean,
        rms=rms,
        peak_abs=peak_abs,
        crest_factor=peak_abs / rms,
    )


def _as_finite_floats(samples: Sequence[float]) -> list[float]:
    if isinstance(samples, (str, bytes)):
        raise ValueError("samples must be a sequence of real numbers")
    values: list[float] = []
    for sample in samples:
        if isinstance(sample, bool) or not isinstance(sample, (int, float)):
            raise ValueError("samples must be real numbers")
        value = float(sample)
        if not math.isfinite(value):
            raise ValueError("samples must be finite")
        values.append(value)
    if len(values) < 2:
        raise ValueError("samples must contain at least 2 values")
    return values

"""Time-domain and single-peak spectral features.

These functions describe an array. They do not classify machine faults and
they are not a predictive-maintenance model.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import detrend
from scipy.signal.windows import hann


def time_domain_features(samples: np.ndarray) -> dict[str, float]:
    """Return mean, RMS, absolute peak, and crest factor of a 1-D array."""
    values = _as_finite_vector(samples)
    mean = float(np.mean(values))
    rms = float(np.sqrt(np.mean(values * values)))
    if rms == 0.0:
        raise ValueError("RMS is zero; crest factor is undefined")
    peak_abs = float(np.max(np.abs(values)))
    return {
        "mean": mean,
        "rms": rms,
        "peak_abs": peak_abs,
        "crest_factor": peak_abs / rms,
    }


def dominant_frequency_hz(samples: np.ndarray, sample_rate_hz: float) -> float:
    """Return the frequency bin with the largest Hann-windowed rFFT magnitude.

    DC is ignored. The result is the bin center, so it is quantized to
    `sample_rate_hz / N`.
    """
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive")
    values = detrend(_as_finite_vector(samples), type="constant")
    window = hann(values.size, sym=False)
    spectrum = np.fft.rfft(values * window)
    magnitude = np.abs(spectrum)
    magnitude[0] = 0.0
    if float(np.max(magnitude)) == 0.0:
        raise ValueError("spectrum has no energy above DC")
    bin_index = int(np.argmax(magnitude))
    return float(bin_index * sample_rate_hz / values.size)


def _as_finite_vector(samples: np.ndarray) -> np.ndarray:
    values = np.asarray(samples, dtype=np.float64)
    if values.ndim != 1 or values.size < 2:
        raise ValueError("samples must be a 1-D array with at least 2 values")
    if not np.all(np.isfinite(values)):
        raise ValueError("samples must be finite")
    return values

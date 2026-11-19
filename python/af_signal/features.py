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
        "peak_to_peak": float(np.max(values) - np.min(values)),
        "crest_factor": peak_abs / rms,
    }


def kurtosis(samples: np.ndarray) -> float:
    """Return Pearson kurtosis (Gaussian noise is about 3, a pure sine is 1.5).

    The mean is removed first. Impacts and spikes raise kurtosis.
    """
    values = _as_finite_vector(samples)
    centered = values - np.mean(values)
    variance = float(np.mean(centered**2))
    if variance == 0.0:
        raise ValueError("variance is zero; kurtosis is undefined")
    return float(np.mean(centered**4) / variance**2)


def band_rms(
    samples: np.ndarray, sample_rate_hz: float, low_hz: float, high_hz: float
) -> float:
    """Return the RMS of the signal content with `low_hz <= f < high_hz`.

    Uses a rectangular-window rFFT and Parseval's theorem, so a tone that sits
    exactly on a bin is measured exactly. Off-bin tones leak into neighbouring
    bins; use bands several bins wide. DC is always excluded. Summing every
    band from 0 Hz to above Nyquist gives the RMS of the mean-removed signal.
    """
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive")
    if not 0 <= low_hz < high_hz:
        raise ValueError("need 0 <= low_hz < high_hz")
    values = _as_finite_vector(samples)
    n = values.size
    spectrum = np.fft.rfft(values)
    freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate_hz)
    power = (np.abs(spectrum) ** 2) / n**2
    # One-sided spectrum: double every bin except DC and (for even n) Nyquist.
    power[1:] *= 2.0
    if n % 2 == 0:
        power[-1] /= 2.0
    power[0] = 0.0
    in_band = (freqs >= low_hz) & (freqs < high_hz)
    return float(np.sqrt(np.sum(power[in_band])))


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

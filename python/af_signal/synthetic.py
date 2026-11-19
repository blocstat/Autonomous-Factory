"""Generators for synthetic waveforms.

Every array returned here is computed, not measured. Callers must keep the
`data_origin` field attached when they save or plot the samples.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from af_signal import DATA_ORIGIN_SYNTHETIC


@dataclass(frozen=True)
class SyntheticWaveform:
    """One synthetic channel and the metadata required to reproduce it."""

    samples: np.ndarray
    sample_rate_hz: float
    tone_hz: float
    amplitude: float
    noise_std: float
    seed: int
    description: str
    data_origin: str = DATA_ORIGIN_SYNTHETIC

    def __post_init__(self) -> None:
        if self.data_origin != DATA_ORIGIN_SYNTHETIC:
            raise ValueError("SyntheticWaveform.data_origin must stay 'synthetic'")
        if self.samples.ndim != 1 or self.samples.dtype != np.float64:
            raise ValueError("samples must be a 1-D float64 array")


def generate_tone(
    *,
    sample_rate_hz: float = 1000.0,
    duration_s: float = 1.0,
    tone_hz: float = 50.0,
    amplitude: float = 1.0,
    noise_std: float = 0.0,
    seed: int = 0,
    description: str = "synthetic single tone",
) -> SyntheticWaveform:
    """Return `amplitude * sin(2π f t)` plus optional Gaussian noise.

    `amplitude` and `noise_std` are dimensionless synthetic units. They are not
    calibrated acceleration, velocity, or voltage.
    """
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive")
    if duration_s <= 0:
        raise ValueError("duration_s must be positive")
    if tone_hz <= 0 or tone_hz >= sample_rate_hz / 2:
        raise ValueError("tone_hz must be positive and below the Nyquist rate")
    if amplitude < 0 or noise_std < 0:
        raise ValueError("amplitude and noise_std must be non-negative")

    sample_count = int(round(sample_rate_hz * duration_s))
    if sample_count < 2:
        raise ValueError("duration and sample rate must yield at least 2 samples")

    time_s = np.arange(sample_count, dtype=np.float64) / sample_rate_hz
    samples = amplitude * np.sin(2.0 * np.pi * tone_hz * time_s)
    if noise_std > 0:
        rng = np.random.default_rng(seed)
        samples = samples + rng.normal(0.0, noise_std, size=sample_count)

    return SyntheticWaveform(
        samples=np.asarray(samples, dtype=np.float64),
        sample_rate_hz=float(sample_rate_hz),
        tone_hz=float(tone_hz),
        amplitude=float(amplitude),
        noise_std=float(noise_std),
        seed=int(seed),
        description=description,
    )

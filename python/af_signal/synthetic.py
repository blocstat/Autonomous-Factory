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
    # Extra sinusoids as (frequency_hz, amplitude) pairs. Empty for a single tone.
    components: tuple[tuple[float, float], ...] = ()
    impulse_rate_hz: float = 0.0
    impulse_amplitude: float = 0.0

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


def generate_fan_vibration(
    *,
    sample_rate_hz: float = 4000.0,
    duration_s: float = 1.0,
    shaft_hz: float = 25.0,
    blade_count: int = 7,
    shaft_amplitude: float = 0.2,
    imbalance_amplitude: float = 0.0,
    blade_pass_amplitude: float = 0.5,
    harmonic_amplitudes: tuple[float, ...] = (),
    impulse_rate_hz: float = 0.0,
    impulse_amplitude: float = 0.0,
    noise_std: float = 0.0,
    seed: int = 0,
    description: str = "synthetic fan-like vibration",
) -> SyntheticWaveform:
    """Return a computed waveform shaped like a small fan's vibration.

    This is a test signal with known contents, not a physical model of a fan:

    - 1x shaft tone at `shaft_hz` with amplitude
      `shaft_amplitude + imbalance_amplitude`. Imbalance is modelled only as
      extra 1x amplitude, in phase.
    - Shaft harmonics: `harmonic_amplitudes[0]` at 2x, `[1]` at 3x, and so on.
    - Blade-pass tone at `blade_count * shaft_hz`.
    - Optional single-sample impulses, evenly spaced at `impulse_rate_hz`.
    - Optional Gaussian noise.

    All amplitudes are dimensionless synthetic units, not calibrated g.
    """
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive")
    if duration_s <= 0:
        raise ValueError("duration_s must be positive")
    if shaft_hz <= 0 or blade_count < 1:
        raise ValueError("shaft_hz must be positive and blade_count at least 1")
    amplitudes = (shaft_amplitude, imbalance_amplitude, blade_pass_amplitude,
                  impulse_amplitude, noise_std, impulse_rate_hz, *harmonic_amplitudes)
    if any(a < 0 for a in amplitudes):
        raise ValueError("amplitudes, rates and noise_std must be non-negative")

    nyquist_hz = sample_rate_hz / 2
    one_x = shaft_amplitude + imbalance_amplitude
    components: list[tuple[float, float]] = [(shaft_hz, one_x)]
    for order, amplitude in enumerate(harmonic_amplitudes, start=2):
        components.append((order * shaft_hz, amplitude))
    components.append((blade_count * shaft_hz, blade_pass_amplitude))
    for frequency_hz, amplitude in components:
        if amplitude > 0 and frequency_hz >= nyquist_hz:
            raise ValueError(
                f"component at {frequency_hz} Hz is at or above the Nyquist rate"
            )

    sample_count = int(round(sample_rate_hz * duration_s))
    if sample_count < 2:
        raise ValueError("duration and sample rate must yield at least 2 samples")

    time_s = np.arange(sample_count, dtype=np.float64) / sample_rate_hz
    samples = np.zeros(sample_count, dtype=np.float64)
    for frequency_hz, amplitude in components:
        samples += amplitude * np.sin(2.0 * np.pi * frequency_hz * time_s)

    if impulse_rate_hz > 0 and impulse_amplitude > 0:
        spacing = int(round(sample_rate_hz / impulse_rate_hz))
        if spacing < 1:
            raise ValueError("impulse_rate_hz is higher than the sample rate")
        samples[::spacing] += impulse_amplitude

    if noise_std > 0:
        rng = np.random.default_rng(seed)
        samples = samples + rng.normal(0.0, noise_std, size=sample_count)

    return SyntheticWaveform(
        samples=np.asarray(samples, dtype=np.float64),
        sample_rate_hz=float(sample_rate_hz),
        tone_hz=float(shaft_hz),
        amplitude=float(one_x),
        noise_std=float(noise_std),
        seed=int(seed),
        description=description,
        components=tuple((float(f), float(a)) for f, a in components),
        impulse_rate_hz=float(impulse_rate_hz),
        impulse_amplitude=float(impulse_amplitude),
    )

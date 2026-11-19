"""Write a CSV and PNG that are explicitly marked synthetic."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from af_signal import DATA_ORIGIN_SYNTHETIC
from af_signal.features import dominant_frequency_hz
from af_signal.synthetic import SyntheticWaveform


def write_synthetic_preview(
    output_dir: Path, waveform: SyntheticWaveform
) -> tuple[Path, Path]:
    """Write `preview.csv` and `preview.png` under `output_dir`."""
    if waveform.data_origin != DATA_ORIGIN_SYNTHETIC:
        raise ValueError("refusing to write a preview that is not synthetic")

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "preview.csv"
    png_path = output_dir / "preview.png"
    _write_csv(csv_path, waveform)
    _write_png(png_path, waveform)
    return csv_path, png_path


def _write_csv(path: Path, waveform: SyntheticWaveform) -> None:
    time_s = np.arange(waveform.samples.size, dtype=np.float64) / waveform.sample_rate_hz
    header = "\n".join(
        [
            f"data_origin: {waveform.data_origin}",
            "not_a_sensor_measurement: true",
            f"description: {waveform.description}",
            f"sample_rate_hz: {waveform.sample_rate_hz}",
            f"tone_hz: {waveform.tone_hz}",
            f"amplitude_synthetic: {waveform.amplitude}",
            f"noise_std_synthetic: {waveform.noise_std}",
            f"seed: {waveform.seed}",
            "columns: time_s, synthetic_amplitude",
        ]
    )
    data = np.column_stack((time_s, waveform.samples))
    np.savetxt(
        path,
        data,
        delimiter=",",
        header=header,
        comments="# ",
    )


def _write_png(path: Path, waveform: SyntheticWaveform) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    peak_hz = dominant_frequency_hz(waveform.samples, waveform.sample_rate_hz)
    time_s = np.arange(waveform.samples.size, dtype=np.float64) / waveform.sample_rate_hz
    shown = min(waveform.samples.size, int(waveform.sample_rate_hz * 0.1))

    figure, axes = plt.subplots(2, 1, figsize=(8, 6))
    figure.suptitle("SYNTHETIC — not a sensor measurement")
    axes[0].plot(time_s[:shown], waveform.samples[:shown])
    axes[0].set_xlabel("time (s)")
    axes[0].set_ylabel("synthetic amplitude")
    axes[0].set_title(waveform.description)
    _plot_spectrum(axes[1], waveform, peak_hz)
    figure.tight_layout()
    figure.savefig(path, dpi=100)
    plt.close(figure)


def _plot_spectrum(axis, waveform: SyntheticWaveform, peak_hz: float) -> None:
    from scipy.signal import detrend
    from scipy.signal.windows import hann

    values = detrend(waveform.samples, type="constant")
    window = hann(values.size, sym=False)
    magnitude = np.abs(np.fft.rfft(values * window))
    freqs = np.fft.rfftfreq(values.size, d=1.0 / waveform.sample_rate_hz)
    axis.plot(freqs, magnitude)
    axis.set_xlim(0, waveform.sample_rate_hz / 2)
    axis.set_xlabel("frequency (Hz)")
    axis.set_ylabel("rFFT magnitude")
    axis.set_title(f"dominant bin {peak_hz:.3f} Hz (synthetic)")

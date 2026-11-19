from pathlib import Path

from af_signal.preview import write_synthetic_preview
from af_signal.synthetic import generate_tone


def test_preview_files_are_marked_synthetic(tmp_path: Path):
    waveform = generate_tone(noise_std=0.0, seed=1, description="synthetic preview fixture")
    csv_path, png_path = write_synthetic_preview(tmp_path, waveform)

    text = csv_path.read_text(encoding="utf-8")
    assert "data_origin: synthetic" in text
    assert "not_a_sensor_measurement: true" in text
    assert "synthetic_amplitude" in text
    assert png_path.stat().st_size > 0
    assert png_path.suffix == ".png"

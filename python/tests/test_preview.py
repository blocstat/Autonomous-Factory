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


def test_fan_preview_lists_components_and_uses_stem(tmp_path: Path):
    from af_signal.synthetic import generate_fan_vibration

    fan = generate_fan_vibration(imbalance_amplitude=0.3)
    csv_path, png_path = write_synthetic_preview(tmp_path, fan, stem="fan_imbalance")

    assert csv_path.name == "fan_imbalance.csv"
    assert png_path.name == "fan_imbalance.png"
    text = csv_path.read_text(encoding="utf-8")
    assert "data_origin: synthetic" in text
    assert "25 Hz x 0.5" in text
    assert "175 Hz x 0.5" in text

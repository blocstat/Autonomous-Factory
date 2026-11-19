import numpy as np
import pytest

from af_signal import DATA_ORIGIN_SYNTHETIC
from af_signal.synthetic import generate_tone


def test_waveform_is_labeled_synthetic_and_reproducible():
    first = generate_tone(noise_std=0.1, seed=7)
    second = generate_tone(noise_std=0.1, seed=7)

    assert first.data_origin == DATA_ORIGIN_SYNTHETIC
    assert first.samples.dtype == np.float64
    assert first.samples.shape == (1000,)
    np.testing.assert_array_equal(first.samples, second.samples)


def test_different_seeds_change_the_noise():
    first = generate_tone(noise_std=0.1, seed=1)
    second = generate_tone(noise_std=0.1, seed=2)
    assert not np.array_equal(first.samples, second.samples)


def test_clean_tone_matches_a_unit_sine():
    waveform = generate_tone(amplitude=1.0, noise_std=0.0, tone_hz=50.0)
    time_s = np.arange(waveform.samples.size) / waveform.sample_rate_hz
    expected = np.sin(2.0 * np.pi * 50.0 * time_s)
    np.testing.assert_allclose(waveform.samples, expected, atol=1e-12)


def test_rejects_tone_at_or_above_nyquist():
    with pytest.raises(ValueError, match="Nyquist"):
        generate_tone(sample_rate_hz=1000.0, tone_hz=500.0)


def test_rejects_non_positive_duration():
    with pytest.raises(ValueError, match="duration_s"):
        generate_tone(duration_s=0.0)

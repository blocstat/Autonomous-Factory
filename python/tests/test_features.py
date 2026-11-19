import math

import numpy as np
import pytest

from af_signal.features import dominant_frequency_hz, time_domain_features
from af_signal.synthetic import generate_tone


def test_unit_sine_rms_and_crest_factor():
    waveform = generate_tone(amplitude=1.0, noise_std=0.0, tone_hz=50.0)
    features = time_domain_features(waveform.samples)

    assert features["mean"] == pytest.approx(0.0, abs=1e-12)
    assert features["rms"] == pytest.approx(1.0 / math.sqrt(2.0), rel=1e-9)
    assert features["peak_abs"] == pytest.approx(1.0, abs=1e-6)
    assert features["crest_factor"] == pytest.approx(math.sqrt(2.0), rel=1e-6)


def test_constant_signal_crest_factor_is_one():
    features = time_domain_features(np.array([2.0, 2.0, 2.0, 2.0]))
    assert features["rms"] == pytest.approx(2.0)
    assert features["crest_factor"] == pytest.approx(1.0)


def test_zero_signal_has_undefined_crest_factor():
    with pytest.raises(ValueError, match="RMS is zero"):
        time_domain_features(np.array([0.0, 0.0, 0.0]))


def test_rejects_empty_and_non_finite_samples():
    with pytest.raises(ValueError):
        time_domain_features(np.array([]))
    with pytest.raises(ValueError, match="finite"):
        time_domain_features(np.array([1.0, np.nan]))


def test_dominant_frequency_of_a_bin_centered_tone():
    waveform = generate_tone(
        sample_rate_hz=1000.0,
        duration_s=1.0,
        tone_hz=50.0,
        noise_std=0.0,
    )
    peak_hz = dominant_frequency_hz(waveform.samples, waveform.sample_rate_hz)
    assert peak_hz == pytest.approx(50.0)


def test_dominant_frequency_survives_small_synthetic_noise():
    waveform = generate_tone(
        sample_rate_hz=1000.0,
        duration_s=1.0,
        tone_hz=50.0,
        amplitude=1.0,
        noise_std=0.05,
        seed=3,
    )
    peak_hz = dominant_frequency_hz(waveform.samples, waveform.sample_rate_hz)
    assert peak_hz == pytest.approx(50.0)


def test_constant_signal_has_no_spectral_peak():
    with pytest.raises(ValueError, match="no energy"):
        dominant_frequency_hz(np.array([1.0, 1.0, 1.0, 1.0]), 1000.0)

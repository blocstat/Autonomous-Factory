"""V0 known-answer tests (review section 6.3).

Every input here is synthetic. Passing these tests shows the feature code
computes what it claims on signals with known contents. It says nothing about
real sensors or machines.
"""

import math

import numpy as np
import pytest

from af_signal import DATA_ORIGIN_SYNTHETIC
from af_signal.features import (
    band_rms,
    dominant_frequency_hz,
    kurtosis,
    time_domain_features,
)
from af_signal.synthetic import generate_fan_vibration, generate_tone


def test_off_bin_tone_peak_is_within_one_bin():
    waveform = generate_tone(sample_rate_hz=1000.0, duration_s=1.0, tone_hz=50.3)
    bin_width_hz = 1000.0 / waveform.samples.size
    peak_hz = dominant_frequency_hz(waveform.samples, waveform.sample_rate_hz)
    assert abs(peak_hz - 50.3) <= bin_width_hz


def test_sine_rms_within_0_1_percent_for_several_amplitudes():
    for amplitude in (0.01, 1.0, 7.5):
        waveform = generate_tone(amplitude=amplitude, tone_hz=50.0)
        rms = time_domain_features(waveform.samples)["rms"]
        assert rms == pytest.approx(amplitude / math.sqrt(2.0), rel=1e-3)


def test_sine_peak_to_peak_is_twice_amplitude():
    waveform = generate_tone(sample_rate_hz=1000.0, tone_hz=50.0, amplitude=2.0)
    assert time_domain_features(waveform.samples)["peak_to_peak"] == pytest.approx(
        4.0, abs=1e-6
    )


def test_sine_kurtosis_is_1_5():
    waveform = generate_tone(sample_rate_hz=1000.0, tone_hz=50.0)
    assert kurtosis(waveform.samples) == pytest.approx(1.5, rel=1e-9)


def test_gaussian_noise_kurtosis_is_about_3():
    # Standard error of kurtosis is about sqrt(24 / N) = 0.015 for N = 100,000.
    noise = np.random.default_rng(11).normal(0.0, 1.0, size=100_000)
    assert kurtosis(noise) == pytest.approx(3.0, abs=0.1)


def test_kurtosis_rejects_constant_signal():
    with pytest.raises(ValueError, match="variance is zero"):
        kurtosis(np.array([1.0, 1.0, 1.0]))


def test_band_rms_of_bin_centred_sine():
    waveform = generate_tone(sample_rate_hz=1000.0, tone_hz=50.0, amplitude=2.0)
    inside = band_rms(waveform.samples, 1000.0, 45.0, 55.0)
    outside = band_rms(waveform.samples, 1000.0, 100.0, 500.1)
    assert inside == pytest.approx(2.0 / math.sqrt(2.0), rel=1e-9)
    assert outside == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize("size", [1000, 1001])
def test_band_rms_over_full_spectrum_matches_time_domain(size):
    # Parseval check, for even and odd lengths.
    noise = np.random.default_rng(5).normal(0.0, 1.0, size=size)
    total = band_rms(noise, 1000.0, 0.0, 501.0)
    expected = math.sqrt(float(np.mean((noise - noise.mean()) ** 2)))
    assert total == pytest.approx(expected, rel=1e-9)


def test_band_rms_rejects_bad_band():
    with pytest.raises(ValueError):
        band_rms(np.array([1.0, 2.0, 3.0]), 1000.0, 10.0, 5.0)


def test_fan_signal_is_synthetic_and_reproducible():
    first = generate_fan_vibration(noise_std=0.1, seed=4)
    second = generate_fan_vibration(noise_std=0.1, seed=4)
    assert first.data_origin == DATA_ORIGIN_SYNTHETIC
    np.testing.assert_array_equal(first.samples, second.samples)


def test_fan_one_x_band_matches_shaft_plus_imbalance():
    # 25 Hz shaft at 4 kHz for 1 s puts every tone exactly on a 1 Hz bin.
    for imbalance in (0.0, 0.1, 0.4):
        fan = generate_fan_vibration(shaft_amplitude=0.2, imbalance_amplitude=imbalance)
        one_x = band_rms(fan.samples, fan.sample_rate_hz, 24.5, 25.5)
        assert one_x == pytest.approx((0.2 + imbalance) / math.sqrt(2.0), rel=1e-9)


def test_fan_imbalance_leaves_blade_pass_unchanged():
    baseline = generate_fan_vibration(imbalance_amplitude=0.0)
    imbalanced = generate_fan_vibration(imbalance_amplitude=0.4)
    band = (174.5, 175.5)  # 7 blades x 25 Hz
    assert band_rms(imbalanced.samples, 4000.0, *band) == pytest.approx(
        band_rms(baseline.samples, 4000.0, *band), rel=1e-9
    )


def test_fan_blade_pass_is_dominant_when_largest():
    fan = generate_fan_vibration(shaft_amplitude=0.2, blade_pass_amplitude=0.5)
    assert dominant_frequency_hz(fan.samples, fan.sample_rate_hz) == pytest.approx(175.0)


def test_fan_harmonics_land_at_integer_multiples():
    fan = generate_fan_vibration(harmonic_amplitudes=(0.3, 0.1))
    assert band_rms(fan.samples, 4000.0, 49.5, 50.5) == pytest.approx(
        0.3 / math.sqrt(2.0), rel=1e-9
    )
    assert band_rms(fan.samples, 4000.0, 74.5, 75.5) == pytest.approx(
        0.1 / math.sqrt(2.0), rel=1e-9
    )


def test_impulses_raise_kurtosis_and_crest_factor():
    clean = generate_fan_vibration(noise_std=0.05, seed=2)
    impacted = generate_fan_vibration(
        noise_std=0.05, seed=2, impulse_rate_hz=10.0, impulse_amplitude=3.0
    )
    assert kurtosis(impacted.samples) > kurtosis(clean.samples) + 1.0
    assert (
        time_domain_features(impacted.samples)["crest_factor"]
        > time_domain_features(clean.samples)["crest_factor"] + 1.0
    )


def test_impulse_count_matches_rate():
    fan = generate_fan_vibration(
        shaft_amplitude=0.0,
        blade_pass_amplitude=0.0,
        impulse_rate_hz=10.0,
        impulse_amplitude=1.0,
        duration_s=2.0,
    )
    assert int(np.count_nonzero(fan.samples)) == 20


def test_fan_rejects_blade_pass_above_nyquist():
    with pytest.raises(ValueError, match="Nyquist"):
        generate_fan_vibration(sample_rate_hz=300.0, shaft_hz=25.0, blade_count=7)

"""Unit tests for the blind decoder and power analysis in Quantum Space Memory v2."""

import pytest
import numpy as np

from scripts.power_analysis import run_analysis, hard_false_alarm, soft_z, z_threshold
from scripts.blind_decoder import periodogram_stat, carrier, decode, selftest, PERIODS, NSAMP


def test_power_analysis_math():
    """Verify statistical formulas in power analysis."""
    # 9 bits should give 2^-9 = 1/512
    assert abs(hard_false_alarm(9) - (1.0 / 512.0)) < 1e-10

    # 64 bits false alarm should be 2^-64
    assert abs(hard_false_alarm(64) - (2.0 ** -64)) < 1e-25

    # Threshold for 1920 cells at alpha=0.01 should be ~4.4
    z_val = z_threshold(1920, alpha=0.01)
    assert 4.3 < z_val < 4.6

    res = run_analysis()
    assert res["recommendation"]["message_bits"] == 64


def test_periodogram_white_noise_statistic():
    """Test that periodogram statistic on Gaussian noise yields reasonable positive values."""
    rng = np.random.default_rng(42)
    noise = rng.standard_normal(1024) + 1j * rng.standard_normal(1024)
    p_val = periodogram_stat(noise, period=8)
    assert p_val >= 0.0
    # Mean of Exp(1) is 1.0; single sample rarely exceeds 10
    assert p_val < 20.0


def test_periodogram_carrier_peak():
    """Test that pure carrier has massive periodogram peak at matching period."""
    target_period = 10
    pure_sig = carrier(target_period, n=1024)
    p_match = periodogram_stat(pure_sig, target_period)
    p_mismatch = periodogram_stat(pure_sig, target_period + 4)

    assert p_match > 100.0  # Massive peak
    assert p_mismatch < p_match / 10.0


def test_blind_decoder_selftest():
    """Verify that blind decoder selftest passes deterministically."""
    assert selftest() is True

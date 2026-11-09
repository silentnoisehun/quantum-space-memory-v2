"""Tests for Quantum Space Memory v2."""

import pytest
import math

from quantum_space_memory_v2 import __version__


def test_version():
    assert __version__ == "2.0.0"


def test_theta_constant():
    """Verify THETA = 0.15 * pi"""
    from scripts.wow_campaign import THETA
    assert abs(THETA - 0.15 * math.pi) < 1e-10


def test_tier_configs():
    from scripts.wow_campaign import TIERS

    assert "B0" in TIERS
    assert "B1" in TIERS
    assert "B2" in TIERS
    assert "B3" in TIERS

    # B0: 1 qubit, 20 cycles, preregistered
    assert TIERS["B0"]["qubits"] == 1
    assert TIERS["B0"]["cycles"] == 20
    assert TIERS["B0"]["prereg"] is True

    # B1: 2 qubits, 20 cycles, preregistered
    assert TIERS["B1"]["qubits"] == 2
    assert TIERS["B1"]["cycles"] == 20
    assert TIERS["B1"]["prereg"] is True

    # B2: 3 qubits, 15 cycles, preregistered
    assert TIERS["B2"]["qubits"] == 3
    assert TIERS["B2"]["cycles"] == 15
    assert TIERS["B2"]["prereg"] is True

    # B3: 5 qubits, 10 cycles, exploratory
    assert TIERS["B3"]["qubits"] == 5
    assert TIERS["B3"]["cycles"] == 10
    assert TIERS["B3"]["prereg"] is False


def test_circuit_builders_exist():
    from scripts.wow_campaign import BUILDERS

    for tier in ["B0", "B1", "B2", "B3"]:
        assert "active" in BUILDERS[tier]
        assert "passive" in BUILDERS[tier]
        assert "cal_1" in BUILDERS[tier]
        assert "cal_0" in BUILDERS[tier]


def test_b0_circuits_build():
    from scripts.wow_campaign import circuit_b0_active, circuit_b0_passive, circuit_b0_cal_1, circuit_b0_cal_0

    active = circuit_b0_active(20)
    passive = circuit_b0_passive(20)
    cal_1 = circuit_b0_cal_1()
    cal_0 = circuit_b0_cal_0()

    assert active.num_qubits == 1
    assert passive.num_qubits == 1
    assert cal_1.num_qubits == 1
    assert cal_0.num_qubits == 1


def test_b1_circuits_build():
    from scripts.wow_campaign import circuit_b1_active, circuit_b1_passive, circuit_b1_cal_1, circuit_b1_cal_0

    active = circuit_b1_active(20)
    passive = circuit_b1_passive(20)
    cal_1 = circuit_b1_cal_1()
    cal_0 = circuit_b1_cal_0()

    assert active.num_qubits == 2
    assert passive.num_qubits == 2
    assert cal_1.num_qubits == 2
    assert cal_0.num_qubits == 2


def test_b2_circuits_build():
    from scripts.wow_campaign import circuit_b2_active, circuit_b2_passive, circuit_b2_cal_1, circuit_b2_cal_0

    active = circuit_b2_active(15)
    passive = circuit_b2_passive(15)
    cal_1 = circuit_b2_cal_1()
    cal_0 = circuit_b2_cal_0()

    assert active.num_qubits == 3
    assert passive.num_qubits == 3
    assert cal_1.num_qubits == 3
    assert cal_0.num_qubits == 3


def test_b3_circuits_build():
    from scripts.wow_campaign import circuit_b3_active, circuit_b3_passive, circuit_b3_cal_1, circuit_b3_cal_0

    active = circuit_b3_active(10)
    passive = circuit_b3_passive(10)
    cal_1 = circuit_b3_cal_1()
    cal_0 = circuit_b3_cal_0()

    assert active.num_qubits == 5
    assert passive.num_qubits == 5
    assert cal_1.num_qubits == 5
    assert cal_0.num_qubits == 5


def test_circuit_hashes():
    from scripts.wow_campaign import circuit_hashes

    for tier in ["B0", "B1", "B2", "B3"]:
        hashes = circuit_hashes(tier, TIERS[tier]["cycles"])
        assert len(hashes) == 4
        for name, h in hashes.items():
            assert len(h) == 64  # SHA-256 hex


def test_wilson_ci():
    from scripts.extract_wow import wilson_ci

    # Test basic case
    low, high = wilson_ci(50, 100)
    assert 0.4 <= low <= 0.5
    assert 0.5 <= high <= 0.6

    # Test edge cases
    low, high = wilson_ci(0, 100)
    assert low == 0.0
    assert high > 0.0

    low, high = wilson_ci(100, 100)
    assert high == 1.0
    assert low < 1.0

    # Test zero shots
    low, high = wilson_ci(0, 0)
    assert low == 0.0
    assert high == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
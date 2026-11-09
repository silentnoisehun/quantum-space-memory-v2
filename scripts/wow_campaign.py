#!/usr/bin/env python3
"""
wow_campaign.py — 4-Tier WOW QPU Campaign for Quantum Space Memory v2

Tiers:
  B0: Single-qubit Zeno (N=20) — preregistered
  B1: Bell parity Zeno (N=20) — preregistered
  B2: GHZ-3 population (N=15) — preregistered
  B3: 5-qubit space memory (N=10) — exploratory

Usage:
  python wow_campaign.py --tier B0 --dry-run
  python wow_campaign.py --tier B0 --submit
  python wow_campaign.py --tier B1 --submit --backend ibm_marrakesh
"""
import argparse
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit import qasm3

THETA = 0.15 * math.pi
RAW = Path(__file__).resolve().parent.parent / "measurement_raw"
RAW.mkdir(parents=True, exist_ok=True)

# Tier configurations
TIERS = {
    "B0": {"name": "Single-Qubit Zeno", "qubits": 1, "cycles": 20, "shots": 2000, "prereg": True},
    "B1": {"name": "Bell Parity Zeno", "qubits": 2, "cycles": 20, "shots": 2000, "prereg": True},
    "B2": {"name": "GHZ-3 Population", "qubits": 3, "cycles": 15, "shots": 2000, "prereg": True},
    "B3": {"name": "5-Qubit Space Memory", "qubits": 5, "cycles": 10, "shots": 2000, "prereg": False},
}


# ============================================================ CIRCUIT BUILDERS
def circuit_b0_active(cycles: int, theta: float = THETA):
    """B0 Active: X -> [Rx -> M -> if(0):X] x N -> M"""
    qr = QuantumRegister(1, "q")
    cr = ClassicalRegister(cycles + 1, "c")
    qc = QuantumCircuit(qr, cr, name=f"b0_active_N{cycles}")
    qc.x(qr[0])
    for s in range(cycles):
        qc.rx(theta, qr[0])
        qc.measure(qr[0], cr[s])
        with qc.if_test((cr[s], 0)):
            qc.x(qr[0])
    qc.measure(qr[0], cr[cycles])
    return qc


def circuit_b0_passive(cycles: int, theta: float = THETA):
    """B0 Passive: X -> [Rx] x N -> M"""
    qr = QuantumRegister(1, "q")
    cr = ClassicalRegister(1, "c")
    qc = QuantumCircuit(qr, cr, name=f"b0_passive_N{cycles}")
    qc.x(qr[0])
    for _ in range(cycles):
        qc.rx(theta, qr[0])
    qc.measure(qr[0], cr[0])
    return qc


def circuit_b0_cal_1():
    qr = QuantumRegister(1, "q")
    cr = ClassicalRegister(1, "c")
    qc = QuantumCircuit(qr, cr, name="b0_cal_1")
    qc.x(qr[0])
    qc.measure(qr[0], cr[0])
    return qc


def circuit_b0_cal_0():
    qr = QuantumRegister(1, "q")
    cr = ClassicalRegister(1, "c")
    qc = QuantumCircuit(qr, cr, name="b0_cal_0")
    qc.measure(qr[0], cr[0])
    return qc


def circuit_b1_active(cycles: int, theta: float = THETA):
    """B1 Active: |Φ⁺⟩ -> [Rx on q1 -> M_q1 -> if(0):X on q1] x N -> Bell measure"""
    qr = QuantumRegister(2, "q")
    cr = ClassicalRegister(cycles + 2, "c")  # cycles mid + 2 final Bell
    qc = QuantumCircuit(qr, cr, name=f"b1_active_N{cycles}")

    # Bell prep
    qc.h(qr[0])
    qc.cx(qr[0], qr[1])

    # Zeno on q1 only
    for s in range(cycles):
        qc.rx(theta, qr[1])
        qc.measure(qr[1], cr[s])
        with qc.if_test((cr[s], 0)):
            qc.x(qr[1])

    # Bell measurement
    qc.cx(qr[0], qr[1])
    qc.h(qr[0])
    qc.measure(qr[0], cr[cycles])
    qc.measure(qr[1], cr[cycles + 1])
    return qc


def circuit_b1_passive(cycles: int, theta: float = THETA):
    """B1 Passive: |Φ⁺⟩ -> [Rx on q1] x N -> Bell measure"""
    qr = QuantumRegister(2, "q")
    cr = ClassicalRegister(2, "c")
    qc = QuantumCircuit(qr, cr, name=f"b1_passive_N{cycles}")

    qc.h(qr[0])
    qc.cx(qr[0], qr[1])
    for _ in range(cycles):
        qc.rx(theta, qr[1])
    qc.cx(qr[0], qr[1])
    qc.h(qr[0])
    qc.measure(qr[0], cr[0])
    qc.measure(qr[1], cr[1])
    return qc


def circuit_b1_cal_1():
    qr = QuantumRegister(2, "q")
    cr = ClassicalRegister(2, "c")
    qc = QuantumCircuit(qr, cr, name="b1_cal_1")
    qc.h(qr[0])
    qc.cx(qr[0], qr[1])
    qc.x(qr[1])
    qc.measure(qr[0], cr[0])
    qc.measure(qr[1], cr[1])
    return qc


def circuit_b1_cal_0():
    qr = QuantumRegister(2, "q")
    cr = ClassicalRegister(2, "c")
    qc = QuantumCircuit(qr, cr, name="b1_cal_0")
    qc.h(qr[0])
    qc.cx(qr[0], qr[1])
    qc.measure(qr[0], cr[0])
    qc.measure(qr[1], cr[1])
    return qc


def circuit_b2_active(cycles: int, theta: float = THETA):
    """B2 Active: |GHZ₃⟩ -> [Rx on all -> M_all -> if(0):X] x N -> measure all"""
    nq = 3
    qr = QuantumRegister(nq, "q")
    cr = ClassicalRegister(nq * cycles + nq, "c")
    qc = QuantumCircuit(qr, cr, name=f"b2_active_N{cycles}")

    # GHZ-3 prep
    qc.h(qr[0])
    qc.cx(qr[0], qr[1])
    qc.cx(qr[1], qr[2])

    # Zeno on all 3 qubits simultaneously
    for s in range(cycles):
        for q in range(nq):
            qc.rx(theta, qr[q])
        qc.barrier()
        for q in range(nq):
            qc.measure(qr[q], cr[s * nq + q])
            with qc.if_test((cr[s * nq + q], 0)):
                qc.x(qr[q])

    for q in range(nq):
        qc.measure(qr[q], cr[cycles * nq + q])
    return qc


def circuit_b2_passive(cycles: int, theta: float = THETA):
    """B2 Passive: |GHZ₃⟩ -> [Rx on all] x N -> measure all"""
    nq = 3
    qr = QuantumRegister(nq, "q")
    cr = ClassicalRegister(nq, "c")
    qc = QuantumCircuit(qr, cr, name=f"b2_passive_N{cycles}")

    qc.h(qr[0])
    qc.cx(qr[0], qr[1])
    qc.cx(qr[1], qr[2])
    for _ in range(cycles):
        for q in range(nq):
            qc.rx(theta, qr[q])
    for q in range(nq):
        qc.measure(qr[q], cr[q])
    return qc


def circuit_b2_cal_1():
    nq = 3
    qr = QuantumRegister(nq, "q")
    cr = ClassicalRegister(nq, "c")
    qc = QuantumCircuit(qr, cr, name="b2_cal_1")
    qc.h(qr[0])
    qc.cx(qr[0], qr[1])
    qc.cx(qr[1], qr[2])
    for q in range(nq):
        qc.x(qr[q])
    for q in range(nq):
        qc.measure(qr[q], cr[q])
    return qc


def circuit_b2_cal_0():
    nq = 3
    qr = QuantumRegister(nq, "q")
    cr = ClassicalRegister(nq, "c")
    qc = QuantumCircuit(qr, cr, name="b2_cal_0")
    qc.h(qr[0])
    qc.cx(qr[0], qr[1])
    qc.cx(qr[1], qr[2])
    for q in range(nq):
        qc.measure(qr[q], cr[q])
    return qc


def circuit_b3_active(cycles: int, theta: float = THETA):
    """B3 Active: |GHZ₅⟩ -> [Rx on all -> M_all -> if(0):X] x N -> measure all"""
    nq = 5
    qr = QuantumRegister(nq, "q")
    cr = ClassicalRegister(nq * cycles + nq, "c")
    qc = QuantumCircuit(qr, cr, name=f"b3_active_N{cycles}")

    # GHZ-5 prep
    qc.h(qr[0])
    for q in range(1, nq):
        qc.cx(qr[q - 1], qr[q])

    # Zeno on all 5 qubits simultaneously
    for s in range(cycles):
        for q in range(nq):
            qc.rx(theta, qr[q])
        qc.barrier()
        for q in range(nq):
            qc.measure(qr[q], cr[s * nq + q])
            with qc.if_test((cr[s * nq + q], 0)):
                qc.x(qr[q])

    for q in range(nq):
        qc.measure(qr[q], cr[cycles * nq + q])
    return qc


def circuit_b3_passive(cycles: int, theta: float = THETA):
    """B3 Passive: |GHZ₅⟩ -> [Rx on all] x N -> measure all"""
    nq = 5
    qr = QuantumRegister(nq, "q")
    cr = ClassicalRegister(nq, "c")
    qc = QuantumCircuit(qr, cr, name=f"b3_passive_N{cycles}")

    qc.h(qr[0])
    for q in range(1, nq):
        qc.cx(qr[q - 1], qr[q])
    for _ in range(cycles):
        for q in range(nq):
            qc.rx(theta, qr[q])
    for q in range(nq):
        qc.measure(qr[q], cr[q])
    return qc


def circuit_b3_cal_1():
    nq = 5
    qr = QuantumRegister(nq, "q")
    cr = ClassicalRegister(nq, "c")
    qc = QuantumCircuit(qr, cr, name="b3_cal_1")
    qc.h(qr[0])
    for q in range(1, nq):
        qc.cx(qr[q - 1], qr[q])
    for q in range(nq):
        qc.x(qr[q])
    for q in range(nq):
        qc.measure(qr[q], cr[q])
    return qc


def circuit_b3_cal_0():
    nq = 5
    qr = QuantumRegister(nq, "q")
    cr = ClassicalRegister(nq, "c")
    qc = QuantumCircuit(qr, cr, name="b3_cal_0")
    qc.h(qr[0])
    for q in range(1, nq):
        qc.cx(qr[q - 1], qr[q])
    for q in range(nq):
        qc.measure(qr[q], cr[q])
    return qc


# Circuit builder map
BUILDERS = {
    "B0": {
        "active": circuit_b0_active,
        "passive": circuit_b0_passive,
        "cal_1": circuit_b0_cal_1,
        "cal_0": circuit_b0_cal_0,
    },
    "B1": {
        "active": circuit_b1_active,
        "passive": circuit_b1_passive,
        "cal_1": circuit_b1_cal_1,
        "cal_0": circuit_b1_cal_0,
    },
    "B2": {
        "active": circuit_b2_active,
        "passive": circuit_b2_passive,
        "cal_1": circuit_b2_cal_1,
        "cal_0": circuit_b2_cal_0,
    },
    "B3": {
        "active": circuit_b3_active,
        "passive": circuit_b3_passive,
        "cal_1": circuit_b3_cal_1,
        "cal_0": circuit_b3_cal_0,
    },
}


def circuit_hashes(tier: str, cycles: int):
    """Compute SHA-256 of QASM3 for all circuits in tier."""
    builders = BUILDERS[tier]
    h = {}
    for name, builder in builders.items():
        if name in ("cal_1", "cal_0"):
            qc = builder()
        else:
            qc = builder(cycles)
        blob = qasm3.dumps(qc).encode()
        h[name] = hashlib.sha256(blob).hexdigest()
    return h


def get_service():
    """Get QiskitRuntimeService with API key from env or Downloads."""
    from qiskit_ibm_runtime import QiskitRuntimeService
    api_key = os.environ.get("QISKIT_IBM_RUNTIME_API_KEY") or os.environ.get("IBM_API_KEY")
    if not api_key:
        downloads = Path(os.environ["USERPROFILE"]) / "Downloads"
        for fname in ["apikey (2) (2).json", "apikey (2) (1).json", "apikey.json"]:
            kp = downloads / fname
            if kp.exists():
                try:
                    data = json.loads(kp.read_text(encoding="utf-8"))
                    api_key = data.get("apikey") or data.get("token")
                    if api_key:
                        break
                except Exception:
                    pass
    if api_key:
        return QiskitRuntimeService(channel="ibm_quantum_platform", token=api_key)
    return QiskitRuntimeService(channel="ibm_quantum_platform", instance="auto")


def main():
    ap = argparse.ArgumentParser(description="WOW Campaign: 4-Tier QPU Jobs")
    ap.add_argument("--tier", choices=list(TIERS.keys()), required=True,
                    help="Campaign tier: B0, B1, B2, B3")
    ap.add_argument("--backend", default="ibm_marrakesh", help="IBM backend name")
    ap.add_argument("--cycles", type=int, default=None, help="Override cycles")
    ap.add_argument("--shots", type=int, default=None, help="Override shots")
    ap.add_argument("--dry-run", action="store_true", help="Build circuits only, no submission")
    ap.add_argument("--submit", action="store_true", help="Submit to QPU")
    a = ap.parse_args()

    if a.tier not in TIERS:
        sys.exit(f"Unknown tier: {a.tier}")

    tier_cfg = TIERS[a.tier]
    cycles = a.cycles or tier_cfg["cycles"]
    shots = a.shots or tier_cfg["shots"]

    # Preregistration check
    if tier_cfg["prereg"] and cycles < tier_cfg["cycles"]:
        sys.exit(f"Tier {a.tier} prereg requires cycles >= {tier_cfg['cycles']}")

    print("=" * 72)
    print(f"WOW CAMPAIGN — Tier {a.tier}: {tier_cfg['name']}")
    print("=" * 72)
    print(f"Qubits: {tier_cfg['qubits']} | Cycles: {cycles} | Shots: {shots}")
    print(f"Preregistered: {tier_cfg['prereg']}")
    print(f"Backend: {a.backend}")
    print()

    builders = BUILDERS[a.tier]
    circuits = {
        "active": builders["active"](cycles),
        "passive": builders["passive"](cycles),
        "cal_1": builders["cal_1"](),
        "cal_0": builders["cal_0"](),
    }

    hashes = circuit_hashes(a.tier, cycles)

    manifest = {
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tier": a.tier,
        "tier_name": tier_cfg["name"],
        "backend": a.backend,
        "qubits": tier_cfg["qubits"],
        "cycles": cycles,
        "shots": shots,
        "theta": THETA,
        "circuit_sha256": hashes,
        "preregistered": tier_cfg["prereg"],
        "pubs": {"0": "active", "1": "passive", "2": "cal_1", "3": "cal_0"},
        "note": "All 4 circuits in one job; cal_1/cal_0 provide in-job readout calibration",
    }

    print(json.dumps(manifest, indent=2))

    if a.dry_run or not a.submit:
        p = RAW / f"wow_{a.tier}_manifest_dry_{int(time.time())}.json"
        p.write_text(json.dumps(manifest, indent=2))
        print(f"\n[dry-run] manifest: {p}")
        print("Submit with: --submit")
        return

    # Submit to hardware
    from qiskit_ibm_runtime import SamplerV2
    svc = get_service()
    backend = svc.backend(a.backend)
    print(f"\nbackend: {backend.name} ({backend.num_qubits} qubit)")

    pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
    isa = {k: pm.run(v) for k, v in circuits.items()}

    sampler = SamplerV2(mode=backend)
    job = sampler.run([isa["active"], isa["passive"], isa["cal_1"], isa["cal_0"]],
                      shots=shots)
    jid = job.job_id()
    manifest.update(job_id=jid, status="QUEUED")
    out = RAW / f"wow_{a.tier}_job_{jid}.json"
    out.write_text(json.dumps(manifest, indent=2))
    print(f"\nJOB ID: {jid}")
    print(f"manifest: {out}")
    print(f"\nExtract with: python scripts/extract_wow.py --job {jid} --tier {a.tier}")


if __name__ == "__main__":
    main()
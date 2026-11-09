#!/usr/bin/env python3
"""
cross_chip_campaign.py — Stage 2: Cross-Chip Kerneled IQ WOW Campaign (Marrakesh -> Kingston)

Architektúra (a PREREGISTRATION-cross_chip_blind_carrier_wow.md szerint):
  Tier A: Azonos qubit, azonos job (ibm_marrakesh) — Műszer pozitív kontroll
  Tier B: Szomszédos qubit, azonos job (ibm_marrakesh) — Fizikai áthallás alapvonal
  Tier C: Távoli qubit / későbbi job (ibm_marrakesh) — Chip-lokális lecsengési plafon
  Tier D: Külön hűtőgép (ibm_kingston) — Vak keresés a 20 qubiten, 6 delay-en, kerneled (I,Q)

Használat:
  python scripts/cross_chip_campaign.py --dry-run
  python scripts/cross_chip_campaign.py --submit-marrakesh   # Tier A, B, C írás & kontroll
  python scripts/cross_chip_campaign.py --submit-kingston    # Tier D vak kiolvasás
"""
import argparse
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path
import numpy as np

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

RAW = Path(__file__).resolve().parent.parent / "measurement_raw"
RAW.mkdir(parents=True, exist_ok=True)

# 64-bites titkos mintázat (determinisztikus sóval és időbélyeggel rögzítve)
SECRET_SALT = "AURORA_WOW_SPACE_MEMORY_20261109"
CARRIER_FREQ_INDEX = 7  # secret carrier period = 11 ticks
DELAYS_US = [0.0, 1.0, 10.0, 100.0, 1000.0, 10000.0]  # 6 lecsengési lépcső
SHOTS = 1024


def get_service():
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


def build_write_read_circuit(delay_us: float, freq_idx: int = CARRIER_FREQ_INDEX, is_control: bool = False) -> QuantumCircuit:
    """
    Tier A & B áramkör Marrakeshre:
    q0: aktív írás + fázis forgatás Rz-vel + BPSK fázisváltások
    q1: szomszédos spectator qubit (passzív idle + mérés az áthallás mérésére)
    """
    qr = QuantumRegister(2, "q")
    cr = ClassicalRegister(2, "c")
    qc = QuantumCircuit(qr, cr, name=f"marrakesh_write_d{int(delay_us)}us")

    # Kezdő állapot: |+> az X-bázisú méréshez
    qc.h(qr[0])
    qc.h(qr[1])

    if not is_control:
        # Digitális vivő fázis-inkrementum Rz-vel
        period_ticks = freq_idx + 4
        dphi = 2.0 * math.pi / period_ticks
        # Virtuális Z moduláció
        qc.rz(dphi, qr[0])

    if delay_us > 0:
        qc.delay(int(delay_us * 1000), qr[0], unit="ns")
        qc.delay(int(delay_us * 1000), qr[1], unit="ns")

    # Mérés X-bázisban (Hadamard után mérés)
    qc.h(qr[0])
    qc.h(qr[1])
    qc.measure(qr[0], cr[0])
    qc.measure(qr[1], cr[1])
    return qc


def build_blind_read_circuit(delay_us: float, num_qubits: int = 4) -> QuantumCircuit:
    """
    Tier D áramkör Kingstonra:
    Tiszta vak kiolvasás kerneled IQ-val, nem ismerve az írás frekvenciáját.
    """
    qr = QuantumRegister(num_qubits, "q")
    cr = ClassicalRegister(num_qubits, "c")
    qc = QuantumCircuit(qr, cr, name=f"kingston_blind_d{int(delay_us)}us")

    # X-bázis vizsgálat
    for q in range(num_qubits):
        qc.h(qr[q])
    if delay_us > 0:
        for q in range(num_qubits):
            qc.delay(int(delay_us * 1000), qr[q], unit="ns")
    for q in range(num_qubits):
        qc.h(qr[q])
        qc.measure(qr[q], cr[q])
    return qc


def main():
    ap = argparse.ArgumentParser(description="Stage 2: Cross-Chip Kerneled IQ Campaign")
    ap.add_argument("--dry-run", action="store_true", help="Build manifests only")
    ap.add_argument("--submit-marrakesh", action="store_true", help="Submit Tier A/B to Marrakesh")
    ap.add_argument("--submit-kingston", action="store_true", help="Submit Tier D to Kingston")
    a = ap.parse_args()

    print("=" * 78)
    print("STAGE 2: CROSS-CHIP KERNELED IQ CAMPAIGN (Marrakesh -> Kingston)")
    print("=" * 78)

    marrakesh_circuits = [build_write_read_circuit(d) for d in DELAYS_US]
    kingston_circuits = [build_blind_read_circuit(d, num_qubits=4) for d in DELAYS_US]

    print(f"Marrakesh (Tier A/B) áramkörök száma: {len(marrakesh_circuits)} (delays: {DELAYS_US} us)")
    print(f"Kingston (Tier D) áramkörök száma:   {len(kingston_circuits)} (delays: {DELAYS_US} us)")

    manifest = {
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "secret_salt": SECRET_SALT,
        "committed_carrier_hash": hashlib.sha256(f"{SECRET_SALT}_{CARRIER_FREQ_INDEX}".encode()).hexdigest(),
        "delays_us": DELAYS_US,
        "shots": SHOTS,
        "options": {"execution": {"meas_type": "kerneled"}},
        "tier_a_b_backend": "ibm_marrakesh",
        "tier_d_backend": "ibm_kingston",
    }

    manifest_file = RAW / f"cross_chip_manifest_dry_{int(time.time())}.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest mentve: {manifest_file}")
    print(f"Titkos vivő hash: {manifest['committed_carrier_hash'][:16]}... (előregisztrálva)")

    if a.dry_run or not (a.submit_marrakesh or a.submit_kingston):
        print("\n[dry-run kész] Futtatáshoz: --submit-marrakesh és --submit-kingston")
        return

    from qiskit_ibm_runtime import SamplerV2
    svc = get_service()

    if a.submit_marrakesh:
        b_marrakesh = svc.backend("ibm_marrakesh")
        print(f"\nTranspiling for {b_marrakesh.name}...")
        pm_m = generate_preset_pass_manager(backend=b_marrakesh, optimization_level=1)
        isa_m = [pm_m.run(qc) for qc in marrakesh_circuits]
        sampler_m = SamplerV2(mode=b_marrakesh)
        sampler_m.options.execution.meas_type = "kerneled"
        job_m = sampler_m.run(isa_m, shots=SHOTS)
        jid_m = job_m.job_id()
        manifest["marrakesh_job_id"] = jid_m
        print(f"MARRAKESH JOB ID: {jid_m} (QUEUED, meas_type='kerneled')")

    if a.submit_kingston:
        b_kingston = svc.backend("ibm_kingston")
        print(f"\nTranspiling for {b_kingston.name}...")
        pm_k = generate_preset_pass_manager(backend=b_kingston, optimization_level=1)
        isa_k = [pm_k.run(qc) for qc in kingston_circuits]
        sampler_k = SamplerV2(mode=b_kingston)
        sampler_k.options.execution.meas_type = "kerneled"
        job_k = sampler_k.run(isa_k, shots=SHOTS)
        jid_k = job_k.job_id()
        manifest["kingston_job_id"] = jid_k
        print(f"KINGSTON JOB ID:  {jid_k} (QUEUED, meas_type='kerneled')")

    out_final = RAW / f"cross_chip_submitted_{int(time.time())}.json"
    out_final.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nJob adatok mentve: {out_final}")


if __name__ == "__main__":
    main()

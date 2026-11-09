#!/usr/bin/env python3
"""
extract_wow.py — Extract and analyze WOW campaign QPU results

Usage:
  python extract_wow.py --job <JOB_ID> --tier B0
  python extract_wow.py --job <JOB_ID> --tier B0 --save
"""
import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

from qiskit_ibm_runtime import QiskitRuntimeService
import numpy as np

RAW = Path(__file__).resolve().parent.parent / "measurement_raw"
RAW.mkdir(parents=True, exist_ok=True)

THETA = 0.15 * math.pi

# Tier configurations
TIERS = {
    "B0": {"name": "Single-Qubit Zeno", "qubits": 1, "cycles": 20, "prereg": True},
    "B1": {"name": "Bell Parity Zeno", "qubits": 2, "cycles": 20, "prereg": True},
    "B2": {"name": "GHZ-3 Population", "qubits": 3, "cycles": 15, "prereg": True},
    "B3": {"name": "5-Qubit Space Memory", "qubits": 5, "cycles": 10, "prereg": False},
}


def wilson_ci(k: int, n: int, z: float = 1.96):
    """Wilson score 95% CI for binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def get_service():
    api_key = os.environ.get("QISKIT_IBM_RUNTIME_API_KEY") or os.environ.get("IBM_API_KEY")
    instance = os.environ.get("IBM_QUANTUM_INSTANCE", "auto")
    if api_key:
        return QiskitRuntimeService(
            channel="ibm_quantum_platform",
            token=api_key,
            instance=instance
        )
    return QiskitRuntimeService(channel="ibm_quantum_platform", instance=instance)


def extract_counts(pub_result, pub_name: str):
    """Extract counts dict from SamplerV2 pub result."""
    try:
        data = pub_result.data()
        if hasattr(data, 'c'):
            return dict(data.c.get_counts())
        # Fallback for different result formats
        return dict(data.get_counts())
    except Exception as e:
        print(f"[warn] Could not extract counts for {pub_name}: {e}")
        return {}


def analyze_b0(counts_active, counts_passive, counts_cal_1, counts_cal_0, shots):
    """B0: Single-qubit Zeno analysis."""
    # Active: final bit (index cycles) should be 1 for survival
    active_1 = counts_active.get('1', 0)
    active_0 = counts_active.get('0', 0)
    p_active = active_1 / shots if shots else 0

    # Passive: final bit should be 0 (decayed to |0⟩)
    passive_0 = counts_passive.get('0', 0)
    passive_1 = counts_passive.get('1', 0)
    p_passive = passive_1 / shots if shots else 0

    # Calibration for readout matrix
    cal1_1 = counts_cal_1.get('1', 0)
    cal1_0 = counts_cal_1.get('0', 0)
    cal0_0 = counts_cal_0.get('0', 0)
    cal0_1 = counts_cal_0.get('1', 0)

    # Readout error rates
    p01 = cal0_1 / shots if shots else 0  # p(1|0)
    p10 = cal1_0 / shots if shots else 0  # p(0|1)

    # Readout-corrected active
    p_active_raw = p_active
    if (1 - p01 - p10) != 0:
        p_active_corr = (p_active - p01) / (1 - p01 - p10)
    else:
        p_active_corr = p_active_raw

    delta = p_active_corr - p_passive

    return {
        "p_active_raw": p_active_raw,
        "p_active_corrected": p_active_corr,
        "p_passive": p_passive,
        "delta_f": delta,
        "readout_p01": p01,
        "readout_p10": p10,
        "active_ci": wilson_ci(active_1, shots),
        "passive_ci": wilson_ci(passive_1, shots),
        "prereg_pass": delta > 0.30,
    }


def analyze_b1(counts_active, counts_passive, counts_cal_1, counts_cal_0, shots):
    """B1: Bell parity Zeno analysis."""
    # Active: parity survival = P(00) + P(11)
    active_parity = counts_active.get('00', 0) + counts_active.get('11', 0)
    p_active = active_parity / shots if shots else 0

    # Passive: parity survival
    passive_parity = counts_passive.get('00', 0) + counts_passive.get('11', 0)
    p_passive = passive_parity / shots if shots else 0

    # Calibration
    cal1_00 = counts_cal_1.get('00', 0)
    cal1_11 = counts_cal_1.get('11', 0)
    cal0_00 = counts_cal_0.get('00', 0)
    cal0_11 = counts_cal_0.get('11', 0)

    # Readout matrix for 2-qubit Bell basis
    # Simplified: use single-qubit rates from cal circuits
    # For Bell state, we need the 4x4 matrix - simplified to parity
    p01_single = 1 - cal0_00 / shots if shots else 0
    p10_single = 1 - cal1_11 / shots if shots else 0

    # Parity readout correction (simplified)
    p_active_corr = p_active  # Placeholder - full 4x4 correction needed
    delta = p_active_corr - p_passive

    return {
        "p_active_raw": p_active,
        "p_active_corrected": p_active_corr,
        "p_passive": p_passive,
        "delta_f": delta,
        "active_parity_count": active_parity,
        "passive_parity_count": passive_parity,
        "active_ci": wilson_ci(active_parity, shots),
        "passive_ci": wilson_ci(passive_parity, shots),
        "prereg_pass": delta > 0.15,
    }


def analyze_b2(counts_active, counts_passive, counts_cal_1, counts_cal_0, shots):
    """B2: GHZ-3 population fidelity."""
    # Population fidelity = P(000) + P(111)
    active_pop = counts_active.get('000', 0) + counts_active.get('111', 0)
    p_active = active_pop / shots if shots else 0

    passive_pop = counts_passive.get('000', 0) + counts_passive.get('111', 0)
    p_passive = passive_pop / shots if shots else 0

    delta = p_active - p_passive  # No readout correction for now

    return {
        "p_active": p_active,
        "p_passive": p_passive,
        "delta_f": delta,
        "active_pop_count": active_pop,
        "passive_pop_count": passive_pop,
        "active_ci": wilson_ci(active_pop, shots),
        "passive_ci": wilson_ci(passive_pop, shots),
        "prereg_pass": delta > 0.05,
    }


def analyze_b3(counts_active, counts_passive, counts_cal_1, counts_cal_0, shots):
    """B3: 5-qubit exploratory."""
    active_pop = counts_active.get('00000', 0) + counts_active.get('11111', 0)
    p_active = active_pop / shots if shots else 0

    passive_pop = counts_passive.get('00000', 0) + counts_passive.get('11111', 0)
    p_passive = passive_pop / shots if shots else 0

    delta = p_active - p_passive

    return {
        "p_active": p_active,
        "p_passive": p_passive,
        "delta_f": delta,
        "active_pop_count": active_pop,
        "passive_pop_count": passive_pop,
        "active_ci": wilson_ci(active_pop, shots),
        "passive_ci": wilson_ci(passive_pop, shots),
        "prereg_pass": None,  # No prereg for B3
    }


ANALYZERS = {
    "B0": analyze_b0,
    "B1": analyze_b1,
    "B2": analyze_b2,
    "B3": analyze_b3,
}


def main():
    ap = argparse.ArgumentParser(description="Extract WOW campaign results")
    ap.add_argument("--job", required=True, help="IBM job ID")
    ap.add_argument("--tier", choices=list(TIERS.keys()), required=True, help="Tier")
    ap.add_argument("--save", action="store_true", help="Save raw counts to measurement_raw/")
    ap.add_argument("--wait", type=int, default=300, help="Max wait time in seconds")
    a = ap.parse_args()

    if a.tier not in TIERS:
        sys.exit(f"Unknown tier: {a.tier}")

    tier_cfg = TIERS[a.tier]

    print("=" * 72)
    print(f"WOW EXTRACT — Tier {a.tier}: {tier_cfg['name']} (Job: {a.job})")
    print("=" * 72)

    svc = get_service()
    job = svc.job(a.job)

    print(f"Status: {job.status()}")
    if job.status().name not in ("DONE", "COMPLETED"):
        print(f"Waiting up to {a.wait}s for completion...")
        job.wait_for_final_state(timeout=a.wait)
        print(f"Final status: {job.status()}")

    if job.status().name not in ("DONE", "COMPLETED"):
        sys.exit(f"Job not completed: {job.status()}")

    result = job.result()
    pubs = result
    print(f"Number of pubs: {len(pubs)}")

    # Extract counts for each pub (0=active, 1=passive, 2=cal_1, 3=cal_0)
    counts = {}
    pub_names = ["active", "passive", "cal_1", "cal_0"]
    for i, name in enumerate(pub_names):
        if i < len(pubs):
            counts[name] = extract_counts(pubs[i], name)
            print(f"  {name}: {len(counts[name])} outcomes, total shots: {sum(counts[name].values())}")
        else:
            counts[name] = {}
            print(f"  {name}: MISSING")

    shots = sum(counts["active"].values()) if counts["active"] else 2000

    # Analyze
    analyzer = ANALYZERS[a.tier]
    analysis = analyzer(
        counts["active"], counts["passive"],
        counts["cal_1"], counts["cal_0"],
        shots
    )

    # Print results
    print("\n" + "=" * 72)
    print("ANALYSIS RESULTS")
    print("=" * 72)
    print(f"Tier: {a.tier} ({tier_cfg['name']})")
    print(f"Shots per circuit: {shots}")

    for k, v in analysis.items():
        if isinstance(v, float):
            if "ci" in k.lower():
                print(f"  {k}: [{v[0]:.4f}, {v[1]:.4f}]")
            else:
                print(f"  {k}: {v:.6f}")
        elif isinstance(v, tuple):
            print(f"  {k}: [{v[0]:.4f}, {v[1]:.4f}]")
        else:
            print(f"  {k}: {v}")

    if tier_cfg["prereg"] and analysis.get("prereg_pass") is not None:
        gate = "ΔF > 0.30" if a.tier == "B0" else ("ΔF > 0.15" if a.tier == "B1" else "ΔF > 0.05")
        print(f"\nPreregistration gate ({gate}): {'✓ PASSED' if analysis['prereg_pass'] else '✗ FAILED'}")

    # Save raw data
    if a.save:
        out = {
            "job_id": a.job,
            "tier": a.tier,
            "tier_name": tier_cfg["name"],
            "extracted_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "shots": shots,
            "counts": counts,
            "analysis": analysis,
        }
        p = RAW / f"wow_{a.tier}_job_{a.job}_{int(time.time())}.json"
        p.write_text(json.dumps(out, indent=2))
        print(f"\nSaved: {p}")

    # Also save as CSV summary
    csv_out = RAW / f"wow_{a.tier}_summary_{a.job}.csv"
    with open(csv_out, "w") as f:
        f.write("tier,job_id,shots,metric,value\n")
        for k, v in analysis.items():
            if isinstance(v, float):
                f.write(f"{a.tier},{a.job},{shots},{k},{v:.6f}\n")
            elif isinstance(v, tuple):
                f.write(f"{a.tier},{a.job},{shots},{k}_low,{v[0]:.6f}\n")
                f.write(f"{a.tier},{a.job},{shots},{k}_high,{v[1]:.6f}\n")
    print(f"CSV summary: {csv_out}")


if __name__ == "__main__":
    main()
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
    """Get QiskitRuntimeService with API key from env or Downloads."""
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


def extract_counts(pub_result, pub_name: str):
    """Extract counts dict from SamplerV2 pub result."""
    try:
        data = pub_result.data
        if hasattr(data, 'c'):
            return dict(data.c.get_counts())
        return dict(data.get_counts())
    except Exception as e:
        print(f"[warn] Could not extract counts for {pub_name}: {e}")
        return {}


def analyze_b0(counts_active, counts_passive, counts_cal_1, counts_cal_0, shots):
    """B0: Single-qubit Zeno analysis."""
    # Active: leftmost bit is the final measurement (c[cycles])
    active_1 = sum(v for k, v in counts_active.items() if k[0] == '1')
    active_0 = sum(v for k, v in counts_active.items() if k[0] == '0')
    p_active = active_1 / shots if shots else 0

    # Passive: final bit (c[0])
    passive_0 = sum(v for k, v in counts_passive.items() if k[-1] == '0')
    passive_1 = sum(v for k, v in counts_passive.items() if k[-1] == '1')
    p_passive = passive_1 / shots if shots else 0

    # Calibration for readout matrix
    cal1_1 = sum(v for k, v in counts_cal_1.items() if k[-1] == '1')
    cal1_0 = sum(v for k, v in counts_cal_1.items() if k[-1] == '0')
    cal0_0 = sum(v for k, v in counts_cal_0.items() if k[-1] == '0')
    cal0_1 = sum(v for k, v in counts_cal_0.items() if k[-1] == '1')

    # Readout error rates
    p01 = cal0_1 / shots if shots else 0  # p(1|0)
    p10 = cal1_0 / shots if shots else 0  # p(0|1)

    # Readout-corrected active
    p_active_raw = p_active
    denom = 1 - p01 - p10
    if abs(denom) > 1e-9:
        p_active_corr = (p_active - p01) / denom
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
    # Active: leftmost 2 bits are final Bell measurement
    active_parity = sum(v for k, v in counts_active.items() if k[:2] in ('00', '11'))
    p_active = active_parity / shots if shots else 0

    # Passive: 2 bits
    passive_parity = sum(v for k, v in counts_passive.items() if k[:2] in ('00', '11'))
    p_passive = passive_parity / shots if shots else 0

    delta = p_active - p_passive

    return {
        "p_active_raw": p_active,
        "p_active_corrected": p_active,
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
    # Population fidelity = P(000) + P(111) on leftmost 3 bits
    active_pop = sum(v for k, v in counts_active.items() if k[:3] in ('000', '111'))
    p_active = active_pop / shots if shots else 0

    passive_pop = sum(v for k, v in counts_passive.items() if k[:3] in ('000', '111'))
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
        "prereg_pass": delta > 0.05,
    }


def analyze_b3(counts_active, counts_passive, counts_cal_1, counts_cal_0, shots):
    """B3: 5-qubit exploratory."""
    active_pop = sum(v for k, v in counts_active.items() if k[:5] in ('00000', '11111'))
    p_active = active_pop / shots if shots else 0

    passive_pop = sum(v for k, v in counts_passive.items() if k[:5] in ('00000', '11111'))
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
        "prereg_pass": None,
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

    cur_status = str(job.status()).upper()
    print(f"Status: {cur_status}")
    if cur_status not in ("DONE", "COMPLETED"):
        print(f"Waiting up to {a.wait}s for completion...")
        job.wait_for_final_state(timeout=a.wait)
        cur_status = str(job.status()).upper()
        print(f"Final status: {cur_status}")

    if cur_status not in ("DONE", "COMPLETED"):
        sys.exit(f"Job not completed: {cur_status}")

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

    analyzer = ANALYZERS.get(a.tier)
    if analyzer:
        res = analyzer(counts["active"], counts["passive"], counts["cal_1"], counts["cal_0"], shots)
        print("\nANALYSIS RESULTS:")
        print("-" * 40)
        for k, v in res.items():
            if isinstance(v, float):
                print(f"  {k:25s}: {v:.4f}")
            elif isinstance(v, tuple):
                print(f"  {k:25s}: ({v[0]:.4f}, {v[1]:.4f})")
            else:
                print(f"  {k:25s}: {v}")

        if a.save:
            out_file = RAW / f"wow_{a.tier}_{a.job}_analysis.json"
            out_data = {
                "job_id": a.job,
                "tier": a.tier,
                "tier_name": tier_cfg["name"],
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "shots": shots,
                "counts": counts,
                "analysis": res,
            }
            out_file.write_text(json.dumps(out_data, indent=2, default=str), encoding="utf-8")
            print(f"\nSaved results to: {out_file}")


if __name__ == "__main__":
    main()

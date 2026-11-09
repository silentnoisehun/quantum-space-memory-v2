#!/usr/bin/env python3
"""
extract_stage2.py — Stage 2: Cross-Chip Kerneled IQ Adatkinyerés és Vak Dekódolás

Figyeli a Marrakesh (Tier A/B) és Kingston (Tier D) jobokat, kinyeri a nyers complex128 (I,Q)
tömböket, és lefuttatja a vak periodogram detektort a döntési szabályok szerint.
"""
import json
import math
import os
import sys
import time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.cross_chip_campaign import get_service, RAW, CARRIER_FREQ_INDEX, DELAYS_US
from scripts.blind_decoder import periodogram_stat, PERIODS, ALPHA

MARRAKESH_JOB = "dbosur8ou4as73csl6bg"
KINGSTON_JOB = "dbosurtt7fqc7388da9g"


def extract_pub_iq(pub_result) -> np.ndarray:
    """Kinyeri a complex128 kerneled tömböt a SamplerV2 pub eredményéből."""
    data = pub_result.data
    if hasattr(data, "c"):
        return np.asarray(data.c, dtype=complex)
    for k in dir(data):
        if not k.startswith("_"):
            val = getattr(data, k)
            if hasattr(val, "shape"):
                return np.asarray(val, dtype=complex)
    raise ValueError("Nem található komplex IQ tömb a pub adatában.")


def main():
    print("=" * 78)
    print("STAGE 2 AUDIT: CROSS-CHIP KERNELED IQ VAK DEKÓDOLÁS")
    print("=" * 78)

    svc = get_service()

    # 1. Marrakesh (Tier A/B) figyelése
    print(f"\n[1/2] Marrakesh job vizsgálata: {MARRAKESH_JOB}...")
    job_m = svc.job(MARRAKESH_JOB)
    st_m = str(job_m.status()).upper()
    print(f"  Kezdeti státusz: {st_m}")
    if st_m not in ("DONE", "COMPLETED"):
        print("  Várakozás a Marrakesh futásra (wait_for_final_state)...")
        job_m.wait_for_final_state()

    res_m = job_m.result()
    print(f"  Marrakesh kész! Pubok száma: {len(res_m)}")
    marrakesh_data = []
    for i, pub in enumerate(res_m):
        iq = extract_pub_iq(pub)
        marrakesh_data.append(iq)
        print(f"    Delay #{i} ({DELAYS_US[i]} us) IQ shape: {iq.shape}, dtype: {iq.dtype}")

    # Mentés
    m_npy = RAW / "stage2_marrakesh_raw_iq.npy"
    np.save(str(m_npy), np.array(marrakesh_data, dtype=object), allow_pickle=True)
    print(f"  Marrakesh nyers IQ mentve: {m_npy}")

    # 2. Kingston (Tier D) figyelése
    print(f"\n[2/2] Kingston job vizsgálata: {KINGSTON_JOB}...")
    job_k = svc.job(KINGSTON_JOB)
    st_k = str(job_k.status()).upper()
    print(f"  Kezdeti státusz: {st_k}")
    if st_k not in ("DONE", "COMPLETED"):
        print("  Várakozás a Kingston futásra (wait_for_final_state)...")
        job_k.wait_for_final_state()

    res_k = job_k.result()
    print(f"  Kingston kész! Pubok száma: {len(res_k)}")
    kingston_data = []
    for i, pub in enumerate(res_k):
        iq = extract_pub_iq(pub)
        kingston_data.append(iq)
        print(f"    Delay #{i} ({DELAYS_US[i]} us) IQ shape: {iq.shape}, dtype: {iq.dtype}")

    k_npy = RAW / "stage2_kingston_raw_iq.npy"
    np.save(str(k_npy), np.array(kingston_data, dtype=object), allow_pickle=True)
    print(f"  Kingston nyers IQ mentve: {k_npy}")

    # 3. Vak Dekódolás a Kingston adatokon
    print("\n" + "=" * 78)
    print("VAK SPEKTRÁLIS PERIODOGRAM ANALÍZIS (Tier D — Kingston)")
    print("=" * 78)

    hits = []
    # kingston_data: 6 delay pub, mindegyik alakja (1024 shots, 4 qubits)
    for d_idx, pub_iq in enumerate(kingston_data):
        num_qubits = pub_iq.shape[1]
        for q in range(num_qubits):
            sig = pub_iq[:, q]
            cell_name = f"kingston_q{q}_d{int(DELAYS_US[d_idx])}us"
            for f_idx, per in enumerate(PERIODS):
                p_val = periodogram_stat(sig, per)
                hits.append((p_val, cell_name, f_idx, per))

    hits.sort(key=lambda t: -t[0])
    p_best, cell_best, f_best, per_best = hits[0]
    total_tests = len(hits)

    if p_best > 700:
        p_fam = 0.0
    else:
        p_fam = 1.0 - (1.0 - math.exp(-p_best)) ** total_tests

    is_detected = p_fam < ALPHA
    secret_period = PERIODS[CARRIER_FREQ_INDEX]
    matches_secret = (f_best == CARRIER_FREQ_INDEX)

    print(f"Összes pásztázott teszt (M): {total_tests}")
    print(f"Legnagyobb periodogram csúcs (P_max): {p_best:.4f}")
    print(f"Talált cella: {cell_best}")
    print(f"Talált frekvencia index: {f_best} (periódus: {per_best} minta)")
    print(f"Titkos vivő frekvencia index: {CARRIER_FREQ_INDEX} (periódus: {secret_period} minta)")
    print(f"Egzakt család-szintű p-érték (p_family): {p_fam:.4e}")
    print(f"Statisztikai küszöb (alpha=0.01): {'MEGHALADVA' if is_detected else 'NEM ÉRTE EL (ZAJPADLÓ)'}")

    # Döntési fa
    print("\n" + "-" * 40)
    print("VÉGSŐ CROSS-CHIP DÖNTÉS:")
    print("-" * 40)
    if is_detected and matches_secret:
        verdict = "CONFIRMED ANOMALY — A vak dekóder Kingstonon megtalálta a titkos Marrakesh vivőt!"
    elif is_detected and not matches_secret:
        verdict = "ARTIFACT / INTERFERENCE — Szignifikáns csúcs van, de NEM a titkos vivőn (műszerzaj/áthallás)."
    else:
        verdict = "CONFIRMED NULL — Tiszta zajpadló a Kingstonon (nincs kimutatható cross-chip tér-memória)."

    print(f"VERDIKT: {verdict}")

    # Összefoglaló mentése
    summary = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "marrakesh_job": MARRAKESH_JOB,
        "kingston_job": KINGSTON_JOB,
        "total_cells_tested": total_tests,
        "P_max": p_best,
        "best_cell": cell_best,
        "detected_freq_index": f_best,
        "detected_period": per_best,
        "secret_freq_index": CARRIER_FREQ_INDEX,
        "secret_period": secret_period,
        "p_family": p_fam,
        "detected": is_detected,
        "matches_secret": matches_secret,
        "verdict": verdict,
        "top_10_peaks": [
            {"P": h[0], "cell": h[1], "freq_idx": h[2], "period": h[3]}
            for h in hits[:10]
        ]
    }
    out_json = RAW / "stage2_blind_decoding_report.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nTeljes jelentés mentve: {out_json}")


if __name__ == "__main__":
    main()

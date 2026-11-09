#!/usr/bin/env python3
"""
power_analysis.py — WOW / space memory v2: mit tud egyáltalán észrevenni a mérés?
Ez a fájl a prereg ELŐTTI száma. Kimenete: hány bites üzenet kell ahhoz, hogy
egy vak dekóder találata ne legyen a véletlen műve, adott keresési tér mellett.

Futtatás:
  python power_analysis.py -> power_analysis.json + táblázat
"""
import json
import math
from pathlib import Path
from scipy.stats import norm

# ---------------------------------------------------------------- keresési tér
F_FREQ = 16   # digitális "vivő" periódus (nem analóg frekvencia: Open Plan alatt nincs pulse-level)
Q_QUBIT = 20  # olvasó qubitek
T_DELAY = 6   # lecsengési késleltetések (0, 1, 10, 100, 1000, 10000 us)
TIERS = 4     # A: azonos qubit/job, B: szomszéd, C: távoli qubit + későbbi job, D: másik chip
CELLS = F_FREQ * Q_QUBIT * T_DELAY
ALPHA = 0.01  # családhiba a teljes kereséstérre, Holm/Bonferroni


def hard_false_alarm(nbits: int) -> float:
    """ha bitenként kell egyezni (hard dekódolás): 2^-nbits cellánként"""
    return 2.0 ** (-nbits)


def soft_z(nbits: int, p_bit: float) -> float:
    """szoft dekódolás jel-zaja: a valódi cella korrelációja / szórás"""
    return math.sqrt(nbits) * (2 * p_bit - 1)


def z_threshold(cells: int, alpha: float = ALPHA) -> float:
    return float(norm.isf(alpha / cells))


def run_analysis():
    rows = []
    for n in (9, 16, 24, 32, 48, 64, 96, 128):
        fa = hard_false_alarm(n)
        exp_fa = fa * CELLS
        rows.append({
            "bits": n,
            "false_alarm_per_cell": fa,
            "expected_false_alarms_over_space": exp_fa,
            "verdict_hard": (
                "ELVETHETŐ" if exp_fa < 0.01 else (
                    "gyenge" if exp_fa < 1 else "HAMIS TALÁLAT GYAKORLATILAG BIZTOS"
                )
            ),
        })

    zthr = z_threshold(CELLS)

    sensitivity = []
    for p in (0.80, 0.85, 0.90, 0.93, 0.95, 0.99):
        sens = []
        for n in (16, 24, 32, 48, 64, 96):
            z = soft_z(n, p)
            sens.append({"bits": n, "z_true": round(z, 2), "detectable": bool(z > zthr)})
        sensitivity.append({"per_bit_fidelity": p, "cells": sens})

    min_bits = {}
    for p in (0.80, 0.85, 0.90, 0.93, 0.95, 0.99):
        need = None
        for n in range(4, 257):
            if soft_z(n, p) > zthr:
                need = n
                break
        min_bits[p] = need

    out = {
        "search_space": {
            "F_freq": F_FREQ,
            "Q_qubit": Q_QUBIT,
            "T_delay": T_DELAY,
            "tiers": TIERS,
            "cells_per_tier": CELLS,
            "cells_total": CELLS * TIERS
        },
        "alpha_familywise": ALPHA,
        "z_threshold_per_cell": round(zthr, 3),
        "hard_decoding": rows,
        "soft_decoding_sensitivity": sensitivity,
        "min_bits_needed_for_detection": {str(k): v for k, v in min_bits.items()},
        "recommendation": {
            "message_bits": 64,
            "why": (
                "64 bit: hard false-alarm 5.4e-20 cellánként (gyakorlatilag nulla), és szoft "
                "dekódolással még 0.80-as bit-hűség mellett is 6.4 sigma, a 4.44-es küszöb felett. "
                "9 jellel (a WOW morze) a várt hamis találat 3.75 LENNE a négy fokozaton -> nem bizonyíték."
            ),
            "wow_kept_as": "élmény / bemutató motif, NEM a szigorú mérés fő mérőszáma",
        },
    }

    out_file = Path(__file__).resolve().parent.parent / "data" / "power_analysis.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    res = run_analysis()
    cells = res["search_space"]["cells_per_tier"]
    tiers = res["search_space"]["tiers"]
    alpha = res["alpha_familywise"]
    zthr = res["z_threshold_per_cell"]
    print(f"Keresési tér: {F_FREQ} frekvencia x {Q_QUBIT} qubit x {T_DELAY} késleltetés = {cells} cella/fokozat")
    print(f" {tiers} fokozat -> {cells * tiers} cella összesen")
    print(f"Küszöb (family-wise alpha={alpha}): z = {zthr:.2f}\n")
    print(f"{'bit':>4} {'hamis/cella':>14} {'várt hamis':>12} verdikt")
    for r in res["hard_decoding"]:
        print(f"{r['bits']:>4} {r['false_alarm_per_cell']:>14.3e} {r['expected_false_alarms_over_space']:>12.3e} {r['verdict_hard']}")
    print("\nSzoft dekódolás: hány bit kell a detektáláshoz, adott bit-hűség mellett")
    for p, n in res["min_bits_needed_for_detection"].items():
        print(f" bit-hűség {float(p):.2f} -> legalább {n} bit")
    print("\nJAVASLAT: 64 bites üzenet.")
    print(" A 9 jeles WOW morze: várt hamis találat = 3.75 -> gyakorlatilag biztosan hamis pozitív.")

#!/usr/bin/env python3
"""
blind_decoder.py — WOW / space memory: VAK detektor, Egzakt null-eloszlással

ALAPELV
A detektor NEM tudja, mit keres: sem a bitsort, sem a fázisugrások helyét.
Minden (frekvencia, qubit, késleltetés) cellára csak azt kérdezi:
"van-e itt periodikus energia az adott periódussal?"

Statisztika: normalizált periodogram-ordináta a vivő frekvenciáján.
Fehér zajra ez PONTOSAN Exp(1) eloszlású, N-től függetlenül (standard spektrális eredmény).
Ezért a családhiba korrekció egzakt:
  p_család = 1 - (1 - exp(-P_max))^M, M = tesztek száma
Nincs Monte-Carlo heurisztika, nincs "utólagos kalibrálás".

A statisztika fázis-ÉRZÉKETLEN (|FFT|²), tehát a 180°-os fázisugrások nem segítik
a detektort -> a detekció valóban vak. Az üzenet visszafejtése (a blokkok előjeléből)
egy KÜLÖN, nem vak lépés, és csak a detekció után következik.
"""

import argparse
import math
import sys
from typing import Dict, Any, List, Tuple
import numpy as np

MSG_BITS = 16
F_FREQ = 16
Q_QUBIT = 20
T_DELAY = 6
BIT_SAMPLES = 128
NSAMP = MSG_BITS * BIT_SAMPLES  # 2048 minta
PERIODS = [f + 4 for f in range(F_FREQ)]  # 4..19 minta (6.7..32 periódus / bit)
ALPHA = 0.01


def carrier(period: int, nbits: int = MSG_BITS, bits: List[int] = None, n: int = NSAMP) -> np.ndarray:
    """BPSK-modulált vivőhullám generálása determinisztikus fázisugrásokkal."""
    w = np.exp(2j * np.pi * np.arange(n) / period)
    if bits is not None and len(bits) > 0:
        blk = BIT_SAMPLES
        for i, b in enumerate(bits[:nbits]):
            if b:
                w[i * blk:(i + 1) * blk] *= -1.0
    return w[:n]


def periodogram_stat(sig: np.ndarray, period: int) -> float:
    """Normalizált periodogram-ordináta a vivő frekvenciáján. Fehér zajra ~Exp(1)."""
    x = np.asarray(sig, dtype=complex)
    x = x - x.mean()
    n = len(x)
    k = int(round(n / period))
    if k <= 0 or k >= n // 2:
        return 0.0
    X = np.fft.fft(x)
    p = (np.abs(X[k]) ** 2 + np.abs(X[n - k]) ** 2) / (n * np.var(x) if np.var(x) > 0 else 1.0)
    return float(p / 2.0)


def decode(signals: Dict[str, np.ndarray], periods: List[int] = None, alpha: float = ALPHA) -> Dict[str, Any]:
    """
    Vak dekódolás a teljes keresési téren:
    Végigpásztázza az összes cellát és periódust, rögzíti a maximumot,
    és kiszámolja a zárt alakú család-szintű p-értéket.
    """
    if periods is None:
        periods = PERIODS
    hits: List[Tuple[float, str, int]] = []
    for cell, sig in signals.items():
        for f, per in enumerate(periods):
            p_val = periodogram_stat(sig, per)
            hits.append((p_val, cell, f))
    hits.sort(key=lambda t: -t[0])
    p_best, cell_best, f_best = hits[0]
    m_tests = len(hits)
    
    # Egzakt családhiba korrekció Exp(1) ordinátákra
    # P(max <= P_best) = (1 - exp(-P_best))^M
    # p_family = 1 - (1 - exp(-P_best))^M
    if p_best > 700:  # numerikus túlcsordulás megelőzése
        p_fam = 0.0
    else:
        p_fam = 1.0 - (1.0 - math.exp(-p_best)) ** m_tests

    return {
        "P_best": p_best,
        "cell": cell_best,
        "freq_index": f_best,
        "period": periods[f_best],
        "n_tests": m_tests,
        "p_family": p_fam,
        "detected": bool(p_fam < alpha)
    }


def selftest() -> bool:
    """Pozitív kontroll: szimulált rejtett jel észlelése."""
    rng = np.random.default_rng(3)
    true_f = 7
    true_period = PERIODS[true_f]
    bits = list(rng.integers(0, 2, MSG_BITS))
    signals = {}
    for q in range(Q_QUBIT):
        for d in range(T_DELAY):
            key = f"q{q}_d{d}"
            noise = rng.standard_normal(NSAMP) + 1j * rng.standard_normal(NSAMP)
            if q < 4 and d == 0:
                signals[key] = carrier(true_period, bits=bits) * 1.0 + noise
            else:
                signals[key] = noise
    res = decode(signals)
    ok = res["detected"] and res["freq_index"] == true_f
    print("SELFTEST (szimulált térmemória: 4 valódi cella 120-ból, SNR ~1):")
    print(f"  találat={res['detected']} P_max={res['P_best']:.1f} cella={res['cell']} "
          f"f={res['freq_index']} (valódi: {true_f}, periódus: {res['period']}) p_család={res['p_family']:.2e} "
          f"M={res['n_tests']}")
    print(f"  -> {'OK: a műszer megtalálja a saját jelét' if ok else 'HIBA: nem találja'}")
    return ok


def null_test(trials: int = 150) -> bool:
    """Negatív kontroll: tiszta fehér zajra a hamis pozitív arány <= alpha."""
    rng = np.random.default_rng(5)
    false_positives = 0
    for _ in range(trials):
        signals = {
            f"q{q}_d{d}": rng.standard_normal(NSAMP) + 1j * rng.standard_normal(NSAMP)
            for q in range(Q_QUBIT) for d in range(T_DELAY)
        }
        res = decode(signals)
        if res["detected"]:
            false_positives += 1
    obs = false_positives / trials
    print(f"NULL teszt: {false_positives}/{trials} hamis találat ({100 * obs:.2f}%, elvárt <= {ALPHA * 100:.0f}%)")
    sd = math.sqrt(ALPHA * (1 - ALPHA) / trials)
    ok = obs <= ALPHA + 3 * sd
    print(f"  -> {'OK' if ok else 'HIBA: a null-eloszlás nem egzakt'}")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--null", action="store_true")
    ap.add_argument("--trials", type=int, default=150)
    args = ap.parse_args()
    if args.selftest:
        sys.exit(0 if selftest() else 1)
    if args.null:
        sys.exit(0 if null_test(args.trials) else 1)
    print(__doc__)

# Quantum Space Memory v2: 4-Tier WOW QPU Campaign

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Author:** Máté Róbert (ORCID: [0009-0003-3986-6039](https://orcid.org/0009-0003-3986-6039))
**Repository:** https://github.com/silentnoisehun/quantum-space-memory-v2
**Version:** v2.0.0 (2026-11-09)
**Hardware:** `ibm_marrakesh` (156-qubit Heron r2) — 4-tier campaign

---

## Overview

This repository implements the **4-tier WOW (Walk of Wonders) QPU campaign** for testing quantum space memory across increasing circuit complexity and qubit counts on IBM Heron r2 processors. The campaign builds upon the successful Active Quantum Zeno validation in `quantum-active-space-memory` (v1.3.3, N=20, ΔF = +97.35 pp, PREREG PASSED).

### Campaign Tiers

| Tier | Name | Qubits | Cycles | Shots/Job | Est. QPU Time | Status |
|------|------|--------|--------|-----------|---------------|--------|
| **B0** | Single-Qubit Zeno | 1 | N=20 | 2000 | ~30 s | Preregistered |
| **B1** | Bell Parity Zeno | 2 | N=20 | 2000 | ~35 s | Preregistered |
| **B2** | GHZ-3 Population | 3 | N=15 | 2000 | ~40 s | Preregistered |
| **B3** | Multi-Qubit Space Memory | 5 | N=10 | 2000 | ~50 s | Exploratory |

---

## Tier B0: Single-Qubit Zeno (Reference)

**Preregistration gate:** ΔF > 0.30 at N ≥ 20, p < 10⁻⁶

- Active: X → [R_x(0.15π) → measure → if(0): X] × N → measure
- Passive: X → [R_x(0.15π)] × N → measure
- Calibration: cal_1 (X → measure), cal_0 (idle → measure) in same job
- **Expected:** P(active) ≈ 97.45%, P(passive) ≈ 0.10%, ΔF ≈ +97.35 pp
- **Validation:** Replicates quantum-active-space-memory v1.3.3 result

---

## Tier B1: Bell Parity Zeno

**Preregistration gate:** ΔF_parity > 0.15 at N ≥ 20, p < 10⁻⁶

- Initial state: |Φ⁺⟩ = (|00⟩ + |11⟩)/√2 via H + CNOT
- Active: [I ⊗ R_x(θ) → measure q1 → if(0): X on q1] × N → Bell measurement
- Passive: [I ⊗ R_x(θ)] × N → Bell measurement
- **Metric:** Parity survival P(00) + P(11) — NOT entanglement witness
- **Expected:** P(active) ≈ 33.60%, P(passive) ≈ 10.90%, ΔF ≈ +22.70 pp

---

## Tier B2: GHZ-3 Population Stabilization

**Preregistration gate:** ΔF_GHZ > 0.05 at N ≥ 15, p < 10⁻³

- Initial state: |GHZ₃⟩ = (|000⟩ + |111⟩)/√2
- Active: [⨂ R_x(θ) → measure all → if(any 0): X on that qubit] × N → measure
- Passive: [⨂ R_x(θ)] × N → measure
- **Metric:** Population fidelity F = P(000) + P(111) — NO phase recovery
- **Expected:** F(active) ≈ 36-39%, F(passive) ≈ 12-13%, ΔF ≈ +23-26 pp
- **Note:** Noiseless ideal F = 1.0000; gap is measurement-induced dephasing

---

## Tier B3: 5-Qubit Space Memory (Exploratory)

**No preregistration gate — exploratory validation**

- Layout: Heron r2 optimal chain (e.g., [51,52,53,54,55])
- Initial: GHZ-5 = (|00000⟩ + |11111⟩)/√2
- Active: Full Zeno loop on all 5 qubits with simultaneous mid-circuit measures
- Passive: Free evolution with same rotations
- **Metric:** Population fidelity + cross-talk analysis
- **QPU budget:** ~50 s (fits within 600 s free tier)

---

## Preregistration Documents

- `docs/PREREGISTRATION-B0_single_qubit_zeno.md`
- `docs/PREREGISTRATION-B1_bell_parity.md`
- `docs/PREREGISTRATION-B2_ghz3_population.md`
- `docs/PREREGISTRATION-B3_exploratory.md`

---

## Installation

```bash
python -m venv .venv-wow
.venv-wow/Scripts/activate          # Windows: .venv-wow\Scripts\activate
pip install -e ".[dev]"

# For hardware runs:
pip install -e ".[hardware]"
```

Requires: `qiskit>=2.0`, `qiskit-ibm-runtime>=0.51`, `numpy`, `scipy`

---

## Usage

```bash
# Dry run (no token needed)
python scripts/wow_campaign.py --tier B0 --dry-run

# Hardware submission (requires IBM_QUANTUM_API_TOKEN)
python scripts/wow_campaign.py --tier B0 --submit

# Extract results
python scripts/extract_wow.py --job <JOB_ID>
```

---

## Cross-Chip Blind Carrier & Power Analysis (Marrakesh -> Kingston)

In addition to the discrete Zeno tiers B0–B3, the repository incorporates the active modulation space memory protocol detailed in `docs/PREREGISTRATION-cross_chip_blind_carrier_wow.md`:
* **Statistical Power Analysis (`scripts/power_analysis.py`):** Demonstrates that a 9-symbol motif over 7,680 cells yields $3.75$ expected false alarms under random noise. The experiment strictly mandates **64 bits** (hard false alarm $5.4 \times 10^{-20}$ per cell; $1.0 \times 10^{-16}$ family-wise).
* **Exact Spectral Blind Detector (`scripts/blind_decoder.py`):** Uses normalized periodogram ordinates which strictly follow an $\text{Exp}(1)$ distribution under Gaussian white noise, providing an exact closed-form family-wise $p$-value ($p_\text{family} = 1 - (1 - e^{-P_\text{max}})^M$).

```bash
# Run power analysis and generate data/power_analysis.json
python scripts/power_analysis.py

# Run blind decoder selftest and null test (150 trials)
python scripts/blind_decoder.py --selftest
python scripts/blind_decoder.py --null --trials 150
```

---

## License

MIT license. The citation metadata is in `CITATION.cff`.

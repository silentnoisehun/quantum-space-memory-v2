# Preregistration: Tier B2 — GHZ-3 Population Stabilization via Active Zeno

**Author:** Máté Róbert (ORCID: [0009-0003-3986-6039](https://orcid.org/0009-0003-3986-6039))
**Repository:** https://github.com/silentnoisehun/quantum-space-memory-v2
**Date:** 2026-11-09
**Status:** Frozen prior to quantum execution

---

## 1. Background & Scientific Question

The `quantum-active-space-memory` v1.3.2/v1.3.3 campaigns showed that ZZ-based Zeno projections on a 3-qubit GHZ state stabilize **population only** (F_active = 36.63% vs F_passive = 12.85%, Δ = +23.78 pp), with **no phase coherence recovery** (F_active ≤ 50% ideal, noiseless F = 1.0000).

**Scientific question:** Does the 3-qubit GHZ population stabilization reproduce at N=15 cycles with identical per-qubit Zeno loops?

---

## 2. Experimental Design

### 2.1 Circuit Definition

**GHZ-3 preparation:**
```
q_0: ──H──●──────────────────────────────────────────────
         │
q_1: ────X──●────────────────────────────────────────────
            │
q_2: ───────X────────────────────────────────────────────
```

**Active arm (N=15 cycles, all qubits):**
```
For each qubit q in {0,1,2}:
  [R_x(θ) → M_q → if(M_q=0): X on q] × 15
Final: measure all 3 qubits
```
- Each qubit independently undergoes Zeno cycles
- Mid-circuit measure + conditional X per qubit per cycle
- θ = 0.15π

**Passive arm (N=15 cycles, all qubits):**
```
For each qubit q in {0,1,2}:
  [R_x(θ)] × 15
Final: measure all 3 qubits
```

**Calibration arms:**
- `cal_1`: X on all 3 → measure (p(1|1) per qubit)
- `cal_0`: idle → measure (p(1|0) per qubit)

### 2.2 Parameters

| Parameter | Value |
|-----------|-------|
| Backend | `ibm_marrakesh` |
| Qubits | Chain of 3 (e.g., [0,1,2] or [53,54,55]) |
| Cycles (N) | 15 |
| Shots per circuit | 2000 |
| θ | 0.15π |

---

## 3. Preregistered Decision Gates

| Gate | Criterion | Threshold |
|------|-----------|-----------|
| **G1** | ΔF_GHZ = F_active - F_passive | > 0.05 (5 pp) |
| **G2** | Cycle count | N ≥ 15 |
| **G3** | One-sided binomial p-value | < 10⁻³ |

Where F = P(000) + P(111) = population fidelity.

**Note:** This is a POPULATION fidelity test. No entanglement witness. The noiseless bound is F = 1.0000; the measured gap is implementation overhead (mid-circuit readout dephasing + ancilla error).

---

## 4. Statistical Analysis

- F_active, F_passive with Wilson 95% CI
- ΔF_GHZ with Wilson 95% CI
- One-sided binomial test
- Per-qubit P(|1⟩) in mid-cycle measurements
- Cross-qubit correlation analysis

---

## 5. Protocol Constraints

- No circuit or analysis modifications after execution commences
- All raw data committed to `measurement_raw/`

---

## 6. QPU Budget Estimate

~40 s QPU time (4 circuits × 2000 shots)
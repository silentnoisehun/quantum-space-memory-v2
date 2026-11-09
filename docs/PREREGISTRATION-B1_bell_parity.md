# Preregistration: Tier B1 — Bell Parity Quantum Zeno Dynamics

**Author:** Máté Róbert (ORCID: [0009-0003-3986-6039](https://orcid.org/0009-0003-3986-6039))
**Repository:** https://github.com/silentnoisehun/quantum-space-memory-v2
**Date:** 2026-11-09
**Status:** Frozen prior to quantum execution

---

## 1. Background & Scientific Question

The `quantum-active-space-memory` v1.3.2/v1.3.3 campaigns demonstrated that ZZ-based Zeno projections on a Bell pair yield **parity survival** (P(00)+P(11)), NOT entanglement preservation. The active arm reached 33.60% vs 10.90% passive (Δ = +22.70 pp), but this is below the 50% separability threshold for this quantity.

**Scientific question:** Can the Bell parity Zeno protection be reproduced with identical circuit parameters on a fresh `ibm_marrakesh` job?

---

## 2. Experimental Design

### 2.1 Circuit Definition

**Bell state preparation (identical for both arms):**
```
q_0: ──H──●──────────────────────────────────────────────────────
         │
q_1: ────X──R_x(θ)──M──c0──(if c0=0: X on q1)──R_x(θ)──M──c1──(if c1=0: X on q1)── ... ×20 ──M─c20──
```

- q_0: remains in superposition (no mid-circuit measures)
- q_1: undergoes Zeno cycles with mid-circuit measure + conditional X
- Final: Bell-basis measurement on both qubits

**Active arm (N=20 cycles on q_1):**
- Initial: |Φ⁺⟩ = (|00⟩ + |11⟩)/√2 via H(q0) + CNOT(q0→q1)
- Per cycle: R_x(0.15π) on q_1 → measure q_1 → if(0): X on q_1
- Final: CNOT(q0→q1) + H(q0) + measure both

**Passive arm (N=20 cycles on q_1):**
- Initial: |Φ⁺⟩ = (|00⟩ + |11⟩)/√2
- Per cycle: R_x(0.15π) on q_1 (NO mid-circuit measure)
- Final: CNOT(q0→q1) + H(q0) + measure both

**Calibration arms (same job):**
- `cal_1`: X on q_1 → measure both (p(1|1) for q_1)
- `cal_0`: idle → measure both (p(1|0) for q_1)

### 2.2 Parameters

| Parameter | Value |
|-----------|-------|
| Backend | `ibm_marrakesh` |
| Qubits | Adjacent pair (e.g., [0,1] or [53,54]) |
| Cycles (N) | 20 |
| Shots per circuit | 2000 |
| θ | 0.15π |

---

## 3. Preregistered Decision Gates

| Gate | Criterion | Threshold |
|------|-----------|-----------|
| **G1** | ΔF_parity = P_active(parity) - P_passive(parity) | > 0.15 (15 pp) |
| **G2** | Cycle count | N ≥ 20 |
| **G3** | One-sided binomial p-value | < 10⁻⁶ |

Where parity survival = P(00) + P(11) after Bell-basis measurement.

**Note:** This is a parity survival test. The separability bound for P(00)+P(11) is 50%. We do not claim entanglement preservation.

---

## 4. Statistical Analysis

- Parity survival: P(00) + P(11) with Wilson 95% CI
- ΔF_parity with Wilson 95% CI
- One-sided binomial test
- Per-cycle parity (if intermediate Bell measurements added)

---

## 5. Protocol Constraints

- No circuit or analysis modifications after execution commences
- All raw data committed to `measurement_raw/`

---

## 6. QPU Budget Estimate

~35 s QPU time (4 circuits × 2000 shots)
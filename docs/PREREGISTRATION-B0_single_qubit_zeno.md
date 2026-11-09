# Preregistration: Tier B0 — Single-Qubit Active Quantum Zeno Dynamics

**Author:** Máté Róbert (ORCID: [0009-0003-3986-6039](https://orcid.org/0009-0003-3986-6039))
**Repository:** https://github.com/silentnoisehun/quantum-space-memory-v2
**Date:** 2026-11-09
**Status:** Frozen prior to quantum execution

---

## 1. Background & Scientific Question

This tier replicates the core finding of `quantum-active-space-memory` v1.3.3 (job `dbokrbk4148s739t68ig` on `ibm_marrakesh`): **Active Quantum Zeno dynamic feedforward stabilizes a transmon qubit against free decay for 20 sequential cycles**, achieving ΔF = +97.35 pp (p < 10⁻¹⁵).

**Scientific question:** Is the single-qubit Zeno protection effect reproducible on a fresh job submission with identical circuit parameters?

---

## 2. Experimental Design

### 2.1 Circuit Definition

**Active arm (N=20 cycles):**
```
q_0: ──X──R_x(θ)──M──c0──(if c0=0: X)──R_x(θ)──M──c1──(if c1=0: X)── ... ×20 ──M─c20──
```

- Initial: X gate prepares |1⟩
- Per cycle: R_x(0.15π) → measure → if outcome=0: conditional X
- Final: measurement in c[20]
- θ = 0.15π (calibrated coherent rotation)

**Passive arm (N=20 cycles):**
```
q_0: ──X──R_x(θ)──R_x(θ)── ... ×20 ──M─c0──
```
- Initial: X gate prepares |1⟩
- No mid-circuit measurements
- Final: measurement in c[0]

**Calibration arms (same job, same qubit):**
- `cal_1`: X → M (measures p(1|1))
- `cal_0`: idle → M (measures p(1|0))

### 2.2 Parameters

| Parameter | Value |
|-----------|-------|
| Backend | `ibm_marrakesh` (156-qubit Heron r2) |
| Qubit | Physical qubit 0 (or backend's best single qubit) |
| Cycles (N) | 20 |
| Shots per circuit | 2000 |
| θ | 0.15π |
| Calibration shots | 2000 each |

### 2.3 Circuit Hashes (for integrity)

Circuits serialized via QASM3, SHA-256 recorded at submission.

---

## 3. Preregistered Decision Gates

The experiment **passes** only if ALL three gates are satisfied:

| Gate | Criterion | Threshold |
|------|-----------|-----------|
| **G1** | ΔF = P_active - P_passive | > 0.30 (30 pp) |
| **G2** | Cycle count | N ≥ 20 |
| **G3** | One-sided binomial p-value | < 10⁻⁶ |

Where P_active = P(|1⟩) in active arm, P_passive = P(|1⟩) in passive arm.

---

## 4. Readout Calibration Resolution

The v1.3.1 anomaly (97.20% > 94.53% ceiling from daily calibration p(0|1)=5.47%) was resolved in v1.3.3 by **in-job calibration**:

- In-job p(0|1) = 0.45% (from `cal_1`)
- In-job p(1|0) = 0.15% (from `cal_0`)
- Readout ceiling = 1 - p(0|1) = 99.55%
- Corrected Q = 97.89% (within Wilson CI of raw 97.45%)

This tier **requires** in-job calibration arms in the same job submission.

---

## 5. Statistical Analysis

- Primary: P_active, P_passive with Wilson 95% CI
- ΔF with Wilson 95% CI
- One-sided binomial test (null: P_active = P_passive)
- Per-bit P(|1⟩) for active arm mid-cycle measurements (bits 0..18)
- Readout-corrected Q from calibration arms

---

## 6. Protocol Constraints

- No circuit or analysis modifications after execution commences
- All raw Qiskit job IDs, calibration snapshots, and full measurement counts committed to `measurement_raw/`
- Analysis via `scripts/extract_wow.py` (re-derivable from raw files)

---

## 7. QPU Budget Estimate

~30 s QPU time (4 circuits × 2000 shots × ~3 s/circuit on Heron r2)
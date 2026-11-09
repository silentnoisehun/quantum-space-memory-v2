# Exploratory Plan: Tier B3 — 5-Qubit Space Memory (No Preregistration Gate)

**Author:** Máté Róbert (ORCID: [0009-0003-3986-6039](https://orcid.org/0009-0003-3986-6039))
**Repository:** https://github.com/silentnoisehun/quantum-space-memory-v2
**Date:** 2026-11-09
**Status:** Exploratory — no pass/fail gate

---

## 1. Background & Scientific Question

This tier extends the Zeno loop to 5 qubits on the Heron r2 optimal chain. The goal is **exploratory validation** of multi-qubit space memory with simultaneous mid-circuit measurements, analyzing:
- Population fidelity scaling with qubit count
- Cross-talk effects during simultaneous mid-circuit measures
- QPU time budget utilization

**No preregistration gate** — this is exploratory. Results inform future preregistered campaigns.

---

## 2. Experimental Design

### 2.1 Circuit Definition

**GHZ-5 preparation (on optimal Heron chain):**
```
q_0: ──H──●──────────────────────────────────────────────
         │
q_1: ────X──●────────────────────────────────────────────
            │
q_2: ───────X──●─────────────────────────────────────────
               │
q_3: ──────────X──●──────────────────────────────────────
                  │
q_4: ─────────────X──────────────────────────────────────
```

**Active arm (N=10 cycles, all 5 qubits simultaneously):**
```
For each cycle 1..10:
  For each qubit q in {0,1,2,3,4}:
    R_x(θ) on q
  Barrier
  Measure all 5 qubits → c[cycle, q]
  For each qubit q:
    if c[cycle, q] = 0: X on q
Final: measure all 5 qubits
```
- θ = 0.15π
- Simultaneous mid-circuit measures across all 5 qubits
- Conditional X per qubit per cycle

**Passive arm (N=10 cycles, all 5 qubits):**
```
For each qubit q in {0,1,2,3,4}:
  [R_x(θ)] × 10
Final: measure all 5 qubits
```

**Calibration arms:**
- `cal_1`: X on all 5 → measure
- `cal_0`: idle → measure

### 2.2 Parameters

| Parameter | Value |
|-----------|-------|
| Backend | `ibm_marrakesh` |
| Qubits | Optimal Heron chain (e.g., [51,52,53,54,55]) |
| Cycles (N) | 10 |
| Shots per circuit | 2000 |
| θ | 0.15π |

---

## 3. Exploratory Metrics (No Pass/Fail)

| Metric | Description |
|--------|-------------|
| F_5qb | Population fidelity P(00000) + P(11111) |
| ΔF_5qb | F_active - F_passive |
| Per-qubit Zeno | P(|1⟩) per qubit in mid-cycle measures |
| Cross-talk | Correlation between simultaneous mid-circuit outcomes |
| QPU time | Total execution time vs. budget |

---

## 4. Analysis Plan

- Population fidelity with Wilson 95% CI
- Per-qubit Zeno protection comparison
- Cross-talk analysis: simultaneous vs. isolated mid-circuit outcomes
- Scaling trend: F vs. qubit count (1, 2, 3, 5 qubits from B0-B3)

---

## 5. Protocol Constraints

- All raw data committed to `measurement_raw/`
- QPU budget: ~50 s (fits within 600 s free tier)

---

## 6. QPU Budget Estimate

~50 s QPU time (4 circuits × 2000 shots × 5 qubits)
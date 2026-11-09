# PREREGISTRATION — Cross-Chip Blind Carrier & Space Memory v2

**Author:** Máté Róbert (ORCID: [0009-0003-3986-6039](https://orcid.org/0009-0003-3986-6039))  
**Repository:** https://github.com/silentnoisehun/quantum-space-memory-v2  
**Date:** 2026-11-09  
**Hardware:** `ibm_marrakesh` (Write) and `ibm_kingston` (Blind Read)  
**Companion code:** `scripts/power_analysis.py`, `scripts/blind_decoder.py`, `data/power_analysis.json`

---

## 1. Context & Motivation

Previous passive idle-chip investigations in `quantum-space-memory` and `quantum-pooled-holdout` (1 016 hardware jobs) yielded a strictly confirmed null ($p = 0.135$ meta-analysis). 

This protocol tests the **active modulation space hypothesis** formulated during the dialogue between Máté and Maya:
1. Information is actively modulated into a physical transmon carrier frequency.
2. A blind decoder scans across frequencies, qubits, and delays on a completely separate, uncoupled dilution refrigerator (`ibm_kingston`) without knowing the secret carrier or the message bits.
3. The claim is evaluated against a rigorous four-tier ladder to separate chip crosstalk from true cross-device effects.

---

## 2. Hardware Implementation of "Frequency" (IBM Open Plan)

Because IBM Open Plan does not provide microwave pulse-level OpenPulse access, modulation is synthesized digitally:
* **Carrier Detuning:** Synthesized digitally via discrete $R_z(\Delta\phi)$ gate increments where $\Delta\phi = 2\pi \cdot f_\text{emul} \cdot \tau$.
* **Phase Inversion (BPSK):** A $180^\circ$ phase flip ($R_z(\pi)$) encodes bit `1`, whereas identity ($I$) encodes bit `0`.
* **Time-Series Formation:** The time axis is realized across delays $\tau_k \in \{0, 1, 10, 100, 1000, 10000\}\,\mu\text{s}$ read in the $X$-basis via kerneled or projective state tomography.

---

## 3. Four-Tier Evaluation Ladder

| Tier | Location | Hardware | Expected Outcome | Role in Experiment |
|------|----------|----------|------------------|-------------------|
| **Tier A** | Same qubit, same job | `ibm_marrakesh` | $F \approx 0.90 - 1.00$ ($p < 10^{-6}$) | Positive instrument control (verifies write + read) |
| **Tier B** | Nearest-neighbor qubit, same job | `ibm_marrakesh` | Decaying with Manhattan distance | Physical crosstalk baseline |
| **Tier C** | Far qubit ($\ge 5$ hops), later job | `ibm_marrakesh` | Null floor | Local residual memory decay limit |
| **Tier D** | Independent chip | `ibm_kingston` | Null floor (or anomaly) | Cross-device space memory test |

**Decision Gates:**
* If **Tier A fails**, Tier D is invalid (instrument broken).
* If **Tier B** does not decay with distance, classical control crosstalk must be audited.
* **Tier D confirmed positive** ONLY IF:
  1. $p_\text{family} < 0.01$ under the exact $\text{Exp}(1)$ periodogram null.
  2. Identified carrier matches the committed secret hash.
  3. Tier C is simultaneously null.
  4. Kingston no-write negative control is null.

---

## 4. Statistical Power & Search Space

From `scripts/power_analysis.py`:
* **Search space:** 16 carrier periods $\times$ 20 qubits $\times$ 6 delay tiers $\times$ 4 tiers = 7 680 cells.
* **Family-wise Significance:** $\alpha = 0.01$ (Bonferroni / Holm adjusted threshold $z \approx 4.41$).
* **Message Length:** A 9-symbol WOW motif gives $3.75$ expected false alarms over this space (insufficient). Therefore, the rigorous test uses **64 bits**, where the false alarm probability per cell is $5.4 \times 10^{-20}$ ($1.0 \times 10^{-16}$ over the entire space).

---

## 5. Preregistration Manifest & Cryptographic Locks

Before QPU submission:
1. `sha256(salt | carrier_period | secret_bits | start_time_utc)` is committed to the repository log.
2. The blind decoder (`scripts/blind_decoder.py`) is locked and immutable.
3. Raw counts and kerneled measurement IQ outputs are archived without filtering.

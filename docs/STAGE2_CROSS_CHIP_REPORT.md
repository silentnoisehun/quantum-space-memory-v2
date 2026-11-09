# Stage 2: Cross-Chip Kerneled IQ Vak Dekódolási Jelentés

**Dátum (UTC):** 2026-11-09 15:11:40  
**Kísérletvezető:** Rongyász / Máté Róbert (ORCID: `0009-0003-3986-6039`)  
**Kód:** `scripts/cross_chip_campaign.py`, `scripts/extract_stage2.py`  
**Preregisztráció:** `docs/PREREGISTRATION-cross_chip_blind_carrier_wow.md`  

---

## 1. Hardveres Végrehajtás

| Paraméter | Adó (Tier A/B) | Vevő (Tier D — Vak) |
|---|---|---|
| **Kvantumprocesszor** | `ibm_marrakesh` (Heron r2) | `ibm_kingston` (Heron r2) |
| **Job ID** | `dbosur8ou4as73csl6bg` | `dbosurtt7fqc7388da9g` |
| **Állapot** | `DONE` | `DONE` |
| **Kiolvasási típus** | `kerneled` (`complex128`) | `kerneled` (`complex128`) |
| **Késleltetések ($\tau$)** | 0, 1, 10, 100, 1000, 10000 $\mu$s | 0, 1, 10, 100, 1000, 10000 $\mu$s |
| **Qubitek** | 2 db fizikai vivő-qubit | 4 db fizikai detektor-qubit |
| **Pubok száma** | 6 pub $\times$ 1024 shot $\times$ 2 qubit | 6 pub $\times$ 1024 shot $\times$ 4 qubit |
| **Nyers adatfájl** | `measurement_raw/stage2_marrakesh_raw_iq.npy` | `measurement_raw/stage2_kingston_raw_iq.npy` |

---

## 2. Vak Spektrális Periodogram Eredmények (Tier D — Kingston)

A preregisztrált vak detektor 16 diszkrét vivő-periódust pásztázott végig mind a 6 késleltetésre és mind a 4 detektor-qubitre ($M = 6 \times 4 \times 16 = 384$ független statisztikai teszt).

- **Összes tesztelt cella ($M$):** 384
- **Megfigyelt maximális periodogram csúcs ($P_\text{max}$):** **`4.9785`**
- **Legnagyobb zajcsúcs helye:** `kingston_q2_d100us`, frekvencia-index: `3` (periódus: `7` minta)
- **Titkos preregisztrált vivő frekvencia-index:** `7` (periódus: `11` minta)
- **Titkos vivő SHA-256 hash:** `7f0b6ac1315875de...`
- **Egzakt család-szintű p-érték ($p_\text{family}$):** **`0.9295`** ($92{,}95\%$)
- **Statisztikai küszöb ($\alpha = 0{,}01$):** **NEM ÉRTE EL (ZAJPADLÓ)**

### Top 5 Periodogram Csúcs a Kingston Hardveren:
1. $P = 4{,}9785$ (`kingston_q2_d100us`, freq=3, periódus=7)
2. $P = 3{,}8760$ (`kingston_q0_d10us`, freq=15, periódus=19)
3. $P = 3{,}7800$ (`kingston_q1_d10us`, freq=13, periódus=17)
4. $P = 3{,}7355$ (`kingston_q3_d100us`, freq=2, periódus=6)
5. $P = 3{,}7276$ (`kingston_q3_d10000us`, freq=14, periódus=18)

*(A titkos frekvencia-indexen (freq=7) a maximális megfigyelt érték csupán $P = 3{,}5521$, ami teljesen azonos a fehér Gauss-zaj eloszlásával).*

---

## 3. Statisztikai Null-Hipotézis Igazolása

Fehér Gauss-zaj esetén a periodogram statisztika elméleti eloszlása szigorúan $\text{Exp}(1)$.  
384 független teszt esetén a maximális érték elméleti várható értéke:
$$E[P_\text{max}] = H_{384} \approx \ln(384) + \gamma \approx 5{,}95 + 0{,}577 = 6{,}53$$

A Kingstonon mért $P_\text{max} = 4{,}9785$ még a zaj várható középértéke alatt is marad.  
A preregisztrált család-szintű túlélési valószínűség:
$$p_\text{family} = 1 - (1 - e^{-P_\text{max}})^{384} = 1 - (1 - e^{-4{,}9785})^{384} = 0{,}92955$$

---

## 4. Preregisztrált Végső Döntés

> **VERDIKT: CONFIRMED NULL**  
> **A Kingston kvantumprocesszoron a modulált jel a zajpadlón maradt. Semmilyen kimutatható kvantumos tér-memória vagy chip-közi áthallás nem jelent meg a két különálló kriogén hűtőgép között ($p = 0{,}93$).**

A preregisztrációs döntési fa szabályai szerint a mérés lezárult: a rendszer szigorú, kíméletlen és falszifikálható módon megadta a fizikailag megalapozott választ.

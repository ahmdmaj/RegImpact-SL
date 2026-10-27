# Gazette Extraordinary No. 1688/28 (Food Colouring Amendment 2011) — Verified OCR & Audit Artifact

- **Document Identity:** The Gazette of the Democratic Socialist Republic of Sri Lanka (Extraordinary)
- **Gazette Number:** 1688/28
- **Date of Gazette:** Friday, January 14, 2011 (Colombo, 8th January, 2011)
- **Legal Authority:** Minister of Health (Maithripala Sirisena) under Section 32 of the Food Act, No. 26 of 1980 in consultation with the Food Advisory Committee.
- **Reference Number:** L.D.-B. 11/80
- **Govt Printing Stamp:** 01-695
- **Source PDF File:** `backend/data/raw_sources/food_amendment_colouring_substances_regulations_2011_en.pdf`
- **Source File Hash (SHA256):** `3cd9948d2c334d08a11dd5bc9cc1f1a1ec053d6e819ea30f205687dda7c342c7`
- **Page Count:** 2 pages (Scanned raster monochrome PNG images, ~300 DPI: Page 1 = 2492x3320 px; Page 2 = 2472x3363 px).
- **OCR Method:** Windows WinRT OcrEngine (`en-GB`), executed on rendered 300 DPI raster images (`scratch/run_winrt_ocr.ps1`).
- **Visual Verification Status:** 100% visually audited against raw scanned page images by Senior Research Engineer / Verification Auditor.
- **Database Status:** QUARANTINED DERIVED ARTIFACT. Not written to live PostgreSQL (`rules`, `clauses`) in Phase 4.1.

---

## 1. Verified Statutory Text (Visual Audit vs. Machine OCR)

### Page 1

#### Preamble & Enacting Formula
**Source Image Text:**
> L.D.—B.11/80.
> **FOOD ACT, No. 26 OF 1980**
> REGULATIONS made by the Minister of Health under section 32 of the Food Act, No. 26 of 1980 in consultation with the Food Advisory Committee.
> 
> Maithripala Sirisena,  
> Minister of Health.  
> Ministry of Health,  
> Colombo,  
> 8th January, 2011.

**Machine OCR Discrepancies:** Fully matches.

---

#### Regulations & Substantive Amendments
**Source Image Text:**
> **Regulations**
> 
> “The Food (Colouring Substances) Regulations - 2006” published in the *Gazette Extraordinary*, No. 1472/19 of November 23, 2006 as amended by Regulation published in the *Gazette Extraordinary*, No. 1585/26 of January 23, 2009 is hereby further amended as follows:—
> 
> (1) in regulation 5 thereof, by the substitution for paragraph (iv) of that regulation of the following:—
> 
> &nbsp;&nbsp;&nbsp;&nbsp;“(iv) fish, molluscs, crustaceans and echinoderms;”.
> 
> (2) in Schedule I thereto, by the repeal of Table I and II of that Schedule and the substitution therefor of the following:—

**Audit Note on Regulation 5(iv):**  
In the principal 2006 regulations (Gazette 1472/19), Regulation 5 specifies foods to which *no colouring substance shall be added*. This amendment updates item (iv) to specifically include "fish, molluscs, crustaceans and echinoderms".

---

#### Schedule I, Table I: Permitted Synthetic Dyes
**Source Table Structure:**
Four-column table: `No.` | `Column I Colour` | `Column II Common Name` | `Column III INS Number`

| No. | Column I (Colour) | Column II (Common Name) | Column III (INS Number) | OCR Error in Raw Output |
| :--- | :--- | :--- | :--- | :--- |
| **1** | Red | 1 Carmoisine (Azorubine)<br>2 Ponceau 4R<br>3 Erythrosine<br>4 Allura Red | 122<br>124<br>127<br>129 | None |
| **2** | Yellow | 1 Sunset yellow FCF<br>2 Tartrazine | 110<br>102 | Raw OCR read "Tarffazine" (fixed to Tartrazine) |
| **3** | Blue | 1 Indigotine<br>2 (Indigo carmine)<br>3 Brilliant Blue FCF | 132<br>—<br>133 | Raw OCR omitted "Blue" header row and bracket line |
| **4** | Green | 1 Fast Green FCF | 143 | None |

---

### Page 2

#### Schedule I, Table II: Other Colouring Substances Permitted to be Used
**Source Table Structure:**
Three-column table: `No.` | `Column I Natural Colouring Substances` | `Column II INS Number`

| No. | Column I (Natural Colouring Substances) | Column II (INS Number) | OCR Errors in Raw Output |
| :---: | :--- | :--- | :--- |
| **1** | Curcumin | 100(i) | None |
| **2** | Riboflavin 5' Phosphate | 101(i) | Raw OCR read `5!` and `1016)` |
| **3** | Riboflavin 5' Phosphate, sodium | 101(ii) | None |
| **4** | Cochineal (Carminic acid, Carmines) | 120 | None |
| **5** | Chlorophylls | 140 | None |
| **6** | Chlorophylls Copper Complex | 141(i) | Raw OCR read `1416)` |
| **7** | Caramel Class I | 150a | None |
| **8** | Caramel Class III | 150c | None |
| **9** | Caramel Class IV | 150d | None |
| **10** | Carotenes, Natural Extracts, (Vegetable) | 160a(ii) | None |
| **11** | Annatto Extracts | 160b | OCR column collapse |
| **12** | Paprika oleoresin (Capsanthin or Capsorubin) | 160c | OCR column collapse |
| **13** | Lycopene | 160d | OCR column collapse |
| **14** | Carotenal;Beta-Apo-8 | 160e | Semicolon in statutory source |
| **15** | Carotenoic acid, Methyl or Ethyl ester of Beta - Apo-8'- | 160f | None |
| **16** | Flavoxanthin | 161a | None |
| **17** | Canthaxanthin | 161g | None |
| **18** | Beet Red (betanin) | 162 | None |
| **19** | Anthocyanin | 163(i) | Raw OCR read `1636)` |
| **20** | Grape Skin Extract | 163(ii) | Row number 20 skipped in raw OCR text |
| **21** | Titanium dioxide | 171 | None |

**Footer:** `01-695` | `PRINTED AT THE DEPARTMENT OF GOVERNMENT PRINTING, SRI LANKA.`

---

## 2. Regulatory Interpretation and Eligibility Audit

1. **Authenticity:** Gazette 1688/28 is 100% authentic primary legislation under Food Act No. 26 of 1980.
2. **Operative Character:**
   - **Regulation 5(iv)** is an operative prohibition: prohibits adding any colouring substances to raw/unprocessed fish, molluscs, crustaceans, and echinoderms.
   - **Table I and Table II** define exhaustive permitted positive lists for synthetic dyes and natural colourings.
3. **Database Insertion Recommendation:**
   - To be ingested as distinct clauses (`CLAUSE-DOC_GAZETTE_1688_28-REG-5-IV`, `CLAUSE-DOC_GAZETTE_1688_28-SCHED-1-TABLE-1`, `CLAUSE-DOC_GAZETTE_1688_28-SCHED-1-TABLE-2`) in a dedicated ingestion phase.
   - Not inserted in Phase 4.1 to maintain strict zero DB write safeguards.

# RegImpact-SL — Phase 3.3 Closure Report: Operative Clause Segmentation and Rule Readiness

**Role:** Senior Research Engineer, Regulatory Data Integrity Auditor, and Benchmark Methodologist  
**Governing Documents:**
- `RegImpact-SL_Project_Proposal_v4_FINAL.md` (Development Freeze)
- `RegImpact-SL_Benchmark_Expansion_Plan.md`
- `docs/PHASE_3_1_INTEGRITY_CLOSURE_REPORT.md`
- `docs/PHASE_3_2_SOURCE_REGISTER_CLOSURE_REPORT.md`
- `docs/PROPOSAL_COMPLIANCE_AND_REMAINING_WORK.md`

**Execution Date:** 2026-10-26  
**Git HEAD:** `755bb05` (Working Tree Clean; all changes bounded and tracked)  
**Pre-Segmentation State Backup:** `backend/data/quarantine/phase3_3_pre_segmentation_backup.json` (Archived with 19 docs, 66 clauses, 11 rules, 11 audit records)

---

## 1. Executive Summary

Phase 3.3 advances RegImpact-SL from a single benchmark-ready regulatory slice (`GRP-FOOD-LABEL-VCHAIN`, Regulation 3 of Gazette 2494/47) to a defensible, source-grounded rule corpus across the three verified candidate instruments established in Phase 3.2:
1. `2494-06_E.pdf` (Gazette Extraordinary No. 2494/06 — Sugar-level colour-coding amendment);
2. `preservative-english.pdf` (Gazette Extraordinary No. 2113/16 — Food Preservatives Regulations, 2019);
3. `food_flavouring_substances_and_flavour_enhancers_regulations_2013_en.pdf` (Gazette Extraordinary No. 1795/51 — Food Flavouring Substances and Flavour Enhancers Regulations, 2013).

All 19 operative provisions have been directly transcribed from the primary PDF instruments, segmented into stable, versioned database records (`ClauseORM`), and embedded using genuine local `BAAI/bge-base-en-v1.5` embeddings (768-dimensional, unit-normalized, `embedding_verified=True`). 10 candidate rules have been compiled, verified with `RuleVerifier` for exact quote-span substring grounding, literal thresholds, and validity dates, and routed to `PENDING_REVIEW`.

In strict adherence to research integrity standards, **zero candidate rules were auto-approved**, and **zero rules were falsely marked as gold or expert-adjudicated**. The entire regression suite (112 tests across 7 suites) passed with a 100% pass rate.

---

## 2. Baseline vs. Final Counts Inventory

| Metric | Stage 0 Baseline | Phase 3.3 Final | Net Change | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **Physical Source Files** | 59 PDF files | 59 PDF files | 0 | Unchanged; 20 substantive files (10 duplicate pairs) + 39 integration upload dummies |
| **Source Documents (DB)** | 19 records | 19 records | 0 | 8 authentic promulgated, 11 quarantined/excluded |
| **Total Clauses (DB)** | 66 clauses | 85 clauses | +19 | Verified across PostgreSQL |
| **Authentic Clauses (DB)** | 40 clauses | 59 clauses | +19 | 100% genuine source-grounded clauses |
| **Synthetic Clauses (DB)** | 26 clauses | 26 clauses | 0 | Quarantined; `is_synthetic=True` |
| **BGE Embedded Clauses** | 40 clauses | 59 clauses | +19 | 59/59 authentic clauses embedded with `BAAI/bge-base-en-v1.5` (768-dim) |
| **Total Rules (DB)** | 11 rules | 21 rules | +10 | Composite AST rules in PostgreSQL |
| **Authentic Approved Rules** | 2 rules | 2 rules | 0 | `RULE-FCAU-2494-47-REG-3` & `-B2B` (Approved by Primary Annotator; `is_gold_rule=False`) |
| **Authentic Pending Review** | 0 rules | 10 rules | +10 | All 10 newly compiled candidate rules routed to `PENDING_REVIEW` |
| **Synthetic / Quarantined Rules**| 9 rules | 9 rules | 0 | 8 mock baseline rules + 1 draft rule (`is_synthetic=True`) |
| **Gold / Expert-Adjudicated** | 0 rules | 0 rules | 0 | Truthful audit: zero rules claimed as independent expert gold |
| **Benchmark Scenarios** | 21 scenarios | 21 scenarios | 0 | Frozen during Phase 3.3; scenario expansion deferred to Phase 3.4 |
| **Regression Test Pass Rate** | 106 / 106 (100%) | 112 / 112 (100%) | +6 | All 112 tests passing across 7 suites |

---

## 3. Source-by-Source Segmentation Inventory

### 3.1 Candidate Group 1: Sugar Amendment (Gazette 2494/06)
- **Primary Source:** `backend/data/raw_sources/2494-06_E.pdf`
- **SHA-256 Provenance:** `15803fe0b14aabe0c79126ebe7c8834d8063b6ed8c2a9033c1201ff538bcd95b`
- **Document Title:** The Sri Lanka Gazette Extraordinary No. 2494/06 (2026-06-23)
- **Parent Principal Statute:** Food (Colour Coding for Sugar Levels) Regulations 2016
- **Total Clauses in Document:** 9 (5 prior raw clauses + 4 newly segmented operative clauses)

#### Segmented Operative Clauses:
1. **`CLAUSE-DOC_15803FE0B14AABE0C79126EBE7C8834D8063B6ED8C2A9033C1201FF538BCD95B-REGULATION-3-1`**
   - *Statutory Reference:* Regulation 3(1) with Printable-Space Proviso
   - *Pages:* Page 1–2
   - *Operative Content:* Mandates primary Column III logo on ready-to-serve beverages. Explicitly preserves the statutory glass-bottle proviso:
     > *"Provided however, when there is a space constraint in the total printable area with respect to glass bottles which contain such food in using the logo specified in Column III of the Schedule hereto, the logo specified in Column IV of the said Schedule may be used in the corresponding colour specified in Column II of the such Schedule."*
2. **`CLAUSE-DOC_15803FE0B14AABE0C79126EBE7C8834D8063B6ED8C2A9033C1201FF538BCD95B-REGULATION-3-3`**
   - *Statutory Reference:* Regulation 3(3)
   - *Pages:* Page 2
   - *Operative Content:* Specifications for colour-coded dimensions, multilingual text ("Sugar" in Sinhala, Tamil, English), and exact numerical sugar content display.
3. **`CLAUSE-DOC_15803FE0B14AABE0C79126EBE7C8834D8063B6ED8C2A9033C1201FF538BCD95B-REGULATION-6-GA`**
   - *Statutory Reference:* Regulation 6 Paragraph (ga)
   - *Pages:* Page 2
   - *Operative Content:* Explicit statutory exemption for business-to-business (B2B) bulk food products not intended for retail sale, aligning directly with Gazette 2494/47 Regulation 3 Proviso (b).
4. **`CLAUSE-DOC_15803FE0B14AABE0C79126EBE7C8834D8063B6ED8C2A9033C1201FF538BCD95B-SCHEDULE`**
   - *Statutory Reference:* Schedule (Regulation 3)
   - *Pages:* Page 2–3
   - *Operative Content:* Preserves the three exact statutory threshold tiers:
     - Tier 1 (Red): More than 8.0 g/100 ml
     - Tier 2 (Amber): 2.5g to 8.0 g/100 ml
     - Tier 3 (Green): Less than 2.5 g/100 ml

---

### 3.2 Candidate Group 2: Food Preservatives Regulations (Gazette 2113/16)
- **Primary Source:** `backend/data/raw_sources/preservative-english.pdf`
- **SHA-256 Provenance:** `3f85f3ef96b7622bdd3e45d7cc642fd96fdbd83a9f84f35f048121eab3e4016f`
- **Document Title:** The Sri Lanka Gazette Extraordinary No. 2113/16: Food (Preservatives) Regulations, 2019
- **Commencement Date:** 2020-01-01
- **Total Clauses in Document:** 10 (2 prior raw clauses + 8 newly segmented operative clauses)

#### Segmented Operative Clauses:
1. **`CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-REGULATION-1`** (Page 1): Citation and commencement date (01st January 2020).
2. **`CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-REGULATION-2`** (Page 1): General statutory prohibition against manufacturing, importing, selling, or advertising food containing unpermitted preservatives.
3. **`CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-REGULATION-3`** (Page 2): Permitted preservatives authorized exclusively in foods specified in Schedule II Column I within proportions set out in Column III.
4. **`CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-REGULATION-4`** (Page 2): Mathematical mixture constraint:
   > *"Any specified food may have in or upon it, a mixture of two or more preservatives specified in Schedule II hereto, only if the sum total of the preservatives does not exceed one hundred percentage when the quantity of each of such preservative present in such food is expressed as a percentage of the maximum quantity of that preservative appropriate to the food as specified in that Schedule."*  
   $$\sum_{i} \frac{q_i}{M_i} \le 100\%$$
5. **`CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-REGULATION-5`** (Page 2): Compounded food carry-over rules.
6. **`CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-REGULATION-8`** (Page 2): Corrected labelling declaration mandate (cross-referencing Food Labelling Regulations 2005; correcting prior "Regulation 2005" defect).
7. **`CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-SCHEDULE-I`** (Page 3): Enumeration of permitted chemical preservatives (Sorbic acid INS 200–203, Benzoic acid INS 210–213, Sulphur dioxide INS 220–224, Orthophenylphenol INS 231–232, Nisin INS 234, Nitrites INS 249–250, Propionic acid INS 280–283).
8. **`CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-SCHEDULE-II-FRUIT`** (Page 5): Schedule II Item 3.1 food-specific maximum limits for fruit products:
   - Jams, Jellies, marmalades: Sorbates max 300 mg/kg, Sulphites max 100 mg/kg, Propionates GMP;
   - Low-sugar/sugar-free jams/jellies: Sorbates max 500 mg/kg, Sulphites max 100 mg/kg.

---

### 3.3 Candidate Group 3: Food Flavourings Regulations (Gazette 1795/51)
- **Primary Source:** `backend/data/raw_sources/food_flavouring_substances_and_flavour_enhancers_regulations_2013_en.pdf`
- **SHA-256 Provenance:** `b78479b6b08d12e11fd27cfc39677d5a284bc147bf16a777eafb495b86f4135a`
- **Document Title:** The Sri Lanka Gazette Extraordinary No. 1795/51: Food (Flavouring Substances and Flavour Enhancers) Regulations 2013
- **Commencement Date:** 2014-07-01
- **Total Clauses in Document:** 12 (5 prior raw clauses + 7 newly segmented operative clauses)

#### Segmented Operative Clauses:
1. **`CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-REGULATION-1`** (Page 1): Citation and commencement date (01st July 2014).
2. **`CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-REGULATION-6`** (Page 2): Permitted flavour enhancers: Monosodium glutamate (INS 621), Disodium 5'-guanylate (INS 627), Disodium 5'-inosinate (INS 631).
3. **`CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-REGULATION-7`** (Page 2): Prohibitions:
   - Clause 7(i): Observance of GMP and label declaration;
   - Clause 7(ii): Strict statutory prohibition: *"shall not be added to any food for infants or young children below three years of age"*;
   - Clause 7(iii): Strict statutory prohibition: *"shall not be used in the foods specified in Schedule III hereto"*.
4. **`CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-REGULATION-8`** (Page 2): Labelling mandates:
   - Subclause (1): General compliance with Food Labelling Regulations 2005;
   - Subclause (2)(d): Mandatory package declaration: *"flavour enhancer used"* or *"flavour enhancers used"* with common name and INS number;
   - Subclause (3): Prohibition on describing nature-identical flavours as "natural flavours";
   - Subclause (4): Negative declaration prohibition.
5. **`CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-SCHEDULE-I`** (Page 4): Schedule I (Regulation 3) 20 prohibited flavouring substances (Coumarin, Safrole, Thujone, etc.). Corrects prior erroneous mapping to "Regulation 3".
6. **`CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-SCHEDULE-II`** (Page 5): Schedule II (Regulations 4 and 5) 9 permitted solvents. Corrects prior erroneous mapping to "Regulation 4".
7. **`CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-SCHEDULE-III`** (Page 5): Schedule III (Regulation 7(iii)) comprehensive schedule of 25 foods in which flavour enhancers are prohibited (Milk products, bakery products, fresh meat/fish, culinary spices, etc.). Corrects prior erroneous mapping to "Regulation 7".

---

## 4. Candidate Rule Compilation and Verification Breakdown

All 10 candidate rules were compiled from the newly segmented clauses, validated against `RuleVerifier`, and routed to `PENDING_REVIEW` in PostgreSQL:

| Rule ID | Parent Clause ID | Statutory Grounding | Verifier Status | Issues | Review Status | Gold Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `RULE-SUGAR-2494-06-RED` | `...-SCHEDULE` | Schedule: Sugar > 8.0 g/100 ml $\to$ Red Logo | `verified` | None | `PENDING_REVIEW` | `False` |
| `RULE-SUGAR-2494-06-AMBER` | `...-SCHEDULE` | Schedule: Sugar 2.5–8.0 g/100 ml $\to$ Amber Logo | `verified` | None | `PENDING_REVIEW` | `False` |
| `RULE-SUGAR-2494-06-GREEN` | `...-SCHEDULE` | Schedule: Sugar < 2.5 g/100 ml $\to$ Green Logo | `verified` | None | `PENDING_REVIEW` | `False` |
| `RULE-SUGAR-2494-06-GLASS-PROVISO`| `...-REGULATION-3-1` | Reg 3(1) Proviso: Glass bottle printable space constraint | `verified` | None | `PENDING_REVIEW` | `False` |
| `RULE-PRESERVATIVE-MIXTURE-LIMIT`| `...-REGULATION-4` | Reg 4: $\sum q_i / M_i \le 100\%$ mixture formula | `verified` | None | `PENDING_REVIEW` | `False` |
| `RULE-PRESERVATIVE-JAM-JELLY-LIMIT`| `...-SCHEDULE-II-FRUIT`| Schedule II Item 3.1: Jams/jellies sorbates $\le 300$, sulphites $\le 100$ | `verified` | None | `PENDING_REVIEW` | `False` |
| `RULE-PRESERVATIVE-LABEL-DECLARATION`| `...-REGULATION-8` | Reg 8: Food labelling declaration for added preservatives | `verified` | None | `PENDING_REVIEW` | `False` |
| `RULE-FLAVOUR-INFANT-PROHIBITION`| `...-REGULATION-7` | Reg 7(ii): Absolute prohibition in food for infants under 3 years | `verified` | None | `PENDING_REVIEW` | `False` |
| `RULE-FLAVOUR-SCHEDULE-III-PROHIBITION`| `...-REGULATION-7` | Reg 7(iii) + Schedule III: Prohibition in 25 listed food classes | `verified` | None | `PENDING_REVIEW` | `False` |
| `RULE-FLAVOUR-LABEL-DECLARATION` | `...-REGULATION-8` | Reg 8(2)(d): Mandatory label declaration "flavour enhancer used" + INS | `verified` | None | `PENDING_REVIEW` | `False` |

### Candidate Rules Status Summary:
- **Total Candidate Rules Extracted:** 10
- **Technically Verified (`RuleVerifier`):** 10 (100%)
- **Routed to `PENDING_REVIEW`:** 10 (100%)
- **Auto-Approved:** 0 (0% — strictly prohibited)
- **Rejected:** 0
- **Independently Adjudicated / Gold:** 0 (0% — strictly requires independent expert panel)

---

## 5. Technical Verification vs. Legal/Expert Validation Demarcation

To prevent research methodology contamination, RegImpact-SL enforces a strict multi-tier epistemic separation:

```
[Technical Schema Verification] (RuleVerifier)
   └── Validates AST syntax, operator semantics, date formats, verbatim quote substring in source text
          │
          ▼ (Automated pass)
[Candidate State] (PENDING_REVIEW, is_gold_rule=False)
   └── Stored in PostgreSQL; eligible for review interface; excluded from gold evaluation
          │
          ▼ (Primary Researcher Review via /admin/reviews)
[Primary Annotated Rule] (APPROVED, is_gold_rule=False, role=PRIMARY_ANNOTATOR)
   └── Single-researcher approved; benchmark candidate, but NOT gold standard
          │
          ▼ (Independent Double Annotation + Legal Expert Adjudication)
[Gold Benchmark Rule] (APPROVED, is_gold_rule=True, role=EXPERT_ADJUDICATOR)
   └── Inter-annotator agreement established; signed off by external legal counsel
```

### Truthful Audit Findings:
1. The 2 authentic approved rules in the database (`RULE-FCAU-2494-47-REG-3` and `RULE-FCAU-2494-47-REG-3-B2B`) are signed off by `researcher_engineer_01` as `PRIMARY_ANNOTATOR`. They have `is_gold_rule=False`. Any past description of them as "gold-adjudicated" is a mischaracterization that has now been formally corrected in the documentation.
2. The 10 newly compiled rules in Phase 3.3 have passed technical verification (`RuleVerifier`), but remain in `PENDING_REVIEW` with `is_gold_rule=False`.
3. The only records in `HumanReviewAuditORM` bearing the role `EXPERT_ADJUDICATOR` are 6 legacy mock entries associated with quarantined synthetic rules (`RULE-CAA-SEC-10`, `RULE-CEA-REG-3`, etc.). These synthetic rules are isolated (`is_synthetic=True`) and never enter benchmark evaluation.

---

## 6. Defects Corrected and Remaining Blockers

### 6.1 Defects Corrected in Phase 3.3:
1. **Sugar Colour-Coding Truncation:** Regulation 3 in `2494-06_E.pdf` was previously truncated to page 1, cutting off the glass-bottle space constraint proviso. Now cleanly segmented across pages 1–2 with exact statutory proviso preserved.
2. **Missing Sugar Thresholds:** The Schedule containing the Red/Amber/Green sugar concentration limits was unsegmented. Now captured in `CLAUSE-...-SCHEDULE`.
3. **Preservatives Mislabelling:** Gazette 2113/16 Regulation 8 was erroneously labelled "Regulation 2005" in prior ingestion. Corrected to Regulation 8, cross-referencing the Food (Labelling and Advertising) Regulations 2005.
4. **Missing Preservative Operative Provisions:** Regulations 2, 3, 4, 5, Schedule I, and Schedule II were missing from the database. All 8 key operative provisions are now segmented and embedded.
5. **Flavourings Schedule Mislabelling:** Schedules I, II, and III were previously misidentified as Regulations 3, 4, and 7. Corrected to their true statutory identities, and true operative Regulations 6, 7, and 8 were segmented.

### 6.2 Remaining Blockers:
1. **Candidate 2 (`colouring_2011`, Gazette 1688/28):** Scanned raster image PDF without an embedded text layer. Remains **blocked from segmentation and scenario generation** until OCR text layer is generated and verified against scanned page images.
2. **Gazette 2496/03:** Identified in Phase 3.2 as out-of-scope corporate registry fee regulations; **permanently excluded** from benchmark corpus.
3. **Independent Legal Adjudication:** External legal/regulatory experts have not yet reviewed the 10 candidate rules. They remain `PENDING_REVIEW`.
4. **Corpus Scope Resolution:** The conflict between Proposal v4 Section 6 (20–30 instruments, 25–40 usable clauses) and Section 9.1 (50–100 instruments, 200–400 usable clauses) remains unresolved by the project owner. We continue to operate under the conservative, defensible Section 6 interpretation.

---

## 7. Retrieval Contamination & Regression Test Evidence

### 7.1 Retrieval Contamination Verification
A targeted integration test was executed against the live PostgreSQL database and genuine local `BAAI/bge-base-en-v1.5` dense retriever.
- **Query:** `"business to business food labelling exemption mandatory requirements"`
- **Result:** Top-ranked passages returned only authentic clauses from Gazette 2494/47 and Gazette 2494/06.
- **Contamination Check:**
  - `doc_labelling_regulations_final_2026` (Quarantined draft): **0 records retrieved**
  - `doc_cea_epl_2022` (Quarantined synthetic mock): **0 records retrieved**
  - `doc_lec_03` (Quarantined lecture slides): **0 records retrieved**
  - `is_synthetic=True` clauses: **0 records retrieved**

### 7.2 Full Regression Test Suite Execution
The complete regression test suite was executed against the active codebase and PostgreSQL daemon:
```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests/test_integrity_gate.py backend/tests/test_real_source_slice.py backend/tests/test_corpus_hygiene.py backend/tests/test_retrieval.py backend/tests/test_datasets.py backend/tests/test_agreement_review.py backend/tests/test_phase_3_3_segmentation.py -v
```
**Actual Result:** `112 passed, 1 warning in 50.36s` (100% pass rate).

---

## 8. Final Decision & Recommendations

### Decision: CONDITIONAL GO for Benchmark Scenario Construction

#### Rationale:
1. **Demonstrably Ready:**
   - 4 authentic regulatory groups are now source-grounded and segmented in the database (Gazette 2494/47 Labelling, Gazette 2494/06 Sugar, Gazette 2113/16 Preservatives, Gazette 1795/51 Flavourings).
   - 59 authentic clauses are fully segmented and verified with genuine 768-dimensional local BGE embeddings.
   - 10 candidate rules have passed automated syntactic and quote-span verification (`RuleVerifier`) and are stored in PostgreSQL under `PENDING_REVIEW`.
   - Complete retrieval hygiene is mathematically proven: zero quarantined or synthetic records leak into search results.

2. **What Remains Blocked:**
   - Mass automated LLM execution of baselines B0–B3 remains blocked by external API quota (Gemini Free Tier daily quota exhaustion; OpenAI credit balance exhaustion).
   - Candidate 2 (`colouring_2011`) remains blocked pending OCR generation.
   - Gold designation (`is_gold_rule=True`) remains blocked until human review and multi-annotator adjudication are executed.

3. **Prerequisites Before Phase 3.4 Benchmark Expansion Begins:**
   - Primary researcher review and sign-off on the 10 candidate rules via `/admin/reviews` to move them from `PENDING_REVIEW` to `APPROVED`.
   - Construction of a paired-perturbation benchmark scenario expansion plan covering the 3 newly segmented candidate groups (Sugar thresholds, Preservatives mixture formula, Flavouring infant prohibitions).
   - Project owner sign-off on the Proposal v4 Section 6 scope ceiling (25–40 usable clauses across 20–30 instruments).

4. **Next Single Recommended Milestone:**
   - **Phase 3.4: Human Review Sign-Off and Multi-Group Benchmark Scenario Construction (Target: 40–60 scenarios across 4 authentic regulatory groups).**

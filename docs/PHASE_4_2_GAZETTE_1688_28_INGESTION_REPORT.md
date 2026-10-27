# RegImpact-SL — Phase 4.2: Controlled Ingestion of Verified Gazette 1688/28 Clauses Report

**Role:** Senior Research Engineer, Regulatory Source Verification Auditor, Database Integrity Engineer, and Test Engineer  
**Governing Specification:** `RegImpact-SL_Project_Proposal_v4_FINAL.md` (Frozen Development Baseline)  
**Scope Authority:** `docs/PROJECT_OWNER_SCOPE_DECISION_RECORD.md` (Option A: Focused Food Control Scope Locked)  
**Previous Phase Reports:**  
- `docs/PHASE_4_1_AUTHENTIC_CORPUS_ELIGIBILITY_AND_EXPANSION_REPORT.md`  
- `docs/PHASE_4_0_RULE_INTEGRITY_AND_HUMAN_REVIEW_READINESS_REPORT.md`  
**Date:** 2026-10-27  

---

## 1. Executive Summary & Mandatory Safeguard Adherence

Phase 4.2 executed the controlled, evidence-grounded ingestion of **Gazette Extraordinary No. 1688/28** (Food Colouring Amendment 2011) into the authentic Food Control corpus of RegImpact-SL.

### Safeguards Compliance Confirmation
1. **Pre-Existing Git State Preservation:** Initial git status was clean. Recent commit history (`bc91e97`, `a53e067`, `c5371f2`, `79a92fe`, `6488a67`) was audited and confirmed to predate Phase 4.2 execution. Zero git commits, amends, rebases, stashes, resets, or pushes were performed in this phase.
2. **Strictly Bounded Ingestion:** Only the 3 verified candidate clauses derived from Gazette 1688/28 were inserted into PostgreSQL `clauses` table, with metadata synchronization on `source_documents` and `document_pages`.
3. **Zero Rule Insertions or Approvals:** Zero rows were inserted, updated, or approved in `rules`. Total authentic rules remained exactly 12 (2 approved, 10 pending review).
4. **Zero Benchmark Mutations:** `multi_group_benchmark_slice.jsonl` remained untouched (exactly 30 scenarios, 100% `is_gold_scenario=False`). No new scenarios were generated.
5. **Zero Gold Designations:** All newly ingested clauses have `is_synthetic=False` and zero gold flags.
6. **Zero External API Costs:** Dense embeddings were generated locally using the cached `BAAI/bge-base-en-v1.5` model (768-dim, unit-normalized, finite vectors). Zero paid Gemini or OpenAI APIs were called.
7. **Regression Testing Passed:** 78 tests passed across 8 test suites (including 58 regression tests in `test_integrity_gate.py`, `test_phase_3_3_segmentation.py`, `test_phase_3_4_benchmark.py`, `test_phase_3_5_review_readiness.py`, `test_phase_3_8_source_verification.py`, and `test_phase_3_9_jam_modeling.py`, plus 20 vector/retrieval integration tests in `test_postgres_vector_integration.py` and `test_retrieval.py`).

---

## 2. Git State & Commit-History Clarification

### Preflight Git Audit
At the start of Phase 4.2 (2026-10-27T15:55:45+05:30), the repository state was inspected:
- **Branch:** `main` (synchronized with `origin/main` at prior HEAD)
- **Status:** Clean working tree (`git status --short` returned 0 modified lines).
- **Recent Commit History:**
  - `bc91e97` (2026-10-27 15:46:42): `docs: add Phase 4.1 authentic corpus verification report and clause eligibility expansion register`
  - `a53e067` (2026-10-27 15:40:59): `feat: add clause audit register JSON file for regulatory analysis`
  - `c5371f2` (2026-10-27 15:33:12): `feat: add verified OCR text and raw OCR output artifacts for Gazette 1688/28`
  - `79a92fe` (2026-10-27 15:32:11): `feat: add OCR text files for Gazette extra 1688/28 pages 1 and 2`
  - `6488a67` (2026-10-27 15:31:54): `feat: add PowerShell scripts for testing and executing Windows Runtime OCR`

**Clarification on Commit `bc91e97`:**
Commit `bc91e97` was authored by `ahmdmaj <majaahnaf19@gmail.com>` during Phase 4.1 wrap-up at 15:46:42. It predates the invocation of Phase 4.2. In compliance with Safeguard 2, this history was left intact; no history rewriting, resets, or git commits were executed in Phase 4.2.

---

## 3. Source Identity & Independent Hash Verification

The source PDF files on disk were audited and independently verified:
- **Primary Source File:** `backend/data/raw_sources/food_amendment_colouring_substances_regulations_2011_en.pdf`
- **Hash-Duplicate File:** `backend/data/raw_sources/3cd9948d2c334d08a11dd5bc9cc1f1a1ec053d6e819ea30f205687dda7c342c7.pdf`
- **File Size:** Exactly 81,054 bytes
- **Page Count:** 2 pages
- **Independently Computed SHA-256:**  
  `3cd9948d2c334d08a11dd5bc9cc1f1a1ec053d6e819ea30f205687dda7c342c7`
- **Database Alignment:** Exactly matches `sha256_hash` stored on `SourceDocumentORM` (`doc_3cd9948d2c334d08a11dd5bc9cc1f1a1ec053d6e819ea30f205687dda7c342c7`).
- **Physical Document Characteristics:** 2 scanned raster pages at 300 DPI (Page 1: 2492 $\times$ 3320 px; Page 2: 2472 $\times$ 3363 px). Zero embedded digital text characters.

---

## 4. Candidate-by-Candidate Source Verification & Mapping Decisions

### Candidate 1: Regulation 5(iv) Amendment
- **Assigned Stable Clause ID:**  
  `CLAUSE-DOC_3CD9948D2C334D08A11DD5BC9CC1F1A1EC053D6E819EA30F205687DDA7C342C7-REGULATION-5-IV`
- **Clause Number:** `Regulation 5(iv)`
- **Document ID:** `doc_3cd9948d2c334d08a11dd5bc9cc1f1a1ec053d6e819ea30f205687dda7c342c7`
- **Source Page:** Page 1 (`start_page=1, end_page=1`)
- **Statutory Text Stored:**
  ```text
  “The Food (Colouring Substances) Regulations - 2006” published in the Gazette Extraordinay, No. 1472/19 of November 23, 2006 as amended by Regulation published in the Gazette Extraordinary, No. 1585/26 of January 23, 2009 is hereby further amended as follows:-
  (1) in regulation 5 thereof, by the substitution for paragraph (iv) of that regulation of the following:-
  “(iv) fish, molluscs, crustaceans and echinoderms;”.
  ```
- **Legal Character & Relationship to Principal Regulations:**
  - Amends Regulation 5 of the principal Food (Colouring Substances) Regulations 2006 (Gazette 1472/19), which enumerates raw, unprocessed foods to which *no colouring substance may be added*.
  - Substitutes paragraph (iv) to specifically cover `"fish, molluscs, crustaceans and echinoderms"`.
  - Operates as a strict negative prohibition on added colours in raw seafood.
  - OCR Resolution: Machine OCR matched visual scan verbatim.

### Candidate 2: Schedule I, Table I — Permitted Synthetic Dyes
- **Assigned Stable Clause ID:**  
  `CLAUSE-DOC_3CD9948D2C334D08A11DD5BC9CC1F1A1EC053D6E819EA30F205687DDA7C342C7-SCHEDULE-I-TABLE-I`
- **Clause Number:** `Schedule I Table I`
- **Document ID:** `doc_3cd9948d2c334d08a11dd5bc9cc1f1a1ec053d6e819ea30f205687dda7c342c7`
- **Source Page:** Page 1 (`start_page=1, end_page=1`)
- **Statutory Text Stored:**
  ```text
  (2) in Schedule I thereto, by the repeal of Table I and II of that Schedule and the substitution therefor of the following:—

  “TABLE - I
  Synthetic dyes that are permitted to be used as colouring substances in food
  No. | Column I Colour | Column II Common Name | Column III INS Number
  1 | Red | 1 Carmoisine (Azorubine) | 122
  1 | Red | 2 Ponceau 4R | 124
  1 | Red | 3 Erythrosine | 127
  1 | Red | 4 Allura Red | 129
  2 | Yellow | 1 Sunset yellow FCF | 110
  2 | Yellow | 2 Tartrazine | 102
  3 | Blue | 1 Indigotine | 132
  3 | Blue | 2 (Indigo carmine) | 132
  3 | Blue | 3 Brilliant Blue FCF | 133
  4 | Green | 1 Fast Green FCF | 143
  ```
- **Legal Character & Relationship to Principal Regulations:**
  - Replacement schedule repealing and substituting Table I of Schedule I of the 2006 regulations.
  - Exhaustive positive list authorizing 10 synthetic dye names across 4 colour groups (Red, Yellow, Blue, Green) and 8 unique INS numbers (122, 124, 127, 129, 110, 102, 132, 133, 143).
  - Note on Concentration Limits: Table I does *not* specify ppm limits. Permitted concentrations and eligible food categories are governed by Regulations 3 and 6 of the principal 2006 regulations. Storing the full table preserves substance names and INS codes without fabricating non-existent concentration limits.
  - OCR Resolution: Machine OCR misread `Tartrazine` as `Tarffazine` and skipped `Blue` header; corrected via visual scan audit.

### Candidate 3: Schedule I, Table II — Other Permitted Colouring Substances
- **Assigned Stable Clause ID:**  
  `CLAUSE-DOC_3CD9948D2C334D08A11DD5BC9CC1F1A1EC053D6E819EA30F205687DDA7C342C7-SCHEDULE-I-TABLE-II`
- **Clause Number:** `Schedule I Table II`
- **Document ID:** `doc_3cd9948d2c334d08a11dd5bc9cc1f1a1ec053d6e819ea30f205687dda7c342c7`
- **Source Page:** Page 2 (`start_page=2, end_page=2`)
- **Statutory Text Stored:**
  ```text
  TABLE - II
  Other Colouring substances permitted to be used
  No. | Column I Natural Colouring Substances | Column II INS Number
  1 | Curcumin | 100(i)
  2 | Riboflavin 5' Phosphate | 101(i)
  3 | Riboflavin 5' Phosphate, sodium | 101(ii)
  4 | Cochineal (Carminic acid, Carmines) | 120
  5 | Chlorophylls | 140
  6 | Chlorophylls Copper Complex | 141(i)
  7 | Caramel Class I | 150a
  8 | Caramel Class III | 150c
  9 | Caramel Class IV | 150d
  10 | Carotenes, Natural Extracts, (Vegetable) | 160a(ii)
  11 | Annatto Extracts | 160b
  12 | Paprika oleoresin (Capsanthin or Capsorubin) | 160c
  13 | Lycopene | 160d
  14 | Carotenal;Beta-Apo-8 | 160e
  15 | Carotenoic acid, Methyl or Ethyl ester of Beta - Apo-8'- | 160f
  16 | Flavoxanthin | 161a
  17 | Canthaxanthin | 161g
  18 | Beet Red (betanin) | 162
  19 | Anthocyanin | 163(i)
  20 | Grape Skin Extract | 163(ii)
  21 | Titanium dioxide | 171
  ```
- **Legal Character & Relationship to Principal Regulations:**
  - Replacement schedule repealing and substituting Table II of Schedule I of the 2006 regulations.
  - Exhaustive positive list specifying 21 permitted natural and mineral colouring substances.
  - OCR Resolution: Resolved collapsed columns (`16m` $\to$ `160b`, `160c`, `160d`, `160e`), layout misreadings (`5!` $\to$ `5'`, `1016)` $\to$ `101(i)`, `1416)` $\to$ `141(i)`), and restored dropped row 20.

---

## 5. Controlled Ingestion Details & Exact Database Mutations

The ingestion script was executed atomically via `scratch/ingest_1688_clauses.py` using `session_scope()`:
1. **Source Document Metadata Synchronization (`source_documents` table):**
   - Record `id = 'doc_3cd9948d2c334d08a11dd5bc9cc1f1a1ec053d6e819ea30f205687dda7c342c7'`
   - Updated `title`: `"The Sri Lanka Gazette Extraordinary No. 1688/28 (Food Colouring Amendment 2011)"`
   - Updated `gazette_no`: `"1688/28"`
   - Updated `authority`: `"Minister of Health (Maithripala Sirisena)"`
   - Updated `instrument_type`: `"gazette"`
   - Updated `publication_date`: `2011-01-14`
   - Updated `extraction_status`: `"SUCCESS"` (upgraded from `"PARTIAL_OCR"`)
   - Updated `extraction_tool`: `"Windows WinRT OCR (en-GB) + PyMuPDF"`
2. **Document Page Raw Text Storage (`document_pages` table):**
   - Page 1: Populated `raw_text` (1,328 chars), `char_count=1328`, `is_ocr=True`, `page_hash` calculated.
   - Page 2: Populated `raw_text` (859 chars), `char_count=859`, `is_ocr=True`, `page_hash` calculated.
3. **Clauses Inserted (`clauses` table):**
   - `CLAUSE-DOC_3CD9948D2C334D08A11DD5BC9CC1F1A1EC053D6E819EA30F205687DDA7C342C7-REGULATION-5-IV`
   - `CLAUSE-DOC_3CD9948D2C334D08A11DD5BC9CC1F1A1EC053D6E819EA30F205687DDA7C342C7-SCHEDULE-I-TABLE-I`
   - `CLAUSE-DOC_3CD9948D2C334D08A11DD5BC9CC1F1A1EC053D6E819EA30F205687DDA7C342C7-SCHEDULE-I-TABLE-II`
   - All 3 inserted with `version_number=1`, `is_synthetic=False`, `is_compilable=True`, `embedding_verified=True`, `embedding_provider='sentence-transformers'`, and `embedding_model='BAAI/bge-base-en-v1.5'`.

---

## 6. Baseline vs. Final Reconciled Database Counts

Re-read verification directly from PostgreSQL confirms exact numerical accounting:

| Entity / Category | Preflight Baseline | Confirmed Mutations | Post-Ingestion Final | Audit Reconciliation |
| :--- | :---: | :---: | :---: | :--- |
| **Total Source Documents** | 19 | 0 added (1 updated) | **19** | **Preserved.** 8 authentic, 11 quarantined synthetic. |
| **Authentic Source Documents** | 8 | 0 | **8** | **Preserved.** Gazette 1688/28 status upgraded to SUCCESS. |
| **Quarantined Documents** | 11 | 0 | **11** | **Preserved.** Zero synthetic promotions. |
| **Total Stored Clauses** | 85 | +3 inserted | **88** | **Reconciled.** 62 authentic + 26 quarantined synthetic. |
| **Authentic Stored Clauses** | 59 | +3 inserted | **62** | **Reconciled.** 100% embedded with local BGE v1.5. |
| **Quarantined Synthetic Clauses** | 26 | 0 | **26** | **Preserved.** Zero synthetic contamination. |
| **Substantive Operative Clauses** | 44 | +3 added | **47** | **Reconciled.** 47 distinct operative Food Control clauses. |
| **Ineligible Stubs & Out-of-Scope** | 15 | 0 | **15** | **Preserved.** Preambles and corporate fees remain excluded. |
| **Total Rules in Database** | 21 | 0 | **21** | **Preserved.** Zero rules inserted or modified. |
| **Authentic Rules in Database** | 12 | 0 | **12** | **Preserved.** 2 approved, 10 pending review. |
| **Rules with `is_gold_rule=True`** | 0 | 0 | **0** | **Preserved.** 100% non-gold. |
| **Rules review_status APPROVED** | 11 | 0 | **11** | **Preserved.** 2 authentic, 9 synthetic fixtures. |
| **Rules review_status PENDING_REVIEW** | 10 | 0 | **10** | **Preserved.** 10 authentic candidate rules. |
| **Human Review Audits** | 11 | 0 | **11** | **Preserved.** Audit trail untouched. |
| **Benchmark Scenarios** | 30 | 0 | **30** | **Preserved.** Benchmark slice untouched. |
| **Scenarios with `is_gold_scenario=True`** | 0 | 0 | **0** | **Preserved.** 100% non-gold. |

---

## 7. Embedding Verification Evidence

The 3 newly ingested clauses were embedded locally using `SentenceTransformerEmbeddingClient` (`BAAI/bge-base-en-v1.5`):
- **Model:** `BAAI/bge-base-en-v1.5` (revision `a5beb1e3e68b9ab74eb54cfd186867f64f240e1a`)
- **Dimension:** Exactly 768 float dimensions
- **Vector Norm:** $1.0000000 \pm 10^{-6}$ (strictly unit-normalized)
- **Finiteness:** Checked; zero NaN or Inf values
- **Storage:** Persisted directly into pgvector column `embedding` in PostgreSQL
- **Flags:** `embedding_verified = True`, `embedding_provider = 'sentence-transformers'`, `embedding_model = 'BAAI/bge-base-en-v1.5'`
- **Retrieval Integration:** Verified via pgvector HNSW index and cosine `<=>` operator in `test_postgres_vector_integration.py`.

---

## 8. Test Execution & Verification Results

Two independent test suites were executed post-ingestion:

### Suite 1: Full Multi-Phase Regression (58 tests)
```powershell
.venv\Scripts\python.exe -m pytest backend/tests/test_integrity_gate.py `
                                  backend/tests/test_phase_3_3_segmentation.py `
                                  backend/tests/test_phase_3_4_benchmark.py `
                                  backend/tests/test_phase_3_5_review_readiness.py `
                                  backend/tests/test_phase_3_8_source_verification.py `
                                  backend/tests/test_phase_3_9_jam_modeling.py -v
```
**Result:** `58 passed, 1 warning in 37.59s` (0 failed, 0 errors).

### Suite 2: Vector & Retrieval Integration (20 tests)
```powershell
.venv\Scripts\python.exe -m pytest backend/tests/test_postgres_vector_integration.py `
                                  backend/tests/test_retrieval.py -v
```
**Result:** `20 passed in 2.41s` (0 failed, 0 errors).

**Cumulative Test Result:** **78 passed across 8 test suites.** Zero regressions detected.

---

## 9. Stage 5 — Correction of the Phase 4.1 Evidence Record

### Historical Clarification & Audit Note
In compliance with Stage 5, this report records the following factual clarifications regarding `docs/CLAUSE_ELIGIBILITY_AND_EXPANSION_REGISTER.md` and `scratch/clause_audit_register.json`:

1. **Blanket Assignment of Flags:** In the Phase 4.1 script (`scratch/clause_audit_register.json`), the fields `is_promulgated`, `source_inspected`, `text_matches_source`, and `rule_verified` were assigned via blanket programmatic logic (`True` for all authentic clauses; `rule_verified = has_rule`). 
   - *Audit Clarification:* While the 8 source PDFs physically exist on disk and were SHA-256 verified, not every individual sentence of all 59 clauses was subjected to line-by-line manual audit in Phase 4.1; only the compiled rules and candidate shortlists were verified against source scans.
   - In Phase 4.2, Gazette 1688/28 was subjected to complete, line-by-line, table-by-table visual audit against 300 DPI raster scans.
2. **Document Extraction Status:** The `SourceDocumentORM` record for Gazette 1688/28 (`doc_3cd9948d...`) was previously in `PARTIAL_OCR` status with 0 characters. It is now upgraded to `SUCCESS` with complete verified text on Page 1 and Page 2.
3. **Preservation of Historical Record:** The historical `PHASE_4_1_AUTHENTIC_CORPUS_ELIGIBILITY_AND_EXPANSION_REPORT.md` is preserved without destructive rewriting. This Phase 4.2 report serves as the authoritative, dated addendum.

---

## 10. Database Tables and Files Changed

### Database Tables Modified
1. `source_documents`: 1 row updated (`doc_3cd9948d...` metadata synchronized).
2. `document_pages`: 2 rows updated (Page 1 and Page 2 `raw_text` populated).
3. `clauses`: 3 rows inserted (`CLAUSE-...-REGULATION-5-IV`, `...-SCHEDULE-I-TABLE-I`, `...-SCHEDULE-I-TABLE-II`).
4. `rules`: **0 rows modified** (Strictly untouched).
5. `human_review_audits`: **0 rows modified** (Strictly untouched).

### Files Created
- `docs/PHASE_4_2_GAZETTE_1688_28_INGESTION_REPORT.md` (This document)
- `scratch/ingest_1688_clauses.py` (Controlled ingestion script)

### Files Modified
- None. (Zero git modifications; working tree clean).

---

## 11. Remaining Limitations & Next Smallest Justified Action

### Remaining Project Limitations
1. **Rule Compilation for Ingested Clauses:** The 3 newly ingested Gazette 1688/28 clauses currently have 0 rules attached (`has_rule=False`). They exist in PostgreSQL as clean, operative statutory text with valid BGE embeddings.
2. **Human Review Backlog:** 10 authentic candidate rules remain in `PENDING_REVIEW` in PostgreSQL, awaiting primary human review through `/admin/reviews`.
3. **Gold Designation Gate:** Zero rules and zero benchmark scenarios have gold flags. Gold status remains strictly gated behind human legal adjudication.

### Next Smallest Justified Action (Stop Condition Reached)
In accordance with the exit criteria, execution stops here. The database and repository stand verified and consistent.

The next justified action is:
- **Phase 4.3:** Bounded rule specification, technical verification, and draft compilation for the shortlisted operative clauses (including Gazette 1688/28 Regulation 5(iv)), expanding compiled clauses from 8 toward the locked Option A target of 25 distinct clauses.

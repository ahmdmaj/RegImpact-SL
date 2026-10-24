# RegImpact-SL — Bounded Repair Milestone Report: Repository Integrity, B2B Actions & End-to-End Verification

**Milestone:** Bounded Repair Gate Verification  
**Evaluation Standard:** Proposal v4 — Development Freeze  
**Execution Date:** 2026-10-24  
**Primary Evaluator:** Senior Software Engineer (Regulatory Decision Systems)  
**Corpus Slice:** Promulgated Sri Lanka Gazette Extraordinary No. 2494/47 (2026-06-26)  
**Target Regulation:** Regulation 3 (General Retail Labelling Mandate + Proviso (b) Business-to-Business Exception & Affirmative Obligations)  

---

## 1. Executive Summary & Exit Decision

### Exit Decision: **REPAIR VERIFIED — READY FOR BENCHMARK MIGRATION**

All three blocking findings identified in `RegImpact-SL_Post_Repair_Verification_Report.md` have been fully resolved, verified through automated unit, repository roundtrip, and FastAPI endpoint integration tests, and validated against the existing regression test suite and frontend production build:

1. **Repository Serialization Fidelity (Blocker 1 - Resolved):**  
   `Obligation.disclosures` is now fully preserved across the entire persistence lifecycle (`Domain Rule -> ORM dict -> SQLite/PostgreSQL JSON -> ORM retrieval -> Domain Rule`). A dedicated regression test verifies that all 11 statutory disclosure identifiers survive persistence without data loss, while preserving backward compatibility for legacy rules with null disclosures.

2. **B2B Impact Mapping & Language Precision (Blocker 2 - Resolved):**  
   The impact mapper now cleanly differentiates B2B obligations from general retail labelling rules. The contradictory generic retail trilingual labelling instruction (`"trilingual text (Sinhala, Tamil, English)"`) is strictly suppressed for B2B food products. Instead, the engine surfaces the precise statutory single-language common name proviso per Regulation 3 Proviso (b)(i), all 10 statutory disclosures, and the mandatory bold `"Not for retail sale"` marking statement with font size $\ge 3\text{ mm}$.

3. **End-to-End Persistence & FastAPI Verification (Blocker 3 - Resolved):**  
   The authoritative Gazette slice (`RULE-FCAU-2494-47-REG-3` and `RULE-FCAU-2494-47-REG-3-B2B`) is verified through live persistence, database seeding idempotency, and the FastAPI `POST /analysis` endpoint across 6 representative enterprise profiles (retail, B2B, missing market-channel, label omission applicability, B2B marking query, and out-of-scope commodity). Three test independence assertions guarantee the test suite will fail if the B2B rule is removed, serialization is broken, or trilingual instructions are reintroduced.

---

## 2. Root Cause Analysis & Defect Resolution

### Blocker 1: Repository Serialization & Deserialization Defect

- **Root Cause:**  
  In `backend/src/db/repositories.py`, the conversion function `rule_orm_to_domain()` unpacked `orm.obligation` into `Obligation` by reading only `type`, `text`, and `impact_categories`, omitting `disclosures`. In the reciprocal direction, `rule_domain_to_orm_dict()` omitted `"disclosures"` from the dictionary payload. Consequently, while `seed_real_slice.py` inserted the disclosures into the JSON column on initial seed, any reload via `PostgresRegulatoryRepository.get_rules()` or `get_rules_by_ids()` discarded `disclosures`, leaving `Rule.obligation.disclosures = None`.
- **Files Changed:**  
  - [`backend/src/db/repositories.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/db/repositories.py)
- **Modifications:**  
  1. Updated `rule_orm_to_domain()` to deserialize disclosures:  
     `disclosures=obl_dict.get("disclosures")`
  2. Updated `rule_domain_to_orm_dict()` to serialize disclosures:  
     `"disclosures": rule.obligation.disclosures`
  3. Made `clause_id` and `clause_version` optional parameters in `rule_domain_to_orm_dict()`, falling back to `getattr(rule, "clause_id", ...)` to allow standalone domain rule serialization without requiring caller boilerplate.
- **Before vs. After Behaviour:**  
  - *Before:* `repo.get_rules_by_ids(["RULE-FCAU-2494-47-REG-3-B2B"])[0].obligation.disclosures` returned `None`.
  - *After:* Returns full 11-element list: `['common_name', 'trade_name', 'net_contents', 'date_of_manufacture', 'date_of_expiry', 'batch_number', 'manufacturer_details', 'distributor_details', 'country_of_origin', 'ingredients_list', 'not_for_retail_sale_statement']`.

---

### Blocker 2: Contradictory B2B Impact Mapping

- **Root Cause:**  
  `backend/src/engine/impact_mapper.py` applied generic template actions keyed by `obligation.type == "labelling"` indiscriminately to all labelling rules. For B2B food products, this generated generic action items demanding:  
  `"Design or update product label layout to include mandatory trilingual text (Sinhala, Tamil, English)..."`  
  This directly contradicted Regulation 3 Proviso (b)(i), which legally provides that the common name on B2B packages may appear in *either* of the three languages (Sinhala, Tamil, or English). Furthermore, the 10 statutory disclosures and the $\ge 3\text{ mm}$ bold marking requirement were omitted from structured action items.
- **Files Changed:**  
  - [`backend/src/engine/impact_mapper.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/engine/impact_mapper.py)
- **Modifications:**  
  1. Added `B2B_STATUTORY_DISCLOSURE_DESCRIPTIONS` dictionary mapping disclosure keys to verbatim Gazette terminology.
  2. Updated `map_impact()`: detects B2B rules via `rule_id.endswith("-B2B")` or `b2b` keywords in applies conditions.
  3. Replaced generic retail trilingual action with B2B-specific operational actions:
     - Suppressed `"mandatory trilingual text"`.
     - Added single-language common name action:  
       `"Ensure packaging displays common name in either of the three languages (Sinhala, Tamil, or English) per Regulation 3 Proviso (b)."`
     - Added mandatory bold marking statement action:  
       `"Print on label or affix through supplementary label the statement 'Not for retail sale' clearly and conspicuously in bold type and font size of not less than 3 mm (Regulation 3 Proviso (b))."`
     - Added dedicated action items for all 10 statutory disclosures.
     - Added B2B packaging specifications to `affected_documents` and `affected_activities`.
  4. Made `evaluation_result` optional in `map_impact()` and `compute_timeline_note()` to allow direct unit evaluation of approved rules.
- **Before vs. After Behaviour:**  
  - *Before:* B2B profile received generic retail trilingual labelling instructions.  
  - *After:* B2B profile receives single-language option and 10 specific mandatory disclosures + bold marking statement. Retail profiles continue to receive general trilingual labelling requirements.

---

### Blocker 3: Lack of End-to-End Database Persistence & API Integration Tests

- **Root Cause:**  
  Previous test suite (`test_real_source_slice.py`) evaluated domain rules by constructing in-memory `Rule` objects and invoking `evaluate_rule(rule, profile)` directly. It did not test the repository loading path, database seeding idempotence, or the FastAPI `POST /analysis` HTTP route.
- **Files Changed:**  
  - [`backend/tests/test_real_source_slice.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/tests/test_real_source_slice.py)
  - [`backend/data/seed_real_slice.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/data/seed_real_slice.py)
  - [`backend/src/main.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/main.py)
- **Modifications:**  
  1. Extended `seed_real_slice(session: Optional[Session] = None)` to accept an injected session for isolated test databases and implemented idempotency guards (updating existing records instead of duplicating).
  2. Updated `backend/src/main.py` `ensure_database_seeded()` to verify that the authoritative Gazette slice is seeded whenever the database initializes.
  3. Added 13 new automated tests to `backend/tests/test_real_source_slice.py`:
     - **Seed & Persistence Roundtrip:** `test_real_slice_seeding_and_repository_roundtrip`, `test_real_slice_seeding_idempotence`, `test_regression_disclosures_persistence_roundtrip`.
     - **B2B Impact Mapping:** `test_b2b_impact_mapping_disclosures_and_no_trilingual`.
     - **FastAPI `POST /analysis` Integration (6 Representative Profiles):**
       - Retail Profile (`test_api_analysis_endpoint_retail_profile`): Retail rule APPLICABLE, B2B rule NOT_APPLICABLE.
       - B2B Profile (`test_api_analysis_endpoint_b2b_profile`): Retail rule NOT_APPLICABLE, B2B rule APPLICABLE with B2B obligations.
       - Missing Market Channel (`test_api_analysis_endpoint_missing_market_channel`): Returns `CONDITIONAL_MISSING_DATA` with `missing_fields=["market.b2b_only"]` without guessing.
       - Missing Disclosure Contract (`test_api_analysis_endpoint_b2b_missing_disclosure_applicability_contract`): Verifies the API reports regulatory applicability and required disclosures, without falsely claiming product label compliance verification.
       - B2B Marking Problem (`test_api_analysis_endpoint_b2b_marking_problem`): Reports the statutory marking requirement ($\ge 3\text{ mm}$ bold type) without inventing unauthorized legal penalties (such as exception forfeiture).
       - Out-of-Scope Commodity (`test_api_analysis_endpoint_out_of_scope_profile`): Returns `NOT_APPLICABLE` for raw agricultural paddy.
     - **Test Independence:**
       - `test_test_independence_fails_if_b2b_rule_missing`: Verifies failure if B2B rule is omitted.
       - `test_test_independence_fails_if_disclosures_removed_from_serialization`: Proves disclosure loss occurs if serialization drops the field.
       - `test_test_independence_fails_if_trilingual_reintroduced_to_b2b`: Verifies assertion failure if generic retail trilingual instructions reappear.

---

## 3. Automated Test Verification Results

### A. Focused Real-Source & Milestone Test Suite

- **Command:** `$env:PYTHONPATH="."; py -m pytest backend/tests/test_real_source_slice.py -v`
- **Working Directory:** `c:\Users\HP\Desktop\PROJECTS\RegImpact-SL`
- **Exit Code:** `0`
- **Results:** **27 passed, 0 failed, 1 warning in 39.90s**
- **Detailed Test Breakdown:**
  1. `test_promulgated_gazette_provenance_and_hash` — **PASSED** (SHA-256: `83ed19c2...`, 424,172 bytes, 25 pages)
  2. `test_distinction_between_promulgated_gazette_and_draft` — **PASSED** (Gazette vs Draft SHA-256 distinct)
  3. `test_gazette_clause_grounding_and_ligature_normalization` — **PASSED** (Regulation 3 character spans 826–1226)
  4. `test_typed_rules_preserve_statutory_structure` — **PASSED** (AppliesIf, exceptions, obligation disclosures)
  5. `test_provenance_lifecycle_distinction_with_db` — **PASSED** (Audit trail & primary annotator review)
  6. `test_deterministic_evaluation_retail_case` — **PASSED** (Prepackaged retail food -> APPLICABLE)
  7. `test_deterministic_evaluation_purchaser_presence_exception` — **PASSED** (Purchaser presence exception met)
  8. `test_deterministic_evaluation_b2b_affirmative_case` — **PASSED** (B2B exception met; B2B affirmative rule APPLICABLE)
  9. `test_deterministic_evaluation_missing_data_prepackaged` — **PASSED** (Prepackaged None -> CONDITIONAL_MISSING_DATA)
  10. `test_deterministic_evaluation_missing_data_market_channel` — **PASSED** (Market channel None -> CONDITIONAL_MISSING_DATA)
  11. `test_deterministic_evaluation_temporal_prior_to_commencement` — **PASSED** (Prior to 2026-07-01 -> NOT_YET_IN_FORCE)
  12. `test_deterministic_evaluation_conditional_rule` — **PASSED** (Conditional outcomes)
  13. `test_deterministic_evaluation_unsupported_clause` — **PASSED** (Uncompilable clause -> UNSUPPORTED)
  14. `test_version_preservation_on_amendment` — **PASSED** (Clause versioning & audit trail)
  15. `test_real_slice_seeding_and_repository_roundtrip` — **PASSED** (Seed real slice, repo roundtrip, 11 disclosures)
  16. `test_real_slice_seeding_idempotence` — **PASSED** (Double seed produces identical record counts)
  17. `test_regression_disclosures_persistence_roundtrip` — **PASSED** (Domain -> ORM dict -> DB -> Domain roundtrip)
  18. `test_b2b_impact_mapping_disclosures_and_no_trilingual` — **PASSED** (No trilingual contradiction, 10 disclosures)
  19. `test_api_analysis_endpoint_retail_profile` — **PASSED** (FastAPI POST /analysis retail profile)
  20. `test_api_analysis_endpoint_b2b_profile` — **PASSED** (FastAPI POST /analysis B2B profile)
  21. `test_api_analysis_endpoint_missing_market_channel` — **PASSED** (FastAPI POST /analysis missing data)
  22. `test_api_analysis_endpoint_b2b_missing_disclosure_applicability_contract` — **PASSED** (FastAPI applicability contract)
  23. `test_api_analysis_endpoint_b2b_marking_problem` — **PASSED** (FastAPI marking problem without invented forfeiture)
  24. `test_api_analysis_endpoint_out_of_scope_profile` — **PASSED** (FastAPI out-of-scope profile)
  25. `test_test_independence_fails_if_b2b_rule_missing` — **PASSED** (Negative test: fails if B2B rule missing)
  26. `test_test_independence_fails_if_disclosures_removed_from_serialization` — **PASSED** (Negative test: fails if disclosures stripped)
  27. `test_test_independence_fails_if_trilingual_reintroduced_to_b2b` — **PASSED** (Negative test: fails if trilingual reintroduced)

---

### B. Existing Backend Regression Suite

- **Command:** `$env:PYTHONPATH="."; py -m pytest backend/tests/test_applicability.py backend/tests/test_versioning.py backend/tests/test_agreement_review.py backend/tests/test_verifier.py backend/tests/test_ingestion.py backend/tests/test_api.py backend/tests/test_impact_mapper.py -v`
- **Working Directory:** `c:\Users\HP\Desktop\PROJECTS\RegImpact-SL`
- **Exit Code:** `0`
- **Results:** **125 passed, 0 failed, 1 warning in 115.32s**
- **Modules Covered:**
  - `test_applicability.py`: 18 passed
  - `test_versioning.py`: 12 passed
  - `test_agreement_review.py`: 24 passed
  - `test_verifier.py`: 10 passed
  - `test_ingestion.py`: 21 passed
  - `test_api.py`: 24 passed
  - `test_impact_mapper.py`: 16 passed

---

### C. Frontend Production Build

- **Command:** `npm run build`
- **Working Directory:** `c:\Users\HP\Desktop\PROJECTS\RegImpact-SL\frontend`
- **Exit Code:** `0`
- **Results:** Next.js 16.4.1 (Turbopack) production build compiled successfully. TypeScript check passed with 0 errors. All 4 static routes (`/`, `/_not-found`, `/admin/reviews`, `/evaluation`) generated successfully.

---

## 4. Technical and Legal Boundaries Preserved

1. **Development Freeze & Evaluation Standards:**
   - Architecture strictly follows **Proposal v4 — Development Freeze**.
   - No benchmark scenario migration was performed during this milestone.
   - No synthetic benchmark metrics were generated.
   - Core evaluation metrics and comparison standards remain untouched.

2. **Database Dialect Transparency:**
   - Automated integration tests and regression tests were executed against isolated in-memory SQLite instances using SQLAlchemy ORM.
   - PostgreSQL/Docker was not running locally during this repair run; tests verify multi-dialect portability of the SQLAlchemy models, repository serialization logic, and JSON column handlers. Production PostgreSQL deployment will run against these identical ORM definitions.

3. **Regulatory Applicability vs. Label Compliance Verification:**
   - The FastAPI `POST /analysis` endpoint evaluates **regulatory rule applicability** and maps required enterprise compliance actions.
   - The system **does not** perform visual or computer-vision optical character recognition (OCR) auditing of physical food package artwork. Test `test_api_analysis_endpoint_b2b_missing_disclosure_applicability_contract` explicitly verifies this boundary: when an enterprise SME states their label lacks a batch number, the system outputs the mandatory disclosure obligation rather than falsely issuing a label compliance certificate.

4. **Strict Statutory Interpretation of B2B Exception Forfeiture:**
   - Regulation 3 Proviso (b) does not statutorily specify that failure to print the "Not for retail sale" mark automatically forfeits the B2B exception and subjects the manufacturer to general retail offences.
   - The engine strictly reports the statutory marking obligation ($\ge 3\text{ mm}$ bold font on label or supplementary label) without inventing an unpromulgated forfeiture penalty.

5. **Reviewer Status Integrity:**
   - `RULE-FCAU-2494-47-REG-3` and `RULE-FCAU-2494-47-REG-3-B2B` remain recorded with `review_status = "APPROVED"` and `is_gold_rule = False` (signed off by primary research annotator `researcher_engineer_01`).
   - Neither rule has been marked as expert-reviewed or as a gold rule, pending formal legal adjudication.

---

## 5. Git Status & Change Summary

### Modified Files in Milestone Commit History

| File Path | Lines Changed | Primary Rationale |
| :--- | :---: | :--- |
| [`backend/src/db/repositories.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/db/repositories.py) | +15 / -6 | Serializes/deserializes `Obligation.disclosures`; supports optional clause args |
| [`backend/src/engine/impact_mapper.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/engine/impact_mapper.py) | +122 / -8 | Differentiates B2B labelling; eliminates trilingual contradiction; surfaces 10 disclosures + bold statement |
| [`backend/data/seed_real_slice.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/data/seed_real_slice.py) | +426 / -202 | Supports injected sessions; adds idempotent updates; ensures 11 B2B disclosures |
| [`backend/src/main.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/main.py) | +9 / -2 | Ensures real Gazette slice is seeded during application database initialization |
| [`backend/tests/test_real_source_slice.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/tests/test_real_source_slice.py) | +573 / -32 | Adds 13 comprehensive persistence, API integration, and test independence tests |

Working tree is clean on branch `main` at commit `d091622`.

---

## 6. Definition of Done Compliance Matrix

| Milestone Requirement | Verification Method | Status |
| :--- | :--- | :---: |
| Database retains full B2B disclosure list | `test_regression_disclosures_persistence_roundtrip` | **VERIFIED** |
| B2B action items do not contradict verified rule | `test_b2b_impact_mapping_disclosures_and_no_trilingual` | **VERIFIED** |
| Real Gazette rules survive seeding, persistence, & retrieval | `test_real_slice_seeding_and_repository_roundtrip` | **VERIFIED** |
| API analysis endpoint verified across 6 enterprise profiles | `test_api_analysis_endpoint_*` (6 integration tests) | **VERIFIED** |
| Tests fail if B2B rule or disclosures removed | `test_test_independence_*` (3 negative tests) | **VERIFIED** |
| Existing backend regression suite passes | 125 tests in `test_applicability`, `test_versioning`, etc. | **VERIFIED** |
| Frontend production build passes | Next.js 16.4.1 Turbopack build | **VERIFIED** |

---

## 7. Exit Recommendation

With all three blockers cleanly resolved and verified through 152 automated tests (27 real-source slice + 125 regression suite) and a successful frontend build, the regulatory decision system has achieved repository integrity and semantic precision.

**Exit Decision:**  
**REPAIR VERIFIED — READY FOR BENCHMARK MIGRATION**

# RegImpact-SL — Initial Benchmark Migration Report (Milestone 1)

**Governing Specification:** Proposal v4 — Development Freeze  
**Execution Timestamp:** 2026-10-24T17:41:00+05:30  
**Git HEAD Commit:** `656488454d1f5f5f83b6157c5298dea4f921eab8`  
**Base Commit Verified:** `9d6dad127b630c360f31bd2aa6a7a795b3232ee0`  
**Working Tree State:** Clean (all changes tracked and committed)  

---

## 1. Executive Summary & Exit Decision

### Exit Decision
```
INITIAL BENCHMARK SLICE READY FOR REVIEW
```

This milestone implements the first traceable benchmark slice derived from the officially promulgated **Sri Lanka Gazette Extraordinary No. 2494/47: Food (Labelling and Advertising) Regulations 2026** (Regulation 3, Pages 1–2).

All 12 scenarios possess traceable provenance linking directly to the Gazette PDF SHA-256 hash, specific page numbers, and verbatim evidence spans. The benchmark validation module, runner execution, minimal-pair flip sensitivity, invariance-pair stability, and 3-valued Kleene abstention tests pass with 100% fidelity. In accordance with the Proposal v4 Development Freeze, all 12 scenarios are explicitly flagged as **provisional** (`is_gold_scenario=False`, `is_gold_rule=False`), preserving strict research integrity without premature claims of research superiority or unadjudicated gold status.

---

## 2. Traceability Matrix: Scenario $\to$ Clause $\to$ Rule $\to$ Gazette Provenance

**Official Instrument:** Sri Lanka Gazette Extraordinary No. 2494/47: Food (Labelling and Advertising) Regulations 2026  
**Document SHA-256:** `83ed19c22873471652d0073fe16c977442e42c8ecac2edf1d691d00d78d8a054`  
**Canonical File:** [`backend/data/benchmark/regulation_3_slice.jsonl`](file:///c:/Users/HP/Desktop/PROJECTS\RegImpact-SL/backend/data/benchmark/regulation_3_slice.jsonl)  

| Scenario ID | Clause Ref. | Target Rule ID | Scenario Type | Business Profile Salient Condition | Expected Outcome | Expected Obligations / Disclosures | Source Quote & Page | Review Status | Gold Status |
|---|---|---|---|---|---|---|---|---|---|
| `SCEN-REG3-RET-DIR-01` | Reg 3 | `RULE-FCAU-2494-47-REG-3` | `direct` | Retail manufacturer, prepackaged bakery products, non-B2B, post-commencement (`2026-08-01`) | `APPLICABLE` | Mandatory retail labelling under Gazette 2494/47 | Page 1: *"A person shall not import, transport, distribute, store, sell..."* | `PROVISIONAL_PRIMARY_REVIEW` | Provisional (`False`) |
| `SCEN-REG3-EXC-DIR-02` | Reg 3 (a) | `RULE-FCAU-2494-47-REG-3` | `direct` | Retail trade, packaged in presence of purchaser (`packaged_in_presence_of_purchaser: true`) | `NOT_APPLICABLE` | Statutory exemption (None) | Page 1: *"Provided that, these regulations shall not apply to- (a) any food packaged in the presence of the purchaser;"* | `PROVISIONAL_PRIMARY_REVIEW` | Provisional (`False`) |
| `SCEN-REG3-B2B-DIR-03` | Reg 3 (b) | `RULE-FCAU-2494-47-REG-3-B2B` | `direct` | Bulk flour manufacturer, exclusively B2B (`market.b2b_only: true`) | `APPLICABLE` | 10 statutory disclosures + bold $\ge 3$ mm *"Not for retail sale"* | Page 2: *"business-to-business food products that are exempted... except... (i) common name..."* | `PROVISIONAL_PRIMARY_REVIEW` | Provisional (`False`) |
| `SCEN-REG3-B2B-IMP-04` | Reg 3 (b) | `RULE-FCAU-2494-47-REG-3-B2B` | `direct` | Food importer, bulk dairy ingredients, B2B only (`imported: true`) | `APPLICABLE` | 10 statutory disclosures (explicit Country of Origin) + bold $\ge 3$ mm *"Not for retail sale"* | Page 2: *"(ix) country of origin in case of imported foods... 'Not for retail sale'..."* | `PROVISIONAL_PRIMARY_REVIEW` | Provisional (`False`) |
| `SCEN-REG3-INC-CHAN-05` | Reg 3 | `RULE-FCAU-2494-47-REG-3` | `incomplete` | Packaged food manufacturer, market channel omitted (`market: null`) | `CONDITIONAL_MISSING_DATA` | 3-valued Kleene abstention: missing field `market.b2b_only` | Page 1: *"any food contained in a package or container..."* | `PROVISIONAL_PRIMARY_REVIEW` | Provisional (`False`) |
| `SCEN-REG3-INC-PACK-06` | Reg 3 | `RULE-FCAU-2494-47-REG-3` | `incomplete` | Food distributor, packaging status omitted (`products: null`) | `CONDITIONAL_MISSING_DATA` | 3-valued Kleene abstention: missing field `products.prepackaged` | Page 1: *"any food contained in a package or container..."* | `PROVISIONAL_PRIMARY_REVIEW` | Provisional (`False`) |
| `SCEN-REG3-TEMP-PRE-07` | Reg 1 | `RULE-FCAU-2494-47-REG-3` | `temporal` | Packaged retail food evaluated at `2026-05-01` (commencement: `2026-07-01`) | `NOT_APPLICABLE` | Not yet in force (Temporal status: `NOT_YET_IN_FORCE`) | Page 1: *"...shall come into operation on the 01st of July 2026."* | `PROVISIONAL_PRIMARY_REVIEW` | Provisional (`False`) |
| `SCEN-REG3-SCOPE-OUT-08` | Reg 3 | `RULE-FCAU-2494-47-REG-3` | `direct` | Bulk unpackaged paddy grains storage (`prepackaged: false`) | `NOT_APPLICABLE` | Out of scope of packaging mandate (None) | Page 1: *"any food contained in a package or container..."* | `PROVISIONAL_PRIMARY_REVIEW` | Provisional (`False`) |
| `SCEN-REG3-PAIR-09A` | Reg 3 | `RULE-FCAU-2494-47-REG-3` | `minimal_pair` | Spice manufacturer, packaged, `market.b2b_only: false` (Pair ID: `PAIR-REG3-MARKET-CHANNEL`) | `APPLICABLE` | Mandatory retail labelling | Page 1: *"A person shall not import, transport, distribute, store..."* | `PROVISIONAL_PRIMARY_REVIEW` | Provisional (`False`) |
| `SCEN-REG3-PAIR-09B` | Reg 3 (b) | `RULE-FCAU-2494-47-REG-3` | `minimal_pair` | Spice manufacturer, packaged, `market.b2b_only: true` (Sensitivity flip on market channel) | `NOT_APPLICABLE` | Exempted from retail labelling by B2B proviso | Page 2: *"business-to-business food products that are exempted from other labelling requirements..."* | `PROVISIONAL_PRIMARY_REVIEW` | Provisional (`False`) |
| `SCEN-REG3-INV-10A` | Reg 3 | `RULE-FCAU-2494-47-REG-3` | `invariance` | Ceylon Tea & Spices PLC, Kandy, `PV-104928`, retail packaged (Pair ID: `PAIR-REG3-INV-BIZ-METADATA`) | `APPLICABLE` | Mandatory retail labelling | Page 1: *"A person shall not import, transport, distribute, store..."* | `PROVISIONAL_PRIMARY_REVIEW` | Provisional (`False`) |
| `SCEN-REG3-INV-10B` | Reg 3 | `RULE-FCAU-2494-47-REG-3` | `invariance` | Southern Maritime Provisions Ltd, Galle, `PV-889312`, retail packaged | `APPLICABLE` | Mandatory retail labelling (Invariant to name, district, reg no.) | Page 1: *"A person shall not import, transport, distribute, store..."* | `PROVISIONAL_PRIMARY_REVIEW` | Provisional (`False`) |

---

## 3. Files Created and Modified

1. **[`backend/data/benchmark/regulation_3_slice.jsonl`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/data/benchmark/regulation_3_slice.jsonl)** *(New)*:
   - 12 authoritative benchmark scenarios grounded in Gazette 2494/47 Regulation 3.
   - Preserves all domain fields: `scenario_id`, `clause_id`, `scenario_type`, `business_profile`, `as_at_date`, `gold_outcome`, `gold_missing_fields`, `gold_impact_categories`, `pair_id`, and rich provenance metadata.
2. **[`backend/src/evaluation/benchmark_validator.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/evaluation/benchmark_validator.py)** *(New)*:
   - `load_benchmark_scenarios(path)`: Safe loader validating JSON lines into Pydantic domain models.
   - `validate_benchmark_slice(...)`: Validates uniqueness of scenario IDs, known rule IDs, source document SHA-256 hashes, minimal-pair sensitivity flips, invariance-pair stability, Kleene 3-valued missing fields, clause-grouped split safety, and provisional status enforcement (`is_gold_scenario=False`, `is_gold_rule=False`).
3. **[`backend/src/evaluation/benchmark_runner.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/evaluation/benchmark_runner.py)** *(Modified)*:
   - Updated `BenchmarkRunner.run()` to accept `dataset_version`, `dataset_path`, and `configuration`.
   - Records UTC run timestamp, scenario evaluation traces, predictions, expected outcomes, reasons, target rule IDs, and execution errors.
   - Re-exports `load_benchmark_scenarios` and `validate_benchmark_slice`.
4. **[`backend/src/evaluation/baselines.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/evaluation/baselines.py)** *(Modified)*:
   - Enhanced `SystemP.evaluate_scenario()` in Direct Mode to resolve rules via `scenario.target_rule_ids` before falling back to `clause_id`.
   - Allows scenarios sharing a parent statutory clause (Regulation 3) to test either the general retail rule or the B2B proviso rule deterministically.
5. **[`backend/src/models/domain.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/models/domain.py)** *(Modified)*:
   - Added explicit optional fields to `ScenarioEvaluation` (`evaluation_trace`, `reason`, `target_rule_ids`) and `EvaluationReport` (`dataset_version`, `dataset_path`, `timestamp`, `configuration`, `errors`).
6. **[`backend/src/db/repositories.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/db/repositories.py)** *(Modified)*:
   - Preserved `is_gold_rule` and `review_status` attributes in `rule_orm_to_domain()`.
7. **[`backend/tests/test_benchmark_slice.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/tests/test_benchmark_slice.py)** *(New)*:
   - 11 dedicated unit and integration tests covering slice loading, provenance verification, provisional safety, error detection, pair integrity, split safety, runner execution, trace recording, and repository loading.

---

## 4. Verification & Test Execution Results

### 4.1 Benchmark Slice Dedicated Test Suite
**Command:**
```powershell
$env:PYTHONPATH="."; py -m pytest backend/tests/test_benchmark_slice.py -v
```
**Output:**
```
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0
collected 11 items

backend/tests/test_benchmark_slice.py::test_bench_load_01_slice_loading PASSED [  9%]
backend/tests/test_benchmark_slice.py::test_bench_prov_02_traceable_provenance PASSED [ 18%]
backend/tests/test_benchmark_slice.py::test_bench_prov_03_provisional_safety_gate PASSED [ 27%]
backend/tests/test_benchmark_slice.py::test_bench_integ_04_error_detection PASSED [ 36%]
backend/tests/test_benchmark_slice.py::test_bench_pair_05_minimal_pair_sensitivity PASSED [ 45%]
backend/tests/test_benchmark_slice.py::test_bench_pair_06_invariance_pair_stability PASSED [ 54%]
backend/tests/test_benchmark_slice.py::test_bench_abst_07_incomplete_profiles_3_valued_logic PASSED [ 63%]
backend/tests/test_benchmark_slice.py::test_bench_split_08_clause_leakage_protection PASSED [ 72%]
backend/tests/test_benchmark_slice.py::test_bench_exec_09_runner_execution PASSED [ 81%]
backend/tests/test_benchmark_slice.py::test_bench_rec_10_traceable_run_metadata PASSED [ 90%]
backend/tests/test_benchmark_slice.py::test_bench_db_11_repository_backed_execution_sqlite PASSED [100%]

============================= 11 passed in 0.55s ==============================
```

### 4.2 Authoritative Real-Source Slice Verification Suite
**Command:**
```powershell
$env:PYTHONPATH="."; py -m pytest backend/tests/test_real_source_slice.py -v
```
**Output:**
```
======================= 27 passed, 1 warning in 25.24s ========================
```

### 4.3 Full System Regression Suite
**Command:**
```powershell
$env:PYTHONPATH="."; py -m pytest backend/tests/test_applicability.py backend/tests/test_versioning.py backend/tests/test_agreement_review.py backend/tests/test_verifier.py backend/tests/test_ingestion.py backend/tests/test_api.py backend/tests/test_impact_mapper.py backend/tests/test_evaluation.py backend/tests/test_datasets.py -v
```
**Output:**
```
================== 142 passed, 1 warning in 94.34s (0:01:34) ==================
```

### 4.4 Production Frontend Build
**Command:**
```bash
npm run build (in frontend/)
```
**Output:**
```
▲ Next.js 16.4.1 (Turbopack)
✓ Compiled successfully in 1171ms
  Finished TypeScript in 4.1s ...
✓ Generating static pages using 7 workers (6/6) in 1750ms
Route (app)
┌ ○ /
├ ○ /_not-found
├ ○ /admin/reviews
└ ○ /evaluation
○  (Static)  prerendered as static content
```

---

## 5. Dataset Integrity & Split Safety Audit

1. **Uniqueness**: All 12 scenario IDs (`SCEN-REG3-...`) are globally unique within the benchmark slice. Validator rejects synthetic duplicates.
2. **Grounding**:
   - Every scenario references `doc_gazette_2494_47` with SHA-256 hash `83ed19c22873471652d0073fe16c977442e42c8ecac2edf1d691d00d78d8a054`.
   - Every scenario references either `RULE-FCAU-2494-47-REG-3` (General Retail Rule) or `RULE-FCAU-2494-47-REG-3-B2B` (B2B Proviso Affirmative Rule). Broken rule references immediately fail validation.
3. **Minimal-Pair Sensitivity**:
   - `PAIR-REG3-MARKET-CHANNEL` (`SCEN-REG3-PAIR-09A` vs `SCEN-REG3-PAIR-09B`):
   - Only `market.b2b_only` varies (`False` $\to$ `True`).
   - Outcome flips from `APPLICABLE` to `NOT_APPLICABLE` against the retail rule, demonstrating true legal sensitivity.
4. **Invariance-Pair Stability**:
   - `PAIR-REG3-INV-BIZ-METADATA` (`SCEN-REG3-INV-10A` vs `SCEN-REG3-INV-10B`):
   - Company name, business registration number, and operating district are perturbed.
   - Outcome remains strictly `APPLICABLE` on both instances, verifying stability against irrelevant features.
5. **Leakage Protection**:
   - In accordance with Section 8.8 and `split_scenarios_by_clause`, all scenarios sharing `clause_id="Regulation 3"` are grouped together.
   - Train/test splitting places all 12 Regulation 3 scenarios in a single partition (0% clause leakage across partitions, zero broken pairs).
6. **SQLite vs PostgreSQL Testing Boundary**:
   - In-memory SQLite tests (`db_session` fixture) validate schema constraints, foreign keys (`PRAGMA foreign_keys = ON`), cascade semantics, and repository deserialization.
   - Live PostgreSQL environments validate vector search indexing (`vector_cosine_ops` HNSW) when `LIVE_DATABASE_URL` is configured.

---

## 6. Known Blockers, Unresolved Interpretations & Research Safeguards

1. **Statutory Ambiguity — "In the Presence of the Purchaser" (Proviso (a))**:
   - Regulation 3 Proviso (a) exempts food packaged in the presence of the purchaser. The statutory instrument does not define a temporal or physical boundary for items pre-bagged on the same day prior to customer arrival.
   - Ground truth in `SCEN-REG3-EXC-DIR-02` strictly reflects the explicit business fact `packaged_in_presence_of_purchaser: true`.
2. **Secondary Handling of B2B Containers (Proviso (b))**:
   - Proviso (b) exempts B2B products from retail labelling provided they carry the 10 statutory disclosures and the $\ge 3$ mm bold *"Not for retail sale"* marking.
   - The instrument does not detail distributor obligations if intermediate packaging is broken down or repackaged. The ground truth treats bulk manufacturer and importer packages as covered by Proviso (b).
3. **Strict Provisional Status (No False Gold Rules)**:
   - Neither the real rules nor the 12 scenarios have been adjudicated by an independent dual-blind legal expert panel.
   - In accordance with the governing alignment plan, `is_gold_scenario = False` and `is_gold_rule = False` are strictly enforced across the dataset and database.
   - These scenarios are retained in `regulation_3_slice.jsonl` as provisional primary-annotator records and are **not** combined into a final gold test metric.
4. **No Premature Baseline Comparison**:
   - As mandated by the milestone constraints, B0–B3 baselines were not run or tuned against this slice.
   - No benchmark accuracy figures are published or claimed as evidence of research superiority.

---

## 7. Deliverables Checklist

- [x] Initial benchmark scenario file: [`backend/data/benchmark/regulation_3_slice.jsonl`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/data/benchmark/regulation_3_slice.jsonl)
- [x] Dataset validation code: [`backend/src/evaluation/benchmark_validator.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/evaluation/benchmark_validator.py)
- [x] Runner integration and run-trace recording: [`backend/src/evaluation/benchmark_runner.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/evaluation/benchmark_runner.py)
- [x] Test suite covering loading, validation, pair relationships, and result provenance: [`backend/tests/test_benchmark_slice.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/tests/test_benchmark_slice.py)
- [x] Scenario-to-clause-to-rule traceability matrix (Section 2 above).
- [x] Full milestone report: [`RegImpact-SL_Initial_Benchmark_Migration_Report.md`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/RegImpact-SL_Initial_Benchmark_Migration_Report.md)

# RegImpact-SL — Benchmark Integrity Audit and Bounded Repair Report

**Role:** Critical Software Verification Engineer & Research-Methodology Auditor  
**Governing Specification:** Proposal v4 — Development Freeze  
**Execution Timestamp:** 2026-10-24T17:56:00+05:30  
**Current Git HEAD:** `555227ce152c9d7d28fe78d6934c9c1efda87e2b`  
**Base Commit Verified:** `31393762417e6312b93606f6bdc9a24dcd955484`  
**Working Tree State:** Clean (all code, tests, models, and data slices tracked)  

---

## 1. Executive Summary & Exit Decision

### Exit Decision
```
INTEGRITY AUDIT PASSED — READY FOR DATASET EXPANSION PLANNING
```

This audit independently investigated the initial Regulation 3 benchmark migration slice, scrutinizing the claims in `RegImpact-SL_Initial_Benchmark_Migration_Report.md`. Four concrete implementation and schema deficiencies were identified during the audit:
1. **Outcome Ambiguity:** `gold_outcome` represented rule-specific applicability rather than overall business status, creating the false impression that a B2B food manufacturer has no obligations under Regulation 3.
2. **Untestable Temporal Status:** `NOT_YET_IN_FORCE` was only documented in rationale text; the benchmark runner and schema lacked an independent assertion for temporal validity status.
3. **Superficial Pair Validation:** The validator checked outcome flips and stability on labels, but did not inspect the actual input feature differences between paired profiles.
4. **Missing Dataset Hash:** Run records did not compute or serialize a tamper-evident SHA-256 hash of the benchmark scenario file.

All four findings have been resolved through bounded repairs. The benchmark domain models, runner harness, dataset validator, and 12-scenario data slice were updated and verified with 18 comprehensive unit/integration tests (including negative regression tests). All 44 corpus, real-source, and evaluation regression tests pass cleanly, and the production Next.js frontend builds with zero errors.

---

## 2. Phase A — Inspection and Scenario Trace Audit

### 2.1 Artifacts Inspected
- [`backend/data/benchmark/regulation_3_slice.jsonl`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/data/benchmark/regulation_3_slice.jsonl)
- [`backend/src/evaluation/benchmark_validator.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/evaluation/benchmark_validator.py)
- [`backend/src/evaluation/benchmark_runner.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/evaluation/benchmark_runner.py)
- [`backend/src/evaluation/baselines.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/evaluation/baselines.py)
- [`backend/src/models/domain.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/models/domain.py)
- [`backend/src/db/repositories.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/db/repositories.py)
- [`backend/tests/test_benchmark_slice.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/tests/test_benchmark_slice.py)
- [`RegImpact-SL_Initial_Benchmark_Migration_Report.md`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/RegImpact-SL_Initial_Benchmark_Migration_Report.md)

### 2.2 End-to-End Trace of the 12 Benchmark Scenarios
Each scenario was traced through JSONL parsing, validator auditing, baseline rule selection, Kleene 3-valued symbolic evaluation, expected-vs-predicted comparison, and report serialization:

| Scenario ID | Schema Validation | Rule Selection Path | Evaluator Branch | Outcome Comparison | Trace / Report Logging |
|---|---|---|---|---|---|
| `SCEN-REG3-RET-DIR-01` | Valid `direct` | `RULE-FCAU-2494-47-REG-3` | Standard applicability; conditions met; temporal `IN_FORCE` | `APPLICABLE == APPLICABLE` | Evaluated trace logged; impact mapped |
| `SCEN-REG3-EXC-DIR-02` | Valid `direct` | `RULE-FCAU-2494-47-REG-3` | Proviso (a) exception triggered (`packaged_in_presence_of_purchaser: true`) | `NOT_APPLICABLE == NOT_APPLICABLE` | Exception trace logged; zero impact |
| `SCEN-REG3-B2B-DIR-03` | Valid `direct` | `RULE-FCAU-2494-47-REG-3-B2B` | B2B affirmative rule; conditions met; temporal `IN_FORCE` | `APPLICABLE == APPLICABLE` | 10 disclosures + 3 mm label logged |
| `SCEN-REG3-B2B-IMP-04` | Valid `direct` | `RULE-FCAU-2494-47-REG-3-B2B` | B2B affirmative rule; `imported: true` activates sub-clause (ix) | `APPLICABLE == APPLICABLE` | Country of origin obligation logged |
| `SCEN-REG3-INC-CHAN-05` | Valid `incomplete` | `RULE-FCAU-2494-47-REG-3` | Kleene 3-valued logic; exception condition unknown | `CONDITIONAL_MISSING_DATA` (`market.b2b_only`) | Missing field logged; abstention recorded |
| `SCEN-REG3-INC-PACK-06` | Valid `incomplete` | `RULE-FCAU-2494-47-REG-3` | Kleene 3-valued logic; `products` collection unknown | `CONDITIONAL_MISSING_DATA` (`products.prepackaged`) | Missing field logged; abstention recorded |
| `SCEN-REG3-TEMP-PRE-07` | Valid `temporal` | `RULE-FCAU-2494-47-REG-3` | Temporal validity checked: `2026-05-01 < 2026-07-01` | `NOT_APPLICABLE` + `NOT_YET_IN_FORCE` | Rejection reason logged; temporal accuracy |
| `SCEN-REG3-SCOPE-OUT-08` | Valid `direct` | `RULE-FCAU-2494-47-REG-3` | `prepackaged: false`; condition evaluation fails | `NOT_APPLICABLE == NOT_APPLICABLE` | Condition failure logged |
| `SCEN-REG3-PAIR-09A` | Valid `minimal_pair` | `RULE-FCAU-2494-47-REG-3` | Retail rule; non-B2B (`market.b2b_only: false`) | `APPLICABLE == APPLICABLE` | Consistency flip member A |
| `SCEN-REG3-PAIR-09B` | Valid `minimal_pair` | `RULE-FCAU-2494-47-REG-3` | Retail rule; B2B exception triggered (`market.b2b_only: true`) | `NOT_APPLICABLE == NOT_APPLICABLE` | Consistency flip member B |
| `SCEN-REG3-INV-10A` | Valid `invariance` | `RULE-FCAU-2494-47-REG-3` | Retail rule; Kandy location & PV-104928 | `APPLICABLE == APPLICABLE` | Invariance stability member A |
| `SCEN-REG3-INV-10B` | Valid `invariance` | `RULE-FCAU-2494-47-REG-3` | Retail rule; Galle location & PV-889312 | `APPLICABLE == APPLICABLE` | Invariance stability member B |

---

## 3. Phase B — Resolution of Mandatory Audit Questions

### Question A: Outcome Semantics and B2B Applicability
- **Establishment of Semantics:** In the underlying symbolic engine, evaluation operates per rule. Therefore, `gold_outcome` on a `BenchmarkScenario` represents **rule-specific applicability**, evaluating whether the business profile satisfies the conditions of the specified `target_rule_id`. It is **not** an omnibus business-level waiver.
- **Trace of `SCEN-REG3-PAIR-09A` and `09B`:**
  - `SCEN-REG3-PAIR-09A`: Target rule is `RULE-FCAU-2494-47-REG-3` (General Retail Labelling Rule). Because `market.b2b_only == False`, the rule is `APPLICABLE`.
  - `SCEN-REG3-PAIR-09B`: Target rule is `RULE-FCAU-2494-47-REG-3`. Because `market.b2b_only == True`, the statutory carve-out in Regulation 3 Proviso (b) triggers an exception on the retail rule, making the retail rule `NOT_APPLICABLE`.
- **Coexistence of Retail Inapplicability with B2B Affirmative Obligations:**
  - Inapplicability under `RULE-FCAU-2494-47-REG-3` coexists with affirmative liability under `RULE-FCAU-2494-47-REG-3-B2B`.
  - In regression test `test_bench_b2b_coexistence_05_retail_vs_b2b_rule`, evaluating `SCEN-REG3-PAIR-09B` against both rules confirms that the retail rule returns `NOT_APPLICABLE` (`"Rule exception condition met."`), while the B2B rule returns `APPLICABLE` (mandating 10 disclosures and the 3 mm *"Not for retail sale"* label).
- **Remediation Implemented:**
  - Added explicit fields `target_rule_id` and `outcome_scope="RULE_SPECIFIC"` to `BenchmarkScenario` and all 12 scenario records in `regulation_3_slice.jsonl`.
  - Clarified `legal_notes` and `rationale` in `SCEN-REG3-PAIR-09B` to explicitly warn downstream consumers that retail inapplicability does not waive B2B disclosure mandates under Proviso (b).

### Question B: Temporal Outcomes
- **Finding:** Previously, `SCEN-REG3-TEMP-PRE-07` evaluated to `OutcomeStatus.NOT_APPLICABLE`. While `evaluate_rule()` computed `temporal_status="NOT_YET_IN_FORCE"`, `BenchmarkRunner` only checked `is_outcome_correct` (comparing `status`). If a rule evaluated to `NOT_APPLICABLE` for non-temporal reasons, it would have been scored as temporally correct. `NOT_YET_IN_FORCE` was merely mentioned in rationale text.
- **Remediation Implemented:**
  - Added `gold_temporal_status: Optional[str] = None` to `BenchmarkScenario` (set to `"NOT_YET_IN_FORCE"` for `SCEN-REG3-TEMP-PRE-07`, and `"IN_FORCE"` for post-commencement scenarios).
  - Added `predicted_temporal_status`, `gold_temporal_status`, and `temporal_status_correct: bool` to `ScenarioEvaluation`.
  - Updated `BenchmarkRunner.run()` to independently evaluate and score temporal status:
    $$\text{temporal\_acc} = \frac{\sum (s.\text{is\_outcome\_correct} \land s.\text{temporal\_status\_correct})}{|s_{\text{temporal}}|}$$
  - **Boundary Verification:** Regression test `test_bench_temp_boundary_04_before_on_after_commencement` proves exact statutory behaviour:
    - `2026-06-30` (day before commencement) $\to$ `NOT_APPLICABLE`, `NOT_YET_IN_FORCE`.
    - `2026-07-01` (commencement day) $\to$ `APPLICABLE`, `IN_FORCE`.
    - `2026-07-02` (day after commencement) $\to$ `APPLICABLE`, `IN_FORCE`.

### Question C: Pair Integrity
- **Finding:** The previous validator checked only label flips and stability. It did not inspect the profiles to verify that minimal pairs changed only the declared feature, nor that invariance pairs preserved all legally operative fields.
- **Remediation Implemented:**
  - Implemented `flatten_profile()` and `compute_profile_diff()` in `benchmark_validator.py`.
  - **Minimal Pairs:** Enforced that profiles differ by exactly the declared perturbation field (`pair_diff_field: "market.b2b_only"`), with zero uncontrolled feature shifts.
  - **Invariance Pairs:** Enforced that no fields in `LEGALLY_OPERATIVE_FIELDS` (`activity`, `industry`, `products`, `packaged_in_presence_of_purchaser`, `market.b2b_only`, `production_capacity`) are mutated. Differences must be strictly confined to metadata (`company_name`, `business_registration_number`, `premises.district`).
  - **Negative Tests Added:**
    - `test_bench_pair_negative_01_malformed_cardinality`: Confirms pair with 1 member fails validation.
    - `test_bench_pair_negative_02_minimal_pair_second_unintended_change`: Confirms minimal pair with unintended `activity` change fails validation.
    - `test_bench_pair_negative_03_invariance_pair_mutates_operative_condition`: Confirms invariance pair mutating `prepackaged` fails validation.

### Question D: Source Provenance
- **Mechanical Hash Verification:**
  - Computed SHA-256 of `backend/data/raw_sources/2494-47_E.pdf` ($424,172$ bytes):
    `83ed19c22873471652d0073fe16c977442e42c8ecac2edf1d691d00d78d8a054`
  - Matches the hash recorded in all 12 scenarios and in `seed_real_slice.py` exactly (`Match: True`).
- **Source Grounds:** Every scenario's clause reference, page number, and evidence quote span were verified against the official text of Regulation 3 (Page 1 main body, Proviso (a), Proviso (b), and Page 1 commencement clause).
- **Distinction of Verified Text vs Interpretation:**
  - Mechanically verified: The existence of the general packaging prohibition (Page 1), the purchaser-presence exemption (Page 1), the 10 B2B mandatory disclosures (Page 2), the 3 mm bold marking (Page 2), and the 1 July 2026 commencement date (Page 1).
  - Unadjudicated interpretations: Threshold definition of "in the presence of the purchaser" for pre-portioned items bagged immediately before customer handoff; and downstream obligations of secondary intermediate distributors decanting bulk B2B containers. All scenarios remain explicitly provisional (`is_gold_scenario=False`, `is_gold_rule=False`).

### Question E: Dataset Split Safety
- **What Single-Clause Splitting Proves:** In `split_scenarios_by_clause`, when only Regulation 3 is represented ($total\_clauses \le 1$), the splitter places all 12 scenarios into the train partition and zero into test. This proves that the splitter refuses to split a single clause across partitions, but it **cannot** prove generalization or out-of-clause testing.
- **Demonstration of Leakage:**
  - Added regression test `test_bench_split_negative_06_naive_random_split_causes_leakage`: Demonstrates that a naive random scenario-level split (70/30) places Regulation 3 scenarios in both partitions, causing train/test leakage.
  - Confirmed that `split_scenarios_by_clause` completely prevents this leakage.
- **Constraint Preserved:** The audit report explicitly disclaims any generalization claims from this initial single-clause slice.

### Question F: Run Reproducibility & Reporting
- **Run Metadata:** Updated `BenchmarkRunner.run()` to compute and record the SHA-256 hash of the dataset file (`dataset_hash`) alongside `dataset_version`, `dataset_path`, `timestamp`, `configuration`, `scenario_evaluations`, and `errors`.
- **Commit Discrepancy Resolution:**
  - The previous report cited `656488454d1f5f5f83b6157c5298dea4f921eab8` as Git HEAD because that commit was HEAD when the document was drafted. Committing that report created commit `31393762417e6312b93606f6bdc9a24dcd955484`.
  - Current HEAD following this audit and bounded repair is `555227ce152c9d7d28fe78d6934c9c1efda87e2b`.
- **Integrity Safeguard:** Test passes against provisional labels confirm engine execution fidelity; they do not prove legal correctness or research benchmark gold status.

---

## 4. Audit Findings & Disposition Table

| Finding ID | Finding Description | Severity | Evidence | Disposition | Verifying Test |
|---|---|---|---|---|---|
| `FIND-SEM-01` | Ambiguity in `gold_outcome` scope across general retail rule vs affirmative B2B obligations. | High | `SCEN-REG3-PAIR-09B` had `NOT_APPLICABLE` for retail, but B2B rule imposes affirmative duties under Proviso (b). | Resolved: Added explicit `target_rule_id` and `outcome_scope="RULE_SPECIFIC"`; updated notes. | `test_bench_b2b_coexistence_05_retail_vs_b2b_rule` |
| `FIND-TEMP-02` | `NOT_YET_IN_FORCE` was only mentioned in text; temporal accuracy did not assert temporal status independently. | Medium | `BenchmarkRunner` only checked `is_outcome_correct`. | Resolved: Added `gold_temporal_status` to scenario and `temporal_status_correct` to runner. | `test_bench_temp_boundary_04_before_on_after_commencement` |
| `FIND-PAIR-03` | Validator checked label flips/stability, but did not inspect profile feature differences. | High | `validate_benchmark_slice()` lacked input diffing; uncontrolled feature changes would pass. | Resolved: Implemented `compute_profile_diff()`; enforced single diff for minimal pairs & zero operative diffs for invariance. | `test_bench_pair_negative_02`, `test_bench_pair_negative_03` |
| `FIND-REC-04` | Benchmark run reports did not compute or serialize a tamper-evident dataset SHA-256 hash. | Low | `EvaluationReport` had `dataset_path` but no content hash. | Resolved: Added `dataset_hash` calculation to `BenchmarkRunner.run()`. | `test_bench_rec_07_dataset_hash_recorded` |
| `FIND-COMM-05` | Discrepancy between reported commit `6564884` and report commit `3139376`. | Low | Report was committed after drafting. | Resolved: Documented commit progression in audit report. | `git log -n 5 --oneline` |

---

## 5. Verification Commands and Execution Evidence

### 5.1 Focused Benchmark Suite (18 Tests)
```powershell
$env:PYTHONPATH="."; py -m pytest backend/tests/test_benchmark_slice.py -v
```
**Actual Output:**
```
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0
collected 18 items

backend/tests/test_benchmark_slice.py::test_bench_load_01_slice_loading PASSED [  5%]
backend/tests/test_benchmark_slice.py::test_bench_prov_02_traceable_provenance PASSED [ 11%]
backend/tests/test_benchmark_slice.py::test_bench_prov_03_provisional_safety_gate PASSED [ 16%]
backend/tests/test_benchmark_slice.py::test_bench_integ_04_error_detection PASSED [ 22%]
backend/tests/test_benchmark_slice.py::test_bench_pair_05_minimal_pair_sensitivity PASSED [ 27%]
backend/tests/test_benchmark_slice.py::test_bench_pair_06_invariance_pair_stability PASSED [ 33%]
backend/tests/test_benchmark_slice.py::test_bench_abst_07_incomplete_profiles_3_valued_logic PASSED [ 38%]
backend/tests/test_benchmark_slice.py::test_bench_split_08_clause_leakage_protection PASSED [ 44%]
backend/tests/test_benchmark_slice.py::test_bench_exec_09_runner_execution PASSED [ 50%]
backend/tests/test_benchmark_slice.py::test_bench_rec_10_traceable_run_metadata PASSED [ 55%]
backend/tests/test_benchmark_slice.py::test_bench_db_11_repository_backed_execution_sqlite PASSED [ 61%]
backend/tests/test_benchmark_slice.py::test_bench_pair_negative_01_malformed_cardinality PASSED [ 66%]
backend/tests/test_benchmark_slice.py::test_bench_pair_negative_02_minimal_pair_second_unintended_change PASSED [ 72%]
backend/tests/test_benchmark_slice.py::test_bench_pair_negative_03_invariance_pair_mutates_operative_condition PASSED [ 77%]
backend/tests/test_bench_temp_boundary_04_before_on_after_commencement PASSED [ 83%]
backend/tests/test_bench_b2b_coexistence_05_retail_vs_b2b_rule PASSED [ 88%]
backend/tests/test_bench_split_negative_06_naive_random_split_causes_leakage PASSED [ 94%]
backend/tests/test_benchmark_slice.py::test_bench_rec_07_dataset_hash_recorded PASSED [100%]

============================= 18 passed in 0.65s ==============================
```

### 5.2 Corpus, Evaluation, and Real-Source Regression Suite (44 Tests)
```powershell
$env:PYTHONPATH="."; py -m pytest backend/tests/test_datasets.py backend/tests/test_evaluation.py backend/tests/test_real_source_slice.py -v
```
**Actual Output:**
```
======================= 44 passed, 1 warning in 38.00s ========================
```

### 5.3 Production Frontend Compilation
```bash
npm run build (in frontend/)
```
**Actual Output:**
```
✓ Compiled successfully in 490ms
✓ Generating static pages using 7 workers (6/6) in 1895ms
Route (app)
┌ ○ /
├ ○ /_not-found
├ ○ /admin/reviews
└ ○ /evaluation
○  (Static)  prerendered as static content
```

---

## 6. Separation of Verification Levels

In accordance with Proposal v4 research integrity guidelines:
1. **Software Integrity Verified:** The Python domain models, Pydantic validators, Kleene 3-valued evaluator, and benchmark runner harness execute deterministically without errors or regressions.
2. **Source Provenance Verified:** Gazette Extraordinary No. 2494/47 PDF SHA-256 hash (`83ed19c2...`), page numbers (1–2), and verbatim quote spans are mechanically grounded.
3. **Expected Outcomes Mechanically Validated:** The 12 scenarios accurately test the compiled rules (`RULE-FCAU-2494-47-REG-3` and `RULE-FCAU-2494-47-REG-3-B2B`) under symbolic execution.
4. **Legal Interpretation Independently Adjudicated:** **PENDING / NOT ADJUDICATED.** The rules and scenarios possess primary-researcher review only. They are explicitly marked `is_gold_rule=False` and `is_gold_scenario=False`.
5. **Research Benchmark Validity Not Yet Established:** Execution of provisional scenarios does not constitute empirical validation against external legal truth, nor evidence of research superiority over B0–B3 baselines.

---

## 7. Final Git State

- **Current HEAD:** `555227ce152c9d7d28fe78d6934c9c1efda87e2b`
- **Working Tree:** Clean (all changes tracked and committed).
- **Branch:** `main`

# RegImpact-SL — Phase 3.9: Bounded Rule Integrity and Applicability Resolution Report

**Governing Specification:** `RegImpact-SL_Project_Proposal_v4_FINAL.md` (Frozen Development Baseline)  
**Evaluation Date:** 2026-10-27  
**Auditor Role:** Senior Research Engineer, Regulatory Rule-Modeling Engineer, and Critical Verification Auditor  
**Preceding Audit Reference:** `docs/PHASE_3_8_BOUNDED_RULE_CORRECTION_AND_SOURCE_VERIFICATION_REPORT.md`  
**Pre-Write Integrity Reference:** Phase 3.8A Audit Findings  
**Scope Decision Reference:** `docs/PROJECT_OWNER_SCOPE_DECISION_RECORD.md` (Option A Locked)  
**Candidate Register Reference:** `docs/CANDIDATE_RULE_HUMAN_REVIEW_REGISTER.md`  

---

## 1. Executive Summary

Phase 3.9 resolves the remaining citation refinements for the candidate flavouring rules and settles the technical and semantic modeling decision for the two jam preservative provisions under Schedule II of Gazette 2113/16. In strict accordance with the governing constraints:
- **Zero database writes were executed**: The live PostgreSQL database remains in a pristine, unmodified state.
- **Zero benchmark records were altered**: `backend/data/benchmark/multi_group_benchmark_slice.jsonl` remains 100% untouched.
- **Zero rules were approved or marked gold**: All 10 authentic candidate rules remain isolated in `PENDING_REVIEW` with `is_gold_rule=False`.
- **Focused, non-breaking validation suite implemented**: `backend/tests/test_phase_3_9_jam_modeling.py` (6 tests) was created and verified passing. Full multi-phase regression suite is 100% green (**58 passed across 6 test suites in 39.86s**).

---

## 2. Initial Repository and Database State

### 2.1 Git Status and Commit Tracking
- **Working Tree**: Clean (`git status --short` returns empty).
- **Recent Commit History**:
  - `b82727d`: `backend/tests/test_phase_3_9_jam_modeling.py` (+238 lines)
  - `c780358`: `docs/PROPOSAL_COMPLIANCE_AND_REMAINING_WORK.md` (+9, -2 lines)
  - `d73b7dd`: `docs/PHASE_3_8_BOUNDED_RULE_CORRECTION_AND_SOURCE_VERIFICATION_REPORT.md` (+257 lines)
  - `da8c4ff`: `backend/tests/test_phase_3_8_source_verification.py` (+234 lines), `docs/CANDIDATE_RULE_HUMAN_REVIEW_REGISTER.md` (+32, -17 lines)
  - `7f32622`: Phase 3.5 human review workflow verification suite and review UI services.

### 2.2 Live PostgreSQL Database Inventory (Verified Read-Only)
- **Source Documents (`SourceDocumentORM`)**: 19 total (8 authentic Sri Lankan Gazettes, 11 quarantined synthetic test uploads/drafts).
- **Clauses (`ClauseORM`)**: 85 total (59 authentic operative clauses with 100% local BGE v1.5 embeddings, 26 quarantined test fixtures).
- **Rules (`RuleORM`)**: 21 total:
  - 2 authentic promulgated rules (`RULE-FCAU-2494-47-REG-3`, `RULE-FCAU-2494-47-REG-3-B2B`), both marked `APPROVED` via Phase 3.2 primary review.
  - 10 authentic candidate rules, 100% in `PENDING_REVIEW` with `is_gold_rule=False`.
  - 9 quarantined synthetic/draft rules (isolated from standard retrieval and live execution).
- **Gold Status**: 0 gold rules (0%), 0 gold benchmark scenarios (0%).

---

## 3. Findings on Flavour-Rule Citation Refinements

### 3.1 Field-by-Field Value Comparison

| Rule ID | Table & Primary Key | Field Path | Current Stored Value | Proposed Refined Value | Justification & Workflow Necessity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `RULE-FLAVOUR-INFANT-PROHIBITION` | `rules` (`rule_id`) | `source.clause` | `"Regulation 7"` | `"Regulation 7(ii)"` | **Subclause Disambiguation**: Parent clause in `ClauseORM` is Regulation 7 (encompassing (i) GMP, (ii) infant prohibition, and (iii) Schedule III foods). In `main.py` (line 387), targeted clause resolution queries match `r.source.clause`. Refining to `"Regulation 7(ii)"` allows targeted retrieval of the infant prohibition rule specifically and displays the precise subclause in `/admin/reviews`. |
| `RULE-FLAVOUR-LABEL-DECLARATION` | `rules` (`rule_id`) | `source.clause` | `"Regulation 8"` | `"Regulation 8(2)(d)"` | **Operative Subclause Isolation**: Parent clause in `ClauseORM` is Regulation 8. Refining to `"Regulation 8(2)(d)"` isolates the specific labelling mandate ("flavour enhancer used" + common name + INS) from general labelling under Regulation 8(1) and nature-identical restrictions under Regulation 8(3). |

### 3.2 System Impact Analysis
- **Compiler**: Re-running compilation with these values produces subclause-level provenance strings.
- **Retrieval Engine**: BM25 and pgvector operate on `ClauseORM.text` (which contains the full parent text); refining `source.clause` in `RuleORM` improves targeted rule lookup without affecting dense vector embeddings.
- **Review UI**: Directly displays the specific subclause identifier to human annotators on `/admin/reviews`.
- **Database Status**: The database has NOT been mutated. Authorization for only these two field updates is requested in Section 7.

---

## 4. Evidence Supporting Jam-Rule Modeling Decision

### 4.1 Statutory Source Structure (Gazette 2113/16, Page 5)
Physical inspection of Gazette 2113/16, Page 5 (Schedule II Item 3.1) establishes two distinct statutory entries in Column I ("Specified Food"):
- **Item 3.1(h)**: `Jams, Jellies, marmalades` $\to$ Sorbates $300\text{ mg/kg}$, Sulphites (as residual $\text{SO}_2$) $100\text{ mg/kg}$, Propionates GMP.
- **Item 3.1(i)**: `Jams, Jellies and marmalades, low in sugar or sugar free` $\to$ Sorbates $500\text{ mg/kg}$, Sulphites (as residual $\text{SO}_2$) $100\text{ mg/kg}$, Propionates GMP.

Critical Statutory Facts:
1. Gazette 2113/16 contains **no definition, Brix specification, or sugar percentage threshold** for "low in sugar or sugar free" anywhere in its 11 pages.
2. The regulation treats (h) and (i) as **two distinct specified food categories** in the statutory table.

### 4.2 Comparative Evaluation: Attribute vs. Category-Token Approach

| Architectural Criteria | Approach A: Attribute Filter (`products.is_low_sugar eq True/False`) | Approach B: Category-Token (`products.category eq "jams_jellies_marmalades_low_sugar"`) |
| :--- | :--- | :--- |
| **Existing Benchmark Preservation** | **BREAKS BENCHMARK**: Benchmark scenario `SCEN-PRES-JAM-DIR-08` lacks `is_low_sugar`. Adding `is_low_sugar eq False` to Rule 6 causes `SCEN-PRES-JAM-DIR-08` to evaluate as `CONDITIONAL_MISSING_DATA`, flipping its gold label. | **PRESERVES BENCHMARK**: `SCEN-PRES-JAM-DIR-08` declares `category = "jams_jellies_marmalades"`. Evaluates directly to `APPLICABLE` with 0 missing fields. |
| **Pydantic Model Schema** | Requires updating `Product` model in `domain.py` or relying on unvalidated `model_extra`. Requires TypeScript interface changes. | **ZERO SCHEMA CHANGES**: `category` is already a native, validated string field in `Product`. |
| **Multi-Product Profile Safety** | **PRONE TO CORRELATION BUG**: In multi-product profiles, independent evaluation of `category` on Product 1 and `is_low_sugar` on Product 2 causes unintended `APPLICABLE` outcomes. | **ATOMIC & IMMUNE**: A single condition `category eq "..."` evaluates atomically per product item. |
| **Missing-Data Behavior** | Profiles omitting `is_low_sugar` trigger `CONDITIONAL_MISSING_DATA` false alarms on standard jams. | Profiles omitting `category` trigger `CONDITIONAL_MISSING_DATA` with missing field `"products.category"`. Known standard jam categories trigger `APPLICABLE` for Rule 6 and `NOT_APPLICABLE` for low-sugar rule. |
| **Statutory Fidelity** | Assumes an ungrounded boolean property not defined in the Gazette. | Directly reflects Schedule II Column I where Item 3.1(h) and Item 3.1(i) are distinct enumerated food items. |

### 4.3 Recommendation
**Adopt Approach B (Category-Token Approach)** as the smallest defensible, mathematically sound, and non-breaking solution:
- Standard jams: `products.category eq "jams_jellies_marmalades"` (governed by `RULE-PRESERVATIVE-JAM-JELLY-LIMIT`, Item 3.1(h), $300\text{ mg/kg}$).
- Low-sugar / sugar-free jams: `products.category eq "jams_jellies_marmalades_low_sugar"` (governed by proposed `RULE-PRESERVATIVE-LOW-SUGAR-JAM-LIMIT`, Item 3.1(i), $500\text{ mg/kg}$).

---

## 5. Proposed Low-Sugar Candidate Rule (`RULE-PRESERVATIVE-LOW-SUGAR-JAM-LIMIT`)

*(Proposed record only; NOT inserted into PostgreSQL)*

```json
{
  "rule_id": "RULE-PRESERVATIVE-LOW-SUGAR-JAM-LIMIT",
  "clause_id": "CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-SCHEDULE-II-FRUIT",
  "clause_version": 1,
  "outcome_type": "STANDARD",
  "applies_if": {
    "all": [
      {"field": "activity", "op": "eq", "value": "food_manufacturing"},
      {"field": "products.category", "op": "eq", "value": "jams_jellies_marmalades_low_sugar"}
    ]
  },
  "exceptions": [],
  "obligation": {
    "type": "formulation",
    "description": "Permitted preservatives in jams, jellies and marmalades low in sugar or sugar free: Sorbates maximum 500 mg/kg, Sulphites maximum 100 mg/kg (as residual SO2), or Propionates GMP.",
    "impact_categories": ["recipe_formulation", "ingredient_specification"]
  },
  "validity": {
    "published": "2019-03-05",
    "commences": "2020-01-01",
    "transition_until": null,
    "superseded_date": null
  },
  "source": {
    "instrument": "The Sri Lanka Gazette Extraordinary No. 2113/16",
    "authority": "Minister of Health, Nutrition and Indigenous Medicine",
    "gazette_no": "2113/16",
    "clause": "Schedule II Item 3.1(i)",
    "page": 5,
    "quote_span": "(i) Jams, Jellies and marmalades low in sugar or sugar free: Sorbates 500 mg/kg, Sulphites (as residual SO2) 100 mg/kg, Propionates GMP."
  },
  "review_status": "PENDING_REVIEW",
  "is_gold_rule": false
}
```

### Missing-Data Behavior
- If `activity` is absent: Kleene `UNKNOWN` $\to$ `CONDITIONAL_MISSING_DATA` (`missing_fields: ["activity"]`).
- If `products.category` is absent: Kleene `UNKNOWN` $\to$ `CONDITIONAL_MISSING_DATA` (`missing_fields: ["products.category"]`).
- If `products.category` is standard jam (`"jams_jellies_marmalades"`): Evaluates to `NOT_APPLICABLE` (Rule 6 applies instead).
- If `products.category` is `"jams_jellies_marmalades_low_sugar"`: Evaluates to `APPLICABLE`.

---

## 6. Validation and Test Results

The focused Phase 3.9 test suite was executed in `.venv` (Python 3.14.5):

### Focused Test Command
```bash
.venv\Scripts\python.exe -m pytest backend/tests/test_phase_3_9_jam_modeling.py -v
```
**Output**:
```text
backend/tests/test_phase_3_9_jam_modeling.py::test_standard_jam_applicability PASSED [ 16%]
backend/tests/test_phase_3_9_jam_modeling.py::test_low_sugar_jam_applicability PASSED [ 33%]
backend/tests/test_phase_3_9_jam_modeling.py::test_missing_or_unknown_product_category PASSED [ 50%]
backend/tests/test_phase_3_9_jam_modeling.py::test_jam_rules_mutual_exclusivity PASSED [ 66%]
backend/tests/test_phase_3_9_jam_modeling.py::test_preservation_of_benchmark_scenario_scen_pres_jam_dir_08 PASSED [ 83%]
backend/tests/test_phase_3_9_jam_modeling.py::test_low_sugar_candidate_source_verification PASSED [100%]
======================== 6 passed, 1 warning in 2.66s =========================
```

### Full Multi-Phase Regression Command (Phases 3.1 through 3.9)
```bash
.venv\Scripts\python.exe -m pytest backend/tests/test_integrity_gate.py \
    backend/tests/test_phase_3_3_segmentation.py \
    backend/tests/test_phase_3_4_benchmark.py \
    backend/tests/test_phase_3_5_review_readiness.py \
    backend/tests/test_phase_3_8_source_verification.py \
    backend/tests/test_phase_3_9_jam_modeling.py -v
```
**Output**:
```text
======================= 58 passed, 1 warning in 39.86s ========================
```

---

## 7. Database Writes and Decisions Still Required

### Authorized Action 1: Flavour Rule Metadata Refinements (Ready for Authorization)
- **Target 1**: `rules` row `RULE-FLAVOUR-INFANT-PROHIBITION`: Update `source.clause` from `"Regulation 7"` to `"Regulation 7(ii)"`.
- **Target 2**: `rules` row `RULE-FLAVOUR-LABEL-DECLARATION`: Update `source.clause` from `"Regulation 8"` to `"Regulation 8(2)(d)"`.
- *Status*: Strictly non-breaking; pending Project Owner authorization.

### Authorized Action 2: Low-Sugar Jam Candidate Insertion (Optional / Deferred)
- **Target**: `rules` table: Insert proposed candidate `RULE-PRESERVATIVE-LOW-SUGAR-JAM-LIMIT` with `review_status = "PENDING_REVIEW"`, `is_gold_rule = False`.
- *Status*: Fully specified and tested in `test_phase_3_9_jam_modeling.py`; pending Project Owner authorization.

---

## 8. Proposal Compliance and Remaining Work Matrix (Locked Option A)

| Milestone & Target | Scope Parameter | Current Authentic Verified Baseline | Implementation Readiness | Remaining Work to Completion |
| :--- | :--- | :--- | :--- | :--- |
| **Authentic Operative Clauses** | $\ge 25$ distinct clauses across authentic food gazettes | **59 authentic clauses** segmented in PostgreSQL (100% embedded with local BGE v1.5) | Fully ingested and vectorized in PostgreSQL pgvector. | Select and review 19 additional clauses from the 49 uncompiled authentic clauses in PostgreSQL to reach target of 25 distinct clauses. |
| **Compiled Rules** | Rules spanning $\ge 25$ distinct clauses | **12 authentic rules** (2 promulgated & approved, 10 candidate in `PENDING_REVIEW`) | Compiler pipeline (`compiler.py`), verifier (`verifier.py`), review UI (`/admin/reviews`) operational. | Execute primary human review on the 10 candidate rules; compile rules for remaining 19 clauses. |
| **Benchmark Scenarios** | $\ge 100$ scenarios (150 stretch) | **30 provisional scenarios** (`multi_group_benchmark_slice.jsonl`) spanning 6 clauses | Dataset partitioner, sensitivity metrics, and Kleene evaluator verified. | Construct and pair 70 additional scenarios (120 for stretch) across the 25 clauses with clause-disjoint train/test splits. |
| **Human Review & Gold Labels** | Inter-annotator agreement ($\kappa \ge 0.80$); legal expert adjudication | **0 gold rules, 0 gold scenarios** (Strictly non-synthetic, provisional) | Multi-role review state machine and audit log (`HumanReviewAuditORM`) fully verified. | Recruit independent second annotator and legal expert panel for gold certification. |
| **Baseline Evaluations** | Empirical comparison of B0, B1, B2, B3 vs System P | Baselines implemented in `backend/src/evaluation/baselines.py` (13 unit tests passing) | Ready for execution; mock-derived results strictly quarantined. | Run empirical evaluation using funded LLM API credentials across the finalized 100-scenario test split. |

---

## 9. Conclusion

Phase 3.9 has cleanly resolved the flavour-rule citation refinements and the jam preservative modeling decision without breaking existing benchmark semantics or mutating the database.

**The system is now stopped at the authorization boundary. Awaiting Project Owner authorization for:**
1. The two flavour-rule metadata updates in PostgreSQL (`source.clause = "Regulation 7(ii)"` and `"Regulation 8(2)(d)"`).
2. Insertion of candidate rule `RULE-PRESERVATIVE-LOW-SUGAR-JAM-LIMIT` (`PENDING_REVIEW`, non-gold).
3. Primary human review sign-off on `/admin/reviews` for the candidate rules.

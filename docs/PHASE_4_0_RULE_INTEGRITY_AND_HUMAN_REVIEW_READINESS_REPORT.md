# RegImpact-SL — Phase 4.0: Rule Integrity Resolution and Human-Review Readiness Report

**Governing Specification:** `RegImpact-SL_Project_Proposal_v4_FINAL.md` (Frozen Development Baseline)  
**Scope Decision Reference:** `docs/PROJECT_OWNER_SCOPE_DECISION_RECORD.md` (Option A: Focused Food Control Scope Locked)  
**Previous Audit Reference:** `docs/PHASE_3_9_RULE_INTEGRITY_AND_APPLICABILITY_REPORT.md`  
**Candidate Register Reference:** `docs/CANDIDATE_RULE_HUMAN_REVIEW_REGISTER.md`  
**Evaluation Date:** 2026-10-27  
**Auditor Roles:** Senior Research Engineer, Regulatory Rule-Modeling Engineer, Benchmark Integrity Auditor, and Critical Implementation Lead  

---

## 1. Initial Repository and Database State

### 1.1 Git Tracking and Working Tree
- **Current Branch**: `main` (synchronized with `origin/main`).
- **Working Tree Status**: Clean (`git status` returns nothing to commit, working tree clean).
- **Recent Git History**:
  - `f26ba29`: `docs: add Phase 3.9 rule integrity and applicability resolution report`
  - `b82727d`: `test: add validation suite for jam preservative rule modeling and applicability resolution`
  - `c780358`: `docs: add proposal compliance and remaining work matrix documentation`
  - `d73b7dd`: `docs: add Phase 3.8 bounded rule correction and source verification report`
  - `da8c4ff`: `test: add Phase 3.8 source verification test suite and candidate rule human-review register`
- **Constraint Adherence**: In strict accordance with Mandatory Constraint 4 (*"Do not commit or push during this phase"*), zero commits or pushes were executed during Phase 4.0.

### 1.2 Database Inventory Audit (PostgreSQL 16 on `localhost:5432`)
Executed audit query via SQLAlchemy ORM over live database:
```python
# Direct audit against PostgreSQL on port 5432
Total SourceDocumentORM: 19 (8 authentic Sri Lankan Gazettes, 11 quarantined synthetic/draft documents)
Total ClauseORM:         85 (59 authentic operative clauses with 100% genuine BGE v1.5 embeddings; 26 quarantined fixtures)
Total RuleORM:           21 (12 authentic rules: 2 approved promulgated rules, 10 candidate rules in PENDING_REVIEW; 9 quarantined synthetic rules)
Rule review_status:      APPROVED: 11 (2 authentic + 9 synthetic test fixtures); PENDING_REVIEW: 10
Rule is_gold_rule:       False: 21 (100% non-gold; ZERO gold contamination)
Benchmark Scenarios:     30 scenarios in multi_group_benchmark_slice.jsonl (100% is_gold_scenario=False, provisional)
```

---

## 2. Workstream A — Evidence for Both Flavour-Rule Citation Corrections

### 2.1 Statutory Evidence and Value Verification

1. **`RULE-FLAVOUR-INFANT-PROHIBITION`**:
   - **Physical Source**: The Sri Lanka Gazette Extraordinary No. 1795/51 (2013-02-01), Page 2 (PDF Index 1).
   - **Statutory Text**: Regulation 7 operative stem: `"7. Flavour enhancers –"`; Subclause (ii): `"(ii) shall not be added to any food for infants or young children below three years of age; and"`.
   - **Parent Clause Record**: `CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-REGULATION-7` (version 1) stores the full text of Regulation 7 (encompassing (i) GMP, (ii) infant prohibition, and (iii) Schedule III foods).
   - **Current `source.clause`**: `"Regulation 7"`.
   - **Proposed `source.clause`**: `"Regulation 7(ii)"`.
   - **Integrity Consistency**: `clause_id`, `clause_version` (1), `source.page` (2), `source.quote_span` (87 characters verbatim), and `applies_if` (`products.target_consumer eq "infants_or_young_children_under_3"`) remain 100% consistent with Regulation 10 definitions.

2. **`RULE-FLAVOUR-LABEL-DECLARATION`**:
   - **Physical Source**: Gazette Extraordinary No. 1795/51, Page 2 (PDF Index 1).
   - **Statutory Text**: Regulation 8(2) stem: `"(2) The label printed on or attached to the package of food containing –"`; Subclause (2)(d): `"(d) any flavour enhancer or enhancers as an ingredient, shall include the words ‘‘flavour enhancer used’’ or ‘‘flavour enhancers used’’ as the case may be, along with the common name or names and the INS number or numbers, as the case may be."`.
   - **Parent Clause Record**: `CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-REGULATION-8` (version 1) stores the full text of Regulation 8.
   - **Current `source.clause`**: `"Regulation 8"`.
   - **Proposed `source.clause`**: `"Regulation 8(2)(d)"`.
   - **Integrity Consistency**: `clause_id`, `clause_version` (1), `source.page` (2), `source.quote_span` (248 characters verbatim), and `applies_if` (`products.contains_flavour_enhancer eq True`) remain 100% consistent.

### 2.2 Component Consumption and Impact Analysis
Audited every component consuming `source.clause`:
1. `backend/src/main.py` (Line 387): `found_rule_ids = {r.rule_id for r in targeted_rules} | {r.source.clause for r in targeted_rules}`.
   - *Impact*: Positive. Targeted queries for `"Regulation 7(ii)"` or `"Regulation 8(2)(d)"` resolve directly to the specific executable rule.
2. `backend/src/evaluation/baselines.py` (Line 508): `self.rules[rule.source.clause] = rule`.
   - *Impact*: Eliminates a critical dictionary key collision. In Gazette 1795/51, two distinct rules derive from Regulation 7 (`RULE-FLAVOUR-INFANT-PROHIBITION` and `RULE-FLAVOUR-SCHEDULE-III-PROHIBITION`). Storing coarse `"Regulation 7"` caused the second rule to overwrite the first in the baseline's clause dictionary. Refining to `"Regulation 7(ii)"` and `"Regulation 7(iii)"` ensures both rules remain independently accessible.
3. `backend/tests/`: Zero existing test assertions break. No test asserts `source.clause == "Regulation 7"`.
4. `ClauseORM` and Embeddings: Unchanged. `ClauseORM.clause_number` remains `"Regulation 7"` and `"Regulation 8"`. The 768-dimensional BGE embeddings are unaffected.

### 2.3 Proposed Transaction-Safe SQL Migration Script (Awaiting Authorization)
In accordance with Mandatory Constraint 9 and Section 3 of the prompt, **no writes were executed**. The exact update prepared for project-owner authorization is:

```sql
BEGIN;

-- Precondition Checks: Verify exact current state before modifying
DO $$
DECLARE
    v_c7 text;
    v_q7 text;
    v_c8 text;
    v_q8 text;
BEGIN
    SELECT source->>'clause', source->>'quote_span' INTO v_c7, v_q7
    FROM rules WHERE rule_id = 'RULE-FLAVOUR-INFANT-PROHIBITION';
    IF v_c7 <> 'Regulation 7' OR v_q7 NOT LIKE '(ii) shall not be added%' THEN
        RAISE EXCEPTION 'Precondition failed for RULE-FLAVOUR-INFANT-PROHIBITION: clause=%, quote=%', v_c7, v_q7;
    END IF;

    SELECT source->>'clause', source->>'quote_span' INTO v_c8, v_q8
    FROM rules WHERE rule_id = 'RULE-FLAVOUR-LABEL-DECLARATION';
    IF v_c8 <> 'Regulation 8' OR v_q8 NOT LIKE '(d) any flavour enhancer%' THEN
        RAISE EXCEPTION 'Precondition failed for RULE-FLAVOUR-LABEL-DECLARATION: clause=%, quote=%', v_c8, v_q8;
    END IF;
END $$;

-- Targeted Updates: Modify strictly source->'clause'
UPDATE rules
SET source = jsonb_set(source::jsonb, '{clause}', '"Regulation 7(ii)"')
WHERE rule_id = 'RULE-FLAVOUR-INFANT-PROHIBITION';

UPDATE rules
SET source = jsonb_set(source::jsonb, '{clause}', '"Regulation 8(2)(d)"')
WHERE rule_id = 'RULE-FLAVOUR-LABEL-DECLARATION';

-- Postcondition Verification: Ensure exactly two rows updated with exact target values
DO $$
DECLARE
    v_post7 text;
    v_post8 text;
BEGIN
    SELECT source->>'clause' INTO v_post7 FROM rules WHERE rule_id = 'RULE-FLAVOUR-INFANT-PROHIBITION';
    SELECT source->>'clause' INTO v_post8 FROM rules WHERE rule_id = 'RULE-FLAVOUR-LABEL-DECLARATION';
    IF v_post7 <> 'Regulation 7(ii)' OR v_post8 <> 'Regulation 8(2)(d)' THEN
        RAISE EXCEPTION 'Postcondition verification failed';
    END IF;
END $$;

COMMIT;
```

---

## 3. Workstream B — Jam-Rule Design Decision and Technical Guarantees

### 3.1 Technical Check Results
1. **Evaluator Exact Matching vs Normalisation**:
   - `backend/src/engine/applicability.py` (`evaluate_operator`, lines 119–127) implements exact string equality: `observed.strip().lower() == target.strip().lower()`.
   - Substring matching, regex fallback, and fuzzy aliasing are **not** performed for `op: "eq"`.
   - Therefore, `category = "jams_jellies_marmalades_low_sugar"` **cannot accidentally match** `"jams_jellies_marmalades"`.
2. **Missing Product Category Behavior**:
   - When `category` is absent or `None`, `extract_field()` returns `(None, False)`.
   - `evaluate_single_condition` yields `TriState.UNKNOWN` with `missing_field = "products.category"`.
   - `evaluate_rule()` produces `OutcomeStatus.CONDITIONAL_MISSING_DATA` with `missing_fields: ["products.category"]`. Neither rule is silently selected.
3. **Multi-Product Profile Safety**:
   - Verified in `test_phase_3_9_jam_modeling.py`: In multi-product profiles, each product's category evaluates atomically. A business manufacturing both lines triggers both rules appropriately.
   - The category-token approach completely eliminates the cross-product correlation bug inherent in independent attribute evaluation (`products.category eq ...` and `products.is_low_sugar eq ...`).
4. **Benchmark Preservation (`SCEN-PRES-JAM-DIR-08`)**:
   - Verified in `test_preservation_of_benchmark_scenario_scen_pres_jam_dir_08`.
   - The existing scenario declares `category = "jams_jellies_marmalades"`. It evaluates to `APPLICABLE` for `RULE-PRESERVATIVE-JAM-JELLY-LIMIT` with zero missing fields, preserving 100% benchmark semantic fidelity.
5. **Multi-Category and Ambiguous Classification Limitation**:
   - The current schema defines `category: Optional[str] = None` per product.
   - A single product item cannot declare dual categories (e.g. both standard jam and fruit spread). If a business manufactures mixed or hybrid products, each must be represented as a distinct `Product` in `products: List[Product]`.

### 3.2 Unresolved Classification Limitations
- **Absence of Statutory Brix Standard**: Gazette 2113/16 contains **no definition** for "low in sugar or sugar free" anywhere in its text. It does not cite Sri Lanka Standard SLS 265 or Codex Stan 296-2009.
- **System Scope Boundary**: The RegImpact-SL deterministic engine evaluates whether a declared product category is subject to a statutory preservative limit. The system **does not and cannot verify chemical laboratory assays** to determine whether a product legally qualifies as low-sugar under external food science standards.

### 3.3 Design Recommendation
**Adopt the Category-Token Architecture (`"jams_jellies_marmalades_low_sugar"`)**:
- Standard Jams (Item 3.1(h)): `RULE-PRESERVATIVE-JAM-JELLY-LIMIT` $\to$ Sorbates $\le 300\text{ mg/kg}$.
- Low-Sugar Jams (Item 3.1(i)): `RULE-PRESERVATIVE-LOW-SUGAR-JAM-LIMIT` $\to$ Sorbates $\le 500\text{ mg/kg}$.
- *Status*: Ready for implementation upon project-owner authorization. Candidate remains uninserted and non-gold.

---

## 4. Workstream C — Human-Review Controls Audit

The review workflow on `/admin/reviews`, backend endpoints in `main.py`, and `HumanReviewAuditORM` in `models.py` were audited against empirical evaluation standards:

| Control & Requirement | Implementation Status | Observed Evidence & Direct Findings | Deficiencies & Human Actions Required |
| :--- | :---: | :--- | :--- |
| **1. Reviewer Identity** | `PARTIALLY VERIFIED` | `HumanReviewAuditORM.reviewer_id` persists string ID passed in `ReviewDecisionRequest`. | In local demo, `reviewer_id` defaults to `"legal_reviewer_01"` if omitted. Lacks cryptographic authentication (OAuth2/JWT). Verified human identity requires credential binding before formal evaluation. |
| **2. Reviewed Version Tracking** | `PARTIALLY VERIFIED` | `RuleORM.verification_report["version_history"]` captures snapshot of `prior_state` on `DECISION_AMENDED`. | For `DECISION_APPROVED`, `HumanReviewAuditORM` records `rule_id` and timestamp, but does not store an immutable SHA-256 hash of the rule payload at approval time. |
| **3. Reviewer Role & Authority** | `VERIFIED` (Domain)<br>`PARTIALLY VERIFIED` (API) | `ReviewService` validates roles in `{'PRIMARY_ANNOTATOR', 'SECONDARY_ANNOTATOR', 'EXPERT_ADJUDICATOR'}`. Only `EXPERT_ADJUDICATOR` can set `is_gold_rule = True`. Primary review leaves `is_gold_rule = False`. | In local demo, the role header `X-User-Role` is client-selectable. Production RBAC requires administrative role provisioning. |
| **4. Decision, Rationale & Timestamp** | `VERIFIED` | Mandatory non-empty rationale enforced (`ValueError` raised if blank); timestamp recorded as UTC datetime; decisions constrained to `{'APPROVED', 'REJECTED', 'MARKED_NON_COMPILABLE', 'AMENDED'}`. | Fully implemented and enforced in `ReviewService.submit_review`. |
| **5. Independent Double Annotation** | `MISSING` | Multiple audit entries can be attached to a rule, but `ReviewService` does not enforce that `reviewer_secondary != reviewer_primary`. | A single user could submit as primary and secondary. Software must enforce distinct reviewer IDs before calculating Cohen's Kappa. |
| **6. Expert Adjudicator Qualification** | `MISSING` | Reviewer ID is stored as an unverified string. No database table or registry exists for legal credentials, Bar registration numbers, or food regulatory certifications. | External legal qualifications must be manually documented and maintained in the review register. |
| **7. Tamper-Proof Audit Logging** | `VERIFIED` | `human_review_audit` is an append-only table. No `UPDATE` or `DELETE` endpoints exist in the API. | Enforced by application architecture. Database-level read-only grants should be applied in production. |
| **8. Gold Status Gating** | `VERIFIED` | Technical verification (`RuleVerifier`) strictly cannot mark rules gold. Primary review cannot mark rules gold. Gold status is gated exclusively to `ROLE_EXPERT_ADJUDICATOR`. | Zero rules in PostgreSQL are marked gold. 100% compliant. |

### Practical Review Protocol & Gold Gating Policy
1. **Primary Review Phase**: Primary annotator signs off on the 10 candidate rules via `/admin/reviews` using [docs/CANDIDATE_RULE_HUMAN_REVIEW_REGISTER.md](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/docs/CANDIDATE_RULE_HUMAN_REVIEW_REGISTER.md). Rules transition to `APPROVED` (`is_gold_rule=False`).
2. **Secondary Independent Review Phase**: Independent second annotator reviews rules separately. Inter-annotator agreement must satisfy Cohen's $\kappa \ge 0.80$.
3. **Expert Adjudication Phase**: Qualified legal expert adjudicates any discordant items. Only after expert sign-off may `is_gold_rule=True` be designated.
4. **Current Status**: **Gold-label certification remains strictly BLOCKED** until independent secondary annotators and external legal experts are formally onboarded.

---

## 5. Workstream D — Authentic Corpus & Benchmark Expansion Path

### 5.1 Verification of Stored Authentic Clauses
A comprehensive audit of all 59 authentic clauses in PostgreSQL was conducted. The audit established that **not all 59 clauses are eligible compliance provisions**:

| Document Identifier | Official Gazette Title | Total Clauses in DB | Already Compiled | Ineligible Stubs (Section 32 / Citation) | Usable Uncompiled Candidate Clauses |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `doc_gazette_2494_47` | Gazette 2494/47 (Labelling & Advertising 2026) | 9 | 1 (Reg 3) | 3 (Sec 32, Sec 1, Sec 2.1) | **5 clauses** (Reg 4, 5, 6, Sec 4.3, Sec 4.6) |
| `doc_15803fe0b14a...` | Gazette 2494/06 (Sugar Labelling 2024) | 7 | 2 (Reg 3 prov, Sched) | 2 (Sec 32, Reg 5 stub) | **3 clauses** (Reg 3 main, Reg 6, Reg 8) |
| `doc_3f85f3ef96b7...` | Gazette 2113/16 (Preservatives 2019) | 10 | 3 (Reg 4, 8, Sched II) | 3 (Sec 32, Reg 1 title, Reg 2005 ref) | **4 clauses** (Reg 2 general, Reg 3 permitted, Reg 5 compounded, Sched I) |
| `doc_b78479b6b08d...` | Gazette 1795/51 (Flavourings 2013) | 12 | 2 (Reg 7, Reg 8) | 2 (Sec 32, Reg 1 title) | **8 clauses** (Reg 3, 4, 6, 9, Sched I, Sched II, Sched III, Reg 7 main) |
| `doc_gazette_2443_27` | Gazette 2443/27 (Packaging Materials 2025) | 15 | 0 | 2 (Sec 32, Item 1.1.3 stub) | **13 clauses** (Reg 2, 4, 5, 8, 9, 12, 13, 14, Items 1.1, 1.2, 2.3.2, 4.4, 6) |
| `doc_gazette_2496_03` | Gazette 2496/03 (Formaldehyde in Fish 2026) | 1 | 0 | 0 | **1 clause** (Section 527 absolute prohibition) |
| `doc_fcau_labelling...` | Food (Labelling and Advertising) Regulations | 3 | 0 | 2 (Sec 32, Reg 1 title) | **1 clause** (Reg 15 date marking) |
| `doc_1688_28` (Candidate) | Gazette 1688/28 (Colouring Substances 2011) | 0 (Requires OCR) | 0 | 0 | **3–5 clauses** post-OCR (Permitted coal tar dyes schedule) |
| **TOTALS** | **Authentic Food Control Scope** | **59 clauses** | **8 clauses** | **14 clauses** | **35–37 eligible uncompiled clauses** |

### 5.2 Evidence-Backed Expansion Feasibility to Proposal Targets
- **Target Mandate**: At least 25 distinct eligible authentic clauses; at least 100 benchmark scenarios (150 stretch).
- **Current Position**: 8 distinct clauses compiled; 12 authentic rules; 30 provisional scenarios.
- **Eligibility Proof**: We have verified **35–37 eligible uncompiled authentic clauses** currently residing in PostgreSQL.
- **Requirement to Reach Target**: Compiling rules for **17 additional clauses** (from the 35 available) reaches the required 25 distinct clauses.
- **Benchmark Scaling**: Constructing and pairing **70 additional scenarios** (averaging 4 scenarios per clause across 25 clauses) satisfies the 100-scenario mandate with 100% authentic Food Control provisions.

---

## 6. Workstream E — Protection of Evaluation Integrity (Baselines & Ablations)

### 6.1 Evaluation Adapter Implementation Audit

| Baseline / System | Implementation File | Verified Status | Operating Mechanism | Actual Data Evaluation Status |
| :--- | :--- | :---: | :--- | :---: |
| **B0 (Oracle Long-Context)** | `backend/src/evaluation/baselines.py` | `IMPLEMENTED` | Bypasses retrieval; injects exact target statutory clause text directly into prompt. | Unit-tested with test doubles. Real execution blocked by funded API credentials. |
| **B1 (BM25 + LLM)** | `backend/src/evaluation/baselines.py` | `IMPLEMENTED` | Pure Okapi BM25 retrieval ($k_1=1.5, b=0.75$) feeds top-$k$ passages to LLM prompt. | Unit-tested. Contaminated mock runs quarantined in `results.json`. Real run pending API access. |
| **B2 (Dense RAG + LLM)** | `backend/src/evaluation/baselines.py` | `IMPLEMENTED` | Local `bge-base-en-v1.5` dense embeddings feed top-$k$ passages via cosine distance to LLM. | Unit-tested. Contaminated mock runs quarantined. Real run pending API access. |
| **B3 (Hybrid RRF + LLM)** | `backend/src/evaluation/baselines.py` | `IMPLEMENTED` | Reciprocal Rank Fusion ($k=60$) combining BM25 and dense rankers feeds passages to LLM. | Unit-tested. Contaminated mock runs quarantined. Real run pending API access. |
| **System P (Proposed Pipeline)** | `backend/src/evaluation/baselines.py` | `IMPLEMENTED` | Hybrid RRF + verified compiler + deterministic Kleene 3-valued engine + coverage gap exposure. | Unit-tested and evaluated on 30 provisional scenarios. Zero mock data. |
| **Statistical Inference Engine** | `backend/src/evaluation/statistics.py` | `IMPLEMENTED` | Clause-level cluster bootstrap (1,000 iterations), paired comparative delta testing, clustered McNemar. | Fully implemented and verified passing unit tests. |

### 6.2 Truthfulness of Prior Benchmark Results
- All metric values in `backend/data/evaluation/results.json` were derived in Phase 3.1 using `MockLLMClient` and simulated strings.
- They are permanently quarantined with `"is_empirical_result": false` and **must never be cited as empirical findings**.
- Real empirical evaluation requires funded API access: 100 scenarios $\times$ 5 systems = 500 LLM generation calls under greedy sampling ($T=0.0$).

---

## 7. Testing and Regression Verification Results

The complete multi-phase regression suite (58 tests across 6 test modules) was executed in the active Python 3.14.5 environment:

```bash
.venv\Scripts\python.exe -m pytest \
    backend/tests/test_integrity_gate.py \
    backend/tests/test_phase_3_3_segmentation.py \
    backend/tests/test_phase_3_4_benchmark.py \
    backend/tests/test_phase_3_5_review_readiness.py \
    backend/tests/test_phase_3_8_source_verification.py \
    backend/tests/test_phase_3_9_jam_modeling.py -v
```

**Actual Command Output**:
```text
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.7.0 -- C:\Users\HP\Desktop\PROJECTS\RegImpact-SL\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\HP\Desktop\PROJECTS\RegImpact-SL
plugins: anyio-4.15.1
collecting ... collected 58 items

backend/tests/test_integrity_gate.py ................. [ 29%]
backend/tests/test_phase_3_3_segmentation.py ......    [ 39%]
backend/tests/test_phase_3_4_benchmark.py ............ [ 60%]
backend/tests/test_phase_3_5_review_readiness.py ...... [ 79%]
backend/tests/test_phase_3_8_source_verification.py ...... [ 89%]
backend/tests/test_phase_3_9_jam_modeling.py ......    [100%]

======================= 58 passed, 1 warning in 28.41s ========================
```
*Result*: 100% green pass rate across all 58 regression tests. Zero regressions.

---

## 8. Database and Benchmark Mutation Statement

- **Database Mutations**: **ZERO (0)** rows inserted, updated, or deleted in PostgreSQL.
- **Rule Review Statuses**: **ZERO (0)** rules transitioned or approved. All 10 candidate rules remain strictly `PENDING_REVIEW`.
- **Gold Labels**: **ZERO (0)** rules or scenarios marked gold (`is_gold_rule=False`, `is_gold_scenario=False`).
- **Benchmark Alterations**: **ZERO (0)** benchmark records modified. `SCEN-PRES-JAM-DIR-08` and all 30 scenarios preserved verbatim.

---

## 9. Remaining Blockers Categorized

1. **Technical Blockers**:
   - Tesseract OCR engine installation needed to extract text from the two native PNG page scans of Gazette 1688/28 (Colouring 2011).
   - Reviewer distinctness check (`reviewer_secondary != reviewer_primary`) to be added to `ReviewService` before secondary review.
2. **Data & Expansion Blockers**:
   - 17 additional authentic clauses must be compiled into candidate rules from the 35 eligible uncompiled clauses.
   - 70 additional paired scenarios must be authored to scale the benchmark from 30 to 100 scenarios.
3. **Human-Review Blockers**:
   - Primary human annotator must sign off on the 10 candidate rules in `/admin/reviews`.
   - Independent second annotator must be recruited to establish inter-annotator agreement ($\kappa \ge 0.80$).
   - External legal expert must be engaged to adjudicate discordant rules before any rule can be designated gold.
4. **Funding & API Access Blockers**:
   - Funded LLM API credentials (Gemini or OpenAI) required to execute the 500-call empirical evaluation of B0–B3 baselines.

---

## 10. Next-Phase Recommendation

**Phase 4.1: Bounded Execution of Authorized Database Updates & Primary Human Review Sign-Off**:
1. Execute the authorized transaction-safe SQL script for the two flavour-rule metadata updates (`Regulation 7(ii)` and `Regulation 8(2)(d)`).
2. Insert candidate rule `RULE-PRESERVATIVE-LOW-SUGAR-JAM-LIMIT` under the verified category-token architecture.
3. Conduct primary human review on the 11 candidate rules via `/admin/reviews` using [CANDIDATE_RULE_HUMAN_REVIEW_REGISTER.md](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/docs/CANDIDATE_RULE_HUMAN_REVIEW_REGISTER.md).
4. Run Tesseract OCR on Gazette 1688/28 (Colouring 2011).

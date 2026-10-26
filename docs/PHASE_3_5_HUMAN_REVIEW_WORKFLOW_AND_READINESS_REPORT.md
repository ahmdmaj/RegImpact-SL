# RegImpact-SL — Phase 3.5: Human Review Workflow & Benchmark Readiness Report

**Phase:** Phase 3.5 — Human Review Workflow & Benchmark Readiness Gate  
**Date:** 2026-10-26  
**Auditor Role:** Senior Research Engineer, Regulatory Data Integrity Auditor, Benchmark Methodologist, Independent Verification Reviewer  
**Governing Specification:** `RegImpact-SL_Project_Proposal_v4_FINAL.md` (Frozen Proposal v4)  
**Related Reports:**
- [docs/PROPOSAL_COMPLIANCE_AND_REMAINING_WORK.md](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/docs/PROPOSAL_COMPLIANCE_AND_REMAINING_WORK.md)
- [docs/PHASE_3_3_CLAUSE_SEGMENTATION_AND_RULE_READINESS_REPORT.md](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/docs/PHASE_3_3_CLAUSE_SEGMENTATION_AND_RULE_READINESS_REPORT.md)
- [docs/PHASE_3_4_HUMAN_REVIEW_AND_BENCHMARK_READINESS_REPORT.md](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/docs/PHASE_3_4_HUMAN_REVIEW_AND_BENCHMARK_READINESS_REPORT.md)
- [docs/CANDIDATE_RULE_HUMAN_REVIEW_REGISTER.md](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/docs/CANDIDATE_RULE_HUMAN_REVIEW_REGISTER.md)

---

## 1. Executive Summary & Completion Decision

### Final Recommendation: **`CONDITIONAL GO`**

The human-review administrative workflow, review audit persistence engine, and provisional 30-scenario benchmark slice are **technically verified, source-grounded, and operationally ready for genuine human review without inventing research data, modifying working components unnecessarily, or introducing synthetic artifacts**.

#### Conditions for Advancing Beyond Phase 3.5:
1. **Primary Human Review Sign-Off**: The 10 candidate rules currently queued in `PENDING_REVIEW` in PostgreSQL must be manually reviewed and decided via `/admin/reviews` by the primary researcher.
2. **Benchmark Volume Ceiling Acknowledgment**: The provisional benchmark comprises 30 scenarios across 6 distinct clauses. It **CANNOT** satisfy Proposal v4's target of 100 scenarios across at least 25 distinct clauses until additional promulgated gazettes are ingested and segmented.
3. **External Dependencies Gated**: Independent secondary annotation (for Cohen's kappa $\kappa$) and expert legal adjudication (for designating `is_gold_rule = True` and `is_gold_scenario = True`) remain outstanding external human dependencies. No empirical baseline experiments (B0–B3) may be reported as gold research findings until these sign-offs occur.

---

## 2. Epistemological Framework

To ensure research integrity, every statement in this audit is classified into one of five categories:
- **[VERIFIED FACT]**: Confirmed by deterministic code execution, database SQL queries, physical byte hashes, or direct test outputs in the runtime environment.
- **[INFERRED FROM CODE]**: Derived from reading static implementation logic and configuration schemas.
- **[PREVIOUS CLAIM]**: Asserted in Phase 3.3 or Phase 3.4 documentation, independently re-tested here.
- **[UNRESOLVED QUESTION]**: Ambiguities or conflicting specifications in governing Proposal v4.
- **[GENUINE HUMAN ACTION REQUIRED]**: Tasks that strictly require human legal or domain judgment and cannot be automated.

---

## 3. Stage 0 — Actual Current State Audit

### 3.1 Git Version Control State
- **Current Commit**: `1622c2b31725616a48c536192d9a5eaa84099ad3`
- **Branch**: `main`
- **Modified Tracked Files**:
  - `frontend/src/services/api.ts` (bounded review repair)
  - `frontend/src/app/admin/reviews/page.tsx` (bounded review repair)
  - `docs/PROPOSAL_COMPLIANCE_AND_REMAINING_WORK.md` (compliance update)
- **New Untracked Files**:
  - `backend/tests/test_phase_3_5_review_readiness.py` (focused verification test suite)
  - `docs/CANDIDATE_RULE_HUMAN_REVIEW_REGISTER.md` (human review register)
  - `docs/PHASE_3_5_HUMAN_REVIEW_WORKFLOW_AND_READINESS_REPORT.md` (this report)
  - `scratch/*` (temporary diagnostic scripts in conversation artifact directory)

### 3.2 Physical PDF Inventory & Byte-Level SHA-256 Verification
[VERIFIED FACT] Every candidate and authoritative PDF on disk was hashed using SHA-256 and matched against authoritative records:

| Source Document | Physical File Path | File Size | SHA-256 Hash | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Gazette 2494/47** (Labelling 2026) | `backend/data/raw_sources/2494-47_E.pdf` | 424,172 B | `83ed19c22873471652d0073fe16c977442e42c8ecac2edf1d691d00d78d8a054` | Authentic, Promulgated |
| **Gazette 2494/06** (Sugar 2026) | `backend/data/raw_sources/2494-06_E.pdf` | 398,991 B | `15803fe0b14aabe0c79126ebe7c8834d8063b6ed8c2a9033c1201ff538bcd95b` | Authentic, Promulgated |
| **Gazette 2113/16** (Preservatives 2019) | `backend/data/raw_sources/2113-16_E.pdf` | 154,178 B | `3f85f3ef96b7622bdd3e45d7cc642fd96fdbd83a9f84f35f048121eab3e4016f` | Authentic, Promulgated |
| **Gazette 1795/51** (Flavourings 2013) | `backend/data/raw_sources/1795-51_E.pdf` | 147,560 B | `b78479b6b08d12e11fd27cfc39677d5a284bc147bf16a777eafb495b86f4135a` | Authentic, Promulgated |
| **Gazette 1688/28** (Colouring 2011) | `backend/data/raw_sources/1688-28_E.pdf` | 81,054 B | `3cd9948dbb4ff329f6dd851bc01d5162b770519a77f98a2872365cb917eef9f2` | Authentic (Requires OCR) |
| **Gazette 2496/03** (Food Hygiene 2026) | `backend/data/raw_sources/2496-03_E.pdf` | 232,401 B | `672a95c960333d7790b79ef54fbcc2bf87a3e81ad3f8d38ee5d9e578c7c13cb5` | Quarantined (Out of scope) |

### 3.3 Database Actual Counts & Records Audit
[VERIFIED FACT] Direct SQL inspection against live PostgreSQL (`localhost:5432/regimpact_db`) confirms:
- **Source Documents (`source_documents`)**: 19 records.
  - 8 Authentic documents (6 promulgated, 1 draft quarantined, 1 candidate).
  - 11 Quarantined test upload dummies (`is_synthetic = True`).
- **Clauses (`clauses`)**: 85 records.
  - 59 Authentic clauses (`is_synthetic = False`), 100% embedded with local BGE v1.5 (768-dim).
  - 26 Synthetic/dummy clauses (`is_synthetic = True`), strictly excluded from retrieval.
- **Rules (`rules`)**: 21 records.
  - 12 Authentic rules (`is_synthetic = False`):
    - 2 `APPROVED` rules (`RULE-FCAU-2494-47-REG-3`, `RULE-FCAU-2494-47-REG-3-B2B`). Both have `is_gold_rule = False`.
    - 10 `PENDING_REVIEW` candidate rules compiled during Phase 3.3.
  - 9 Quarantined synthetic/draft rules (`is_synthetic = True` or unpromulgated draft).
  - **Gold Rules Count**: Exactly 0.

### 3.4 Historical Review Audit Trail Audit (`human_review_audit`)
[VERIFIED FACT] PostgreSQL contains exactly 11 review audit records in the singular table `human_review_audit`:
- **Audits 1–8 (2026-10-19)**: Synthetic test seed rules (`RULE-FCAU-REG-4`, etc.). These relate to legacy synthetic fixtures.
- **Audit 9 (2026-10-22)**: Draft unpromulgated rule (`RULE-FCAU-REAL-2026-REG-2`), quarantined in Phase 3.1.
- **Audits 10 & 11 (2026-10-25)**: Authentic promulgated rules (`RULE-FCAU-2494-47-REG-3` and `-B2B`), both reviewed by `PRIMARY_ANNOTATOR` `researcher_engineer_01`. Both explicitly state: *"Note: Independent legal expert adjudication is pending."*
- **The 10 candidate rules compiled in Phase 3.3 have ZERO audit records and remain in `PENDING_REVIEW`.**

---

## 4. Stage 1 — Human-Review Workflow Audit

[INFERRED FROM CODE & VERIFIED FACT] The human review workflow spans [backend/src/engine/review.py](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/engine/review.py), [backend/src/main.py](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/main.py), [frontend/src/services/api.ts](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/frontend/src/services/api.ts), and [frontend/src/app/admin/reviews/page.tsx](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/frontend/src/app/admin/reviews/page.tsx).

### Pass/Fail Workflow Audit Table

| Workflow Capability | Status | File & Function Reference | Findings & Evidence |
| :--- | :--- | :--- | :--- |
| **Inspect exact source clause & instrument provenance** | **PASS** | `backend/src/main.py:get_admin_reviews`<br>`frontend/src/app/admin/reviews/page.tsx:ReviewCard` | Returns `source.clause`, `source.quote_span`, `clause_number`, and `document_title`. Quote spans (70–393 chars) match verbatim text. |
| **Inspect proposed rule fields, conditions, obligations, dates** | **PASS** | `backend/src/engine/review.py:get_pending_reviews`<br>`frontend/src/app/admin/reviews/page.tsx:ReviewCard` | Formats `applies_if`, `obligation.type`, `obligation.description`, `validity`, and `impact_categories`. |
| **Inspect statutory exceptions & provisos** | **PASS** *(Repaired)* | `frontend/src/app/admin/reviews/page.tsx:ReviewCard` | Initially only in raw JSON; repaired to explicitly render statutory exceptions under a dedicated visual section. |
| **Explicit approve / reject action** | **PASS** | `backend/src/main.py:approve_review`, `reject_review`<br>`backend/src/engine/review.py:submit_review` | Buttons trigger `POST /admin/reviews/{rule_id}/approve` and `reject`. Rejects without rationale fail with HTTP 422/400. |
| **Record reviewer identity, role, decision, timestamp, rationale** | **PASS** *(Repaired)* | `backend/src/engine/review.py:submit_review`<br>`frontend/src/app/admin/reviews/page.tsx` | UI previously omitted `reviewer_role` selector. Repaired to support dropdown selection (`PRIMARY_ANNOTATOR`, `SECONDARY_ANNOTATOR`, `EXPERT_ADJUDICATOR`). |
| **Prevent invalid state transitions & false gold designation** | **PASS** | `backend/src/engine/review.py:submit_review` | Validates `reviewer_role in VALID_ROLES`. Only `EXPERT_ADJUDICATOR` can set `is_gold_rule = True`. Primary/secondary review sets `is_gold_rule = False`. |
| **Non-destructive re-review without losing audit history** | **PASS** | `backend/src/engine/review.py:submit_review`, `get_audit_trail` | Appends new immutable records to `human_review_audit` with UTC timestamps; captures version snapshots for amendments. |
| **Distinguish technical verification, primary review, adjudication** | **PASS** *(Repaired)* | `frontend/src/app/admin/reviews/page.tsx`<br>`backend/src/extraction/compiler.py` | UI language was repaired to eliminate confusing "Approve & Certify" terms; status badges clearly show "PENDING HUMAN REVIEW". |
| **Safe handling of unavailable evidence / errors** | **PASS** | `backend/src/main.py:approve_review`<br>`backend/src/engine/review.py:ReviewService` | Missing rules return HTTP 404 `RuleNotFoundError`. Invalid roles return HTTP 400 `InvalidReviewerRoleError`. Blank rationales return HTTP 400 `ValueError`. |

---

## 5. Stage 2 — Bounded Workflow Repairs

Three bounded, non-destructive repairs were executed to resolve concrete defects identified in Stage 1:

### Repair 1: Reviewer Role Support in Frontend API & UI
- **Defect**: The frontend API interface `ReviewDecisionPayload` omitted `reviewer_role`, forcing all backend review actions to default to `PRIMARY_ANNOTATOR`. Users could not specify `SECONDARY_ANNOTATOR` or `EXPERT_ADJUDICATOR`.
- **Smallest Affected Code Path**:
  - `frontend/src/services/api.ts`: Added optional `reviewer_role?: string;` to `ReviewDecisionPayload`. Aligned return types of `approveReview` and `rejectReview` to `{ success: boolean; rule_id: string; review_status: string; message: string }`.
  - `frontend/src/app/admin/reviews/page.tsx`: Added `reviewerRole` state and dropdown selector permitting the user to explicitly declare their role (`PRIMARY_ANNOTATOR`, `SECONDARY_ANNOTATOR`, or `EXPERT_ADJUDICATOR`).
- **Regression Risk**: Negligible. Backend already supported and validated `reviewer_role`.

### Repair 2: Rendering Statutory Exceptions & Provisos in Review UI
- **Defect**: Candidate rules containing statutory provisos (such as B2B exceptions in Sugar 2494/06) did not display their `exceptions` array in the formatted card view (only visible if the reviewer expanded the raw JSON drawer).
- **Smallest Affected Code Path**:
  - `frontend/src/app/admin/reviews/page.tsx`: Added formatted section rendering `rule.exceptions` ("Statutory Exceptions & Provisos") showing condition fields, operators, and values.
- **Regression Risk**: None. Purely additive presentation element.

### Repair 3: Research Integrity Terminology Alignment
- **Defect**: The UI button previously read "Approve & Certify", and status badges displayed "PENDING VERIFICATION". This risked implying that an approving researcher was certifying legal truth.
- **Smallest Affected Code Path**:
  - `frontend/src/app/admin/reviews/page.tsx`:
    - Updated button label to `"Approve Candidate Rule"`.
    - Updated queue badge to `"PENDING HUMAN REVIEW"`.
    - Updated empty state description to `"All candidate statutory rules in the review queue have been reviewed."`
- **Regression Risk**: None.

---

## 6. Stage 3 — Benchmark Integrity & Feasibility Gate

### 6.1 Audit of Provisional 30-Scenario Benchmark Slice
[VERIFIED FACT] The file `backend/data/benchmark/multi_group_benchmark_slice.jsonl` was audited across all 30 scenarios:
- **Total Scenarios**: Exactly 30.
- **Provisional Status**: 100% provisional (`is_gold_scenario = False`, `is_gold_rule = False`). Zero scenarios falsely claimed as gold.
- **Authentic Clause Grounding**: All 30 scenarios resolve to authentic clauses in PostgreSQL across 4 authentic candidate groups.
- **Minimal Pairs Sensitivity (5 pairs, 10 scenarios)**:
  - `PAIR-REG3-MARKET-CHANNEL`: Regulation 3 retail (`APPLICABLE`) vs B2B wholesale (`NOT_APPLICABLE`). Diffs strictly on `market.b2b_only`.
  - `PAIR-SUGAR-RED-THRESHOLD`: Sugar Schedule Tier 1 (`8.5 g/100ml` $\to$ `APPLICABLE`) vs (`7.5 g/100ml` $\to$ `NOT_APPLICABLE`). Diffs strictly on `products[0].sugar_g_per_100ml`.
  - `PAIR-SUGAR-AMBER-LOWER-BOUND`: Sugar Schedule Tier 2 (`2.5 g/100ml` $\to$ `APPLICABLE`) vs (`2.0 g/100ml` $\to$ `NOT_APPLICABLE`). Diffs strictly on `products[0].sugar_g_per_100ml`.
  - `PAIR-PRES-MIXTURE-FLAG`: Preservatives Regulation 4 mixture summation (`has_preservative_mixture = True` $\to$ `APPLICABLE`) vs (`False` $\to$ `NOT_APPLICABLE`).
  - `PAIR-FLAV-TARGET-CONSUMER`: Flavourings Regulation 7 infant prohibition (`target_consumer = 'infants_under_12_months'` $\to$ `APPLICABLE`) vs (`'general_population'` $\to$ `NOT_APPLICABLE`).
- **Invariance Pairs Stability (2 pairs, 4 scenarios)**:
  - `PAIR-REG3-INV-BIZ-METADATA`: Mutates company name, premises, employee count $\to$ Outcome invariant (`APPLICABLE` $\to$ `APPLICABLE`).
  - `PAIR-SUGAR-INV-LOCATION`: Mutates factory district from Colombo to Kandy $\to$ Outcome invariant (`APPLICABLE` $\to$ `APPLICABLE`).
- **Incomplete Profiles & 3-Valued Kleene Logic (3 scenarios)**:
  - `SCEN-REG3-INC-CHAN-05`: Missing `market.b2b_only` $\to$ `CONDITIONAL_MISSING_DATA`.
  - `SCEN-REG3-INC-PACK-06`: Missing `products.prepackaged` $\to$ `CONDITIONAL_MISSING_DATA`.
  - `SCEN-SUGAR-INC-06`: Missing `products.sugar_g_per_100ml` $\to$ `CONDITIONAL_MISSING_DATA`.
- **Temporal Validity (2 scenarios)**:
  - `SCEN-REG3-TEMP-PRE-07`: Evaluated at `2026-05-01` (pre-commencement `2026-07-01`) $\to$ `NOT_YET_IN_FORCE`, outcome `NOT_APPLICABLE`.
  - `SCEN-SUGAR-TEMP-05`: Evaluated at `2026-05-01` (pre-commencement `2026-06-23`) $\to$ `NOT_YET_IN_FORCE`, outcome `NOT_APPLICABLE`.
- **Clause-Level Partition Leakage Audit**:
  - Partitioning via `split_scenarios_by_clause(multi_group_scenarios, test_ratio=0.3)` across multiple random seeds (1, 7, 42, 99, 1234) consistently produces **ZERO clause leakage** between train and test sets, and **ZERO broken pair IDs**.

### 6.2 Reconciliation of Clause Count Discrepancies
[UNRESOLVED QUESTION] The audit revealed two fundamental volume discrepancies between the current implementation and governing Proposal v4:

#### 1. Current Benchmark vs Proposal Minimum Benchmark Target
- **Current Implementation**: 30 scenarios covering **6 distinct clauses** (`Regulation 3`, `Schedule (Regulation 3)`, `Regulation 3(1)`, `Schedule II Item 3.1`, `Regulation 4`, `Regulation 7`).
- **Proposal v4 Requirement (§9.2, §10.2)**: At least **100 evaluation scenarios covering at least 25 distinct statutory clauses**.
- **Reconciliation Finding**: The current 30-scenario slice is a **provisional candidate benchmark**. It satisfies the proportional structural diversity requirements (direct, minimal pair, invariance, incomplete, temporal) across 4 authentic instruments, but **CANNOT** satisfy the proposal's volume requirements without ingesting and segmenting at least 19 additional operative clauses.

#### 2. Governing Proposal v4 Section 6 vs Section 9.1 Instrument Count Conflict
- **Proposal v4 Section 6 ("Prioritized Domain & Corpus Scope")**:
  > *"20–30 prioritized statutory instruments, focusing on key operative clauses (~25–40 clauses across the corpus)."*
- **Proposal v4 Section 9.1 ("Corpus Expansion Target")**:
  > *"Target corpus: 50–100 gazetted instruments, ~200–400 operative provisions."*
- **Reconciliation Finding**: This conflict between Section 6 (20–30 instruments, 25–40 clauses) and Section 9.1 (50–100 instruments, 200–400 clauses) is an internal inconsistency in the frozen proposal. The auditor recommends that the project owner adopt **Section 6** as the governing benchmark target, as 25–40 operative clauses across 20–30 instruments is sufficient for statistical cluster bootstrapping ($N \ge 25$ clusters) while remaining feasible within computational and human review budgets.

---

## 7. Stage 4 — Human-Review Readiness Register

A dedicated [Candidate Rule Human-Review Register](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/docs/CANDIDATE_RULE_HUMAN_REVIEW_REGISTER.md) has been established documenting all 12 authentic rules.

### Review Register Summary

| Rule ID | Instrument | Clause | Review Status | Primary Review | Second Annotator | Legal Expert | Gold Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `RULE-SUGAR-2494-06-RED` | Gazette 2494/06 | Sched (Reg 3) | `PENDING_REVIEW` | PENDING | PENDING | PENDING | `False` |
| `RULE-SUGAR-2494-06-AMBER` | Gazette 2494/06 | Sched (Reg 3) | `PENDING_REVIEW` | PENDING | PENDING | PENDING | `False` |
| `RULE-SUGAR-2494-06-GREEN` | Gazette 2494/06 | Sched (Reg 3) | `PENDING_REVIEW` | PENDING | PENDING | PENDING | `False` |
| `RULE-SUGAR-2494-06-GLASS-PROVISO` | Gazette 2494/06 | Reg 3(1) prov | `PENDING_REVIEW` | PENDING | PENDING | PENDING | `False` |
| `RULE-PRESERVATIVE-JAM-JELLY-LIMIT` | Gazette 2113/16 | Sched II 3.1 | `PENDING_REVIEW` | PENDING | PENDING | PENDING | `False` |
| `RULE-PRESERVATIVE-MIXTURE-LIMIT` | Gazette 2113/16 | Reg 4 | `PENDING_REVIEW` | PENDING | PENDING | PENDING | `False` |
| `RULE-PRESERVATIVE-LABEL-DECLARATION` | Gazette 2113/16 | Reg 8 | `PENDING_REVIEW` | PENDING | PENDING | PENDING | `False` |
| `RULE-FLAVOUR-INFANT-PROHIBITION` | Gazette 1795/51 | Reg 7(i) | `PENDING_REVIEW` | PENDING | PENDING | PENDING | `False` |
| `RULE-FLAVOUR-SCHEDULE-III-PROHIBITION` | Gazette 1795/51 | Reg 7(iii) | `PENDING_REVIEW` | PENDING | PENDING | PENDING | `False` |
| `RULE-FLAVOUR-LABEL-DECLARATION` | Gazette 1795/51 | Reg 8 | `PENDING_REVIEW` | PENDING | PENDING | PENDING | `False` |
| `RULE-FCAU-2494-47-REG-3` | Gazette 2494/47 | Reg 3 | `APPROVED` | **APPROVED** | PENDING | PENDING | `False` |
| `RULE-FCAU-2494-47-REG-3-B2B` | Gazette 2494/47 | Reg 3 prov | `APPROVED` | **APPROVED** | PENDING | PENDING | `False` |

---

## 8. Stage 5 — Test Execution & Regression Protection

### 8.1 Focused Phase 3.5 Test Suite
A focused test suite [backend/tests/test_phase_3_5_review_readiness.py](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/tests/test_phase_3_5_review_readiness.py) was implemented covering all required gates:
- **Command**: `.venv\Scripts\python.exe -m pytest backend/tests/test_phase_3_5_review_readiness.py -v`
- **Exit Status**: `0`
- **Results**: 11 passed in 3.50s.

### 8.2 Full Regression Test Suite
All 11 test suites across the repository were executed simultaneously:
- **Command**:
  ```bash
  .venv\Scripts\python.exe -m pytest \
    backend/tests/test_integrity_gate.py \
    backend/tests/test_real_source_slice.py \
    backend/tests/test_corpus_hygiene.py \
    backend/tests/test_retrieval.py \
    backend/tests/test_datasets.py \
    backend/tests/test_agreement_review.py \
    backend/tests/test_phase_3_3_segmentation.py \
    backend/tests/test_phase_3_4_benchmark.py \
    backend/tests/test_statistics.py \
    backend/tests/test_benchmark_slice.py \
    backend/tests/test_phase_3_5_review_readiness.py -v
  ```
- **Exit Status**: `0`
- **Results**: **158 passed, 1 warning (deprecation warning for `fitz`) in 38.49s**. Zero failures.

### 8.3 FastAPI Test Suite
- **Command**: `.venv\Scripts\python.exe -m pytest backend/tests/test_api.py -v`
- **Exit Status**: `0`
- **Results**: **20 passed, 1 warning in 7.27s**. Zero failures.

---

## 9. Proposal Compliance & Remaining Work Updates

The compliance matrix in [docs/PROPOSAL_COMPLIANCE_AND_REMAINING_WORK.md](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/docs/PROPOSAL_COMPLIANCE_AND_REMAINING_WORK.md) was updated:
- **Row 3 (Evidence Verification & Human Review)**: Updated to reflect Phase 3.5 repairs: `reviewer_role` support added to frontend, `exceptions` display added, research-grade terminology instituted, and Candidate Rule Human-Review Register established.
- **Row 13 (Evaluation Dataset & Metrics)**: Re-confirmed as `PARTIAL`. 30 provisional scenarios verified; 100-scenario target requires expanding the corpus across additional authentic clauses.
- **Action Plan**: Formally records completion of Phase 3.5 under `CONDITIONAL GO`.

---

## 10. Prioritized Next Actions

In accordance with strict research integrity and audit discipline, actions are separated into local steps the project owner can perform immediately versus external dependencies requiring third parties or credentials:

### Priority 1: Local Actions (Project Owner Can Perform Locally)
1. **Human Review Sign-Off via Admin UI**:
   - Start the backend (`python -m uvicorn backend.src.main:app --port 8000`) and frontend (`npm run dev` on port 3000).
   - Navigate to `http://localhost:3000/admin/reviews` with header/role `reviewer`.
   - Review each of the 10 candidate rules using the [Candidate Rule Human-Review Register](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/docs/CANDIDATE_RULE_HUMAN_REVIEW_REGISTER.md) questions.
   - Click "Approve Candidate Rule" or "Reject Candidate Rule" with an explicit rationale. This will transition the rules from `PENDING_REVIEW` to `APPROVED` or `REJECTED` in PostgreSQL without making them gold.
2. **Resolve Governing Specification Conflict**:
   - Formally confirm whether Proposal v4 Section 6 (20–30 instruments, 25–40 clauses) or Section 9.1 (50–100 instruments, 200–400 clauses) governs the final benchmark scope ceiling.
3. **Execute Tesseract OCR on Candidate 2**:
   - Run Tesseract OCR on `backend/data/raw_sources/1688-28_E.pdf` (Food Colouring Regulations 2011) to unlock its 8 operative clauses and permit rule compilation.

### Priority 2: External Dependencies (Requires Second Party, Legal Counsel, or Paid API)
1. **Recruit Independent Second Annotator**:
   - Conduct a blind secondary review of the approved candidate rules using `/admin/reviews` with role `SECONDARY_ANNOTATOR`.
   - Run `compute_cohens_kappa` to empirically verify inter-rater agreement ($\kappa \ge 0.80$).
2. **Recruit Qualified Sri Lankan Legal Expert**:
   - Convene expert legal adjudication for consensus sign-off on the rules and scenarios using role `EXPERT_ADJUDICATOR` to formally promote approved rules to `is_gold_rule = True`.
3. **Funded LLM Provider Credentials**:
   - Supply a funded Pay-as-you-go Gemini or OpenAI API key to execute the mass empirical baseline evaluation (B0–B3) across the completed test partition.

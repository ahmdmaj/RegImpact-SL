# RegImpact-SL — Phase 2: Benchmark Dataset Expansion Plan (Critical Revision)

**Role:** Critical Research-Methodology Auditor & Senior Verification Engineer  
**Governing Specification:** [Proposal v4 — Development Freeze](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/PROPOSAL_V4_FREEZE.md) (`RegImpact-SL_Project_Proposal_v4_FINAL.md`)  
**Prior Verification Gate:** [RegImpact-SL_Benchmark_Integrity_Audit.md](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/RegImpact-SL_Benchmark_Integrity_Audit.md)  
**Current Baseline Slice:** [`backend/data/benchmark/regulation_3_slice.jsonl`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/data/benchmark/regulation_3_slice.jsonl) (12 provisional scenarios)  
**Execution Timestamp:** 2026-10-24T18:25:00+05:30  
**Document Status:** Critical Revision — Methodological Alignment & Unverified Claim Downgrade  

---

## 1. Executive Summary & Exit Decision

```text
REVISED PLAN READY FOR RESEARCHER APPROVAL
```

### Purpose of Critical Revision
This revision rigorously corrects material inconsistencies identified in the preliminary expansion plan:
1. **Reconciliation of Benchmark Scenario Counts:** The preliminary draft proposed category totals (126 min / 166 stretch) that breached the frozen Proposal v4 ceiling of 150 scenarios and conflated primary scenario types with cross-cutting evaluation tags. This revision establishes an arithmetically strict, two-tier taxonomy strictly bounded within **100 (minimum) to 150 (stretch maximum)** scenarios, explicitly incorporating the existing 12 Regulation 3 scenarios.
2. **Downgrade of Unverified Legal Claims:** All regulatory provisions, capacity thresholds, additive limits, and amendment relationships outside the audited Gazette 2494/47 Regulation 3 vertical slice are formally downgraded to `UNVERIFIED_CANDIDATE`. Unverified claims are stripped of authoritative status until primary official Gazettes are inspected line-by-line.
3. **Realism in Dataset Partitioning:** The premature assumption of a 60/20/20 three-way split is replaced with an empirical feasibility protocol. With small numbers of independent clause families, three-way splits suffer severe statistical instability; a two-way split or cross-validation strategy is formally specified as a disciplined alternative.
4. **Source Preservation & Exclusion Protocol:** Establishes an explicit Exclusion Register to screen out unvetted lecture slides, working-group drafts, and test dummies without destructive modification of repository files.
5. **Strengthened Gold Annotation Standard:** Replaces vague sampling assumptions with a formal four-stage lifecycle, documenting the exact unit of review, label agreement criteria, the limitations of Cohen's kappa on imbalanced legal datasets, and the absolute requirement that unreviewed rules remain provisional.
6. **Preservation of the Frozen Proposal Discrepancy:** The textual conflict between Section 6 (20–30 instruments) and Section 9.1 (25–40 instruments) in Proposal v4 is retained as an unresolved ambiguity and framed as an explicit decision requiring lead researcher sign-off.

---

## 2. Findings from Repository & Baseline Slice Inspection

An exhaustive audit of the codebase, existing benchmark slice, database seeders, and raw source storage was conducted:

```
c:\Users\HP\Desktop\PROJECTS\RegImpact-SL
├── backend/
│   ├── data/
│   │   ├── benchmark/regulation_3_slice.jsonl   (12 provisional scenarios; SHA-256: 0837d94c...)
│   │   ├── raw_sources/                         (37 files; mix of authentic Gazettes & unvetted artifacts)
│   │   └── seed_real_slice.py                   (DB seeder for Gazette 2494/47 Regulation 3)
│   ├── src/
│   │   ├── db/models.py                         (SourceDocumentORM, ClauseORM, RuleORM, ReviewAuditORM)
│   │   ├── engine/applicability.py              (Deterministic 3-valued Kleene applicability engine)
│   │   ├── evaluation/
│   │   │   ├── baselines.py                     (B0 oracle, B1 BM25, B2 dense, B3 hybrid, System P)
│   │   │   ├── benchmark_runner.py              (BenchmarkRunner, metrics engine, SHA-256 recording)
│   │   │   ├── benchmark_validator.py           (Input diffing, pair integrity, provisional safety)
│   │   │   └── dataset_split.py                 (split_scenarios_by_clause; single-clause aware)
│   │   └── models/domain.py                     (BenchmarkScenario, EvaluationReport, Rule)
│   └── tests/
│       └── test_benchmark_slice.py              (18 unit/negative/regression tests passing)
```

### 2.1 Separation of Fact Levels

To preserve research integrity, facts and claims in this repository are categorized into four distinct levels:

| Level | Definition | Current Repository Status |
|---|---|---|
| **Level 1: Verified Repository Facts** | Code, tests, models, and data slices mechanically verified and passing CI. | - 12 provisional scenarios in [`regulation_3_slice.jsonl`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/data/benchmark/regulation_3_slice.jsonl).<br>- 18 unit/negative tests in [`test_benchmark_slice.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/tests/test_benchmark_slice.py) passing.<br>- Pydantic domain models in [`domain.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/models/domain.py).<br>- Deterministic Kleene engine in [`applicability.py`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/engine/applicability.py). |
| **Level 2: Claims Verified Against Official Sources** | Statutory provisions mechanically checked against authentic Gazette PDFs with verified SHA-256 hashes. | - Gazette Extraordinary No. 2494/47 (2026-06-26): SHA-256 `83ed19c2...` verified.<br>- Regulation 3 (Retail labelling mandate, Page 1).<br>- Regulation 3 Proviso (a) (Purchaser presence exemption, Page 1).<br>- Regulation 3 Proviso (b) (B2B 10 disclosures + 3 mm marking, Pages 1–2).<br>- Regulation 1 (Commencement 1 July 2026, Page 1). |
| **Level 3: Proposed Candidates Requiring Verification** | Candidate regulations, clauses, thresholds, and amendment links proposed for expansion. | - All other clauses (Regulations 4, 7, 9, 18 of Gazette 2494/47).<br>- Food (Preservatives) Regulations and chemical limits.<br>- Food (Colouring Substances) Regulations 2011.<br>- Food (Flavouring Substances) Regulations 2013.<br>- Central Environmental Authority EPL Gazettes 1533/16 & 2264/18.<br>- Industrial Development Act registration thresholds.<br>*Status:* **`UNVERIFIED_CANDIDATE`**. |
| **Level 4: Unresolved Legal Questions** | Statutory terms subject to interpretive ambiguity requiring legal adjudication. | - Exact evidentiary boundary of "in the presence of the purchaser" for pre-portioned foods bagged at point of sale.<br>- Downstream distributor labelling liabilities for decanted bulk B2B packages.<br>- Municipal council trade licence interaction with CEA EPL thresholds. |

---

## 3. Section 1 — Benchmark Scenario Allocation & Mathematical Reconciliation

### 3.1 Accounting for Existing Scenarios
The **12 existing scenarios** in [`backend/data/benchmark/regulation_3_slice.jsonl`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/data/benchmark/regulation_3_slice.jsonl) are an integral part of the benchmark and **count directly toward the final total**:
- 4 direct positive scenarios (`SCEN-REG3-RET-DIR-01`, `SCEN-REG3-B2B-DIR-03`, `SCEN-REG3-B2B-IMP-04`, `SCEN-REG3-SCOPE-OUT-08` [out-of-scope negative])
- 1 direct statutory exception (`SCEN-REG3-EXC-DIR-02`)
- 2 minimal pair scenarios forming 1 complete pair (`SCEN-REG3-PAIR-09A` / `09B`)
- 2 invariance scenarios forming 1 complete pair (`SCEN-REG3-INV-10A` / `10B`)
- 1 temporal pre-commencement scenario (`SCEN-REG3-TEMP-PRE-07`)
- 2 incomplete profile scenarios (`SCEN-REG3-INC-CHAN-05`, `SCEN-REG3-INC-PACK-06`)

To expand to the Proposal v4 targets:
- **Minimum Target:** 100 total scenarios (12 existing + 88 new candidates).
- **Stretch Maximum Target:** 150 total scenarios (12 existing + 138 new candidates).

### 3.2 Two-Tier Scenario Taxonomy
To eliminate double-counting, scenarios are classified into:
1. **Primary Mutual-Exclusive Scenario Types:** Stored in [`BenchmarkScenario.scenario_type`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/models/domain.py). Every scenario belongs to **exactly one** primary type.
2. **Secondary Cross-Cutting Evaluation Dimensions:** Evaluated as subset slices by [`BenchmarkRunner`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/evaluation/benchmark_runner.py) across scenarios drawn from the primary types.

### 3.3 Primary Scenario Allocation Table (Strict Mathematical Reconciliation)

| Primary Scenario Type (`scenario_type`) | Inclusion Criteria & Operational Definition | Min Target (100 Total) | Min Share (%) | Stretch Target (150 Total) | Stretch Share (%) | Complete Pair Integrity |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Direct Positive (`direct_positive`)** | Baseline profile satisfying all statutory conditions of an in-force rule. | 22 | 22.0% | 34 | 22.67% | N/A |
| **Direct Negative / Exception (`direct_negative`)** | Profile outside statutory scope or satisfying an explicit statutory exemption/proviso. | 18 | 18.0% | 26 | 17.33% | N/A |
| **Minimal Pairs (`minimal_pair`)** | Paired profiles differing in exactly one legally operative condition that flips outcome. | 24 | 24.0% | 36 | 24.0% | Exactly 12 pairs (min) / 18 pairs (stretch) |
| **Invariance Pairs (`invariance`)** | Paired profiles differing only in legally irrelevant metadata, preserving identical outcome. | 16 | 16.0% | 24 | 16.0% | Exactly 8 pairs (min) / 12 pairs (stretch) |
| **Temporal Boundary (`temporal`)** | Profile evaluated at boundary dates ($T-1$, $T$, $T+1$) or within explicit transition windows. | 10 | 10.0% | 15 | 10.0% | N/A |
| **Incomplete Profile (`incomplete`)** | Profile omitting decisive facts, mandating `CONDITIONAL_MISSING_DATA` + exact missing fields. | 10 | 10.0% | 15 | 10.0% | N/A |
| **TOTAL PRIMARY SCENARIOS** | **Mutually exclusive partition of benchmark** | **100** | **100.0%** | **150** | **100.0%** | **All pairs complete** |

*Verification Check:*  
- $22 + 18 + 24 + 16 + 10 + 10 = 100$ scenarios ($100.0\%$).
- $34 + 26 + 36 + 24 + 15 + 15 = 150$ scenarios ($100.0\%$).
- Minimal pairs ($24$ and $36$) and invariance pairs ($16$ and $24$) are divisible by 2 with zero remainder, guaranteeing complete pair cardinality.

### 3.4 Secondary Cross-Cutting Evaluation Dimensions (Non-Additive)

These dimensions evaluate specific research capabilities without adding to the scenario headcount:

| Secondary Dimension Tag | Research Question | Source Subset Description | Planned Target Count |
|---|---|---|:---:|
| **Amendment / Version Chains** | RQ2, H1 | Scenarios testing point-in-time rules across $\ge 5$ verified version chains. Drawn from `direct`, `temporal`, and `minimal_pair`. | 12–16 scenarios across $\ge 5$ chains |
| **Numerical / Capacity Thresholds** | RQ1, RQ2 | Scenarios testing precision at $\text{threshold} \pm \epsilon$ (e.g. engine hp, capacity kg/day, additive ppm). Drawn from `minimal_pair` and `direct`. | 10–14 scenarios |
| **Impact & Action Mapping** | RQ5, H5 | Evaluates gold affected activities, documents, and action templates on all applicable scenarios. | Evaluated on all $\sim 45-65$ applicable scenarios |

---

## 4. Section 2 — Regulatory Coverage Matrix & Candidate Downgrade

In accordance with strict auditor standards, all provisions not mechanically inspected in primary Gazettes during this audit are labeled `UNVERIFIED_CANDIDATE`. Their thresholds and amendment relationships remain unresolved proposals until Gate 1 verification.

### 4.1 Candidate Clause Coverage Matrix

| Clause ID | Candidate Instrument Title | Candidate Requirement / Obligation | Candidate Condition / Threshold | Required Primary Source Document | Actual Inspection Status in This Audit | Legal Status |
|---|---|---|---|---|---|---|
| `REG-2494-47-R3` | Gazette 2494/47 | Retail mandatory labelling prohibition | `activity: food_mfg`, `prepackaged: true` | Gazette Extraordinary No. 2494/47, Page 1 | Inspected (`2494-47_E.pdf`, SHA-256 `83ed19c2...`) | **VERIFIED_PRIMARY_SOURCE** |
| `REG-2494-47-R3-B2B` | Gazette 2494/47 | B2B mandatory 10 disclosures + 3mm label | `market.b2b_only: true` | Gazette Extraordinary No. 2494/47, Pages 1–2 | Inspected (`2494-47_E.pdf`, SHA-256 `83ed19c2...`) | **VERIFIED_PRIMARY_SOURCE** |
| `CAND-2494-47-R4` | Gazette 2494/47 | Language requirements (Sinhala, Tamil, English) | Retail prepackaged vs B2B single language | Gazette Extraordinary No. 2494/47, Page 2 | Not line-audited in current task | **`UNVERIFIED_CANDIDATE`** |
| `CAND-2494-47-R7` | Gazette 2494/47 | Date marking & format of expiry/durability | Durability format by shelf life ($> 3$ months) | Gazette Extraordinary No. 2494/47, Pages 3–4 | Not line-audited in current task | **`UNVERIFIED_CANDIDATE`** |
| `CAND-2494-47-R9` | Gazette 2494/47 | Batch / lot identification requirements | Packaged food for distribution | Gazette Extraordinary No. 2494/47, Page 5 | Not line-audited in current task | **`UNVERIFIED_CANDIDATE`** |
| `CAND-2494-47-R18` | Gazette 2494/47 | Nutritional labelling & small-pack exemptions | Small pack surface area $< 100\text{ cm}^2$ | Gazette Extraordinary No. 2494/47, Pages 8–10 | Not line-audited in current task | **`UNVERIFIED_CANDIDATE`** |
| `CAND-PRESERV-04` | Food (Preservatives) Regulations | Preservative limits (e.g. sulfur dioxide) | Jams/cordials concentration threshold (ppm) | Official Gazette for Food (Preservatives) Regs | `preservative-english.pdf` exists; provision not audited | **`UNVERIFIED_CANDIDATE`** |
| `CAND-COLOUR-03` | Food (Colouring Substances) Regs 2011 | Schedule of permitted synthetic dyes | Food categories; infant food prohibition | Gazette 1718/12 (2011 amendment) | `food_amendment_..._2011_en.pdf` exists; not line-audited | **`UNVERIFIED_CANDIDATE`** |
| `CAND-FLAVOUR-05` | Food (Flavouring Substances) Regs 2013 | Monosodium glutamate (MSG) labelling | Added flavour enhancer declaration | Gazette 1837/25 (2013 regulations) | `food_flavouring_..._2013_en.pdf` exists; not line-audited | **`UNVERIFIED_CANDIDATE`** |
| `CAND-EPL-SCHED-B12` | CEA EPL Regulations (Gazette 1533/16) | Environmental Protection Licence Category B | Commercial bakeries with fuel/power $\ge 10\text{ hp}$ | Gazette Extraordinary No. 1533/16 (2008), Sched B | Source PDF not yet registered in SourceDocumentORM | **`UNVERIFIED_CANDIDATE`** |
| `CAND-EPL-SCHED-B15` | CEA EPL Regulations (Gazette 1533/16) | Environmental Protection Licence Category B | Grain milling capacity $\ge 500\text{ kg/day}$ | Gazette Extraordinary No. 1533/16 (2008), Sched B | Source PDF not yet registered in SourceDocumentORM | **`UNVERIFIED_CANDIDATE`** |
| `CAND-EPL-AMEND-22` | CEA EPL Amendment (Gazette 2264/18) | EPL horsepower threshold amendment | Proposed threshold shift to $\ge 15\text{ hp}$ | Gazette Extraordinary No. 2264/18 (2022) | Source PDF not yet registered in SourceDocumentORM | **`UNVERIFIED_CANDIDATE`** |
| `CAND-IND-REG-02` | Industrial Development Act Regs | Mandatory manufacturing registration | Threshold based on machinery value / workers | Industrial Development Act No. 36 of 1969 | Primary Act and Gazette orders not yet inspected | **`UNVERIFIED_CANDIDATE`** |
| `CAND-SWEET-04` | Food (Sweeteners) Regulations | Non-nutritive sweetener declaration | Food category and maximum limit | Official Food (Sweeteners) Gazette | Source PDF not yet registered in SourceDocumentORM | **`UNVERIFIED_CANDIDATE`** |

*Integrity Rule:* Gate 1 must explicitly audit each candidate against its authentic Gazette, verify character offsets and SHA-256 hashes, and only promote validated clauses to `VERIFIED_PRIMARY_SOURCE`.

---

## 5. Section 3 — Dataset Partitioning & Leakage Prevention Strategy

### 5.1 Definition of the Independent Grouping Unit
Partitioning scenarios by simple `scenario_id` or isolated `clause_id` is statistically invalid because related legal rules share common definitions, statutory structures, and amendments.

The atomic, indivisible unit of dataset partitioning is defined as the **Clause Family / Version Chain Group (`group_id`)**:
$$\text{Group}(C) = \{ c \mid c \text{ is related to } C \text{ by amendment, shared statutory exception, or co-dependent definition} \}$$

**Indivisibility Constraints:**
1. **Pair Cohesion:** Both members of every minimal pair (`PAIR-xxxA` and `PAIR-xxxB`) and invariance pair (`INV-xxxA` and `INV-xxxB`) share the exact same `group_id` and must be placed in the same partition.
2. **Version Chain Cohesion:** A base clause (V1) and its amending clause (V2) belong to the same `group_id`. Placing V1 in Train and V2 in Test is strictly forbidden because knowledge of the base clause leaks the structure of the amendment.
3. **Co-Dependent Provisos:** Regulation 3 main body and Regulation 3 Provisos (a) and (b) belong to a single `group_id` (`GRP-FCAU-REG3`).

### 5.2 Statistical Reality of Three-Way Splits on Small Groups
The preliminary plan proposed a 60% Train / 20% Val / 20% Test split. A critical statistical analysis reveals:
- Sourcing 25–40 clauses across Sri Lankan food regulations yields approximately **12 to 18 independent clause families (`group_id` units)**.
- If $N_{groups} = 15$, a $20\%$ test partition contains only **3 independent groups** ($\sim 20-30$ scenarios).
- **Statistical Consequence:**
  - Clustered bootstrap confidence intervals on 3 test clusters will be excessively wide ($\pm 15-25\%$), making system comparison inconclusive.
  - A 3-group validation set offers insufficient power for prompt or threshold tuning.
  - Performance on 1 idiosyncratic clause can swing the test macro-F1 by 30 percentage points.

### 5.3 Feasibility Evaluation Protocol & Alternative Split Designs
Before freezing the partition split, Gate 1 must establish the final inventory of independent groups ($N_{groups}$) and apply the following decision rule:

```
[Determine Final Independent Group Inventory: N_groups]
  │
  ├── IF N_groups >= 25:
  │     Adopt 60% Train / 20% Val / 20% Test Split
  │     (Sufficient power: >= 5 independent test groups)
  │
  ├── IF 12 <= N_groups < 25:
  │     Adopt 75% Train / 25% Held-Out Test Split
  │     (Use 5-fold cross-validation on Train for tuning; eliminates high-variance 2-group Val set)
  │
  └── IF N_groups < 12:
        PROHIBIT CLAIMS OF GENERALIZATION TO UNSEEN CLAUSES
        Adopt Leave-One-Group-Out Cross-Validation (LOGO-CV)
        Report results strictly as point-in-time and conditionality reasoning across available clauses.
```

*Generalization Claim Policy:* No research paper or report may claim "generalization to unseen regulatory clauses" unless the held-out test partition contains at least 5 statistically independent, un-leaked clause families.

---

## 6. Section 4 — Source Preservation & Exclusion Protocol

### 6.1 Strict Prohibition on File Deletion
Unvetted files, draft documents, and test artifacts must be excluded from the legal ground-truth registry. However, **no files shall be deleted, moved, or renamed from `backend/data/raw_sources/`**. Physical files are preserved to maintain git history and reproducible audit trails.

### 6.2 Separation of Repository Storage vs. Legal Ground Truth
A file's physical presence in `backend/data/raw_sources/` does **not** grant it status as legal ground truth. A document enters the benchmark corpus **only** when ingested into [`SourceDocumentORM`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/db/models.py) with verified publication metadata and an official government URL.

### 6.3 Formal Exclusion Register

The following artifacts currently stored in `backend/data/raw_sources/` are formally barred from benchmark ground truth:

| Filename | File Size | Exclusion Reason | Review Status | Mandatory Repository Action |
|---|---|---|---|---|
| `Lec 03.pdf` | $1,583,780\text{ bytes}$ | Academic slide deck on food legislation; secondary commentary, not primary law. | **EXCLUDED_NON_STATUTORY** | Preserve on disk; do not ingest into `source_documents`. |
| `Labelling_Regulations_Final_-_11.02.2026.pdf` | $613,690\text{ bytes}$ | Internal draft of Food Advisory Committee; not officially promulgated in Gazette. | **EXCLUDED_NON_PROMULGATED** | Preserve on disk for draft-comparison exploratory studies; exclude from benchmark ground truth. |
| `test_gazette_upload.pdf` | $1,037\text{ bytes}$ | Dummy PDF fixture generated during ingestion pipeline testing. | **EXCLUDED_TEST_FIXTURE** | Preserve in test directory; do not register as official source. |
| Multiple $1,037\text{-byte}$ hash-named PDFs | $1,037\text{ bytes}$ | Duplicate test fixture uploads generated by integration tests. | **EXCLUDED_TEST_FIXTURE** | Preserve on disk; bar from benchmark corpus registration. |

---

## 7. Section 5 — Annotation Lifecycle & Gold-Label Policy

### 7.1 Multi-Level Unit of Annotation
Legal compliance reasoning involves multi-layered representations. The benchmark annotation protocol defines distinct units of review:

```
[1. Source Document Level] -> Authenticity, official publication date, SHA-256 hash.
  │
  ▼
[2. Clause / Rule Level]   -> Quote span verbatim match, character offsets, formalizability,
  │                           bounded JSON rule conditions, exceptions, obligation type.
  ▼
[3. Scenario Level]        -> Business profile plausibility, perturbation validity,
                              outcome status (APPLICABLE / NOT_APPLICABLE / CONDITIONAL),
                              temporal validity status (IN_FORCE / NOT_YET_IN_FORCE).
```

*Integrity Principle:* A scenario cannot be marked gold if the underlying rule is unverified. Both the rule and the scenario must satisfy adjudication gates.

### 7.2 Independent Dual-Annotation & Disagreement Resolution
1. **Blind Annotation:** Primary annotator (researcher) and secondary annotator independently extract rules and label scenario outcomes without access to each other's work.
2. **Labels Requiring Independent Agreement:**
   - Applicability outcome status (`APPLICABLE`, `NOT_APPLICABLE`, `CONDITIONAL_MISSING_DATA`, `UNSUPPORTED`).
   - Decisive conditions and exceptions.
   - Temporal status (`IN_FORCE`, `NOT_YET_IN_FORCE`, `SUPERSEDED`).
   - Minimum missing fields on incomplete profiles.
   - Verbatim quote spans.
3. **Disagreement Recording:** Disagreements are automatically logged into [`HumanReviewAuditORM`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/db/models.py). No annotator may overwrite a disputed label without documented reconciliation.

### 7.3 Inter-Annotator Agreement & Cohen's Kappa Limitations
- Target threshold: Unweighted Cohen's kappa $\kappa \ge 0.85$.
- **Known Methodological Limitation (The Kappa Paradox):** In legal compliance datasets where specific outcome classes (e.g. `APPLICABLE`) have high prevalence, standard unweighted kappa can be paradoxically low despite high percentage agreement.
- **Reporting Protocol:** The evaluation must report:
  1. Percentage raw agreement ($P_o$).
  2. Unweighted Cohen's kappa ($\kappa$).
  3. Prevalence-Adjusted Bias-Adjusted Kappa (PABAK) to account for skewed category distributions.

### 7.4 Role and Qualifications of External Legal Reviewer
- **Qualifications:** The external legal reviewer must be a qualified Sri Lankan attorney-at-law, state counsel, or senior regulatory enforcement officer with demonstrated expertise in administrative or food safety law.
- **Scope of Sample Review:** The expert reviews a representative sample of at least $20\%$ of scenarios, plus $100\%$ of cases with inter-annotator disagreement or statutory ambiguity.
- **Crucial Gold-Status Boundary:** External review of a $20\%$ sample confirms the statistical reliability of the annotation protocol; **it does not validate the remaining $80\%$ of rules as expert-adjudicated gold**.
- **Provisional Status Safeguard:**
  - Scenarios reviewed and signed off by the expert: `review_status="EXPERT_ADJUDICATED_GOLD"`, `is_gold_scenario=True`, `is_gold_rule=True`.
  - Scenarios passing dual annotation without expert sign-off: `review_status="DUAL_ANNOTATED_RESEARCHER"`, `is_gold_scenario=False`, `is_gold_rule=False`.
  - Scenarios with primary annotation only: `review_status="PROVISIONAL_PRIMARY_REVIEW"`, `is_gold_scenario=False`, `is_gold_rule=False`.

---

## 8. Section 6 — Frozen-Proposal Target Discrepancy

### 8.1 Documentation of the Textual Conflict
Proposal v4 contains an unresolved textual discrepancy regarding corpus targets:
- **Section 6 ("Scope", Page 4):**
  > *"Corpus: 20 to 30 authoritative instruments, prioritising 25 to 40 usable clauses and at least 5 amendment/version chains."*
- **Section 9.1 ("Dataset A: regulatory corpus", Page 9):**
  > *"25 to 40 instruments from official sources (FCAU, Ministry of Industry, CEA, EPF/ETF, Gazette), including real amendment chains."*

### 8.2 Analysis & Proposed Interpretation
- In Sri Lankan administrative law, major regulatory instruments contain dozens of substantive clauses. Requiring 40 distinct *instruments* for 40 clauses would compel the inclusion of trivial or repetitive gazette notifications.
- **Proposed Interpretation:** Adopt the Section 6 standard: **20 to 30 official statutory instruments** (including base acts, specific regulations, and amending gazettes) yielding **25 to 40 substantive, conditional clauses**.
- **Governance Status:** This conflict is **not** formally resolved in this audit. It is submitted to the lead researcher as **Decision 1** for formal approval.

---

## 9. Section 7 — Methodological Decisions Requiring Researcher Approval

Before Gate 1 execution begins, the lead researcher must formally approve the following decisions:

1. **Decision 1: Regulatory Corpus Instrument Target Count:**  
   *Question:* Confirm adopting the Section 6 standard (20–30 instruments yielding 25–40 conditional clauses) over the Section 9.1 wording (25–40 instruments).  
   *Auditor Recommendation:* **Approve 20–30 instruments.** Protects legal realism and avoids padding with trivial notices.
2. **Decision 2: Permanent Exclusion of Working Drafts from Legal Ground Truth:**  
   *Question:* Confirm that `Labelling_Regulations_Final_-_11.02.2026.pdf` (FAC Draft) and `Lec 03.pdf` are barred from the benchmark ground-truth corpus while remaining preserved on disk.  
   *Auditor Recommendation:* **Approve permanent exclusion.** Only promulgated Gazettes and primary Acts can serve as legal ground truth.
3. **Decision 3: Deferral of Secondary Domain 4 (EPF/ETF Labour Obligations):**  
   *Question:* Formally decide whether to defer EPF/ETF obligations as permitted by the Week-3 decision gate in Proposal v4.  
   *Auditor Recommendation:* **Approve deferral.** Food labelling, compositional additive standards, and environmental licensing provide over 35 rich conditional clauses. Deferring EPF/ETF preserves research focus.
4. **Decision 4: Group-Count-Conditioned Partition Split Strategy:**  
   *Question:* Confirm adopting the group-feasibility protocol (Section 5.3) allowing a 75/25 split or cross-validation if the final independent group count $N_{groups} < 25$, rather than forcing a 60/20/20 split.  
   *Auditor Recommendation:* **Approve group-conditioned split.** Prevents high-variance 2-group validation sets and avoids unsupportable generalization claims.

---

## 10. Section 8 — Phased Implementation Roadmap & Verification Gates

```
Gate 1: Source Register & Corpus Verification
  │   - Verify 20–30 instruments; compute SHA-256; register official URLs.
  │   - Populate Exclusion Register; audit candidate clauses against primary text.
  ▼
Gate 2: Schema & Validator Upgrades
  │   - Add typed `chain_id` and first-class provenance fields to BenchmarkScenario.
  │   - Implement dynamic rule/source verification in benchmark_validator.py.
  ▼
Gate 3: Pilot Expansion Batch (30 Scenarios across 6 Clauses)
  │   - Author and dual-annotate 30 scenarios; compute Cohen's kappa and PABAK.
  │   - Verify pair integrity and temporal boundaries; maintain provisional status.
  ▼
Gate 4: Full Benchmark Expansion (100–150 Scenarios across 25–40 Clauses)
  │   - Complete balanced taxonomy allocation; verify 0 duplicate IDs and 0 pair leaks.
  │   - Conduct external legal expert review on >= 20% sample; assign gold status to signed-off cases.
  ▼
Gate 5: Partition Freeze & Evaluation Lock
      - Compute final N_groups; execute approved split; freeze test SHA-256 hash.
      - Lock prompt configurations and parameters; authorize baseline B0–B3 comparative runs.
```

---

## 11. Final Verification & Repository Integrity

1. **Repository Code & Benchmark State:**
   - Zero changes made to application code, domain models, validators, or baselines.
   - [`backend/data/benchmark/regulation_3_slice.jsonl`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/data/benchmark/regulation_3_slice.jsonl) is untouched (12 provisional scenarios preserved).
   - Zero source PDF files moved, renamed, or deleted.
2. **Git Working Tree Status:**
   - Only [`RegImpact-SL_Benchmark_Expansion_Plan.md`](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/RegImpact-SL_Benchmark_Expansion_Plan.md) is modified/untracked.
   - No git commits executed.
3. **Internal Consistency Verification:**
   - Minimum scenario allocation ($22 + 18 + 24 + 16 + 10 + 10 = 100$) and stretch allocation ($34 + 26 + 36 + 24 + 15 + 15 = 150$) arithmetically reconcile to $100.0\%$.
   - Minimal pairs ($12$ and $18$ pairs) and invariance pairs ($8$ and $12$ pairs) are complete with zero unpaired scenarios.
   - All proposed non-audited provisions are labeled `UNVERIFIED_CANDIDATE`.

# RegImpact-SL — Scope Decision Record: Corpus & Benchmark Scope Lock

**Document Status:** `FORMALLY DECIDED: OPTION A SELECTED`  
**Governing Specification:** `RegImpact-SL_Project_Proposal_v4_FINAL.md` (Frozen Proposal v4)  
**Date Created:** 2026-10-26  
**Decision Date:** 2026-10-26  
**Auditor:** Senior Research Engineer, Benchmark Methodologist, Regulatory Data Integrity Auditor

---

## 1. Context & Purpose

This decision record provides the project owner with an authoritative, text-grounded analysis of the scope requirements in the frozen proposal.

In previous phase reports (Phase 3.3, 3.4, and 3.5), an assertion was repeatedly made that Section 9.1 required *"50–100 gazetted instruments and ~200–400 operative provisions"*.  
**An independent text audit of `RegImpact-SL_Project_Proposal_v4_FINAL.md` reveals that this claim was false.** That phrase does not appear anywhere in Proposal v4.

Instead, the actual frozen proposal text contains a much narrower, well-bounded textual ambiguity between Section 6, Section 9.1, and Section 9.2.

---

## 2. Text Comparison of Frozen Proposal v4

| Proposal Section | Exact Written Proposal Text | Scope Parameter | Interpretation & Requirement Level |
| :--- | :--- | :--- | :--- |
| **Section 6**<br>*(Scope, line 98)* | *"Corpus: 20 to 30 authoritative instruments, prioritising 25 to 40 usable clauses and at least 5 amendment/version chains."* | **20–30 instruments**<br>25–40 clauses<br>$\ge 5$ amendment chains | **Governing Boundary (Scope Definition)**.<br>Prioritizes depth over superficial breadth; establishes 25–40 operative clauses as the core research target. |
| **Section 9.1**<br>*(Dataset A, line 318)* | *"25 to 40 instruments from official sources (FCAU, Ministry of Industry, CEA, EPF/ETF, Gazette), including real amendment chains."* | **25–40 instruments**<br>Multi-authority representation | **Corpus Collection Target**.<br>Represents the upper-bound instrument intake across all 4 potential regulatory domains. |
| **Section 9.2**<br>*(Dataset B, line 324)* | *"Target: 25 to 40 distinct clauses and 100 to 150 scenarios, subject to the availability of sufficiently clear authoritative clauses. Minimum acceptable benchmark: 100 scenarios covering at least 25 distinct clauses; 150 is a stretch target."* | **$\ge 25$ distinct clauses**<br>**100 scenarios (minimum)**<br>150 scenarios (stretch target) | **Mandatory Benchmark Target**.<br>Strict minimum of 100 scenarios across at least 25 distinct clauses; 150 scenarios is a stretch target. |
| **Section 10.3**<br>*(Statistical Treatment, line 383)* | *"Confidence intervals by clause-level (cluster) bootstrap, because scenarios from the same clause are not independent. Paired comparisons... Effect sizes are reported alongside significance."* | **Clause-clustered bootstrap** | **Mandatory Statistical Requirement**.<br>Requires at least 25 independent clause clusters ($N \ge 25$) for statistically valid bootstrap resampling. |
| **Section 11**<br>*(Implementation Priority Rule, line 400)* | *"The research result is the compile-verify-execute comparison, not the UI. If time becomes constrained, cut in this order: UI richness, broad document coverage, counterfactual breadth, then secondary EPF/ETF coverage. Protect the gold rules, benchmark quality, B0-B3 baselines, deterministic engine, provenance, core evaluation, and reproducible experiments."* | **Explicit Priority Rule** | **Mandatory Contingency Hierarchy**.<br>Explicitly authorizes cutting broad document coverage and secondary EPF/ETF coverage to protect benchmark quality and baselines. |

---

## 3. Analysis of Decision Options

### Option A: Focused Food Control & Compositional Scope (Section 6 + Section 11 Priority Rule) — **[RECOMMENDED]**
- **Corpus**: 6–10 prioritized, fully verified Gazettes within Food Control & Labelling (Gazettes 2494/47, 2494/06, 2113/16, 1795/51, 2443/27, and post-OCR 1688/28).
- **Clauses**: Exactly **25 distinct operative clauses** selected from these instruments.
- **Benchmark**: Exactly **100 scenarios** (minimum required by §9.2), allocated across the 25 clauses (~4 scenarios per clause: 1 direct, 2 minimal pair, 1 incomplete/temporal/invariance).
- **Advantages**:
  1. Feasible within the human-review bottleneck (25 rules to review, 100 scenarios to annotate).
  2. Statistically valid: 25 distinct clause clusters satisfy the cluster bootstrap requirement of §10.3.
  3. Grounded in authentic, promulgated Sri Lankan food regulations already in repository storage.
  4. Fully aligned with Section 11 Priority Rule ("cut broad document coverage... protect benchmark quality").
- **Tradeoffs**: Omits CEA environmental licensing and EPF/ETF secondary domains.

---

### Option B: Cross-Domain Multi-Authority Scope (Section 9.1 Upper Bound)
- **Corpus**: 25–40 instruments spanning Food Control (FCAU), Industry Registration (Ministry of Industry), Environmental Licensing (CEA), and EPF/ETF.
- **Clauses**: 30–40 operative clauses across 4 domains.
- **Benchmark**: 100–150 scenarios.
- **Advantages**: Demonstrates cross-authority generalization across multiple government departments.
- **Tradeoffs**:
  1. High acquisition and verification overhead: requires collecting, verifying, and extracting 20+ additional official PDFs from CEA, Ministry of Industry, and Department of Labour.
  2. Drastically increases human review effort: 40 rules $\times$ 2 annotators + expert adjudication.
  3. Higher risk of encountering non-compilable discretionary standards (e.g. CEA environmental clearance guidelines).

---

## 4. Formal Project Owner Decision Block

```text
================================================================================
PROJECT OWNER SCOPE DECISION RECORD
================================================================================

Selected Option: [X] Option A (Focused Food Control Scope: 25 Clauses, 100 Scenarios)
                 [ ] Option B (Cross-Domain Scope: 25-40 Instruments, 100-150 Scenarios)
                 [ ] Custom Scope Directive

Decision Status: FORMALLY DECIDED & LOCKED
Decision Date:   2026-10-26
Authority:       Project Owner Directive (Phase 3.7 Instruction)

--------------------------------------------------------------------------------
DECISION RATIONALE & OPERATIONAL GOVERNANCE
--------------------------------------------------------------------------------

1. Priority Rule Authority:
   Section 11 (line 400) of Proposal v4 establishes the governing contingency hierarchy:
   "If time becomes constrained, cut in this order: UI richness, broad document
   coverage, counterfactual breadth, then secondary EPF/ETF coverage. Protect the
   gold rules, benchmark quality, B0-B3 baselines, deterministic engine, provenance,
   core evaluation, and reproducible experiments."
   Option A directly implements this rule by focusing resources on benchmark quality,
   paired scenario consistency, and verified clause grounding.

2. Statistical Validity & Benchmark Thresholds:
   Option A achieves the mandatory minimum of Section 9.2 (line 324): at least 100
   scenarios across at least 25 distinct clauses. It also satisfies Section 10.3
   (line 383), which requires clause-level (cluster) bootstrap resampling with N >= 25
   independent clause clusters.

3. Human Annotation Feasibility:
   Compiling and verifying 25 operative clauses and 100 scenarios is bounded and
   tractable within human-review constraints (requiring 25 candidate rules to review
   and 100 scenarios for double annotation and sample expert adjudication), preventing
   compromises to annotation integrity.

--------------------------------------------------------------------------------
CANDIDATE REGULATORY SOURCES (FOCUSED FOOD CONTROL SCOPE)
--------------------------------------------------------------------------------
The following instruments constitute the candidate pool for Option A.
Note: These are candidate instruments, not automatically approved sources or
eligible clauses; each clause must be individually verified and reviewed:

1. Gazette Extraordinary No. 2494/47 (Food Labelling and Advertising Regulations 2026)
   - Status: Promulgated, authentic primary gazette (25 clauses segmented in DB)
   - Verified SHA-256: 83ed19c22873471652d0073fe16c977442e42c8ecac2edf1d691d00d78d8a054

2. Gazette Extraordinary No. 2494/06 (Food Colour Coding for Sugar Levels Amendment 2026)
   - Status: Promulgated, authentic primary gazette (4 clauses segmented in DB)
   - Verified SHA-256: 15803fe0b14aabe0c79126ebe7c8834d8063b6ed8c2a9033c1201ff538bcd95b

3. Gazette Extraordinary No. 2113/16 (Food Preservatives Regulations 2019)
   - Status: Promulgated, authentic primary gazette (8 clauses segmented in DB)
   - Verified SHA-256: 3f85f3ef96b7622bdd3e45d7cc642fd96fdbd83a9f84f35f048121eab3e4016f

4. Gazette Extraordinary No. 1795/51 (Food Flavouring Substances and Flavour Enhancers 2013)
   - Status: Promulgated, authentic primary gazette (7 clauses segmented in DB)
   - Verified SHA-256: b78479b6b08d12e11fd27cfc39677d5a284bc147bf16a777eafb495b86f4135a

5. Gazette Extraordinary No. 2443/27 (Food Labelling and Advertising Amendment 2025)
   - Status: Promulgated, authentic amendment chain to 2494/47 (4 clauses segmented in DB)
   - Verified SHA-256: d7852dcc0da491ee0f67dbc355ad3ed96c1b860018b6151204d0db9d3fe2f45d

6. Gazette Extraordinary No. 1688/28 (Food Colouring Substances Regulations 2011)
   - Status: Authentic scanned raster PDF; 0 embedded text characters; contains two
     native 300 DPI PNG scans. Candidate source subject to Tesseract OCR and visual
     page verification before clause ingestion.
   - Verified SHA-256: 3cd9948d2c334d08a11dd5bc9cc1f1a1ec053d6e819ea30f205687dda7c342c7

--------------------------------------------------------------------------------
EXPLICIT DOMAIN EXCLUSIONS
--------------------------------------------------------------------------------
Under this locked Option A scope:
- Central Environmental Authority (CEA) Environmental Protection Licensing (EPL)
  regulations and National Environmental Act schedules are EXCLUDED.
- Employees' Provident Fund (EPF) and Employees' Trust Fund (ETF) labour-related
  regulations are EXCLUDED.
- Neither domain shall be introduced into the benchmark or corpus unless the project
  owner formally issues an explicit scope directive amending this record.

--------------------------------------------------------------------------------
DOCUMENTATION OF PROPOSAL TEXTUAL INCONSISTENCY & OPERATIONAL INTERPRETATION
--------------------------------------------------------------------------------
1. Textual Inconsistency in Frozen Proposal v4:
   - Section 6 (line 98) specifies: "Corpus: 20 to 30 authoritative instruments,
     prioritising 25 to 40 usable clauses and at least 5 amendment/version chains."
   - Section 9.1 (line 318) specifies: "25 to 40 instruments from official sources
     (FCAU, Ministry of Industry, CEA, EPF/ETF, Gazette), including real amendment chains."
   - Section 9.2 (line 324) specifies: "Target: 25 to 40 distinct clauses and 100 to 150
     scenarios... Minimum acceptable benchmark: 100 scenarios covering at least 25
     distinct clauses; 150 is a stretch target."

2. Operational Interpretation:
   The frozen Proposal v4 document (`RegImpact-SL_Project_Proposal_v4_FINAL.md`) is
   strictly preserved without modification. The textual variance between Section 6
   (20-30 instruments) and Section 9.1 (25-40 instruments) is recorded as a known
   drafting inconsistency in the frozen proposal. Option A operationally interprets
   the research commitment as governed by the clause-level and benchmark targets of
   Section 6, Section 9.2, and Section 11 Priority Rule: achieving >= 25 distinct
   operative clauses and >= 100 scenarios across authentic Food Control regulations
   with high provenance and paired scenario integrity.

================================================================================
RECORDED DECISION STATUS: OPTION A LOCKED (2026-10-26)
================================================================================
```

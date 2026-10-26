# RegImpact-SL — Phase 3.8: Bounded Rule Correction and Source Verification Report

**Governing Specification:** `RegImpact-SL_Project_Proposal_v4_FINAL.md` (Frozen Development Baseline)  
**Evaluation Date:** 2026-10-27  
**Auditor Role:** Senior Research Engineer and Critical Regulatory-Source Verification Auditor  
**Preceding Audit Reference:** `docs/PHASE_3_6_SOURCE_VALIDATION_AND_EXPANSION_FEASIBILITY_REPORT.md`  
**Scope Decision Reference:** `docs/PROJECT_OWNER_SCOPE_DECISION_RECORD.md` (Option A Locked)  
**Candidate Register Reference:** `docs/CANDIDATE_RULE_HUMAN_REVIEW_REGISTER.md`  

---

## 1. Executive Summary

Phase 3.8 executes the bounded regulatory source verification and rule correction protocol mandated by the project owner following Phase 3.6 and Phase 3.7. In accordance with strict empirical research standards, this phase resolves three critical rule anomalies without expanding the benchmark, mutating the PostgreSQL database without authorization, or compromising the frozen architecture.

### Key Outcomes
1. **Physical Source Grounding Verified**:
   - **Gazette 1795/51 (Flavourings 2013)**: Regulation 7(ii) was physically audited on Page 2. The exact verbatim text `"(ii) shall not be added to any food for infants or young children below three years of age; and"` was confirmed. The statutory definition in Regulation 10 (Page 3) was verified. Regulation 8(2)(d) was physically audited on Page 2, confirming the exact statutory wording for flavour enhancer label declarations.
   - **Gazette 2113/16 (Preservatives 2019)**: Schedule II Item 3.1 was physically audited on Page 5. The source explicitly distinguishes standard jams (`Item 3.1(h)`: Sorbates maximum $300\text{ mg/kg}$) from low-sugar / sugar-free jams (`Item 3.1(i)`: Sorbates maximum $500\text{ mg/kg}$).
2. **Audit Root-Cause Reconciliation**:
   - The line-by-line audit revealed that the underlying PostgreSQL database records (`RuleORM`) and the Phase 3.3 segmentation pipeline (`execute_phase_3_3_segmentation.py`) **already contained the exact verbatim quotes on Page 2 and Page 5**.
   - The primary defect resided in `docs/CANDIDATE_RULE_HUMAN_REVIEW_REGISTER.md` (compiled during Phase 3.5), which had erroneously cited Regulation 7(i) on Page 3 with a foreign paraphrased quote, Regulation 8 on Page 3 with an LLM summary, and Schedule II Item 3.1 on a non-existent "Page 13".
   - The human review register has been fully updated and corrected against physical sources.
3. **Database Mutation Invariant Preserved**:
   - In accordance with Critical Integrity Constraint 4, **zero database mutations, resets, or migrations were executed**.
   - A formal, itemized database authorization request is detailed in Section 7 for the project owner's approval before modifying any stored record.
4. **Focused Test Suite Created**:
   - A dedicated 6-test suite (`backend/tests/test_phase_3_8_source_verification.py`) was implemented to enforce PDF text extraction grounding, database verifier conformance, and statutory scope distinctions.
   - 100% of the focused suite passed (`6 passed in 4.02s`). Full multi-phase regression suite passed completely (**52 passed across 5 test suites in 40.35s**).
5. **Zero Gold Label Contamination**:
   - All 10 candidate rules remain strictly isolated in `PENDING_REVIEW` with `is_gold_rule=False`.
   - All 30 benchmark scenarios remain strictly provisional with `is_gold_scenario=False`.

---

## 2. Critical Integrity Constraints & Verification

| # | Integrity Constraint | Compliance Status | Direct Evidence |
| :--- | :--- | :---: | :--- |
| **1** | Inspect `git status --short` before action; preserve pre-existing files | **COMPLIANT** | Executed git status check; zero untracked or modified working files damaged. |
| **2** | Do not reset, clean, stash, commit, rebase, or rewrite Git history | **COMPLIANT** | No history modification or working tree cleanup executed. |
| **3** | Do not modify frozen Proposal v4 | **COMPLIANT** | `RegImpact-SL_Project_Proposal_v4_FINAL.md` preserved without a single byte modified. |
| **4** | Zero DB mutation without prior explanation and authorization | **COMPLIANT** | Database read-only; 0 rows inserted, updated, or deleted. |
| **5** | Do not approve or reject candidates through UI or API | **COMPLIANT** | Candidate review statuses untouched; `/admin/reviews` workflow unaltered. |
| **6** | Do not mark any rule or scenario as gold | **COMPLIANT** | Live DB verified: 0 gold rules, 0 gold scenarios. |
| **7** | Do not create synthetic text, quotes, or expert decisions | **COMPLIANT** | All verified text extracted verbatim from physical government gazettes. |
| **8** | Do not make broad refactors or change unrelated rules | **COMPLIANT** | Scope strictly bounded to Rules 8, 10, and 6. |
| **9** | Treat legal interpretations as unresolved unless evidence supports | **COMPLIANT** | Ambiguities flagged for human legal review in the review register. |
| **10** | Do not treat passing quote checks as proof of legal validity | **COMPLIANT** | Verifier passes confirmed only syntactic grounding; legal questions flagged. |

---

## 3. Physical Source Verification Audit

### Issue A: Infant Prohibition Rule (`RULE-FLAVOUR-INFANT-PROHIBITION`)
- **Physical Document**: `backend/data/raw_sources/food_flavouring_substances_and_flavour_enhancers_regulations_2013_en.pdf`
- **Official Title**: The Sri Lanka Gazette Extraordinary No. 1795/51 (2013-02-01), Food (Flavouring Substances and Flavour Enhancers) Regulations 2013.
- **Physical Inspection Details**:
  - **Page 2 (PDF Page Index 1)** contains operative Regulation 7:
    ```text
    7. Flavour enhancers –
       (i) may be added to foods subject to observance of Good Manufacturing Practices (GMP)
           and where the label carries clearly a declaration as to the particular substance
           or substances used ;
       (ii) shall not be added to any food for infants or young children below three years
            of age; and
       (iii) shall not be used in the foods specified in Schedule III hereto.
    ```
  - **Page 3 (PDF Page Index 2)** contains statutory definition under Regulation 10:
    ```text
    ‘‘foods for infants or young children below three years of age ’’ means foods that are
    specifically prepared, manufactured or marketed for infants or young children below
    three years of age.
    ```
- **Findings**:
  - Regulation 7(i) governs GMP and declaration for general food.
  - Regulation 7(ii) contains the absolute prohibition against adding flavour enhancers to food for infants or young children below three years of age.
  - The Phase 3.5 human review register had incorrectly listed Regulation 7(i) on Page 3 with foreign text (`"(i) shall not be added to any food for infants and young children except as permitted in the regulations made under the Act;"`).
  - In PostgreSQL, the `rules` record already stored the exact verbatim quote: `"(ii) shall not be added to any food for infants or young children below three years of age; and"`, located on Page 2. However, `source.clause` was stored as `"Regulation 7"` rather than specifying `"Regulation 7(ii)"`.

### Issue B: Flavour-Label Declaration Rule (`RULE-FLAVOUR-LABEL-DECLARATION`)
- **Physical Document**: `backend/data/raw_sources/food_flavouring_substances_and_flavour_enhancers_regulations_2013_en.pdf`
- **Official Title**: Gazette Extraordinary No. 1795/51 (2013-02-01).
- **Physical Inspection Details**:
  - **Page 2 (PDF Page Index 1)** contains operative Regulation 8:
    ```text
    8. (1) Labelling of an article of food containing either a flavouring substance or
           a flavour enhancer shall be in compliance with the provisions of the Food
           (Labelling and Advertising) Regulations - 2005 published in Gazette Extraordinary
           No. 1376/9 of January 19, 2005 as may be amended or replaced subsequently.
       (2) The label printed on or attached to the package of food containing –
           (a) natural flavouring substances ...
           (b) nature - identical flavouring substances ...
           (c) artificial flavouring substances ...
           (d) any flavour enhancer or enhancers as an ingredient, shall include the
               words ‘‘flavour enhancer used’’ or ‘‘flavour enhancers used’’ as the case
               may be, along with the common name or names and the INS number or numbers,
               as the case may be.
       (3) The label printed on or attached to the package of food shall not describe
           any nature - identical flavours in conjunction with any food as ‘‘natural flavours’’.
       (4) No declaration shall be made on the label printed on or attached to the package
           of food, of the absence of any single flavour enhancer when the food contains
           any other flavour enhancer or enhancers.
    ```
- **Findings**:
  - Sub-clause (2)(d) is the specific operative mandate for flavour enhancer labelling.
  - The Phase 3.5 review register had stored a 322-character synthetic summary quote on Page 3.
  - In PostgreSQL, the `rules` record already stored the exact verbatim quote on Page 2: `"(d) any flavour enhancer or enhancers as an ingredient, shall include the words \u2018\u2018flavour enhancer used\u2019\u2019 or \u2018\u2018flavour enhancers used\u2019\u2019 as the case may be, along with the common name or names and the INS number or numbers, as the case may be."`. However, `source.clause` was stored as `"Regulation 8"` rather than `"Regulation 8(2)(d)"`.

### Issue C: Preservative Jam/Jelly Limit (`RULE-PRESERVATIVE-JAM-JELLY-LIMIT`)
- **Physical Document**: `backend/data/raw_sources/preservative-english.pdf`
- **Official Title**: The Sri Lanka Gazette Extraordinary No. 2113/16 (2019-03-05), Food (Preservatives) Regulations 2019.
- **Physical Inspection Details**:
  - **Page 5 (PDF Page Index 4)** contains Schedule II, Section 3.1:
    ```text
    SCHEDULE II
    Articles of Food which may contain permitted preservatives
    3.1 Fruits and fruit products:
        (f) Fruit based spreads e.g. chutney:
            Sorbates 300 mg/kg, Propionates GMP;
        (g) Fruit preparations including pulp, puree, fruit topping:
            Sorbates 1000 mg/kg, Sulphites 100 mg/kg, Propionates GMP;
        (h) Jams, Jellies, marmalades:
            Sorbates 300 mg/kg, Sulphites (as residual SO2) 100 mg/kg, Propionates GMP;
        (i) Jams, Jellies and marmalades, low in sugar or sugar free:
            Sorbates 500 mg/kg, Sulphites (as residual SO2) 100 mg/kg, Propionates GMP.
    ```
- **Findings**:
  - The regulation establishes two distinct legal standards:
    - **Item 3.1(h)**: Standard Jams, Jellies, and Marmalades $\to$ Sorbates $300\text{ mg/kg}$.
    - **Item 3.1(i)**: Low in sugar or sugar-free Jams, Jellies, and Marmalades $\to$ Sorbates $500\text{ mg/kg}$.
  - The current database rule `RULE-PRESERVATIVE-JAM-JELLY-LIMIT` models only Item 3.1(h) with an unconstrained product category `jams_jellies_marmalades`.
  - If a manufacturer produces low-sugar jam with $450\text{ mg/kg}$ sorbates, the current rule would evaluate it as non-compliant under the $300\text{ mg/kg}$ threshold, despite being fully lawful under Item 3.1(i).
  - The review register had cited "Page 13", which does not exist in Gazette 2113/16 (document terminates on Page 12). The actual table is located on Page 5.

---

## 4. Source Audit Findings Table

| Rule ID | Actual Source & Provision | Existing Defect | Evidence Inspected | Proposed Correction | Unambiguous? | Human Legal Review Needed? |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| `RULE-FLAVOUR-INFANT-PROHIBITION` | Gazette 1795/51, Page 2, Regulation 7(ii) | Review register cited Reg 7(i) on Page 3 with foreign text. DB quote was verbatim on Page 2, but `clause` string was coarse `"Regulation 7"`. | Page 2 PDF extraction; Reg 10 statutory definition on Page 3; live PostgreSQL `rules` and `clauses` tables. | Corrected review register entry 8 and summary table. Proposed DB update: refine `source.clause` to `"Regulation 7(ii)"`. | **YES** | **YES** (clinical formula exceptions under Food Act) |
| `RULE-FLAVOUR-LABEL-DECLARATION` | Gazette 1795/51, Page 2, Regulation 8(2)(d) | Review register cited Reg 8 on Page 3 with 322-char LLM paraphrase. DB quote was verbatim on Page 2, but `clause` string was coarse `"Regulation 8"`. | Page 2 PDF extraction; live PostgreSQL `rules` and `clauses` tables. | Corrected review register entry 10 and summary table. Proposed DB update: refine `source.clause` to `"Regulation 8(2)(d)"`. | **YES** | **YES** (conjunctive class title AND common name AND INS) |
| `RULE-PRESERVATIVE-JAM-JELLY-LIMIT` | Gazette 2113/16, Page 5, Schedule II Item 3.1(h) | Review register cited non-existent Page 13. Scope covers general jams ($300\text{ mg/kg}$) without conditioning out low-sugar jams ($500\text{ mg/kg}$ under Item 3.1(i)). | Page 5 PDF extraction; live PostgreSQL `rules` and `clauses` tables. | Corrected review register entry 5 to Page 5, Item 3.1(h), and added low-sugar proviso notes. Proposed DB update: qualify `applies_if` with `products.is_low_sugar eq False` and compile separate rule for Item 3.1(i). | **YES** | **YES** (statutory Brix / sugar threshold for low-sugar classification) |

---

## 5. Non-Mutating Corrections Implemented

1. **`docs/CANDIDATE_RULE_HUMAN_REVIEW_REGISTER.md`**:
   - **Entry 5 (`RULE-PRESERVATIVE-JAM-JELLY-LIMIT`)**: Updated citation from "Page 13" to Page 5, clarified Schedule II Item 3.1(h), documented the 300 mg/kg vs 500 mg/kg sorbate differential against Item 3.1(i), and added legal review questions regarding Brix thresholds and Propionates GMP logic.
   - **Entry 8 (`RULE-FLAVOUR-INFANT-PROHIBITION`)**: Corrected clause citation to Regulation 7(ii), updated quote span to exact 87-character verbatim text on Page 2, documented statutory context from Regulation 7 stem and Regulation 10 definitions, and reconciled audit history.
   - **Entry 10 (`RULE-FLAVOUR-LABEL-DECLARATION`)**: Corrected clause citation to Regulation 8(2)(d), replaced 322-char paraphrase with exact 248-character verbatim quote span on Page 2, and added legal review questions regarding conjunctive labelling requirements.
   - **Summary Table**: Aligned clause references and page numbers across all candidate entries.
2. **`backend/tests/test_phase_3_8_source_verification.py`**:
   - Implemented 6 deterministic tests asserting:
     - `test_gazette_1795_51_regulation_7_ii_verbatim_text`: Verifies physical PDF text on Page 2 and definitions on Page 3.
     - `test_rule_flavour_infant_prohibition_verifier`: Validates `RULE-FLAVOUR-INFANT-PROHIBITION` in PostgreSQL against `RuleVerifier`.
     - `test_gazette_1795_51_regulation_8_2_d_verbatim_text`: Verifies physical PDF text of Regulation 8(2)(d) on Page 2.
     - `test_rule_flavour_label_declaration_verifier`: Validates `RULE-FLAVOUR-LABEL-DECLARATION` in PostgreSQL against `RuleVerifier`.
     - `test_gazette_2113_16_schedule_ii_jam_items_distinction`: Verifies Page 5 distinction between standard jams (Item 3.1(h)) and low-sugar jams (Item 3.1(i)).
     - `test_rule_preservative_jam_jelly_limit_scope`: Asserts that `RULE-PRESERVATIVE-JAM-JELLY-LIMIT` correctly references Item 3.1(h) limits.

---

## 6. Formal Database Mutation Authorization Request

In compliance with Critical Integrity Constraint 4, **no changes were written to the database**. The following updates are identified as necessary to bring stored database records into strict alignment with authoritative sources:

### Proposed Mutation 1: Refine Clause Sub-reference for Rule 8
- **Table**: `rules`
- **Primary Key**: `rule_id = 'RULE-FLAVOUR-INFANT-PROHIBITION'`
- **Column**: `source` (JSONB)
- **Current Value**: `{"clause": "Regulation 7", "page": 2, ...}`
- **Proposed Value**: `{"clause": "Regulation 7(ii)", "page": 2, ...}`
- **Rationale**: While the quote span is already exact verbatim text of sub-clause (ii), refining `source.clause` eliminates sub-clause ambiguity during UI display and retrieval.

### Proposed Mutation 2: Refine Clause Sub-reference for Rule 10
- **Table**: `rules`
- **Primary Key**: `rule_id = 'RULE-FLAVOUR-LABEL-DECLARATION'`
- **Column**: `source` (JSONB)
- **Current Value**: `{"clause": "Regulation 8", "page": 2, ...}`
- **Proposed Value**: `{"clause": "Regulation 8(2)(d)", "page": 2, ...}`
- **Rationale**: Aligns clause reference directly with the specific operative sub-clause in Gazette 1795/51.

### Proposed Mutation 3: Scope Qualification for Rule 6
- **Table**: `rules`
- **Primary Key**: `rule_id = 'RULE-PRESERVATIVE-JAM-JELLY-LIMIT'`
- **Columns to Update**:
  - `source`: Change `"clause": "Schedule II Item 3.1"` to `"clause": "Schedule II Item 3.1(h)"`
  - `applies_if`: Add condition `{"field": "products.is_low_sugar", "op": "eq", "value": false}`
  - `obligation`: Update description to specify standard jams (`"Permitted preservatives in standard jams, jellies, marmalades: Sorbates maximum 300 mg/kg..."`)
- **Rationale**: Restricts `RULE-PRESERVATIVE-JAM-JELLY-LIMIT` to standard sugar jams as intended by Item 3.1(h), preventing false violations on low-sugar products.

### Proposed Mutation 4 (Optional Expansion): Add Candidate Rule for Item 3.1(i)
- **Table**: `rules`
- **Action**: Insert candidate rule `RULE-PRESERVATIVE-LOW-SUGAR-JAM-LIMIT`
- **Attributes**:
  - `clause_id`: `CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-SCHEDULE-II-FRUIT`
  - `review_status`: `PENDING_REVIEW`
  - `is_gold_rule`: `False`
  - `applies_if`: `products.category eq "jams_jellies_marmalades"` AND `products.is_low_sugar eq True`
  - `obligation`: Sorbates maximum $500\text{ mg/kg}$, Sulphites maximum $100\text{ mg/kg}$, Propionates GMP.
  - `source`: Gazette 2113/16, Page 5, Schedule II Item 3.1(i).
- **Rationale**: Implements full coverage of Schedule II Fruit products without architectural restructuring.

*Authorization from the project owner is requested prior to executing these operations.*

---

## 7. Verification Test Execution

The focused test suite and full multi-phase regression suites were executed using the active environment (`.venv`, Python 3.14.5).

### Focused Test Command
```bash
.venv\Scripts\python.exe -m pytest backend/tests/test_phase_3_8_source_verification.py -v
```
**Result**: `6 passed, 1 warning in 4.02s` (100% pass rate).

### Comprehensive Multi-Phase Regression Command
```bash
.venv\Scripts\python.exe -m pytest backend/tests/test_integrity_gate.py \
    backend/tests/test_phase_3_3_segmentation.py \
    backend/tests/test_phase_3_4_benchmark.py \
    backend/tests/test_phase_3_5_review_readiness.py \
    backend/tests/test_phase_3_8_source_verification.py -v
```
**Result**: `52 passed, 1 warning in 40.35s` (100% pass rate).

---

## 8. Resolution Status of Phase 3.6 Anomaly Claims

1. **Issue A (`RULE-FLAVOUR-INFANT-PROHIBITION`)**:
   - **Status**: **RESOLVED** in documentation and verified in database.
   - Source is Gazette 1795/51, Page 2, Regulation 7(ii). Database record already matches verbatim text. Review register amended.
   - Pending database field update (`source.clause = "Regulation 7(ii)"`) queued for authorization.
2. **Issue B (`RULE-FLAVOUR-LABEL-DECLARATION`)**:
   - **Status**: **RESOLVED** in documentation and verified in database.
   - Source is Gazette 1795/51, Page 2, Regulation 8(2)(d). Database record already matches verbatim text. Review register amended.
   - Pending database field update (`source.clause = "Regulation 8(2)(d)"`) queued for authorization.
3. **Issue C (`RULE-PRESERVATIVE-JAM-JELLY-LIMIT`)**:
   - **Status**: **RESOLVED** in documentation; architectural scope defined.
   - Source verified on Page 5 as Schedule II Item 3.1(h). Distinction from Item 3.1(i) established. Review register updated with low-sugar proviso notes.
   - Targeted solution formulated: separate rule for Item 3.1(i) and condition on Item 3.1(h), queued for authorization.

---

## 9. Conclusion and Next Steps

Phase 3.8 has successfully audited, grounded, and verified the three contested candidate rules against physical government gazettes. The audit established that the underlying system was more accurate than previously reported in Phase 3.6, with discrepancies largely confined to review register documentation.

With Phase 3.8 concluded:
1. **Submit Database Authorization Request**: Await project owner approval for the four targeted database operations detailed in Section 6.
2. **Primary Human Review Sign-Off**: Once authorized, perform primary review of the 10 candidate rules via `/admin/reviews` using the corrected review register.
3. **Phase 3.9 (OCR Execution)**: Proceed to Tesseract OCR on Gazette 1688/28 (Colouring 2011) to segment remaining candidate clauses under locked Option A.

# RegImpact-SL — Post-Repair Verification Gate Report

**Milestone:** Post-Repair Verification Gate for Authoritative Gazette Slice  
**Document Identifier:** `REP-POST-REPAIR-GATE-2026-10-24`  
**Date:** 2026-10-24  
**Status:** Completed  
**Prior Reference:** `RegImpact-SL_Authoritative_Slice_Repair_Report.md` (`REP-AUTHORITATIVE-SLICE-2026-10-23`)  
**Operating Framework:** Proposal v4 — Development Freeze & Verification Gate  
**Auditor:** Independent Technical Verification Agent (Antigravity Senior RSE)  

---

## Executive Summary

This independent post-repair verification audit investigated the repaired authoritative Gazette vertical slice (`doc_gazette_2494_47`, `RULE-FCAU-2494-47-REG-3`, and `RULE-FCAU-2494-47-REG-3-B2B`) and evaluated whether the prototype is technically and empirically sound to begin migrating benchmark scenarios from synthetic fixtures to real regulatory sources.

The audit reproduced all test claims from `RegImpact-SL_Authoritative_Slice_Repair_Report.md` (14 focused tests in 0.84s, 109 backend regression tests in 83.88s, and the Next.js production build in 9.5s). However, in-depth architectural tracing uncovered **three critical technical defects and one severe test-independence vulnerability**:

1. **Silent Repository Dropping of Disclosures ([repositories.py:191-195](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/db/repositories.py#L191-L195)):** While `Obligation` in [domain.py](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/models/domain.py#L88) was extended with `disclosures: Optional[List[str]] = None`, both `rule_orm_to_domain()` and `rule_domain_to_orm_dict()` in [repositories.py](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/db/repositories.py#L191-L195) omit `disclosures`. Any rule retrieved from the database ORM silently loses all 11 statutory B2B disclosures (`obligation.disclosures` becomes `None`).
2. **Contradictory Operational Action Items ([impact_mapper.py:44](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/engine/impact_mapper.py#L44)):** `impact_mapper.py` ignores `obligation.disclosures` and applies generic labelling templates to B2B food products, instructing manufacturers to *"Ensure packaging displays required trilingual text (Sinhala, Tamil, English)"*, which directly contradicts Regulation 3 Proviso (b)(i) (*"common name (in either of the three languages)"*).
3. **Severe Test Independence & False Coverage Gap ([test_real_source_slice.py:441-501](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/tests/test_real_source_slice.py#L441-L501)):** Focused tests define rules in an isolated in-memory Python fixture (`gazette_rules`) rather than querying the database. If `RULE-FCAU-2494-47-REG-3-B2B` or `seed_real_slice.py` is removed, the focused test suite still passes 100%. No test in the repository exercises the real-source rules through `POST /analysis` or verifies `seed_real_slice()`.
4. **Primary Official URL Inaccessibility:** The recorded government URL (`http://www.documents.gov.lk/files/egz/2026/6/2494-47_E.pdf`) returns `HTTP Error 404: Not Found` because the government host is serving an unconfigured Nginx Proxy Manager default page. Byte-for-byte authentication was only possible via the official Ministry of Health mirror (`https://eohfs.health.gov.lk/food/images/2494-47_E.pdf`).

**Gate Verdict:** **BLOCK BENCHMARK MIGRATION**. Benchmark migration cannot proceed until the repository serialization defect is fixed, the B2B action mapper is aligned with statutory text, and end-to-end API tests are added.

---

## 1. Source Authentication Result (Check 1)

### 1.1 Source Location & Network Verification

| Dimension | Repair Report Claim | Actual Verified State | Audit Finding |
| :--- | :--- | :--- | :--- |
| **Recorded URL** | `http://www.documents.gov.lk/files/egz/2026/6/2494-47_E.pdf` | `http://www.documents.gov.lk/files/egz/2026/6/2494-47_E.pdf` | Recorded URL matches report. |
| **Primary URL Status** | Implied reachable | **HTTP 404: Not Found** | `www.documents.gov.lk` is serving an unconfigured Nginx Proxy Manager default landing page; deep file path is unreachable. |
| **HTTPS Primary URL** | Unstated | `[SSL: UNEXPECTED_EOF_WHILE_READING]` | SSL handshake terminates abruptly on `www.documents.gov.lk:443`. |
| **Official Mirror URL** | Not recorded in report | `https://eohfs.health.gov.lk/food/images/2494-47_E.pdf` | Verified active mirror hosted by the Directorate of Environmental Health, Occupational Health & Food Safety (Ministry of Health). Returns **HTTP 200**. |
| **Mirror Byte Count** | N/A | **424,172 bytes** | Exactly matches local file. |
| **Mirror SHA-256** | N/A | `83ed19c22873471652d0073fe16c977442e42c8ecac2edf1d691d00d78d8a054` | Exactly matches local file byte-for-byte. |

### 1.2 Local File Integrity & Statutory Metadata

- **Local Path:** `backend/data/raw_sources/2494-47_E.pdf`
- **File Size:** `424,172 bytes` (reproduced via Python `os.path.getsize`)
- **SHA-256 Checksum:** `83ed19c22873471652d0073fe16c977442e42c8ecac2edf1d691d00d78d8a054` (reproduced via PowerShell `Get-FileHash` and Python `hashlib.sha256`)
- **Page Count:** 25 pages (PyMuPDF verified)
- **Official Instrument Title:** Food (Labelling and Advertising) Regulations 2026
- **Gazette Identification:** Gazette Extraordinary No. 2494/47
- **Enacting Authority:** Dr. Nalinda Jayatissa, Minister of Health and Mass Media, in consultation with the Food Advisory Committee under Section 32 of the Food Act, No. 26 of 1980
- **Promulgation Date:** Friday, 26th June 2026 (`2026-06-26`)
- **Commencement Date:** Wednesday, 01st July 2026 (`2026-07-01`) per Regulation 1:
  > *"These regulations may be cited as Food (Labelling and Advertising) Regulations 2026 and shall come into operation on 01st July 2026."*
- **Regulation Numbering Hierarchy:**
  - **Regulation 1 (Page 1):** Citation & Commencement (`2026-07-01`).
  - **Regulation 2 (Page 1):** Transitional exemption for food products manufactured prior to commencement.
  - **Regulation 3 (Pages 1–2):** General labelling prohibition, purchaser-presence exemption (Proviso (a)), and B2B mandatory disclosures & $\ge 3\text{ mm}$ marking (Proviso (b)).
  - **Regulation 4+ (Pages 2–25):** Specific labelling rules, nutrition declarations, and font tables.

> [!WARNING]
> Direct comparison against `documents.gov.lk` is marked **UNRESOLVED** due to remote server misconfiguration. However, byte-for-byte authentication was successfully achieved against the enacting Ministry's official domain (`eohfs.health.gov.lk`).

---

## 2. Retail and B2B Rule Interaction (Check 2)

### 2.1 Trace of Execution Across 7 Conceptual Cases

The actual execution path was traced through [applicability.py](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/engine/applicability.py), [impact_mapper.py](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/engine/impact_mapper.py), and [main.py](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/main.py):

| Case # | Conceptual Profile Description | Input Profile Fields | Executing Rules | Retail Rule Outcome | B2B Rule Outcome | Final Aggregate Outcome | Actions Shown to User | Evaluation Analysis & Integrity Checks |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **1** | Retail packaged food; all facts known | `prepackaged=True`, `b2b_only=False`, `activity="food_manufacturing"` | Both | `APPLICABLE` | `NOT_APPLICABLE` | 1 APPLICABLE, 1 NOT_APPLICABLE | 6 Retail labelling action items (FCAU audit, font size, trilingual declarations). | Clean separation. Retail obligation triggers; B2B short-circuits on `market.b2b_only`. No duplicated obligations. |
| **2** | B2B product satisfying all B2B obligations | `prepackaged=True`, `b2b_only=True`, `all 10 disclosures present`, `marking=True (>=3mm)` | Both | `NOT_APPLICABLE` | `APPLICABLE` | 1 APPLICABLE, 1 NOT_APPLICABLE | 6 Action items including generic labelling templates + direct obligation text. | Retail rule triggers exception (`market.b2b_only == True`). B2B rule evaluates `APPLICABLE`. |
| **3** | B2B product missing one mandatory disclosure | `prepackaged=True`, `b2b_only=True`, `batch_number=None` | Both | `NOT_APPLICABLE` | `APPLICABLE` | 1 APPLICABLE, 1 NOT_APPLICABLE | Identical to Case 2. | **Engine Limitation:** The applicability engine only evaluates whether the rule *applies* to the entity, not whether the entity *complies* with the obligation. Cases 2 and 3 produce identical outcomes. |
| **4** | B2B product missing applicability data | `prepackaged=True`, `market=None` (channel unknown) | Both | `CONDITIONAL_MISSING_DATA` | `CONDITIONAL_MISSING_DATA` | 2 CONDITIONAL_MISSING_DATA, 0 APPLICABLE | 0 action items; generates clarifying question for `market.b2b_only`. | Missing information is correctly distinguished from non-compliance. Kleene 3-valued logic halts evaluation. |
| **5** | Product under B2B exception violating 3 mm marking | `prepackaged=True`, `b2b_only=True`, `marking=False` or `< 3mm` | Both | `NOT_APPLICABLE` | `APPLICABLE` | 1 APPLICABLE, 1 NOT_APPLICABLE | Identical to Case 2. | **Statutory Gap:** Retail rule exception only checks `market.b2b_only == True`. It does not verify marking compliance. If marking violation forfeits B2B status in law, the engine fails to re-route to Retail. |
| **6** | Product outside scope of both rules | `activity="farming"`, `prepackaged=False` | Both | `NOT_APPLICABLE` | `NOT_APPLICABLE` | 0 APPLICABLE, 2 NOT_APPLICABLE | 0 action items; 0 impacts. | Clean rejection on negative preconditions (`prepackaged=False`, activity mismatch). |
| **7** | Rules produce differing outcomes | Same as Case 1 or Case 2 | Both | Divergent | Divergent | Partitioned | As Case 1 or 2. | Both rules execute deterministically without collision or mutual deadlock. |

### 2.2 Duplication, Dropped Obligations, and Contradictory Actions

1. **Dropped Disclosures in Repository Layer ([repositories.py:191-195](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/db/repositories.py#L191-L195)):**
   When `repo.get_rules_by_ids()` loads `RULE-FCAU-2494-47-REG-3-B2B` from the database, `rule_orm_to_domain()` reconstructs the `Obligation` as:
   ```python
   obligation = Obligation(
       type=obl_dict.get("type", ""),
       text=obl_dict.get("text", ""),
       impact_categories=obl_dict.get("impact_categories", []),
   )
   ```
   Because `disclosures=obl_dict.get("disclosures")` is omitted, **the 11 B2B disclosures are erased during ORM-to-domain deserialization**.
2. **Contradictory Language Action Item ([impact_mapper.py:44](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/engine/impact_mapper.py#L44)):**
   `impact_mapper.py` parameterizes actions using a hardcoded `labelling` vocabulary. For `RULE-FCAU-2494-47-REG-3-B2B`, it presents:
   > *"Ensure packaging displays required trilingual text (Sinhala, Tamil, English) adhering to prescribed font dimensions."*  
   
   This directly contradicts Gazette Regulation 3 Proviso (b)(i), which mandates common name *"in either of the three languages"*, not all three.
3. **Applicability vs. Downstream Operational Compliance:**
   The engine successfully distinguishes unknown facts (`CONDITIONAL_MISSING_DATA`) from determined outcomes. However, it cannot verify whether a label actually satisfies the 10 disclosures or the 3 mm font requirement.

---

## 3. B2B Obligation Integrity (Check 3)

### 3.1 Gazette Regulation 3 Proviso (b) vs. System Implementation

| Statutory Element in Gazette 2494/47 | Gazette Wording & Locator | Implementation Schema in `seed_real_slice.py` | Implementation Schema in Repair Report §5 | Integrity Assessment |
| :--- | :--- | :--- | :--- | :--- |
| **(i) Common Name** | `common name (in either of the three languages)` (p. 2) | `"common_name"` | `"common_name_in_either_of_three_languages"` | **Divergence:** Actual code drops statutory language qualification `in_either_of_three_languages`. |
| **(ii) Trade Name** | `trade name (if applicable)` (p. 2) | `"trade_name"` | `"trade_name_if_applicable"` | **Divergence:** Actual code drops `if_applicable`. |
| **(iii) Net Contents** | `net contents` (p. 2) | `"net_contents"` | `"net_contents"` | **Match** |
| **(iv) Date of Manufacture** | `date of manufacture` (p. 2) | `"date_of_manufacture"` | `"date_of_manufacture"` | **Match** |
| **(v) Date of Expiry** | `date of expiry` (p. 2) | `"date_of_expiry"` | `"date_of_expiry"` | **Match** |
| **(vi) Batch Number** | `batch number` (p. 2) | `"batch_number"` | `"batch_number"` | **Match** |
| **(vii) Manufacturer Details**| `manufacturer's name and address` (p. 2) | `"manufacturer_details"` | `"manufacturer_name_and_address"` | **Divergence:** Actual code weakens statutory `"name and address"` to `"details"`. |
| **(viii) Distributor Details** | `distributor's name and address` (p. 2) | `"distributor_details"` | `"distributor_name_and_address"` | **Divergence:** Actual code weakens statutory `"name and address"` to `"details"`. |
| **(ix) Country of Origin** | `country of origin in case of imported foods` (p. 2) | `"country_of_origin"` | `"country_of_origin_if_imported"` | **Divergence:** Actual code drops conditional qualification `if_imported`. |
| **(x) Ingredients List** | `a complete list of ingredients` (p. 2) | `"ingredients_list"` | `"complete_list_of_ingredients"` | **Divergence:** Actual code drops statutory requirement `complete`. |
| **Marking Statement** | `statement "Not for retail sale"` (p. 2) | `"not_for_retail_sale_statement"`| `"statement_not_for_retail_sale_conspicuous_bold_gte_3mm"` | **Divergence:** Code uses simplified token. Marking is grounded in quote span. |
| **Marking Font $\ge 3\text{ mm}$**| `clearly and conspicuously in bold type and font size of not less than three millimetres (3 mm)` (p. 2) | Captured in `obligation.text` and `source.quote_span` | Captured in `obligation.text` and `source.quote_span` | **Match** Grounded verbatim in Page 2 text stream. |

### 3.2 Traceable Evidence & Grounding

- The quote spans for both rules match the PyMuPDF text extraction from `2494-47_E.pdf`:
  - Retail quote span starts at Page 1 offset 826 (`"3.\nA person shall not import..."`).
  - B2B quote span is located on Page 2 offsets 199 to 1226.
- PUA font ligatures (`\ue055` $\to$ `ff`, `\ue056` $\to$ `ffi`) are correctly converted to standard ASCII in [verifier.py:84](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/engine/verifier.py#L84), allowing literal quote matching.

---

## 4. Evidence and Test Independence (Check 4)

### 4.1 Audit of `backend/tests/test_real_source_slice.py`

| Test Name | PDF / DB Checked? | Real Execution Path? | Survives Deletion of DB Rule? | Test Independence Finding |
| :--- | :---: | :---: | :---: | :--- |
| `test_promulgated_gazette_provenance_and_hash` | Reads raw PDF | No (filesystem only) | Yes | **PASS**: Genuinely validates PDF hash, byte count, page count, and masthead strings against local file. |
| `test_distinction_between_promulgated_gazette_and_draft` | Reads raw PDFs | No (filesystem only) | Yes | **PASS**: Genuinely proves hash, page count, and regulation numbering differences between draft and gazette. |
| `test_gazette_clause_grounding_and_ligature_normalization` | Reads raw PDF | Isolated `RuleVerifier` | Yes | **PASS**: Validates PUA ligatures and quote spans directly against Gazette page text. |
| `test_typed_rules_preserve_statutory_structure` | Neither | In-memory Pydantic only | Yes | **FAIL (Tautological)**: Manually constructs `Rule(...)` in memory and asserts that the fields just passed into the constructor exist. Does not test parser, compiler, or DB. |
| `test_provenance_lifecycle_distinction_with_db` | Uses SQLite DB | ReviewService isolated | Yes | **PARTIAL**: Tests review state machine on a local mock candidate rule; does not test `seed_real_slice()`. |
| `test_deterministic_evaluation_retail_case` | Neither | Isolated `evaluate_rule` | **YES (False Confidence)** | **FAIL (Isolated)**: Uses in-memory fixture `gazette_rules`. Does not test DB loading or API response. |
| `test_deterministic_evaluation_purchaser_presence_exception` | Neither | Isolated `evaluate_rule` | **YES (False Confidence)** | **FAIL (Isolated)**: Bypasses DB and API. |
| `test_deterministic_evaluation_b2b_affirmative_case` | Neither | Isolated `evaluate_rule` | **YES (False Confidence)** | **FAIL (Isolated)**: Bypasses DB and API. |
| `test_deterministic_evaluation_missing_data_prepackaged` | Neither | Isolated `evaluate_rule` | **YES (False Confidence)** | **FAIL (Isolated)**: Bypasses DB and API. |
| `test_deterministic_evaluation_missing_data_market_channel` | Neither | Isolated `evaluate_rule` | **YES (False Confidence)** | **FAIL (Isolated)**: Bypasses DB and API. |
| `test_deterministic_evaluation_temporal_prior_to_commencement` | Neither | Isolated `evaluate_rule` | **YES (False Confidence)** | **FAIL (Isolated)**: Bypasses DB and API. |
| `test_deterministic_evaluation_conditional_rule` | Neither | Isolated `evaluate_rule` | Yes | **PASS**: Verifies `CONDITIONAL_RULE` propagation. |
| `test_deterministic_evaluation_unsupported_clause` | Neither | Isolated `evaluate_rule` | Yes | **PASS**: Verifies `UNSUPPORTED` status propagation. |
| `test_version_preservation_on_amendment` | Uses SQLite DB | ReviewService isolated | Yes | **PASS**: Genuinely checks JSON audit snapshot on amendment. |

### 4.2 Key Independence Defects

1. **In-Memory Fixture Insulation ([test_real_source_slice.py:441-501](file:///c:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/tests/test_real_source_slice.py#L441-L501)):**
   The deterministic evaluation tests (Tests 6–11) rely on the `gazette_rules` fixture, which instantiates `Rule` objects directly in Python memory. If `RULE-FCAU-2494-47-REG-3-B2B` is dropped or corrupted in the database or in `seed_real_slice.py`, **all 14 tests still pass**.
2. **Zero End-to-End API Coverage:**
   Not a single test exercises the real-source rules through FastAPI's `POST /analysis`. Consequently, the API's rule selection, retrieval, aggregation, and response serialization were never verified for Gazette No. 2494/47.
3. **Seeding Script Never Tested:**
   `backend/data/seed_real_slice.py` is not imported or executed by any test in `backend/tests/`.

---

## 5. Remaining Defects and Unresolved Legal Questions

### 5.1 Technical Defects to be Remediated

1. **`repositories.py:191-195` Deserialization Defect:**
   `rule_orm_to_domain` must map `disclosures=obl_dict.get("disclosures")`.
2. **`repositories.py:244-248` Serialization Defect:**
   `rule_domain_to_orm_dict` must include `"disclosures": rule.obligation.disclosures`.
3. **`impact_mapper.py:44` B2B Contradiction:**
   The mapper must not output generic retail trilingual labelling requirements when evaluating B2B products under Regulation 3 Proviso (b).
4. **Disclosures Lost in Impact Mapping:**
   `map_impact()` does not expose `obligation.disclosures` in `action_items` or `affected_documents`.

### 5.2 Unresolved Statutory & Legal Interpretations

1. **Definition of "Business-to-Business Food Products":**
   Regulation 3 does not define the threshold for B2B classification (e.g., whether bulk sales to restaurants, hotel caterers, or commercial bakeries qualify as B2B or consumer supply).
2. **Trilingual vs. Single-Language Scope:**
   Regulation 3 Proviso (b)(i) allows the common name to be in *"either of the three languages"*, but the Gazette is silent on whether the other 9 disclosures (e.g., ingredients list, manufacturer details) may also be single-language or must follow general trilingual rules.
3. **Condition Precedent vs. Separate Obligation for 3 mm Marking:**
   If a B2B product omits the statement *"Not for retail sale"* or prints it below 3 mm, statutory interpretation is divided on whether this constitutes a standalone B2B marking infraction or entirely forfeits the B2B exemption, exposing the manufacturer to prosecution under the general retail labelling prohibition.
4. **Regulation 2 Evidentiary Standards:**
   The Gazette does not specify the documentary evidence required to prove pre-commencement manufacture (prior to July 1, 2026) during regulatory audits.

---

## 6. Reproducibility Evidence (Check 5)

### 6.1 Repository State
- **Git Commit:** `b784334` (`feat: add authoritative slice repair report for Sri Lanka Gazette No. 2494/47`)
- **Git Branch:** `main`
- **Working Tree:** Clean (verified via `git status`, 0 uncommitted changes)

### 6.2 Executed Test Commands & Exact Outputs

#### 1. Focused Real-Source Test Suite
```powershell
$env:PYTHONPATH="."; py -m pytest backend/tests/test_real_source_slice.py -v
```
- **Exit Code:** `0`
- **Result:** `14 passed in 0.84s`
- **Warnings / Skips:** 0 warnings, 0 skips.

#### 2. Full Backend Regression Suite
```powershell
$env:PYTHONPATH="."; py -m pytest backend/tests/test_applicability.py backend/tests/test_versioning.py backend/tests/test_agreement_review.py backend/tests/test_verifier.py backend/tests/test_ingestion.py backend/tests/test_api.py
```
- **Exit Code:** `0`
- **Result:** `109 passed, 1 warning in 83.88s`
- **Warning Details:** `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.`

#### 3. Frontend Production Build
```bash
npm run build (in frontend/)
```
- **Exit Code:** `0`
- **Result:** Compiled in 1.13s; TypeScript finished in 5.6s; static pages generated (6/6) in 2.4s. Zero lint or type errors across routes `/`, `/_not-found`, `/admin/reviews`, `/evaluation`.

### 6.3 Environmental Limitations
- **OS Platform:** Windows host (Python 3.14.5).
- **Database:** SQLite in-memory default used; no PostgreSQL container daemon was active.
- **Docker:** Docker Desktop daemon was not running; no containerized verification claimed.

---

## 7. Decision for Each Check

| Check Number & Title | Verdict | Primary Justification |
| :--- | :---: | :--- |
| **Check 1 — Authoritative Source Identity** | **PARTIAL** | Byte count and SHA-256 match official Ministry of Health mirror (`eohfs.health.gov.lk`) identically; however, primary government URL (`documents.gov.lk`) is currently unreachable (HTTP 404 / Nginx misconfiguration). |
| **Check 2 — Retail and B2B Rule Interaction** | **PARTIAL** | Kleene logic and applicability outcomes execute deterministically across all 7 cases; however, `repositories.py` drops `disclosures`, and `impact_mapper.py` outputs contradictory trilingual instructions for B2B. |
| **Check 3 — B2B Obligation Integrity** | **PARTIAL** | Grounded in Gazette Regulation 3 Proviso (b) with 10 disclosures and 3 mm marking; however, schema representation simplifies statutory qualifications, and repository deserialization drops the disclosure list. |
| **Check 4 — Evidence and Test Independence** | **FAIL** | Tests rely on hardcoded in-memory fixtures (`gazette_rules`) rather than the database; tests bypass `POST /analysis` entirely; tests pass even if database seeding is broken. |
| **Check 5 — State and Reproducibility** | **PASS** | Clean Git working tree (`b784334`), exact reproduction of 14 focused tests (0.84s), 109 regression tests (83.88s), and frontend build (9.5s) with honest environmental boundaries. |

---

## 8. Final Decision

### **BLOCK BENCHMARK MIGRATION**

**Rationale:**  
While the authoritative Gazette source file (`2494-47_E.pdf`) is authentic and its statutory logic is correctly modeled conceptually, benchmark migration cannot proceed until the following technical and verification defects are resolved:

1. **Fix Repository ORM Serialization:** Update `rule_orm_to_domain()` and `rule_domain_to_orm_dict()` in `backend/src/db/repositories.py` so that `obligation.disclosures` is preserved through database persistence.
2. **Align B2B Impact Mapping:** Update `backend/src/engine/impact_mapper.py` to prevent emitting generic trilingual labelling actions for B2B products and to expose the specific mandatory disclosure items.
3. **Implement True End-to-End API Tests:** Add tests to `backend/tests/test_real_source_slice.py` that execute `seed_real_slice()`, query the seeded rules through `PostgresRegulatoryRepository`, and call `POST /analysis` to verify the final aggregated `StructuredImpactReport`.

Once these bounded technical repairs are implemented and verified against the API, benchmark scenario migration can safely be unlocked.

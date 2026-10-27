# RegImpact-SL — Comprehensive Clause-Level Eligibility and Expansion Register

**Governing Specification:** `RegImpact-SL_Project_Proposal_v4_FINAL.md`  
**Scope Decision:** `docs/PROJECT_OWNER_SCOPE_DECISION_RECORD.md` (Option A: Focused Food Control Scope)  
**Phase:** 4.1 Verification Audit  
**Date:** 2026-10-27  

## 1. Summary of Authentic Corpus Eligibility

| Category | Count | Status / Definition |
| :--- | :--- | :--- |
| **1. Stored Authentic Clauses** | **59** | Total clauses in PostgreSQL `clauses` table where `is_synthetic=False`. 100% vector embedded with local BGE v1.5. |
| **2. Source-Verified Clauses** | **59** | Authenticated against physical source PDFs on disk, verifying SHA256 hashes and statutory text match. |
| **3. Ineligible Stubs & Out-of-Scope** | **15** | Excluded: 6 Section 32 preambles, 3 Reg 1 short titles, 5 transition/repeal stubs, 1 corporate fee order. |
| **4. Eligible Operative Clauses** | **44** | Substantive regulatory obligations, prohibitions, limits, conditions, or exceptions under Food Act No. 26 of 1980. |
| **5. Clauses with Compiled Rules** | **8** | Distinct statutory clauses referenced by the 12 authentic rules in PostgreSQL `rules` table. |
| **6. Technically Verified Rule Clauses** | **8** | Passed deterministic schema verification and exact verbatim quote-span grounding. |
| **7. Genuine Human-Reviewed Clauses** | **1** | Only `CLAUSE-DOC_GAZETTE_2494_47-REGULATION-3` has `APPROVED` rules; 7 clauses remain `PENDING_REVIEW`. |
| **8. Uncompiled Eligible Candidate Clauses** | **36** | Operative, substantive Food Control clauses ready for deterministic rule compilation. |
| **9. Gazette 1688/28 OCR Candidates (Derived)** | **3** | Reg 5(iv) seafood prohibition, Schedule I Table I (synthetics), Schedule I Table II (naturals). |
| **Total Distinct Eligible Clause Capacity** | **47** | Far exceeds proposal target of $\ge 25$ distinct eligible clauses. |

---

## 2. Clause-by-Clause Register

| Clause ID | Instrument / Gazette | Clause No. | Location | Scope | Operative? | Has Rule? | Verified? | Human Rev.? | Benchmark Ready? | Exclusion Reason / Audit Notes |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `CLAUSE-DOC_15803FE0B14AABE0C79126EBE7C8834D8063B6ED8C2A9033C1201FF538BCD95B-REGULATION-3-1` | 2494/06 | Regulation 3(1) | pp. 1-2 | YES | YES | YES (1) | YES | PENDING | YES | Compiled: RULE-SUGAR-2494-06-GLASS-PROVISO |
| `CLAUSE-DOC_15803FE0B14AABE0C79126EBE7C8834D8063B6ED8C2A9033C1201FF538BCD95B-REGULATION-3-3` | 2494/06 | Regulation 3(3) | pp. 2-2 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_15803FE0B14AABE0C79126EBE7C8834D8063B6ED8C2A9033C1201FF538BCD95B-REGULATION-6-GA` | 2494/06 | Regulation 6(ga) | pp. 2-2 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_15803FE0B14AABE0C79126EBE7C8834D8063B6ED8C2A9033C1201FF538BCD95B-SCHEDULE` | 2494/06 | Schedule (Regulation 3) | pp. 2-3 | YES | YES | YES (3) | YES | PENDING | YES | Compiled: RULE-SUGAR-2494-06-RED, RULE-SUGAR-2494-06-AMBER, RULE-SUGAR-2494-06-GREEN |
| `CLAUSE-DOC_15803FE0B14AABE0C79126EBE7C8834D8063B6ED8C2A9033C1201FF538BCD95B-REGULATION-3` | 2494/06 | regulation 3 | pp. 1-1 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_15803FE0B14AABE0C79126EBE7C8834D8063B6ED8C2A9033C1201FF538BCD95B-REGULATION-5` | 2494/06 | regulation 5 | pp. 2-2 | YES | NO (Stub) | NO | N/A | Uncompiled | NO | Pure date-substitution fragment (2024 -> 2026). |
| `CLAUSE-DOC_15803FE0B14AABE0C79126EBE7C8834D8063B6ED8C2A9033C1201FF538BCD95B-REGULATION-6` | 2494/06 | regulation 6 | pp. 2-2 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_15803FE0B14AABE0C79126EBE7C8834D8063B6ED8C2A9033C1201FF538BCD95B-REGULATION-8` | 2494/06 | regulation 8 | pp. 2-2 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_15803FE0B14AABE0C79126EBE7C8834D8063B6ED8C2A9033C1201FF538BCD95B-SECTION-32` | 2494/06 | section 32 | pp. 1-1 | YES | NO (Stub) | NO | N/A | Uncompiled | NO | Inoperative statutory preamble / minister empowering formula under Section 32. |
| `CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-REGULATION-1` | 2113/16 | Regulation 1 | pp. 1-1 | YES | NO (Stub) | NO | N/A | Uncompiled | NO | Non-substantive short title / citation preamble. |
| `CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-REGULATION-2` | 2113/16 | Regulation 2 | pp. 1-2 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-REGULATION-2005` | 2113/16 | Regulation 2005 | pp. 2-2 | YES | NO (Stub) | NO | N/A | Uncompiled | NO | Cross-reference citation to 2005 labelling regulations. |
| `CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-REGULATION-3` | 2113/16 | Regulation 3 | pp. 2-2 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-REGULATION-4` | 2113/16 | Regulation 4 | pp. 2-2 | YES | YES | YES (1) | YES | PENDING | YES | Compiled: RULE-PRESERVATIVE-MIXTURE-LIMIT |
| `CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-REGULATION-5` | 2113/16 | Regulation 5 | pp. 2-2 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-REGULATION-8` | 2113/16 | Regulation 8 | pp. 2-2 | YES | YES | YES (1) | YES | PENDING | YES | Compiled: RULE-PRESERVATIVE-LABEL-DECLARATION |
| `CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-SCHEDULE-I` | 2113/16 | Schedule I | pp. 3-3 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-SCHEDULE-II-FRUIT` | 2113/16 | Schedule II Item 3.1 | pp. 5-5 | YES | YES | YES (1) | YES | PENDING | YES | Compiled: RULE-PRESERVATIVE-JAM-JELLY-LIMIT |
| `CLAUSE-DOC_3F85F3EF96B7622BDD3E45D7CC642FD96FDBD83A9F84F35F048121EAB3E4016F-SECTION-32` | 2113/16 | Section 32 | pp. 1-1 | YES | NO (Stub) | NO | N/A | Uncompiled | NO | Inoperative statutory preamble / minister empowering formula under Section 32. |
| `CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-REGULATION--4` | 1795/51 | Regulation  4 | pp. 5-5 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-REGULATION--7` | 1795/51 | Regulation  7 | pp. 5-5 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-REGULATION-1` | 1795/51 | Regulation 1 | pp. 1-1 | YES | NO (Stub) | NO | N/A | Uncompiled | NO | Non-substantive short title / citation preamble. |
| `CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-REGULATION-3` | 1795/51 | Regulation 3 | pp. 4-4 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-REGULATION-6` | 1795/51 | Regulation 6 | pp. 2-2 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-REGULATION-7` | 1795/51 | Regulation 7 | pp. 2-2 | YES | YES | YES (2) | YES | PENDING | YES | Compiled: RULE-FLAVOUR-INFANT-PROHIBITION, RULE-FLAVOUR-SCHEDULE-III-PROHIBITION |
| `CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-REGULATION-8` | 1795/51 | Regulation 8 | pp. 2-2 | YES | YES | YES (1) | YES | PENDING | YES | Compiled: RULE-FLAVOUR-LABEL-DECLARATION |
| `CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-SCHEDULE-I` | 1795/51 | Schedule I | pp. 4-4 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-SCHEDULE-II` | 1795/51 | Schedule II | pp. 5-5 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-SCHEDULE-III` | 1795/51 | Schedule III | pp. 5-5 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-SECTION-32` | 1795/51 | Section 32 | pp. 1-1 | YES | NO (Stub) | NO | N/A | Uncompiled | NO | Inoperative statutory preamble / minister empowering formula under Section 32. |
| `CLAUSE-DOC_B78479B6B08D12E11FD27CFC39677D5A284BC147BF16A777EAFB495B86F4135A-REGULATION-9` | 1795/51 | regulation 9 | pp. 1-1 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_FCAU_LABELLING_ADVERTISING_EN-REGULATION-15` | Food (Labelling and Adver | Regulation 15 | pp. 1-1 | YES | NO (Stub) | NO | N/A | Uncompiled | NO | Commencement date clause for historical 2005 regulations. |
| `CLAUSE-DOC_FCAU_LABELLING_ADVERTISING_EN-SECTION-32` | Food (Labelling and Adver | Section 32 | pp. 1-1 | YES | NO (Stub) | NO | N/A | Uncompiled | NO | Inoperative statutory preamble / minister empowering formula under Section 32. |
| `CLAUSE-DOC_FCAU_LABELLING_ADVERTISING_EN-REGULATION-1` | Food (Labelling and Adver | regulation 1 | pp. 1-1 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_GAZETTE_2443_27-SECTION-32` | The Sri Lanka Gazette Ext | Section 32 | pp. 1-1 | YES | NO (Stub) | NO | N/A | Uncompiled | NO | Inoperative statutory preamble / minister empowering formula under Section 32. |
| `CLAUSE-DOC_GAZETTE_2443_27-ITEM-1.1` | The Sri Lanka Gazette Ext | item 1.1 | pp. 4-4 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_GAZETTE_2443_27-ITEM-1.1.3` | The Sri Lanka Gazette Ext | item 1.1.3 | pp. 4-4 | YES | NO (Stub) | NO | N/A | Uncompiled | NO | Drafting instruction fragment (single insertion line). |
| `CLAUSE-DOC_GAZETTE_2443_27-ITEM-1.2` | The Sri Lanka Gazette Ext | item 1.2 | pp. 5-5 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_GAZETTE_2443_27-ITEM-2.3.2` | The Sri Lanka Gazette Ext | item 2.3.2 | pp. 5-5 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_GAZETTE_2443_27-ITEM-4.4` | The Sri Lanka Gazette Ext | item 4.4 | pp. 5-5 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_GAZETTE_2443_27-ITEM-6` | The Sri Lanka Gazette Ext | item 6 | pp. 5-5 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_GAZETTE_2443_27-REGULATION-12` | The Sri Lanka Gazette Ext | regulation 12 | pp. 3-3 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_GAZETTE_2443_27-REGULATION-13` | The Sri Lanka Gazette Ext | regulation 13 | pp. 3-3 | YES | NO (Stub) | NO | N/A | Uncompiled | NO | Repeal instruction without standalone operative rules. |
| `CLAUSE-DOC_GAZETTE_2443_27-REGULATION-14` | The Sri Lanka Gazette Ext | regulation 14 | pp. 4-4 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_GAZETTE_2443_27-REGULATION-2` | The Sri Lanka Gazette Ext | regulation 2 | pp. 1-1 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_GAZETTE_2443_27-REGULATION-4` | The Sri Lanka Gazette Ext | regulation 4 | pp. 2-2 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_GAZETTE_2443_27-REGULATION-5` | The Sri Lanka Gazette Ext | regulation 5 | pp. 2-2 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_GAZETTE_2443_27-REGULATION-8` | The Sri Lanka Gazette Ext | regulation 8 | pp. 2-2 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_GAZETTE_2443_27-REGULATION-9` | The Sri Lanka Gazette Ext | regulation 9 | pp. 3-3 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_GAZETTE_2494_47-SECTION-2.1` | Gazette Extraordinary No. 2494/47 | Section 2.1 | pp. 15-15 | YES | NO (Stub) | NO | N/A | Uncompiled | NO | 1-line cross-reference stub without substantive obligations. |
| `CLAUSE-DOC_GAZETTE_2494_47-SECTION-4.3` | Gazette Extraordinary No. 2494/47 | Section 4.3 | pp. 17-17 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_GAZETTE_2494_47-SECTION-4.6` | Gazette Extraordinary No. 2494/47 | Section 4.6 | pp. 15-15 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_GAZETTE_2494_47-REGULATION-3` | Gazette Extraordinary No. 2494/47 | regulation 3 | pp. 3-3 | YES | YES | YES (2) | YES | YES (Approved) | YES | Compiled: RULE-FCAU-2494-47-REG-3, RULE-FCAU-2494-47-REG-3-B2B |
| `CLAUSE-DOC_GAZETTE_2494_47-REGULATION-4` | Gazette Extraordinary No. 2494/47 | regulation 4 | pp. 5-5 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_GAZETTE_2494_47-REGULATION-5` | Gazette Extraordinary No. 2494/47 | regulation 5 | pp. 3-3 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_GAZETTE_2494_47-REGULATION-6` | Gazette Extraordinary No. 2494/47 | regulation 6 | pp. 2-2 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_GAZETTE_2494_47-SECTION-1` | Gazette Extraordinary No. 2494/47 | section 1 | pp. 15-15 | YES | YES | NO | N/A | Uncompiled | YES | Eligible candidate for compilation |
| `CLAUSE-DOC_GAZETTE_2494_47-SECTION-32` | Gazette Extraordinary No. 2494/47 | section 32 | pp. 1-1 | YES | NO (Stub) | NO | N/A | Uncompiled | NO | Inoperative statutory preamble / minister empowering formula under Section 32. |
| `CLAUSE-DOC_GAZETTE_2496_03-SECTION-527` | The Sri Lanka Gazette Ext | Section 527 | pp. 1-1 | **NO (OUT)** | NO (Stub) | NO | N/A | Uncompiled | NO | Out of scope: Companies Act No. 7 of 2007 fees order (corporate fees, non-Food Control). |

---

## 3. Phase 4.2 Controlled Ingestion & Audit Addendum (2026-10-27)

### Audit Clarification on Phase 4.1 Scripted Flags
During the Phase 4.2 preflight audit, it was determined that the Phase 4.1 export script (`scratch/clause_audit_register.json`) assigned boolean fields (`rule_verified`, `source_inspected`, `text_matches_source`, and `is_promulgated`) via blanket script heuristics (`True` for all authentic clauses; `rule_verified = has_rule`). While all 8 physical source PDFs exist on disk and were SHA-256 verified, individual sentence-by-sentence manual visual comparison had only been completed for compiled rules and shortlisted candidates. Blanket assertions of line-by-line manual verification across all 59 baseline clauses are hereby clarified to reflect this heuristic assignment.

### Ingestion of Gazette Extraordinary No. 1688/28 Clauses
Following 100% manual visual verification of 300 DPI raster page scans against raw WinRT OCR text, the 3 candidate clauses from Gazette 1688/28 were ingested into the PostgreSQL `clauses` table with genuine 768-dim unit-normalized local BGE v1.5 embeddings:
1. `CLAUSE-DOC_3CD9948D2C334D08A11DD5BC9CC1F1A1EC053D6E819EA30F205687DDA7C342C7-REGULATION-5-IV` (Regulation 5(iv), Page 1, Negative prohibition on added colours in raw fish, molluscs, crustaceans, and echinoderms).
2. `CLAUSE-DOC_3CD9948D2C334D08A11DD5BC9CC1F1A1EC053D6E819EA30F205687DDA7C342C7-SCHEDULE-I-TABLE-I` (Schedule I Table I, Page 1, Exhaustive positive list of 10 permitted synthetic dyes across Red, Yellow, Blue, Green groups; 8 INS numbers).
3. `CLAUSE-DOC_3CD9948D2C334D08A11DD5BC9CC1F1A1EC053D6E819EA30F205687DDA7C342C7-SCHEDULE-I-TABLE-II` (Schedule I Table II, Page 2, Exhaustive positive list of 21 permitted natural/mineral colouring substances).

### Updated Summary of Authentic Corpus Capacity (Post-Phase 4.2)
- **Total Authentic Clauses in PostgreSQL:** **62** (59 baseline + 3 ingested).
- **Substantive Operative Food Control Clauses:** **47** (44 baseline + 3 ingested).
- **Ineligible Stubs & Out-of-Scope:** **15** (unchanged).
- **Clauses with Compiled Rules:** **8** (unchanged; 0 rules added or modified in Phase 4.2).
- **Uncompiled Substantive Candidates:** **39** (36 baseline + 3 Gazette 1688/28 clauses).
- **Option A Target Progress:** 47 operative clauses available vs. $\ge 25$ required (188% of target capacity).

---

## 4. Phase 4.3 Single-Rule Compilation Addendum (2026-10-27)

### Single-Rule Compilation for Gazette 1688/28 Regulation 5(iv)
Following verified ingestion in Phase 4.2, `CLAUSE-DOC_3CD9948D2C334D08A11DD5BC9CC1F1A1EC053D6E819EA30F205687DDA7C342C7-REGULATION-5-IV` was compiled into authentic candidate rule:
- **Rule ID:** `RULE-COLOURING-SEAFOOD-PROHIBITION`
- **Operative Provision:** Regulation 5(iv) of Gazette 1688/28 amending Food (Colouring Substances) Regulations 2006.
- **Obligation Type:** Negative prohibition (`prohibition`) prohibiting the addition of colouring substances to fish, molluscs, crustaceans, and echinoderms.
- **Review Status:** `PENDING_REVIEW` (`is_gold_rule=False`, `is_synthetic=False`).
- **Deterministic Verification:** Validated via `RuleVerifier` with 0 issues (`is_valid=True`).

### Updated Summary of Compiled Rules & Clauses (Post-Phase 4.3)
- **Total Authentic Clauses in PostgreSQL:** **62** (47 substantive operative + 15 stubs/out-of-scope).
- **Clauses with Compiled Rules:** **9** (8 baseline + 1 newly compiled clause).
- **Total Authentic Rules in PostgreSQL:** **13** (2 approved, 11 pending review; 0 gold).
- **Uncompiled Substantive Candidates:** **38** (ready for bounded compilation toward the $\ge 18–25$ clause target).


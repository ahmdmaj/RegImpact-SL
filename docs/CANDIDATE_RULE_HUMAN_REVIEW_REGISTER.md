# RegImpact-SL — Candidate Rule Human-Review Register

**Evaluation Date:** 2026-10-26  
**Auditor Role:** Senior Research Engineer, Regulatory Data Integrity Auditor, Benchmark Methodologist, Independent Verification Reviewer  
**Governing Specification:** `RegImpact-SL_Project_Proposal_v4_FINAL.md` (Frozen Proposal v4)  
**Corpus Scope:** Promulgated Sri Lankan Food Regulations (Authentic Gazettes)

---

## 1. Executive Summary & Review Governance

This register provides the definitive human-review audit status for all 12 authentic statutory rules currently persisted in the RegImpact-SL database.

### Review Level Definitions
1. **Technical Verification (Deterministic Gate)**: Validates JSON schema conformance, character-exact quote span substring matching within the source PDF page, and literal check (numeric values, dates, units). *Passing technical verification does NOT constitute legal approval or gold designation.*
2. **Primary Annotator Review**: Formal manual evaluation by the primary research engineer via `/admin/reviews`. Confirms legal interpretation, boundary consistency, and exception modeling. Transitions status to `APPROVED`, but keeps `is_gold_rule=False`.
3. **Independent Secondary Annotation**: Blind independent evaluation by a distinct researcher. Required to compute inter-rater agreement (Cohen's kappa $\kappa$).
4. **Adjudication**: Consensus review process applied only where primary and secondary annotators disagree.
5. **Expert Legal Adjudication**: Formal review and sign-off by a qualified Sri Lankan legal expert / regulatory counsel. *This is the ONLY authorized mechanism to designate `is_gold_rule=True`.*

### Current Integrity Baseline
- **Total Authentic Rules in Database**: 12
- **Primary Annotator Approved**: 2 (`RULE-FCAU-2494-47-REG-3`, `RULE-FCAU-2494-47-REG-3-B2B`)
- **Pending Human Review**: 10 (compiled during Phase 3.3 across 3 candidate instruments)
- **Independent Secondary Reviews**: 0 (no fake annotators created)
- **Expert Legal Adjudications**: 0 (no fake legal sign-offs created)
- **Gold Rules (`is_gold_rule=True`)**: 0 (100% compliant with zero-gold provisional gate)

---

## 2. Candidate Rule Review Register (10 Pending Rules)

The 10 rules below were deterministically compiled from authentic operative clauses in Phase 3.3. All 10 are queued in PostgreSQL with `review_status = 'PENDING_REVIEW'`.

### Sugar Colour-Coding Regulations (Gazette Extraordinary No. 2494/06)

#### 1. `RULE-SUGAR-2494-06-RED`
- **Rule Identifier**: `RULE-SUGAR-2494-06-RED`
- **Source Instrument**: The Sri Lanka Gazette Extraordinary No. 2494/06 (2026-06-23)
- **Source Clause**: `Schedule (Regulation 3)` (Item 1, Red Logo)
- **Observed Review Status**: `PENDING_REVIEW` (`is_gold_rule=False`)
- **Source Evidence Available**: Quote span (76 chars) on Page 2:  
  `"1. More than 8.0 g/100 ml | Red | Logo with Sugar in Sinhala, Tamil, English"`  
  Verified SHA-256: `15803fe0b14aabe0c79126ebe7c8834d8063b6ed8c2a9033c1201ff538bcd95b`
- **Questions Requiring Human Judgement**:
  1. Does the rule accurately capture all prepackaged ready-to-serve beverages, and is the B2B exception (`products.is_b2b == True`) correctly linked to principal Regulation 3(2)?
  2. Is the statutory boundary strictly greater than 8.0 g/100ml (`> 8.0`)? (Gazette text explicitly states "More than 8.0 g/100 ml").
- **Primary Review Status**: PENDING_REVIEW (Queued in `/admin/reviews`)
- **Independent Annotation Status**: PENDING (External dependency)
- **Adjudication Status**: PENDING (Not required unless annotators disagree)
- **Expert Review Status**: PENDING (External dependency)
- **Gold Eligibility Status & Reason**: **INELIGIBLE**. Requires independent second annotation and legal expert sign-off.

---

#### 2. `RULE-SUGAR-2494-06-AMBER`
- **Rule Identifier**: `RULE-SUGAR-2494-06-AMBER`
- **Source Instrument**: The Sri Lanka Gazette Extraordinary No. 2494/06 (2026-06-23)
- **Source Clause**: `Schedule (Regulation 3)` (Item 2, Amber Logo)
- **Observed Review Status**: `PENDING_REVIEW` (`is_gold_rule=False`)
- **Source Evidence Available**: Quote span (76 chars) on Page 2:  
  `"2. 2.5g to 8.0 g/100 ml | Amber | Logo with Sugar in Sinhala, Tamil, English"`  
  Verified SHA-256: `15803fe0b14aabe0c79126ebe7c8834d8063b6ed8c2a9033c1201ff538bcd95b`
- **Questions Requiring Human Judgement**:
  1. Are both interval boundaries inclusive (`2.5 <= sugar <= 8.0`), given the phrasing "2.5g to 8.0 g/100 ml"?
  2. How should boundary measurements at exactly 8.00 g/100ml be harmonized with Tier 1 ("More than 8.0")?
- **Primary Review Status**: PENDING_REVIEW (Queued in `/admin/reviews`)
- **Independent Annotation Status**: PENDING (External dependency)
- **Adjudication Status**: PENDING
- **Expert Review Status**: PENDING
- **Gold Eligibility Status & Reason**: **INELIGIBLE**.

---

#### 3. `RULE-SUGAR-2494-06-GREEN`
- **Rule Identifier**: `RULE-SUGAR-2494-06-GREEN`
- **Source Instrument**: The Sri Lanka Gazette Extraordinary No. 2494/06 (2026-06-23)
- **Source Clause**: `Schedule (Regulation 3)` (Item 3, Green Logo)
- **Observed Review Status**: `PENDING_REVIEW` (`is_gold_rule=False`)
- **Source Evidence Available**: Quote span (78 chars) on Page 2:  
  `"3. Less than 2.5 g/100 ml | Green | Logo with Sugar in Sinhala, Tamil, English"`  
  Verified SHA-256: `15803fe0b14aabe0c79126ebe7c8834d8063b6ed8c2a9033c1201ff538bcd95b`
- **Questions Requiring Human Judgement**:
  1. Does "Less than 2.5 g/100 ml" strictly exclude 2.5 g (`< 2.5`)?
  2. Should naturally occurring sugars in milk/pure fruit extracts be evaluated identically under this schedule?
- **Primary Review Status**: PENDING_REVIEW (Queued in `/admin/reviews`)
- **Independent Annotation Status**: PENDING (External dependency)
- **Adjudication Status**: PENDING
- **Expert Review Status**: PENDING
- **Gold Eligibility Status & Reason**: **INELIGIBLE**.

---

#### 4. `RULE-SUGAR-2494-06-GLASS-PROVISO`
- **Rule Identifier**: `RULE-SUGAR-2494-06-GLASS-PROVISO`
- **Source Instrument**: The Sri Lanka Gazette Extraordinary No. 2494/06 (2026-06-23)
- **Source Clause**: `Regulation 3(1)` proviso
- **Observed Review Status**: `PENDING_REVIEW` (`is_gold_rule=False`)
- **Source Evidence Available**: Quote span (336 chars) on Page 2:  
  `"Provided however, when there is a space constraint in the total printable area with respect to glass bottles which contain such food in using the logo specified in Column III of the Schedule hereto, the logo specified in Column IV of the said Schedule may be used in the corresponding colour specified in Column II of the such Schedule."`  
  Verified SHA-256: `15803fe0b14aabe0c79126ebe7c8834d8063b6ed8c2a9033c1201ff538bcd95b`
- **Questions Requiring Human Judgement**:
  1. What constitutes an objective threshold for "space constraint in total printable area" (e.g. printable area $< 50\text{ cm}^2$ or bottle crown diameter), or must this remain a discretionary SME assertion?
  2. Does the exception apply strictly to glass bottles or extend by legal implication to other small rigid containers?
- **Primary Review Status**: PENDING_REVIEW (Queued in `/admin/reviews`)
- **Independent Annotation Status**: PENDING (External dependency)
- **Adjudication Status**: PENDING
- **Expert Review Status**: PENDING
- **Gold Eligibility Status & Reason**: **INELIGIBLE**.

---

### Food Preservatives Regulations 2019 (Gazette Extraordinary No. 2113/16)

#### 5. `RULE-PRESERVATIVE-JAM-JELLY-LIMIT`
- **Rule Identifier**: `RULE-PRESERVATIVE-JAM-JELLY-LIMIT`
- **Source Instrument**: The Sri Lanka Gazette Extraordinary No. 2113/16 (2019-03-05)
- **Source Clause**: `Schedule II Item 3.1(h)`
- **Observed Review Status**: `PENDING_REVIEW` (`is_gold_rule=False`)
- **Source Evidence Available**: Quote span (106 chars) on Page 13:  
  `"(h) Jams, Jellies, marmalades: Sorbates 300 mg/kg, Sulphites (as residual SO2) 100 mg/kg, Propionates GMP;"`  
  Verified SHA-256: `3f85f3ef96b7622bdd3e45d7cc642fd96fdbd83a9f84f35f048121eab3e4016f`
- **Questions Requiring Human Judgement**:
  1. How should "Propionates GMP" (Good Manufacturing Practice) be modeled in deterministic Kleene logic: does GMP constitute unconstrained compliance or a discretionary standard requiring `CONDITIONAL_RULE`?
  2. Does the Sulphite limit of 100 mg/kg apply to residual $\text{SO}_2$ or total added salt mass?
- **Primary Review Status**: PENDING_REVIEW (Queued in `/admin/reviews`)
- **Independent Annotation Status**: PENDING (External dependency)
- **Adjudication Status**: PENDING
- **Expert Review Status**: PENDING
- **Gold Eligibility Status & Reason**: **INELIGIBLE**.

---

#### 6. `RULE-PRESERVATIVE-MIXTURE-LIMIT`
- **Rule Identifier**: `RULE-PRESERVATIVE-MIXTURE-LIMIT`
- **Source Instrument**: The Sri Lanka Gazette Extraordinary No. 2113/16 (2019-03-05)
- **Source Clause**: `Regulation 4`
- **Observed Review Status**: `PENDING_REVIEW` (`is_gold_rule=False`)
- **Source Evidence Available**: Quote span (393 chars) on Page 2:  
  `"Any specified food may have in or upon it, a mixture of two or more preservatives specified in Schedule II hereto, only if the sum total of the preservatives does not exceed one hundred percentage when the quantity of each of such preservative present in such food is expressed as a percentage of the maximum quantity of that preservative appropriate to the food as specified in that Schedule."`  
  Verified SHA-256: `3f85f3ef96b7622bdd3e45d7cc642fd96fdbd83a9f84f35f048121eab3e4016f`
- **Questions Requiring Human Judgement**:
  1. Does the summation formula $\sum \frac{C_i}{L_i} \le 100\%$ apply when one of the mixture components has a GMP limit?
  2. Does exceeding 100% trigger mandatory reformulation or an outright prohibition of distribution?
- **Primary Review Status**: PENDING_REVIEW (Queued in `/admin/reviews`)
- **Independent Annotation Status**: PENDING (External dependency)
- **Adjudication Status**: PENDING
- **Expert Review Status**: PENDING
- **Gold Eligibility Status & Reason**: **INELIGIBLE**.

---

#### 7. `RULE-PRESERVATIVE-LABEL-DECLARATION`
- **Rule Identifier**: `RULE-PRESERVATIVE-LABEL-DECLARATION`
- **Source Instrument**: The Sri Lanka Gazette Extraordinary No. 2113/16 (2019-03-05)
- **Source Clause**: `Regulation 8`
- **Observed Review Status**: `PENDING_REVIEW` (`is_gold_rule=False`)
- **Source Evidence Available**: Quote span (336 chars) on Page 4:  
  `"The label on every container or package of food, to which a permitted preservative as specified in these regulations has been added, shall have a declaration as set out in the Food (Labelling and Advertising) Regulation 2005 published in the Gazette Extraordinary No. 1376/9 of January 19, 2005 as amended from time to time or replaced."`  
  Verified SHA-256: `3f85f3ef96b7622bdd3e45d7cc642fd96fdbd83a9f84f35f048121eab3e4016f`
- **Questions Requiring Human Judgement**:
  1. Cross-instrument dynamic reference: Does the clause's statutory language ("as amended from time to time or replaced") automatically attach to Gazette Extraordinary No. 2494/47 Regulation 6 following the repeal of Gazette 1376/9?
- **Primary Review Status**: PENDING_REVIEW (Queued in `/admin/reviews`)
- **Independent Annotation Status**: PENDING (External dependency)
- **Adjudication Status**: PENDING
- **Expert Review Status**: PENDING
- **Gold Eligibility Status & Reason**: **INELIGIBLE**.

---

### Food Flavourings Regulations 2013 (Gazette Extraordinary No. 1795/51)

#### 8. `RULE-FLAVOUR-INFANT-PROHIBITION`
- **Rule Identifier**: `RULE-FLAVOUR-INFANT-PROHIBITION`
- **Source Instrument**: The Sri Lanka Gazette Extraordinary No. 1795/51 (2013-02-01)
- **Source Clause**: `Regulation 7(i)`
- **Observed Review Status**: `PENDING_REVIEW` (`is_gold_rule=False`)
- **Source Evidence Available**: Quote span (128 chars) on Page 3:  
  `"(i) shall not be added to any food for infants and young children except as permitted in the regulations made under the Act;"`  
  Verified SHA-256: `b78479b6b08d12e11fd27cfc39677d5a284bc147bf16a777eafb495b86f4135a`
- **Questions Requiring Human Judgement**:
  1. What age boundary legally defines "infants and young children" under Sri Lankan food law (e.g. infant $< 12$ months, young children $12\text{--}36$ months)?
  2. Does the exception phrase ("except as permitted in the regulations made under the Act") require cross-referencing specific infant formula gazettes?
- **Primary Review Status**: PENDING_REVIEW (Queued in `/admin/reviews`)
- **Independent Annotation Status**: PENDING (External dependency)
- **Adjudication Status**: PENDING
- **Expert Review Status**: PENDING
- **Gold Eligibility Status & Reason**: **INELIGIBLE**.

---

#### 9. `RULE-FLAVOUR-SCHEDULE-III-PROHIBITION`
- **Rule Identifier**: `RULE-FLAVOUR-SCHEDULE-III-PROHIBITION`
- **Source Instrument**: The Sri Lanka Gazette Extraordinary No. 1795/51 (2013-02-01)
- **Source Clause**: `Regulation 7(iii)`
- **Observed Review Status**: `PENDING_REVIEW` (`is_gold_rule=False`)
- **Source Evidence Available**: Quote span (70 chars) on Page 3:  
  `"(iii) shall not be used in the foods specified in Schedule III hereto."`  
  Verified SHA-256: `b78479b6b08d12e11fd27cfc39677d5a284bc147bf16a777eafb495b86f4135a`
- **Questions Requiring Human Judgement**:
  1. Schedule III encompasses unprocessed foods (milk, honey, white sugar, flour, tea, coffee, fresh meat). Does adding permitted flavouring to tea make it a permitted "specialty tea" under another standard, or does Regulation 7(iii) strictly prohibit flavouring plain tea?
- **Primary Review Status**: PENDING_REVIEW (Queued in `/admin/reviews`)
- **Independent Annotation Status**: PENDING (External dependency)
- **Adjudication Status**: PENDING
- **Expert Review Status**: PENDING
- **Gold Eligibility Status & Reason**: **INELIGIBLE**.

---

#### 10. `RULE-FLAVOUR-LABEL-DECLARATION`
- **Rule Identifier**: `RULE-FLAVOUR-LABEL-DECLARATION`
- **Source Instrument**: The Sri Lanka Gazette Extraordinary No. 1795/51 (2013-02-01)
- **Source Clause**: `Regulation 8`
- **Observed Review Status**: `PENDING_REVIEW` (`is_gold_rule=False`)
- **Source Evidence Available**: Quote span (322 chars) on Page 3:  
  `"The label on every package of food containing added flavouring substances or flavour enhancers shall include a statement indicating the presence of such flavouring substances or flavour enhancers in the list of ingredients as 'Flavouring' or 'Flavour Enhancer' as the case may be, together with its common name or INS number."`  
  Verified SHA-256: `b78479b6b08d12e11fd27cfc39677d5a284bc147bf16a777eafb495b86f4135a`
- **Questions Requiring Human Judgement**:
  1. Does providing the INS number alone fulfill the obligation, or must both the class title ("Flavouring") and INS number appear together?
  2. How does this requirement coordinate with Gazette 2494/47 Regulation 6(1)(c)?
- **Primary Review Status**: PENDING_REVIEW (Queued in `/admin/reviews`)
- **Independent Annotation Status**: PENDING (External dependency)
- **Adjudication Status**: PENDING
- **Expert Review Status**: PENDING
- **Gold Eligibility Status & Reason**: **INELIGIBLE**.

---

## 3. Previously Reviewed Authentic Rules (2 Approved Rules)

#### 11. `RULE-FCAU-2494-47-REG-3`
- **Rule Identifier**: `RULE-FCAU-2494-47-REG-3`
- **Source Instrument**: Sri Lanka Gazette Extraordinary No. 2494/47 (2026-04-17)
- **Source Clause**: `Regulation 3`
- **Observed Review Status**: `APPROVED` (`is_gold_rule=False`)
- **Source Evidence Available**: Quote span (187 chars) on Page 1:  
  `"A person shall not import, transport, distribute, store, sell, offer for sale, expose or keep for sale or advertise, any food contained in a package or container, unless such package or container is labelled in accordance with these regulations:"`  
  Verified SHA-256: `83ed19c22873471652d0073fe16c977442e42c8ecac2edf1d691d00d78d8a054`
- **Questions Requiring Human Judgement**: Clarification of strict liability scope across intermediate distributors vs retail sellers.
- **Primary Review Status**: **APPROVED** (Reviewed by `researcher_engineer_01` on 2026-10-25)
- **Independent Annotation Status**: PENDING (External dependency)
- **Adjudication Status**: PENDING
- **Expert Review Status**: PENDING (External dependency)
- **Gold Eligibility Status & Reason**: **INELIGIBLE**. Remains non-gold until independent legal expert signs off.

---

#### 12. `RULE-FCAU-2494-47-REG-3-B2B`
- **Rule Identifier**: `RULE-FCAU-2494-47-REG-3-B2B`
- **Source Instrument**: Sri Lanka Gazette Extraordinary No. 2494/47 (2026-04-17)
- **Source Clause**: `Regulation 3` proviso
- **Observed Review Status**: `APPROVED` (`is_gold_rule=False`)
- **Source Evidence Available**: Quote span (248 chars) on Page 1:  
  `"Provided however, the provisions of these regulations shall not apply to a food... for further processing or manufacture and not intended for sale directly to the final consumer, where such food is accompanied by documents containing adequate information..."`  
  Verified SHA-256: `83ed19c22873471652d0073fe16c977442e42c8ecac2edf1d691d00d78d8a054`
- **Questions Requiring Human Judgement**: Practical criteria defining "adequate information" in wholesale trade documentation.
- **Primary Review Status**: **APPROVED** (Reviewed by `researcher_engineer_01` on 2026-10-25)
- **Independent Annotation Status**: PENDING (External dependency)
- **Adjudication Status**: PENDING
- **Expert Review Status**: PENDING (External dependency)
- **Gold Eligibility Status & Reason**: **INELIGIBLE**. Remains non-gold until independent legal expert signs off.

---

## 4. Summary Table of Human Review Status

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

## 5. Effect on Research Claims

1. **No Legal Correctness Claims**: The system cannot and does not claim that any candidate rule is legally correct or represents official statutory ground truth.
2. **Provisional Benchmark Integrity**: Because all 12 rules have `is_gold_rule = False`, all 30 evaluation scenarios derived from them have `is_gold_scenario = False`.
3. **No Empirical Claim of Human-Level Evaluation**: Any evaluation run against this provisional slice measures relative baseline sensitivity (B0 vs B1 vs B2 vs B3 vs P) on candidate ground truth, not absolute legal accuracy.
4. **Reproducibility Guarantee**: The candidate rules are 100% reproducible from authentic gazette texts and character-offset spans without external LLM dependencies or fabricated data.

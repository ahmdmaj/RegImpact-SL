# RegImpact-SL: LLM-Assisted Verified Rule Compilation for Business-Specific Regulatory Impact Analysis of Small Food Manufacturers in Sri Lanka

**Project proposal, version 4 — development freeze (revised after feasibility and literature-informed review)**

Author: Ahnaf, Faculty of Computing, Sabaragamuwa University of Sri Lanka

Research area: Regulatory intelligence, information retrieval, retrieval-augmented generation, rules-as-code, neuro-symbolic reasoning, AI-assisted decision support

## Abstract

Small food manufacturers in Sri Lanka operate under several overlapping regulatory instruments issued by different authorities. When a regulation is amended or replaced, an owner must work out whether the change applies to their business, why, what it affects, what to do, from when, and on what authority. Retrieval-augmented generation (RAG) systems can surface relevant passages, but applicability depends on precise conditions (product type, activity, capacity thresholds, dates, transition periods) that language models handle inconsistently.

This project proposes RegImpact-SL, a system that uses an LLM-assisted rule-compilation pipeline to translate selected regulatory clauses into typed, provenance-carrying executable rules (instrument, clause, page, quote span), followed by deterministic verification and execution. Clauses that cannot be represented safely are marked unsupported rather than forced into rules. A deterministic engine evaluates rules against a structured business profile, handles effective dates and transition periods, and, when the profile is incomplete, names the minimum missing facts needed to decide. It also produces counterfactual explanations where a valid alternative state exists, and maps applicable rules to impacts and actions. The approach is compared against an oracle-context long-context LLM and three RAG baselines on a new benchmark, independently double-annotated and externally reviewed on a representative sample, built from real Sri Lankan regulatory clauses. Evaluation emphasises applicability, temporal correctness, abstention quality, impact and action identification, and citation faithfulness, not only accuracy.

The system is decision support and a research prototype. It does not provide legal advice.

## 1. Background and motivation

Small and medium enterprises are a major contributor to employment and output in Sri Lanka, and published policy and development-bank sources identify regulatory and institutional complexity as a constraint on their growth. A small food manufacturer may need to consider food-control and labelling regulations (Food Control Administration Unit), industry registration (Ministry of Industry), environmental licensing for prescribed activities (Central Environmental Authority and local authorities), and, where included, labour-related obligations (EPF/ETF). These come from different authorities, are published in different forms (gazettes, web pages, forms, circulars) and change at different times. The practical question is rarely "what does the regulation say". It is: given my business, does this change affect me?

**Source-verification note:** every factual statement about specific regulations, dates and thresholds in the final submission must be checked against the primary official source and cited. This proposal deliberately avoids stating unverified thresholds.

## 2. Problem statement

Existing approaches fall short in three ways.

1. Keyword search retrieves the regulation but cannot decide relevance for a specific business.
2. Vector RAG retrieves semantically close passages, but an LLM reasoning over them can be inconsistent on exact thresholds, conjunctions of conditions, dates and exceptions, and cannot reliably tell when information is missing.
3. Change handling is weak. Sri Lankan amendments are often published as separate gazettes containing textual instructions (substitute, insert, omit, repeal) rather than as consolidated versions, so "what changed" and "what was in force on date X" are not directly retrievable.

The problem addressed is therefore: given a regulatory change and a structured business profile, determine applicability, reason, obligation, impact, action, effective date and evidence, consistently, auditably, and with honest uncertainty.

## 3. Related work and research gap

The literature review is organised into streams. For each stream the review states what it already solves and what it does not solve for this task. All citations below are candidates and must be located, read and verified before submission.

| Research stream | What it already solves | What it does not solve for this project |
| --- | --- | --- |
| Regulatory QA and obligation retrieval (e.g. Umar et al. 2025; Gokhan and Briscoe 2025) | Finding relevant regulatory passages, multi-passage evidence | Business-specific applicability |
| Legal RAG and its benchmarks (e.g. Legal RAG Bench 2026; legal RAG statutory-survey benchmarking 2026) | Evaluating retrieval and reasoning, separating retrieval from reasoning failures | A Sri Lankan food-SME impact benchmark |
| Temporal legal reasoning (e.g. Apofasi 2026, reported to address Sri Lankan legal materials; versioned-corpus French tax benchmark 2026) | Point-in-time validity, version-aware retrieval, temporal misgrounding | Business-profile-conditioned applicability and impact |
| Rules-as-code (OpenFisca, Catala; discussion of LLMs and rules-as-code) | Executable, auditable rules | Low-cost, verified, LLM-assisted rule compilation; these systems rely on human interpretation |
| LLM-based legal information extraction | Extracting obligations, conditions, thresholds, exceptions | Verified executable applicability rules with provenance |
| Abstention and clarifying questions (e.g. statute-centric legal QA with safe abstention, 2026) | Declining when context is insufficient | Identifying the minimum missing business facts |
| Citation and groundedness evaluation (e.g. Trautmann et al. 2024; Filice et al. 2025; Reuter et al. 2025) | Checking whether answers are grounded in sources | Clause-level trace from rule to business impact |
| Sri Lankan legal AI | Temporal legal RAG reportedly exists | Food-SME regulatory impact task |

**Gap.** Existing research demonstrates strong capabilities in regulatory retrieval, legal RAG, temporal legal reasoning, rules-as-code, structured legal extraction, abstention and citation verification, but largely treats them as separate problems. Temporal legal RAG has also been reported in the Sri Lankan context, so temporal reasoning alone is not claimed as the primary novelty. A specific gap remains in evaluating whether an LLM-assisted, provenance-preserving rule-compilation pipeline combined with deterministic business-profile reasoning improves business-specific regulatory applicability analysis and impact identification for small food manufacturers in Sri Lanka. In particular there is limited evidence on minimal-pair consistency, missing-business-fact abstention, counterfactual applicability explanations and operational impact mapping in this domain.

**Novelty statement.** No benchmark was identified in the reviewed literature that targets business-specific regulatory applicability and impact analysis for small food manufacturers in Sri Lanka, with clause-level provenance, minimal-pair consistency, incomplete-profile abstention and executable applicability rules. This claim will be re-checked at the end of the literature review.

## 4. Research questions and hypotheses

**Main question.** To what extent does an LLM-assisted, verified rule-compilation and deterministic execution approach improve the accuracy, consistency, temporal correctness and abstention quality of business-specific regulatory applicability analysis, and the identification of impacts and actions, for small food manufacturers in Sri Lanka, compared with end-to-end LLM and RAG approaches?

| ID | Research question |
| --- | --- |
| RQ1 | How does applicability accuracy of the proposed system compare with long-context and RAG baselines when all systems receive the same business profile? |
| RQ2 | Does the proposed system show better minimal-pair consistency and temporal correctness (effective dates, transition periods, amendments)? |
| RQ3 | Can the system abstain correctly when the profile is incomplete, and identify the minimum missing facts? |
| RQ4 | How accurate is LLM-assisted rule extraction, how much does the verification pipeline reduce manual correction, and how much human verification effort remains? |
| RQ5 | How well does the system identify the affected activities, documents or processes, and the required actions, for applicable rules? |

**Hypotheses.**

- **H1.** The proposed system achieves higher minimal-pair consistency and temporal correctness than the RAG baselines.
- **H2.** The proposed system achieves higher applicability F1 than the lexical and dense-retrieval baselines; performance relative to the oracle-context long-context baseline is treated as an empirical comparison rather than an assumed win.
- **H3.** The proposed system achieves higher abstention precision and recall than the RAG baselines on incomplete profiles.
- **H4.** Verification reduces the proportion of compiled rules requiring manual correction compared with unverified LLM rule extraction, while maintaining high agreement with gold rules.
- **H5.** The proposed system achieves higher impact-identification and action-identification F1 than the RAG baselines on applicable cases.
- **H0 (for each).** There is no meaningful difference between the compared systems, judged using effect sizes and confidence intervals with clause-level clustering.

## 5. Aim and objectives

**Aim.** To design, implement and evaluate a verified rule-compilation and execution pipeline for regulatory change impact analysis, and to release a benchmark for Sri Lankan small food manufacturers.

| # | Objective |
| --- | --- |
| O1 | Build a versioned corpus of official instruments with page-level provenance. |
| O2 | Define a typed business-profile schema and a typed rule schema. |
| O3 | Build an amendment-aware version model (patch operations, effective dates, transitions). |
| O4 | Build LLM-assisted rule extraction with a multi-stage verification pipeline, including a non-compilable state for clauses that cannot be safely formalised. |
| O5 | Build a deterministic applicability engine with abstention, minimum-missing-field search and counterfactual explanation. |
| O6 | Implement baselines B0 to B3 under identical inputs. |
| O7 | Construct and validate the benchmark (real clauses, minimal pairs, temporal, incomplete-profile and impact/action cases). |
| O8 | Run controlled experiments with ablations and report results with uncertainty. |
| O9 | Provide a thin API and UI demonstrating the pipeline. |

## 6. Scope

**In scope.** Geography: Sri Lanka. Business type: small food manufacturers. Language: English.

Regulatory domains:

- **Core:** (1) food control and labelling; (2) manufacturing/industry registration; (3) environmental licensing for prescribed activities.
- **Secondary:** (4) EPF/ETF obligations, included only if sufficient conditional and versioned rules are identified during corpus selection (decision recorded at the Week 3 gate).

Corpus: 20 to 30 authoritative instruments, prioritising 25 to 40 usable clauses and at least 5 amendment/version chains.

Core task: change impact analysis, with output CHANGE → APPLICABILITY → REASON → OBLIGATION → IMPACT → ACTION → EFFECTIVE DATE → EVIDENCE → UNCERTAINTY.

**Out of scope (initial).** Tax and local-authority bylaws beyond selected examples, other industries, Sinhala and Tamil text, automated submissions, legal advice, knowledge graphs, agentic workflows, multi-LLM orchestration.

## 7. Expected contributions

**Primary contribution**

1. Business-context-aware, executable applicability analysis for SME regulatory impact: an LLM-assisted compile-verify-execute pipeline that converts regulatory clauses into verified, provenance-carrying rules and evaluates them against a business profile.

**Supporting contributions**

2. Verified LLM-to-rule extraction with explicit handling of non-compilable clauses.
3. Incomplete-profile abstention with minimum-missing-field identification, and counterfactual explanations for numeric, ordinal and explicitly defined categorical conditions.
4. Business-impact and action mapping with its own evaluation.
5. Benchmark: a real-clause-based regulatory impact benchmark for small food manufacturers, independently double-annotated with external expert review of a representative sample, with minimal-pair, invariance, temporal, incomplete-profile and impact subsets.
6. A temporal and amendment model for Sri Lankan instruments supporting "in force on date X" and transition-period reasoning. This is a supporting component, not the claimed novelty.
7. Empirical evidence comparing oracle-context long-context, keyword, vector and hybrid RAG baselines with the proposed system and its ablations.
8. Open prototype with API and UI.

## 8. System architecture plan

### 8.1 Design principle

The LLM is used where language understanding is needed (reading clauses, explaining results) and is kept out of where precision is needed (evaluating conditions, dates and thresholds). The authoritative source is always the official document, never the model. The architecture is neuro-symbolic in character (neural: extraction, explanation, embeddings; symbolic: typed rules, deterministic logic, temporal validity, three-valued evaluation); this is a description of the design, not a novelty claim. Converting law into executable rules (rules-as-code) is established work; the research question here is whether LLM-assisted compilation with verification can match or improve on end-to-end approaches for this task.

Research pipeline:

```
Business Profile + Regulatory Change
 -> Rule lookup -> Applicability -> Obligation -> Impact
 -> Action -> Effective date -> Evidence -> Uncertainty
```

### 8.2 End-to-end architecture

```
OFFICIAL SOURCES (gazettes, FCAU, Ministry of Industry, CEA, EPF/ETF)
 |
 v
[A] INGESTION & PROCESSING
 PDF -> text (PyMuPDF/pdfplumber, OCR fallback) -> cleaning
 -> page/clause segmentation -> metadata -> source snapshot
 |
 v
[B] VERSION & AMENDMENT MODEL
 base instrument + amendment gazettes -> patch operations
 (substitute / insert / omit / repeal) -> clause versions
 -> validity intervals (published, commences, transition, superseded)
 |
 +------+---------------------------+
 | |
 v v
[C] RULE COMPILATION [D] RETRIEVAL INDEXES
 LLM extracts typed rules BM25 + vector (pgvector)
 with quote spans + metadata filters + reranker
 or marks clause NON_COMPILABLE |
 | |
 v |
[E] VERIFICATION |
 schema check, quote-span |
 grounding, literal check, |
 cross-extraction agreement, |
 human review queue |
 | |
 v |
[F] VERSIONED RULE STORE (PostgreSQL) <--+ (retrieval finds candidate
 | clauses and uncompiled gaps)
 v
[G] APPLICABILITY ENGINE (deterministic)
 inputs: business profile + as-at date
 outputs: outcome status + trace
 + minimum missing fields + counterfactuals
 |
 v
[H] IMPACT & ACTION MAPPER
 obligation type -> affected activity/document -> action template
 |
 v
[I] EXPLANATION LAYER (LLM, constrained)
 writes the report from structured facts + verified evidence only
 |
 v
[J] EVIDENCE CHECK
 every claim -> rule -> clause -> page -> quote span -> source URL
 |
 v
STRUCTURED IMPACT REPORT --> FastAPI --> React UI
```

### 8.3 Component specifications

**\[A\] Ingestion and processing.** Download official documents and store immutable snapshots with hash, retrieval date and source URL. Extract text with two methods and compare (PyMuPDF, pdfplumber), with OCR for scanned gazettes. Preserve page numbers and character offsets so every later quote span can be located.

**\[B\] Version and amendment model.** Each instrument has versions with a validity interval: publication date, commencement date, optional transition end, and superseded-by link. Amendments are parsed into patch operations and applied to the base clause text to create the new clause version. A change event is the diff between two clause versions, typed as threshold change, new obligation, removed obligation, changed condition, or changed date. Where an authoritative consolidated version exists, it is used to validate the patch result.

**\[C\] Rule compilation.** An LLM reads a clause and either emits a rule in a fixed JSON schema (section 8.5) or marks the clause NON\_COMPILABLE. Output is constrained to the schema and must include the exact supporting quote. Clauses are marked NON\_COMPILABLE when they contain discretionary, ambiguous, cross-referenced or context-dependent language that cannot be reliably represented in the initial rule vocabulary. They are never forced into an executable rule.

**\[D\] Retrieval indexes.** Hybrid retrieval (BM25, dense embeddings in pgvector, metadata filters, reranker) has a defined role: find candidate clauses for a change event, link amendments to base instruments, and detect clauses with no compiled rule (coverage gaps), which are flagged as low-confidence instead of silently answered. The retrieval layer is also the retrieval part of baselines B1 to B3.

**\[E\] Verification (what makes compiled rules trustworthy).**

1. Schema and type validation.
2. Quote-span grounding: the quoted text must appear verbatim on the cited page.
3. Literal check: every number, unit and date in the rule must occur in the quote span.
4. Cross-extraction agreement: a second extraction using a different prompt configuration must agree on the rule logic; disagreements go to review. A second model is optional and is not required for the core implementation.
5. Human review queue for disagreements and low-confidence rules. Rules for the test set are written and verified by hand as gold rules.

**\[G\] Applicability engine.** Evaluates rule conditions over the profile using three-valued logic. A missing field yields UNKNOWN, which propagates through AND/OR. Internally the engine distinguishes five outcome statuses:

| Status | Meaning |
| --- | --- |
| APPLICABLE | Rule conditions are satisfied, and the rule is in force at the as-at date. |
| NOT\_APPLICABLE | Rule conditions are not satisfied, or an exception applies. |
| CONDITIONAL\_MISSING\_DATA | The outcome depends on profile fields that are unknown. |
| CONDITIONAL\_RULE | The rule itself is conditional (for example "applies if X, unless Y") in a way the profile cannot resolve. |
| UNSUPPORTED | The clause is NON\_COMPILABLE; no executable rule exists and the system declines to decide. |

User-facing reports may group these, but evaluation separates them. Abstention metrics (RQ3) are computed on CONDITIONAL\_MISSING\_DATA.

- **Minimum missing fields:** for a CONDITIONAL\_MISSING\_DATA result, the engine searches for the smallest set of unknown fields whose values could decide the outcome and turns it into clarifying questions.
- **Counterfactuals:** for each decisive condition, the nearest profile value that would flip the outcome. Counterfactuals are supported for numeric or ordinal threshold conditions and for explicitly defined categorical conditions where a valid alternative state can be identified. They are not promised for arbitrary categorical values (for example there is no meaningful "nearest product").
- **Temporal evaluation:** takes an as-at date and checks the validity interval, including transition periods (not yet in force, in transition, in force, superseded).
- Produces a full evaluation trace for audit.

**\[H\] Impact and action mapper.** Uses a bounded manually defined mapping vocabulary to map obligation types (labelling, registration, licensing, documentation, reporting, process) to affected business activities/documents/processes and action templates. The mapping is deterministic and is evaluated only for categories represented in the benchmark.

**\[I\] Explanation layer.** The LLM receives only structured facts (engine output, trace, verified evidence) and writes the human-readable report. It cannot add claims. Output is checked in \[J\].

**\[J\] Evidence check.** Every sentence-level claim in the report must map to an engine output or a verified quote span. Unmapped claims are removed or flagged and counted in the unsupported-claim rate.

### 8.4 Business profile schema

```
BusinessProfile
 business_id
 industry / activity (e.g. food_manufacturing)
 employee_count
 products[] (category, prepackaged: bool, ...)
 production_capacity (value, unit, per period)
 premises (type, location authority area)
 market (domestic / import / export flags)
 existing_licences[]
 as_at_date
 (every field may be null = unknown)
```

Fields are driven by what real clauses reference. The schema is extended only when a gold rule requires a new field.

### 8.5 Rule schema (illustrative example)

The values below are placeholders and not real regulatory content. The initial vocabulary (all, exceptions, field, operator, value) will be extended only when gold rules require it; clauses beyond it are marked NON\_COMPILABLE.

```json
{
 "rule_id": "EXAMPLE-001",
 "source": {
 "instrument": "<official title>",
 "authority": "<authority>",
 "gazette_no": "<number>",
 "clause": "<clause id>",
 "page": 0,
 "quote_span": "<exact text from the page>"
 },
 "validity": {
 "published": "<date>",
 "commences": "<date>",
 "transition_until": null,
 "superseded_by": null
 },
 "applies_if": {
 "all": [
 {"field": "activity", "op": "eq", "value": "food_manufacturing"},
 {"field": "products.prepackaged", "op": "eq", "value": true},
 {"field": "production_capacity.kg_per_day", "op": "gte", "value": "<threshold from source>"}
 ]
 },
 "exceptions": [],
 "obligation": {
 "type": "labelling",
 "text": "<obligation as stated>",
 "impact_categories": ["packaging", "labelling"]
 },
 "verification": {
 "status": "human_verified",
 "extraction_model": "<model id>",
 "agreement": true
 }
}
```

### 8.6 Data storage

PostgreSQL: instruments, versions, clauses, rules, profiles, scenarios, runs, results. pgvector: clause and passage embeddings. A dedicated vector database is not used. File store: original PDF snapshots, extracted text, page images for OCR cases.

### 8.7 Backend and frontend

FastAPI services: profiles, regulations and versions, analysis, evidence, evaluation. React + TypeScript thin UI: profile form, change selection with as-at date, impact report with evidence viewer, clarifying-question panel, counterfactual view, evaluation dashboard. Example endpoints: POST /profiles, POST /analysis, GET /regulations, GET /changes, GET /evidence/{id}, GET /evaluation.

### 8.8 Evaluation architecture (separate from the application)

```
Benchmark scenarios
 -> run each system under identical inputs and identical LLM settings
 B0 oracle-context long-context | B1 BM25+LLM | B2 vector+LLM | B3 hybrid+rerank+LLM
 P proposed | P-ablations
 -> parse outputs into a common result schema
 -> metrics engine (applicability, temporal, abstention, impact/action, evidence)
 -> statistics (clause-clustered confidence intervals, paired tests)
 -> report
```

Failures are attributed by stage (retrieval, rule extraction, applicability reasoning, generation) so that retrieval errors are not conflated with reasoning errors.

## 9. Data strategy

### 9.1 Dataset A: regulatory corpus

25 to 40 instruments from official sources (FCAU, Ministry of Industry, CEA, EPF/ETF, Gazette), including real amendment chains. Selection rule: prefer instruments containing conditional or threshold-based applicability (for example prescribed-activity schedules in environmental licensing), because these exercise the research question. Universal obligations are still included as negative controls for conditionality. Every document has a source snapshot, hash and metadata record.

### 9.2 Dataset B: regulatory impact benchmark

**Scenario source.** Real authoritative regulatory clauses. Test scenarios are constructed from these real clauses, including minimal-pair, invariance, temporal and incomplete-profile variants; the underlying rule is real, the business scenario is synthetic.

**Size.** Target: 25 to 40 distinct clauses and 100 to 150 scenarios, subject to the availability of sufficiently clear authoritative clauses. Minimum acceptable benchmark: 100 scenarios covering at least 25 distinct clauses; 150 is a stretch target.

**Scenario types**

- Direct: profile versus a clause.
- Minimal pairs: identical profiles differing in one attribute that should flip the outcome.
- Invariance pairs: profiles differing in an attribute that should not change the outcome.
- Temporal: as-at date before, within transition and after commencement.
- Incomplete: a required field removed; the correct output is CONDITIONAL\_MISSING\_DATA plus the right missing field.
- Change events: from real amendments.
- Impact: for each applicable case, the gold affected activity/document/process and required action.

**Annotation.** Two annotators label independently, agreement is reported (Cohen's kappa), disagreements are adjudicated, and at least one external expert reviews a representative sample. The benchmark is described as independently double-annotated with external expert review of a sample; it is described as expert-validated only if an expert verifies all gold rules.

**Splits.** Development and test are split by clause, so no clause appears in both. The test set is frozen before final system tuning.

**Reporting.** Scenario counts are always reported per source clause and per type, not only in total.

## 10. Experimental design

### 10.1 Systems compared

All systems receive the same business profile (as text where needed), the same as-at date, the same LLM and settings (temperature 0, fixed prompts, several repeated runs for variance). The primary LLM, embedding model, reranker, prompts and inference parameters used for the final comparison are frozen before evaluation on the held-out test set.

| ID | System | Role |
| --- | --- | --- |
| B0 | Long-context LLM with an oracle-selected relevant regulatory context; no retrieval | Upper-bound reasoning baseline, not retrieval-comparable |
| B1 | BM25 retrieval + LLM | Lexical baseline |
| B2 | Dense retrieval + LLM | Standard vector RAG |
| B3 | Hybrid + reranker + LLM | Strong RAG baseline |
| P | Proposed compile-verify-execute system | Contribution |

| ID | Ablation | Role |
| --- | --- | --- |
| P-A | P without verification stage | Tests H4 and error propagation |
| P-B | P without temporal module | Isolates temporal contribution |
| P-C | P without abstention and minimum-missing-field search | Isolates abstention contribution |
| P-D | P with manually written gold rules instead of LLM-compiled | Upper bound for the engine |

### 10.2 Metrics

| Dimension | Metrics |
| --- | --- |
| Applicability | Precision, recall, F1 over outcome classes |
| Consistency | Minimal-pair flip accuracy (flips exactly when it should), invariance accuracy (does not flip when it should not) |
| Temporal | Accuracy on before, transition and after cases |
| Abstention | Precision and recall of CONDITIONAL\_MISSING\_DATA; correctness of the identified missing fields |
| Impact and action | Impact-identification F1 (affected activity, document or process); action-identification F1 |
| Rule extraction (upstream) | Agreement with gold rules (field, operator, value, exception match); correction rate with and without verification; NON\_COMPILABLE precision and recall; reviewer disagreement rate |
| Change detection | Precision, recall, F1 on typed change events |
| Evidence | Citation correctness (instrument, clause, page), quote-span exact match, evidence precision and recall |
| Generation | Unsupported-claim rate, hallucination rate |
| Cost | Verification effort (reviewer minutes per rule), LLM calls, latency |
| Human evaluation (if feasible) | Usefulness, clarity, correctness rating by domain-informed reviewers |

The five primary evaluation dimensions are applicability, temporal correctness, abstention, impact and action identification, and evidence faithfulness. Rule extraction is an upstream pipeline evaluation.

### 10.3 Statistical treatment

Confidence intervals by clause-level (cluster) bootstrap, because scenarios from the same clause are not independent. Paired comparisons (for example McNemar's test or paired bootstrap) between systems on the same scenarios. Effect sizes are reported alongside significance. No claim is made from scenario count alone.

### 10.4 Threats to validity and countermeasures

| Threat | Countermeasure |
| --- | --- |
| Circular ground truth (author writes rules and labels) | Clause-level held-out test, second annotator, expert sample review |
| Benchmark favours the engine | Include invariance pairs, incomplete profiles and ambiguous clauses that stress it |
| Baseline unfairness | Identical inputs, same LLM, tuned prompts for each baseline; B0 labelled as oracle-context upper bound |
| Few real changes | Report per-clause results and limitations honestly; do not inflate with synthetic rules |
| LLM nondeterminism | Temperature 0, repeated runs, report variance |
| Post-hoc tuning | Model, prompts, embeddings, reranker and parameters frozen before test evaluation |
| Extraction errors silently propagate | Verification stage, ablation P-A, report rule error rates |
| Rule formalizability: some clauses cannot be safely executable | NON\_COMPILABLE / UNSUPPORTED state; report the share of non-compilable clauses as a finding |

## 11. Methodology and work plan

**Implementation priority rule.** The research result is the compile-verify-execute comparison, not the UI. If time becomes constrained, cut in this order: UI richness, broad document coverage, counterfactual breadth, then secondary EPF/ETF coverage. Protect the gold rules, benchmark quality, B0-B3 baselines, deterministic engine, provenance, core evaluation, and reproducible experiments.



The plan assumes about 20 weeks and should be scaled to the actual deadline. Benchmark annotation runs in parallel from week 3 and is the highest-risk task.

| Weeks | Work | Output |
| --- | --- | --- |
| 1 to 3 | Select clauses and instruments, collect sources, define schemas, write the first gold rules by hand | Corpus v0, profile and rule schemas, gold rules v0 |
| 3 to 16 | Benchmark construction and annotation (parallel) | Benchmark v1 with agreement statistics |
| 4 to 5 | Ingestion pipeline with page-level provenance | Processed corpus |
| 6 to 7 | Rule engine and baselines B0 to B3 | Working baselines |
| 8 to 10 | LLM rule extraction and verification pipeline | Compiled and verified rule store |
| 11 to 12 | Amendment parsing, versioning and temporal evaluation | Version model, change events |
| 13 to 14 | Abstention, minimum-missing-field search, counterfactuals, impact mapping | Full proposed system |
| 15 to 16 | Freeze test set, finalize prompts, models and settings | Frozen experiment protocol |
| 17 to 18 | Run experiments and ablations, statistical analysis | Results |
| 19 | Thin API and UI, demonstration scenarios | Prototype |
| 20 | Final report and paper draft | Report, paper |

**Decision gates**

- **End of week 3:** confirm at least 25 usable clauses, at least 5 reliable amendment/version chains, and enough clauses to populate minimal-pair and incomplete-profile cases. If not, reduce temporal/change claims and narrow the research question before further implementation. Decide whether EPF/ETF is included.
- **End of week 9:** if extraction agreement with gold rules is too low to support deterministic execution, narrow the rule vocabulary and report extraction difficulty as a finding rather than expanding prompts/models indefinitely.

## 12. Technology stack

| Layer | Choice | Reason |
| --- | --- | --- |
| Language | Python | NLP ecosystem, testing, research speed |
| Document processing | PyMuPDF, pdfplumber, OCR where needed | Compare extraction methods on real gazettes |
| Database | PostgreSQL with pgvector | One system for structured data and vectors |
| Lexical search | BM25 (Postgres full-text or a BM25 library) | Baseline and hybrid component |
| Embeddings and reranker | sentence-transformers or API models, chosen by a small retrieval pilot | Selected on measured retrieval quality, cost and reproducibility; frozen before final test |
| LLM | One primary model, same across all systems; structured-output mode | Fair comparison, schema-constrained extraction |
| Rule engine | Pure Python, typed, three-valued logic | Deterministic, testable, auditable |
| Backend | FastAPI | Clean separation of research logic and UI |
| Frontend | React + TypeScript (thin) | Visualize report, evidence and counterfactuals |
| Testing | pytest | Engine logic, extraction validation, metrics |
| DevOps | Git, Docker, GitHub Actions | Reproducibility |

Not used initially: knowledge graph, agent frameworks, multiple LLMs, microservices, dedicated vector database.

## 13. Feasibility

| Dimension | Assessment | Note |
| --- | --- | --- |
| Technical | High | Mature components; no model training |
| Data | Medium | Risk is real conditional clauses and benchmark quality, not volume |
| Research | Medium–High | Clear baselines, ablations and metrics, but the project combines rule extraction, temporal modelling, abstention and benchmark construction; feasibility depends on restricting the rule vocabulary and regulatory domains |
| Computational | High | Small corpus, API or small local models |
| Financial | High | Costs limited to LLM API calls and hosting; control with caching and batching |
| Time | Medium | Achievable in about 20 weeks only with the reduced corpus/benchmark and strict feature prioritisation |
| Ethical and legal | High with safeguards | Decision support only; sources cited |

## 14. Risk management

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Too few real conditional clauses or amendment chains | High | Week-3 gate; prefer threshold-rich instruments such as prescribed-activity schedules |
| Weak or circular ground truth | Very high | Second annotator, expert review, clause-level held-out test |
| Scanned or trilingual gazettes hard to extract | Medium | Two extraction methods, OCR, manual correction, English-only scope |
| LLM extraction errors | High | Verification pipeline, agreement checks, human review |
| Rule formalizability: provisions with discretionary, ambiguous, cross-referenced or context-dependent language cannot be represented in the initial vocabulary | High | Mark as NON\_COMPILABLE / UNSUPPORTED rather than forcing an executable rule; report their share |
| Long-context baseline outperforms proposed system on accuracy | Medium | Expected possibility; the contribution is consistency, temporal correctness, abstention, impact identification and auditability |
| Novelty overlap with concurrent work (e.g. temporal legal RAG for Sri Lanka) | Medium | Narrow novelty claim; re-check literature before submission |
| Scope growth | Very high | Fixed domains, decision gates |
| Engineering overhead | High | Thin UI, no extra infrastructure |
| Regulations change during the project | Medium | Versioned corpus with snapshots and as-at dates |

## 15. Ethical and legal considerations

- The system is regulatory information and decision support, not legal advice, and shows that clearly in the UI and reports.
- Only official, publicly available sources are used; source versions are preserved and historical versus current instruments are distinguished.
- Uncertainty is stated explicitly (CONDITIONAL statuses, UNSUPPORTED clauses, coverage gaps, unverified rules).
- Human verification remains necessary for real compliance decisions.
- No personal data is used; business profiles in the benchmark are synthetic.

## 16. Limitations

- Limited coverage of regulations and industries.
- The benchmark depends on the small number of real amendments and clauses available.
- Some clauses cannot be safely formalised and are reported as unsupported rather than hidden.
- Interpretation ambiguity in some clauses may require expert judgement, and this is reported.
- Counterfactual explanations cover only numeric, ordinal and explicitly defined categorical conditions.
- English-language documents only.
- Results depend on the chosen LLM; model comparison is future work.

## 17. Success criteria

1. A versioned corpus with page-level provenance exists and is reproducible.
2. Rule extraction accuracy against gold rules, and the effect of verification on correction rate, are measured and reported.
3. The engine handles three-valued logic, the five outcome statuses, temporal validity, minimum missing fields and counterfactuals, with tests.
4. Baselines B0 to B3 and ablations are implemented under identical inputs, with B0 reported as an oracle-context upper bound.
5. The benchmark has reported inter-annotator agreement and an externally reviewed sample.
6. Results with clustered confidence intervals answer RQ1 to RQ5, including if the finding is parity on accuracy with gains elsewhere, or a negative result.
7. Impact and action identification are evaluated against gold annotations.
8. Another developer can reproduce the experiments from the repository.

## 18. Future work

Sinhala and Tamil support, additional industries, continuous gazette monitoring, regulation-to-regulation dependency analysis, knowledge-graph evaluation, compliance calendars, model comparison, and expert-in-the-loop rule authoring.

## 19. Final development freeze

This version is the development baseline. No new research capability should be added after implementation begins unless it is required to answer RQ1-RQ5 or to repair a validity/reproducibility problem.

**Frozen core:** selected official corpus; typed business profile; bounded typed rule vocabulary; provenance; deterministic applicability engine; B0-B3 baselines; proposed compile-verify-execute pipeline; clause-level benchmark split; reliable temporal cases; incomplete-profile abstention; bounded impact/action mapping; evidence checks; clustered statistical evaluation.

**Deferred:** knowledge graphs, agentic workflows, multiple-LLM ensembles, multilingual support, broad tax/local-authority coverage, continuous monitoring, sophisticated counterfactual search, and production-scale deployment.

**Minimum viable research result:** even if the full UI is incomplete, the project is successful if the reproducible offline experiment answers RQ1-RQ5 with the frozen benchmark and produces auditable evidence traces.

## 19. References and source list (to be completed)

**Official sources to cite after verification:** FCAU food regulation catalogue and domestic control process; Ministry of Industry industry-registration requirements; Central Environmental Authority Environmental Protection Licence framework and prescribed-activity schedule; relevant EPF/ETF instruments; Gazette of Sri Lanka issues for each instrument and amendment used. Record exact titles, gazette numbers, dates and retrieval dates.

**Literature to locate, read and verify before citing (do not cite from this list unread):**

- Apofasi: a neuro-symbolic temporal RAG framework for evolving mixed legal systems (2026, IEEE; reported to cover Sri Lankan legal materials).
- Temporal misgrounding in legal RAG: versioned-corpus benchmark for French tax law (2026).
- Legal RAG Bench: end-to-end benchmark for legal RAG (2026); Benchmarking legal RAG: AI statutory surveys (2026).
- Umar et al. (2025), regulatory compliance retrieval, reranking and answer generation (RegNLP workshop).
- Gokhan and Briscoe (2025), learning-to-rank for multi-passage regulatory RAG (ObliQA-MP).
- Rules-as-code: OpenFisca documentation; Catala language documentation; literature on rules-as-code and LLMs.
- Trautmann et al. (2024), groundedness of legal QA systems; Filice et al. (2025), generate-but-verify faithfulness in RAG; Reuter et al. (2025), reliable retrieval for large legal datasets.
- Statute-centric legal QA with structure-aware retrieval and safe abstention (2026).
- SME regulatory-burden sources for Sri Lanka.

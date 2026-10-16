# RegImpact-SL --- Implementation Alignment & Change Plan

**Version:** 1.0\
**Status:** Proposed implementation baseline\
**Parent specification:** `RegImpact-SL_Project_Proposal_v4_FINAL.md`\
**Purpose:** Convert the Phase A repository audit into a controlled
implementation plan aligned with the v4 proposal.

## 1. Executive decision

The audit identifies RegImpact-SL as a functional deterministic-engine
and UI prototype, but not yet a complete end-to-end regulatory
intelligence system or research-ready experimental implementation.

Preserve the existing Pydantic models, deterministic applicability
engine, impact/action mapper, rule verifier, version patcher, evidence
checker, compiler/explanation interfaces, FastAPI API, Next.js UI and
passing tests. Strengthen or change them only where the audit identifies
a specific gap.

The critical missing path is:

**authoritative source document → extracted, traceable clause →
candidate rule → verification and review → persistent approved rule →
real retrieval → deterministic evaluation → auditable report →
reproducible benchmark result.**

This document supplements the v4 proposal. It does not silently change
the research questions, hypotheses, contribution claims or project
scope.

### Audit findings used as the baseline

The supplied audit reports that: 1. PDF ingestion, page provenance and
document hashing are missing. 2. The API uses an in-memory repository
seeded with two hard-coded rules; persistent regulatory storage is
missing. 3. A concrete live LLM provider adapter is missing; tests use
mocks and explanations can fall back to deterministic templates. 4.
B0--B3 are stubs and do not perform genuine retrieval/LLM inference. 5.
No real corpus or held-out benchmark dataset exists on disk; evaluation
tests use a small synthetic fixture. 6. Cross-extraction agreement and a
human-review queue are missing. 7. `CONDITIONAL_RULE` is absent from the
outcome enum despite being specified in v4. 8. Some metrics and
clustered statistical procedures remain unimplemented. 9. The audit
reports 82 passing backend tests and a successful frontend production
build. These must be rerun after changes.

These are findings reported by the audit, not a substitute for verifying
the repository after implementation.

## 2. Non-negotiable design principles

1.  **Official sources are authoritative.** Never invent a statute,
    quotation, effective date, amendment, threshold, exemption or legal
    interpretation.
2.  **Retrieval must be real.** A baseline must retrieve actual corpus
    text and pass the evidence to its configured model. A class name or
    stub does not count.
3.  **LLMs propose; verification and review gate; deterministic code
    executes.** Generated prose must not override structured rule
    evaluation.
4.  **Quote grounding is not semantic correctness.** A correctly quoted
    number can still be associated with the wrong operator, condition,
    unit, exception or legal scope. Gold rules require manual review.
5.  **Every output is traceable.** Results must link to an approved
    rule, exact clause version, source document, page/quotation and
    source metadata.
6.  **Unknown is not false.** Missing profile information must remain
    unknown and trigger the specified abstention/clarification
    behaviour.
7.  **Unresolved legal history stays unresolved.** Do not fabricate
    amendment reconstructions.
8.  **Research metrics require genuine experiments.** Passing unit tests
    or mock baselines cannot support performance claims.
9.  **Avoid unnecessary complexity.** No knowledge graph, agents,
    multilingual scope, live web scraping per user request or
    production-scale infrastructure.
10. **Do not rewrite working code without evidence.** Keep current
    interfaces unless an evidenced defect or required integration
    demands a change.
11. **Keep secrets out of source control.** Use environment variables;
    never log credentials.
12. **Human review is a safety gate.** Disputed or semantically
    uncertain rules must not silently become executable.

## 3. Target architecture

### 3.1 Offline ingestion and rule preparation

`Official source PDF / authoritative source` → immutable source snapshot
and metadata\
→ text extraction with page provenance\
→ clause segmentation and source records\
→ candidate rule compilation\
→ schema, quotation and literal checks\
→ cross-extraction agreement where required\
→ human review of disagreements and gold rules\
→ persistent approved rule/version store\
→ retrieval indexes.

Ingestion and compilation are update workflows. They do not need to run
from scratch for every end-user analysis.

### 3.2 Online analysis

`Business profile + regulatory change/query + as-at date` → retrieve
relevant clauses and approved rules\
→ identify uncompiled or unsupported coverage gaps\
→ deterministic evaluation of approved rules\
→ bounded impact/action mapping\
→ constrained explanation from structured facts\
→ evidence/claim validation\
→ auditable report through FastAPI and the UI.

A retrieved passage is not automatically a verified executable rule. If
a relevant clause has no approved rule, disclose the coverage gap or
return `UNSUPPORTED` as appropriate.

### 3.3 Separate evaluation pipeline

The benchmark runner executes B0--B3, System P and required ablations
using a common scenario schema, frozen configurations and recorded
outputs. Evaluation is separate from the user-facing application.

## 4. Required architecture corrections

### 4.1 Correct B0's definition

The v4 proposal defines **B0 as a long-context LLM supplied with
oracle-selected relevant regulatory context**. The audit found the
existing `OracleBaseline` is a stub returning a default outcome.

Implement B0 as specified: - Supply the relevant gold/oracle-selected
source context and the same profile/date as other systems. - Invoke the
configured LLM and parse its answer into the common result schema. -
Treat B0 as an upper-bound context baseline, not a retrieval baseline. -
If a rule-based gold oracle is useful for engine validation, name it
separately (e.g. `GoldRuleOracle`); do not label it B0.

### 4.2 Add `CONDITIONAL_RULE`

Add `CONDITIONAL_RULE` to the domain model and handle it in the
engine/API/UI/benchmark/metrics with tests. Preserve the five v4
outcomes: - `APPLICABLE` - `NOT_APPLICABLE` -
`CONDITIONAL_MISSING_DATA` - `CONDITIONAL_RULE` - `UNSUPPORTED`

Do not conflate `CONDITIONAL_RULE` with missing profile data.
`CONDITIONAL_MISSING_DATA` is the primary abstention class for RQ3.

### 4.3 Separate three kinds of correctness

-   **Grounding:** Is the quotation and source/page reference real?
-   **Semantic rule correctness:** Does the rule accurately represent
    conditions, operators, units, exceptions, obligation and validity?
-   **Execution correctness:** Does the engine evaluate the verified
    rule correctly for the profile/date?

Automated checks help but cannot replace semantic review. Gold rules
must be manually verified; a representative subset should receive
independent/external expert review as v4 specifies.

### 4.4 Persistent storage

The v4 target is PostgreSQL plus `pgvector`. Use PostgreSQL for
persistent records and `pgvector` for dense embeddings. Store source PDF
snapshots in a controlled local/object file store; the database should
retain stable identifiers, hashes and paths/URIs. Do not introduce a
separate vector database.

### 4.5 Prevent benchmark leakage

Split by **source clause**, not scenario row. All minimal-pair, temporal
and incomplete-profile variants derived from one clause must remain in
the same partition. Freeze the test set before final prompt/model
tuning.

## 5. Prioritised implementation roadmap

The sequence below includes dependencies and acceptance gates. Source
verification and benchmark planning should begin early alongside
ingestion.

### Milestone 0 --- Preserve baseline

**Purpose:** Make changes auditable and avoid regressions.

Tasks: - Create a Git commit/tag for the current audited state. - Record
Python, Node, dependency and database versions. - Rerun backend tests
and frontend production build; save actual outputs. - Inspect dependency
compatibility before upgrading packages. - Add `.env.example` with
placeholders only. - Ensure credentials and local source snapshots are
not accidentally committed.

**Acceptance criteria:** baseline commit exists; commands/results are
recorded; no feature code changes; environment problems are documented
rather than silently worked around.

### Milestone 1 --- Official document ingestion and persistent source store

**Priority:** Critical. **Dependency:** Milestone 0.

Tasks: 1. Define typed records for instruments/documents, source
snapshots, clause versions, rules and review state. 2. Add PostgreSQL
configuration and migrations. 3. Implement an ingestion command/service
for explicitly supplied official PDFs. Do not indiscriminately scrape
websites. 4. Record source URL, authority, title, instrument/gazette
identifier where available, verified publication date where available,
retrieval timestamp, SHA-256 hash, file reference, extraction status and
extraction-tool version. 5. Extract text with PyMuPDF or pdfplumber; add
OCR only for documents that demonstrably need it. 6. Preserve page
number and stable character offsets or equivalent locators. 7. Segment
clauses conservatively and retain raw page text for auditing. 8. Store
source and clause records persistently. 9. Add an inspection report for
metadata, page count, extraction warnings and clause counts. 10. Keep
seed rules as clearly labelled demo/test fixtures; do not treat them as
verified corpus records.

**Acceptance criteria:** - At least two selected authoritative documents
are ingested with verified metadata. - Re-ingestion does not create
uncontrolled duplicates; identical bytes are identified by hash. - Each
selected clause traces to a source document and page/quotation. -
Extraction failures and scanned pages are explicitly reported. - Records
survive backend restart. - The API no longer relies exclusively on
`seed_repository()`. - Tests cover hashing, duplicate handling,
provenance, extraction errors and persistence.

Never invent source URLs or metadata to meet the target. Unverified
facts must be marked unresolved.

### Milestone 2 --- Real LLM adapter, rule compilation and review workflow

**Priority:** Critical. **Dependency:** Milestone 1.

Tasks: 1. Implement one concrete provider adapter behind the existing
`LLMClient` interface. Choose a provider after checking available
credentials, cost and structured-output support. 2. Read credentials
from environment variables; never hard-code them. 3. Add timeouts,
bounded retries, explicit error types and safe malformed-response
handling. 4. Preserve relevant model/config metadata for reproducibility
without logging secrets. 5. Run the compiler/verifier loop on real
extracted clauses. 6. Add cross-extraction agreement using a second
prompt/configuration. A second model is optional; a distinct extraction
pass/configuration is required by v4. 7. Add human-review states for
disagreements, low-confidence cases and semantic adjudication. 8. Record
reviewer role/identifier, timestamp, decision and rationale. 9. Add
`CONDITIONAL_RULE` with serialization and downstream tests. 10. Keep
non-compilable clauses explicit; do not force ambiguous clauses into
executable rules. 11. Use manually reviewed rules as gold rules, not the
model's own output.

**Acceptance criteria:** - A configured real provider compiles a
selected clause into candidate schema-valid JSON. - Verification rejects
malformed or ungrounded outputs. - Failed attempts can be corrected
within bounded retries; persistent failure ends in safe
rejection/non-compilable/review state. - Disagreement or unresolved
semantics prevents automatic approval. - Approved rules preserve
source/page/quote references. - Unit tests remain offline with mocks;
opt-in integration tests exercise the real provider when configured. -
API credentials are not required for ordinary unit tests.

### Milestone 3 --- Real lexical, dense and hybrid retrieval

**Priority:** Critical. The corpus schema must be stable first.

Tasks: 1. Implement BM25 over actual extracted clause/passage text. 2.
Implement dense embeddings and vector similarity search using the
selected embedding model and PostgreSQL `pgvector`. 3. Implement hybrid
fusion and the planned reranker. If the fusion method is not fixed in
v4, document a rank-fusion method such as reciprocal rank fusion. 4. Add
appropriate metadata filters for instrument, clause version and
temporal/source metadata. 5. Return ranked results with passage text,
source identity, page/locator, version and retrieval score. 6. Record
index/model versions and retrieval configuration. 7. Detect relevant
passages without approved compiled rules and expose them as coverage
gaps. 8. Add indexing/re-indexing commands and tests for empty corpus,
duplicates, metadata filters and stable references.

**Acceptance criteria:** - Queries return ranked real passages; no
hard-coded result is substituted. - BM25 and dense retrieval are
separately callable and testable. - Hybrid retrieval actually combines
rankings and applies the configured reranker if included in B3. -
Evidence is inspectable and traceable. - Re-indexing updates the index
without losing source identity. - A test demonstrates
query-to-retrieved-passage flow.

### Milestone 4 --- Genuine baselines and common result schema

**Priority:** Critical. **Dependencies:** Milestone 3 and one configured
LLM provider.

Implement: - **B0:** long-context LLM with oracle-selected relevant
context. - **B1:** BM25 + LLM. - **B2:** dense retrieval + LLM. -
**B3:** hybrid retrieval + reranker + LLM. - **P:** candidate
clause/approved-rule retrieval, verified deterministic execution,
bounded impact/action mapping, constrained explanation and evidence
checking. - **Gold rule/engine oracle:** optional separate diagnostic
baseline, never a replacement for B0.

Fairness controls: - Identical profile, date, scenario and target output
schema. - Same primary LLM and generation settings where technically
applicable. - Fixed prompts and temperature 0 where supported. - Same
corpus and source versions. - Document how oracle context is selected
for B0. - Record model/version, embedding model, reranker, top-k,
prompts, token use, latency, cost and errors. - Failed
retrieval/provider calls are recorded as failures, not successful
predictions.

**Acceptance criteria:** - Every baseline runs a real scenario from
input to output. - Outputs are parsed into the common result schema. -
Each baseline records its evidence and failure reason. - No baseline is
counted as successful when retrieval/provider execution failed. - Tests
demonstrate distinct retrieval paths.

### Milestone 5 --- Dataset A and Dataset B

**Priority:** Critical for research validity. Begin source curation
during Milestone 1; freeze final scenarios after the schema/pipeline
stabilises.

**Dataset A --- corpus** - Target 20--30 authoritative instruments,
prioritising 25--40 usable clauses and at least five reliable
amendment/version chains, consistent with v4. - Prioritise food
control/labelling, manufacturing/industry registration and environmental
licensing. - Include EPF/ETF only if the v4 Week 3 gate shows enough
relevant conditional/versioned clauses. - Store source snapshots,
hashes, metadata, extraction status and version relations. - Track
compilable, non-compilable, manually verified and unresolved clause
states.

**Dataset B --- benchmark** - Target 100--150 scenarios; minimum 100
across at least 25 distinct clauses, subject to source feasibility. -
Include direct cases, minimal pairs, invariance pairs, incomplete
profiles, temporal/change cases and impact/action labels. - Each
scenario references source clause/version IDs and includes expected
output plus rationale. - Business profiles may be synthetic; underlying
legal rules must be real and verified. - Double-annotate independently,
adjudicate disagreements, report agreement and obtain external expert
review of a representative sample as v4 states. - Split by source
clause; keep all variants of a clause in one partition. - Freeze the
held-out test set before final tuning. - Store versioned JSON/JSONL data
under `backend/data/`, with annotation metadata.

**Acceptance criteria:** - No unverified legal detail in gold test
labels. - Every gold rule/scenario traces to source and reviewer
decision. - Counts are reported per clause and scenario type. - Test
clauses are disjoint from development clauses. - Ambiguous source
evidence is marked unresolved rather than guessed.

### Milestone 6 --- Metrics and reproducible experiments

**Priority:** Critical. **Dependencies:** Milestones 4 and 5.

Implement or verify: - Applicability precision, recall, F1 and
accuracy. - Minimal-pair flip consistency and invariance accuracy. -
Temporal validity accuracy on verified historical cases. - Abstention
precision/recall/F1 and missing-field correctness. - Impact/action F1
for categories represented in the benchmark. - Rule extraction
agreement, correction rate, rejection/non-compilable classification and
human review effort. - Evidence/citation/quote-span correctness and
unsupported-claim rate. - Cost and latency where reliably measured.

Statistics: - Clause-level cluster bootstrap confidence intervals to
account for related scenarios from each clause. - Paired comparisons
where systems share scenarios. - Report effect sizes and uncertainty,
not only point estimates. - Keep test set frozen; test-driven tuning
invalidates it as a final held-out set. - Attribute failures by stage:
ingestion, retrieval, extraction, verification, execution, explanation
or evidence validation.

Required v4 ablations: - Without verification. - Without temporal
module. - Without abstention/minimum-missing-field handling. - Manual
gold rules instead of LLM-compiled rules.

**Acceptance criteria:** one documented command runs the frozen
benchmark and writes raw machine-readable results and a summary report;
code/config/dataset/model versions are recorded; results trace to
scenario IDs and clauses; failures are not silently dropped; report
includes per-clause/per-type metrics and uncertainty.

### Milestone 7 --- End-to-end API/UI integration

**Priority:** After core pipeline functionality. Evaluation dashboard
depends on Milestone 6.

Tasks: - Replace the in-memory-only regulatory path with persistent
storage. - Support selection of a regulatory change/query and as-at date
where required by v4. - Display retrieved evidence, approved
rule/version status and source metadata. - Distinguish verified rules,
unresolved clauses, missing profile data and unsupported analysis. -
Display all five outcome states consistently. - Preserve the evidence
viewer and condition trace. - Make fallback explanations visible; do not
label them as LLM-generated. - Add evaluation dashboard only after
genuine benchmark results exist.

**Acceptance criteria:** the complete acceptance scenario below works;
no LLM output is labelled verified merely because it was generated; each
legal claim has an inspectable source trail; UI work does not delay the
core pipeline.

## 6. First end-to-end acceptance scenario

The first integrated milestone is deliberately small; it is not the full
corpus or benchmark.

1.  Ingest two verified authoritative documents.
2.  Extract at least one clause from each with source/page provenance.
3.  Compile one candidate rule using the configured real LLM.
4.  Verify it and route uncertain semantics to human review.
5.  Store one approved rule persistently.
6.  Restart the backend and prove the document, clause and rule remain
    available.
7.  Run BM25 and dense retrieval against the stored corpus and inspect
    results.
8.  Retrieve an approved rule for a relevant business scenario.
9.  Evaluate a complete and an incomplete business profile
    deterministically.
10. Display outcome and source quotation in API/UI.
11. Cover the path with integration tests using deterministic test
    doubles for external services, plus a separately marked live
    integration test.

This proves the data-to-analysis path exists. It does **not** prove
research performance; that requires Milestones 5 and 6.

## 7. Scope control and non-goals

Do not implement unless a documented v4 requirement cannot be met
otherwise: - Knowledge graph/GraphRAG; agentic workflows; multi-provider
orchestration. - Sinhala/Tamil processing; live internet scraping during
each analysis request. - Automated legal filings or legal advice. -
Every Sri Lankan regulatory domain. - Production-scale authentication,
multi-tenancy or deployment infrastructure. - UI animations/cosmetic
redesign. - Arbitrary counterfactuals for categorical values without
defensible ordering. - Automatic amendment reconstruction when source
evidence is ambiguous.

**Cut order if time is constrained:** UI richness → broad corpus
coverage → optional secondary domain → advanced counterfactual breadth →
optional reranker complexity.

**Protect:** verified gold rules, provenance, real B0--B3, deterministic
engine correctness, clause-disjoint benchmark, abstention, evidence
correctness and reproducible experiments.

## 8. Risk gates and stop conditions

### Data feasibility gate (v4 Week 3)

If enough usable clauses and at least five reliable amendment/version
chains cannot be found: - Narrow temporal/change claims. - Prioritise
high-quality core-domain clauses. - Record effects on RQ2. - Never
fabricate amendment chains to meet a target.

### Extraction quality gate

If LLM extraction often encodes wrong operators, conditions, units or
exceptions: - Narrow the rule vocabulary. - Increase manual review. -
Mark unsupported clauses non-compilable. - Do not respond first by
adding models/orchestration.

### Retrieval quality gate

If the corpus is too small for meaningful embedding/reranking
comparison: - Implement the methods correctly and report the
small-domain scope. - Avoid broad claims about general RAG superiority.

### Provider/cost gate

If credentials, rate limits or cost prevent repeatable experiments: -
Keep unit tests offline with mocks. - Make live integration tests
opt-in. - Record provider choice and cost before expanding calls. -
Never report mocked runs as real-model results.

### Provenance gate

If a source, clause, commencement date or amendment relation cannot be
verified: - Exclude it from gold test labels. - Mark it unresolved with
a reason. - Do not infer a legal fact from a secondary summary alone.

## 9. Definition of done for the research implementation

-   [ ] Official source snapshots and metadata are stored/versioned.
-   [ ] Clauses retain exact source/page provenance.
-   [ ] Real-provider rule compilation works in the configured
    integration environment.
-   [ ] Cross-extraction disagreement and human review are implemented.
-   [ ] Only approved/appropriate rules enter deterministic execution.
-   [ ] Persistent storage survives backend restarts.
-   [ ] BM25, dense and hybrid retrieval work on the real corpus.
-   [ ] B0 is the specified oracle-context long-context LLM baseline.
-   [ ] B1--B3 are genuine retrieval-plus-LLM baselines.
-   [ ] System P is integrated end to end and exposes coverage gaps.
-   [ ] `CONDITIONAL_RULE` works across models, engine, API, UI and
    metrics.
-   [ ] Dataset A and B are source-grounded and versioned.
-   [ ] Gold labels are reviewed; agreement/adjudication are recorded.
-   [ ] Test data is clause-disjoint and frozen before final tuning.
-   [ ] Required metrics, ablations and clustered uncertainty estimates
    exist.
-   [ ] Raw experiments/configuration are reproducible.
-   [ ] End-to-end acceptance scenario passes.
-   [ ] Tests and frontend build pass after integration; failures are
    documented.
-   [ ] Claims are limited to what experiments demonstrate.

## 10. Coding-agent workflow and constraints

Use this plan with `RegImpact-SL_Project_Proposal_v4_FINAL.md` and the
Phase A audit report.

For each milestone: 1. Read the relevant proposal section, audit finding
and current source. 2. State scope and files expected to change before
coding. 3. Implement only the current milestone. 4. Add/update tests for
new behaviour and failure cases. 5. Run relevant tests and report exact
commands/results. 6. Update a progress log with completed criteria,
limitations and deviations. 7. Do not mark criteria complete without
evidence. 8. Stop and request approval before beginning the next
milestone.

Agent restrictions: - No unrelated refactors or weakened/deleted
tests. - No invented legal data, labels or experiment results. - No
silent changes to research questions or baseline definitions. - No broad
dependency installation without justification. - No credentials or
sensitive local paths in source control. - Do not implement all
milestones in one run. - Record uncertain legal/source matters for human
review.

Required milestone report: 1. Implemented files/functions. 2. Acceptance
criteria: pass/fail/not verified, with evidence. 3. Test commands and
actual results. 4. Data provenance, where applicable. 5.
Limitations/risks and research impact. 6. Deviations from v4 and
rationale. 7. Proposed next milestone; wait for approval before
implementing.

## 11. Immediate next task for the coding agent

**Implement Milestone 0, then propose Milestone 1; do not implement
later milestones in the same run.**

After baseline preservation, implement **Milestone 1 only: official
document ingestion and persistent source storage**. Before coding,
inspect existing dependencies, current domain schemas, repository
interfaces and the local PostgreSQL setup. Propose the smallest
schema/migration that satisfies Milestone 1. Do not implement live LLM
integration, retrieval baselines or the benchmark runner in that task.

Milestone 1 is complete only when real source documents and extracted
clauses persist across backend restarts with source/page provenance, and
automated tests verify those properties.

## 12. Governance

This is an implementation alignment document; v4 remains the parent
research specification. Any proposed change to scope, dataset targets,
hypotheses, research questions, baseline definitions or primary
contribution must be documented as a proposed deviation and approved
before implementation.

**Current state:** Phase A audit reported complete.\
**Next authorised activity:** Milestone 0 baseline preservation,
followed by Milestone 1 after scope confirmation.\
**Not authorised:** all-at-once implementation, broad refactoring, new
research claims or declaring the project research-ready before the
acceptance criteria are met.

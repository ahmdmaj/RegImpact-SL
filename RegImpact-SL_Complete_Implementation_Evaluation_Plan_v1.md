# RegImpact-SL — Complete Implementation Evaluation & Verification Plan
**Document type:** Audit and acceptance plan  
**Version:** 1.0  
**Date:** 22 October 2026  
**Controlling specifications:** RegImpact-SL Proposal v4 — Development Freeze; RegImpact-SL Implementation Alignment Change Plan v1.0

## 1. Purpose

This plan determines what has actually been implemented, whether it works correctly, whether it aligns with the approved research design, and what remains before it can be considered research-ready. This is an evaluation plan, not permission to implement new features. Inspect and collect evidence first; propose fixes only after findings are documented.

**Core question:** Can RegImpact-SL take an authoritative regulatory source and a business profile, identify relevant regulatory rules, determine applicability using the intended verified/deterministic process, produce a traceable impact/action report, handle missing or uncertain information safely, and support reproducible comparisons against properly implemented baselines?

A feature is not complete merely because code exists or a test passes. Distinguish:
- **Implemented:** code/configuration exists.
- **Tested:** an executable test covers it.
- **Verified:** results and failure behaviour meet explicit acceptance criteria.
- **Research-valid:** implementation and data support the intended claim.
- **Complete:** all required acceptance criteria are met and evidence is recorded.

## 2. Audit rules

1. Audit before editing; do not modify application code during initial inspection.
2. Treat the current repository as the source of truth; the previous audit is historical context.
3. Tie every conclusion to evidence: command, output, file/function, test, dataset statistic, log, or reproducible example.
4. Separate code correctness from research validity.
5. Never invent legal facts. Gold rules need authoritative provenance, exact clause/quote, location, relevant dates, and review status.
6. Record Git commit, branch, dirty working tree, environment, and baseline test results before changes.
7. Do not expand scope into knowledge graphs, agents, multilingual support, live scraping on each query, extra providers, or cosmetic UI work.
8. Do not weaken tests to make the build green.
9. Separate live integrations from mocks. A mock does not prove a real integration works.
10. Use synthetic fixtures for logic edge cases and verified legal data for legal correctness.
11. Never expose API keys, tokens, or private environment values in reports.
12. Status values must be **PASS, PARTIAL, FAIL, BLOCKED, or NOT TESTED**.

## 3. Required audit outputs

1. Repository inventory: modules, routes, data files, configuration, integrations.
2. Test/build report: exact commands, exit codes, pass/fail/skip counts, errors.
3. Requirement traceability matrix.
4. End-to-end test report.
5. Source/provenance audit: source inventory, hashes, extraction coverage, rule-review status.
6. Benchmark validity report: gold labels, split integrity, baseline fidelity, metric correctness.
7. Defect register with severity, evidence, reproduction steps, and recommended correction.
8. Research-claim readiness assessment.
9. Prioritised remediation plan, written only after the audit.
10. Final milestone decision: research-ready, restricted, remediation required, or blocked.

## 4. Stage 0 — Freeze and establish the baseline

Record the current branch, commit hash, uncommitted/untracked files, project structure, runtime/package versions, startup/test commands, database configuration, data files, and required environment-variable **names only**. Record README/setup gaps.

Suggested commands, adapted to the repository:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git log -5 --oneline
python --version
node --version
npm --version
```

Run documented backend tests, frontend tests/build, lint/type checks, dataset/schema validation, and a safe evaluation smoke test where available. Record exact command, exit code, totals, skipped tests, warnings, and elapsed time. Do not merely report “tests passed.”

**Stage acceptance:** repository state is identified; baseline results and blockers are recorded; existing failures are separated from future regressions; no application files were modified during baseline collection.

## 5. Stage 1 — Requirement traceability and architecture alignment

For each requirement, record its implementation path/function/endpoint, automated test, manual/integration evidence, status, severity, and next action.

| ID | Requirement | Required evidence |
|---|---|---|
| R01 | Authoritative source ingestion | Real official document ingested with stable identity and traceable text. |
| R02 | Provenance | Instrument, clause/section, page/location, source URL/file, document hash, version/date survive the pipeline. |
| R03 | Candidate-rule compilation | Configured real LLM or documented alternative creates typed rule from a real clause. |
| R04 | Verification/review | Structural and grounding checks run; semantic approval is not inferred from schema validity. |
| R05 | Persistence | Approved rules survive restart and remain linked to sources. |
| R06 | Real retrieval | BM25/keyword, dense, and hybrid methods retrieve from the real corpus, not stubs or hard-coded examples. |
| R07 | Profile reasoning | Business facts are evaluated against relevant conditions by the intended deterministic engine. |
| R08 | Missing data | Unknown values are not silently converted to false, true, zero, or invented facts. |
| R09 | Outcome taxonomy | `APPLICABLE`, `NOT_APPLICABLE`, `CONDITIONAL_MISSING_DATA`, `CONDITIONAL_RULE`, and `UNSUPPORTED` are consistently handled where required. |
| R10 | Temporal/version logic | Validity dates and version relationships are handled correctly; unresolved relationships are not fabricated. |
| R11 | Impact/action | Evaluated obligations map to bounded, documented categories represented in the benchmark. |
| R12 | Evidence-backed report | Conclusions link to evidence and distinguish source facts, interpretation, missing information, and uncertainty. |
| R13 | Baselines | B0–B3 implement the approved definitions and execute real methods. |
| R14 | Benchmark | Gold cases are reviewed, traceable, sufficiently diverse, and split without source-clause leakage. |
| R15 | Metrics | Metrics compare predictions to frozen gold labels and have tested implementations. |
| R16 | Reproducibility | Dataset/split/config/model/prompt/index versions and run outputs are recorded. |
| R17 | End-to-end integration | API/UI complete flow works, including evidence and failure states. |
| R18 | Safe failures | Invalid, unsupported, ambiguous, unavailable, or unverified inputs produce clear errors/abstentions rather than confident invention. |

Architecture questions:
- Is ingestion an offline/update workflow rather than scraping on every user query?
- Is the LLM limited to extraction/explanation while applicability and temporal logic are deterministic?
- Are source text, compiled candidate rules, approved rules, and gold labels separate?
- Are real persistent storage and retrieval components used, or are seed data/stubs still present?
- Are baselines independent, or do they reuse proposed-method results?
- Does the UI show live backend results rather than static/demo reports?
- Are errors and uncertainty consistent from domain model through engine, API, UI, and metrics?

## 6. Stage 2 — Source corpus and ingestion audit

### Source register
For each document record stable source ID, instrument title, issuing authority, official URL/location, local filename/format, publication date, established effective date, amendment/repeal relationship, SHA-256 hash, access date, extraction method/tool version, extraction status, review status, reviewer, and OCR/scan/version limitations.

### Ingestion tests
1. Ingest a real official source.
2. Verify the stored hash against the original file.
3. Verify page count and extracted-page coverage.
4. Compare extracted text against original pages, including tables, schedules, footnotes, and scans where applicable.
5. Check page/section/clause boundaries.
6. Re-ingest the same file and check duplicate/idempotent behaviour.
7. Ingest a changed version and verify history is preserved rather than silently overwritten.
8. Confirm extraction failures/partial documents are visible and not treated as valid complete sources.
9. Trace each compiled clause to its exact source and location.

**Acceptance:** every gold rule has authoritative provenance; version identity is clear or marked unresolved; no placeholder/guessed clause or fabricated date is gold truth; limitations are recorded; duplicate and changed-file behaviour is tested.

### Corpus feasibility gate
Compare with the frozen proposal targets: approximately 20–30 instruments, at least 25–40 usable verified clauses, and at least five reliable amendment/version chains if temporal-change claims remain central. Include enough conditional, numeric/threshold, exception, temporal, and incomplete-profile cases. These are feasibility targets, not permission to inflate counts with duplicates. If amendment evidence is insufficient, narrow temporal claims rather than fabricate relationships.

## 7. Stage 3 — Rule compilation, verification, and review

Evaluate four separate layers:

**A. Structural validation:** required fields, types/enums, valid condition/operator structure, explicit unsupported constructs, useful rejection errors.

**B. Evidence/grounding:** quoted text exists in the cited source; clause/page pointers are correct; numbers, units, dates, thresholds, exceptions, and entities match. A matching quote does not prove the interpretation is correct.

**C. Semantic/legal review:** rule meaning, scope, applicability, exceptions, obligations, and dates accurately represent the provision; material conditions are not omitted; the rule does not overstate the source; reviewer decision/rationale/corrections are stored.

**D. Execution validation:** approved rule yields expected outcomes on known profiles; missing values and boundaries behave as specified; result can be explained from conditions and evidence.

Use a fixed compilation set covering simple clauses, multiple conditions, thresholds/units, exceptions, effective dates/amendments, tables/schedules, non-compilable clauses, and ambiguous text. Capture source span, raw model output, parsed rule, verifier output, human review, corrections, and final approved version.

Required failure tests: malformed JSON; missing fields; invalid operators; quote not found; wrong threshold/unit; omitted exception; fabricated date/clause; structurally valid but semantically wrong rule; non-compilable clause wrongly accepted; provider timeout/rate limit/unavailable credentials; retry exhaustion and duplicate side effects.

**Acceptance:** invalid candidates can be rejected/quarantined; unapproved rules cannot enter production analysis; review history is retained. Automated quote/grounding checks do not count as semantic/legal review.

## 8. Stage 4 — Persistence and integrity

Verify the actual approved storage implementation:
1. Approved rules survive backend restart.
2. Source documents/versions, extracted clauses, candidate rules, approved rules, and review records are distinguishable.
3. Relationships prevent orphaned records where applicable.
4. Idempotency/constraints prevent accidental duplicates.
5. Failed transactions do not leave partially approved records.
6. Rule updates preserve history needed to reproduce experiments.
7. Dataset exports are deterministic and versioned.
8. Database failure is explicit and safe.
9. Clean setup/migrations are documented and runnable.
10. Secrets are not committed or printed.

If persistence is not implemented, mark the requirement PARTIAL/FAIL as appropriate; do not describe in-memory storage as durable.

## 9. Stage 5 — Retrieval verification

Test methods independently:
- Keyword/BM25 over the real approved-clause corpus.
- Dense embedding retrieval over that corpus.
- Hybrid retrieval combining lexical and dense candidates; verify a reranker actually runs if claimed.
- Oracle-context condition only as defined for its baseline, not as a substitute for retrieval.

Queries should include exact wording, paraphrases, threshold/unit wording, exceptions/schedules, similar irrelevant clauses, amendment/version questions, no-support queries, and business-profile-specific attributes.

For every run record query ID/text, corpus/index version, method/configuration, returned source/rule IDs and ranks, scores where available, gold relevant IDs, latency, and errors. Where labels permit, calculate Recall@k, Precision@k, MRR and/or nDCG@k, plus no-support behaviour and latency. Verify indexes update when approved rules change; historical/current validity is respected; similarity is not described as legal confidence; empty retrieval does not cause fabricated evidence.

**Acceptance:** results originate from the actual corpus and the method performs the claimed retrieval. Non-empty results alone do not prove retrieval quality.

## 10. Stage 6 — Deterministic applicability and profile reasoning

Test true/false/unknown conditions; AND/OR/NOT; nested paths; missing nested paths; invalid paths/operators/types; empty/malformed groups; numeric boundaries below/equal/above threshold; units; booleans/categories/dates; exceptions; multiple simultaneous rules; conflicts/overlap; unsupported conditions that must not be ignored.

Check all required outcomes distinctly: `APPLICABLE`, `NOT_APPLICABLE`, `CONDITIONAL_MISSING_DATA`, `CONDITIONAL_RULE`, and `UNSUPPORTED`. Do not collapse missing facts, a conditional clause, and a non-compilable rule into generic false.

For each required profile field, remove it and verify no default is invented, the right missing field is identified, and the result changes only when justified after the value is supplied.

### Minimal-pair/metamorphic tests
- Profile just below vs just above threshold.
- Activity category A vs B.
- Required licence present vs absent.
- Date before vs after effective date.
- Known vs missing required fact.
- Same profile with irrelevant attribute changed.

Relevant changes should flip outcomes when logic requires; irrelevant changes should not. Missing data must not become a negative fact. Boundary behaviour must follow explicit comparator semantics.

**Acceptance:** results match hand-calculated expectations and semantics agree across engine, API, UI, and metrics.

## 11. Stage 7 — Temporal/version reasoning

Test not-yet-effective, current, expired/repealed/superseded rules where authoritative evidence exists; amendments changing thresholds/scope/exceptions; old/new versions retained with their own validity intervals; publication date differing from effective date; unknown/ambiguous dates; overlapping/gapped intervals; and unresolved amendment relationships.

Do not infer amendment links from similar wording alone or fabricate validity intervals. Mark unresolved relationships (e.g. `NON_RECONSTRUCTED`) and exclude them from gold temporal claims. Historical queries must use the appropriate version; current queries must not silently apply future/superseded rules. Maintain a human-reviewed timeline for each chain used in temporal evaluation. Measure against reviewed timelines, not model-generated dates.

## 12. Stage 8 — Impact, action, evidence, explanation

Inspect whether impact/action mapping follows evaluated obligations and profile facts, uses only documented finite categories, avoids recommendations broader than the evidence, handles duplicate impacts without losing source obligations, and uses reviewed gold labels for metrics.

For every report verify: correct instrument/clause; exact quote; page/section; source version/effective-date context; distinction between legal text and interpretation; visible uncertainty/missing facts/unsupported clauses/retrieval failure; citations only to sources actually retrieved/evaluated; UI output matches API output.

The explanation LLM must not override deterministic outcomes, invent obligations, turn conditional into definitive results, hide missing data/unresolved time status, or create unsupported citations. Test adversarial instructions embedded in source text and profile fields; treat those texts as data, not trusted instructions.

## 13. Stage 9 — Baseline fidelity

Approved definitions:
- **B0:** long-context LLM with oracle-selected relevant context. This is an oracle-context reasoning comparison, not a normal retrieval baseline.
- **B1:** BM25 + LLM.
- **B2:** dense retrieval + LLM.
- **B3:** hybrid retrieval + reranker + LLM.
- **P:** proposed compile–verify–execute system.

B0 must receive the proper oracle-selected context and must not reuse the proposed deterministic answer. B1–B3 must execute their stated retrieval methods; B3 must actually rerank if claimed. Document prompts, model/provider, top-k, context limits, and settings. No baseline may read gold answers/held-out labels or copy proposed-method outputs. Proposed method must use approved rules and deterministic execution without test labels or unlogged test-specific human correction.

A stub, constant/default answer, reused output, or unexecuted pipeline is NOT a valid baseline. Mark it NOT IMPLEMENTED and exclude it from comparative claims until repaired.

## 14. Stage 10 — Benchmark and gold-label audit

For each dataset version report scenario count; unique instruments/clauses; types (ordinary, conditional, numeric, exception, temporal, minimal pair, incomplete profile, unsupported/non-compilable, no-support); class distributions; missing/ambiguous labels; authoritative-evidence coverage; reviewer status/disagreements.

Each gold case needs stable ID, profile/query, relevant source/clause IDs, expected outcome/reason/conditions, impact/action labels where scored, missing fields/uncertainty, date/version context, source evidence, and reviewer status. A developer-entered expected answer is not gold until checked against authoritative evidence and rule semantics.

Split by source clause or a justified group, not random scenario row alone. Keep minimal pairs/derived variants together; group temporal versions of the same chain unless a justified cross-version generalisation design says otherwise. Tune prompts/indexes without held-out gold labels. Record split seed and exact IDs; freeze the test set before final comparisons.

Check for gold answers in prompts/retrieval metadata/fixtures, benchmark-specific branches, copied baseline outputs, verbatim test examples in prompts, near-duplicate leakage, and unrecorded rule corrections after inspecting test results. If the dataset is small, present a bounded controlled evaluation; do not claim representativeness of all Sri Lankan regulations or SMEs.

## 15. Stage 11 — Metrics and statistical validity

Validate each metric on tiny hand-computed fixtures before full evaluation:
- Applicability precision/recall/F1 and confusion matrix/per-class counts.
- Minimal-pair correct-flip and irrelevant-change invariance rates.
- Temporal correctness on reviewed timelines.
- Abstention/missing-data metrics and minimum-required-field correctness.
- Impact/action per-label and aggregate F1 where justified.
- Compilation field/condition agreement, correction rate, non-compilable classification, reviewer time.
- Evidence source/clause/quote/page/version correctness.
- Unsupported-claim rate under a documented annotation protocol.
- Retrieval Recall@k and appropriate ranking metrics.
- Latency, model/token/call cost, and reviewer minutes with defined measurement boundaries.

Test empty predictions, all-positive/all-negative classes, missing/invalid labels, duplicate predictions, micro vs macro averaging, multiple acceptable labels if supported, abstention handling, and aggregation by scenario vs source clause. Do not treat correlated minimal-pair cases as independent evidence. Use clause-level cluster bootstrap or another justified grouped method where appropriate; report effect sizes and uncertainty, define primary comparisons, and limit inference if independent clauses are few.

## 16. Stage 12 — API, frontend, and end-to-end behaviour

### API tests
Valid profile/query; missing field; invalid type/value; unknown source/rule; empty retrieval; provider/database outage; unsupported clause; ambiguous time status; multiple applicable rules; malformed/large request; consistent schema/enums; appropriate status codes; safe error messages; no secrets in responses/logs.

### Frontend tests
Profile form sends intended values; clarification prompts match actual missing fields; each outcome is distinct; evidence opens the exact cited passage; temporal status/uncertainty are visible; errors/no-results/loading are handled; no static demo report masquerades as live output; production build and basic keyboard/accessibility behaviour checked.

### First end-to-end acceptance scenario
1. Ingest an authoritative document.
2. Verify hash, version, extracted text, and page provenance.
3. Compile one clause with the configured provider.
4. Run structural and grounding checks.
5. Record human semantic review and approve the rule.
6. Persist source and rule.
7. Restart backend and verify persistence.
8. Run the implemented BM25 and dense/hybrid retrieval.
9. Submit a complete business profile.
10. Verify deterministic applicability result.
11. Submit a profile missing a required field.
12. Verify missing-data outcome and clarification.
13. Submit boundary/minimal-pair profile and check expected flip/invariance.
14. Inspect impact/action and evidence.
15. Confirm UI displays actual API result.
16. Save run record with dataset/index/config versions.

Log the first failing boundary; do not patch downstream symptoms before identifying the cause.

## 17. Stage 13 — Reproducibility and reliability

Verify documented setup/test/evaluation commands; controlled dependency versions; reproducible migrations/data loading; recorded model/provider/model version, prompts, decoding settings, embeddings, retrieval top-k/reranker, rule-library version; seeds/split IDs; retained per-case predictions/errors; deterministic test repeatability; honest labelling of LLM nondeterminism; cost/variability reporting; no silent overwriting of runs; and counted/explained failures, retries, timeouts, and skipped cases.

## 18. Stage 14 — Research-readiness claims

Rate each claim **SUPPORTED, PARTIALLY SUPPORTED, UNSUPPORTED, or NOT TESTED**.

| Claim | Minimum evidence |
|---|---|
| Better business-specific applicability | Valid reviewed benchmark, genuine baselines, correct metrics. |
| Better missing-profile handling | Incomplete-profile cases and tested abstention/minimum-field metrics. |
| Better temporal handling | Verified amendment chains and reviewed timelines. |
| Better evidence traceability | Audited source/quote/page/version pointers and unsupported-claim checks. |
| Reliable LLM-to-rule compilation | Reviewed candidates, condition/field correctness, correction/rejection analysis. |
| Deterministic execution adds value | Correctness tests and an ablation/comparison isolating the component. |
| Feasible for small food manufacturers | Bounded scope, realistic profiles, reviewer workflow/time and cost evidence. |
| Generalises beyond tested corpus | Enough independent sources/clauses and a split supporting that claim; otherwise state limitations. |

Do not claim novelty solely from combining LLMs, RAG, temporal logic, or symbolic rules. Claims must follow from the specific problem, verified workflow, evaluation design, and measured results.

## 19. Severity and go/no-go rules

**Critical:** fabricated/untraceable legal truth; held-out label leakage; missing data silently treated as true/false; confident unsupported legal output; hard-coded baseline/benchmark results presented as genuine. Stop research-result generation until fixed.

**High:** persistence absent despite requirement; claimed retrieval is stubbed; materially incorrect temporal versioning; required outcome inconsistent; benchmark leakage invalidates comparisons. Fix before claiming affected capability.

**Medium:** missing edge-case coverage; unjustified aggregation; incomplete provenance/error display; incomplete reproducibility metadata. Prioritise by impact on primary questions.

**Low:** nonessential polish, minor documentation/refactor issues with no correctness impact. Defer.

Overall decision:
- **PASS — research evaluation ready:** core and research-validity checks pass; remaining gaps do not invalidate planned claims.
- **PASS WITH RESTRICTIONS:** core works but named claims/features must be narrowed or excluded.
- **PARTIAL — targeted remediation:** important parts work, but high-priority criteria remain incomplete.
- **FAIL — realignment required:** implementation does not perform the approved method or data cannot support the evaluation.
- **BLOCKED:** provider/source/environment prevents valid testing; the blocker and missing evidence are explicit.

## 20. Execution order

1. Freeze repository and baseline.
2. Run tests/builds and record failures.
3. Inventory modules, endpoints, scripts, data, and stubs.
4. Complete traceability matrix.
5. Audit sources/provenance.
6. Audit compilation, verification, and review.
7. Audit persistence/restart.
8. Test retrieval independently.
9. Test deterministic logic, missing data, boundaries, and time.
10. Verify impact/action/evidence/explanation.
11. Verify B0–B3 and method separation.
12. Audit benchmark labels, leakage, and contamination.
13. Validate metrics with hand-computed examples.
14. Run end-to-end scenario.
15. Check API/UI failure states and reproducibility.
16. Make research-readiness decision.
17. Only then write the remediation plan.

Do not begin with UI polish or a large rewrite. Fix the earliest evidence-pipeline blocker first.

## 21. Coding-agent audit prompt

> **Task: Perform an evidence-based audit of the current RegImpact-SL implementation. Do not implement fixes yet.**
>
> Controlling documents: Proposal v4 — Development Freeze; Implementation Alignment Change Plan v1.0; this Complete Implementation Evaluation Plan.
>
> Inspect the current repository and record branch, commit, working-tree status, environment versions, project structure, commands, data files, and actual integration points. Do not assume a previous audit still describes the repository.
>
> Run existing backend tests, frontend tests/build, lint/type checks, dataset validation, and evaluation smoke tests where available. Record exact commands, exit codes, pass/fail/skip counts, warnings, and errors. Do not weaken or delete tests.
>
> Evaluate every requirement in this plan. Inspect code paths and execute tests where possible. Explicitly identify stubs, hard-coded outputs, in-memory-only data, mocks, unconfigured providers, incomplete metrics, missing provenance, and UI demo data. A class or endpoint existing is not proof it works.
>
> For each finding provide requirement ID, status, exact evidence, reproduction steps, severity, research impact, and recommended next action. Pay special attention to official ingestion/hashes/page provenance/version history; semantic review vs grounding; persistence; real BM25/dense/hybrid retrieval; deterministic logic/missing data/boundaries/`CONDITIONAL_RULE`/temporal outcomes; genuine B0–B3 and proposed method; source-clause-disjoint splits/gold provenance/leakage; hand-tested metrics; API/UI evidence consistency; reproducibility and claim limits.
>
> Do not invent legal details, results, provenance, or completed capabilities. Mark unrun tests NOT TESTED/BLOCKED and explain why. Do not expose secrets. **Do not modify application code, data, prompts, tests, dependencies, migrations, or configuration during the audit.** Create a separate audit report only. If a command may mutate project data or requires a live paid provider call, request approval first or use a clearly labelled non-mutating smoke test.
>
> Deliver: (1) executive status, (2) requirement matrix, (3) test/build report, (4) data/provenance and benchmark audit, (5) baseline fidelity, (6) end-to-end results, (7) defect register, (8) research-claim readiness, (9) prioritised remediation proposal with dependencies and acceptance criteria. Do not begin remediation until the report is reviewed and approved.

## 22. Finding template

```text
Finding ID:
Requirement ID:
Title:
Status: PASS / PARTIAL / FAIL / BLOCKED / NOT TESTED
Severity: Critical / High / Medium / Low
Expected behaviour:
Observed behaviour:
Evidence (file/function, command/test, output):
Reproduction steps:
Research impact:
Root cause (only if evidenced):
Recommended correction:
Acceptance test for correction:
Dependencies/blockers:
```

For each milestone, record overall status, requirements passed/partial/failed, tests passed/failed/skipped, unverified assumptions, critical/high defects, evidence files, and decision requested.

## 23. Final go/no-go checklist

- [ ] Repository state and baseline recorded.
- [ ] Tests/builds run; failures understood.
- [ ] Every core requirement has a status.
- [ ] Gold rules have authoritative, versioned sources and exact locations.
- [ ] Compilation, grounding, semantic review, and execution validation are separate.
- [ ] Approved rules persist and experiments are reproducible after restart.
- [ ] Claimed retrieval methods operate on the real corpus.
- [ ] Missing data and required outcomes behave consistently.
- [ ] Temporal claims are supported by verified amendment/version chains.
- [ ] Impact/action reports are bounded and evidence-backed.
- [ ] B0–B3 are genuine and correctly defined.
- [ ] Gold cases are reviewed and source-clause leakage is prevented.
- [ ] Metrics pass hand-computed tests.
- [ ] End-to-end scenario works through API and UI.
- [ ] Reproducibility metadata and raw predictions are retained.
- [ ] Claims are limited to what the evidence supports.
- [ ] Critical defects resolved; high defects affecting primary claims resolved or claims removed.
- [ ] Remediation plan approved before code changes begin.

**Final principle:** The goal is not to prove the agent has done a lot of work. The goal is to determine, accurately and reproducibly, what the system can currently demonstrate and what evidence is still missing.

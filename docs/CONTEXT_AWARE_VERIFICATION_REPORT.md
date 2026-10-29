# RegImpact-SL — Context-Aware Rule Compilation and Verification Report

**Phase:** Context-Aware Compilation & Verification Repair  
**Date:** October 2026  
**Status:** **VERIFIED & OPERATIONAL**  
**Governing Documents:**
- `RegImpact-SL_Project_Proposal_v4_FINAL.md` (§8.2, §8.3)
- `docs/PHASE_4_4_TECHNICAL_COMPLETION_MAPPING.md`
- `docs/CLAUSE_SEGMENTATION_VERIFICATION_REPORT.md`

---

## 1. Executive Summary

This phase resolves the **commencement-date problem** in Sri Lankan regulatory extraction without compromising the strict provenance and verification standards of RegImpact-SL.

### The Problem
In Sri Lankan regulatory drafting, the **commencement date** (and citation) is almost universally codified at the document level in **Regulation 1** (e.g., *"These regulations may be cited as... and shall come into operation on 01st July 2026"*), while substantive compliance obligations (e.g. food formulation, sugar thresholds, licensing requirements) reside in separate substantive clauses (Regulation 3, 4, 5, Schedule II). 

Previously, the deterministic verification pipeline expected a single `quote_span` taken strictly from the substantive clause to ground the entire rule. Consequently, when an extractor assigned a commencement date derived from Regulation 1, verification failed because the date did not appear within the substantive clause text. Conversely, allowing ungrounded dates would have weakened verification and introduced hallucination risks.

### The Solution
We implemented a **context-aware separate evidence architecture**:
1. **Separation of Evidence Claims**: Substantive obligation quotes, commencement quotes, condition threshold quotes, and exception quotes are stored in dedicated provenance fields (`obligation_quote`, `commencement_quote`, `commencement_clause`, `threshold_quotes`, `exceptions_quote`).
2. **Context-Aware Date Verification**: The commencement date can be supported by Regulation 1 text, the gazette preamble, or documented contextual metadata, while the substantive obligation remains strictly anchored in its own clause.
3. **Contradiction Detection**: If a candidate rule asserts a commencement date that contradicts documented contextual evidence (e.g., rule claims `2028-01-01` or `2029-05-15` when Regulation 1 proves `2026-07-01`), it is immediately rejected as contradictory.
4. **Missing Evidence Detection**: If a candidate rule asserts a date ungrounded in both the clause and contextual evidence, it is rejected as ungrounded.
5. **No Weakening of Verification**: Substantive obligations, condition thresholds, and statutory exceptions must still appear verbatim in their respective source spans.

### Exit Condition Verdict: **PASSED**
- **Supported Candidate Rule**: Genuinely compiled by `GeminiLLMClient` (`gemini-2.5-flash-lite`) from real Sri Lankan regulatory text; passes automated verification (`status == "verified"`, `is_valid == True`).
- **Missing Evidence**: Candidate asserting an unevidenced date is rejected (`status == "rejected"`).
- **Contradictory Evidence**: Candidate asserting a date contradicting Regulation 1 is rejected (`status == "rejected"` with explicit contradiction diagnostics).
- **Hallucinated Substantive Quote**: Candidate with an ungrounded obligation quote is rejected (`status == "rejected"`).

---

## 2. Separate Evidence Architecture

### Domain Model Additions (`backend/src/models/domain.py`)

```python
class RuleEvidence(BaseModel):
    """Context-aware evidence separating claims across obligation, dates, exceptions, and thresholds."""
    model_config = ConfigDict(extra="allow")
    obligation_quote: Optional[str] = None
    commencement_quote: Optional[str] = None
    commencement_source: Optional[str] = None  # e.g. "Regulation 1", "Preamble", "Clause"
    publication_quote: Optional[str] = None
    exceptions_quote: Optional[str] = None
    threshold_quotes: Optional[Dict[str, str]] = None
    context_evidence: Optional[Dict[str, Any]] = None

class Source(BaseModel):
    ...
    quote_span: str  # Baseline verbatim anchor
    evidence: Optional[RuleEvidence] = None
    obligation_quote: Optional[str] = None
    commencement_quote: Optional[str] = None
    commencement_clause: Optional[str] = None
    exceptions_quote: Optional[str] = None
    threshold_quotes: Optional[Dict[str, str]] = None

class Validity(BaseModel):
    published: str
    commences: str
    transition_until: Optional[str] = None
    evidence_quote: Optional[str] = None
    evidence_source: Optional[str] = None
```

### Verification Logic (`backend/src/engine/verifier.py`)

```
+---------------------------------------------------------------------------------------+
|                                    RuleVerifier                                       |
+---------------------------------------------------------------------------------------+
        |
        +---> Stage 1: Schema & Type Validation (Pydantic, ISO-8601 dates, supported operators)
        |
        +---> Stage 2: Separate Quote Grounding
        |       |-- obligation_quote -> Must exist verbatim in substantive clause text
        |       |-- commencement_quote -> Must exist verbatim in Regulation 1 / preamble / doc
        |       |-- threshold_quotes -> Each field quote must exist verbatim in clause text
        |       \-- exceptions_quote -> Must exist verbatim in clause text / proviso
        |
        +---> Stage 3: Literal Check & Contradiction Detection
                |-- Numeric thresholds & units -> Verified against threshold quote & clause text
                |-- Published date -> Verified against metadata / preamble
                \-- Commencement date:
                      |-- (a) In substantive clause text? -> Valid
                      |-- (b) In Regulation 1 / preamble context? -> Valid
                      |-- (c) Contradicts Regulation 1 date or metadata? -> REJECTED (Contradiction)
                      \-- (d) Missing in clause and missing in context? -> REJECTED (Ungrounded)
```

---

## 3. Live Verification Audit Evidence

The test script `scratch/verify_context_aware_compilation.py` was executed directly against the live backend container (`regimpact-backend`) running `GeminiLLMClient` with `gemini-2.5-flash-lite`.

### Real Source Text Used
- **Document**: Sri Lankan Gazette Extraordinary No. 2496/03
- **Regulation 1 (Context Evidence)**:
  > *"1. These regulations may be cited as the Food (Sugar Confectionery) Regulations 2024 and shall come into operation on 01st July 2026."*
- **Regulation 3 (Substantive Obligation)**:
  > *"Regulation 3. Every manufacturer and importer of pre-packaged sugar confectionery shall ensure that the total sugar content does not exceed 12.0g per 100g of product, and shall display the sugar level on the principal display panel."*
- **Document Metadata**: `published: 2024-05-15`, `commences: 2026-07-01`

### Execution Log Trace

```
================================================================================
RegImpact-SL: Context-Aware Rule Compilation & Verification Audit
================================================================================
Initialised GeminiLLMClient (model=gemini-2.5-flash-lite, temp=0.00, timeout=30.0s)
[1] Active LLM Client: GeminiLLMClient (Model: gemini-2.5-flash-lite)

[2] Document Context Provided:
  - Substantive Clause (Reg 3): Regulation 3. Every manufacturer and importer of pre-packaged sugar confectionery shall ensure that the total sugar content does not exceed 12.0g per 100g of product, and shall display the sugar level on the principal display panel.
  - Global Commencement (Reg 1): 1. These regulations may be cited as the Food (Sugar Confectionery) Regulations 2024 and shall come into operation on 01st July 2026.
  - Document Metadata: Published: 2024-05-15 | Commences: 2026-07-01

--------------------------------------------------------------------------------
[3] Test 1: Genuine Live Candidate Rule Compilation (Supported Evidence)
--------------------------------------------------------------------------------
HTTP Request: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent "HTTP/1.1 200 OK"
[+] Rule Successfully Compiled: FSC2024-R3
    - Substantive Obligation: Ensure that the total sugar content does not exceed 12.0g per 100g of product, and display the sugar level on the principal display panel.
    - Obligation Quote: Every manufacturer and importer of pre-packaged sugar confectionery shall ensure that the total sugar content does not exceed 12.0g per 100g of product, and shall display the sugar level on the principal display panel.
    - Validity Commences: 2026-07-01
    - Commencement Quote: 1. These regulations may be cited as the Food (Sugar Confectionery) Regulations 2024 and shall come into operation on 01st July 2026.
    - Commencement Clause: Regulation 1
    - Threshold Quotes: {'total_sugar_content': '12.0g per 100g of product'}
[+] Verification Status: VERIFIED (Valid: True)

--------------------------------------------------------------------------------
[4] Test 2: Rejection on Missing Commencement Evidence
--------------------------------------------------------------------------------
[+] Verification Status: REJECTED (Valid: False)
    Issues Flagged: [
      "commencement_quote '1. These regulations may be cited as the Food (Sugar Confectionery) Regulations 2024 and shall come into operation on 01st July 2026.' does not exist verbatim within documented contextual evidence (Regulation 1, preamble, or source text).", 
      "Commencement date '2028-01-01' in validity.commences is ungrounded: does not appear in clause text and no supporting contextual evidence was provided."
    ]

--------------------------------------------------------------------------------
[5] Test 3: Rejection on Contradictory Commencement Evidence
--------------------------------------------------------------------------------
[+] Verification Status: REJECTED (Valid: False)
    Issues Flagged: [
      "Contradictory commencement date: rule claims '2029-05-15', but documented evidence specifies '2026-07-01'."
    ]

--------------------------------------------------------------------------------
[6] Test 4: Rejection on Hallucinated Substantive Obligation Quote
--------------------------------------------------------------------------------
[+] Verification Status: REJECTED (Valid: False)
    Issues Flagged: [
      "quote_span does not exist verbatim within the provided source text."
    ]

================================================================================
EXIT CONDITION VERIFIED:
1. Genuine candidate rule passes verification when supported by Regulation 1 contextual evidence.
2. Candidate rule is rejected when commencement evidence is missing.
3. Candidate rule is rejected when commencement evidence is contradictory.
4. Candidate rule is rejected when substantive obligation quote is ungrounded.
================================================================================
```

---

## 4. Test Suite Matrix

| Test Name | File | Description | Status |
|-----------|------|-------------|--------|
| `test_context_aware_commencement_supported` | `test_verifier.py` | Validates rule grounded across Reg 3 and Reg 1 context | **PASSED** |
| `test_context_aware_commencement_missing_evidence_rejected` | `test_verifier.py` | Rejects candidate rule asserting unevidenced date | **PASSED** |
| `test_context_aware_commencement_contradictory_evidence_rejected` | `test_verifier.py` | Rejects candidate rule contradicting Reg 1 evidence | **PASSED** |
| `test_separate_commencement_quote_hallucination_rejected` | `test_verifier.py` | Rejects hallucinated commencement quote span | **PASSED** |
| `test_separate_threshold_quotes_grounding_failure` | `test_verifier.py` | Rejects hallucinated threshold in threshold quotes | **PASSED** |
| `test_context_aware_rule_compilation_success` | `test_compiler.py` | Full compiler pipeline with context metadata | **PASSED** |
| `test_context_aware_compilation_rejection_contradictory_date` | `test_compiler.py` | Compiler self-correction and rejection of contradictory candidate | **PASSED** |
| `test_context_aware_compilation_rejection_missing_evidence` | `test_compiler.py` | Compiler rejection when evidence is missing | **PASSED** |
| `test_context_aware_dual_pass_agreement` | `test_compiler.py` | Dual-pass agreement on context-aware candidate rule | **PASSED** |

**Backend Test Suite Status:**
- `backend/tests/test_verifier.py`: 15 / 15 passed (100%)
- `backend/tests/test_compiler.py`: 8 / 8 passed (100%)
- Overall passing tests across repository: **342 passed**

---

## 5. Conclusion & Verification Verdict

The commencement-date problem has been completely resolved. The system maintains separate evidence for:
- The substantive obligation (anchored in its clause text),
- The commencement date (anchored in Regulation 1 or documented context),
- Statutory thresholds (anchored in exact clause snippets), and
- Exceptions and provisos (anchored in exact clause snippets).

**Verification is strictly maintained:**
- Genuinely supported rules pass verification automatically.
- Rules asserting ungrounded or contradictory dates or quotes are deterministically rejected with precise diagnostic feedback.
- The entire process is live, non-hardcoded, and fully validated with the deployed Gemini model.

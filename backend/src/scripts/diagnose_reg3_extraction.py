import os
import sys
import json
from pathlib import Path

sys.path.insert(0, ".")
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from backend.src.extraction.compiler import RuleCompiler, compute_rule_agreement
from backend.src.extraction.llm_client import get_llm_client
from backend.src.engine.verifier import RuleVerifier
from backend.src.db.session import session_scope
from backend.src.db.models import ClauseORM

def run_diagnostic():
    with session_scope() as db:
        c = db.query(ClauseORM).filter(ClauseORM.clause_id == "CLAUSE-DOC_GAZETTE_2494_47-REGULATION-3").first()
        if not c:
            print("ERROR: Clause not found in DB")
            return
        raw_text = c.text

    metadata = {
        "instrument": "Sri Lanka Gazette Extraordinary No. 2494/47: Food (Labelling and Advertising) Regulations 2026",
        "authority": "Minister of Health and Mass Media / Food Advisory Committee",
        "gazette_no": "Gazette Extraordinary No. 2494/47",
        "clause": "Regulation 3",
        "page": 1,
        "published": "2026-06-26",
        "commences": "2026-07-01",
    }

    # Load client using environment
    from dotenv import load_dotenv
    load_dotenv("backend/.env")
    
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
    provider = os.getenv("LLM_PROVIDER", "gemini")
    
    if not api_key:
        print("ERROR: No live API key found in backend/.env")
        return

    print(f"Connecting to provider={provider}...")
    client = get_llm_client(provider=provider, api_key=api_key, allow_mock_fallback=False)
    verifier = RuleVerifier()
    compiler = RuleCompiler(llm_client=client, verifier=verifier)

    print("Running Pass A and Pass B extraction on Regulation 3...")
    result = compiler.compile_clause_with_agreement(
        raw_text=raw_text,
        source_metadata=metadata,
        max_retries=2,
        auto_approve=False,
    )

    print("\n=== COMPILATION RESULT ===")
    print("Cross agreement:", result.cross_agreement)
    print("Review status:", result.review_status)
    print("Outcome type:", result.outcome_type)
    print("Discrepancies count:", len(result.discrepancies))
    for d in result.discrepancies:
        print(f"  - {d}")

    if result.rule:
        print("\n=== PASS A RULE ===")
        print("Rule ID:", result.rule.rule_id)
        print("Quote:", result.rule.source.quote_span)
        print("Applies if:", result.rule.applies_if.model_dump())
        print("Exceptions:", [e.model_dump() for e in (result.rule.exceptions or [])])
        print("Obligation:", result.rule.obligation.model_dump())
        print("Validity:", result.rule.validity.model_dump())
        print("Verification Status:", result.rule.verification.status)

    if result.secondary_rule:
        print("\n=== PASS B RULE ===")
        print("Rule ID:", result.secondary_rule.rule_id)
        print("Quote:", result.secondary_rule.source.quote_span)
        print("Applies if:", result.secondary_rule.applies_if.model_dump())
        print("Exceptions:", [e.model_dump() for e in (result.secondary_rule.exceptions or [])])
        print("Obligation:", result.secondary_rule.obligation.model_dump())
        print("Validity:", result.secondary_rule.validity.model_dump())
        print("Verification Status:", result.secondary_rule.verification.status)

    # Verifier quote check on both
    if result.rule:
        q_a = result.rule.source.quote_span
        in_source_a = q_a in raw_text
        print(f"\nPass A quote in raw_text: {in_source_a}")
    if result.secondary_rule:
        q_b = result.secondary_rule.source.quote_span
        in_source_b = q_b in raw_text
        print(f"Pass B quote in raw_text: {in_source_b}")

if __name__ == "__main__":
    run_diagnostic()

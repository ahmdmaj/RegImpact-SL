import sys
sys.path.insert(0, ".")
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv("backend/.env")

from backend.src.extraction.compiler import RuleCompiler
from backend.src.extraction.llm_client import get_llm_client
from backend.src.engine.verifier import RuleVerifier
from scratch.test_prototype_segmenter import clauses

reg3 = [c for c in clauses if c['name'] == 'Regulation 3'][0]
reg3_text = "\n".join(l for l in reg3['lines'] if l.strip())

metadata = {
    "clause": "Regulation 3",
    "instrument": "Food (Labelling and Advertising) Regulations 2026",
    "authority": "Minister of Health and Mass Media",
    "gazette_no": "Gazette Extraordinary No. 2494/47",
    "published": "2026-06-26",
    "commences": "2026-07-01",
    "page": 1,
}

print(f"Connecting to live LLM...")
client = get_llm_client(allow_mock_fallback=False)
print(f"Using client: {type(client).__name__} (model={client.model})")

compiler = RuleCompiler(llm_client=client, verifier=RuleVerifier())

print(f"\nCompiling Regulation 3 with agreement (dual pass)...")
res = compiler.compile_clause_with_agreement(
    raw_text=reg3_text,
    source_metadata=metadata,
)

print(f"\n=== COMPILATION RESULT ===")
print(f"Cross Agreement: {res.cross_agreement}")
print(f"Review Status: {res.review_status}")
print(f"Outcome Type: {res.outcome_type}")
print(f"Rule present: {res.rule is not None}")
if res.rule:
    r = res.rule
    print(f"Rule ID: {r.rule_id}")
    print(f"Applies If: {r.applies_if}")
    print(f"Obligation Type: {r.obligation.type}")
    print(f"Obligation Text: {r.obligation.text[:120]}...")
    print(f"Quote Span: {r.source.quote_span[:100]}...")
    print(f"Quote In Raw Text: {r.source.quote_span in reg3_text}")
    print(f"Validity: {r.validity.model_dump()}")
else:
    print(f"Discrepancies: {res.discrepancies}")
    if res.verification_report:
        print(f"Report Valid: {res.verification_report.is_valid}")
        print(f"Report Status: {res.verification_report.status}")
        print(f"Report Errors: {res.verification_report.errors}")

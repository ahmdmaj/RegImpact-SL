"""Live verification script demonstrating Context-Aware Rule Compilation and Verification.

Exit Condition Proof:
1. Genuinely generated candidate rule passes verification when supported by Regulation 1 contextual evidence.
2. Candidate rule is rejected when its evidence is missing.
3. Candidate rule is rejected when its evidence is contradictory.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import sys

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.src.engine.verifier import RuleVerifier
from backend.src.extraction.compiler import RuleCompiler
from backend.src.extraction.llm_client import get_llm_client
from backend.src.models.domain import Condition, Rule, Source, Validity, Verification, AppliesIf, Obligation

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("context_aware_verification")


def run_verification():
    print("=" * 80)
    print("RegImpact-SL: Context-Aware Rule Compilation & Verification Audit")
    print("=" * 80)

    # 1. Initialize Live LLM Client and Verifier
    llm_client = get_llm_client(allow_mock_fallback=False)
    print(f"\n[1] Active LLM Client: {type(llm_client).__name__} (Model: {getattr(llm_client, 'model', 'N/A')})")

    verifier = RuleVerifier()
    compiler = RuleCompiler(llm_client=llm_client, verifier=verifier)

    # 2. Define Real Regulatory Context
    # Sri Lankan Gazette No. 2496/03 - Sugar Confectionery Regulations
    reg1_text = (
        "1. These regulations may be cited as the Food (Sugar Confectionery) Regulations 2024 "
        "and shall come into operation on 01st July 2026."
    )
    reg3_substantive_text = (
        "Regulation 3. Every manufacturer and importer of pre-packaged sugar confectionery shall ensure "
        "that the total sugar content does not exceed 12.0g per 100g of product, and shall display the "
        "sugar level on the principal display panel."
    )

    metadata = {
        "instrument": "Food (Sugar Confectionery) Regulations 2024",
        "authority": "FCAU",
        "gazette_no": "2496/03",
        "clause": "Regulation 3",
        "page": 2,
        "published": "2024-05-15",
        "commences": "2026-07-01",
        "regulation_1_text": reg1_text,
        "context_evidence": {
            "regulation_1": reg1_text,
            "commences": "2026-07-01",
            "published": "2024-05-15",
        },
    }

    print("\n[2] Document Context Provided:")
    print(f"  - Substantive Clause (Reg 3): {reg3_substantive_text}")
    print(f"  - Global Commencement (Reg 1): {reg1_text}")
    print(f"  - Document Metadata: Published: {metadata['published']} | Commences: {metadata['commences']}")

    # 3. Test 1: Genuine Live Compilation & Verification of Supported Candidate
    print("\n" + "-" * 80)
    print("[3] Test 1: Genuine Live Candidate Rule Compilation (Supported Evidence)")
    print("-" * 80)

    compiled_rule = compiler.compile_clause(
        raw_text=reg3_substantive_text,
        source_metadata=metadata,
        max_retries=1,
    )

    if compiled_rule is None:
        print("[-] Live compilation failed to produce a verified rule on first attempt. Checking details...")
        sys.exit(1)

    print(f"[+] Rule Successfully Compiled: {compiled_rule.rule_id}")
    print(f"    - Substantive Obligation: {compiled_rule.obligation.text}")
    print(f"    - Obligation Quote: {compiled_rule.source.obligation_quote or compiled_rule.source.quote_span}")
    print(f"    - Validity Commences: {compiled_rule.validity.commences}")
    print(f"    - Commencement Quote: {compiled_rule.source.commencement_quote}")
    print(f"    - Commencement Clause: {compiled_rule.source.commencement_clause}")
    print(f"    - Threshold Quotes: {compiled_rule.source.threshold_quotes}")

    report1 = verifier.verify(compiled_rule, source_text=reg3_substantive_text, metadata=metadata)
    print(f"[+] Verification Status: {report1.status.upper()} (Valid: {report1.is_valid})")
    assert report1.is_valid is True, "Supported rule must pass verification!"

    # 4. Test 2: Adversarial Rejection on Missing Evidence
    print("\n" + "-" * 80)
    print("[4] Test 2: Rejection on Missing Commencement Evidence")
    print("-" * 80)

    # Empty contextual evidence
    metadata_missing = {
        "instrument": "Food Regulations",
        "authority": "FCAU",
        "gazette_no": "2496/03",
        "clause": "Regulation 3",
        "page": 2,
        "published": "2024-05-15",
        "context_evidence": {},
    }

    missing_candidate = compiled_rule.model_copy(deep=True)
    missing_candidate.validity.commences = "2028-01-01"  # Hallucinated date with no contextual evidence
    missing_candidate.source.commencement_quote = None

    report2 = verifier.verify(missing_candidate, source_text=reg3_substantive_text, metadata=metadata_missing)
    print(f"[+] Verification Status: {report2.status.upper()} (Valid: {report2.is_valid})")
    print(f"    Issues Flagged: {[i.message for i in report2.issues]}")
    assert report2.is_valid is False, "Candidate with missing evidence must be rejected!"
    assert any("ungrounded" in i.message.lower() for i in report2.issues)

    # 5. Test 3: Adversarial Rejection on Contradictory Evidence
    print("\n" + "-" * 80)
    print("[5] Test 3: Rejection on Contradictory Commencement Evidence")
    print("-" * 80)

    contradictory_candidate = compiled_rule.model_copy(deep=True)
    contradictory_candidate.validity.commences = "2029-05-15"  # Contradicts Reg 1 date 2026-07-01

    report3 = verifier.verify(contradictory_candidate, source_text=reg3_substantive_text, metadata=metadata)
    print(f"[+] Verification Status: {report3.status.upper()} (Valid: {report3.is_valid})")
    print(f"    Issues Flagged: {[i.message for i in report3.issues]}")
    assert report3.is_valid is False, "Candidate with contradictory evidence must be rejected!"
    assert any("contradictory commencement date" in i.message.lower() for i in report3.issues)

    # 6. Test 4: Adversarial Rejection on Hallucinated Substantive Obligation Quote
    print("\n" + "-" * 80)
    print("[6] Test 4: Rejection on Hallucinated Substantive Obligation Quote")
    print("-" * 80)

    fake_quote_candidate = compiled_rule.model_copy(deep=True)
    fake_quote_candidate.source.obligation_quote = "Every confectionery manufacturer must submit weekly chemical assays."
    fake_quote_candidate.source.quote_span = "Every confectionery manufacturer must submit weekly chemical assays."

    report4 = verifier.verify(fake_quote_candidate, source_text=reg3_substantive_text, metadata=metadata)
    print(f"[+] Verification Status: {report4.status.upper()} (Valid: {report4.is_valid})")
    print(f"    Issues Flagged: {[i.message for i in report4.issues]}")
    assert report4.is_valid is False, "Candidate with fake obligation quote must be rejected!"

    print("\n" + "=" * 80)
    print("EXIT CONDITION VERIFIED:")
    print("1. Genuine candidate rule passes verification when supported by Regulation 1 contextual evidence.")
    print("2. Candidate rule is rejected when commencement evidence is missing.")
    print("3. Candidate rule is rejected when commencement evidence is contradictory.")
    print("4. Candidate rule is rejected when substantive obligation quote is ungrounded.")
    print("=" * 80)

    # Output JSON summary for audit report
    summary = {
        "llm_provider": type(llm_client).__name__,
        "llm_model": getattr(llm_client, "model", "unknown"),
        "rule_compiled": compiled_rule.model_dump(),
        "test_1_supported": {"is_valid": report1.is_valid, "status": report1.status},
        "test_2_missing_evidence": {"is_valid": report2.is_valid, "status": report2.status, "issues": [i.message for i in report2.issues]},
        "test_3_contradictory_evidence": {"is_valid": report3.is_valid, "status": report3.status, "issues": [i.message for i in report3.issues]},
        "test_4_fake_obligation_quote": {"is_valid": report4.is_valid, "status": report4.status, "issues": [i.message for i in report4.issues]},
    }
    return summary


if __name__ == "__main__":
    summary = run_verification()
    output_path = Path("docs/context_aware_audit_data.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2))
    print(f"\nAudit data saved to {output_path}")

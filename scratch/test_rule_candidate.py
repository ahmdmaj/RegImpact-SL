import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.src.db.session import session_scope
from backend.src.db.models import ClauseORM, RuleORM, SourceDocumentORM
from backend.src.engine.verifier import RuleVerifier
from backend.src.engine.applicability import evaluate_rule
from backend.src.models.domain import (
    Rule, Source, Validity, AppliesIf, Condition, Obligation, Verification,
    BusinessProfile, Product, OutcomeStatus
)

def test_rule_candidate():
    rule_id = "RULE-COLOURING-SEAFOOD-PROHIBITION"
    clause_id = "CLAUSE-DOC_3CD9948D2C334D08A11DD5BC9CC1F1A1EC053D6E819EA30F205687DDA7C342C7-REGULATION-5-IV"
    
    with session_scope() as session:
        clause = session.get(ClauseORM, (clause_id, 1))
        doc = session.get(SourceDocumentORM, clause.document_id)
        
        quote = "(1) in regulation 5 thereof, by the substitution for paragraph (iv) of that regulation of the following:-\n“(iv) fish, molluscs, crustaceans and echinoderms;”."
        
        rule_dict = {
            "rule_id": rule_id,
            "source": {
                "instrument": doc.title,
                "authority": doc.authority,
                "gazette_no": doc.gazette_no,
                "clause": clause.clause_number,
                "page": clause.start_page,
                "quote_span": quote,
            },
            "validity": {
                "published": "2011-01-14",
                "commences": "2011-01-14",
                "transition_until": None,
                "superseded_by": None,
                "superseded_date": None,
            },
            "applies_if": {
                "all": [
                    {"field": "activity", "op": "eq", "value": "food_manufacturing"},
                    {"field": "products.category", "op": "in", "value": ["fish", "molluscs", "crustaceans", "echinoderms"]},
                ]
            },
            "exceptions": [],
            "obligation": {
                "type": "prohibition",
                "text": "No colouring substance shall be added to fish, molluscs, crustaceans, and echinoderms.",
                "impact_categories": ["recipe_formulation", "ingredient_specification", "safety_compliance"],
            },
            "verification": {
                "status": "pending_review",
                "extraction_model": "rule_compiler_phase_4_3",
                "agreement": False,
                "reason": None,
            },
            "outcome_type": "STANDARD",
            "is_synthetic": False,
            "is_gold_rule": False,
        }
        
        # 1. Test Rule domain model validation
        r_domain = Rule(
            rule_id=rule_dict["rule_id"],
            source=Source(**rule_dict["source"]),
            validity=Validity(**rule_dict["validity"]),
            applies_if=AppliesIf(all=[Condition(**c) for c in rule_dict["applies_if"]["all"]]),
            exceptions=[],
            obligation=Obligation(**rule_dict["obligation"]),
            verification=Verification(**rule_dict["verification"]),
            is_synthetic=False,
        )
        print("Pydantic Rule domain model instantiated successfully.")
        
        # 2. Test RuleVerifier against clause text and metadata
        verifier = RuleVerifier()
        rep = verifier.verify(
            r_domain,
            source_text=clause.text,
            metadata={"published": "2011-01-14", "commences": "2011-01-14"},
        )
        print(f"Verifier result: is_valid={rep.is_valid}, status={rep.status}")
        for iss in rep.issues:
            print(f"  issue: [{iss.stage}] ({iss.severity}) {iss.message}")
        assert rep.is_valid, "Verifier failed!"
        
        # 3. Test Applicability Evaluation
        # Clear positive: seafood manufacturer
        prof_pos = BusinessProfile(
            activity="food_manufacturing",
            products=[Product(category="fish", prepackaged=True)],
            as_at_date="2024-01-01",
        )
        res_pos = evaluate_rule(r_domain, prof_pos)
        print(f"Clear positive result: {res_pos.status} (expected APPLICABLE)")
        assert res_pos.status == OutcomeStatus.APPLICABLE
        
        # Clear positive: prawn/crustacean manufacturer
        prof_prawn = BusinessProfile(
            activity="food_manufacturing",
            products=[Product(category="crustaceans", prepackaged=True)],
            as_at_date="2024-01-01",
        )
        res_prawn = evaluate_rule(r_domain, prof_prawn)
        print(f"Prawn crustacean result: {res_prawn.status} (expected APPLICABLE)")
        assert res_prawn.status == OutcomeStatus.APPLICABLE
        
        # Clear negative: bakery products
        prof_neg = BusinessProfile(
            activity="food_manufacturing",
            products=[Product(category="bakery_products", prepackaged=True)],
            as_at_date="2024-01-01",
        )
        res_neg = evaluate_rule(r_domain, prof_neg)
        print(f"Clear negative result: {res_neg.status} (expected NOT_APPLICABLE)")
        assert res_neg.status == OutcomeStatus.NOT_APPLICABLE
        
        # Missing data: category is None
        prof_missing = BusinessProfile(
            activity="food_manufacturing",
            products=[Product(category=None, prepackaged=True)],
            as_at_date="2024-01-01",
        )
        res_missing = evaluate_rule(r_domain, prof_missing)
        print(f"Missing data result: {res_missing.status}, missing_fields={res_missing.missing_fields} (expected CONDITIONAL_MISSING_DATA)")
        assert res_missing.status == OutcomeStatus.CONDITIONAL_MISSING_DATA
        assert "products.category" in res_missing.missing_fields
        
        # Temporal check: before commencement (e.g. 2010-01-01)
        prof_temp = BusinessProfile(
            activity="food_manufacturing",
            products=[Product(category="fish", prepackaged=True)],
            as_at_date="2010-01-01",
        )
        res_temp = evaluate_rule(r_domain, prof_temp)
        print(f"Before commencement result: {res_temp.status}, temporal_status={res_temp.temporal_status} (expected NOT_APPLICABLE)")
        assert res_temp.status == OutcomeStatus.NOT_APPLICABLE
        assert res_temp.temporal_status == "NOT_YET_IN_FORCE"

if __name__ == "__main__":
    test_rule_candidate()

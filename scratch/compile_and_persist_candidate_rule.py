import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.src.db.session import session_scope
from backend.src.db.models import ClauseORM, RuleORM, SourceDocumentORM
from backend.src.db.repositories import rule_domain_to_orm_dict
from backend.src.engine.verifier import RuleVerifier
from backend.src.models.domain import (
    Rule, Source, Validity, AppliesIf, Condition, Obligation, Verification
)

def compile_and_persist_single_rule():
    rule_id = "RULE-COLOURING-SEAFOOD-PROHIBITION"
    clause_id = "CLAUSE-DOC_3CD9948D2C334D08A11DD5BC9CC1F1A1EC053D6E819EA30F205687DDA7C342C7-REGULATION-5-IV"
    
    with session_scope() as session:
        # Check idempotency
        existing_rule = session.get(RuleORM, rule_id)
        if existing_rule is not None:
            print(f"Rule {rule_id} already exists in database (idempotent no-op).")
            return rule_id, False

        # Verify clause exists
        clause = session.get(ClauseORM, (clause_id, 1))
        assert clause is not None, f"Clause {clause_id} not found in database!"
        
        doc = session.get(SourceDocumentORM, clause.document_id)
        assert doc is not None, f"Source document {clause.document_id} not found!"

        quote = "(1) in regulation 5 thereof, by the substitution for paragraph (iv) of that regulation of the following:-\n“(iv) fish, molluscs, crustaceans and echinoderms;”."

        rule_data = {
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
                "status": "PENDING_REVIEW",
                "extraction_model": "rule_compiler_phase_4_3",
                "agreement": False,
                "reason": None,
            },
            "outcome_type": "STANDARD",
            "is_synthetic": False,
            "is_gold_rule": False,
        }

        # Validate with Pydantic domain model
        domain_rule = Rule(
            rule_id=rule_data["rule_id"],
            source=Source(**rule_data["source"]),
            validity=Validity(**rule_data["validity"]),
            applies_if=AppliesIf(all=[Condition(**c) for c in rule_data["applies_if"]["all"]]),
            exceptions=[],
            obligation=Obligation(**rule_data["obligation"]),
            verification=Verification(**rule_data["verification"]),
            is_synthetic=False,
        )

        # Validate with deterministic verifier
        verifier = RuleVerifier()
        report = verifier.verify(
            domain_rule,
            source_text=clause.text,
            metadata={"published": "2011-01-14", "commences": "2011-01-14"},
        )
        assert report.is_valid, f"Rule verification failed: {report.issues}"

        # Convert to ORM dictionary
        orm_dict = rule_domain_to_orm_dict(domain_rule, clause_id=clause.clause_id, clause_version=1)
        orm_dict["review_status"] = "PENDING_REVIEW"
        orm_dict["is_gold_rule"] = False
        orm_dict["is_synthetic"] = False
        orm_dict["outcome_type"] = "STANDARD"
        orm_dict["verification_report"] = {
            "status": "verified",
            "reason": None,
            "justification": None,
        }

        rule_orm = RuleORM(**orm_dict)
        session.add(rule_orm)
        session.flush()
        print(f"Successfully compiled, verified, and persisted rule {rule_id} into PostgreSQL.")
        return rule_id, True

if __name__ == "__main__":
    compile_and_persist_single_rule()

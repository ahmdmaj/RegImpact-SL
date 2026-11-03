import sys
import json
from pathlib import Path

sys.path.insert(0, ".")

from backend.src.db.session import session_scope
from backend.src.db.models import RuleORM
from backend.src.db.repositories import rule_orm_to_domain
from backend.src.engine.applicability import evaluate_rule
from backend.src.models.domain import BusinessProfile, Product, Market, OutcomeStatus

def test_deterministic_rules():
    with session_scope() as session:
        r3_orm = session.query(RuleORM).filter_by(rule_id="RULE-FCAU-2494-47-REG-3").first()
        r3_b2b_orm = session.query(RuleORM).filter_by(rule_id="RULE-FCAU-2494-47-REG-3-B2B").first()
        
        assert r3_orm is not None, "RULE-FCAU-2494-47-REG-3 not found!"
        assert r3_b2b_orm is not None, "RULE-FCAU-2494-47-REG-3-B2B not found!"
        
        r3 = rule_orm_to_domain(r3_orm)
        r3_b2b = rule_orm_to_domain(r3_b2b_orm)
        
        profiles = [
            {
                "case": "Case 1: Retail Food Manufacturer (Prepackaged) -> Should be APPLICABLE for REG-3, NOT_APPLICABLE for B2B",
                "profile": BusinessProfile(
                    business_id="BIZ-TEST-RETAIL-001",
                    activity="food_manufacturing",
                    products=[Product(category="bakery", prepackaged=True)],
                    market=Market(domestic=True, export_flag=False, b2b_only=False),
                    employee_count=15,
                ),
            },
            {
                "case": "Case 2: B2B Food Manufacturer -> Should be APPLICABLE for REG-3-B2B",
                "profile": BusinessProfile(
                    business_id="BIZ-TEST-B2B-002",
                    activity="food_manufacturing",
                    products=[Product(category="bulk_flour", prepackaged=True)],
                    market=Market(domestic=True, export_flag=False, b2b_only=True),
                    employee_count=25,
                ),
            },
            {
                "case": "Case 3: Non-Food Textile Business -> Should be NOT_APPLICABLE",
                "profile": BusinessProfile(
                    business_id="BIZ-TEST-TEXTILE-003",
                    activity="textile_manufacturing",
                    products=[Product(category="textiles", prepackaged=False)],
                    employee_count=50,
                ),
            },
            {
                "case": "Case 4: Missing Data (Missing 'products.prepackaged') -> Should be CONDITIONAL_MISSING_DATA",
                "profile": BusinessProfile(
                    business_id="BIZ-TEST-INCOMPLETE-004",
                    activity="food_manufacturing",
                    products=None,
                    employee_count=5,
                ),
            },
        ]
        
        eval_date = "2026-07-01"
        outcomes = []
        
        for p_info in profiles:
            p = p_info["profile"]
            case_name = p_info["case"]
            
            res_r3 = evaluate_rule(rule=r3, profile=p, as_at_date=eval_date)
            res_b2b = evaluate_rule(rule=r3_b2b, profile=p, as_at_date=eval_date)
            
            outcomes.append({
                "case": case_name,
                "profile_id": p.business_id,
                "REG-3": {
                    "status": res_r3.status.value,
                    "reason": res_r3.reason,
                    "missing_fields": res_r3.missing_fields,
                    "counterfactuals": res_r3.counterfactuals,
                },
                "REG-3-B2B": {
                    "status": res_b2b.status.value,
                    "reason": res_b2b.reason,
                    "missing_fields": res_b2b.missing_fields,
                }
            })
            
        print("DETERMINISTIC_EVAL_START")
        print(json.dumps(outcomes, indent=2))
        print("DETERMINISTIC_EVAL_END")

if __name__ == "__main__":
    test_deterministic_rules()

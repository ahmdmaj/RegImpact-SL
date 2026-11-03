from backend.src.db.session import session_scope
from backend.src.db.models import RuleORM
from backend.src.db.repositories import rule_orm_to_domain
from backend.src.engine.applicability import evaluate_rule
from backend.src.models.domain import BusinessProfile, Product, Market

with session_scope() as s:
    r3 = rule_orm_to_domain(s.query(RuleORM).filter_by(rule_id="RULE-FCAU-2494-47-REG-3").first())
    p = BusinessProfile(
        business_id="BIZ-TEST-RETAIL-001",
        activity="food_manufacturing",
        products=[Product(category="bakery", prepackaged=True)],
        market=Market(domestic=True, export_flag=False, b2b_only=False),
        packaged_in_presence_of_purchaser=False,
    )
    res = evaluate_rule(r3, p, as_at_date="2026-07-01")
    print("Status:", res.status.value)
    print("Reason:", res.reason)
    print("Trace:", res.evaluation_trace)

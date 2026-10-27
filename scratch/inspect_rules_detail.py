import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.src.db.session import session_scope
from backend.src.db.models import RuleORM

with session_scope() as session:
    rules = session.query(RuleORM).filter(RuleORM.is_synthetic == False).all()
    print(f"Total authentic rules in DB: {len(rules)}")
    for r in rules:
        print(f"RULE: {r.rule_id} | clause_id={r.clause_id} | status={r.review_status} | outcome_type={r.outcome_type}")
        print(f"  applies_if: {r.applies_if}")
        print(f"  exceptions: {r.exceptions}")
        print(f"  obligation: {r.obligation}")
        print(f"  validity: {r.validity}")
        src = r.source or {}
        q = src.get("quote_span", "")
        print(f"  source: clause={src.get('clause')} page={src.get('page')} gazette={src.get('gazette_no')}")
        print(f"  quote_span: {q[:100]}...")
        print("-" * 60)

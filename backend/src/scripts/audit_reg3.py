import sys
import json
from pathlib import Path

sys.path.insert(0, ".")
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from backend.src.db.session import session_scope
from backend.src.db.models import RuleORM, ClauseORM

with session_scope() as db:
    rules = db.query(RuleORM).filter(RuleORM.rule_id.in_(["RULE-FCAU-2494-47-REG-3", "RULE-FCAU-2494-47-REG-3-B2B"])).all()
    for r in rules:
        print(f"=== {r.rule_id} ===")
        print("clause_id:", r.clause_id)
        print("outcome_type:", r.outcome_type)
        print("applies_if:", json.dumps(r.applies_if, indent=2))
        print("exceptions:", json.dumps(r.exceptions, indent=2))
        print("obligation:", json.dumps(r.obligation, indent=2))
        print("validity:", json.dumps(r.validity, indent=2))
        print("source:", json.dumps(r.source, indent=2))
        print("verification_report:", json.dumps(r.verification_report, indent=2))

    clause = db.query(ClauseORM).filter(ClauseORM.clause_id == "CLAUSE-DOC_GAZETTE_2494_47-REGULATION-3").first()
    if clause:
        print("\n=== CLAUSE TEXT (CLAUSE-DOC_GAZETTE_2494_47-REGULATION-3) ===")
        print(clause.text)

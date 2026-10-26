import json
from sqlalchemy import create_engine, text

engine = create_engine('postgresql://regimpact:regimpact@localhost:5432/regimpact')
with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT rule_id, clause_id, review_status, source, applies_if, obligation, exceptions
        FROM rules 
        WHERE rule_id IN ('RULE-FLAVOUR-INFANT-PROHIBITION', 'RULE-FLAVOUR-LABEL-DECLARATION', 'RULE-PRESERVATIVE-JAM-JELLY-LIMIT')
    """)).fetchall()
    for r in rows:
        print(f"=== {r[0]} (clause: {r[1]}, status: {r[2]}) ===")
        print("Source:", json.dumps(r[3], indent=2))
        print("Applies if:", json.dumps(r[4], indent=2))
        print("Obligation:", json.dumps(r[5], indent=2))
        print("Exceptions:", json.dumps(r[6], indent=2))
        print()

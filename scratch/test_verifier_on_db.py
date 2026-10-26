import sys
import os
sys.path.insert(0, os.path.abspath("."))

import json
from sqlalchemy import create_engine, text
from backend.src.engine.verifier import RuleVerifier
from backend.src.models.domain import Rule

engine = create_engine('postgresql://regimpact:regimpact@localhost:5432/regimpact')
verifier = RuleVerifier()

with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT r.rule_id, r.clause_id, r.source, r.applies_if, r.obligation, r.validity, r.exceptions,
               c.text, p.raw_text
        FROM rules r
        JOIN clauses c ON r.clause_id = c.clause_id AND r.clause_version = c.version_number
        JOIN source_documents d ON c.document_id = d.id
        JOIN document_pages p ON d.id = p.document_id AND (r.source->>'page')::int = p.page_number
        WHERE r.rule_id IN ('RULE-FLAVOUR-INFANT-PROHIBITION', 'RULE-FLAVOUR-LABEL-DECLARATION', 'RULE-PRESERVATIVE-JAM-JELLY-LIMIT')
    """)).fetchall()

    for r in rows:
        rule_id = r[0]
        clause_id = r[1]
        source_meta = r[2]
        applies_if = r[3]
        obligation = r[4]
        validity = r[5]
        exceptions = r[6] or []
        clause_text = r[7]
        page_raw_text = r[8]

        rule_dict = {
            "rule_id": rule_id,
            "clause_id": clause_id,
            "clause_version": 1,
            "outcome_type": "STANDARD",
            "applies_if": applies_if,
            "exceptions": exceptions,
            "obligation": obligation,
            "validity": validity,
            "source": source_meta
        }

        rule_obj = Rule(**rule_dict)
        report = verifier.verify(rule_obj, page_raw_text=page_raw_text)
        print(f"=== {rule_id} ===")
        print(f"Is valid: {report.is_valid}")
        print(f"Quote found: {report.quote_found_on_page}")
        print(f"Quote span in DB: {json.dumps(source_meta.get('quote_span'))}")
        print(f"Clause in DB: {source_meta.get('clause')}")
        print(f"Page in DB: {source_meta.get('page')}")
        if report.errors:
            print("Errors:", report.errors)
        if report.warnings:
            print("Warnings:", report.warnings)
        print()

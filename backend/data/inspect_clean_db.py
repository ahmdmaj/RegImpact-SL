from backend.src.db.session import session_scope
from sqlalchemy import text

with session_scope() as session:
    doc = session.execute(
        text("SELECT id, title, authority, instrument_type, gazette_no, publication_date, sha256_hash, file_path, page_count FROM source_documents WHERE id = 'doc_labelling_regulations_final_2026'")
    ).fetchone()
    print("Document:", doc)

    clauses = session.execute(
        text("SELECT clause_id, clause_number, start_page, end_page, char_start, char_end, text FROM clauses WHERE document_id = 'doc_labelling_regulations_final_2026'")
    ).fetchall()
    print(f"Clauses ({len(clauses)}):")
    for c in clauses:
        print(f"  {c[0]} | num: {c[1]} | pages: {c[2]}-{c[3]} | chars: {c[4]}-{c[5]}")
        print("    Preview:", repr(c[6][:100]))

    rules = session.execute(
        text("SELECT rule_id, clause_id, review_status, outcome_type FROM rules WHERE clause_id LIKE '%LABELLING_REGULATIONS_FINAL%'")
    ).fetchall()
    print(f"Rules ({len(rules)}):")
    for r in rules:
        print(f"  {r[0]} | clause: {r[1]} | status: {r[2]} | outcome: {r[3]}")

import json
from sqlalchemy import create_engine, text

engine = create_engine('postgresql://regimpact:regimpact@localhost:5432/regimpact')
with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT clause_id, clause_number, start_page, text
        FROM clauses 
        WHERE document_id = 'doc_b78479b6b08d12e11fd27cfc39677d5a284bc147bf16a777eafb495b86f4135a'
        ORDER BY clause_id
    """)).fetchall()
    for r in rows:
        print(f"Clause: {r[0]} | Clause No: {r[1]} | Page: {r[2]}")
        print("Text snippet:", r[3][:140].replace('\n', ' '))
        print()

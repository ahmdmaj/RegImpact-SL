import sys
sys.path.insert(0, ".")

from backend.src.db.session import session_scope
from backend.src.db.models import (
    SourceDocumentORM,
    ClauseORM,
    RuleORM,
    is_synthetic_document,
    is_synthetic_clause,
    is_synthetic_rule,
)

with session_scope() as db:
    docs = db.query(SourceDocumentORM).all()
    clauses = db.query(ClauseORM).all()
    rules = db.query(RuleORM).all()

    auth_docs = [d for d in docs if not is_synthetic_document(d)]
    synth_docs = [d for d in docs if is_synthetic_document(d)]

    auth_clauses = [c for c in clauses if not is_synthetic_clause(c)]
    synth_clauses = [c for c in clauses if is_synthetic_clause(c)]
    verif_emb_clauses = [c for c in clauses if c.embedding_verified and not is_synthetic_clause(c)]

    auth_rules = [r for r in rules if not is_synthetic_rule(r)]
    synth_rules = [r for r in rules if is_synthetic_rule(r)]

    print(f"=== DATABASE COUNTS SUMMARY ===")
    print(f"Total Source Documents: {len(docs)}")
    print(f"  - Authentic / Promulgated: {len(auth_docs)}")
    print(f"  - Synthetic / Quarantined / Excluded: {len(synth_docs)}")
    print(f"Total Clauses: {len(clauses)}")
    print(f"  - Authentic Clauses: {len(auth_clauses)}")
    print(f"  - Verified Embeddings on Authentic Clauses: {len(verif_emb_clauses)}")
    print(f"  - Synthetic / Quarantined Clauses: {len(synth_clauses)}")
    print(f"Total Rules: {len(rules)}")
    print(f"  - Authentic Promulgated Rules: {len(auth_rules)} (all {auth_rules[0].review_status if auth_rules else 'N/A'})")
    print(f"  - Synthetic / Quarantined Rules: {len(synth_rules)}")
    for r in auth_rules:
        print(f"    * [{r.rule_id}] status={r.review_status} gold={r.is_gold_rule} clause={r.clause_id}")

import sys
import json
from pathlib import Path

sys.path.insert(0, ".")
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from backend.src.db.session import session_scope
from backend.src.db.models import (
    SourceDocumentORM,
    ClauseORM,
    RuleORM,
    HumanReviewAuditORM,
)

def main():
    with session_scope() as db:
        docs = db.query(SourceDocumentORM).all()
        print(f"Total SourceDocumentORM: {len(docs)}")
        
        doc_summary = []
        for d in docs:
            clauses = db.query(ClauseORM).filter_by(document_id=d.id).all()
            rules = (
                db.query(RuleORM)
                .join(ClauseORM, RuleORM.clause_id == ClauseORM.clause_id)
                .filter(ClauseORM.document_id == d.id)
                .all()
            )
            doc_summary.append({
                "id": d.id,
                "title": d.title,
                "sha256": d.sha256_hash,
                "is_synthetic": d.is_synthetic,
                "clauses_count": len(clauses),
                "clauses": [
                    {
                        "clause_id": c.clause_id,
                        "clause_number": c.clause_number,
                        "pages": f"{c.start_page}-{c.end_page}",
                        "verified_emb": c.embedding_verified,
                        "is_synthetic": c.is_synthetic,
                        "text_snippet": c.text[:80].replace("\n", " "),
                    }
                    for c in clauses
                ],
                "rules_count": len(rules),
                "rules": [
                    {
                        "rule_id": r.rule_id,
                        "clause_id": r.clause_id,
                        "status": r.review_status,
                        "is_gold": getattr(r, "is_gold_rule", False),
                        "is_synthetic": r.is_synthetic,
                    }
                    for r in rules
                ],
            })
            
        print("\n--- ALL DOCUMENTS SUMMARY ---")
        for ds in doc_summary:
            print(f"Doc: {ds['id']} | synth={ds['is_synthetic']} | clauses={ds['clauses_count']} | rules={ds['rules_count']}")
            for cl in ds["clauses"]:
                print(f"   [Clause] {cl['clause_id']} (Num: {cl['clause_number']}, Pages: {cl['pages']}, EmbVerified: {cl['verified_emb']})")
            for rl in ds["rules"]:
                print(f"   [Rule] {rl['rule_id']} (Clause: {rl['clause_id']}, Status: {rl['status']}, Gold: {rl['is_gold']})")

        # Check all rules in DB
        all_rules = db.query(RuleORM).all()
        print(f"\nTotal RuleORM: {len(all_rules)}")
        for r in all_rules:
            print(f"Rule: {r.rule_id} | Clause: {r.clause_id} | Status: {r.review_status} | Gold: {getattr(r, 'is_gold_rule', False)} | Synth: {r.is_synthetic}")


        # Check HumanReviewAuditORM
        audits = db.query(HumanReviewAuditORM).all()
        print(f"\nTotal HumanReviewAuditORM: {len(audits)}")
        for a in audits:
            print(f"Audit: Rule {a.rule_id} | Decision: {a.decision} | Reviewer: {a.reviewer_id} ({a.reviewer_role}) | Timestamp: {a.reviewed_at}")

        # Benchmark scenarios
        scenarios_path = Path("backend/data/benchmark/scenarios.jsonl")
        if scenarios_path.exists():
            scenarios = [json.loads(line) for line in scenarios_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            print(f"\nTotal benchmark scenarios in scenarios.jsonl: {len(scenarios)}")
            types = {}
            for s in scenarios:
                t = s.get("scenario_type") or s.get("type", "unknown")
                types[t] = types.get(t, 0) + 1
            print("Scenario types:", types)


if __name__ == "__main__":
    main()

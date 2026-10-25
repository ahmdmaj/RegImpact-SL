import sys, json
from pathlib import Path
sys.path.insert(0, '.')
from backend.src.db.session import session_scope
from backend.src.db.models import SourceDocumentORM, ClauseORM, RuleORM

with session_scope() as db:
    docs = db.query(SourceDocumentORM).all()
    print(f"=== SOURCE DOCUMENTS IN DB ({len(docs)}) ===")
    for d in docs:
        c_count = db.query(ClauseORM).filter(ClauseORM.document_id == d.id).count()
        emb_count = db.query(ClauseORM).filter(
            ClauseORM.document_id == d.id,
            ClauseORM.embedding_verified == True
        ).count()
        print(f"  [{d.id}] is_synthetic={d.is_synthetic} title=\"{d.title[:50]}\" | {c_count} clauses ({emb_count} verified embs)")

    total_clauses = db.query(ClauseORM).count()
    verified_embs = db.query(ClauseORM).filter(ClauseORM.embedding_verified == True).count()
    synthetic_clauses = db.query(ClauseORM).filter(ClauseORM.is_synthetic == True).count()

    print(f"\n=== CLAUSE SUMMARY ===")
    print(f"  Total Clauses: {total_clauses}")
    print(f"  Verified Embeddings: {verified_embs}")
    print(f"  Synthetic/Quarantined Clauses: {synthetic_clauses}")

    rules = db.query(RuleORM).all()
    print(f"\n=== RULES IN DB ({len(rules)}) ===")
    for r in rules:
        print(f"  [{r.rule_id}] status={r.review_status} is_synthetic={r.is_synthetic} clause={r.clause_id}")

    # Benchmark scenarios in JSONL
    benchmark_file = Path("backend/data/benchmark/scenarios.jsonl")
    if benchmark_file.exists():
        scenarios = []
        with open(benchmark_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    scenarios.append(json.loads(line))
        print(f"\n=== BENCHMARK SCENARIOS IN {benchmark_file} ({len(scenarios)}) ===")
        types = {}
        for sc in scenarios:
            st = sc.get("scenario_type", "unknown")
            types[st] = types.get(st, 0) + 1
        for st, count in types.items():
            print(f"  {st}: {count}")
    else:
        print(f"\nBenchmark file {benchmark_file} does not exist.")

import sys
sys.path.insert(0, ".")

from backend.src.db.session import session_scope
from backend.src.engine.retrieval import DenseRetrievalEngine, HybridRetrievalEngine
from backend.src.extraction.embedding_client import SentenceTransformerEmbeddingClient

client = SentenceTransformerEmbeddingClient(model="BAAI/bge-base-en-v1.5")

with session_scope() as db:
    dense_engine = DenseRetrievalEngine(db=db, embedding_client=client)
    hybrid_engine = HybridRetrievalEngine(db=db, dense_engine=dense_engine)

    query = "business-to-business food products labelling not for retail sale"
    print(f"Testing query: {query!r}")
    results = hybrid_engine.search(query, top_k=5)
    print(f"Returned {len(results)} results:")
    for r in results:
        print(f"  Rank {r.rank}: {r.clause_id} | doc: {r.document_id} | score: {r.score:.4f} | method: {r.retrieval_method}")
        print(f"    Snippet: {r.text[:90]}...")

    clause_ids = [r.clause_id for r in results]
    assert "TEST-VEC-CLAUSE-A" not in clause_ids, "TEST-VEC-CLAUSE-A leaked into search!"
    assert "TEST-VEC-CLAUSE-B" not in clause_ids, "TEST-VEC-CLAUSE-B leaked into search!"
    print("\nIntegrity check PASSED: Quarantined test vectors successfully excluded.")
    print(f"Top 1 match: {clause_ids[0] if clause_ids else 'None'}")

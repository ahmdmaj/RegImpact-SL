import sys
sys.path.insert(0, ".")

from backend.src.db.session import session_scope
from backend.src.engine.retrieval import BM25RetrievalEngine, DenseRetrievalEngine, HybridRetrievalEngine
from backend.src.extraction.embedding_client import SentenceTransformerEmbeddingClient

with session_scope() as db:
    client = SentenceTransformerEmbeddingClient(model="BAAI/bge-base-en-v1.5")
    dense = DenseRetrievalEngine(db=db, embedding_client=client, allow_unverified=False)
    query = "commercial cold storage facility operating at temperature below minus 18"
    results = dense.search(query, top_k=5)
    print("DENSE SEARCH RESULTS:")
    for r in results:
        print(f"  [{r.clause_id}] score={r.score} doc={r.document_id} synth={r.is_synthetic} title={r.document_title}")

    bm25 = BM25RetrievalEngine(db=db)
    bm25_res = bm25.search(query, top_k=5)
    print("\nBM25 SEARCH RESULTS:")
    for r in bm25_res:
        print(f"  [{r.clause_id}] score={r.score} doc={r.document_id} synth={r.is_synthetic} title={r.document_title}")

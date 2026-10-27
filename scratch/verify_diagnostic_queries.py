"""Verification of diagnostic retrieval queries against authentic indexed PostgreSQL clauses."""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend can be imported
sys.path.insert(0, os.path.abspath("."))

from backend.src.engine.retrieval import (
    BM25RetrievalEngine,
    DenseRetrievalEngine,
    HybridRetrievalEngine,
    build_retrieval_query,
)
from backend.src.extraction.embedding_client import get_embedding_client
from backend.src.models.domain import BusinessProfile, Product

DB_URL = "postgresql://regimpact:regimpact@localhost:5432/regimpact"

def run_diagnostics():
    engine = create_engine(DB_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    print("=" * 80)
    print("PHASE 4.5: DIAGNOSTIC RETRIEVAL VERIFICATION")
    print("=" * 80)

    # 1. Inspect configured embedding client
    emb_client = get_embedding_client(allow_mock_fallback=False)
    prov = emb_client.get_provenance() if hasattr(emb_client, "get_provenance") else {}
    print(f"Embedding Provider: {emb_client.provider_name}")
    print(f"Embedding Model:    {emb_client.model_name}")
    print(f"Dimension:          {emb_client.dimension}")
    print(f"Is Verified:        {emb_client.is_verified}")
    print(f"Provenance:         {prov}")
    print("-" * 80)

    # 2. Setup engines
    bm25 = BM25RetrievalEngine(db)
    dense = DenseRetrievalEngine(db, embedding_client=emb_client, allow_unverified=False)
    hybrid = HybridRetrievalEngine(db, bm25_engine=bm25, dense_engine=dense)

    # Realistic profile query construction
    sample_profile = BusinessProfile(
        business_id="BIZ-SEAFOOD-001",
        activity="food_manufacturing",
        industry="food_and_beverage",
        products=[
            Product(name="Frozen Raw Prawns", category="fish", prepackaged=True),
        ],
    )
    built_query = build_retrieval_query(sample_profile)

    queries = [
        ("Diagnostic Query 1", "seafood coloring prohibition"),
        ("Diagnostic Query 2", "colouring substances fish molluscs crustaceans echinoderms"),
        ("Diagnostic Query 3 (Built from Profile)", built_query),
    ]

    for label, q_text in queries:
        print(f"\n>>> {label}: '{q_text}'")
        
        # Test query embedding
        try:
            q_vec = emb_client.embed_query(q_text)
            print(f"  [+] Query embedding succeeded: {len(q_vec)} dimensions, norm={sum(x*x for x in q_vec)**0.5:.4f}")
        except Exception as e:
            print(f"  [-] Query embedding failed: {e}")
            continue

        # Test dense search
        try:
            dense_res = dense.search(q_text, top_k=5)
            print(f"  [+] Dense retrieval executed: {len(dense_res)} candidates returned.")
            for r in dense_res[:3]:
                print(f"      - Dense Rank {r.rank}: {r.clause_id} | score={r.score:.4f} | doc={r.document_id}")
        except Exception as e:
            print(f"  [-] Dense retrieval failed: {e}")

        # Test BM25 search
        try:
            bm25_res = bm25.search(q_text, top_k=5)
            print(f"  [+] BM25 retrieval executed: {len(bm25_res)} candidates returned.")
            for r in bm25_res[:3]:
                print(f"      - BM25 Rank {r.rank}: {r.clause_id} | score={r.score:.4f} | doc={r.document_id}")
        except Exception as e:
            print(f"  [-] BM25 retrieval failed: {e}")

        # Test Hybrid search
        try:
            hybrid_res = hybrid.search(q_text, top_k=5)
            print(f"  [+] Hybrid retrieval executed: {len(hybrid_res)} candidates returned.")
            if hybrid_res:
                top = hybrid_res[0]
                print(f"      Actual method:   {top.retrieval_method}")
                print(f"      Dense active:    {top.metadata.get('dense_active')}")
                print(f"      BM25 active:     {top.metadata.get('bm25_active')}")
                print(f"      Fallback reason: {top.metadata.get('fallback_reason')}")
                print("      Top 5 Hybrid Candidates:")
                for r in hybrid_res:
                    print(f"        Rank {r.rank}: {r.clause_id} (score={r.score:.5f}) doc={r.document_id}")
                    snippet = r.text[:120].encode('ascii', 'replace').decode('ascii')
                    print(f"               text snippet: {snippet}...")
        except Exception as e:
            print(f"  [-] Hybrid retrieval failed: {e}")

    db.close()

if __name__ == "__main__":
    run_diagnostics()

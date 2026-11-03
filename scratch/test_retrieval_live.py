import sys
import json
from pathlib import Path

sys.path.insert(0, ".")

from backend.src.db.session import session_scope
from backend.src.engine.retrieval import (
    BM25RetrievalEngine,
    DenseRetrievalEngine,
    HybridRetrievalEngine,
)

def test_retrieval():
    test_queries = [
        {
            "topic": "Prepackaged Food Labelling & Advertising",
            "query": "prepackaged food labelling advertising mandatory retail sale requirements",
        },
        {
            "topic": "Sugar Level Colour Coding in Sweetened Beverages",
            "query": "sugar levels colour coding logo red amber green sweetened beverages",
        },
        {
            "topic": "Permitted Colouring in Seafood Prohibition",
            "query": "food colouring prohibition raw meat fresh fish molluscs crustaceans",
        },
        {
            "topic": "Preservatives in Jams and Jellies",
            "query": "permitted preservatives fruit jam jelly sulphur dioxide benzoic acid",
        },
        {
            "topic": "Flavouring Substances in Infant Food Prohibition",
            "query": "flavouring substances flavour enhancers infant foods prohibition",
        },
        {
            "topic": "Gazette 2332/03 Salt Iodization",
            "query": "iodization of salt potassium iodate packaging standards",
        }
    ]

    with session_scope() as session:
        bm25 = BM25RetrievalEngine(session)
        dense = DenseRetrievalEngine(session)
        hybrid = HybridRetrievalEngine(session)

        results = []

        print(f"Dense engine embedding_client: {type(dense.embedding_client).__name__ if dense.embedding_client else None}")
        print(f"Dense engine is_intentional_bm25: {dense.is_intentional_bm25}")
        print(f"Dense engine init_error: {dense.init_error}")

        for tq in test_queries:
            q = tq["query"]
            topic = tq["topic"]

            # 1. BM25 search
            bm25_res = bm25.search(q, top_k=3, filters={"include_synthetic": False})
            
            # 2. Dense search
            dense_res = dense.search(q, top_k=3, filters={"include_synthetic": False})
            
            # 3. Hybrid search
            hybrid_res = hybrid.search(q, top_k=3, filters={"include_synthetic": False})

            item = {
                "topic": topic,
                "query": q,
                "bm25": [
                    {
                        "rank": r.rank,
                        "clause_id": r.clause_id,
                        "document_id": r.document_id,
                        "document_title": r.document_title,
                        "score": r.score,
                        "has_approved_rule": r.has_approved_rule,
                        "coverage_gap": r.coverage_gap,
                        "is_synthetic": r.is_synthetic,
                    }
                    for r in bm25_res
                ],
                "dense": [
                    {
                        "rank": r.rank,
                        "clause_id": r.clause_id,
                        "document_id": r.document_id,
                        "document_title": r.document_title,
                        "score": r.score,
                        "has_approved_rule": r.has_approved_rule,
                        "coverage_gap": r.coverage_gap,
                        "is_synthetic": r.is_synthetic,
                    }
                    for r in dense_res
                ],
                "hybrid": [
                    {
                        "rank": r.rank,
                        "clause_id": r.clause_id,
                        "document_id": r.document_id,
                        "document_title": r.document_title,
                        "score": r.score,
                        "retrieval_method": r.retrieval_method,
                        "has_approved_rule": r.has_approved_rule,
                        "coverage_gap": r.coverage_gap,
                        "is_synthetic": r.is_synthetic,
                        "metadata": r.metadata,
                    }
                    for r in hybrid_res
                ]
            }
            results.append(item)

        print("RETRIEVAL_TEST_START")
        print(json.dumps(results))
        print("RETRIEVAL_TEST_END")

if __name__ == "__main__":
    test_retrieval()

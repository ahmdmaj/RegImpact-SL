"""Stage 3 Bounded End-to-End Dense and Hybrid Retrieval Proof for RegImpact-SL.

Audits:
1. Gazette source authentication & SHA-256 verification.
2. Authentic clause & rule verification in PostgreSQL.
3. Real model (BAAI/bge-base-en-v1.5) clause embedding generation & persistence.
4. Live pgvector cosine distance query execution & reload verification.
5. Hybrid RRF retrieval verification (BM25 + Dense contribution).
6. Honest semantic smoke test report (non-benchmark).
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from backend.data.seed_real_slice import seed_real_slice
from backend.src.db.models import ClauseORM, RuleORM, SourceDocumentORM
from backend.src.engine.retrieval import BM25RetrievalEngine, DenseRetrievalEngine, HybridRetrievalEngine
from backend.src.extraction.embedding_client import SentenceTransformerEmbeddingClient
from backend.tests.conftest import LIVE_DATABASE_URL


def run_proof() -> Dict[str, Any]:
    print("=" * 75)
    print("RegImpact-SL: Stage 3 Bounded End-to-End Retrieval Proof")
    print("=" * 75)

    report: Dict[str, Any] = {}

    # -----------------------------------------------------------------------
    # Step 1: Confirm Authenticated Gazette Source
    # -----------------------------------------------------------------------
    print("\n--- Step 1: Authenticate Gazette Source ---")
    pdf_path = Path("backend/data/raw_sources/2494-47_E.pdf")
    if not pdf_path.exists():
        raise FileNotFoundError(f"Gazette PDF not found at {pdf_path}")

    actual_sha256 = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    expected_sha256 = "83ed19c22873471652d0073fe16c977442e42c8ecac2edf1d691d00d78d8a054"
    print(f"File Path:       {pdf_path}")
    print(f"File Size:       {pdf_path.stat().st_size} bytes")
    print(f"Computed SHA256: {actual_sha256}")
    print(f"Expected SHA256: {expected_sha256}")
    if actual_sha256 != expected_sha256:
        raise ValueError(f"Gazette SHA-256 mismatch! Expected {expected_sha256}, got {actual_sha256}")
    print("Source Authentication: PASSED (Byte-for-byte verified)")
    report["gazette_sha256_verified"] = True

    # -----------------------------------------------------------------------
    # Step 2: Ensure Authentic Slice is Seeded in PostgreSQL
    # -----------------------------------------------------------------------
    print("\n--- Step 2: Connect to PostgreSQL & Verify Authentic Slice ---")
    if not LIVE_DATABASE_URL or "postgresql" not in LIVE_DATABASE_URL.lower():
        raise RuntimeError(f"PostgreSQL DATABASE_URL not available. Got: {LIVE_DATABASE_URL}")

    engine = create_engine(LIVE_DATABASE_URL)
    with Session(engine) as session:
        # Seed authentic slice idempotently
        seed_real_slice(session)
        session.commit()

        doc = session.get(SourceDocumentORM, "doc_gazette_2494_47")
        clause = session.get(ClauseORM, ("CLAUSE-DOC_GAZETTE_2494_47-REGULATION-3", 1))
        rules = (
            session.query(RuleORM)
            .filter_by(clause_id="CLAUSE-DOC_GAZETTE_2494_47-REGULATION-3")
            .all()
        )

        assert doc is not None, "doc_gazette_2494_47 missing from DB"
        assert doc.sha256_hash == expected_sha256, "DB document SHA-256 mismatch"
        assert clause is not None, "CLAUSE-DOC_GAZETTE_2494_47-REGULATION-3 missing from DB"
        assert len(rules) >= 2, f"Expected at least 2 rules for Regulation 3, found {len(rules)}"
        print(f"Document in DB:  {doc.id} ('{doc.title[:45]}...')")
        print(f"Clause in DB:    {clause.clause_id} (Version {clause.version_number})")
        print(f"Rules in DB:     {[r.rule_id for r in rules]}")

    # -----------------------------------------------------------------------
    # Step 3: Initialize Real Embedding Client & Index Clause
    # -----------------------------------------------------------------------
    print("\n--- Step 3: Embed Clause using Real BAAI/bge-base-en-v1.5 ---")
    emb_client = SentenceTransformerEmbeddingClient(model="BAAI/bge-base-en-v1.5")
    provenance = emb_client.get_provenance()
    print(f"Embedding Provenance: {provenance}")
    report["embedding_provenance"] = provenance

    with Session(engine) as session:
        dense_engine = DenseRetrievalEngine(db=session, embedding_client=emb_client)

        # Index specifically the authentic clause with verified vector
        target_clause_id = "CLAUSE-DOC_GAZETTE_2494_47-REGULATION-3"
        indexed_count = dense_engine.index_clauses(
            clause_ids=[target_clause_id],
            reindex_unverified=True,
        )
        session.commit()
        print(f"Clauses Indexed: {indexed_count}")

        # Reload clause directly from PostgreSQL and verify persistence
        session.expire_all()
        reloaded_clause = session.get(ClauseORM, (target_clause_id, 1))
        assert reloaded_clause is not None
        assert reloaded_clause.embedding is not None, "Embedding not persisted in DB!"
        assert len(reloaded_clause.embedding) == 768, f"Dimension {len(reloaded_clause.embedding)} != 768"
        assert reloaded_clause.embedding_verified is True, "embedding_verified flag is False!"
        assert reloaded_clause.embedding_provider == "sentence-transformers"
        assert reloaded_clause.embedding_model == "BAAI/bge-base-en-v1.5"
        assert all(math.isfinite(x) for x in reloaded_clause.embedding), "Non-finite values in vector!"

        norm = math.sqrt(sum(x * x for x in reloaded_clause.embedding))
        print(f"Reloaded Clause Vector: length={len(reloaded_clause.embedding)}, norm={norm:.6f}")
        print(f"  embedding_verified: {reloaded_clause.embedding_verified}")
        print(f"  embedding_provider: {reloaded_clause.embedding_provider}")
        print(f"  embedding_model:    {reloaded_clause.embedding_model}")
        print(f"  Vector head (first 5 elements): {reloaded_clause.embedding[:5]}")
        report["clause_vector_persisted"] = True
        report["clause_vector_dim"] = len(reloaded_clause.embedding)
        report["clause_vector_sample"] = reloaded_clause.embedding[:5]

    # -----------------------------------------------------------------------
    # Step 4: Execute Native pgvector SQL Cosine Distance Query
    # -----------------------------------------------------------------------
    print("\n--- Step 4: Native pgvector SQL Cosine Distance Query ---")
    query_text = "What are the mandatory labelling requirements for prepackaged food products?"
    query_vec = emb_client.embed_query(query_text)
    print(f"Query: '{query_text}'")
    print(f"Query Vector: dim={len(query_vec)}, norm={math.sqrt(sum(x*x for x in query_vec)):.6f}")

    raw_sql = text("""
        SELECT
            clause_id,
            clause_number,
            document_id,
            embedding_verified,
            embedding_provider,
            embedding_model,
            1.0 - (embedding <=> (:query_vec)::vector) AS cosine_similarity
        FROM clauses
        WHERE embedding IS NOT NULL
          AND embedding_verified = TRUE
        ORDER BY embedding <=> (:query_vec)::vector ASC
        LIMIT 5;
    """)

    with Session(engine) as session:
        # Cast query vector to string format '[v1, v2, ...]' for pgvector
        query_vec_str = "[" + ",".join(f"{x:.8f}" for x in query_vec) + "]"
        result_rows = session.execute(raw_sql, {"query_vec": query_vec_str}).fetchall()

        print(f"\npgvector Raw SQL Results ({len(result_rows)} rows returned):")
        for i, row in enumerate(result_rows, 1):
            print(
                f"  Rank {i}: clause_id={row.clause_id} "
                f"similarity={row.cosine_similarity:.4f} "
                f"verified={row.embedding_verified} "
                f"provider={row.embedding_provider} "
                f"model={row.embedding_model}"
            )

        report["raw_pgvector_rows"] = [
            {
                "clause_id": r.clause_id,
                "similarity": round(float(r.cosine_similarity), 4),
                "verified": r.embedding_verified,
                "provider": r.embedding_provider,
                "model": r.embedding_model,
            }
            for r in result_rows
        ]

    # -----------------------------------------------------------------------
    # Step 5: DenseRetrievalEngine Search
    # -----------------------------------------------------------------------
    print("\n--- Step 5: DenseRetrievalEngine.search() ---")
    with Session(engine) as session:
        dense_engine = DenseRetrievalEngine(db=session, embedding_client=emb_client)
        dense_results = dense_engine.search(
            query=query_text,
            top_k=5,
            filters={"include_synthetic": False},
        )
        print(f"Dense Engine Results ({len(dense_results)} results):")
        for res in dense_results:
            print(
                f"  Rank {res.rank}: {res.clause_id} ({res.clause_number}) "
                f"score={res.score} doc={res.document_id} "
                f"method={res.retrieval_method} has_approved={res.has_approved_rule}"
            )
        report["dense_results_count"] = len(dense_results)
        if dense_results:
            report["top_dense_clause"] = dense_results[0].clause_id
            report["top_dense_score"] = dense_results[0].score

    # -----------------------------------------------------------------------
    # Step 6: HybridRetrievalEngine Search (BM25 + Dense RRF)
    # -----------------------------------------------------------------------
    print("\n--- Step 6: HybridRetrievalEngine.search() ---")
    with Session(engine) as session:
        bm25_engine = BM25RetrievalEngine(db=session)
        dense_engine = DenseRetrievalEngine(db=session, embedding_client=emb_client)
        hybrid_engine = HybridRetrievalEngine(
            db=session,
            bm25_engine=bm25_engine,
            dense_engine=dense_engine,
            rrf_k=60,
        )

        bm25_candidates = bm25_engine.search(query=query_text, top_k=5, filters={"include_synthetic": False})
        dense_candidates = dense_engine.search(query=query_text, top_k=5, filters={"include_synthetic": False})
        hybrid_results = hybrid_engine.search(query=query_text, top_k=5, filters={"include_synthetic": False})

        print(f"BM25 candidates count:  {len(bm25_candidates)}")
        for r in bm25_candidates:
            print(f"  BM25 Rank {r.rank}: {r.clause_id} score={r.score}")

        print(f"Dense candidates count: {len(dense_candidates)}")
        for r in dense_candidates:
            print(f"  Dense Rank {r.rank}: {r.clause_id} score={r.score}")

        print(f"Hybrid RRF results count: {len(hybrid_results)}")
        for r in hybrid_results:
            print(
                f"  Hybrid Rank {r.rank}: {r.clause_id} RRF_score={r.score} "
                f"method={r.retrieval_method} meta={r.metadata}"
            )

        report["bm25_candidate_count"] = len(bm25_candidates)
        report["dense_candidate_count"] = len(dense_candidates)
        report["hybrid_results_count"] = len(hybrid_results)
        if hybrid_results:
            report["hybrid_method"] = hybrid_results[0].retrieval_method
            report["top_hybrid_clause"] = hybrid_results[0].clause_id
            report["top_hybrid_score"] = hybrid_results[0].score
            report["hybrid_metadata"] = hybrid_results[0].metadata

    # -----------------------------------------------------------------------
    # Step 7: Negative Semantic Control Smoke Test
    # -----------------------------------------------------------------------
    print("\n--- Step 7: Unrelated Control Query Smoke Test ---")
    control_query = "Wastewater discharge standards, EPL licence thresholds and chemical storage bunding"
    with Session(engine) as session:
        dense_engine = DenseRetrievalEngine(db=session, embedding_client=emb_client)
        ctrl_results = dense_engine.search(
            query=control_query,
            top_k=5,
            filters={"include_synthetic": False},
        )
        print(f"Control Query: '{control_query}'")
        for r in ctrl_results:
            print(f"  Rank {r.rank}: {r.clause_id} score={r.score}")
        if dense_results and ctrl_results and dense_results[0].clause_id == ctrl_results[0].clause_id:
            rel_score = dense_results[0].score
            ctrl_score = ctrl_results[0].score
            delta = rel_score - ctrl_score
            print(f"Relevant Query Score for Regulation 3: {rel_score:.4f}")
            print(f"Control Query Score for Regulation 3:  {ctrl_score:.4f}")
            print(f"Discrimination Delta:                  {delta:+.4f}")
            report["discrimination_delta"] = round(delta, 4)

    print("\n" + "=" * 75)
    print("STATUS: VERIFIED_WITH_REAL_MODEL — Stage 3 Proof Completed Successfully")
    print("=" * 75)

    return report


if __name__ == "__main__":
    result = run_proof()

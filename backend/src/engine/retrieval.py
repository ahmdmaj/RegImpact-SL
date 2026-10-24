"""Component [B]: Multi-strategy regulatory clause retrieval engine for RegImpact-SL.

Provides:
  - RetrievalResult: structured schema for retrieved passages with coverage gap metadata.
  - BaseRetrievalEngine: common interface (search(query, top_k, filters)).
  - BM25RetrievalEngine: exact Okapi BM25 ranker over regulatory clauses.
  - DenseRetrievalEngine: semantic vector ranker with SQLite in-memory cosine fallback.
  - HybridRetrievalEngine: Reciprocal Rank Fusion (RRF) combining sparse and dense ranks.
  - Coverage gap identification: cross-references retrieved clauses against approved rules.

Design constraints (§2, Milestone 3 of alignment plan):
  1. Multi-dialect portability: zero dependency on external vector daemons during offline tests.
  2. RRF k=60 default parameter matching configuration.
  3. Coverage gap metadata explicitly flags clauses lacking approved rules.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter, defaultdict
import logging
import math
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.src.db.models import (
    ClauseORM,
    RuleORM,
    SourceDocumentORM,
    SYNTHETIC_DOCUMENT_IDS,
    SYNTHETIC_RULE_IDS,
    is_synthetic_clause,
)
from backend.src.extraction.embedding_client import BaseEmbeddingClient, MockEmbeddingClient, get_embedding_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result Schema
# ---------------------------------------------------------------------------

class RetrievalResult(BaseModel):
    """A ranked regulatory clause passage returned by a retrieval engine."""

    model_config = ConfigDict(extra="allow")

    clause_id: str
    clause_version: int
    clause_number: str
    text: str
    document_id: Optional[str] = None
    document_title: Optional[str] = None
    score: float
    retrieval_method: str  # "bm25" | "dense" | "hybrid_rrf"
    rank: int  # 1-indexed rank
    has_approved_rule: bool = False
    coverage_gap: bool = False
    is_synthetic: bool = False
    metadata: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Coverage Gap Helper
# ---------------------------------------------------------------------------

def cross_reference_coverage_gaps(
    db: Session,
    clause_ids: List[str],
    include_synthetic: bool = False,
) -> Set[str]:
    """Return the set of clause_ids that have at least one APPROVED Rule."""
    if not clause_ids:
        return set()

    query = db.query(RuleORM.clause_id).filter(
        RuleORM.clause_id.in_(clause_ids),
        RuleORM.review_status == "APPROVED",
    )
    if not include_synthetic:
        query = query.filter(
            RuleORM.is_synthetic.is_(False),
            ~RuleORM.rule_id.in_(SYNTHETIC_RULE_IDS),
        )
    rows = query.all()
    return {r[0] for r in rows}


# ---------------------------------------------------------------------------
# Base Interface
# ---------------------------------------------------------------------------

class BaseRetrievalEngine(ABC):
    """Common interface for regulatory retrieval engines."""

    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """Retrieve top_k passages matching query, applying optional filters."""
        pass


# ---------------------------------------------------------------------------
# BM25 Lexical Retrieval Engine
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    """Tokenize and normalize text into word tokens."""
    return re.findall(r"\w+", text.lower())


class BM25RetrievalEngine(BaseRetrievalEngine):
    """Okapi BM25 lexical ranker operating over regulatory clauses."""

    def __init__(
        self,
        db: Session,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.db = db
        self.k1 = k1
        self.b = b
        self._index_built = False
        self._corpus: List[Dict[str, Any]] = []
        self._doc_lengths: List[int] = []
        self._avgdl: float = 0.0
        self._doc_freqs: Dict[str, int] = defaultdict(int)
        self._term_freqs: List[Counter[str]] = []
        self._num_docs: int = 0

    def build_index(self) -> None:
        """Load all clauses from the database and build the BM25 index."""
        clauses = (
            self.db.query(ClauseORM, SourceDocumentORM)
            .outerjoin(SourceDocumentORM, ClauseORM.document_id == SourceDocumentORM.id)
            .all()
        )

        self._corpus = []
        self._doc_lengths = []
        self._doc_freqs = defaultdict(int)
        self._term_freqs = []

        for clause, doc in clauses:
            entry = {
                "clause_id": clause.clause_id,
                "clause_version": clause.version_number,
                "clause_number": clause.clause_number,
                "text": clause.text,
                "document_id": clause.document_id,
                "document_title": doc.title if doc else "",
                "is_compilable": clause.is_compilable,
                "is_synthetic": getattr(clause, "is_synthetic", False) or is_synthetic_clause(
                    clause, clause_id=clause.clause_id, document_id=clause.document_id
                ),
            }
            tokens = _tokenize(clause.text)
            tf = Counter(tokens)

            self._corpus.append(entry)
            self._doc_lengths.append(len(tokens))
            self._term_freqs.append(tf)

            for token in tf.keys():
                self._doc_freqs[token] += 1

        self._num_docs = len(self._corpus)
        self._avgdl = (
            sum(self._doc_lengths) / self._num_docs if self._num_docs > 0 else 0.0
        )
        self._index_built = True
        logger.info(
            "Built BM25 index over %d clauses (avg length: %.1f tokens)",
            self._num_docs,
            self._avgdl,
        )

    def _compute_idf(self, term: str) -> float:
        """Compute smoothed Robertson-Spärck Jones IDF."""
        df = self._doc_freqs.get(term, 0)
        return math.log(((self._num_docs - df + 0.5) / (df + 0.5)) + 1.0)

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """Perform BM25 search over indexed clauses."""
        if not self._index_built:
            self.build_index()

        query_tokens = _tokenize(query)
        if not query_tokens or self._num_docs == 0:
            return []

        # Score all candidate documents
        include_synthetic = bool(filters.get("include_synthetic", False)) if filters else False
        scored_candidates: List[Tuple[float, int]] = []
        for doc_idx, entry in enumerate(self._corpus):
            # Exclude synthetic fixtures unless explicitly requested
            if not include_synthetic and entry.get("is_synthetic", False):
                continue

            # Apply filters
            if filters:
                if "document_id" in filters and entry["document_id"] != filters["document_id"]:
                    continue
                if "is_compilable" in filters and entry["is_compilable"] != filters["is_compilable"]:
                    continue
                if "document_title" in filters and filters["document_title"].lower() not in entry["document_title"].lower():
                    continue

            doc_len = self._doc_lengths[doc_idx]
            tf_dict = self._term_freqs[doc_idx]

            score = 0.0
            for token in query_tokens:
                if token not in tf_dict:
                    continue
                tf = tf_dict[token]
                idf = self._compute_idf(token)
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / (self._avgdl or 1.0)))
                score += idf * (numerator / denominator)

            if score > 0.0:
                scored_candidates.append((score, doc_idx))

        # Sort descending by BM25 score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_slice = scored_candidates[:top_k]

        # Cross-reference coverage gaps
        top_clause_ids = [self._corpus[idx]["clause_id"] for _, idx in top_slice]
        approved_set = cross_reference_coverage_gaps(self.db, top_clause_ids, include_synthetic=include_synthetic)

        results: List[RetrievalResult] = []
        for rank, (score, doc_idx) in enumerate(top_slice, start=1):
            entry = self._corpus[doc_idx]
            cid = entry["clause_id"]
            has_approved = cid in approved_set
            results.append(
                RetrievalResult(
                    clause_id=cid,
                    clause_version=entry["clause_version"],
                    clause_number=entry["clause_number"],
                    text=entry["text"],
                    document_id=entry["document_id"],
                    document_title=entry["document_title"],
                    score=round(score, 4),
                    retrieval_method="bm25",
                    rank=rank,
                    has_approved_rule=has_approved,
                    coverage_gap=not has_approved,
                    is_synthetic=entry.get("is_synthetic", False),
                )
            )

        return results


# ---------------------------------------------------------------------------
# Dense Vector Retrieval Engine
# ---------------------------------------------------------------------------

def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vec_a, vec_b):
        dot += a * b
        norm_a += a * a
        norm_b += b * b
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


class DenseRetrievalEngine(BaseRetrievalEngine):
    """Dense vector retriever using embedding client with SQLite cosine fallback."""

    def __init__(
        self,
        db: Session,
        embedding_client: Optional[BaseEmbeddingClient] = None,
    ) -> None:
        self.db = db
        self.embedding_client = embedding_client or get_embedding_client(allow_mock_fallback=True)

    def index_clauses(self, batch_size: int = 50) -> int:
        """Compute and persist embeddings for clauses that lack an embedding."""
        clauses_to_embed = (
            self.db.query(ClauseORM)
            .filter(ClauseORM.embedding.is_(None))
            .all()
        )
        if not clauses_to_embed:
            return 0

        for i in range(0, len(clauses_to_embed), batch_size):
            chunk = clauses_to_embed[i : i + batch_size]
            texts = [c.text for c in chunk]
            embeddings = self.embedding_client.embed_batch(texts)
            for clause, emb in zip(chunk, embeddings):
                clause.embedding = emb

        self.db.commit()
        logger.info("Indexed dense embeddings for %d clauses.", len(clauses_to_embed))
        return len(clauses_to_embed)

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """Perform dense vector search against stored clause embeddings."""
        try:
            query_vec = self.embedding_client.embed_text(query)
        except Exception as exc:
            logger.warning("Embedding client failed (%s); using deterministic fallback.", exc)
            query_vec = MockEmbeddingClient().embed_text(query)

        # Detect database dialect: when PostgreSQL with pgvector is active, execute native distance query
        is_postgres = False
        try:
            bind = self.db.get_bind()
            if bind and "postgresql" in bind.dialect.name:
                is_postgres = True
        except Exception:
            is_postgres = False

        if is_postgres:
            return self._search_native_pgvector(query_vec, top_k=top_k, filters=filters)
        return self._search_in_memory_fallback(query_vec, top_k=top_k, filters=filters)

    def _search_native_pgvector(
        self,
        query_vec: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """Perform native PostgreSQL vector search using the <=> cosine distance operator."""
        distance_expr = ClauseORM.embedding.cosine_distance(query_vec)

        query_builder = (
            self.db.query(ClauseORM, SourceDocumentORM, distance_expr.label("distance"))
            .outerjoin(SourceDocumentORM, ClauseORM.document_id == SourceDocumentORM.id)
            .filter(ClauseORM.embedding.isnot(None))
        )

        include_synthetic = bool(filters.get("include_synthetic", False)) if filters else False
        if not include_synthetic:
            query_builder = query_builder.filter(ClauseORM.is_synthetic.is_(False))
            query_builder = query_builder.filter(~ClauseORM.document_id.in_(SYNTHETIC_DOCUMENT_IDS))

        if filters:
            if "document_id" in filters:
                query_builder = query_builder.filter(ClauseORM.document_id == filters["document_id"])
            if "is_compilable" in filters:
                query_builder = query_builder.filter(ClauseORM.is_compilable == filters["is_compilable"])
            if "document_title" in filters:
                query_builder = query_builder.filter(
                    SourceDocumentORM.title.ilike(f"%{filters['document_title']}%")
                )

        rows = query_builder.order_by(distance_expr).limit(top_k).all()
        if not rows:
            return []

        top_clause_ids = [clause.clause_id for clause, _, _ in rows]
        approved_set = cross_reference_coverage_gaps(self.db, top_clause_ids, include_synthetic=include_synthetic)

        results: List[RetrievalResult] = []
        for rank, (clause, doc, distance) in enumerate(rows, start=1):
            score = max(0.0, 1.0 - float(distance if distance is not None else 1.0))
            cid = clause.clause_id
            has_approved = cid in approved_set
            results.append(
                RetrievalResult(
                    clause_id=cid,
                    clause_version=clause.version_number,
                    clause_number=clause.clause_number,
                    text=clause.text,
                    document_id=clause.document_id,
                    document_title=doc.title if doc else "",
                    score=round(score, 4),
                    retrieval_method="dense",
                    rank=rank,
                    has_approved_rule=has_approved,
                    coverage_gap=not has_approved,
                    is_synthetic=getattr(clause, "is_synthetic", False) or is_synthetic_clause(
                        clause, clause_id=clause.clause_id, document_id=clause.document_id
                    ),
                )
            )

        return results

    def _search_in_memory_fallback(
        self,
        query_vec: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """In-memory cosine similarity search fallback for SQLite and offline test doubles."""
        query_builder = (
            self.db.query(ClauseORM, SourceDocumentORM)
            .outerjoin(SourceDocumentORM, ClauseORM.document_id == SourceDocumentORM.id)
            .filter(ClauseORM.embedding.isnot(None))
        )

        if filters:
            if "document_id" in filters:
                query_builder = query_builder.filter(ClauseORM.document_id == filters["document_id"])
            if "is_compilable" in filters:
                query_builder = query_builder.filter(ClauseORM.is_compilable == filters["is_compilable"])

        rows = query_builder.all()
        if not rows:
            return []

        include_synthetic = bool(filters.get("include_synthetic", False)) if filters else False
        candidates: List[Tuple[float, ClauseORM, Optional[SourceDocumentORM]]] = []
        for clause, doc in rows:
            if not include_synthetic and (
                getattr(clause, "is_synthetic", False)
                or is_synthetic_clause(clause, clause_id=clause.clause_id, document_id=clause.document_id)
            ):
                continue

            emb = clause.embedding
            if isinstance(emb, list) and len(emb) > 0:
                sim = _cosine_similarity(query_vec, emb)
                if filters and "document_title" in filters:
                    doc_title = doc.title if doc else ""
                    if filters["document_title"].lower() not in doc_title.lower():
                        continue
                candidates.append((sim, clause, doc))

        candidates.sort(key=lambda x: x[0], reverse=True)
        top_slice = candidates[:top_k]

        top_clause_ids = [clause.clause_id for _, clause, _ in top_slice]
        approved_set = cross_reference_coverage_gaps(self.db, top_clause_ids, include_synthetic=include_synthetic)

        results: List[RetrievalResult] = []
        for rank, (score, clause, doc) in enumerate(top_slice, start=1):
            has_approved = clause.clause_id in approved_set
            results.append(
                RetrievalResult(
                    clause_id=clause.clause_id,
                    clause_version=clause.version_number,
                    clause_number=clause.clause_number,
                    text=clause.text,
                    document_id=clause.document_id,
                    document_title=doc.title if doc else "",
                    score=round(score, 4),
                    retrieval_method="dense",
                    rank=rank,
                    has_approved_rule=has_approved,
                    coverage_gap=not has_approved,
                    is_synthetic=getattr(clause, "is_synthetic", False) or is_synthetic_clause(
                        clause, clause_id=clause.clause_id, document_id=clause.document_id
                    ),
                )
            )

        return results


# ---------------------------------------------------------------------------
# Hybrid Retrieval Engine (Reciprocal Rank Fusion - RRF)
# ---------------------------------------------------------------------------

class HybridRetrievalEngine(BaseRetrievalEngine):
    """Hybrid ranker combining BM25 and Dense retrieval via Reciprocal Rank Fusion."""

    def __init__(
        self,
        db: Session,
        bm25_engine: Optional[BM25RetrievalEngine] = None,
        dense_engine: Optional[DenseRetrievalEngine] = None,
        rrf_k: Optional[int] = None,
    ) -> None:
        self.db = db
        self.bm25_engine = bm25_engine or BM25RetrievalEngine(db)
        self.dense_engine = dense_engine or DenseRetrievalEngine(db)
        self.rrf_k = rrf_k or int(os.environ.get("HYBRID_RRF_K", 60))

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """Perform hybrid search with Reciprocal Rank Fusion.

        Formula:
            RRF_score(d) = sum_{m in {bm25, dense}} 1 / (rrf_k + rank_m(d))
        """
        # Fetch candidate pools from both rankers
        candidate_pool_size = max(top_k * 2, 50)
        bm25_results = self.bm25_engine.search(query, top_k=candidate_pool_size, filters=filters)
        dense_results = self.dense_engine.search(query, top_k=candidate_pool_size, filters=filters)

        rrf_scores: Dict[str, float] = defaultdict(float)
        clause_map: Dict[str, RetrievalResult] = {}

        # Add reciprocal ranks from BM25
        for res in bm25_results:
            rrf_scores[res.clause_id] += 1.0 / (self.rrf_k + res.rank)
            clause_map[res.clause_id] = res

        # Add reciprocal ranks from Dense
        for res in dense_results:
            rrf_scores[res.clause_id] += 1.0 / (self.rrf_k + res.rank)
            if res.clause_id not in clause_map:
                clause_map[res.clause_id] = res

        # Sort combined results by RRF score descending
        sorted_clause_ids = sorted(
            rrf_scores.keys(),
            key=lambda cid: rrf_scores[cid],
            reverse=True,
        )

        include_synthetic = bool(filters.get("include_synthetic", False)) if filters else False
        top_ids = sorted_clause_ids[:top_k]
        approved_set = cross_reference_coverage_gaps(self.db, top_ids, include_synthetic=include_synthetic)

        hybrid_results: List[RetrievalResult] = []
        for rank, cid in enumerate(top_ids, start=1):
            base_res = clause_map[cid]
            has_approved = cid in approved_set
            hybrid_results.append(
                RetrievalResult(
                    clause_id=base_res.clause_id,
                    clause_version=base_res.clause_version,
                    clause_number=base_res.clause_number,
                    text=base_res.text,
                    document_id=base_res.document_id,
                    document_title=base_res.document_title,
                    score=round(rrf_scores[cid], 5),
                    retrieval_method="hybrid_rrf",
                    rank=rank,
                    has_approved_rule=has_approved,
                    coverage_gap=not has_approved,
                    is_synthetic=base_res.is_synthetic,
                )
            )

        return hybrid_results

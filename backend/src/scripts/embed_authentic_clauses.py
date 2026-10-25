"""Script: Generate genuine local embeddings for all authentic, non-synthetic clauses.

Integrity rules:
  1. Strictly excludes synthetic documents (SYNTHETIC_DOCUMENT_IDS) and quarantined fixtures.
  2. Embeds authentic clause text using SentenceTransformersEmbeddingClient (BAAI/bge-base-en-v1.5).
  3. Records model name, provider, and sets embedding_verified=True.
  4. Operates idempotently without damaging existing data or approved rules.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, ".")

from backend.src.db.models import (
    ClauseORM,
    SourceDocumentORM,
    is_synthetic_clause,
    is_synthetic_document,
)
from backend.src.db.session import session_scope
from backend.src.extraction.embedding_client import SentenceTransformersEmbeddingClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def embed_authentic_clauses(force_reembed: bool = False) -> int:
    client = SentenceTransformersEmbeddingClient(model_name="BAAI/bge-base-en-v1.5")
    logger.info("Initialized embedding client: %r", client)

    embedded_count = 0
    skipped_count = 0
    synthetic_count = 0

    with session_scope() as db:
        clauses = db.query(ClauseORM).all()
        logger.info("Found %d total clauses in database.", len(clauses))

        for c in clauses:
            # Check synthetic isolation
            if c.is_synthetic or is_synthetic_clause(c) or is_synthetic_document(doc_id=c.document_id):
                synthetic_count += 1
                continue

            # Check if parent document is marked synthetic
            parent_doc = db.get(SourceDocumentORM, c.document_id)
            if parent_doc and parent_doc.is_synthetic:
                synthetic_count += 1
                continue

            # Check if already embedded with verified provenance
            if not force_reembed and c.embedding_verified and c.embedding is not None and c.embedding_provider == "sentence-transformers":
                skipped_count += 1
                continue

            # Generate real local embedding
            try:
                emb = client.embed_text(c.text)
                c.embedding = emb
                c.embedding_verified = True
                c.embedding_provider = "sentence-transformers"
                c.embedding_model = "BAAI/bge-base-en-v1.5"
                c.is_synthetic = False
                embedded_count += 1
                if embedded_count % 10 == 0:
                    logger.info("Embedded %d authentic clauses...", embedded_count)
            except Exception as e:
                logger.error("Failed to embed clause %s: %s", c.clause_id, e)

        db.flush()

    logger.info(
        "Embedding run complete: %d embedded, %d already verified, %d synthetic/quarantined excluded.",
        embedded_count,
        skipped_count,
        synthetic_count,
    )
    return embedded_count


if __name__ == "__main__":
    count = embed_authentic_clauses()
    print(f"\nSuccessfully generated genuine embeddings for {count} authentic clauses.")

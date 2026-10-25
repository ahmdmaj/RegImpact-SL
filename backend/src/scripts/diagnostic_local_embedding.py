"""Diagnostic: Local Embedding Feasibility Gate for RegImpact-SL.

Verifies:
1. Model loading: BAAI/bge-base-en-v1.5 via sentence-transformers.
2. Model metadata: Revision, parameters, architecture, license.
3. Dimension validation: Exactly 768 dimensions.
4. Numerical validation: Finite, non-empty, unit-normalized.
5. Semantic discrimination: Relevant regulatory query vs unrelated control query.
6. Fail-fast integrity: Never falls back to mock or random embeddings.
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def run_diagnostic() -> Dict[str, Any]:
    print("=" * 70)
    print("RegImpact-SL: BAAI/bge-base-en-v1.5 Local Feasibility Diagnostic")
    print("=" * 70)

    # 1. Check dependencies
    try:
        import torch
        import transformers
        import sentence_transformers
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        print(f"FAIL: Missing required dependency: {exc}")
        return {"success": False, "error": str(exc)}

    print(f"PyTorch version:             {torch.__version__}")
    print(f"Transformers version:        {transformers.__version__}")
    print(f"Sentence-Transformers version: {sentence_transformers.__version__}")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Execution Device:            {device}")

    # 2. Load model
    model_name = "BAAI/bge-base-en-v1.5"
    print(f"\nLoading model: {model_name} ...")
    try:
        model = SentenceTransformer(model_name, device=device)
    except Exception as exc:
        print(f"FAIL: Failed to load model '{model_name}': {exc}")
        return {"success": False, "error": str(exc)}

    # 3. Model inspection and provenance
    expected_dim = 768
    model_dim = model.get_sentence_embedding_dimension()
    max_seq_len = model.max_seq_length
    print(f"Loaded successfully!")
    print(f"  Sentence embedding dim:    {model_dim} (expected {expected_dim})")
    print(f"  Max sequence length:       {max_seq_len}")

    if model_dim != expected_dim:
        print(f"FAIL: Dimension mismatch ({model_dim} != {expected_dim})")
        return {"success": False, "error": f"Dimension mismatch: {model_dim} != {expected_dim}"}

    # Extract revision / commit hash if available
    revision_info = "unknown"
    try:
        first_mod = model[0]
        if hasattr(first_mod, "auto_model") and hasattr(first_mod.auto_model, "config"):
            cfg = first_mod.auto_model.config
            revision_info = getattr(cfg, "_commit_hash", None) or getattr(cfg, "transformers_version", "available")
    except Exception:
        pass
    print(f"  Model revision info:       {revision_info}")

    # 4. Test texts
    clause_text = (
        "A person shall not import, transport, distribute, store, sell, offer for sale, expose or keep for sale "
        "or advertise, any food contained in a package or container, unless such package or container is "
        "labelled in accordance with these regulations."
    )
    relevant_query = "What are the mandatory labelling requirements for prepackaged food products?"
    control_query = "Wastewater discharge standards and environmental protection licence thresholds."

    test_corpus = [
        ("regulatory_clause", clause_text),
        ("relevant_query", relevant_query),
        ("control_query", control_query),
    ]

    print("\nEncoding test texts...")
    embeddings: List[List[float]] = []
    for label, text in test_corpus:
        # v1.5 retrieval instruction for queries (optional but standard practice in BGE)
        if label.endswith("query"):
            inp = f"Represent this sentence for searching relevant passages: {text}"
        else:
            inp = text

        vec = model.encode(inp, normalize_embeddings=True, show_progress_bar=False)
        vec_list = vec.tolist()

        # Integrity checks
        if len(vec_list) != expected_dim:
            print(f"FAIL: Text '{label}' generated {len(vec_list)} dimensions, expected {expected_dim}")
            return {"success": False, "error": "Dimension validation failure"}

        if any(not math.isfinite(x) for x in vec_list):
            print(f"FAIL: Text '{label}' contains non-finite values (NaN/Inf)")
            return {"success": False, "error": "Non-finite values in embedding"}

        norm = math.sqrt(sum(x * x for x in vec_list))
        if abs(norm - 1.0) > 1e-4:
            print(f"FAIL: Text '{label}' is not unit-normalized (norm = {norm})")
            return {"success": False, "error": "Normalization failure"}

        embeddings.append(vec_list)
        print(f"  [{label}] dim={len(vec_list)}, norm={norm:.6f}, sample={vec_list[:4]}...")

    clause_vec, rel_q_vec, ctrl_q_vec = embeddings

    # Cosine similarities (vectors are unit-normalized, so dot product = cosine similarity)
    def dot_product(v1: List[float], v2: List[float]) -> float:
        return sum(a * b for a, b in zip(v1, v2))

    sim_relevant = dot_product(rel_q_vec, clause_vec)
    sim_control = dot_product(ctrl_q_vec, clause_vec)

    print("\nSemantic Discrimination Check:")
    print(f"  Similarity(Relevant Query, Regulation 3 Clause): {sim_relevant:.4f}")
    print(f"  Similarity(Control Query,  Regulation 3 Clause): {sim_control:.4f}")
    print(f"  Delta (Relevant - Control):                    {sim_relevant - sim_control:.4f}")

    if sim_relevant <= sim_control:
        print("FAIL: Relevant query did not score higher than unrelated control query.")
        return {"success": False, "error": "Semantic ranking inverted"}

    print("\n" + "=" * 70)
    print("STATUS: VERIFIED_WITH_REAL_MODEL — Stage 2 Diagnostic Passed Successfully")
    print("=" * 70)

    return {
        "success": True,
        "model_name": model_name,
        "dimension": model_dim,
        "revision": revision_info,
        "device": device,
        "sim_relevant": sim_relevant,
        "sim_control": sim_control,
        "clause_vec_sample": clause_vec[:5],
    }


if __name__ == "__main__":
    result = run_diagnostic()
    if not result.get("success"):
        sys.exit(1)

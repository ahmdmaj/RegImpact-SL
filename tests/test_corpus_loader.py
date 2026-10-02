import pytest
from pathlib import Path
from src.regimpact.ingestion.corpus_loader import load_regulatory_corpus

def test_load_corpus():
    path = Path("data/regulatory_corpus_v0.1.json")
    if not path.exists():
        pytest.skip(f"Dataset not found at {path}")
    
    corpus = load_regulatory_corpus(path)
    assert len(corpus) > 0
    assert corpus[0].regulation_id is not None

import pytest
from pathlib import Path
from src.regimpact.ingestion.corpus_loader import load_regulatory_corpus
from src.regimpact.ingestion.benchmark_loader import load_benchmark
from src.regimpact.validation.dataset_validator import validate_datasets

def test_validation():
    corpus_path = Path("data/regulatory_corpus_v0.1.json")
    benchmark_path = Path("data/regimpact_sl_benchmark_v0.1.csv")
    
    if not corpus_path.exists() or not benchmark_path.exists():
        pytest.skip(f"Datasets not found")
        
    corpus = load_regulatory_corpus(corpus_path)
    benchmark = load_benchmark(benchmark_path)
    
    errors = validate_datasets(corpus, benchmark)
    assert len(errors) == 0, "Dataset validation failed: " + "\n".join(errors)

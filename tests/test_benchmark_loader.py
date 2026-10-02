import pytest
from pathlib import Path
from src.regimpact.ingestion.benchmark_loader import load_benchmark

def test_load_benchmark():
    path = Path("data/regimpact_sl_benchmark_v0.1.csv")
    if not path.exists():
        pytest.skip(f"Dataset not found at {path}")
    
    benchmark = load_benchmark(path)
    assert len(benchmark) > 0
    assert benchmark[0].scenario_id is not None

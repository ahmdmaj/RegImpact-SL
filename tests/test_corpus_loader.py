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
# Benchmark validation
    scenario_ids = set()
    for i, scen in enumerate(benchmark):
        if scen.scenario_id in scenario_ids:
            errors.append(f"Benchmark: Duplicate scenario_id '{scen.scenario_id}'")
        scenario_ids.add(scen.scenario_id)
        
        if not scen.business_id:
            errors.append(f"Benchmark: Empty business_id in {scen.scenario_id}")
        if not scen.regulation_id:
            errors.append(f"Benchmark: Empty regulation_id in {scen.scenario_id}")
        if not scen.question:
            errors.append(f"Benchmark: Empty question in {scen.scenario_id}")
        if not scen.expected_applicability:
            errors.append(f"Benchmark: Empty expected_applicability in {scen.scenario_id}")
           
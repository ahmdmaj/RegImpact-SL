from typing import List
from ..models.regulation import RegulationRecord
from ..models.scenario import Scenario

def validate_datasets(corpus: List[RegulationRecord], benchmark: List[Scenario]) -> List[str]:
    errors = []
    
    # Corpus validation
    reg_ids = set()
    for i, reg in enumerate(corpus):
        if reg.regulation_id in reg_ids:
            errors.append(f"Corpus: Duplicate regulation_id '{reg.regulation_id}'")
        reg_ids.add(reg.regulation_id)
        
        if not reg.title:
            errors.append(f"Corpus: Empty title for {reg.regulation_id}")
        if not reg.authority:
            errors.append(f"Corpus: Empty authority for {reg.regulation_id}")
        if not reg.domain:
            errors.append(f"Corpus: Empty domain for {reg.regulation_id}")
        if not reg.status:
            errors.append(f"Corpus: Empty status for {reg.regulation_id}")
            
     
        # Cross-validation
        # We assume regulations containing "placeholder" or "example" might not be in the corpus
        if scen.regulation_id not in reg_ids and "placeholder" not in scen.regulation_id.lower() and "example" not in scen.regulation_id.lower():
            errors.append(f"Cross-Validation: Benchmark scenario {scen.scenario_id} references regulation_id '{scen.regulation_id}' not found in corpus")
            
    return errors

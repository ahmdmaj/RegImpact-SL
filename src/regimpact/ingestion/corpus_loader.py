import json
from pathlib import Path
from typing import List, Dict, Any
from pydantic import ValidationError
from ..models.regulation import RegulationRecord

def load_regulatory_corpus(file_path: str | Path) -> List[RegulationRecord]:
    """
    Loads and validates the regulatory corpus from a JSON file.
    
    Args:
        file_path: Path to the regulatory corpus JSON file.
        
    Returns:
        List of validated RegulationRecord objects.
        
    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        pydantic.ValidationError: If the data does not match the expected schema.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Corpus file not found: {path}")
        
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    if not isinstance(data, list):
        raise ValueError("Corpus JSON must contain a list of records")
        
    records = []
    errors = []
    
    for i, item in enumerate(data):
        try:
            record = RegulationRecord.model_validate(item)
            records.append(record)
        except ValidationError as e:
            errors.append(f"Record {i} ({item.get('regulation_id', 'unknown')}): {e}")
            
    if errors:
        error_msg = "\n".join(errors)
        raise ValueError(f"Validation failed for {len(errors)} records:\n{error_msg}")
        
    return records

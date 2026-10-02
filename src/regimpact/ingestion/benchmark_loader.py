import pandas as pd
from pathlib import Path
from typing import List
from pydantic import ValidationError
import math
from ..models.scenario import Scenario
from ..models.business import BusinessProfile

def _clean_nan(val):
    if pd.isna(val):
        return None
    return val

def _parse_list(val):
    if pd.isna(val):
        return []
    if isinstance(val, str):
        return [x.strip() for x in val.split(';') if x.strip()]
    return []

def load_benchmark(file_path: str | Path) -> List[Scenario]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {path}")
        
    df = pd.read_csv(path)
    
    scenarios = []
    errors = []
    
    for i, row in df.iterrows():
        try:
            business_profile = BusinessProfile(
                business_id=str(row['business_id']) if pd.notna(row.get('business_id')) else "unknown",
                industry=_clean_nan(row.get('industry')),
                product=_parse_list(row.get('product')),
                employees=int(row.get('employees')) if pd.notna(row.get('employees')) else None,
                production_capacity=_clean_nan(row.get('production_capacity')),
                production_unit=_clean_nan(row.get('production_unit')),
                packaging=_parse_list(row.get('packaging')),
                market=_parse_list(row.get('market')),
                import_activity=bool(row.get('import_activity')) if pd.notna(row.get('import_activity')) else None,
                export_activity=bool(row.get('export_activity')) if pd.notna(row.get('export_activity')) else None,
                premises=_clean_nan(row.get('premises')),
                location=_clean_nan(row.get('location')),
                revenue_band=_clean_nan(row.get('revenue_band')),
                environmental_activity=_parse_list(row.get('environmental_activity')),
                existing_registrations=_parse_list(row.get('existing_registrations'))
            )
            
            scenario = Scenario(
                scenario_id=str(row['scenario_id']),
                business_id=str(row['business_id']),
                business_profile=business_profile,
                regulation_id=str(row['regulation_id']),
                regulatory_event=_clean_nan(row.get('regulatory_event')),
                question=str(row['question']),
                expected_applicability=str(row['expected_applicability']),
                applicability_reason=_clean_nan(row.get('applicability_reason')),
                expected_obligation=_parse_list(row.get('expected_obligation')),
                expected_impact=_clean_nan(row.get('expected_impact')),
                expected_action=_clean_nan(row.get('expected_action')),
                evidence_reference=_clean_nan(row.get('evidence_reference')),
                effective_date=_clean_nan(row.get('effective_date')),
                difficulty=_clean_nan(row.get('difficulty')),
                scenario_type=_clean_nan(row.get('scenario_type'))
            )
            scenarios.append(scenario)
        except Exception as e:
            errors.append(f"Row {i} ({row.get('scenario_id', 'unknown')}): {str(e)}")
            
    if errors:
        error_msg = "\n".join(errors)
        raise ValueError(f"Validation failed for {len(errors)} benchmark scenarios:\n{error_msg}")
        
    return scenarios

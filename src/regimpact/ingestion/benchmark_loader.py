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


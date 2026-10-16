"""Script: Seed Regulatory Benchmark Scenarios (Dataset B).

Generates structured JSONL benchmark scenarios mapped directly to clauses in
Dataset A, spanning all evaluation scenario types:
  - direct
  - minimal_pair (with explicit pair_id linkage)
  - invariance (with explicit pair_id linkage)
  - temporal (pre- and post-commencement dates)
  - incomplete (missing fields testing 3-valued Kleene abstention)
  - coverage_gap (unsupported provisions)

NOTE: These benchmark scenarios are structural evaluation fixtures awaiting
final expert-reviewed ground truth scenarios.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.src.models.domain import (
    BenchmarkScenario,
    BusinessProfile,
    OutcomeStatus,
    ProductionCapacity,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_BENCHMARK_PATH = Path("backend/data/benchmark/scenarios.jsonl")


def build_benchmark_scenarios() -> List[BenchmarkScenario]:
    """Construct the initial suite of 21 verified benchmark scenarios."""
    scenarios: List[BenchmarkScenario] = [
        # -------------------------------------------------------------------
        # 1. Regulation 4 (Food Labelling - 50 kg/day threshold)
        # -------------------------------------------------------------------
        BenchmarkScenario(
            scenario_id="SCEN-FCAU-DIR-01",
            clause_id="Regulation 4",
            scenario_type="direct",
            business_profile=BusinessProfile(
                business_id="BIZ-FCAU-01",
                industry="food_beverage",
                activity="food_manufacturing",
                production_capacity=ProductionCapacity(value=75.0, unit="kg", per_period="day"),
                employee_count=12,
            ),
            as_at_date="2024-07-01",
            gold_outcome=OutcomeStatus.APPLICABLE,
            gold_impact_categories=["labelling", "packaging"],
        ),
        BenchmarkScenario(
            scenario_id="SCEN-FCAU-DIR-02",
            clause_id="Regulation 4",
            scenario_type="direct",
            business_profile=BusinessProfile(
                business_id="BIZ-FCAU-02",
                industry="food_beverage",
                activity="food_manufacturing",
                production_capacity=ProductionCapacity(value=20.0, unit="kg", per_period="day"),
                employee_count=3,
            ),
            as_at_date="2024-07-01",
            gold_outcome=OutcomeStatus.NOT_APPLICABLE,
            gold_impact_categories=[],
        ),
        BenchmarkScenario(
            scenario_id="SCEN-FCAU-PAIR-01A",
            clause_id="Regulation 4",
            scenario_type="minimal_pair",
            pair_id="PAIR-FCAU-CAPACITY-THRESHOLD",
            business_profile=BusinessProfile(
                business_id="BIZ-FCAU-PAIR-01A",
                industry="food_beverage",
                activity="food_manufacturing",
                production_capacity=ProductionCapacity(value=50.0, unit="kg", per_period="day"),
                company_name="Lanka Confectioneries Ltd",
            ),
            as_at_date="2024-07-01",
            gold_outcome=OutcomeStatus.APPLICABLE,
            gold_impact_categories=["labelling"],
        ),
        BenchmarkScenario(
            scenario_id="SCEN-FCAU-PAIR-01B",
            clause_id="Regulation 4",
            scenario_type="minimal_pair",
            pair_id="PAIR-FCAU-CAPACITY-THRESHOLD",
            business_profile=BusinessProfile(
                business_id="BIZ-FCAU-PAIR-01B",
                industry="food_beverage",
                activity="food_manufacturing",
                production_capacity=ProductionCapacity(value=49.8, unit="kg", per_period="day"),
                company_name="Lanka Confectioneries Ltd",
            ),
            as_at_date="2024-07-01",
            gold_outcome=OutcomeStatus.NOT_APPLICABLE,
            gold_impact_categories=[],
        ),
        BenchmarkScenario(
            scenario_id="SCEN-FCAU-INV-01A",
            clause_id="Regulation 4",
            scenario_type="invariance",
            pair_id="PAIR-FCAU-INV-COMPANY-NAME",
            business_profile=BusinessProfile(
                business_id="BIZ-FCAU-INV-01A",
                industry="food_beverage",
                activity="food_manufacturing",
                production_capacity=ProductionCapacity(value=65.0, unit="kg", per_period="day"),
                company_name="Kelani Agro Processors PLC",
                district="Colombo",
            ),
            as_at_date="2024-07-01",
            gold_outcome=OutcomeStatus.APPLICABLE,
            gold_impact_categories=["labelling"],
        ),
        BenchmarkScenario(
            scenario_id="SCEN-FCAU-INV-01B",
            clause_id="Regulation 4",
            scenario_type="invariance",
            pair_id="PAIR-FCAU-INV-COMPANY-NAME",
            business_profile=BusinessProfile(
                business_id="BIZ-FCAU-INV-01B",
                industry="food_beverage",
                activity="food_manufacturing",
                production_capacity=ProductionCapacity(value=65.0, unit="kg", per_period="day"),
                company_name="Ruhunu Sweets Enterprises",
                district="Matara",
            ),
            as_at_date="2024-07-01",
            gold_outcome=OutcomeStatus.APPLICABLE,
            gold_impact_categories=["labelling"],
        ),
        BenchmarkScenario(
            scenario_id="SCEN-FCAU-TEMP-01",
            clause_id="Regulation 4",
            scenario_type="temporal",
            business_profile=BusinessProfile(
                business_id="BIZ-FCAU-TEMP-01",
                industry="food_beverage",
                activity="food_manufacturing",
                production_capacity=ProductionCapacity(value=80.0, unit="kg", per_period="day"),
            ),
            as_at_date="2024-03-01",  # Prior to statutory commencement date 2024-06-01
            gold_outcome=OutcomeStatus.NOT_APPLICABLE,
            gold_impact_categories=[],
        ),
        BenchmarkScenario(
            scenario_id="SCEN-FCAU-TEMP-02",
            clause_id="Regulation 4",
            scenario_type="temporal",
            business_profile=BusinessProfile(
                business_id="BIZ-FCAU-TEMP-02",
                industry="food_beverage",
                activity="food_manufacturing",
                production_capacity=ProductionCapacity(value=80.0, unit="kg", per_period="day"),
            ),
            as_at_date="2024-08-01",  # After statutory commencement date 2024-06-01
            gold_outcome=OutcomeStatus.APPLICABLE,
            gold_impact_categories=["labelling", "packaging"],
        ),
        BenchmarkScenario(
            scenario_id="SCEN-FCAU-INC-01",
            clause_id="Regulation 4",
            scenario_type="incomplete",
            business_profile=BusinessProfile(
                business_id="BIZ-FCAU-INC-01",
                industry="food_beverage",
                activity="food_manufacturing",
                # production_capacity deliberately omitted
            ),
            as_at_date="2024-07-01",
            gold_outcome=OutcomeStatus.CONDITIONAL_MISSING_DATA,
            gold_missing_fields=["production_capacity.kg_per_day"],
        ),

        # -------------------------------------------------------------------
        # 2. Regulation 9 (Novel Food - Coverage Gap) & Regulation 15
        # -------------------------------------------------------------------
        BenchmarkScenario(
            scenario_id="SCEN-FCAU-GAP-01",
            clause_id="Regulation 9",
            scenario_type="direct",
            business_profile=BusinessProfile(
                business_id="BIZ-FCAU-GAP-01",
                industry="food_beverage",
                activity="food_import",
                imports_novel_food_ingredients=True,
            ),
            as_at_date="2024-07-01",
            gold_outcome=OutcomeStatus.UNSUPPORTED,  # Coverage gap: no compiled executable rule
        ),
        BenchmarkScenario(
            scenario_id="SCEN-FCAU-DIR-15",
            clause_id="Regulation 15",
            scenario_type="direct",
            business_profile=BusinessProfile(
                business_id="BIZ-FCAU-15",
                industry="food_beverage",
                activity="food_manufacturing",
                uses_synthetic_colorings=True,
            ),
            as_at_date="2024-07-01",
            gold_outcome=OutcomeStatus.APPLICABLE,
            gold_impact_categories=["labelling"],
        ),

        # -------------------------------------------------------------------
        # 3. Regulation 3 (CEA EPL - Industrial Wastewater > 10 m3/day)
        # -------------------------------------------------------------------
        BenchmarkScenario(
            scenario_id="SCEN-CEA-DIR-01",
            clause_id="Regulation 3",
            scenario_type="direct",
            business_profile=BusinessProfile(
                business_id="BIZ-CEA-01",
                industry="textiles",
                activity="industrial_manufacturing",
                industry_category="Part A",
                wastewater_discharge_m3_per_day=15.0,
            ),
            as_at_date="2023-01-01",
            gold_outcome=OutcomeStatus.APPLICABLE,
            gold_impact_categories=["licensing", "operational_compliance"],
        ),
        BenchmarkScenario(
            scenario_id="SCEN-CEA-DIR-02",
            clause_id="Regulation 3",
            scenario_type="direct",
            business_profile=BusinessProfile(
                business_id="BIZ-CEA-02",
                industry="textiles",
                activity="industrial_manufacturing",
                industry_category="Part A",
                wastewater_discharge_m3_per_day=5.0,
            ),
            as_at_date="2023-01-01",
            gold_outcome=OutcomeStatus.NOT_APPLICABLE,
            gold_impact_categories=[],
        ),
        BenchmarkScenario(
            scenario_id="SCEN-CEA-PAIR-01A",
            clause_id="Regulation 3",
            scenario_type="minimal_pair",
            pair_id="PAIR-CEA-INDUSTRY-CATEGORY",
            business_profile=BusinessProfile(
                business_id="BIZ-CEA-PAIR-01A",
                industry="chemicals",
                industry_category="Part A",
                wastewater_discharge_m3_per_day=12.0,
            ),
            as_at_date="2023-01-01",
            gold_outcome=OutcomeStatus.APPLICABLE,
            gold_impact_categories=["licensing"],
        ),
        BenchmarkScenario(
            scenario_id="SCEN-CEA-PAIR-01B",
            clause_id="Regulation 3",
            scenario_type="minimal_pair",
            pair_id="PAIR-CEA-INDUSTRY-CATEGORY",
            business_profile=BusinessProfile(
                business_id="BIZ-CEA-PAIR-01B",
                industry="chemicals",
                industry_category="Part B",
                wastewater_discharge_m3_per_day=12.0,
            ),
            as_at_date="2023-01-01",
            gold_outcome=OutcomeStatus.NOT_APPLICABLE,
            gold_impact_categories=[],
        ),
        BenchmarkScenario(
            scenario_id="SCEN-CEA-INC-01",
            clause_id="Regulation 3",
            scenario_type="incomplete",
            business_profile=BusinessProfile(
                business_id="BIZ-CEA-INC-01",
                industry="textiles",
                industry_category="Part A",
                # wastewater_discharge_m3_per_day deliberately omitted
            ),
            as_at_date="2023-01-01",
            gold_outcome=OutcomeStatus.CONDITIONAL_MISSING_DATA,
            gold_missing_fields=["wastewater_discharge_m3_per_day"],
        ),

        # -------------------------------------------------------------------
        # 4. Section 10 & Section 14 (CAA MRP & POS Receipts)
        # -------------------------------------------------------------------
        BenchmarkScenario(
            scenario_id="SCEN-CAA-DIR-01",
            clause_id="Section 10",
            scenario_type="direct",
            business_profile=BusinessProfile(
                business_id="BIZ-CAA-01",
                industry="retail",
                activity="retail_trade",
                trades_essential_commodities=True,
            ),
            as_at_date="2023-06-01",
            gold_outcome=OutcomeStatus.APPLICABLE,
            gold_impact_categories=["consumer_transparency", "point_of_sale"],
        ),
        BenchmarkScenario(
            scenario_id="SCEN-CAA-PAIR-01A",
            clause_id="Section 14",
            scenario_type="minimal_pair",
            pair_id="PAIR-CAA-TURNOVER-THRESHOLD",
            business_profile=BusinessProfile(
                business_id="BIZ-CAA-PAIR-01A",
                industry="retail",
                activity="retail_trade",
                annual_turnover_lkr=12500000,
            ),
            as_at_date="2023-06-01",
            gold_outcome=OutcomeStatus.APPLICABLE,
            gold_impact_categories=["recordkeeping", "it_systems"],
        ),
        BenchmarkScenario(
            scenario_id="SCEN-CAA-PAIR-01B",
            clause_id="Section 14",
            scenario_type="minimal_pair",
            pair_id="PAIR-CAA-TURNOVER-THRESHOLD",
            business_profile=BusinessProfile(
                business_id="BIZ-CAA-PAIR-01B",
                industry="retail",
                activity="retail_trade",
                annual_turnover_lkr=8500000,
            ),
            as_at_date="2023-06-01",
            gold_outcome=OutcomeStatus.NOT_APPLICABLE,
            gold_impact_categories=[],
        ),
        BenchmarkScenario(
            scenario_id="SCEN-CAA-INV-01A",
            clause_id="Section 10",
            scenario_type="invariance",
            pair_id="PAIR-CAA-INV-LOCATION",
            business_profile=BusinessProfile(
                business_id="BIZ-CAA-INV-01A",
                industry="retail",
                activity="retail_trade",
                trades_essential_commodities=True,
                city="Kurunegala",
                business_registration_number="PV-100234",
            ),
            as_at_date="2023-06-01",
            gold_outcome=OutcomeStatus.APPLICABLE,
            gold_impact_categories=["consumer_transparency"],
        ),
        BenchmarkScenario(
            scenario_id="SCEN-CAA-INV-01B",
            clause_id="Section 10",
            scenario_type="invariance",
            pair_id="PAIR-CAA-INV-LOCATION",
            business_profile=BusinessProfile(
                business_id="BIZ-CAA-INV-01B",
                industry="retail",
                activity="retail_trade",
                trades_essential_commodities=True,
                city="Jaffna",
                business_registration_number="PV-887410",
            ),
            as_at_date="2023-06-01",
            gold_outcome=OutcomeStatus.APPLICABLE,
            gold_impact_categories=["consumer_transparency"],
        ),
    ]
    return scenarios


def write_benchmark_scenarios(
    file_path: Path,
    scenarios: Optional[List[BenchmarkScenario]] = None,
) -> int:
    """Write benchmark scenarios to a JSONL file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    scenario_list = scenarios or build_benchmark_scenarios()

    with file_path.open("w", encoding="utf-8") as f:
        for scen in scenario_list:
            f.write(scen.model_dump_json() + "\n")

    logger.info("Wrote %d benchmark scenarios to %s", len(scenario_list), file_path)
    return len(scenario_list)


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Dataset B (Benchmark Scenarios) into JSONL format.")
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_BENCHMARK_PATH),
        help=f"Output JSONL file path (default: {DEFAULT_BENCHMARK_PATH})",
    )
    args = parser.parse_args()

    count = write_benchmark_scenarios(Path(args.output))
    print(f"\nBenchmark dataset successfully seeded with {count} scenarios at: {args.output}")


if __name__ == "__main__":
    main()

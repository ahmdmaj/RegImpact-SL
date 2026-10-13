"""Unit tests for Component [O6 / Section 8.8]: Baselines and Evaluation Harness."""

import pytest

from backend.src.evaluation.baselines import (
    BM25Baseline,
    DenseBaseline,
    HybridBaseline,
    OracleBaseline,
    SystemP,
)
from backend.src.evaluation.benchmark_runner import (
    BenchmarkRunner,
    compare_systems,
)
from backend.src.models.domain import (
    AppliesIf,
    BenchmarkScenario,
    BusinessProfile,
    Condition,
    EvaluationReport,
    EvaluationResult,
    Obligation,
    OutcomeStatus,
    Product,
    ProductionCapacity,
    Rule,
    Source,
    Validity,
    Verification,
)


@pytest.fixture
def eval_rule() -> Rule:
    """Fixture providing a verified rule for benchmark scenario execution."""
    return Rule(
        rule_id="RULE-EVAL-001",
        source=Source(
            instrument="Food Act No. 26 of 1980 Regulations",
            authority="FCAU",
            gazette_no="2024/01",
            clause="Regulation 4",
            page=1,
            quote_span="Every food manufacturing enterprise having a production capacity of 50 kg per day...",
        ),
        validity=Validity(
            published="2024-01-01",
            commences="2024-06-01",
            transition_until=None,
        ),
        applies_if=AppliesIf(
            all=[
                Condition(field="activity", op="eq", value="food_manufacturing"),
                Condition(field="products.prepackaged", op="eq", value=True),
                Condition(field="production_capacity.kg_per_day", op="gte", value=50),
            ]
        ),
        exceptions=[],
        obligation=Obligation(
            type="labelling",
            text="Display nutrition panel in Sinhala, Tamil, and English.",
            impact_categories=["packaging", "labelling"],
        ),
        verification=Verification(
            status="human_verified",
            extraction_model="gpt-4o",
            agreement=True,
        ),
    )


@pytest.fixture
def benchmark_suite() -> list[BenchmarkScenario]:
    """Fixture providing a diverse 5-scenario benchmark suite."""
    # 1. Direct match scenario -> APPLICABLE
    scen_direct = BenchmarkScenario(
        scenario_id="SCEN-001-DIRECT",
        clause_id="Regulation 4",
        scenario_type="direct",
        business_profile=BusinessProfile(
            business_id="BIZ-01",
            activity="food_manufacturing",
            products=[Product(category="spices", prepackaged=True)],
            production_capacity=ProductionCapacity(value=60.0, unit="kg", per_period="day"),
        ),
        as_at_date="2024-08-01",
        gold_outcome=OutcomeStatus.APPLICABLE,
        gold_impact_categories=["packaging", "labelling"],
    )

    # 2. Temporal scenario: date prior to commencement -> NOT_APPLICABLE
    scen_temporal = BenchmarkScenario(
        scenario_id="SCEN-002-TEMPORAL-BEFORE",
        clause_id="Regulation 4",
        scenario_type="temporal",
        business_profile=BusinessProfile(
            business_id="BIZ-02",
            activity="food_manufacturing",
            products=[Product(category="spices", prepackaged=True)],
            production_capacity=ProductionCapacity(value=60.0, unit="kg", per_period="day"),
        ),
        as_at_date="2024-03-01",  # Prior to commences 2024-06-01
        gold_outcome=OutcomeStatus.NOT_APPLICABLE,
    )

    # 3. Incomplete profile scenario: missing capacity -> CONDITIONAL_MISSING_DATA
    scen_incomplete = BenchmarkScenario(
        scenario_id="SCEN-003-INCOMPLETE",
        clause_id="Regulation 4",
        scenario_type="incomplete",
        business_profile=BusinessProfile(
            business_id="BIZ-03",
            activity="food_manufacturing",
            products=[Product(category="spices", prepackaged=True)],
            production_capacity=None,  # Missing field
        ),
        as_at_date="2024-08-01",
        gold_outcome=OutcomeStatus.CONDITIONAL_MISSING_DATA,
        gold_missing_fields=["production_capacity.kg_per_day"],
    )

    # 4 & 5. Minimal pair: identical except threshold flips outcome
    scen_pair_a = BenchmarkScenario(
        scenario_id="SCEN-004-PAIR-A",
        clause_id="Regulation 4",
        scenario_type="minimal_pair",
        pair_id="PAIR-CAPACITY-THRESHOLD",
        business_profile=BusinessProfile(
            business_id="BIZ-04A",
            activity="food_manufacturing",
            products=[Product(category="spices", prepackaged=True)],
            production_capacity=ProductionCapacity(value=60.0, unit="kg", per_period="day"),  # >= 50
        ),
        as_at_date="2024-08-01",
        gold_outcome=OutcomeStatus.APPLICABLE,
    )

    scen_pair_b = BenchmarkScenario(
        scenario_id="SCEN-005-PAIR-B",
        clause_id="Regulation 4",
        scenario_type="minimal_pair",
        pair_id="PAIR-CAPACITY-THRESHOLD",
        business_profile=BusinessProfile(
            business_id="BIZ-04B",
            activity="food_manufacturing",
            products=[Product(category="spices", prepackaged=True)],
            production_capacity=ProductionCapacity(value=40.0, unit="kg", per_period="day"),  # < 50
        ),
        as_at_date="2024-08-01",
        gold_outcome=OutcomeStatus.NOT_APPLICABLE,
    )

    return [scen_direct, scen_temporal, scen_incomplete, scen_pair_a, scen_pair_b]


# Test 1: System P evaluation through BenchmarkRunner
def test_system_p_benchmark_execution(eval_rule: Rule, benchmark_suite: list[BenchmarkScenario]):
    system_p = SystemP(rules=eval_rule)
    runner = BenchmarkRunner()

    report = runner.run(system_p, benchmark_suite)

    assert isinstance(report, EvaluationReport)
    assert report.total_scenarios == 5
    assert report.system_name == "P_Proposed_System"

    # System P achieves 100% accuracy on verified symbolic logic
    assert report.accuracy == 1.0
    assert report.macro_f1 == 1.0

    # Abstention metrics on CONDITIONAL_MISSING_DATA
    assert report.abstention_precision == 1.0
    assert report.abstention_recall == 1.0
    assert report.abstention_f1 == 1.0
    assert report.missing_fields_accuracy == 1.0

    # Minimal-pair consistency score (pair flipped properly)
    assert report.consistency_score == 1.0

    # Temporal accuracy
    assert report.temporal_accuracy == 1.0

    # Verify impact was attached for applicable scenario
    direct_eval = next(s for s in report.scenario_evaluations if s.scenario_id == "SCEN-001-DIRECT")
    assert direct_eval.is_outcome_correct is True


# Test 2: Incomplete profile identification and missing fields verification
def test_abstention_metric_discriminates_failures(eval_rule: Rule, benchmark_suite: list[BenchmarkScenario]):
    # A flawed baseline that always predicts APPLICABLE (fails to abstain on incomplete profiles)
    flawed_oracle = OracleBaseline(
        predictor=lambda s: EvaluationResult(
            status=OutcomeStatus.APPLICABLE,
            rule_id=s.clause_id,
            missing_fields=[],
            evaluation_trace=[],
            reason="Flawed model always hallucinating APPLICABLE.",
        )
    )

    runner = BenchmarkRunner()
    report = runner.run(flawed_oracle, benchmark_suite)

    # Accuracy must be lower because it fails on NOT_APPLICABLE and CONDITIONAL_MISSING_DATA
    assert report.accuracy < 1.0
    # Abstention recall must be 0.0 because it never predicted CONDITIONAL_MISSING_DATA
    assert report.abstention_recall == 0.0
    # Minimal pair flip consistency fails because both pair items predicted APPLICABLE
    assert report.consistency_score == 0.0


# Test 3: Multi-system comparison using compare_systems
def test_compare_systems_harness(eval_rule: Rule, benchmark_suite: list[BenchmarkScenario]):
    system_p = SystemP(rules=eval_rule)

    b0 = OracleBaseline()
    b1 = BM25Baseline()
    b2 = DenseBaseline()
    b3 = HybridBaseline()

    systems = [system_p, b0, b1, b2, b3]
    reports = compare_systems(systems, benchmark_suite)

    assert len(reports) == 5
    assert "P_Proposed_System" in reports
    assert "B0_Oracle_LongContext" in reports
    assert "B1_BM25_Lexical" in reports
    assert "B2_Dense_RAG" in reports
    assert "B3_Hybrid_Rerank_RAG" in reports

    # System P has higher accuracy than naive unconditioned stubs
    assert reports["P_Proposed_System"].accuracy >= reports["B1_BM25_Lexical"].accuracy


# Test 4: System P unsupported clause handling for coverage gaps
def test_system_p_unsupported_clause():
    system_p = SystemP(rules=[])  # Empty rule store
    runner = BenchmarkRunner()

    gap_scenario = BenchmarkScenario(
        scenario_id="SCEN-GAP-001",
        clause_id="Unregistered_Clause_99",
        scenario_type="direct",
        business_profile=BusinessProfile(activity="food_manufacturing"),
        as_at_date="2024-01-01",
        gold_outcome=OutcomeStatus.UNSUPPORTED,
    )

    report = runner.run(system_p, [gap_scenario])
    assert report.accuracy == 1.0
    assert report.scenario_evaluations[0].predicted_outcome == OutcomeStatus.UNSUPPORTED

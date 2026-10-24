"""Unit and Integration Tests for Initial Benchmark Migration (Milestone 1).

Validates:
  BENCH-LOAD-01  regulation_3_slice.jsonl exists and parses into valid BenchmarkScenario objects.
  BENCH-PROV-02  Every scenario possesses full, traceable provenance grounded in Gazette 2494/47.
  BENCH-PROV-03  Provisional safety gate: no rules or scenarios are falsely represented as gold.
  BENCH-INTEG-04 Duplicate scenario IDs, unknown rules, and unknown hashes trigger validation errors.
  BENCH-PAIR-05  Minimal pairs link via pair_id and exhibit sensitivity outcome flips.
  BENCH-PAIR-06  Invariance pairs link via pair_id and exhibit invariant outcome stability.
  BENCH-ABST-07  Incomplete scenarios require 3-valued Kleene abstention with exact missing fields.
  BENCH-SPLIT-08 Clause-grouped partitioning prevents clause leakage and keeps pairs intact.
  BENCH-EXEC-09  BenchmarkRunner executes SystemP on the slice with 100% deterministic fidelity.
  BENCH-REC-10   Benchmark run records dataset version, configuration, timestamp, traces, and errors.
  BENCH-DB-11    Database-backed repository loads real rules and confirms non-gold provisional status.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import pytest
from sqlalchemy.orm import Session

from backend.data.seed_real_slice import (
    EXPECTED_GAZETTE_SHA256,
    GAZETTE_DOC_TITLE,
    seed_real_slice,
)
from backend.src.db.models import RuleORM
from backend.src.db.repositories import PostgresRegulatoryRepository, rule_orm_to_domain
from backend.src.evaluation.baselines import SystemP
from backend.src.evaluation.benchmark_runner import BenchmarkRunner
from backend.src.evaluation.benchmark_validator import (
    GAZETTE_2494_47_SHA256,
    KNOWN_REGULATION_3_RULES,
    load_benchmark_scenarios,
    validate_benchmark_slice,
)
from backend.src.evaluation.dataset_split import split_scenarios_by_clause
from backend.src.models.domain import BenchmarkScenario, OutcomeStatus

SLICE_PATH = Path("backend/data/benchmark/regulation_3_slice.jsonl")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def benchmark_scenarios() -> List[BenchmarkScenario]:
    """Load the initial Regulation 3 benchmark scenarios."""
    assert SLICE_PATH.exists(), f"Benchmark slice file missing at {SLICE_PATH}"
    return load_benchmark_scenarios(SLICE_PATH)


@pytest.fixture()
def populated_real_slice_db(db_session: Session) -> Session:
    """Populate isolated in-memory SQLite database with Gazette 2494/47 rules."""
    seed_real_slice(db_session)
    return db_session


# ---------------------------------------------------------------------------
# Tests: Loading, Validation, and Provenance
# ---------------------------------------------------------------------------

def test_bench_load_01_slice_loading(benchmark_scenarios: List[BenchmarkScenario]):
    """BENCH-LOAD-01: regulation_3_slice.jsonl exists and loads 12 valid scenarios."""
    assert len(benchmark_scenarios) == 12
    for scen in benchmark_scenarios:
        assert scen.scenario_id.startswith("SCEN-REG3-")
        assert scen.clause_id == "Regulation 3"
        assert scen.scenario_type in {"direct", "minimal_pair", "invariance", "temporal", "incomplete"}
        assert scen.gold_outcome in list(OutcomeStatus)
        assert scen.business_profile.business_id is not None


def test_bench_prov_02_traceable_provenance(benchmark_scenarios: List[BenchmarkScenario]):
    """BENCH-PROV-02: Every scenario possesses full, traceable provenance grounded in Gazette 2494/47."""
    for scen in benchmark_scenarios:
        extra = scen.model_extra or {}
        # 1. Exact official instrument identifier and SHA-256 hash
        assert extra.get("source_instrument") == GAZETTE_DOC_TITLE
        assert extra.get("source_hash") == EXPECTED_GAZETTE_SHA256

        # 2. Clause and page reference
        assert extra.get("source_clause") in {"Regulation 3", "Regulation 3 Proviso (a)", "Regulation 3 Proviso (b)", "Regulation 1 / Gazette Preamble"}
        assert extra.get("source_page") in {1, 2}
        assert len(extra.get("source_quote_span", "")) > 10

        # 3. Applicable rule IDs
        target_rules = extra.get("target_rule_ids") or []
        assert len(target_rules) >= 1
        for rid in target_rules:
            assert rid in KNOWN_REGULATION_3_RULES

        # 4. Rationale and review metadata
        assert len(extra.get("rationale", "")) > 15
        assert extra.get("review_status") == "PROVISIONAL_PRIMARY_REVIEW"
        assert extra.get("reviewer_role") == "PRIMARY_ANNOTATOR"
        assert len(extra.get("legal_notes", "")) > 10


def test_bench_prov_03_provisional_safety_gate(benchmark_scenarios: List[BenchmarkScenario]):
    """BENCH-PROV-03: No scenario or rule is falsely represented as expert-adjudicated gold."""
    for scen in benchmark_scenarios:
        extra = scen.model_extra or {}
        assert extra.get("is_gold_scenario") is False, (
            f"Scenario {scen.scenario_id} must NOT be marked is_gold_scenario=True."
        )
        assert extra.get("is_gold_rule") is False, (
            f"Scenario {scen.scenario_id} must NOT be marked is_gold_rule=True."
        )

    # Validate with validator
    report = validate_benchmark_slice(
        benchmark_scenarios,
        known_rules=KNOWN_REGULATION_3_RULES,
        known_sources={GAZETTE_2494_47_SHA256},
        enforce_provisional=True,
    )
    assert report.is_valid is True
    assert report.provisional_scenarios_count == 12
    assert report.gold_scenarios_count == 0
    assert len(report.errors) == 0


def test_bench_integ_04_error_detection(benchmark_scenarios: List[BenchmarkScenario]):
    """BENCH-INTEG-04: Duplicate IDs, unknown rules, and unknown hashes trigger validation errors."""
    # 1. Duplicate ID detection
    cloned = [s.model_copy(deep=True) for s in benchmark_scenarios]
    cloned.append(cloned[0].model_copy(deep=True))
    rep_dup = validate_benchmark_slice(cloned)
    assert rep_dup.is_valid is False
    assert any("Duplicate scenario IDs detected" in err for err in rep_dup.errors)

    # 2. Unknown rule detection
    bad_rule_scens = [s.model_copy(deep=True) for s in benchmark_scenarios]
    bad_rule_scens[0].model_extra["target_rule_ids"] = ["RULE-NONEXISTENT-999"]
    rep_rule = validate_benchmark_slice(bad_rule_scens, known_rules=KNOWN_REGULATION_3_RULES)
    assert rep_rule.is_valid is False
    assert any("references unknown rule" in err for err in rep_rule.errors)

    # 3. Unknown source hash detection
    bad_hash_scens = [s.model_copy(deep=True) for s in benchmark_scenarios]
    bad_hash_scens[0].model_extra["source_hash"] = "deadbeef12345678"
    rep_hash = validate_benchmark_slice(bad_hash_scens, known_sources={GAZETTE_2494_47_SHA256})
    assert rep_hash.is_valid is False
    assert any("unknown source_hash" in err for err in rep_hash.errors)

    # 4. False gold status rejection
    gold_scens = [s.model_copy(deep=True) for s in benchmark_scenarios]
    gold_scens[0].model_extra["is_gold_scenario"] = True
    rep_gold = validate_benchmark_slice(gold_scens, enforce_provisional=True)
    assert rep_gold.is_valid is False
    assert any("marked as gold" in err for err in rep_gold.errors)


# ---------------------------------------------------------------------------
# Tests: Pair Integrity and Abstention
# ---------------------------------------------------------------------------

def test_bench_pair_05_minimal_pair_sensitivity(benchmark_scenarios: List[BenchmarkScenario]):
    """BENCH-PAIR-05: Minimal pair PAIR-REG3-MARKET-CHANNEL flips outcome on market.b2b_only."""
    pair_scens = [s for s in benchmark_scenarios if s.pair_id == "PAIR-REG3-MARKET-CHANNEL"]
    assert len(pair_scens) == 2

    scen_a = next(s for s in pair_scens if s.scenario_id == "SCEN-REG3-PAIR-09A")
    scen_b = next(s for s in pair_scens if s.scenario_id == "SCEN-REG3-PAIR-09B")

    # Profile perturbation: only market.b2b_only flips
    assert scen_a.business_profile.market.model_extra["b2b_only"] is False
    assert scen_b.business_profile.market.model_extra["b2b_only"] is True

    # Outcome sensitivity flip
    assert scen_a.gold_outcome == OutcomeStatus.APPLICABLE
    assert scen_b.gold_outcome == OutcomeStatus.NOT_APPLICABLE


def test_bench_pair_06_invariance_pair_stability(benchmark_scenarios: List[BenchmarkScenario]):
    """BENCH-PAIR-06: Invariance pair PAIR-REG3-INV-BIZ-METADATA preserves APPLICABLE outcome."""
    pair_scens = [s for s in benchmark_scenarios if s.pair_id == "PAIR-REG3-INV-BIZ-METADATA"]
    assert len(pair_scens) == 2

    scen_a = next(s for s in pair_scens if s.scenario_id == "SCEN-REG3-INV-10A")
    scen_b = next(s for s in pair_scens if s.scenario_id == "SCEN-REG3-INV-10B")

    # Irrelevant perturbation: different company name, district, and reg number
    assert scen_a.business_profile.model_extra["company_name"] != scen_b.business_profile.model_extra["company_name"]
    assert scen_a.business_profile.premises.model_extra["district"] != scen_b.business_profile.premises.model_extra["district"]

    # Invariant stability
    assert scen_a.gold_outcome == OutcomeStatus.APPLICABLE
    assert scen_b.gold_outcome == OutcomeStatus.APPLICABLE


def test_bench_abst_07_incomplete_profiles_3_valued_logic(benchmark_scenarios: List[BenchmarkScenario]):
    """BENCH-ABST-07: Incomplete scenarios mandate CONDITIONAL_MISSING_DATA with specific fields."""
    incomplete = [s for s in benchmark_scenarios if s.scenario_type == "incomplete"]
    assert len(incomplete) == 2

    chan_scen = next(s for s in incomplete if s.scenario_id == "SCEN-REG3-INC-CHAN-05")
    pack_scen = next(s for s in incomplete if s.scenario_id == "SCEN-REG3-INC-PACK-06")

    assert chan_scen.gold_outcome == OutcomeStatus.CONDITIONAL_MISSING_DATA
    assert chan_scen.gold_missing_fields == ["market.b2b_only"]

    assert pack_scen.gold_outcome == OutcomeStatus.CONDITIONAL_MISSING_DATA
    assert pack_scen.gold_missing_fields == ["products.prepackaged"]


def test_bench_split_08_clause_leakage_protection(benchmark_scenarios: List[BenchmarkScenario]):
    """BENCH-SPLIT-08: Clause-grouped partitioning prevents clause leakage and preserves pairs."""
    train_set, test_set = split_scenarios_by_clause(benchmark_scenarios, test_ratio=0.3, random_seed=42)

    # Since all 12 scenarios belong to "Regulation 3", they must all stay in one partition
    assert len(train_set) == 12
    assert len(test_set) == 0

    # Test multi-clause safety by adding dummy scenarios from another clause
    dummy_scens = [
        BenchmarkScenario(
            scenario_id="SCEN-DUMMY-01",
            clause_id="Regulation 99",
            scenario_type="direct",
            business_profile=benchmark_scenarios[0].business_profile,
            as_at_date="2026-08-01",
            gold_outcome=OutcomeStatus.NOT_APPLICABLE,
        )
    ]
    combined = list(benchmark_scenarios) + dummy_scens
    c_train, c_test = split_scenarios_by_clause(combined, test_ratio=0.5, random_seed=42)

    train_cids = {s.clause_id for s in c_train}
    test_cids = {s.clause_id for s in c_test}
    assert len(train_cids.intersection(test_cids)) == 0, "Zero clause leakage violated!"


# ---------------------------------------------------------------------------
# Tests: Benchmark Runner Execution and Trace Provenance
# ---------------------------------------------------------------------------

def test_bench_exec_09_runner_execution(
    benchmark_scenarios: List[BenchmarkScenario],
    populated_real_slice_db: Session,
):
    """BENCH-EXEC-09: BenchmarkRunner executes SystemP on the slice with 100% deterministic fidelity."""
    db = populated_real_slice_db
    retail_orm = db.query(RuleORM).filter_by(rule_id="RULE-FCAU-2494-47-REG-3").first()
    b2b_orm = db.query(RuleORM).filter_by(rule_id="RULE-FCAU-2494-47-REG-3-B2B").first()
    assert retail_orm is not None
    assert b2b_orm is not None

    r_retail = rule_orm_to_domain(retail_orm)
    r_b2b = rule_orm_to_domain(b2b_orm)

    system_p = SystemP(rules={
        r_retail.rule_id: r_retail,
        r_b2b.rule_id: r_b2b,
        "Regulation 3": r_retail,
        "Regulation 3 Proviso (b)": r_b2b,
    })

    runner = BenchmarkRunner()
    report = runner.run(
        system=system_p,
        scenarios=benchmark_scenarios,
        dataset_version="v1.0-provisional-reg3",
        dataset_path=str(SLICE_PATH),
        configuration={"evaluation_mode": "deterministic_symbolic", "target_regulation": "Regulation 3"},
    )

    # 1. Classification fidelity
    assert report.total_scenarios == 12
    assert report.accuracy == 1.0
    assert report.macro_f1 == 1.0
    assert report.consistency_score == 1.0
    assert report.temporal_accuracy == 1.0
    assert report.missing_fields_accuracy == 1.0
    assert report.abstention_f1 == 1.0
    assert len(report.errors) == 0

    # 2. Every individual scenario evaluated correctly
    for ev in report.scenario_evaluations:
        assert ev.is_outcome_correct is True
        assert ev.predicted_outcome == ev.gold_outcome
        if ev.gold_outcome == OutcomeStatus.CONDITIONAL_MISSING_DATA:
            assert ev.missing_fields_correct is True


def test_bench_rec_10_traceable_run_metadata(
    benchmark_scenarios: List[BenchmarkScenario],
    populated_real_slice_db: Session,
):
    """BENCH-REC-10: Benchmark run records dataset version, config, timestamp, traces, and errors."""
    db = populated_real_slice_db
    r_retail = rule_orm_to_domain(db.query(RuleORM).filter_by(rule_id="RULE-FCAU-2494-47-REG-3").first())
    r_b2b = rule_orm_to_domain(db.query(RuleORM).filter_by(rule_id="RULE-FCAU-2494-47-REG-3-B2B").first())

    system_p = SystemP(rules={r_retail.rule_id: r_retail, r_b2b.rule_id: r_b2b})
    runner = BenchmarkRunner()

    report = runner.run(
        system=system_p,
        scenarios=benchmark_scenarios,
        dataset_version="v1.0-provisional-reg3",
        dataset_path=str(SLICE_PATH),
        configuration={"engine": "symbolic_kleene_3val"},
    )

    # Check run-level metadata
    assert report.dataset_version == "v1.0-provisional-reg3"
    assert report.dataset_path == str(SLICE_PATH)
    assert report.timestamp is not None
    assert report.configuration == {"engine": "symbolic_kleene_3val"}
    assert isinstance(report.errors, list)

    # Check scenario-level trace records
    for ev in report.scenario_evaluations:
        assert ev.scenario_id.startswith("SCEN-REG3-")
        assert ev.reason is not None
        assert isinstance(ev.evaluation_trace, list)
        assert len(ev.evaluation_trace) > 0 or ev.scenario_type == "temporal"
        if getattr(ev, "target_rule_ids", None):
            assert ev.target_rule_ids[0] in KNOWN_REGULATION_3_RULES


def test_bench_db_11_repository_backed_execution_sqlite(populated_real_slice_db: Session):
    """BENCH-DB-11: Database repository loads real rules with verified non-gold status."""
    repo = PostgresRegulatoryRepository(populated_real_slice_db)

    # Retrieve rules through repository
    rules = repo.get_rules_by_ids(["RULE-FCAU-2494-47-REG-3", "RULE-FCAU-2494-47-REG-3-B2B"])
    assert len(rules) == 2

    for r in rules:
        assert r.is_gold_rule is False
        assert r.review_status == "APPROVED"
        assert r.source.gazette_no == "Gazette Extraordinary No. 2494/47"

    # Verify B2B obligations are intact
    b2b_rule = next(r for r in rules if r.rule_id == "RULE-FCAU-2494-47-REG-3-B2B")
    assert "not_for_retail_sale_statement" in b2b_rule.obligation.disclosures
    assert len(b2b_rule.obligation.disclosures) == 11


# ---------------------------------------------------------------------------
# Phase B / Phase C Audit Regression Tests
# ---------------------------------------------------------------------------

def test_bench_pair_negative_01_malformed_cardinality(benchmark_scenarios: List[BenchmarkScenario]):
    """AUDIT-PAIR-01: Pairs with != 2 members must strictly fail validation."""
    scens = [s.model_copy(deep=True) for s in benchmark_scenarios]
    # Remove one member of minimal pair
    scens = [s for s in scens if s.scenario_id != "SCEN-REG3-PAIR-09B"]
    rep = validate_benchmark_slice(scens)
    assert rep.is_valid is False
    assert any("must have exactly 2 scenarios, got 1" in err for err in rep.errors)


def test_bench_pair_negative_02_minimal_pair_second_unintended_change(benchmark_scenarios: List[BenchmarkScenario]):
    """AUDIT-PAIR-02: Minimal pair with an unintended second feature change must fail validation."""
    scens = [s.model_copy(deep=True) for s in benchmark_scenarios]
    scen_9b = next(s for s in scens if s.scenario_id == "SCEN-REG3-PAIR-09B")
    # Mutate a second legally relevant field: activity changed from food_manufacturing to retail_trade
    scen_9b.business_profile.activity = "retail_trade"

    rep = validate_benchmark_slice(scens)
    assert rep.is_valid is False
    assert any("input differences" in err or "uncontrolled feature differences" in err for err in rep.errors)


def test_bench_pair_negative_03_invariance_pair_mutates_operative_condition(benchmark_scenarios: List[BenchmarkScenario]):
    """AUDIT-PAIR-03: Invariance pair that mutates a legally operative condition must fail validation."""
    scens = [s.model_copy(deep=True) for s in benchmark_scenarios]
    scen_10b = next(s for s in scens if s.scenario_id == "SCEN-REG3-INV-10B")
    # Inadvertently mutate an operative field: prepackaged flag changed from True to False
    scen_10b.business_profile.products[0].prepackaged = False

    rep = validate_benchmark_slice(scens)
    assert rep.is_valid is False
    assert any("mutates legally relevant field" in err for err in rep.errors)


def test_bench_temp_boundary_04_before_on_after_commencement(populated_real_slice_db: Session):
    """AUDIT-TEMP-04: Commencement boundary at 2026-07-01 behaves correctly before, on, and after."""
    from backend.src.engine.applicability import evaluate_rule

    repo = PostgresRegulatoryRepository(populated_real_slice_db)
    retail_rule = repo.get_rules_by_ids(["RULE-FCAU-2494-47-REG-3"])[0]

    profile = benchmark_scenarios = BenchmarkScenario(
        scenario_id="TEMP-TEST",
        clause_id="Regulation 3",
        scenario_type="temporal",
        business_profile={
            "activity": "food_manufacturing",
            "products": [{"prepackaged": True}],
            "market": {"b2b_only": False},
            "packaged_in_presence_of_purchaser": False,
        },
        as_at_date="2026-06-30",
        gold_outcome=OutcomeStatus.NOT_APPLICABLE,
        gold_temporal_status="NOT_YET_IN_FORCE",
    ).business_profile

    # 1. Day before commencement (2026-06-30)
    res_before = evaluate_rule(retail_rule, profile, as_at_date="2026-06-30")
    assert res_before.status == OutcomeStatus.NOT_APPLICABLE
    assert res_before.temporal_status == "NOT_YET_IN_FORCE"
    assert "Rule not yet in force" in (res_before.reason or "")

    # 2. Commencement day (2026-07-01)
    res_on = evaluate_rule(retail_rule, profile, as_at_date="2026-07-01")
    assert res_on.status == OutcomeStatus.APPLICABLE
    assert res_on.temporal_status == "IN_FORCE"

    # 3. Day after commencement (2026-07-02)
    res_after = evaluate_rule(retail_rule, profile, as_at_date="2026-07-02")
    assert res_after.status == OutcomeStatus.APPLICABLE
    assert res_after.temporal_status == "IN_FORCE"


def test_bench_b2b_coexistence_05_retail_vs_b2b_rule(
    benchmark_scenarios: List[BenchmarkScenario],
    populated_real_slice_db: Session,
):
    """AUDIT-B2B-05: SCEN-REG3-PAIR-09B is NOT_APPLICABLE for retail, but APPLICABLE for B2B affirmative rule."""
    from backend.src.engine.applicability import evaluate_rule

    repo = PostgresRegulatoryRepository(populated_real_slice_db)
    rules = {r.rule_id: r for r in repo.get_rules_by_ids(["RULE-FCAU-2494-47-REG-3", "RULE-FCAU-2494-47-REG-3-B2B"])}

    scen_9b = next(s for s in benchmark_scenarios if s.scenario_id == "SCEN-REG3-PAIR-09B")

    # Evaluate against General Retail Rule: NOT_APPLICABLE (due to Proviso (b) B2B exemption)
    res_retail = evaluate_rule(rules["RULE-FCAU-2494-47-REG-3"], scen_9b.business_profile, as_at_date=scen_9b.as_at_date)
    assert res_retail.status == OutcomeStatus.NOT_APPLICABLE
    assert res_retail.reason == "Rule exception condition met."

    # Evaluate against Affirmative B2B Rule: APPLICABLE (mandating disclosures + 3 mm label)
    res_b2b = evaluate_rule(rules["RULE-FCAU-2494-47-REG-3-B2B"], scen_9b.business_profile, as_at_date=scen_9b.as_at_date)
    assert res_b2b.status == OutcomeStatus.APPLICABLE
    assert "common_name" in (rules["RULE-FCAU-2494-47-REG-3-B2B"].obligation.disclosures or [])
    assert "not_for_retail_sale_statement" in (rules["RULE-FCAU-2494-47-REG-3-B2B"].obligation.disclosures or [])


def test_bench_split_negative_06_naive_random_split_causes_leakage(benchmark_scenarios: List[BenchmarkScenario]):
    """AUDIT-SPLIT-06: Naive random record-level partitioning leaks Regulation 3 across train and test."""
    import random

    rng = random.Random(42)
    shuffled = list(benchmark_scenarios)
    rng.shuffle(shuffled)

    # Naive record-level split: 70% train, 30% test
    split_idx = int(len(shuffled) * 0.7)
    naive_train = shuffled[:split_idx]
    naive_test = shuffled[split_idx:]

    naive_train_cids = {s.clause_id for s in naive_train}
    naive_test_cids = {s.clause_id for s in naive_test}
    leakage = naive_train_cids.intersection(naive_test_cids)

    # In a naive random split, Regulation 3 is leaked into both partitions!
    assert "Regulation 3" in leakage, "Expected naive split to leak Regulation 3."

    # In contrast, split_scenarios_by_clause prevents leakage
    safe_train, safe_test = split_scenarios_by_clause(benchmark_scenarios, test_ratio=0.3)
    safe_train_cids = {s.clause_id for s in safe_train}
    safe_test_cids = {s.clause_id for s in safe_test}
    assert len(safe_train_cids.intersection(safe_test_cids)) == 0


def test_bench_rec_07_dataset_hash_recorded(
    benchmark_scenarios: List[BenchmarkScenario],
    populated_real_slice_db: Session,
):
    """AUDIT-REC-07: BenchmarkRunner records tamper-evident SHA-256 hash of scenario file."""
    import hashlib

    repo = PostgresRegulatoryRepository(populated_real_slice_db)
    r1 = repo.get_rules_by_ids(["RULE-FCAU-2494-47-REG-3"])[0]

    system_p = SystemP(rules={r1.rule_id: r1})
    runner = BenchmarkRunner()

    report = runner.run(
        system=system_p,
        scenarios=benchmark_scenarios,
        dataset_version="v1.0-provisional-reg3",
        dataset_path=str(SLICE_PATH),
    )

    expected_hash = hashlib.sha256(SLICE_PATH.read_bytes()).hexdigest()
    assert report.dataset_hash == expected_hash
    assert len(report.dataset_hash) == 64


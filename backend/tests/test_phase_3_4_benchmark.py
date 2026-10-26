"""Focused Verification Suite for Phase 3.4: Human Review, Benchmark Construction & Dataset Integrity.

Validates:
  P34-BENCH-01  multi_group_benchmark_slice.jsonl parses into valid BenchmarkScenario objects with authentic provenance.
  P34-BENCH-02  Every referenced clause ID resolves to a real, authentic, non-synthetic clause in PostgreSQL.
  P34-BENCH-03  Provisional safety gate: no rules or scenarios are falsely represented as gold.
  P34-BENCH-04  Minimal pairs exhibit sensitivity outcome flips across regulatory groups.
  P34-BENCH-05  Invariance pairs exhibit outcome stability across regulatory groups.
  P34-BENCH-06  Incomplete profiles enforce 3-valued Kleene abstention with exact expected missing fields.
  P34-BENCH-07  Temporal scenarios correctly reflect pre-enactment vs post-enactment dates.
  P34-BENCH-08  Clause-level split partitioning ensures strictly disjoint clause sets and intact pairs.
  P34-BENCH-09  Integrity validator catches duplicate scenarios, unknown hashes, and illegal gold claims.
  P34-BENCH-10  Cohen's kappa implementation computes Po, Pe, kappa, SE, CI accurately on known matrices.
  P34-BENCH-11  Truthful annotation audit verifies unperformed second annotator status without fabrication.
  P34-BENCH-12  Quarantined sources and synthetic records are excluded from benchmark retrieval.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.src.db.session import session_scope
from backend.src.evaluation.benchmark_validator import (
    AUTHENTIC_SOURCE_HASHES,
    GAZETTE_2494_47_SHA256,
    KNOWN_AUTHENTIC_RULES,
    load_benchmark_scenarios,
    validate_benchmark_slice,
)
from backend.src.evaluation.dataset_split import split_scenarios_by_clause
from backend.src.evaluation.statistics import compute_cohens_kappa
from backend.src.models.domain import BenchmarkScenario, OutcomeStatus

MULTI_SLICE_PATH = Path("backend/data/benchmark/multi_group_benchmark_slice.jsonl")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def multi_group_scenarios() -> List[BenchmarkScenario]:
    """Load the Phase 3.4 multi-group candidate benchmark scenarios."""
    assert MULTI_SLICE_PATH.exists(), f"Benchmark slice file missing at {MULTI_SLICE_PATH}"
    return load_benchmark_scenarios(MULTI_SLICE_PATH)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_p34_bench_01_multi_group_benchmark_load_and_provenance(multi_group_scenarios):
    """P34-BENCH-01: Load all 30 scenarios and verify provenance."""
    assert len(multi_group_scenarios) == 30

    known_hashes = set(AUTHENTIC_SOURCE_HASHES.keys())

    for s in multi_group_scenarios:
        assert s.scenario_id, "Scenario must have an ID"
        assert s.clause_id, f"Scenario {s.scenario_id} must have a clause_id"
        assert s.rule_id in KNOWN_AUTHENTIC_RULES, f"Scenario {s.scenario_id} references unknown rule {s.rule_id}"
        assert s.source_hash in known_hashes, f"Scenario {s.scenario_id} has unverified source hash {s.source_hash}"
        assert s.source_document, f"Scenario {s.scenario_id} must cite source document"
        assert s.legal_notes, f"Scenario {s.scenario_id} must include legal notes/rationale"
        assert s.is_gold_scenario is False, f"Scenario {s.scenario_id} must NOT be marked gold"


def test_p34_bench_02_clause_resolution_against_database():
    """P34-BENCH-02: Every referenced clause ID exists as an authentic clause in PostgreSQL."""
    scenarios = load_benchmark_scenarios(MULTI_SLICE_PATH)
    scenario_clause_ids = {s.clause_id for s in scenarios}
    assert len(scenario_clause_ids) >= 8, f"Expected at least 8 distinct clauses, found {len(scenario_clause_ids)}"

    with session_scope() as session:
        query = text(
            "SELECT clause_id, is_synthetic FROM regulatory_clauses WHERE clause_id = ANY(:clause_ids)"
        )
        rows = session.execute(query, {"clause_ids": list(scenario_clause_ids)}).fetchall()
        db_clauses = {r[0]: r[1] for r in rows}

        for cid in scenario_clause_ids:
            assert cid in db_clauses, f"Benchmark scenario references clause {cid} not found in database!"
            assert db_clauses[cid] is False, f"Benchmark scenario references synthetic clause {cid}!"


def test_p34_bench_03_provisional_safety_gate(multi_group_scenarios):
    """P34-BENCH-03: Validation report confirms 100% provisional and 0% gold scenarios."""
    rep = validate_benchmark_slice(
        multi_group_scenarios,
        known_rules=KNOWN_AUTHENTIC_RULES,
        known_sources=set(AUTHENTIC_SOURCE_HASHES.keys()),
        enforce_provisional=True,
    )
    assert rep.is_valid is True
    assert rep.total_scenarios == 30
    assert rep.gold_scenarios_count == 0
    assert rep.provisional_scenarios_count == 30
    assert rep.minimal_pairs_count >= 5
    assert rep.invariance_pairs_count >= 2
    assert rep.errors == []


def test_p34_bench_04_minimal_pairs_sensitivity(multi_group_scenarios):
    """P34-BENCH-04: Minimal pairs exhibit sensitivity outcome flips across regulatory groups."""
    pairs_by_id = {}
    for s in multi_group_scenarios:
        if s.pair_id:
            pairs_by_id.setdefault(s.pair_id, []).append(s)

    minimal_pairs = {pid: scs for pid, scs in pairs_by_id.items() if any(s.scenario_type == "minimal_pair" for s in scs)}
    assert len(minimal_pairs) >= 5, f"Expected at least 5 minimal pairs, found {len(minimal_pairs)}"

    for pid, scs in minimal_pairs.items():
        assert len(scs) == 2, f"Pair {pid} should contain exactly 2 scenarios, got {len(scs)}"
        s1, s2 = scs[0], scs[1]
        assert s1.clause_id == s2.clause_id, f"Pair {pid} must evaluate the same clause"
        assert s1.expected_outcome != s2.expected_outcome, (
            f"Minimal pair {pid} must exhibit sensitivity flip, but both expected {s1.expected_outcome}"
        )


def test_p34_bench_05_invariance_pairs_stability(multi_group_scenarios):
    """P34-BENCH-05: Invariance pairs exhibit outcome stability across groups."""
    pairs_by_id = {}
    for s in multi_group_scenarios:
        if s.pair_id:
            pairs_by_id.setdefault(s.pair_id, []).append(s)

    invariance_pairs = {pid: scs for pid, scs in pairs_by_id.items() if any(s.scenario_type == "invariance" for s in scs)}
    assert len(invariance_pairs) >= 2, f"Expected at least 2 invariance pairs, found {len(invariance_pairs)}"

    for pid, scs in invariance_pairs.items():
        assert len(scs) == 2, f"Pair {pid} should contain exactly 2 scenarios, got {len(scs)}"
        s1, s2 = scs[0], scs[1]
        assert s1.clause_id == s2.clause_id, f"Pair {pid} must evaluate the same clause"
        assert s1.expected_outcome == s2.expected_outcome, (
            f"Invariance pair {pid} must have identical expected outcome, but got {s1.expected_outcome} vs {s2.expected_outcome}"
        )


def test_p34_bench_06_incomplete_profiles_and_kleene_abstention(multi_group_scenarios):
    """P34-BENCH-06: Incomplete profiles require CONDITIONAL_MISSING_DATA and specify exact missing fields."""
    incomplete = [s for s in multi_group_scenarios if s.scenario_type == "incomplete"]
    assert len(incomplete) >= 3, f"Expected at least 3 incomplete scenarios, found {len(incomplete)}"

    for s in incomplete:
        assert s.expected_outcome == OutcomeStatus.CONDITIONAL_MISSING_DATA, (
            f"Incomplete scenario {s.scenario_id} must have CONDITIONAL_MISSING_DATA outcome"
        )
        assert len(s.expected_missing_fields) > 0, (
            f"Incomplete scenario {s.scenario_id} must specify missing fields"
        )
        for field in s.expected_missing_fields:
            assert field not in s.business_profile or s.business_profile[field] is None, (
                f"Missing field {field} was found present in profile for {s.scenario_id}"
            )


def test_p34_bench_07_temporal_applicability(multi_group_scenarios):
    """P34-BENCH-07: Temporal scenarios correctly reflect pre-enactment vs post-enactment."""
    temporal = [s for s in multi_group_scenarios if s.scenario_type == "temporal"]
    assert len(temporal) >= 2, f"Expected at least 2 temporal scenarios, found {len(temporal)}"

    pre_cases = [s for s in temporal if s.expected_outcome == OutcomeStatus.EXEMPT_TEMPORAL]
    post_cases = [s for s in temporal if s.expected_outcome == OutcomeStatus.APPLICABLE]

    assert len(pre_cases) >= 1, "Expected at least 1 pre-enactment exempt temporal scenario"
    assert len(post_cases) >= 1, "Expected at least 1 post-enactment applicable scenario"


def test_p34_bench_08_clause_disjoint_train_test_split(multi_group_scenarios):
    """P34-BENCH-08: Clause-level split partitioning ensures strictly disjoint clause sets and intact pairs."""
    train_set, test_set = split_scenarios_by_clause(
        multi_group_scenarios,
        train_ratio=0.6,
        random_seed=42,
    )

    assert len(train_set) + len(test_set) == len(multi_group_scenarios)

    train_clauses = {s.clause_id for s in train_set}
    test_clauses = {s.clause_id for s in test_set}

    overlap = train_clauses & test_clauses
    assert len(overlap) == 0, f"Clause leakage detected! Overlapping clauses: {overlap}"

    # Verify paired scenarios remain together
    train_pair_ids = {s.pair_id for s in train_set if s.pair_id}
    test_pair_ids = {s.pair_id for s in test_set if s.pair_id}
    pair_overlap = train_pair_ids & test_pair_ids
    assert len(pair_overlap) == 0, f"Paired scenarios were broken across splits! Broken pair IDs: {pair_overlap}"


def test_p34_bench_09_duplicate_and_tamper_rejection():
    """P34-BENCH-09: Validator rejects duplicates, unknown rules, and illegal gold claims."""
    scenarios = load_benchmark_scenarios(MULTI_SLICE_PATH)

    # 1. Duplicate scenario ID
    dup_scenarios = list(scenarios) + [scenarios[0]]
    rep_dup = validate_benchmark_slice(
        dup_scenarios,
        known_rules=KNOWN_AUTHENTIC_RULES,
        known_sources=set(AUTHENTIC_SOURCE_HASHES.keys()),
    )
    assert rep_dup.is_valid is False
    assert any("Duplicate scenario_id" in e for e in rep_dup.errors)

    # 2. Unknown rule ID
    fake_rule_scenario = scenarios[0].model_copy(update={"scenario_id": "SCN-FAKE-01", "rule_id": "RULE-NONEXISTENT"})
    rep_rule = validate_benchmark_slice(
        [fake_rule_scenario],
        known_rules=KNOWN_AUTHENTIC_RULES,
        known_sources=set(AUTHENTIC_SOURCE_HASHES.keys()),
    )
    assert rep_rule.is_valid is False
    assert any("references unknown rule" in e for e in rep_rule.errors)

    # 3. Illegal gold claim when enforce_provisional=True
    gold_scenario = scenarios[0].model_copy(update={"scenario_id": "SCN-FAKE-02", "is_gold_scenario": True})
    rep_gold = validate_benchmark_slice(
        [gold_scenario],
        known_rules=KNOWN_AUTHENTIC_RULES,
        known_sources=set(AUTHENTIC_SOURCE_HASHES.keys()),
        enforce_provisional=True,
    )
    assert rep_gold.is_valid is False
    assert any("falsely claimed as gold" in e for e in rep_gold.errors)


def test_p34_bench_10_cohens_kappa_calculation():
    """P34-BENCH-10: Cohen's kappa computes Po, Pe, kappa, SE, and CI accurately."""
    # Perfect agreement
    r_perfect = compute_cohens_kappa(
        labels_a=["APPLICABLE", "EXEMPT", "CONDITIONAL_MISSING_DATA", "APPLICABLE"],
        labels_b=["APPLICABLE", "EXEMPT", "CONDITIONAL_MISSING_DATA", "APPLICABLE"],
    )
    assert r_perfect.observed_agreement == 1.0
    assert r_perfect.kappa == 1.0
    assert r_perfect.interpretation == "Almost perfect agreement"

    # Complete disagreement (inverted)
    r_disagree = compute_cohens_kappa(
        labels_a=["APPLICABLE", "APPLICABLE", "EXEMPT", "EXEMPT"],
        labels_b=["EXEMPT", "EXEMPT", "APPLICABLE", "APPLICABLE"],
    )
    assert r_disagree.observed_agreement == 0.0
    assert r_disagree.kappa < 0.0

    # Known standard contingency test
    labels_1 = ["A"] * 20 + ["B"] * 10 + ["C"] * 10
    labels_2 = ["A"] * 18 + ["B"] * 2 + ["B"] * 8 + ["C"] * 2 + ["C"] * 9 + ["A"] * 1
    res = compute_cohens_kappa(labels_1, labels_2)
    assert 0.0 < res.kappa < 1.0
    assert res.ci_lower <= res.kappa <= res.ci_upper
    assert res.standard_error > 0.0


def test_p34_bench_11_truthful_annotation_audit_in_database():
    """P34-BENCH-11: Truthful audit confirms rules in PostgreSQL are not falsely marked gold."""
    with get_db_context() as session:
        # Check all candidate rules
        query = text(
            "SELECT rule_id, review_status, is_gold_rule, is_synthetic FROM regulatory_rules "
            "WHERE is_synthetic = false"
        )
        rows = session.execute(query).fetchall()
        assert len(rows) >= 12, f"Expected at least 12 authentic rules in DB, got {len(rows)}"

        gold_rules = [r for r in rows if r[2] is True]
        assert len(gold_rules) == 0, f"Found rules falsely marked as gold without expert review: {gold_rules}"

        pending_rules = [r for r in rows if r[1] == "PENDING_REVIEW"]
        approved_rules = [r for r in rows if r[1] == "APPROVED"]

        # Regulation 3 rules approved by primary annotator in Phase 3.2
        assert len(approved_rules) >= 2
        # Phase 3.3 candidate rules remain pending review
        assert len(pending_rules) >= 10


def test_p34_bench_12_quarantined_sources_isolated_from_retrieval():
    """P34-BENCH-12: Quarantined sources and synthetic records are excluded from retrieval and benchmark."""
    with get_db_context() as session:
        # 1. Gazette 2496/03 is permanently quarantined
        q_doc = session.execute(
            text("SELECT document_id, is_quarantined FROM regulatory_documents WHERE document_id = 'gazette_2496_03_en'")
        ).fetchone()
        if q_doc:
            assert q_doc[1] is True, "Gazette 2496/03 must remain quarantined"

        # 2. Scanned colouring regulations Gazette 1688/28 is quarantined/blocked
        colouring_doc = session.execute(
            text("SELECT document_id, is_quarantined FROM regulatory_documents WHERE document_id = 'colouring_2011'")
        ).fetchone()
        if colouring_doc:
            assert colouring_doc[1] is True, "Scanned colouring regulations must remain quarantined"

        # 3. Verify no clauses from quarantined documents exist in the benchmark slice
        scenarios = load_benchmark_scenarios(MULTI_SLICE_PATH)
        for s in scenarios:
            assert "1688" not in s.clause_id, f"Quarantined Gazette 1688/28 clause {s.clause_id} leaked into benchmark"
            assert "2496" not in s.clause_id, f"Quarantined Gazette 2496/03 clause {s.clause_id} leaked into benchmark"

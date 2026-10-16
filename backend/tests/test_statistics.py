"""Unit tests for clustered statistics and paired hypothesis testing (Milestone 6).

Validates:
  STAT-001  cluster_bootstrap_metric point estimate matches direct metric and CI bounds enclose it.
  STAT-002  cluster_bootstrap_metric resamples at the clause_id cluster level.
  STAT-003  paired_cluster_bootstrap_test detects significant performance difference.
  STAT-004  paired_cluster_bootstrap_test returns zero difference and p=1.0 for identical systems.
  STAT-005  compute_contingency_table correctly counts concordant and discordant pairs.
"""

from __future__ import annotations

import pytest

from backend.src.evaluation.statistics import (
    cluster_bootstrap_metric,
    compute_contingency_table,
    paired_cluster_bootstrap_test,
)
from backend.src.models.domain import OutcomeStatus, ScenarioEvaluation


def _make_eval(
    scenario_id: str,
    clause_id: str,
    is_correct: bool,
    pred: OutcomeStatus = OutcomeStatus.APPLICABLE,
    gold: OutcomeStatus = OutcomeStatus.APPLICABLE,
) -> ScenarioEvaluation:
    """Helper to construct ScenarioEvaluation."""
    return ScenarioEvaluation(
        scenario_id=scenario_id,
        clause_id=clause_id,
        scenario_type="direct",
        predicted_outcome=pred,
        gold_outcome=gold,
        is_outcome_correct=is_correct,
        missing_fields_correct=True,
    )


def test_stat_001_cluster_bootstrap_bounds_and_point_estimate():
    """Cluster bootstrap point estimate matches direct mean and 95% CI encloses it."""
    evals = [
        _make_eval("s1", "clause_a", True),
        _make_eval("s2", "clause_a", True),
        _make_eval("s3", "clause_b", False),
        _make_eval("s4", "clause_b", True),
        _make_eval("s5", "clause_c", True),
        _make_eval("s6", "clause_c", False),
    ]

    metric_fn = lambda evs: sum(1 for e in evs if e.is_outcome_correct) / len(evs)
    res = cluster_bootstrap_metric(
        evaluations=evals,
        metric_fn=metric_fn,
        cluster_key="clause_id",
        n_bootstraps=500,
        random_seed=42,
    )

    expected_acc = 4 / 6  # 0.6667
    assert round(res.point_estimate, 4) == round(expected_acc, 4)
    assert res.ci_lower <= res.point_estimate <= res.ci_upper
    assert res.std_err > 0.0
    assert res.n_bootstraps == 500


def test_stat_002_cluster_level_resampling_unit():
    """Cluster bootstrap samples entire clusters together."""
    # Two clusters: clause_all_correct (all True) vs clause_all_wrong (all False)
    evals = [
        _make_eval("s1", "cluster_good", True),
        _make_eval("s2", "cluster_good", True),
        _make_eval("s3", "cluster_good", True),
        _make_eval("s4", "cluster_bad", False),
        _make_eval("s5", "cluster_bad", False),
        _make_eval("s6", "cluster_bad", False),
    ]

    metric_fn = lambda evs: sum(1 for e in evs if e.is_outcome_correct) / len(evs)
    res = cluster_bootstrap_metric(
        evaluations=evals,
        metric_fn=metric_fn,
        cluster_key="clause_id",
        n_bootstraps=200,
        random_seed=123,
    )

    # Point estimate is 0.5; clusters sampled are all 1.0 or all 0.0
    assert res.point_estimate == 0.5
    assert res.ci_lower <= 0.5 <= res.ci_upper


def test_stat_003_paired_cluster_bootstrap_superiority():
    """Paired cluster bootstrap correctly identifies a significant performance advantage."""
    # System A gets 100% correct, System B gets 0% correct across 4 distinct clause clusters
    evals_a = [
        _make_eval(f"s{i}", f"clause_{i % 4}", True)
        for i in range(12)
    ]
    evals_b = [
        _make_eval(f"s{i}", f"clause_{i % 4}", False)
        for i in range(12)
    ]

    metric_fn = lambda evs: sum(1 for e in evs if e.is_outcome_correct) / len(evs)
    paired_res = paired_cluster_bootstrap_test(
        evaluations_a=evals_a,
        evaluations_b=evals_b,
        metric_fn=metric_fn,
        system_a_name="System P",
        system_b_name="Baseline B1",
        cluster_key="clause_id",
        n_bootstraps=500,
        random_seed=42,
    )

    assert paired_res.difference == 1.0
    assert paired_res.ci_lower > 0.0
    assert paired_res.ci_upper > 0.0
    assert paired_res.p_value < 0.05
    assert paired_res.is_significant is True


def test_stat_004_paired_cluster_bootstrap_null_identical():
    """Paired cluster bootstrap returns zero delta and p=1.0 for identical systems."""
    evals = [
        _make_eval("s1", "c1", True),
        _make_eval("s2", "c1", False),
        _make_eval("s3", "c2", True),
        _make_eval("s4", "c2", True),
    ]

    metric_fn = lambda evs: sum(1 for e in evs if e.is_outcome_correct) / len(evs)
    paired_res = paired_cluster_bootstrap_test(
        evaluations_a=evals,
        evaluations_b=evals,
        metric_fn=metric_fn,
        system_a_name="System P",
        system_b_name="System P Copy",
        cluster_key="clause_id",
        n_bootstraps=200,
        random_seed=42,
    )

    assert paired_res.difference == 0.0
    assert paired_res.is_significant is False


def test_stat_005_contingency_table_counts():
    """compute_contingency_table computes correct concordant and discordant counts."""
    evals_a = [
        _make_eval("s1", "c1", True),   # Both True (n_11)
        _make_eval("s2", "c1", True),   # A True, B False (n_10)
        _make_eval("s3", "c2", False),  # A False, B True (n_01)
        _make_eval("s4", "c2", False),  # Both False (n_00)
    ]
    evals_b = [
        _make_eval("s1", "c1", True),
        _make_eval("s2", "c1", False),
        _make_eval("s3", "c2", True),
        _make_eval("s4", "c2", False),
    ]

    table = compute_contingency_table(evals_a, evals_b)
    assert table["n_11"] == 1
    assert table["n_10"] == 1
    assert table["n_01"] == 1
    assert table["n_00"] == 1

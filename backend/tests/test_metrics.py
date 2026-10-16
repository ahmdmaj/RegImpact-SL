"""Unit tests for the evaluation metrics engine (Section 10.2).

Validates:
  METR-001  compute_classification_metrics computes exact accuracy, per-class P/R/F1, and macro-F1.
  METR-002  compute_abstention_metrics evaluates CONDITIONAL_MISSING_DATA precision, recall, and F1.
  METR-003  compute_abstention_metrics computes exact missing-field set matching and Jaccard similarity.
  METR-004  compute_consistency_metrics evaluates minimal-pair flip sensitivity (C_sens).
  METR-005  compute_consistency_metrics evaluates invariance robustness (C_inv).
  METR-006  compute_subset_accuracies calculates temporal and coverage gap accuracies.
  METR-007  compute_all_metrics returns complete consolidated dictionary with zero errors.
"""

from __future__ import annotations

import pytest

from backend.src.evaluation.metrics import (
    compute_abstention_metrics,
    compute_all_metrics,
    compute_classification_metrics,
    compute_consistency_metrics,
    compute_subset_accuracies,
)
from backend.src.models.domain import OutcomeStatus, ScenarioEvaluation


def _make_eval(
    scenario_id: str,
    clause_id: str,
    scenario_type: str,
    pred: OutcomeStatus,
    gold: OutcomeStatus,
    pair_id: str | None = None,
    pred_missing: list[str] | None = None,
    gold_missing: list[str] | None = None,
) -> ScenarioEvaluation:
    """Helper to construct ScenarioEvaluation instances."""
    is_corr = (pred == gold)
    missing_corr = True
    if gold == OutcomeStatus.CONDITIONAL_MISSING_DATA:
        missing_corr = set(pred_missing or []) == set(gold_missing or [])

    return ScenarioEvaluation(
        scenario_id=scenario_id,
        clause_id=clause_id,
        scenario_type=scenario_type,
        predicted_outcome=pred,
        gold_outcome=gold,
        is_outcome_correct=is_corr,
        predicted_missing_fields=pred_missing or [],
        gold_missing_fields=gold_missing,
        missing_fields_correct=missing_corr,
        pair_id=pair_id,
    )


def test_metr_001_classification_metrics_exact():
    """Classification metrics calculate accuracy, per-class P/R/F1, and macro-F1 correctly."""
    evals = [
        _make_eval("s1", "c1", "direct", OutcomeStatus.APPLICABLE, OutcomeStatus.APPLICABLE),
        _make_eval("s2", "c1", "direct", OutcomeStatus.NOT_APPLICABLE, OutcomeStatus.NOT_APPLICABLE),
        _make_eval("s3", "c2", "direct", OutcomeStatus.APPLICABLE, OutcomeStatus.NOT_APPLICABLE),  # FP
        _make_eval("s4", "c2", "direct", OutcomeStatus.NOT_APPLICABLE, OutcomeStatus.APPLICABLE),  # FN
    ]
    acc, macro_f1, per_class = compute_classification_metrics(evals)

    assert acc == 0.5
    # APPLICABLE: TP=1, FP=1, FN=1 -> Prec=0.5, Rec=0.5, F1=0.5
    assert per_class["APPLICABLE"]["precision"] == 0.5
    assert per_class["APPLICABLE"]["recall"] == 0.5
    assert per_class["APPLICABLE"]["f1"] == 0.5

    # NOT_APPLICABLE: TP=1, FP=1, FN=1 -> Prec=0.5, Rec=0.5, F1=0.5
    assert per_class["NOT_APPLICABLE"]["precision"] == 0.5
    assert per_class["NOT_APPLICABLE"]["recall"] == 0.5
    assert per_class["NOT_APPLICABLE"]["f1"] == 0.5

    assert macro_f1 == 0.5


def test_metr_002_abstention_metrics():
    """Abstention metrics evaluate precision, recall, and F1 on CONDITIONAL_MISSING_DATA."""
    evals = [
        # TP for abstention
        _make_eval("s1", "c1", "incomplete", OutcomeStatus.CONDITIONAL_MISSING_DATA, OutcomeStatus.CONDITIONAL_MISSING_DATA),
        # FP for abstention (abstained when should have been APPLICABLE)
        _make_eval("s2", "c1", "direct", OutcomeStatus.CONDITIONAL_MISSING_DATA, OutcomeStatus.APPLICABLE),
        # FN for abstention (predicted APPLICABLE when should have abstained)
        _make_eval("s3", "c2", "incomplete", OutcomeStatus.APPLICABLE, OutcomeStatus.CONDITIONAL_MISSING_DATA),
        # TN
        _make_eval("s4", "c2", "direct", OutcomeStatus.NOT_APPLICABLE, OutcomeStatus.NOT_APPLICABLE),
    ]
    abs_metrics = compute_abstention_metrics(evals)

    # TP=1, FP=1, FN=1 -> Prec=0.5, Rec=0.5, F1=0.5
    assert abs_metrics["abstention_precision"] == 0.5
    assert abs_metrics["abstention_recall"] == 0.5
    assert abs_metrics["abstention_f1"] == 0.5


def test_metr_003_missing_fields_set_matching():
    """Missing field accuracy evaluates exact set equality and Jaccard similarity."""
    evals = [
        # Exact match
        _make_eval(
            "s1", "c1", "incomplete",
            OutcomeStatus.CONDITIONAL_MISSING_DATA, OutcomeStatus.CONDITIONAL_MISSING_DATA,
            pred_missing=["field_a", "field_b"], gold_missing=["field_b", "field_a"],
        ),
        # Partial match (Jaccard = 1/2 = 0.5, Exact = 0)
        _make_eval(
            "s2", "c1", "incomplete",
            OutcomeStatus.CONDITIONAL_MISSING_DATA, OutcomeStatus.CONDITIONAL_MISSING_DATA,
            pred_missing=["field_a"], gold_missing=["field_a", "field_c"],
        ),
    ]
    abs_metrics = compute_abstention_metrics(evals)

    assert abs_metrics["missing_fields_accuracy"] == 0.5  # 1 out of 2 exact
    assert abs_metrics["missing_fields_jaccard"] == 0.75  # (1.0 + 0.5) / 2 = 0.75


def test_metr_004_minimal_pair_consistency_score():
    """Minimal-pair sensitivity flip consistency (C_sens) evaluates threshold flips."""
    evals = [
        # Consistent pair 1: both correct and flipped
        _make_eval("p1a", "c1", "minimal_pair", OutcomeStatus.APPLICABLE, OutcomeStatus.APPLICABLE, pair_id="PAIR-01"),
        _make_eval("p1b", "c1", "minimal_pair", OutcomeStatus.NOT_APPLICABLE, OutcomeStatus.NOT_APPLICABLE, pair_id="PAIR-01"),
        # Inconsistent pair 2: model did not flip (predicted APPLICABLE on both)
        _make_eval("p2a", "c2", "minimal_pair", OutcomeStatus.APPLICABLE, OutcomeStatus.APPLICABLE, pair_id="PAIR-02"),
        _make_eval("p2b", "c2", "minimal_pair", OutcomeStatus.APPLICABLE, OutcomeStatus.NOT_APPLICABLE, pair_id="PAIR-02"),
    ]
    c_res = compute_consistency_metrics(evals)

    assert c_res["sens_pair_count"] == 2
    assert c_res["c_sens"] == 0.5  # 1 consistent out of 2 pairs


def test_metr_005_invariance_consistency_score():
    """Invariance robustness consistency (C_inv) evaluates identical outcomes under noise."""
    evals = [
        # Invariant pair 1: identical predictions
        _make_eval("inv1a", "c1", "invariance", OutcomeStatus.APPLICABLE, OutcomeStatus.APPLICABLE, pair_id="INV-01"),
        _make_eval("inv1b", "c1", "invariance", OutcomeStatus.APPLICABLE, OutcomeStatus.APPLICABLE, pair_id="INV-01"),
        # Broken invariance pair 2: predictions differ
        _make_eval("inv2a", "c2", "invariance", OutcomeStatus.APPLICABLE, OutcomeStatus.APPLICABLE, pair_id="INV-02"),
        _make_eval("inv2b", "c2", "invariance", OutcomeStatus.NOT_APPLICABLE, OutcomeStatus.APPLICABLE, pair_id="INV-02"),
    ]
    c_res = compute_consistency_metrics(evals)

    assert c_res["inv_pair_count"] == 2
    assert c_res["c_inv"] == 0.5  # 1 invariant out of 2 pairs


def test_metr_006_temporal_and_gap_accuracies():
    """Subset accuracies calculate correct fractions for temporal and coverage gap cases."""
    evals = [
        _make_eval("t1", "c1", "temporal", OutcomeStatus.NOT_APPLICABLE, OutcomeStatus.NOT_APPLICABLE),
        _make_eval("t2", "c1", "temporal", OutcomeStatus.APPLICABLE, OutcomeStatus.APPLICABLE),
        _make_eval("g1", "c2", "direct", OutcomeStatus.UNSUPPORTED, OutcomeStatus.UNSUPPORTED),
        _make_eval("d1", "c3", "direct", OutcomeStatus.APPLICABLE, OutcomeStatus.NOT_APPLICABLE),
    ]
    subsets = compute_subset_accuracies(evals)

    assert subsets["temporal_accuracy"] == 1.0
    assert subsets["coverage_gap_accuracy"] == 1.0
    assert subsets["direct_accuracy"] == 0.5  # g1 is correct, d1 is wrong


def test_metr_007_compute_all_metrics_full():
    """compute_all_metrics consolidates all metrics into a unified dictionary."""
    evals = [
        _make_eval("s1", "c1", "direct", OutcomeStatus.APPLICABLE, OutcomeStatus.APPLICABLE),
    ]
    res = compute_all_metrics(evals)

    assert "accuracy" in res
    assert "macro_f1" in res
    assert "abstention_f1" in res
    assert "c_sens" in res
    assert "temporal_accuracy" in res
    assert res["total_scenarios"] == 1

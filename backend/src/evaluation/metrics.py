"""Component: Evaluation Metrics Engine.

Implements all metrics defined in Section 10.2 and Section 6 of the alignment plan:
  1. Applicability: Accuracy, Per-Class Precision/Recall/F1, and Macro-F1.
  2. Incomplete-Profile Abstention: Precision, Recall, F1, and exact Missing-Field Accuracy.
  3. Consistency:
     - Minimal-Pair Sensitivity Flip Accuracy (C_sens)
     - Invariance Robustness Accuracy (C_inv)
     - Overall Pair Consistency (C_comb)
  4. Temporal Accuracy (A_temp) on commencement boundary transitions.
  5. Coverage Gap Accuracy (A_gap) on uncompiled/unsupported provisions.
"""

from __future__ import annotations

import collections
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.src.models.domain import (
    BenchmarkScenario,
    EvaluationResult,
    OutcomeStatus,
    ScenarioEvaluation,
)


def compute_classification_metrics(
    evaluations: List[ScenarioEvaluation],
) -> Tuple[float, float, Dict[str, Dict[str, float]]]:
    """Compute overall accuracy, macro-F1, and per-class precision/recall/F1.

    Returns:
        (accuracy, macro_f1, per_class_metrics)
    """
    if not evaluations:
        return 0.0, 0.0, {}

    total = len(evaluations)
    correct = sum(1 for e in evaluations if e.is_outcome_correct)
    accuracy = correct / total

    classes: Set[str] = {
        e.gold_outcome.value for e in evaluations
    } | {e.predicted_outcome.value for e in evaluations}

    per_class: Dict[str, Dict[str, float]] = {}
    f1_list: List[float] = []

    for c in sorted(classes):
        tp = sum(1 for e in evaluations if e.predicted_outcome.value == c and e.gold_outcome.value == c)
        fp = sum(1 for e in evaluations if e.predicted_outcome.value == c and e.gold_outcome.value != c)
        fn = sum(1 for e in evaluations if e.predicted_outcome.value != c and e.gold_outcome.value == c)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        support = tp + fn
        per_class[c] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": support,
        }
        if support > 0:
            f1_list.append(f1)

    macro_f1 = sum(f1_list) / len(f1_list) if f1_list else 0.0
    return round(accuracy, 4), round(macro_f1, 4), per_class


def compute_abstention_metrics(
    evaluations: List[ScenarioEvaluation],
) -> Dict[str, float]:
    """Compute precision, recall, F1, and missing field matching on CONDITIONAL_MISSING_DATA.

    Returns:
        Dict with 'precision', 'recall', 'f1', 'missing_fields_accuracy', 'missing_fields_jaccard'.
    """
    abstain_status = OutcomeStatus.CONDITIONAL_MISSING_DATA

    tp = sum(1 for e in evaluations if e.predicted_outcome == abstain_status and e.gold_outcome == abstain_status)
    fp = sum(1 for e in evaluations if e.predicted_outcome == abstain_status and e.gold_outcome != abstain_status)
    fn = sum(1 for e in evaluations if e.predicted_outcome != abstain_status and e.gold_outcome == abstain_status)

    prec = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if fn == 0 else 0.0)
    rec = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if fp == 0 else 0.0)
    f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

    # Missing field identification accuracy on gold abstention cases
    gold_abstentions = [e for e in evaluations if e.gold_outcome == abstain_status]
    if gold_abstentions:
        exact_matches = sum(1 for e in gold_abstentions if e.missing_fields_correct)
        missing_acc = exact_matches / len(gold_abstentions)

        # Average Jaccard similarity across predicted and gold fields
        jaccard_scores: List[float] = []
        for e in gold_abstentions:
            pred_set = set(e.predicted_missing_fields or [])
            gold_set = set(e.gold_missing_fields or [])
            union = pred_set.union(gold_set)
            inter = pred_set.intersection(gold_set)
            jaccard_scores.append(len(inter) / len(union) if union else 1.0)
        jaccard_avg = sum(jaccard_scores) / len(jaccard_scores)
    else:
        missing_acc = 1.0
        jaccard_avg = 1.0

    return {
        "abstention_precision": round(prec, 4),
        "abstention_recall": round(rec, 4),
        "abstention_f1": round(f1, 4),
        "missing_fields_accuracy": round(missing_acc, 4),
        "missing_fields_jaccard": round(jaccard_avg, 4),
    }


def compute_consistency_metrics(
    evaluations: List[ScenarioEvaluation],
) -> Dict[str, Optional[float]]:
    """Compute minimal-pair flip sensitivity (C_sens), invariance stability (C_inv), and C_comb.

    - C_sens: For pairs where gold outcome changes across borderline thresholds,
              the system is consistent if both predictions are correct or flip identically.
    - C_inv:  For pairs where gold outcome is invariant across irrelevant attributes,
              the system is invariant if predictions on both members are identical.
    - C_comb: Overall average consistency across all valid pairs.
    """
    pair_map: Dict[str, List[ScenarioEvaluation]] = collections.defaultdict(list)
    for ev in evaluations:
        if ev.pair_id:
            pair_map[ev.pair_id].append(ev)

    sens_pairs = 0
    sens_consistent = 0

    inv_pairs = 0
    inv_consistent = 0

    for pair_id, pair_evals in pair_map.items():
        if len(pair_evals) != 2:
            continue

        e1, e2 = pair_evals[0], pair_evals[1]

        # Case A: Minimal Pair (Sensitivity Flip)
        if e1.scenario_type == "minimal_pair" or (e1.gold_outcome != e2.gold_outcome):
            sens_pairs += 1
            if e1.is_outcome_correct and e2.is_outcome_correct:
                sens_consistent += 1
            elif (e1.gold_outcome != e2.gold_outcome) and (e1.predicted_outcome != e2.predicted_outcome):
                sens_consistent += 1

        # Case B: Invariance Pair (Stability)
        elif e1.scenario_type == "invariance" or (e1.gold_outcome == e2.gold_outcome):
            inv_pairs += 1
            if e1.predicted_outcome == e2.predicted_outcome:
                inv_consistent += 1

    c_sens = (sens_consistent / sens_pairs) if sens_pairs > 0 else None
    c_inv = (inv_consistent / inv_pairs) if inv_pairs > 0 else None

    total_pairs = sens_pairs + inv_pairs
    c_comb = ((sens_consistent + inv_consistent) / total_pairs) if total_pairs > 0 else None

    return {
        "c_sens": round(c_sens, 4) if c_sens is not None else None,
        "c_inv": round(c_inv, 4) if c_inv is not None else None,
        "c_comb": round(c_comb, 4) if c_comb is not None else None,
        "sens_pair_count": sens_pairs,
        "inv_pair_count": inv_pairs,
    }


def compute_subset_accuracies(
    evaluations: List[ScenarioEvaluation],
) -> Dict[str, Optional[float]]:
    """Compute subset accuracies for temporal transitions and coverage gap scenarios."""
    temporal_evals = [e for e in evaluations if e.scenario_type == "temporal"]
    temporal_acc = (
        sum(1 for e in temporal_evals if e.is_outcome_correct) / len(temporal_evals)
        if temporal_evals
        else None
    )

    gap_evals = [e for e in evaluations if e.gold_outcome == OutcomeStatus.UNSUPPORTED]
    gap_acc = (
        sum(1 for e in gap_evals if e.is_outcome_correct) / len(gap_evals)
        if gap_evals
        else None
    )

    direct_evals = [e for e in evaluations if e.scenario_type == "direct"]
    direct_acc = (
        sum(1 for e in direct_evals if e.is_outcome_correct) / len(direct_evals)
        if direct_evals
        else None
    )

    return {
        "temporal_accuracy": round(temporal_acc, 4) if temporal_acc is not None else None,
        "coverage_gap_accuracy": round(gap_acc, 4) if gap_acc is not None else None,
        "direct_accuracy": round(direct_acc, 4) if direct_acc is not None else None,
    }


def compute_all_metrics(
    evaluations: List[ScenarioEvaluation],
) -> Dict[str, Any]:
    """Compute the unified composite metrics dictionary across all evaluation dimensions."""
    accuracy, macro_f1, per_class = compute_classification_metrics(evaluations)
    abstention = compute_abstention_metrics(evaluations)
    consistency = compute_consistency_metrics(evaluations)
    subsets = compute_subset_accuracies(evaluations)

    return {
        "total_scenarios": len(evaluations),
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "per_class": per_class,
        **abstention,
        **consistency,
        **subsets,
    }

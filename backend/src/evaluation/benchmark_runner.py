"""Component [O6 / Section 8.8]: The Benchmark and Evaluation Harness.

Executes benchmark scenarios across BaselineSystem implementations and calculates
evaluation metrics defined in Section 10.2:
- Applicability Accuracy & Macro-F1
- Incomplete-Profile Abstention Precision, Recall, & F1
- Missing-Field Identification Accuracy
- Minimal-Pair Consistency (Flip Accuracy)
- Temporal Scenario Accuracy
"""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.src.evaluation.baselines import BaselineSystem
from backend.src.models.domain import (
    BenchmarkScenario,
    EvaluationReport,
    EvaluationResult,
    OutcomeStatus,
    ScenarioEvaluation,
)


class BenchmarkRunner:
    """Benchmark evaluation runner executing scenarios and calculating metrics."""

    def __init__(self, scenarios: Optional[List[BenchmarkScenario]] = None):
        self.scenarios = scenarios or []

    def run(
        self,
        system: BaselineSystem,
        scenarios: Optional[List[BenchmarkScenario]] = None,
        dataset_version: Optional[str] = None,
        dataset_path: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
    ) -> EvaluationReport:
        """Run benchmark evaluation for a given system against scenarios."""
        target_scenarios = scenarios if scenarios is not None else self.scenarios
        run_timestamp = datetime.now(timezone.utc).isoformat()

        # Compute dataset SHA-256 hash if path provided
        dataset_hash = None
        if dataset_path:
            p = Path(dataset_path)
            if p.exists():
                import hashlib
                dataset_hash = hashlib.sha256(p.read_bytes()).hexdigest()

        if not target_scenarios:
            return EvaluationReport(
                system_name=system.name,
                total_scenarios=0,
                accuracy=0.0,
                macro_f1=0.0,
                abstention_precision=0.0,
                abstention_recall=0.0,
                abstention_f1=0.0,
                missing_fields_accuracy=0.0,
                scenario_evaluations=[],
                dataset_version=dataset_version,
                dataset_path=str(dataset_path) if dataset_path else None,
                dataset_hash=dataset_hash,
                configuration=configuration or {},
                timestamp=run_timestamp,
                errors=[],
            )

        scenario_evaluations: List[ScenarioEvaluation] = []
        predictions: List[Tuple[BenchmarkScenario, EvaluationResult]] = []
        errors: List[str] = []

        # 1. Execute all scenarios through the system
        for scen in target_scenarios:
            try:
                result = system.evaluate_scenario(scen)
            except Exception as e:
                err_msg = f"Error evaluating scenario {scen.scenario_id}: {e}"
                errors.append(err_msg)
                result = EvaluationResult(
                    status=OutcomeStatus.UNSUPPORTED,
                    rule_id=scen.clause_id,
                    missing_fields=[],
                    evaluation_trace=[],
                    reason=err_msg,
                )

            predictions.append((scen, result))

            is_correct = result.status == scen.gold_outcome

            # Check missing fields correctness
            gold_missing = set(scen.gold_missing_fields or [])
            pred_missing = set(result.missing_fields or [])
            missing_correct = True
            if scen.gold_outcome == OutcomeStatus.CONDITIONAL_MISSING_DATA:
                missing_correct = (gold_missing == pred_missing)

            # Check temporal status correctness
            pred_temp = getattr(result, "temporal_status", None)
            gold_temp = getattr(scen, "gold_temporal_status", None) or (
                scen.model_extra.get("gold_temporal_status") if scen.model_extra else None
            )
            temp_correct = True
            if gold_temp is not None:
                temp_correct = (pred_temp == gold_temp)

            extra_meta = scen.model_extra or {}
            target_rules = getattr(scen, "target_rule_ids", None) or extra_meta.get("target_rule_ids")

            scenario_evaluations.append(
                ScenarioEvaluation(
                    scenario_id=scen.scenario_id,
                    clause_id=scen.clause_id,
                    scenario_type=scen.scenario_type,
                    predicted_outcome=result.status,
                    gold_outcome=scen.gold_outcome,
                    is_outcome_correct=is_correct,
                    predicted_missing_fields=result.missing_fields,
                    gold_missing_fields=scen.gold_missing_fields,
                    missing_fields_correct=missing_correct,
                    pair_id=scen.pair_id,
                    evaluation_trace=getattr(result, "evaluation_trace", []),
                    reason=result.reason,
                    target_rule_ids=target_rules,
                    predicted_temporal_status=pred_temp,
                    gold_temporal_status=gold_temp,
                    temporal_status_correct=temp_correct,
                )
            )

        # 2. Compute Applicability Accuracy
        correct_count = sum(1 for s in scenario_evaluations if s.is_outcome_correct)
        accuracy = correct_count / len(scenario_evaluations)

        # 3. Compute Per-Class Precision, Recall, F1 and Macro-F1
        per_class_metrics, macro_f1 = self._compute_classification_metrics(
            scenario_evaluations
        )

        # 4. Compute Abstention Metrics (Section 8.3 [G] & RQ3 on CONDITIONAL_MISSING_DATA)
        abs_prec, abs_rec, abs_f1, missing_acc = self._compute_abstention_metrics(
            scenario_evaluations
        )

        # 5. Compute Minimal-Pair Consistency Score (RQ2 / Section 10.2)
        consistency_score = self._compute_consistency_score(
            scenario_evaluations, target_scenarios
        )

        # 6. Compute Temporal Scenario Accuracy (validates both outcome and temporal_status)
        temporal_evals = [s for s in scenario_evaluations if s.scenario_type == "temporal"]
        temporal_acc = (
            sum(1 for s in temporal_evals if s.is_outcome_correct and s.temporal_status_correct) / len(temporal_evals)
            if temporal_evals
            else None
        )

        return EvaluationReport(
            system_name=system.name,
            total_scenarios=len(scenario_evaluations),
            accuracy=round(accuracy, 4),
            macro_f1=round(macro_f1, 4),
            per_class_metrics=per_class_metrics,
            abstention_precision=round(abs_prec, 4),
            abstention_recall=round(abs_rec, 4),
            abstention_f1=round(abs_f1, 4),
            missing_fields_accuracy=round(missing_acc, 4),
            consistency_score=round(consistency_score, 4) if consistency_score is not None else None,
            temporal_accuracy=round(temporal_acc, 4) if temporal_acc is not None else None,
            scenario_evaluations=scenario_evaluations,
            dataset_version=dataset_version,
            dataset_path=str(dataset_path) if dataset_path else None,
            dataset_hash=dataset_hash,
            configuration=configuration or {},
            timestamp=run_timestamp,
            errors=errors,
        )

    def _compute_classification_metrics(
        self,
        evaluations: List[ScenarioEvaluation],
    ) -> Tuple[Dict[str, Dict[str, float]], float]:
        """Compute precision, recall, and F1 for all outcome classes."""
        classes: Set[str] = {
            s.gold_outcome.value for s in evaluations
        } | {s.predicted_outcome.value for s in evaluations}

        metrics: Dict[str, Dict[str, float]] = {}
        f1_scores: List[float] = []

        for c in classes:
            tp = sum(
                1
                for s in evaluations
                if s.predicted_outcome.value == c and s.gold_outcome.value == c
            )
            fp = sum(
                1
                for s in evaluations
                if s.predicted_outcome.value == c and s.gold_outcome.value != c
            )
            fn = sum(
                1
                for s in evaluations
                if s.predicted_outcome.value != c and s.gold_outcome.value == c
            )

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (
                (2 * precision * recall) / (precision + recall)
                if (precision + recall) > 0
                else 0.0
            )

            metrics[c] = {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "support": tp + fn,
            }
            # Only average over classes that actually appear in ground truth
            if (tp + fn) > 0:
                f1_scores.append(f1)

        macro_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0
        return metrics, macro_f1

    def _compute_abstention_metrics(
        self,
        evaluations: List[ScenarioEvaluation],
    ) -> Tuple[float, float, float, float]:
        """Compute abstention precision, recall, F1, and missing field accuracy."""
        abstain_val = OutcomeStatus.CONDITIONAL_MISSING_DATA

        tp = sum(
            1
            for s in evaluations
            if s.predicted_outcome == abstain_val and s.gold_outcome == abstain_val
        )
        fp = sum(
            1
            for s in evaluations
            if s.predicted_outcome == abstain_val and s.gold_outcome != abstain_val
        )
        fn = sum(
            1
            for s in evaluations
            if s.predicted_outcome != abstain_val and s.gold_outcome == abstain_val
        )

        prec = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if fn == 0 else 0.0)
        rec = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if fp == 0 else 0.0)
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        # Missing field accuracy evaluated on gold CONDITIONAL_MISSING_DATA cases
        missing_cases = [s for s in evaluations if s.gold_outcome == abstain_val]
        missing_acc = (
            sum(1 for s in missing_cases if s.missing_fields_correct) / len(missing_cases)
            if missing_cases
            else 1.0
        )

        return prec, rec, f1, missing_acc

    def _compute_consistency_score(
        self,
        evaluations: List[ScenarioEvaluation],
        scenarios: List[BenchmarkScenario],
    ) -> Optional[float]:
        """Compute minimal-pair flip consistency score (Section 10.2)."""
        pair_map: Dict[str, List[ScenarioEvaluation]] = defaultdict(list)

        # 1. Group by explicit pair_id
        for ev in evaluations:
            if ev.pair_id:
                pair_map[ev.pair_id].append(ev)

        # 2. If no pair_ids, check minimal_pair scenario_types by grouping consecutive pairs
        if not pair_map:
            min_pairs = [ev for ev in evaluations if ev.scenario_type == "minimal_pair"]
            for i in range(0, len(min_pairs) - 1, 2):
                pair_map[f"auto_pair_{i}"] = [min_pairs[i], min_pairs[i + 1]]

        if not pair_map:
            return None

        consistent_pairs = 0
        total_valid_pairs = 0

        for pair_id, pair_evals in pair_map.items():
            if len(pair_evals) != 2:
                continue

            total_valid_pairs += 1
            e1, e2 = pair_evals[0], pair_evals[1]

            # In minimal pairs, the gold outcomes flip: e1.gold != e2.gold
            # System is consistent if predictions match gold verdicts on both pair instances
            if e1.is_outcome_correct and e2.is_outcome_correct:
                consistent_pairs += 1
            elif (e1.gold_outcome != e2.gold_outcome) and (e1.predicted_outcome != e2.predicted_outcome):
                # Flipped in same direction
                consistent_pairs += 1

        return consistent_pairs / total_valid_pairs if total_valid_pairs > 0 else None


def compare_systems(
    systems: List[BaselineSystem],
    scenarios: List[BenchmarkScenario],
) -> Dict[str, EvaluationReport]:
    """Convenience helper to evaluate multiple systems on the identical benchmark."""
    runner = BenchmarkRunner()
    reports: Dict[str, EvaluationReport] = {}
    for sys in systems:
        reports[sys.name] = runner.run(sys, scenarios)
    return reports


# Re-export loader and validator for convenience
from backend.src.evaluation.benchmark_validator import (  # noqa: E402
    load_benchmark_scenarios,
    validate_benchmark_slice,
)

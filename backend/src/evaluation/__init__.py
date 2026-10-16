"""Evaluation and baseline systems package for RegImpact-SL."""

from backend.src.evaluation.baselines import (
    BASELINE_EVALUATION_SCHEMA,
    BM25Baseline,
    BaselineSystem,
    DenseBaseline,
    HybridBaseline,
    OracleBaseline,
    SystemP,
    construct_baseline_prompt,
)
from backend.src.evaluation.benchmark_runner import (
    BenchmarkRunner,
    compare_systems,
)
from backend.src.evaluation.dataset_split import split_scenarios_by_clause
from backend.src.models.domain import (
    BenchmarkScenario,
    EvaluationReport,
    ScenarioEvaluation,
)

__all__ = [
    "BaselineSystem",
    "SystemP",
    "OracleBaseline",
    "BM25Baseline",
    "DenseBaseline",
    "HybridBaseline",
    "BenchmarkRunner",
    "compare_systems",
    "split_scenarios_by_clause",
    "BenchmarkScenario",
    "EvaluationReport",
    "ScenarioEvaluation",
    "construct_baseline_prompt",
    "BASELINE_EVALUATION_SCHEMA",
]

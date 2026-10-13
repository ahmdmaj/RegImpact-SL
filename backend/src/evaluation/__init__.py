"""Evaluation and baseline systems package for RegImpact-SL."""

from backend.src.evaluation.baselines import (
    BM25Baseline,
    BaselineSystem,
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
    "BenchmarkScenario",
    "EvaluationReport",
    "ScenarioEvaluation",
]

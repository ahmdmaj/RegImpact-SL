"""Evaluation and baseline systems package for RegImpact-SL."""

from backend.src.evaluation.baselines import (
    BASELINE_EVALUATION_SCHEMA,
    AblationPNoAbstention,
    AblationPNoTemporal,
    AblationPNoVerification,
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
from backend.src.evaluation.metrics import (
    compute_abstention_metrics,
    compute_all_metrics,
    compute_classification_metrics,
    compute_consistency_metrics,
    compute_subset_accuracies,
)
from backend.src.evaluation.statistics import (
    BootstrapResult,
    CohensKappaResult,
    PairedBootstrapResult,
    cluster_bootstrap_metric,
    compute_cohens_kappa,
    compute_contingency_table,
    paired_cluster_bootstrap_test,
)
from backend.src.models.domain import (
    BenchmarkScenario,
    EvaluationReport,
    ScenarioEvaluation,
)

__all__ = [
    "BaselineSystem",
    "SystemP",
    "AblationPNoVerification",
    "AblationPNoTemporal",
    "AblationPNoAbstention",
    "OracleBaseline",
    "BM25Baseline",
    "DenseBaseline",
    "HybridBaseline",
    "BenchmarkRunner",
    "compare_systems",
    "split_scenarios_by_clause",
    "compute_all_metrics",
    "compute_classification_metrics",
    "compute_abstention_metrics",
    "compute_consistency_metrics",
    "compute_subset_accuracies",
    "cluster_bootstrap_metric",
    "paired_cluster_bootstrap_test",
    "compute_contingency_table",
    "compute_cohens_kappa",
    "BootstrapResult",
    "CohensKappaResult",
    "PairedBootstrapResult",
    "BenchmarkScenario",
    "EvaluationReport",
    "ScenarioEvaluation",
    "construct_baseline_prompt",
    "BASELINE_EVALUATION_SCHEMA",
]

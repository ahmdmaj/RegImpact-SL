"""Component: Clustered Statistical Testing & Bootstrap Inference.

Implements clause-level cluster bootstrap algorithm and paired comparative testing:
  1. Clause-level Cluster Bootstrap: Accounts for intra-cluster correlation across
     scenarios sharing the same statutory provision (clause_id). Standard i.i.d.
     bootstrapping artificially deflates standard errors and inflates confidence.
  2. Paired Cluster Bootstrap Difference Test: Computes confidence intervals on the
     performance delta between System P and baselines (B0-B3, ablations) with empirical
     two-tailed p-values.
  3. Clustered McNemar / Contingency Analysis: Analyzes discordant prediction pairs.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass
import math
import random
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from backend.src.models.domain import ScenarioEvaluation


@dataclass
class BootstrapResult:
    """Summary of a cluster bootstrap confidence interval."""
    point_estimate: float
    ci_lower: float
    ci_upper: float
    std_err: float
    ci_level: float
    n_bootstraps: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "point_estimate": round(self.point_estimate, 4),
            "ci_lower": round(self.ci_lower, 4),
            "ci_upper": round(self.ci_upper, 4),
            "std_err": round(self.std_err, 4),
            "ci_level": self.ci_level,
            "n_bootstraps": self.n_bootstraps,
        }

    def format_ci(self) -> str:
        """Format as: 0.8500 [0.7200, 0.9500]."""
        return f"{self.point_estimate:.4f} [{self.ci_lower:.4f}, {self.ci_upper:.4f}]"


@dataclass
class PairedBootstrapResult:
    """Summary of a paired comparative cluster bootstrap test."""
    system_a: str
    system_b: str
    metric_a: float
    metric_b: float
    difference: float
    ci_lower: float
    ci_upper: float
    p_value: float
    ci_level: float
    is_significant: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_a": self.system_a,
            "system_b": self.system_b,
            "metric_a": round(self.metric_a, 4),
            "metric_b": round(self.metric_b, 4),
            "difference": round(self.difference, 4),
            "ci_lower": round(self.ci_lower, 4),
            "ci_upper": round(self.ci_upper, 4),
            "p_value": round(self.p_value, 4),
            "is_significant": self.is_significant,
        }

    def format_diff_ci(self) -> str:
        sig_marker = "**" if self.p_value < 0.01 else ("*" if self.p_value < 0.05 else "")
        return f"{self.difference:+.4f} [{self.ci_lower:+.4f}, {self.ci_upper:+.4f}]{sig_marker} (p={self.p_value:.4f})"


def cluster_bootstrap_metric(
    evaluations: List[ScenarioEvaluation],
    metric_fn: Callable[[List[ScenarioEvaluation]], float],
    cluster_key: str = "clause_id",
    n_bootstraps: int = 1000,
    ci_level: float = 0.95,
    random_seed: int = 42,
) -> BootstrapResult:
    """Compute cluster bootstrap confidence intervals by resampling clusters with replacement.

    Args:
        evaluations: List of ScenarioEvaluation objects.
        metric_fn: Callable that accepts a list of ScenarioEvaluation and returns a float metric.
        cluster_key: Attribute name on ScenarioEvaluation to group by (default "clause_id").
        n_bootstraps: Number of bootstrap replications (default 1000).
        ci_level: Confidence level (default 0.95).
        random_seed: Random seed for reproducibility.

    Returns:
        BootstrapResult with point estimate, empirical percentile CI, and standard error.
    """
    if not evaluations:
        return BootstrapResult(0.0, 0.0, 0.0, 0.0, ci_level, n_bootstraps)

    # 1. Point estimate on original dataset
    point_estimate = float(metric_fn(evaluations))

    # 2. Group evaluations by cluster_key
    clusters: Dict[str, List[ScenarioEvaluation]] = collections.defaultdict(list)
    for ev in evaluations:
        val = getattr(ev, cluster_key, None) or "unknown_cluster"
        clusters[str(val)].append(ev)

    cluster_keys = sorted(clusters.keys())
    k_clusters = len(cluster_keys)

    if k_clusters <= 1:
        # Fall back to single cluster (cannot resample clusters)
        return BootstrapResult(point_estimate, point_estimate, point_estimate, 0.0, ci_level, n_bootstraps)

    # 3. Resample clusters with replacement
    rng = random.Random(random_seed)
    boot_values: List[float] = []

    for _ in range(n_bootstraps):
        sampled_keys = [cluster_keys[rng.randint(0, k_clusters - 1)] for _ in range(k_clusters)]
        boot_sample: List[ScenarioEvaluation] = []
        for ck in sampled_keys:
            boot_sample.extend(clusters[ck])

        boot_val = float(metric_fn(boot_sample))
        boot_values.append(boot_val)

    # 4. Compute empirical percentiles and standard error
    boot_values.sort()
    alpha = (1.0 - ci_level) / 2.0
    lower_idx = int(math.floor(alpha * n_bootstraps))
    upper_idx = int(math.ceil((1.0 - alpha) * n_bootstraps)) - 1
    lower_idx = max(0, min(n_bootstraps - 1, lower_idx))
    upper_idx = max(0, min(n_bootstraps - 1, upper_idx))

    ci_lower = boot_values[lower_idx]
    ci_upper = boot_values[upper_idx]

    mean_boot = sum(boot_values) / n_bootstraps
    variance = sum((x - mean_boot) ** 2 for x in boot_values) / max(1, n_bootstraps - 1)
    std_err = math.sqrt(variance)

    return BootstrapResult(
        point_estimate=point_estimate,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        std_err=std_err,
        ci_level=ci_level,
        n_bootstraps=n_bootstraps,
    )


def paired_cluster_bootstrap_test(
    evaluations_a: List[ScenarioEvaluation],
    evaluations_b: List[ScenarioEvaluation],
    metric_fn: Callable[[List[ScenarioEvaluation]], float],
    system_a_name: str = "System P",
    system_b_name: str = "Baseline",
    cluster_key: str = "clause_id",
    n_bootstraps: int = 1000,
    ci_level: float = 0.95,
    random_seed: int = 42,
) -> PairedBootstrapResult:
    """Run paired cluster bootstrap difference test comparing System A against System B.

    Computes:
      - Point estimates metric_A, metric_B, and difference Delta = metric_A - metric_B.
      - 95% Confidence Interval for Delta under cluster resampling.
      - Empirical two-tailed p-value testing H0: Delta = 0.
    """
    if len(evaluations_a) != len(evaluations_b):
        raise ValueError(
            f"Evaluation lists must have equal length: {len(evaluations_a)} vs {len(evaluations_b)}"
        )

    # Check alignment by scenario_id
    id_map_b = {e.scenario_id: e for e in evaluations_b}
    aligned_a: List[ScenarioEvaluation] = []
    aligned_b: List[ScenarioEvaluation] = []

    for ea in evaluations_a:
        eb = id_map_b.get(ea.scenario_id)
        if eb is not None:
            aligned_a.append(ea)
            aligned_b.append(eb)

    if not aligned_a:
        raise ValueError("Zero overlapping scenario IDs found between the two evaluation sets.")

    # 1. Point estimates
    metric_a = float(metric_fn(aligned_a))
    metric_b = float(metric_fn(aligned_b))
    difference = metric_a - metric_b

    # 2. Group paired records by cluster_key
    paired_clusters: Dict[str, List[Tuple[ScenarioEvaluation, ScenarioEvaluation]]] = collections.defaultdict(list)
    for ea, eb in zip(aligned_a, aligned_b):
        ck = str(getattr(ea, cluster_key, None) or "unknown")
        paired_clusters[ck].append((ea, eb))

    cluster_keys = sorted(paired_clusters.keys())
    k_clusters = len(cluster_keys)

    if k_clusters <= 1:
        return PairedBootstrapResult(
            system_a=system_a_name,
            system_b=system_b_name,
            metric_a=metric_a,
            metric_b=metric_b,
            difference=difference,
            ci_lower=difference,
            ci_upper=difference,
            p_value=1.0,
            ci_level=ci_level,
            is_significant=False,
        )

    # 3. Resample clusters with replacement
    rng = random.Random(random_seed)
    diff_values: List[float] = []

    for _ in range(n_bootstraps):
        sampled_keys = [cluster_keys[rng.randint(0, k_clusters - 1)] for _ in range(k_clusters)]
        sample_a: List[ScenarioEvaluation] = []
        sample_b: List[ScenarioEvaluation] = []
        for ck in sampled_keys:
            for pair_a, pair_b in paired_clusters[ck]:
                sample_a.append(pair_a)
                sample_b.append(pair_b)

        val_a = float(metric_fn(sample_a))
        val_b = float(metric_fn(sample_b))
        diff_values.append(val_a - val_b)

    # 4. Percentiles for difference CI
    diff_values.sort()
    alpha = (1.0 - ci_level) / 2.0
    lower_idx = int(math.floor(alpha * n_bootstraps))
    upper_idx = int(math.ceil((1.0 - alpha) * n_bootstraps)) - 1
    lower_idx = max(0, min(n_bootstraps - 1, lower_idx))
    upper_idx = max(0, min(n_bootstraps - 1, upper_idx))

    ci_lower = diff_values[lower_idx]
    ci_upper = diff_values[upper_idx]

    # 5. Empirical two-tailed p-value
    # Proportion of bootstrap differences on the other side of zero
    if difference >= 0:
        p_val = 2.0 * (sum(1 for d in diff_values if d <= 0) / n_bootstraps)
    else:
        p_val = 2.0 * (sum(1 for d in diff_values if d >= 0) / n_bootstraps)
    p_val = min(1.0, max(0.0, p_val))

    is_significant = (p_val < (1.0 - ci_level)) or (ci_lower > 0 and ci_upper > 0) or (ci_lower < 0 and ci_upper < 0)

    return PairedBootstrapResult(
        system_a=system_a_name,
        system_b=system_b_name,
        metric_a=metric_a,
        metric_b=metric_b,
        difference=difference,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        p_value=p_val,
        ci_level=ci_level,
        is_significant=is_significant,
    )


def compute_contingency_table(
    evaluations_a: List[ScenarioEvaluation],
    evaluations_b: List[ScenarioEvaluation],
) -> Dict[str, int]:
    """Compute 2x2 contingency table of prediction correctness for McNemar analysis.

    Table cells:
      - n_11: Both systems correct
      - n_10: System A correct, System B incorrect
      - n_01: System A incorrect, System B correct
      - n_00: Both systems incorrect
    """
    id_map_b = {e.scenario_id: e for e in evaluations_b}
    n_11 = 0
    n_10 = 0
    n_01 = 0
    n_00 = 0

    for ea in evaluations_a:
        eb = id_map_b.get(ea.scenario_id)
        if eb is None:
            continue
        corr_a = ea.is_outcome_correct
        corr_b = eb.is_outcome_correct

        if corr_a and corr_b:
            n_11 += 1
        elif corr_a and not corr_b:
            n_10 += 1
        elif not corr_a and corr_b:
            n_01 += 1
        else:
            n_00 += 1

    return {"n_11": n_11, "n_10": n_10, "n_01": n_01, "n_00": n_00}


@dataclass
class CohensKappaResult:
    """Summary of Cohen's kappa inter-annotator agreement test."""
    n_items: int
    observed_agreement: float
    expected_agreement: float
    kappa: float
    std_err: float
    ci_lower: float
    ci_upper: float
    interpretation: str
    categories: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_items": self.n_items,
            "observed_agreement": round(self.observed_agreement, 4),
            "expected_agreement": round(self.expected_agreement, 4),
            "kappa": round(self.kappa, 4),
            "std_err": round(self.std_err, 4),
            "ci_lower": round(self.ci_lower, 4),
            "ci_upper": round(self.ci_upper, 4),
            "interpretation": self.interpretation,
            "categories": self.categories,
        }


def compute_cohens_kappa(
    annotations_a: Sequence[str],
    annotations_b: Sequence[str],
    categories: Optional[Sequence[str]] = None,
    ci_level: float = 0.95,
) -> CohensKappaResult:
    """Compute Cohen's kappa coefficient of inter-annotator agreement.

    Formula:
        kappa = (P_o - P_e) / (1.0 - P_e)
    where:
        P_o = Observed proportion of agreement across items.
        P_e = Expected proportion of agreement by chance.
    """
    if len(annotations_a) != len(annotations_b):
        raise ValueError(
            f"Annotation sequences must have identical length: {len(annotations_a)} != {len(annotations_b)}"
        )
    n = len(annotations_a)
    if n == 0:
        return CohensKappaResult(
            n_items=0,
            observed_agreement=0.0,
            expected_agreement=0.0,
            kappa=0.0,
            std_err=0.0,
            ci_lower=0.0,
            ci_upper=0.0,
            interpretation="No data",
            categories=[],
        )

    all_cats = sorted(set(categories or (set(annotations_a) | set(annotations_b))))

    # Observed agreement
    agree_count = sum(1 for a, b in zip(annotations_a, annotations_b) if a == b)
    p_o = agree_count / n

    # Marginals for expected agreement
    counts_a = collections.Counter(annotations_a)
    counts_b = collections.Counter(annotations_b)
    p_e = sum((counts_a[c] / n) * (counts_b[c] / n) for c in all_cats)

    if math.isclose(p_e, 1.0):
        kappa = 1.0 if math.isclose(p_o, 1.0) else 0.0
    else:
        kappa = (p_o - p_e) / (1.0 - p_e)

    # Standard error approximation
    denom = (1.0 - p_e)
    if math.isclose(denom, 0.0) or n <= 1:
        se = 0.0
    else:
        var_kappa = (p_o * (1.0 - p_o)) / (n * (denom ** 2)) if p_o < 1.0 else 0.0
        se = math.sqrt(max(0.0, var_kappa))

    z = 1.96 if math.isclose(ci_level, 0.95) else 1.645
    ci_lower = max(-1.0, kappa - z * se)
    ci_upper = min(1.0, kappa + z * se)

    # Landis & Koch (1977) benchmark scale
    if kappa < 0.0:
        interp = "Poor agreement (less than chance)"
    elif kappa <= 0.20:
        interp = "Slight agreement"
    elif kappa <= 0.40:
        interp = "Fair agreement"
    elif kappa <= 0.60:
        interp = "Moderate agreement"
    elif kappa <= 0.80:
        interp = "Substantial agreement"
    else:
        interp = "Almost perfect agreement"

    return CohensKappaResult(
        n_items=n,
        observed_agreement=p_o,
        expected_agreement=p_e,
        kappa=kappa,
        std_err=se,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        interpretation=interp,
        categories=all_cats,
    )

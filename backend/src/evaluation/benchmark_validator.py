"""Benchmark Slice Loading, Validation, and Provenance Verification.

Enforces dataset integrity, provenance traceability, pair cohesion, and
gold status safety for benchmark slices under Proposal v4.
"""

from __future__ import annotations

import collections
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field

from backend.src.evaluation.dataset_split import split_scenarios_by_clause
from backend.src.models.domain import BenchmarkScenario, OutcomeStatus

# Constants for authoritative Gazette slice
GAZETTE_2494_47_SHA256 = "83ed19c22873471652d0073fe16c977442e42c8ecac2edf1d691d00d78d8a054"
KNOWN_REGULATION_3_RULES = {
    "RULE-FCAU-2494-47-REG-3",
    "RULE-FCAU-2494-47-REG-3-B2B",
}


class ValidationReport(BaseModel):
    """Dataset integrity and provenance audit report for benchmark slices."""

    is_valid: bool
    total_scenarios: int
    provisional_scenarios_count: int
    gold_scenarios_count: int
    scenario_types: Dict[str, int] = Field(default_factory=dict)
    pairs_validated: int = 0
    minimal_pairs_count: int = 0
    invariance_pairs_count: int = 0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


def load_benchmark_scenarios(path: Union[str, Path]) -> List[BenchmarkScenario]:
    """Load and parse benchmark scenarios from a JSONL file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Benchmark file not found: {p}")

    scenarios: List[BenchmarkScenario] = []
    with p.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                scen = BenchmarkScenario.model_validate_json(line_str)
                scenarios.append(scen)
            except Exception as e:
                raise ValueError(f"Failed to parse scenario at line {line_num}: {e}") from e

    return scenarios


def validate_benchmark_slice(
    scenarios: List[BenchmarkScenario],
    known_rules: Optional[Set[str]] = None,
    known_sources: Optional[Set[str]] = None,
    enforce_provisional: bool = True,
) -> ValidationReport:
    """Validate benchmark slice data integrity, provenance, and split safety.

    Args:
        scenarios: List of loaded BenchmarkScenario objects.
        known_rules: Optional set of approved/registered rule IDs to verify against.
        known_sources: Optional set of verified source document hashes.
        enforce_provisional: If True, asserts scenarios are NOT marked gold without expert adjudication.

    Returns:
        ValidationReport detailing audit outcome and any integrity errors.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not scenarios:
        return ValidationReport(
            is_valid=False,
            total_scenarios=0,
            provisional_scenarios_count=0,
            gold_scenarios_count=0,
            errors=["Benchmark scenario list is empty."],
        )

    # 1. Uniqueness of scenario IDs
    seen_ids: Set[str] = set()
    dup_ids: Set[str] = set()
    for s in scenarios:
        if s.scenario_id in seen_ids:
            dup_ids.add(s.scenario_id)
        seen_ids.add(s.scenario_id)

    if dup_ids:
        errors.append(f"Duplicate scenario IDs detected: {sorted(dup_ids)}")

    # 2. Scenario types and outcomes
    valid_types = {"direct", "minimal_pair", "invariance", "temporal", "incomplete"}
    type_counts: Dict[str, int] = collections.defaultdict(int)
    provisional_count = 0
    gold_count = 0

    minimal_pairs: Dict[str, List[BenchmarkScenario]] = collections.defaultdict(list)
    invariance_pairs: Dict[str, List[BenchmarkScenario]] = collections.defaultdict(list)

    for s in scenarios:
        type_counts[s.scenario_type] += 1
        if s.scenario_type not in valid_types:
            errors.append(f"Scenario '{s.scenario_id}' has invalid scenario_type '{s.scenario_type}'.")

        if s.gold_outcome not in list(OutcomeStatus):
            errors.append(f"Scenario '{s.scenario_id}' has invalid gold_outcome '{s.gold_outcome}'.")

        # Incomplete profile checks
        if s.scenario_type == "incomplete":
            if s.gold_outcome != OutcomeStatus.CONDITIONAL_MISSING_DATA:
                errors.append(
                    f"Incomplete scenario '{s.scenario_id}' must have gold_outcome CONDITIONAL_MISSING_DATA, "
                    f"got '{s.gold_outcome}'."
                )
            if not s.gold_missing_fields:
                errors.append(
                    f"Incomplete scenario '{s.scenario_id}' missing required gold_missing_fields list."
                )

        # Pair grouping
        if s.scenario_type == "minimal_pair":
            if not s.pair_id:
                errors.append(f"Minimal pair scenario '{s.scenario_id}' missing pair_id.")
            else:
                minimal_pairs[s.pair_id].append(s)

        if s.scenario_type == "invariance":
            if not s.pair_id:
                errors.append(f"Invariance scenario '{s.scenario_id}' missing pair_id.")
            else:
                invariance_pairs[s.pair_id].append(s)

        # Provenance field audits
        extra = s.model_extra or {}
        is_gold_scen = extra.get("is_gold_scenario", False)
        is_gold_r = extra.get("is_gold_rule", False)
        review_status = extra.get("review_status", "")
        reviewer_role = extra.get("reviewer_role", "")

        if is_gold_scen:
            gold_count += 1
            if enforce_provisional:
                errors.append(
                    f"Scenario '{s.scenario_id}' is marked as gold (is_gold_scenario=True), "
                    "violating milestone provisional freeze."
                )
        else:
            provisional_count += 1

        if is_gold_r and enforce_provisional:
            errors.append(
                f"Scenario '{s.scenario_id}' references an un-adjudicated gold rule (is_gold_rule=True)."
            )

        # Check required provenance fields
        source_hash = extra.get("source_hash")
        if not source_hash:
            errors.append(f"Scenario '{s.scenario_id}' missing required 'source_hash' provenance.")
        elif known_sources and source_hash not in known_sources:
            errors.append(
                f"Scenario '{s.scenario_id}' has unknown source_hash '{source_hash}' not in known sources."
            )

        source_instrument = extra.get("source_instrument")
        if not source_instrument:
            errors.append(f"Scenario '{s.scenario_id}' missing required 'source_instrument' provenance.")

        source_quote = extra.get("source_quote_span")
        if not source_quote:
            warnings.append(f"Scenario '{s.scenario_id}' missing verbatim 'source_quote_span'.")

        target_rules = extra.get("target_rule_ids") or []
        if not target_rules:
            warnings.append(f"Scenario '{s.scenario_id}' does not specify 'target_rule_ids'.")
        elif known_rules:
            for rid in target_rules:
                if rid not in known_rules:
                    errors.append(f"Scenario '{s.scenario_id}' references unknown rule '{rid}'.")

    # 3. Minimal pair consistency (flip verification)
    for pair_id, members in minimal_pairs.items():
        if len(members) != 2:
            errors.append(f"Minimal pair '{pair_id}' must have exactly 2 scenarios, got {len(members)}.")
            continue
        outcomes = {m.gold_outcome for m in members}
        if OutcomeStatus.APPLICABLE not in outcomes or OutcomeStatus.NOT_APPLICABLE not in outcomes:
            errors.append(
                f"Minimal pair '{pair_id}' does not flip outcomes: found {[m.gold_outcome.value for m in members]}."
            )

    # 4. Invariance pair consistency (stability verification)
    for pair_id, members in invariance_pairs.items():
        if len(members) != 2:
            errors.append(f"Invariance pair '{pair_id}' must have exactly 2 scenarios, got {len(members)}.")
            continue
        if members[0].gold_outcome != members[1].gold_outcome:
            errors.append(
                f"Invariance pair '{pair_id}' outcome unstable: {members[0].gold_outcome} != {members[1].gold_outcome}."
            )

    # 5. Clause grouping split safety
    try:
        train_set, test_set = split_scenarios_by_clause(scenarios, test_ratio=0.3, random_seed=42)
        # If single clause, split safely puts all in train (0% leakage)
        train_clauses = {s.clause_id for s in train_set}
        test_clauses = {s.clause_id for s in test_set}
        leakage = train_clauses.intersection(test_clauses)
        if leakage:
            errors.append(f"Clause leakage in split_scenarios_by_clause: {leakage}")

        train_pairs = {s.pair_id for s in train_set if s.pair_id}
        test_pairs = {s.pair_id for s in test_set if s.pair_id}
        pair_leakage = train_pairs.intersection(test_pairs)
        if pair_leakage:
            errors.append(f"Pair breakage across partitions in split_scenarios_by_clause: {pair_leakage}")
    except Exception as e:
        errors.append(f"Split safety evaluation failed: {e}")

    is_valid = len(errors) == 0
    return ValidationReport(
        is_valid=is_valid,
        total_scenarios=len(scenarios),
        provisional_scenarios_count=provisional_count,
        gold_scenarios_count=gold_count,
        scenario_types=dict(type_counts),
        pairs_validated=len(minimal_pairs) + len(invariance_pairs),
        minimal_pairs_count=len(minimal_pairs),
        invariance_pairs_count=len(invariance_pairs),
        errors=errors,
        warnings=warnings,
    )

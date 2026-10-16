"""Dataset Partitioning and Leakage Protection Utility.

Implements clause-grouped partitioning required by the alignment plan and v4 spec:
  "Split by source clause; keep all variants of a clause in one partition."
  "Test clauses are disjoint from development clauses."

Ensures:
  1. Zero leakage of source provisions between partitions (train vs test clauses are strictly disjoint).
  2. Minimal pairs and invariance pairs sharing a pair_id remain together in the same partition.
"""

from __future__ import annotations

import collections
import random
from typing import Dict, List, Set, Tuple

from backend.src.models.domain import BenchmarkScenario


def split_scenarios_by_clause(
    scenarios: List[BenchmarkScenario],
    test_ratio: float = 0.3,
    random_seed: int = 42,
) -> Tuple[List[BenchmarkScenario], List[BenchmarkScenario]]:
    """Partition benchmark scenarios into train and test sets grouped strictly by clause_id.

    Guarantees:
      - All scenarios derived from a specific clause_id belong to either the train or test partition.
      - Scenarios linked by a pair_id (minimal pairs, invariance pairs) always stay together.
      - Train and test partitions contain disjoint sets of clause_ids.

    Args:
        scenarios: List of BenchmarkScenario objects.
        test_ratio: Target fraction of distinct clauses in the test set (default 0.3).
        random_seed: Deterministic seed for reproducible partitioning.

    Returns:
        (train_scenarios, test_scenarios)
    """
    if not scenarios:
        return [], []

    # 1. Group scenarios by clause_id
    clause_to_scenarios: Dict[str, List[BenchmarkScenario]] = collections.defaultdict(list)
    for scen in scenarios:
        clause_to_scenarios[scen.clause_id].append(scen)

    unique_clauses = sorted(clause_to_scenarios.keys())
    total_clauses = len(unique_clauses)

    if total_clauses <= 1:
        # Cannot split single clause without leakage; put all in train
        return list(scenarios), []

    # 2. Deterministic shuffle of clause IDs
    rng = random.Random(random_seed)
    shuffled_clauses = list(unique_clauses)
    rng.shuffle(shuffled_clauses)

    # 3. Determine partition boundary
    test_count = max(1, int(round(total_clauses * test_ratio)))
    if test_count >= total_clauses:
        test_count = total_clauses - 1

    test_clauses: Set[str] = set(shuffled_clauses[:test_count])
    train_clauses: Set[str] = set(shuffled_clauses[test_count:])

    # 4. Assemble partitions
    train_scenarios: List[BenchmarkScenario] = []
    test_scenarios: List[BenchmarkScenario] = []

    for cid in train_clauses:
        train_scenarios.extend(clause_to_scenarios[cid])

    for cid in test_clauses:
        test_scenarios.extend(clause_to_scenarios[cid])

    # 5. Sanity assertion: Zero clause leakage
    train_cids = {s.clause_id for s in train_scenarios}
    test_cids = {s.clause_id for s in test_scenarios}
    leakage = train_cids.intersection(test_cids)
    if leakage:
        raise AssertionError(f"Leakage detected! Clauses present in both partitions: {leakage}")

    # 6. Sanity assertion: Zero pair_id breakage
    train_pairs = {s.pair_id for s in train_scenarios if s.pair_id}
    test_pairs = {s.pair_id for s in test_scenarios if s.pair_id}
    pair_leakage = train_pairs.intersection(test_pairs)
    if pair_leakage:
        raise AssertionError(f"Leakage detected! Pair IDs split across partitions: {pair_leakage}")

    return train_scenarios, test_scenarios

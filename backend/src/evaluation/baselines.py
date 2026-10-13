"""Component [O6]: Baselines and Common Evaluation Interface.

Defines the common BaselineSystem interface and adapters for:
- System P (Proposed pipeline: verified compile-and-execute)
- Baseline B0 (Oracle-context long-context LLM)
- Baseline B1 (BM25 lexical retrieval + LLM)
- Baseline B2 (Dense embedding retrieval + LLM)
- Baseline B3 (Hybrid BM25 + dense + reranker + LLM)
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union

from backend.src.engine.applicability import evaluate_rule
from backend.src.engine.impact_mapper import BusinessImpact, map_impact
from backend.src.models.domain import (
    BenchmarkScenario,
    EvaluationResult,
    OutcomeStatus,
    Rule,
)


class BaselineSystem(ABC):
    """Abstract base class representing an evaluatable regulatory impact system."""

    name: str

    @abstractmethod
    def evaluate_scenario(self, scenario: BenchmarkScenario) -> EvaluationResult:
        """Evaluate a benchmark scenario and return an EvaluationResult."""
        pass


class SystemP(BaselineSystem):
    """Proposed System (P): Verified Rule Compilation and Deterministic Execution Pipeline.
    
    Evaluates regulatory rules against a business profile using 3-valued Kleene logic,
    temporal intervals, and deterministic impact mapping.
    """

    name: str = "P_Proposed_System"

    def __init__(
        self,
        rules: Optional[Union[Dict[str, Rule], List[Rule], Rule]] = None,
    ):
        self.rules: Dict[str, Rule] = {}
        if isinstance(rules, Rule):
            self.register_rule(rules)
        elif isinstance(rules, list):
            for r in rules:
                self.register_rule(r)
        elif isinstance(rules, dict):
            for k, r in rules.items():
                self.register_rule(r)

    def register_rule(self, rule: Rule) -> None:
        """Register a compiled/verified rule into the system's rule store."""
        self.rules[rule.rule_id] = rule
        self.rules[rule.source.clause] = rule

    def evaluate_scenario(self, scenario: BenchmarkScenario) -> EvaluationResult:
        """Execute deterministic rule evaluation for the scenario."""
        # Find rule matching scenario clause_id or rule_id
        rule = self.rules.get(scenario.clause_id)
        if not rule:
            for r in self.rules.values():
                if r.rule_id == scenario.clause_id or r.source.clause == scenario.clause_id:
                    rule = r
                    break

        if not rule:
            return EvaluationResult(
                status=OutcomeStatus.UNSUPPORTED,
                rule_id=scenario.clause_id,
                missing_fields=[],
                evaluation_trace=[],
                reason=f"No verified compiled rule found for clause '{scenario.clause_id}' (unsupported / coverage gap).",
            )

        # Deterministic evaluation using engine
        eval_result = evaluate_rule(
            rule=rule,
            profile=scenario.business_profile,
            as_at_date=scenario.as_at_date,
        )

        # Map impact if applicable
        if eval_result.status == OutcomeStatus.APPLICABLE:
            impact: Optional[BusinessImpact] = map_impact(rule, eval_result)
            if impact and hasattr(eval_result, "model_extra"):
                if eval_result.model_extra is None:
                    eval_result.model_extra = {}
                eval_result.model_extra["impact"] = impact.model_dump()

        return eval_result


class OracleBaseline(BaselineSystem):
    """Baseline B0: Long-context LLM with oracle-selected relevant regulatory context (no retrieval)."""

    name: str = "B0_Oracle_LongContext"

    def __init__(
        self,
        predictor: Optional[Callable[[BenchmarkScenario], EvaluationResult]] = None,
        context_store: Optional[Dict[str, str]] = None,
    ):
        self.predictor = predictor
        self.context_store = context_store or {}

    def evaluate_scenario(self, scenario: BenchmarkScenario) -> EvaluationResult:
        if self.predictor:
            return self.predictor(scenario)
        # Default mock simulation
        return EvaluationResult(
            status=OutcomeStatus.APPLICABLE,
            rule_id=scenario.clause_id,
            missing_fields=[],
            evaluation_trace=[],
            reason="Oracle baseline simulation response.",
        )


class BM25Baseline(BaselineSystem):
    """Baseline B1: BM25 lexical retrieval + LLM."""

    name: str = "B1_BM25_Lexical"

    def __init__(
        self,
        predictor: Optional[Callable[[BenchmarkScenario], EvaluationResult]] = None,
    ):
        self.predictor = predictor

    def evaluate_scenario(self, scenario: BenchmarkScenario) -> EvaluationResult:
        if self.predictor:
            return self.predictor(scenario)
        return EvaluationResult(
            status=OutcomeStatus.APPLICABLE,
            rule_id=scenario.clause_id,
            missing_fields=[],
            evaluation_trace=[],
            reason="BM25 baseline simulation response.",
        )


class DenseBaseline(BaselineSystem):
    """Baseline B2: Dense vector retrieval + LLM."""

    name: str = "B2_Dense_RAG"

    def __init__(
        self,
        predictor: Optional[Callable[[BenchmarkScenario], EvaluationResult]] = None,
    ):
        self.predictor = predictor

    def evaluate_scenario(self, scenario: BenchmarkScenario) -> EvaluationResult:
        if self.predictor:
            return self.predictor(scenario)
        return EvaluationResult(
            status=OutcomeStatus.APPLICABLE,
            rule_id=scenario.clause_id,
            missing_fields=[],
            evaluation_trace=[],
            reason="Dense RAG baseline simulation response.",
        )


class HybridBaseline(BaselineSystem):
    """Baseline B3: Hybrid retrieval (BM25 + pgvector) with reranker + LLM."""

    name: str = "B3_Hybrid_Rerank_RAG"

    def __init__(
        self,
        predictor: Optional[Callable[[BenchmarkScenario], EvaluationResult]] = None,
    ):
        self.predictor = predictor

    def evaluate_scenario(self, scenario: BenchmarkScenario) -> EvaluationResult:
        if self.predictor:
            return self.predictor(scenario)
        return EvaluationResult(
            status=OutcomeStatus.APPLICABLE,
            rule_id=scenario.clause_id,
            missing_fields=[],
            evaluation_trace=[],
            reason="Hybrid RAG baseline simulation response.",
        )

"""Component [O6]: Genuine Baselines and Common Evaluation Interface.

Defines the common BaselineSystem interface and complete RAG adapters for:
  - Baseline B0 (Oracle-context long-context LLM, bypassing retrieval)
  - Baseline B1 (BM25 lexical retrieval + LLM generation)
  - Baseline B2 (Dense vector retrieval + LLM generation)
  - Baseline B3 (Hybrid RRF retrieval + LLM generation)
  - System P (Proposed pipeline: retrieval + verified compilation + deterministic execution + coverage gap exposure)

Design Constraints (§5, Milestone 4 of alignment plan):
  1. Identical prompt structure, target output schema, and LLM temperature (0.0) across all baselines.
  2. Failures in retrieval or LLM parsing are recorded as UNSUPPORTED evaluation failures, never hallucinated as successes.
  3. System P explicitly identifies coverage gaps (retrieved clauses lacking approved rules).
  4. Preserves backward compatibility with Phase A custom predictor callables.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from backend.src.db.models import RuleORM
from backend.src.db.repositories import PostgresRegulatoryRepository, rule_orm_to_domain
from backend.src.engine.applicability import evaluate_rule
from backend.src.engine.impact_mapper import BusinessImpact, map_impact
from backend.src.engine.retrieval import (
    BM25RetrievalEngine,
    BaseRetrievalEngine,
    DenseRetrievalEngine,
    HybridRetrievalEngine,
    RetrievalResult,
    cross_reference_coverage_gaps,
)
from backend.src.extraction.compiler import BaseLLMClient, LLMClient
from backend.src.models.domain import (
    BenchmarkScenario,
    EvaluationResult,
    OutcomeStatus,
    Rule,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Common LLM Prompt for RAG Baselines
# ---------------------------------------------------------------------------

BASELINE_EVALUATION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": [
                "APPLICABLE",
                "NOT_APPLICABLE",
                "CONDITIONAL_MISSING_DATA",
                "UNSUPPORTED",
            ],
        },
        "missing_fields": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of business profile fields missing to decide applicability.",
        },
        "reason": {
            "type": "string",
            "description": "Factual statutory explanation justifying the outcome.",
        },
    },
    "required": ["status"],
}


def construct_baseline_prompt(
    context_text: str,
    scenario: BenchmarkScenario,
) -> str:
    """Construct standard evaluation prompt for LLM RAG baselines.

    Used across B0, B1, B2, and B3 to ensure strict experimental fairness.
    """
    profile_json = json.dumps(scenario.business_profile.model_dump(exclude_none=True), indent=2)
    return (
        "You are an expert regulatory compliance assessor for Sri Lanka legislation.\n"
        "Evaluate whether the provided business profile is subject to regulatory obligations "
        "under the given legal context as of the specified assessment date.\n\n"
        "### REGULATORY CONTEXT:\n"
        f"{context_text}\n\n"
        "### BUSINESS PROFILE:\n"
        f"{profile_json}\n\n"
        f"### AS-AT ASSESSMENT DATE:\n{scenario.as_at_date}\n\n"
        "### TARGET CLAUSE / TOPIC OF INQUIRY:\n"
        f"{scenario.clause_id}\n\n"
        "### OUTPUT INSTRUCTIONS:\n"
        "Determine the regulatory outcome. You MUST return a JSON object with:\n"
        "1. 'status': One of 'APPLICABLE', 'NOT_APPLICABLE', 'CONDITIONAL_MISSING_DATA', or 'UNSUPPORTED'.\n"
        "   - Use 'APPLICABLE' if all statutory conditions are met as of the assessment date.\n"
        "   - Use 'NOT_APPLICABLE' if the profile falls outside statutory scope or before commencement.\n"
        "   - Use 'CONDITIONAL_MISSING_DATA' if specific required profile data is missing to decide.\n"
        "   - Use 'UNSUPPORTED' if the context does not contain sufficient statutory rules to decide.\n"
        "2. 'missing_fields': Array of field names if status is CONDITIONAL_MISSING_DATA, otherwise empty.\n"
        "3. 'reason': Concise statutory explanation.\n\n"
        "Return valid JSON only."
    )


def _parse_llm_response(
    raw_dict: Dict[str, Any],
    clause_id: str,
    retrieval_metadata: Optional[Dict[str, Any]] = None,
) -> EvaluationResult:
    """Safely parse LLM baseline JSON response into EvaluationResult."""
    status_str = str(raw_dict.get("status", "UNSUPPORTED")).strip().upper()
    try:
        status_enum = OutcomeStatus(status_str)
    except ValueError:
        logger.warning("Unrecognised status %r from LLM baseline; defaulting to UNSUPPORTED.", status_str)
        status_enum = OutcomeStatus.UNSUPPORTED

    missing_fields = raw_dict.get("missing_fields") or []
    if not isinstance(missing_fields, list):
        missing_fields = []

    reason = str(raw_dict.get("reason", "LLM baseline evaluation result."))

    extra = dict(retrieval_metadata or {})
    return EvaluationResult(
        status=status_enum,
        rule_id=clause_id,
        missing_fields=missing_fields,
        evaluation_trace=[],
        reason=reason,
        **extra,
    )


# ---------------------------------------------------------------------------
# Base Interface
# ---------------------------------------------------------------------------

class BaselineSystem(ABC):
    """Abstract base class representing an evaluatable regulatory impact system."""

    name: str

    @abstractmethod
    def evaluate_scenario(self, scenario: BenchmarkScenario) -> EvaluationResult:
        """Evaluate a benchmark scenario and return an EvaluationResult."""
        pass


# ---------------------------------------------------------------------------
# Baseline B0: Oracle Long-Context LLM (No Retrieval)
# ---------------------------------------------------------------------------

class OracleBaseline(BaselineSystem):
    """Baseline B0: Long-context LLM with oracle-selected regulatory context.

    Represents the upper-bound context comprehension ceiling by feeding the exact
    relevant source clause text directly into the LLM, bypassing retrieval entirely.
    """

    name: str = "B0_Oracle_LongContext"

    def __init__(
        self,
        predictor: Optional[Callable[[BenchmarkScenario], EvaluationResult]] = None,
        context_store: Optional[Dict[str, str]] = None,
        llm_client: Optional[Union[LLMClient, BaseLLMClient]] = None,
    ):
        self.predictor = predictor
        self.context_store = context_store or {}
        self.llm_client = llm_client

    def evaluate_scenario(self, scenario: BenchmarkScenario) -> EvaluationResult:
        if self.predictor:
            return self.predictor(scenario)

        if not self.llm_client:
            return EvaluationResult(
                status=OutcomeStatus.UNSUPPORTED,
                rule_id=scenario.clause_id,
                missing_fields=[],
                evaluation_trace=[],
                reason="Baseline B0 unavailable: LLM client is not configured.",
                error="missing_llm_client",
                failed=True,
            )

        # Retrieve oracle ground-truth context
        oracle_text = self.context_store.get(scenario.clause_id)
        if not oracle_text and hasattr(scenario, "oracle_context"):
            oracle_text = getattr(scenario, "oracle_context")

        if not oracle_text:
            return EvaluationResult(
                status=OutcomeStatus.UNSUPPORTED,
                rule_id=scenario.clause_id,
                missing_fields=[],
                reason=f"No oracle context found in context_store for '{scenario.clause_id}'.",
                error="missing_oracle_context",
                failed=True,
            )

        prompt = construct_baseline_prompt(oracle_text, scenario)
        try:
            response_dict = self.llm_client.generate_rule(prompt, BASELINE_EVALUATION_SCHEMA)
            return _parse_llm_response(
                response_dict,
                scenario.clause_id,
                retrieval_metadata={"oracle_context_length": len(oracle_text), "method": "oracle"},
            )
        except Exception as exc:
            logger.error("B0 Oracle LLM generation failed: %s", exc)
            return EvaluationResult(
                status=OutcomeStatus.UNSUPPORTED,
                rule_id=scenario.clause_id,
                missing_fields=[],
                reason=f"Oracle LLM generation failed: {exc}",
                error=str(exc),
                failed=True,
                method="oracle",
            )


# ---------------------------------------------------------------------------
# Baseline B1: BM25 Lexical Retrieval + LLM
# ---------------------------------------------------------------------------

class BM25Baseline(BaselineSystem):
    """Baseline B1: BM25 lexical retrieval + LLM generation."""

    name: str = "B1_BM25_Lexical"

    def __init__(
        self,
        retrieval_engine: Optional[BM25RetrievalEngine] = None,
        llm_client: Optional[Union[LLMClient, BaseLLMClient]] = None,
        predictor: Optional[Callable[[BenchmarkScenario], EvaluationResult]] = None,
        top_k: int = 3,
    ):
        self.retrieval_engine = retrieval_engine
        self.llm_client = llm_client
        self.predictor = predictor
        self.top_k = top_k

    def evaluate_scenario(self, scenario: BenchmarkScenario) -> EvaluationResult:
        if self.predictor:
            return self.predictor(scenario)

        if not self.retrieval_engine or not self.llm_client:
            missing_dep = "retrieval engine" if not self.retrieval_engine else "LLM client"
            return EvaluationResult(
                status=OutcomeStatus.UNSUPPORTED,
                rule_id=scenario.clause_id,
                missing_fields=[],
                evaluation_trace=[],
                reason=f"Baseline B1 unavailable: {missing_dep} is not configured.",
                error=f"missing_{missing_dep.replace(' ', '_')}",
                failed=True,
            )

        # Construct query from scenario
        query = f"{scenario.clause_id} {scenario.business_profile.activity or ''} {scenario.business_profile.industry or ''}".strip()
        passages = self.retrieval_engine.search(query, top_k=self.top_k)

        if not passages:
            return EvaluationResult(
                status=OutcomeStatus.UNSUPPORTED,
                rule_id=scenario.clause_id,
                missing_fields=[],
                reason=f"BM25 retrieval returned zero candidate passages for query {query!r}.",
                retrieved_count=0,
                method="bm25",
            )

        context_text = "\n\n---\n\n".join(
            f"Passage [{p.clause_id} - {p.document_title or p.document_id}]:\n{p.text}"
            for p in passages
        )
        prompt = construct_baseline_prompt(context_text, scenario)

        try:
            response_dict = self.llm_client.generate_rule(prompt, BASELINE_EVALUATION_SCHEMA)
            meta = {
                "method": "bm25",
                "retrieved_clause_ids": [p.clause_id for p in passages],
                "top_score": passages[0].score,
            }
            return _parse_llm_response(response_dict, scenario.clause_id, retrieval_metadata=meta)
        except Exception as exc:
            logger.error("B1 BM25 LLM evaluation failed: %s", exc)
            return EvaluationResult(
                status=OutcomeStatus.UNSUPPORTED,
                rule_id=scenario.clause_id,
                missing_fields=[],
                reason=f"BM25 LLM generation failed: {exc}",
                error=str(exc),
                method="bm25",
                failed=True,
            )


# ---------------------------------------------------------------------------
# Baseline B2: Dense Vector Retrieval + LLM
# ---------------------------------------------------------------------------

class DenseBaseline(BaselineSystem):
    """Baseline B2: Dense embedding vector retrieval + LLM generation."""

    name: str = "B2_Dense_RAG"

    def __init__(
        self,
        retrieval_engine: Optional[DenseRetrievalEngine] = None,
        llm_client: Optional[Union[LLMClient, BaseLLMClient]] = None,
        predictor: Optional[Callable[[BenchmarkScenario], EvaluationResult]] = None,
        top_k: int = 3,
    ):
        self.retrieval_engine = retrieval_engine
        self.llm_client = llm_client
        self.predictor = predictor
        self.top_k = top_k

    def evaluate_scenario(self, scenario: BenchmarkScenario) -> EvaluationResult:
        if self.predictor:
            return self.predictor(scenario)

        if not self.retrieval_engine or not self.llm_client:
            missing_dep = "retrieval engine" if not self.retrieval_engine else "LLM client"
            return EvaluationResult(
                status=OutcomeStatus.UNSUPPORTED,
                rule_id=scenario.clause_id,
                missing_fields=[],
                evaluation_trace=[],
                reason=f"Baseline B2 unavailable: {missing_dep} is not configured.",
                error=f"missing_{missing_dep.replace(' ', '_')}",
                failed=True,
            )

        query = f"{scenario.clause_id} {scenario.business_profile.activity or ''} {scenario.business_profile.industry or ''}".strip()
        passages = self.retrieval_engine.search(query, top_k=self.top_k)

        if not passages:
            return EvaluationResult(
                status=OutcomeStatus.UNSUPPORTED,
                rule_id=scenario.clause_id,
                missing_fields=[],
                reason=f"Dense retrieval returned zero candidate passages for query {query!r}.",
                retrieved_count=0,
                method="dense",
            )

        context_text = "\n\n---\n\n".join(
            f"Passage [{p.clause_id} - {p.document_title or p.document_id}]:\n{p.text}"
            for p in passages
        )
        prompt = construct_baseline_prompt(context_text, scenario)

        try:
            response_dict = self.llm_client.generate_rule(prompt, BASELINE_EVALUATION_SCHEMA)
            meta = {
                "method": "dense",
                "retrieved_clause_ids": [p.clause_id for p in passages],
                "top_score": passages[0].score,
            }
            return _parse_llm_response(response_dict, scenario.clause_id, retrieval_metadata=meta)
        except Exception as exc:
            logger.error("B2 Dense LLM evaluation failed: %s", exc)
            return EvaluationResult(
                status=OutcomeStatus.UNSUPPORTED,
                rule_id=scenario.clause_id,
                missing_fields=[],
                reason=f"Dense LLM generation failed: {exc}",
                error=str(exc),
                method="dense",
                failed=True,
            )


# ---------------------------------------------------------------------------
# Baseline B3: Hybrid RRF Retrieval + LLM
# ---------------------------------------------------------------------------

class HybridBaseline(BaselineSystem):
    """Baseline B3: Hybrid retrieval (BM25 + Dense fused via RRF) + LLM generation."""

    name: str = "B3_Hybrid_Rerank_RAG"

    def __init__(
        self,
        retrieval_engine: Optional[HybridRetrievalEngine] = None,
        llm_client: Optional[Union[LLMClient, BaseLLMClient]] = None,
        predictor: Optional[Callable[[BenchmarkScenario], EvaluationResult]] = None,
        top_k: int = 3,
    ):
        self.retrieval_engine = retrieval_engine
        self.llm_client = llm_client
        self.predictor = predictor
        self.top_k = top_k

    def evaluate_scenario(self, scenario: BenchmarkScenario) -> EvaluationResult:
        if self.predictor:
            return self.predictor(scenario)

        if not self.retrieval_engine or not self.llm_client:
            missing_dep = "retrieval engine" if not self.retrieval_engine else "LLM client"
            return EvaluationResult(
                status=OutcomeStatus.UNSUPPORTED,
                rule_id=scenario.clause_id,
                missing_fields=[],
                evaluation_trace=[],
                reason=f"Baseline B3 unavailable: {missing_dep} is not configured.",
                error=f"missing_{missing_dep.replace(' ', '_')}",
                failed=True,
            )

        query = f"{scenario.clause_id} {scenario.business_profile.activity or ''} {scenario.business_profile.industry or ''}".strip()
        passages = self.retrieval_engine.search(query, top_k=self.top_k)

        if not passages:
            return EvaluationResult(
                status=OutcomeStatus.UNSUPPORTED,
                rule_id=scenario.clause_id,
                missing_fields=[],
                reason=f"Hybrid retrieval returned zero candidate passages for query {query!r}.",
                retrieved_count=0,
                method="hybrid_rrf",
            )

        context_text = "\n\n---\n\n".join(
            f"Passage [{p.clause_id} - {p.document_title or p.document_id}]:\n{p.text}"
            for p in passages
        )
        prompt = construct_baseline_prompt(context_text, scenario)

        try:
            response_dict = self.llm_client.generate_rule(prompt, BASELINE_EVALUATION_SCHEMA)
            actual_method = passages[0].retrieval_method if passages else "hybrid_rrf"
            fallback_reason = (passages[0].metadata or {}).get("fallback_reason") if passages else None
            meta = {
                "method": actual_method,
                "retrieved_clause_ids": [p.clause_id for p in passages],
                "top_score": passages[0].score,
                "fallback_reason": fallback_reason,
            }
            return _parse_llm_response(response_dict, scenario.clause_id, retrieval_metadata=meta)
        except Exception as exc:
            logger.error("B3 Hybrid LLM evaluation failed: %s", exc)
            return EvaluationResult(
                status=OutcomeStatus.UNSUPPORTED,
                rule_id=scenario.clause_id,
                missing_fields=[],
                reason=f"Hybrid LLM generation failed: {exc}",
                error=str(exc),
                method="hybrid_rrf",
                failed=True,
            )


# ---------------------------------------------------------------------------
# Proposed System P: End-to-End Retrieval + Verified Compilation + Engine
# ---------------------------------------------------------------------------

class SystemP(BaselineSystem):
    """Proposed System (P): Retrieval $\to$ Verified Rule Selection $\to$ Deterministic Engine.

    Execution Pipeline:
      1. If configured with retrieval_engine + db, searches for candidate clauses matching the scenario.
      2. Cross-references candidates against the database for an APPROVED rule.
      3. If no approved rule exists, explicitly flags a 'coverage gap' and returns UNSUPPORTED.
      4. If an approved rule exists, executes deterministic Kleene logic via evaluate_rule.
      5. Maps business impact if APPLICABLE.
      6. Maintains backward-compatible fallback for directly registered rules.
    """

    name: str = "P_Proposed_System"

    def __init__(
        self,
        rules: Optional[Union[Dict[str, Rule], List[Rule], Rule]] = None,
        db: Optional[Session] = None,
        retrieval_engine: Optional[BaseRetrievalEngine] = None,
        top_k: int = 3,
    ):
        self.rules: Dict[str, Rule] = {}
        self.db = db
        self.retrieval_engine = retrieval_engine
        self.top_k = top_k

        if isinstance(rules, Rule):
            self.register_rule(rules)
        elif isinstance(rules, list):
            for r in rules:
                self.register_rule(r)
        elif isinstance(rules, dict):
            for r in rules.values():
                self.register_rule(r)

    def register_rule(self, rule: Rule) -> None:
        """Register a verified rule into the local rule store."""
        self.rules[rule.rule_id] = rule
        self.rules[rule.source.clause] = rule

    def evaluate_scenario(self, scenario: BenchmarkScenario) -> EvaluationResult:
        """Execute the verified System P pipeline for a benchmark scenario."""
        # --- Mode 1: Full Pipeline with Retrieval & Coverage Gap Detection ---
        if self.retrieval_engine is not None and self.db is not None:
            query = f"{scenario.clause_id} {scenario.business_profile.activity or ''} {scenario.business_profile.industry or ''}".strip()
            candidates = self.retrieval_engine.search(query, top_k=self.top_k)

            if not candidates:
                return EvaluationResult(
                    status=OutcomeStatus.UNSUPPORTED,
                    rule_id=scenario.clause_id,
                    missing_fields=[],
                    evaluation_trace=[],
                    reason=f"System P: No candidate statutory clauses retrieved for {query!r}.",
                    coverage_gap=True,
                    method="system_p_retrieval",
                )

            # Cross-reference candidates against database rules
            candidate_ids = [c.clause_id for c in candidates]
            approved_set = cross_reference_coverage_gaps(self.db, candidate_ids)

            # In retrieval mode, examine the primary retrieved candidate (top rank)
            top_candidate = candidates[0]
            if top_candidate.clause_id not in approved_set:
                return EvaluationResult(
                    status=OutcomeStatus.UNSUPPORTED,
                    rule_id=scenario.clause_id,
                    missing_fields=[],
                    evaluation_trace=[],
                    reason=(
                        f"System P Coverage Gap: Candidate clause '{top_candidate.clause_id}' was retrieved "
                        "but does not have an approved, verified executable rule."
                    ),
                    coverage_gap=True,
                    retrieved_clause_ids=candidate_ids,
                    method="system_p_retrieval",
                )

            # Retrieve the verified rule from database
            rule_orm = (
                self.db.query(RuleORM)
                .filter(
                    RuleORM.clause_id == top_candidate.clause_id,
                    RuleORM.review_status == "APPROVED",
                )
                .first()
            )
            if not rule_orm:
                return EvaluationResult(
                    status=OutcomeStatus.UNSUPPORTED,
                    rule_id=scenario.clause_id,
                    missing_fields=[],
                    evaluation_trace=[],
                    reason=(
                        f"System P Coverage Gap: Candidate clause '{top_candidate.clause_id}' was retrieved "
                        "but does not have an approved, verified executable rule."
                    ),
                    coverage_gap=True,
                    retrieved_clause_ids=candidate_ids,
                    method="system_p_retrieval",
                )

            matched_rule = rule_orm_to_domain(rule_orm)

            # Deterministic execution of the verified approved rule
            eval_result = evaluate_rule(
                rule=matched_rule,
                profile=scenario.business_profile,
                as_at_date=scenario.as_at_date,
            )

            setattr(eval_result, "coverage_gap", False)
            setattr(eval_result, "method", "system_p_retrieval")
            setattr(eval_result, "grounded_rule_id", matched_rule.rule_id)

            if eval_result.status == OutcomeStatus.APPLICABLE:
                impact = map_impact(matched_rule, eval_result)
                if impact:
                    setattr(eval_result, "impact", impact.model_dump())

            return eval_result

        # --- Mode 2: Direct Rule Store Mode (Phase A compatibility) ---
        target_rule_id = getattr(scenario, "target_rule_id", None)
        if not target_rule_id:
            extra = getattr(scenario, "model_extra", None) or {}
            target_rule_ids = getattr(scenario, "target_rule_ids", None) or extra.get("target_rule_ids")
            if target_rule_ids and isinstance(target_rule_ids, list) and len(target_rule_ids) > 0:
                target_rule_id = target_rule_ids[0]

        rule = None
        if target_rule_id and target_rule_id in self.rules:
            rule = self.rules[target_rule_id]
        if not rule:
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
                coverage_gap=True,
                method="system_p_direct",
            )

        eval_result = evaluate_rule(
            rule=rule,
            profile=scenario.business_profile,
            as_at_date=scenario.as_at_date,
        )

        setattr(eval_result, "coverage_gap", False)
        setattr(eval_result, "method", "system_p_direct")

        if eval_result.status == OutcomeStatus.APPLICABLE:
            impact = map_impact(rule, eval_result)
            if impact:
                setattr(eval_result, "impact", impact.model_dump())

        return eval_result


# ---------------------------------------------------------------------------
# System P Ablations (Section 8.8 / Milestone 6)
# ---------------------------------------------------------------------------

class AblationPNoVerification(SystemP):
    """Ablation P-A: System P without human-review verification safety gate.

    Bypasses the approved-rule gate by executing unreviewed candidates or attempting
    direct unverified completion when an approved rule is absent.
    """

    name: str = "P-A_NoVerification"

    def evaluate_scenario(self, scenario: BenchmarkScenario) -> EvaluationResult:
        res = super().evaluate_scenario(scenario)
        if res.status == OutcomeStatus.UNSUPPORTED and res.model_extra.get("coverage_gap"):
            return EvaluationResult(
                status=OutcomeStatus.APPLICABLE,
                rule_id=scenario.clause_id,
                missing_fields=[],
                evaluation_trace=[],
                reason="[Ablation P-A: Unverified execution] Bypassed verification safety gate; ungrounded assumption of applicability.",
                coverage_gap=False,
                method="ablation_p_no_verification",
            )
        return res


class AblationPNoTemporal(SystemP):
    """Ablation P-B: System P without temporal / commencement validity checks.

    Evaluates rules assuming they are in active effect regardless of the scenario as_at_date.
    """

    name: str = "P-B_NoTemporal"

    def evaluate_scenario(self, scenario: BenchmarkScenario) -> EvaluationResult:
        scen_future = scenario.model_copy(deep=True)
        scen_future.as_at_date = "2099-12-31"
        res = super().evaluate_scenario(scen_future)
        setattr(res, "method", "ablation_p_no_temporal")
        return res


class AblationPNoAbstention(SystemP):
    """Ablation P-C: System P with 2-valued forced choice logic (no 3-valued Kleene abstention).

    Coerces CONDITIONAL_MISSING_DATA into NOT_APPLICABLE.
    """

    name: str = "P-C_NoAbstention"

    def evaluate_scenario(self, scenario: BenchmarkScenario) -> EvaluationResult:
        res = super().evaluate_scenario(scenario)
        if res.status == OutcomeStatus.CONDITIONAL_MISSING_DATA:
            res_dict = res.model_dump()
            res_dict["status"] = OutcomeStatus.NOT_APPLICABLE
            res_dict["missing_fields"] = []
            res_dict["reason"] = f"[Ablation P-C: 2-valued forced choice] Missing data coerced to NOT_APPLICABLE: {res.reason}"
            coerced = EvaluationResult(**res_dict)
            setattr(coerced, "method", "ablation_p_no_abstention")
            return coerced
        return res


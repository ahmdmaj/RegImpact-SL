"""Component [I]: The Explanation Layer for RegImpact-SL.

Generates human-readable, executive regulatory summaries strictly conditioned on
the structured facts, audit traces, and action items of a StructuredImpactReport.
"""

from typing import Any, List, Optional
import json

from backend.src.extraction.compiler import LLMClient


def construct_explanation_prompt(report: Any) -> str:
    """Construct a constrained prompt providing structured facts to the LLM."""
    # 1. Summary statistics
    total = getattr(report, "total_rules_evaluated", 0)
    applicable = getattr(report, "applicable_rules_count", 0)
    conditional = getattr(report, "conditional_rules_count", 0)
    not_applicable = getattr(report, "not_applicable_rules_count", 0)
    as_at_date = getattr(report, "as_at_date", "2024-08-01")

    # 2. Extract applicable rules information
    evals = getattr(report, "evaluations", []) or []
    applicable_details: List[str] = []
    counterfactual_details: List[str] = []

    for ev in evals:
        st = getattr(ev, "status", "")
        st_val = st.value if hasattr(st, "value") else str(st)
        if st_val == "APPLICABLE":
            clause = getattr(ev, "clause", "Clause")
            inst = getattr(ev, "instrument", "Regulation")
            auth = getattr(ev, "authority", "Authority")
            applicable_details.append(f"- {clause} of {inst} ({auth})")
        
        cfs = getattr(ev, "counterfactuals", []) or []
        for cf in cfs:
            counterfactual_details.append(f"- {cf}")

    # 3. Action checklist and clarifying questions
    actions = getattr(report, "action_checklist", []) or []
    clarifying_questions = getattr(report, "clarifying_questions", []) or []

    prompt = (
        "You are an AI regulatory compliance assistant for RegImpact-SL, supporting small food manufacturers in Sri Lanka.\n"
        "Your task is to write a concise, professional executive summary explaining the regulatory impact results to the business owner.\n\n"
        "### STRUCTURED COMPLIANCE FACTS:\n"
        f"- Evaluation Date (As-At Date): {as_at_date}\n"
        f"- Total Rules Evaluated: {total}\n"
        f"- Applicable Rules ({applicable}):\n"
        + ("\n".join(applicable_details) if applicable_details else "  None") + "\n"
        f"- Conditional Missing Data Rules ({conditional})\n"
        f"- Not Applicable Rules ({not_applicable})\n\n"
        "### MANDATORY ACTION CHECKLIST:\n"
        + ("\n".join(f"- {a}" for a in actions) if actions else "  No immediate actions required.") + "\n\n"
        "### CLARIFYING QUESTIONS (MISSING DATA):\n"
        + ("\n".join(f"- {q}" for q in clarifying_questions) if clarifying_questions else "  No missing profile data.") + "\n\n"
        "### COUNTERFACTUAL GUIDANCE:\n"
        + ("\n".join(counterfactual_details) if counterfactual_details else "  None") + "\n\n"
        "### STRICT FACTUAL GROUNDING RULES:\n"
        "1. You MUST ONLY use the numbers, dates, thresholds, and facts explicitly listed above.\n"
        "2. Do NOT add external legal advice, unprovided dates, or unprovided penalty amounts/fines (e.g. do NOT invent fines like Rs. 50,000).\n"
        "3. Every factual statement must trace back directly to the provided structured facts.\n"
        "4. Keep the summary under 150 words, clear and actionable for an SME owner.\n\n"
        "Write the executive summary now:"
    )
    return prompt


class ExplanationGenerator:
    """Generates constrained natural-language summaries from StructuredImpactReport."""

    def __init__(self, llm_client: Optional[Any] = None):
        self.llm_client = llm_client

    def generate_summary(self, report: Any) -> str:
        """Generate a natural-language executive summary of the impact report."""
        prompt = construct_explanation_prompt(report)

        # 1. If an LLM client is provided, call it
        if self.llm_client is not None:
            if hasattr(self.llm_client, "generate_text"):
                return self.llm_client.generate_text(prompt)
            elif hasattr(self.llm_client, "generate_summary"):
                return self.llm_client.generate_summary(prompt)
            elif hasattr(self.llm_client, "generate_rule"):
                res = self.llm_client.generate_rule(
                    prompt,
                    {"type": "object", "properties": {"summary": {"type": "string"}}},
                )
                if isinstance(res, dict) and "summary" in res:
                    return res["summary"]
                return str(res)

        # 2. Deterministic grounded fallback synthesis (when no LLM client is configured)
        return self._generate_fallback_summary(report)

    def _generate_fallback_summary(self, report: Any) -> str:
        """Deterministically synthesize a grounded summary directly from facts."""
        total = getattr(report, "total_rules_evaluated", 0)
        applicable = getattr(report, "applicable_rules_count", 0)
        conditional = getattr(report, "conditional_rules_count", 0)
        as_at = getattr(report, "as_at_date", "2024-08-01")
        actions = getattr(report, "action_checklist", []) or []

        sentences = [
            f"As of {as_at}, {applicable} of {total} evaluated regulatory rules apply to your business."
        ]

        if applicable > 0 and actions:
            sentences.append(f"Immediate compliance actions include: {actions[0]}")

        if conditional > 0:
            sentences.append(
                f"{conditional} rule(s) require additional business details to determine final applicability."
            )

        return " ".join(sentences)

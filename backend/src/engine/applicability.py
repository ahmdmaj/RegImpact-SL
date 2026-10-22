"""Deterministic applicability engine for RegImpact-SL.

Evaluates regulatory rules against a business profile using:
- Three-valued logic (TRUE, FALSE, UNKNOWN)
- Nested dot-notation field lookups
- Kleene boolean logic with short-circuit safety
- Temporal validity intervals (published, commences, transition, superseded)
- Auditable evaluation trace and minimum missing fields search
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.src.models.domain import (
    BusinessProfile,
    Condition,
    EvaluationResult,
    OutcomeStatus,
    Rule,
    TriState,
    Validity,
)


def parse_date(val: Optional[Union[str, date, datetime]]) -> Optional[date]:
    """Parse string, date, or datetime into date object."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        cleaned = val.strip()
        if not cleaned:
            return None
        # Handle ISO date format like YYYY-MM-DD or full ISO datetime
        try:
            return date.fromisoformat(cleaned[:10])
        except (ValueError, TypeError):
            try:
                return datetime.fromisoformat(cleaned.replace("Z", "+00:00")).date()
            except (ValueError, TypeError):
                return None
    return None


def extract_field(obj: Any, path: str) -> Tuple[Any, bool]:
    """Extract nested field using dot-notation.
    
    Returns:
        (value, is_known): value of the field and whether it was successfully found (not None).
    """
    if obj is None or not path:
        return None, False

    tokens = path.split(".")
    curr = obj

    for i, token in enumerate(tokens):
        if curr is None:
            return None, False

        # Support dict lookup
        if isinstance(curr, dict):
            if token in curr:
                curr = curr[token]
            else:
                # Check compound unit conversion for production capacity
                if token == "kg_per_day":
                    unit = curr.get("unit")
                    period = curr.get("per_period")
                    val = curr.get("value")
                    if unit and str(unit).lower() == "kg" and period and str(period).lower() in ["day", "daily", "per_day"]:
                        curr = val
                    else:
                        return None, False
                else:
                    return None, False
        # Support Pydantic model / object lookup
        else:
            if hasattr(curr, token):
                curr = getattr(curr, token)
            elif hasattr(curr, "model_extra") and curr.model_extra and token in curr.model_extra:
                curr = curr.model_extra[token]
            else:
                # Check compound unit conversion for production capacity model
                if token == "kg_per_day":
                    unit = getattr(curr, "unit", None)
                    period = getattr(curr, "per_period", None)
                    val = getattr(curr, "value", None)
                    if unit and str(unit).lower() == "kg" and period and str(period).lower() in ["day", "daily", "per_day"]:
                        curr = val
                    else:
                        return None, False
                else:
                    return None, False

    if curr is None:
        return None, False
    return curr, True


def evaluate_operator(op: str, observed: Any, target: Any) -> bool:
    """Evaluate comparison operators between observed profile value and target rule value."""
    op_norm = op.strip().lower()

    # Normalize aliases
    op_map = {
        "==": "eq",
        "!=": "neq",
        ">": "gt",
        ">=": "gte",
        "<": "lt",
        "<=": "lte",
    }
    op_norm = op_map.get(op_norm, op_norm)

    if op_norm == "eq":
        if isinstance(observed, str) and isinstance(target, str):
            return observed.strip().lower() == target.strip().lower()
        if isinstance(observed, (int, float)) and isinstance(target, (int, float, str)):
            try:
                return float(observed) == float(target)
            except (ValueError, TypeError):
                pass
        return observed == target

    elif op_norm == "neq":
        return not evaluate_operator("eq", observed, target)

    elif op_norm in ("gt", "gte", "lt", "lte"):
        try:
            obs_num = float(observed)
            tgt_num = float(target)
            if op_norm == "gt":
                return obs_num > tgt_num
            elif op_norm == "gte":
                return obs_num >= tgt_num
            elif op_norm == "lt":
                return obs_num < tgt_num
            elif op_norm == "lte":
                return obs_num <= tgt_num
        except (ValueError, TypeError):
            return False

    elif op_norm == "in":
        if isinstance(target, (list, tuple, set)):
            if isinstance(observed, str):
                return observed.strip().lower() in [str(x).strip().lower() for x in target]
            return observed in target
        elif isinstance(target, str):
            return str(observed).strip().lower() in target.strip().lower()
        return False

    elif op_norm == "contains":
        if isinstance(observed, (list, tuple, set)):
            if isinstance(target, str):
                return target.strip().lower() in [str(x).strip().lower() for x in observed]
            return target in observed
        elif isinstance(observed, str):
            return str(target).strip().lower() in observed.strip().lower()
        elif isinstance(observed, dict):
            return target in observed
        return False

    return False


def evaluate_single_condition(
    condition: Union[Condition, Dict[str, Any]],
    profile: Union[BusinessProfile, Dict[str, Any]],
) -> Tuple[TriState, Any, Optional[str]]:
    """Evaluate a single condition over the profile.
    
    Returns:
        (result, observed_value, missing_field_path_if_unknown)
    """
    if isinstance(condition, dict):
        field_path = condition.get("field", "")
        op = condition.get("op", "")
        target_val = condition.get("value")
    else:
        field_path = condition.field
        op = condition.op
        target_val = condition.value

    # Check if dot path traverses a list collection (e.g., products.prepackaged)
    tokens = field_path.split(".")
    first_token = tokens[0]
    
    # Get collection from profile if first token points to a list
    coll_val, coll_known = extract_field(profile, first_token)
    if isinstance(coll_val, list) and len(tokens) > 1:
        rem_path = ".".join(tokens[1:])
        if len(coll_val) == 0:
            # Empty collection cannot satisfy condition
            return TriState.FALSE, [], None

        sub_results = []
        sub_observed = []
        has_unknown = False

        for item in coll_val:
            item_val, item_known = extract_field(item, rem_path)
            sub_observed.append(item_val)
            if not item_known or item_val is None:
                sub_results.append(TriState.UNKNOWN)
                has_unknown = True
            else:
                try:
                    match = evaluate_operator(op, item_val, target_val)
                    sub_results.append(TriState.TRUE if match else TriState.FALSE)
                except Exception:
                    sub_results.append(TriState.FALSE)

        # Existential matching over collection:
        # If any item is TRUE -> TRUE
        if any(r == TriState.TRUE for r in sub_results):
            return TriState.TRUE, sub_observed, None
        # If any item was UNKNOWN -> UNKNOWN
        if has_unknown:
            return TriState.UNKNOWN, sub_observed, field_path
        # Otherwise all were FALSE -> FALSE
        return TriState.FALSE, sub_observed, None

    # Scalar / nested dict / model path lookup
    observed_val, is_known = extract_field(profile, field_path)
    if not is_known or observed_val is None:
        return TriState.UNKNOWN, observed_val, field_path

    try:
        match = evaluate_operator(op, observed_val, target_val)
        return (TriState.TRUE if match else TriState.FALSE), observed_val, None
    except Exception:
        return TriState.FALSE, observed_val, None


# Alias for backward compatibility and clean export
evaluate_condition = evaluate_single_condition



def evaluate_temporal_validity(
    validity: Union[Validity, Dict[str, Any]],
    as_at_date: Optional[Union[str, date, datetime]] = None,
) -> Tuple[bool, str, Optional[str]]:
    """Evaluate whether a rule is temporally valid at as_at_date.
    
    Returns:
        (is_valid, temporal_status, rejection_reason)
    """
    if as_at_date is None:
        return True, "IN_FORCE", None

    eval_date = parse_date(as_at_date)
    if eval_date is None:
        return True, "IN_FORCE", None

    if isinstance(validity, dict):
        published_str = validity.get("published")
        commences_str = validity.get("commences")
        transition_str = validity.get("transition_until")
        superseded_by = validity.get("superseded_by")
        superseded_date_str = validity.get("superseded_date")
    else:
        published_str = validity.published
        commences_str = validity.commences
        transition_str = validity.transition_until
        superseded_by = validity.superseded_by
        superseded_date_str = getattr(validity, "superseded_date", None)

    commences_d = parse_date(commences_str)
    transition_d = parse_date(transition_str)
    
    # Determine superseded date if present
    superseded_d = parse_date(superseded_date_str)
    if superseded_d is None and superseded_by:
        superseded_d = parse_date(superseded_by)

    # 1. Before commencement -> NOT_APPLICABLE (not yet in force)
    if commences_d and eval_date < commences_d:
        return False, "NOT_YET_IN_FORCE", f"Rule not yet in force as of {eval_date.isoformat()} (commences {commences_d.isoformat()})"

    # 2. Superseded check: if superseded_by is set and eval_date >= superseded_date
    if superseded_by:
        if superseded_d and eval_date >= superseded_d:
            # Check if transition_until provides a grace period
            if transition_d and eval_date <= transition_d:
                return True, "IN_TRANSITION", f"Rule superseded on {superseded_d.isoformat()} but valid within transition period until {transition_d.isoformat()}"
            return False, "SUPERSEDED", f"Rule superseded as of {eval_date.isoformat()} (superseded by {superseded_by})"

    # 3. Transition period during commencement
    if transition_d and commences_d and commences_d <= eval_date <= transition_d:
        return True, "IN_TRANSITION", None

    return True, "IN_FORCE", None


def evaluate_rule(
    rule: Union[Rule, Dict[str, Any]],
    profile: Union[BusinessProfile, Dict[str, Any]],
    as_at_date: Optional[Union[str, date, datetime]] = None,
) -> EvaluationResult:
    """Deterministically evaluate regulatory applicability of a rule against a business profile."""
    # Convert dicts or extract fields
    if isinstance(rule, dict):
        rule_id = rule.get("rule_id", "UNKNOWN_RULE")
        verification = rule.get("verification", {})
        validity = rule.get("validity", {})
        applies_if = rule.get("applies_if", {})
        exceptions = rule.get("exceptions", []) or []
    else:
        rule_id = rule.rule_id
        verification = rule.verification
        validity = rule.validity
        applies_if = rule.applies_if
        exceptions = rule.exceptions or []

    # Determine outcome_type (STANDARD vs CONDITIONAL_RULE per v4 §8.3)
    outcome_type = "STANDARD"
    if isinstance(rule, dict):
        outcome_type = str(rule.get("outcome_type", "")).upper()
    elif hasattr(rule, "outcome_type"):
        outcome_type = str(getattr(rule, "outcome_type", "")).upper()

    # Check for UNSUPPORTED / NON_COMPILABLE status
    v_status = ""
    if isinstance(verification, dict):
        v_status = str(verification.get("status", "")).upper()
    elif hasattr(verification, "status"):
        v_status = str(verification.status).upper()

    if not outcome_type or outcome_type == "STANDARD":
        if v_status == "CONDITIONAL_RULE":
            outcome_type = "CONDITIONAL_RULE"

    if v_status in ("NON_COMPILABLE", "UNSUPPORTED"):
        return EvaluationResult(
            status=OutcomeStatus.UNSUPPORTED,
            rule_id=rule_id,
            missing_fields=[],
            evaluation_trace=[],
            temporal_status=None,
            reason="Clause marked NON_COMPILABLE or UNSUPPORTED; no deterministic rule exists.",
        )

    # Determine evaluation date (argument takes priority over profile.as_at_date)
    target_date = as_at_date
    if target_date is None:
        if isinstance(profile, dict):
            target_date = profile.get("as_at_date")
        elif hasattr(profile, "as_at_date"):
            target_date = profile.as_at_date

    # Evaluate temporal validity
    is_temporally_valid, temporal_status, temporal_reason = evaluate_temporal_validity(
        validity, target_date
    )

    evaluation_trace: List[Dict[str, Any]] = []
    missing_fields_set: List[str] = []

    # Extract conditions from applies_if
    all_conds = []
    any_conds = []
    if isinstance(applies_if, dict):
        all_conds = applies_if.get("all") or []
        any_conds = applies_if.get("any") or []
    elif applies_if:
        all_conds = applies_if.all or []
        any_conds = applies_if.any or []

    # Evaluate AND block (all)
    all_state = TriState.TRUE
    if all_conds:
        all_results: List[TriState] = []
        all_unknown_fields: List[str] = []

        for cond in all_conds:
            res, obs_val, missing_field = evaluate_single_condition(cond, profile)
            f_name = cond.get("field", "") if isinstance(cond, dict) else cond.field
            op_name = cond.get("op", "") if isinstance(cond, dict) else cond.op
            val_target = cond.get("value") if isinstance(cond, dict) else cond.value

            evaluation_trace.append({
                "field": f_name,
                "op": op_name,
                "target_value": val_target,
                "observed_value": obs_val,
                "result": res.value,
                "block": "all",
            })
            all_results.append(res)
            if res == TriState.UNKNOWN and missing_field:
                all_unknown_fields.append(missing_field)

        # Kleene AND evaluation:
        # FALSE if any is FALSE; UNKNOWN if no FALSE but at least one UNKNOWN; TRUE if all TRUE
        if any(r == TriState.FALSE for r in all_results):
            all_state = TriState.FALSE
        elif any(r == TriState.UNKNOWN for r in all_results):
            all_state = TriState.UNKNOWN
            # Only add to missing fields if not short-circuited by FALSE
            for uf in all_unknown_fields:
                if uf not in missing_fields_set:
                    missing_fields_set.append(uf)
        else:
            all_state = TriState.TRUE

    # Evaluate OR block (any)
    any_state = TriState.TRUE
    if any_conds:
        any_results: List[TriState] = []
        any_unknown_fields: List[str] = []

        for cond in any_conds:
            res, obs_val, missing_field = evaluate_single_condition(cond, profile)
            f_name = cond.get("field", "") if isinstance(cond, dict) else cond.field
            op_name = cond.get("op", "") if isinstance(cond, dict) else cond.op
            val_target = cond.get("value") if isinstance(cond, dict) else cond.value

            evaluation_trace.append({
                "field": f_name,
                "op": op_name,
                "target_value": val_target,
                "observed_value": obs_val,
                "result": res.value,
                "block": "any",
            })
            any_results.append(res)
            if res == TriState.UNKNOWN and missing_field:
                any_unknown_fields.append(missing_field)

        # Kleene OR evaluation:
        # TRUE if any is TRUE; UNKNOWN if no TRUE but at least one UNKNOWN; FALSE if all FALSE
        if any(r == TriState.TRUE for r in any_results):
            any_state = TriState.TRUE
        elif any(r == TriState.UNKNOWN for r in any_results):
            any_state = TriState.UNKNOWN
            for uf in any_unknown_fields:
                if uf not in missing_fields_set:
                    missing_fields_set.append(uf)
        else:
            any_state = TriState.FALSE

    # Combine all and any blocks (AND conjunction)
    if all_conds and any_conds:
        if all_state == TriState.FALSE or any_state == TriState.FALSE:
            conditions_state = TriState.FALSE
        elif all_state == TriState.UNKNOWN or any_state == TriState.UNKNOWN:
            conditions_state = TriState.UNKNOWN
        else:
            conditions_state = TriState.TRUE
    elif all_conds:
        conditions_state = all_state
    elif any_conds:
        conditions_state = any_state
    else:
        # Universal rule with no conditions
        conditions_state = TriState.TRUE

    # Evaluate exceptions if present
    exception_triggered = False
    exception_unknown = False
    if exceptions:
        for exc in exceptions:
            res, obs_val, missing_field = evaluate_single_condition(exc, profile)
            f_name = exc.get("field", "") if isinstance(exc, dict) else exc.field
            op_name = exc.get("op", "") if isinstance(exc, dict) else exc.op
            val_target = exc.get("value") if isinstance(exc, dict) else exc.value

            evaluation_trace.append({
                "field": f_name,
                "op": op_name,
                "target_value": val_target,
                "observed_value": obs_val,
                "result": res.value,
                "block": "exceptions",
            })

            if res == TriState.TRUE:
                exception_triggered = True
                break
            elif res == TriState.UNKNOWN:
                exception_unknown = True
                if missing_field and missing_field not in missing_fields_set:
                    missing_fields_set.append(missing_field)

    # If not temporally valid: rule is NOT_APPLICABLE regardless of profile conditions
    if not is_temporally_valid:
        cfs = generate_counterfactuals(evaluation_trace, OutcomeStatus.NOT_APPLICABLE)
        return EvaluationResult(
            status=OutcomeStatus.NOT_APPLICABLE,
            rule_id=rule_id,
            missing_fields=[],
            evaluation_trace=evaluation_trace,
            temporal_status=temporal_status,
            reason=temporal_reason,
            counterfactuals=cfs,
        )

    # If an exception condition is satisfied -> NOT_APPLICABLE
    if exception_triggered:
        cfs = generate_counterfactuals(evaluation_trace, OutcomeStatus.NOT_APPLICABLE)
        return EvaluationResult(
            status=OutcomeStatus.NOT_APPLICABLE,
            rule_id=rule_id,
            missing_fields=[],
            evaluation_trace=evaluation_trace,
            temporal_status=temporal_status,
            reason="Rule exception condition met.",
            counterfactuals=cfs,
        )

    # Resolve outcome based on 3-valued condition status
    if conditions_state == TriState.FALSE:
        cfs = generate_counterfactuals(evaluation_trace, OutcomeStatus.NOT_APPLICABLE)
        return EvaluationResult(
            status=OutcomeStatus.NOT_APPLICABLE,
            rule_id=rule_id,
            missing_fields=[],
            evaluation_trace=evaluation_trace,
            temporal_status=temporal_status,
            reason="Rule applicability conditions not satisfied.",
            counterfactuals=cfs,
        )
    elif conditions_state == TriState.UNKNOWN or (conditions_state == TriState.TRUE and exception_unknown):
        return EvaluationResult(
            status=OutcomeStatus.CONDITIONAL_MISSING_DATA,
            rule_id=rule_id,
            missing_fields=missing_fields_set,
            evaluation_trace=evaluation_trace,
            temporal_status=temporal_status,
            reason="Outcome depends on unknown business profile fields.",
            counterfactuals=[],
        )
    else:  # conditions_state == TriState.TRUE and not exception_triggered and not exception_unknown
        if outcome_type == "CONDITIONAL_RULE":
            return EvaluationResult(
                status=OutcomeStatus.CONDITIONAL_RULE,
                rule_id=rule_id,
                missing_fields=[],
                evaluation_trace=evaluation_trace,
                temporal_status=temporal_status,
                reason="Statutory conditions met, but rule imposes external administrative/conditional compliance requirements.",
                counterfactuals=[],
            )
        else:
            cfs = generate_counterfactuals(evaluation_trace, OutcomeStatus.APPLICABLE)
            return EvaluationResult(
                status=OutcomeStatus.APPLICABLE,
                rule_id=rule_id,
                missing_fields=[],
                evaluation_trace=evaluation_trace,
                temporal_status=temporal_status,
                reason="All applicability conditions satisfied and rule is currently in force.",
                counterfactuals=cfs,
            )


def format_field_metadata(field: str) -> Tuple[str, str]:
    """Return (display_name, unit_string) for a field path."""
    if field == "production_capacity.kg_per_day":
        return "production capacity", " kg/day"
    if field == "production_capacity.value":
        return "production capacity", ""
    if field == "employee_count":
        return "employee count", ""
    if field == "products.prepackaged":
        return "products", ""

    clean_name = field.split(".")[-1].replace("_", " ")
    return clean_name, ""


def format_numeric_counterfactual(
    field_display: str,
    unit: str,
    op: str,
    target_val: Any,
    status: OutcomeStatus,
) -> Optional[str]:
    """Generate threshold counterfactual for numeric condition."""
    try:
        val_float = float(target_val)
        val_str = str(int(val_float)) if val_float.is_integer() else str(val_float)
    except (ValueError, TypeError):
        val_str = str(target_val)

    if status == OutcomeStatus.APPLICABLE:
        if op == "gte":
            return f"If {field_display} were below {val_str}{unit}, this obligation would not apply."
        elif op == "gt":
            return f"If {field_display} were {val_str}{unit} or below, this obligation would not apply."
        elif op == "lte":
            return f"If {field_display} were above {val_str}{unit}, this obligation would not apply."
        elif op == "lt":
            return f"If {field_display} were {val_str}{unit} or above, this obligation would not apply."
    elif status == OutcomeStatus.NOT_APPLICABLE:
        if op == "gte":
            return f"If {field_display} were {val_str}{unit} or greater, this obligation would apply."
        elif op == "gt":
            return f"If {field_display} were greater than {val_str}{unit}, this obligation would apply."
        elif op == "lte":
            return f"If {field_display} were {val_str}{unit} or below, this obligation would apply."
        elif op == "lt":
            return f"If {field_display} were below {val_str}{unit}, this obligation would apply."
    return None


def format_boolean_counterfactual(
    field: str,
    field_display: str,
    target_val: bool,
    status: OutcomeStatus,
) -> Optional[str]:
    """Generate counterfactual for boolean condition."""
    if field == "products.prepackaged":
        if target_val is True:
            if status == OutcomeStatus.APPLICABLE:
                return "If products were not prepackaged, this obligation would not apply."
            else:
                return "If products were prepackaged, this obligation would apply."
        else:
            if status == OutcomeStatus.APPLICABLE:
                return "If products were prepackaged, this obligation would not apply."
            else:
                return "If products were not prepackaged, this obligation would apply."

    if status == OutcomeStatus.APPLICABLE:
        inverted = not target_val
        return f"If {field} were {inverted}, this obligation would not apply."
    else:
        return f"If {field} were {target_val}, this obligation would apply."


def generate_counterfactuals(
    evaluation_trace_or_rule: Any,
    status_or_result: Any = None,
    profile: Optional[Any] = None,
) -> List[str]:
    """Generate counterfactual explanations for decisive conditions.
    
    Supports both signatures:
    - generate_counterfactuals(evaluation_trace, status)
    - generate_counterfactuals(rule, evaluation_result, profile)
    """
    if isinstance(evaluation_trace_or_rule, list):
        evaluation_trace = evaluation_trace_or_rule
        status = status_or_result
    elif hasattr(status_or_result, "evaluation_trace") and hasattr(status_or_result, "status"):
        evaluation_trace = status_or_result.evaluation_trace
        status = status_or_result.status
    else:
        return []

    if status not in (OutcomeStatus.APPLICABLE, OutcomeStatus.NOT_APPLICABLE):
        return []

    counterfactuals: List[str] = []

    for entry in evaluation_trace:
        field = entry.get("field", "")
        op = entry.get("op", "")
        target_val = entry.get("target_value")
        result = entry.get("result")

        # In APPLICABLE: conditions that evaluated to TRUE are decisive in conjunction
        # In NOT_APPLICABLE: conditions that evaluated to FALSE are decisive
        is_decisive = (status == OutcomeStatus.APPLICABLE and result == "TRUE") or \
                      (status == OutcomeStatus.NOT_APPLICABLE and result == "FALSE")

        if not is_decisive:
            continue

        field_display, unit = format_field_metadata(field)

        # 1. Numerical / ordinal conditions
        if op in ("gt", "gte", "lt", "lte"):
            cf = format_numeric_counterfactual(
                field_display=field_display,
                unit=unit,
                op=op,
                target_val=target_val,
                status=status,
            )
            if cf and cf not in counterfactuals:
                counterfactuals.append(cf)

        # 2. Boolean flag conditions
        elif op in ("eq", "==") and (isinstance(target_val, bool) or str(target_val).lower() in ("true", "false")):
            target_bool = bool(target_val) if isinstance(target_val, bool) else (str(target_val).lower() == "true")
            cf = format_boolean_counterfactual(
                field=field,
                field_display=field_display,
                target_val=target_bool,
                status=status,
            )
            if cf and cf not in counterfactuals:
                counterfactuals.append(cf)

    return counterfactuals


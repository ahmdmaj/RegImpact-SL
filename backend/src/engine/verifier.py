"""Component [E]: The Verification Pipeline for RegImpact-SL.

Validates candidate compiled rules against source clause text and metadata:
- Stage 1: Schema & Type Validation (Pydantic model, valid operators, dates, provenance)
- Stage 2: Quote-Span Grounding (verbatim/normalized match in source text)
- Stage 3: Literal Check (thresholds, units, dates present in quote_span)
- Stage 4: Non-Compilable Handling (justification reason, no half-baked logic)
"""

from datetime import date
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from backend.src.engine.applicability import parse_date
from backend.src.models.domain import (
    Condition,
    Rule,
    VerificationIssue,
    VerificationReport,
)

# Supported condition comparison operators
SUPPORTED_OPERATORS: Set[str] = {
    "eq",
    "neq",
    "gt",
    "gte",
    "lt",
    "lte",
    "in",
    "contains",
    "==",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
}

# Number words mapping for English gazettes
NUMBER_WORDS: Dict[int, str] = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    12: "twelve",
    15: "fifteen",
    20: "twenty",
    25: "twenty-five",
    30: "thirty",
    50: "fifty",
    100: "hundred",
    500: "five hundred",
    1000: "thousand",
}

# Unit dictionary with common natural language equivalents
UNIT_EQUIVALENTS: Dict[str, List[str]] = {
    "kg": ["kg", "kgs", "kilogram", "kilograms", "kilo", "kilos"],
    "g": ["g", "gm", "gms", "gram", "grams"],
    "l": ["l", "ltr", "litre", "litres", "liter", "liters"],
    "mt": ["mt", "ton", "tons", "tonne", "tonnes", "metric ton", "metric tons"],
    "day": ["day", "daily", "per day", "a day"],
    "month": ["month", "monthly", "per month", "a month"],
    "year": ["year", "annually", "annual", "per annum", "per year", "a year"],
}


def normalize_text(text: Optional[str]) -> str:
    """Normalize text for whitespace, casing, quotes, and punctuation resiliency."""
    if not text:
        return ""
    # Normalize unicode quotes, dashes, ellipses
    t = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    t = t.replace("–", "-").replace("—", "-").replace("…", "...")
    # Normalize all whitespace (including newlines, tabs, non-breaking spaces) to single space
    t = re.sub(r"[\s\u00a0]+", " ", t)
    return t.strip()


def get_date_equivalents(d: date) -> List[str]:
    """Generate direct natural language equivalent strings for a date object."""
    year = str(d.year)
    month_num = str(d.month)
    month_padded = f"{d.month:02d}"
    day_num = str(d.day)
    day_padded = f"{d.day:02d}"

    months = [
        "",
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    ]
    m_full = months[d.month]
    m_short = m_full[:3]

    ordinals = {1: "1st", 2: "2nd", 3: "3rd", 21: "21st", 22: "22nd", 23: "23rd", 31: "31st"}
    d_ord = ordinals.get(d.day, f"{d.day}th")
    word_ordinals = {1: "first", 2: "second", 3: "third"}
    w_ord = word_ordinals.get(d.day, d_ord)

    variants = [
        # ISO / standard numeric
        f"{year}-{month_padded}-{day_padded}",
        f"{year}/{month_padded}/{day_padded}",
        f"{day_padded}-{month_padded}-{year}",
        f"{day_padded}/{month_padded}/{year}",
        f"{day_padded}.{month_padded}.{year}",
        f"{day_num}/{month_num}/{year}",
        # Day-first textual (common in Sri Lankan / British legal drafting)
        f"{d_ord} {m_full} {year}",
        f"{d_ord} of {m_full} {year}",
        f"{d_ord} of {m_full}, {year}",
        f"{d_ord} day of {m_full} {year}",
        f"{d_ord} day of {m_full}, {year}",
        f"{w_ord} day of {m_full} {year}",
        f"{day_num} {m_full} {year}",
        f"{day_padded} {m_full} {year}",
        f"{day_num} {m_short} {year}",
        f"{d_ord} {m_short} {year}",
        # Month-first textual
        f"{m_full} {day_num}, {year}",
        f"{m_full} {day_num} {year}",
        f"{m_full} {d_ord}, {year}",
        f"{m_full} {d_ord} {year}",
        f"{m_short} {day_num}, {year}",
        f"{m_short} {day_num} {year}",
        f"{m_short} {d_ord}, {year}",
    ]
    return [v.lower() for v in variants]


def date_in_text(date_val: Union[str, date], text: str) -> bool:
    """Check if a date appears verbatim or in direct equivalent form in text."""
    parsed = parse_date(date_val)
    norm_text = normalize_text(text).lower()
    if parsed is not None:
        variants = get_date_equivalents(parsed)
        for v in variants:
            if v in norm_text:
                return True
        return False
    # If not parseable as date, check verbatim string
    return str(date_val).strip().lower() in norm_text


def number_in_text(val: Union[int, float], text: str) -> bool:
    """Check if a numeric threshold appears as a distinct number/token in text."""
    norm_text = normalize_text(text).lower()
    variants: List[str] = []

    try:
        val_float = float(val)
        if val_float.is_integer():
            int_val = int(val_float)
            variants.append(str(int_val))
            variants.append(f"{val_float:.1f}")
            if int_val in NUMBER_WORDS:
                variants.append(NUMBER_WORDS[int_val])
        else:
            variants.append(str(val))
    except (ValueError, TypeError):
        variants.append(str(val))

    for v in variants:
        # Use digit-boundary assertion to avoid partial matches (e.g., 50 inside 150)
        pattern = rf"(?<!\d){re.escape(v)}(?!\d)"
        if re.search(pattern, norm_text):
            return True
    return False


def unit_in_text(unit_key: str, text: str) -> bool:
    """Check if a measurement unit appears in text in equivalent form."""
    norm_text = normalize_text(text).lower()
    variants = UNIT_EQUIVALENTS.get(unit_key.lower(), [unit_key.lower()])
    for v in variants:
        if re.search(rf"\b{re.escape(v)}\b", norm_text):
            return True
    return False


class RuleVerifier:
    """Verification pipeline validating candidate rules against official source text."""

    def verify(
        self,
        rule: Union[Rule, Dict[str, Any]],
        source_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VerificationReport:
        """Run all verification stages on a candidate rule.
        
        Stages:
        1. Schema & Type Validation
        2. Quote-Span Grounding
        3. Literal Check
        4. Non-Compilable Handling
        """
        issues: List[VerificationIssue] = []

        # Stage 1: Pydantic parsing / basic schema check
        rule_obj: Optional[Rule] = None
        if isinstance(rule, Rule):
            rule_obj = rule
        elif isinstance(rule, dict):
            try:
                rule_obj = Rule(**rule)
            except Exception as e:
                issues.append(
                    VerificationIssue(
                        stage="schema",
                        severity="error",
                        message=f"Pydantic schema validation error: {str(e)}",
                    )
                )
                return VerificationReport(
                    is_valid=False,
                    issues=issues,
                    status="rejected",
                )
        else:
            issues.append(
                VerificationIssue(
                    stage="schema",
                    severity="error",
                    message="Candidate rule must be an instance of Rule or dict.",
                )
            )
            return VerificationReport(
                is_valid=False,
                issues=issues,
                status="rejected",
            )

        # Stage 4 check: Is this rule explicitly marked NON_COMPILABLE / UNSUPPORTED?
        status_val = str(rule_obj.verification.status).strip().upper()
        is_non_compilable = status_val in ("NON_COMPILABLE", "UNSUPPORTED")

        # Stage 1 detailed checks
        schema_issues = self.verify_schema(rule_obj, is_non_compilable)
        issues.extend(schema_issues)

        # Stage 2: Quote-Span Grounding
        grounding_issues = self.verify_quote_grounding(rule_obj, source_text)
        issues.extend(grounding_issues)

        # If non-compilable, evaluate Stage 4 requirements
        if is_non_compilable:
            non_comp_issues = self.verify_non_compilable(rule_obj)
            issues.extend(non_comp_issues)

            has_errors = any(i.severity == "error" for i in issues)
            return VerificationReport(
                is_valid=not has_errors,
                issues=issues,
                status="non_compilable" if not has_errors else "rejected",
            )

        # Stage 3: Literal Check (for standard compilable rules)
        literal_issues = self.verify_literals(rule_obj)
        issues.extend(literal_issues)

        has_errors = any(i.severity == "error" for i in issues)
        return VerificationReport(
            is_valid=not has_errors,
            issues=issues,
            status="verified" if not has_errors else "rejected",
        )

    def verify_schema(self, rule: Rule, is_non_compilable: bool = False) -> List[VerificationIssue]:
        """Stage 1: Validate schema, provenance, operators, and dates."""
        issues: List[VerificationIssue] = []

        # Provenance checks
        src = rule.source
        if not src.instrument or not src.instrument.strip():
            issues.append(VerificationIssue(stage="schema", severity="error", message="Missing source.instrument."))
        if not src.authority or not src.authority.strip():
            issues.append(VerificationIssue(stage="schema", severity="error", message="Missing source.authority."))
        if not src.gazette_no or not src.gazette_no.strip():
            issues.append(VerificationIssue(stage="schema", severity="error", message="Missing source.gazette_no."))
        if not src.clause or not src.clause.strip():
            issues.append(VerificationIssue(stage="schema", severity="error", message="Missing source.clause."))
        if src.page is None or src.page < 0:
            issues.append(VerificationIssue(stage="schema", severity="error", message="Invalid source.page number."))
        if not src.quote_span or not src.quote_span.strip():
            issues.append(VerificationIssue(stage="schema", severity="error", message="Missing source.quote_span."))

        # Date format checks in validity
        val = rule.validity
        if not is_non_compilable:
            if not val.published or parse_date(val.published) is None:
                issues.append(VerificationIssue(stage="schema", severity="error", message=f"Invalid date format in validity.published: '{val.published}'."))
            if not val.commences or parse_date(val.commences) is None:
                issues.append(VerificationIssue(stage="schema", severity="error", message=f"Invalid date format in validity.commences: '{val.commences}'."))
            if val.transition_until and parse_date(val.transition_until) is None:
                issues.append(VerificationIssue(stage="schema", severity="error", message=f"Invalid date format in validity.transition_until: '{val.transition_until}'."))
            if val.superseded_date and parse_date(val.superseded_date) is None:
                issues.append(VerificationIssue(stage="schema", severity="error", message=f"Invalid date format in validity.superseded_date: '{val.superseded_date}'."))

        # Supported condition comparison operators check
        all_conds: List[Condition] = []
        if rule.applies_if:
            all_conds.extend(rule.applies_if.all or [])
            all_conds.extend(rule.applies_if.any or [])

        for cond in all_conds:
            if not cond.field or not cond.field.strip():
                issues.append(VerificationIssue(stage="schema", severity="error", message="Condition missing 'field' path."))
            op_norm = cond.op.strip().lower()
            if op_norm not in SUPPORTED_OPERATORS:
                issues.append(
                    VerificationIssue(
                        stage="schema",
                        severity="error",
                        message=f"Unsupported operator '{cond.op}' in condition for field '{cond.field}'.",
                    )
                )

        return issues

    def verify_quote_grounding(self, rule: Rule, source_text: Optional[str]) -> List[VerificationIssue]:
        """Stage 2: Verify that quote_span exists verbatim (normalized) within source text."""
        issues: List[VerificationIssue] = []
        quote = rule.source.quote_span

        if not quote or not quote.strip():
            issues.append(
                VerificationIssue(
                    stage="quote_grounding",
                    severity="error",
                    message="quote_span is empty; cannot ground in source text.",
                )
            )
            return issues

        if source_text is None:
            issues.append(
                VerificationIssue(
                    stage="quote_grounding",
                    severity="error",
                    message="source_text was not provided; cannot verify quote grounding.",
                )
            )
            return issues

        norm_quote = normalize_text(quote).lower()
        norm_source = normalize_text(source_text).lower()

        if norm_quote not in norm_source:
            issues.append(
                VerificationIssue(
                    stage="quote_grounding",
                    severity="error",
                    message="quote_span does not exist verbatim within the provided source text.",
                )
            )

        return issues

    def verify_literals(self, rule: Rule) -> List[VerificationIssue]:
        """Stage 3: Verify that every numeric literal, unit, and date exists in quote_span."""
        issues: List[VerificationIssue] = []
        quote = rule.source.quote_span or ""

        # 1. Condition literals and units
        all_conds: List[Condition] = []
        if rule.applies_if:
            all_conds.extend(rule.applies_if.all or [])
            all_conds.extend(rule.applies_if.any or [])

        for cond in all_conds:
            val = cond.value
            field = cond.field

            # Numeric literal checks
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                if not number_in_text(val, quote):
                    issues.append(
                        VerificationIssue(
                            stage="literal_check",
                            severity="error",
                            message=f"Numeric threshold '{val}' from condition '{field}' does not appear in quote_span.",
                        )
                    )
            elif isinstance(val, str):
                # Check if value is a date
                parsed_val_date = parse_date(val)
                if parsed_val_date is not None and len(val.strip()) >= 8:
                    if not date_in_text(parsed_val_date, quote):
                        issues.append(
                            VerificationIssue(
                                stage="literal_check",
                                severity="error",
                                message=f"Date literal '{val}' from condition '{field}' does not appear in quote_span.",
                            )
                        )
                else:
                    # Check if string contains numeric literals (e.g., '50 kg')
                    numbers = re.findall(r"\d+(?:\.\d+)?", val)
                    for num_str in numbers:
                        num_val = float(num_str) if "." in num_str else int(num_str)
                        if not number_in_text(num_val, quote):
                            issues.append(
                                VerificationIssue(
                                    stage="literal_check",
                                    severity="error",
                                    message=f"Numeric literal '{num_str}' from condition value '{val}' does not appear in quote_span.",
                                )
                            )

            # Unit checks derived from field path (e.g. production_capacity.kg_per_day)
            field_tokens = field.lower().replace(".", "_").split("_")
            for token in field_tokens:
                if token in UNIT_EQUIVALENTS:
                    if not unit_in_text(token, quote):
                        issues.append(
                            VerificationIssue(
                                stage="literal_check",
                                severity="error",
                                message=f"Unit '{token}' required by condition field '{field}' does not appear in quote_span.",
                            )
                        )

        # 2. Validity date literals
        val = rule.validity
        dates_to_check: List[Tuple[str, Optional[str]]] = [
            ("commences", val.commences),
            ("published", val.published),
            ("transition_until", val.transition_until),
            ("superseded_date", val.superseded_date),
        ]

        for field_name, d_str in dates_to_check:
            if d_str and d_str.strip():
                if not date_in_text(d_str, quote):
                    issues.append(
                        VerificationIssue(
                            stage="literal_check",
                            severity="error",
                            message=f"Date '{d_str}' in validity.{field_name} does not appear in quote_span.",
                        )
                    )

        return issues

    def verify_non_compilable(self, rule: Rule) -> List[VerificationIssue]:
        """Stage 4: Verify that NON_COMPILABLE rules have justification and no half-baked logic."""
        issues: List[VerificationIssue] = []

        # Check for justification reason
        v = rule.verification
        reason = getattr(v, "reason", None) or getattr(v, "justification", None)
        if not reason and hasattr(v, "model_extra") and v.model_extra:
            reason = v.model_extra.get("reason") or v.model_extra.get("justification")
        if not reason and getattr(rule, "reason", None):
            reason = getattr(rule, "reason")
        if not reason and rule.obligation and rule.obligation.text:
            reason = rule.obligation.text

        if not reason or not str(reason).strip():
            issues.append(
                VerificationIssue(
                    stage="schema",
                    severity="error",
                    message="NON_COMPILABLE marker must contain a justification reason explaining why clause cannot be compiled.",
                )
            )

        # Check for half-baked rule logic (cannot have active conditions)
        has_conditions = False
        if rule.applies_if:
            if rule.applies_if.all and len(rule.applies_if.all) > 0:
                has_conditions = True
            if rule.applies_if.any and len(rule.applies_if.any) > 0:
                has_conditions = True

        if has_conditions:
            issues.append(
                VerificationIssue(
                    stage="consistency",
                    severity="error",
                    message="NON_COMPILABLE clause cannot contain executable conditions in applies_if. Non-compilable clauses must not contain partial condition trees.",
                )
            )

        return issues


def verify_rule(
    rule: Union[Rule, Dict[str, Any]],
    source_text: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> VerificationReport:
    """Convenience functional wrapper for RuleVerifier."""
    verifier = RuleVerifier()
    return verifier.verify(rule, source_text, metadata)

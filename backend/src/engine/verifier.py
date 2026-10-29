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
    # Normalize typography and Sri Lankan Government Gazette PUA font ligatures
    t = t.replace("\ue055", "ff").replace("\ue056", "ffi").replace("\ue04f", "fi").replace("\ue050", "fl")
    t = t.replace("\ufb00", "ff").replace("\ufb01", "fi").replace("\ufb02", "fl").replace("\ufb03", "ffi").replace("\ufb04", "ffl")
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


def extract_dates_from_text(text: str) -> List[date]:
    """Extract explicit calendar dates from natural language text."""
    if not text:
        return []
    found_dates: List[date] = []

    # 1. ISO format: YYYY-MM-DD
    for m in re.finditer(r"\b\d{4}-\d{2}-\d{2}\b", text):
        d = parse_date(m.group(0))
        if d and d not in found_dates:
            found_dates.append(d)

    # 2. Commonwealth / natural textual dates (e.g. 1st June 2024, 01st July 2026, June 1, 2024)
    textual_pattern = (
        r"\b(?:\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})"
        r"|(?:\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?(?:,)?\s+\d{4})"
    )
    for m in re.finditer(textual_pattern, text, re.IGNORECASE):
        d = parse_date(m.group(0))
        if d and d not in found_dates:
            found_dates.append(d)

    # 3. Numeric formats: DD/MM/YYYY or DD-MM-YYYY
    numeric_pattern = r"\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4}\b"
    for m in re.finditer(numeric_pattern, text):
        d = parse_date(m.group(0))
        if d and d not in found_dates:
            found_dates.append(d)

    return found_dates


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
        # Match standalone word (\bkg\b) or attached to number/punct (12.0g, 50kg, 100ml)
        pattern = rf"(?:(?<=[0-9\s\.\,/])|^){re.escape(v)}(?=[^a-zA-Z]|$)"
        if re.search(pattern, norm_text):
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
        grounding_issues = self.verify_quote_grounding(rule_obj, source_text, metadata=metadata)
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
        literal_issues = self.verify_literals(rule_obj, source_text=source_text, metadata=metadata)
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

    def verify_quote_grounding(
        self,
        rule: Rule,
        source_text: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[VerificationIssue]:
        """Stage 2: Verify that substantive obligation quote, threshold quotes, and exceptions quotes exist verbatim."""
        issues: List[VerificationIssue] = []
        src = rule.source
        meta_dict = metadata or {}
        context_evidence = meta_dict.get("context_evidence") or {}
        reg1_text = meta_dict.get("regulation_1_text") or context_evidence.get("regulation_1") or ""
        preamble_text = meta_dict.get("preamble_text") or context_evidence.get("preamble") or ""

        # 1. Ground substantive obligation quote in source clause text
        obl_quote = (
            getattr(src, "obligation_quote", None)
            or (getattr(src.evidence, "obligation_quote", None) if getattr(src, "evidence", None) else None)
            or src.quote_span
        )

        if not obl_quote or not obl_quote.strip():
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

        norm_quote = normalize_text(obl_quote).lower()
        norm_source = normalize_text(source_text).lower()

        if norm_quote not in norm_source:
            issues.append(
                VerificationIssue(
                    stage="quote_grounding",
                    severity="error",
                    message="quote_span does not exist verbatim within the provided source text.",
                )
            )

        # 2. Ground separate commencement quote in documented contextual evidence
        comm_quote = (
            getattr(src, "commencement_quote", None)
            or (getattr(src.evidence, "commencement_quote", None) if getattr(src, "evidence", None) else None)
            or getattr(rule.validity, "evidence_quote", None)
        )
        if comm_quote and comm_quote.strip():
            context_sources_all = f"{reg1_text} {preamble_text} {source_text or ''}".strip()
            if context_sources_all:
                if normalize_text(comm_quote).lower() not in normalize_text(context_sources_all).lower():
                    issues.append(
                        VerificationIssue(
                            stage="quote_grounding",
                            severity="error",
                            message=(
                                f"commencement_quote '{comm_quote}' does not exist verbatim "
                                "within documented contextual evidence (Regulation 1, preamble, or source text)."
                            ),
                        )
                    )

        # 3. Ground separate threshold quotes in source clause text
        threshold_quotes = (
            getattr(src, "threshold_quotes", None)
            or (getattr(src.evidence, "threshold_quotes", None) if getattr(src, "evidence", None) else None)
            or {}
        )
        if isinstance(threshold_quotes, dict):
            for t_field, t_quote in threshold_quotes.items():
                if t_quote and t_quote.strip():
                    if normalize_text(t_quote).lower() not in norm_source:
                        issues.append(
                            VerificationIssue(
                                stage="quote_grounding",
                                severity="error",
                                message=(
                                    f"threshold_quote for '{t_field}' ('{t_quote}') does not exist verbatim "
                                    "within the source clause text."
                                ),
                            )
                        )

        # 4. Ground separate exceptions quote in source clause text
        exc_quote = (
            getattr(src, "exceptions_quote", None)
            or (getattr(src.evidence, "exceptions_quote", None) if getattr(src, "evidence", None) else None)
        )
        if exc_quote and exc_quote.strip():
            if normalize_text(exc_quote).lower() not in norm_source:
                issues.append(
                    VerificationIssue(
                        stage="quote_grounding",
                        severity="error",
                        message=(
                            f"exceptions_quote ('{exc_quote}') does not exist verbatim "
                            "within the source clause text."
                        ),
                    )
                )

        return issues

    def verify_literals(
        self,
        rule: Rule,
        source_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[VerificationIssue]:
        """Stage 3: Verify that every numeric literal, unit, exception, and date is grounded in evidence."""
        issues: List[VerificationIssue] = []
        src = rule.source
        quote = (
            getattr(src, "obligation_quote", None)
            or (getattr(src.evidence, "obligation_quote", None) if getattr(src, "evidence", None) else None)
            or src.quote_span
            or ""
        )

        meta_dict = metadata or {}
        context_evidence = meta_dict.get("context_evidence") or {}
        reg1_text = meta_dict.get("regulation_1_text") or context_evidence.get("regulation_1") or ""
        preamble_text = meta_dict.get("preamble_text") or context_evidence.get("preamble") or ""
        doc_commences = meta_dict.get("commences") or context_evidence.get("commences") or ""
        doc_published = meta_dict.get("published") or context_evidence.get("published") or ""

        # 1. Condition literals and units
        all_conds: List[Condition] = []
        if rule.applies_if:
            all_conds.extend(rule.applies_if.all or [])
            all_conds.extend(rule.applies_if.any or [])

        threshold_quotes = getattr(src, "threshold_quotes", None) or {}
        combined_clause_text = f"{quote} {source_text or ''}".strip()

        for cond in all_conds:
            val = cond.value
            field = cond.field
            field_quote = threshold_quotes.get(field, "")
            text_for_cond = f"{field_quote} {combined_clause_text}".strip()

            # Numeric literal checks
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                if not number_in_text(val, text_for_cond):
                    issues.append(
                        VerificationIssue(
                            stage="literal_check",
                            severity="error",
                            message=f"Numeric threshold '{val}' from condition '{field}' does not appear in quote_span.",
                        )
                    )
            elif isinstance(val, str):
                parsed_val_date = parse_date(val)
                if parsed_val_date is not None and len(val.strip()) >= 8:
                    if not date_in_text(parsed_val_date, text_for_cond):
                        issues.append(
                            VerificationIssue(
                                stage="literal_check",
                                severity="error",
                                message=f"Date literal '{val}' from condition '{field}' does not appear in quote_span.",
                            )
                        )
                else:
                    numbers = re.findall(r"\d+(?:\.\d+)?", val)
                    for num_str in numbers:
                        num_val = float(num_str) if "." in num_str else int(num_str)
                        if not number_in_text(num_val, text_for_cond):
                            issues.append(
                                VerificationIssue(
                                    stage="literal_check",
                                    severity="error",
                                    message=f"Numeric literal '{num_str}' from condition value '{val}' does not appear in quote_span.",
                                )
                            )

            # Unit checks
            field_tokens = field.lower().replace(".", "_").split("_")
            for token in field_tokens:
                if token in UNIT_EQUIVALENTS:
                    if not unit_in_text(token, text_for_cond):
                        issues.append(
                            VerificationIssue(
                                stage="literal_check",
                                severity="error",
                                message=f"Unit '{token}' required by condition field '{field}' does not appear in quote_span.",
                            )
                        )

        # 2. Exceptions check
        if rule.exceptions:
            exc_quote = (
                getattr(src, "exceptions_quote", None)
                or (getattr(src.evidence, "exceptions_quote", None) if getattr(src, "evidence", None) else None)
            )
            if exc_quote:
                if not normalize_text(exc_quote).lower() in normalize_text(source_text or "").lower():
                    issues.append(
                        VerificationIssue(
                            stage="literal_check",
                            severity="error",
                            message="Exceptions quote does not appear in the source clause text.",
                        )
                    )

        # 3. Validity date literals and contextual verification
        val = rule.validity
        meta_text = " ".join(str(v) for v in meta_dict.values())

        # (a) Published date verification
        if val.published and val.published.strip():
            pub_context = f"{combined_clause_text} {preamble_text} {doc_published} {meta_text}".strip()
            if not date_in_text(val.published, pub_context):
                issues.append(
                    VerificationIssue(
                        stage="literal_check",
                        severity="error",
                        message=f"Date '{val.published}' in validity.published does not appear in quote_span or source text.",
                    )
                )

        # (b) Commencement date verification (context-aware)
        if val.commences and val.commences.strip():
            comm_quote = (
                getattr(src, "commencement_quote", None)
                or (getattr(src.evidence, "commencement_quote", None) if getattr(src, "evidence", None) else None)
                or getattr(val, "evidence_quote", None)
            )

            # Check if commences date appears directly in the clause itself
            in_clause = date_in_text(val.commences, combined_clause_text)

            # Check documented contextual evidence
            context_sources_text = f"{reg1_text} {preamble_text} {comm_quote or ''}".strip()
            in_context = bool(context_sources_text and date_in_text(val.commences, context_sources_text))

            # Contradiction check:
            parsed_rule_d = parse_date(val.commences)
            contradiction_found = False

            # 1. Contradiction against metadata doc_commences
            if doc_commences and doc_commences.strip():
                parsed_doc_d = parse_date(doc_commences)
                if parsed_rule_d and parsed_doc_d and parsed_rule_d != parsed_doc_d:
                    contradiction_found = True
                    issues.append(
                        VerificationIssue(
                            stage="literal_check",
                            severity="error",
                            message=(
                                f"Contradictory commencement date: rule claims '{val.commences}', "
                                f"but documented evidence specifies '{doc_commences}'."
                            ),
                        )
                    )

            # 2. Contradiction against Regulation 1 text dates
            if reg1_text and reg1_text.strip():
                reg1_dates = extract_dates_from_text(reg1_text)
                if reg1_dates and parsed_rule_d and parsed_rule_d not in reg1_dates:
                    contradiction_found = True
                    doc_date_str = str(reg1_dates[0])
                    issues.append(
                        VerificationIssue(
                            stage="literal_check",
                            severity="error",
                            message=(
                                f"Contradictory commencement date: rule claims '{val.commences}', "
                                f"but documented contextual evidence (Regulation 1) specifies '{doc_date_str}'."
                            ),
                        )
                    )

            # 3. Missing evidence check (ungrounded)
            if not in_clause and not in_context and not date_in_text(val.commences, meta_text):
                if not contradiction_found:
                    issues.append(
                        VerificationIssue(
                            stage="literal_check",
                            severity="error",
                            message=(
                                f"Commencement date '{val.commences}' in validity.commences is ungrounded: "
                                f"does not appear in clause text and no supporting contextual evidence was provided."
                            ),
                        )
                    )

        # Transition / superseded dates
        for field_name, d_str in [("transition_until", val.transition_until), ("superseded_date", val.superseded_date)]:
            if d_str and d_str.strip():
                all_text = f"{combined_clause_text} {reg1_text} {preamble_text} {meta_text}".strip()
                if not date_in_text(d_str, all_text):
                    issues.append(
                        VerificationIssue(
                            stage="literal_check",
                            severity="error",
                            message=f"Date '{d_str}' in validity.{field_name} does not appear in quote_span or source text.",
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

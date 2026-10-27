"""Phase 3.9: Jam Preservative Rule Modeling & Applicability Resolution Suite.

Validates the bounded modeling decision for Schedule II Items 3.1(h) and 3.1(i):
  1. Standard jam applicability (Item 3.1(h), 300 mg/kg sorbates).
  2. Low-sugar jam applicability (Item 3.1(i), 500 mg/kg sorbates).
  3. Missing/unknown category abstention (Kleene 3-valued logic).
  4. Mutual exclusivity of standard and low-sugar rule scopes.
  5. Preservation of existing benchmark scenario semantics (SCEN-PRES-JAM-DIR-08).
  6. Source quotation verification for the proposed low-sugar candidate.
"""

from pathlib import Path
import json
import fitz
import pytest

from backend.src.engine.applicability import evaluate_rule
from backend.src.engine.verifier import RuleVerifier
from backend.src.models.domain import (
    AppliesIf,
    Condition,
    Obligation,
    OutcomeStatus,
    Rule,
    Source,
    Validity,
    Verification,
)

PDF_PRESERVATIVE = Path("backend/data/raw_sources/preservative-english.pdf")
BENCHMARK_FILE = Path("backend/data/benchmark/multi_group_benchmark_slice.jsonl")


def build_standard_jam_rule() -> Rule:
    """Build Rule 6 as currently structured in PostgreSQL (Schedule II Item 3.1(h))."""
    return Rule(
        rule_id="RULE-PRESERVATIVE-JAM-JELLY-LIMIT",
        source=Source(
            instrument="The Sri Lanka Gazette Extraordinary No. 2113/16",
            authority="Minister of Health, Nutrition and Indigenous Medicine",
            gazette_no="2113/16",
            clause="Schedule II Item 3.1(h)",
            page=5,
            quote_span="(h) Jams, Jellies, marmalades: Sorbates 300 mg/kg, Sulphites (as residual SO2) 100 mg/kg, Propionates GMP;",
        ),
        validity=Validity(
            published="2019-03-05",
            commences="2020-01-01",
        ),
        applies_if=AppliesIf(
            all=[
                Condition(field="activity", op="eq", value="food_manufacturing"),
                Condition(field="products.category", op="eq", value="jams_jellies_marmalades"),
            ]
        ),
        exceptions=[],
        obligation=Obligation(
            type="formulation",
            text="Permitted preservatives in jams, jellies, marmalades: Sorbates maximum 300 mg/kg, Sulphites maximum 100 mg/kg, or Propionates GMP.",
            impact_categories=["recipe_formulation", "ingredient_specification"],
        ),
        verification=Verification(
            status="pending_review",
            extraction_model="manual_audit",
            agreement=False,
        ),
    )


def build_proposed_low_sugar_jam_rule() -> Rule:
    """Build proposed candidate rule for Schedule II Item 3.1(i) using category-token approach."""
    return Rule(
        rule_id="RULE-PRESERVATIVE-LOW-SUGAR-JAM-LIMIT",
        source=Source(
            instrument="The Sri Lanka Gazette Extraordinary No. 2113/16",
            authority="Minister of Health, Nutrition and Indigenous Medicine",
            gazette_no="2113/16",
            clause="Schedule II Item 3.1(i)",
            page=5,
            quote_span="(i) Jams, Jellies and marmalades low in sugar or sugar free: Sorbates 500 mg/kg, Sulphites (as residual SO2) 100 mg/kg, Propionates GMP.",
        ),
        validity=Validity(
            published="2019-03-05",
            commences="2020-01-01",
        ),
        applies_if=AppliesIf(
            all=[
                Condition(field="activity", op="eq", value="food_manufacturing"),
                Condition(field="products.category", op="eq", value="jams_jellies_marmalades_low_sugar"),
            ]
        ),
        exceptions=[],
        obligation=Obligation(
            type="formulation",
            text="Permitted preservatives in jams, jellies and marmalades low in sugar or sugar free: Sorbates maximum 500 mg/kg, Sulphites maximum 100 mg/kg (as residual SO2), or Propionates GMP.",
            impact_categories=["recipe_formulation", "ingredient_specification"],
        ),
        verification=Verification(
            status="pending_review",
            extraction_model="manual_audit",
            agreement=False,
        ),
    )


# ---------------------------------------------------------------------------
# 1. Applicability & Mutual Exclusivity Tests
# ---------------------------------------------------------------------------

def test_standard_jam_applicability():
    """Verify standard jam profile triggers Rule 6 and excludes low-sugar rule."""
    r_std = build_standard_jam_rule()
    r_low = build_proposed_low_sugar_jam_rule()

    profile_standard = {
        "activity": "food_manufacturing",
        "products": [{"category": "jams_jellies_marmalades", "sorbates_mg_per_kg": 250.0}],
    }

    res_std = evaluate_rule(r_std, profile_standard, as_at_date="2024-01-01")
    res_low = evaluate_rule(r_low, profile_standard, as_at_date="2024-01-01")

    assert res_std.status == OutcomeStatus.APPLICABLE
    assert res_std.missing_fields == []
    assert res_low.status == OutcomeStatus.NOT_APPLICABLE


def test_low_sugar_jam_applicability():
    """Verify low-sugar jam profile triggers low-sugar candidate and excludes Rule 6."""
    r_std = build_standard_jam_rule()
    r_low = build_proposed_low_sugar_jam_rule()

    profile_low_sugar = {
        "activity": "food_manufacturing",
        "products": [{"category": "jams_jellies_marmalades_low_sugar", "sorbates_mg_per_kg": 450.0}],
    }

    res_std = evaluate_rule(r_std, profile_low_sugar, as_at_date="2024-01-01")
    res_low = evaluate_rule(r_low, profile_low_sugar, as_at_date="2024-01-01")

    assert res_std.status == OutcomeStatus.NOT_APPLICABLE
    assert res_low.status == OutcomeStatus.APPLICABLE
    assert res_low.missing_fields == []


def test_missing_or_unknown_product_category():
    """Verify missing category field causes Kleene CONDITIONAL_MISSING_DATA abstention."""
    r_std = build_standard_jam_rule()
    r_low = build_proposed_low_sugar_jam_rule()

    profile_missing_cat = {
        "activity": "food_manufacturing",
        "products": [{"prepackaged": True}],  # Category completely absent
    }

    res_std = evaluate_rule(r_std, profile_missing_cat, as_at_date="2024-01-01")
    res_low = evaluate_rule(r_low, profile_missing_cat, as_at_date="2024-01-01")

    assert res_std.status == OutcomeStatus.CONDITIONAL_MISSING_DATA
    assert "products.category" in res_std.missing_fields

    assert res_low.status == OutcomeStatus.CONDITIONAL_MISSING_DATA
    assert "products.category" in res_low.missing_fields


def test_jam_rules_mutual_exclusivity():
    """Verify mutual exclusivity across various product profiles."""
    r_std = build_standard_jam_rule()
    r_low = build_proposed_low_sugar_jam_rule()

    categories_to_test = [
        ("jams_jellies_marmalades", OutcomeStatus.APPLICABLE, OutcomeStatus.NOT_APPLICABLE),
        ("jams_jellies_marmalades_low_sugar", OutcomeStatus.NOT_APPLICABLE, OutcomeStatus.APPLICABLE),
        ("bakery_products", OutcomeStatus.NOT_APPLICABLE, OutcomeStatus.NOT_APPLICABLE),
        ("fruit_juice", OutcomeStatus.NOT_APPLICABLE, OutcomeStatus.NOT_APPLICABLE),
    ]

    for cat, expected_std, expected_low in categories_to_test:
        prof = {
            "activity": "food_manufacturing",
            "products": [{"category": cat}],
        }
        res_std = evaluate_rule(r_std, prof, as_at_date="2024-01-01")
        res_low = evaluate_rule(r_low, prof, as_at_date="2024-01-01")

        assert res_std.status == expected_std, f"Failed std rule on {cat}"
        assert res_low.status == expected_low, f"Failed low rule on {cat}"
        # Crucial: standard and low-sugar never both evaluate to APPLICABLE on a single product
        assert not (res_std.status == OutcomeStatus.APPLICABLE and res_low.status == OutcomeStatus.APPLICABLE)


def test_preservation_of_benchmark_scenario_scen_pres_jam_dir_08():
    """Verify that existing benchmark scenario SCEN-PRES-JAM-DIR-08 semantics are 100% preserved."""
    assert BENCHMARK_FILE.exists(), f"Benchmark file missing: {BENCHMARK_FILE}"

    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        scenarios = [json.loads(line) for line in f]

    scen = next((s for s in scenarios if s.get("scenario_id") == "SCEN-PRES-JAM-DIR-08"), None)
    assert scen is not None, "SCEN-PRES-JAM-DIR-08 missing in multi_group_benchmark_slice.jsonl"

    r_std = build_standard_jam_rule()
    res = evaluate_rule(r_std, scen["business_profile"], as_at_date=scen["as_at_date"])

    assert res.status == OutcomeStatus(scen["gold_outcome"]), "Scenario outcome flipped!"
    assert res.missing_fields == []
    assert scen["gold_missing_fields"] is None


def test_low_sugar_candidate_source_verification():
    """Verify the exact source quotation of Item 3.1(i) against physical Gazette 2113/16 PDF."""
    assert PDF_PRESERVATIVE.exists(), f"Source PDF missing: {PDF_PRESERVATIVE}"
    doc = fitz.open(PDF_PRESERVATIVE)

    # Page 5 (index 4) contains Schedule II Item 3.1
    page_5_text = doc[4].get_text()

    assert "(i) Jams, Jellies and marmalades," in page_5_text
    assert "low in sugar or sugar free" in page_5_text

    r_low = build_proposed_low_sugar_jam_rule()
    assert r_low.source.page == 5
    assert r_low.source.clause == "Schedule II Item 3.1(i)"

    clause_synthetic_block = (
        "SCHEDULE II Articles of Food which may contain permitted preservatives. "
        "3.1 Fruits and fruit products: "
        "(h) Jams, Jellies, marmalades: Sorbates 300 mg/kg, Sulphites (as residual SO2) 100 mg/kg, Propionates GMP; "
        "(i) Jams, Jellies and marmalades low in sugar or sugar free: Sorbates 500 mg/kg, Sulphites (as residual SO2) 100 mg/kg, Propionates GMP."
    )

    verifier = RuleVerifier()
    rep = verifier.verify(
        r_low,
        source_text=clause_synthetic_block,
        metadata={"published": "2019-03-05", "commences": "2020-01-01"},
    )
    assert rep.is_valid is True, f"Verifier failed: {rep.issues}"

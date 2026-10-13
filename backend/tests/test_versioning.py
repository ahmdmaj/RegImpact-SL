"""Unit tests for Component [B]: Version and Amendment Model (Versioning)."""

import pytest

from backend.src.engine.versioning import (
    ClauseVersion,
    PatchError,
    PatchOperation,
    PatchType,
    apply_patch,
    apply_patches,
    create_clause_version,
)


@pytest.fixture
def base_clause_text() -> str:
    """Fixture providing a base Sri Lankan regulatory clause text."""
    return (
        "Regulation 4. Every food manufacturing enterprise having a production capacity "
        "of 50 kg per day or more, and engaged in the production of prepackaged food products, "
        "shall ensure that each retail package carries a nutrition information panel in Sinhala, "
        "Tamil, and English."
    )


# 1. Test successful substitute operation
def test_apply_patch_substitute(base_clause_text: str):
    # Substitute threshold from 50 kg to 100 kg
    patch = PatchOperation(
        patch_type=PatchType.SUBSTITUTE,
        target_text="50 kg",
        replacement_text="100 kg",
    )

    result = apply_patch(base_clause_text, patch)

    assert "100 kg per day" in result
    assert "50 kg per day" not in result
    assert result.startswith("Regulation 4.")


# 2. Test successful insert operation
def test_apply_patch_insert(base_clause_text: str):
    # Insert 'or processing' immediately after 'food manufacturing'
    patch = PatchOperation(
        patch_type=PatchType.INSERT,
        target_text="food manufacturing",
        replacement_text=" or processing",
    )

    result = apply_patch(base_clause_text, patch)

    assert "food manufacturing or processing enterprise" in result
    assert result.startswith("Regulation 4.")


# 3. Test successful omit operation
def test_apply_patch_omit(base_clause_text: str):
    # Omit ', Tamil,' from the language requirements
    patch = PatchOperation(
        patch_type=PatchType.OMIT,
        target_text=", Tamil,",
        replacement_text="",
    )

    result = apply_patch(base_clause_text, patch)

    assert ", Tamil," not in result
    assert "Sinhala and English" in result or "Sinhala, and English" in result


# 4. Test successful repeal operation
def test_apply_patch_repeal_whole_clause(base_clause_text: str):
    # Repeal whole clause with default marker
    patch = PatchOperation(
        patch_type=PatchType.REPEAL,
        target_text=None,
        replacement_text="",
    )

    result = apply_patch(base_clause_text, patch)
    assert result == "[REPEALED]"


def test_apply_patch_repeal_with_custom_replacement(base_clause_text: str):
    # Repeal with statutory placeholder text
    patch = PatchOperation(
        patch_type=PatchType.REPEAL,
        target_text=None,
        replacement_text="[Regulation 4 repealed by Gazette Extraordinary No. 2025/99]",
    )

    result = apply_patch(base_clause_text, patch)
    assert result == "[Regulation 4 repealed by Gazette Extraordinary No. 2025/99]"


def test_apply_patch_repeal_specific_target(base_clause_text: str):
    # Repeal a specific subsection within clause text
    target = "and engaged in the production of prepackaged food products,"
    patch = PatchOperation(
        patch_type=PatchType.REPEAL,
        target_text=target,
    )

    result = apply_patch(base_clause_text, patch)
    assert "[REPEALED]" in result
    assert target not in result


# 5. Strict Error Handling: Missing or misspelled target_text
def test_substitute_missing_target_raises_error(base_clause_text: str):
    patch = PatchOperation(
        patch_type=PatchType.SUBSTITUTE,
        target_text="500 kilograms",  # Misspelled / not in text
        replacement_text="1000 kilograms",
    )

    with pytest.raises(PatchError) as exc_info:
        apply_patch(base_clause_text, patch)

    assert "not found in base text" in str(exc_info.value)


def test_insert_missing_target_raises_error(base_clause_text: str):
    patch = PatchOperation(
        patch_type=PatchType.INSERT,
        target_text="beverage manufacturing",  # Missing target
        replacement_text=" or bottling",
    )

    with pytest.raises(PatchError) as exc_info:
        apply_patch(base_clause_text, patch)

    assert "not found in base text" in str(exc_info.value)


def test_omit_missing_target_raises_error(base_clause_text: str):
    patch = PatchOperation(
        patch_type=PatchType.OMIT,
        target_text="mandatory audit requirement",  # Missing target
    )

    with pytest.raises(PatchError) as exc_info:
        apply_patch(base_clause_text, patch)

    assert "not found in base text" in str(exc_info.value)


def test_empty_target_for_non_repeal_raises_error(base_clause_text: str):
    patch = PatchOperation(
        patch_type=PatchType.SUBSTITUTE,
        target_text="",
        replacement_text="some new text",
    )

    with pytest.raises(PatchError) as exc_info:
        apply_patch(base_clause_text, patch)

    assert "requires a non-empty target_text" in str(exc_info.value)


# 6. Ambiguity Safety: Multiple occurrences of target_text rejected
def test_ambiguous_patch_target_raises_error():
    repeated_text = "The manufacturer shall inspect food. The manufacturer shall package food."
    patch = PatchOperation(
        patch_type=PatchType.SUBSTITUTE,
        target_text="The manufacturer",  # Appears twice
        replacement_text="The licensed producer",
    )

    with pytest.raises(PatchError) as exc_info:
        apply_patch(repeated_text, patch)

    assert "Ambiguous patch" in str(exc_info.value)
    assert "appears 2 times" in str(exc_info.value)


# 7. Sequential patch application via apply_patches
def test_apply_patches_chain(base_clause_text: str):
    patches = [
        # Patch 1: Substitute threshold 50 kg -> 75 kg
        PatchOperation(
            patch_type=PatchType.SUBSTITUTE,
            target_text="50 kg",
            replacement_text="75 kg",
        ),
        # Patch 2: Insert category requirement
        PatchOperation(
            patch_type=PatchType.INSERT,
            target_text="prepackaged food products",
            replacement_text=" (including spices and confectionery)",
        ),
        # Patch 3: Omit 'Tamil, '
        PatchOperation(
            patch_type=PatchType.OMIT,
            target_text="Tamil, ",
            replacement_text="",
        ),
    ]

    amended = apply_patches(base_clause_text, patches)

    assert "75 kg per day" in amended
    assert "prepackaged food products (including spices and confectionery)" in amended
    assert "Tamil, " not in amended


# 8. Test ClauseVersion creation and metadata tracking
def test_create_clause_version(base_clause_text: str):
    v1 = ClauseVersion(
        clause_id="FCAU-REG-04",
        instrument="Food (Labelling) Regulations 2024",
        version_number=1,
        text=base_clause_text,
        valid_from="2024-01-01",
        valid_to="2025-01-01",
    )

    patch = PatchOperation(
        patch_type=PatchType.SUBSTITUTE,
        target_text="50 kg",
        replacement_text="100 kg",
    )

    v2 = create_clause_version(
        base_version=v1,
        new_instrument="Food (Labelling Amendment) Regulations 2025",
        new_version_number=2,
        valid_from="2025-01-01",
        patches=[patch],
    )

    assert v2.clause_id == "FCAU-REG-04"
    assert v2.version_number == 2
    assert v2.valid_from == "2025-01-01"
    assert "100 kg" in v2.text
    assert len(v2.applied_patches) == 1

"""Component [B]: The Version and Amendment Model for RegImpact-SL.

Handles textual amendments (substitute, insert, omit, repeal) to regulatory
clauses, enabling point-in-time statutory reconstruction.
"""

from typing import Any, Dict, List, Optional, Union

from backend.src.models.domain import (
    ClauseVersion,
    PatchOperation,
    PatchType,
)


class PatchError(Exception):
    """Raised when a patch operation cannot be deterministically applied."""

    pass


def apply_patch(
    base_text: str,
    operation: Union[PatchOperation, Dict[str, Any]],
) -> str:
    """Apply a single patch operation to a base clause text deterministically.
    
    Args:
        base_text: The source text of the clause before the patch.
        operation: The patch operation to apply (substitute, insert, omit, repeal).
        
    Returns:
        The amended clause text.
        
    Raises:
        PatchError: If target_text is missing from base_text or if ambiguous occurrences exist.
    """
    if isinstance(operation, dict):
        op = PatchOperation(**operation)
    else:
        op = operation

    op_type = op.patch_type
    target = op.target_text
    replacement = op.replacement_text or ""

    # 1. Repeal operation
    if op_type == PatchType.REPEAL:
        marker = replacement if replacement else "[REPEALED]"
        if target:
            if target not in base_text:
                raise PatchError(
                    f"Target text '{target}' not found in base text for repeal operation."
                )
            if base_text.count(target) > 1:
                raise PatchError(
                    f"Ambiguous patch: Target text '{target}' appears {base_text.count(target)} times in base text."
                )
            if target.strip() == base_text.strip():
                return marker
            return base_text.replace(target, marker, 1)
        return marker

    # 2. Operations requiring target_text (substitute, insert, omit)
    if not target:
        raise PatchError(
            f"Operation '{op_type.value}' requires a non-empty target_text to match."
        )

    if target not in base_text:
        raise PatchError(
            f"Target text '{target}' not found in base text for {op_type.value} operation."
        )

    if base_text.count(target) > 1:
        raise PatchError(
            f"Ambiguous patch: Target text '{target}' appears {base_text.count(target)} times in base text. "
            "Patches must target unique text spans."
        )

    # 3. Substitute operation
    if op_type == PatchType.SUBSTITUTE:
        return base_text.replace(target, replacement, 1)

    # 4. Insert operation: insert replacement_text immediately after target_text
    elif op_type == PatchType.INSERT:
        idx = base_text.find(target)
        insert_pos = idx + len(target)
        return base_text[:insert_pos] + replacement + base_text[insert_pos:]

    # 5. Omit operation: remove target_text
    elif op_type == PatchType.OMIT:
        return base_text.replace(target, "", 1)

    raise PatchError(f"Unsupported patch operation type: '{op_type}'")


def apply_patches(
    base_text: str,
    operations: List[Union[PatchOperation, Dict[str, Any]]],
) -> str:
    """Sequentially apply an ordered list of patch operations to a base clause text."""
    current_text = base_text
    for op in operations:
        current_text = apply_patch(current_text, op)
    return current_text


def create_clause_version(
    base_version: ClauseVersion,
    new_instrument: str,
    new_version_number: int,
    valid_from: str,
    patches: List[PatchOperation],
    valid_to: Optional[str] = None,
) -> ClauseVersion:
    """Construct a new ClauseVersion by applying patches to a base ClauseVersion."""
    amended_text = apply_patches(base_version.text, patches)
    return ClauseVersion(
        clause_id=base_version.clause_id,
        instrument=new_instrument,
        version_number=new_version_number,
        text=amended_text,
        valid_from=valid_from,
        valid_to=valid_to,
        applied_patches=patches,
    )

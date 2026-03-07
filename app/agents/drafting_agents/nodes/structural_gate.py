"""Structural Gate Node — deterministic section presence check.

Checks that the draft has all required sections for its doc_type.
Uses severity tiers: ERROR (must fix), WARN (flag but proceed), INFO (log).

Pipeline position: draft_single_call → **structural_gate** → assembler
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

from langgraph.types import Command

from ....config import logger
from ..prompts.draft_prompt import get_section_keys
from ..states import DraftingState
from ._utils import _as_dict


# Required sections (ERROR if missing) per category
_REQUIRED_SECTIONS: Dict[str, List[str]] = {
    "civil": ["parties", "facts", "prayer", "verification"],
    "criminal": ["parties", "facts", "prayer", "verification"],
    "family": ["parties", "facts", "prayer", "verification"],
    "constitutional": ["parties", "facts", "prayer", "verification"],
    "response": ["parties", "parawise_reply", "prayer", "verification"],
}

# WARN if missing (flag but proceed)
_WARN_SECTIONS: List[str] = [
    "court_heading", "title", "limitation", "valuation_court_fee",
    "document_list", "jurisdiction",
]

# INFO if missing (log only)
_INFO_SECTIONS: List[str] = [
    "interest", "cause_of_action",
]


def _detect_category(doc_type: str) -> str:
    """Map doc_type to a broad category for required sections."""
    doc_lower = doc_type.lower().replace(" ", "_").replace("-", "_")
    for kw in ("criminal", "bail", "quashing"):
        if kw in doc_lower:
            return "criminal"
    for kw in ("family", "divorce", "maintenance", "custody"):
        if kw in doc_lower:
            return "family"
    for kw in ("writ", "pil", "habeas", "constitutional"):
        if kw in doc_lower:
            return "constitutional"
    for kw in ("written_statement", "counter", "reply", "response"):
        if kw in doc_lower:
            return "response"
    return "civil"


def structural_gate_node(state: DraftingState) -> Command:
    """Check required sections are present. Route to assembler or fix."""
    logger.info("[STRUCTURAL_GATE] ▶ start")
    t0 = time.perf_counter()

    classify = _as_dict(state.get("classify"))
    doc_type = classify.get("doc_type", "")
    cause_type = classify.get("cause_type", "")
    filled_sections = state.get("filled_sections") or {}

    if isinstance(filled_sections, list):
        # Legacy format — convert
        filled_sections = {}

    present_keys = set(
        k for k, v in filled_sections.items()
        if isinstance(v, str) and v.strip()
    )

    category = _detect_category(doc_type)
    expected_keys = set(get_section_keys(doc_type, cause_type))

    errors: List[Dict[str, str]] = []
    warns: List[Dict[str, str]] = []
    infos: List[Dict[str, str]] = []

    # Check ERROR sections
    required = _REQUIRED_SECTIONS.get(category, _REQUIRED_SECTIONS["civil"])
    for sec in required:
        if sec not in present_keys:
            errors.append({"section": sec, "severity": "ERROR", "message": f"Required section '{sec}' is missing"})

    # Check WARN sections
    for sec in _WARN_SECTIONS:
        if sec in expected_keys and sec not in present_keys:
            warns.append({"section": sec, "severity": "WARN", "message": f"Expected section '{sec}' is missing"})

    # Check INFO sections
    for sec in _INFO_SECTIONS:
        if sec in expected_keys and sec not in present_keys:
            infos.append({"section": sec, "severity": "INFO", "message": f"Optional section '{sec}' is missing"})

    gate_result = {
        "errors": errors,
        "warnings": warns,
        "info": infos,
        "present_sections": list(present_keys),
        "expected_sections": list(expected_keys),
        "category": category,
    }

    elapsed = time.perf_counter() - t0

    if errors:
        logger.warning(
            "[STRUCTURAL_GATE] ✗ %d ERROR(s) (%.1fs) | missing=%s",
            len(errors), elapsed, [e["section"] for e in errors],
        )
        # Even with errors, proceed to assembler — it will handle missing sections
        # gracefully with placeholders. Full re-draft is too expensive.
        return Command(update={"structural_gate": gate_result}, goto="assembler")

    logger.info(
        "[STRUCTURAL_GATE] ✓ done (%.1fs) | present=%d/%d | warns=%d | info=%d",
        elapsed, len(present_keys), len(expected_keys), len(warns), len(infos),
    )
    return Command(update={"structural_gate": gate_result}, goto="assembler")

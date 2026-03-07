"""Outline Validator Node — deterministic (NO LLM).

Validates the loaded template: section IDs unique, ordering valid,
must_include items well-formed. If invalid → routes to old draft node.

Pipeline position: template_loader → **outline_validator** → section_drafter
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Set

from langgraph.types import Command

from ....config import logger
from ..states import DraftingState
from ._utils import _as_dict


def _validate_template(template: Dict[str, Any]) -> List[str]:
    """Validate template structure. Returns list of error messages (empty = valid)."""
    errors: List[str] = []

    sections = template.get("sections", [])
    if not sections:
        errors.append("Template has no sections")
        return errors

    # Check unique section_ids
    seen_ids: Set[str] = set()
    for i, sec in enumerate(sections):
        sid = sec.get("section_id", "")
        if not sid:
            errors.append(f"Section {i} has no section_id")
            continue
        if sid in seen_ids:
            errors.append(f"Duplicate section_id: {sid}")
        seen_ids.add(sid)

    # Validate must_include items
    for sec in sections:
        sid = sec.get("section_id", "?")
        must_include = sec.get("must_include", [])
        if not isinstance(must_include, list):
            errors.append(f"Section {sid}: must_include is not a list")
            continue
        for j, item in enumerate(must_include):
            if not isinstance(item, dict):
                errors.append(f"Section {sid}: must_include[{j}] is not a dict")
                continue
            if "type" not in item or "match" not in item:
                errors.append(f"Section {sid}: must_include[{j}] missing type or match")
                continue
            if item["type"] not in ("keyword", "regex", "concept", "evidence_anchor"):
                errors.append(f"Section {sid}: must_include[{j}] invalid type: {item['type']}")
            # Validate regex patterns compile
            if item["type"] == "regex":
                try:
                    re.compile(item["match"], re.IGNORECASE)
                except re.error as exc:
                    errors.append(f"Section {sid}: must_include[{j}] invalid regex: {exc}")

    # Validate section types have required fields
    for sec in sections:
        sid = sec.get("section_id", "?")
        stype = sec.get("type", "")
        if stype == "template" and not sec.get("body"):
            errors.append(f"Section {sid}: template type requires 'body' field")
        if stype in ("template_with_fill", "llm_fill") and not sec.get("instruction"):
            errors.append(f"Section {sid}: {stype} type requires 'instruction' field")

    return errors


def outline_validator_node(state: DraftingState) -> Command:
    """Validate the loaded template. Route to section_drafter or fallback to draft."""
    logger.info("[OUTLINE_VALIDATOR] ▶ start")
    t0 = time.perf_counter()

    template = state.get("template")
    if template is None:
        logger.error("[OUTLINE_VALIDATOR] no template in state — fallback to draft")
        return Command(goto="draft")

    template_dict = _as_dict(template) if not isinstance(template, dict) else template
    errors = _validate_template(template_dict)

    elapsed = time.perf_counter() - t0

    if errors:
        logger.error(
            "[OUTLINE_VALIDATOR] ✗ template invalid (%.1fs) | errors=%d: %s → fallback to draft",
            elapsed, len(errors), "; ".join(errors[:5]),
        )
        return Command(
            update={"errors": [f"template_validation: {e}" for e in errors]},
            goto="draft",
        )

    section_ids = [s["section_id"] for s in template_dict.get("sections", [])]
    logger.info(
        "[OUTLINE_VALIDATOR] ✓ valid (%.1fs) | sections=%s",
        elapsed, ", ".join(section_ids),
    )
    return Command(goto="section_drafter")

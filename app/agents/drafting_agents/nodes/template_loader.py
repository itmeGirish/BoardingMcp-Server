"""Template Loader Node — deterministic (NO LLM).

Loads the JSON template for the classified doc_type. Validates against schema.
If no template found → routes to old monolithic draft node as fallback.

Pipeline position: court_fee → **template_loader** → outline_validator (or draft fallback)
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from langgraph.types import Command

from ....config import logger
from ..schema_contracts import validate_template_payload
from ..states import DraftingState
from ._utils import _as_dict

# Template directory
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

# doc_type → template file path mapping
# Only map EXACT doc_types that have specific optimized templates.
# Unknown doc_types → _fallback.json (generic but correct for any suit).
_TEMPLATE_MAP: Dict[str, str] = {
    "money_recovery_plaint": "civil/money_recovery_plaint.json",
    "recovery_of_money": "civil/money_recovery_plaint.json",
    "money_suit": "civil/money_recovery_plaint.json",
    "hand_loan_plaint": "civil/money_recovery_plaint.json",
    "hand_loan_recovery": "civil/money_recovery_plaint.json",
    "cheque_bounce_recovery_plaint": "civil/money_recovery_plaint.json",
}

# Fallback template for any doc_type not in _TEMPLATE_MAP
_FALLBACK_TEMPLATE = "_fallback.json"

# Required schema version
_REQUIRED_VERSION = "1.1"


def _normalize_doc_type(doc_type: str) -> str:
    """Normalize doc_type string for template lookup."""
    return (
        doc_type.lower()
        .strip()
        .replace(" ", "_")
        .replace("-", "_")
    )


def _load_template(doc_type: str) -> Optional[Dict[str, Any]]:
    """Load and validate a template JSON file for the given doc_type.

    Priority: exact match → fallback template → None (old draft node).
    Never uses partial matching — prevents wrong template being loaded.
    """
    normalized = _normalize_doc_type(doc_type)

    # Exact lookup only — no partial matching
    rel_path = _TEMPLATE_MAP.get(normalized)

    if not rel_path:
        # Use generic fallback template
        fallback_path = _TEMPLATE_DIR / _FALLBACK_TEMPLATE
        if fallback_path.exists():
            rel_path = _FALLBACK_TEMPLATE
            logger.info(
                "[TEMPLATE] no specific template for %r → using _fallback.json",
                doc_type,
            )
        else:
            return None

    template_path = _TEMPLATE_DIR / rel_path
    if not template_path.exists():
        logger.error("[TEMPLATE] file not found: %s", template_path)
        return None

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("[TEMPLATE] failed to parse %s: %s", template_path, exc)
        return None

    errors = validate_template_payload(template)
    if errors:
        logger.error("[TEMPLATE] invalid template %s: %s", template_path, "; ".join(errors[:5]))
        return None

    # Version check
    if template.get("template_version") != _REQUIRED_VERSION:
        logger.warning(
            "[TEMPLATE] version mismatch: got %s, expected %s",
            template.get("template_version"), _REQUIRED_VERSION,
        )

    return template


def template_loader_node(state: DraftingState) -> Command:
    """Load template for doc_type. Fallback to old draft node if no template."""
    logger.info("[TEMPLATE] ▶ start")
    t0 = time.perf_counter()

    classify = _as_dict(state.get("classify"))
    doc_type = classify.get("doc_type", "")

    template = _load_template(doc_type)

    if template is None:
        elapsed = time.perf_counter() - t0
        logger.info(
            "[TEMPLATE] ✗ no template for doc_type=%r (%.1fs) → fallback to old draft node",
            doc_type, elapsed,
        )
        return Command(update={"template": None}, goto="draft_freetext")

    section_count = len(template.get("sections", []))
    llm_sections = sum(1 for s in template["sections"] if s["type"] in ("llm_fill", "template_with_fill"))

    elapsed = time.perf_counter() - t0
    logger.info(
        "[TEMPLATE] ✓ loaded %s (%.1fs) | sections=%d | llm_sections=%d",
        template["template_id"], elapsed, section_count, llm_sections,
    )

    return Command(
        update={"template": template},
        goto="outline_validator",
    )

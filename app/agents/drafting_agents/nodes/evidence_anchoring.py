"""Evidence Anchoring Node — deterministic (NO LLM).

Applies evidence anchoring to the full assembled draft text:
  - Entity extraction (dates, amounts, references)
  - Tier A: unsupported tokens → {{PLACEHOLDER}} replacement
  - Tier B: drafting quality checks (skeleton sentences, notes language)

Reuses extraction functions from section_validator.

Pipeline position: assembler → **evidence_anchoring** → postprocess
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

from langgraph.types import Command

from ....config import logger, settings
from ..states import DraftingState
from ._utils import _as_dict
from .section_validator import (
    _extract_dates,
    _extract_amounts,
    _extract_references,
    _anchor_entities,
    _check_drafting_quality,
)


def evidence_anchoring_node(state: DraftingState) -> Command:
    """Apply evidence anchoring to the full assembled draft."""
    logger.info("[EVIDENCE_ANCHORING] ▶ start")
    t0 = time.perf_counter()

    draft = _as_dict(state.get("draft"))
    intake = _as_dict(state.get("intake"))
    user_request = (state.get("user_request") or "").strip()

    artifacts = draft.get("draft_artifacts") or []
    if not artifacts or not isinstance(artifacts[0], dict):
        logger.info("[EVIDENCE_ANCHORING] no draft artifacts — skipping")
        return Command(update={"evidence_anchoring_issues": []}, goto="lkb_compliance")

    text = artifacts[0].get("text", "")
    if not text:
        logger.info("[EVIDENCE_ANCHORING] empty draft text — skipping")
        return Command(update={"evidence_anchoring_issues": []}, goto="lkb_compliance")

    all_issues: List[Dict[str, Any]] = []

    # Layer A: Entity extraction
    dates = _extract_dates(text)
    amounts = _extract_amounts(text)
    references = _extract_references(text)
    entities_found = len(dates) + len(amounts) + len(references)

    # Layer B Tier A: Evidence anchoring (unsupported tokens → placeholders)
    corrected_text, anchor_issues = _anchor_entities(
        text, dates, amounts, references, intake, user_request,
    )
    all_issues.extend(anchor_issues)
    entities_replaced = len(anchor_issues)
    entities_anchored = entities_found - entities_replaced

    # Layer D: Drafting quality checks on key sections
    # We check the full text since in v4.0 we don't have per-section access
    quality_issues = _check_drafting_quality(corrected_text, "facts")
    all_issues.extend(quality_issues)

    # Update the draft artifact with corrected text
    corrected_artifact = {**artifacts[0], "text": corrected_text}
    draft_update = {"draft_artifacts": [corrected_artifact]}

    # v10.0: Run accuracy gates on corrected text
    from .accuracy_gates import run_accuracy_gates

    lkb_brief = _as_dict(state.get("lkb_brief"))
    accuracy_issues = run_accuracy_gates(corrected_text, lkb_brief, intake)

    elapsed = time.perf_counter() - t0
    logger.info(
        "[EVIDENCE_ANCHORING] ✓ done (%.1fs) | entities=%d | anchored=%d | replaced=%d | quality=%d | accuracy=%d",
        elapsed, entities_found, entities_anchored, entities_replaced,
        len(quality_issues), len(accuracy_issues),
    )

    return Command(
        update={
            "draft": draft_update,
            "evidence_anchoring_issues": all_issues,
            "accuracy_gate_issues": accuracy_issues,
        },
        goto="lkb_compliance",
    )

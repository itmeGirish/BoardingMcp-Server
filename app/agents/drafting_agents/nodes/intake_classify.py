"""Merged Intake + Classify Node — ONE LLM call instead of two.

Saves ~10-15s by doing fact extraction AND classification in a single call.
Splits result into separate `intake` and `classify` state fields so downstream
nodes (rag, enrichment, draft) work unchanged.

Pipeline position: START → **intake_classify** → rag
"""
from __future__ import annotations

import time
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command

from ....config import logger
from ....services import glm_model as ollma_model
from ....utils.draftingAgent import CIVIL_PROFILE, get_active_qdrant_profile
from ..prompts.intake_classify import (
    INTAKE_CLASSIFY_USER_PROMPT,
    build_intake_classify_system_prompt,
)
from ..states import DraftingState, IntakeClassifyNode, IntakeNode, ClassifyNode
from ._utils import _as_dict, _as_json


def _split_result(result: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Split merged result into separate intake and classify dicts."""
    intake = {
        "facts": result.get("facts", {}),
        "jurisdiction": result.get("jurisdiction", {}),
        "parties": result.get("parties", {}),
        "evidence": result.get("evidence", []),
        "dynamic_fields": result.get("dynamic_fields", {}),
        "classification": result.get("classification", {}),
    }
    classify = {
        "law_domain": result.get("law_domain", "Civil"),
        "doc_type": result.get("doc_type", ""),
        "cause_type": result.get("cause_type", ""),
        "classification": result.get("classification", {}),
        "rag_plan": result.get("rag_plan", {}),
    }
    return intake, classify


def intake_classify_node(state: DraftingState) -> Dict[str, Any]:
    """Extract intake + classify in ONE LLM call."""
    logger.info("[INTAKE+CLASSIFY] ▶ start")
    t0 = time.perf_counter()

    user_text = (state.get("user_request") or "").strip()
    if not user_text:
        logger.warning("[INTAKE+CLASSIFY] ✗ missing user_request — skipping")
        return Command(
            update={
                "errors": ["intake_classify_node: missing user_request"],
                "intake": None,
                "classify": None,
            },
            goto="rag",
        )

    try:
        active_collection = get_active_qdrant_profile().collection_name
    except Exception:
        active_collection = CIVIL_PROFILE.collection_name

    structured_llm = ollma_model.with_structured_output(IntakeClassifyNode)
    user_prompt = INTAKE_CLASSIFY_USER_PROMPT.format(
        user_text=user_text,
        available_collections=_as_json([active_collection]),
    )

    try:
        messages = [
            SystemMessage(content=build_intake_classify_system_prompt()),
            HumanMessage(content=user_prompt),
        ]
        response = structured_llm.invoke(messages)
        result = _as_dict(response)
        intake, classify = _split_result(result)

        facts_summary = (intake.get("facts") or {}).get("summary", "")[:80]
        logger.info(
            "[INTAKE+CLASSIFY] ✓ done (%.1fs) | domain=%s | doc_type=%s | facts=%r",
            time.perf_counter() - t0,
            classify.get("law_domain"),
            classify.get("doc_type"),
            facts_summary,
        )
        return Command(update={"intake": intake, "classify": classify}, goto="rag")
    except Exception as first_exc:
        logger.error("[INTAKE+CLASSIFY] attempt1 failed (%.1fs): %s", time.perf_counter() - t0, first_exc)

    # Retry with validation hint
    try:
        retry_messages = [
            SystemMessage(content=build_intake_classify_system_prompt(retry=True)),
            HumanMessage(content=user_prompt),
        ]
        response = structured_llm.invoke(retry_messages)
        result = _as_dict(response)
        intake, classify = _split_result(result)

        logger.info("[INTAKE+CLASSIFY] ✓ done on retry (%.1fs)", time.perf_counter() - t0)
        return Command(update={"intake": intake, "classify": classify}, goto="rag")
    except Exception as exc:
        logger.error("[INTAKE+CLASSIFY] ✗ failed after 2 attempts (%.1fs): %s", time.perf_counter() - t0, exc)
        return Command(
            update={
                "errors": [f"intake_classify_node failed: {exc}"],
                "intake": None,
                "classify": None,
            },
            goto="rag",
        )

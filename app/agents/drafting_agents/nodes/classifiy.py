from __future__ import annotations

import time
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command

from ....config import logger
from ....services import glm_model as ollma_model
from ....utils.draftingAgent import CIVIL_PROFILE, get_active_qdrant_profile
from ..prompts import CLASSIFY_USER_PROMPT, build_classify_system_prompt
from ..states import ClassifyNode, DraftingState
from ._utils import _as_dict, _as_json


def classifier_node(state: DraftingState) -> Dict[str, Any]:
    """Classify legal domain/doc type and prepare retrieval plan."""
    logger.info("[CLASSIFY] ▶ start")
    t0 = time.perf_counter()

    intake = _as_dict(state.get("intake"))
    user_request = (state.get("user_request") or "").strip()

    try:
        active_collection = get_active_qdrant_profile().collection_name
    except Exception as profile_exc:
        logger.warning("[CLASSIFY] profile lookup failed (%s), using env default", profile_exc)
        active_collection = CIVIL_PROFILE.collection_name

    # Build user payload once — shared by both attempts.
    user_payload = CLASSIFY_USER_PROMPT.format(
        user_request=user_request,
        facts=_as_json(intake.get("facts", {})),
        evidence=_as_json(intake.get("evidence", [])),
        jurisdiction=_as_json(intake.get("jurisdiction", {})),
        slots=_as_json(_as_dict(intake.get("dynamic_fields")).get("slots", [])),
        available_collections=_as_json([active_collection]),
    )
    human_message = HumanMessage(content=user_payload)
    structured_llm = ollma_model.with_structured_output(ClassifyNode)

    try:
        messages = [SystemMessage(content=build_classify_system_prompt()), human_message]
        response = structured_llm.invoke(messages)
        result = _as_dict(response)
        logger.info(
            "[CLASSIFY] ✓ done (%.1fs) | domain=%s | doc_type=%s | collection=%s",
            time.perf_counter() - t0,
            result.get("law_domain"),
            result.get("doc_type"),
            active_collection,
        )
        return Command(update={"classify": result}, goto="domain_router")
    except Exception as first_exc:
        logger.error("[CLASSIFY] attempt1 failed (%.1fs): %s", time.perf_counter() - t0, first_exc)

    try:
        retry_system = build_classify_system_prompt(retry=True)
        retry_messages = [SystemMessage(content=retry_system), human_message]
        response = structured_llm.invoke(retry_messages)
        result = _as_dict(response)
        logger.info(
            "[CLASSIFY] ✓ done on retry (%.1fs) | domain=%s | doc_type=%s",
            time.perf_counter() - t0,
            result.get("law_domain"),
            result.get("doc_type"),
        )
        return Command(update={"classify": result}, goto="domain_router")
    except Exception as exc:
        logger.error("[CLASSIFY] ✗ failed after 2 attempts (%.1fs): %s", time.perf_counter() - t0, exc)
        return Command(
            update={"errors": [f"classifier_node failed: {exc}"], "classify": None},
            goto="domain_router",
        )

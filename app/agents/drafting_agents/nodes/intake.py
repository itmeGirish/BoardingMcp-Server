from __future__ import annotations

import time
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Command

from ....config import logger
from ....services import glm_model as ollma_model
from ..prompts import INTAKE_USER_PROMPT, build_intake_system_prompt
from ..states import DraftingState, IntakeNode
from ._utils import _as_dict


def intake_node(state: DraftingState) -> Dict[str, Any]:
    """Extract structured intake details from the raw user request."""
    logger.info("[INTAKE] ▶ start")
    t0 = time.perf_counter()

    user_text = (state.get("user_request") or "").strip()
    if not user_text:
        logger.warning("[INTAKE] ✗ missing user_request — skipping")
        return Command(
            update={"errors": ["intake_node: missing user_request"], "intake": None},
            goto="classify",
        )

    structured_llm = ollma_model.with_structured_output(IntakeNode)
    messages = [
        SystemMessage(content=build_intake_system_prompt()),
        HumanMessage(content=INTAKE_USER_PROMPT.format(user_text=user_text)),
    ]

    try:
        response = structured_llm.invoke(messages)
        result = _as_dict(response)
        facts_summary = (result.get("facts") or {}).get("summary", "")[:80]
        jurisdiction = (result.get("jurisdiction") or {})
        logger.info(
            "[INTAKE] ✓ done (%.1fs) | facts=%r | jurisdiction=%s/%s",
            time.perf_counter() - t0,
            facts_summary,
            jurisdiction.get("state"),
            jurisdiction.get("city"),
        )
        return Command(update={"intake": result}, goto="classify")
    except Exception as first_exc:
        logger.error("[INTAKE] attempt1 failed (%.1fs): %s", time.perf_counter() - t0, first_exc)

    try:
        retry_messages = [
            SystemMessage(
                content=(
                    build_intake_system_prompt()
                    + "\nYour previous output did not validate. Fix field names/types and return valid JSON only."
                )
            ),
            HumanMessage(content=INTAKE_USER_PROMPT.format(user_text=user_text)),
        ]
        response = structured_llm.invoke(retry_messages)
        result = _as_dict(response)
        logger.info("[INTAKE] ✓ done on retry (%.1fs)", time.perf_counter() - t0)
        return Command(update={"intake": result}, goto="classify")
    except Exception as exc:
        logger.error("[INTAKE] ✗ failed after 2 attempts (%.1fs): %s", time.perf_counter() - t0, exc)
        return Command(
            update={"errors": [f"intake_node failed: {exc}"], "intake": None},
            goto="classify",
        )

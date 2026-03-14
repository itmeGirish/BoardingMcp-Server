"""
Court Fee + Legal Research Node — fetches court fee rates and legal doctrine from the web.

Both searches run concurrently. Court fees are jurisdiction-specific and change via government
notifications. Legal research surfaces limitation periods and procedural requirements dynamically
— avoiding hardcoded legal rules in prompts.

Routing: rag → court_fee → draft
"""
from __future__ import annotations
import asyncio
import time
from typing import Any, Dict

from langgraph.types import Command

from ....config import logger, settings
from ..states import DraftingState
from ..tools import CourtFeeWebSearchTool, LegalResearchWebSearchTool
from ._utils import _as_dict


async def court_fee_node(state: DraftingState) -> Dict[str, Any]:
    """Fetch court fee rates AND legal research concurrently via Brave web search.

    Court fee search: jurisdiction-specific fee rates (ad valorem % for the suit value).
    Legal research: limitation period + procedural requirements for the doc_type.

    Both are best-effort — failures are non-fatal. Draft node receives whatever context
    was successfully fetched; missing context falls back to RAG chunks or placeholders.
    """
    intake = _as_dict(state.get("intake"))
    classify = _as_dict(state.get("classify"))
    jurisdiction = _as_dict(intake.get("jurisdiction"))

    state_name = (jurisdiction.get("state") or "").strip()
    court_type = (jurisdiction.get("court_type") or jurisdiction.get("city") or "").strip()
    doc_type = (classify.get("doc_type") or "").strip()

    # Extract suit value for court fee context.
    facts = _as_dict(intake.get("facts"))
    amounts = _as_dict(facts.get("amounts"))
    suit_value: float | None = amounts.get("principal")

    # Extract cause of action type from classification topics (first topic, if any).
    classification = _as_dict(classify.get("classification"))
    topics = classification.get("topics") or []
    cause_of_action = topics[0] if topics else ""

    # Build jurisdiction string for legal research queries.
    jurisdiction_str = " ".join(filter(None, [state_name, court_type]))

    logger.info(
        "[WEBRESEARCH] ▶ start | state=%r | doc_type=%r | coa=%r | value=%s",
        state_name, doc_type, cause_of_action, suit_value,
    )
    t0 = time.perf_counter()

    # Run court fee search and legal research concurrently.
    court_fee_coro = CourtFeeWebSearchTool(
        state=state_name,
        court_type=court_type,
        doc_type=doc_type,
        suit_value=suit_value,
    ) if state_name else None

    legal_research_coro = LegalResearchWebSearchTool(
        doc_type=doc_type,
        cause_of_action=cause_of_action,
        jurisdiction=jurisdiction_str,
    ) if (doc_type and getattr(settings, "DRAFTING_LEGAL_RESEARCH_ENABLED", True)) else None

    tasks = [t for t in [court_fee_coro, legal_research_coro] if t is not None]
    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.perf_counter() - t0
    update: Dict[str, Any] = {}

    # Map results back — order matches [court_fee, legal_research] based on which were created.
    result_idx = 0
    if court_fee_coro is not None:
        cf_result = results_list[result_idx]
        result_idx += 1
        if isinstance(cf_result, Exception):
            logger.warning("[WEBRESEARCH] court_fee failed: %s", cf_result)
        elif not cf_result.get("error"):
            update["court_fee"] = cf_result
            logger.info("[WEBRESEARCH] court_fee ✓ | results=%d", len(cf_result.get("results") or []))
        else:
            logger.warning("[WEBRESEARCH] court_fee error: %s", cf_result.get("error"))
    else:
        logger.info("[WEBRESEARCH] court_fee skipped — jurisdiction state not known")

    if legal_research_coro is not None:
        lr_result = results_list[result_idx]
        if isinstance(lr_result, Exception):
            logger.warning("[WEBRESEARCH] legal_research failed: %s", lr_result)
        elif not lr_result.get("error"):
            update["legal_research"] = lr_result
            logger.info("[WEBRESEARCH] legal_research ✓ | results=%d", len(lr_result.get("results") or []))
        else:
            logger.warning("[WEBRESEARCH] legal_research error: %s", lr_result.get("error"))

    if getattr(settings, "TEMPLATE_ENGINE_ENABLED", False):
        next_node = "draft_template_fill"
    else:
        next_node = "draft_freetext"
    logger.info("[WEBRESEARCH] ✓ done (%.1fs) → %s", elapsed, next_node)
    return Command(update=update, goto=next_node)

from __future__ import annotations

import time
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END
from langgraph.types import Command

from ....config import logger, settings
from ....services import draft_ollama_model as draft_openai_model
from ..prompts import DRAFT_USER_PROMPT, build_draft_system_prompt
from ..states import DraftingState, DraftNode
from ._utils import (
    _as_dict, _as_json,
    build_court_fee_context, build_legal_research_context,
    build_mandatory_provisions_context,
    extract_json_from_text,
)


def draft_node(state: DraftingState) -> Dict[str, Any]:
    """Generate draft artifacts from intake/classification/rag context."""
    review = _as_dict(state.get("review"))
    pass_label = "pass-2 (final)" if review else "pass-1"
    logger.info("[DRAFT] ▶ start | %s", pass_label)
    t0 = time.perf_counter()

    user_request = (state.get("user_request") or "").strip()
    intake = _as_dict(state.get("intake"))
    classify = _as_dict(state.get("classify"))
    rag = _as_dict(state.get("rag"))
    court_fee = _as_dict(state.get("court_fee"))
    legal_research = _as_dict(state.get("legal_research"))
    mandatory_provisions = _as_dict(state.get("mandatory_provisions"))

    # For pass-2: include pass-1 draft text so model improves it rather than regenerating.
    existing_draft = ""
    if review:
        pass1 = _as_dict(state.get("draft"))
        pass1_artifacts = pass1.get("draft_artifacts") or []
        if pass1_artifacts:
            first = pass1_artifacts[0]
            existing_draft = (first.get("text") if isinstance(first, dict) else "") or ""

    # Build web search context strings via shared helpers.
    court_fee_context = build_court_fee_context(court_fee, settings.DRAFTING_WEBSEARCH_SOURCE_URLS)
    legal_research_context = build_legal_research_context(legal_research, settings.DRAFTING_WEBSEARCH_SOURCE_URLS)
    mandatory_provisions_context = build_mandatory_provisions_context(mandatory_provisions)

    # Common fields used by both passes.
    _common = dict(
        user_request=user_request,
        doc_type=classify.get("doc_type", ""),
        law_domain=classify.get("law_domain", ""),
        parties=_as_json(intake.get("parties", {})),
        jurisdiction=_as_json(intake.get("jurisdiction", {})),
        facts=_as_json(intake.get("facts", {})),
        evidence=_as_json(intake.get("evidence", [])),
        slots=_as_json(_as_dict(intake.get("dynamic_fields")).get("slots", [])),
        classification=_as_json(classify.get("classification", {})),
        existing_draft=existing_draft,
        review_feedback=_as_json(review.get("review", {})),
    )

    if review:
        # Pass-2: slim context — model already drafted from RAG in pass-1.
        # Only send the draft to fix + review feedback + minimal ground-truth facts.
        # Skipping RAG/court-fee/legal-research saves ~3000-4000 input tokens.
        user_payload = DRAFT_USER_PROMPT.format(
            **_common,
            rag_plan="",
            rules="",
            rag_chunks="",
            court_fee_context="",
            legal_research_context="",
            mandatory_provisions=mandatory_provisions_context,
        )
        logger.info("[DRAFT] pass-2 slim context | existing_draft_len=%d", len(existing_draft))
    else:
        # Pass-1: full context with capped RAG chunks (top-N by Qdrant score).
        capped_rules = (rag.get("rules") or [])[:settings.DRAFTING_DRAFT_RULES_LIMIT]
        capped_chunks = (rag.get("chunks") or [])[:settings.DRAFTING_DRAFT_RAG_LIMIT]
        logger.info(
            "[DRAFT] pass-1 context | rules=%d/%d | chunks=%d/%d",
            len(capped_rules), len(rag.get("rules") or []),
            len(capped_chunks), len(rag.get("chunks") or []),
        )
        user_payload = DRAFT_USER_PROMPT.format(
            **_common,
            rag_plan=_as_json(classify.get("rag_plan", {})),
            rules=_as_json(capped_rules),
            rag_chunks=_as_json(capped_chunks),
            court_fee_context=court_fee_context,
            legal_research_context=legal_research_context,
            mandatory_provisions=mandatory_provisions_context,
        )

    structured_llm = draft_openai_model.with_structured_output(DraftNode)
    human_message = HumanMessage(content=user_payload)

    try:
        messages = [SystemMessage(content=build_draft_system_prompt()), human_message]
        response = structured_llm.invoke(messages)
    except Exception as first_exc:
        logger.error("[DRAFT] attempt1 failed (%.1fs): %s", time.perf_counter() - t0, first_exc)
        try:
            retry_messages = [SystemMessage(content=build_draft_system_prompt(retry=True)), human_message]
            response = structured_llm.invoke(retry_messages)
        except Exception as exc:
            logger.warning("[DRAFT] attempt2 structured output failed (%.1fs): %s — trying raw extraction", time.perf_counter() - t0, exc)
            try:
                raw_messages = [SystemMessage(content=build_draft_system_prompt(retry=True)), human_message]
                raw_response = draft_openai_model.invoke(raw_messages)
                raw_text = getattr(raw_response, "content", "") or ""
                parsed = extract_json_from_text(raw_text)
                if parsed and parsed.get("draft_artifacts"):
                    logger.info("[DRAFT] attempt3 raw extraction succeeded (%.1fs)", time.perf_counter() - t0)
                    response = DraftNode.model_validate(parsed)
                else:
                    raise ValueError("raw extraction produced no draft_artifacts")
            except Exception as raw_exc:
                logger.error("[DRAFT] ✗ failed after 3 attempts (%.1fs): %s", time.perf_counter() - t0, raw_exc)
                # pass-2: do NOT overwrite draft — preserve pass-1 output for Streamlit fallback.
                # pass-1: clear draft so state doesn't carry a stale None value.
                update = {"errors": [f"draft_node failed: {raw_exc}"]}
                if not review:
                    update["draft"] = None
                return Command(update=update, goto=END)

    result = _as_dict(response)
    artifacts = result.get("draft_artifacts") or []
    title = artifacts[0].get("title", "") if artifacts else ""
    placeholders = len(artifacts[0].get("placeholders_used") or []) if artifacts else 0
    logger.info(
        "[DRAFT] ✓ done | %s (%.1fs) | artifacts=%d | title=%r | placeholders=%d",
        pass_label,
        time.perf_counter() - t0,
        len(artifacts),
        title,
        placeholders,
    )

    # First pass → review. Second pass (after review feedback) → final output.
    if review:
        if not artifacts or not artifacts[0].get("text", "").strip():
            logger.warning("[DRAFT] pass-2 returned empty artifacts — promoting pass-1 draft to final_draft")
            # Promote pass-1 draft so Streamlit always gets a final_draft, never a bare fallback.
            pass1 = state.get("draft")
            if pass1:
                return Command(update={"final_draft": _as_dict(pass1)}, goto=END)
            return Command(update={}, goto=END)
        return Command(update={"final_draft": result}, goto=END)
    return Command(update={"draft": result}, goto="review")

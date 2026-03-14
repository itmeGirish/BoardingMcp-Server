from __future__ import annotations

import re
import time
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END
from langgraph.types import Command

from ....config import logger, settings
from ....services import review_openai_model
from ..prompts import build_review_system_prompt
from ..states import DraftingState, ReviewNode
from ._utils import (
    _as_dict,
    extract_json_from_text,
)
from .postprocess import _fix_and_or

MAX_REVIEW_CYCLES = settings.DRAFTING_MAX_REVIEW_CYCLES

# ---------------------------------------------------------------------------
# Slim review prompt — only draft text + gate errors + user request
# ---------------------------------------------------------------------------

REVIEW_USER_PROMPT_SLIM = """
Review the generated draft for legal correctness and filing readiness.

USER_REQUEST:
{user_request}

DOC_TYPE: {doc_type}
LAW_DOMAIN: {law_domain}

GATE ERRORS (from deterministic validation gates — already verified):
{gate_errors}

DRAFT TEXT:
{draft_text}
"""


def _resolve_last_para_placeholders(text: str) -> str:
    if not text:
        return text

    placeholder_pattern = re.compile(
        r"\{\{(?:LAST|TOTAL)_(?:PARA|PARAGRAPH)(?:S|_NUMBER|_NUMBERS|GRAPH_NUMBER|GRAPHS)?\}\}",
        re.IGNORECASE,
    )
    variants = (
        "{{LAST_PARA}}",
        "{{LAST_PARA_NUMBER}}",
        "{{LAST_PARAGRAPH}}",
        "{{LAST_PARAGRAPH_NUMBER}}",
        "{{TOTAL_PARAGRAPHS}}",
        "{{TOTAL_PARAGRAPH_NUMBER}}",
    )
    if not any(v in text for v in variants) and not placeholder_pattern.search(text):
        return text

    para_nums = [int(m.group(1)) for m in re.finditer(r"^\s*(\d+)\.\s", text, re.MULTILINE)]
    last_para = max(para_nums) if para_nums else 0
    if last_para <= 0:
        return text

    for v in variants:
        text = text.replace(v, str(last_para))
    text = placeholder_pattern.sub(str(last_para), text)

    stale = re.search(r"paragraphs\s+1\s+to\s+(\d+)", text)
    if stale:
        stated = int(stale.group(1))
        if stated != last_para:
            text = text.replace(f"paragraphs 1 to {stated}", f"paragraphs 1 to {last_para}")
    return text


def _sanitize_contract_inline_fix(text: str, cause_type: str) -> str:
    if not text or cause_type != "breach_of_contract":
        return text

    text = re.sub(r"\bfailed and refused to comply\b", "failed to comply", text, flags=re.IGNORECASE)
    text = re.sub(r"\bfailed to respond satisfactorily\b", "failed to comply", text, flags=re.IGNORECASE)
    text = re.sub(r"\brefused and failed to perform\b", "failed to perform", text, flags=re.IGNORECASE)
    text = re.sub(
        r"The cause of action continues to subsist[^.\n]*\.",
        "The Defendant has not compensated the Plaintiff despite legal notice, and the Plaintiff's right to claim damages therefore subsists.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"The Plaintiff's loss and right to claim damages continue until compensated in accordance with law\.",
        "The Plaintiff's claim for damages subsists and remains enforceable in law.",
        text,
        flags=re.IGNORECASE,
    )
    return text


def _strip_reviewer_notes(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"\s*\[NOTE:[^\]]+\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*\[DRAFTING NOTE:[^\]]+\]", "", text, flags=re.IGNORECASE)
    return text


def _build_gate_errors_summary(state: DraftingState) -> str:
    """Build a compact summary of all gate errors for the review prompt."""
    lines = []

    # Evidence anchoring issues
    ea_issues = state.get("evidence_anchoring_issues") or []
    if ea_issues:
        lines.append("EVIDENCE ANCHORING:")
        for i in ea_issues:
            if isinstance(i, dict):
                lines.append(f"  - {i.get('type', 'issue')}: {i.get('description', str(i))}")

    # Postprocess issues (includes lkb_compliance issues)
    pp_issues = state.get("postprocess_issues") or []
    if pp_issues:
        lines.append("POSTPROCESS/LKB COMPLIANCE:")
        for i in pp_issues:
            if isinstance(i, dict):
                lines.append(f"  - {i.get('type', 'issue')}: {i.get('description', str(i))}")

    # Citation issues
    ct_issues = state.get("citation_issues") or []
    if ct_issues:
        lines.append("CITATION VALIDATION:")
        for i in ct_issues:
            if isinstance(i, dict):
                lines.append(f"  - {i.get('severity', 'error')}: {i.get('message', str(i))}")

    if not lines:
        return "No gate errors — all deterministic checks passed."

    return "\n".join(lines)


def _issue_severity(issue: Any) -> str:
    """Extract severity from a blocking issue (dict or Pydantic model). Defaults to 'legal'."""
    if isinstance(issue, dict):
        return issue.get("severity") or "legal"
    return getattr(issue, "severity", None) or "legal"


def _has_valid_artifacts(artifacts: Any) -> bool:
    """Return True if *artifacts* contains at least one entry with non-empty text."""
    if not isinstance(artifacts, list) or not artifacts:
        return False
    for a in artifacts:
        text = (a.get("text") if isinstance(a, dict) else getattr(a, "text", "")) or ""
        if text.strip():
            return True
    return False


def _route_after_review(
    *,
    result: Dict[str, Any],
    review_count: int,
    state: DraftingState,
    elapsed: float,
    inline_fix_enabled: bool = True,
) -> Command:
    """Decide next node based on blocking issue severity and inline-fix availability.

    Priority order:
    1. No legal blocking issues → promote pass-1 (formatting-only or clean).
    2. Legal issues + inline fix present → promote review's corrected final_artifacts.
    3. Legal issues + no inline fix + within cycles → route to draft pass-2 (fallback).
    4. Max cycles exceeded → END regardless.

    severity="legal"      → wrong citation, wrong limitation anchor, missing legal section
    severity="formatting" → annexure label mismatch, numbering gap, heading style
    """
    review_data = result.get("review") or {}
    blocking = review_data.get("blocking_issues") or []
    review_pass = review_data.get("review_pass", False)
    final_artifacts = review_data.get("final_artifacts") or []

    legal_blocking = [i for i in blocking if _issue_severity(i) == "legal"]
    formatting_blocking = [i for i in blocking if _issue_severity(i) == "formatting"]

    within_cycles = review_count <= MAX_REVIEW_CYCLES

    # Check if review produced a valid inline fix (Phase 2 output).
    has_inline_fix = inline_fix_enabled and _has_valid_artifacts(final_artifacts)

    if not legal_blocking:
        # No legal defects (clean or formatting-only) — promote pass-1 directly.
        next_node = END
        current_draft = _as_dict(state.get("draft"))
        extra_update: Dict[str, Any] = {"final_draft": current_draft}
        if formatting_blocking:
            next_label = (
                f"END (pass-1 promoted — {len(formatting_blocking)} formatting issue(s) only)"
            )
            logger.info(
                "[REVIEW] formatting-only issues (%d) — skipping pass-2, promoting pass-1",
                len(formatting_blocking),
            )
        else:
            next_label = "END (pass-1 promoted — clean review)"
            logger.info("[REVIEW] clean review — promoting pass-1 to final_draft, skipping pass-2")

    elif has_inline_fix:
        # Legal issues found but review fixed them inline — use corrected artifacts.
        # Apply safe deterministic fixes (e.g., "and/or" → "and") since inline fix
        # bypasses postprocess and the LLM may reintroduce anti-patterns.
        next_node = END
        classify = _as_dict(state.get("classify"))
        cause_type = classify.get("cause_type", "")
        sanitized_artifacts = []
        for a in final_artifacts:
            art = a if isinstance(a, dict) else _as_dict(a)
            text = art.get("text", "")
            if text:
                text, _ = _fix_and_or(text)
                text = _sanitize_contract_inline_fix(text, cause_type)
                text = _strip_reviewer_notes(text)
                text = _resolve_last_para_placeholders(text)
                art = {**art, "text": text}
            sanitized_artifacts.append(art)

        # v10.0: Re-run accuracy gates on inline-fixed text (Critical Gap #40)
        from .accuracy_gates import run_accuracy_gates

        lkb_brief = _as_dict(state.get("lkb_brief"))
        intake = _as_dict(state.get("intake"))
        for art in sanitized_artifacts:
            fixed_text = art.get("text", "")
            if fixed_text:
                post_fix_issues = run_accuracy_gates(fixed_text, lkb_brief, intake)
                blocking = [i for i in post_fix_issues if i.get("blocking")]
                if blocking:
                    logger.warning(
                        "[REVIEW] inline fix introduced %d blocking accuracy issues — flagging",
                        len(blocking),
                    )

        inline_draft = {"draft_artifacts": sanitized_artifacts}
        extra_update = {"final_draft": inline_draft}
        next_label = (
            f"END (inline fix — {len(legal_blocking)} legal issue(s) corrected in review)"
        )
        logger.info(
            "[REVIEW] inline fix applied — %d legal issue(s) corrected, skipping pass-2",
            len(legal_blocking),
        )

    elif within_cycles:
        # Legal defects, no inline fix — re-draft full document.
        if getattr(settings, "TEMPLATE_ENGINE_ENABLED", False):
            next_node = "draft_template_fill"
            next_label = f"draft_template_fill (pass-2) | {len(legal_blocking)} legal issue(s)"
        else:
            next_node = "draft_freetext"
            next_label = f"draft_freetext (pass-2) | {len(legal_blocking)} legal issue(s)"
        extra_update = {}
        logger.info(
            "[REVIEW] routing to %s (pass-2) for %d legal issue(s)",
            next_node, len(legal_blocking),
        )

    else:
        # Max cycles reached — END with whatever draft exists.
        next_node = END
        next_label = "END (max cycles reached)"
        extra_update = {}

    logger.info(
        "[REVIEW] ✓ done (%.1fs) | pass=%s | legal=%d | formatting=%d | inline_fix=%s | → %s",
        elapsed,
        review_pass,
        len(legal_blocking),
        len(formatting_blocking),
        has_inline_fix,
        next_label,
    )
    return Command(
        update={"review": result, "review_count": review_count, **extra_update},
        goto=next_node,
    )


def review_node(state: DraftingState) -> Dict[str, Any]:
    """Review current draft, optionally generate inline corrected draft.

    Single-call approach: Phase 1 checks + Phase 2 inline fix in one LLM call.
    The model is more judicious about flagging issues when it knows it must fix them.
    """
    review_count = (state.get("review_count") or 0) + 1
    inline_fix_enabled = settings.DRAFTING_REVIEW_INLINE_FIX
    logger.info(
        "[REVIEW] ▶ start | cycle=%d/%d | inline_fix=%s",
        review_count, MAX_REVIEW_CYCLES, inline_fix_enabled,
    )
    t0 = time.perf_counter()

    user_request = (state.get("user_request") or "").strip()
    classify = _as_dict(state.get("classify"))
    draft = _as_dict(state.get("draft"))

    drafts = draft.get("draft_artifacts", []) if isinstance(draft.get("draft_artifacts"), list) else []

    # Build compact gate errors summary — gates already ran deterministically,
    # no need to re-send full RAG/court_fee/legal_research context.
    gate_errors = _build_gate_errors_summary(state)

    # Extract just the draft text (not full JSON with metadata)
    draft_text = ""
    if drafts:
        draft_text = drafts[0].get("text", "") if isinstance(drafts[0], dict) else getattr(drafts[0], "text", "")

    user_payload = REVIEW_USER_PROMPT_SLIM.format(
        user_request=user_request,
        doc_type=classify.get("doc_type", ""),
        law_domain=classify.get("law_domain", ""),
        gate_errors=gate_errors,
        draft_text=draft_text,
    )

    logger.info(
        "[REVIEW] slim payload | user_request=%d chars | draft=%d chars | gate_errors=%d chars",
        len(user_request), len(draft_text), len(gate_errors),
    )

    structured_llm = review_openai_model.with_structured_output(ReviewNode)
    human_message = HumanMessage(content=user_payload)

    # Log approximate token counts for cost tracking
    _sys_text = build_review_system_prompt(inline_fix=inline_fix_enabled)
    _approx_input_chars = len(_sys_text) + len(user_payload)
    logger.info(
        "[REVIEW] prompt size | system=%d chars | user=%d chars | total≈%d tokens (est)",
        len(_sys_text), len(user_payload), _approx_input_chars // 4,
    )

    route_kwargs = dict(
        review_count=review_count, state=state,
        inline_fix_enabled=inline_fix_enabled,
    )

    # Attempt 1 — structured output.
    try:
        messages = [
            SystemMessage(content=_sys_text),
            human_message,
        ]
        response = structured_llm.invoke(messages)
        # Log token usage from response metadata if available
        _meta = getattr(response, "response_metadata", None) or {}
        _usage = _meta.get("token_usage") or _meta.get("usage") or {}
        if _usage:
            logger.info(
                "[REVIEW] token usage | input=%s | output=%s | total=%s",
                _usage.get("prompt_tokens", "?"),
                _usage.get("completion_tokens", "?"),
                _usage.get("total_tokens", "?"),
            )
        result = _as_dict(response)
        return _route_after_review(result=result, elapsed=time.perf_counter() - t0, **route_kwargs)
    except Exception as first_exc:
        logger.error("[REVIEW] attempt1 failed (%.1fs): %s", time.perf_counter() - t0, first_exc)

    # Attempt 2 — structured output with retry suffix.
    try:
        retry_messages = [
            SystemMessage(content=build_review_system_prompt(retry=True, inline_fix=inline_fix_enabled)),
            human_message,
        ]
        response = structured_llm.invoke(retry_messages)
        result = _as_dict(response)
        return _route_after_review(result=result, elapsed=time.perf_counter() - t0, **route_kwargs)
    except Exception as second_exc:
        logger.warning(
            "[REVIEW] attempt2 structured output failed (%.1fs): %s — trying raw extraction",
            time.perf_counter() - t0, second_exc,
        )

    # Attempt 3 — raw model call + JSON extraction.
    try:
        raw_messages = [
            SystemMessage(content=build_review_system_prompt(retry=True, inline_fix=inline_fix_enabled)),
            human_message,
        ]
        raw_response = review_openai_model.invoke(raw_messages)
        # Log token usage from raw response
        _raw_meta = getattr(raw_response, "response_metadata", None) or {}
        _raw_usage = _raw_meta.get("token_usage") or _raw_meta.get("usage") or {}
        if _raw_usage:
            logger.info(
                "[REVIEW] attempt3 token usage | input=%s | output=%s | total=%s",
                _raw_usage.get("prompt_tokens", "?"),
                _raw_usage.get("completion_tokens", "?"),
                _raw_usage.get("total_tokens", "?"),
            )
        raw_text = getattr(raw_response, "content", "") or ""
        parsed = extract_json_from_text(raw_text)
        if parsed and "review" not in parsed and "review_pass" in parsed:
            parsed = {"review": parsed}
        if parsed and parsed.get("review") is not None:
            logger.info("[REVIEW] attempt3 raw extraction succeeded (%.1fs)", time.perf_counter() - t0)
            return _route_after_review(result=parsed, elapsed=time.perf_counter() - t0, **route_kwargs)
        else:
            raise ValueError("raw extraction produced no review data")
    except Exception as raw_exc:
        logger.error("[REVIEW] ✗ failed after 3 attempts (%.1fs): %s", time.perf_counter() - t0, raw_exc)
        fallback = {
            "review": {
                "review_pass": False,
                "blocking_issues": [
                    {"issue": f"review_node failed: {raw_exc}", "fix": "Retry draft", "location": "review_node"}
                ],
                "non_blocking_issues": [],
                "unsupported_statements": [],
                "final_artifacts": [],
            }
        }
        return Command(
            update={"review": fallback, "review_count": review_count, "errors": [f"review_node failed: {raw_exc}"]},
            goto=END,
        )

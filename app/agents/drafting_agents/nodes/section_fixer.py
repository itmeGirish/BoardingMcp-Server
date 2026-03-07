"""Section Fixer Node — LLM, targeted patch per flagged section.

Receives blocking issues from review. Fixes each section individually.
Patch-only mode: corrects the section body, wrapper re-inserts heading.
Max 2 fix attempts per section. After fixes → postprocess(light=True) → END.

Pipeline position: review (has blocking) → **section_fixer** → postprocess(light) → END
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END
from langgraph.types import Command

from ....config import logger, settings
from ....services import draft_ollama_model as draft_openai_model
from ..prompts.section_fixer import build_fixer_system_prompt, build_fixer_user_prompt
from ..states import DraftingState
from ._utils import _as_dict, build_mandatory_provisions_context

_MAX_FIX_ATTEMPTS = 2


def _find_section_in_draft(draft_text: str, section_id: str, filled_sections: List[Dict]) -> str:
    """Find the text of a specific section from filled_sections."""
    for sec in filled_sections:
        if isinstance(sec, dict) and sec.get("section_id") == section_id:
            return sec.get("text", "")
    return ""


def _build_fix_context(
    state: DraftingState,
    section_id: str,
) -> str:
    """Build relevant context for fixing a section."""
    intake = _as_dict(state.get("intake"))
    mandatory_provisions = _as_dict(state.get("mandatory_provisions"))
    court_fee = _as_dict(state.get("court_fee"))

    parts: List[str] = []

    # Facts summary
    facts = intake.get("facts", {})
    if isinstance(facts, dict):
        summary = facts.get("summary", "")
        if summary:
            parts.append(f"FACTS: {summary}")
        amounts = facts.get("amounts", {})
        if isinstance(amounts, dict) and amounts.get("principal"):
            parts.append(f"PRINCIPAL AMOUNT: Rs. {amounts['principal']:,.0f}/-")

    # Evidence
    evidence = intake.get("evidence", [])
    if isinstance(evidence, list) and evidence:
        parts.append("EVIDENCE:")
        for item in evidence:
            if isinstance(item, dict):
                parts.append(f"  [{item.get('type', '')}] {item.get('description', '')}")

    # Mandatory provisions
    mp_context = build_mandatory_provisions_context(mandatory_provisions)
    if mp_context:
        parts.append(f"ENRICHMENT:\n{mp_context}")

    # Court fee
    if court_fee:
        cf_summary = (court_fee.get("summary") or "").strip()
        if cf_summary:
            parts.append(f"COURT FEE CONTEXT: {cf_summary[:300]}")

    return "\n".join(parts) if parts else "(No additional context available)"


def section_fixer_node(state: DraftingState) -> Command:
    """Fix sections flagged with blocking issues by review."""
    logger.info("[SECTION_FIXER] ▶ start")
    t0 = time.perf_counter()

    review = _as_dict(state.get("review"))
    review_data = review.get("review") if isinstance(review.get("review"), dict) else review
    blocking_issues = review_data.get("blocking_issues", [])

    if not blocking_issues:
        logger.info("[SECTION_FIXER] no blocking issues — skipping")
        current_draft = _as_dict(state.get("draft"))
        return Command(
            update={"final_draft": current_draft},
            goto=END,
        )

    filled_sections = state.get("filled_sections", [])
    draft = _as_dict(state.get("draft"))
    artifacts = draft.get("draft_artifacts", [])
    draft_text = artifacts[0].get("text", "") if artifacts else ""

    system_prompt = build_fixer_system_prompt()
    sections_fixed = 0
    total_attempts = 0

    # Group issues by section_id
    issues_by_section: Dict[str, List[Dict]] = {}
    for issue in blocking_issues:
        if isinstance(issue, dict):
            sid = issue.get("section_id", "unknown")
            issues_by_section.setdefault(sid, []).append(issue)

    # Fix each section
    updated_sections: Dict[str, str] = {}
    for sid, issues in issues_by_section.items():
        section_text = _find_section_in_draft(draft_text, sid, filled_sections)
        if not section_text:
            logger.warning("[SECTION_FIXER] section %s not found in filled_sections", sid)
            continue

        context = _build_fix_context(state, sid)

        # Apply each issue fix sequentially
        current_text = section_text
        for issue in issues:
            fix_instruction = issue.get("fix_instruction") or issue.get("fix", "")
            issue_type = issue.get("issue_type") or issue.get("issue", "")
            quote = issue.get("quote", "")

            for attempt in range(_MAX_FIX_ATTEMPTS):
                total_attempts += 1
                try:
                    user_prompt = build_fixer_user_prompt(
                        section_id=sid,
                        section_text=current_text,
                        issue_type=issue_type,
                        fix_instruction=fix_instruction,
                        quote=quote,
                        context=context,
                    )

                    messages = [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=user_prompt),
                    ]
                    response = draft_openai_model.invoke(messages)
                    fixed_text = (getattr(response, "content", "") or "").strip()

                    if fixed_text and len(fixed_text) > 50:
                        current_text = fixed_text
                        sections_fixed += 1
                        logger.info(
                            "[SECTION_FIXER] %s: fixed issue %r (attempt %d)",
                            sid, issue_type, attempt + 1,
                        )
                        break
                    else:
                        logger.warning(
                            "[SECTION_FIXER] %s: empty/short fix output (attempt %d)",
                            sid, attempt + 1,
                        )
                except Exception as exc:
                    logger.error(
                        "[SECTION_FIXER] %s: error (attempt %d): %s",
                        sid, attempt + 1, exc,
                    )

        updated_sections[sid] = current_text

    # Rebuild draft text with fixed sections
    if updated_sections and artifacts:
        full_text = artifacts[0].get("text", "")
        for sid, new_text in updated_sections.items():
            old_text = _find_section_in_draft("", sid, filled_sections)
            if old_text and old_text in full_text:
                full_text = full_text.replace(old_text, new_text)

        fixed_artifact = {**artifacts[0], "text": full_text}
        fixed_draft = {"draft_artifacts": [fixed_artifact]}
    else:
        fixed_draft = draft

    elapsed = time.perf_counter() - t0
    logger.info(
        "[SECTION_FIXER] ✓ done (%.1fs) | sections_fixed=%d | attempts=%d",
        elapsed, sections_fixed, total_attempts,
    )

    return Command(
        update={
            "draft": fixed_draft,
            "final_draft": fixed_draft,
            "postprocess_light": True,
        },
        goto="postprocess",
    )

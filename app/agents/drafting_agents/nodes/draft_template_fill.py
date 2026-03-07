"""v8.1 Template Assembly + LLM Gap Fill + Document Merge node.

Pipeline position: court_fee → **draft_template_fill** → evidence_anchoring

Three phases in ONE node:
  Phase 1: Template Assembly (<100ms, deterministic)
  Phase 2: LLM Gap Fill (15-60s, 1 LLM call)
  Phase 3: Document Merge (<100ms, deterministic)

Fallback: if template assembly or gap fill fails → route to draft_freetext.
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END
from langgraph.types import Command

from ....config import logger, settings
from ....services import draft_ollama_model as draft_openai_model
from ..prompts.gap_fill_prompt import (
    build_gap_fill_system_prompt,
    build_gap_fill_user_prompt,
    merge_template_with_gaps,
    parse_gap_fill_response,
    renumber_paragraphs,
)
from ..states import DraftingState
from ..templates.engine import TemplateEngine
from ._utils import _as_dict, _as_json


# ---------------------------------------------------------------------------
# Helpers (reused from draft_single_call)
# ---------------------------------------------------------------------------

def _build_facts_summary(intake: Dict[str, Any]) -> str:
    """Build a summary of extracted facts for the gap-fill prompt."""
    facts = intake.get("facts", {})
    if hasattr(facts, "model_dump"):
        facts = facts.model_dump()
    if not isinstance(facts, dict):
        return ""

    parts: List[str] = []
    summary = facts.get("summary", "")
    if summary:
        parts.append(summary)

    chronology = facts.get("chronology", [])
    if chronology:
        parts.append("CHRONOLOGY:")
        for item in chronology:
            if isinstance(item, dict):
                date = item.get("date", "")
                event = item.get("event", "")
                parts.append(f"  - {date}: {event}" if date else f"  - {event}")

    amounts = facts.get("amounts", {})
    if isinstance(amounts, dict):
        if hasattr(amounts, "model_dump"):
            amounts = amounts.model_dump()
        for k, v in amounts.items():
            if v is not None:
                parts.append(f"  {k}: {v}")

    return "\n".join(parts)


def _build_parties_context(intake: Dict[str, Any]) -> str:
    """Build a parties context string."""
    parties = intake.get("parties", {})
    if hasattr(parties, "model_dump"):
        parties = parties.model_dump()
    if not isinstance(parties, dict):
        return ""

    parts: List[str] = []
    primary = parties.get("primary", {})
    if hasattr(primary, "model_dump"):
        primary = primary.model_dump()
    if primary:
        parts.append(f"PLAINTIFF: {primary.get('name', '{{PLAINTIFF_NAME}}')} "
                     f"({primary.get('occupation', '')}), {primary.get('address', '')}")

    opposite = parties.get("opposite", [])
    for i, d in enumerate(opposite):
        if hasattr(d, "model_dump"):
            d = d.model_dump()
        parts.append(f"DEFENDANT {i+1}: {d.get('name', '{{DEFENDANT_NAME}}')} "
                     f"({d.get('occupation', '')}), {d.get('address', '')}")

    return "\n".join(parts)


def _build_evidence_context(intake: Dict[str, Any]) -> str:
    """Build evidence list for the gap-fill prompt."""
    evidence = intake.get("evidence", [])
    if not evidence:
        return ""

    parts: List[str] = []
    for i, ev in enumerate(evidence):
        if hasattr(ev, "model_dump"):
            ev = ev.model_dump()
        if isinstance(ev, dict):
            parts.append(f"Annexure {chr(65+i)}: {ev.get('type', '')} — {ev.get('description', '')}")

    return "\n".join(parts)


def _build_verified_provisions(mandatory_provisions: Dict[str, Any]) -> str:
    """Build verified provisions string for gap fill."""
    provisions = mandatory_provisions.get("verified_provisions") or []
    if not provisions:
        return ""

    lines: List[str] = []
    for p in provisions:
        if isinstance(p, dict):
            sec = p.get("section", "")
            act = p.get("act", "")
            text = p.get("text", "")
            line = f"- {sec} {act}"
            if text:
                line += f": {text[:300]}"
            lines.append(line)

    return "\n".join(lines)


def _build_rag_context(rag: Dict[str, Any]) -> str:
    """Build RAG context from top chunks."""
    chunks = (rag.get("chunks") or [])[:5]  # top 5 only
    if not chunks:
        return ""

    lines: List[str] = []
    for i, c in enumerate(chunks):
        if isinstance(c, dict):
            text = c.get("text", "")[:500]
            source = c.get("source", {})
            book = source.get("book", "") if isinstance(source, dict) else ""
            lines.append(f"[{i+1}] {book}: {text}")

    return "\n\n".join(lines)


def _strip_markdown_fences(text: str) -> str:
    """Strip markdown code fences if LLM wraps output."""
    stripped = re.sub(r"^```(?:text|plaintext|plain)?\s*\n?", "", text.strip())
    stripped = re.sub(r"\n?```\s*$", "", stripped)
    return stripped.strip()


def _clean_encoding_artifacts(text: str) -> str:
    """Clean Unicode control chars and garbled apostrophes from LLM output."""
    text = text.replace("\ufffd", "-")
    text = text.replace("\u200b", "").replace("\u200c", "")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f](?=[a-z])", "'", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return text


def _collect_placeholders(text: str) -> List[Dict[str, str]]:
    """Find all {{PLACEHOLDER}} patterns in text."""
    placeholders: List[Dict[str, str]] = []
    seen: set = set()
    for m in re.finditer(r"\{\{(\w+)\}\}", text):
        key = m.group(1)
        if key not in seen and not key.startswith("GENERATE"):
            seen.add(key)
            placeholders.append({"key": key, "reason": "Detail not provided — verify before filing"})
    return placeholders


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------

async def draft_template_fill_node(state: DraftingState) -> Command:
    """v8.1: Template Assembly + LLM Gap Fill + Document Merge.

    Phase 1: TemplateEngine.assemble() builds 15+ deterministic sections
    Phase 2: LLM fills 3 gaps (facts, breach, damages) — ~5-12K chars
    Phase 3: merge_template_with_gaps() inserts LLM output into template

    Fallback: if any phase fails → route to draft_freetext.
    """
    logger.info("[DRAFT_TEMPLATE_FILL] ▶ start (v8.1 template + gap fill)")
    t0 = time.perf_counter()

    user_request = (state.get("user_request") or "").strip()
    intake = _as_dict(state.get("intake"))
    classify = _as_dict(state.get("classify"))
    rag = _as_dict(state.get("rag"))
    court_fee = _as_dict(state.get("court_fee"))
    mandatory_provisions = _as_dict(state.get("mandatory_provisions"))
    lkb_brief = _as_dict(state.get("lkb_brief"))

    doc_type = classify.get("doc_type", "")
    cause_type = classify.get("cause_type", "")

    # -----------------------------------------------------------------------
    # Phase 1: Template Assembly (<100ms)
    # -----------------------------------------------------------------------
    try:
        engine = TemplateEngine()
        assembled_template = engine.assemble(
            intake=intake,
            classify=classify,
            lkb_brief=lkb_brief,
            mandatory_provisions=mandatory_provisions,
            court_fee=court_fee,
            user_request=user_request,
        )
        t_assembly = time.perf_counter() - t0
        logger.info(
            "[DRAFT_TEMPLATE_FILL] Phase 1 ✓ template assembled (%.0fms) | chars=%d",
            t_assembly * 1000, len(assembled_template),
        )
    except Exception as exc:
        logger.error("[DRAFT_TEMPLATE_FILL] Phase 1 ✗ template assembly failed: %s", exc)
        return Command(
            update={"errors": [f"template_assembly: {exc}"]},
            goto="draft_freetext",
        )

    # -----------------------------------------------------------------------
    # Phase 2: LLM Gap Fill (15-60s)
    # -----------------------------------------------------------------------
    facts_summary = _build_facts_summary(intake)
    parties_context = _build_parties_context(intake)
    evidence_context = _build_evidence_context(intake)
    verified_provisions = _build_verified_provisions(mandatory_provisions)
    rag_context = _build_rag_context(rag)

    # Get damages categories from LKB
    damages_categories = lkb_brief.get("damages_categories", [])

    system_prompt = build_gap_fill_system_prompt()
    user_prompt = build_gap_fill_user_prompt(
        user_request=user_request,
        assembled_template=assembled_template,
        facts_summary=facts_summary,
        parties_context=parties_context,
        evidence_context=evidence_context,
        verified_provisions=verified_provisions,
        rag_context=rag_context,
        cause_type=cause_type,
        damages_categories=damages_categories,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    model = draft_openai_model.resolve_model() if hasattr(draft_openai_model, "resolve_model") else draft_openai_model
    if model is None:
        logger.error("[DRAFT_TEMPLATE_FILL] ✗ draft_openai_model unavailable")
        return Command(
            update={"errors": ["draft_template_fill: model unavailable"]},
            goto="draft_freetext",
        )

    llm_response = ""
    for attempt in range(1, 3):
        try:
            response = model.invoke(messages)
            raw_text = getattr(response, "content", "") or ""
            logger.info(
                "[DRAFT_TEMPLATE_FILL] Phase 2 attempt %d | raw_len=%d",
                attempt, len(raw_text),
            )

            cleaned = _strip_markdown_fences(raw_text)
            cleaned = _clean_encoding_artifacts(cleaned)

            if len(cleaned) >= 200:
                llm_response = cleaned
                break
            else:
                logger.warning(
                    "[DRAFT_TEMPLATE_FILL] attempt %d too short (%d chars)",
                    attempt, len(cleaned),
                )
        except Exception as exc:
            logger.error("[DRAFT_TEMPLATE_FILL] attempt %d failed: %s", attempt, exc)

    if not llm_response:
        logger.error("[DRAFT_TEMPLATE_FILL] Phase 2 ✗ gap fill failed — fallback to freetext")
        return Command(
            update={"errors": ["draft_template_fill: gap fill failed"]},
            goto="draft_freetext",
        )

    t_gap = time.perf_counter() - t0
    logger.info(
        "[DRAFT_TEMPLATE_FILL] Phase 2 ✓ gap fill done (%.1fs) | llm_chars=%d",
        t_gap, len(llm_response),
    )

    # -----------------------------------------------------------------------
    # Phase 3: Document Merge (<100ms)
    # -----------------------------------------------------------------------
    try:
        gaps = parse_gap_fill_response(llm_response)
        filled_count = sum(1 for v in gaps.values() if v)
        logger.info(
            "[DRAFT_TEMPLATE_FILL] Phase 3 parsed gaps | filled=%d/3 (facts=%d, breach=%d, damages=%d)",
            filled_count,
            len(gaps.get("facts", "")),
            len(gaps.get("breach", "")),
            len(gaps.get("damages", "")),
        )

        merged = merge_template_with_gaps(assembled_template, gaps)
        merged = renumber_paragraphs(merged)
        merged = _clean_encoding_artifacts(merged)

        t_merge = time.perf_counter() - t0
        logger.info(
            "[DRAFT_TEMPLATE_FILL] Phase 3 ✓ merged (%.0fms total) | final_chars=%d",
            t_merge * 1000, len(merged),
        )
    except Exception as exc:
        logger.error("[DRAFT_TEMPLATE_FILL] Phase 3 ✗ merge failed: %s", exc)
        return Command(
            update={"errors": [f"template_merge: {exc}"]},
            goto="draft_freetext",
        )

    # If merge left unfilled markers, warn but continue
    unfilled = re.findall(r"\{\{SECTION_NOT_GENERATED\}\}", merged)
    if unfilled:
        logger.warning(
            "[DRAFT_TEMPLATE_FILL] %d unfilled gap markers remain", len(unfilled),
        )

    # Collect placeholders
    placeholders = _collect_placeholders(merged)

    # Extract title
    title = doc_type.replace("_", " ").title()
    for line in merged.split("\n")[:15]:
        stripped = line.strip().upper()
        if any(stripped.startswith(p) for p in (
            "SUIT FOR", "APPLICATION FOR", "PLAINT FOR", "PARTITION",
            "DAMAGES CLAIM", "PETITION FOR", "COMMERCIAL SUIT",
        )):
            title = line.strip()
            break

    draft_artifact = {
        "doc_type": doc_type,
        "title": title,
        "text": merged,
        "placeholders_used": placeholders,
        "citations_used": [],
    }

    elapsed = time.perf_counter() - t0
    logger.info(
        "[DRAFT_TEMPLATE_FILL] ✓ done (%.1fs) | template_chars=%d | llm_chars=%d | final_chars=%d | placeholders=%d",
        elapsed, len(assembled_template), len(llm_response), len(merged), len(placeholders),
    )

    return Command(
        update={"draft": {"draft_artifacts": [draft_artifact]}},
        goto="evidence_anchoring",
    )

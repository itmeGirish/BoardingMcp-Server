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
from ..lkb.causes._family_defaults import resolve_gap_definitions
from ..templates.engine import TemplateEngine
from ._utils import _as_dict, _as_json


_CONTRACT_DAMAGES_CAUSE_TYPES = {
    "breach_of_contract",
    "breach_dealership_franchise",
    "breach_employment",
    "breach_construction",
    "supply_service_contract",
    "agency_dispute",
}


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
            parts.append(f"Annexure P-{i+1}: {ev.get('type', '')} — {ev.get('description', '')}")

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


def _build_draft_plan_context(civil_draft_plan: Dict[str, Any], decision_ir: Dict[str, Any] | None = None) -> str:
    """Build a compact civil draft-plan context for the gap-fill prompt.

    Includes forbidden constraints from decision_ir so LLM knows what to avoid.
    """
    if not civil_draft_plan:
        return ""

    parts: List[str] = []
    family = civil_draft_plan.get("family", "")
    cause_type = civil_draft_plan.get("cause_type", "") or civil_draft_plan.get("subtype", "")
    if family or cause_type:
        parts.append(f"Family: {family} | Cause type: {cause_type}")

    required_reliefs = civil_draft_plan.get("required_reliefs") or []
    if required_reliefs:
        parts.append("Required reliefs: " + ", ".join(required_reliefs))

    sections = civil_draft_plan.get("required_sections") or []
    if sections:
        parts.append("Required sections: " + ", ".join(sections[:12]))

    missing_fields = civil_draft_plan.get("missing_fields") or []
    if missing_fields:
        parts.append("Missing fields to preserve as placeholders: " + ", ".join(missing_fields[:10]))

    evidence = civil_draft_plan.get("evidence_checklist") or []
    if evidence:
        parts.append("Evidence focus: " + ", ".join(evidence[:8]))

    red_flags = civil_draft_plan.get("red_flags") or []
    if red_flags:
        parts.append("Red flags: " + " | ".join(red_flags))

    # Emit applicability compiler constraints (from decision_ir)
    _decision = decision_ir or {}
    forbidden_statutes = _decision.get("forbidden_statutes") or []
    if forbidden_statutes:
        parts.append("DO NOT CITE (inapplicable to this case): " + ", ".join(forbidden_statutes))

    forbidden_damages = _decision.get("forbidden_damages") or []
    if forbidden_damages:
        display = [d.replace("_", " ") for d in forbidden_damages]
        parts.append("DO NOT CLAIM AS RELIEF: " + ", ".join(display))

    forbidden_reliefs = _decision.get("forbidden_reliefs") or []
    if forbidden_reliefs:
        display = [r.replace("_", " ") for r in forbidden_reliefs]
        parts.append("FORBIDDEN RELIEFS: " + ", ".join(display))

    forbidden_doctrines = _decision.get("forbidden_doctrines") or []
    if forbidden_doctrines:
        display = [d.replace("_", " ") for d in forbidden_doctrines]
        parts.append("DO NOT PLEAD THESE LEGAL THEORIES: " + ", ".join(display))

    return "\n".join(parts)


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


def _sanitize_contract_damages_drift(text: str, cause_type: str) -> str:
    """Strip specific-performance phrasing from a plain contract-damages draft."""
    if not text or cause_type != "breach_of_contract":
        return text

    patterns = [
        r"(?im)^\s*\d+\.\s+[^.\n]*\bready and willing\b[^.\n]*\.\s*",
        r"(?im)^\s*\d+\.\s+[^.\n]*\breadiness and willingness\b[^.\n]*\.\s*",
        r"(?im)^\s*\d+\.\s+[^.\n]*\bspecific performance\b[^.\n]*\.\s*",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text)

    text = re.sub(
        r"(?im)(^\s*\d+\.\s+The Defendant[^.\n]*?)(?:,\s*(?:thereby\s+)?causing[^.\n]*)\.",
        r"\1.",
        text,
    )
    text = re.sub(
        r"(?im)(^\s*\d+\.\s+The breach[^.\n]*?)(?:,\s*(?:thereby\s+)?causing[^.\n]*)\.",
        r"\1.",
        text,
    )
    text = re.sub(
        r"(?i)\bquantif(?:ies|ied)\s+the\s+actual\s+loss\s+at\s+\{\{TOTAL_SUIT_VALUE\}\}(?!/-)",
        lambda m: m.group(0).replace("{{TOTAL_SUIT_VALUE}}", "Rs. {{TOTAL_SUIT_VALUE}}/-"),
        text,
    )
    text = re.sub(
        r"(?i)\bactual\s+loss\s+amounting\s+to\s+\{\{TOTAL_SUIT_VALUE\}\}(?!/-)",
        lambda m: m.group(0).replace("{{TOTAL_SUIT_VALUE}}", "Rs. {{TOTAL_SUIT_VALUE}}/-"),
        text,
    )
    text = re.sub(
        r"(?i)entered into\s+\{\{CONTRACT_DETAILS\}\}",
        "entered into a written agreement regarding {{CONTRACT_DETAILS}}",
        text,
    )
    text = text.replace(
        "calling upon the Defendant to perform the obligations",
        "calling upon the Defendant to comply with the terms of the agreement",
    )
    text = text.replace(
        "did not perform the contractual obligations",
        "did not cure the contractual default",
    )
    text = text.replace(
        "failed to perform the contractual obligations by",
        "committed default in performance by",
    )
    text = text.replace(
        "failed to perform the contractual obligations stipulated therein by",
        "committed default under the agreement on",
    )
    text = text.replace(
        "failed to perform the contractual obligations stipulated therein",
        "committed default under the agreement",
    )
    text = text.replace(
        "remained in default as on {{DATE_OF_BREACH}}",
        "committed breach on {{DATE_OF_BREACH}}",
    )
    text = text.replace(
        "failed to perform the agreed obligations by",
        "committed default under the agreement on",
    )
    text = text.replace(
        "failed to perform the contractual obligations due under the agreement",
        "committed default under the agreement",
    )
    text = text.replace(
        "failing to perform the obligations undertaken therein",
        "remaining in default of the obligations undertaken therein",
    )
    text = text.replace(
        "continues to remain in default",
        "has not cured the default",
    )
    text = text.replace(
        "remained in default of the agreed terms",
        "has not cured the contractual default",
    )
    text = text.replace(
        "has not performed the contractual obligations till date",
        "has not cured the default",
    )

    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _build_contract_gap_fill_fallback(cause_type: str, damages_categories: List[str]) -> str:
    """Deterministic fallback when contract gap-fill LLM is unavailable.

    This preserves a filing-grade Section 73 damages draft for contract causes
    rather than returning a blocked template artifact on transient model failures.
    """
    if cause_type not in _CONTRACT_DAMAGES_CAUSE_TYPES:
        return ""

    damages_lines = [
        "10. By reason of the Defendant's failure to perform, the Plaintiff has suffered loss and damage under the heads particularised in the Schedule of Damages and Annexure P-3.",
        "11. The total damages claimed are quantified at Rs. {{TOTAL_SUIT_VALUE}}/-, being the direct and natural consequence of the Defendant's breach.",
    ]
    if damages_categories == ["actual_loss"]:
        damages_lines = [
            "10. By reason of the Defendant's failure to perform, the Plaintiff has suffered actual and direct financial loss.",
            "11. The Plaintiff quantifies the said loss at Rs. {{TOTAL_SUIT_VALUE}}/-, and the computation with supporting material is set out in Annexure P-3.",
        ]

    return (
        "{{GENERATE:FACTS}}\n"
        "5. On {{DATE_OF_CONTRACT}}, the Plaintiff and the Defendant entered into a written agreement regarding {{CONTRACT_DETAILS}}, copy whereof is filed as Annexure P-1.\n"
        "6. The Plaintiff duly performed all obligations required on its part under the agreement, specifically {{PLAINTIFF_PERFORMANCE_DETAILS}}.\n"
        "7. Under the terms of the agreement, the Defendant was required to {{DEFENDANT_OBLIGATION}}.\n\n"
        "{{GENERATE:BREACH}}\n"
        "8. The Defendant failed to perform the contractual obligations on {{DATE_OF_BREACH}}.\n"
        "9. The Plaintiff issued legal notice dated {{NOTICE_DATE}} calling upon the Defendant to perform its obligations, but the Defendant did not comply. A copy of the notice is filed as Annexure P-2.\n\n"
        "{{GENERATE:DAMAGES}}\n"
        + "\n".join(damages_lines)
    )


def _build_blocked_artifact(classify: Dict[str, Any], heading: str, issues: List[str]) -> Dict[str, Any]:
    doc_type = classify.get("doc_type", "civil_draft")
    lines = [heading, "", "The civil drafting pipeline stopped before finalization for the following reasons:"]
    for idx, issue in enumerate(issues, start=1):
        lines.append(f"{idx}. {issue}")
    lines.append("")
    lines.append("Correct the above issues and rerun drafting.")
    return {
        "draft_artifacts": [
            {
                "doc_type": doc_type,
                "title": heading,
                "text": "\n".join(lines),
                "placeholders_used": [],
                "citations_used": [],
            }
        ]
    }


def _template_failure_command(classify: Dict[str, Any], cause_type: str, issue: str) -> Command:
    """Block on template failure for ALL families — no silent fallback to legacy freetext."""
    blocked = _build_blocked_artifact(classify, "TEMPLATE DRAFTING FAILED", [issue])
    logger.warning("[DRAFT_TEMPLATE_FILL] template failure blocked | cause=%s | issue=%s", cause_type, issue)
    return Command(
        update={
            "errors": [issue],
            "final_draft": blocked,
        },
        goto=END,
    )


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
    decision_ir = _as_dict(state.get("decision_ir"))
    civil_draft_plan = _as_dict(state.get("civil_draft_plan")) or _as_dict(state.get("plan_ir"))

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
            decision_ir=decision_ir,
        )
        t_assembly = time.perf_counter() - t0
        logger.info(
            "[DRAFT_TEMPLATE_FILL] Phase 1 ✓ template assembled (%.0fms) | chars=%d",
            t_assembly * 1000, len(assembled_template),
        )
    except Exception as exc:
        logger.error("[DRAFT_TEMPLATE_FILL] Phase 1 ✗ template assembly failed: %s", exc)
        return _template_failure_command(classify, cause_type, f"template_assembly: {exc}")

    # -----------------------------------------------------------------------
    # Phase 2: LLM Gap Fill (15-60s)
    # -----------------------------------------------------------------------
    facts_summary = _build_facts_summary(intake)
    parties_context = _build_parties_context(intake)
    evidence_context = _build_evidence_context(intake)
    verified_provisions = _build_verified_provisions(mandatory_provisions)
    rag_context = _build_rag_context(rag)
    draft_plan_context = _build_draft_plan_context(civil_draft_plan, decision_ir)

    # Get damages categories from LKB, filtered through decision_ir
    _allowed_damages = list(decision_ir.get("allowed_damages") or [])
    _forbidden_damages = set(decision_ir.get("forbidden_damages") or [])
    if cause_type in {"permanent_injunction", "mandatory_injunction"}:
        damages_categories = []
    else:
        if _allowed_damages:
            damages_categories = [d for d in _allowed_damages if d not in _forbidden_damages]
        else:
            raw_damages = lkb_brief.get("damages_categories", [])
            damages_categories = [d for d in raw_damages if d not in _forbidden_damages]

    # Get facts_must_cover from LKB for guided fact-pleading
    facts_must_cover = lkb_brief.get("facts_must_cover") or []

    # v10.0: Resolve gap_definitions (from LKB entry or family defaults)
    gap_definitions = resolve_gap_definitions(lkb_brief, cause_type)

    system_prompt = build_gap_fill_system_prompt(gap_definitions=gap_definitions)
    user_prompt = build_gap_fill_user_prompt(
        user_request=user_request,
        assembled_template=assembled_template,
        facts_summary=facts_summary,
        parties_context=parties_context,
        evidence_context=evidence_context,
        verified_provisions=verified_provisions,
        rag_context=rag_context,
        draft_plan_context=draft_plan_context,
        cause_type=cause_type,
        damages_categories=damages_categories,
        facts_must_cover=facts_must_cover,
        gap_definitions=gap_definitions,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    model = draft_openai_model.resolve_model() if hasattr(draft_openai_model, "resolve_model") else draft_openai_model
    if model is None:
        logger.error("[DRAFT_TEMPLATE_FILL] ✗ draft_openai_model unavailable")
        return _template_failure_command(classify, cause_type, "draft_template_fill: model unavailable")

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
        llm_response = _build_contract_gap_fill_fallback(cause_type, damages_categories)
        if llm_response:
            logger.warning(
                "[DRAFT_TEMPLATE_FILL] Phase 2 fallback | cause=%s | using deterministic contract gap-fill",
                cause_type,
            )
        else:
            logger.error("[DRAFT_TEMPLATE_FILL] Phase 2 ✗ gap fill failed — fallback to freetext")
            return _template_failure_command(classify, cause_type, "draft_template_fill: gap fill failed")

    t_gap = time.perf_counter() - t0
    logger.info(
        "[DRAFT_TEMPLATE_FILL] Phase 2 ✓ gap fill done (%.1fs) | llm_chars=%d",
        t_gap, len(llm_response),
    )

    # -----------------------------------------------------------------------
    # Phase 3: Document Merge (<100ms)
    # -----------------------------------------------------------------------
    try:
        gaps = parse_gap_fill_response(llm_response, gap_definitions=gap_definitions)
        filled_count = sum(1 for v in gaps.values() if v)
        total_gaps = len(gaps)
        if gap_definitions:
            gap_sizes = ", ".join(f"{k}={len(v)}" for k, v in gaps.items() if v)
            logger.info(
                "[DRAFT_TEMPLATE_FILL] Phase 3 parsed gaps | filled=%d/%d (%s)",
                filled_count, total_gaps, gap_sizes,
            )
        else:
            logger.info(
                "[DRAFT_TEMPLATE_FILL] Phase 3 parsed gaps | filled=%d/3 (facts=%d, breach=%d, damages=%d)",
                filled_count,
                len(gaps.get("facts", "")),
                len(gaps.get("breach", "")),
                len(gaps.get("damages", "")),
            )

        merged = merge_template_with_gaps(
            assembled_template, gaps, cause_type=cause_type,
            gap_definitions=gap_definitions,
        )
        merged = _sanitize_contract_damages_drift(merged, cause_type)
        merged = renumber_paragraphs(merged)
        merged = _clean_encoding_artifacts(merged)

        t_merge = time.perf_counter() - t0
        logger.info(
            "[DRAFT_TEMPLATE_FILL] Phase 3 ✓ merged (%.0fms total) | final_chars=%d",
            t_merge * 1000, len(merged),
        )
    except Exception as exc:
        logger.error("[DRAFT_TEMPLATE_FILL] Phase 3 ✗ merge failed: %s", exc)
        return _template_failure_command(classify, cause_type, f"template_merge: {exc}")

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
            goto="domain_consistency_gate",
        )

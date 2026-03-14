"""Draft Single Call Node — ONE LLM call produces court-ready document.

v5.0 freetext: LKB-guided plain text generation.
Legacy JSON path: section-keyed JSON (not used in production).

Pipeline position: enrichment → **draft_freetext** → evidence_anchoring
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END
from langgraph.types import Command

from ....config import logger, settings
from ....services import draft_ollama_model as draft_openai_model
from ..lkb.limitation import get_limitation_reference_details, normalize_coa_type
from ..prompts.draft_prompt import (
    build_draft_system_prompt,
    build_draft_user_prompt,
    build_draft_freetext_system_prompt,
    build_draft_freetext_user_prompt,
    build_structured_draft_prompt,
    build_structured_system_prompt,
    get_section_keys,
)
from ..schemas import get_schema
from ..states import DraftingState
from ._utils import (
    _as_dict, _as_json,
    build_court_fee_context,
    build_mandatory_provisions_context,
    extract_json_from_text,
)


def _build_limitation_context(mandatory_provisions: Dict[str, Any]) -> str:
    """Build a limitation context string from enrichment output."""
    lim = mandatory_provisions.get("limitation")
    if not lim or not isinstance(lim, dict):
        return "Limitation article could not be determined. Use {{LIMITATION_ARTICLE}} placeholder."

    details = get_limitation_reference_details(lim)
    article = lim.get("article", "UNKNOWN")
    if article == "UNKNOWN" and not details["citation"]:
        return "Limitation article could not be determined. Use {{LIMITATION_ARTICLE}} placeholder."

    if details["kind"] == "none":
        desc = lim.get("description", "No specific limitation applies.")
        return f"NO LIMITATION APPLIES: {desc}\nDo NOT cite any Limitation Act article in this draft."

    if details["kind"] == "unknown":
        return "Limitation article could not be determined. Use {{LIMITATION_ARTICLE}} placeholder."

    if details["kind"] == "not_applicable" or (
        details["kind"] == "statutory_reference" and not details["is_limitation_act"]
    ):
        desc = lim.get("description", "Limitation is governed by the specific statute or forum.")
        period = lim.get("period", "")
        reason = lim.get("reason", "")
        parts = ["SPECIAL STATUTORY LIMITATION / FORUM RULE:"]
        if details["citation"]:
            parts.append(details["citation"])
        if desc:
            parts.append(desc)
        if period:
            parts.append(f"Period: {period}")
        if reason:
            parts.append(f"Reason: {reason}")
        parts.append("Do NOT convert this into a Limitation Act article unless the source expressly says so.")
        return "\n".join(parts)

    desc = lim.get("description", "")
    period = lim.get("period", "")
    reason = lim.get("reason", "")
    source = lim.get("source", "")

    parts = [details["citation"] or f"Article {article} of the Schedule to the Limitation Act, 1963"]
    if desc:
        parts.append(f"Description: {desc}")
    if period:
        parts.append(f"Period: {period}")
    if reason:
        parts.append(f"Reason: {reason}")
    parts.append(f"(source: {source})")
    return "\n".join(parts)


def _build_verified_provisions_context(mandatory_provisions: Dict[str, Any]) -> str:
    """Build verified provisions string for the draft prompt, grouped by source."""
    provisions = mandatory_provisions.get("verified_provisions") or []
    if not provisions:
        return "No verified provisions available."

    user_cited: List[str] = []
    rag_sourced: List[str] = []
    for p in provisions:
        if isinstance(p, dict):
            sec = p.get("section", "")
            act = p.get("act", "")
            text = p.get("text", "")
            source = p.get("source", "")
            line = f"- {sec} {act}"
            if text:
                line += f": {text[:300]}"
            if source == "rag":
                rag_sourced.append(line)
            else:
                user_cited.append(line)

    parts: List[str] = []
    if user_cited:
        parts.append("USER-CITED / ENRICHMENT (mandatory — cite these):\n" + "\n".join(user_cited))
    if rag_sourced:
        # Deduplicate RAG-sourced provisions (keep first 20 to avoid prompt bloat)
        parts.append("RAG-SOURCED (cite specific section numbers if relevant to this case):\n" + "\n".join(rag_sourced[:20]))
    return "\n\n".join(parts) if parts else "No verified provisions available."


def _build_rag_context(rag: Dict[str, Any], limit: int) -> str:
    """Build RAG context from top chunks, filtering out superseded act references."""
    import re
    from ..lkb import SUPERSEDED_ACTS

    chunks = (rag.get("chunks") or [])[:limit]
    if not chunks:
        return ""

    # Build regex to detect superseded acts in chunk text
    superseded_patterns = []
    for old_act in SUPERSEDED_ACTS:
        # "Specific Relief Act, 1877" or "Specific Relief Act 1877"
        pattern = re.escape(old_act).replace(r",\ ", r",?\s*").replace(r"\ ", r"\s+")
        superseded_patterns.append(pattern)
    superseded_re = re.compile("|".join(superseded_patterns), re.IGNORECASE) if superseded_patterns else None

    lines = []
    skipped = 0
    for i, c in enumerate(chunks):
        if isinstance(c, dict):
            text = c.get("text", "")[:500]
            source = c.get("source", {})
            book = source.get("book", "") if isinstance(source, dict) else ""

            # Skip chunks that primarily reference superseded acts
            if superseded_re and superseded_re.search(text):
                skipped += 1
                continue

            lines.append(f"[Chunk {i+1}] {book}: {text}")

    if skipped:
        logger.info("[DRAFT] filtered %d RAG chunks referencing superseded acts", skipped)

    return "\n\n".join(lines) if lines else "No RAG context available."


def _build_procedural_requirements_context(mandatory_provisions: Dict[str, Any]) -> str:
    """Build procedural requirements context from enrichment output."""
    context = (mandatory_provisions.get("procedural_context") or "").strip()
    if not context:
        return ""

    proc_provisions = mandatory_provisions.get("procedural_provisions") or []
    if proc_provisions:
        prov_lines = [
            f"- {p['section']} {p.get('act', '')}"
            for p in proc_provisions
            if isinstance(p, dict)
        ]
        if prov_lines:
            context += "\n\nExtracted procedural provisions:\n" + "\n".join(prov_lines)

    return context


def _build_lkb_brief_context(lkb_brief: Dict[str, Any], decision_ir: Dict[str, Any] | None = None) -> str:
    """Build a structured legal brief from LKB entry for the draft LLM.

    This tells the LLM exactly what law to cite, what court format to use,
    what damages to claim, and how to structure the cause of action.

    When decision_ir is provided, filters through applicability compiler output:
    - forbidden_statutes are excluded and warned about
    - forbidden_damages are excluded
    - filtered_red_flags replace raw drafting_red_flags
    """
    if not lkb_brief:
        return (
            "LEGAL BRIEF: No specific Legal Knowledge Base entry found for this cause type.\n"
            "Use your legal knowledge and the VERIFIED PROVISIONS provided.\n"
            "For limitation, court fee, and jurisdiction: use {{PLACEHOLDER}} if not certain.\n"
            "Do NOT guess — accuracy is more important than completeness."
        )

    # Extract compiler decisions for filtering
    _decision = decision_ir or {}
    _forbidden_statutes = set(_decision.get("forbidden_statutes") or [])
    _forbidden_damages = set(_decision.get("forbidden_damages") or [])
    _forbidden_reliefs = set(_decision.get("forbidden_reliefs") or [])
    _forbidden_doctrines = set(_decision.get("forbidden_doctrines") or [])
    _allowed_doctrines = _decision.get("allowed_doctrines") or []
    _filtered_red_flags = _decision.get("filtered_red_flags") or []

    lines = ["LEGAL BRIEF (from verified Legal Knowledge Base — follow these precisely):"]

    display = lkb_brief.get("display_name", "")
    if display:
        lines.append(f"\nCASE TYPE: {display}")

    # === SUPERSEDED ACTS WARNING (CRITICAL — put first) ===
    from ..lkb import SUPERSEDED_ACTS
    if SUPERSEDED_ACTS:
        lines.append("\n*** DO NOT CITE — REPEALED / SUPERSEDED STATUTES ***")
        lines.append("The following Acts have been REPEALED. Citing them is a FATAL legal error:")
        for old_act, new_act in SUPERSEDED_ACTS.items():
            if "," in old_act:  # skip duplicates without comma
                lines.append(f"  - WRONG: {old_act} → CORRECT: {new_act}")
        lines.append("If any context mentions these Acts, IGNORE those references completely.")

    primary = lkb_brief.get("primary_acts", [])
    if primary:
        lines.append("\nPRIMARY STATUTES (cite these as the main legal basis):")
        for act_info in primary:
            act = act_info.get("act", "")
            if act in _forbidden_statutes:
                continue  # filtered by applicability compiler
            sections = ", ".join(act_info.get("sections", []))
            lines.append(f"  - {act}: {sections}")
        lines.append("  IMPORTANT: When describing what a provision says, use the text from")
        lines.append("  VERIFIED PROVISIONS — do NOT paraphrase from memory.")
        lines.append("  If the provision text is not available, cite the section number only")
        lines.append("  without attempting to describe its content.")

    alt_acts_raw = lkb_brief.get("alternative_acts", [])
    alt_acts = alt_acts_raw if isinstance(alt_acts_raw, list) else []
    if alt_acts:
        lines.append("\nADDITIONAL STATUTES (cite where facts support):")
        for act_info in alt_acts:
            act = act_info.get("act", "")
            if act in _forbidden_statutes:
                continue  # filtered by applicability compiler
            sections = ", ".join(act_info.get("sections", []))
            lines.append(f"  - {act}: {sections}")

    # Forbidden statutes warning (from applicability compiler)
    if _forbidden_statutes:
        lines.append("\n*** DO NOT CITE — INAPPLICABLE TO THIS CASE ***")
        for fs in _forbidden_statutes:
            lines.append(f"  - {fs}")
        lines.append("  The applicability compiler determined these statutes do not apply.")

    # Forbidden doctrines (from applicability compiler — facts don't support these)
    if _forbidden_doctrines:
        lines.append("\n*** DO NOT PLEAD — UNSUPPORTED BY FACTS ***")
        for fd in _forbidden_doctrines:
            lines.append(f"  - {fd.replace('_', ' ').title()}")
        lines.append("  These legal theories require specific factual triggers that are ABSENT.")
        lines.append("  Pleading them without factual basis is a professional conduct violation.")
    # Allowed doctrines (only these may be used in the draft)
    if _allowed_doctrines:
        lines.append("\nALLOWED LEGAL THEORIES (use ONLY these in the draft):")
        for ad in _allowed_doctrines:
            lines.append(f"  - {ad.replace('_', ' ').title()}")

    lim = lkb_brief.get("limitation", {})
    lim_details = get_limitation_reference_details(lim)
    if lim and (lim.get("article") or lim_details["citation"]):
        if lim_details["kind"] == "none":
            lines.append(f"\nLIMITATION: NO LIMITATION APPLIES")
            lines.append(f"  {lim.get('description', 'No specific limitation for this suit type.')}")
            lines.append("  Do NOT cite any Article of the Limitation Act, 1963.")
        elif lim_details["kind"] == "unknown":
            lines.append("\nLIMITATION: UNKNOWN")
            lines.append("  Verify the applicable limitation provision before filing.")
        elif lim_details["kind"] == "not_applicable":
            lines.append("\nLIMITATION: SPECIAL STATUTORY / FORUM-SPECIFIC RULE")
            lines.append(f"  {lim.get('description', 'No Limitation Act article applies to this proceeding.')}")
        else:
            lines.append(f"\nLIMITATION: {lim_details['citation']}")
        if lim.get("period"):
            lines.append(f"  Period: {lim['period']}")
        if lim.get("from"):
            lines.append(f"  Accrual: {lim['from']}")
        if lim.get("description"):
            lines.append(f"  Description: {lim['description']}")

    detected_court = lkb_brief.get("detected_court", {})
    if not detected_court:
        court_rules = lkb_brief.get("court_rules", {})
        if isinstance(court_rules, dict):
            detected_court = court_rules.get("default", {})
    if detected_court:
        lines.append(f"\nCOURT FORMAT:")
        lines.append(f"  Court: {detected_court.get('court', '')}")
        lines.append(f"  Case numbering: {detected_court.get('format', '')}")
        heading = detected_court.get("heading", "")
        if heading:
            lines.append(f"  Heading template: {heading}")
        proc = detected_court.get("procedural", [])
        if proc:
            lines.append("  MANDATORY procedural requirements:")
            for p in proc:
                lines.append(f"    - {p}")

    damages = lkb_brief.get("damages_categories", [])
    if damages:
        # Filter through applicability compiler
        filtered_damages = [d for d in damages if d not in _forbidden_damages]
        if filtered_damages:
            lines.append(f"\nDAMAGES CATEGORIES (itemise each in prayer with specific amounts):")
            for d in filtered_damages:
                lines.append(f"  - {d.replace('_', ' ').title()}")
        if _forbidden_damages:
            lines.append(f"\n  DO NOT claim these as damages/relief (defence concepts, not plaintiff relief):")
            for fd in _forbidden_damages:
                lines.append(f"    - {fd.replace('_', ' ').title()}")

    coa_type = normalize_coa_type(lkb_brief.get("coa_type") or "")
    coa_guidance = lkb_brief.get("coa_guidance", "")
    if coa_type:
        # Explicit coa_type set in LKB — give strong instruction
        lines.append(f"\nCAUSE OF ACTION TYPE: {coa_type.upper()}")
        if coa_type == "single_event":
            lines.append("  *** CRITICAL: This is a SINGLE EVENT breach. The cause of action arose")
            lines.append("  on ONE date (the breach date). Do NOT write 'continuing cause of action',")
            lines.append("  'continuing breach', or 'continues to this day'. The LOSS may continue,")
            lines.append("  but the BREACH was a single event. Write: 'The cause of action arose on")
            lines.append("  {{DATE}} when the Defendant [breached/terminated/refused].' ***")
        elif coa_type == "continuing":
            lines.append("  This is a continuing cause of action — the breach is ongoing.")
            lines.append("  Write both origin date AND continuing accrual language.")
    else:
        # No explicit coa_type — let LLM determine from case type description
        lines.append(f"\nCAUSE OF ACTION: Determine from the case type description above whether")
        lines.append("  the cause of action is a single event or continuing wrong, and draft")
        lines.append("  accordingly. Use terminology consistent with the case type description.")
    if coa_guidance:
        lines.append(f"  {coa_guidance}")

    defensive = lkb_brief.get("defensive_points", [])
    if defensive:
        lines.append(f"\nDEFENSIVE PLEADING POINTS (include to pre-empt defences):")
        for d in defensive:
            lines.append(f"  - {d.replace('_', ' ')}")

    interest_guidance = lkb_brief.get("interest_guidance", "")
    if interest_guidance:
        lines.append(f"\nINTEREST JUSTIFICATION: {interest_guidance}")

    # Terminology guidance (resolved from conditional — tells LLM exact labels to use)
    terminology = lkb_brief.get("terminology")
    if isinstance(terminology, dict) and not terminology.get("_type"):
        lines.append("\nTERMINOLOGY (use these exact characterizations in the draft):")
        for key, val in terminology.items():
            lines.append(f"  - {key.replace('_', ' ')}: {val}")

    # Mandatory averments
    mandatory_av = lkb_brief.get("mandatory_averments", [])
    if mandatory_av:
        lines.append("\nMANDATORY AVERMENTS (MUST appear in the draft — omission is FATAL):")
        for av in mandatory_av:
            if isinstance(av, dict):
                lines.append(f"  - {av.get('averment', '')}: {av.get('instruction', '')}")
                prov = av.get("provision", "")
                if prov:
                    lines.append(f"    (Required by: {prov})")

    # Partition-specific (and other doc-type-specific) inline section requirements
    mandatory_inline = lkb_brief.get("mandatory_inline_sections", [])
    if mandatory_inline:
        lines.append("\n*** MANDATORY INLINE SECTIONS (MUST include these directly in the plaint body) ***")
        lines.append("  (These are drafting instructions for YOU — do NOT copy these instructions")
        lines.append("   into the draft. Write the actual legal content for each section.)")
        for sec in mandatory_inline:
            placement = sec.get('placement', '')
            lines.append(f"\n  SECTION HEADING: {sec['section']}")
            if placement:
                lines.append(f"  (place this section {placement})")
            lines.append(f"  WHAT TO WRITE: {sec['instruction']}")

    facts_must = lkb_brief.get("facts_must_cover", [])
    if facts_must:
        lines.append("\nFACTS SECTION MUST COVER (each point must appear as a substantive paragraph):")
        for i, point in enumerate(facts_must, 1):
            lines.append(f"  {i}. {point}")

    prayer_template = lkb_brief.get("prayer_template", [])
    if prayer_template:
        lines.append("\nPRAYER — USE THESE EXACT ITEMS (copy statutory citations verbatim — do NOT paraphrase or drop section numbers):")
        for i, item in enumerate(prayer_template, 1):
            lines.append(f"  ({chr(96+i)}) {item}")

    # Anti-fabrication rules
    lines.append("\n*** DO NOT INVENT FACTS ***")
    lines.append("  - Do NOT assert arbitration clause exists/doesn't exist unless user provided that fact.")
    lines.append("  - Do NOT claim mediation was attempted unless user provided mediation details.")
    lines.append("  - Do NOT assert readiness/willingness as a conclusory formula — plead specific acts.")
    lines.append("  - If a fact is unknown, use {{PLACEHOLDER}} — never fabricate.")

    return "\n".join(lines)


async def draft_single_call_node(state: DraftingState) -> Command:
    """ONE LLM call → section-keyed JSON → stored as filled_sections."""
    logger.info("[DRAFT] ▶ start (single-call LKB-guided)")
    t0 = time.perf_counter()

    user_request = (state.get("user_request") or "").strip()
    intake = _as_dict(state.get("intake"))
    classify = _as_dict(state.get("classify"))
    rag = _as_dict(state.get("rag"))
    court_fee = _as_dict(state.get("court_fee"))
    mandatory_provisions = _as_dict(state.get("mandatory_provisions"))
    lkb_brief = _as_dict(state.get("lkb_brief"))

    doc_type = classify.get("doc_type", "")
    law_domain = classify.get("law_domain", "")
    cause_type = classify.get("cause_type", "")

    # Build system prompt (cause_type determines section list)
    system_prompt = build_draft_system_prompt(doc_type, cause_type)

    # Build user prompt with all context
    court_fee_context = build_court_fee_context(
        court_fee, settings.DRAFTING_WEBSEARCH_SOURCE_URLS,
    )
    limitation_context = _build_limitation_context(mandatory_provisions)
    verified_provisions_context = _build_verified_provisions_context(mandatory_provisions)
    rag_context = _build_rag_context(rag, settings.DRAFTING_DRAFT_RAG_LIMIT)
    procedural_requirements_context = _build_procedural_requirements_context(mandatory_provisions)
    decision_ir = _as_dict(state.get("decision_ir"))
    lkb_brief_context = _build_lkb_brief_context(lkb_brief, decision_ir)

    user_prompt = build_draft_user_prompt(
        user_request=user_request,
        doc_type=doc_type,
        law_domain=law_domain,
        jurisdiction=_as_json(intake.get("jurisdiction", {})),
        parties=_as_json(intake.get("parties", {})),
        facts=_as_json(intake.get("facts", {})),
        evidence=_as_json(intake.get("evidence", [])),
        verified_provisions=verified_provisions_context,
        limitation=limitation_context,
        court_fee_context=court_fee_context,
        rag_context=rag_context,
        procedural_requirements=procedural_requirements_context,
        lkb_brief=lkb_brief_context,
    )

    # Invoke LLM
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    section_keys = get_section_keys(doc_type, cause_type)
    filled_sections: Dict[str, str] = {}

    model = draft_openai_model.resolve_model() if hasattr(draft_openai_model, "resolve_model") else draft_openai_model
    if model is None:
        logger.error("[DRAFT] ✗ draft_openai_model unavailable")
        return Command(
            update={"errors": ["draft_single_call: model unavailable"]},
            goto=END,
        )

    for attempt in range(1, 3):
        try:
            response = model.invoke(messages)
            raw_text = getattr(response, "content", "") or ""
            logger.info(
                "[DRAFT] attempt %d raw response length: %d",
                attempt, len(raw_text),
            )

            # Parse JSON from response
            parsed = extract_json_from_text(raw_text)
            if not parsed:
                import json
                try:
                    parsed = json.loads(raw_text.strip())
                except (json.JSONDecodeError, ValueError):
                    pass

            if parsed and isinstance(parsed, dict):
                # Check how many expected keys are present
                found_keys = [k for k in section_keys if k in parsed and parsed[k]]
                if len(found_keys) >= len(section_keys) * 0.5:
                    filled_sections = {k: str(v) for k, v in parsed.items() if isinstance(v, str)}
                    logger.info(
                        "[DRAFT] ✓ attempt %d parsed | keys=%d/%d",
                        attempt, len(found_keys), len(section_keys),
                    )
                    break
                else:
                    logger.warning(
                        "[DRAFT] attempt %d — only %d/%d keys found, retrying",
                        attempt, len(found_keys), len(section_keys),
                    )
            else:
                logger.warning("[DRAFT] attempt %d — could not parse JSON", attempt)

        except Exception as exc:
            logger.error("[DRAFT] attempt %d failed: %s", attempt, exc)

    if not filled_sections:
        logger.error("[DRAFT] ✗ failed after 2 attempts — falling back to old draft node")
        return Command(
            update={"errors": ["draft_single_call: failed to produce section JSON"]},
            goto="draft",
        )

    elapsed = time.perf_counter() - t0
    logger.info(
        "[DRAFT] ✓ done (%.1fs) | sections=%d | keys=%s",
        elapsed, len(filled_sections), list(filled_sections.keys()),
    )

    return Command(
        update={"filled_sections": filled_sections},
        goto="structural_gate",
    )


# ---------------------------------------------------------------------------
# v5.0 FREE-TEXT draft node — plain text output, no JSON parsing
# ---------------------------------------------------------------------------

_FREETEXT_ADVOCATE_BLOCK = """
Through:
{{ADVOCATE_NAME}}
Advocate
Enrollment No. {{ADVOCATE_ENROLLMENT}}
{{ADVOCATE_ADDRESS}}
"""


def _strip_markdown_fences(text: str) -> str:
    """Strip markdown code fences if LLM wraps output."""
    import re
    # Remove ```text ... ``` or ```plaintext ... ``` or bare ``` ... ```
    stripped = re.sub(r"^```(?:text|plaintext|plain)?\s*\n?", "", text.strip())
    stripped = re.sub(r"\n?```\s*$", "", stripped)
    return stripped.strip()


def _collect_placeholders_from_text(text: str) -> List[Dict[str, str]]:
    """Find all {{PLACEHOLDER}} patterns in text."""
    import re
    placeholders: List[Dict[str, str]] = []
    seen: set = set()
    for m in re.finditer(r"\{\{(\w+)\}\}", text):
        key = m.group(1)
        if key not in seen:
            seen.add(key)
            placeholders.append({"key": key, "reason": "Detail not provided — verify before filing"})
    return placeholders


async def draft_freetext_node(state: DraftingState) -> Command:
    """v5.0: ONE LLM call → plain text document → skip to evidence_anchoring.

    Simplified prompt (5 rules, not 26). User facts at top.
    No JSON parsing. No section keys. LLM structures document naturally.
    """
    logger.info("[DRAFT_FREETEXT] ▶ start (v5.0 free-text)")
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

    court_fee_context = build_court_fee_context(
        court_fee, settings.DRAFTING_WEBSEARCH_SOURCE_URLS,
    )
    limitation_context = _build_limitation_context(mandatory_provisions)
    verified_provisions_context = _build_verified_provisions_context(mandatory_provisions)
    rag_context = _build_rag_context(rag, settings.DRAFTING_DRAFT_RAG_LIMIT)
    procedural_requirements_context = _build_procedural_requirements_context(mandatory_provisions)
    decision_ir = _as_dict(state.get("decision_ir"))

    # --- v11.0: try structured prompt (schema + LKB 2-layer) first ---
    doc_schema = get_schema(doc_type) if doc_type else None
    if doc_schema and lkb_brief:
        logger.info("[DRAFT_FREETEXT] using v11.0 structured prompt (schema=%s)", doc_schema.get("code"))
        system_prompt = build_structured_system_prompt(doc_schema)

        structured_context = build_structured_draft_prompt(
            lkb_entry=lkb_brief,
            doc_schema=doc_schema,
            user_facts=user_request,
            verified_provisions=verified_provisions_context,
            parties=_as_json(intake.get("parties", {})),
            jurisdiction=_as_json(intake.get("jurisdiction", {})),
            court_fee_context=court_fee_context,
            decision_ir=decision_ir,
        )

        # Build user prompt with structured context replacing lkb_brief
        user_prompt = build_draft_freetext_user_prompt(
            user_request=user_request,
            doc_type=doc_type,
            law_domain=classify.get("law_domain", ""),
            jurisdiction=_as_json(intake.get("jurisdiction", {})),
            parties=_as_json(intake.get("parties", {})),
            facts=_as_json(intake.get("facts", {})),
            evidence=_as_json(intake.get("evidence", [])),
            verified_provisions=verified_provisions_context,
            limitation=limitation_context,
            court_fee_context=court_fee_context,
            rag_context=rag_context,
            procedural_requirements=procedural_requirements_context,
            lkb_brief=structured_context,
        )
    else:
        # --- Fallback: v5.1 flat prompt ---
        logger.info("[DRAFT_FREETEXT] using v5.1 flat prompt (no schema match for doc_type=%s)", doc_type)
        system_prompt = build_draft_freetext_system_prompt(doc_type, cause_type)
        lkb_brief_context = _build_lkb_brief_context(lkb_brief, decision_ir)

        user_prompt = build_draft_freetext_user_prompt(
            user_request=user_request,
            doc_type=doc_type,
            law_domain=classify.get("law_domain", ""),
            jurisdiction=_as_json(intake.get("jurisdiction", {})),
            parties=_as_json(intake.get("parties", {})),
            facts=_as_json(intake.get("facts", {})),
            evidence=_as_json(intake.get("evidence", [])),
            verified_provisions=verified_provisions_context,
            limitation=limitation_context,
            court_fee_context=court_fee_context,
            rag_context=rag_context,
            procedural_requirements=procedural_requirements_context,
            lkb_brief=lkb_brief_context,
        )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    model = draft_openai_model.resolve_model() if hasattr(draft_openai_model, "resolve_model") else draft_openai_model
    if model is None:
        logger.error("[DRAFT_FREETEXT] ✗ draft_openai_model unavailable")
        return Command(
            update={"errors": ["draft_freetext: model unavailable"]},
            goto=END,
        )

    draft_text = ""
    for attempt in range(1, 3):
        try:
            response = model.invoke(messages)
            raw_text = getattr(response, "content", "") or ""
            logger.info(
                "[DRAFT_FREETEXT] attempt %d raw response length: %d",
                attempt, len(raw_text),
            )

            # Strip markdown fences if present
            cleaned = _strip_markdown_fences(raw_text)

            # Clean encoding artifacts — Unicode control chars and garbled apostrophes
            import re as _re
            cleaned = cleaned.replace("\ufffd", "-")
            cleaned = cleaned.replace("\u200b", "").replace("\u200c", "")
            # Replace common garbled apostrophes: \u0009 (tab), \u0003 (ETX), \u0001 (SOH)
            # followed by optional chars like 's', 'f' that appear in LLM output
            cleaned = _re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f](?=[a-z])", "'", cleaned)
            cleaned = _re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", cleaned)

            if len(cleaned) >= 500:
                draft_text = cleaned
                logger.info(
                    "[DRAFT_FREETEXT] ✓ attempt %d | chars=%d",
                    attempt, len(draft_text),
                )
                break
            else:
                logger.warning(
                    "[DRAFT_FREETEXT] attempt %d — too short (%d chars), retrying",
                    attempt, len(cleaned),
                )
        except Exception as exc:
            logger.error("[DRAFT_FREETEXT] attempt %d failed: %s", attempt, exc)

    if not draft_text:
        logger.error("[DRAFT_FREETEXT] ✗ failed after 2 attempts — falling back to v4.0 draft")
        return Command(
            update={"errors": ["draft_freetext: failed to produce text"]},
            goto="draft_single_call",
        )

    # Append advocate block if not present (check for key markers)
    _lower_text = draft_text.lower()
    _has_advocate = "advocate" in _lower_text and "enrollment" in _lower_text
    if not _has_advocate:
        draft_text += "\n" + _FREETEXT_ADVOCATE_BLOCK.strip()
    else:
        # Remove duplicate "ADVOCATE BLOCK" heading if LLM added one as a section
        import re as _re2
        draft_text = _re2.sub(
            r"\n+ADVOCATE BLOCK\s*\n+Through:\s*\n\{\{ADVOCATE_NAME\}\}\s*\nAdvocate\s*\nEnrollment No\.\s*\{\{ADVOCATE_ENROLLMENT\}\}\s*\n\{\{ADVOCATE_ADDRESS\}\}\s*$",
            "",
            draft_text,
        ).rstrip()

    # Collect placeholders
    placeholders = _collect_placeholders_from_text(draft_text)

    # Extract title from first few lines
    title = doc_type.replace("_", " ").title()
    _title_prefixes = (
        "SUIT FOR", "APPLICATION FOR", "PLAINT FOR", "PARTITION",
        "DAMAGES CLAIM", "PETITION FOR", "COMMERCIAL SUIT",
    )
    for line in draft_text.split("\n")[:15]:
        stripped = line.strip().upper()
        if any(stripped.startswith(p) for p in _title_prefixes):
            title = line.strip()
            break

    draft_artifact = {
        "doc_type": doc_type,
        "title": title,
        "text": draft_text,
        "placeholders_used": placeholders,
        "citations_used": [],
    }

    elapsed = time.perf_counter() - t0
    logger.info(
        "[DRAFT_FREETEXT] ✓ done (%.1fs) | chars=%d | placeholders=%d",
        elapsed, len(draft_text), len(placeholders),
    )

    # Skip structural_gate + assembler — go straight to evidence_anchoring
    return Command(
        update={"draft": {"draft_artifacts": [draft_artifact]}},
            goto="domain_consistency_gate",
        )

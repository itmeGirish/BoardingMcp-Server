"""Per-section LLM prompts for the section drafter node.

Each section gets a focused prompt with targeted context — not a monolithic blob.
System prompt ~200-500 tokens. User prompt only includes relevant context_keys.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..lkb.limitation import get_limitation_reference_details


def _get_quality_guidance(section_id: str, heading: str, section: Dict[str, Any] = None, doc_type: str = "") -> str:
    """Return STRUCTURAL drafting guidance per section type.

    Zero legal content here — no statute numbers, no suit-type-specific law.
    Legal substance comes from: LLM knowledge + enrichment + RAG + doc_type.
    This function provides ONLY formatting/structural/style rules.
    """
    # Build examples block from template JSON (if present)
    examples_block = ""
    if section and isinstance(section.get("examples"), dict):
        ex = section["examples"]
        bad = ex.get("bad", "")
        good = ex.get("good", "")
        if bad or good:
            examples_block = "\nEXAMPLES:"
            if bad:
                examples_block += f"\n- BAD: \"{bad}\""
            if good:
                examples_block += f"\n- GOOD: \"{good}\""
            examples_block += "\n"

    # Purely structural guidance — applies to ANY suit type
    guidance: Dict[str, str] = {
        "facts": """
STYLE GUIDANCE — FACTS:
- Write a NARRATIVE, not a skeleton. Each paragraph must tell a story.
- Frame the narrative around the PRIMARY RELIEF sought (from the doc_type) — not secondary issues.
- Chronological flow covering: how parties came together, what relationship existed, what events occurred, what went wrong, what happened after.
- Each numbered paragraph should cover ONE event or stage.
- Attach Annexure references to the specific paragraph where that document is relevant.
- Do NOT state legal conclusions — keep it purely factual.
""",
        "jurisdiction": """
STYLE GUIDANCE — JURISDICTION:
- Territorial jurisdiction must show a SPECIFIC territorial link with concrete facts.
- Pecuniary jurisdiction: state the specific suit valuation and that it falls within this court's limits.
- Keep it SHORT — 2-3 paragraphs maximum.
""",
        "legal_basis": """
STYLE GUIDANCE — LEGAL BASIS:
- Cite ONLY provisions from the VERIFIED STATUTORY PROVISIONS list in context, or well-known substantive provisions directly relevant to the doc_type.
- Do NOT cite procedural boilerplate sections that have no pleading relevance.
- For each provision, state in paragraph form: (a) the legal rule, (b) what triggers it, (c) how the facts satisfy it.
- If an alternative plea applies, use "In the alternative and without prejudice to the above..."
- Keep it CONCISE — a plaint pleads legal grounds, it does not lecture on law.
""",
        "cause_of_action": """
STYLE GUIDANCE — CAUSE OF ACTION:
- Must contain three distinct elements in PARAGRAPH prose (not numbered sub-headings):
  (a) ORIGIN: When and how the right to sue first arose
  (b) ACCRUAL: Continuing acts/omissions that sustain the right to sue
  (c) CONTINUITY: Why the cause of action is continuing
- Anchor to the actual triggering event from the facts, not to procedural dates.
""",
        "interest": """
STYLE GUIDANCE — INTEREST:
- Draft ONLY if interest/financial compensation is relevant to this doc_type.
- Structure clearly with rates, periods, and legal basis.
- Keep it CONCISE.
""",
        "prayer": """
STYLE GUIDANCE — PRAYER:
- Each prayer must be SPECIFIC — not vague.
- Structure as lettered items (a), (b), (c), etc.
- Prayers must match the PRIMARY RELIEF of the doc_type. Do NOT pray for relief inconsistent with the suit type.
- Always include a general relief clause.
""",
        "limitation": """
STYLE GUIDANCE — LIMITATION:
- Use ONLY the limitation citation provided in the LIMITATION context below.
- If the context gives a statutory reference, cite that exact provision. Do NOT rewrite it as a Limitation Act article.
- If no limitation citation is provided, use {{LIMITATION_ARTICLE}} as placeholder — do NOT guess or invent an article number.
- Anchor the limitation period START to the actual cause of action accrual event.
- State clearly that the suit is within time.
- Keep this section SHORT — 1-2 paragraphs. Do not explain limitation theory.
""",
    }

    base = guidance.get(section_id, "")
    return base + examples_block


def build_section_system_prompt(
    *,
    section: Dict[str, Any],
    doc_type: str,
    party_labels: Dict[str, str],
    is_retry: bool = False,
) -> str:
    """Build a focused system prompt for a single section."""
    section_heading = section.get("heading") or section.get("section_id", "")
    instruction = section.get("instruction", "")
    must_include = section.get("must_include", [])
    allowed_entities = section.get("allowed_entities", [])

    # Format must_include list
    mi_lines = []
    for item in must_include:
        desc = item.get("description", item.get("match", ""))
        required = "REQUIRED" if item.get("required", True) else "OPTIONAL"
        mi_lines.append(f"  - [{required}] {desc}")
    mi_block = "\n".join(mi_lines) if mi_lines else "  (none)"

    # Format allowed entities
    ae_block = ", ".join(allowed_entities) if allowed_entities else "(all from intake)"

    retry_suffix = ""
    if is_retry:
        retry_suffix = (
            "\n\nRETRY: Your previous attempt FAILED the must-include checks. "
            "Ensure ALL required items are present. Check the MUST INCLUDE list carefully."
        )

    # Determine if claim ledger is needed
    needs_claims = section.get("type") == "llm_fill"

    output_format = ""
    if needs_claims:
        output_format = """

OUTPUT FORMAT:
Return your response in this exact format:

---SECTION_TEXT---
[Your section text here — plain text, no JSON, no markdown fences]

---CLAIM_LEDGER---
[{"claim_type": "payment|notice|breach|admission|agreement|refusal|no_benefit|failure_of_consideration|continuing_cause",
  "entities": ["entity names used"],
  "dates": ["dates or date placeholders used"],
  "evidence_refs": ["Annexure labels referenced"]}]"""
    else:
        output_format = """

OUTPUT FORMAT:
Return ONLY the section body text. No JSON, no markdown fences, no preamble."""

    # Section-specific quality guidance — reads examples from template JSON if available
    quality_guidance = _get_quality_guidance(section.get("section_id", ""), section_heading, section, doc_type=doc_type)

    return f"""CRITICAL: Follow the OUTPUT FORMAT exactly.

You are drafting the "{section_heading}" section of a {doc_type}.

INSTRUCTION:
{instruction}

DRAFTING QUALITY RULES:
1. Write in professional litigation style — paragraph prose, NOT bullet points or exam-style sub-headings.
2. PLEAD, DON'T LECTURE. A plaint states facts and legal grounds concisely. Do NOT explain legal theory, CPC procedure, limitation doctrine, or execution law. Courts want clear facts → clean cause → straight relief. Excessive legal exposition weakens credibility.
3. Every factual assertion must include WHO did WHAT, WHEN, WHERE, and HOW — a judge must understand the dispute without reading attached documents.
4. NEVER use drafting-notes language in the output: no "to be verified", "placeholder", "to be entered", "to be calculated", "as per records", "details to follow". If a fact is missing, use {{{{PLACEHOLDER_NAME}}}} — nothing else.
5. Keep FACTS and LAW separate — facts section must contain only chronological narrative of events. Legal analysis belongs only in the legal basis section.
6. NEVER use "and/or" — use either "and" or "or" as appropriate.
7. Do NOT repeat the same phrase (e.g., "total failure of consideration", "recovery of Rs.X") more than twice in a section. Be concise.
8. When explaining a legal provision, state the rule it creates and explain WHY the facts satisfy that rule — do not merely name the section.
9. MATCH THE DOC_TYPE: Every section must be consistent with the classified document type. The doc_type tells you what PRIMARY RELIEF the user seeks. All facts, legal arguments, cause of action, and prayers must serve THAT relief. Do NOT introduce claims, prayers, or legal theories that belong to a different suit type.

HALLUCINATION RULES:
- Do NOT invent facts, dates, names, or amounts not in the provided context
- Use {{{{PLACEHOLDER_NAME}}}} for any missing detail (but the placeholder itself is the ONLY acceptable gap marker)
- Do NOT fabricate case law citations (no AIR/SCC/ILR patterns)
- Cite ONLY statutory provisions provided in the enrichment context
- Reference documents as 'Annexure [LABEL]' per the annexure scheme
{quality_guidance}
MUST INCLUDE (your output will be validated against these):
{mi_block}

ALLOWED ENTITIES (do not introduce names/institutions outside this list):
{ae_block}

PARTY LABELS:
Primary: {party_labels.get('primary', 'Plaintiff')}
Opposite: {party_labels.get('opposite', 'Defendant')}{output_format}{retry_suffix}"""


def build_section_user_prompt(
    *,
    section: Dict[str, Any],
    intake: Dict[str, Any],
    classify: Dict[str, Any],
    rag: Dict[str, Any],
    mandatory_provisions: Dict[str, Any],
    court_fee: Dict[str, Any],
    template: Dict[str, Any],
    user_request: str = "",
) -> str:
    """Build context-specific user prompt for a single section."""
    context_keys = section.get("context_keys", [])
    section_heading = section.get("heading") or section.get("section_id", "")

    parts: List[str] = [f"Generate the \"{section_heading}\" section.\n"]

    # Include the original user request so the LLM understands the full context
    if user_request:
        parts.append(f"ORIGINAL USER REQUEST:\n{user_request}\n")

    # Include classified document type
    doc_type = classify.get("doc_type", "")
    if doc_type:
        parts.append(f"DOCUMENT TYPE: {doc_type}\n")

    # Party info (always include minimal party labels)
    parties = intake.get("parties", {})
    if isinstance(parties, dict):
        primary = parties.get("primary", {})
        opposite_list = parties.get("opposite", [])
        opposite = opposite_list[0] if isinstance(opposite_list, list) and opposite_list else {}
        parts.append(f"PARTIES:")
        parts.append(f"  Plaintiff: {_safe_get(primary, 'name', '{{PLAINTIFF_NAME}}')}")
        parts.append(f"  Defendant: {_safe_get(opposite, 'name', '{{DEFENDANT_NAME}}')}")
        parts.append("")

    # Context-specific fields
    for key in context_keys:
        block = _extract_context(key, intake, mandatory_provisions, court_fee, rag)
        if block:
            parts.append(block)

    # Annexure scheme — only for sections that reference documents
    _ANNEXURE_SECTIONS = {"facts", "document_list", "legal_basis", "parties"}
    sid = section.get("section_id", "")
    annexure_scheme = template.get("annexure_scheme", {})
    if annexure_scheme and sid in _ANNEXURE_SECTIONS:
        parts.append("ANNEXURE SCHEME:")
        for label, desc in annexure_scheme.items():
            parts.append(f"  Annexure {label}: {desc}")
        parts.append("")

    # Placeholder dates — only for sections that use dates
    _DATE_SECTIONS = {"facts", "cause_of_action", "limitation", "interest", "prayer", "jurisdiction"}
    placeholder_dates = template.get("placeholder_dates", {})
    if placeholder_dates and sid in _DATE_SECTIONS:
        parts.append("PLACEHOLDER DATES (use these exact names if date is unknown):")
        for name, desc in placeholder_dates.items():
            parts.append(f"  {{{{{name}}}}}: {desc}")
        parts.append("")

    # RAG context (targeted, max 2 chunks)
    rag_query = section.get("rag_query")
    if rag_query == "from_enrichment" and mandatory_provisions:
        # Include enrichment data as RAG context
        user_cited = mandatory_provisions.get("user_cited_provisions", [])
        if user_cited:
            parts.append("VERIFIED STATUTORY PROVISIONS:")
            for prov in user_cited:
                if isinstance(prov, dict):
                    parts.append(f"  {prov.get('section', '')} {prov.get('act', '')}:")
                    parts.append(f"    {(prov.get('text', ''))[:400]}")
            parts.append("")
        lim = mandatory_provisions.get("limitation")
        if lim and isinstance(lim, dict):
            details = get_limitation_reference_details(lim)
            parts.append("LIMITATION:")
            if details["kind"] == "none":
                parts.append("  No limitation article applies.")
            elif details["kind"] == "unknown":
                parts.append("  Citation: verify the applicable limitation article from the case-specific facts before filing.")
            elif details["citation"]:
                parts.append(f"  Citation: {details['citation']}")
            else:
                parts.append(f"  Article: {lim.get('article', '{{LIMITATION_ARTICLE}}')}")
            parts.append(f"  Description: {lim.get('description', '')}")
            parts.append(f"  Period: {lim.get('period', '{{LIMITATION_PERIOD}}')}")
            accrual = lim.get("accrual", lim.get("from", ""))
            if accrual:
                parts.append(f"  Accrual: {accrual}")
            parts.append("")

    return "\n".join(parts)


def _safe_get(obj: Any, key: str, default: str = "") -> str:
    """Safely get a value from dict or Pydantic model."""
    if isinstance(obj, dict):
        return obj.get(key, default) or default
    return getattr(obj, key, default) or default


def _extract_context(
    key: str,
    intake: Dict[str, Any],
    mandatory_provisions: Dict[str, Any],
    court_fee: Dict[str, Any],
    rag: Dict[str, Any],
) -> Optional[str]:
    """Extract a context block for the given key."""
    parts: List[str] = []

    if key == "intake.parties":
        parties = intake.get("parties", {})
        if isinstance(parties, dict):
            primary = parties.get("primary", {})
            opposite_list = parties.get("opposite", [])
            parts.append("PLAINTIFF DETAILS:")
            parts.append(f"  Name: {_safe_get(primary, 'name', '{{PLAINTIFF_NAME}}')}")
            parts.append(f"  Age: {_safe_get(primary, 'age', '{{PLAINTIFF_AGE}}')}")
            parts.append(f"  Occupation: {_safe_get(primary, 'occupation', '{{PLAINTIFF_OCCUPATION}}')}")
            parts.append(f"  Address: {_safe_get(primary, 'address', '{{PLAINTIFF_ADDRESS}}')}")
            if isinstance(opposite_list, list):
                for i, opp in enumerate(opposite_list):
                    label = f"DEFENDANT {i+1} DETAILS:" if len(opposite_list) > 1 else "DEFENDANT DETAILS:"
                    parts.append(label)
                    parts.append(f"  Name: {_safe_get(opp, 'name', '{{DEFENDANT_NAME}}')}")
                    parts.append(f"  Age: {_safe_get(opp, 'age', '{{DEFENDANT_AGE}}')}")
                    parts.append(f"  Occupation: {_safe_get(opp, 'occupation', '{{DEFENDANT_OCCUPATION}}')}")
                    parts.append(f"  Address: {_safe_get(opp, 'address', '{{DEFENDANT_ADDRESS}}')}")
            parts.append("")

    elif key == "intake.jurisdiction":
        jurisdiction = intake.get("jurisdiction", {})
        if isinstance(jurisdiction, dict):
            parts.append("JURISDICTION:")
            parts.append(f"  State: {_safe_get(jurisdiction, 'state', '{{STATE}}')}")
            parts.append(f"  City: {_safe_get(jurisdiction, 'city', '{{COURT_PLACE}}')}")
            parts.append(f"  Court type: {_safe_get(jurisdiction, 'court_type', '{{COURT_TYPE}}')}")
            parts.append(f"  Place: {_safe_get(jurisdiction, 'place', '')}")
            parts.append("")

    elif key == "intake.facts":
        facts = intake.get("facts", {})
        if isinstance(facts, dict):
            parts.append("FACTS:")
            summary = facts.get("summary", "")
            if summary:
                parts.append(f"  Summary: {summary}")
            amounts = facts.get("amounts", {})
            if isinstance(amounts, dict):
                parts.append("  AMOUNTS:")
                if amounts.get("principal"):
                    parts.append(f"    Principal: Rs. {amounts['principal']:,.0f}/-")
                if amounts.get("interest_rate"):
                    parts.append(f"    Interest rate: {amounts['interest_rate']}% per annum")
                if amounts.get("damages"):
                    parts.append(f"    Damages: Rs. {amounts['damages']:,.0f}/-")
            chronology = facts.get("chronology", [])
            if chronology:
                parts.append("  CHRONOLOGY:")
                for item in chronology:
                    if isinstance(item, dict):
                        date = item.get("date", "{{DATE}}")
                        event = item.get("event", "")
                        parts.append(f"    {date}: {event}")
            coa_date = facts.get("cause_of_action_date")
            if coa_date:
                parts.append(f"  Cause of action date: {coa_date}")
            parts.append("")

    elif key == "intake.facts.amounts":
        facts = intake.get("facts", {})
        amounts = facts.get("amounts", {}) if isinstance(facts, dict) else {}
        if isinstance(amounts, dict) and any(amounts.values()):
            parts.append("AMOUNTS:")
            if amounts.get("principal"):
                parts.append(f"  Principal: Rs. {amounts['principal']:,.0f}/-")
            if amounts.get("interest_rate"):
                parts.append(f"  Interest rate: {amounts['interest_rate']}% per annum")
            if amounts.get("damages"):
                parts.append(f"  Damages: Rs. {amounts['damages']:,.0f}/-")
            parts.append("")

    elif key == "intake.evidence":
        evidence = intake.get("evidence", [])
        if isinstance(evidence, list) and evidence:
            parts.append("EVIDENCE:")
            for i, item in enumerate(evidence):
                if isinstance(item, dict):
                    parts.append(f"  {i+1}. [{item.get('type', '')}] {item.get('description', '')}")
                    ref = item.get("ref")
                    if ref:
                        parts.append(f"     Ref: {ref}")
            parts.append("")

    elif key == "mandatory_provisions.user_cited_provisions":
        user_cited = mandatory_provisions.get("user_cited_provisions", [])
        if user_cited:
            parts.append("VERIFIED STATUTORY PROVISIONS:")
            for prov in user_cited:
                if isinstance(prov, dict):
                    parts.append(f"  {prov.get('section', '')} {prov.get('act', '')}:")
                    parts.append(f"    {(prov.get('text', ''))[:400]}")
            parts.append("")

    elif key == "mandatory_provisions.limitation":
        lim = mandatory_provisions.get("limitation")
        if lim and isinstance(lim, dict):
            details = get_limitation_reference_details(lim)
            parts.append("LIMITATION:")
            if details["kind"] == "none":
                parts.append("  No limitation article applies.")
            elif details["kind"] == "unknown":
                parts.append("  Citation: verify the applicable limitation article from the case-specific facts before filing.")
            elif details["citation"]:
                parts.append(f"  Citation: {details['citation']}")
            else:
                parts.append(f"  Article: {lim.get('article', '{{LIMITATION_ARTICLE}}')}")
            parts.append(f"  Period: {lim.get('period', '{{LIMITATION_PERIOD}}')}")
            accrual = lim.get("accrual", lim.get("from", ""))
            if accrual:
                parts.append(f"  Accrual: {accrual}")
            parts.append("")

    elif key == "court_fee":
        if court_fee:
            summary = (court_fee.get("summary") or "").strip()
            if summary:
                parts.append("COURT FEE CONTEXT:")
                parts.append(f"  {summary[:500]}")
                parts.append("")

    return "\n".join(parts) if parts else None

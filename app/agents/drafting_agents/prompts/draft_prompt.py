"""Draft prompt — LKB-guided free-text drafting.

System prompt: role + format rules.
User prompt: user request + intake + enrichment + court fee + LKB brief.

v11.0: build_structured_draft_prompt() combines LKB + document schema into
ONE structured prompt with clear hierarchy (~1,500 tokens).
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ....config import logger


# ---------------------------------------------------------------------------
# Section keys per doc_type category
# ---------------------------------------------------------------------------

CIVIL_PLAINT_SECTIONS: List[str] = [
    "court_heading", "title", "parties", "jurisdiction", "facts",
    "legal_basis", "cause_of_action", "limitation", "valuation_court_fee",
    "interest", "prayer", "document_list", "verification",
]

# Non-monetary civil suits: injunction, declaration, partition, possession, etc.
# These do NOT have an interest section (no monetary claim to charge interest on).
CIVIL_NON_MONETARY_SECTIONS: List[str] = [
    "court_heading", "title", "parties", "jurisdiction", "facts",
    "legal_basis", "cause_of_action", "limitation", "valuation_court_fee",
    "prayer", "document_list", "verification",
]

# Cause types where the relief is NON-MONETARY → skip interest section.
# Structural metadata, not legal content — safe per CLAUDE.md rule 11.1.
# Pure non-monetary — no monetary claim possible. These get no interest section.
# specific_performance, recovery_of_possession, eviction are NOT here because:
#   - specific_performance: Section 21 SRA allows damages in lieu
#   - recovery_of_possession: mesne profits are a valid monetary head
#   - eviction: arrears of rent + mesne profits are recoverable
_NON_MONETARY_CAUSE_TYPES = frozenset({
    "permanent_injunction", "mandatory_injunction", "declaration_title",
    "partition", "mortgage_redemption", "easement",
})

CRIMINAL_SECTIONS: List[str] = [
    "court_heading", "title", "parties", "facts", "legal_basis",
    "grounds", "prayer", "verification",
]

FAMILY_SECTIONS: List[str] = [
    "court_heading", "title", "parties", "jurisdiction", "facts",
    "legal_basis", "prayer", "verification",
]

CONSTITUTIONAL_SECTIONS: List[str] = [
    "court_heading", "title", "parties", "jurisdiction", "facts",
    "legal_basis", "fundamental_rights", "grounds", "no_alternative_remedy",
    "interim_relief", "prayer", "verification",
]

RESPONSE_SECTIONS: List[str] = [
    "court_heading", "title", "parties", "preliminary_objections",
    "parawise_reply", "additional_facts", "legal_grounds", "prayer",
    "verification",
]


def get_section_keys(doc_type: str, cause_type: str = "") -> List[str]:
    """Return the section keys for the given doc_type and cause_type.

    For civil suits, cause_type determines whether the interest section
    is included (monetary relief) or excluded (non-monetary relief like
    injunction, declaration, partition).
    """
    doc_lower = doc_type.lower().replace(" ", "_").replace("-", "_")
    for kw in ("criminal", "bail", "quashing"):
        if kw in doc_lower:
            return CRIMINAL_SECTIONS
    for kw in ("family", "divorce", "maintenance", "custody"):
        if kw in doc_lower:
            return FAMILY_SECTIONS
    for kw in ("writ", "pil", "habeas", "constitutional"):
        if kw in doc_lower:
            return CONSTITUTIONAL_SECTIONS
    for kw in ("written_statement", "counter", "reply", "response"):
        if kw in doc_lower:
            return RESPONSE_SECTIONS

    # Civil: check if non-monetary based on cause_type
    ct = cause_type.lower().replace(" ", "_").replace("-", "_") if cause_type else ""
    if ct in _NON_MONETARY_CAUSE_TYPES:
        logger.info("[DRAFT_PROMPT] non-monetary cause_type=%s → omitting interest section", ct)
        return CIVIL_NON_MONETARY_SECTIONS
    return CIVIL_PLAINT_SECTIONS


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_TEMPLATE = """CRITICAL: Return ONLY a valid JSON object. No explanation, no markdown fences, no preamble.

You are a senior Indian litigation lawyer with 25 years of courtroom practice.
Draft a {doc_type} for filing.

OUTPUT FORMAT:
Return a JSON object with these exact keys. Each value is the section body text (string).
Do NOT include section headings in the values — the assembler adds those.
Do NOT wrap in markdown code fences — return raw JSON only.

Required keys: {section_keys}

RULES:
1. ANTI-FABRICATION (HIGHEST PRIORITY): Write ONLY facts explicitly stated in the provided
   FACTS/EVIDENCE. NEVER invent events, documents, correspondence, visits, admissions, or
   details not in the input. A shorter accurate draft is ALWAYS superior to a longer
   fabricated one. If information is missing, use {{{{PLACEHOLDER_NAME}}}} — do NOT fill gaps
   with invented narrative. Write one fact paragraph per provided fact — no more, no less.
2. Do NOT fabricate case citations (AIR, SCC, ILR) — use only statutory provisions from
   VERIFIED PROVISIONS and RAG CONTEXT. For every cited provision, explain what it says
   and how the facts trigger it. Fill in actual section numbers from LEGAL BRIEF — do NOT
   use placeholders when the section is provided.
3. Number paragraphs continuously. Verification follows Order VI Rule 15 CPC.
   Reference Annexures by label ONLY for documents mentioned in the provided EVIDENCE.
   Do NOT invent Annexures for documents not provided.
4. NEVER cite repealed/superseded Acts (see LEGAL BRIEF for DO NOT CITE list).
   If LEGAL BRIEF specifies CAUSE OF ACTION TYPE as SINGLE_EVENT, do NOT plead
   "continuing cause of action" or "continuing breach". If LIMITATION provides a
   special statutory reference, cite that exact provision and do NOT rewrite it
   as an Article of the Limitation Act.
5. If PROCEDURAL REQUIREMENTS are provided, incorporate them. Omission causes rejection.
   Use COURT_FEE_CONTEXT for court fee — do not guess rates. If rates are unverified,
   use {{{{COURT_FEE_AMOUNT}}}} placeholder.
"""


def build_draft_system_prompt(doc_type: str, cause_type: str = "") -> str:
    """Build the system prompt with section keys (no exemplar)."""
    section_keys = get_section_keys(doc_type, cause_type)

    return _SYSTEM_TEMPLATE.format(
        doc_type=doc_type,
        section_keys=json.dumps(section_keys),
    )



# ---------------------------------------------------------------------------
# User prompt
# ---------------------------------------------------------------------------

_USER_TEMPLATE = """Draft a {doc_type} based on the following:

USER REQUEST:
{user_request}

DOCUMENT TYPE: {doc_type}
LAW DOMAIN: {law_domain}

{lkb_brief}

JURISDICTION:
{jurisdiction}

PARTIES:
{parties}

FACTS:
{facts}

EVIDENCE:
{evidence}

VERIFIED LEGAL PROVISIONS (cite these — do not guess section numbers):
{verified_provisions}

LIMITATION:
{limitation}

COURT FEE CONTEXT:
{court_fee_context}

RAG CONTEXT (verified statutory text — use for legal framing):
{rag_context}

PROCEDURAL REQUIREMENTS (comply with these if provided):
{procedural_requirements}
"""


def build_draft_user_prompt(
    user_request: str,
    doc_type: str,
    law_domain: str,
    jurisdiction: str,
    parties: str,
    facts: str,
    evidence: str,
    verified_provisions: str,
    limitation: str,
    court_fee_context: str,
    rag_context: str,
    procedural_requirements: str = "",
    lkb_brief: str = "",
) -> str:
    """Build the user prompt with all context."""
    return _USER_TEMPLATE.format(
        user_request=user_request,
        doc_type=doc_type,
        law_domain=law_domain,
        jurisdiction=jurisdiction,
        parties=parties,
        facts=facts,
        evidence=evidence,
        verified_provisions=verified_provisions,
        limitation=limitation,
        court_fee_context=court_fee_context,
        rag_context=rag_context,
        procedural_requirements=procedural_requirements,
        lkb_brief=lkb_brief,
    )


# ---------------------------------------------------------------------------
# v5.0 FREE-TEXT prompts (simplified — research-informed context engineering)
# ---------------------------------------------------------------------------

_FREETEXT_SYSTEM_TEMPLATE = """You are a senior Indian litigation lawyer with 25 years of courtroom practice.
Draft a {doc_type} for filing in an Indian court.

Write the COMPLETE document exactly as it would appear when filed in court.
Include all section headings (ALL CAPS), continuous paragraph numbering,
verification clause, and advocate block.

Output plain text only — not JSON, not markdown code blocks.

FORMAT:
- Court heading with SPECIFIC court name (e.g., "Principal Civil Judge (Senior Division)",
  "City Civil Judge" — NOT just "District Judge"). Use LEGAL BRIEF court if provided.
- Case number: ORIGINAL SUIT NO. _____ OF {{{{YEAR}}}}
- Party block in STANDARD INDIAN COURT format:
    Name, S/o Father, Aged about __ years, R/o Address, City, State – PIN.  ... PLAINTIFF
    VERSUS
    Name, S/o Father, ...  ... DEFENDANT
- Suit title in ALL CAPS
- Section headings in ALL CAPS
- *** CONTINUOUS paragraph numbering 1,2,3... through ENTIRE document. NEVER restart per section ***
- For immovable property: SCHEDULE OF PROPERTY with boundaries (E/W/N/S), survey no, area
- CAUSE OF ACTION: 2-3 paragraphs — (1) when first arose, (2) when further arose, (3) notice date
- For monetary claims: INTEREST section with pre-suit on a contractual or other legally sustainable basis,
  pendente lite under Section 34 CPC (from suit to decree), future interest under Section 34 CPC (post-decree)
- PRAYER: (a) through (f)+. Include specific amounts, costs, and "such other relief"
- LIST OF DOCUMENTS: ANNEXURE-A/B/C ONLY for documents mentioned in the provided EVIDENCE
- Verification per Order VI Rule 15 CPC with correct paragraph range
- Advocate block: Name, Enrollment No., address, mobile

RULES:
1. ANTI-FABRICATION (HIGHEST PRIORITY): Write ONLY facts explicitly stated in the provided
   FACTS/EVIDENCE. NEVER invent events, documents, correspondence, visits, admissions, or
   details not in the input. A shorter accurate draft is ALWAYS superior to a longer
   fabricated one. If information is missing, use {{{{PLACEHOLDER_NAME}}}} — do NOT fill gaps
   with invented narrative. Write one fact paragraph per provided fact — no more, no less.
   List Annexures ONLY for documents mentioned in the provided EVIDENCE — do NOT invent
   documents that were not provided.
2. Do NOT fabricate case citations (AIR, SCC, ILR). Use only statutory provisions from
   VERIFIED PROVISIONS and LEGAL BRIEF. For every cited provision, explain what it says
   and how the facts trigger it. Fill in actual section numbers from LEGAL BRIEF — do NOT
   use placeholders like {{{{PRIMARY_PROVISION}}}} when the section is provided.
3. Number paragraphs continuously. Verification follows Order VI Rule 15 CPC.
   Facts section must contain ONLY factual events — legal analysis belongs in LEGAL BASIS.
4. NEVER cite repealed/superseded Acts (see LEGAL BRIEF for DO NOT CITE list).
   If LEGAL BRIEF specifies CAUSE OF ACTION TYPE as SINGLE_EVENT, do NOT plead
   "continuing cause of action". If LIMITATION says NONE, do NOT cite Limitation Act.
   If LIMITATION provides a special statutory reference, cite that exact provision
   and do NOT rewrite it as an Article of the Limitation Act.
5. If PROCEDURAL REQUIREMENTS are provided, incorporate them. Omission causes rejection.
   Use COURT_FEE_CONTEXT for court fee — do not guess rates. If rates are unverified,
   use {{{{COURT_FEE_AMOUNT}}}} placeholder.
6. LEGAL BRIEF COMPLIANCE: If the LEGAL BRIEF lists "DO NOT CITE" statutes or "DO NOT PLEAD"
   doctrines, treat these as ABSOLUTE PROHIBITIONS. If it lists MANDATORY AVERMENTS, each
   MUST appear in the draft. If it lists FACTS MUST COVER items, each must be addressed.
   If it lists PRAYER MUST INCLUDE items, each must appear as a sub-prayer.
"""

_FREETEXT_USER_TEMPLATE = """Draft a {doc_type}.

USER REQUEST:
{user_request}

{lkb_brief}

PARTIES:
{parties}

FACTS AND EVIDENCE:
{facts}

{evidence}

JURISDICTION:
{jurisdiction}

LIMITATION:
{limitation}

VERIFIED LEGAL PROVISIONS:
{verified_provisions}

COURT FEE:
{court_fee_context}

{rag_context}

{procedural_requirements}
"""


def build_draft_freetext_system_prompt(doc_type: str, cause_type: str = "") -> str:
    """Build system prompt for v5.0 free-text drafting.

    No exemplar — LKB brief provides all legal guidance.
    Format instructions replace exemplar for structural guidance.
    """
    return _FREETEXT_SYSTEM_TEMPLATE.format(
        doc_type=doc_type,
    )


def build_draft_freetext_user_prompt(
    user_request: str,
    doc_type: str,
    law_domain: str,
    jurisdiction: str,
    parties: str,
    facts: str,
    evidence: str,
    verified_provisions: str,
    limitation: str,
    court_fee_context: str,
    rag_context: str,
    procedural_requirements: str = "",
    lkb_brief: str = "",
) -> str:
    """Build user prompt for v5.0 free-text drafting.

    Research-informed: user request and facts at TOP (highest attention position).
    LKB brief and RAG context after facts.
    """
    return _FREETEXT_USER_TEMPLATE.format(
        user_request=user_request,
        doc_type=doc_type,
        jurisdiction=jurisdiction,
        parties=parties,
        facts=facts,
        evidence=evidence,
        verified_provisions=verified_provisions,
        limitation=limitation,
        court_fee_context=court_fee_context,
        rag_context=(
            f"STATUTORY CONTEXT (from verified sources):\n{rag_context}"
            if rag_context else ""
        ),
        procedural_requirements=(
            f"PROCEDURAL REQUIREMENTS:\n{procedural_requirements}"
            if procedural_requirements else ""
        ),
        lkb_brief=lkb_brief,
    )


# ---------------------------------------------------------------------------
# v11.0 STRUCTURED PROMPT — LKB 2-layer + document schema → one prompt
# ---------------------------------------------------------------------------

def _format_section_plan(doc_schema: dict) -> str:
    """Format document schema sections into numbered list."""
    lines = []
    lines.append(f"Document type: {doc_schema['display_name']}")
    lines.append(f"Filed by: {doc_schema['filed_by']}")
    lines.append(f"Annexure prefix: {doc_schema['annexure_prefix']}")
    lines.append(f"CPC reference: {doc_schema.get('cpc_reference', '')}")
    lines.append("\nSections (in this order):")
    for i, section in enumerate(doc_schema["sections"], 1):
        lines.append(f"  {i}. {section['key'].upper()} — {section['instruction']}")
    return "\n".join(lines)


def _format_acts(primary_acts: List[dict]) -> str:
    """Format primary acts into readable list."""
    if not primary_acts:
        return "None specified"
    lines = []
    for act_info in primary_acts:
        act = act_info.get("act", "")
        sections = act_info.get("sections", [])
        if sections:
            lines.append(f"  - {act}: {', '.join(sections)}")
        else:
            lines.append(f"  - {act}")
    return "\n".join(lines)


def _format_limitation(limitation: dict) -> str:
    """Format limitation info."""
    if not limitation:
        return "UNKNOWN"
    article = limitation.get("article", "UNKNOWN")
    period = limitation.get("period", "")
    from_text = limitation.get("from", "")
    parts = [f"Article {article}"]
    if period:
        parts.append(f"— {period}")
    if from_text:
        parts.append(f"from {from_text}")
    return " ".join(parts)


def _format_reliefs(available_reliefs: Optional[List[dict]]) -> str:
    """Format available reliefs with prayer text."""
    if not available_reliefs:
        return "Draft appropriate prayer based on cause type"
    lines = []
    for i, relief in enumerate(available_reliefs, 1):
        prayer = relief.get("prayer_text", "")
        statute = relief.get("statute", "")
        if statute:
            lines.append(f"  ({chr(96 + i)}) {prayer} ({statute})")
        else:
            lines.append(f"  ({chr(96 + i)}) {prayer}")
    return "\n".join(lines)


def build_structured_draft_prompt(
    lkb_entry: dict,
    doc_schema: dict,
    user_facts: str,
    verified_provisions: str = "",
    parties: str = "",
    jurisdiction: str = "",
    court_fee_context: str = "",
    decision_ir: Optional[dict] = None,
) -> str:
    """Build v11.0 structured prompt from LKB + document schema.

    Replaces _build_lkb_brief_context() (~400 lines) with ~1,500 token
    structured prompt. Clear hierarchy: STRUCTURE > LAW > FACTS > RULES.

    Args:
        lkb_entry: Full LKB entry (Layer 1 + Layer 2)
        doc_schema: Document type schema from schemas/
        user_facts: User's request/facts from intake
        verified_provisions: Verified legal provisions from enrichment
        parties: Party details from intake
        jurisdiction: Jurisdiction info
        court_fee_context: Court fee info
        decision_ir: Applicability compiler output (if available)
    """
    parts = []

    # ═══ Section 1: DOCUMENT STRUCTURE (from schema) ═══
    parts.append("═══ DOCUMENT STRUCTURE (follow this section order exactly) ═══")
    parts.append(_format_section_plan(doc_schema))

    # ═══ Section 2: LEGAL DATA (from LKB Layer 1 + Layer 2) ═══
    parts.append("\n═══ LEGAL DATA (cite ONLY from this) ═══")
    parts.append(f"Cause: {lkb_entry.get('display_name', 'Unknown')}")

    parts.append(f"\nStatutes to cite:\n{_format_acts(lkb_entry.get('primary_acts', []))}")

    parts.append(f"\nLimitation: {_format_limitation(lkb_entry.get('limitation', {}))}")

    # Layer 2: reliefs with prayer_text
    available_reliefs = lkb_entry.get("available_reliefs")
    if available_reliefs:
        parts.append(f"\nReliefs to pray for:\n{_format_reliefs(available_reliefs)}")
    elif lkb_entry.get("prayer_template"):
        # Fallback: use existing prayer_template if Layer 2 not yet enriched
        items = lkb_entry["prayer_template"]
        lines = [f"  ({chr(96 + i)}) {item}" for i, item in enumerate(items, 1)]
        parts.append(f"\nReliefs to pray for:\n" + "\n".join(lines))

    # Layer 2: jurisdiction basis
    jb = lkb_entry.get("jurisdiction_basis")
    if jb:
        parts.append(f"\nJurisdiction basis: {jb}")

    # Layer 2: valuation basis
    vb = lkb_entry.get("valuation_basis")
    if vb:
        parts.append(f"\nValuation basis: {vb}")

    # Verified provisions
    if verified_provisions:
        parts.append(f"\nVerified provisions (cite these — do not guess section numbers):\n{verified_provisions}")

    # ═══ Section 3: FACTS GUIDANCE (from LKB Layer 1) ═══
    parts.append("\n═══ FACTS GUIDANCE ═══")

    fmc = lkb_entry.get("facts_must_cover", [])
    if fmc:
        parts.append("MUST COVER:")
        for item in fmc:
            parts.append(f"  - {item}")

    red_flags = lkb_entry.get("drafting_red_flags", [])
    if red_flags:
        parts.append("DO NOT:")
        for rf in red_flags:
            parts.append(f"  - {rf}")

    # Mandatory averments
    ma = lkb_entry.get("mandatory_averments", [])
    if ma:
        parts.append("MANDATORY AVERMENTS (must appear in draft):")
        for av in ma:
            if isinstance(av, dict):
                parts.append(f"  - {av.get('averment', '')}: {av.get('instruction', '')}")
            else:
                parts.append(f"  - {av}")

    # ═══ Section 4: CLIENT FACTS ═══
    parts.append(f"\n═══ CLIENT FACTS ═══\n{user_facts}")

    if parties:
        parts.append(f"\nPARTIES:\n{parties}")

    if jurisdiction:
        parts.append(f"\nJURISDICTION:\n{jurisdiction}")

    if court_fee_context:
        parts.append(f"\nCOURT FEE:\n{court_fee_context}")

    # ═══ Section 5: UNIVERSAL RULES ═══
    parts.append("\n═══ UNIVERSAL RULES ═══")
    parts.append("1. Cite ONLY from the statutes listed above")
    parts.append("2. Do NOT include case law citations — use {{CASE_LAW_NEEDED: [topic]}}")
    parts.append("3. Every document reference must use annexure label (%s)" % doc_schema.get("annexure_prefix", "Annexure-"))
    parts.append("4. Verification must distinguish personal knowledge from information")
    parts.append("5. In FACTS section, plead ONLY factual events — no Section/Act numbers")
    parts.append("6. If information is missing, use {{PLACEHOLDER_NAME}} — do NOT fabricate")
    parts.append("7. Do NOT use 'on or about' for dates — use exact dates or {{DATE}} placeholder")
    parts.append("8. For ordinary money decrees, pendente lite and post-decree interest fall under Section 34 CPC")

    return "\n".join(parts)


def build_structured_system_prompt(doc_schema: dict) -> str:
    """Build v11.0 system prompt for structured drafting.

    Simpler than v5.1 system prompt — document structure comes from
    the structured user prompt, not the system prompt.
    """
    doc_type = doc_schema.get("display_name", "legal document")
    return f"""You are a senior Indian litigation lawyer with 25 years of courtroom practice.
Draft a {doc_type} for filing in an Indian court.

Write the COMPLETE document exactly as it would appear when filed in court.
Include all section headings (ALL CAPS), continuous paragraph numbering,
verification clause, and advocate block.

Output plain text only — not JSON, not markdown code blocks.

Follow the DOCUMENT STRUCTURE section order EXACTLY as given.
Use the LEGAL DATA section for all statutory citations.
Use the FACTS GUIDANCE to ensure all required facts are pleaded.
Use RELIEFS TO PRAY FOR as exact prayer text.
Obey all UNIVERSAL RULES.

ANTI-FABRICATION (HIGHEST PRIORITY): Write ONLY facts explicitly stated in CLIENT FACTS.
NEVER invent events, documents, correspondence, or details.
A shorter accurate draft is ALWAYS superior to a longer fabricated one.
If information is missing, use {{{{PLACEHOLDER_NAME}}}} — do NOT fill gaps with invented narrative."""

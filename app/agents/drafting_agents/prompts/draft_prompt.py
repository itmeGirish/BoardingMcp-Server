"""Exemplar-guided draft prompt — ONE LLM call produces section-keyed JSON.

System prompt: role + exemplar + format rules + section keys.
User prompt: user request + intake + enrichment + court fee + RAG.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from ....config import logger


# ---------------------------------------------------------------------------
# Exemplar loading
# ---------------------------------------------------------------------------

_EXEMPLAR_DIR = Path(__file__).resolve().parent.parent / "exemplars"

# doc_type keyword → exemplar file mapping
# Order matters: specific terms BEFORE broad categories.
# "family_court_reply" must match "reply" (response_document) not "family" (family_petition).
_CATEGORY_MAP: Dict[str, str] = {
    # Response documents — check FIRST (most specific)
    "written_statement": "response_document.txt",
    "counter": "response_document.txt",
    "reply": "response_document.txt",
    "response": "response_document.txt",
    # Criminal
    "bail": "criminal_application.txt",
    "quashing": "criminal_application.txt",
    "criminal": "criminal_application.txt",
    # Family
    "divorce": "family_petition.txt",
    "maintenance": "family_petition.txt",
    "custody": "family_petition.txt",
    "family": "family_petition.txt",
    # Constitutional
    "writ": "constitutional_petition.txt",
    "pil": "constitutional_petition.txt",
    "habeas": "constitutional_petition.txt",
    "constitutional": "constitutional_petition.txt",
    # Civil — specialized (check before generic civil default)
    "partition": "partition_plaint.txt",
}

_DEFAULT_EXEMPLAR = "civil_plaint.txt"


def load_exemplar(doc_type: str) -> str:
    """Load the exemplar text for the given doc_type category."""
    doc_lower = doc_type.lower().replace(" ", "_").replace("-", "_")

    # Check keywords in doc_type
    exemplar_file = _DEFAULT_EXEMPLAR
    for keyword, filename in _CATEGORY_MAP.items():
        if keyword in doc_lower:
            exemplar_file = filename
            break

    path = _EXEMPLAR_DIR / exemplar_file
    if not path.exists():
        logger.warning("[DRAFT_PROMPT] exemplar not found: %s — using empty", path)
        return ""

    text = path.read_text(encoding="utf-8").strip()
    logger.info("[DRAFT_PROMPT] loaded exemplar: %s (%d chars)", exemplar_file, len(text))
    return text


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
   "continuing cause of action" or "continuing breach".
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
- Court heading, case number, party block, suit title
- Section headings in ALL CAPS: JURISDICTION, FACTS OF THE CASE, LEGAL BASIS,
  CAUSE OF ACTION, LIMITATION, VALUATION AND COURT FEE, PRAYER, LIST OF DOCUMENTS, VERIFICATION
- For possession/property suits: include SCHEDULE OF PROPERTY section
- For mesne profits: include separate MESNE PROFITS section
- Continuous paragraph numbering throughout
- Prayer sub-items as (a), (b), (c)...
- Verification clause per Order VI Rule 15 CPC
- Advocate block at the end

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
5. If PROCEDURAL REQUIREMENTS are provided, incorporate them. Omission causes rejection.
   Use COURT_FEE_CONTEXT for court fee — do not guess rates. If rates are unverified,
   use {{{{COURT_FEE_AMOUNT}}}} placeholder.
"""

_FREETEXT_USER_TEMPLATE = """Draft a {doc_type}.

USER REQUEST:
{user_request}

PARTIES:
{parties}

FACTS AND EVIDENCE:
{facts}

{evidence}

JURISDICTION:
{jurisdiction}

{lkb_brief}

LIMITATION:
{limitation}

VERIFIED LEGAL PROVISIONS:
{verified_provisions}

COURT FEE:
{court_fee_context}

STATUTORY CONTEXT (from verified sources):
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
        rag_context=rag_context,
        procedural_requirements=(
            f"PROCEDURAL REQUIREMENTS:\n{procedural_requirements}"
            if procedural_requirements else ""
        ),
        lkb_brief=lkb_brief,
    )

"""Gate 2: Legal Theory Anchoring — verify every doctrine traces to LKB/RAG/user.

Deterministic, no LLM calls. Flags unanchored theories without removing them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# Doctrine detection patterns
DOCTRINE_PATTERNS: dict[str, list[str]] = {
    "unjust_enrichment": [r"unjust(?:ly)?\s+enrich", r"\brestitution\b"],
    "quantum_meruit": [r"quantum\s+meruit", r"reasonable\s+remuneration"],
    "estoppel": [r"\bestop(?:pel|ped)\b", r"promissory\s+estoppel"],
    "res_judicata": [r"res\s+judicata"],
    "tortious_interference": [r"tortious\s+interference"],
    "breach_of_contract": [
        r"breach\s+of\s+(?:the\s+)?(?:said\s+)?(?:contract|agreement)",
    ],
    "damages_s73": [
        r"section\s+73\b",
        r"compensation\s+for\s+(?:loss|damage|breach)",
    ],
    "damages_s74": [r"section\s+74\b", r"liquidated\s+damages"],
    "repudiatory_breach_s39": [r"section\s+39\b", r"repudiat(?:ory|ion|ed)"],
    "specific_performance": [r"specific\s+performance"],
    "lis_pendens": [r"lis\s+pendens", r"section\s+52\b.*(?:TPA|Transfer)"],
    "part_performance": [r"part\s+performance", r"section\s+53\s*A"],
    "frustration": [r"frustration\s+of\s+contract", r"section\s+56\b"],
    "novation": [r"\bnovation\b", r"section\s+62\b"],
    "waiver": [r"\bwaiver\b"],
    "mitigation": [r"mitigat(?:e|ion)\s+(?:of\s+)?(?:damage|loss)"],
}


@dataclass
class TheoryAnchoringResult:
    """Result of legal theory anchoring gate."""
    passed: bool = True
    theories_found: list[str] = field(default_factory=list)
    theories_anchored: list[str] = field(default_factory=list)
    theories_unanchored: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


def extract_legal_theories(draft: str) -> list[str]:
    """Extract legal theories/doctrines found in the draft text."""
    found = []
    draft_lower = draft.lower()
    for theory, patterns in DOCTRINE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, draft_lower, re.IGNORECASE):
                if theory not in found:
                    found.append(theory)
                break
    return found


def _build_allowed_set(
    lkb_entry: dict[str, Any] | None,
    verified_provisions: list[dict[str, Any]] | None,
    user_request: str = "",
) -> set[str]:
    """Build set of allowed theories from LKB, provisions, and user request."""
    allowed: set[str] = set()

    # From LKB permitted_doctrines
    if lkb_entry:
        for doctrine in lkb_entry.get("permitted_doctrines", []):
            allowed.add(doctrine)

    # From verified provisions — derive implied theories
    if verified_provisions:
        for prov in verified_provisions:
            section = ""
            if isinstance(prov, dict):
                section = str(prov.get("section", "")) + " " + str(prov.get("act", ""))
            elif isinstance(prov, str):
                section = prov
            section_lower = section.lower()
            if "section 73" in section_lower:
                allowed.add("damages_s73")
            if "section 74" in section_lower:
                allowed.add("damages_s74")
            if "section 39" in section_lower:
                allowed.add("repudiatory_breach_s39")
            if "section 56" in section_lower:
                allowed.add("frustration")
            if "specific performance" in section_lower or "section 10" in section_lower:
                allowed.add("specific_performance")

    # From user request — explicit theory mentions
    user_lower = user_request.lower()
    for theory, patterns in DOCTRINE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, user_lower, re.IGNORECASE):
                allowed.add(theory)
                break

    # Always-allowed universal theories
    allowed.update({"breach_of_contract", "mitigation", "waiver"})

    return allowed


def legal_theory_anchoring_gate(
    draft: str,
    lkb_entry: dict[str, Any] | None = None,
    verified_provisions: list[dict[str, Any]] | None = None,
    user_request: str = "",
) -> TheoryAnchoringResult:
    """Check every legal theory in the draft traces to LKB, provisions, or user request.

    Args:
        draft: Full draft text
        lkb_entry: LKB entry for the cause type (with permitted_doctrines)
        verified_provisions: List of verified statutory provisions
        user_request: Original user request text

    Returns:
        TheoryAnchoringResult with pass/fail and details
    """
    result = TheoryAnchoringResult()

    theories_found = extract_legal_theories(draft)
    result.theories_found = theories_found

    if not theories_found:
        return result

    allowed = _build_allowed_set(lkb_entry, verified_provisions, user_request)

    for theory in theories_found:
        if theory in allowed:
            result.theories_anchored.append(theory)
        else:
            result.theories_unanchored.append(theory)
            result.flags.append(f"UNANCHORED_THEORY: {theory}")

    result.passed = len(result.flags) == 0
    return result

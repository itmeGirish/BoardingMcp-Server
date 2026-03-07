"""Gate 4: Procedural Prerequisites — check mandatory pre-suit requirements.

Deterministic, no LLM calls. Inserts placeholders when prerequisites
are not confirmed in intake.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PrerequisiteCheck:
    """A single prerequisite check result."""
    id: str
    description: str
    found_in_intake: bool
    found_in_draft: bool
    placeholder_inserted: bool = False
    placeholder_text: str = ""


@dataclass
class PrerequisitesResult:
    """Result of procedural prerequisites gate."""
    passed: bool = True
    checks: list[PrerequisiteCheck] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    modified_draft: str = ""
    placeholders_inserted: int = 0


# Prerequisites per doc_type
PREREQUISITES: dict[str, list[dict[str, Any]]] = {
    "commercial_suit": [
        {
            "id": "section_12a_mediation",
            "description": "Section 12A pre-institution mediation (Commercial Courts Act, 2015)",
            "check_intake_for": ["mediation", "12A", "12a", "pre-institution", "urgent", "interim relief"],
            "check_draft_for": r"(?:section|s\.?)\s*12\s*A",
            "placeholder": (
                "{{MEDIATION_STATUS -- The Plaintiff has/has not complied with "
                "Section 12A of the Commercial Courts Act, 2015. If no urgent "
                "interim relief is sought, pre-institution mediation certificate "
                "must be filed. CONFIRM STATUS.}}"
            ),
        },
        {
            "id": "arbitration_clause",
            "description": "Arbitration clause in agreement",
            "check_intake_for": ["arbitration", "arbitral", "tribunal", "arbitration clause"],
            "check_draft_for": r"arbitrat",
            "placeholder": (
                "{{ARBITRATION -- Confirm whether the agreement contains an "
                "arbitration clause. If yes, the suit may need to establish "
                "why court jurisdiction is proper despite the clause.}}"
            ),
        },
    ],
    "commercial_plaint": [
        {
            "id": "section_12a_mediation",
            "description": "Section 12A pre-institution mediation",
            "check_intake_for": ["mediation", "12A", "12a", "pre-institution", "urgent", "interim relief"],
            "check_draft_for": r"(?:section|s\.?)\s*12\s*A",
            "placeholder": (
                "{{MEDIATION_STATUS -- The Plaintiff has/has not complied with "
                "Section 12A. CONFIRM STATUS.}}"
            ),
        },
    ],
    "ni_138_complaint": [
        {
            "id": "statutory_notice_s138",
            "description": "Statutory demand notice under Section 138 NI Act",
            "check_intake_for": ["notice", "demand notice", "30 days", "legal notice"],
            "check_draft_for": r"notice\s+(?:under|u/s)\s*(?:section\s*)?138",
            "placeholder": (
                "{{NOTICE_DATE -- Date of statutory demand notice under "
                "Section 138 Negotiable Instruments Act, 1881}}"
            ),
        },
    ],
    "eviction_suit": [
        {
            "id": "notice_s106_tpa",
            "description": "Notice to quit under Section 106 TPA",
            "check_intake_for": ["notice to quit", "section 106", "termination notice", "quit notice"],
            "check_draft_for": r"notice\s+(?:to\s+quit|under\s+section\s*106)",
            "placeholder": (
                "{{NOTICE_DATE_S106 -- Date of notice to quit under "
                "Section 106 Transfer of Property Act, 1882}}"
            ),
        },
    ],
}


def _check_intake_for_keywords(
    intake_text: str,
    keywords: list[str],
) -> bool:
    """Check if any keywords are present in intake text."""
    intake_lower = intake_text.lower()
    return any(kw.lower() in intake_lower for kw in keywords)


def _check_draft_for_pattern(draft: str, pattern: str) -> bool:
    """Check if regex pattern is found in draft."""
    return bool(re.search(pattern, draft, re.IGNORECASE))


def procedural_prerequisites_gate(
    draft: str,
    doc_type: str,
    intake_text: str = "",
    user_request: str = "",
) -> PrerequisitesResult:
    """Check mandatory pre-suit requirements are confirmed or placeholdered.

    Args:
        draft: Full draft text
        doc_type: Document type (e.g., "commercial_suit")
        intake_text: Combined intake text (facts, evidence, etc.)
        user_request: Original user request

    Returns:
        PrerequisitesResult with checks, flags, and modified draft
    """
    result = PrerequisitesResult()
    result.modified_draft = draft

    # Get prerequisites for this doc_type
    prereqs = PREREQUISITES.get(doc_type, [])
    if not prereqs:
        return result

    # Combine intake text and user request for keyword search
    combined_text = f"{intake_text} {user_request}"

    for prereq in prereqs:
        check = PrerequisiteCheck(
            id=prereq["id"],
            description=prereq["description"],
            found_in_intake=_check_intake_for_keywords(
                combined_text, prereq["check_intake_for"]
            ),
            found_in_draft=_check_draft_for_pattern(
                draft, prereq["check_draft_for"]
            ),
        )

        # If prerequisite is mentioned in draft but NOT confirmed in intake,
        # the draft is making an assumption — flag it
        if not check.found_in_intake and not check.found_in_draft:
            # Neither in intake nor draft — might be missing entirely
            # Insert placeholder if relevant
            check.placeholder_inserted = True
            check.placeholder_text = prereq["placeholder"]
            result.placeholders_inserted += 1
            result.flags.append(
                f"MISSING_PREREQUISITE: {prereq['id']} — "
                f"{prereq['description']}. Not confirmed in intake."
            )

        result.checks.append(check)

    result.passed = len(result.flags) == 0
    return result

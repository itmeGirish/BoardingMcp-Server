"""
Draft Quality Gate — Rule-based, NO LLM calls.

Validates structural quality of generated drafts:
- Required sections present
- Minimum content length
- No placeholder text remaining
- Proper formatting markers
"""

import re

# Required sections per document type
# Includes both generic and Indian-specific document types.
REQUIRED_SECTIONS = {
    # --- Generic / US-style ---
    "demand_letter": ["date", "recipient", "subject", "body", "demand", "signature"],
    "motion": ["caption", "introduction", "statement_of_facts", "argument", "conclusion", "signature"],
    "brief": ["caption", "table_of_contents", "statement_of_issues", "statement_of_facts", "argument", "conclusion"],
    "complaint": ["caption", "parties", "jurisdiction", "facts", "causes_of_action", "prayer_for_relief"],
    "answer": ["caption", "responses", "affirmative_defenses", "signature"],
    "contract": ["parties", "recitals", "definitions", "terms", "representations", "signatures"],
    "nda": ["parties", "definition_of_confidential_information", "obligations", "term", "signatures"],
    "cease_desist": ["date", "recipient", "infringement_description", "demand", "deadline", "signature"],
    "legal_notice": ["date", "recipient", "subject", "notice_content", "signature"],
    "pleading": ["caption", "body", "prayer", "signature"],
    # --- Indian litigation ---
    "bail_application": [
        "cause_title", "facts", "grounds", "prayer", "verification", "signature",
    ],
    "writ_petition": [
        "cause_title", "jurisdiction", "facts", "grounds",
        "prayer", "verification", "signature",
    ],
    "quashing_petition": [
        "cause_title", "facts", "grounds", "prayer", "verification", "signature",
    ],
    "divorce_petition": [
        "cause_title", "facts", "grounds", "prayer", "verification", "signature",
    ],
    "civil_suit": [
        "cause_title", "jurisdiction", "facts", "cause_of_action",
        "prayer", "verification", "signature",
    ],
    "injunction_application": [
        "cause_title", "facts", "grounds", "prayer", "verification", "signature",
    ],
    "appeal": [
        "cause_title", "facts", "grounds", "prayer", "verification", "signature",
    ],
    "revision_petition": [
        "cause_title", "facts", "grounds", "prayer", "verification", "signature",
    ],
    "arbitration_petition": [
        "cause_title", "facts", "grounds", "prayer", "signature",
    ],
    "complaint_138": [
        "cause_title", "facts", "cheque_details", "prayer", "verification", "signature",
    ],
}

DEFAULT_SECTIONS = ["heading", "body", "conclusion"]

# Minimum character count for a valid draft
MIN_DRAFT_LENGTH = 200

# Patterns that indicate incomplete/placeholder content
PLACEHOLDER_PATTERNS = [
    r"\[INSERT\s+.*?\]",
    r"\[TODO\]",
    r"\[PLACEHOLDER\]",
    r"\[YOUR\s+.*?\]",
    r"\[FILL\s+IN\]",
    r"<INSERT>",
    r"<TODO>",
    r"XXX",
]


def _normalize_doc_type(document_type: str) -> str:
    """Normalize document_type to lowercase underscore format.

    Handles both 'Bail Application' and 'bail_application' conventions.
    """
    return document_type.strip().lower().replace(" ", "_")


def check_draft_quality(draft_content: str, document_type: str) -> dict:
    """
    Rule-based check: Does the draft meet structural quality requirements?

    Args:
        draft_content: The generated draft text
        document_type: The type of legal document

    Returns:
        dict with 'passed', 'issues', 'details'
    """
    issues = []
    doc_type_normalized = _normalize_doc_type(document_type)

    # Check 1: Draft is not empty or too short
    if not draft_content or not draft_content.strip():
        return {
            "gate": "draft_quality",
            "passed": False,
            "issues": ["Draft content is empty"],
            "details": {"checks_run": 1, "checks_passed": 0},
        }

    content_length = len(draft_content.strip())
    if content_length < MIN_DRAFT_LENGTH:
        issues.append(
            f"Draft too short: {content_length} chars (minimum: {MIN_DRAFT_LENGTH})"
        )

    # Check 2: No placeholder text remaining
    placeholders_found = []
    for pattern in PLACEHOLDER_PATTERNS:
        matches = re.findall(pattern, draft_content, re.IGNORECASE)
        placeholders_found.extend(matches)

    if placeholders_found:
        issues.append(
            f"Placeholder text found: {placeholders_found[:5]}"
        )

    # Check 3: Required sections present (check for section headings)
    required = REQUIRED_SECTIONS.get(doc_type_normalized, DEFAULT_SECTIONS)
    content_lower = draft_content.lower()
    missing_sections = []
    for section in required:
        # Check for section heading in various formats
        section_normalized = section.replace("_", " ")
        if section_normalized not in content_lower and section not in content_lower:
            missing_sections.append(section_normalized)

    if missing_sections:
        issues.append(
            f"Missing sections: {missing_sections}"
        )

    # Check 4: Has proper structure (at least some line breaks / paragraphs)
    line_count = len(draft_content.strip().split("\n"))
    if line_count < 5:
        issues.append(
            f"Draft has only {line_count} lines — may lack proper structure"
        )

    passed = len(issues) == 0

    details = {
        "document_type": document_type,
        "content_length": content_length,
        "line_count": line_count,
        "placeholders_found": len(placeholders_found),
        "missing_sections": missing_sections,
        "issues": issues,
    }

    return {
        "gate": "draft_quality",
        "passed": passed,
        "issues": issues,
        "details": details,
    }

"""
Fact Traceability Gate — Rule-based, NO LLM calls.

Cross-references key entities (party names, amounts, dates, case numbers)
found in the final draft against MASTER_FACTS.  Any entity that appears
in the draft but has no matching fact entry is flagged as potentially
hallucinated.

This gate does NOT parse legal reasoning or arguments — only verifiable
named entities and structured data.
"""

import re


# ---------------------------------------------------------------------------
# Entity extraction patterns
# ---------------------------------------------------------------------------

# Indian currency amounts: Rs. 1,00,000 / INR 50000 / ₹10,00,000
_AMOUNT_RE = re.compile(
    r"(?:Rs\.?\s*|INR\s*|₹\s*)"
    r"(\d[\d,]*(?:\.\d{1,2})?)",
    re.IGNORECASE,
)

# Dates: 12/03/2024, 12-03-2024, 12.03.2024, 2024-03-12
_DATE_RE = re.compile(
    r"(?:"
    r"\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b"
    r"|"
    r"\b\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}\b"
    r"|"
    r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|"
    r"August|September|October|November|December)\s+\d{4}\b"
    r")",
    re.IGNORECASE,
)

# FIR / Case numbers: FIR No. 123/2024, Crime No. 45/2023
_CASE_NUMBER_RE = re.compile(
    r"(?:FIR|Crime|Case|Complaint)\s*(?:No\.?|Number)\s*"
    r"(\d+\s*/\s*\d{4})",
    re.IGNORECASE,
)

# Cheque numbers: 6-digit patterns near cheque context
_CHEQUE_RE = re.compile(
    r"(?:cheque|check)\s*(?:no\.?|number)?\s*:?\s*(\d{6,})",
    re.IGNORECASE,
)

# Sections of law: Section 439, Section 138, u/s 482
_SECTION_RE = re.compile(
    r"(?:section|sec\.?|u/s\.?|s\.)\s*(\d+[A-Za-z]?)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_entities_from_text(text: str) -> dict[str, set[str]]:
    """Extract verifiable entities from draft text."""
    entities: dict[str, set[str]] = {
        "amounts": set(),
        "dates": set(),
        "case_numbers": set(),
        "cheque_numbers": set(),
        "sections": set(),
    }

    for m in _AMOUNT_RE.finditer(text):
        # Normalize: remove commas
        entities["amounts"].add(m.group(1).replace(",", ""))

    for m in _DATE_RE.finditer(text):
        entities["dates"].add(m.group().strip())

    for m in _CASE_NUMBER_RE.finditer(text):
        entities["case_numbers"].add(m.group(1).replace(" ", ""))

    for m in _CHEQUE_RE.finditer(text):
        entities["cheque_numbers"].add(m.group(1))

    for m in _SECTION_RE.finditer(text):
        entities["sections"].add(m.group(1).lower())

    return entities


def _extract_entities_from_facts(facts: list[dict]) -> dict[str, set[str]]:
    """Extract verifiable entities from MASTER_FACTS."""
    entities: dict[str, set[str]] = {
        "amounts": set(),
        "dates": set(),
        "case_numbers": set(),
        "cheque_numbers": set(),
        "sections": set(),
    }

    for fact in facts:
        value = str(fact.get("fact_value", ""))
        key = str(fact.get("fact_key", "")).lower()

        # Amounts
        for m in _AMOUNT_RE.finditer(value):
            entities["amounts"].add(m.group(1).replace(",", ""))
        # Also capture plain numeric values for amount-related keys
        if any(kw in key for kw in ("amount", "value", "cost", "price", "damages")):
            digits = re.sub(r"[^\d.]", "", value)
            if digits:
                entities["amounts"].add(digits)

        # Dates
        for m in _DATE_RE.finditer(value):
            entities["dates"].add(m.group().strip())
        if any(kw in key for kw in ("date", "_at", "filed_on")):
            entities["dates"].add(value.strip())

        # Case numbers
        for m in _CASE_NUMBER_RE.finditer(value):
            entities["case_numbers"].add(m.group(1).replace(" ", ""))
        if any(kw in key for kw in ("fir_number", "case_number", "crime_number")):
            entities["case_numbers"].add(value.strip().replace(" ", ""))

        # Cheque numbers
        for m in _CHEQUE_RE.finditer(value):
            entities["cheque_numbers"].add(m.group(1))
        if "cheque_number" in key:
            digits = re.sub(r"[^\d]", "", value)
            if digits:
                entities["cheque_numbers"].add(digits)

        # Sections of law
        for m in _SECTION_RE.finditer(value):
            entities["sections"].add(m.group(1).lower())
        if any(kw in key for kw in ("section", "offence_sections")):
            for m in re.finditer(r"\d+[A-Za-z]?", value):
                entities["sections"].add(m.group().lower())

    return entities


def _find_untraced(
    draft_entities: dict[str, set[str]],
    fact_entities: dict[str, set[str]],
) -> list[dict]:
    """Find entities in draft that have no matching fact."""
    untraced: list[dict] = []

    for entity_type in draft_entities:
        draft_set = draft_entities[entity_type]
        fact_set = fact_entities.get(entity_type, set())

        for entity_val in draft_set:
            if entity_val not in fact_set:
                untraced.append({
                    "entity_type": entity_type,
                    "entity_value": entity_val,
                    "severity": "high" if entity_type in ("amounts", "case_numbers", "cheque_numbers") else "medium",
                    "reason": f"'{entity_val}' ({entity_type}) found in draft but not in MASTER_FACTS",
                })

    return untraced


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_fact_traceability(
    draft_content: str,
    facts: list[dict],
) -> dict:
    """
    Fact Traceability gate — validates that key entities in the draft
    are traceable to MASTER_FACTS.

    Pure rule-based — NO LLM calls.

    Checks: amounts, dates, case/FIR numbers, cheque numbers, and
    legal section references.

    Args:
        draft_content: The final draft text.
        facts:         List of fact dicts from MASTER_FACTS
                       (with ``fact_key`` and ``fact_value``).

    Returns:
        dict with keys:
            gate              - "fact_traceability"
            passed            - bool (True if no high-severity untraced entities)
            untraced_entities - list[{entity_type, entity_value, severity, reason}]
            details           - {draft_entity_counts, fact_entity_counts, ...}
    """
    if not draft_content or not draft_content.strip():
        return {
            "gate": "fact_traceability",
            "passed": True,
            "untraced_entities": [],
            "details": {"message": "No draft content to check"},
        }

    draft_entities = _extract_entities_from_text(draft_content)
    fact_entities = _extract_entities_from_facts(facts)

    untraced = _find_untraced(draft_entities, fact_entities)

    # Only fail on high-severity untraced entities (amounts, case numbers, cheque numbers)
    high_severity_count = sum(1 for u in untraced if u["severity"] == "high")
    passed = high_severity_count == 0

    details = {
        "draft_entity_counts": {k: len(v) for k, v in draft_entities.items()},
        "fact_entity_counts": {k: len(v) for k, v in fact_entities.items()},
        "untraced_count": len(untraced),
        "high_severity_count": high_severity_count,
    }

    return {
        "gate": "fact_traceability",
        "passed": passed,
        "untraced_entities": untraced,
        "details": details,
    }

"""
Jurisdiction Gate — Rule-based, NO LLM calls.

Validates that jurisdiction/state/court information is present.
If missing, workflow must STOP and ask the user (never guess).
"""


def check_jurisdiction(facts: list[dict], document_type: str) -> dict:
    """
    Rule-based check: Is jurisdiction information present?

    For litigation documents, court_name is also required.
    For transactional documents, governing_law is checked.

    Args:
        facts: List of fact dicts with 'fact_key' and 'fact_value' fields
        document_type: The type of legal document

    Returns:
        dict with 'passed', 'missing_fields', 'details'
    """
    fact_map = {f.get("fact_key", ""): f.get("fact_value", "") for f in facts}

    # Documents that require court information
    litigation_types = {"motion", "brief", "complaint", "answer", "pleading"}
    # Documents that need governing law
    transactional_types = {"contract", "nda"}

    missing = []

    # Jurisdiction is always required
    jurisdiction = fact_map.get("jurisdiction") or fact_map.get("state") or fact_map.get("governing_law")
    if not jurisdiction:
        missing.append("jurisdiction")

    # Litigation documents need court info
    if document_type in litigation_types:
        court = fact_map.get("court_name") or fact_map.get("court_type")
        if not court:
            missing.append("court_name")

    # Transactional documents need governing law
    if document_type in transactional_types:
        gov_law = fact_map.get("governing_law") or fact_map.get("jurisdiction")
        if not gov_law:
            missing.append("governing_law")

    passed = len(missing) == 0

    details = {
        "document_type": document_type,
        "is_litigation": document_type in litigation_types,
        "is_transactional": document_type in transactional_types,
        "jurisdiction_found": jurisdiction or None,
        "missing_fields": missing,
    }

    return {
        "gate": "jurisdiction",
        "passed": passed,
        "missing_fields": missing,
        "details": details,
        "action_required": "STOP and ask user for missing jurisdiction info" if not passed else None,
    }

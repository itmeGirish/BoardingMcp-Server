"""
Fact Completeness Gate — Rule-based, NO LLM calls.

Checks that all required facts are present for the selected document type.
"""

# Required facts per document type (keys are lowercase underscore format).
REQUIRED_FACTS = {
    # --- Generic / US-style ---
    "demand_letter": {
        "required": ["sender_name", "recipient_name", "demand_description", "deadline"],
        "recommended": ["amount", "prior_communication", "legal_basis"],
    },
    "motion": {
        "required": ["case_title", "court_name", "motion_type", "moving_party", "grounds"],
        "recommended": ["case_number", "opposing_party", "supporting_facts"],
    },
    "brief": {
        "required": ["case_title", "court_name", "issue_presented", "argument_summary"],
        "recommended": ["case_number", "statement_of_facts", "standard_of_review"],
    },
    "complaint": {
        "required": ["plaintiff_name", "defendant_name", "cause_of_action", "facts_alleged", "relief_sought"],
        "recommended": ["court_name", "jurisdiction_basis", "venue"],
    },
    "answer": {
        "required": ["case_title", "defendant_name", "responses_to_allegations"],
        "recommended": ["case_number", "affirmative_defenses", "counterclaims"],
    },
    "contract": {
        "required": ["party_a", "party_b", "subject_matter", "terms"],
        "recommended": ["effective_date", "termination_clause", "governing_law"],
    },
    "nda": {
        "required": ["disclosing_party", "receiving_party", "confidential_info_definition", "duration"],
        "recommended": ["exclusions", "permitted_disclosures", "governing_law"],
    },
    "cease_desist": {
        "required": ["sender_name", "recipient_name", "infringing_activity", "demanded_action"],
        "recommended": ["legal_basis", "evidence_summary", "deadline"],
    },
    "legal_notice": {
        "required": ["sender_name", "recipient_name", "subject_matter", "notice_content"],
        "recommended": ["legal_basis", "response_deadline"],
    },
    "pleading": {
        "required": ["case_title", "court_name", "party_name", "claims_or_defenses"],
        "recommended": ["case_number", "supporting_facts", "relief_sought"],
    },
    # --- Indian litigation ---
    "bail_application": {
        "required": ["accused_name", "fir_number", "police_station", "offence_sections"],
        "recommended": ["court_name", "jurisdiction", "grounds", "surety_details"],
    },
    "writ_petition": {
        "required": ["petitioner_name", "respondent_name", "relief_sought", "jurisdiction"],
        "recommended": ["court_name", "fundamental_right", "grounds"],
    },
    "quashing_petition": {
        "required": ["petitioner_name", "respondent_name", "fir_number"],
        "recommended": ["police_station", "offence_sections", "grounds"],
    },
    "divorce_petition": {
        "required": ["petitioner_name", "respondent_name", "marriage_date"],
        "recommended": ["marriage_place", "children_details", "grounds"],
    },
    "civil_suit": {
        "required": ["plaintiff_name", "defendant_name", "cause_of_action"],
        "recommended": ["court_name", "jurisdiction", "relief_sought", "property_description"],
    },
    "injunction_application": {
        "required": ["applicant_name", "respondent_name", "property_description"],
        "recommended": ["court_name", "urgency_reason", "balance_of_convenience"],
    },
    "appeal": {
        "required": ["appellant_name", "respondent_name", "impugned_order"],
        "recommended": ["court_name", "grounds", "date_of_order"],
    },
    "revision_petition": {
        "required": ["petitioner_name", "respondent_name", "impugned_order"],
        "recommended": ["court_name", "grounds", "date_of_order"],
    },
    "arbitration_petition": {
        "required": ["petitioner_name", "respondent_name", "arbitration_clause"],
        "recommended": ["court_name", "relief_sought", "contract_details"],
    },
    "complaint_138": {
        "required": ["complainant_name", "accused_name", "cheque_number", "cheque_amount", "bank_name"],
        "recommended": ["cheque_date", "presentation_date", "dishonour_date", "notice_date"],
    },
}

# Fallback for unknown document types
DEFAULT_REQUIRED = {
    "required": ["party_names", "subject_matter", "key_facts"],
    "recommended": ["jurisdiction", "legal_basis"],
}


def _normalize_doc_type(document_type: str) -> str:
    """Normalize document_type to lowercase underscore format."""
    return document_type.strip().lower().replace(" ", "_")


def check_fact_completeness(facts: list[dict], document_type: str) -> dict:
    """
    Rule-based check: Are all required facts present for this document type?

    Args:
        facts: List of fact dicts with 'fact_key' field
        document_type: The type of legal document

    Returns:
        dict with 'passed', 'missing_required', 'missing_recommended', 'details'
    """
    doc_type_normalized = _normalize_doc_type(document_type)
    requirements = REQUIRED_FACTS.get(doc_type_normalized, DEFAULT_REQUIRED)
    fact_keys = {f.get("fact_key", "") for f in facts}

    missing_required = [r for r in requirements["required"] if r not in fact_keys]
    missing_recommended = [r for r in requirements.get("recommended", []) if r not in fact_keys]

    passed = len(missing_required) == 0

    details = {
        "document_type": document_type,
        "total_facts": len(facts),
        "required_count": len(requirements["required"]),
        "present_required": len(requirements["required"]) - len(missing_required),
        "missing_required": missing_required,
        "missing_recommended": missing_recommended,
    }

    return {
        "gate": "fact_completeness",
        "passed": passed,
        "missing_required": missing_required,
        "missing_recommended": missing_recommended,
        "details": details,
    }

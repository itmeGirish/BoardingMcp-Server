"""
Clarification Handler Gate  (CLAUD.md Step 5) -- Rule-based, NO LLM calls.

Aggregates all "needs_clarification" and "hard_block" signals from
upstream gates and fact extraction.  If anything critical is missing
the workflow MUST stop and present questions to the user -- never guess.
"""


# ---------------------------------------------------------------------------
# Mandatory facts per document type  (a lighter subset than fact_completeness;
# these are the bare-minimum fields without which we cannot even begin drafting)
# ---------------------------------------------------------------------------

_MANDATORY_FACTS: dict[str, list[str]] = {
    "bail_application": [
        "accused_name", "fir_number", "police_station", "offence_sections",
    ],
    "writ_petition": [
        "petitioner_name", "respondent_name", "relief_sought",
    ],
    "complaint_138": [
        "complainant_name", "accused_name", "cheque_number", "cheque_amount",
        "bank_name",
    ],
    "divorce_petition": [
        "petitioner_name", "respondent_name", "marriage_date",
    ],
    "civil_suit": [
        "plaintiff_name", "defendant_name", "cause_of_action",
    ],
    "injunction_application": [
        "applicant_name", "respondent_name", "property_description",
    ],
    "quashing_petition": [
        "petitioner_name", "respondent_name", "fir_number",
    ],
    "appeal": [
        "appellant_name", "respondent_name", "impugned_order",
    ],
    "revision_petition": [
        "petitioner_name", "respondent_name", "impugned_order",
    ],
    "arbitration_petition": [
        "petitioner_name", "respondent_name", "arbitration_clause",
    ],
    "legal_notice": [
        "sender_name", "recipient_name", "subject_matter",
    ],
    "contract": [
        "party_a", "party_b", "subject_matter",
    ],
    "nda": [
        "disclosing_party", "receiving_party",
    ],
}

_DEFAULT_MANDATORY = ["party_names", "subject_matter"]

# Minimum acceptable classification confidence
_MIN_CLASSIFICATION_CONFIDENCE = 0.5


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_jurisdiction(facts: list[dict]) -> list[dict]:
    """
    Return questions if jurisdiction / state is missing or unspecified.
    """
    questions: list[dict] = []
    fact_map = {f.get("fact_key", ""): f.get("fact_value", "") for f in facts}

    jurisdiction = (
        fact_map.get("jurisdiction", "")
        or fact_map.get("state", "")
        or fact_map.get("governing_law", "")
    )

    if not jurisdiction or jurisdiction.lower().strip() in ("unspecified", "unknown", ""):
        questions.append({
            "field": "jurisdiction",
            "question": (
                "Which state / jurisdiction does this matter fall under? "
                "Please specify the exact state and court."
            ),
        })

    return questions


def _check_gate_flags(gate_results: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Scan prior gate results for needs_clarification or hard_block flags.

    Returns:
        (questions, hard_blocks)
    """
    questions: list[dict] = []
    hard_blocks: list[dict] = []

    for gr in gate_results:
        gate_name = gr.get("gate", "unknown")

        # Check for explicit needs_clarification
        if gr.get("needs_clarification"):
            # Pull conflict details if available (e.g. from route_resolver)
            conflicts = gr.get("conflict_details", {})
            for field, detail in conflicts.items():
                rule_guess = detail.get("rule_guess")
                llm_guess = detail.get("llm_guess")
                questions.append({
                    "field": field,
                    "question": (
                        f"Conflicting classification for '{field}': "
                        f"rule-based suggests '{rule_guess}', "
                        f"LLM suggests '{llm_guess}'. "
                        f"Please confirm the correct value."
                    ),
                })

            # Fallback if no conflict_details but still needs clarification
            if not conflicts:
                missing = gr.get("missing_fields", [])
                for field in missing:
                    questions.append({
                        "field": field,
                        "question": f"Please provide the missing '{field}'.",
                    })

        # Check for hard blocks
        if gr.get("hard_block") or (not gr.get("passed", True) and gr.get("action_required")):
            hard_blocks.append({
                "gate": gate_name,
                "reason": gr.get("action_required") or "Gate did not pass",
                "details": {
                    k: v for k, v in gr.items()
                    if k not in ("gate", "passed", "action_required")
                },
            })

    return questions, hard_blocks


def _check_classification_confidence(classification: dict) -> list[dict]:
    """
    Return questions if classification confidence is too low.
    """
    questions: list[dict] = []
    confidence = float(classification.get("confidence", 0.0))

    if confidence < _MIN_CLASSIFICATION_CONFIDENCE:
        doc_type = classification.get("doc_type") or classification.get("doc_type_guess")
        questions.append({
            "field": "document_type",
            "question": (
                f"We are not confident about the document type "
                f"(current guess: '{doc_type}', confidence: {confidence:.0%}). "
                f"Please confirm: what type of legal document do you need?"
            ),
        })

    return questions


def _normalize_doc_type(doc_type: str) -> str:
    """Normalize document_type to lowercase underscore format."""
    return doc_type.strip().lower().replace(" ", "_")


def _check_mandatory_facts(facts: list[dict], classification: dict) -> list[dict]:
    """
    Return questions for any mandatory facts missing based on the doc_type.
    """
    questions: list[dict] = []
    doc_type = (
        classification.get("doc_type")
        or classification.get("doc_type_guess")
        or ""
    )
    doc_type_normalized = _normalize_doc_type(doc_type)

    mandatory = _MANDATORY_FACTS.get(doc_type_normalized, _DEFAULT_MANDATORY)
    fact_keys = {f.get("fact_key", "") for f in facts}

    for field in mandatory:
        if field not in fact_keys:
            # Humanise the field name for the question
            human_field = field.replace("_", " ")
            questions.append({
                "field": field,
                "question": f"Please provide the {human_field}.",
            })

    return questions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_clarification_needed(
    facts: list[dict],
    classification: dict,
    gate_results: list[dict],
) -> dict:
    """
    Clarification handler gate (Step 5).

    Aggregates all needs_clarification / hard_block signals.  If any
    critical information is missing the workflow MUST stop.

    Pure rule-based -- no LLM calls.

    Args:
        facts:          List of extracted fact dicts (``fact_key``, ``fact_value``).
        classification: Resolved classification dict (from route_resolver or
                        a single classifier).  Expected keys: doc_type (or
                        doc_type_guess), confidence.
        gate_results:   List of output dicts from all gates run so far.

    Returns:
        dict with keys:
            gate                 - "clarification_handler"
            passed               - bool  (True = no clarification needed)
            needs_clarification  - bool
            questions            - list[{field, question}]
            hard_blocks          - list[{gate, reason, details}]
    """
    all_questions: list[dict] = []
    all_hard_blocks: list[dict] = []

    # 1. Jurisdiction check
    all_questions.extend(_check_jurisdiction(facts))

    # 2. Gate flag aggregation
    gate_questions, gate_blocks = _check_gate_flags(gate_results)
    all_questions.extend(gate_questions)
    all_hard_blocks.extend(gate_blocks)

    # 3. Classification confidence check
    all_questions.extend(_check_classification_confidence(classification))

    # 4. Mandatory facts check
    all_questions.extend(_check_mandatory_facts(facts, classification))

    # Deduplicate questions by field (keep first occurrence)
    seen_fields: set[str] = set()
    unique_questions: list[dict] = []
    for q in all_questions:
        field = q["field"]
        if field not in seen_fields:
            seen_fields.add(field)
            unique_questions.append(q)

    needs_clarification = len(unique_questions) > 0 or len(all_hard_blocks) > 0
    passed = not needs_clarification

    return {
        "gate": "clarification_handler",
        "passed": passed,
        "needs_clarification": needs_clarification,
        "questions": unique_questions,
        "hard_blocks": all_hard_blocks,
    }

"""Group 11 — Special & Miscellaneous causes."""
from __future__ import annotations

from ._helpers import (
    COMMON_CIVIL_PLAINT_SECTIONS,
    _civil_court_rules,
    _entry,
)

CAUSES: dict = {
    "periodically_recurring_right": _entry(
        registry_kind="cause",
        code="periodically_recurring_right",
        display_name="Suit to establish a periodically recurring right",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16"]},
        ],
        limitation={"article": "104", "period": "Three years", "from": "When the plaintiff is first refused the enjoyment of the right"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "right_description",
            "periodic_character",
            "first_refusal",
            "evidence_of_past_enjoyment",
        ],
        required_reliefs=["declaration_of_right", "permanent_injunction", "damages_if_applicable", "costs"],
        doc_type_keywords=["recurring right", "periodic right", "irrigation right", "seasonal right", "customary right"],
        drafting_red_flags=[
            "Art 104 starts from FIRST refusal — not from each subsequent refusal.",
            "Must establish the periodic/recurring character of the right — one-time right does not qualify.",
            "Common in rural disputes: irrigation rights, grazing rights, fair/market rights, customary passage on specific days.",
        ],
        complexity_weight=2,
    ),
    "hereditary_office_possession": _entry(
        registry_kind="cause",
        code="hereditary_office_possession",
        display_name="Suit for possession of hereditary office",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16"]},
        ],
        limitation={"article": "107", "period": "Twelve years", "from": "When the defendant takes possession of the office adversely to the plaintiff"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "office_description",
            "hereditary_character",
            "plaintiff_succession_right",
            "defendant_adverse_claim",
        ],
        required_reliefs=["declaration_of_right_to_office", "possession_of_office", "costs"],
        doc_type_keywords=["hereditary office", "temple priest", "village accountant", "pujari", "archaka"],
        drafting_red_flags=[
            "Art 107 Explanation: hereditary office is 'possessed' when its properties are usually received, or if no properties, when its duties are usually performed.",
            "Still litigated in some states for temple offices, traditional village offices.",
            "Must prove hereditary succession chain.",
        ],
        complexity_weight=3,
    ),
}

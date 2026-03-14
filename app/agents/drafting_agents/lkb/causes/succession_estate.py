"""Group 12 — Succession & Estate causes."""
from __future__ import annotations

from ._helpers import (
    _entry,
)

CAUSES: dict = {
    "probate_petition": _entry(
        registry_kind="cause",
        code="probate_petition",
        document_type="petition",
        display_name="Petition for Probate of Will",
        primary_acts=[
            {"act": "Indian Succession Act, 1925", "sections": ["Section 2(f)", "Section 222", "Section 223", "Section 276"]},
        ],
        limitation={"article": "137", "period": "Three years", "from": "When the right to apply accrues; do not assume it invariably runs from the date of death"},
        required_sections=[
            "court_heading",
            "petitioner_details",
            "deceased_details",
            "will_details",
            "asset_schedule",
            "legal_heirs",
            "prayer_for_probate",
        ],
        doc_type_keywords=["probate", "will", "testator", "executor", "testamentary"],
        drafting_red_flags=[
            "Probate is the testamentary grant to the executor named in the will; screen territorial jurisdiction, citations, caveats, and local High Court testamentary practice carefully.",
            "S.223: Minors and persons of unsound mind cannot be granted probate.",
        ],
        complexity_weight=3,
    ),
    "letters_of_administration": _entry(
        registry_kind="cause",
        code="letters_of_administration",
        document_type="petition",
        display_name="Petition for Letters of Administration",
        primary_acts=[
            {"act": "Indian Succession Act, 1925", "sections": ["Section 218", "Section 234", "Section 235", "Section 276"]},
        ],
        limitation={"article": "137", "period": "Three years", "from": "When right to apply accrues"},
        required_sections=[
            "court_heading",
            "petitioner_details",
            "deceased_details",
            "intestacy_statement_or_will_without_executor",
            "asset_schedule",
            "legal_heirs",
            "prayer_for_administration",
        ],
        doc_type_keywords=["letters of administration", "intestate", "administrator", "estate administration"],
        drafting_red_flags=[
            "Filed when deceased died intestate OR will exists but no executor named/capable.",
            "S.234: priority order for grant — spouse, next of kin.",
            "Court issues citation/notice to all interested parties before grant.",
        ],
        complexity_weight=3,
    ),
    "succession_certificate": _entry(
        registry_kind="cause",
        code="succession_certificate",
        document_type="petition",
        display_name="Petition for Succession Certificate",
        primary_acts=[
            {"act": "Indian Succession Act, 1925", "sections": ["Section 370", "Section 371", "Section 372", "Section 373"]},
        ],
        limitation={"article": "137", "period": "Three years", "from": "When right to apply accrues"},
        required_sections=[
            "court_heading",
            "petitioner_details",
            "deceased_details",
            "debts_and_securities_schedule",
            "legal_heir_relationship",
            "prayer_for_certificate",
        ],
        doc_type_keywords=["succession certificate", "debts and securities", "section 370", "legal heir certificate"],
        drafting_red_flags=[
            "A succession certificate is confined to debts and securities; it is not the proceeding for adjudicating title to immovable property.",
            "Section 370 must be screened for excluded classes of debts/securities before filing.",
            "Summary proceedings — faster than probate.",
        ],
        complexity_weight=2,
    ),
}

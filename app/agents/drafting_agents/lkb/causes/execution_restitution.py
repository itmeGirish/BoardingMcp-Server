"""Group 10 — Execution & Restitution causes."""
from __future__ import annotations

from ._helpers import (
    COMMON_CIVIL_PLAINT_SECTIONS,
    _civil_court_rules,
    _entry,
)

CAUSES: dict = {
    "suit_on_judgment_decree": _entry(
        registry_kind="cause",
        code="suit_on_judgment_decree",
        display_name="Suit upon a judgment or decree including foreign judgment",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 13 (foreign judgment conditions)", "Section 44A (reciprocal enforcement)"]},
        ],
        limitation={"article": "101", "period": "Three years", "from": "The date of the judgment or recognisance"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "judgment_decree_details",
            "non_satisfaction",
            "enforcement_basis",
        ],
        required_reliefs=["money_decree_on_judgment", "costs"],
        doc_type_keywords=["suit on judgment", "foreign judgment", "decree enforcement", "recognisance"],
        drafting_red_flags=[
            "S.13 CPC: foreign judgment not conclusive if obtained by fraud, in breach of natural justice, founded on wrong jurisdiction, etc.",
            "S.44A CPC: decrees from reciprocating territories may be executed directly without fresh suit.",
            "Distinguish suit on judgment (Art 101, 3 years) from execution of decree (Art 136, 12 years).",
        ],
        complexity_weight=2,
    ),
    "set_aside_court_sale": _entry(
        registry_kind="cause",
        code="set_aside_court_sale",
        display_name="Suit to set aside sale by civil or revenue court",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16", "Order XXI"]},
        ],
        limitation={"article": "99", "period": "One year", "from": "When the sale is confirmed or would otherwise have become final and conclusive had no such suit been brought"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "sale_details",
            "decree_under_which_sold",
            "ground_for_setting_aside",
            "schedule_of_property",
        ],
        required_reliefs=["set_aside_sale", "restoration_of_property", "costs"],
        doc_type_keywords=["set aside court sale", "auction sale", "execution sale", "revenue sale"],
        drafting_red_flags=[
            "Limitation ONLY ONE YEAR (Art 99) from confirmation of sale.",
            "Distinguish from application to set aside sale under Order XXI Rule 90 (Art 127 — 60 days) which is filed IN the execution proceedings. Art 99 is for a SEPARATE SUIT.",
            "Grounds: material irregularity or fraud in conducting sale.",
        ],
        complexity_weight=2,
    ),
    "restitution_s144_cpc": _entry(
        registry_kind="cause",
        code="restitution_s144_cpc",
        document_type="application",
        display_name="Application for restitution under Section 144 CPC",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 144"]},
        ],
        limitation={"article": "137", "period": "Three years", "from": "When the right to apply accrues (typically when appellate decree reversing original decree is passed)"},
        required_sections=[
            "court_heading",
            "title",
            "original_decree_details",
            "appellate_reversal",
            "benefit_obtained_by_opposite_party",
            "restitution_sought",
        ],
        required_reliefs=["restitution_order", "refund_or_restoration", "interest_if_applicable", "costs"],
        doc_type_keywords=["restitution", "section 144", "reversal of decree", "restoration"],
        drafting_red_flags=[
            "S.144 CPC: court which passed original decree has jurisdiction for restitution.",
            "Restitution is based on equity — party who obtained benefit under reversed decree must restore it.",
            "Art 137: 3 years from right to apply (date of appellate decree, not original).",
        ],
        complexity_weight=2,
    ),
}

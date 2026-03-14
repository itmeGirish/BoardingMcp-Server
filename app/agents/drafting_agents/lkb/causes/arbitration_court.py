"""Group 14 -- Arbitration (Court-side) causes."""
from __future__ import annotations

from ._helpers import _entry

CAUSES: dict = {
    "arbitration_s9_interim": _entry(
        registry_kind="cause",
        code="arbitration_s9_interim",
        document_type="application",
        display_name="Application for Interim Measures (Section 9 A&C Act)",
        primary_acts=[
            {"act": "Arbitration and Conciliation Act, 1996", "sections": ["Section 9"]},
        ],
        limitation={"article": "137", "period": "Three years", "from": "When right to apply accrues"},
        required_sections=[
            "court_heading", "arbitration_agreement_details",
            "interim_measure_sought", "urgency_and_necessity", "prayer",
        ],
        doc_type_keywords=["section 9 arbitration", "interim measures", "arbitration injunction"],
        drafting_red_flags=[
            "Post-2015 Amendment: Section 9 relief after constitution of the tribunal is available only if the tribunal remedy is ineffective.",
            "Court must not enter into merits of the dispute.",
            "Section 9(3): after constitution of the tribunal, the court should not entertain the application unless circumstances make the tribunal remedy inefficacious.",
        ],
        complexity_weight=3,
    ),

    "arbitration_s11_appointment": _entry(
        registry_kind="cause",
        code="arbitration_s11_appointment",
        document_type="application",
        display_name="Application for Appointment of Arbitrator (Section 11 A&C Act)",
        primary_acts=[
            {"act": "Arbitration and Conciliation Act, 1996", "sections": ["Section 11"]},
        ],
        limitation={"article": "137", "period": "Three years", "from": "When right to apply accrues (when opposite party fails to appoint within 30 days of request)"},
        required_sections=[
            "court_heading", "arbitration_agreement",
            "failure_to_appoint", "proposed_arbitrator_if_any", "prayer",
        ],
        doc_type_keywords=["section 11 arbitration", "appoint arbitrator", "arbitrator appointment"],
        drafting_red_flags=[
            "Post-2015 amendment regime: Section 11(6A) confined scrutiny to the existence of the arbitration agreement, not the merits of the dispute.",
            "Section 11 applications go to the High Court for domestic arbitration and to the Supreme Court for international commercial arbitration.",
            "Court should confine examination to the existence of the arbitration agreement.",
            "Section 11(6): if a party fails to act within 30 days, the other party may approach the court for appointment.",
        ],
        complexity_weight=2,
    ),

    "arbitration_s34_set_aside": _entry(
        registry_kind="cause",
        code="arbitration_s34_set_aside",
        document_type="application",
        display_name="Application to Set Aside Arbitral Award (Section 34 A&C Act)",
        primary_acts=[
            {"act": "Arbitration and Conciliation Act, 1996", "sections": ["Section 34"]},
        ],
        limitation={
            "article": "N/A",
            "reference": "Section 34(3) of the Arbitration and Conciliation Act, 1996",
            "act": "Arbitration and Conciliation Act, 1996",
            "period": "Three months from receipt of award (extendable by 30 days only, not under Section 5 of the Limitation Act)",
            "from": "Date of receipt of arbitral award",
        },
        required_sections=[
            "court_heading", "award_details", "grounds_for_setting_aside",
            "s34_2_grounds_analysis", "prayer",
        ],
        doc_type_keywords=["set aside award", "section 34 arbitration", "challenge award"],
        drafting_red_flags=[
            "Strict three-month limitation plus a maximum thirty-day extension only.",
            "Grounds are confined to Section 34(2) and Section 34(2A), as applicable.",
            "Court cannot review the merits of the award.",
        ],
        complexity_weight=3,
    ),

    "arbitration_s37_appeal": _entry(
        registry_kind="cause",
        code="arbitration_s37_appeal",
        document_type="application",
        display_name="Appeal under Section 37 A&C Act",
        primary_acts=[
            {"act": "Arbitration and Conciliation Act, 1996", "sections": ["Section 37"]},
        ],
        limitation={
            "article": "N/A",
            "reference": "Section 37 of the Arbitration and Conciliation Act, 1996",
            "act": "Arbitration and Conciliation Act, 1996",
            "period": "Thirty days from the appealable order, or as prescribed by the applicable appellate regime",
            "from": "Date of the impugned order or decree",
        },
        required_sections=[
            "appellate_heading", "impugned_order_details",
            "s37_appealability_basis", "grounds", "prayer",
        ],
        doc_type_keywords=["section 37 arbitration", "arbitration appeal", "appeal against S.34 order"],
        drafting_red_flags=[
            "Section 37 appeal lies only against orders expressly listed in Section 37.",
            "No appeal lies against a pure Section 11 appointment order under Section 37.",
            "Appeal lies to the court authorized by law to hear appeals from the original order.",
        ],
        complexity_weight=3,
    ),
}

"""Group 16 -- Public Law & Special Proceedings causes."""
from __future__ import annotations

from ._helpers import _entry, COMMON_CIVIL_PLAINT_SECTIONS

CAUSES: dict = {
    "s92_cpc_public_trust": _entry(
        registry_kind="cause",
        code="s92_cpc_public_trust",
        display_name="Suit relating to Public Trust / Charity (Section 92 CPC)",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 92"]},
        ],
        limitation={"article": "113", "period": "Three years", "from": "When right to sue accrues"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "trust_details", "charitable_purpose",
            "breach_or_mismanagement", "ag_consent_or_two_interested_persons",
            "relief_sought",
        ],
        doc_type_keywords=["section 92 CPC", "public trust", "charitable trust", "breach of trust public"],
        drafting_red_flags=[
            "S.92(1): Suit can be filed by (a) Advocate General, or (b) two or more persons interested in the trust, WITH leave of court.",
            "Do NOT assume that the Advocate General must be impleaded as a party in every Section 92 suit. The statutory requirement is the proper plaintiff category plus leave of court where required.",
            "Relief can include removal of trustee, appointment of new trustee, vesting of property, scheme for administration.",
        ],
        complexity_weight=3,
    ),

    "public_premises_eviction": _entry(
        registry_kind="cause",
        code="public_premises_eviction",
        display_name="Eviction from Public Premises",
        primary_acts=[
            {"act": "Public Premises (Eviction of Unauthorised Occupants) Act, 1971", "sections": ["Section 4", "Section 5", "Section 5A", "Section 9"]},
        ],
        limitation={"article": "N/A", "period": "Governed by the Act — no Limitation Act article", "from": "N/A"},
        required_sections=[
            "estate_officer_heading", "premises_details",
            "unauthorized_occupation", "show_cause_notice",
            "eviction_order",
        ],
        doc_type_keywords=["public premises", "unauthorized occupant", "government premises", "estate officer eviction"],
        drafting_red_flags=[
            "Estate Officer (not civil court) has jurisdiction.",
            "S.4: Show cause notice is mandatory before an eviction order is made under Section 5.",
            "S.9: Appeal to the appellate officer lies within 12 days of publication of the eviction order.",
            "Civil court jurisdiction barred under S.15.",
        ],
        complexity_weight=2,
    ),
}

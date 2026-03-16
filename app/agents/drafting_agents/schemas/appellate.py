"""Appellate document schemas — appeal_memo, revision_petition, review_petition.

Each schema defines section order + per-section instructions for ONE document type.
Independent of cause type — same schema for all 92 causes.
"""
from __future__ import annotations

SCHEMAS: dict = {

    # ── appeal_memo (Order XLI Rule 1 CPC) ──────────────────────────────────
    "appeal_memo": {
        "code": "appeal_memo",
        "display_name": "Memorandum of Appeal",
        "filed_by": "appellant",
        "cpc_reference": "Order XLI Rule 1 CPC",
        "annexure_prefix": "Annexure-",
        "verification_type": "appellant",
        "signing_format": "Appellant through Advocate",

        "sections": [
            {
                "key": "court_heading",
                "instruction": "Appellate court name, place, appeal number",
            },
            {
                "key": "parties",
                "instruction": "Appellant (party aggrieved) and Respondent details. State original suit designation",
            },
            {
                "key": "impugned_order",
                "instruction": "Date, court, and nature of the impugned judgment/decree. Suit number and date of decree",
            },
            {
                "key": "brief_facts",
                "instruction": "Brief facts of the case and proceedings below. Chronological narrative of trial court proceedings",
            },
            {
                "key": "grounds_of_appeal",
                "instruction": "Numbered grounds — each ground a separate legal or factual error. Be specific: 'The learned trial court erred in...'",
            },
            {
                "key": "prayer",
                "instruction": "Set aside/modify the impugned decree. Specific relief sought on appeal. Costs",
            },
            {
                "key": "verification",
                "instruction": "Verification on oath",
            },
        ],

        "filing_rules": {
            "court_fee": True,
            "filing_deadline": "30 days from date of decree when appealing to District Court or subordinate appellate court (Art 116(b)); 90 days when appealing to High Court (Art 116(a) Limitation Act, read with S.96 CPC)",
            "vakalatnama": True,
            "certified_copy": True,
        },
    },

    # ── revision_petition (S.115 CPC) ───────────────────────────────────────
    "revision_petition": {
        "code": "revision_petition",
        "display_name": "Revision Petition",
        "filed_by": "aggrieved_party",
        "cpc_reference": "Section 115 CPC",
        "annexure_prefix": "Annexure-",
        "verification_type": "petitioner",
        "signing_format": "Petitioner through Advocate",

        "sections": [
            {
                "key": "court_heading",
                "instruction": "High Court name, place, revision petition number",
            },
            {
                "key": "parties",
                "instruction": "Petitioner and Respondent details with original case designation",
            },
            {
                "key": "impugned_order",
                "instruction": "Date, court, and nature of the impugned order. Must be an order (not decree) of a subordinate court",
            },
            {
                "key": "brief_facts",
                "instruction": "Brief facts and procedural history of the case below",
            },
            {
                "key": "jurisdictional_error",
                "instruction": "Specific jurisdictional error under S.115 CPC — (a) exercised jurisdiction not vested, (b) failed to exercise vested jurisdiction, (c) acted illegally or with material irregularity",
            },
            {
                "key": "prayer",
                "instruction": "Set aside/quash the impugned order. Specific direction sought. Costs",
            },
            {
                "key": "verification",
                "instruction": "Verification on oath",
            },
        ],

        "filing_rules": {
            "court_fee": True,
            "filing_deadline": "90 days from the decree or order sought to be revised (Art 131 Limitation Act)",
            "vakalatnama": True,
            "certified_copy": True,
        },
    },

    # ── review_petition (Order XLVII / S.114 CPC) ──────────────────────────
    "review_petition": {
        "code": "review_petition",
        "display_name": "Review Petition",
        "filed_by": "aggrieved_party",
        "cpc_reference": "Order XLVII, Section 114 CPC",
        "annexure_prefix": "Annexure-",
        "verification_type": "petitioner",
        "signing_format": "Petitioner through Advocate",

        "sections": [
            {
                "key": "court_heading",
                "instruction": "Same court that passed the decree/order, petition number",
            },
            {
                "key": "parties",
                "instruction": "Petitioner and Respondent details",
            },
            {
                "key": "impugned_order",
                "instruction": "Date and nature of the decree/order sought to be reviewed",
            },
            {
                "key": "grounds_for_review",
                "instruction": "Specific grounds under Order XLVII Rule 1: (a) discovery of new important matter/evidence, (b) mistake or error apparent on face of record, (c) any other sufficient reason. NOT a rehearing",
            },
            {
                "key": "prayer",
                "instruction": "Review and recall/modify the decree/order dated ___. Specific modification sought",
            },
            {
                "key": "verification",
                "instruction": "Verification on oath",
            },
        ],

        "filing_rules": {
            "court_fee": True,
            "filing_deadline": "30 days from date of decree/order (Art 124 Limitation Act)",
            "vakalatnama": True,
            "certified_copy": True,
        },
    },
}

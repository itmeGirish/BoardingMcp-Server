"""Group 15 -- Consumer & Special Tribunal causes."""
from __future__ import annotations

from ._helpers import _entry

CAUSES: dict = {
    "consumer_complaint": _entry(
        registry_kind="cause",
        code="consumer_complaint",
        document_type="complaint",
        display_name="Consumer Complaint under Consumer Protection Act",
        primary_acts=[
            {"act": "Consumer Protection Act, 2019", "sections": ["Section 2(7) (consumer)", "Section 34 (District Commission)", "Section 35 (complaint)", "Section 69 (limitation)", "Section 82 (product liability action)"]},
        ],
        limitation={
            "article": "N/A",
            "reference": "Section 69 of the Consumer Protection Act, 2019",
            "act": "Consumer Protection Act, 2019",
            "period": "Two years",
            "from": "Date on which the cause of action arises (delay may be condoned for sufficient cause)",
        },
        required_sections=[
            "commission_heading", "complainant_details",
            "opposite_party_details", "deficiency_or_defect",
            "relief_sought", "valuation",
        ],
        doc_type_keywords=["consumer complaint", "deficiency of service", "defective goods", "product liability", "consumer forum"],
        drafting_red_flags=[
            "Pecuniary jurisdiction is based on the value of goods or services paid as consideration: District Commission up to Rs.50 lakh, State Commission above Rs.50 lakh and up to Rs.2 crore, National Commission above Rs.2 crore.",
            "Product liability (Chapter VI) is NEW under 2019 Act — manufacturer/seller/service provider all liable.",
            "E-commerce included — online purchases covered.",
            "Mediation under S.74-81 available.",
        ],
        complexity_weight=2,
    ),

    "sarfaesi_s17_application": _entry(
        registry_kind="cause",
        code="sarfaesi_s17_application",
        document_type="application",
        display_name="Application under Section 17 SARFAESI Act (challenge to possession/sale)",
        primary_acts=[
            {"act": "Securitisation and Reconstruction of Financial Assets and Enforcement of Security Interest Act, 2002", "sections": ["Section 17"]},
        ],
        limitation={
            "article": "N/A",
            "reference": "Section 17 of the Securitisation and Reconstruction of Financial Assets and Enforcement of Security Interest Act, 2002",
            "act": "Securitisation and Reconstruction of Financial Assets and Enforcement of Security Interest Act, 2002",
            "period": "Forty-five days",
            "from": "Date on which measures were taken under Section 13(4)",
        },
        required_sections=[
            "drt_heading", "applicant_details",
            "secured_creditor_details", "measures_challenged",
            "grounds", "prayer",
        ],
        doc_type_keywords=["SARFAESI", "section 17", "securitisation", "possession notice", "DRT application"],
        drafting_red_flags=[
            "STRICT 45-day limitation from date of S.13(4) action (not from notice date).",
            "Filed before DRT, NOT civil court.",
            "S.17(1): can challenge on ground that measures taken are not in accordance with provisions of the Act.",
            "No statutory pre-deposit applies to the initial Section 17 application before the DRT.",
            "S.18: Appeal to DRAT within 30 days with 50% pre-deposit requirement (reducible to not less than 25%).",
        ],
        complexity_weight=3,
    ),

    "ibc_initiation": _entry(
        registry_kind="cause",
        code="ibc_initiation",
        document_type="application",
        display_name="Application for Initiation of CIRP / Insolvency (IBC)",
        primary_acts=[
            {"act": "Insolvency and Bankruptcy Code, 2016", "sections": ["Section 7 (financial creditor)", "Section 9 (operational creditor)", "Section 10 (corporate debtor)"]},
        ],
        limitation={
            "article": "N/A",
            "reference": "Section 238A of the Insolvency and Bankruptcy Code, 2016",
            "act": "Insolvency and Bankruptcy Code, 2016",
            "period": "Three years subject to the applicable Limitation Act rule for the underlying debt",
            "from": "Date of default",
        },
        required_sections=[
            "nclt_heading", "applicant_details",
            "corporate_debtor_details", "default_details",
            "debt_and_default_evidence", "proposed_irp", "prayer",
        ],
        doc_type_keywords=["IBC", "CIRP", "insolvency", "NCLT", "section 7", "section 9", "operational creditor", "financial creditor"],
        drafting_red_flags=[
            "Minimum default threshold: Rs.1 crore (raised from Rs.1 lakh by notification).",
            "S.7: Financial creditor — must show financial debt and default.",
            "S.9: Operational creditor — must first issue demand notice under S.8, wait 10 days.",
            "S.238A: Limitation Act applies to IBC applications.",
            "S.10 application requires special resolution of shareholders/members — mandatory procedural prerequisite.",
            "S.9: Operational creditor CANNOT apply if corporate debtor disputes the debt with documentary evidence.",
            "CIRP must be completed within 330 days (S.12 IBC) including all litigation time.",
        ],
        complexity_weight=3,
    ),
}

"""Trial court document schemas — plaint, written_statement, rejoinder, counter_claim.

Each schema defines section order + per-section instructions for ONE document type.
Independent of cause type — same schema for all 92 causes.
"""
from __future__ import annotations

SCHEMAS: dict = {

    # ── plaint (Order VII CPC) ──────────────────────────────────────────────
    "plaint": {
        "code": "plaint",
        "display_name": "Plaint",
        "filed_by": "plaintiff",
        "cpc_reference": "Order VII CPC",
        "annexure_prefix": "P-",
        "verification_type": "plaintiff",
        "signing_format": "Plaintiff through Advocate",

        "sections": [
            {
                "key": "court_heading",
                "instruction": "Court name with specific designation (e.g., Principal Civil Judge Senior Division), place, suit number",
            },
            {
                "key": "parties",
                "instruction": "Full party details — Name, S/o or D/o or W/o, Age, Occupation, R/o full address with PIN. PLAINTIFF / VERSUS / DEFENDANT format",
            },
            {
                "key": "suit_title",
                "instruction": "Suit title in ALL CAPS describing nature of suit",
            },
            {
                "key": "facts",
                "instruction": "Factual narrative in numbered paragraphs. ONLY factual events — dates, actions, amounts. Do NOT cite Section/Act numbers here",
            },
            {
                "key": "legal_basis",
                "instruction": "Statutory provisions and legal principles supporting the claim. Cite specific sections from LEGAL DATA",
            },
            {
                "key": "cause_of_action",
                "instruction": "When cause of action arose (specific date), where it arose (jurisdiction basis), when it last arose",
            },
            {
                "key": "limitation",
                "instruction": "Applicable limitation article, period, and that suit is within time",
            },
            {
                "key": "jurisdiction",
                "instruction": "Territorial and pecuniary jurisdiction basis with CPC section reference",
            },
            {
                "key": "valuation_court_fee",
                "instruction": "Suit valuation for jurisdiction and court fee purposes. Court fee paid or to be paid",
            },
            {
                "key": "interest",
                "instruction": "Pre-suit interest (contractual or statutory rate), and pendente lite and future interest under Section 34 CPC. OMIT this section for non-monetary suits",
                "condition": "monetary_claim",
            },
            {
                "key": "schedule_of_property",
                "instruction": "Full property description — address, survey/plot number, extent/area, boundaries (East/West/North/South). INCLUDE only for immovable property suits",
                "condition": "immovable_property",
            },
            {
                "key": "prayer",
                "instruction": "Numbered prayer clauses (a) through (n). Use EXACT prayer text from RELIEFS TO PRAY FOR. Include costs and general relief",
            },
            {
                "key": "documents_list",
                "instruction": "List of documents filed as annexures. ONLY list documents mentioned in evidence — do NOT fabricate",
            },
            {
                "key": "verification",
                "instruction": "Verification on oath per Order VI Rule 15 CPC. Distinguish personal knowledge paragraphs from information paragraphs",
            },
        ],

        "filing_rules": {
            "court_fee": True,
            "filing_deadline": "Within limitation period",
            "vakalatnama": True,
            "certified_copy": False,
        },
    },

    # ── written_statement (Order VIII CPC) ──────────────────────────────────
    "written_statement": {
        "code": "written_statement",
        "display_name": "Written Statement",
        "filed_by": "defendant",
        "cpc_reference": "Order VIII CPC",
        "annexure_prefix": "D-",
        "verification_type": "defendant",
        "signing_format": "Defendant through Advocate",

        "sections": [
            {
                "key": "court_heading",
                "instruction": "Court name, place, suit number, names of parties",
            },
            {
                "key": "parties",
                "instruction": "Defendant and Plaintiff details in standard format",
            },
            {
                "key": "preliminary_objections",
                "instruction": "Limitation bar, jurisdiction challenge, non-joinder/misjoinder, maintainability, res judicata, cause of action not disclosed",
            },
            {
                "key": "parawise_reply",
                "instruction": "Reply to EVERY plaint paragraph numbered to match. Each paragraph: ADMITTED / DENIED / NOT ADMITTED with specific basis",
            },
            {
                "key": "additional_facts",
                "instruction": "New facts in defence not mentioned in plaint. Numbered paragraphs continuing from parawise reply",
            },
            {
                "key": "legal_grounds",
                "instruction": "Statutory provisions and legal principles supporting defence",
            },
            {
                "key": "prayer",
                "instruction": "Dismiss the suit with costs. Additional relief if counter-claim not filed",
            },
            {
                "key": "verification",
                "instruction": "Verification on oath per Order VI Rule 15 CPC",
            },
        ],

        "filing_rules": {
            "court_fee": False,
            "filing_deadline": "Ordinarily within 30 days from service of summons; in regular civil suits the court may extend time beyond 30 days and ordinarily up to 90 days for recorded reasons, while commercial disputes carry a strict outer limit of 120 days from service under the Commercial Courts Act",
            "vakalatnama": True,
            "certified_copy": False,
        },
    },

    # ── rejoinder / replication (Order VIII Rule 9 CPC) ─────────────────────
    "rejoinder": {
        "code": "rejoinder",
        "display_name": "Rejoinder",
        "filed_by": "plaintiff",
        "cpc_reference": "Order VIII Rule 9 CPC",
        "annexure_prefix": "P-",
        "verification_type": "plaintiff",
        "signing_format": "Plaintiff through Advocate",

        "sections": [
            {
                "key": "court_heading",
                "instruction": "Court name, place, suit number",
            },
            {
                "key": "parties",
                "instruction": "Plaintiff and Defendant details",
            },
            {
                "key": "reply_to_preliminary_objections",
                "instruction": "Reply to each preliminary objection raised in Written Statement",
            },
            {
                "key": "reply_to_additional_facts",
                "instruction": "Reply to additional facts stated by Defendant. ADMITTED / DENIED / NOT ADMITTED",
            },
            {
                "key": "reaffirmation",
                "instruction": "Reaffirm plaint averments. State that plaint facts are true and Written Statement is false/misleading",
            },
            {
                "key": "prayer",
                "instruction": "Reiterate plaint prayer. Pray for decree as prayed in plaint",
            },
            {
                "key": "verification",
                "instruction": "Verification on oath per Order VI Rule 15 CPC",
            },
        ],

        "filing_rules": {
            "court_fee": False,
            "filing_deadline": "Only with leave of Court unless ordered; thereafter as directed by Court",
            "vakalatnama": False,
            "certified_copy": False,
        },
    },

    # ── counter_claim (Order VIII Rule 6A-6G CPC) ──────────────────────────
    "counter_claim": {
        "code": "counter_claim",
        "display_name": "Counter Claim",
        "filed_by": "defendant",
        "cpc_reference": "Order VIII Rule 6A-6G CPC",
        "annexure_prefix": "D-",
        "verification_type": "defendant",
        "signing_format": "Defendant through Advocate",

        "sections": [
            {
                "key": "court_heading",
                "instruction": "Court name, place, suit number",
            },
            {
                "key": "parties",
                "instruction": "Defendant (counter-claimant) and Plaintiff (counter-defendant) details",
            },
            {
                "key": "facts",
                "instruction": "Facts supporting the counter-claim in numbered paragraphs. Only factual events",
            },
            {
                "key": "legal_basis",
                "instruction": "Statutory basis for the counter-claim",
            },
            {
                "key": "cause_of_action",
                "instruction": "When and where counter-claim cause of action arose",
            },
            {
                "key": "limitation",
                "instruction": "Counter-claim is within limitation",
            },
            {
                "key": "valuation_court_fee",
                "instruction": "Valuation and court fee for counter-claim",
            },
            {
                "key": "prayer",
                "instruction": "Specific relief sought in counter-claim with amounts. Plus costs",
            },
            {
                "key": "verification",
                "instruction": "Verification on oath",
            },
        ],

        "filing_rules": {
            "court_fee": True,
            "filing_deadline": "May be raised before issues are framed; subject to independent limitation for the counter-claim cause of action (Order VIII Rule 6A CPC)",
            "vakalatnama": False,
            "certified_copy": False,
        },
    },
}

"""Application document schemas — interim_application, condonation_of_delay, set_aside_ex_parte, caveat.

Each schema defines section order + per-section instructions for ONE document type.
Independent of cause type — same schema for all 92 causes.
"""
from __future__ import annotations

SCHEMAS: dict = {

    # ── interim_application (Order XXXVIII/XXXIX/XL CPC) ────────────────────
    "interim_application": {
        "code": "interim_application",
        "display_name": "Interim Application",
        "filed_by": "either",
        "cpc_reference": "Order XXXVIII / XXXIX / XL CPC",
        "annexure_prefix": "Annexure-",
        "verification_type": "applicant",
        "signing_format": "Applicant through Advocate",

        "sections": [
            {
                "key": "court_heading",
                "instruction": "Court name, place, suit number, application number",
            },
            {
                "key": "parties",
                "instruction": "Applicant and Respondent details",
            },
            {
                "key": "nature_of_application",
                "instruction": "State the CPC provision under which application is filed (e.g., Order XXXIX Rule 1 & 2 for temporary injunction)",
            },
            {
                "key": "brief_facts",
                "instruction": "Brief facts of the main suit and circumstances necessitating interim relief",
            },
            {
                "key": "grounds",
                "instruction": "Legal grounds for interim relief. For temp injunction (O.XXXIX): prima facie case, balance of convenience, irreparable injury. For attachment (O.XXXVIII): defendant likely to dispose/remove property. For receiver (O.XL): just and convenient",
            },
            {
                "key": "urgency",
                "instruction": "Why interim relief is urgent and cannot wait till final hearing. Specific prejudice if not granted",
            },
            {
                "key": "prayer",
                "instruction": "Specific interim relief sought. Be precise about what is to be restrained/directed",
            },
            {
                "key": "verification",
                "instruction": "Verification on oath",
            },
        ],

        "filing_rules": {
            "court_fee": True,
            "filing_deadline": "Any time during pendency of suit",
            "vakalatnama": False,
            "certified_copy": False,
        },
    },

    # ── condonation_of_delay (S.5 Limitation Act, 1963) ────────────────────
    "condonation_of_delay": {
        "code": "condonation_of_delay",
        "display_name": "Application for Condonation of Delay",
        "filed_by": "applicant",
        "cpc_reference": "Section 5, Limitation Act, 1963",
        "annexure_prefix": "Annexure-",
        "verification_type": "applicant",
        "signing_format": "Applicant through Advocate",

        "sections": [
            {
                "key": "court_heading",
                "instruction": "Court name, place, case number",
            },
            {
                "key": "parties",
                "instruction": "Applicant and Respondent details",
            },
            {
                "key": "delay_facts",
                "instruction": "Chronology: limitation expiry date, actual filing date, total days of delay, day-by-day explanation",
            },
            {
                "key": "sufficient_cause",
                "instruction": "Explain sufficient cause for each period of delay. Must be bona fide, not negligence. Cite specific reasons (illness, legal advice, administrative delay)",
            },
            {
                "key": "no_negligence",
                "instruction": "State that delay is not due to negligence or deliberate inaction. Applicant was diligent",
            },
            {
                "key": "meritorious_case",
                "instruction": "Briefly state that the main case has merit — dismissal on limitation alone would cause grave injustice",
            },
            {
                "key": "prayer",
                "instruction": "Condone the delay of ___ days in filing the appeal/application. NOTE: S.5 applies ONLY to appeals and applications, NOT to original suits or Order XXI execution applications",
            },
            {
                "key": "verification",
                "instruction": "Verification on oath",
            },
        ],

        "filing_rules": {
            "court_fee": True,
            "filing_deadline": "Filed along with the delayed document",
            "vakalatnama": False,
            "certified_copy": False,
        },
    },

    # ── set_aside_ex_parte (Order IX Rule 13 CPC) ──────────────────────────
    "set_aside_ex_parte": {
        "code": "set_aside_ex_parte",
        "display_name": "Application to Set Aside Ex Parte Decree",
        "filed_by": "defendant",
        "cpc_reference": "Order IX Rule 13 CPC",
        "annexure_prefix": "Annexure-",
        "verification_type": "defendant",
        "signing_format": "Defendant/Applicant through Advocate",

        "sections": [
            {
                "key": "court_heading",
                "instruction": "Court name, place, suit number, application number",
            },
            {
                "key": "parties",
                "instruction": "Applicant (Defendant) and Respondent (Plaintiff) details",
            },
            {
                "key": "decree_details",
                "instruction": "Date of ex parte decree, what was decreed, when applicant learned of it",
            },
            {
                "key": "sufficient_cause",
                "instruction": "Sufficient cause for non-appearance on the date of hearing. Specific reasons — not general allegations",
            },
            {
                "key": "meritorious_defence",
                "instruction": "Brief defence on merits to show that setting aside is not futile. Triable issues exist",
            },
            {
                "key": "prayer",
                "instruction": "Set aside the ex parte decree dated ___ and restore the suit to file for fresh hearing",
            },
            {
                "key": "verification",
                "instruction": "Verification on oath",
            },
        ],

        "filing_rules": {
            "court_fee": True,
            "filing_deadline": "30 days from the date of decree, or where summons was not duly served, from when the applicant had knowledge of the decree (Art 123 Limitation Act)",
            "vakalatnama": True,
            "certified_copy": True,
        },
    },

    # ── caveat (S.148A CPC) ─────────────────────────────────────────────────
    "caveat": {
        "code": "caveat",
        "display_name": "Caveat Petition",
        "filed_by": "caveator",
        "cpc_reference": "Section 148A CPC",
        "annexure_prefix": "Annexure-",
        "verification_type": "caveator",
        "signing_format": "Caveator through Advocate",

        "sections": [
            {
                "key": "court_heading",
                "instruction": "Court name, place",
            },
            {
                "key": "parties",
                "instruction": "Caveator and expected Petitioner/Plaintiff details",
            },
            {
                "key": "facts",
                "instruction": "Facts showing caveator's interest. Why an application/suit is expected. How caveator will be affected",
            },
            {
                "key": "prayer",
                "instruction": "Notice to caveator before any ex parte order is passed. Opportunity of hearing",
            },
            {
                "key": "verification",
                "instruction": "Verification on oath",
            },
        ],

        "filing_rules": {
            "court_fee": True,
            "filing_deadline": "Caveat remains in force for 90 days from filing (S.148A(5))",
            "vakalatnama": True,
            "certified_copy": False,
        },
    },
}

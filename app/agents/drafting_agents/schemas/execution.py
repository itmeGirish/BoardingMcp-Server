"""Execution document schemas — execution_application.

Each schema defines section order + per-section instructions for ONE document type.
Independent of cause type — same schema for all 92 causes.
"""
from __future__ import annotations

SCHEMAS: dict = {

    # ── execution_application (Order XXI CPC) ───────────────────────────────
    "execution_application": {
        "code": "execution_application",
        "display_name": "Execution Application",
        "filed_by": "decree_holder",
        "cpc_reference": "Order XXI CPC",
        "annexure_prefix": "Annexure-",
        "verification_type": "decree_holder",
        "signing_format": "Decree Holder through Advocate",

        "sections": [
            {
                "key": "court_heading",
                "instruction": "Executing court name, place, execution petition number",
            },
            {
                "key": "parties",
                "instruction": "Decree Holder and Judgment Debtor details",
            },
            {
                "key": "decree_details",
                "instruction": "Date of decree, court that passed it, suit number, nature of decree (money/possession/injunction), amount decreed with interest",
            },
            {
                "key": "satisfaction_status",
                "instruction": "What has been satisfied (if any), what remains unsatisfied, total amount due as on date",
            },
            {
                "key": "execution_mode",
                "instruction": "Mode of execution sought — attachment and sale of property (Order XXI Rule 54), arrest and detention (Rule 37), delivery of possession (Rule 35/36), garnishee order",
            },
            {
                "key": "property_details",
                "instruction": "If attachment sought: full description of judgment debtor's property — address, survey number, boundaries, estimated value",
            },
            {
                "key": "prayer",
                "instruction": "Execute the decree dated ___. Specific execution mode. Attach and sell / deliver possession / arrest. Costs of execution",
            },
            {
                "key": "verification",
                "instruction": "Verification on oath",
            },
        ],

        "filing_rules": {
            "court_fee": True,
            "filing_deadline": "12 years from when the decree or order becomes enforceable; for a decree granting a mandatory injunction, from the date of breach or successive breaches (Art 136 Limitation Act)",
            "vakalatnama": True,
            "certified_copy": True,
        },
    },
}

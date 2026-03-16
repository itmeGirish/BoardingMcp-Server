"""Group 7 — Partnership / Business causes.

Covers: partnership dissolution, partner restraint injunction.
"""
from __future__ import annotations

from ._helpers import (
    COMMON_CIVIL_PLAINT_SECTIONS,
    _civil_and_commercial_rules,
    _entry,
)

CAUSES: dict = {
    # ── partnership_dissolution (flattened — default Art 5) ──────────

    "partnership_dissolution": _entry(
        registry_kind="cause",
        code="partnership_dissolution",
        display_name="Dissolution of partnership and rendition of accounts",
        primary_acts=[
            {"act": "Indian Partnership Act, 1932", "sections": ["Section 44", "Section 46", "Section 48"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20", "Order XX Rule 16"]},
        ],
        limitation={
            "article": "5",
            "period": "Three years",
            "from": "The date of the dissolution (Art 5 — suit for account and share of profits of a dissolved partnership. Where winding up continues under Ss.45-48 IPA, courts have sometimes treated the date of final winding up as the accrual date)",
        },
        court_rules=_civil_and_commercial_rules(nature_keywords=["partnership", "business", "firm"]),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "partnership_details", "dissolution_ground_or_status", "accounts_state",
        ],
        required_reliefs=["dissolution_decree", "rendition_of_accounts", "share_in_assets", "costs"],
        doc_type_keywords=["partnership dissolution", "rendition of accounts", "partner dispute"],
        facts_must_cover=[
            "Partnership deed details — date, parties, firm name, nature of business",
            "Capital contribution and profit/loss sharing ratio of each partner",
            "Ground for dissolution — conduct affecting the business (S.44(c)), willful or persistent breach (S.44(d)), transfer of entire interest (S.44(e)), business at a loss (S.44(f)), mutual agreement, or just and equitable ground (S.44(g))",
            "Demand for accounts — when the Plaintiff demanded rendition and Defendant's refusal",
            "Registration status of the firm under S.69 IPA",
        ],
        prayer_template=[
            "Pass a decree for dissolution of the partnership firm",
            "Direct the Defendant to render true and faithful accounts of all partnership dealings from inception to the date of dissolution",
            "Appoint a Commissioner / Receiver for taking accounts and winding up the partnership affairs",
            "Pass a decree for payment of the Plaintiff's share in the net assets of the firm as may be found due upon rendition of accounts",
            "Award pendente lite and post-decree interest under Section 34 CPC on the amount found due to the Plaintiff",
            "Award costs of the suit",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        drafting_red_flags=[
            "S.69 IPA: Unregistered firm cannot sue partner on partnership contract — verify registration.",
        ],
        complexity_weight=3,
    ),

    # ── partner_restraint_injunction ─────────────────────────────────

    "partner_restraint_injunction": _entry(
        registry_kind="cause",
        code="partner_restraint_injunction",
        display_name="Injunction against partner / ex-partner conduct",
        primary_acts=[
            {"act": "Indian Partnership Act, 1932", "sections": ["Section 9", "Section 36"]},
            {"act": "Specific Relief Act, 1963", "sections": ["Section 38", "Section 39", "Section 42"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        limitation={
            "article": "113",
            "period": "Three years",
            "from": "When right to sue accrues",
        },
        court_rules=_civil_and_commercial_rules(nature_keywords=["partnership", "business"]),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "partnership_relationship", "wrongful_conduct", "need_for_restraint",
        ],
        required_reliefs=["permanent_injunction", "delivery_up_confidential_information", "damages_or_account_of_profits", "costs"],
        doc_type_keywords=["partner injunction", "restrain partner", "ex-partner restraint"],
        facts_must_cover=[
            "Partnership relationship — deed date, nature of business, partners involved",
            "Dissolution details — date, mode (mutual / court-ordered / S.43 IPA)",
            "Wrongful conduct — competition, solicitation, misuse of confidential information",
            "Covenant terms — non-compete clause in partnership deed (if any) with duration and geographic scope",
        ],
        prayer_template=[
            "Pass a decree of permanent injunction restraining the Defendant from carrying on {{COMPETING_BUSINESS}} within {{GEOGRAPHIC_AREA}} for the period stipulated in the partnership deed",
            "Direct the Defendant to deliver up all confidential information, client lists, and trade secrets of the firm",
            "Pass a decree for damages of Rs. {{CLAIM_AMOUNT}}/- / direct an account of profits earned by the Defendant through wrongful competition",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "S.69 IPA: Unregistered firm cannot sue.",
            "S.27 ICA voids restraint of trade; S.36 IPA post-dissolution restraint is exception.",
            "Injunction against ex-partner must state dissolution date and covenant terms.",
        ],
        coa_type="continuing",
        complexity_weight=2,
    ),
}

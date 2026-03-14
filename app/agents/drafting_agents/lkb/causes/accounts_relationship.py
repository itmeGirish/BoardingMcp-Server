"""Accounts & Relationship family — suits where the cause of action
is a fiduciary, agency, partnership, or joint-business duty to account.

Architecturally separate from money_and_debt because:
  - The relationship CREATES the duty to account (not a debt owed).
  - Pleading structure is: RELATIONSHIP BASIS → DUTY TO ACCOUNT → FAILURE
    TO RENDER → AMOUNT FOUND DUE — not FACTS / BREACH / DAMAGES.
  - Prayer is two-stage: preliminary decree (accounts) + final decree (amount).
  - Limitation varies by underlying relationship, never a fixed article.
"""
from __future__ import annotations

from ._helpers import COMMON_CIVIL_PLAINT_SECTIONS, _civil_and_commercial_rules, _entry

CAUSES: dict = {
    # ── rendition_of_accounts ─────────────────────────────────────────────
    "rendition_of_accounts": _entry(
        registry_kind="cause",
        code="rendition_of_accounts",
        display_name="Suit for rendition of accounts",
        document_type="rendition_of_accounts_plaint",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20", "Order XX Rule 16"]},
        ],
        alternative_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 213", "Section 214"]},
            {"act": "Indian Partnership Act, 1932", "sections": []},
        ],
        limitation={
            "article": "RELATIONSHIP_DEPENDENT",
            "description": (
                "Limitation depends on the underlying relationship that creates "
                "the duty to account. Agency, partnership, fiduciary, and trust-based "
                "account suits do not safely collapse into one residuary article. "
                "The court must determine limitation from the relationship."
            ),
            "period": "Varies by the underlying relationship and duty to account",
            "from": (
                "From termination of the relationship or breach of the duty to account, "
                "depending on the governing cause"
            ),
        },
        court_rules=_civil_and_commercial_rules(
            nature_keywords=["agency", "fiduciary", "business", "accounts"],
        ),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "relationship_basis",
            "duty_to_account",
            "accounts_not_rendered",
            "amount_found_due",
        ],
        required_reliefs=[
            "preliminary_decree_for_accounts",
            "final_decree_amount_found_due",
            "pendente_lite_and_future_interest",
            "costs",
        ],
        doc_type_keywords=["rendition of accounts", "accounts", "accounting", "duty to account"],
        mandatory_inline_sections=[
            {
                "section": "RELATIONSHIP BASIS",
                "placement": "after jurisdiction",
                "instruction": "Nature of relationship creating the duty to account — agency, partnership, trust, joint business, fiduciary.",
            },
            {
                "section": "DUTY TO ACCOUNT AND DEFAULT",
                "placement": "after relationship_basis",
                "instruction": "Period of account, books withheld, demand made, refusal by Defendant.",
            },
        ],
        facts_must_cover=[
            "Nature of the relationship creating the duty to account — agency, trust, fiduciary, partnership, or joint business arrangement",
            "Period during which the Defendant managed funds / property on behalf of the Plaintiff",
            "Particulars of books, records, or accounts withheld by the Defendant",
            "Demand for accounts — when made and Defendant's refusal or failure to comply",
            "Approximate amount believed to be due (if known)",
        ],
        prayer_template=[
            "Pass a preliminary decree directing the Defendant to render true and faithful accounts of all transactions and dealings during the period {{ACCOUNTING_PERIOD}}",
            "Appoint a Commissioner for taking accounts if necessary",
            "Pass a final decree for payment of such sum as may be found due to the Plaintiff upon rendition of accounts",
            "Award pendente lite and post-decree interest under Section 34 CPC at such rate as this Hon'ble Court deems just",
            "Award costs of the suit",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        drafting_red_flags=[
            "Order XX Rule 16 CPC: seek a preliminary decree for accounts and a final decree for the amount found due.",
            "If commercial (agency/partnership), Commercial Court may have jurisdiction if value exceeds Rs.3 lakh.",
            "Do NOT cite Article 113 mechanically; first identify the relationship that creates the duty to account.",
            "Do NOT treat this as a generic money recovery suit — the cause is the relationship, not a debt.",
            "Limitation is RELATIONSHIP-DEPENDENT: do not assign a fixed limitation article without identifying the underlying relationship.",
        ],
        complexity_weight=3,
    ),

    # ── accounts_stated ───────────────────────────────────────────────────
    "accounts_stated": _entry(
        registry_kind="cause",
        code="accounts_stated",
        display_name="Suit on accounts stated in writing",
        document_type="accounts_stated_plaint",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 73"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        limitation={
            "article": "14",
            "period": "Three years",
            "from": "When accounts are stated in writing signed by defendant or his authorised agent (unless payable at future date, then when that date arrives)",
        },
        court_rules=_civil_and_commercial_rules(),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "account_statement_details",
            "signed_document",
            "balance_due",
        ],
        required_reliefs=["money_decree", "interest_pendente_lite_future", "costs"],
        doc_type_keywords=["accounts stated", "signed account", "ledger balance", "statement of account signed"],
        facts_must_cover=[
            "Nature of the business relationship between the parties that gave rise to mutual accounts",
            "Details of the written statement of account — date, contents, amount shown as balance due",
            "That the statement was signed by the Defendant or his authorised agent",
            "Whether the balance was payable immediately or at a future date (affects limitation trigger)",
            "Demand for payment and Defendant's refusal or failure to pay",
        ],
        prayer_template=[
            "Pass a decree for recovery of Rs. {{CLAIM_AMOUNT}}/- being the balance due on the accounts stated in writing dated {{ACCOUNT_DATE}} signed by the Defendant",
            "Award pendente lite interest at such rate as this Hon'ble Court deems just from the date of suit till realisation",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        complexity_weight=1,
    ),
}

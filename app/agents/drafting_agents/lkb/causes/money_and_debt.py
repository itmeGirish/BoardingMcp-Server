"""Group 1 — Money, Debt, Accounts & Movable Property Recovery.

Flattened from civil.py SUBSTANTIVE_CAUSES. All conditional fields resolved
to their default/most-common variant.
"""
from __future__ import annotations

from ._helpers import (
    COMMON_CIVIL_PLAINT_SECTIONS,
    COMMON_REQUIRED_AVERMENTS,
    _civil_and_commercial_rules,
    _entry,
)

# ---------------------------------------------------------------------------
# CAUSES
# ---------------------------------------------------------------------------

CAUSES: dict = {

    # ── money_recovery_loan ───────────────────────────────────────────────
    # Limitation depends on the loan terms and accrual trigger.
    "money_recovery_loan": _entry(
        registry_kind="cause",
        code="money_recovery_loan",
        display_name="Recovery of money lent / advance paid",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 73"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        limitation={
            "article": "UNKNOWN",
            "description": "Verify the applicable loan article from the transaction terms. Article 19 commonly applies to money payable for money lent, while Article 21 commonly applies where the loan is expressly payable on demand.",
            "period": "Usually three years, subject to the governing loan article",
            "from": "From the accrual rule in the applicable loan article, such as the date of loan or the date of demand depending on the instrument",
        },
        court_rules=_civil_and_commercial_rules(
            nature_keywords=["business", "company", "firm", "trade", "commercial"],
        ),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["transaction_details", "demands_and_notice", "interest"],
        required_reliefs=["money_decree", "interest_pendente_lite_future", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["transaction_basis"],
        doc_type_keywords=["loan", "hand loan", "advance", "money recovery", "bank transfer"],
        interest_basis="wrongful_retention_of_money",
        interest_guidance=(
            "Claim pendente lite interest under Section 34 CPC. "
            "Pre-suit interest: claim it only on a contractual, mercantile usage, substantive-law, or other legally sustainable basis; avoid presenting any fixed percentage as a statutory default. "
            "Post-decree future interest under Section 34 CPC at such rate as the Court deems fit. "
            "For MSME suppliers: compound interest at three times bank rate under Section 16 MSMED Act. "
            "Do NOT claim compound interest for ordinary loans unless contract expressly provides."
        ),
        evidence_checklist=["bank transfer proof", "admission messages", "legal notice", "acknowledgment / part-payment"],
        facts_must_cover=[
            "Date and mode of advancing the loan (bank transfer / cash / cheque with details)",
            "Terms of repayment — fixed date, on demand, or instalment schedule",
            "Rate of interest agreed (if any) and whether simple or compound",
            "Part-payments made by defendant (date-wise) reducing the outstanding",
            "Date of demand for repayment and mode of demand (oral / written / legal notice)",
            "Defendant's response or failure to respond to demand",
            "Total outstanding as on date of filing (principal + accrued interest)",
        ],
        prayer_template=[
            "Pass a decree directing the Defendant to pay to the Plaintiff a sum of Rs. {{PRINCIPAL_AMOUNT}}/- being the principal amount of the loan",
            "Award pre-suit interest at the rate of {{INTEREST_RATE}}% per annum on the principal sum from {{DATE_OF_DEFAULT}} till the date of institution of the suit",
            "Award pendente lite interest at such rate as this Hon'ble Court deems fit from the date of institution of the suit till the date of decree under Section 34 CPC",
            "Award future interest at such rate as this Hon'ble Court deems fit from the date of decree till the date of realisation under Section 34 CPC",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper in the facts and circumstances of the case",
        ],
        defensive_points=[
            "Pre-empt 'no consideration' defence: plead mode of payment with documentary trail (bank statement, UTR number)",
            "Pre-empt 'time-barred' defence: plead acknowledgment or part-payment under Section 18/19 Limitation Act if applicable",
            "Pre-empt 'already repaid' defence: provide date-wise statement of account showing credits and balance",
            "Pre-empt 'usurious interest' defence: plead that rate is within RBI/market norms for unsecured lending",
            "Pre-empt 'no privity' defence for third-party payments: plead agency or direction to pay",
        ],
        mandatory_averments=[
            {
                "averment": "consideration_and_transfer",
                "provision": "Section 25, Indian Contract Act, 1872",
                "instruction": "Plead that the loan was advanced for lawful consideration with specific mode and date of transfer.",
            },
            {
                "averment": "demand_for_repayment",
                "provision": "Order VII Rule 1(e), CPC",
                "instruction": "Plead specific date and mode of demand; attach legal notice if sent.",
            },
        ],
        mandatory_inline_sections=[
            {
                "section": "STATEMENT OF ACCOUNT",
                "placement": "after transaction details",
                "instruction": "Tabular: principal, part-payments (date-wise), balance, interest computation.",
            },
        ],
        drafting_red_flags=[
            "If lender is non-banking entity lending habitually, screen RBI registration and state money-lending act.",
            "High or penal interest in an unsecured transaction may be scrutinised for excessiveness or unconscionability.",
            "Order II Rule 2 CPC: entire claim from one cause must be included.",
            "Do NOT cite Article 19 mechanically; payable-on-demand terms may shift the accrual article.",
        ],
        # ── v11.0 Layer 2: Document Components ──
        available_reliefs=[
            {"type": "money_decree", "statute": "S.73 ICA",
             "prayer_text": "decree directing the Defendant to pay Rs.{{PRINCIPAL_AMOUNT}}/- being the principal amount of the loan"},
            {"type": "interest", "subtype": "pre_suit", "statute": "Contract / usage / substantive law",
             "prayer_text": "pre-suit interest at the rate of {{INTEREST_RATE}}% per annum from {{DATE_OF_DEFAULT}} till date of filing"},
            {"type": "interest", "subtype": "pendente_lite", "statute": "S.34 CPC",
             "prayer_text": "pendente lite interest at such rate as this Hon'ble Court deems fit from filing till decree"},
            {"type": "interest", "subtype": "future", "statute": "S.34 CPC",
             "prayer_text": "future interest at such rate as this Hon'ble Court deems fit from decree till realisation"},
            {"type": "costs", "statute": "S.35 CPC",
             "prayer_text": "costs of the suit"},
            {"type": "general",
             "prayer_text": "such other and further relief(s) as this Hon'ble Court may deem fit and proper"},
        ],
        jurisdiction_basis="Section 20 CPC — where defendant resides or where cause of action arose",
        valuation_basis="Principal amount claimed (for court fee and pecuniary jurisdiction)",
        complexity_weight=1,
    ),

    # ── money_recovery_goods ──────────────────────────────────────────────
    # Limitation varies with the sale and credit structure.
    "money_recovery_goods": _entry(
        registry_kind="cause",
        code="money_recovery_goods",
        display_name="Recovery of price of goods sold and delivered",
        primary_acts=[
            {"act": "Sale of Goods Act, 1930", "sections": ["Section 55"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        limitation={
            "article": "UNKNOWN",
            "description": "Verify the limitation article from the invoice and credit terms. Claims for price of goods sold and delivered may accrue from delivery, expiry of credit, or another contractually fixed due date.",
            "period": "Usually three years, subject to the governing sales article",
            "from": "From delivery, expiry of credit period, or the contractually fixed due date, depending on the sale terms",
        },
        court_rules=_civil_and_commercial_rules(),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["supply_and_delivery_details", "invoice_details", "ledger_and_outstanding", "interest"],
        required_reliefs=["money_decree", "interest_pendente_lite_future", "costs"],
        doc_type_keywords=["goods sold", "delivered", "invoice", "supply", "price of goods"],
        mandatory_inline_sections=[
            {
                "section": "STATEMENT OF ACCOUNT / LEDGER EXTRACT",
                "placement": "after invoice details",
                "instruction": "Date-wise: goods supplied, invoice, amount, payments, balance.",
            },
        ],
        facts_must_cover=[
            "Purchase orders / invoices with description of goods, quantities, rates, and delivery dates",
            "Delivery receipts / challans / GRNs proving goods were delivered and accepted",
            "Credit period agreed (if any) and when each invoice became due",
            "Part payments received (date-wise) and outstanding balance per invoice",
            "Demand for payment — legal notice date, contents, and Defendant's response",
            "Whether supplier qualifies under MSMED Act (for compound interest under S.16)",
        ],
        prayer_template=[
            "Pass a decree directing the Defendant to pay to the Plaintiff a sum of Rs. {{CLAIM_AMOUNT}}/- being the price of goods sold and delivered",
            "Award pre-suit interest at the rate of {{INTEREST_RATE}}% per annum from the respective invoice due dates till the date of institution of the suit",
            "Award pendente lite and future interest under Section 34 CPC",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "If the supplier qualifies under the MSMED Act, Section 16 compound interest and the Section 18 conciliation/arbitration mechanism must be screened.",
            "Distinguish price-of-goods (SOGA) from breach-of-contract damages (ICA) — limitation articles differ.",
            "Do NOT cite Article 14 mechanically without checking the credit and payment structure.",
        ],
        complexity_weight=1,
    ),

    # ── failure_of_consideration ──────────────────────────────────────────
    "failure_of_consideration": _entry(
        registry_kind="cause",
        code="failure_of_consideration",
        display_name="Recovery of advance paid on failure of consideration",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 65"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        limitation={
            "article": "UNKNOWN",
            "description": "Verify the applicable refund article. Art 19 (money paid for purpose that fails) or Art 22 (money payable on date fixed) may apply depending on the transaction. Art 47 is a 12-year possession-recovery article and does NOT apply to money claims.",
            "period": "Three years under the governing refund article",
            "from": "From the date the consideration fails or the advance becomes refundable",
        },
        court_rules=_civil_and_commercial_rules(
            nature_keywords=["commercial", "franchise", "dealership", "construction", "supply"],
        ),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["payment_and_purpose", "failure_event", "demands_and_notice", "interest"],
        required_reliefs=["money_decree", "interest_pendente_lite_future", "costs"],
        doc_type_keywords=["advance refund", "failure of consideration", "void agreement refund"],
        interest_basis="wrongful_retention_of_money",
        facts_must_cover=[
            "Date and amount of advance paid by Plaintiff, mode of payment (bank transfer / cheque / cash)",
            "Purpose for which the advance was paid (purchase of goods/property, service contract, etc.)",
            "Terms of the agreement under which the advance was paid",
            "Date and manner of failure of consideration — what was promised but not delivered",
            "S.65 ICA: obligation of person who has received advantage under void/voidable agreement to restore it",
            "Demand for refund — legal notice date, contents, and Defendant's response or refusal",
        ],
        prayer_template=[
            "Pass a decree directing the Defendant to refund to the Plaintiff a sum of Rs. {{ADVANCE_AMOUNT}}/- being the advance paid on failure of consideration",
            "Award pre-suit interest at the rate of {{INTEREST_RATE}}% per annum from {{DATE_OF_FAILURE}} till the date of institution of the suit",
            "Award pendente lite and future interest under Section 34 CPC",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Do NOT cite Art 47 (12-year possession article) for money refund claims.",
            "S.65 ICA requires restitution when agreement becomes void — both parties must restore benefits.",
        ],
        complexity_weight=1,
    ),

    # ── deposit_refund ────────────────────────────────────────────────────
    # Refund-deposit accrual is contract-sensitive.
    # S.65 ICA applies ONLY when contract becomes void — NOT for normal lease expiry.
    # For lease security deposit: refund obligation arises from the lease terms themselves
    # and breach-based recovery under S.73 ICA.
    "deposit_refund": _entry(
        registry_kind="cause",
        code="deposit_refund",
        display_name="Recovery of refundable security deposit / earnest money",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 73"]},
            {"act": "Transfer of Property Act, 1882", "sections": ["Section 111 (determination of lease)"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        alternative_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 65 (ONLY when contract discovered void or becomes void — NOT for normal lease expiry/termination)"]},
            {"act": "Indian Contract Act, 1872", "sections": ["Section 70 (quantum meruit — if no express contract)"]},
        ],
        limitation={
            "article": "UNKNOWN",
            "description": "Verify the limitation article from the deposit clause and refund trigger. Security deposits, earnest money, and refundable advances do not all share one accrual rule. For lease security deposit, accrual is typically from date refund became due (vacation + handover + expiry of contractual refund period).",
            "period": "Usually three years, subject to the governing refund article",
            "from": "From demand, breach, termination, or the contractual refund trigger, depending on the underlying transaction",
        },
        coa_type="single_event",
        coa_guidance="The cause of action is a SINGLE EVENT — it arose on the date the refund became due and was not paid. Do NOT plead 'continuing cause of action'. The withholding may continue, but the breach (non-refund) crystallised on one date.",
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["deposit_details", "refund_trigger", "demand_and_refusal", "interest"],
        required_reliefs=["money_decree", "interest_pendente_lite_future", "costs"],
        doc_type_keywords=["deposit refund", "security deposit", "earnest money refund"],
        interest_basis="wrongful_retention_of_money",
        interest_guidance=(
            "Pre-suit interest: claim it only if supported by the lease/agreement, mercantile usage, substantive law, or another legally sustainable basis. "
            "Section 34 CPC governs pendente lite interest from the date of suit to decree and may also govern post-decree interest till realisation."
        ),
        facts_must_cover=[
            "Nature of deposit — security deposit, earnest money, or refundable advance",
            "Date and amount of deposit paid, mode of payment (cheque/NEFT/cash with receipt)",
            "Agreement under which deposit was paid (lease, sale, service contract) — date and parties",
            "Refund trigger — termination/expiry of lease, completion of contract, cancellation, or contractual condition",
            "Date when Plaintiff vacated/handed over the premises (for lease deposits) — vacant and peaceful possession",
            "That all dues (rent, electricity, water, maintenance) were cleared before/at handover",
            "That no damage memo or deduction notice was served by the Defendant, or if served, was unjustified",
            "Date when refund became due under the agreement terms (handover + contractual refund period)",
            "Demand for refund — legal notice date, mode of service, and Defendant's response or refusal",
            "That the Defendant has no lawful right to withhold/forfeit the deposit",
        ],
        prayer_template=[
            "Pass a decree directing the Defendant to refund to the Plaintiff a sum of Rs. {{DEPOSIT_AMOUNT}}/- being the refundable security deposit paid under the {{AGREEMENT_TYPE}} dated {{AGREEMENT_DATE}}",
            "Award pre-suit interest at the rate of {{INTEREST_RATE}}% per annum from {{REFUND_DUE_DATE}} till the date of institution of the suit",
            "Award pendente lite interest at such rate as this Hon'ble Court deems fit from the date of suit till the date of decree under Section 34 CPC",
            "Award future interest at such rate as this Hon'ble Court deems fit from the date of decree till realisation under Section 34 CPC",
            "Award costs of the suit",
        ],
        mandatory_averments=[
            {"averment": "Deposit payment", "instruction": "Plead exact date, amount, mode of payment, and receipt/proof", "provision": "S.73 ICA"},
            {"averment": "Vacancy and handover", "instruction": "Plead that Plaintiff vacated premises and handed over vacant peaceful possession on a specific date", "provision": "S.111 TPA"},
            {"averment": "Dues clearance", "instruction": "Plead that all rent, utility, and maintenance dues were cleared", "provision": "Defence pre-emption"},
            {"averment": "Demand and refusal", "instruction": "Plead legal notice with date and that Defendant failed/refused to refund", "provision": "S.73 ICA"},
        ],
        defensive_points=[
            "no_damage_to_property",
            "all_dues_cleared",
            "no_forfeiture_clause_triggered",
            "no_lawful_deductions",
        ],
        drafting_red_flags=[
            "Do NOT cite Section 65 ICA as primary basis — S.65 applies ONLY when contract becomes void, not for normal lease expiry/termination. Use S.73 ICA (breach/non-performance) as primary basis.",
            "Do NOT use 'security deposit / earnest money' interchangeably — identify the exact nature of the deposit from the agreement and use precise terminology throughout.",
            "Do NOT cite Article 22 mechanically unless the deposit is expressly payable on demand.",
            "Do NOT plead 'continuing cause of action' — this is a single-event money recovery claim.",
            "Earnest money forfeiture disputes may follow a different accrual analysis from refundable security deposits.",
            "Section 34 CPC covers pendente lite interest in an ordinary money decree; do not cite Order XX Rule 11 CPC as the general source for pendente lite interest.",
        ],
        complexity_weight=1,
    ),

    # ── summary_suit_instrument ───────────────────────────────────────────
    # Order XXXVII maintainability does not itself fix the limitation article.
    "summary_suit_instrument": _entry(
        registry_kind="cause",
        code="summary_suit_instrument",
        display_name="Summary suit on negotiable instrument / written contract",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20", "Order XXXVII"]},
            {"act": "Negotiable Instruments Act, 1881", "sections": ["Section 30", "Section 32", "Section 118"]},
        ],
        limitation={
            "article": "UNKNOWN",
            "description": "Verify limitation from the underlying negotiable instrument or written contract. Order XXXVII CPC does not create a single limitation article for all summary suits.",
            "period": "Varies by the underlying instrument or contract",
            "from": "Depends on instrument type, maturity, dishonour, default, or contractual breach",
        },
        court_rules=_civil_and_commercial_rules(
            nature_keywords=["business", "firm", "company", "commercial"],
        ),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["order_37_maintainability", "instrument_details", "default_or_dishonour", "interest"],
        required_reliefs=["money_decree", "interest_pendente_lite_future", "costs"],
        doc_type_keywords=["order 37", "summary suit", "promissory note", "cheque", "bill of exchange"],
        mandatory_inline_sections=[
            {
                "section": "ORDER XXXVII MAINTAINABILITY",
                "placement": "after jurisdiction",
                "instruction": "State suit is on negotiable instrument or written contract for liquidated amount.",
            },
            {
                "section": "INSTRUMENT DETAILS",
                "placement": "after maintainability",
                "instruction": "Type, date, drawer/drawee/payee, amount, maturity, dishonour date if applicable.",
            },
        ],
        facts_must_cover=[
            "Type of instrument — promissory note, bill of exchange, cheque, or written contract for liquidated amount",
            "Date of instrument, parties, amount, maturity/due date",
            "Dishonour / default details — date of dishonour, bank memo (for cheques), or date of non-payment",
            "That suit falls within Order XXXVII CPC — negotiable instrument or written contract for liquidated sum",
            "Demand for payment after dishonour/default and Defendant's failure to pay",
        ],
        prayer_template=[
            "Pass a decree under Order XXXVII CPC directing the Defendant to pay to the Plaintiff a sum of Rs. {{CLAIM_AMOUNT}}/- being the amount due on the instrument",
            "Award pre-suit interest at the rate of {{INTEREST_RATE}}% per annum from {{DUE_DATE}} till the date of institution of the suit",
            "Award pendente lite and future interest under Section 34 CPC",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Order XXXVII available only in courts notified by High Court — verify.",
            "If cheque also subject to S.138 NI Act criminal complaint, suits can run concurrently but avoid double recovery.",
            "Leave to defend under Order XXXVII Rule 3 requires triable issues — draft plaint tightly.",
            "Do NOT cite Article 35 for all written contracts; verify the article from the underlying instrument.",
        ],
        complexity_weight=2,
    ),

    # rendition_of_accounts — MOVED to accounts_relationship.py (separate family)

    # ── recovery_specific_movable ─────────────────────────────────────────
    # Recovery of specific movable property can engage different articles.
    "recovery_specific_movable": _entry(
        registry_kind="cause",
        code="recovery_specific_movable",
        display_name="Recovery of specific movable property",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 7", "Section 8"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 19"]},
        ],
        limitation={
            "article": "UNKNOWN",
            "description": "Verify the applicable article before filing. Specific movable recovery may engage different limitation rules depending on whether the case is framed as wrongful taking, detention, theft, dishonest misappropriation, or conversion.",
            "period": "Usually three years, subject to the governing movable-property article",
            "from": "From wrongful taking, first knowledge of possession, or the detention trigger, depending on the governing article",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["movable_description", "plaintiff_entitlement", "wrongful_detention"],
        required_reliefs=["delivery_of_specific_movable", "damages_or_detention_charges_if_claimed", "costs"],
        doc_type_keywords=["movable property recovery", "return articles", "specific movable"],
        mandatory_inline_sections=[
            {
                "section": "MOVABLE PROPERTY DESCRIPTION",
                "placement": "after jurisdiction",
                "instruction": "Make, model, serial number, distinguishing marks, quantity, value, how plaintiff acquired ownership.",
            },
        ],
        facts_must_cover=[
            "Description of the specific movable property — make, model, serial number, distinguishing marks, quantity, value",
            "How Plaintiff acquired ownership or right to possess the property",
            "How the property came into Defendant's possession — entrustment, bailment, wrongful taking, or detention",
            "Date from when Defendant is wrongfully detaining the property",
            "Demand for return and Defendant's refusal",
            "Alternative value of the property (in case delivery is not possible)",
        ],
        prayer_template=[
            "Pass a decree directing the Defendant to deliver up the specific movable property described in the plaint to the Plaintiff",
            "In the alternative, pass a decree for payment of Rs. {{VALUE}}/- being the value of the said property if delivery cannot be had",
            "Pass a decree for damages of Rs. {{DAMAGES}}/- for wrongful detention of the property from {{DETENTION_DATE}} till delivery",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Section 7 SRA requires the specific movable property to be identified with precision and the plaintiff's entitlement to possess it to be clearly pleaded.",
            "If reliance is placed on Section 8 SRA, plead that the defendant has possession or control of the specific movable property and is not entitled to hold it as owner.",
            "Do NOT cite Article 69 mechanically; conversion or detention theories may engage a different article.",
        ],
        complexity_weight=2,
    ),

    # accounts_stated — MOVED to accounts_relationship.py (separate family)

    # ── suit_on_bond ──────────────────────────────────────────────────────
    # Bond limitation depends on the bond trigger.
    "suit_on_bond": _entry(
        registry_kind="cause",
        code="suit_on_bond",
        display_name="Suit on bond / single bond",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 73", "Section 74"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        limitation={
            "article": "UNKNOWN",
            "description": "Verify the applicable bond article from the bond terms. Bonds payable on demand, on a fixed date, or on default or contingency do not share one safe accrual rule.",
            "period": "Usually three years under Art 55 for informal bonds; BUT formal bonds may attract Art 27/28 with a TWELVE-YEAR period",
            "from": "From the trigger fixed by the bond terms, such as execution, demand, default, or the fixed due date",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["bond_details", "default_details", "interest"],
        required_reliefs=["money_decree", "interest_pendente_lite_future", "costs"],
        doc_type_keywords=["bond", "single bond", "conditional bond", "instalment bond", "chit fund bond"],
        facts_must_cover=[
            "Bond details — date of execution, parties, principal sum, interest rate, conditions",
            "Whether bond is payable on demand, on a fixed date, or on contingency/default",
            "Date when bond became enforceable (maturity, demand, or triggering event)",
            "Total amount due under the bond (principal + interest + penalty if applicable)",
            "Demand for payment and Defendant's default or refusal",
        ],
        prayer_template=[
            "Pass a decree directing the Defendant to pay to the Plaintiff a sum of Rs. {{BOND_AMOUNT}}/- being the amount due under the bond dated {{BOND_DATE}}",
            "Award pre-suit interest at the rate stipulated in the bond / at {{INTEREST_RATE}}% per annum from {{DUE_DATE}} till the date of institution of the suit",
            "Award pendente lite and future interest under Section 34 CPC",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Do NOT select one bond article mechanically without checking whether the bond is payable on demand, on a fixed date, or on contingency.",
        ],
        complexity_weight=1,
    ),

    # ── suit_for_wages ────────────────────────────────────────────────────
    "suit_for_wages": _entry(
        registry_kind="cause",
        code="suit_for_wages",
        display_name="Suit for wages (non-workman)",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 73"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        limitation={"article": "7", "period": "Three years", "from": "When the wages accrue due"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["employment_details", "wages_due_chart", "demand_and_default"],
        required_reliefs=["money_decree", "interest_pendente_lite_future", "costs"],
        doc_type_keywords=["wages", "salary recovery", "unpaid wages", "service compensation"],
        drafting_red_flags=[
            "If employee is a 'workman' under Industrial Disputes Act, 1947, civil court has NO jurisdiction — remedy before Labour Court.",
            "Art 7 applies to non-seaman wages. Seaman wages are Art 6.",
        ],
        procedural_prerequisites=["labour_forum_bar_screen"],
        complexity_weight=1,
    ),

    # ── quantum_meruit ────────────────────────────────────────────────────
    "quantum_meruit": _entry(
        registry_kind="cause",
        code="quantum_meruit",
        display_name="Suit on quantum meruit for value of work done",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 65", "Section 70"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        limitation={
            "article": "18",
            "period": "Three years",
            "from": "When the work is done (Art 18 — 'for the price of work done by the plaintiff at the request of the defendant where no time has been fixed for payment'. This is the specific article for quantum meruit claims. Accrual: when the work is completed and the defendant has received the benefit)",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["work_performed_details", "absence_of_agreed_price", "reasonable_value_computation"],
        required_reliefs=["money_decree_for_reasonable_value", "interest_pendente_lite_future", "costs"],
        doc_type_keywords=["quantum meruit", "reasonable value", "work done no price agreed"],
        complexity_weight=2,
    ),

    # ── contribution_co_debtors ───────────────────────────────────────────
    "contribution_co_debtors": _entry(
        registry_kind="cause",
        code="contribution_co_debtors",
        display_name="Suit for contribution between co-debtors / co-sureties / joint tortfeasors",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 43 (joint promise)", "Section 146 (co-surety contribution)"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        limitation={
            "article": "UNKNOWN",
            "description": "Verify the applicable article based on relationship: Art 43 for co-sureties (S.146 ICA — 3 years from date of payment in excess of own share), Art 48 for contribution after paying more than share under a joint decree, Art 55 (breach of contract) or Art 113 (residuary) for joint promisors/co-debtors under S.43 ICA or joint tortfeasors. NOTE: Art 46 is a Succession Act article (executor/legacy refund) and does NOT apply to ICA joint promisors.",
            "period": "Three years",
            "from": "The date of payment in excess of the plaintiff's own share",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["joint_liability_basis", "payment_in_excess", "share_computation"],
        required_reliefs=["money_decree_for_excess_share", "interest", "costs"],
        doc_type_keywords=["contribution", "co-debtor", "co-surety", "joint tortfeasor", "excess payment"],
        notes=["S.43 ICA: promisee may compel any joint promisor to perform. Art 43 Limitation Act: surety against co-surety, contribution runs from date of excess payment."],
        facts_must_cover=[
            "Joint liability basis — joint promise (S.43 ICA), co-suretyship (S.146 ICA), or joint tort",
            "Total debt / liability amount and each co-debtor's proportionate share",
            "Amount paid by Plaintiff — date and proof of payment",
            "That Plaintiff paid MORE than his proportionate share",
            "Excess amount for which contribution is sought (amount paid minus Plaintiff's share)",
            "Demand for contribution and Defendant's refusal",
        ],
        prayer_template=[
            "Pass a decree directing the Defendant to pay to the Plaintiff a sum of Rs. {{EXCESS_AMOUNT}}/- being the contribution for the excess payment made by the Plaintiff beyond his proportionate share",
            "Award interest at such rate as this Hon'ble Court deems just from {{DATE_OF_EXCESS_PAYMENT}} till realisation",
            "Award costs of the suit",
        ],
        complexity_weight=2,
    ),

    # ── suit_on_judgment_decree ────────────────────────────────────────────
    # ── guarantee_recovery ────────────────────────────────────────────────
    # Split from guarantee_indemnity_recovery: guarantee variant.
    "guarantee_recovery": _entry(
        registry_kind="cause",
        code="guarantee_recovery",
        display_name="Recovery under guarantee (creditor vs surety)",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 126", "Section 128"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        alternative_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 129 (only for continuing guarantees)", "Section 133 (discharge by variance — pre-empt defence)", "Section 139 (discharge by creditor's act — pre-empt defence)"]},
        ],
        limitation={
            "article": "55",
            "period": "Three years",
            "from": "When the principal debtor defaults — that is the date the guarantee contract is broken, triggering Art 55. Where the guarantee is payable on demand, time runs from the date of demand on the surety. Art 44 is WRONG for guarantees — it covers insurance policies only",
        },
        court_rules=_civil_and_commercial_rules(
            nature_keywords=["business", "commercial", "guarantee"],
        ),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["guarantee_terms", "default_and_trigger", "payment_demand", "interest"],
        required_reliefs=["money_decree", "interest_pendente_lite_future", "costs"],
        doc_type_keywords=["guarantee recovery", "surety", "bank guarantee invocation"],
        mandatory_inline_sections=[
            {
                "section": "GUARANTEE TERMS",
                "placement": "after jurisdiction",
                "instruction": "Tripartite relationship, date, terms, extent of liability, conditions of invocation.",
            },
            {
                "section": "DEFAULT AND INVOCATION",
                "placement": "after terms",
                "instruction": "Specific default by principal debtor, demand on surety, response or failure.",
            },
        ],
        facts_must_cover=[
            "Guarantee contract details — date, parties (creditor, principal debtor, surety), nature of guarantee",
            "Scope and extent of surety's liability (S.128 ICA — co-extensive with principal debtor unless contract provides otherwise)",
            "Default by principal debtor — date and nature of default that triggered the guarantee",
            "Demand on surety — date, mode of demand, and surety's response or refusal to pay",
            "Amount claimed under the guarantee (principal + interest if covered)",
            "Whether guarantee is continuing (S.129 ICA) or for a specific transaction",
        ],
        prayer_template=[
            "Pass a decree directing the Defendant-Surety to pay to the Plaintiff a sum of Rs. {{GUARANTEE_AMOUNT}}/- being the amount due under the guarantee",
            "Award pre-suit interest from {{DEFAULT_DATE}} till the date of institution of the suit",
            "Award pendente lite and future interest under Section 34 CPC",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Co-extensive liability S.128 ICA — plead specifically.",
            "S.133-139 ICA: variance/release may discharge surety.",
            "NOTE: Art 43 (surety against principal debtor) and Art 48 (co-debtor contribution) are SEPARATE causes.",
        ],
        complexity_weight=2,
    ),

    # ── indemnity_recovery ────────────────────────────────────────────────
    # Split from guarantee_indemnity_recovery: indemnity variant.
    "indemnity_recovery": _entry(
        registry_kind="cause",
        code="indemnity_recovery",
        display_name="Recovery under indemnity (indemnified party vs indemnifier)",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 124", "Section 125"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        limitation={
            "article": "55",
            "period": "Three years",
            "from": "When the contract of indemnity is broken — i.e., when the indemnifier refuses to indemnify after the indemnified party suffers actual loss or makes payment (date of damnification). Art 55 applies because indemnity is a contract, and breach occurs when the indemnifier fails to honour the indemnity obligation upon the triggering event",
        },
        court_rules=_civil_and_commercial_rules(
            nature_keywords=["business", "commercial", "indemnity"],
        ),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["indemnity_terms", "loss_or_payment", "demand_and_refusal", "interest"],
        required_reliefs=["money_decree", "interest_pendente_lite_future", "costs"],
        doc_type_keywords=["indemnity recovery", "indemnification claim", "reimbursement"],
        mandatory_inline_sections=[
            {
                "section": "INDEMNITY TERMS",
                "placement": "after jurisdiction",
                "instruction": "Indemnity clause, date, scope, triggering event, extent of coverage.",
            },
            {
                "section": "LOSS AND DEMAND",
                "placement": "after terms",
                "instruction": "Actual loss suffered, date of damnification, demand for reimbursement, refusal.",
            },
        ],
        facts_must_cover=[
            "Indemnity contract details — date, parties, clause, scope of indemnity coverage",
            "Event triggering the indemnity — what loss or liability the Plaintiff suffered",
            "Date of damnification — when Plaintiff actually suffered loss or made payment",
            "Amount of actual loss / payment made by Plaintiff under the indemnity",
            "Demand for reimbursement and Defendant-Indemnifier's refusal",
        ],
        prayer_template=[
            "Pass a decree directing the Defendant to indemnify the Plaintiff by paying a sum of Rs. {{INDEMNITY_AMOUNT}}/- being the actual loss suffered / payment made by the Plaintiff",
            "Award interest from {{DATE_OF_DAMNIFICATION}} till realisation",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "S.124-125 ICA govern indemnity. Right to sue arises on actual loss/payment, not on mere threat.",
            "Distinguish indemnity (bilateral promise to hold harmless) from guarantee (tripartite surety arrangement).",
        ],
        complexity_weight=2,
    ),

    # ── vendor_unpaid_purchase_money ──────────────────────────────────────
    "vendor_unpaid_purchase_money": _entry(
        registry_kind="cause",
        code="vendor_unpaid_purchase_money",
        display_name="Suit by vendor of immovable property for unpaid purchase money",
        primary_acts=[
            {"act": "Transfer of Property Act, 1882", "sections": ["Section 55(4)(b) (vendor's charge for unpaid purchase money)"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16"]},
        ],
        limitation={"article": "53", "period": "Three years", "from": "The time fixed for completing the sale, or where the title is accepted after the time fixed, the date of acceptance"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["sale_agreement_details", "consideration_and_payments", "balance_due", "schedule_of_property"],
        required_reliefs=["money_decree_for_balance_consideration", "vendor_charge_on_property", "interest", "costs"],
        doc_type_keywords=["vendor unpaid", "purchase money", "balance consideration", "seller suing buyer"],
        facts_must_cover=[
            "Sale agreement details — date, parties, property description, total sale consideration",
            "Amounts paid by purchaser (date-wise) and balance consideration outstanding",
            "Date fixed for completing the sale (triggers Art 53 limitation)",
            "Whether sale deed has been executed and registered (affects vendor's charge under S.55(4)(b) TPA)",
            "Demand for balance payment and purchaser's default or refusal",
            "Schedule of property with survey number, area, boundaries",
        ],
        prayer_template=[
            "Pass a decree directing the Defendant to pay to the Plaintiff a sum of Rs. {{BALANCE_AMOUNT}}/- being the unpaid balance of the purchase money",
            "Declare that the Plaintiff has a vendor's charge on the suit property under Section 55(4)(b) TPA for the unpaid purchase money",
            "Award interest from {{DUE_DATE}} till realisation",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Art 53 is specific — do NOT use Art 55 (general breach) for vendor's suit for purchase money.",
            "S.55(4)(b) TPA: vendor has a charge on property for unpaid purchase money — plead this specifically.",
            "If sale deed is already executed and registered, vendor's charge may be lost — screen carefully.",
        ],
        complexity_weight=2,
    ),

    # ── profits_wrongfully_received ───────────────────────────────────────
    "profits_wrongfully_received": _entry(
        registry_kind="cause",
        code="profits_wrongfully_received",
        display_name="Suit for profits of immovable property wrongfully received",
        primary_acts=[
            {"act": "Transfer of Property Act, 1882", "sections": ["Section 44"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16"]},
        ],
        alternative_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 70 (unjust enrichment — secondary foundation)"]},
        ],
        limitation={"article": "51", "period": "Three years", "from": "When the profits are received"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["property_details", "plaintiff_entitlement_to_profits", "wrongful_receipt_by_defendant", "profit_computation"],
        required_reliefs=["money_decree_for_profits", "accounts_if_needed", "costs"],
        doc_type_keywords=["profits wrongfully received", "rental income diverted", "co-owner rent collection"],
        facts_must_cover=[
            "Plaintiff's entitlement to the profits — ownership, co-ownership share, or other right",
            "Property from which profits were generated — schedule with survey number, area, boundaries",
            "How Defendant received the profits — rent collection, crop proceeds, business income from the property",
            "Period and quantum of profits received by Defendant (date-wise / instalment-wise for limitation)",
            "Plaintiff's share of the profits and computation of amount wrongfully received",
            "Demand for accounting / payment and Defendant's refusal",
        ],
        prayer_template=[
            "Pass a decree directing the Defendant to pay to the Plaintiff a sum of Rs. {{CLAIM_AMOUNT}}/- being the profits of the suit property wrongfully received by the Defendant",
            "Direct the Defendant to render a true and faithful account of all profits received from the suit property during the period {{PERIOD}}",
            "Award interest on the amount found due from the date of each wrongful receipt till realisation",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Art 51 runs from when EACH profit is received — limitation runs separately for each instalment.",
            "Distinct from mesne profits (which is for wrongful possession after title). Art 51 covers wrongful receipt of profits even without possession dispute.",
            "Common in co-ownership disputes where one co-owner collects entire rent.",
        ],
        complexity_weight=2,
    ),
}

"""Group 2 — Contract & Commercial Disputes.

Flattened from civil.py SUBSTANTIVE_CAUSES. No conditional fields remain.
"""
from __future__ import annotations

from ._helpers import (
    COMMON_CIVIL_PLAINT_SECTIONS,
    COMMON_REQUIRED_AVERMENTS,
    _civil_and_commercial_rules,
    _civil_court_rules,
    _entry,
)

# ---------------------------------------------------------------------------
# CAUSES
# ---------------------------------------------------------------------------

CAUSES: dict = {

    # ── breach_of_contract ────────────────────────────────────────────────
    "breach_of_contract": _entry(
        registry_kind="cause",
        code="breach_of_contract",
        display_name="Damages for breach of contract",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 73"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        alternative_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 37 (only when defendant's non-performance is the direct issue)", "Section 39 (only when there is anticipatory repudiation before due date)", "Section 55 (only when time is of the essence)", "Section 74 (only when liquidated damages stipulated)"]},
        ],
        limitation={"article": "55", "period": "Three years", "from": "When contract is broken; or for continuing breach, when it ceases"},
        court_rules=_civil_and_commercial_rules(
            nature_keywords=["business", "commercial", "trade", "supply", "vendor", "franchise", "construction"],
        ),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["contract_details", "breach_particulars", "loss_and_damage", "interest"],
        required_reliefs=["damages_decree", "interest_pendente_lite_future", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["breach_date"],
        doc_type_keywords=["breach of contract", "damages", "compensation"],
        coa_guidance="For a continuing default (e.g., ongoing non-performance, repeated non-payment), plead continuing cause of action with accrual dates. For a one-time termination or refusal, plead date of breach only. Do NOT add a conclusory declaration that the cause of action 'is not continuing in nature' — let the facts speak.",
        permitted_doctrines=[
            "damages_s73", "remoteness_hadley_v_baxendale", "duty_to_mitigate",
        ],
        procedural_prerequisites=["section_12a_mediation", "arbitration_clause_screen"],
        mandatory_inline_sections=[
            {
                "section": "PARTICULARS OF BREACH AND LOSS",
                "placement": "after contract details",
                "instruction": "Itemise each breach, obligation breached, date, specific loss with computation.",
            },
        ],
        damages_categories=["actual_loss", "consequential_loss", "interest_on_delayed_payment"],
        interest_guidance=(
            "Pre-suit interest on delayed payment: claim it only if supported by contract, mercantile usage, substantive law, or another legally sustainable basis. "
            "Pendente lite interest under Section 34 CPC. "
            "Post-decree future interest under Section 34 CPC. "
            "S.73 ICA: compensation for loss naturally arising from breach — interest on delayed payment is a standard head."
        ),
        facts_must_cover=[
            "Date, parties, and essential terms of the contract (written or oral)",
            "Consideration paid or exchanged by the Plaintiff",
            "Specific obligation(s) the Defendant was bound to perform",
            "Date and manner of breach — what the Defendant did or failed to do",
            "Notice of breach given by Plaintiff (legal notice with date and response)",
            "Quantification of each head of loss (actual loss, consequential loss, wasted expenditure)",
            "Steps taken by Plaintiff to mitigate loss (duty to mitigate under S.73 ICA)",
        ],
        prayer_template=[
            "Pass a decree directing the Defendant to pay to the Plaintiff a sum of Rs. {{TOTAL_DAMAGES}}/- as damages for breach of contract",
            "Award pre-suit interest at the rate of {{INTEREST_RATE}}% per annum from {{DATE_OF_BREACH}} till the date of institution of the suit",
            "Award pendente lite interest at such rate as this Hon'ble Court deems fit from the date of institution of the suit till decree under Section 34 CPC",
            "Award future interest at such rate as this Hon'ble Court deems fit from the date of decree till realisation under Section 34 CPC",
            "Award costs of the suit including advocate's fees to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        defensive_points=[
            "Pre-empt 'novation / accord and satisfaction' defence under S.62-63 ICA: plead that no subsequent agreement replaced or discharged the original contract",
            "Pre-empt 'failure to mitigate' defence: plead specific steps taken to minimise loss after breach",
        ],
        mandatory_averments=[
            {
                "averment": "contract_existence_and_terms",
                "provision": "Section 10, Indian Contract Act, 1872",
                "instruction": "Plead date of contract, mode (written/oral), essential terms, and that all elements of a valid contract are present.",
            },
            {
                "averment": "breach_date_and_particulars",
                "provision": "Order VII Rule 1(e), CPC",
                "instruction": "Plead specific date of breach and the precise obligation that was breached.",
            },
            {
                "averment": "loss_computation",
                "provision": "Section 73, Indian Contract Act, 1872",
                "instruction": "Quantify each head of loss separately — actual loss, consequential loss, wasted expenditure.",
            },
        ],
        drafting_red_flags=[
            "Screen arbitration clause — S.8 Arbitration Act may apply.",
            "S.12A Commercial Courts Act pre-institution mediation is mandatory for commercial disputes of specified value not less than Rs.3 lakh, unless urgent interim relief is sought.",
            "Liquidated damages S.74 ICA: plead stipulated sum specifically.",
        ],
        # ── v11.0 Layer 2: Document Components ──
        available_reliefs=[
            {"type": "damages", "subtype": "compensatory", "statute": "S.73 ICA",
             "prayer_text": "decree for damages in the sum of Rs.{{TOTAL_DAMAGES}}/- on account of breach of contract"},
            {"type": "interest", "subtype": "pre_suit", "statute": "Contract / usage / substantive law",
             "prayer_text": "pre-suit interest at the rate of {{INTEREST_RATE}}% per annum from {{DATE_OF_BREACH}} till date of filing"},
            {"type": "interest", "subtype": "pendente_lite", "statute": "S.34 CPC",
             "prayer_text": "pendente lite interest at such rate as this Hon'ble Court deems fit from filing till decree"},
            {"type": "interest", "subtype": "future", "statute": "S.34 CPC",
             "prayer_text": "future interest at such rate as this Hon'ble Court deems fit from decree till realisation"},
            {"type": "costs", "statute": "S.35 CPC",
             "prayer_text": "costs of the suit including advocate's fees"},
            {"type": "general",
             "prayer_text": "such other and further relief(s) as this Hon'ble Court may deem fit and proper"},
        ],
        jurisdiction_basis="Section 20 CPC — where cause of action arose wholly or in part",
        valuation_basis="Amount of damages claimed (for court fee and pecuniary jurisdiction)",
        complexity_weight=2,
    ),

    # ── breach_dealership_franchise ───────────────────────────────────────
    "breach_dealership_franchise": _entry(
        registry_kind="cause",
        code="breach_dealership_franchise",
        display_name="Damages for illegal termination of dealership / franchise / agency",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 73"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        alternative_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 39 (anticipatory breach — only when termination before agreement end date)", "Section 55 (time of essence — only when delivery dates critical)", "Section 74 (only when agreement has LD clause)"]},
        ],
        limitation={"article": "55", "period": "Three years", "from": "Date of illegal termination / breach"},
        court_rules=_civil_and_commercial_rules(),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "commercial_maintainability", "section_12a", "arbitration_disclosure",
            "agreement_details", "termination_and_breach", "damages_quantum",
            "interest", "statement_of_truth",
        ],
        required_reliefs=["damages_decree", "interest_pendente_lite_future", "costs"],
        doc_type_keywords=["dealership", "franchise", "agency termination", "distributor"],
        procedural_prerequisites=["section_12a_mediation", "arbitration_clause_screen"],
        permitted_doctrines=["repudiatory_breach", "anticipatory_breach", "fundamental_breach", "mitigation_of_damages"],
        damages_categories=["loss_of_profits", "loss_of_goodwill", "investment_recovery", "stock_in_trade_losses", "consequential_damages"],
        facts_must_cover=[
            "Date of dealership/franchise agreement, parties, territory assigned, and duration",
            "Key terms — commission rate, renewal/auto-renewal clauses, termination conditions",
            "Plaintiff's investment (infrastructure, stock, staff) and performance record under the agreement",
            "Date and manner of termination communication (termination letter/notice)",
            "Whether contractual termination conditions were satisfied by the Defendant",
            "Whether notice period under the agreement was given or waived",
            "Goodwill and territory development evidence (customer base built, marketing spend)",
            "Whether an arbitration clause exists and its status",
        ],
        prayer_template=[
            "Pass a decree directing the Defendant to pay to the Plaintiff a sum of Rs. {{TOTAL_DAMAGES}}/- as damages for wrongful termination of the dealership/franchise agreement",
            "Award pre-suit interest at the rate of {{INTEREST_RATE}}% per annum from {{DATE_OF_TERMINATION}} till the date of institution of the suit",
            "Award pendente lite interest at such rate as this Hon'ble Court deems fit under Section 34 CPC",
            "Award future interest from the date of decree till realisation under Section 34 CPC",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Screen for arbitration clause — S.8 Arbitration Act 1996 may oust civil court jurisdiction.",
            "S.12A pre-institution mediation is mandatory for commercial disputes of specified value not less than Rs.3 lakh unless urgent interim relief is sought.",
            "S.39 ICA anticipatory breach — if termination is before agreement end date, plead anticipatory breach specifically.",
            "Goodwill damages must be pleaded with evidence of territory development — not presumed.",
        ],
        complexity_weight=3,
    ),

    # ── breach_employment ─────────────────────────────────────────────────
    "breach_employment": _entry(
        registry_kind="cause",
        code="breach_employment",
        display_name="Damages for breach of employment / service contract",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 73"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        alternative_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 74 (only when employment contract has LD/bond clause)"]},
        ],
        limitation={"article": "55", "period": "Three years", "from": "When contract is broken (date of wrongful termination)"},
        court_rules=_civil_and_commercial_rules(),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["contract_details", "breach_details", "loss_quantification"],
        required_reliefs=["damages_decree", "interest_pendente_lite_future", "costs"],
        doc_type_keywords=["employment contract", "service contract", "wrongful termination"],
        procedural_prerequisites=["section_12a_mediation", "arbitration_clause_screen"],
        damages_categories=["salary_in_lieu_of_notice", "loss_of_service_benefits", "reputational_damages", "mitigation_credit"],
        facts_must_cover=[
            "Date of appointment, designation, and contractual terms (notice period, salary, benefits)",
            "Duration of service rendered by the Plaintiff",
            "Date, manner, and reason given for termination",
            "Whether termination followed contractual procedure (notice period, inquiry if applicable)",
            "Whether the Plaintiff is a 'workman' under the Industrial Disputes Act, 1947 — if yes, civil court jurisdiction is excluded",
            "Salary in lieu of notice computation (monthly salary x notice period months)",
            "Steps taken to mitigate loss (job search, new employment obtained)",
        ],
        prayer_template=[
            "Pass a decree directing the Defendant to pay to the Plaintiff a sum of Rs. {{TOTAL_DAMAGES}}/- as damages for wrongful termination of employment",
            "Award pre-suit interest at the rate of {{INTEREST_RATE}}% per annum from {{DATE_OF_TERMINATION}} till the date of institution of the suit",
            "Award pendente lite interest at such rate as this Hon'ble Court deems fit under Section 34 CPC",
            "Award future interest from the date of decree till realisation under Section 34 CPC",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "CRITICAL: If employee is a 'workman' under Industrial Disputes Act 1947, civil court jurisdiction under CPC S.9 may be EXCLUDED. Labour Court / Industrial Tribunal has exclusive jurisdiction for workmen.",
            "S.14(1) SRA bars specific performance of personal service contracts — only damages can be sought.",
        ],
        complexity_weight=2,
    ),

    # ── breach_construction ───────────────────────────────────────────────
    "breach_construction": _entry(
        registry_kind="cause",
        code="breach_construction",
        display_name="Damages for breach of construction / development agreement",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 73"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        alternative_acts=[
            {"act": "Real Estate (Regulation and Development) Act, 2016", "sections": ["Section 18"]},
            {"act": "Indian Contract Act, 1872", "sections": ["Section 55 (when completion date is of the essence)", "Section 74 (when agreement has LD clause)"]},
        ],
        limitation={"article": "55", "period": "Three years", "from": "When contract is broken (abandonment, delivery of defective work, or expiry of completion date)"},
        court_rules=_civil_and_commercial_rules(),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["contract_details", "breach_details", "loss_quantification"],
        required_reliefs=["damages_decree", "interest_pendente_lite_future", "costs"],
        doc_type_keywords=["construction", "development agreement", "builder breach", "delay"],
        procedural_prerequisites=["section_12a_mediation", "arbitration_clause_screen"],
        damages_categories=["cost_of_defects_rectification", "delay_damages", "loss_of_use", "wasted_expenditure"],
        facts_must_cover=[
            "Date of construction/development agreement and agreed scope of work",
            "Total contract value, amounts paid by Plaintiff, and balance",
            "Agreed completion/delivery date",
            "Date and manner of breach — abandonment, defective construction, delay beyond agreed date",
            "Inspection reports or defect notices served on the Defendant",
            "Expert assessment of rectification cost (if defective work)",
            "RERA registration status of project — essential to determine whether civil court has jurisdiction",
        ],
        prayer_template=[
            "Pass a decree directing the Defendant to pay to the Plaintiff a sum of Rs. {{TOTAL_DAMAGES}}/- as damages for breach of the construction/development agreement",
            "Award pre-suit interest at the rate of {{INTEREST_RATE}}% per annum from {{DATE_OF_BREACH}} till the date of institution of the suit",
            "Award pendente lite interest at such rate as this Hon'ble Court deems fit under Section 34 CPC",
            "Award future interest from the date of decree till realisation under Section 34 CPC",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "CRITICAL: For matters the RERA Authority, Adjudicating Officer, or Appellate Tribunal is empowered to determine, civil court jurisdiction is barred under Section 79 of RERA. Screen the proper RERA forum first.",
            "Consumer Protection Act 2019 is an alternative forum for individual homebuyers.",
            "RERA S.31 is a complaint procedure before the RERA Authority — do NOT cite it in a civil plaint.",
        ],
        complexity_weight=2,
    ),

    # ── agency_dispute ────────────────────────────────────────────────────
    "agency_dispute": _entry(
        registry_kind="cause",
        code="agency_dispute",
        display_name="Civil dispute arising from agency relationship",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 73", "Section 213"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        alternative_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 211 (agent acting beyond authority)", "Section 212 (skill and diligence)", "Section 221 (agent's right to remuneration)", "Section 222 (indemnity for lawful acts)", "Section 74 (only when agency agreement has LD clause)"]},
        ],
        limitation={"article": "55", "period": "Three years", "from": "When contract is broken (date commission/amount became due and payable)"},
        court_rules=_civil_and_commercial_rules(),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["contract_details", "breach_details", "loss_quantification"],
        required_reliefs=["damages_decree", "interest_pendente_lite_future", "costs"],
        doc_type_keywords=["agency", "agent dispute", "principal-agent"],
        procedural_prerequisites=["section_12a_mediation", "arbitration_clause_screen"],
        damages_categories=["commission_withheld", "undisclosed_profit_recovery", "indemnity_claim", "lien_on_goods"],
        facts_must_cover=[
            "Nature of agency — express, implied, or apparent authority",
            "Date of agency agreement, scope, duration, and commission/remuneration terms",
            "Specific acts or omissions constituting breach of agency duties",
            "Amount of commission/remuneration withheld or undisclosed profits",
            "Demand for accounts/payment and Defendant's refusal or silence",
        ],
        prayer_template=[
            "Pass a decree directing the Defendant to pay to the Plaintiff a sum of Rs. {{CLAIM_AMOUNT}}/- being the commission/remuneration withheld / undisclosed profits recovered",
            "Direct the Defendant to render a true and faithful account of all transactions conducted as agent of the Plaintiff",
            "Award pre-suit interest at the rate of {{INTEREST_RATE}}% per annum from the date each amount became due till the date of institution of the suit",
            "Award pendente lite and future interest under Section 34 CPC",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Distinguish agency from employment — different legal regime (ICA Chapter X vs ID Act).",
            "Agent's authority: plead whether express, implied, or apparent authority.",
            "Duty to account: S.213 ICA — agent must render proper accounts on demand.",
        ],
        complexity_weight=2,
    ),

    # ── supply_service_contract ───────────────────────────────────────────
    "supply_service_contract": _entry(
        registry_kind="cause",
        code="supply_service_contract",
        display_name="Civil claim on supply / service contract",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 73"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        alternative_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 55 (when delivery date is of the essence)", "Section 74 (when contract has LD clause)"]},
            {"act": "Sale of Goods Act, 1930", "sections": ["Section 55 (suit for damages for non-delivery)", "Section 56 (suit for damages for non-acceptance)"]},
        ],
        limitation={"article": "55", "period": "Three years", "from": "When each payment obligation was breached (invoice due date)"},
        court_rules=_civil_and_commercial_rules(),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["contract_details", "breach_details", "loss_quantification"],
        required_reliefs=["damages_decree", "interest_pendente_lite_future", "costs"],
        doc_type_keywords=["service contract", "supply contract", "work order"],
        procedural_prerequisites=["section_12a_mediation", "arbitration_clause_screen"],
        facts_must_cover=[
            "Purchase orders / work orders with specifications, quantities, and delivery dates",
            "Goods delivered / services rendered with delivery notes or completion certificates",
            "Invoices raised — amounts due per invoice and total outstanding",
            "Defendant's acceptance of goods/services (or rejection with reasons given)",
            "Payment history — amounts paid, dates, and outstanding balance",
            "Demand notice served on Defendant and response received (if any)",
        ],
        prayer_template=[
            "Pass a decree directing the Defendant to pay to the Plaintiff a sum of Rs. {{CLAIM_AMOUNT}}/- being the amount due for goods supplied / services rendered",
            "Award pre-suit interest at the rate of {{INTEREST_RATE}}% per annum from the respective invoice due dates till the date of institution of the suit",
            "Award pendente lite and future interest under Section 34 CPC",
            "Award costs of the suit",
        ],
        complexity_weight=2,
    ),

    # ── specific_performance ──────────────────────────────────────────────
    "specific_performance": _entry(
        registry_kind="cause",
        code="specific_performance",
        display_name="Specific performance of contract relating to immovable property",
        primary_acts=[
            {
                "act": "Specific Relief Act, 1963",
                "sections": [
                    "Section 10 (specific performance shall be enforced subject to Sections 11(2), 14, and 16)",
                    "Section 16", "Section 21", "Section 22",
                ],
            },
            {"act": "Indian Contract Act, 1872", "sections": ["Section 10"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16"]},
        ],
        limitation={"article": "54", "period": "Three years", "from": "Date fixed for performance, or if no date fixed, when plaintiff has notice that performance is refused"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["agreement_details", "readiness_willingness", "refusal_or_default", "schedule_of_property"],
        required_reliefs=["specific_performance_decree", "direction_to_execute_sale_deed", "costs"],
        optional_reliefs=["possession_if_specifically_claimed_u_s_22", "refund_if_specifically_claimed", "compensation_if_claimed_u_s_21"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["readiness_and_willingness"],
        doc_type_keywords=["specific performance", "agreement to sell", "sale deed execution"],
        mandatory_averments=[
            {
                "averment": "readiness_and_willingness",
                "provision": "Section 16(c), Specific Relief Act, 1963",
                "instruction": "Plead factual readiness, not mere formulaic language.",
            },
        ],
        mandatory_inline_sections=[
            {
                "section": "READINESS AND WILLINGNESS",
                "placement": "after agreement details",
                "instruction": "State factual readiness material.",
            },
            {
                "section": "SECTION 22 RELIEFS",
                "placement": "within prayer",
                "instruction": "Claim possession/partition/refund only if required.",
            },
        ],
        facts_must_cover=[
            "Date of agreement to sell, parties, and essential terms (sale price, property description, timeline)",
            "Consideration paid — amount, date, mode (cheque/NEFT/cash) with documentary proof",
            "Balance consideration and Plaintiff's readiness to pay (bank statement showing availability)",
            "Date fixed for execution of sale deed and what happened on that date",
            "Defendant's refusal or failure to execute sale deed — specific acts/omissions",
            "Legal notice sent by Plaintiff calling upon Defendant to perform (date, contents, response)",
            "Plaintiff's continuous readiness and willingness to perform (S.16(c) SRA — factual, not formulaic)",
            "Status of possession — whether Plaintiff is in possession under Part Performance (S.53A TPA)",
        ],
        prayer_template=[
            "Direct the Defendant to execute and register the sale deed in respect of the suit property in favour of the Plaintiff upon receipt of the balance consideration of Rs. {{BALANCE_CONSIDERATION}}/-",
            "Direct the Defendant to deliver vacant and peaceful possession of the suit property to the Plaintiff (if not already in possession)",
            "In the alternative, award compensation under Section 21 of the Specific Relief Act, 1963 in lieu of or in addition to specific performance, at such amount as this Hon'ble Court deems fit",
            "Award pre-suit interest if contract, usage, or substantive law permits, and pendente lite and future interest under Section 34 CPC as this Hon'ble Court deems fit",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        defensive_points=[
            "Pre-empt S.16(c) readiness challenge: plead specific factual acts showing continuous readiness (bank deposits, repeated offers, arranging stamp duty) — not mere formulaic 'always ready and willing'",
            "Pre-empt S.14 'personal service / unsupervisable' bar: plead that the contract is for transfer of immovable property and none of S.14(1) exceptions apply",
            "Pre-empt 'unregistered agreement' defence: if Section 53A TPA is relied on, plead registration where Section 17(1A) of the Registration Act applies; otherwise confine any use of the document to the limited collateral purpose saved by Section 49",
            "Pre-empt 'time is essence' defence: plead that in Indian law, time is generally NOT of essence for immovable property contracts unless expressly stipulated (Chand Rani v. Kamal Rani)",
        ],
        evidence_checklist=[
            "Agreement to sell (original or certified copy)",
            "Payment receipts / bank statements showing consideration paid",
            "Bank statement showing balance consideration availability (readiness proof)",
            "Legal notice calling for performance + postal receipt + AD card",
            "Defendant's reply (if any) to legal notice",
            "Title documents of Defendant (sale deed, khata, EC)",
            "Encumbrance certificate (recent)",
            "Tax paid receipts / utility bills (if in possession under Part Performance)",
        ],
        drafting_red_flags=[
            "Post-2018 Amendment: Section 10 SRA says specific performance shall be enforced subject to Sections 11(2), 14, and 16. Screen the current statutory bars carefully instead of relying on the old discretionary-refusal framework.",
            "Section 41(ha) SRA (2018 Amendment) bars INJUNCTIONS (not specific performance) in infrastructure project contracts listed in SRA Schedule. Note: Section 20A SRA is a separate provision creating Special Courts, not the injunction bar.",
            "Section 20 SRA (substituted performance — 2018 Amendment): Defendant may have the contract performed through a third party at the Plaintiff's cost. Screen for this defence in construction/work contracts.",
            "Section 17(1A) of the Registration Act applies to documents containing contracts to transfer immovable property for consideration when they are relied on for Section 53A TPA. Do not treat it as a blanket registration rule for every agreement to sell.",
        ],
        alternative_acts=[
            {"act": "Transfer of Property Act, 1882", "sections": ["Section 53A"]},
            {"act": "Registration Act, 1908", "sections": ["Section 17(1A)"]},
        ],
        complexity_weight=3,
    ),

    # ── rescission_contract ───────────────────────────────────────────────
    "rescission_contract": _entry(
        registry_kind="cause",
        code="rescission_contract",
        display_name="Rescission of contract",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 27", "Section 30"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16", "Section 20"]},
        ],
        alternative_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 28", "Section 29"]},
        ],
        limitation={"article": "59", "period": "Three years", "from": "When facts entitling rescission first become known"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["contract_details", "grounds_for_rescission", "restoration_offer_if_needed"],
        doc_type_keywords=["rescission", "rescind contract", "section 27 specific relief"],
        facts_must_cover=[
            "Contract details — date, parties, subject matter, and material terms",
            "Ground for rescission — fraud (S.19 ICA), misrepresentation (S.18 ICA), coercion (S.15 ICA), undue influence (S.16 ICA), or mutual mistake (S.20 ICA)",
            "Particulars of fraud or misrepresentation — what was represented, by whom, when, and how it was false",
            "Date of discovery — when the Plaintiff first became aware of the ground for rescission",
            "Plaintiff's readiness to restore benefits received under the contract (restitutio in integrum)",
        ],
        prayer_template=[
            "Pass a decree for rescission of the contract / agreement dated {{DATE_OF_CONTRACT}}",
            "Direct the Defendant to restore to the Plaintiff all benefits received under the contract",
            "Direct restitution, refund, or other consequential relief required to do equity upon rescission, together with appropriate interest if maintainable",
            "Award costs of the suit",
        ],
        required_reliefs=["rescission_decree", "restoration_of_benefits", "restitutionary_refund_if_claimed", "costs"],
        drafting_red_flags=[
            "S.28 SRA governs rescission after a decree for specific performance in sale/lease cases; use it only in that procedural posture.",
            "S.29 SRA concerns an alternative prayer for rescission in a suit for specific performance; it is not a standalone damages provision in a pure rescission suit.",
            "Restitutio in integrum: plaintiff must be ready to restore benefits.",
        ],
        complexity_weight=3,
    ),

    # ── injunction_negative_covenant ──────────────────────────────────────
    "injunction_negative_covenant": _entry(
        registry_kind="cause",
        code="injunction_negative_covenant",
        display_name="Injunction to enforce negative covenant",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 42"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        limitation={"article": "113", "period": "Three years", "from": "When the right to sue accrues (i.e., date of breach of the negative covenant — residuary article, no specific article exists in the Schedule)"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["contract_and_negative_covenant", "breach_or_threat"],
        required_reliefs=["permanent_injunction_decree", "damages_if_past_breach", "costs"],
        doc_type_keywords=["negative covenant", "section 42", "restraint covenant"],
        facts_must_cover=[
            "Contract containing the negative covenant — date, parties, specific clause",
            "Exact terms of the negative covenant (what the Defendant agreed NOT to do)",
            "Date, nature, and specifics of the breach or threatened breach",
            "Damage or threatened damage to the Plaintiff from the breach",
            "Whether the negative covenant is ancillary to a main contract (determines S.27 ICA applicability)",
        ],
        prayer_template=[
            "Pass a decree of permanent injunction restraining the Defendant from breaching the negative covenant contained in clause {{CLAUSE_NUMBER}} of the agreement dated {{DATE_OF_CONTRACT}}",
            "Pass a decree for damages of Rs. {{DAMAGES_AMOUNT}}/- for breach already committed (if applicable)",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "S.27 ICA voids restraint of trade — ensure exception applies (must be ancillary to a main transaction and reasonable in scope/duration/geography).",
            "S.42 SRA: if negative covenant proved, court MAY grant injunction (discretionary, not mandatory).",
            "Art.113 (residuary — 3 years) applies — there is no specific article for injunction suits in the Limitation Act.",
            "For continuing covenant violations (e.g., ongoing non-compete breach): each successive breach is a fresh cause of action for injunction. Plead the date of first discovered breach AND the continuing nature. Art 55 accrual for damages runs from the first breach (Art 58 is for declaratory suits, not contractual damages).",
        ],
        complexity_weight=2,
    ),

    # ── rectification_instrument ──────────────────────────────────────────
    "rectification_instrument": _entry(
        registry_kind="cause",
        code="rectification_instrument",
        display_name="Rectification of instrument",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 26"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 20"]},
        ],
        alternative_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16 (only when instrument relates to immovable property)"]},
        ],
        limitation={"article": "59", "period": "Three years", "from": "When the facts entitling the plaintiff to have the instrument rectified first become known to him (Art 59 covers suits to obtain a declaration, cancel, set aside, or rectify an instrument — it is the specific article, displacing the residuary Art 113)"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["instrument_details", "mutual_mistake_or_fraud", "correct_text_sought"],
        required_reliefs=["rectification_decree", "costs"],
        doc_type_keywords=["rectification", "section 26 specific relief", "correct deed"],
        facts_must_cover=[
            "Parties to the instrument, date of execution, and nature of transaction",
            "True intention of the parties (the agreement the instrument was meant to record)",
            "Specific mistake in the instrument — what it says vs what the parties intended",
            "How the mistake occurred — mutual mistake of fact (S.26(a) SRA) or fraud/misrepresentation (S.26(b) SRA)",
            "Date of discovery of the mistake",
        ],
        prayer_template=[
            "Pass a decree directing rectification of the instrument dated {{DATE_OF_INSTRUMENT}} by substituting the correct clause/term as set out in the plaint",
            "Declare that the rectified instrument represents the true agreement between the parties",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "S.26 SRA: rectification is for MUTUAL mistake or fraud — unilateral mistake by one party alone is not sufficient.",
            "Distinction from cancellation: rectification corrects the instrument (it survives), cancellation voids it.",
        ],
        complexity_weight=3,
    ),

    # ── cancellation_instrument ───────────────────────────────────────────
    "cancellation_instrument": _entry(
        registry_kind="cause",
        code="cancellation_instrument",
        display_name="Cancellation of deed / instrument",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 31", "Section 33"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16"]},
        ],
        alternative_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 32 (only when partial cancellation of severable portion is sought)"]},
        ],
        limitation={"article": "59", "period": "Three years", "from": "When facts entitling cancellation first become known"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "instrument_details", "grounds_for_cancellation", "knowledge_date",
            "consequential_relief", "schedule_of_property_if_needed",
        ],
        required_reliefs=["cancellation_decree", "restoration_direction", "permanent_injunction_against_instrument", "costs"],
        doc_type_keywords=["cancellation of sale deed", "cancel instrument", "voidable deed", "section 31"],
        facts_must_cover=[
            "Particulars of the instrument — date, parties, registration details (if registered)",
            "Ground for cancellation — void ab initio (forgery, no consent) or voidable (fraud, coercion, misrepresentation, undue influence)",
            "Date of execution and registration of the instrument",
            "Date when Plaintiff discovered the ground for cancellation (critical for Art 59 limitation)",
            "Benefits Plaintiff is prepared to restore (restitutio in integrum — S.33 SRA)",
            "Continuing damage or apprehension of damage from the instrument remaining in force",
        ],
        prayer_template=[
            "Pass a decree of cancellation of the instrument dated {{DATE_OF_INSTRUMENT}} executed by the Defendant",
            "Declare that the said instrument is void / voidable and of no legal effect",
            "Direct the Defendant to restore all benefits received under the instrument",
            "Pass a decree of permanent injunction restraining the Defendant from acting upon or relying on the cancelled instrument",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Distinguish void (declaration S.34 SRA) vs voidable (cancellation S.31 SRA).",
            "S.33 SRA requires plaintiff to restore benefits — plead restitution offer.",
            "Knowledge date critical for Art 59.",
        ],
        complexity_weight=3,
    ),
}

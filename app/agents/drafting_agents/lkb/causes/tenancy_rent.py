"""Group 6 — Tenancy / Rent causes.

Covers: eviction, arrears of rent, mesne profits after tenancy termination.
"""
from __future__ import annotations

from ._helpers import (
    COMMON_CIVIL_PLAINT_SECTIONS,
    _civil_court_rules,
    _entry,
)

CAUSES: dict = {
    # ── eviction (flattened — state-specific conditionals removed) ────

    "eviction": _entry(
        registry_kind="cause",
        code="eviction",
        display_name="Eviction of tenant under special rent / tenancy law or TPA",
        primary_acts=[
            {"act": "State Rent / Tenancy Law", "sections": ["Grounds for eviction / possession"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16"]},
        ],
        limitation={
            "article": "UNKNOWN",
            "description": "Eviction limitation must be verified with the governing rent statute or tenancy framework. If the case proceeds as a title or tenancy-determination suit under the Transfer of Property Act, a possession article may apply instead.",
            "period": "Varies by governing statute or forum",
            "from": "From tenancy determination, statutory default, or another ground-specific trigger under the governing law",
        },
        alternative_acts=[
            {"act": "Transfer of Property Act, 1882", "sections": ["Section 106", "Section 111"]},
            {"act": "Karnataka Rent Act, 1999", "sections": ["Grounds for eviction"]},
            {"act": "Maharashtra Rent Control Act, 1999", "sections": ["Grounds for eviction"]},
            {"act": "Delhi Rent Control Act, 1958", "sections": ["Section 14"]},
            {"act": "Tamil Nadu Regulation of Rights and Responsibilities of Landlords and Tenants Act, 2017", "sections": ["Grounds for eviction"]},
            {"act": "Telangana Buildings (Lease, Rent and Eviction) Control Act, 1960", "sections": ["Grounds for eviction"]},
            {"act": "UP Urban Buildings (Regulation of Letting, Rent and Eviction) Act, 1972", "sections": ["Grounds for eviction"]},
            {"act": "West Bengal Premises Tenancy Act, 1997", "sections": ["Grounds for eviction"]},
            {"act": "Andhra Pradesh Buildings (Lease, Rent and Eviction) Control Act, 1960", "sections": ["Grounds for eviction"]},
            {"act": "Gujarat Rent Control Act, 1999", "sections": ["Grounds for eviction"]},
            {"act": "Rajasthan Rent Control Act, 2001", "sections": ["Grounds for eviction"]},
            {"act": "Kerala Buildings (Lease and Rent Control) Act, 1965", "sections": ["Grounds for eviction"]},
            {"act": "Madhya Pradesh Accommodation Control Act, 1961", "sections": ["Grounds for eviction"]},
            {"act": "East Punjab Urban Rent Restriction Act, 1949", "sections": ["Grounds for eviction"]},
            {"act": "Haryana Urban (Control of Rent and Eviction) Act, 1973", "sections": ["Grounds for eviction"]},
            {"act": "Bihar Buildings (Lease, Rent and Eviction) Control Act, 1982", "sections": ["Grounds for eviction"]},
            {"act": "Odisha House Rent Control Act, 1967", "sections": ["Grounds for eviction"]},
            {"act": "Assam Urban Areas Rent Control Act, 1972", "sections": ["Grounds for eviction"]},
        ],
        court_rules=_civil_court_rules(),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "jurisdiction_or_forum", "tenancy_details",
            "statutory_ground_of_eviction", "notice_if_required",
        ],
        required_reliefs=["eviction_decree_or_order", "arrears_if_claimed", "costs"],
        doc_type_keywords=["eviction", "tenant", "landlord", "vacate", "rent control"],
        procedural_prerequisites=["state_statute_screen", "rent_act_bar_screen"],
        mandatory_inline_sections=[
            {
                "section": "TENANCY DETAILS",
                "placement": "after jurisdiction",
                "instruction": "Date, rent, mode, duration, applicable act.",
            },
            {
                "section": "STATUTORY GROUND",
                "placement": "after tenancy",
                "instruction": "Specific section of rent act with all required particulars.",
            },
            {
                "section": "NOTICE TO QUIT",
                "placement": "after ground",
                "instruction": "Date, mode, period, demand, response.",
            },
        ],
        facts_must_cover=[
            "Landlord-tenant relationship: date of letting, written lease or oral, monthly/yearly tenancy, agreed rent, mode of payment",
            "Whether premises fall within Rent Act protection — if NOT, state why (commercial premises above threshold, premises built after cut-off date, premises in exempted area)",
            "Statutory ground of eviction relied upon — cite specific section of applicable Rent Act (e.g., S.14(1)(a) Delhi Rent Control Act for non-payment)",
            "For non-payment ground: arrears chart (month-wise), demand notice with date, tenant's failure to pay within statutory period",
            "For bona fide need ground: specific need (personal residence / business), no other reasonably suitable accommodation, comparative hardship",
            "For subletting ground: date and circumstances of subletting, identity of sub-tenant, that subletting was without landlord's consent",
            "Notice to quit: date served, mode of service (registered post / hand delivery), period given (S.106 TPA: 15 days for monthly, 6 months for yearly for agricultural/manufacturing), expiry date, tenant's response or non-response",
            "Current status: whether tenant is in occupation, whether rent is being tendered/deposited",
        ],
        prayer_template=[
            "Pass a decree / order directing the Defendant to vacate and hand over peaceful possession of the suit premises being {{PROPERTY_DESCRIPTION}} to the Plaintiff",
            "Pass a decree for recovery of arrears of rent amounting to Rs. {{ARREARS_AMOUNT}}/- for the period {{ARREARS_PERIOD}} as per the statement of account annexed hereto",
            "Award mesne profits / occupation charges at the rate of Rs. {{MARKET_MONTHLY_RENT}}/- per month (prevailing market rent) from the date of termination of tenancy till delivery of vacant possession",
            "Direct an inquiry under Order XX Rule 12 CPC for determination of mesne profits for the period from the date of suit till delivery of vacant possession",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper in the facts and circumstances of the case",
        ],
        defensive_points=[
            "Pre-empt 'Rent Act protection' defence: plead specific basis for exemption from Rent Act (threshold, date of construction, area), OR if Rent Act applies, file before Rent Controller not civil court",
            "Pre-empt 'invalid notice' defence: plead compliance with S.106 TPA period (15 days for monthly tenancy), mode of service, and that notice clearly determined tenancy / demanded compliance",
            "Pre-empt 'bona fide need not proved' defence: plead specific need, no alternative accommodation, and that need arose after letting — attach affidavit",
            "Pre-empt 'tenant willing to pay' defence (for non-payment ground): plead that tender was after statutory notice period expired, or was partial, or was not unconditional",
            "Pre-empt 'sub-tenant's independent right' defence: plead sub-tenant has no independent right as subletting was without landlord's written consent",
        ],
        mandatory_averments=[
            {
                "averment": "landlord_tenant_relationship",
                "provision": "Section 105, Transfer of Property Act, 1882",
                "instruction": "Plead the creation of tenancy — date, parties, premises, rent, duration. If oral, plead the terms agreed. If written, annex the lease deed.",
            },
            {
                "averment": "valid_notice_to_quit",
                "provision": "Section 106, Transfer of Property Act, 1882",
                "instruction": "Plead that notice was served in accordance with Section 106 TPA, including the correct statutory notice period and a recognised mode of service. Annex the notice.",
            },
            {
                "averment": "statutory_ground_of_eviction",
                "provision": "Applicable State Rent Act",
                "instruction": "Plead the specific statutory ground under the applicable Rent Act with the exact section number (e.g., S.14(1)(a) Delhi Rent Control Act for non-payment). Without this, the plaint is liable to be returned.",
            },
        ],
        evidence_checklist=[
            "Lease deed / rent agreement (registered if term exceeds 11 months)",
            "Rent receipts / bank statements showing rent payment history",
            "Legal notice / notice to quit with postal receipt / acknowledgment",
            "Municipal tax receipts / property documents proving ownership",
            "Photographs of premises (especially for misuse / subletting grounds)",
            "Affidavit of bona fide need (for personal requirement ground)",
        ],
        drafting_red_flags=[
            "Civil suit against rent-act-protected tenant NOT maintainable — remedy before Rent Controller.",
            "Notice must comply with period requirements (S.106 TPA: 15 days for monthly, 6 months for yearly for agricultural/manufacturing).",
            "Sub-tenants must be separately impleaded.",
            "Do NOT assume a single Limitation Act article; verify the forum first, then the accrual rule.",
            "For Delhi: S.14(1) grounds are exhaustive — no eviction outside listed grounds for protected tenants.",
            "Distinguish 'tenant' from 'licensee' (S.52 Easements Act) — if licensee, Rent Act protection does not apply.",
        ],
        complexity_weight=2,
    ),

    # ── arrears_of_rent ──────────────────────────────────────────────

    "arrears_of_rent": _entry(
        registry_kind="cause",
        code="arrears_of_rent",
        display_name="Recovery of arrears of rent / licence fee",
        primary_acts=[
            {"act": "Transfer of Property Act, 1882", "sections": ["Section 105", "Section 108"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16", "Section 20"]},
        ],
        limitation={
            "article": "52",
            "period": "Three years",
            "from": "When each instalment of rent falls due (runs separately for each period)",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "tenancy_or_licence_details", "arrears_chart",
            "demand_and_default", "interest",
        ],
        required_reliefs=["money_decree_for_arrears", "interest_pendente_lite_future", "costs"],
        doc_type_keywords=["arrears of rent", "rent due", "licence fee due"],
        facts_must_cover=[
            "Landlord-tenant / licensor-licensee relationship: date of letting, parties, premises, agreed rent, mode of payment",
            "Arrears chart: month-wise breakdown of rent due, rent paid (if any), and balance outstanding",
            "Demand for payment: date of demand notice, mode of service, period given, tenant's response or silence",
            "Total amount claimed with calculation (principal arrears + interest if applicable)",
        ],
        prayer_template=[
            "Pass a decree for recovery of Rs. {{ARREARS_AMOUNT}}/- being arrears of rent for the period {{ARREARS_PERIOD}} as per the statement of account annexed hereto",
            "Award interest at the rate of {{INTEREST_RATE}}% per annum on the arrears from the respective due dates till realisation",
            "Award costs of the suit",
        ],
        mandatory_averments=[
            {
                "averment": "tenancy_relationship_and_rent",
                "provision": "Section 105, Transfer of Property Act, 1882",
                "instruction": "Plead the tenancy relationship, agreed rent, and the obligation to pay rent under S.108(l) TPA or the lease deed.",
            },
            {
                "averment": "demand_and_default",
                "provision": "Section 108, Transfer of Property Act, 1882",
                "instruction": "Plead that demand for rent was made and the tenant has failed or refused to pay despite demand.",
            },
        ],
        evidence_checklist=[
            "Lease deed / rent agreement",
            "Rent receipts / bank statements showing payment history and defaults",
            "Demand notice / legal notice with postal receipt",
            "Statement of account (month-wise arrears chart)",
        ],
        procedural_prerequisites=["rent_control_forum_screen"],
        coa_type="continuing",
        complexity_weight=1,
    ),

    # ── mesne_profits_post_tenancy ───────────────────────────────────

    "mesne_profits_post_tenancy": _entry(
        registry_kind="cause",
        code="mesne_profits_post_tenancy",
        display_name="Mesne profits / occupation charges after termination",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16", "Section 2(12)", "Order XX Rule 12"]},
        ],
        alternative_acts=[
            {"act": "Transfer of Property Act, 1882", "sections": ["Section 106", "Section 111"]},
        ],
        limitation={
            "article": "87",
            "period": "Three years",
            "from": "When each period's profits are received — limitation runs separately for each period of wrongful occupation profits. Plaintiff can recover only mesne profits within three years prior to suit. Where mesne profits are directed by Order XX Rule 12 CPC inquiry in an existing possession suit, the inquiry is not a separate suit and limitation does not bar it separately",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "termination_details", "unauthorized_occupation_period",
            "basis_of_quantification",
        ],
        required_reliefs=["mesne_profits_decree", "inquiry_under_order_xx_rule_12", "costs"],
        doc_type_keywords=["mesne profits", "occupation charges"],
        facts_must_cover=[
            "How and when the tenancy was determined — notice to quit, efflux of time, forfeiture",
            "Date from which occupation became wrongful / unauthorised",
            "Period-wise quantification of mesne profits claimed (monthly market rental value)",
            "Basis of quantification — comparable market rent, previous rent, municipal valuation",
        ],
        prayer_template=[
            "Pass a decree for mesne profits / occupation charges at the rate of Rs. {{MONTHLY_RATE}}/- per month from {{TERMINATION_DATE}} till the date of delivery of vacant possession",
            "Direct an inquiry under Order XX Rule 12 CPC for determination of mesne profits for the period from suit date till delivery of possession",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Do NOT cite Article 32 for mesne profits after termination; verify the governing profits article before filing.",
            "Mesne profits (S.2(12) CPC) = profits wrongfully received by a person in possession — distinct from arrears of rent (which accrued during tenancy).",
        ],
        coa_type="continuing",
        complexity_weight=2,
    ),
}

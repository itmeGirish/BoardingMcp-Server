"""Group 3 — Immovable Property (Title, Possession, Mortgage, Land).

Flattened from civil.py SUBSTANTIVE_CAUSES. All conditional fields resolved
to flat values. recovery_of_possession split into 4 sub-type entries.
mortgage_foreclosure_sale split into mortgage_foreclosure and mortgage_sale.
"""
from __future__ import annotations

from ._helpers import (
    COMMON_CIVIL_PLAINT_SECTIONS,
    COMMON_REQUIRED_AVERMENTS,
    _civil_court_rules,
    _entry,
)

# ---------------------------------------------------------------------------
# Shared inline sections / red-flags for recovery_of_possession variants
# ---------------------------------------------------------------------------

_ROP_REQUIRED_SECTIONS = COMMON_CIVIL_PLAINT_SECTIONS + [
    "title_and_ownership", "defendant_occupation",
    "termination_or_revocation_details", "legal_notice",
    "mesne_profits_claim", "schedule_of_property",
]

_ROP_REQUIRED_RELIEFS = [
    "possession_decree", "mesne_profits_inquiry_order_xx_r12", "costs",
]

_ROP_REQUIRED_AVERMENTS = COMMON_REQUIRED_AVERMENTS + [
    "title_basis", "defendant_occupation_basis",
    "demand_for_vacant_possession", "termination_of_tenancy_licence",
]

_ROP_PROCEDURAL = [
    "rent_act_bar_screen",
    "section_80_cpc_notice_if_government_defendant",
    "licence_vs_tenancy_classification_screen",
]

_ROP_EVIDENCE = [
    "title documents", "lease / licence documents", "termination notice",
    "property schedule", "market rent evidence / comparable rental valuation",
    "property tax receipts", "encumbrance certificate",
]

_ROP_INLINE_SECTIONS = [
    {
        "section": "SCHEDULE OF PROPERTY",
        "placement": "after facts",
        "instruction": "Survey number, area, boundaries (N/S/E/W), village, taluk, district, encumbrances.",
    },
    {
        "section": "TITLE AND OWNERSHIP",
        "placement": "within facts",
        "instruction": "Chain of title documents with dates and registration numbers.",
    },
    {
        "section": "VALUATION AND COURT FEE",
        "placement": "after mesne profits",
        "instruction": "Market value for jurisdictional purposes, valuation for court fee under applicable state Court Fees Act, court fee paid.",
    },
    {
        "section": "VERIFICATION",
        "placement": "end of plaint",
        "instruction": "Order VI Rule 15 CPC format. State paragraphs true to personal knowledge vs information/belief. Signed by plaintiff — NOT sworn affidavit.",
    },
]

_ROP_RED_FLAGS = [
    "Do not confuse S.5 SRA (title-based recovery) with S.6 SRA (summary recovery within 6 months of dispossession without title). S.6 has strict 6-month bar.",
    "Do not merge possession and mesne profits into one undifferentiated prayer.",
    "If defendant is tenant protected under State Rent Act, civil suit NOT maintainable — remedy before Rent Controller.",
    "Distinguish tenancy (TPA S.105) from licence (Easements Act S.52) — hybrid language weakens the claim.",
    "S.106 TPA = notice/duration rules. S.111(a) = determination by efflux of time. Do NOT attribute efflux-of-time to S.106.",
    "NEVER say 'plaintiff is in lawful possession' when defendant is in occupation. Say 'plaintiff is the owner ENTITLED TO possession' — the whole suit is because plaintiff does NOT have possession.",
    "For tenant cases: explicitly plead HOW the tenancy was determined — efflux of time under S.111(a) TPA, or forfeiture under S.111(g), or notice under S.106. Do not leave determination vague.",
    "Mesne profits prayer: (a) past mesne profits from specific date to date of suit, (b) inquiry into future mesne profits under Order XX Rule 12 CPC from suit to delivery/relinquishment/3 years from decree, whichever first. Do NOT overlap these two heads.",
]

# ---------------------------------------------------------------------------
# CAUSES
# ---------------------------------------------------------------------------

CAUSES: dict = {

    # ══════════════════════════════════════════════════════════════════════
    # recovery_of_possession — FLATTENED into 4 sub-types
    # ══════════════════════════════════════════════════════════════════════

    # ── recovery_of_possession_tenant ─────────────────────────────────────
    "recovery_of_possession_tenant": _entry(
        registry_kind="cause",
        code="recovery_of_possession_tenant",
        display_name="Recovery of possession — expired/determined lease (tenant)",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 5"]},
            {"act": "Transfer of Property Act, 1882", "sections": ["Section 106", "Section 111(a)"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16", "Order XX Rule 12"]},
        ],
        alternative_acts=[],
        limitation={"article": "64", "period": "Twelve years", "from": "When the tenancy is determined"},
        required_sections=_ROP_REQUIRED_SECTIONS,
        required_reliefs=_ROP_REQUIRED_RELIEFS,
        required_averments=_ROP_REQUIRED_AVERMENTS,
        doc_type_keywords=["recovery of possession", "tenant", "lease expired", "eviction", "vacate"],
        procedural_prerequisites=_ROP_PROCEDURAL,
        evidence_checklist=_ROP_EVIDENCE,
        mandatory_inline_sections=_ROP_INLINE_SECTIONS,
        drafting_red_flags=_ROP_RED_FLAGS,
        facts_must_cover=[
            "Plaintiff's title to the suit property (sale deed / inheritance / gift deed with dates and registration details)",
            "Date and terms of the lease / tenancy agreement (written or oral, monthly rent, duration)",
            "How the tenancy was determined — efflux of time under S.111(a) TPA, forfeiture under S.111(g), or notice under S.106 TPA",
            "Details of termination notice: date served, mode of service, period of notice, expiry date",
            "Defendant's failure to vacate after determination of tenancy",
            "Whether defendant is protected under any State Rent Control Act (and why civil court has jurisdiction)",
            "Mesne profits claim: market rental value, period from determination to date of suit",
        ],
        prayer_template=[
            "Pass a decree for recovery of possession of the suit property more fully described in the Schedule hereto",
            "Pass a decree for past mesne profits at the rate of Rs. {{MONTHLY_RENT}}/- per month from {{DETERMINATION_DATE}} till the date of filing of the suit",
            "Direct an inquiry into future mesne profits under Order XX Rule 12 CPC from the date of suit till delivery of possession or three years from the date of decree, whichever is earlier",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        defensive_points=[
            "Pre-empt 'Rent Act protection' defence: plead that the premises fall outside the ambit of the applicable State Rent Control Act (exempted category, new construction, commercial premises above threshold)",
            "Pre-empt 'notice defective' defence: plead strict compliance with S.106 TPA — 15 days for month-to-month tenancy (unless modified by state law) and service by one of the statutorily recognised modes",
            "Pre-empt 'sub-tenant / deemed tenant' defence: plead that no sub-letting was authorised and defendant is the original tenant",
            "Pre-empt 'estoppel by acceptance of rent after notice' defence: plead that no rent was accepted after service of termination notice",
            "Pre-empt 'tenancy not determined' defence: plead the specific statutory mechanism of determination with dates",
        ],
        mandatory_averments=[
            {
                "averment": "determination_of_tenancy",
                "provision": "Section 106 / Section 111, Transfer of Property Act, 1882",
                "instruction": "Plead the specific mode by which the tenancy stood determined — efflux of time, notice, or forfeiture.",
            },
            {
                "averment": "rent_act_inapplicability",
                "provision": "Applicable State Rent Control Act",
                "instruction": "Plead why the Rent Controller does not have exclusive jurisdiction — exemption category, non-applicability, or vacancy.",
            },
        ],
        complexity_weight=2,
    ),

    # ── recovery_of_possession_licensee ───────────────────────────────────
    "recovery_of_possession_licensee": _entry(
        registry_kind="cause",
        code="recovery_of_possession_licensee",
        display_name="Recovery of possession — revoked licence (licensee)",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 5"]},
            {"act": "Indian Easements Act, 1882", "sections": ["Section 52", "Section 60"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16", "Order XX Rule 12"]},
        ],
        alternative_acts=[
            {"act": "Indian Easements Act, 1882", "sections": ["Section 61", "Section 62", "Section 63"]},
        ],
        limitation={
            "article": "UNKNOWN",
            "description": "Verify the governing possession article. Article 67 is confined to landlord-versus-tenant suits after determination of tenancy and should not be mechanically used for a licensor's title-based recovery claim.",
            "period": "Usually the title-based possession period, subject to the governing article actually attracted by the pleadings",
            "from": "From revocation or from the accrual rule of the governing possession article, depending on how the suit is framed",
        },
        required_sections=_ROP_REQUIRED_SECTIONS,
        required_reliefs=_ROP_REQUIRED_RELIEFS,
        required_averments=_ROP_REQUIRED_AVERMENTS,
        doc_type_keywords=["recovery of possession", "licensee", "licence revoked", "leave and licence"],
        procedural_prerequisites=_ROP_PROCEDURAL,
        evidence_checklist=_ROP_EVIDENCE,
        mandatory_inline_sections=_ROP_INLINE_SECTIONS,
        drafting_red_flags=_ROP_RED_FLAGS,
        facts_must_cover=[
            "Plaintiff's title to the suit property (sale deed / inheritance / gift deed with dates and registration details)",
            "Nature and terms of the licence — leave and licence agreement date, monthly compensation, purpose, duration",
            "Whether the licence is in writing or oral; if written, registration status",
            "How and when the licence was revoked — notice date, mode of service, reasonable time given under S.63 Indian Easements Act",
            "Defendant's failure to vacate after revocation despite reasonable time",
            "That the arrangement is a licence (personal, revocable permission) and NOT a tenancy (exclusive possession, interest in property)",
            "Mesne profits / compensation for use and occupation: market rental value, period from revocation to date of suit",
        ],
        prayer_template=[
            "Pass a decree for recovery of possession of the suit property more fully described in the Schedule hereto",
            "Pass a decree for compensation for use and occupation at the rate of Rs. {{MONTHLY_COMPENSATION}}/- per month from {{REVOCATION_DATE}} till the date of filing of the suit",
            "Direct an inquiry into future mesne profits under Order XX Rule 12 CPC from the date of suit till delivery of possession or three years from the date of decree, whichever is earlier",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        complexity_weight=2,
    ),

    # ── recovery_of_possession_trespasser ─────────────────────────────────
    "recovery_of_possession_trespasser": _entry(
        registry_kind="cause",
        code="recovery_of_possession_trespasser",
        display_name="Recovery of possession — trespasser / unauthorized occupier",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 5", "Section 6 (summary recovery within 6 months)"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16", "Order XX Rule 12"]},
        ],
        alternative_acts=[],
        limitation={"article": "65", "period": "Twelve years", "from": "When possession of defendant becomes adverse to plaintiff"},
        required_sections=_ROP_REQUIRED_SECTIONS,
        required_reliefs=_ROP_REQUIRED_RELIEFS,
        required_averments=COMMON_REQUIRED_AVERMENTS + [
            "title_basis", "defendant_occupation_basis", "demand_for_vacant_possession",
        ],
        doc_type_keywords=["recovery of possession", "trespasser", "encroachment", "unauthorized occupation", "squatter"],
        procedural_prerequisites=[
            "rent_act_bar_screen",
            "section_80_cpc_notice_if_government_defendant",
        ],
        evidence_checklist=_ROP_EVIDENCE,
        mandatory_inline_sections=_ROP_INLINE_SECTIONS,
        drafting_red_flags=_ROP_RED_FLAGS + [
            "S.6 SRA summary recovery available ONLY within 6 months of dispossession — strict bar.",
        ],
        facts_must_cover=[
            "Plaintiff's title to the suit property (sale deed / inheritance / gift deed with dates and registration details)",
            "Plaintiff's prior possession — when and how Plaintiff was in possession before dispossession",
            "Date and manner of trespass / encroachment — how Defendant entered, whether forcibly or stealthily",
            "Whether S.6 SRA summary recovery is available (dispossession within last 6 months) or title-based S.5 SRA",
            "Nature of unauthorised construction or occupation (if any) — area encroached, structures built",
            "Demand for vacant possession — date of demand and Defendant's refusal",
            "Mesne profits claim: market rental value, period from trespass to date of suit",
        ],
        prayer_template=[
            "Pass a decree for recovery of possession of the suit property more fully described in the Schedule hereto by evicting the Defendant therefrom",
            "Pass a decree of mandatory injunction directing the Defendant to remove all unauthorised constructions / structures raised on the suit property",
            "Pass a decree for past mesne profits at the rate of Rs. {{MONTHLY_RENT}}/- per month from {{TRESPASS_DATE}} till the date of filing of the suit",
            "Direct an inquiry into future mesne profits under Order XX Rule 12 CPC from the date of suit till delivery of possession or three years from the date of decree, whichever is earlier",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        complexity_weight=2,
    ),

    # ── recovery_of_possession_co_owner ───────────────────────────────────
    "recovery_of_possession_co_owner": _entry(
        registry_kind="cause",
        code="recovery_of_possession_co_owner",
        display_name="Recovery of possession — co-owner ouster",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 5"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16", "Order XX Rule 12"]},
        ],
        alternative_acts=[],
        limitation={"article": "65", "period": "Twelve years", "from": "When ouster is proved"},
        required_sections=_ROP_REQUIRED_SECTIONS + ["co_ownership_basis", "ouster_particulars"],
        required_reliefs=_ROP_REQUIRED_RELIEFS,
        required_averments=COMMON_REQUIRED_AVERMENTS + [
            "title_basis", "co_ownership_basis", "ouster_details", "demand_for_vacant_possession",
        ],
        doc_type_keywords=["recovery of possession", "co-owner", "ouster", "joint property", "co-sharer"],
        procedural_prerequisites=_ROP_PROCEDURAL,
        evidence_checklist=_ROP_EVIDENCE,
        mandatory_inline_sections=_ROP_INLINE_SECTIONS,
        drafting_red_flags=_ROP_RED_FLAGS + [
            "Ouster must be PROVED — mere non-sharing of income may not amount to ouster.",
            "Consider partition suit as alternative or combined remedy.",
        ],
        facts_must_cover=[
            "Co-ownership basis — how Plaintiff and Defendant became co-owners (inheritance, joint purchase, partition)",
            "Plaintiff's fractional share in the property and documentary basis",
            "Details of ouster — specific acts by which Defendant excluded Plaintiff from possession or enjoyment",
            "Date when ouster commenced (triggers Art 65 limitation — 12 years from ouster)",
            "Demand for restoration of joint possession and Defendant's refusal",
            "Whether partition suit is also being sought as alternative / combined remedy",
            "Mesne profits claim: Plaintiff's proportionate share of rental value, period from ouster to date of suit",
        ],
        prayer_template=[
            "Pass a decree for recovery of joint possession of the suit property more fully described in the Schedule hereto",
            "Pass a decree for past mesne profits proportionate to the Plaintiff's share at the rate of Rs. {{MONTHLY_SHARE}}/- per month from {{OUSTER_DATE}} till the date of filing of the suit",
            "Direct an inquiry into future mesne profits under Order XX Rule 12 CPC from the date of suit till delivery of possession or three years from the date of decree, whichever is earlier",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        complexity_weight=2,
    ),

    # ══════════════════════════════════════════════════════════════════════
    # Other immovable property causes
    # ══════════════════════════════════════════════════════════════════════

    # ── declaration_title ─────────────────────────────────────────────────
    "declaration_title": _entry(
        registry_kind="cause",
        code="declaration_title",
        display_name="Declaration as to title to immovable property",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 34", "Section 35"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16"]},
        ],
        limitation={"article": "58", "period": "Three years", "from": "When right to sue first accrues"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["chain_of_title", "cloud_on_title", "consequential_relief_basis", "schedule_of_property"],
        required_reliefs=["declaration_decree", "consequential_relief", "costs"],
        doc_type_keywords=["declaration of title", "cloud on title", "ownership declaration"],
        mandatory_averments=[
            {
                "averment": "consequential_relief",
                "provision": "Proviso to Section 34, SRA",
                "instruction": "If further relief is available, do not omit it.",
            },
        ],
        facts_must_cover=[
            "Chain of title — how Plaintiff acquired ownership (sale deed, inheritance, gift, partition)",
            "Description of suit property with survey/plot number, area, and boundaries",
            "Nature of cloud on title — what act or claim of Defendant casts doubt on Plaintiff's title",
            "Plaintiff's possession status — whether in actual possession or constructively in possession",
            "Consequential relief sought (if any) beyond bare declaration",
        ],
        prayer_template=[
            "Pass a decree declaring that the Plaintiff is the absolute owner of the suit property described in the Schedule",
            "Pass a decree of consequential relief directing the Defendant to {{CONSEQUENTIAL_RELIEF}}",
            "Pass a decree of permanent injunction restraining the Defendant from interfering with the Plaintiff's title or possession",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Bare declaration without consequential relief may be dismissed under proviso to S.34 SRA.",
            "Revenue entries (RTC/Pahani) are only presumptive — need title documents.",
        ],
        complexity_weight=2,
        # v10.0: gap_definitions inherited from "declaration" gap-family
        # (NOT "partition" — two-level family mapping in _family_defaults.py)
    ),

    # ── partition ─────────────────────────────────────────────────────────
    # Conditional limitation flattened: joint_possession_case (no fixed limitation) as default.
    "partition": _entry(
        registry_kind="cause",
        code="partition",
        display_name="Partition and separate possession",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16", "Section 17", "Order XX Rule 18"]},
            {
                "act": "Hindu Succession Act, 1956",
                "sections": [
                    "Section 6 (pre-09.09.2005: daughters not coparceners; post-09.09.2005 Amendment: daughters are coparceners by birth with same rights as sons)",
                    "Section 8 (succession to male Hindu dying intestate)",
                    "Section 10 (distribution among heirs in class I)",
                ],
            },
        ],
        alternative_acts=[
            {"act": "Partition Act, 1893", "sections": ["Section 2", "Section 3", "Section 4"]},
        ],
        limitation={
            "article": "UNKNOWN",
            "description": "Verify limitation from the pleaded possession status. No fixed limitation commonly applies while co-ownership and joint possession subsist, but exclusion or ouster may engage a specific article.",
            "period": "No fixed period while co-ownership and joint possession subsist; otherwise the exclusion article must be verified",
            "from": "From proven ouster or exclusion if pleaded; otherwise the right may subsist during co-ownership",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["genealogy_table", "schedule_of_property", "share_of_plaintiff"],
        required_reliefs=[
            "preliminary_decree_shares", "partition_by_metes_and_bounds",
            "appointment_of_commissioner", "separate_possession", "final_decree", "costs",
        ],
        doc_type_keywords=["partition", "separate possession", "coparcener", "joint property"],
        mandatory_inline_sections=[
            {"section": "GENEALOGY TABLE", "placement": "before facts", "instruction": "Lineal descent from common ancestor."},
            {"section": "SCHEDULE OF PROPERTY", "placement": "after facts", "instruction": "Complete property description."},
            {"section": "SHARE OF PLAINTIFF", "placement": "after schedule", "instruction": "Exact fractional share and basis."},
        ],
        facts_must_cover=[
            "Common ancestor: name, date of death, religion (Hindu/Muslim/Christian — determines succession law)",
            "Genealogy: complete lineal descent from common ancestor showing all branches, including predeceased members",
            "Whether property is coparcenary (Hindu joint family) or self-acquired by the common ancestor",
            "For Hindu coparcenary: whether any partition or disposition protected by the 2005 amendment occurred before 20.12.2004, and the relevant succession dates for applying the amended Section 6 HSA",
            "Each co-sharer's fractional share with computation basis (per stirpes / per capita / HSA Schedule)",
            "Complete schedule of all properties (immovable + movable) with survey numbers, boundaries, area, market value",
            "Whether any co-sharer has been excluded from possession or enjoyment (affects limitation)",
            "Prior attempts at amicable partition (if any) and why they failed",
        ],
        prayer_template=[
            "Pass a preliminary decree declaring the shares of the parties in the suit properties under Order XX Rule 18 of the Code of Civil Procedure, 1908",
            "Direct partition of the suit properties by metes and bounds according to the shares declared",
            "Appoint a Commissioner under Order XXVI Rule 13 CPC to effect division of the suit properties and submit a report",
            "Pass a final decree allotting specific portions to each party in accordance with the preliminary decree",
            "Direct the parties to bear the costs of the Commissioner proportionate to their shares",
            "In the event that physical partition is not feasible, direct sale of the properties and distribution of sale proceeds in accordance with the declared shares",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        defensive_points=[
            "Pre-empt 'no coparcenary exists' defence: plead the source of joint ownership (inheritance, joint purchase, coparcenary) with documentary proof",
            "Pre-empt 'limitation under Art 110' defence: plead that co-ownership subsists and Plaintiff has not been excluded from enjoyment — therefore no limitation applies",
            "Pre-empt 'partial partition already effected' defence: plead that any prior family arrangement was not a valid partition (no registered deed, no physical division)",
            "Pre-empt 'Plaintiff's share already received' defence: plead that no share was allotted to Plaintiff in any prior division",
            "Pre-empt 'property is self-acquired not joint' defence: plead documentary evidence of joint family nucleus or blending of self-acquired with joint property",
        ],
        mandatory_averments=[
            {
                "averment": "coparcenary_or_co_ownership_status",
                "provision": "Section 6, Hindu Succession Act, 1956 (as amended 2005)",
                "instruction": "Plead the basis of co-ownership — coparcenary birth right, intestate succession, or joint purchase.",
            },
            {
                "averment": "share_computation",
                "provision": "Sections 8 and 10, Hindu Succession Act, 1956",
                "instruction": "Compute and plead the exact fractional share of each party with the statutory basis.",
            },
        ],
        drafting_red_flags=[
            "CRITICAL: After the 2005 amendment as explained in Vineeta Sharma, a daughter's coparcenary right is by birth and does NOT depend on the father being alive on 09.09.2005. Screen instead for the statutory saving of partitions or dispositions protected up to 20.12.2004.",
            "Partition suit follows two-stage decree (Order XX Rule 18 CPC): preliminary decree then final decree — prayer must reflect both.",
            "If property in multiple jurisdictions, S.17 CPC allows suit in any court having jurisdiction over any portion.",
            "Article 110 Limitation Act (12 years) applies if plaintiff has been EXCLUDED from enjoyment of property. 'No limitation' applies ONLY where co-ownership continues without exclusion.",
        ],
        complexity_weight=3,
    ),

    # ── easement ──────────────────────────────────────────────────────────
    "easement": _entry(
        registry_kind="cause",
        code="easement",
        display_name="Declaration of easementary right and injunction",
        coa_type="continuing",
        primary_acts=[
            {"act": "Indian Easements Act, 1882", "sections": ["Section 4 (definition of easement)", "Section 15 (prescriptive easement — 20 years)", "Section 33 (suit for disturbance of easement)"]},
            {"act": "Specific Relief Act, 1963", "sections": ["Section 34", "Section 38", "Section 39"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16"]},
        ],
        limitation={"article": "33", "period": "Three years", "from": "When the right of easement is disturbed"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["schedule_of_property", "easement_right_basis", "disturbance_details"],
        required_reliefs=[
            "declaration_decree",
            "mandatory_injunction_decree",
            "permanent_injunction_decree",
            "costs",
        ],
        doc_type_keywords=["easement", "right of way", "passage", "light", "air", "prescriptive easement"],
        facts_must_cover=[
            "More than twenty years of open, peaceable, uninterrupted use as of right (for prescriptive easement under S.15)",
            "Identification of dominant heritage (Plaintiff's property) and servient heritage (Defendant's property)",
            "Pathway / passage dimensions — width, length, start point, and end point",
            "Specific obstruction events — what the Defendant did, when, and how it blocks the easement",
            "Revenue records or survey references supporting the pathway existence",
        ],
        prayer_template=[
            "Pass a decree declaring that the Plaintiff has an easementary right of way over the pathway described in Schedule B for access to the dominant heritage described in Schedule A",
            "Pass a decree of mandatory injunction directing the Defendant to remove the obstruction from the said pathway and restore the Plaintiff's access",
            "Pass a decree of permanent injunction restraining the Defendant from obstructing or interfering with the Plaintiff's peaceful use of the said pathway in future",
            "Award costs of the suit",
        ],
        drafting_red_flags=[
            "Prescriptive easement requires 20 years of peaceable, open, and uninterrupted enjoyment (S.15 Indian Easements Act).",
            "Distinguish easement (S.4) from licence (S.52) — licence is revocable, easement is not.",
            "S.33: owner of dominant heritage can sue for disturbance of easement.",
        ],
        complexity_weight=2,
    ),

    # ── mortgage_redemption ───────────────────────────────────────────────
    "mortgage_redemption": _entry(
        registry_kind="cause",
        code="mortgage_redemption",
        display_name="Redemption of mortgage",
        primary_acts=[
            {"act": "Transfer of Property Act, 1882", "sections": ["Section 60 (right of mortgagor to redeem)", "Section 91 (persons who may sue for redemption)"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16", "Order XXXIV"]},
        ],
        limitation={"article": "61", "period": "Thirty years", "from": "When right to redeem accrues"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["mortgage_details", "tender_and_refusal", "schedule_of_property"],
        required_reliefs=["preliminary_mortgage_decree", "redemption_decree", "reconveyance", "costs"],
        doc_type_keywords=["mortgage redemption", "redeem mortgage"],
        facts_must_cover=[
            "Mortgage deed details — date, parties, registration number, nature of mortgage (simple, usufructuary, English, conditional sale)",
            "Principal amount secured and interest rate stipulated in the deed",
            "Amount due as of date of suit — principal + interest computation",
            "Plaintiff's willingness and readiness to pay the mortgage money (tender)",
            "Demand for reconveyance and Defendant's refusal to accept payment and release the property",
            "Whether possession was delivered to mortgagee (usufructuary) and rents/profits received",
            "Schedule of mortgaged property with survey number, area, boundaries",
        ],
        prayer_template=[
            "Pass a preliminary decree for redemption under Order XXXIV Rule 7 CPC directing the Defendant to accept the mortgage money found due and deliver possession / execute a reconveyance deed",
            "Direct an account of the mortgage money actually due, including principal, interest, and costs",
            "In default of the Defendant accepting payment within the time fixed by the Court, pass a final decree for redemption",
            "Direct the Defendant to execute and register a deed of reconveyance at the cost of the Plaintiff",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        drafting_red_flags=[
            "Order XXXIV CPC: preliminary-and-final decree procedure mandatory for redemption suits.",
            "S.60 TPA: right to redeem subsists until extinguished by decree — once the right to redeem is extinguished, it is gone.",
            "Art 61: 30 years — but compute from when the right to redeem accrues (usually the date the mortgage money becomes due).",
            "Usufructuary mortgage: mortgagee in possession must account for rents and profits received.",
        ],
        complexity_weight=2,
    ),

    # ── mortgage_foreclosure ──────────────────────────────────────────────
    # Split from mortgage_foreclosure_sale: foreclosure variant.
    "mortgage_foreclosure": _entry(
        registry_kind="cause",
        code="mortgage_foreclosure",
        display_name="Suit for foreclosure on mortgage",
        primary_acts=[
            {"act": "Transfer of Property Act, 1882", "sections": ["Section 67", "Section 68"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16", "Order XXXIV"]},
        ],
        limitation={"article": "62", "period": "Thirty years", "from": "When the money secured by the mortgage becomes due"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["mortgage_details", "default", "amount_due", "schedule_of_property"],
        required_reliefs=["preliminary_mortgage_decree", "final_decree_for_foreclosure", "costs"],
        doc_type_keywords=["foreclosure", "order 34 mortgage", "mortgage by conditional sale", "anomalous mortgage with foreclosure right"],
        facts_must_cover=[
            "Mortgage deed details — date, parties, registration number, nature of mortgage (conditional sale / anomalous with foreclosure clause)",
            "Principal amount secured and interest rate stipulated",
            "Default by mortgagor — date when mortgage money became due and failure to repay",
            "Total amount due as of date of suit (principal + interest + costs)",
            "That the mortgage is of a type that entitles foreclosure (NOT simple or English mortgage — those proceed by sale)",
            "Schedule of mortgaged property with survey number, area, boundaries, market value",
        ],
        prayer_template=[
            "Pass a preliminary decree for foreclosure under Order XXXIV Rule 3 CPC fixing a date for payment of the mortgage money found due",
            "In default of the Defendant paying the amount within the time fixed, pass a final decree for foreclosure declaring that the Defendant is absolutely debarred from all right of redemption",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        drafting_red_flags=[
            "Order XXXIV CPC: preliminary-and-final decree procedure mandatory.",
            "Foreclosure is ordinarily associated with a mortgage by conditional sale and with an anomalous mortgage if its terms confer that remedy. Simple and English mortgages ordinarily proceed by sale, while a usufructuary mortgagee cannot sue for foreclosure or sale under Section 67.",
            "Right of redemption subsists until final decree — mortgagor can redeem after preliminary decree.",
        ],
        complexity_weight=3,
    ),

    # ── mortgage_sale ─────────────────────────────────────────────────────
    # Split from mortgage_foreclosure_sale: sale variant.
    "mortgage_sale": _entry(
        registry_kind="cause",
        code="mortgage_sale",
        display_name="Suit for sale on mortgage",
        primary_acts=[
            {"act": "Transfer of Property Act, 1882", "sections": ["Section 67", "Section 68"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16", "Order XXXIV"]},
        ],
        limitation={"article": "63", "period": "Twelve years", "from": "When the money secured by the mortgage becomes due"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["mortgage_details", "default", "amount_due", "schedule_of_property"],
        required_reliefs=["preliminary_mortgage_decree", "final_decree_for_sale", "costs"],
        doc_type_keywords=["mortgage sale", "order 34 sale", "English mortgage sale"],
        facts_must_cover=[
            "Mortgage deed details — date, parties, registration number, nature of mortgage (simple / English / anomalous)",
            "Principal amount secured and interest rate stipulated",
            "Default by mortgagor — date when mortgage money became due and failure to repay",
            "Total amount due as of date of suit (principal + interest + costs)",
            "That the mortgage is of a type that entitles sale (simple or English mortgage — NOT conditional sale or usufructuary)",
            "Schedule of mortgaged property with survey number, area, boundaries, market value",
        ],
        prayer_template=[
            "Pass a preliminary decree under Order XXXIV Rule 4 CPC directing the Defendant to pay the mortgage money found due within such time as the Court fixes",
            "In default of the Defendant paying the amount within the time fixed, pass a final decree for sale of the mortgaged property described in the Schedule",
            "Direct that the sale proceeds be applied first towards costs, then towards the mortgage money due, and the balance (if any) be paid to the Defendant",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        drafting_red_flags=[
            "Order XXXIV CPC: preliminary-and-final decree procedure mandatory.",
            "Right of redemption subsists until final decree — mortgagor can redeem after preliminary decree.",
            "Art 63 (12 years) for sale vs Art 62 (30 years) for foreclosure — verify which relief is sought.",
        ],
        complexity_weight=3,
    ),

    # ── adverse_possession_claim ──────────────────────────────────────────
    "adverse_possession_claim": _entry(
        registry_kind="cause",
        code="adverse_possession_claim",
        display_name="Declaration of title by adverse possession",
        primary_acts=[
            {"act": "Limitation Act, 1963", "sections": ["Section 27 (extinguishment of right)"]},
            {"act": "Specific Relief Act, 1963", "sections": ["Section 34"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16"]},
        ],
        limitation={"article": "65", "period": "Twelve years (thirty years against Government under Art 112)", "from": "When adverse possession commenced"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "adverse_possession_elements", "12_year_continuous_possession",
            "hostile_open_notorious_exclusive", "schedule_of_property",
        ],
        required_reliefs=["declaration_of_title_by_adverse_possession", "permanent_injunction", "costs"],
        doc_type_keywords=["adverse possession", "prescriptive title", "section 27 limitation"],
        evidence_checklist=[
            "tax payment receipts 12+ years", "mutation records", "encumbrance certificate",
            "neighbourhood witnesses", "construction/improvement proof", "utility connections in own name",
        ],
        facts_must_cover=[
            "Date when Plaintiff first took adverse possession of the suit property",
            "Nature of possession — hostile (not permissive), open (visible to true owner), continuous (unbroken for 12+ years), exclusive (to exclusion of true owner), notorious (known to neighbourhood)",
            "Specific acts of ownership exercised — construction, cultivation, fencing, tax payment, utility connections",
            "That possession was NOT with permission, licence, or tenancy from the true owner",
            "True owner's knowledge of and acquiescence in the adverse possession",
            "Whether suit property belongs to Government (30 years under Art 112) or private party (12 years under Art 65)",
            "Schedule of property with survey number, area, boundaries",
        ],
        prayer_template=[
            "Pass a decree declaring that the Plaintiff has perfected title to the suit property described in the Schedule by adverse possession and that the right of the true owner stands extinguished under Section 27 of the Limitation Act, 1963",
            "Pass a decree of permanent injunction restraining the Defendant from interfering with the Plaintiff's peaceful possession and enjoyment of the suit property",
            "Direct the revenue authorities to mutate the property records in favour of the Plaintiff",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        drafting_red_flags=[
            "ALL elements required: hostile, open, continuous, exclusive, notorious.",
            "Against Government: 30 years (Art 112).",
            "S.27: at END of period, true owner right EXTINGUISHED.",
            "Cannot claim against co-owner in joint possession — ouster must be proved.",
            "WARNING — Plaintiff's limitation trap: if the true owner files a recovery suit, Art 65 gives 12 years. But if the adverse possessor files a declaratory suit (Art 58), limitation is only 3 years from when title was denied/disputed. Plead the correct limitation article.",
        ],
        complexity_weight=3,
    ),

    # ── pre_emption ───────────────────────────────────────────────────────
    "pre_emption": _entry(
        registry_kind="cause",
        code="pre_emption",
        display_name="Suit for pre-emption",
        primary_acts=[
            {"act": "State-specific Pre-emption Act", "sections": ["Varies by state"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16"]},
        ],
        limitation={"article": "97", "period": "One year", "from": "When the buyer takes physical possession of the whole or part of the property sold, or, where the subject of the sale does not admit of physical possession, when the instrument of sale is registered"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["pre_emption_right_basis", "sale_details", "demand_and_tender", "deposit_of_purchase_price"],
        doc_type_keywords=["pre-emption", "right of pre-emption", "article 97"],
        facts_must_cover=[
            "Plaintiff's pre-emptive right — basis under applicable state Pre-emption Act (co-sharer, adjoining owner, village resident)",
            "Sale transaction details — date of sale, sale deed registration number, vendor, vendee, consideration",
            "When Plaintiff first learnt of the sale (triggers limitation)",
            "When buyer took physical possession (triggers Art 97 — 1 year from this date)",
            "Demand and tender — Plaintiff's offer to purchase at the sale price and Defendant's refusal",
            "Deposit of sale consideration (mandatory at filing in most states)",
            "Schedule of property sold with survey number, area, boundaries",
        ],
        prayer_template=[
            "Pass a decree for pre-emption in favour of the Plaintiff in respect of the suit property described in the Schedule",
            "Direct the Defendant-vendee to execute a sale deed in favour of the Plaintiff upon payment of the sale consideration of Rs. {{SALE_PRICE}}/-",
            "Direct the Sub-Registrar to register the transfer in favour of the Plaintiff if the Defendant fails to execute the deed",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        drafting_red_flags=[
            "Pre-emption rights are state-specific — verify applicable statute.",
            "Limitation ONLY ONE YEAR (Art 97).",
            "Deposit of consideration typically mandatory at filing.",
        ],
        complexity_weight=2,
    ),

    # ── benami_declaration ────────────────────────────────────────────────
    # ── lis_pendens_challenge ─────────────────────────────────────────────
    "lis_pendens_challenge": _entry(
        registry_kind="cause",
        code="lis_pendens_challenge",
        display_name="Challenge to transfer during lis pendens (S.52 TPA)",
        primary_acts=[
            {"act": "Transfer of Property Act, 1882", "sections": ["Section 52 (doctrine of lis pendens)"]},
            {"act": "Specific Relief Act, 1963", "sections": ["Section 34", "Section 31"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16"]},
        ],
        limitation={"article": "58", "period": "Three years", "from": "When plaintiff first has knowledge of the transfer made during pendency of suit"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["pending_suit_details", "transfer_during_pendency", "transferee_knowledge", "schedule_of_property"],
        doc_type_keywords=["lis pendens", "section 52 TPA", "transfer during suit", "pendente lite transfer"],
        facts_must_cover=[
            "Prior pending suit — court, case number, parties, subject matter, date of institution",
            "Property that is directly and specifically in question in the pending suit",
            "Transfer during pendency — date, nature (sale/gift/mortgage), transferor, transferee, consideration",
            "Transferee's knowledge of the pending suit (actual or constructive notice)",
            "How the transfer affects the Plaintiff's rights in the pending suit",
            "Schedule of property with survey number, area, boundaries",
        ],
        prayer_template=[
            "Pass a decree declaring that the transfer dated {{TRANSFER_DATE}} in favour of the Defendant is subject to the outcome of the pending suit and does not affect the Plaintiff's rights",
            "Pass a decree of permanent injunction restraining the Defendant-transferee from alienating, encumbering, or dealing with the suit property",
            "Direct the Sub-Registrar to note the pendency of the suit on the property records",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        drafting_red_flags=[
            "S.52 TPA: transfer during pendency of suit is not void but subject to outcome of suit.",
            "Transferee pendente lite is bound by decree even if not party — but impleadment is advisable.",
            "Lis pendens applies only to immovable property directly in question.",
        ],
        complexity_weight=2,
    ),

    # ── guardian_transfer_challenge ────────────────────────────────────────
    # Conditional limitation flattened: ward_attained_majority (article 60(a)) as default.
    "guardian_transfer_challenge": _entry(
        registry_kind="cause",
        code="guardian_transfer_challenge",
        display_name="Suit to set aside transfer of property by guardian of ward",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16"]},
            {"act": "Guardians and Wards Act, 1890", "sections": ["Section 29", "Section 30"]},
        ],
        limitation={
            "article": "UNKNOWN",
            "description": "Guardian-transfer challenges are governed by Article 60, but the correct sub-clause depends on who sues and the accrual trigger. Verify the precise Article 60 branch before filing.",
            "period": "Three years under the applicable Article 60 branch",
            "from": "Often from attaining majority, but verify the statutory trigger for the actual claimant",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["guardian_ward_relationship", "transfer_details", "lack_of_authority_or_necessity", "schedule_of_property"],
        doc_type_keywords=["guardian transfer", "ward property", "minor property", "set aside guardian sale"],
        facts_must_cover=[
            "Guardian-ward relationship — how guardianship arose (natural / court-appointed), ward's date of birth, minority status at time of transfer",
            "Transfer details — date, nature (sale/mortgage/lease), consideration received, transferee",
            "Lack of authority — whether guardian had court permission under S.29 GWA, or necessity justifying the transfer",
            "That the transfer was NOT for the legal necessity or manifest advantage of the ward",
            "Ward's date of attaining majority (triggers limitation under Art 60)",
            "Schedule of property transferred with survey number, area, boundaries",
        ],
        prayer_template=[
            "Pass a decree setting aside the transfer / sale deed dated {{TRANSFER_DATE}} executed by the guardian in respect of the suit property described in the Schedule",
            "Pass a decree for recovery of possession of the suit property from the Defendant-transferee",
            "Direct the Sub-Registrar to cancel the registration of the impugned transfer deed",
            "Pass a decree of permanent injunction restraining the Defendant from alienating, encumbering, or dealing with the suit property",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        drafting_red_flags=[
            "S.29 GWA: guardian cannot alienate ward's immovable property without court permission.",
            "S.30 GWA: void if without permission — but bona fide purchaser for value without notice may have defence.",
            "Art 60 limitation: 3 years — verify accrual trigger (attaining majority vs knowledge of transfer).",
        ],
        complexity_weight=2,
    ),

    # ── boundary_dispute ──────────────────────────────────────────────────
    "boundary_dispute": _entry(
        registry_kind="cause",
        code="boundary_dispute",
        display_name="Suit for settlement of boundary / demarcation",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16"]},
            {"act": "Specific Relief Act, 1963", "sections": ["Section 34 (declaration)", "Section 38 (injunction)"]},
        ],
        limitation={"article": "113", "period": "Three years", "from": "When right to sue accrues (when encroachment/boundary dispute first arises)"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["survey_and_boundary_details", "encroachment_or_overlap", "schedule_of_property", "prayer_for_demarcation"],
        required_reliefs=["declaration_of_boundary", "permanent_injunction", "appointment_of_commissioner_for_survey", "costs"],
        doc_type_keywords=["boundary dispute", "demarcation", "survey", "encroachment", "boundary wall"],
        evidence_checklist=["survey sketch", "revenue records", "village map", "satellite imagery", "FMB (field measurement book)", "neighbouring title documents"],
        facts_must_cover=[
            "Plaintiff's title to the property and boundary as per title deed / revenue records",
            "Survey / revenue records showing the correct boundary (survey number, FMB reference)",
            "Nature of boundary dispute — encroachment, overlap, shifting of boundary stones, construction beyond boundary",
            "Date when encroachment / boundary violation first occurred",
            "Quantum of area encroached (in sq. ft / sq. m / acres)",
            "Attempts at amicable settlement or revenue authority intervention (if any)",
            "Schedule of both properties with survey numbers, area, and existing boundaries",
        ],
        prayer_template=[
            "Pass a decree declaring the correct boundary between the Plaintiff's property (Schedule A) and the Defendant's property (Schedule B) as per the revenue records / survey sketch",
            "Appoint a Commissioner under Order XXVI Rule 9 CPC to survey and demarcate the boundary between the properties",
            "Pass a decree of mandatory injunction directing the Defendant to remove all constructions / encroachments beyond the correct boundary line",
            "Pass a decree of permanent injunction restraining the Defendant from encroaching upon or interfering with the Plaintiff's property beyond the demarcated boundary",
            "Award costs of the suit including Commissioner's fees to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        complexity_weight=2,
    ),

    # ── trespass_immovable ────────────────────────────────────────────────
    # Pure trespass compensation and title or possession relief do not share one limitation rule.
    "trespass_immovable": _entry(
        registry_kind="cause",
        code="trespass_immovable",
        display_name="Civil action for trespass to immovable property",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Trespass to land"]},
            {"act": "Specific Relief Act, 1963", "sections": ["Section 5", "Section 6"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16"]},
        ],
        limitation={
            "article": "UNKNOWN",
            "description": "Do not use Article 65 mechanically for a pure trespass action. Compensation-only trespass claims follow a shorter trespass article, while title or possession relief follows the appropriate possession article.",
            "period": "One year for compensation-only trespass; title or possession relief follows the applicable possession article",
            "from": "From the trespass itself for compensation-only claims, or from the accrual rule of the governing title or possession article",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["plaintiff_possession_or_title", "acts_of_trespass", "damage_or_threat"],
        doc_type_keywords=["trespass", "encroachment", "illegal entry"],
        mandatory_inline_sections=[
            {"section": "SCHEDULE OF PROPERTY", "placement": "after facts", "instruction": "Survey number, area, boundaries, village, taluk, district."},
            {"section": "ACTS OF TRESPASS", "placement": "within facts", "instruction": "Specific acts, dates, nature of construction, area encroached."},
        ],
        facts_must_cover=[
            "Plaintiff's title or possession of the suit property (sale deed / revenue records / prior possession)",
            "Specific acts of trespass — date, manner of entry, what the Defendant did (construction, cultivation, dumping, occupation)",
            "Area trespassed upon — measurements in sq. ft / sq. m",
            "Whether trespass is continuing (fresh cause of action accrues with each day of continuing trespass)",
            "Damage caused to the property or Plaintiff's loss due to the trespass",
            "Demand to vacate / cease trespass and Defendant's refusal",
            "Schedule of property with survey number, area, boundaries",
        ],
        prayer_template=[
            "Pass a decree of mandatory injunction directing the Defendant to remove all unauthorised constructions / encroachments from the suit property and restore it to its original condition",
            "Pass a decree of permanent injunction restraining the Defendant from trespassing upon or entering the suit property in future",
            "Pass a decree for damages / compensation of Rs. {{CLAIM_AMOUNT}}/- for loss caused by the trespass",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        drafting_red_flags=[
            "If possession on title is the real relief, use the appropriate recovery-of-possession cause rather than a pure trespass framing.",
            "Do NOT cite Article 65 for a pure compensation-only trespass claim.",
        ],
        coa_type="continuing",
        complexity_weight=2,
    ),

    # ── mesne_profits ─────────────────────────────────────────────────────
    # New standalone entry for mesne profits claims.
    "mesne_profits": _entry(
        registry_kind="cause",
        code="mesne_profits",
        display_name="Mesne profits / occupation charges (standalone claim)",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 16", "Section 2(12)", "Order XX Rule 12"]},
        ],
        limitation={
            "article": "UNKNOWN",
            "description": "Do not use Article 32 for mesne profits. Verify the governing profits article and plead the claim period-wise.",
            "period": "Runs separately for each profits period under the applicable article",
            "from": "From each period of wrongful receipt or occupation profits, subject to the governing article",
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "title_or_decree_basis", "unauthorized_occupation_period",
            "basis_of_quantification", "schedule_of_property",
        ],
        required_reliefs=["mesne_profits_decree", "inquiry_under_order_xx_rule_12", "costs"],
        doc_type_keywords=["mesne profits", "occupation charges", "use and occupation"],
        coa_type="continuing",
        facts_must_cover=[
            "Plaintiff's title to the suit property or prior decree establishing right to possession",
            "Defendant's wrongful occupation — from when, and on what basis Defendant claims to remain",
            "Period for which mesne profits are claimed (past: from specific date to date of suit; future: inquiry under Order XX Rule 12)",
            "Basis of quantification — market rental value of the property, comparable rentals in the area",
            "Whether Defendant actually received rents/profits from the property during wrongful occupation",
            "Any prior decree for possession (if this is a standalone mesne profits claim following an earlier possession decree)",
            "Schedule of property with survey number, area, boundaries",
        ],
        prayer_template=[
            "Pass a decree for past mesne profits at the rate of Rs. {{MONTHLY_RENT}}/- per month from {{START_DATE}} till the date of filing of the suit, totalling Rs. {{TOTAL_PAST_AMOUNT}}/-",
            "Direct an inquiry into future mesne profits under Order XX Rule 12 CPC from the date of suit till delivery of possession or three years from the date of decree, whichever is earlier",
            "Award pendente lite interest at such rate as this Hon'ble Court deems just on the mesne profits found due",
            "Award costs of the suit to the Plaintiff",
            "Grant such other and further relief(s) as this Hon'ble Court deems fit and proper",
        ],
        drafting_red_flags=[
            "Do NOT cite Article 32 for mesne profits; verify the governing profits article before filing.",
            "CPC S.2(12) defines mesne profits — profits which person in wrongful possession actually received or might with ordinary diligence have received.",
            "Order XX Rule 12: court may pass decree for mesne profits with inquiry.",
            "Distinguish from profits_wrongfully_received (Art 51) which covers wrongful receipt without possession dispute.",
        ],
        complexity_weight=2,
    ),
}

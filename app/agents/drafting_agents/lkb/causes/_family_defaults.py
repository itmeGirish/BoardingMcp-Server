"""v10.0 Family Defaults — TWO-LEVEL family mapping.

TWO SEPARATE CONCERNS:
1. BUILDER FAMILY (_FAMILY_MAP) — broad grouping for engine builders
   (_is_partition_cause, _is_contract_cause, etc.). Builders have per-cause-type
   branches inside, so broad grouping works. Used by templates/engine.py.

2. GAP FAMILY (_GAP_FAMILY_MAP) — fine-grained grouping for gap_definitions
   inheritance. Each gap-family has homogeneous section_plan + gap_definitions
   that genuinely fit ALL its members. Used by resolve_section_plan/resolve_gap_definitions.

WHY TWO LEVELS:
   declaration_title needs _is_partition_cause()=True for builders (engine already
   has 'elif cause_type == "declaration_title"' inside partition branch). But it
   must NOT inherit partition's gap_definitions (GENEALOGY_AND_SHARES etc.).
   Same for easement, mortgage_*, adverse_possession, etc.

Usage:
    from ._family_defaults import get_family, get_gap_family
    from ._family_defaults import resolve_section_plan, resolve_gap_definitions

    get_family("declaration_title")       # "partition" (for engine builders)
    get_gap_family("declaration_title")    # "declaration" (for gap inheritance)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# LEVEL 1: Builder family — broad grouping for engine._is_X_cause() methods
# ---------------------------------------------------------------------------

_FAMILY_MAP: Dict[str, str] = {}


def _register(family: str, cause_types: set):
    for ct in cause_types:
        _FAMILY_MAP[ct] = family


_register("contract", {
    "breach_of_contract", "breach_dealership_franchise", "breach_employment",
    "breach_construction", "agency_dispute", "supply_service_contract",
    "specific_performance", "rescission_contract", "injunction_negative_covenant",
    "rectification_instrument", "cancellation_instrument",
})

_register("money", {
    "money_recovery_loan", "money_recovery_goods", "failure_of_consideration",
    "deposit_refund", "summary_suit_instrument", "recovery_specific_movable",
    "suit_on_bond", "suit_for_wages", "quantum_meruit", "contribution_co_debtors",
    "guarantee_recovery", "indemnity_recovery", "vendor_unpaid_purchase_money",
    "profits_wrongfully_received",
})

_register("accounts", {
    "rendition_of_accounts", "accounts_stated",
})

_register("possession", {
    "recovery_of_possession_tenant", "recovery_of_possession_licensee",
    "recovery_of_possession_trespasser", "recovery_of_possession_co_owner",
})

_register("injunction", {
    "permanent_injunction", "mandatory_injunction",
})

# "partition" = ALL immovable property causes (broad, for engine builders)
_register("partition", {
    "partition", "declaration_title", "easement", "mortgage_redemption",
    "mortgage_foreclosure", "mortgage_sale", "adverse_possession_claim",
    "pre_emption", "lis_pendens_challenge", "guardian_transfer_challenge",
    "boundary_dispute", "trespass_immovable", "mesne_profits",
})

_register("tenancy", {
    "eviction", "arrears_of_rent", "mesne_profits_post_tenancy",
})

_register("tort", {
    "negligence_personal_injury", "negligence_property_damage", "defamation",
    "nuisance", "trespass_goods_movable", "business_disparagement", "conversion",
    "false_imprisonment_civil", "malicious_prosecution_civil",
    "fraud_misrepresentation_standalone", "wrongful_seizure_compensation",
    "illegal_distress_compensation", "tortious_interference_contract",
    "compensation_act_under_enactment",
})


def get_family(cause_type: str) -> str:
    """Get BUILDER family name. Used by engine._is_X_cause() methods."""
    return _FAMILY_MAP.get((cause_type or "").strip(), "")


# ---------------------------------------------------------------------------
# LEVEL 2: Gap family — fine-grained grouping for gap_definitions inheritance
# Only cause types with HOMOGENEOUS gap structure share a gap-family.
# ---------------------------------------------------------------------------

_GAP_FAMILY_MAP: Dict[str, str] = {}


def _register_gap(gap_family: str, cause_types: set):
    for ct in cause_types:
        _GAP_FAMILY_MAP[ct] = gap_family


# Contract: all share FACTS / BREACH_PARTICULARS / DAMAGES
_register_gap("contract", {
    "breach_of_contract", "breach_dealership_franchise", "breach_employment",
    "breach_construction", "agency_dispute", "supply_service_contract",
})

# Contract-specific-performance: readiness + specific performance structure
_register_gap("specific_performance", {
    "specific_performance",
})

# Contract-rescission/cancellation: different gap structure
_register_gap("rescission", {
    "rescission_contract", "cancellation_instrument", "rectification_instrument",
    "injunction_negative_covenant",
})

# Money: all share TRANSACTION / DEFAULT / QUANTIFICATION
_register_gap("money", {
    "money_recovery_loan", "money_recovery_goods", "failure_of_consideration",
    "deposit_refund", "summary_suit_instrument", "suit_on_bond",
    "suit_for_wages", "quantum_meruit", "contribution_co_debtors",
    "guarantee_recovery", "indemnity_recovery", "vendor_unpaid_purchase_money",
    "profits_wrongfully_received", "recovery_specific_movable",
})

# Accounts: FACTS / DUTY_AND_DEFAULT / AMOUNT_DUE
_register_gap("accounts", {
    "rendition_of_accounts", "accounts_stated",
})

# Possession: FACTS_OF_POSSESSION / DISPOSSESSION / LOSS_AND_DAMAGE
_register_gap("possession", {
    "recovery_of_possession_tenant", "recovery_of_possession_licensee",
    "recovery_of_possession_trespasser", "recovery_of_possession_co_owner",
})

# Injunction: FACTS / THREATENED_INJURY / BALANCE_OF_CONVENIENCE
_register_gap("injunction", {
    "permanent_injunction", "mandatory_injunction",
})

# Partition (ONLY actual partition): FACTS / GENEALOGY / DEFENDANT_CONDUCT / NECESSITY
_register_gap("partition", {
    "partition",
})

# Declaration: FACTS / CLOUD_ON_TITLE / CONSEQUENTIAL_RELIEF
_register_gap("declaration", {
    "declaration_title",
})

# Easement: FACTS / LONG_ENJOYMENT / OBSTRUCTION
_register_gap("easement", {
    "easement",
})

# Mortgage: FACTS / MORTGAGE_TERMS / DEFAULT_AND_TENDER
_register_gap("mortgage", {
    "mortgage_redemption", "mortgage_foreclosure", "mortgage_sale",
})

# Adverse possession: FACTS / POSSESSION_HISTORY / ANIMUS_AND_CONTINUITY
_register_gap("adverse_possession", {
    "adverse_possession_claim",
})

# Immovable general: FACTS / DISPUTE / NECESSITY (generic 3-gap for remainder)
_register_gap("immovable_general", {
    "pre_emption", "lis_pendens_challenge", "guardian_transfer_challenge",
    "boundary_dispute", "trespass_immovable", "mesne_profits",
})

# Tenancy: FACTS / NOTICE_COMPLIANCE / GROUNDS / ARREARS_OR_MESNE
_register_gap("tenancy", {
    "eviction", "arrears_of_rent", "mesne_profits_post_tenancy",
})

# Tort: FACTS_OF_WRONG / CAUSATION / DAMAGES
_register_gap("tort", {
    "negligence_personal_injury", "negligence_property_damage", "defamation",
    "nuisance", "trespass_goods_movable", "business_disparagement", "conversion",
    "false_imprisonment_civil", "malicious_prosecution_civil",
    "fraud_misrepresentation_standalone", "wrongful_seizure_compensation",
    "illegal_distress_compensation", "tortious_interference_contract",
    "compensation_act_under_enactment",
})


def get_gap_family(cause_type: str) -> str:
    """Get GAP family name. Used for gap_definitions/section_plan inheritance."""
    return _GAP_FAMILY_MAP.get((cause_type or "").strip(), "")


# ---------------------------------------------------------------------------
# Common section plan components (reused across families)
# ---------------------------------------------------------------------------

def _header_sections():
    """Court heading + parties + title + showeth — universal."""
    return [
        {"key": "court_heading",    "source": "engine", "builder": "court_heading"},
        {"key": "parties",          "source": "engine", "builder": "parties"},
        {"key": "title",            "source": "engine", "builder": "suit_title"},
        {"key": "showeth",          "source": "engine", "builder": "showeth"},
    ]


def _commercial_section():
    return {"key": "commercial", "source": "engine", "builder": "commercial_maintainability",
            "condition": "is_commercial"}


def _pre_gap_sections():
    """Jurisdiction (LLM) + limitation (engine) — before factual LLM gaps."""
    return [
        # Jurisdiction → LLM writes it, auto-constrained by LKB fields
        {"key": "jurisdiction", "source": "llm_gap", "gap_id": "JURISDICTION"},
        # Limitation stays deterministic — simple template from LKB data
        {"key": "limitation",   "source": "engine", "builder": "limitation"},
        {"key": "section_12a",  "source": "engine", "builder": "section_12a",
         "condition": "is_commercial"},
    ]


def _post_gap_sections(*, include_interest=True, include_damages_schedule=True,
                        include_schedule_of_property=False):
    """Substantive sections (LLM) + structural sections (engine) after factual gaps.

    LLM writes: legal_basis, cause_of_action, valuation, prayer
    Engine writes: interest, damages_schedule, schedule, docs, verification, advocate
    """
    sections = [
        # Substantive → LLM writes, auto-constrained by LKB fields
        {"key": "legal_basis",      "source": "llm_gap", "gap_id": "LEGAL_BASIS"},
        {"key": "cause_of_action",  "source": "llm_gap", "gap_id": "CAUSE_OF_ACTION"},
        {"key": "valuation",        "source": "llm_gap", "gap_id": "VALUATION"},
    ]
    # Interest stays deterministic — simple template, no per-cause-type logic needed
    if include_interest:
        sections.append(
            {"key": "interest", "source": "engine", "builder": "interest",
             "condition": "has_interest"})
    # Prayer → LLM writes, auto-constrained by required_reliefs
    sections.append(
        {"key": "prayer", "source": "llm_gap", "gap_id": "PRAYER"})
    # Structural sections stay as engine (generic, no per-cause-type logic)
    if include_damages_schedule:
        sections.append(
            {"key": "damages_schedule", "source": "engine", "builder": "damages_schedule",
             "condition": "has_damages_categories"})
    if include_schedule_of_property:
        sections.append(
            {"key": "schedule_of_property", "source": "engine", "builder": "schedule_of_property",
             "condition": "has_schedule_of_property"})
    sections.extend([
        {"key": "documents_list",   "source": "engine", "builder": "documents_list"},
        {"key": "verification",     "source": "engine", "builder": "verification"},
        {"key": "statement_of_truth", "source": "engine", "builder": "statement_of_truth",
         "condition": "is_commercial"},
        {"key": "advocate_block",   "source": "engine", "builder": "advocate_block"},
    ])
    return sections


# ---------------------------------------------------------------------------
# GAP_FAMILY_DEFAULTS — keyed by GAP family (not builder family)
# Each entry: section_plan + gap_definitions that fit ALL members of that gap-family.
# ---------------------------------------------------------------------------

GAP_FAMILY_DEFAULTS: Dict[str, Dict[str, Any]] = {

    # ── CONTRACT ──────────────────────────────────────────────────────────
    "contract": {
        "section_plan": (
            _header_sections()
            + [_commercial_section()]
            + _pre_gap_sections()
            + [
                {"key": "facts",  "source": "llm_gap", "gap_id": "FACTS"},
                {"key": "breach", "source": "llm_gap", "gap_id": "BREACH_PARTICULARS"},
                {"key": "damages", "source": "llm_gap", "gap_id": "DAMAGES"},
            ]
            + _post_gap_sections(include_schedule_of_property=False)
        ),
        "gap_definitions": [
            {
                "gap_id": "FACTS",
                "heading": "FACTS OF THE CASE",
                "constraints": [
                    "Date, parties, and essential terms of the contract (written or oral)",
                    "Place where contract was executed and where performance was due (situs for jurisdiction)",
                    "Consideration exchanged — what each party gave or promised",
                    "Competency of parties to contract (adults, of sound mind, not disqualified by law)",
                    "Plaintiff's performance or readiness to perform",
                    "Reference to supporting documents as Annexures",
                ],
                "anti_constraints": [
                    "Do NOT cite Section/Order/Act numbers — legal basis is a separate section",
                    "Do NOT plead breach or damages — those belong in later sections",
                ],
            },
            {
                "gap_id": "BREACH_PARTICULARS",
                "heading": "BREACH OF CONTRACT AND PARTICULARS",
                "constraints": [
                    "Specific act or omission constituting breach",
                    "Date of breach",
                    "Demand made and response (or silence)",
                ],
                "anti_constraints": [
                    "Do NOT repeat facts already stated",
                    "Do NOT compute damages — that belongs in DAMAGES section",
                    "Do NOT use repudiatory/anticipatory/abandonment language unless USER FACTS support it",
                ],
            },
            {
                "gap_id": "DAMAGES",
                "heading": "LOSS AND DAMAGE",
                "constraints": [
                    "Itemized heads of damage with amounts — attach documentary proof (invoice, receipt, estimate, valuation report) as Annexure for EACH head",
                    "S.73 ICA two-limb foreseeability test: (1) loss naturally arising in the usual course from the breach, AND (2) loss the parties knew at contract formation would likely result from breach",
                    "Causal link between breach and each head of damage",
                    "Mitigation efforts by Plaintiff — what steps Plaintiff took to minimize loss (Explanation to S.73 ICA — duty to mitigate)",
                ],
                "anti_constraints": [
                    "Do NOT claim compound interest unless contract expressly provides",
                    "Do NOT claim punitive damages (not recognized in Indian contract law)",
                    "Do NOT claim remote or speculative damages not within contemplation at the time of contract",
                ],
            },
        ],
    },

    # ── SPECIFIC PERFORMANCE ──────────────────────────────────────────────
    "specific_performance": {
        "section_plan": (
            _header_sections()
            + [_commercial_section()]
            + _pre_gap_sections()
            + [
                {"key": "facts",       "source": "llm_gap", "gap_id": "FACTS"},
                {"key": "readiness",   "source": "llm_gap", "gap_id": "READINESS_AND_WILLINGNESS"},
                {"key": "refusal",     "source": "llm_gap", "gap_id": "DEFENDANT_REFUSAL"},
            ]
            + _post_gap_sections(include_schedule_of_property=True)
        ),
        "gap_definitions": [
            {
                "gap_id": "FACTS",
                "heading": "FACTS OF THE AGREEMENT",
                "constraints": [
                    "Date, parties, and essential terms of the agreement",
                    "Nature of property / subject matter of performance",
                    "Consideration paid or tendered and mode of payment",
                    "Reference to agreement as Annexure",
                ],
                "anti_constraints": [
                    "Do NOT cite Section/Act numbers",
                    "Do NOT plead readiness or refusal here",
                ],
            },
            {
                "gap_id": "READINESS_AND_WILLINGNESS",
                "heading": "PLAINTIFF'S READINESS AND WILLINGNESS",
                "constraints": [
                    "Plaintiff has always been and continues to be ready and willing to perform (S.16(c) SRA)",
                    "Steps taken to perform — balance consideration arranged, documents prepared",
                    "Any tender or offer made to Defendant",
                ],
                "anti_constraints": [
                    "Do NOT admit inability to perform any term",
                ],
            },
            {
                "gap_id": "DEFENDANT_REFUSAL",
                "heading": "DEFENDANT'S REFUSAL TO PERFORM",
                "constraints": [
                    "Specific act of refusal or evasion by Defendant",
                    "Date and manner of refusal",
                    "Legal notice demanding performance and response",
                ],
                "anti_constraints": [
                    "Do NOT claim damages as primary relief — specific performance is primary",
                ],
            },
        ],
    },

    # ── RESCISSION / CANCELLATION / RECTIFICATION ─────────────────────────
    "rescission": {
        "section_plan": (
            _header_sections()
            + _pre_gap_sections()
            + [
                {"key": "facts",     "source": "llm_gap", "gap_id": "FACTS"},
                {"key": "ground",    "source": "llm_gap", "gap_id": "GROUND_FOR_RELIEF"},
                {"key": "prejudice", "source": "llm_gap", "gap_id": "PREJUDICE_AND_NECESSITY"},
            ]
            + _post_gap_sections(include_interest=False, include_damages_schedule=False)
        ),
        "gap_definitions": [
            {
                "gap_id": "FACTS",
                "heading": "FACTS OF THE INSTRUMENT / CONTRACT",
                "constraints": [
                    "Date, parties, and nature of the instrument / contract",
                    "Place where instrument was executed (situs for jurisdiction if immovable property involved)",
                    "How and why the instrument was executed",
                    "Current status and effect of the instrument",
                ],
                "anti_constraints": [
                    "Do NOT cite statutory sections",
                    "Do NOT plead ground for relief here",
                ],
            },
            {
                "gap_id": "GROUND_FOR_RELIEF",
                "heading": "GROUND FOR RESCISSION / CANCELLATION / RECTIFICATION",
                "constraints": [
                    "Specific vitiating factor (fraud / coercion / undue influence / mistake / misrepresentation)",
                    "Particulars of the vitiating act with dates",
                    "How Plaintiff discovered the ground (for limitation purposes)",
                ],
                "anti_constraints": [
                    "Do NOT use vague allegations — plead specific facts",
                ],
            },
            {
                "gap_id": "PREJUDICE_AND_NECESSITY",
                "heading": "PREJUDICE AND NECESSITY FOR RELIEF",
                "constraints": [
                    "How the instrument causes ongoing prejudice to Plaintiff",
                    "For rescission: plead that Plaintiff has been or is in a position to restore benefits received under the contract (S.27 SRA)",
                    "For cancellation: plead reasonable apprehension of serious injury if instrument left outstanding (S.31 SRA test)",
                    "Restoration / restitution sought if any (S.30 SRA restitution on rescission)",
                ],
                "anti_constraints": [
                    "Do NOT use Order XXXIX interim application language (prima facie case, balance of convenience, irreparable harm)",
                ],
            },
        ],
    },

    # ── MONEY / DEBT ──────────────────────────────────────────────────────
    "money": {
        "section_plan": (
            _header_sections()
            + [_commercial_section()]
            + _pre_gap_sections()
            + [
                {"key": "facts",   "source": "llm_gap", "gap_id": "TRANSACTION"},
                {"key": "default", "source": "llm_gap", "gap_id": "DEFAULT"},
                {"key": "quant",   "source": "llm_gap", "gap_id": "QUANTIFICATION"},
            ]
            + _post_gap_sections(include_schedule_of_property=False)
        ),
        "gap_definitions": [
            {
                "gap_id": "TRANSACTION",
                "heading": "FACTS OF THE TRANSACTION",
                "constraints": [
                    "Nature and date of the transaction (loan/sale/service/instrument)",
                    "Place where transaction occurred and where payment was due (situs for jurisdiction)",
                    "Amount advanced, goods supplied, or service rendered",
                    "Terms of repayment or payment agreed",
                ],
                "anti_constraints": [
                    "Do NOT cite statutory sections — legal basis is separate",
                    "Do NOT plead default or quantification here",
                ],
            },
            {
                "gap_id": "DEFAULT",
                "heading": "DEFAULT AND DEMAND",
                "constraints": [
                    "When payment/repayment became due",
                    "Specific default by the Defendant",
                    "Legal notice / demand with date and response",
                ],
                "anti_constraints": [
                    "Do NOT repeat transaction facts",
                    "Do NOT compute interest or total claim here",
                ],
            },
            {
                "gap_id": "QUANTIFICATION",
                "heading": "QUANTIFICATION OF CLAIM",
                "constraints": [
                    "Principal amount due — attach documentary proof (promissory note, invoice, contract, receipt) as Annexure",
                    "Interest computation (rate, period, simple/compound) with basis — contractual rate from agreement, or reasonable rate if no contract",
                    "Total claim amount with breakdown: principal + pre-suit interest + costs",
                    "For breach claims: S.73 ICA two-limb test — (1) loss naturally arising from breach, AND (2) loss known at contract time as likely result",
                ],
                "anti_constraints": [
                    "Do NOT claim compound interest unless expressly agreed in writing",
                    "Do NOT exceed contractual rate or 18% p.a. whichever is lower",
                    "Do NOT claim remote or speculative loss not within contemplation at the time of contract",
                ],
            },
        ],
    },

    # ── ACCOUNTS ──────────────────────────────────────────────────────────
    "accounts": {
        "section_plan": (
            _header_sections()
            + _pre_gap_sections()
            + [
                {"key": "facts",    "source": "llm_gap", "gap_id": "FACTS"},
                {"key": "account",  "source": "llm_gap", "gap_id": "DUTY_AND_DEFAULT"},
                {"key": "amount",   "source": "llm_gap", "gap_id": "AMOUNT_DUE"},
            ]
            + _post_gap_sections(include_interest=False, include_damages_schedule=False)
        ),
        "gap_definitions": [
            {
                "gap_id": "FACTS",
                "heading": "RELATIONSHIP BASIS AND FACTS",
                "constraints": [
                    "Nature of the relationship (agency/partnership/joint business/fiduciary/trust)",
                    "When the relationship was formed and the Defendant's role",
                    "Place where the business/relationship was carried on (situs for jurisdiction)",
                    "Period of account and Plaintiff's entitlement to accounts",
                ],
                "anti_constraints": [
                    "Do NOT cite statutory sections",
                    "Do NOT plead default or amount due here",
                ],
            },
            {
                "gap_id": "DUTY_AND_DEFAULT",
                "heading": "DUTY TO ACCOUNT AND DEFAULT",
                "constraints": [
                    "Defendant's obligation to render accounts",
                    "Specific demands made by Plaintiff (dates and mode)",
                    "Defendant's refusal or failure to comply",
                    "Particulars of books/records/accounts withheld",
                ],
                "anti_constraints": [
                    "Do NOT use typical damages language (loss suffered, compensation)",
                ],
            },
            {
                "gap_id": "AMOUNT_DUE",
                "heading": "AMOUNT BELIEVED DUE AFTER ACCOUNTS",
                "constraints": [
                    "For RENDITION OF ACCOUNTS: approximate amount Plaintiff believes is due, basis of that belief, and why court-supervised accounting is necessary (Defendant controls the books)",
                    "For ACCOUNTS STATED: the specific settled amount agreed between parties, date of settlement, and Defendant's failure to pay the settled sum",
                    "Distinguish clearly: rendition = Defendant must FIRST render accounts; accounts stated = amount already settled, suit is for that fixed sum",
                ],
                "anti_constraints": [
                    "Do NOT plead interest on delayed payment or liquidated damages for rendition suits — amount is unknown until accounts are taken",
                    "For accounts stated: interest may be claimed from date of settlement",
                ],
            },
        ],
    },

    # ── POSSESSION ────────────────────────────────────────────────────────
    "possession": {
        "section_plan": (
            _header_sections()
            + _pre_gap_sections()
            + [
                {"key": "facts",   "source": "llm_gap", "gap_id": "FACTS_OF_POSSESSION"},
                {"key": "dispos",  "source": "llm_gap", "gap_id": "DISPOSSESSION"},
                {"key": "loss",    "source": "llm_gap", "gap_id": "LOSS_AND_DAMAGE"},
            ]
            + _post_gap_sections(include_schedule_of_property=True)
        ),
        "gap_definitions": [
            {
                "gap_id": "FACTS_OF_POSSESSION",
                "heading": "FACTS ESTABLISHING PLAINTIFF'S POSSESSION",
                "constraints": [
                    "Basis of Plaintiff's right to possession — state EXACTLY ONE: owner/lessee/licensee/co-owner",
                    "For LEASE: plead lease deed, monthly rent, lease period, S.105 TPA tenancy — Defendant is 'tenant'",
                    "For LICENCE: plead licence agreement/permission, no exclusive possession, S.52 Easements Act — Defendant is 'licensee', NOT 'tenant'",
                    "For CO-OWNER: plead co-ownership shares, ouster by Defendant co-owner, right to joint possession",
                    "Duration and nature of possession with documentary proof",
                    "Property identification with location/address (schedule reference) — situs determines S.16 CPC jurisdiction",
                ],
                "anti_constraints": [
                    "Do NOT cite statutory sections",
                    "Do NOT plead dispossession or damages here",
                    "Do NOT describe a licensee as 'tenant' or claim tenancy rights for a licence — they are legally distinct (S.52 Easements Act vs S.105 TPA)",
                ],
            },
            {
                "gap_id": "DISPOSSESSION",
                "heading": "DEFENDANT'S UNAUTHORIZED OCCUPATION",
                "constraints": [
                    "How and when Defendant entered or refused to vacate",
                    "Specific acts of dispossession or unauthorized occupation",
                    "Notice given and Defendant's response",
                ],
                "anti_constraints": [
                    "Do NOT repeat facts of possession",
                    "Do NOT compute mesne profits here",
                ],
            },
            {
                "gap_id": "LOSS_AND_DAMAGE",
                "heading": "MESNE PROFITS AND LOSS",
                "constraints": [
                    "Market rent or fair rental value per month — attach valuation report or comparable rental evidence as Annexure",
                    "Period of unauthorized occupation (from date of dispossession to date of suit)",
                    "Total mesne profits / damages claimed with computation breakdown",
                ],
                "anti_constraints": [
                    "Do NOT claim compound interest on mesne profits",
                ],
            },
        ],
    },

    # ── INJUNCTION ────────────────────────────────────────────────────────
    "injunction": {
        "section_plan": (
            _header_sections()
            + _pre_gap_sections()
            + [
                {"key": "facts",   "source": "llm_gap", "gap_id": "FACTS"},
                {"key": "threat",  "source": "llm_gap", "gap_id": "THREATENED_INJURY"},
                {"key": "balance", "source": "llm_gap", "gap_id": "WHY_INJUNCTION_IS_NECESSARY"},
            ]
            + _post_gap_sections(include_interest=False, include_damages_schedule=False,
                                 include_schedule_of_property=True)
        ),
        "gap_definitions": [
            {
                "gap_id": "FACTS",
                "heading": "FACTS OF THE CASE",
                "constraints": [
                    "Plaintiff's existing legal right (title/possession/easement)",
                    "Property identification and Plaintiff's connection to it",
                    "Background context establishing the dispute",
                ],
                "anti_constraints": [
                    "Do NOT cite statutory sections",
                    "Do NOT plead threatened injury or balance of convenience here",
                ],
            },
            {
                "gap_id": "THREATENED_INJURY",
                "heading": "PLAINTIFF'S RIGHT AND DEFENDANT'S INTERFERENCE",
                "constraints": [
                    "Specific acts of interference or threat by Defendant",
                    "When the interference began or was threatened",
                    "How the interference affects Plaintiff's enjoyment of right",
                ],
                "anti_constraints": [
                    "Do NOT plead money damages or interest",
                    "Do NOT argue law — state facts only",
                ],
            },
            {
                "gap_id": "WHY_INJUNCTION_IS_NECESSARY",
                "heading": "WHY INJUNCTION IS NECESSARY",
                "constraints": [
                    "Why monetary compensation is inadequate as a remedy (S.38(3) SRA)",
                    "Multiplicity of suits / continuing wrong that makes damages impractical",
                    "Plaintiff's conduct — prompt action, no delay or acquiescence",
                    "None of the S.41 SRA bars (a) through (j) apply",
                ],
                "anti_constraints": [
                    "Do NOT use Order XXXIX interim application language (prima facie case / balance of convenience / irreparable harm) — those are for IA, not plaint body",
                    "Do NOT claim money damages",
                    "Do NOT cite case law",
                ],
            },
        ],
    },

    # ── PARTITION (only actual partition suits) ───────────────────────────
    "partition": {
        "section_plan": (
            _header_sections()
            + _pre_gap_sections()
            + [
                {"key": "facts",       "source": "llm_gap", "gap_id": "FACTS"},
                {"key": "genealogy",   "source": "llm_gap", "gap_id": "GENEALOGY_AND_SHARES"},
                {"key": "defendant",   "source": "llm_gap", "gap_id": "DEFENDANT_CONDUCT"},
                {"key": "necessity",   "source": "llm_gap", "gap_id": "NECESSITY"},
            ]
            + _post_gap_sections(include_interest=False, include_damages_schedule=False,
                                 include_schedule_of_property=True)
        ),
        "gap_definitions": [
            {
                "gap_id": "FACTS",
                "heading": "FACTS OF THE CASE",
                "constraints": [
                    "Family/co-ownership relationship and how property was acquired",
                    "Property identification and schedule reference",
                    "How joint ownership arose (inheritance/purchase/gift)",
                ],
                "anti_constraints": [
                    "Do NOT cite statutory sections",
                    "Do NOT plead shares or Defendant's conduct here",
                ],
            },
            {
                "gap_id": "GENEALOGY_AND_SHARES",
                "heading": "GENEALOGY TABLE AND SHARE COMPUTATION",
                "constraints": [
                    "Genealogy table showing all co-owners/co-parceners",
                    "Share computation with legal basis (succession/deed)",
                    "Plaintiff's specific share claim",
                ],
                "anti_constraints": [
                    "Do NOT use pre-2005 rules for daughters mechanically. After Vineeta Sharma, the daughter's coparcenary right does not depend on the father being alive on 09-Sep-2005; instead screen for any saving of partitions/dispositions protected up to 20-Dec-2004.",
                ],
            },
            {
                "gap_id": "DEFENDANT_CONDUCT",
                "heading": "DEFENDANT'S CONDUCT AND REFUSAL TO PARTITION",
                "constraints": [
                    "Plaintiff's demand for partition and Defendant's refusal",
                    "Any alienation or encroachment by Defendant",
                    "Current possession status of each co-owner",
                ],
                "anti_constraints": [
                    "Do NOT compute damages or claim interest",
                ],
            },
            {
                "gap_id": "NECESSITY",
                "heading": "NECESSITY FOR COURT INTERVENTION",
                "constraints": [
                    "Why amicable partition is not possible",
                    "Why court-supervised partition is necessary",
                    "Suit seeks two-stage decree under Order XX Rule 18 CPC: (1) preliminary decree declaring shares, (2) final decree effecting physical division",
                ],
                "anti_constraints": [],
            },
        ],
    },

    # ── DECLARATION (title declaration — NOT partition) ───────────────────
    "declaration": {
        "section_plan": (
            _header_sections()
            + _pre_gap_sections()
            + [
                {"key": "facts",          "source": "llm_gap", "gap_id": "FACTS"},
                {"key": "cloud_on_title", "source": "llm_gap", "gap_id": "CLOUD_ON_TITLE"},
                {"key": "consequential",  "source": "llm_gap", "gap_id": "CONSEQUENTIAL_RELIEF"},
            ]
            + _post_gap_sections(include_interest=False, include_damages_schedule=False,
                                 include_schedule_of_property=True)
        ),
        "gap_definitions": [
            {
                "gap_id": "FACTS",
                "heading": "FACTS OF THE CASE",
                "constraints": [
                    "Chain of title — how Plaintiff acquired ownership (sale deed, inheritance, gift, partition, will)",
                    "Description of suit property with survey/plot number, area, and boundaries",
                    "Possession status — actual physical possession, mutation/khata entries, tax payments",
                    "Revenue records (RTC/Pahani/Khata) — these are only PRESUMPTIVE evidence of possession, NOT conclusive proof of title. Must be supported by title deeds",
                ],
                "anti_constraints": [
                    "Do NOT cite statutory sections — legal basis is a separate section",
                    "Do NOT plead Defendant's conduct here — that belongs in CLOUD_ON_TITLE",
                    "Do NOT use genealogy table or share computation language — this is NOT a partition suit",
                ],
            },
            {
                "gap_id": "CLOUD_ON_TITLE",
                "heading": "CLOUD ON TITLE AND DEFENDANT'S INTERFERENCE",
                "constraints": [
                    "Nature of cloud on title — what specific act or claim of Defendant casts doubt on Plaintiff's ownership",
                    "When and how Defendant's interference/denial began",
                    "Any fraudulent documents, false claims, or unauthorized acts by Defendant",
                    "How Defendant's conduct threatens Plaintiff's peaceful enjoyment",
                ],
                "anti_constraints": [
                    "Do NOT use partition/coparcenary language — this is a declaration suit",
                    "Do NOT compute damages or claim monetary compensation",
                ],
            },
            {
                "gap_id": "CONSEQUENTIAL_RELIEF",
                "heading": "CONSEQUENTIAL RELIEF AND NECESSITY FOR DECLARATION",
                "constraints": [
                    "Why bare declaration is insufficient — Proviso to Section 34 SRA requires consequential relief if available",
                    "Specific consequential relief sought (permanent injunction, delivery of possession, cancellation of fraudulent document)",
                    "Continuing prejudice to Plaintiff if declaration is not granted",
                    "Plaintiff has no other adequate remedy at law",
                ],
                "anti_constraints": [
                    "Do NOT use Order XXXIX IA language (irreparable harm / balance of convenience / prima facie case) — those are for interim applications, not plaint",
                    "Do NOT plead money damages unless specifically claimed",
                    "Do NOT use 'refusal to partition' language",
                ],
            },
        ],
    },

    # ── EASEMENT ──────────────────────────────────────────────────────────
    "easement": {
        "section_plan": (
            _header_sections()
            + _pre_gap_sections()
            + [
                {"key": "facts",        "source": "llm_gap", "gap_id": "FACTS"},
                {"key": "long_use",     "source": "llm_gap", "gap_id": "LONG_ENJOYMENT"},
                {"key": "obstruction",  "source": "llm_gap", "gap_id": "OBSTRUCTION"},
            ]
            + _post_gap_sections(include_interest=False, include_damages_schedule=False,
                                 include_schedule_of_property=True)
        ),
        "gap_definitions": [
            {
                "gap_id": "FACTS",
                "heading": "FACTS OF THE CASE",
                "constraints": [
                    "Plaintiff's property (dominant heritage) and Defendant's property (servient heritage)",
                    "Nature of easement claimed (right of way / light / water / support)",
                    "How the easement was created (grant / prescription / necessity)",
                ],
                "anti_constraints": [
                    "Do NOT cite statutory sections",
                    "Do NOT plead obstruction here",
                ],
            },
            {
                "gap_id": "LONG_ENJOYMENT",
                "heading": "PEACEABLE AND CONTINUOUS ENJOYMENT",
                "constraints": [
                    "Period of enjoyment (20+ years for prescriptive easement under S.15 Easements Act)",
                    "Nature of enjoyment — peaceable, open, continuous, uninterrupted, as of right",
                    "Specific acts of user over the prescriptive period",
                ],
                "anti_constraints": [
                    "Do NOT admit any interruption or permission-based use",
                ],
            },
            {
                "gap_id": "OBSTRUCTION",
                "heading": "DEFENDANT'S OBSTRUCTION AND INTERFERENCE",
                "constraints": [
                    "Specific acts of obstruction by Defendant with dates",
                    "How obstruction affects Plaintiff's established right",
                    "Any notice or demand made and Defendant's response",
                ],
                "anti_constraints": [
                    "Do NOT claim money damages as primary relief",
                ],
            },
        ],
    },

    # ── MORTGAGE ──────────────────────────────────────────────────────────
    "mortgage": {
        "section_plan": (
            _header_sections()
            + _pre_gap_sections()
            + [
                {"key": "facts",     "source": "llm_gap", "gap_id": "FACTS"},
                {"key": "mortgage",  "source": "llm_gap", "gap_id": "MORTGAGE_TERMS"},
                {"key": "default",   "source": "llm_gap", "gap_id": "DEFAULT_AND_TENDER"},
            ]
            + _post_gap_sections(include_interest=True, include_damages_schedule=False,
                                 include_schedule_of_property=True)
        ),
        "gap_definitions": [
            {
                "gap_id": "FACTS",
                "heading": "FACTS OF THE MORTGAGE",
                "constraints": [
                    "Date and nature of the mortgage deed (simple/English/usufructuary/anomalous)",
                    "Parties to the mortgage and their capacities",
                    "Principal amount secured and rate of interest agreed",
                    "Property mortgaged with location/address and registration details — situs determines S.16 CPC jurisdiction",
                ],
                "anti_constraints": [
                    "Do NOT cite statutory sections",
                    "Do NOT plead default or tender here",
                ],
            },
            {
                "gap_id": "MORTGAGE_TERMS",
                "heading": "TERMS OF MORTGAGE AND OBLIGATIONS",
                "constraints": [
                    "Repayment terms and schedule",
                    "Mortgage type determines remedy: simple mortgage → S.67 suit for sale; English mortgage → S.67 sale; usufructuary mortgage → S.62 redemption on payment; anomalous → as per deed terms",
                    "Whether mortgage is registered and stamped (S.59 TPA: registered instrument required for immovable > Rs.100)",
                    "Once a mortgage always a mortgage — clog on equity of redemption void (S.60 TPA)",
                ],
                "anti_constraints": [
                    "Do NOT repeat facts already stated",
                    "Do NOT confuse S.67 (mortgagee's right to sell) with S.69 (power of sale without court intervention — only for English mortgage with express power)",
                ],
            },
            {
                "gap_id": "DEFAULT_AND_TENDER",
                "heading": "DEFAULT / TENDER AND DEMAND",
                "constraints": [
                    "For redemption: tender of mortgage amount and mortgagee's refusal — plead willingness and readiness to pay (S.60 TPA)",
                    "For foreclosure/sale: mortgagor's default in repayment with specific dates and amounts",
                    "Legal notice demanding reconveyance/payment and response (date, mode, addressee)",
                    "Art 61 (redemption, 30 years) / Art 62 (foreclosure, 30 years) / Art 63 (sale, 12 years) — verify correct limitation article applies",
                ],
                "anti_constraints": [
                    "Do NOT claim damages beyond mortgage amount + interest",
                    "Do NOT confuse redemption (mortgagor's suit) with foreclosure (mortgagee's suit)",
                ],
            },
        ],
    },

    # ── ADVERSE POSSESSION ────────────────────────────────────────────────
    "adverse_possession": {
        "section_plan": (
            _header_sections()
            + _pre_gap_sections()
            + [
                {"key": "facts",       "source": "llm_gap", "gap_id": "FACTS"},
                {"key": "possession",  "source": "llm_gap", "gap_id": "POSSESSION_HISTORY"},
                {"key": "animus",      "source": "llm_gap", "gap_id": "ANIMUS_AND_CONTINUITY"},
            ]
            + _post_gap_sections(include_interest=False, include_damages_schedule=False,
                                 include_schedule_of_property=True)
        ),
        "gap_definitions": [
            {
                "gap_id": "FACTS",
                "heading": "FACTS OF THE CASE",
                "constraints": [
                    "Property description with location/address (situs determines S.16 CPC jurisdiction) and original ownership",
                    "How and when Plaintiff came into possession",
                    "Current status of the property and parties",
                ],
                "anti_constraints": [
                    "Do NOT cite statutory sections",
                    "Do NOT plead limitation period details here",
                ],
            },
            {
                "gap_id": "POSSESSION_HISTORY",
                "heading": "CONTINUOUS AND UNINTERRUPTED POSSESSION",
                "constraints": [
                    "Complete history of possession for 12+ years (Art 65 Limitation Act)",
                    "Acts of ownership — construction, cultivation, tax payments, mutation entries",
                    "No interruption, abandonment, or acknowledgment of true owner's title",
                ],
                "anti_constraints": [
                    "Do NOT admit any period of dispossession",
                    "Do NOT admit permission-based occupation",
                ],
            },
            {
                "gap_id": "ANIMUS_AND_CONTINUITY",
                "heading": "ANIMUS POSSIDENDI AND HOSTILE CLAIM",
                "constraints": [
                    "Possession was hostile to the true owner — animus possidendi (intention to hold as owner, not as tenant/licensee/caretaker)",
                    "Possession was open and notorious — not concealed or clandestine",
                    "Exclusive possession to the exclusion of the true owner",
                    "MUST plead the title of the true owner (Defendant) and that Plaintiff's possession was ADVERSE to that title — adverse possession cannot exist in vacuum",
                ],
                "anti_constraints": [
                    "Do NOT require proving that true owner 'knew or ought to have known' — that is NOT an Indian law requirement",
                    "Do NOT cite case law for quantum of evidence",
                ],
            },
        ],
    },

    # ── IMMOVABLE GENERAL (generic for remaining immovable property causes) ──
    "immovable_general": {
        "section_plan": (
            _header_sections()
            + _pre_gap_sections()
            + [
                {"key": "facts",    "source": "llm_gap", "gap_id": "FACTS"},
                {"key": "dispute",  "source": "llm_gap", "gap_id": "DISPUTE_PARTICULARS"},
                {"key": "relief",   "source": "llm_gap", "gap_id": "NECESSITY_FOR_RELIEF"},
            ]
            + _post_gap_sections(include_interest=False, include_damages_schedule=False,
                                 include_schedule_of_property=True)
        ),
        "gap_definitions": [
            {
                "gap_id": "FACTS",
                "heading": "FACTS OF THE CASE",
                "constraints": [
                    "Plaintiff's right or interest in the immovable property",
                    "Property description with location/address, survey/plot number and boundaries — situs determines S.16 CPC jurisdiction",
                    "Background facts establishing the dispute",
                ],
                "anti_constraints": [
                    "Do NOT cite statutory sections",
                    "Do NOT plead the dispute details here — those belong in DISPUTE_PARTICULARS",
                ],
            },
            {
                "gap_id": "DISPUTE_PARTICULARS",
                "heading": "PARTICULARS OF THE DISPUTE",
                "constraints": [
                    "Specific wrongful act or claim by Defendant",
                    "When and how the dispute arose",
                    "Demand made and Defendant's response",
                ],
                "anti_constraints": [
                    "Do NOT repeat facts already stated",
                ],
            },
            {
                "gap_id": "NECESSITY_FOR_RELIEF",
                "heading": "NECESSITY FOR COURT INTERVENTION",
                "constraints": [
                    "Why Plaintiff cannot obtain relief without court intervention",
                    "Continuing wrong or prejudice if relief is not granted",
                    "Plaintiff has no other adequate remedy at law",
                ],
                "anti_constraints": [
                    "Do NOT use Order XXXIX IA language (irreparable harm / balance of convenience) — those are for interim applications, not plaint",
                ],
            },
        ],
    },

    # ── TENANCY / RENT ────────────────────────────────────────────────────
    "tenancy": {
        "section_plan": (
            _header_sections()
            + _pre_gap_sections()
            + [
                {"key": "facts",     "source": "llm_gap", "gap_id": "FACTS"},
                {"key": "notice",    "source": "llm_gap", "gap_id": "NOTICE_COMPLIANCE"},
                {"key": "grounds",   "source": "llm_gap", "gap_id": "GROUNDS"},
                {"key": "arrears",   "source": "llm_gap", "gap_id": "ARREARS_OR_MESNE"},
            ]
            + _post_gap_sections(include_schedule_of_property=True)
        ),
        "gap_definitions": [
            {
                "gap_id": "FACTS",
                "heading": "FACTS OF THE TENANCY",
                "constraints": [
                    "Nature of tenancy (monthly/yearly/lease term)",
                    "Date of commencement and agreed rent",
                    "Property identification with location/address and schedule reference — situs determines S.16 CPC jurisdiction",
                ],
                "anti_constraints": [
                    "Do NOT cite statutory sections",
                    "Do NOT plead notice or grounds here",
                ],
            },
            {
                "gap_id": "NOTICE_COMPLIANCE",
                "heading": "NOTICE AND COMPLIANCE",
                "constraints": [
                    "S.106 TPA notice: 15 days for monthly tenancy, 6 months for yearly (agricultural/manufacturing)",
                    "Date of notice, mode of service (registered post AD / hand delivery)",
                    "Notice must expire on last day of tenancy month — plead the expiry date explicitly",
                    "Tenant's response or non-compliance after notice expiry",
                ],
                "anti_constraints": [
                    "Do NOT plead Rent Act grounds unless USER FACTS mention Rent Act protection",
                    "Do NOT confuse S.106 (notice/duration rules) with S.111(a) (determination by efflux of time)",
                ],
            },
            {
                "gap_id": "GROUNDS",
                "heading": "GROUNDS FOR EVICTION",
                "constraints": [
                    "Specific statutory/contractual ground for eviction",
                    "Facts supporting each ground",
                ],
                "anti_constraints": [],
            },
            {
                "gap_id": "ARREARS_OR_MESNE",
                "heading": "ARREARS OF RENT / MESNE PROFITS",
                "constraints": [
                    "Period of arrears with month-wise computation — attach rent receipts/bank statements as Annexure showing last payment",
                    "Total arrears claimed with breakdown",
                    "Mesne profits from notice expiry till delivery of possession — at market rate (attach valuation evidence as Annexure)",
                ],
                "anti_constraints": [
                    "Do NOT claim compound interest on arrears",
                ],
            },
        ],
    },

    # ── TORT / CIVIL WRONG ────────────────────────────────────────────────
    "tort": {
        "section_plan": (
            _header_sections()
            + _pre_gap_sections()
            + [
                {"key": "facts",      "source": "llm_gap", "gap_id": "FACTS_OF_WRONG"},
                {"key": "causation",  "source": "llm_gap", "gap_id": "CAUSATION"},
                {"key": "damages",    "source": "llm_gap", "gap_id": "DAMAGES"},
            ]
            + _post_gap_sections(include_schedule_of_property=False)
        ),
        "gap_definitions": [
            {
                "gap_id": "FACTS_OF_WRONG",
                "heading": "FACTS OF THE TORTIOUS ACT",
                "constraints": [
                    "Specific wrongful act or omission by Defendant with date, place (situs for jurisdiction), and circumstances",
                    "For DEFAMATION: identify the defamatory statement, medium of publication, identifiable reference to Plaintiff, and that statement is false",
                    "For NEGLIGENCE: plead Defendant's duty of care, standard of care expected, and specific breach of that duty",
                    "For NUISANCE: identify the continuous or repeated interference, its nature (noise/smell/obstruction), and effect on Plaintiff's enjoyment",
                    "For MALICIOUS PROSECUTION: identify the prior proceeding, its termination in Plaintiff's favour, absence of reasonable cause, and malice",
                    "For CONVERSION: identify the specific chattel, Plaintiff's right to possession, and Defendant's act inconsistent with that right",
                ],
                "anti_constraints": [
                    "Do NOT cite statutory sections — legal basis is separate",
                    "Do NOT plead causation or damages here",
                    "For DEFAMATION: Do NOT use the word 'defamation' as a conclusion — plead the FACTS that make the statement defamatory",
                ],
            },
            {
                "gap_id": "CAUSATION",
                "heading": "CAUSATION AND INJURY",
                "constraints": [
                    "Direct causal link between Defendant's act and Plaintiff's injury — but-for test",
                    "Nature and extent of injury (physical/reputational/financial)",
                    "For DEFAMATION: publication to third parties, loss of reputation, shunning by community/business associates",
                    "For NEGLIGENCE: proximate cause — foreseeable consequence of the breach (Re Polemis / Wagon Mound test)",
                    "For NUISANCE: ongoing nature of harm, inability to enjoy property/right",
                    "Special damage must be specifically pleaded with particulars (names, dates, amounts lost) — especially for slander and public nuisance",
                ],
                "anti_constraints": [
                    "Do NOT compute damages amounts — that belongs in DAMAGES section",
                    "Do NOT use vague phrases like 'suffered immensely' without specific particulars",
                ],
            },
            {
                "gap_id": "DAMAGES",
                "heading": "DAMAGES AND COMPENSATION",
                "constraints": [
                    "Itemized heads of damage (general + special damages) — attach documentary proof for EACH head as Annexure",
                    "Specific amounts with basis of computation",
                    "Medical bills / repair costs / loss of earnings (as applicable) — each with supporting document reference",
                    "Special damages must be specifically pleaded with particulars (names, dates, amounts) — mandatory for slander and public nuisance",
                ],
                "anti_constraints": [
                    "Do NOT claim punitive damages unless fraud/malice is pleaded",
                    "Do NOT cite case law for quantum",
                ],
            },
        ],
    },
}

# Backward compat alias — old code may reference FAMILY_DEFAULTS
FAMILY_DEFAULTS = GAP_FAMILY_DEFAULTS


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------

def resolve_family_defaults(cause_type: str) -> Dict[str, Any]:
    """Get GAP family defaults for a cause type. Returns empty dict if unmapped.

    NOTE: Uses _GAP_FAMILY_MAP (fine-grained), NOT _FAMILY_MAP (broad).
    This ensures declaration_title gets "declaration" defaults, not "partition".
    """
    gap_family = get_gap_family(cause_type)
    if not gap_family:
        return {}
    return GAP_FAMILY_DEFAULTS.get(gap_family, {})


def resolve_section_plan(lkb_entry: Dict[str, Any], cause_type: str) -> Optional[List[Dict]]:
    """Cause-type plan overrides gap-family default; None means legacy path."""
    plan = lkb_entry.get("section_plan")
    if plan is not None:
        return plan
    defaults = resolve_family_defaults(cause_type)
    return defaults.get("section_plan")


def resolve_gap_definitions(lkb_entry: Dict[str, Any], cause_type: str) -> Optional[List[Dict]]:
    """Resolve ALL gap_definitions: factual gaps + auto-generated substantive gaps.

    Factual gaps (FACTS, BREACH, DAMAGES, etc.) come from:
      1. LKB entry's own gap_definitions (if set), OR
      2. GAP_FAMILY_DEFAULTS for the gap-family

    Substantive gaps (JURISDICTION, LEGAL_BASIS, CAUSE_OF_ACTION, VALUATION, PRAYER)
    are auto-generated from existing LKB fields (primary_acts, required_reliefs, etc.).
    No manual data authoring needed.
    """
    from ._auto_constraints import build_substantive_gaps

    # 1. Factual gaps
    factual = lkb_entry.get("gap_definitions")
    if factual is None:
        defaults = resolve_family_defaults(cause_type)
        factual = defaults.get("gap_definitions")

    if factual is None:
        return None  # No section_plan → legacy path

    # 2. Auto-generated substantive gaps from LKB fields
    substantive = build_substantive_gaps(lkb_entry, cause_type)

    # 3. Merge: factual first, then substantive (matches section_plan order)
    return factual + substantive

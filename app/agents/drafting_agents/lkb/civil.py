
"""
civil_drafting_master_base.py

Comprehensive master base for mainstream CPC-based civil drafting.

Scope
-----
This module is designed as a production-friendly registry and resolution layer for
ordinary civil-court drafting in India. It is intentionally broader than a plaint
cause-type file. It models:

- draft families (plaint, WS, counterclaim, IA, appeal, execution, etc.)
- substantive civil causes
- forum adapters (civil, commercial, rent / tenancy, small causes, HC original side)
- validation registries
- conditional resolution helpers
- fallback classification
- red-flag screening and drafting support metadata

Important
---------
1. This is a master drafting base, not a substitute for legal review.
2. State rent / tenancy regimes, court-fee computation, and pecuniary jurisdiction
   remain jurisdiction-sensitive and should be finalized through local adapters.
3. Special-forum families that are civil in nature but not ordinary CPC drafting
   (probate, family, consumer, MACT, company/NCLT, etc.) should be added as
   separate modules rather than mixed blindly into this base.

Versioning
----------
LKB_VERSION = "4.0-master-civil"
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


LKB_VERSION = "4.0-master-civil"


# ============================================================================
# GLOBAL CONSTANTS
# ============================================================================

COMMERCIAL_THRESHOLD = 300000

COURT_FEE_STATUTES = {
    "Karnataka": "Karnataka Court Fees and Suits Valuation Act, 1958",
    "Maharashtra": "Maharashtra Court Fees Act, 1959",
    "Tamil Nadu": "Tamil Nadu Court Fees and Suits Valuation Act, 1955",
    "Telangana": "Telangana Court Fees and Suits Valuation Act, 1956",
    "Delhi": "Court Fees Act, 1870",
    "_default": "Court Fees Act, 1870",
}

COMMON_REQUIRED_AVERMENTS = [
    "jurisdiction_basis",
    "cause_of_action_dates",
    "valuation_statement",
    "court_fee_basis",
    "verification_clause",
]

COMMON_CIVIL_PLAINT_SECTIONS = [
    "court_heading",
    "title",
    "parties",
    "jurisdiction",
    "facts",
    "legal_basis",
    "cause_of_action",
    "limitation",
    "valuation_court_fee",
    "prayer",
    "document_list",
    "verification",
]

COMMON_WRITTEN_STATEMENT_SECTIONS = [
    "court_heading",
    "title",
    "parties",
    "preliminary_objections",
    "para_wise_reply",
    "additional_pleas",
    "set_off_or_counterclaim_disclosure",
    "prayer",
    "verification",
]

COMMON_IA_SECTIONS = [
    "court_heading",
    "title",
    "parties",
    "application_basis",
    "facts_requiring_urgent_relief",
    "grounds",
    "prayer",
    "affidavit_support",
]

GLOBAL_LIMITATION_SAVERS = {
    "acknowledgment_in_writing": {
        "act": "Limitation Act, 1963",
        "section": "Section 18",
        "effect": "Fresh limitation may run from a valid written acknowledgment signed before expiry.",
    },
    "part_payment_before_expiry": {
        "act": "Limitation Act, 1963",
        "section": "Section 19",
        "effect": "Fresh limitation may run from valid part-payment acknowledged before expiry.",
    },
    "fraud_or_concealment": {
        "act": "Limitation Act, 1963",
        "section": "Section 17",
        "effect": "Limitation may run from discovery of fraud / concealed document / mistake.",
    },
    "prior_wrong_forum": {
        "act": "Limitation Act, 1963",
        "section": "Section 14",
        "effect": "Time spent bona fide in wrong forum may be excluded.",
    },
    "court_closed_last_day": {
        "act": "Limitation Act, 1963",
        "section": "Section 4",
        "effect": "If the prescribed period ends on court holiday, filing on reopening day may be saved.",
    },
}

GLOBAL_DRAFTING_RULES = {
    "real_relief_controls": (
        "Document selection must follow the real substantive relief, not merely a label in the facts."
    ),
    "forum_first": (
        "Before drafting, always screen forum bar, arbitration clause, special statute, pecuniary jurisdiction, and territorial jurisdiction."
    ),
    "commercial_screen": (
        "Commercial format applies only where both subject matter and specified value requirements are satisfied."
    ),
    "rent_screen": (
        "Landlord-tenant disputes must be screened against special rent / tenancy regime before ordinary civil suit drafting."
    ),
    "section_80_screen": (
        "If the defendant is Government or public officer in official capacity, screen Section 80 CPC notice."
    ),
    "interest_screen": (
        "Separate pre-suit interest, pendente lite interest, and future interest. Plead Section 34 CPC where applicable."
    ),
    "consequential_relief_screen": (
        "For declaration suits, screen whether further relief is available and therefore mandatory."
    ),
}

SPECIAL_MODULE_RECOMMENDATIONS = {
    "family_litigation": "Keep in separate family / matrimonial drafting base.",
    "probate_succession": "Keep in separate succession / probate drafting base.",
    "consumer": "Keep in separate consumer forum drafting base.",
    "ma_ct": "Keep in separate MACT / tribunal drafting base.",
    "criminal": "Keep in separate criminal drafting base.",
    "company_nclt": "Keep in separate company / insolvency drafting base.",
}


# ============================================================================
# LOW-LEVEL HELPERS
# ============================================================================

def _civil_court_rules() -> dict:
    return {
        "default": {
            "court": "District Court / Civil Court of competent jurisdiction",
            "format": "O.S. No.",
            "heading": "IN THE COURT OF THE {court_type}",
        }
    }


def _civil_and_commercial_rules(
    *,
    nature_keywords: Optional[List[str]] = None,
    extra_procedural: Optional[List[str]] = None,
) -> dict:
    procedural = [
        "Screen whether the dispute is a commercial dispute under the Commercial Courts Act, 2015",
        "If commercial and specified value is not less than ₹3 lakh, use Commercial Court format",
        "Section 12A pre-institution mediation mandatory unless urgent interim relief is genuinely sought",
        "Statement of truth as per Order VI Rule 15A / Appendix-I for commercial disputes",
    ]
    if extra_procedural:
        procedural.extend(extra_procedural)

    return {
        "default": _civil_court_rules()["default"],
        "commercial": {
            "threshold": COMMERCIAL_THRESHOLD,
            "court": "Commercial Court",
            "format": "Commercial Suit No.",
            "heading": "IN THE COURT OF THE {court_type} (COMMERCIAL DIVISION)",
            "act": "Commercial Courts Act, 2015",
            "procedural": procedural,
            "nature_keywords": nature_keywords or [],
        },
    }


def _entry(
    *,
    registry_kind: str,
    code: str,
    display_name: str,
    stage: Optional[str] = None,
    primary_acts: Optional[List[dict]] = None,
    alternative_acts: Optional[List[dict] | dict] = None,
    limitation: Optional[dict] = None,
    court_rules: Optional[dict] = None,
    required_sections: Optional[List[str]] = None,
    required_reliefs: Optional[List[str]] = None,
    required_averments: Optional[List[str]] = None,
    optional_reliefs: Optional[List[str]] = None,
    procedural_prerequisites: Optional[List[str]] = None,
    doc_type_keywords: Optional[List[str]] = None,
    classification_hints: Optional[List[str]] = None,
    permitted_doctrines: Optional[List[str] | dict] = None,
    excluded_doctrines: Optional[List[str] | dict] = None,
    damages_categories: Optional[List[str]] = None,
    interest_basis: str = "not_applicable",
    interest_guidance: str = "",
    coa_type: str = "single_event",
    coa_guidance: str = "",
    facts_must_cover: Optional[List[str]] = None,
    evidence_checklist: Optional[List[str]] = None,
    mandatory_averments: Optional[List[Any]] = None,
    mandatory_inline_sections: Optional[List[dict]] = None,
    drafting_red_flags: Optional[List[str]] = None,
    complexity_weight: int = 2,
    notes: Optional[List[str]] = None,
) -> dict:
    return {
        "registry_kind": registry_kind,
        "code": code,
        "display_name": display_name,
        "stage": stage,
        "primary_acts": primary_acts or [],
        "alternative_acts": alternative_acts or [],
        "limitation": limitation or {},
        "court_rules": deepcopy(court_rules or _civil_court_rules()),
        "required_sections": required_sections or [],
        "required_reliefs": required_reliefs or [],
        "required_averments": required_averments or [],
        "optional_reliefs": optional_reliefs or [],
        "procedural_prerequisites": procedural_prerequisites or [],
        "doc_type_keywords": doc_type_keywords or [],
        "classification_hints": classification_hints or [],
        "permitted_doctrines": permitted_doctrines or [],
        "excluded_doctrines": excluded_doctrines or [],
        "damages_categories": damages_categories or [],
        "interest_basis": interest_basis,
        "interest_guidance": interest_guidance,
        "coa_type": coa_type,
        "coa_guidance": coa_guidance,
        "facts_must_cover": facts_must_cover or [],
        "evidence_checklist": evidence_checklist or [],
        "mandatory_averments": mandatory_averments or [],
        "mandatory_inline_sections": mandatory_inline_sections or [],
        "drafting_red_flags": drafting_red_flags or [],
        "complexity_weight": complexity_weight,
        "notes": notes or [],
    }


# ============================================================================
# DRAFT FAMILY REGISTRY
# ============================================================================

DRAFT_FAMILIES: Dict[str, dict] = {

    "plaint": _entry(
        registry_kind="draft_family",
        code="plaint",
        display_name="Plaint / suit instituting pleading",
        stage="institution",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 26", "Order VII Rule 1"]},
        ],
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS,
        required_averments=COMMON_REQUIRED_AVERMENTS,
        procedural_prerequisites=[
            "forum_screen",
            "pecuniary_jurisdiction_screen",
            "territorial_jurisdiction_screen",
            "limitation_screen",
            "court_fee_screen",
            "arbitration_screen",
            "special_forum_bar_screen",
        ],
        doc_type_keywords=["plaint", "suit", "civil suit", "original suit"],
        classification_hints=["Use when the draft institutes an ordinary civil action."],
        complexity_weight=1,
    ),

    "written_statement": _entry(
        registry_kind="draft_family",
        code="written_statement",
        display_name="Written Statement",
        stage="pleadings",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order VIII Rule 1", "Order VIII Rule 2", "Order VIII Rule 3"]},
        ],
        required_sections=COMMON_WRITTEN_STATEMENT_SECTIONS,
        doc_type_keywords=["written statement", "ws", "defence", "reply to plaint"],
        classification_hints=["Use for defendant's pleading answering a plaint."],
        procedural_prerequisites=["timeline_screen_for_ws", "admission_denial_screen"],
        complexity_weight=1,
    ),

    "set_off": _entry(
        registry_kind="draft_family",
        code="set_off",
        display_name="Set-off in Written Statement",
        stage="pleadings",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order VIII Rule 6"]},
        ],
        required_sections=COMMON_WRITTEN_STATEMENT_SECTIONS + ["set_off_particulars"],
        doc_type_keywords=["set off", "set-off", "adjustment claim"],
        classification_hints=["Use where defendant seeks an ascertained sum recoverable from plaintiff."],
        complexity_weight=2,
    ),

    "counter_claim": _entry(
        registry_kind="draft_family",
        code="counter_claim",
        display_name="Counter-claim",
        stage="pleadings",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order VIII Rule 6A", "Order VIII Rule 6B"]},
        ],
        required_sections=COMMON_WRITTEN_STATEMENT_SECTIONS + ["counter_claim_facts", "counter_claim_prayer"],
        doc_type_keywords=["counter claim", "counter-claim"],
        classification_hints=["Use where defendant asserts an independent claim against plaintiff in same suit."],
        complexity_weight=2,
    ),

    "replication": _entry(
        registry_kind="draft_family",
        code="replication",
        display_name="Replication / Rejoinder to Written Statement",
        stage="pleadings",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order VIII", "Court practice"]},
        ],
        required_sections=[
            "court_heading", "title", "parties", "reply_to_preliminary_objections",
            "reply_to_new_facts", "affirmation_of_plaint", "prayer", "verification",
        ],
        doc_type_keywords=["replication", "rejoinder"],
        classification_hints=["Use only when leave / practice requires response to new facts or counterclaim."],
        complexity_weight=1,
    ),

    "interim_application_temp_injunction": _entry(
        registry_kind="draft_family",
        code="interim_application_temp_injunction",
        display_name="Interim Application for Temporary Injunction",
        stage="interim_relief",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XXXIX Rule 1", "Order XXXIX Rule 2"]},
        ],
        required_sections=COMMON_IA_SECTIONS + ["prima_facie_case", "balance_of_convenience", "irreparable_injury"],
        doc_type_keywords=["temporary injunction", "interim injunction", "order 39", "status quo"],
        complexity_weight=2,
    ),

    "interim_application_mandatory_injunction": _entry(
        registry_kind="draft_family",
        code="interim_application_mandatory_injunction",
        display_name="Interim Mandatory Injunction Application",
        stage="interim_relief",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XXXIX"]},
            {"act": "Specific Relief Act, 1963", "sections": ["Section 39"]},
        ],
        required_sections=COMMON_IA_SECTIONS + ["exceptional_circumstances", "urgent_restoration_basis"],
        doc_type_keywords=["interim mandatory injunction", "restore status quo ante"],
        complexity_weight=3,
    ),

    "interim_application_receiver": _entry(
        registry_kind="draft_family",
        code="interim_application_receiver",
        display_name="Application for Appointment of Receiver",
        stage="interim_relief",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XL Rule 1"]},
        ],
        required_sections=COMMON_IA_SECTIONS + ["receiver_necessity", "property_risk", "management_failure"],
        doc_type_keywords=["receiver", "order 40"],
        complexity_weight=3,
    ),

    "interim_application_commissioner": _entry(
        registry_kind="draft_family",
        code="interim_application_commissioner",
        display_name="Application for Commission / Local Inspection",
        stage="interim_relief",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XXVI"]},
        ],
        required_sections=COMMON_IA_SECTIONS + ["purpose_of_commission", "issues_to_be_elucidated"],
        doc_type_keywords=["commissioner", "local inspection", "survey commission", "order 26"],
        complexity_weight=2,
    ),

    "interim_application_attachment_before_judgment": _entry(
        registry_kind="draft_family",
        code="interim_application_attachment_before_judgment",
        display_name="Application for Attachment Before Judgment",
        stage="interim_relief",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XXXVIII Rule 5"]},
        ],
        required_sections=COMMON_IA_SECTIONS + ["defendant_intent_to_obstruct_execution", "property_details"],
        doc_type_keywords=["attachment before judgment", "order 38 rule 5"],
        complexity_weight=3,
    ),

    "interim_application_security_for_costs": _entry(
        registry_kind="draft_family",
        code="interim_application_security_for_costs",
        display_name="Application for Security for Costs",
        stage="interim_relief",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XXV"]},
        ],
        required_sections=COMMON_IA_SECTIONS + ["basis_for_security"],
        doc_type_keywords=["security for costs", "order 25"],
        complexity_weight=2,
    ),

    "application_condonation_delay": _entry(
        registry_kind="draft_family",
        code="application_condonation_delay",
        display_name="Application for Condonation of Delay",
        stage="institution",
        primary_acts=[
            {"act": "Limitation Act, 1963", "sections": ["Section 5"]},
        ],
        required_sections=[
            "court_heading", "title", "delay_period", "sufficient_cause_facts", "grounds", "prayer", "affidavit_support",
        ],
        doc_type_keywords=["condonation of delay", "delay petition", "section 5 limitation"],
        complexity_weight=2,
    ),

    "application_amendment_pleadings": _entry(
        registry_kind="draft_family",
        code="application_amendment_pleadings",
        display_name="Application for Amendment of Pleadings",
        stage="pleadings",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order VI Rule 17"]},
        ],
        required_sections=[
            "court_heading", "title", "existing_pleading_reference", "proposed_amendments",
            "necessity_for_amendment", "due_diligence_if_post_trial", "prayer", "affidavit_support",
        ],
        doc_type_keywords=["amendment", "order 6 rule 17"],
        complexity_weight=2,
    ),

    "application_impleadment": _entry(
        registry_kind="draft_family",
        code="application_impleadment",
        display_name="Application for Impleadment / Addition of Parties",
        stage="pleadings",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order I Rule 10"]},
        ],
        required_sections=[
            "court_heading", "title", "party_to_be_added", "necessity_or_propriety", "grounds", "prayer", "affidavit_support",
        ],
        doc_type_keywords=["impleadment", "order 1 rule 10", "add party"],
        complexity_weight=2,
    ),

    "application_rejection_plaint": _entry(
        registry_kind="draft_family",
        code="application_rejection_plaint",
        display_name="Application for Rejection of Plaint",
        stage="pleadings",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order VII Rule 11"]},
        ],
        required_sections=[
            "court_heading", "title", "ground_for_rejection", "analysis_of_plaint_allegations_only", "prayer",
        ],
        doc_type_keywords=["rejection of plaint", "order 7 rule 11"],
        complexity_weight=2,
    ),

    "application_return_plaint": _entry(
        registry_kind="draft_family",
        code="application_return_plaint",
        display_name="Application for Return of Plaint",
        stage="institution",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order VII Rule 10"]},
        ],
        required_sections=[
            "court_heading", "title", "jurisdiction_defect", "proper_forum_basis", "prayer",
        ],
        doc_type_keywords=["return of plaint", "order 7 rule 10"],
        complexity_weight=2,
    ),

    "application_restore_suit": _entry(
        registry_kind="draft_family",
        code="application_restore_suit",
        display_name="Application to Restore Suit Dismissed for Default",
        stage="post_decree_or_restoration",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order IX Rule 9"]},
        ],
        required_sections=[
            "court_heading", "title", "dismissal_details", "sufficient_cause", "prayer", "affidavit_support",
        ],
        doc_type_keywords=["restore suit", "order 9 rule 9", "dismissed for default"],
        complexity_weight=2,
    ),

    "application_set_aside_ex_parte": _entry(
        registry_kind="draft_family",
        code="application_set_aside_ex_parte",
        display_name="Application to Set Aside Ex Parte Decree",
        stage="post_decree_or_restoration",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order IX Rule 13"]},
        ],
        required_sections=[
            "court_heading", "title", "decree_details", "non_service_or_sufficient_cause", "prayer", "affidavit_support",
        ],
        doc_type_keywords=["set aside ex parte", "order 9 rule 13"],
        complexity_weight=2,
    ),

    "affidavit": _entry(
        registry_kind="draft_family",
        code="affidavit",
        display_name="Supporting Affidavit",
        stage="supporting_document",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XIX"]},
        ],
        required_sections=["deponent_details", "facts_by_paragraph", "verification", "attestation"],
        doc_type_keywords=["affidavit", "sworn statement"],
        complexity_weight=1,
    ),

    "chief_examination_affidavit": _entry(
        registry_kind="draft_family",
        code="chief_examination_affidavit",
        display_name="Affidavit in Lieu of Chief Examination",
        stage="evidence",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XVIII Rule 4"]},
        ],
        required_sections=["witness_identity", "facts_in_chief", "exhibits_reference", "verification"],
        doc_type_keywords=["chief examination affidavit", "evidence affidavit"],
        complexity_weight=2,
    ),

    "list_of_documents": _entry(
        registry_kind="draft_family",
        code="list_of_documents",
        display_name="List / Memo of Documents",
        stage="pleadings",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order VII Rule 14", "Order VIII Rule 1A"]},
        ],
        required_sections=["court_heading", "title", "document_table", "prayer_or_filing_note"],
        doc_type_keywords=["list of documents", "memo of documents"],
        complexity_weight=1,
    ),

    "interrogatories_discovery_inspection": _entry(
        registry_kind="draft_family",
        code="interrogatories_discovery_inspection",
        display_name="Discovery / Interrogatories / Inspection Application",
        stage="discovery",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XI"]},
        ],
        required_sections=[
            "court_heading", "title", "issues_requiring_discovery", "questions_or_document_classes", "relevance", "prayer",
        ],
        doc_type_keywords=["interrogatories", "discovery", "inspection", "order 11"],
        complexity_weight=2,
    ),

    "appeal_first": _entry(
        registry_kind="draft_family",
        code="appeal_first",
        display_name="Regular First Appeal / First Appeal from Original Decree",
        stage="appeal",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 96", "Order XLI"]},
        ],
        required_sections=[
            "appellate_heading", "cause_title", "impugned_judgment_and_decree_details",
            "facts", "grounds_of_appeal", "limitation", "valuation_if_required", "prayer",
        ],
        doc_type_keywords=["first appeal", "regular first appeal", "section 96", "order 41"],
        complexity_weight=3,
    ),

    "appeal_second": _entry(
        registry_kind="draft_family",
        code="appeal_second",
        display_name="Second Appeal",
        stage="appeal",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 100"]},
        ],
        required_sections=[
            "appellate_heading", "cause_title", "impugned_judgments_details",
            "substantial_question_of_law", "grounds", "limitation", "prayer",
        ],
        doc_type_keywords=["second appeal", "section 100"],
        complexity_weight=4,
    ),

    "appeal_commercial": _entry(
        registry_kind="draft_family",
        code="appeal_commercial",
        display_name="Commercial Appeal",
        stage="appeal",
        primary_acts=[
            {"act": "Commercial Courts Act, 2015", "sections": ["Section 13"]},
        ],
        required_sections=[
            "appellate_heading", "cause_title", "impugned_order_details",
            "commercial_maintainability", "grounds", "limitation", "prayer",
        ],
        doc_type_keywords=["commercial appeal", "section 13 commercial courts"],
        complexity_weight=3,
    ),

    "stay_application": _entry(
        registry_kind="draft_family",
        code="stay_application",
        display_name="Stay Application in Appeal / Proceedings",
        stage="appeal",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XLI Rule 5"]},
        ],
        required_sections=["court_heading", "title", "impugned_decree_or_order", "stay_grounds", "irreparable_prejudice", "prayer"],
        doc_type_keywords=["stay application", "order 41 rule 5"],
        complexity_weight=2,
    ),

    "review_petition": _entry(
        registry_kind="draft_family",
        code="review_petition",
        display_name="Review Petition",
        stage="review_revision",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 114", "Order XLVII Rule 1"]},
        ],
        required_sections=["court_heading", "title", "impugned_order", "error_apparent_or_new_matter", "grounds", "prayer"],
        doc_type_keywords=["review", "order 47"],
        complexity_weight=2,
    ),

    "revision_support": _entry(
        registry_kind="draft_family",
        code="revision_support",
        display_name="Revision Support Drafting Skeleton",
        stage="review_revision",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 115"]},
        ],
        required_sections=["revisional_heading", "jurisdictional_error", "grounds", "prayer"],
        doc_type_keywords=["revision", "section 115"],
        complexity_weight=3,
        notes=["High Court rules and local practice may require separate formatting adapter."],
    ),

    "execution_petition": _entry(
        registry_kind="draft_family",
        code="execution_petition",
        display_name="Execution Petition",
        stage="post_decree_execution",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XXI", "Section 38"]},
        ],
        required_sections=[
            "executing_court_heading", "decree_details", "parties", "execution_mode_sought",
            "amount_due_or_relief_due", "property_details_if_any", "prayer",
        ],
        doc_type_keywords=["execution petition", "ep", "order 21"],
        complexity_weight=3,
    ),

    "execution_objection": _entry(
        registry_kind="draft_family",
        code="execution_objection",
        display_name="Objections in Execution",
        stage="post_decree_execution",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 47", "Order XXI"]},
        ],
        required_sections=[
            "executing_court_heading", "decree_details", "objection_facts", "legal_objections", "prayer",
        ],
        doc_type_keywords=["execution objection", "section 47", "order 21 objection"],
        complexity_weight=3,
    ),

    "claim_petition_execution": _entry(
        registry_kind="draft_family",
        code="claim_petition_execution",
        display_name="Claim / Objection to Attachment in Execution",
        stage="post_decree_execution",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XXI Rule 58"]},
        ],
        required_sections=[
            "executing_court_heading", "attachment_details", "claimant_interest", "grounds", "prayer",
        ],
        doc_type_keywords=["claim petition", "order 21 rule 58", "attachment objection"],
        complexity_weight=3,
    ),

    "arrest_attachment_execution_application": _entry(
        registry_kind="draft_family",
        code="arrest_attachment_execution_application",
        display_name="Application for Arrest / Attachment in Execution",
        stage="post_decree_execution",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XXI"]},
        ],
        required_sections=[
            "executing_court_heading", "decree_details", "debtor_default", "mode_justification",
            "property_or_arrest_details", "prayer",
        ],
        doc_type_keywords=["attachment in execution", "arrest in execution"],
        complexity_weight=3,
    ),

    "caveat": _entry(
        registry_kind="draft_family",
        code="caveat",
        display_name="Caveat Petition",
        stage="pre_suit",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 148A"]},
        ],
        required_sections=["court_heading", "caveator_details", "expected_proceeding", "adverse_party_details", "prayer"],
        doc_type_keywords=["caveat", "section 148a"],
        complexity_weight=1,
    ),

    "compromise_petition": _entry(
        registry_kind="draft_family",
        code="compromise_petition",
        display_name="Compromise Petition / Memo of Settlement",
        stage="judgment_decree",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XXIII Rule 3"]},
        ],
        required_sections=["court_heading", "title", "settlement_terms", "lawfulness_statement", "prayer", "signatures"],
        doc_type_keywords=["compromise petition", "settlement memo", "order 23 rule 3"],
        complexity_weight=2,
    ),

    "memo_for_withdrawal": _entry(
        registry_kind="draft_family",
        code="memo_for_withdrawal",
        display_name="Memo / Application for Withdrawal of Suit",
        stage="judgment_decree",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XXIII Rule 1"]},
        ],
        required_sections=["court_heading", "title", "withdrawal_basis", "liberty_if_sought", "prayer"],
        doc_type_keywords=["withdrawal", "order 23 rule 1"],
        complexity_weight=1,
    ),

    "decree_drafting_support": _entry(
        registry_kind="draft_family",
        code="decree_drafting_support",
        display_name="Judgment / Decree Drafting Support Metadata",
        stage="judgment_decree",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XX"]},
        ],
        required_sections=["operative_reliefs", "costs_direction", "interest_direction", "schedule_reference"],
        doc_type_keywords=["decree", "judgment operative portion"],
        complexity_weight=2,
    ),
}


# ============================================================================
# SUBSTANTIVE CAUSE REGISTRY
# ============================================================================

SUBSTANTIVE_CAUSES: Dict[str, dict] = {

    # ------------------------------------------------------------------
    # MONEY / ACCOUNT / MOVABLE PROPERTY
    # ------------------------------------------------------------------

    "money_recovery_loan": _entry(
        registry_kind="cause",
        code="money_recovery_loan",
        display_name="Recovery of money lent / advance paid",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 73"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 34"]},
        ],
        limitation={
            "_type": "conditional",
            "_resolve_by": "loan_character",
            "_rules": [
                {"when": "simple_loan", "then": {"article": "19", "period": "Three years", "from": "When loan is made"}},
                {"when": "lender_gave_cheque", "then": {"article": "20", "period": "Three years", "from": "When the cheque is paid"}},
                {"when": "payable_on_demand_under_agreement", "then": {"article": "19", "period": "Three years", "from": "When the loan is made"}},
            ],
            "_default": {"article": "19", "period": "Three years", "from": "When loan is made"},
        },
        court_rules=_civil_and_commercial_rules(
            nature_keywords=["business", "company", "firm", "trade", "commercial", "vendor", "supply"]
        ),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["transaction_details", "demands_and_notice", "interest"],
        required_reliefs=["money_decree", "interest_pendente_lite_future", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["transaction_basis"],
        doc_type_keywords=["loan", "hand loan", "advance", "money recovery", "bank transfer"],
        permitted_doctrines=["restitution_s65", "non_gratuitous_act_s70", "money_had_and_received_type_recovery"],
        damages_categories=["principal_amount", "interest"],
        interest_basis="wrongful_retention_of_money",
        interest_guidance="Plead agreed rate if any; otherwise reasonable pre-suit rate and Section 34 CPC thereafter.",
        coa_type="continuing",
        coa_guidance="Money remains unpaid after due date or demand.",
        evidence_checklist=["bank transfer proof", "admission messages", "legal notice", "acknowledgment / part-payment"],
        complexity_weight=1,
    ),

    "money_recovery_goods": _entry(
        registry_kind="cause",
        code="money_recovery_goods",
        display_name="Recovery of price of goods sold and delivered",
        primary_acts=[
            {"act": "Sale of Goods Act, 1930", "sections": ["Section 55"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 34"]},
        ],
        alternative_acts=[{"act": "Sale of Goods Act, 1930", "sections": ["Section 56"]}],
        limitation={
            "_type": "conditional",
            "_resolve_by": "credit_period_status",
            "_rules": [
                {"when": "fixed_credit_period", "then": {"article": "15", "period": "Three years", "from": "When period of credit expires"}},
                {"when": "no_fixed_credit_period", "then": {"article": "14", "period": "Three years", "from": "Date of delivery"}},
            ],
            "_default": {"article": "14", "period": "Three years", "from": "Date of delivery"},
        },
        court_rules=_civil_and_commercial_rules(),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "supply_and_delivery_details", "invoice_details", "ledger_and_outstanding", "interest",
        ],
        required_reliefs=["money_decree", "interest_pendente_lite_future", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["delivery_acceptance_basis"],
        doc_type_keywords=["goods sold", "delivered", "invoice", "supply", "price of goods"],
        permitted_doctrines=["price_recovery_soga", "account_stated", "quantum_meruit"],
        damages_categories=["price_of_goods", "interest_on_price"],
        interest_basis="wrongful_retention_of_money",
        interest_guidance="Use invoice / trade usage rate if provable; otherwise Section 34 CPC.",
        coa_type="continuing",
        coa_guidance="Price remains due and unpaid after delivery and demand; each day of non-payment keeps cause of action alive.",
        evidence_checklist=["purchase order", "delivery challan", "invoice", "ledger", "tax invoice"],
        complexity_weight=1,
    ),

    "failure_of_consideration": _entry(
        registry_kind="cause",
        code="failure_of_consideration",
        display_name="Recovery of advance paid on failure of consideration",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 65"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 34"]},
        ],
        alternative_acts=[{"act": "Indian Contract Act, 1872", "sections": ["Section 70", "Section 72", "Section 73"]}],
        limitation={"article": "47", "period": "Three years", "from": "When the consideration fails"},
        court_rules=_civil_and_commercial_rules(
            nature_keywords=["commercial", "franchise", "dealership", "construction", "supply"]
        ),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["payment_and_purpose", "failure_event", "demands_and_notice", "interest"],
        required_reliefs=["money_decree", "interest_pendente_lite_future", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["failure_date"],
        doc_type_keywords=["advance refund", "failure of consideration", "void agreement refund"],
        permitted_doctrines=["restitution_s65", "money_had_and_received", "failure_of_consideration_common_law", "unjust_enrichment_s70"],
        damages_categories=["advance_amount", "interest"],
        interest_basis="wrongful_retention_of_money",
        interest_guidance="Plead interest from date of failure of consideration at reasonable rate (wrongful retention basis); Section 34 CPC for pendente lite and future interest.",
        coa_type="single_accrual",
        coa_guidance="Cause of action accrues on the date the consideration fails and refund is refused or demanded.",
        evidence_checklist=["payment proof", "agreement", "failure proof", "legal notice"],
        complexity_weight=1,
    ),

    "deposit_refund": _entry(
        registry_kind="cause",
        code="deposit_refund",
        display_name="Recovery of security deposit / earnest money / refundable deposit",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 73", "Section 74"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 34"]},
        ],
        alternative_acts=[{"act": "Indian Contract Act, 1872", "sections": ["Section 65"]}],
        limitation={
            "_type": "conditional",
            "_resolve_by": "deposit_refund_trigger",
            "_rules": [
                {"when": "payable_on_demand", "then": {"article": "22", "period": "Three years", "from": "When demand is made"}},
                {"when": "event_triggered_refund", "then": {"article": "55", "period": "Three years", "from": "When the contract to refund is broken (typically when refund is refused after the triggering event)"}},
            ],
            "_default": {"article": "22", "period": "Three years", "from": "When demand is made"},
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["deposit_details", "refund_trigger", "demand_and_refusal", "interest"],
        required_reliefs=["money_decree", "interest_pendente_lite_future", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["demand_date"],
        doc_type_keywords=["deposit refund", "security deposit", "earnest money refund"],
        permitted_doctrines=["unjust_enrichment", "section_65_restitution", "wrongful_retention"],
        damages_categories=["deposit_amount", "interest"],
        interest_basis="wrongful_retention_of_money",
        interest_guidance="Interest runs from date of demand for refund or date refund was due under the agreement; Section 34 CPC for future interest.",
        coa_type="single_accrual",
        coa_guidance="Cause of action accrues when the refund-triggering event occurs and defendant refuses or fails to refund on demand.",
        evidence_checklist=["receipt / deposit proof", "agreement clause", "refund notice"],
        complexity_weight=1,
    ),

    "summary_suit_instrument": _entry(
        registry_kind="cause",
        code="summary_suit_instrument",
        display_name="Summary suit on negotiable instrument / written contract",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XXXVII"]},
            {"act": "Negotiable Instruments Act, 1881", "sections": ["Section 30", "Section 32", "Section 118"]},
        ],
        limitation={
            "_type": "conditional",
            "_resolve_by": "instrument_type",
            "_rules": [
                {"when": "cheque", "then": {"article": "35", "period": "Three years", "from": "When the cheque is presented for payment and payment is refused (date of dishonour)"}},
                {"when": "promissory_note_payable_on_demand", "then": {"article": "35", "period": "Three years", "from": "When the note is presented for payment"}},
                {"when": "bill_of_exchange_payable_on_demand", "then": {"article": "35", "period": "Three years", "from": "When the bill is presented for payment"}},
            ],
            "_default": {"article": "35", "period": "Three years", "from": "When the instrument is presented for payment and payment is refused"},
        },
        court_rules=_civil_and_commercial_rules(
            nature_keywords=["business", "firm", "company", "commercial", "trade"]
        ),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "order_37_maintainability", "instrument_details", "default_or_dishonour", "interest",
        ],
        required_reliefs=["money_decree", "interest_pendente_lite_future", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["order_37_basis"],
        doc_type_keywords=["order 37", "summary suit", "promissory note", "cheque", "bill of exchange"],
        permitted_doctrines=["summary_procedure_order_37"],
        damages_categories=["instrument_amount", "interest_on_instrument", "costs_of_dishonour"],
        interest_basis="instrument_liability",
        interest_guidance="Plead interest from date of instrument / dishonour at the rate endorsed on the instrument or at a reasonable commercial rate; Section 34 CPC for future interest.",
        coa_type="single_accrual",
        coa_guidance="Cause of action accrues on the date the instrument matures, is dishonoured, or becomes payable on demand and payment is refused.",
        evidence_checklist=["instrument original", "dishonour memo if any", "underlying debt proof"],
        complexity_weight=2,
    ),

    "rendition_of_accounts": _entry(
        registry_kind="cause",
        code="rendition_of_accounts",
        display_name="Suit for rendition of accounts",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 213", "Section 214"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 34"]},
        ],
        limitation={"article": "113", "period": "Three years", "from": "When the right to demand accounts arises and is refused (typically on termination of fiduciary/agency relationship, or on demand and refusal)"},
        court_rules=_civil_and_commercial_rules(
            nature_keywords=["agency", "fiduciary", "business", "commercial", "accounts"]
        ),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["relationship_basis", "duty_to_account", "accounts_not_rendered"],
        required_reliefs=["rendition_of_accounts", "money_found_due_after_accounts", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["basis_for_accounting_duty"],
        doc_type_keywords=["rendition of accounts", "accounts", "accounting"],
        permitted_doctrines=["fiduciary_accounting", "agency_accounting"],
        damages_categories=["balance_found_due_after_accounts", "interest_on_balance"],
        interest_basis="balance_found_due_on_accounting",
        interest_guidance="Interest on the balance found due runs from date accounts were due or demand was made; quantified only after accounts are taken.",
        coa_type="single_accrual",
        coa_guidance="Cause of action accrues when the fiduciary or agent has received monies and refuses or fails to render accounts after demand.",
        evidence_checklist=["agreement", "ledger access requests", "demand notices"],
        complexity_weight=3,
    ),

    "recovery_specific_movable": _entry(
        registry_kind="cause",
        code="recovery_specific_movable",
        display_name="Recovery of specific movable property",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 7", "Section 8"]},
        ],
        limitation={
            "_type": "conditional",
            "_resolve_by": "movable_acquisition",
            "_rules": [
                {"when": "lost_stolen_converted", "then": {"article": "69", "period": "Three years", "from": "When the plaintiff first learns in whose possession the property is (discovery rule for stolen/lost goods)"}},
                {"when": "other_wrongful_taking", "then": {"article": "69", "period": "Three years", "from": "When property is wrongfully taken"}},
            ],
            "_default": {"article": "69", "period": "Three years", "from": "When property is wrongfully taken"},
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["movable_description", "plaintiff_entitlement", "wrongful_detention"],
        required_reliefs=["delivery_of_specific_movable", "damages_or_detention_charges_if_claimed", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["movable_identification"],
        doc_type_keywords=["movable property recovery", "return articles", "specific movable"],
        permitted_doctrines=["specific_recovery_movable_s7_s8"],
        damages_categories=["market_value_if_unrecoverable", "detention_charges", "costs"],
        interest_basis="wrongful_detention_of_property",
        interest_guidance="Plead detention charges or use and occupation charges from date of wrongful taking; if property cannot be recovered, market value as of date of conversion with interest under Section 34 CPC.",
        coa_type="continuing",
        coa_guidance="Wrongful detention continues until property is returned; cause of action accrues when property is wrongfully taken or withheld after demand.",
        evidence_checklist=["invoice / ownership proof", "serial number details", "demand for return"],
        complexity_weight=2,
    ),

    # ------------------------------------------------------------------
    # CONTRACT / COMMERCIAL
    # ------------------------------------------------------------------

    "breach_of_contract": _entry(
        registry_kind="cause",
        code="breach_of_contract",
        display_name="Damages for breach of contract",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 37", "Section 39", "Section 55", "Section 73", "Section 74"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 34"]},
        ],
        limitation={"article": "55", "period": "Three years", "from": "When contract is broken; or, for a continuing breach, when it ceases"},
        court_rules=_civil_and_commercial_rules(
            nature_keywords=["business", "commercial", "trade", "supply", "vendor", "franchise", "construction"],
            extra_procedural=["Particularised damages schedule with computation methodology"],
        ),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["contract_details", "breach_particulars", "loss_and_damage", "interest"],
        required_reliefs=["damages_decree", "interest_pendente_lite_future", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["breach_date"],
        doc_type_keywords=["breach of contract", "damages", "compensation"],
        permitted_doctrines=["repudiatory_breach", "time_is_essence", "damages_s73", "liquidated_damages_s74", "remoteness_hadley_v_baxendale", "duty_to_mitigate", "anticipatory_breach_s39"],
        damages_categories=["loss_of_profit", "wasted_expenditure", "consequential_loss", "diminution_in_value", "reliance_losses"],
        interest_basis="deprivation_of_money_or_benefit",
        coa_type="single_accrual",
        coa_guidance="Cause of action accrues on the date the contract is broken — actual breach or anticipatory repudiation.",
        procedural_prerequisites=["section_12a_mediation", "arbitration_clause_screen"],
        evidence_checklist=["contract", "breach letter", "loss computation", "mitigation material"],
        complexity_weight=2,
    ),

    "breach_dealership_franchise": _entry(
        registry_kind="cause",
        code="breach_dealership_franchise",
        display_name="Damages for illegal termination of dealership / franchise / agency",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 37", "Section 39", "Section 55", "Section 73", "Section 74"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 34"]},
        ],
        limitation={"article": "55", "period": "Three years", "from": "Date of illegal termination / breach"},
        court_rules=_civil_and_commercial_rules(
            extra_procedural=[
                "Detailed damages schedule for profits, goodwill, capital investment and unsold stock",
            ]
        ),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "commercial_maintainability", "section_12a", "arbitration_disclosure",
            "agreement_details", "termination_and_breach", "damages_quantum",
            "interest", "statement_of_truth",
        ],
        required_reliefs=["damages_decree", "interest_pendente_lite_future", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["termination_date", "section_12a_compliance"],
        doc_type_keywords=["dealership", "franchise", "agency termination", "distributor"],
        permitted_doctrines=["repudiatory_breach", "commercial_damages", "mitigation"],
        damages_categories=["loss_of_profit", "loss_of_goodwill", "wasted_capital", "loss_on_unsold_stock", "rendition_of_accounts_on_sub_dealers"],
        interest_basis="deprivation_of_profit_and_capital",
        interest_guidance="Plead pre-suit interest on wasted capital at contractual or commercial rate; Section 34 CPC for pendente lite and future interest on money decree.",
        coa_type="single_accrual",
        coa_guidance="Cause of action crystallises on the date of illegal / wrongful termination of the dealership / franchise / agency.",
        optional_reliefs=["declaration_of_illegal_termination", "rendition_of_accounts", "injunction_against_rival_appointment_if_exclusive"],
        procedural_prerequisites=["section_12a_mediation", "arbitration_clause_screen"],
        evidence_checklist=["agreement", "termination letter", "investment proof", "stock valuation", "sales history"],
        complexity_weight=3,
    ),

    "breach_employment": _entry(
        registry_kind="cause",
        code="breach_employment",
        display_name="Damages for breach of employment / service contract",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 73", "Section 74"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 34"]},
        ],
        limitation={"article": "55", "period": "Three years", "from": "When contract is broken"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["employment_terms", "breach_details", "loss_and_entitlements"],
        required_reliefs=["damages_decree", "interest_pendente_lite_future", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["employment_contract_basis"],
        doc_type_keywords=["employment contract", "service contract", "wrongful termination", "notice pay"],
        permitted_doctrines=["damages_for_breach_of_service_contract", "mitigation", "liquidated_damages_s74"],
        damages_categories=["loss_of_salary_unexpired_term", "notice_pay_in_lieu", "loss_of_benefits"],
        interest_basis="deprivation_of_money_or_benefit",
        interest_guidance="Interest on unpaid salary and notice pay from date of wrongful termination; Section 34 CPC for future interest.",
        coa_type="single_accrual",
        coa_guidance="Cause of action accrues on the date of wrongful termination or when the breach of service contract is communicated.",
        evidence_checklist=["appointment letter", "termination letter", "salary slips", "HR communications"],
        procedural_prerequisites=[
            "labour_forum_bar_screen",
            "industrial_disputes_act_forum_screen",
            "arbitration_clause_screen",
        ],
        drafting_red_flags=[
            "Specific performance of personal service contracts is ordinarily unavailable in private employment disputes.",
            "Screen labour / industrial dispute forum issues before civil suit drafting.",
            "Section 12A Commercial Courts Act pre-institution mediation applies if the employment dispute is commercial in nature and value exceeds Rs. 3 lakh.",
        ],
        complexity_weight=2,
    ),

    "breach_construction": _entry(
        registry_kind="cause",
        code="breach_construction",
        display_name="Damages for breach of construction / development agreement",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 55", "Section 73", "Section 74"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 34"]},
        ],
        limitation={"article": "55", "period": "Three years", "from": "When contract is broken"},
        court_rules=_civil_and_commercial_rules(
            nature_keywords=["construction", "developer", "builder", "joint development"]
        ),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "agreement_details", "construction_status", "breach_details", "loss_quantification", "interest",
        ],
        required_reliefs=["damages_decree", "interest_pendente_lite_future", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["breach_date"],
        doc_type_keywords=["construction", "development agreement", "builder breach", "delay"],
        permitted_doctrines=["time_is_essence", "damages_s73", "liquidated_damages_s74", "mitigation", "independent_contractor_rule"],
        damages_categories=["cost_of_completion_or_rectification", "delay_damages_loss_of_use", "advance_paid_unrecovered", "consequential_loss", "loss_of_rent_or_business_profit", "professional_fees_for_reassessment"],
        interest_basis="deprivation_of_money_or_benefit",
        interest_guidance="Interest on advances paid and on ascertained loss from date of breach; Section 34 CPC for pendente lite and future interest.",
        coa_type="single_accrual",
        coa_guidance="Cause of action accrues on the date the construction agreement is broken — typically on contractor's abandonment, delay beyond time-is-essence date, or defective completion.",
        procedural_prerequisites=["section_12a_mediation", "arbitration_clause_screen", "rera_forum_screen", "consumer_forum_screen_if_residential_unit"],
        drafting_red_flags=[
            "If the construction is of a residential flat/apartment, screen RERA (Real Estate (Regulation and Development) Act, 2016) before civil suit drafting — RERA adjudicator has primary jurisdiction.",
            "Consumer Forum has concurrent jurisdiction for residential unit disputes — advise client on choice of forum.",
            "Arbitration clause in construction agreements is common — screen carefully; court may refer under Section 8 Arbitration and Conciliation Act, 1996.",
        ],
        evidence_checklist=["agreement", "payment schedule", "site photos", "engineer estimate", "notices"],
        complexity_weight=2,
    ),

    "guarantee_indemnity_recovery": _entry(
        registry_kind="cause",
        code="guarantee_indemnity_recovery",
        display_name="Recovery under indemnity / guarantee",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 124", "Section 125", "Section 126", "Section 128", "Section 129", "Section 145"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 34"]},
        ],
        limitation={
            "_type": "conditional",
            "_resolve_by": "guarantee_or_indemnity_type",
            "_rules": [
                {"when": "indemnity", "then": {"article": "25", "period": "Three years", "from": "When the plaintiff is damnified (i.e., when the indemnified party suffers actual loss or makes actual payment)"}},
                {"when": "guarantee", "then": {"article": "43", "period": "Three years", "from": "When the money guaranteed becomes payable (i.e., on default of the principal debtor)"}},
            ],
            "_default": {"article": "43", "period": "Three years", "from": "When the money guaranteed becomes payable on default of the principal debtor"},
        },
        court_rules=_civil_and_commercial_rules(
            nature_keywords=["business", "commercial", "guarantee", "indemnity"]
        ),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["guarantee_or_indemnity_terms", "default_and_trigger", "payment_or_loss", "interest"],
        required_reliefs=["money_decree", "interest_pendente_lite_future", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["trigger_event"],
        doc_type_keywords=["guarantee recovery", "indemnity recovery", "surety"],
        permitted_doctrines=[
            "co_extensive_liability_of_surety_s128",
            "indemnity_recovery",
            "continuing_guarantee_s129",
            "discharge_of_surety_s133_to_s139",
            "right_of_subrogation_s140",
            "right_of_contribution_among_co_sureties_s146",
        ],
        damages_categories=[
            "principal_debt_or_guaranteed_sum",
            "interest_paid_on_principal_debt",
            "costs_and_expenses_incurred_in_enforcing_principal_debt",
            "indemnity_amount_actually_paid",
            "consequential_losses_within_indemnity_terms",
        ],
        interest_basis="wrongful_retention_of_money_or_reimbursement_due",
        interest_guidance="Plead interest from date of payment by indemnified party or from date surety met the guarantee call; use contractual rate if specified, otherwise reasonable commercial rate; Section 34 CPC for future interest.",
        coa_type="single_accrual",
        coa_guidance="For guarantee: cause of action accrues on the principal debtor's default and the surety's failure to pay on demand; for indemnity: on the date the indemnified party suffers the loss and makes demand.",
        evidence_checklist=["guarantee / indemnity document", "principal default proof", "payment proof"],
        complexity_weight=2,
    ),

    "agency_dispute": _entry(
        registry_kind="cause",
        code="agency_dispute",
        display_name="Civil dispute arising from agency relationship",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 182", "Section 211", "Section 212", "Section 213", "Section 214", "Section 217", "Section 221"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 34"]},
        ],
        limitation={"article": "55", "period": "Three years", "from": "When contract / duty is broken"},
        court_rules=_civil_and_commercial_rules(
            nature_keywords=["agency", "business", "commercial"]
        ),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["agency_relationship", "scope_of_authority", "breach_or_misaccounting"],
        required_reliefs=["damages_or_accounts", "interest_if_money_claimed", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["agency_basis"],
        doc_type_keywords=["agency", "agent dispute", "principal-agent"],
        permitted_doctrines=[
            "agency_accounting_s213_s214", "breach_of_authority_s211",
            "agent_lien_s217", "irrevocable_agency_s202",
            "commission_recovery_s221",
        ],
        damages_categories=["unpaid_commission", "unreimbursed_expenses", "loss_from_agent_negligence"],
        interest_basis="wrongful_retention_of_money",
        interest_guidance="Interest on unpaid commission and unreimbursed expenses from the date they fell due; Section 34 CPC for future interest on any money decree.",
        coa_type="single_accrual",
        coa_guidance="Cause of action accrues when the agent's duty is breached — on failure to pay commission due, failure to account, or negligent execution of the principal's instructions.",
        evidence_checklist=["agency agreement", "correspondence", "accounts"],
        complexity_weight=2,
    ),

    "supply_service_contract": _entry(
        registry_kind="cause",
        code="supply_service_contract",
        display_name="Civil claim on supply / service contract",
        primary_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 55", "Section 73", "Section 74"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 34"]},
        ],
        alternative_acts=[
            {"act": "Sale of Goods Act, 1930", "sections": ["Section 55", "Section 56", "Section 57", "Section 59"]},
        ],
        limitation={"article": "55", "period": "Three years", "from": "When contract is broken"},
        court_rules=_civil_and_commercial_rules(
            nature_keywords=["supply", "services", "commercial", "trade", "business"]
        ),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["purchase_or_work_order", "performance_details", "breach_details", "loss_quantification"],
        required_reliefs=["money_or_damages_decree", "interest_pendente_lite_future", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["contractual_basis"],
        doc_type_keywords=["service contract", "supply contract", "work order"],
        permitted_doctrines=[
            "breach_of_contract",
            "service_nonperformance",
            "quantum_meruit_s70_ica",
            "rejection_of_goods_s41_soga",
            "damages_measure_difference_in_market_price_s56_s57_soga",
        ],
        damages_categories=[
            "unpaid_contract_price_or_service_fee",
            "cost_of_procuring_substitute_performance",
            "difference_between_contract_price_and_market_price",
            "consequential_loss_from_non_delivery",
            "quantum_meruit_for_partial_performance",
        ],
        interest_basis="wrongful_retention_of_contract_price_or_deprivation_of_benefit",
        interest_guidance="Plead agreed interest rate if specified in PO/WO; otherwise reasonable commercial rate from due date; Section 34 CPC for pendente lite and future interest.",
        coa_type="single_accrual",
        coa_guidance="Cause of action arises on the date of breach — non-delivery, non-payment after due date, or rejection of services/goods.",
        procedural_prerequisites=["section_12a_mediation", "arbitration_clause_screen", "msmed_act_screen"],
        drafting_red_flags=[
            "If the supplier or service provider is a Micro or Small Enterprise under MSMED Act, 2006, the buyer may be liable for compound interest at three times Bank Rate under Section 16 — screen before drafting.",
            "MSMED Act mandates conciliation then arbitration through MSME Facilitation Councils (Sections 18-20) before a civil suit is maintainable.",
        ],
        evidence_checklist=["contract / PO / WO", "invoices", "emails", "service logs"],
        complexity_weight=2,
    ),

    # ------------------------------------------------------------------
    # PROPERTY / TITLE / POSSESSION / RELIEF
    # ------------------------------------------------------------------

    "specific_performance": _entry(
        registry_kind="cause",
        code="specific_performance",
        display_name="Specific performance of contract relating to immovable property",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 10 (mandatory after 2018 Amendment — court SHALL grant unless s.11(2) exception)", "Section 16", "Section 21", "Section 22"]},
            {"act": "Indian Contract Act, 1872", "sections": ["Section 10"]},
        ],
        alternative_acts=[{"act": "Transfer of Property Act, 1882", "sections": ["Section 53A"]}],
        limitation={"article": "54", "period": "Three years", "from": "Date fixed for performance, or if no date fixed, when plaintiff has notice that performance is refused"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "agreement_details", "readiness_willingness", "refusal_or_default", "schedule_of_property",
        ],
        required_reliefs=["specific_performance_decree", "direction_to_execute_sale_deed", "costs"],
        optional_reliefs=[
            "possession_if_specifically_claimed_u_s_22",
            "partition_if_specifically_claimed_u_s_22",
            "refund_if_specifically_claimed",
            "compensation_if_claimed_u_s_21",
        ],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["readiness_and_willingness"],
        doc_type_keywords=["specific performance", "agreement to sell", "sale deed execution"],
        permitted_doctrines=["specific_performance", "readiness_willingness", "section_22_specific_claim_rule", "part_performance", "time_not_of_essence_in_equity"],
        damages_categories=["compensation_in_lieu_u_s_21", "compensation_in_addition_u_s_21"],
        interest_basis="deprivation_of_money_paid",
        interest_guidance="Plead interest on earnest money / advance paid from date of refusal. Compensation under Section 21 may be claimed in lieu of or in addition to specific performance.",
        coa_type="single_event",
        coa_guidance="Cause of action accrues on the date fixed for performance, or if no date is fixed, when the plaintiff first receives notice of refusal.",
        evidence_checklist=["agreement to sell", "earnest payment proof", "fund capacity proof", "notices"],
        drafting_red_flags=[
            "Post-2018: Section 11(2) SRA is the only ground to refuse — old discretionary refusal under Section 20 no longer exists",
            "Section 6A SRA bars suits for specific performance of infrastructure contracts",
            "Unregistered agreement to sell immovable property valued above Rs 100 must be registered under Section 17(1A) Registration Act",
        ],
        mandatory_averments=[
            {
                "averment": "readiness_and_willingness",
                "provision": "Section 16(c), Specific Relief Act, 1963",
                "instruction": (
                    "Plead that the plaintiff has performed or has always been ready and willing "
                    "to perform the essential terms applicable to him."
                ),
            }
        ],
        mandatory_inline_sections=[
            {
                "section": "READINESS AND WILLINGNESS",
                "placement": "after agreement details",
                "instruction": "State factual readiness material, not mere formulaic language.",
            },
            {
                "section": "SECTION 22 RELIEFS",
                "placement": "within prayer",
                "instruction": "Claim possession / partition / refund only if required and specifically intended.",
            },
        ],
        complexity_weight=3,
    ),

    "recovery_of_possession": _entry(
        registry_kind="cause",
        code="recovery_of_possession",
        display_name="Recovery of possession of immovable property",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 5"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XX Rule 12"]},
        ],
        alternative_acts={
            "_type": "conditional",
            "_resolve_by": "occupancy_type",
            "_rules": [
                {"when": "trespasser", "then": [{"act": "Specific Relief Act, 1963", "sections": ["Section 6"]}]},
                {"when": "tenant_determined", "then": [{"act": "Transfer of Property Act, 1882", "sections": ["Section 106", "Section 111"]}]},
                {"when": "tenant_holding_over", "then": [{"act": "Transfer of Property Act, 1882", "sections": ["Section 106", "Section 111", "Section 116"]}]},
                {"when": "licensee_revoked", "then": [{"act": "Indian Easements Act, 1882", "sections": ["Section 52", "Section 60", "Section 61", "Section 62", "Section 63"]}]},
            ],
            "_default": [],
        },
        limitation={
            "_type": "conditional",
            "_resolve_by": "occupancy_type",
            "_rules": [
                {"when": "trespasser", "then": {"article": "65", "period": "Twelve years", "from": "When possession becomes adverse"}},
                {"when": "tenant_determined", "then": {"article": "67", "period": "Twelve years", "from": "When tenancy is determined"}},
                {"when": "tenant_holding_over", "then": {"article": "67", "period": "Twelve years", "from": "When holding over / tenancy is determined"}},
                {"when": "licensee_revoked", "then": {"article": "67", "period": "Twelve years", "from": "When licence is revoked and occupation becomes unauthorized"}},
            ],
            "_default": {"article": "65", "period": "Twelve years", "from": "When possession becomes adverse"},
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "title_and_ownership", "defendant_occupation", "termination_or_revocation_details",
            "legal_notice", "mesne_profits_claim", "schedule_of_property",
        ],
        required_reliefs=["possession_decree", "mesne_profits_inquiry_order_xx_r12", "costs"],
        optional_reliefs=["permanent_injunction"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["title_basis", "defendant_occupation_basis", "demand_for_vacant_possession", "termination_of_tenancy_licence"],
        doc_type_keywords=["recovery of possession", "vacate", "unauthorized occupation", "encroachment", "trespass"],
        permitted_doctrines=["recovery_possession_s5", "mesne_profits_order_xx_r12", "adverse_possession_defence", "holding_over_s116_TPA", "section_6_sra_bar_six_month_limit"],
        damages_categories=["mesne_profits_past", "mesne_profits_pendente_lite", "future_mesne_profits_till_delivery"],
        interest_basis="deprivation_of_property",
        interest_guidance="Plead mesne profits as a separate relief with inquiry structure.",
        evidence_checklist=["title documents", "lease / licence documents", "termination notice", "property schedule"],
        drafting_red_flags=[
            "Do not cite Sections 31-33 Specific Relief Act for a plain possession suit.",
            "Do not merge possession and mesne profits into one undifferentiated prayer.",
        ],
        complexity_weight=2,
    ),

    "declaration_title": _entry(
        registry_kind="cause",
        code="declaration_title",
        display_name="Declaration as to title to immovable property",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 34", "Section 35"]},
        ],
        limitation={"article": "58", "period": "Three years", "from": "When right to sue first accrues"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "chain_of_title", "cloud_on_title", "consequential_relief_basis", "schedule_of_property",
        ],
        required_reliefs=["declaration_decree", "consequential_relief", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["title_basis", "consequential_relief_basis"],
        doc_type_keywords=["declaration of title", "cloud on title", "ownership declaration"],
        coa_type="single_event",
        coa_guidance="Cause of action accrues when the hostile claim or denial of title first comes to the plaintiff's notice.",
        permitted_doctrines=["declaration_s34", "consequential_relief_proviso_s34", "hostile_claim_requirement", "cloud_on_title_doctrine"],
        optional_reliefs=["possession_if_consequential", "injunction_if_consequential"],
        damages_categories=["mesne_profits_if_possession_also_sought"],
        interest_basis="deprivation_of_property_rights",
        interest_guidance="Plead mesne profits as consequential relief only if possession is also sought under the proviso to Section 34.",
        mandatory_averments=[
            {
                "averment": "consequential_relief",
                "provision": "Proviso to Section 34, Specific Relief Act, 1963",
                "instruction": "If further relief is available, do not omit it.",
            }
        ],
        evidence_checklist=["title chain", "revenue records", "hostile claim document"],
        complexity_weight=2,
    ),

    "permanent_injunction": _entry(
        registry_kind="cause",
        code="permanent_injunction",
        display_name="Suit for perpetual / permanent injunction",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 36", "Section 37", "Section 38"]},
        ],
        limitation={"article": "113", "period": "Three years", "from": "When right to sue accrues"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["plaintiff_right", "defendant_threat", "irreparable_harm"],
        required_reliefs=["permanent_injunction_decree", "costs"],
        optional_reliefs=["interim_injunction_prayer_order_39_cpc"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["plaintiff_possession_or_right", "irreparable_harm_basis", "damages_inadequacy"],
        doc_type_keywords=["permanent injunction", "restrain", "prohibit", "injunction suit"],
        permitted_doctrines=["permanent_injunction_s38", "irreparable_injury_doctrine", "balance_of_convenience", "acquiescence", "delay_laches", "clean_hands_doctrine"],
        damages_categories=["general_damages_wrongful_act", "special_damages_if_loss_quantifiable"],
        coa_type="continuing",
        coa_guidance="Cause of action is continuing where the threat or encroachment persists. Plead both the first date of the wrong and the continuing nature.",
        evidence_checklist=["possession / title proof", "threat material", "photos"],
        complexity_weight=2,
    ),

    "mandatory_injunction": _entry(
        registry_kind="cause",
        code="mandatory_injunction",
        display_name="Suit for mandatory injunction / removal / restoration",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 37", "Section 39"]},
        ],
        limitation={"article": "113", "period": "Three years", "from": "When right to sue accrues"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["status_quo_ante", "wrongful_change_or_obstruction"],
        required_reliefs=["mandatory_injunction_decree", "costs"],
        optional_reliefs=["damages_in_lieu_of_injunction_s40_sra"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["status_quo_ante_description", "restoration_feasibility", "damages_inadequacy"],
        doc_type_keywords=["mandatory injunction", "removal", "restore", "demolition"],
        permitted_doctrines=["mandatory_injunction_s39", "higher_standard_mandatory_vs_prohibitory", "acquiescence", "delay_laches", "damages_in_lieu_s40"],
        damages_categories=["damages_in_lieu_u_s_40", "damages_in_addition_u_s_40"],
        coa_type="continuing",
        coa_guidance="Cause of action arises from the wrongful act and continues so long as the wrongful state persists. Plead both origin date and continuing nature.",
        evidence_checklist=["before/after photos", "site sketch", "complaints"],
        complexity_weight=2,
    ),

    "injunction_negative_covenant": _entry(
        registry_kind="cause",
        code="injunction_negative_covenant",
        display_name="Injunction to enforce negative covenant",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 42"]},
        ],
        limitation={"article": "113", "period": "Three years", "from": "When breach of negative covenant occurs"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["contract_and_negative_covenant", "breach_or_threat"],
        required_reliefs=["injunction_against_breach", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + [
            "negative_covenant_terms", "affirmative_obligation_in_contract", "breach_of_negative_stipulation",
        ],
        doc_type_keywords=["negative covenant", "section 42", "restraint covenant"],
        permitted_doctrines=[
            "negative_covenant_enforcement", "section_27_ica_bar_screen",
            "partial_restraint_doctrine", "section_42_sra_mandatory_grant_if_proved",
        ],
        damages_categories=["loss_from_breach_of_covenant", "diverted_business_profits", "damages_in_lieu_of_injunction_s38_3"],
        alternative_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 27"]},
            {"act": "Specific Relief Act, 1963", "sections": ["Section 37", "Section 38"]},
        ],
        coa_type="continuing",
        coa_guidance="Cause of action subsists as long as the negative covenant is being breached; fresh cause on each act of breach.",
        evidence_checklist=["contract with negative stipulation", "breach evidence"],
        complexity_weight=2,
    ),

    "cancellation_instrument": _entry(
        registry_kind="cause",
        code="cancellation_instrument",
        display_name="Cancellation of deed / instrument",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 31", "Section 32", "Section 33"]},
        ],
        limitation={"article": "59", "period": "Three years", "from": "When facts entitling cancellation first become known"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "instrument_details", "grounds_for_cancellation", "knowledge_date", "consequential_relief", "schedule_of_property_if_needed",
        ],
        required_reliefs=["cancellation_decree", "declaration_not_binding_if_needed", "injunction_if_needed", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + [
            "instrument_particulars", "knowledge_date",
            "ground_of_voidability", "reasonable_apprehension_of_injury", "restitution_offer_s33",
        ],
        doc_type_keywords=["cancellation of sale deed", "cancel instrument", "voidable deed", "section 31"],
        permitted_doctrines=[
            "cancellation_s31_s33", "void_vs_voidable_distinction",
            "partial_cancellation_s32", "restitution_on_cancellation_s33",
            "section_35_saving_rights_of_third_parties",
        ],
        damages_categories=["restitution_of_consideration_paid", "consequential_loss_from_instrument"],
        interest_basis="restitution_and_restoration",
        interest_guidance="Interest on consideration paid for the cancelled instrument from date of execution; Section 34 CPC for pendente lite.",
        coa_type="single_event",
        coa_guidance="Cause of action accrues when facts entitling cancellation first become known to the plaintiff (Article 59 — knowledge date is critical).",
        evidence_checklist=["impugned deed", "fraud / coercion proof", "knowledge date proof"],
        complexity_weight=3,
    ),

    "rectification_instrument": _entry(
        registry_kind="cause",
        code="rectification_instrument",
        display_name="Rectification of instrument",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 26"]},
        ],
        limitation={"article": "59", "period": "Three years", "from": "When the facts entitling rectification first become known to the plaintiff"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["instrument_details", "mutual_mistake_or_fraud", "correct_text_sought"],
        required_reliefs=["rectification_decree", "consequential_relief_if_needed", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + [
            "mistake_particulars", "original_agreement_or_prior_terms",
            "how_instrument_fails_to_express_true_intention", "ground_of_rectification_s26a_or_s26b",
        ],
        doc_type_keywords=["rectification", "section 26 specific relief", "correct deed"],
        permitted_doctrines=[
            "rectification_s26", "common_mistake_rectification",
            "unilateral_mistake_with_fraud_rectification", "parol_evidence_admissible_for_rectification",
            "ad_idem_requirement", "prior_agreement_governs",
            "section_17_limitation_act_fraud_concealment",
        ],
        damages_categories=["consequential_loss_from_erroneous_instrument"],
        coa_type="single_event",
        coa_guidance="Cause of action accrues when the plaintiff first becomes aware of the mistake in the instrument (Article 59 — knowledge date governs).",
        evidence_checklist=["instrument", "drafting trail", "correspondence showing intended terms"],
        complexity_weight=3,
    ),

    "rescission_contract": _entry(
        registry_kind="cause",
        code="rescission_contract",
        display_name="Rescission of contract",
        primary_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 27", "Section 28", "Section 29", "Section 30"]},
        ],
        limitation={"article": "59", "period": "Three years", "from": "When facts entitling rescission first become known"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["contract_details", "grounds_for_rescission", "restoration_offer_if_needed"],
        required_reliefs=["rescission_decree", "restitution_if_needed", "injunction_if_needed", "costs"],
        alternative_acts=[
            {"act": "Indian Contract Act, 1872", "sections": ["Section 19", "Section 19A", "Section 64"]},
        ],
        required_averments=COMMON_REQUIRED_AVERMENTS + [
            "rescission_ground", "section_28_immovable_bar_check", "restitution_offer",
        ],
        doc_type_keywords=["rescission", "rescind contract", "section 27 specific relief"],
        permitted_doctrines=[
            "rescission_s27_s30", "restitutio_in_integrum", "election_doctrine", "section_29_alternative_prayer",
            "section_19_ica_voidable_contract", "section_19a_ica_undue_influence",
            "section_64_ica_restitution_on_void_or_rescinded_contract", "section_17_limitation_act_fraud_extension",
        ],
        damages_categories=["restitution_of_consideration", "damages_for_fraud_if_applicable", "loss_of_bargain"],
        interest_basis="restitution_of_consideration",
        interest_guidance="Interest on consideration paid from date of contract to date of rescission decree; Section 34 CPC for pendente lite.",
        coa_type="single_event",
        coa_guidance="Cause of action accrues when facts entitling rescission first become known (fraud, misrepresentation, undue influence — Article 59 knowledge date).",
        evidence_checklist=["contract", "fraud / mistake / voidability proof", "restoration readiness"],
        complexity_weight=3,
    ),

    "partition": _entry(
        registry_kind="cause",
        code="partition",
        display_name="Partition and separate possession",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XX Rule 18"]},
        ],
        alternative_acts=[
            {"act": "Hindu Succession Act, 1956", "sections": ["Section 6", "Section 8", "Section 10"]},
            {"act": "Partition Act, 1893", "sections": ["Section 2", "Section 3", "Section 4"]},
        ],
        limitation={
            "_type": "conditional",
            "_resolve_by": "ouster_status",
            "_rules": [
                {"when": "joint_possession_case", "then": {"article": "NONE", "period": "No fixed limitation", "from": "Right subsists during co-ownership"}},
                {"when": "ouster_or_exclusion_alleged", "then": {"article": "65", "period": "Twelve years", "from": "When possession of defendant becomes adverse to plaintiff"}},
                {"when": "erroneous_prior_partition", "then": {"article": "58", "period": "Three years", "from": "When the plaintiff first has notice that the prior partition is being set up against him or the instrument thereof becomes known"}},
            ],
            "_default": {"article": "NONE", "period": "No fixed limitation", "from": "Right subsists during co-ownership"},
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "genealogy_table", "schedule_of_property", "share_of_plaintiff", "limitation_if_ouster_pleaded",
        ],
        required_reliefs=["preliminary_decree_shares", "partition_by_metes_and_bounds", "appointment_of_commissioner", "separate_possession", "final_decree", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["share_basis", "property_description"],
        doc_type_keywords=["partition", "separate possession", "coparcener", "joint property"],
        permitted_doctrines=["right_to_partition", "preliminary_decree_order_xx_r18", "daughters_coparcenary_right_s6_hsa_2005", "partition_in_kind_vs_sale", "unity_of_possession_coparcener", "right_not_extinguished_by_joint_possession"],
        optional_reliefs=["mesne_profits_inquiry_order_xx_r18"],
        damages_categories=["mesne_profits_for_ouster", "share_of_income_from_property"],
        interest_basis="deprivation_of_property",
        interest_guidance="Plead mesne profits under Order XX Rule 12 CPC only when ouster/exclusion from possession is specifically alleged and pleaded.",
        mandatory_inline_sections=[
            {"section": "GENEALOGY TABLE", "placement": "before facts", "instruction": "State lineal descent from common ancestor."},
            {"section": "SCHEDULE OF PROPERTY", "placement": "after facts", "instruction": "Give complete property description."},
            {"section": "SHARE OF THE PLAINTIFF", "placement": "after schedule", "instruction": "State exact fractional share and basis."},
        ],
        evidence_checklist=["genealogy proof", "title / mutation / RTC", "death certificates", "tax records", "will_or_settlement_deed_if_applicable", "legal_heir_certificate"],
        complexity_weight=3,
    ),

    "easement": _entry(
        registry_kind="cause",
        code="easement",
        display_name="Suit for declaration / protection of easement rights",
        primary_acts=[
            {"act": "Indian Easements Act, 1882", "sections": ["Section 4", "Section 15"]},
            {"act": "Specific Relief Act, 1963", "sections": ["Section 34", "Section 38"]},
        ],
        limitation={
            "_type": "conditional",
            "_resolve_by": "relief_form",
            "_rules": [
                {"when": "declaration_plus_injunction", "then": {"article": "58", "period": "Three years", "from": "When right to sue first accrues"}},
                {"when": "injunction_only", "then": {"article": "113", "period": "Three years", "from": "When right to sue accrues"}},
            ],
            "_default": {"article": "58", "period": "Three years", "from": "When right to sue first accrues"},
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "dominant_and_servient_heritage", "easement_basis", "obstruction_details", "schedule_of_property",
        ],
        required_reliefs=["declaration_of_easement_if_claimed", "permanent_injunction", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + [
            "easement_basis", "continuous_use", "continuous_use_20_years",
            "user_as_of_right", "no_permissive_use_s16",
        ],
        doc_type_keywords=["easement", "right of way", "passage", "light", "air", "water"],
        permitted_doctrines=["easement_by_prescription", "easement_by_grant", "easement_by_necessity_s13", "easement_by_custom_s18"],
        damages_categories=["general_damages_obstruction", "special_damages_business_loss", "mesne_profits"],
        evidence_checklist=["maps", "sketch", "witnesses of long use", "photos"],
        complexity_weight=2,
    ),

    "mortgage_redemption": _entry(
        registry_kind="cause",
        code="mortgage_redemption",
        display_name="Redemption of mortgage",
        primary_acts=[
            {"act": "Transfer of Property Act, 1882", "sections": ["Section 60", "Section 62", "Section 91"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XXXIV"]},
        ],
        limitation={"article": "61", "period": "Thirty years", "from": "When right to redeem accrues"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "mortgage_details", "amount_due_and_tender", "schedule_of_property",
        ],
        required_reliefs=["redemption_decree", "delivery_of_documents", "possession_after_redemption", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["mortgage_basis", "tender_or_deposit"],
        doc_type_keywords=["mortgage redemption", "redeem mortgage", "mortgagor"],
        permitted_doctrines=["right_to_redeem", "once_a_mortgage_always_a_mortgage", "clog_on_equity_of_redemption"],
        damages_categories=["damages_wrongful_withholding_title", "mesne_profits_if_mortgagee_in_possession"],
        interest_basis="deprivation_of_property_or_money",
        interest_guidance="Plead interest on amount tendered from date of tender; mesne profits for period mortgagee remained in possession after tender.",
        evidence_checklist=["mortgage deed", "accounts", "tender proof"],
        complexity_weight=2,
    ),

    "mortgage_foreclosure_sale": _entry(
        registry_kind="cause",
        code="mortgage_foreclosure_sale",
        display_name="Suit for foreclosure / sale on mortgage",
        primary_acts=[
            {"act": "Transfer of Property Act, 1882", "sections": ["Section 67", "Section 68", "Section 69"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Order XXXIV"]},
        ],
        limitation={
            "_type": "conditional",
            "_resolve_by": "mortgage_relief",
            "_rules": [
                {"when": "foreclosure", "then": {"article": "62", "period": "Thirty years", "from": "When money secured becomes due"}},
                {"when": "sale", "then": {"article": "64", "period": "Twelve years", "from": "When money secured becomes due"}},
            ],
            "_default": {"article": "64", "period": "Twelve years", "from": "When money secured becomes due"},
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["mortgage_details", "default", "amount_due", "schedule_of_property"],
        required_reliefs=["preliminary_mortgage_decree", "final_decree_for_sale_or_foreclosure", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["mortgage_basis", "default_date"],
        doc_type_keywords=["mortgage sale", "foreclosure", "order 34 mortgage"],
        permitted_doctrines=["mortgage_suit_order_34", "preliminary_and_final_decree_procedure", "right_to_redemption_before_final_decree"],
        damages_categories=["principal_due", "interest_due", "costs_of_suit"],
        interest_basis="deprivation_of_money",
        interest_guidance="Plead contractual rate to date of suit; pendente lite and future interest under Section 34 CPC.",
        evidence_checklist=["mortgage deed", "default account", "demand notice"],
        complexity_weight=3,
    ),

    # ------------------------------------------------------------------
    # TORTS / CIVIL WRONGS
    # ------------------------------------------------------------------

    "tortious_negligence": _entry(
        registry_kind="cause",
        code="tortious_negligence",
        display_name="Damages for negligence",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Negligence", "Duty of care"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 34"]},
        ],
        limitation={
            "_type": "conditional",
            "_resolve_by": "negligence_injury_type",
            "_rules": [
                {"when": "personal_injury_or_bodily_harm", "then": {"article": "88", "period": "One year", "from": "When the injury complained of occurs"}},
                {"when": "property_damage_or_economic_loss", "then": {"article": "113", "period": "Three years", "from": "When the right to sue accrues (date of negligent act causing damage)"}},
            ],
            "_default": {"article": "113", "period": "Three years", "from": "When the right to sue accrues (date of negligent act causing damage)"},
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["duty_of_care", "breach_of_duty", "causation_and_damage"],
        required_reliefs=["damages_decree", "interest_pendente_lite_future", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["causation_basis"],
        doc_type_keywords=["negligence", "tort", "duty of care", "damages"],
        permitted_doctrines=["duty_breach_causation", "res_ipsa_loquitur", "contributory_negligence", "volenti_non_fit_injuria"],
        damages_categories=["general_damages_pain_suffering", "special_damages_medical_expenses", "loss_of_earnings", "property_damage"],
        interest_basis="compensation_for_loss",
        interest_guidance="Interest under Section 34 CPC on special damages (medical, repair costs) from date of suit. No pre-suit interest unless liquidated debt component exists.",
        coa_type="single_event",
        evidence_checklist=["incident record", "expert material", "bills", "witnesses"],
        complexity_weight=2,
    ),

    "defamation": _entry(
        registry_kind="cause",
        code="defamation",
        display_name="Suit for damages for defamation",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Libel", "Slander", "Defamation"]},
        ],
        alternative_acts=[{"act": "Bharatiya Nyaya Sanhita, 2023", "sections": ["Section 356", "Section 357"]}],
        limitation={
            "_type": "conditional",
            "_resolve_by": "statement_medium",
            "_rules": [
                {"when": "written_or_published", "then": {"article": "75", "period": "One year", "from": "When defamatory matter is published"}},
                {"when": "oral_only", "then": {"article": "76", "period": "One year", "from": "When words are spoken"}},
            ],
            "_default": {"article": "75", "period": "One year", "from": "When defamatory matter is published"},
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "defamatory_statement", "publication_to_third_parties", "falsity_and_malice", "damage_to_reputation",
        ],
        required_reliefs=["damages_decree", "permanent_injunction_against_repetition", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["publication_date"],
        doc_type_keywords=["defamation", "libel", "slander", "false allegations", "social media defamation"],
        permitted_doctrines=["libel", "slander", "malice", "innuendo", "justification_truth_defence", "fair_comment", "qualified_privilege"],
        damages_categories=["general_damages_reputation", "special_damages_financial_loss", "aggravated_damages"],
        interest_basis="compensation_for_reputational_harm",
        interest_guidance="No pre-suit interest on general damages (unliquidated). Interest under Section 34 CPC on special financial damages from date of suit only.",
        coa_type="single_event",
        evidence_checklist=["screenshots", "URLs", "publication copies", "business loss proof"],
        complexity_weight=2,
    ),

    "nuisance": _entry(
        registry_kind="cause",
        code="nuisance",
        display_name="Abatement of nuisance and damages",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Private Nuisance"]},
            {"act": "Specific Relief Act, 1963", "sections": ["Section 38", "Section 39"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 91"]},
        ],
        limitation={"article": "113", "period": "Three years", "from": "When nuisance first affects the plaintiff (continuing nuisance: fresh cause accrues daily per Section 22, Limitation Act 1963)"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["nuisance_description", "interference_with_enjoyment"],
        required_reliefs=["injunction_abate_nuisance", "damages_if_claimed", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["nuisance_nature_frequency_duration", "plaintiff_right_to_enjoyment"],
        damages_categories=["general_damages_loss_of_enjoyment", "special_damages_medical_or_property", "costs_of_abatement"],
        doc_type_keywords=["nuisance", "noise pollution", "obstruction", "interference"],
        permitted_doctrines=["private_nuisance", "public_nuisance", "continuing_wrong_s22_limitation_act", "coming_to_the_nuisance_not_a_defence", "prescriptive_right_s26_easement_act_1882", "reasonable_user_test"],
        evidence_checklist=["photos", "videos", "complaint records", "municipal reports"],
        complexity_weight=2,
    ),

    "trespass_immovable": _entry(
        registry_kind="cause",
        code="trespass_immovable",
        display_name="Civil action for trespass to immovable property",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Trespass to land"]},
            {"act": "Specific Relief Act, 1963", "sections": ["Section 5", "Section 6"]},
        ],
        limitation={
            "_type": "conditional",
            "_resolve_by": "trespass_relief",
            "_rules": [
                {"when": "possession_based_on_title", "then": {"article": "65", "period": "Twelve years", "from": "When possession of defendant becomes adverse to plaintiff"}},
                {"when": "possession_based_on_prior_possession", "then": {"article": "64", "period": "Twelve years", "from": "When plaintiff is dispossessed"}},
                {"when": "damages_only", "then": {"article": "113", "period": "Three years", "from": "When the trespass causing damage takes place"}},
            ],
            "_default": {"article": "65", "period": "Twelve years", "from": "When possession of defendant becomes adverse to plaintiff"},
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["plaintiff_possession_or_title", "acts_of_trespass", "damage_or_threat"],
        required_reliefs=["injunction_or_possession_as_applicable", "damages_if_claimed", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["trespass_particulars"],
        doc_type_keywords=["trespass", "encroachment", "illegal entry"],
        permitted_doctrines=["trespass_to_land"],
        damages_categories=["general_damages_for_trespass", "special_damages_loss_from_entry", "restitution_of_profits_wrongfully_derived"],
        interest_basis="wrongful_interference_with_land",
        interest_guidance="Interest under Section 34 CPC on quantified special damages from date of suit. General damages at court's discretion.",
        evidence_checklist=["title / possession proof", "photos", "sketch", "complaints"],
        complexity_weight=2,
    ),

    "trespass_goods_movable": _entry(
        registry_kind="cause",
        code="trespass_goods_movable",
        display_name="Civil action for trespass / interference with goods",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Trespass to goods", "Detinue / conversion type principles"]},
        ],
        alternative_acts=[
            {"act": "Specific Relief Act, 1963", "sections": ["Section 7", "Section 8"]},
        ],
        limitation={"article": "91", "period": "Three years", "from": "When property is wrongfully taken or injured / detained"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["movable_description", "interference_details", "loss_or_detention"],
        required_reliefs=["return_or_value", "damages", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["movable_identification", "specific_goods_identification", "plaintiff_ownership_or_right"],
        damages_categories=["actual_loss_of_goods_value", "compensation_for_injury_to_goods", "loss_of_use", "special_damages"],
        doc_type_keywords=["trespass to goods", "movable interference", "detention of goods"],
        permitted_doctrines=["trespass_to_goods"],
        evidence_checklist=["invoice", "photos", "serial number", "demand notice"],
        complexity_weight=2,
    ),

    "business_disparagement": _entry(
        registry_kind="cause",
        code="business_disparagement",
        display_name="Civil action for business disparagement / injurious falsehood",
        primary_acts=[
            {"act": "Law of Torts (Common Law)", "sections": ["Malicious falsehood / disparagement"]},
        ],
        alternative_acts=[
            {"act": "Trade Marks Act, 1999", "sections": ["Section 142"]},
        ],
        limitation={"article": "113", "period": "Three years", "from": "When right to sue accrues"},
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["false_statement", "publication", "malice", "special_damage"],
        required_reliefs=["damages_decree", "injunction_against_repetition", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["special_damage_particulars", "malice_particulars", "falsity_of_statement", "loss_linkage"],
        damages_categories=["special_damages_proved", "loss_of_customers", "loss_of_contracts", "business_loss"],
        drafting_red_flags=[
            "Special damage is mandatory — general reputational injury is insufficient for business disparagement; plaint must particularise specific customers lost, contracts cancelled, or quantifiable business loss.",
        ],
        doc_type_keywords=["business disparagement", "malicious falsehood", "trade libel"],
        permitted_doctrines=["injurious_falsehood"],
        evidence_checklist=["publication proof", "customer loss evidence", "screenshots"],
        complexity_weight=2,
    ),

    # ------------------------------------------------------------------
    # TENANCY / RENT / BUSINESS RELATIONSHIPS
    # ------------------------------------------------------------------

    "eviction": _entry(
        registry_kind="cause",
        code="eviction",
        display_name="Eviction of tenant under special rent / tenancy law or TPA",
        primary_acts=[{"act": "State Rent / Tenancy Law", "sections": ["Grounds for eviction / possession"]}],
        alternative_acts=[{"act": "Transfer of Property Act, 1882", "sections": ["Section 106", "Section 111"]}],
        limitation={
            "_type": "conditional",
            "_resolve_by": "forum_track",
            "_rules": [
                {"when": "special_rent_forum", "then": {"article": "NONE", "period": "Statute/forum controlled", "from": "When statutory ground arises"}},
                {"when": "ordinary_tpa_suit", "then": {"article": "67", "period": "Twelve years", "from": "When tenancy is determined"}},
            ],
            "_default": {"article": "NONE", "period": "Screen statute first", "from": "Depends on forum track"},
        },
        court_rules={
            "_type": "conditional",
            "_resolve_by": "state",
            "_rules": [
                {
                    "when": "Karnataka",
                    "then": {"default": {"court": "Court exercising jurisdiction under Karnataka Rent Act", "format": "H.R.C. / state format", "heading": "IN THE COURT OF THE {court_type}", "applicable_act": "Karnataka Rent Act, 1999"}},
                },
                {
                    "when": "Maharashtra",
                    "then": {"default": {"court": "Small Causes Court / Civil Court as applicable", "format": "R.A.E. & R. No. / Eviction Petition No.", "heading": "IN THE COURT OF THE {court_type}", "applicable_act": "Maharashtra Rent Control Act, 1999"}},
                },
                {
                    "when": "Delhi",
                    "then": {"default": {"court": "Rent Controller / Additional Rent Controller", "format": "Eviction Petition No.", "heading": "BEFORE THE {court_type}", "applicable_act": "Delhi Rent Control Act, 1958"}},
                },
                {
                    "when": "Tamil Nadu",
                    "then": {"default": {"court": "Rent Court", "format": "Rent Court Petition No.", "heading": "BEFORE THE {court_type}", "applicable_act": "Tamil Nadu Regulation of Rights and Responsibilities of Landlords and Tenants Act, 2017"}},
                },
                {
                    "when": "Telangana",
                    "then": {"default": {"court": "Rent Controller", "format": "R.C. No.", "heading": "BEFORE THE {court_type}", "applicable_act": "Telangana Buildings (Lease, Rent and Eviction) Control Act, 1960"}},
                },
                {
                    "when": "Uttar Pradesh",
                    "then": {"default": {"court": "Prescribed Authority (Civil Judge Junior Division)", "format": "Eviction Case No.", "heading": "BEFORE THE {court_type}", "applicable_act": "Uttar Pradesh Urban Buildings (Regulation of Letting, Rent and Eviction) Act, 1972"}},
                },
                {
                    "when": "West Bengal",
                    "then": {"default": {"court": "Rent Controller", "format": "R.C. No.", "heading": "BEFORE THE {court_type}", "applicable_act": "West Bengal Premises Tenancy Act, 1997"}},
                },
                {
                    "when": "Andhra Pradesh",
                    "then": {"default": {"court": "Rent Controller", "format": "R.C. No.", "heading": "BEFORE THE {court_type}", "applicable_act": "Andhra Pradesh Buildings (Lease, Rent and Eviction) Control Act, 1960"}},
                },
                {
                    "when": "Gujarat",
                    "then": {"default": {"court": "Mamlatdar / Designated Rent Court", "format": "H.R.P. No.", "heading": "BEFORE THE {court_type}", "applicable_act": "Gujarat Rent Control Act, 1999"}},
                },
                {
                    "when": "Rajasthan",
                    "then": {"default": {"court": "Rent Tribunal", "format": "Eviction Petition No.", "heading": "BEFORE THE {court_type}", "applicable_act": "Rajasthan Rent Control Act, 2001"}},
                },
            ],
            "_default": {"default": {"court": "Civil Court", "format": "O.S. No.", "heading": "IN THE COURT OF THE {court_type}", "applicable_act": "Transfer of Property Act, 1882"}},
        },
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + [
            "jurisdiction_or_forum", "tenancy_details", "statutory_ground_of_eviction", "notice_if_required",
        ],
        required_reliefs=["eviction_decree_or_order", "arrears_if_claimed", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["tenancy_basis", "ground_of_eviction"],
        doc_type_keywords=["eviction", "tenant", "landlord", "vacate", "rent control"],
        permitted_doctrines=["rent_act_screen", "notice_screen"],
        damages_categories=["arrears_of_rent_if_claimed", "mesne_profits_or_occupation_charges", "damages_for_misuse_if_applicable"],
        procedural_prerequisites=["state_statute_screen", "rent_act_bar_screen"],
        evidence_checklist=["tenancy agreement", "rent receipts / default chart", "ground-specific proof", "notice"],
        complexity_weight=2,
    ),

    "arrears_of_rent": _entry(
        registry_kind="cause",
        code="arrears_of_rent",
        display_name="Recovery of arrears of rent / licence fee",
        primary_acts=[
            {"act": "Transfer of Property Act, 1882", "sections": ["Section 105", "Section 108"]},
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 34"]},
        ],
        limitation={"article": "52", "period": "Three years", "from": "When each instalment of rent falls due (runs separately for each period)"},
        coa_type="continuing",
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["tenancy_or_licence_details", "arrears_chart", "demand_and_default", "interest"],
        required_reliefs=["money_decree", "interest_if_claimed", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["period_of_arrears"],
        damages_categories=["arrears_amount", "interest_on_arrears"],
        procedural_prerequisites=["rent_control_forum_screen"],
        doc_type_keywords=["arrears of rent", "rent due", "licence fee due"],
        permitted_doctrines=["arrears_recovery"],
        evidence_checklist=["rent agreement", "arrears statement", "notice"],
        complexity_weight=1,
    ),

    "mesne_profits_post_tenancy": _entry(
        registry_kind="cause",
        code="mesne_profits_post_tenancy",
        display_name="Mesne profits / occupation charges after termination",
        primary_acts=[
            {"act": "Code of Civil Procedure, 1908", "sections": ["Section 2(12)", "Order XX Rule 12", "Section 34"]},
        ],
        limitation={"article": "32", "period": "Three years", "from": "When the mesne profits are received by the defendant (for each period of occupation, time runs separately)"},
        coa_type="continuing",
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["termination_details", "unauthorized_occupation_period", "basis_of_quantification"],
        required_reliefs=["mesne_profits_or_occupation_charges", "interest_on_past_mesne_profits_u_s_34_cpc", "future_inquiry_if_needed", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["unauthorized_period"],
        damages_categories=["past_mesne_profits_at_market_rate", "interest_on_past_mesne_profits", "future_mesne_profits_by_inquiry"],
        doc_type_keywords=["mesne profits", "occupation charges"],
        permitted_doctrines=["mesne_profits"],
        evidence_checklist=["termination notice", "market rent proof", "possession status"],
        complexity_weight=2,
    ),

    "partnership_dissolution": _entry(
        registry_kind="cause",
        code="partnership_dissolution",
        display_name="Dissolution of partnership and rendition of accounts",
        primary_acts=[
            {"act": "Indian Partnership Act, 1932", "sections": ["Section 44", "Section 46", "Section 48"]},
        ],
        limitation={
            "_type": "conditional",
            "_resolve_by": "dissolution_status",
            "_rules": [
                {"when": "accounts_after_dissolution", "then": {"article": "5", "period": "Three years", "from": "Date of dissolution or date of last entry in the accounts, whichever is later"}},
                {"when": "court_dissolution_of_subsisting_firm", "then": {"article": "113", "period": "Three years", "from": "When right to sue accrues (e.g. ground under Section 44 arises)"}},
            ],
            "_default": {"article": "5", "period": "Three years", "from": "Date of dissolution or date of last entry in the accounts, whichever is later"},
        },
        drafting_red_flags=[
            "Section 69 IPA: Unregistered firm cannot sue partner on rights arising from contract of partnership — verify registration before drafting.",
        ],
        court_rules=_civil_and_commercial_rules(
            nature_keywords=["partnership", "business", "firm", "commercial"]
        ),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["partnership_details", "dissolution_ground_or_status", "accounts_state"],
        required_reliefs=["dissolution_decree", "rendition_of_accounts", "share_in_assets", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["partnership_basis"],
        doc_type_keywords=["partnership dissolution", "rendition of accounts", "partner dispute"],
        permitted_doctrines=[
            "dissolution_s44", "accounting_between_partners",
            "section_46_settlement_of_accounts", "section_48_mode_of_settlement",
            "goodwill_valuation_s55", "section_69_unregistered_firm_bar",
        ],
        damages_categories=["share_in_net_assets", "loss_of_goodwill_share", "unpaid_profit_share", "interest_on_capital_contribution"],
        interest_basis="capital_contribution_and_profit_share",
        interest_guidance="Interest on capital contribution and profit share from date of dissolution at rate agreed in deed or at 6% per annum (Section 13(d) IPA); Section 34 CPC for pendente lite.",
        coa_type="single_event",
        coa_guidance="Cause of action accrues on the date of dissolution (if seeking accounts) or when ground under Section 44 arises (if seeking judicial dissolution).",
        evidence_checklist=["partnership deed", "books", "bank statements", "notice", "firm registration certificate"],
        complexity_weight=3,
    ),

    "partner_restraint_injunction": _entry(
        registry_kind="cause",
        code="partner_restraint_injunction",
        display_name="Injunction against partner / ex-partner conduct",
        primary_acts=[
            {"act": "Indian Partnership Act, 1932", "sections": ["Section 9", "Section 36"]},
            {"act": "Specific Relief Act, 1963", "sections": ["Section 37", "Section 38", "Section 42"]},
        ],
        limitation={"article": "113", "period": "Three years", "from": "When right to sue accrues"},
        court_rules=_civil_and_commercial_rules(
            nature_keywords=["partnership", "business", "commercial"]
        ),
        required_sections=COMMON_CIVIL_PLAINT_SECTIONS + ["partnership_relationship", "wrongful_conduct", "need_for_restraint"],
        required_reliefs=["perpetual_injunction_s38", "interim_injunction_if_sought", "damages_in_lieu_or_addition_s38_3", "costs"],
        required_averments=COMMON_REQUIRED_AVERMENTS + ["injunction_basis"],
        doc_type_keywords=["partner injunction", "restrain partner", "ex-partner restraint"],
        permitted_doctrines=[
            "injunction_in_partnership_dispute",
            "balance_of_convenience", "irreparable_injury",
            "section_36_ipa_post_dissolution_restraint", "section_9_ipa_good_faith_duty",
            "negative_covenant_enforcement", "section_42_sra_negative_agreement",
            "section_69_registration_bar_screen",
        ],
        damages_categories=["loss_of_business_opportunity", "goodwill_erosion", "diversion_of_clients_profits"],
        drafting_red_flags=[
            "Section 69 IPA: Unregistered firm cannot sue — verify firm registration before drafting.",
            "Section 27 ICA broadly voids restraint of trade; Section 36 IPA post-dissolution restraint is a statutory exception — plead it specifically.",
            "Injunction against ex-partner for post-dissolution conduct must state dissolution date and covenant terms.",
        ],
        coa_type="continuing",
        coa_guidance="Cause of action is continuing so long as wrongful conduct persists; fresh cause on each repetition.",
        evidence_checklist=["deed", "communications", "threat/breach proof", "firm registration"],
        complexity_weight=2,
    ),
}

# Backward-compatible alias — pipeline __init__.py imports CIVIL_CAUSE_TYPES
CIVIL_CAUSE_TYPES = SUBSTANTIVE_CAUSES


# ============================================================================
# FORUM REGISTRY
# ============================================================================

FORUM_REGISTRY: Dict[str, dict] = {

    "civil_court": _entry(
        registry_kind="forum",
        code="civil_court",
        display_name="Ordinary Civil Court",
        primary_acts=[{"act": "Code of Civil Procedure, 1908", "sections": ["Section 9"]}],
        required_sections=["jurisdiction", "pecuniary_jurisdiction", "territorial_jurisdiction"],
        doc_type_keywords=["civil court", "district court", "civil judge"],
        notes=["Default forum for mainstream CPC-based civil suits unless special forum or statutory bar applies."],
        complexity_weight=1,
    ),

    "commercial_court": _entry(
        registry_kind="forum",
        code="commercial_court",
        display_name="Commercial Court / Commercial Division",
        primary_acts=[{"act": "Commercial Courts Act, 2015", "sections": ["Section 2(1)(c)", "Section 2(1)(i)", "Section 12", "Section 12A"]}],
        required_sections=["commercial_maintainability", "specified_value", "section_12a_compliance", "statement_of_truth"],
        doc_type_keywords=["commercial court", "commercial division"],
        notes=["Use only if subject matter is commercial and specified value is not less than ₹3 lakh."],
        complexity_weight=2,
    ),

    "rent_forum": _entry(
        registry_kind="forum",
        code="rent_forum",
        display_name="State Rent / Tenancy Forum",
        primary_acts=[{"act": "State Rent / Tenancy Law", "sections": ["Grounds and forum provisions"]}],
        required_sections=["state_specific_forum_basis", "tenancy_relationship", "statutory_ground"],
        doc_type_keywords=["rent controller", "rent court", "eviction petition"],
        notes=["Must be adapted state-wise before deployment."],
        complexity_weight=2,
    ),

    "small_causes": _entry(
        registry_kind="forum",
        code="small_causes",
        display_name="Court of Small Causes / analogous forum",
        primary_acts=[{"act": "Provincial Small Cause Courts Act / local statute", "sections": ["Jurisdiction provisions"]}],
        required_sections=["small_causes_jurisdiction_basis"],
        doc_type_keywords=["small causes", "small cause court"],
        complexity_weight=2,
    ),

    "high_court_original_side": _entry(
        registry_kind="forum",
        code="high_court_original_side",
        display_name="High Court Original Side",
        primary_acts=[{"act": "Letters Patent / High Court rules", "sections": ["Original side provisions"]}],
        required_sections=["original_side_maintainability", "pecuniary_and_subject_matter_basis"],
        doc_type_keywords=["original side", "high court original jurisdiction"],
        notes=["Use separate High Court rules adapter."],
        complexity_weight=3,
    ),

    "special_statutory_civil_forum": _entry(
        registry_kind="forum",
        code="special_statutory_civil_forum",
        display_name="Special statutory civil forum adapter",
        primary_acts=[{"act": "Forum-specific statute", "sections": ["Forum provisions"]}],
        required_sections=["special_forum_basis"],
        doc_type_keywords=["special forum"],
        notes=["Use separate module if the statute provides its own form / process."],
        complexity_weight=3,
    ),
}


# ============================================================================
# VALIDATION REGISTRY
# ============================================================================

VALIDATION_REGISTRY: Dict[str, dict] = {

    "limitation_engine": {
        "description": "Resolves limitation article, period, starting point, and saver provisions.",
        "checks": [
            "cause_specific_article",
            "first_accrual_date",
            "conditional_resolution",
            "section_17_screen",
            "section_18_acknowledgment_screen",
            "section_19_part_payment_screen",
            "section_14_wrong_forum_screen",
            "section_4_holiday_screen",
        ],
    },

    "jurisdiction_engine": {
        "description": "Determines subject matter, territorial, pecuniary, and forum competence.",
        "checks": [
            "section_9_cpc_screen",
            "territorial_jurisdiction_basis",
            "pecuniary_jurisdiction_basis",
            "special_forum_bar_screen",
            "arbitration_clause_screen",
            "rent_act_bar_screen",
        ],
    },

    "court_fee_engine": {
        "description": "Determines governing court-fee statute and valuation mode.",
        "checks": [
            "state_court_fee_statute",
            "ad_valorem_or_fixed",
            "market_value_or_consideration_or_declared_value_screen",
        ],
    },

    "notice_engine": {
        "description": "Screens statutory notice requirements before institution.",
        "checks": [
            "section_80_cpc_notice",
            "tp_act_106_notice_if_required",
            "contractual_notice_clause",
            "section_12a_commercial_mediation",
        ],
    },

    "relief_compatibility_engine": {
        "description": "Checks whether the selected prayers are logically and legally compatible.",
        "checks": [
            "declaration_plus_consequential_relief_screen",
            "specific_performance_section_22_screen",
            "possession_and_mesne_profits_screen",
            "injunction_vs_possession_screen",
            "damages_in_addition_or_substitution_screen",
        ],
    },

    "chronology_engine": {
        "description": "Checks internal factual chronology.",
        "checks": [
            "contract_before_breach",
            "notice_after_default",
            "termination_before_mesne_profits",
            "knowledge_date_before_article_59_count",
        ],
    },

    "amount_computation_engine": {
        "description": "Checks arithmetic and damages basis.",
        "checks": [
            "principal_total",
            "interest_rate_and_period",
            "arrears_chart",
            "damages_schedule",
            "mesne_profit_basis",
        ],
    },

    "document_proof_engine": {
        "description": "Checks that the key pleaded facts are supported by an evidence list.",
        "checks": [
            "title_documents",
            "contract_documents",
            "notice_proof",
            "payment_proof",
            "identity_of_property_or_instrument",
        ],
    },
}


# ============================================================================
# RESOLUTION HELPERS
# ============================================================================

def _matches_condition(condition: Any, actual: Any) -> bool:
    if isinstance(condition, list):
        return actual in condition
    return condition == actual


def resolve_conditional(value: Any, context: Optional[Mapping[str, Any]] = None) -> Any:
    """
    Resolve conditional objects of the form:
    {
        "_type": "conditional",
        "_resolve_by": "...",
        "_rules": [{"when": ..., "then": ...}],
        "_default": ...
    }
    """
    context = context or {}

    if not isinstance(value, dict) or value.get("_type") != "conditional":
        return value

    key = value.get("_resolve_by")
    actual = context.get(key)

    for rule in value.get("_rules", []):
        if _matches_condition(rule.get("when"), actual):
            return rule.get("then")

    return value.get("_default")


def _resolved_copy(entry: Mapping[str, Any], context: Optional[Mapping[str, Any]] = None) -> dict:
    context = context or {}
    raw = deepcopy(dict(entry))
    for key, val in list(raw.items()):
        raw[key] = resolve_conditional(val, context)
    return raw


def get_draft_family(code: str, context: Optional[Mapping[str, Any]] = None) -> dict:
    if code not in DRAFT_FAMILIES:
        raise KeyError(f"Unknown draft family: {code}")
    return _resolved_copy(DRAFT_FAMILIES[code], context)


def get_substantive_cause(code: str, context: Optional[Mapping[str, Any]] = None) -> dict:
    if code not in SUBSTANTIVE_CAUSES:
        raise KeyError(f"Unknown substantive cause: {code}")
    return _resolved_copy(SUBSTANTIVE_CAUSES[code], context)


def get_forum(code: str, context: Optional[Mapping[str, Any]] = None) -> dict:
    if code not in FORUM_REGISTRY:
        raise KeyError(f"Unknown forum: {code}")
    return _resolved_copy(FORUM_REGISTRY[code], context)


def build_drafting_profile(
    *,
    draft_family: str,
    cause_code: Optional[str] = None,
    forum_code: Optional[str] = None,
    context: Optional[Mapping[str, Any]] = None,
) -> dict:
    """
    Combine selected family + cause + forum into one resolved drafting profile.
    """
    context = context or {}

    profile = {
        "version": LKB_VERSION,
        "draft_family": get_draft_family(draft_family, context),
        "cause": get_substantive_cause(cause_code, context) if cause_code else None,
        "forum": get_forum(forum_code, context) if forum_code else None,
        "global_rules": deepcopy(GLOBAL_DRAFTING_RULES),
        "limitation_savers": deepcopy(GLOBAL_LIMITATION_SAVERS),
        "validation_registry": deepcopy(VALIDATION_REGISTRY),
        "court_fee_statutes": deepcopy(COURT_FEE_STATUTES),
    }

    # Merge required sections / averments / red flags into convenience fields.
    sections: List[str] = []
    averments: List[str] = []
    red_flags: List[str] = []
    evidence: List[str] = []
    prereq: List[str] = []
    reliefs: List[str] = []

    for component_name in ("draft_family", "cause", "forum"):
        component = profile.get(component_name)
        if not component:
            continue
        sections.extend(component.get("required_sections", []))
        averments.extend(component.get("required_averments", []))
        red_flags.extend(component.get("drafting_red_flags", []))
        evidence.extend(component.get("evidence_checklist", []))
        prereq.extend(component.get("procedural_prerequisites", []))
        reliefs.extend(component.get("required_reliefs", []))

    profile["consolidated_required_sections"] = _dedupe_preserve_order(sections)
    profile["consolidated_required_averments"] = _dedupe_preserve_order(averments)
    profile["consolidated_required_reliefs"] = _dedupe_preserve_order(reliefs)
    profile["consolidated_prerequisites"] = _dedupe_preserve_order(prereq)
    profile["consolidated_evidence_checklist"] = _dedupe_preserve_order(evidence)
    profile["consolidated_red_flags"] = _dedupe_preserve_order(red_flags)

    return profile


def _dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


# ============================================================================
# FALLBACK CLASSIFIERS
# ============================================================================
# These are intentionally conservative. Primary classification should remain
# LLM or higher-order rule based.

def _score_keywords(text: str, keywords: List[str]) -> float:
    score = 0.0
    for kw in keywords:
        if kw.lower() in text:
            score += 1.0
    return score


def infer_draft_family(
    doc_type: str,
    user_request: str,
    topics: Optional[List[str]] = None,
) -> Tuple[str, float]:
    text = f"{doc_type} {user_request} {' '.join(topics or [])}".lower()

    best = ""
    best_score = 0.0

    for code, entry in DRAFT_FAMILIES.items():
        score = _score_keywords(text, entry.get("doc_type_keywords", []))
        if code == "interim_application_temp_injunction" and "order 39" in text:
            score += 0.75
        if code == "counter_claim" and "counter claim" in text:
            score += 0.75
        if code == "execution_petition" and ("execution" in text or "order 21" in text):
            score += 0.75
        if code == "appeal_first" and ("first appeal" in text or "section 96" in text):
            score += 0.75

        if score > best_score:
            best = code
            best_score = score

    if not best or best_score <= 0:
        return "", 0.0

    total = max(len(DRAFT_FAMILIES[best].get("doc_type_keywords", [])), 1)
    return best, min(best_score / total, 0.70)


def infer_substantive_cause(
    doc_type: str,
    user_request: str,
    topics: Optional[List[str]] = None,
) -> Tuple[str, float]:
    text = f"{doc_type} {user_request} {' '.join(topics or [])}".lower()

    best = ""
    best_score = 0.0

    for code, entry in SUBSTANTIVE_CAUSES.items():
        score = _score_keywords(text, entry.get("doc_type_keywords", []))

        # Soft disambiguation
        if code == "declaration_title" and ("possession" in text or "vacate" in text):
            score -= 0.5
        if code == "permanent_injunction" and ("declaration" in text or "title" in text):
            score -= 0.25
        if code == "summary_suit_instrument" and "order 37" in text:
            score += 0.75
        if code == "specific_performance" and "agreement to sell" in text:
            score += 0.5
        if code == "cancellation_instrument" and ("sale deed" in text or "gift deed" in text or "release deed" in text):
            score += 0.5
        if code == "recovery_of_possession" and ("unauthorized occupation" in text or "vacate" in text):
            score += 0.5

        if score > best_score:
            best = code
            best_score = score

    if not best or best_score <= 0:
        return "", 0.0

    total = max(len(SUBSTANTIVE_CAUSES[best].get("doc_type_keywords", [])), 1)
    return best, min(best_score / total, 0.70)


# Backward-compatible alias — enrichment.py imports this name
infer_cause_type = infer_substantive_cause


# ============================================================================
# SCREENERS / DECISION SUPPORT
# ============================================================================

def screen_forum_flags(
    *,
    cause_code: str,
    facts: Mapping[str, Any] | None = None,
) -> List[str]:
    facts = facts or {}
    flags: List[str] = []

    if cause_code in {"breach_of_contract", "breach_dealership_franchise", "breach_construction", "supply_service_contract"}:
        flags.append("arbitration_clause_screen")
        flags.append("commercial_dispute_screen")

    if cause_code in {"eviction", "arrears_of_rent", "mesne_profits_post_tenancy"}:
        flags.append("rent_act_bar_screen")
        flags.append("state_specific_tenancy_forum_screen")

    if cause_code in {"declaration_title", "recovery_of_possession", "partition", "easement"}:
        flags.append("property_schedule_and_boundary_screen")

    if facts.get("defendant_is_government"):
        flags.append("section_80_cpc_notice_screen")

    return _dedupe_preserve_order(flags)


def suggest_default_forum(
    *,
    cause_code: str,
    facts: Mapping[str, Any] | None = None,
) -> str:
    facts = facts or {}

    if cause_code == "eviction":
        return "rent_forum"

    if facts.get("is_commercial_dispute") and facts.get("specified_value", 0) >= COMMERCIAL_THRESHOLD:
        return "commercial_court"

    return "civil_court"


def suggest_default_draft_family(
    *,
    task_kind: str,
) -> str:
    mapping = {
        "institute_suit": "plaint",
        "defend_suit": "written_statement",
        "seek_setoff": "set_off",
        "assert_counterclaim": "counter_claim",
        "reply_to_ws": "replication",
        "seek_temp_injunction": "interim_application_temp_injunction",
        "seek_receiver": "interim_application_receiver",
        "seek_commission": "interim_application_commissioner",
        "seek_attachment_before_judgment": "interim_application_attachment_before_judgment",
        "appeal_decree": "appeal_first",
        "appeal_second": "appeal_second",
        "seek_stay": "stay_application",
        "review": "review_petition",
        "execute_decree": "execution_petition",
        "object_in_execution": "execution_objection",
        "lodge_caveat": "caveat",
    }
    return mapping.get(task_kind, "plaint")


# ============================================================================
# BASIC VALIDATION
# ============================================================================

def validate_master_base() -> List[str]:
    errors: List[str] = []

    for name, entry in DRAFT_FAMILIES.items():
        if entry.get("registry_kind") != "draft_family":
            errors.append(f"{name}: draft family registry_kind mismatch")
        if entry.get("code") != name:
            errors.append(f"{name}: draft family code mismatch")
        if not entry.get("required_sections"):
            errors.append(f"{name}: required_sections empty")

    for name, entry in SUBSTANTIVE_CAUSES.items():
        if entry.get("registry_kind") != "cause":
            errors.append(f"{name}: cause registry_kind mismatch")
        if entry.get("code") != name:
            errors.append(f"{name}: cause code mismatch")
        if not entry.get("doc_type_keywords"):
            errors.append(f"{name}: doc_type_keywords empty")

    # Hard legal guardrails built into this version
    rp = SUBSTANTIVE_CAUSES["recovery_of_possession"]
    if rp["primary_acts"][0]["sections"][0] != "Section 5":
        errors.append("recovery_of_possession: primary anchor must be Section 5 SRA")

    ss = SUBSTANTIVE_CAUSES["summary_suit_instrument"]
    resolved_ss = _resolved_copy(ss, {"instrument_type": "cheque"})
    if resolved_ss["limitation"].get("article") != "35":
        errors.append("summary_suit_instrument: cheque mapping should resolve to Article 35 in this version")

    tn_rules = resolve_conditional(SUBSTANTIVE_CAUSES["eviction"]["court_rules"], {"state": "Tamil Nadu"})
    tn_act = tn_rules["default"]["applicable_act"]
    if "2017" not in tn_act:
        errors.append("eviction: Tamil Nadu mapping should point to 2017 tenancy regime")

    sp = SUBSTANTIVE_CAUSES["specific_performance"]
    if "readiness_and_willingness" not in sp.get("required_averments", []):
        errors.append("specific_performance: readiness_and_willingness must remain a required averment")

    return errors


# ============================================================================
# HUMAN-FRIENDLY INDEXES
# ============================================================================

def list_draft_families() -> List[str]:
    return list(DRAFT_FAMILIES.keys())


def list_substantive_causes() -> List[str]:
    return list(SUBSTANTIVE_CAUSES.keys())


def list_forums() -> List[str]:
    return list(FORUM_REGISTRY.keys())


def search_registry(
    query: str,
    *,
    registry: str = "all",
) -> Dict[str, List[str]]:
    q = query.lower()

    registries = {
        "draft_family": DRAFT_FAMILIES,
        "cause": SUBSTANTIVE_CAUSES,
        "forum": FORUM_REGISTRY,
    }

    out: Dict[str, List[str]] = {"draft_family": [], "cause": [], "forum": []}

    for reg_name, reg in registries.items():
        if registry != "all" and registry != reg_name:
            continue

        for code, entry in reg.items():
            hay = " ".join(
                [code, entry.get("display_name", ""), " ".join(entry.get("doc_type_keywords", []))]
            ).lower()
            if q in hay:
                out[reg_name].append(code)

    return out


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def _example() -> None:
    """
    Quick smoke example.
    """
    draft_family, family_conf = infer_draft_family(
        doc_type="civil suit",
        user_request="Draft a plaint for recovery of possession with mesne profits after expiry of lease and notice to quit",
    )
    cause_code, cause_conf = infer_substantive_cause(
        doc_type="civil suit",
        user_request="Draft a plaint for recovery of possession with mesne profits after expiry of lease and notice to quit",
    )
    forum_code = suggest_default_forum(
        cause_code=cause_code or "recovery_of_possession",
        facts={"is_commercial_dispute": False},
    )
    profile = build_drafting_profile(
        draft_family=draft_family or "plaint",
        cause_code=cause_code or "recovery_of_possession",
        forum_code=forum_code,
        context={"occupancy_type": "tenant_determined"},
    )

    print("Draft family:", draft_family, family_conf)
    print("Cause:", cause_code, cause_conf)
    print("Forum:", forum_code)
    print("Required sections:", profile["consolidated_required_sections"])
    print("Red flags:", profile["consolidated_red_flags"])


if __name__ == "__main__":
    errs = validate_master_base()
    if errs:
        print("Validation errors:")
        for err in errs:
            print("-", err)
    else:
        print("Master base validation passed.")
    _example()

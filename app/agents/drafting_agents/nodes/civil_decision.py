from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from langgraph.graph import END
from langgraph.types import Command

from ....config import logger, settings
from ..lkb import lookup
from ..lkb.causes import CAUSE_GROUPS
from ..lkb.causes._family_defaults import get_family
from ..states import CivilDecision, DraftingState
from ._utils import _as_dict

_GROUP_TO_FAMILY = {
    "MONEY_AND_DEBT": "money_and_debt",
    "CONTRACT_AND_COMMERCIAL": "contract_and_commercial",
    "IMMOVABLE_PROPERTY": "immovable_property",
    "INJUNCTION_AND_DECLARATORY": "injunction_and_declaratory",
    "TORT_AND_CIVIL_WRONG": "tort_and_civil_wrong",
    "TENANCY_AND_RENT": "tenancy_and_rent",
    "ACCOUNTS_AND_RELATIONSHIP": "accounts_and_relationship",
    "PARTNERSHIP_AND_BUSINESS": "partnership_and_business",
    "IP_CIVIL": "ip_civil",
    "TRUST_AND_FIDUCIARY": "trust_and_fiduciary",
    "EXECUTION_AND_RESTITUTION": "execution_and_restitution",
    "SPECIAL_AND_MISCELLANEOUS": "special_and_miscellaneous",
    "SUCCESSION_AND_ESTATE": "succession_and_estate",
}

_CAUSE_TO_FAMILY = {
    cause: _GROUP_TO_FAMILY[group_name]
    for group_name, meta in CAUSE_GROUPS.items()
    if group_name in _GROUP_TO_FAMILY
    for cause in meta["causes"]
}

_TEMPLATE_FAMILIES = {
    "money_and_debt",
    "contract_and_commercial",
    "immovable_property",
    "injunction_and_declaratory",
    "tort_and_civil_wrong",
    "tenancy_and_rent",
    "accounts_and_relationship",
    "partnership_and_business",
    "ip_civil",
    "trust_and_fiduciary",
    "execution_and_restitution",
}

_GENERIC_POSSESSION_CAUSES = {
    "",
    "property_law",
    "eviction_unauthorized_occupation",
    "eviction_plaint",
    "possession_suit",
    "recovery_possession",
    "suit_for_possession",
    "recovery_of_possession",
}

_DOC_TYPE_CAUSE_FALLBACKS = {
    "specific_performance_plaint": "specific_performance",
    "partition_plaint": "partition",
    "permanent_injunction_plaint": "permanent_injunction",
    "mandatory_injunction_plaint": "mandatory_injunction",
}

_TENANT_HINTS = (
    "tenant",
    "tenancy",
    "lease",
    "rent",
    "landlord",
    "lessee",
    "monthly rent",
    "notice to quit",
    "section 106",
    "section 111",
)
_LICENSE_HINTS = (
    "licence",
    "license",
    "leave and licence",
    "leave and license",
    "permissive possession",
    "permission to occupy",
    "licensee",
    "section 52 easements",
    "revocation of licence",
    "revocation of license",
)
_CO_OWNER_HINTS = (
    "co-owner",
    "co owner",
    "co-sharer",
    "joint owner",
    "joint family property",
    "share in property",
    "ouster",
)
_TRESPASS_HINTS = (
    "trespass",
    "encroachment",
    "unauthorized occupation",
    "unauthorised occupation",
    "encroacher",
    "squatter",
)
_EVICTION_HINTS = (
    "rent control",
    "rent act",
    "rent controller",
    "bona fide requirement",
    "wilful default",
    "subletting",
    "eviction ground",
)


def _next_context_node() -> str:
    """Always route to enrichment — RAG disconnected (code kept, not called)."""
    return "enrichment"


def _dedupe_preserve(items: List[Any]) -> List[Any]:
    seen = set()
    result: List[Any] = []
    for item in items:
        key = repr(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _build_blocked_artifact(classify: Dict[str, Any], heading: str, issues: List[str]) -> Dict[str, Any]:
    doc_type = classify.get("doc_type", "civil_draft")
    lines = [heading, "", "The civil drafting pipeline stopped before finalization for the following reasons:"]
    for idx, issue in enumerate(issues, start=1):
        lines.append(f"{idx}. {issue}")
    lines.append("")
    lines.append("Clarify the above issues and rerun drafting.")
    return {
        "draft_artifacts": [
            {
                "doc_type": doc_type,
                "title": heading,
                "text": "\n".join(lines),
                "placeholders_used": [],
                "citations_used": [],
            }
        ]
    }


def _text_blob(user_request: str, classify: Dict[str, Any], intake: Dict[str, Any]) -> str:
    facts = _as_dict(intake.get("facts"))
    jurisdiction = _as_dict(intake.get("jurisdiction"))
    classification = _as_dict(classify.get("classification"))
    topics = classification.get("topics") or []
    parts = [
        user_request or "",
        classify.get("doc_type", "") or "",
        classify.get("cause_type", "") or "",
        facts.get("summary", "") or "",
        jurisdiction.get("court_type", "") or "",
        " ".join(str(topic) for topic in topics),
    ]
    return " ".join(parts).lower()


def _find_hits(text: str, tokens: Tuple[str, ...]) -> List[str]:
    return [token for token in tokens if token in text]


def _resolve_possession_track(text: str, doc_type: str) -> Tuple[Optional[str], List[str], str]:
    tenant_hits = _find_hits(text, _TENANT_HINTS)
    license_hits = _find_hits(text, _LICENSE_HINTS)
    co_owner_hits = _find_hits(text, _CO_OWNER_HINTS)
    trespass_hits = _find_hits(text, _TRESPASS_HINTS)
    eviction_hits = _find_hits(text, _EVICTION_HINTS)

    signals = {
        "tenant": tenant_hits,
        "licensee": license_hits,
        "co_owner": co_owner_hits,
        "trespasser": trespass_hits,
    }
    active_signals = [name for name, hits in signals.items() if hits]

    if len(active_signals) > 1:
        return (
            None,
            [
                "Ambiguous possession theory: multiple occupancy tracks detected "
                f"({', '.join(active_signals)}). Resolve tenant/licensee/trespasser/co-owner before drafting."
            ],
            "Multiple possession-track signals detected in facts/request.",
        )

    if co_owner_hits:
        return "recovery_of_possession_co_owner", [], "Resolved possession track from co-owner/ouster indicators."
    if license_hits:
        return "recovery_of_possession_licensee", [], "Resolved possession track from licence indicators."
    if eviction_hits:
        return "eviction", [], "Resolved tenancy dispute to eviction track from rent-control indicators."
    if tenant_hits or doc_type == "eviction_plaint":
        return "recovery_of_possession_tenant", [], "Resolved possession track from tenancy indicators."
    if trespass_hits:
        return "recovery_of_possession_trespasser", [], "Resolved possession track from trespass indicators."

    return (
        None,
        ["Ambiguous possession theory: occupancy basis is not clear from the request."],
        "Possession dispute detected, but occupancy basis could not be resolved.",
    )


def _resolve_accounts_relationship(text: str) -> str:
    lower = (text or "").lower()

    if any(token in lower for token in ("partner", "partnership", "firm", "partnership deed", "retiring partner")):
        return "partnership_accounts"
    if any(token in lower for token in ("agent", "agency", "principal", "commission agent", "on behalf of")):
        return "agency_accounts"
    if any(token in lower for token in ("trust", "trustee", "beneficiary", "fiduciary")):
        return "fiduciary_accounts"
    if any(token in lower for token in ("joint business", "joint venture", "shared profits", "profit share", "business venture")):
        return "joint_business_accounts"
    return "relationship_sensitive_accounts"


# ---------------------------------------------------------------------------
# Applicability Compiler — decides what law applies BEFORE drafting
# ---------------------------------------------------------------------------

_COMMERCIAL_KEYWORDS = (
    "commercial", "business", "trade", "supply", "vendor", "franchise",
    "construction", "dealership", "distributor", "mercantile",
)

_LIQUIDATED_DAMAGES_HINTS = (
    "liquidated damages", "penalty clause", "stipulated sum",
    "agreed damages", "pre-estimated", "section 74",
)

_ARBITRATION_HINTS = (
    "arbitration", "arbitral", "arbitrator", "section 8",
    "arbitration clause", "arbitration agreement",
)


_WORKMAN_HINTS = (
    "workman", "workmen", "industrial dispute", "industrial disputes act",
    "labour court", "labor court", "factory worker",
)

_RENT_ACT_HINTS = (
    "rent control", "rent act", "rent controller", "rent court",
    "rent tribunal",
)

_MACT_HINTS = (
    "motor accident", "motor vehicle", "mact", "motor vehicles act",
)

_CONSUMER_HINTS = (
    "consumer forum", "consumer commission", "consumer protection act",
    "consumer complaint", "consumer dispute",
)

_RERA_HINTS = (
    "rera", "real estate regulatory", "real estate authority",
    "homebuyer", "home buyer",
)

_MSMED_HINTS = (
    "msmed", "msme", "micro small medium", "micro, small and medium",
)


def _compile_applicability(
    entry: Dict[str, Any],
    user_request: str,
    intake: Dict[str, Any],
    classify: Dict[str, Any],
    family: str = "",
    cause_type: str = "",
) -> Dict[str, Any]:
    """Deterministic applicability compiler — filters LKB entry based on case facts.

    Dispatches to family-specific sub-compilers after running universal screening.

    Returns dict with:
      allowed_statutes, forbidden_statutes, allowed_reliefs, forbidden_reliefs,
      allowed_damages, forbidden_damages, filtered_red_flags
    """
    text = _text_blob(user_request, classify, intake).lower()
    facts = _as_dict(intake.get("facts"))
    amounts = _as_dict(facts.get("amounts") if isinstance(facts.get("amounts"), dict) else {})

    allowed_statutes: List[str] = []
    forbidden_statutes: List[str] = []
    allowed_reliefs: List[str] = []
    forbidden_reliefs: List[str] = []
    allowed_damages: List[str] = []
    forbidden_damages: List[str] = []
    allowed_doctrines: List[str] = []
    forbidden_doctrines: List[str] = []
    filtered_red_flags: List[str] = []

    # ===================================================================
    # UNIVERSAL SCREENING (all families)
    # ===================================================================

    # --- Common factual triggers used by multiple screeners ---
    has_liquidated = any(hint in text for hint in _LIQUIDATED_DAMAGES_HINTS)

    # --- Commercial Courts Act screening ---
    is_commercial = any(kw in text for kw in _COMMERCIAL_KEYWORDS)
    principal = amounts.get("principal") or 0
    suit_value_above_threshold = principal >= 300000  # Rs. 3 lakh

    if is_commercial and suit_value_above_threshold:
        allowed_statutes.append("Commercial Courts Act, 2015")
    else:
        forbidden_statutes.append("Commercial Courts Act, 2015")
        for rf in entry.get("drafting_red_flags", []):
            rf_lower = rf.lower()
            if "12a" in rf_lower or "commercial courts" in rf_lower or "commercial dispute" in rf_lower:
                continue
            if "arbitration" in rf_lower:
                continue
            if ("liquidated damages" in rf_lower or "s.74" in rf_lower or "section 74" in rf_lower) and not has_liquidated:
                continue
            filtered_red_flags.append(rf)

    # --- Section 74 / Liquidated Damages screening ---
    damages_categories = list(entry.get("damages_categories", []))

    for dc in damages_categories:
        if dc == "mitigation_credit":
            forbidden_damages.append(dc)
        elif dc == "liquidated_damages_s74" and not has_liquidated:
            forbidden_damages.append(dc)
        else:
            allowed_damages.append(dc)

    # --- Arbitration screening ---
    has_arbitration = any(hint in text for hint in _ARBITRATION_HINTS)
    if has_arbitration:
        for rf in entry.get("drafting_red_flags", []):
            if "arbitration" in rf.lower() and rf not in filtered_red_flags:
                filtered_red_flags.append(rf)

    # If we didn't filter red flags (non-commercial), use originals minus commercial
    if not filtered_red_flags:
        for rf in entry.get("drafting_red_flags", []):
            rf_lower = rf.lower()
            if "12a" in rf_lower or "commercial courts" in rf_lower or "commercial dispute" in rf_lower:
                continue
            if "arbitration" in rf_lower:
                continue
            if ("liquidated damages" in rf_lower or "s.74" in rf_lower or "section 74" in rf_lower) and not has_liquidated:
                continue
            filtered_red_flags.append(rf)

    # --- Reliefs ---
    for relief in entry.get("required_reliefs", []):
        allowed_reliefs.append(relief)

    # --- Doctrine screening ---
    # Filter permitted_doctrines based on factual support.
    # Doctrines that require specific factual triggers are forbidden when unsupported.
    _DOCTRINE_FACT_TRIGGERS = {
        "repudiatory_breach": ("repudiat", "refused to perform", "disabled", "refused", "abandon", "renounce"),
        "repudiatory_breach_s39": ("repudiat", "refused to perform", "disabled", "refused", "abandon", "renounce"),
        "anticipatory_breach": ("anticipat", "before due date", "advance refusal", "repudiat"),
        "anticipatory_breach_s39": ("anticipat", "before due date", "advance refusal", "repudiat"),
        "fundamental_breach": ("root of the contract", "fundamental", "goes to the root", "frustrat"),
        "liquidated_damages_s74": ("penalty clause", "stipulated sum", "liquidated damage", "penalty"),
        "damages_s74": ("penalty clause", "stipulated sum", "liquidated damage", "penalty"),
    }
    # Damages categories that need factual support — screened the same way
    _DAMAGE_FACT_TRIGGERS = {
        "consequential_loss": ("consequential", "foreseeable", "contemplat", "special damage", "indirect loss", "loss of profit", "loss of business"),
        "interest_on_delayed_payment": ("delayed payment", "late payment", "overdue", "payment default", "invoice unpaid", "unpaid invoice"),
    }
    # Screen damages_categories too (not just doctrines)
    screened_damages: List[str] = []
    for dc in allowed_damages:
        triggers = _DAMAGE_FACT_TRIGGERS.get(dc)
        if triggers:
            if not any(t in text for t in triggers):
                forbidden_damages.append(dc)
                continue
        screened_damages.append(dc)
    allowed_damages = screened_damages
    for doctrine in entry.get("permitted_doctrines", []):
        triggers = _DOCTRINE_FACT_TRIGGERS.get(doctrine)
        if triggers:
            if any(t in text for t in triggers):
                allowed_doctrines.append(doctrine)
            else:
                forbidden_doctrines.append(doctrine)
        else:
            allowed_doctrines.append(doctrine)

    # ===================================================================
    # FAMILY-SPECIFIC SCREENING
    # ===================================================================
    _ctx = _ApplicabilityContext(
        text=text, facts=facts, amounts=amounts, entry=entry,
        cause_type=cause_type, has_liquidated=has_liquidated,
        has_arbitration=has_arbitration, is_commercial=is_commercial and suit_value_above_threshold,
        allowed_statutes=allowed_statutes, forbidden_statutes=forbidden_statutes,
        allowed_reliefs=allowed_reliefs, forbidden_reliefs=forbidden_reliefs,
        allowed_damages=allowed_damages, forbidden_damages=forbidden_damages,
        allowed_doctrines=allowed_doctrines, forbidden_doctrines=forbidden_doctrines,
        filtered_red_flags=filtered_red_flags,
        relationship_track="",
    )

    if family == "contract_and_commercial":
        _compile_contract(_ctx)
    elif family == "money_and_debt":
        _compile_money(_ctx)
    elif family == "immovable_property":
        _compile_immovable_property(_ctx)
    elif family == "injunction_and_declaratory":
        _compile_injunction(_ctx)
    elif family == "tenancy_and_rent":
        _compile_tenancy(_ctx)
    elif family == "tort_and_civil_wrong":
        _compile_tort(_ctx)
    elif family == "accounts_and_relationship":
        _compile_accounts(_ctx)

    return {
        "allowed_statutes": _ctx.allowed_statutes,
        "forbidden_statutes": _ctx.forbidden_statutes,
        "allowed_reliefs": _ctx.allowed_reliefs,
        "forbidden_reliefs": _ctx.forbidden_reliefs,
        "allowed_damages": _ctx.allowed_damages,
        "forbidden_damages": _ctx.forbidden_damages,
        "allowed_doctrines": _ctx.allowed_doctrines,
        "forbidden_doctrines": _ctx.forbidden_doctrines,
        "filtered_red_flags": _ctx.filtered_red_flags,
        "relationship_track": _ctx.relationship_track,
        "is_commercial": _ctx.is_commercial,
    }


class _ApplicabilityContext:
    """Mutable context bag passed to family-specific sub-compilers."""
    __slots__ = (
        "text", "facts", "amounts", "entry", "cause_type",
        "has_liquidated", "has_arbitration", "is_commercial",
        "allowed_statutes", "forbidden_statutes",
        "allowed_reliefs", "forbidden_reliefs",
        "allowed_damages", "forbidden_damages",
        "allowed_doctrines", "forbidden_doctrines",
        "filtered_red_flags", "relationship_track",
    )

    def __init__(self, **kw: Any):
        for k, v in kw.items():
            setattr(self, k, v)


# ── Contract / Commercial family compiler ──────────────────────────────────

def _compile_contract(ctx: _ApplicabilityContext) -> None:
    """Family-specific screening for contract/commercial causes."""

    # S73 vs S74 mutual exclusivity — if both claimed, forbid S74 (stricter track)
    # unless facts explicitly show liquidated damages
    if not ctx.has_liquidated:
        if "section 74" in ctx.text:
            ctx.filtered_red_flags.append(
                "Facts do not show stipulated sum / penalty clause — "
                "Section 74 may be inapplicable. Plead under Section 73 only."
            )

    # Specific performance — S14 bars (personal service contracts, building contracts >threshold)
    if ctx.cause_type == "specific_performance":
        if any(kw in ctx.text for kw in ("personal service", "employment contract", "service agreement")):
            ctx.filtered_red_flags.append(
                "Personal service contracts cannot be specifically enforced (Section 14(1)(b) SRA)."
            )
        # Must plead readiness and willingness — add as red flag if not already present
        if not any("readiness" in rf.lower() for rf in ctx.filtered_red_flags):
            ctx.filtered_red_flags.append(
                "Readiness and willingness must be pleaded as ongoing fact, not formula (Section 16(c) SRA)."
            )

    # RERA homebuyer — RERA authority has exclusive jurisdiction
    if ctx.cause_type == "rera_homebuyer" or any(kw in ctx.text for kw in _RERA_HINTS):
        if ctx.cause_type == "rera_homebuyer":
            ctx.filtered_red_flags.append(
                "RERA homebuyer claims lie before RERA Authority — civil court jurisdiction "
                "may be barred under Section 79 RERA, 2016."
            )

    # Workman exclusion — IDA workers must go to Labour Court
    if any(kw in ctx.text for kw in _WORKMAN_HINTS):
        if ctx.cause_type in ("employment_termination", "breach_of_contract"):
            ctx.filtered_red_flags.append(
                "If plaintiff qualifies as 'workman' under Industrial Disputes Act, "
                "civil court jurisdiction is barred — claim lies before Labour Court."
            )

    # Guarantee vs indemnity — mutually exclusive legal tracks
    if ctx.cause_type in ("guarantee_invocation", "guarantee_recovery"):
        # S126 applies, not S124
        ctx.filtered_red_flags.append(
            "Guarantee: plead under Section 126-147 Indian Contract Act. "
            "Do NOT cite Section 124 (indemnity)."
        )
    elif ctx.cause_type == "indemnity_claim":
        ctx.filtered_red_flags.append(
            "Indemnity: plead under Section 124-125 Indian Contract Act. "
            "Do NOT cite Section 126 (guarantee)."
        )


# ── Money / Debt family compiler ───────────────────────────────────────────

def _compile_accounts(ctx: _ApplicabilityContext) -> None:
    """Family-specific screening for accounts/relationship causes.

    The duty to account arises from the relationship (agency, partnership,
    fiduciary, joint business) — not from a debt. The compiler resolves the
    relationship subtype and sets allowed/forbidden statutes accordingly.
    """
    ctx.relationship_track = _resolve_accounts_relationship(ctx.text)

    ctx.filtered_red_flags.append(
        "Rendition of accounts is relationship-sensitive: plead clearly whether "
        "the duty to account arises from agency, partnership, joint business "
        "management, or another fiduciary arrangement."
    )
    ctx.filtered_red_flags.append(
        "Accounts suit: seek a preliminary decree for rendition / taking of "
        "accounts and a final decree for the amount found due under Order XX "
        "Rule 16 CPC."
    )
    ctx.filtered_red_flags.append(
        "Do NOT treat rendition of accounts as a generic money recovery / "
        "damages claim. Plead the relationship, the duty to account, the "
        "accounting period, and the amount found due after accounts."
    )

    # Relationship-specific statute allowance
    if ctx.relationship_track == "agency_accounts":
        if "Indian Contract Act, 1872" not in ctx.allowed_statutes:
            ctx.allowed_statutes.append("Indian Contract Act, 1872")
    elif ctx.relationship_track == "partnership_accounts":
        if "Indian Partnership Act, 1932" not in ctx.allowed_statutes:
            ctx.allowed_statutes.append("Indian Partnership Act, 1932")
        ctx.filtered_red_flags.append(
            "If the arrangement is a partnership, plead the partnership basis, "
            "share ratio, access to books, and whether the relief sought is "
            "pure accounts or dissolution and accounts."
        )
    elif ctx.relationship_track == "joint_business_accounts":
        ctx.filtered_red_flags.append(
            "Joint-business accounts: plead the profit-sharing arrangement, "
            "the Defendant's exclusive control of books / receipts, and the "
            "Plaintiff's inability to ascertain profits without court-supervised "
            "accounting."
        )
    elif ctx.relationship_track == "fiduciary_accounts":
        ctx.filtered_red_flags.append(
            "Fiduciary accounts: identify the entrustment of funds / management "
            "and the Defendant's obligation to communicate and account faithfully."
        )

    # Forbidden damages — accounts suits are NOT damages suits
    for forbidden in (
        "actual_loss", "consequential_loss",
        "interest_on_delayed_payment", "liquidated_damages_s74",
    ):
        if forbidden not in ctx.forbidden_damages:
            ctx.forbidden_damages.append(forbidden)


def _compile_money(ctx: _ApplicabilityContext) -> None:
    """Family-specific screening for money/debt causes."""

    # Workman exclusion
    if any(kw in ctx.text for kw in _WORKMAN_HINTS):
        ctx.filtered_red_flags.append(
            "Workman wage/dues claims lie before Labour Court under IDA — "
            "not maintainable in civil court."
        )

    # MSMED compliance — MSMED supplier must first approach MSMED Council
    if ctx.cause_type == "msmed_recovery" or any(kw in ctx.text for kw in _MSMED_HINTS):
        ctx.filtered_red_flags.append(
            "MSMED suppliers must refer to Micro and Small Enterprise Facilitation Council "
            "under Section 18 MSMED Act, 2006 before civil suit."
        )

    # Cheque bounce — S138 NI Act has specific prerequisites
    if ctx.cause_type == "cheque_bounce_civil":
        ctx.filtered_red_flags.append(
            "Cheque bounce: demand notice within 30 days of dishonour (S138 proviso) "
            "and 15-day waiting period are mandatory prerequisites."
        )

    # Summary suit — Order XXXVII has limited applicability
    if ctx.cause_type in ("summary_suit", "summary_suit_instrument"):
        ctx.filtered_red_flags.append(
            "Order XXXVII summary suit available only for: (a) bill of exchange/promissory note, "
            "(b) written contract for liquidated amount. Verify eligibility."
        )
        # Summary suit not available in every court
        if not ctx.is_commercial:
            ctx.filtered_red_flags.append(
                "Order XXXVII summary suit is available only in High Courts, City Civil Courts, "
                "and courts notified by the State Government — verify forum eligibility."
            )

    # Excessive interest — flag if contractual rate exceeds reasonable threshold
    principal = ctx.amounts.get("principal") or 0
    interest_rate = ctx.amounts.get("interest_rate") or 0
    if interest_rate and interest_rate > 24:
        ctx.filtered_red_flags.append(
            f"Contractual interest rate {interest_rate}% exceeds 24% — courts may reduce "
            "to reasonable rate. Plead contractual basis with supporting evidence."
        )

    # Insurance claim — insurer's forum may be exclusive
    if ctx.cause_type == "insurance_claim":
        if any(kw in ctx.text for kw in _CONSUMER_HINTS):
            ctx.filtered_red_flags.append(
                "Insurance disputes may lie before Consumer Forum — verify if "
                "Consumer Protection Act provides exclusive/alternative remedy."
            )


# ── Immovable Property family compiler ─────────────────────────────────────

def _compile_immovable_property(ctx: _ApplicabilityContext) -> None:
    """Family-specific screening for immovable property causes (partition, possession, easement, etc.)."""

    # Partition — pre/post 2005 Hindu Succession Act amendment
    if ctx.cause_type in ("partition", "partition_ancestral"):
        # Check if Hindu joint family property
        has_hindu_context = any(
            kw in ctx.text for kw in ("hindu", "coparcener", "coparcenary", "joint family", "ancestral property")
        )
        if has_hindu_context:
            ctx.filtered_red_flags.append(
                "Partition of Hindu joint family property: clarify whether property is "
                "ancestral/coparcenary. Post-2005 amendment (Vineeta Sharma v Kumar, 2020): "
                "daughters are coparceners by birth regardless of father's death date."
            )

        # Art 110 vs Art 65 limitation
        ctx.filtered_red_flags.append(
            "Partition limitation: use Article 110 (12 years from exclusion) for joint family property, "
            "NOT Article 65 (general immovable property)."
        )

    # Adverse possession — different limitation track
    if ctx.cause_type == "adverse_possession":
        ctx.filtered_red_flags.append(
            "Adverse possession: 12-year limitation under Article 65 for private land, "
            "30 years for government land (Article 112). Plead uninterrupted, hostile, "
            "open possession with animus possidendi."
        )

    # ── Recovery of possession — track-specific screening ──────────────
    if ctx.cause_type.startswith("recovery_of_possession"):
        # Rent Act bar for ALL possession tracks
        has_rent_act = any(kw in ctx.text for kw in _RENT_ACT_HINTS)
        if has_rent_act:
            ctx.filtered_red_flags.append(
                "CRITICAL: If premises are protected under state Rent Control Act, "
                "civil suit for possession NOT maintainable — remedy before Rent Controller."
            )

        # S5 vs S6 SRA — title-based vs summary recovery
        has_recent_dispossession = any(
            kw in ctx.text for kw in ("dispossessed within", "within six months", "within 6 months", "summary recovery")
        )
        if has_recent_dispossession:
            ctx.filtered_red_flags.append(
                "If dispossession occurred within 6 months, consider Section 6 SRA summary recovery "
                "(no title proof needed). S.6 has strict 6-month bar — verify accrual date."
            )

    if ctx.cause_type == "recovery_of_possession_tenant":
        # Must plead HOW tenancy was determined
        ctx.filtered_red_flags.append(
            "Tenant recovery: explicitly plead tenancy determination basis — efflux of time "
            "(S.111(a) TPA), forfeiture (S.111(g) TPA), or notice to quit (S.106 TPA)."
        )
        # S106 notice compliance
        ctx.filtered_red_flags.append(
            "Verify S.106 TPA notice: 15 days for monthly tenancy, 6 months for yearly tenancy, "
            "or as per lease terms. Notice must EXPIRE before filing suit."
        )
        # Forbid Easements Act footing
        ctx.forbidden_statutes.append("Indian Easements Act, 1882")
        ctx.filtered_red_flags.append(
            "Tenant track: do NOT cite Easements Act (S.52/60-63). "
            "Tenancy is governed by Transfer of Property Act, not Easements Act."
        )

    elif ctx.cause_type == "recovery_of_possession_licensee":
        # Must use Easements Act footing, NOT TPA
        ctx.forbidden_statutes.append("Transfer of Property Act, 1882 — Section 106")
        ctx.forbidden_statutes.append("Transfer of Property Act, 1882 — Section 111")
        ctx.filtered_red_flags.append(
            "Licensee track: plead under Indian Easements Act, S.52/60-63. "
            "Do NOT cite S.106/S.111 TPA (those are tenancy provisions). "
            "Licence is revocable at will — plead revocation notice."
        )
        # Licence vs tenancy classification is the key legal issue
        ctx.filtered_red_flags.append(
            "CRITICAL: Distinguish licence from tenancy — exclusive possession + rent + defined term "
            "= tenancy (TPA S.105), NOT licence. If wrongly classified, suit fails for wrong footing."
        )

    elif ctx.cause_type == "recovery_of_possession_trespasser":
        # No contractual relationship — pure title-based recovery
        ctx.filtered_red_flags.append(
            "Trespasser track: plead title + right to possession under S.5 SRA. "
            "No lease/licence determination needed. Plead date of encroachment and steps taken."
        )
        # Forbid tenancy/licence statutes
        ctx.forbidden_statutes.append("Transfer of Property Act, 1882 — Section 106")
        ctx.forbidden_statutes.append("Transfer of Property Act, 1882 — Section 111")
        ctx.forbidden_statutes.append("Indian Easements Act, 1882")
        ctx.filtered_red_flags.append(
            "Trespasser: do NOT cite S.106/S.111 TPA or Easements Act — "
            "no contractual relationship exists with a trespasser."
        )

    elif ctx.cause_type == "recovery_of_possession_co_owner":
        # Co-owner must plead ouster — mere co-ownership is not enough
        ctx.filtered_red_flags.append(
            "Co-owner recovery: must plead OUSTER — that co-owner was denied access or excluded. "
            "Mere co-ownership without denial of access is not a cause of action for possession."
        )
        # May also have partition right
        ctx.filtered_red_flags.append(
            "Consider whether partition suit is more appropriate — co-owner may file "
            "suit for partition and separate possession under Order XX Rule 18 CPC."
        )

    # Situs jurisdiction for all immovable property suits
    ctx.filtered_red_flags.append(
        "Immovable property suit: jurisdiction lies under Section 16 CPC (situs of property), "
        "NOT under Section 20 (defendant's residence)."
    )


# ── Injunction / Declaratory family compiler ──────────────────────────────

# Hint keywords for injunction screening
_INFRASTRUCTURE_HINTS = (
    "infrastructure", "highway", "national project", "public road",
    "railway", "metro", "airport", "government project", "public utility",
)

_DELAY_ACQUIESCENCE_HINTS = (
    "since long", "several years", "many years", "for years",
    "acquiesced", "acquiescence", "stood by", "did not object",
    "delayed", "long delay", "inordinate delay",
)

def _compile_injunction(ctx: _ApplicabilityContext) -> None:
    """Family-specific screening for injunction and declaratory causes."""

    # ── Permanent injunction (S.38 SRA) ──
    if ctx.cause_type == "permanent_injunction":
        # Three mandatory elements — plead all three
        ctx.filtered_red_flags.append(
            "Permanent injunction (S.38 SRA): plead all 3 elements — "
            "(1) plaintiff's legal right, (2) invasion/threat by defendant, "
            "(3) damages would be inadequate remedy."
        )

        # S.41 SRA — 10 clauses of non-grantability including (ha) infrastructure bar
        if any(kw in ctx.text for kw in _INFRASTRUCTURE_HINTS):
            ctx.filtered_red_flags.append(
                "S.41(ha) SRA (2018 Amendment): injunction CANNOT be granted against "
                "infrastructure projects of national importance. Verify if defendant's activity "
                "falls under this bar."
            )

        # Delay and acquiescence bar
        if any(kw in ctx.text for kw in _DELAY_ACQUIESCENCE_HINTS):
            ctx.filtered_red_flags.append(
                "Delay/acquiescence may bar injunction — plead that plaintiff acted promptly "
                "and did not acquiesce. Address timeline of interference vs filing."
            )

    # ── Mandatory injunction (S.39 SRA) ──
    elif ctx.cause_type == "mandatory_injunction":
        ctx.filtered_red_flags.append(
            "Mandatory injunction (S.39 SRA) is EXCEPTIONAL — court grants only when: "
            "(1) strong prima facie case, (2) balance of convenience clearly in favour, "
            "(3) irreparable harm. Stricter threshold than prohibitory injunction."
        )
        ctx.filtered_red_flags.append(
            "Delay is MORE fatal for mandatory injunction — if unauthorized construction "
            "is substantially complete, court may award damages instead of demolition. "
            "Plead promptness and plead demolition + damages as alternatives."
        )

    # ── Declaration of title (S.34 SRA) ──
    elif ctx.cause_type == "declaration_title":
        ctx.filtered_red_flags.append(
            "Declaration (S.34 SRA): plaintiff must show existing legal character/right that "
            "defendant denies or is interested to deny. Cannot declare future rights."
        )
        ctx.filtered_red_flags.append(
            "S.34 proviso: if plaintiff could seek FURTHER relief (e.g. possession, injunction) "
            "but does not, court MUST refuse bare declaration. Always plead consequential relief."
        )

    # ── Property-based injunction — situs jurisdiction ──
    property_based = any(
        kw in ctx.text for kw in (
            "land", "property", "survey", "immovable", "plot", "house",
            "building", "flat", "revenue", "mutation", "agricultural",
        )
    )
    if property_based:
        ctx.filtered_red_flags.append(
            "Property injunction: jurisdiction under S.16 CPC (situs of property), "
            "NOT S.20 (defendant's residence)."
        )
    else:
        # Non-property injunction (e.g. restraining defamation, business interference)
        ctx.filtered_red_flags.append(
            "Non-property injunction: jurisdiction under S.20 CPC "
            "(defendant's residence or cause of action)."
        )

    # ── Bare injunction — no interest/damages section ──
    if ctx.cause_type in ("permanent_injunction", "mandatory_injunction"):
        # Forbid S.34 CPC interest footing for bare injunction
        ctx.filtered_red_flags.append(
            "Bare injunction suit: do NOT include standalone INTEREST section or "
            "cite S.34 CPC for pendente lite interest — this is not a money suit."
        )
        # No money damages decree in prayer
        ctx.filtered_red_flags.append(
            "Injunction prayer: seek specific injunctive relief (restrain/direct), "
            "NOT a money damages decree. Costs are appropriate."
        )


# ── Tenancy / Rent family compiler ────────────────────────────────────────

def _compile_tenancy(ctx: _ApplicabilityContext) -> None:
    """Family-specific screening for tenancy/rent causes."""

    # Rent Act bar — if premises are protected, civil court has NO jurisdiction
    has_rent_act = any(kw in ctx.text for kw in _RENT_ACT_HINTS)
    if has_rent_act:
        ctx.filtered_red_flags.append(
            "CRITICAL: If premises are protected under state Rent Control Act, "
            "civil court has NO jurisdiction for eviction — file before Rent Controller. "
            "Verify exemption/non-applicability before proceeding."
        )
    else:
        ctx.filtered_red_flags.append(
            "Verify whether premises fall under state Rent Control Act. "
            "If protected, civil suit for eviction is NOT maintainable."
        )

    # S106 TPA — notice to determine lease is mandatory
    if ctx.cause_type == "eviction":
        ctx.filtered_red_flags.append(
            "Eviction requires valid notice to determine lease under Section 106 TPA. "
            "Notice must be: (a) 15 days for monthly tenancy, (b) 6 months for yearly tenancy, "
            "(c) as per lease terms if specified. Plead notice compliance."
        )

    # Mesne profits post-tenancy — must plead tenancy termination first
    if ctx.cause_type == "mesne_profits_post_tenancy":
        ctx.filtered_red_flags.append(
            "Mesne profits: plead that tenancy has been lawfully determined, "
            "and defendant continues in wrongful occupation. Use Order XX Rule 12 CPC."
        )

    # State-specific forum — different states have different rent courts
    ctx.filtered_red_flags.append(
        "Forum: verify state-specific Rent Act forum — Rent Controller (most states), "
        "Small Causes Court (Maharashtra, Gujarat), Rent Tribunal (some states)."
    )


# ── Tort / Civil Wrong family compiler ─────────────────────────────────────

def _compile_tort(ctx: _ApplicabilityContext) -> None:
    """Family-specific screening for tort/civil wrong causes."""

    # MACT exclusion — motor accident claims go to MACT
    if any(kw in ctx.text for kw in _MACT_HINTS):
        if ctx.cause_type not in ("medical_negligence",):
            ctx.forbidden_statutes.append("Motor Vehicles Act, 1988")
            ctx.filtered_red_flags.append(
                "Motor accident claims lie EXCLUSIVELY before Motor Accident Claims Tribunal "
                "(MACT) under Motor Vehicles Act, 1988 — NOT civil court."
            )

    # Consumer forum exclusion
    if any(kw in ctx.text for kw in _CONSUMER_HINTS):
        ctx.filtered_red_flags.append(
            "If plaintiff qualifies as 'consumer' under Consumer Protection Act, 2019, "
            "consumer forum may be the appropriate/exclusive remedy."
        )

    # Short limitation torts — 1 year
    if ctx.cause_type == "defamation_civil":
        ctx.filtered_red_flags.append(
            "Defamation: 1-year limitation under Article 75 Limitation Act, 1963. "
            "Verify accrual date — limitation runs from date of publication/utterance."
        )
    elif ctx.cause_type == "false_imprisonment":
        ctx.filtered_red_flags.append(
            "False imprisonment: 1-year limitation under Article 73 Limitation Act, 1963."
        )
    elif ctx.cause_type == "malicious_prosecution":
        ctx.filtered_red_flags.append(
            "Malicious prosecution: 1-year limitation under Article 74 Limitation Act, 1963. "
            "Must plead: (a) prosecution by defendant, (b) without reasonable cause, "
            "(c) with malice, (d) termination in plaintiff's favour."
        )

    # Medical negligence — Bolam test
    if ctx.cause_type == "medical_negligence":
        ctx.filtered_red_flags.append(
            "Medical negligence: plead deviation from accepted medical practice (Bolam test). "
            "Expert medical opinion is essential evidence. 3-year limitation under Article 113 (residual article)."
        )
        # Consumer forum may also have jurisdiction
        ctx.filtered_red_flags.append(
            "Medical negligence: Consumer Protection Act, 2019 also provides remedy — "
            "consider whether consumer forum is more appropriate."
        )

    # Negligence — must plead all 4 elements
    if ctx.cause_type == "negligence":
        ctx.filtered_red_flags.append(
            "Negligence: plead all 4 elements — (1) duty of care, (2) breach, "
            "(3) causation, (4) damage. Missing any element defeats the claim."
        )

    # Public nuisance — special damage or AG authorization
    if ctx.cause_type == "nuisance_public":
        ctx.filtered_red_flags.append(
            "Public nuisance: civil action by private individual requires either "
            "(a) special damage beyond common injury, or (b) Attorney/Advocate General authorization."
        )

    # Slander — special damage required unless actionable per se
    if ctx.cause_type == "defamation_civil":
        if "slander" in ctx.text:
            ctx.filtered_red_flags.append(
                "Slander (oral defamation): must plead special damage unless words are "
                "actionable per se (imputation of crime, loathsome disease, unchastity, "
                "or affecting profession/trade)."
            )


def _resolve_cause_type(classify: Dict[str, Any], intake: Dict[str, Any], user_request: str) -> Tuple[str, List[str], str, float]:
    raw_cause_type = (classify.get("cause_type") or "").strip()
    doc_type = (classify.get("doc_type") or "").strip()
    text = _text_blob(user_request, classify, intake)

    if raw_cause_type in _GENERIC_POSSESSION_CAUSES or (
        "possession" in doc_type and raw_cause_type not in _CAUSE_TO_FAMILY
    ):
        resolved, issues, reason = _resolve_possession_track(text, doc_type)
        return resolved or "", issues, reason, 0.75 if resolved else 0.35

    if not raw_cause_type and doc_type in _DOC_TYPE_CAUSE_FALLBACKS:
        resolved = _DOC_TYPE_CAUSE_FALLBACKS[doc_type]
        return resolved, [], f"Resolved cause_type from doc_type={doc_type}.", 0.8

    if raw_cause_type:
        entry = lookup("Civil", raw_cause_type)
        if entry:
            resolved = entry.get("code", raw_cause_type)
            confidence = 0.95 if resolved == raw_cause_type else 0.85
            reason = "Matched civil LKB entry." if resolved == raw_cause_type else "Normalized cause_type via civil LKB alias."
            return resolved, [], reason, confidence

    return raw_cause_type, [], "No deterministic civil normalization applied.", 0.5 if raw_cause_type else 0.0


def civil_case_resolver_node(state: DraftingState) -> Command:
    user_request = (state.get("user_request") or "").strip()
    intake = _as_dict(state.get("intake"))
    classify = _as_dict(state.get("classify"))
    law_domain = classify.get("law_domain", "")
    raw_cause_type = (classify.get("cause_type") or "").strip()

    if law_domain != "Civil":
        decision = CivilDecision(
            enabled=False,
            status="not_applicable",
            route_reason=f"Civil resolver skipped for law_domain={law_domain or 'unknown'}.",
        )
        return Command(update={"civil_decision": decision.model_dump()}, goto=_next_context_node())

    resolved_cause, blocking_issues, route_reason, confidence = _resolve_cause_type(classify, intake, user_request)
    entry = lookup("Civil", resolved_cause) if resolved_cause else None
    family = _CAUSE_TO_FAMILY.get(resolved_cause, "unsupported") if resolved_cause else "unsupported"
    template_eligible = bool(entry) and family in _TEMPLATE_FAMILIES and not blocking_issues
    draft_strategy = "template_first" if template_eligible else "free_text"

    if resolved_cause and resolved_cause != classify.get("cause_type"):
        classify["cause_type"] = resolved_cause

    # Run applicability compiler — decides what law applies BEFORE drafting
    applicability = _compile_applicability(
        entry or {}, user_request, intake, classify,
        family=family, cause_type=resolved_cause,
    ) if entry else {}

    decision = CivilDecision(
        enabled=True,
        family=family,
        original_cause_type=raw_cause_type or None,
        resolved_cause_type=resolved_cause or None,
        relationship_track=applicability.get("relationship_track") or None,
        status=(
            "ambiguous"
            if blocking_issues
            else "resolved"
            if entry and family != "unsupported"
            else "unsupported"
        ),
        draft_strategy=draft_strategy,
        template_eligible=template_eligible,
        maintainability_checks=list(entry.get("procedural_prerequisites", [])) if entry else [],
        ambiguity_flags=list(blocking_issues),
        blocking_issues=list(blocking_issues),
        limitation=dict(entry.get("limitation", {})) if entry else {},
        allowed_statutes=applicability.get("allowed_statutes", []),
        forbidden_statutes=applicability.get("forbidden_statutes", []),
        allowed_reliefs=applicability.get("allowed_reliefs", []),
        forbidden_reliefs=applicability.get("forbidden_reliefs", []),
        allowed_damages=applicability.get("allowed_damages", []),
        forbidden_damages=applicability.get("forbidden_damages", []),
        allowed_doctrines=applicability.get("allowed_doctrines", []),
        forbidden_doctrines=applicability.get("forbidden_doctrines", []),
        filtered_red_flags=applicability.get("filtered_red_flags", []),
        route_reason=route_reason,
        confidence=confidence,
    )

    logger.info(
        "[CIVIL_RESOLVER] domain=%s raw=%s resolved=%s family=%s strategy=%s issues=%d",
        law_domain,
        raw_cause_type,
        decision.resolved_cause_type,
        decision.family,
        decision.draft_strategy,
        len(decision.blocking_issues),
    )
    return Command(update={"classify": classify, "civil_decision": decision.model_dump()}, goto="civil_ambiguity_gate")


def civil_ambiguity_gate_node(state: DraftingState) -> Command:
    classify = _as_dict(state.get("classify"))
    decision = _as_dict(state.get("civil_decision"))
    blocking_issues = [str(i) for i in (decision.get("blocking_issues") or []) if str(i).strip()]

    if classify.get("law_domain") != "Civil" or not decision.get("enabled"):
        return Command(goto=_next_context_node())

    if not blocking_issues:
        return Command(update={"civil_gate_issues": []}, goto=_next_context_node())

    combined_errors = list(state.get("errors") or [])
    combined_errors.extend(blocking_issues)
    issues = [
        {
            "type": "civil_ambiguity_block",
            "severity": "blocking",
            "issue": issue,
            "fix": "Clarify the civil facts and rerun drafting.",
        }
        for issue in blocking_issues
    ]
    blocked = _build_blocked_artifact(classify, "CLARIFICATION REQUIRED", blocking_issues)

    logger.info("[CIVIL_AMBIGUITY_GATE] blocked civil drafting | issues=%d", len(blocking_issues))
    return Command(
        update={
            "errors": combined_errors,
            "civil_gate_issues": issues,
            "draft": blocked,
            "final_draft": blocked,
        },
        goto=END,
    )


def civil_draft_plan_compiler_node(state: DraftingState) -> Command:
    classify = _as_dict(state.get("classify"))
    decision = _as_dict(state.get("civil_decision"))
    mandatory_provisions = _as_dict(state.get("mandatory_provisions"))
    lkb_brief = _as_dict(state.get("lkb_brief"))

    if classify.get("law_domain") != "Civil" or not decision.get("enabled"):
        return Command(update={"civil_draft_plan": None}, goto="civil_draft_router")

    cause_type = decision.get("resolved_cause_type") or classify.get("cause_type", "")
    entry = lkb_brief if lkb_brief else (lookup("Civil", cause_type) or {})
    classification = _as_dict(classify.get("classification"))
    verified_provisions = mandatory_provisions.get("verified_provisions") or []
    limitation = mandatory_provisions.get("limitation") or decision.get("limitation") or entry.get("limitation", {})

    # Use applicability compiler output (decision) when available, fall back to raw LKB entry
    _decision_allowed_reliefs = decision.get("allowed_reliefs") or []
    _decision_forbidden_reliefs = set(decision.get("forbidden_reliefs") or [])
    _decision_has_filtered_red_flags = "filtered_red_flags" in decision
    _decision_filtered_red_flags = decision.get("filtered_red_flags") or []
    _decision_forbidden_statutes = set(decision.get("forbidden_statutes") or [])
    _decision_forbidden_damages = set(decision.get("forbidden_damages") or [])

    # Reliefs: use decision.allowed_reliefs if populated, else entry minus forbidden
    raw_required_reliefs = list(entry.get("required_reliefs", []))
    if _decision_allowed_reliefs:
        required_reliefs = list(_decision_allowed_reliefs)
    else:
        required_reliefs = [r for r in raw_required_reliefs if r not in _decision_forbidden_reliefs]
    optional_reliefs = [r for r in entry.get("optional_reliefs", []) if r not in _decision_forbidden_reliefs]

    # Red flags: use applicability-compiled list whenever decision_ir carries it,
    # even if the correct filtered result is an empty list.
    if _decision_has_filtered_red_flags:
        red_flags = list(_decision_filtered_red_flags)
    else:
        red_flags = list(entry.get("drafting_red_flags", []))

    required_sections = list(entry.get("required_sections", []))
    inline_sections = list(entry.get("mandatory_inline_sections", []))
    evidence_checklist = list(entry.get("evidence_checklist", []))
    maintainability_checks = list(decision.get("maintainability_checks") or [])
    missing_fields = list(classification.get("missing_fields") or [])
    required_averments = list(entry.get("required_averments", []))

    claim_ledger: List[Dict[str, Any]] = []
    for relief in required_reliefs:
        claim_ledger.append(
            {
                "claim_kind": "relief",
                "key": relief,
                "status": "required",
                "source": "lkb",
                "cause_type": cause_type,
            }
        )
    for provision in verified_provisions:
        if isinstance(provision, dict):
            claim_ledger.append(
                {
                    "claim_kind": "citation",
                    "key": provision.get("section", ""),
                    "status": "verified",
                    "source": provision.get("source", ""),
                    "act": provision.get("act", ""),
                }
            )

    draft_plan = {
        "family": decision.get("family"),
        "cause_type": cause_type,
        "relationship_track": decision.get("relationship_track", ""),
        "route_reason": decision.get("route_reason", ""),
        "required_sections": _dedupe_preserve(required_sections),
        "required_reliefs": _dedupe_preserve(required_reliefs),
        "optional_reliefs": _dedupe_preserve(optional_reliefs),
        "required_averments": _dedupe_preserve(required_averments),
        "mandatory_inline_sections": inline_sections,
        "maintainability_checks": _dedupe_preserve(maintainability_checks),
        "limitation": limitation,
        "verified_provisions": verified_provisions,
        "evidence_checklist": _dedupe_preserve(evidence_checklist),
        "red_flags": _dedupe_preserve(red_flags),
        "missing_fields": _dedupe_preserve(missing_fields),
        # Propagate applicability compiler decisions into plan for plan_ir mirroring
        "allowed_statutes": list(decision.get("allowed_statutes") or []),
        "forbidden_statutes": list(decision.get("forbidden_statutes") or []),
        "allowed_reliefs": _dedupe_preserve(required_reliefs),  # already filtered
        "forbidden_reliefs": list(decision.get("forbidden_reliefs") or []),
        "allowed_damages": list(decision.get("allowed_damages") or []),
        "forbidden_damages": list(decision.get("forbidden_damages") or []),
        "allowed_doctrines": list(decision.get("allowed_doctrines") or []),
        "forbidden_doctrines": list(decision.get("forbidden_doctrines") or []),
        "filtered_red_flags": _dedupe_preserve(red_flags),  # already filtered
    }

    logger.info(
        "[CIVIL_DRAFT_PLAN] family=%s cause=%s sections=%d reliefs=%d citations=%d",
        decision.get("family"),
        cause_type,
        len(required_sections),
        len(required_reliefs),
        len(verified_provisions),
    )
    return Command(
        update={
            "civil_draft_plan": draft_plan,
            "claim_ledger": claim_ledger,
        },
        goto="civil_draft_router",
    )


def civil_draft_router_node(state: DraftingState) -> Command:
    classify = _as_dict(state.get("classify"))
    decision = _as_dict(state.get("civil_decision"))

    template_enabled = getattr(settings, "TEMPLATE_ENGINE_ENABLED", False)

    if not template_enabled:
        # Global setting overrides — always use freetext when template engine is off
        goto = "draft_freetext"
    elif classify.get("law_domain") == "Civil" and decision.get("draft_strategy") == "template_first":
        goto = "draft_template_fill"
    elif (
        classify.get("law_domain") == "Civil"
        and not decision.get("blocking_issues")
    ):
        goto = "draft_template_fill"
    else:
        goto = "draft_freetext"

    logger.info(
        "[CIVIL_DRAFT_ROUTER] domain=%s strategy=%s goto=%s",
        classify.get("law_domain"),
        decision.get("draft_strategy"),
        goto,
    )
    return Command(goto=goto)


def _extract_draft_text(state: DraftingState) -> str:
    draft = _as_dict(state.get("draft"))
    artifacts = draft.get("draft_artifacts") or []
    if artifacts and isinstance(artifacts[0], dict):
        return artifacts[0].get("text", "") or ""
    return ""


def _forbidden_content_violations(text: str, decision: Dict[str, Any]) -> List[str]:
    """Check if draft cites forbidden statutes or includes forbidden reliefs/damages.

    Returns blocking violations only — these are hard errors from the applicability compiler.
    """
    if not text:
        return []

    lower = text.lower()
    violations: List[str] = []

    # Check forbidden statutes
    for statute in (decision.get("forbidden_statutes") or []):
        # Normalize for search: "Commercial Courts Act, 2015" -> "commercial courts act"
        search_term = statute.lower().split(",")[0].strip()
        if search_term and search_term in lower:
            violations.append(f"Draft cites forbidden statute: {statute}")

    # Check forbidden damages used as prayer/relief
    for damage in (decision.get("forbidden_damages") or []):
        search_term = damage.replace("_", " ").lower()
        if search_term in lower:
            # Only flag if it appears in prayer section (not just mentioned in facts)
            prayer_start = lower.rfind("prayer")
            if prayer_start >= 0 and search_term in lower[prayer_start:]:
                violations.append(f"Draft claims '{damage.replace('_', ' ')}' as relief — this is a defence concept, not a plaintiff claim.")

    return violations


def _prayer_completeness_issues(text: str, decision: Dict[str, Any], plan: Dict[str, Any] | None = None) -> List[str]:
    """Check required_reliefs from decision_ir/plan_ir appear in the prayer section.

    Source priority: plan_ir.required_reliefs > decision.allowed_reliefs > empty.
    Normalizes relief vocabulary (strips _decree suffix for matching).
    """
    if not text:
        return []

    # Source: plan_ir first (compiled plan), then decision (allowed_reliefs)
    required_reliefs = []
    if plan and plan.get("required_reliefs"):
        required_reliefs = list(plan["required_reliefs"])
    elif decision.get("allowed_reliefs"):
        required_reliefs = list(decision["allowed_reliefs"])

    if not required_reliefs:
        return []

    lower = text.lower()
    issues: List[str] = []

    # Keyword map — covers both _decree and non-_decree variants
    relief_checks = {
        "possession_decree": ["possession", "vacate", "hand over"],
        "mesne_profits_inquiry_order_xx_r12": ["mesne profits", "order xx rule 12", "inquiry"],
        "costs": ["costs of the suit", "cost of this suit", "costs"],
        "preliminary_decree_shares": ["preliminary decree", "shares"],
        "partition_by_metes_and_bounds": ["metes and bounds", "partition"],
        "appointment_of_commissioner": ["commissioner"],
        "separate_possession": ["separate possession"],
        "final_decree": ["final decree"],
        "declaration_decree": ["declaration", "declared", "declaring", "declare"],
        "consequential_relief": ["consequential relief"],
        "permanent_injunction": ["injunction", "restrained"],
        "permanent_injunction_decree": ["injunction", "restrained"],
        "mandatory_injunction": ["mandatory injunction", "directed to"],
        "mandatory_injunction_decree": ["mandatory injunction", "directed to"],
        "mesne_profits_decree": ["mesne profits"],
        "inquiry_under_order_xx_rule_12": ["order xx rule 12", "inquiry"],
        "interest_pendente_lite_future": ["interest", "pendente lite", "future interest"],
        "damages": ["damages", "compensation"],
        "specific_performance": ["specific performance"],
        "rendition_of_accounts": ["render true and faithful accounts", "render accounts", "taking of accounts", "preliminary decree"],
        "money_found_due_after_accounts": ["amount found due", "found due", "upon rendition of accounts", "upon taking accounts", "final decree"],
    }

    for relief in required_reliefs:
        keywords = relief_checks.get(relief, [relief.replace("_decree", "").replace("_", " ")])
        if not any(kw in lower for kw in keywords):
            issues.append(f"Required relief '{relief.replace('_', ' ')}' missing from prayer.")

    return issues


def _possession_consistency_issues(text: str, cause_type: str) -> List[str]:
    if not text or not cause_type.startswith("recovery_of_possession"):
        return []

    lower = text.lower()
    issues: List[str] = []
    has_section_16 = bool(re.search(r"\bsection\s+16\b", text, re.IGNORECASE))
    has_situs_jurisdiction = bool(
        re.search(r"(immovable property|suit property)[^.\n]{0,140}\b(situated|situate)\b", lower, re.IGNORECASE)
    )

    if "with interest and costs" in lower:
        issues.append("Possession draft title still uses the generic 'WITH INTEREST AND COSTS' damages template.")
    if "carries on business / resides" in lower or re.search(r"territorial jurisdiction[^.\n]{0,180}defendant[^.\n]{0,80}resides", lower):
        issues.append("Possession draft pleads Section 20-style residence/cause-of-action jurisdiction instead of immovable-property situs jurisdiction.")
    if not has_section_16 and not has_situs_jurisdiction:
        issues.append("Possession draft does not clearly plead property-situs jurisdiction under Section 16 CPC.")

    if cause_type == "recovery_of_possession_tenant":
        if re.search(r"\bArticle\s+65\b", text, re.IGNORECASE):
            issues.append("Tenant possession draft cites Article 65 instead of the tenant track limitation.")
        if "easements act" in lower or re.search(r"\bSection\s+52\b|\bSection\s+62\b", text, re.IGNORECASE):
            issues.append("Tenant possession draft mixes licence/Easements Act language.")
    elif cause_type == "recovery_of_possession_licensee":
        if re.search(r"\bArticle\s+67\b", text, re.IGNORECASE):
            issues.append("Licensee possession draft cites Article 67 instead of the title-based licence track.")
        if "transfer of property act" in lower or re.search(r"\bSection\s+106\b|\bSection\s+111\b", text, re.IGNORECASE):
            issues.append("Licensee possession draft mixes tenancy/Transfer of Property Act language.")
        if "easements act" not in lower and not re.search(r"\bSection\s+52\b|\bSection\s+60\b|\bSection\s+61\b|\bSection\s+62\b|\bSection\s+63\b", text, re.IGNORECASE):
            issues.append("Licensee possession draft omits the Indian Easements Act footing for the licence track.")
    elif cause_type == "recovery_of_possession_trespasser":
        if re.search(r"\bArticle\s+67\b", text, re.IGNORECASE):
            issues.append("Trespasser possession draft cites Article 67 instead of Article 65.")
        if re.search(r"\bSection\s+106\b|\bSection\s+111\b", text, re.IGNORECASE):
            issues.append("Trespasser possession draft mixes tenancy-determination language.")

    if re.search(r"pass a decree[^.\n]{0,180}(sum of rs|towards damages)", lower, re.IGNORECASE):
        issues.append("Possession prayer still begins with a generic money-damages decree instead of a possession decree.")
    if re.search(r"mesne profits[^.\n]{0,120}rate of[^.\n]{0,40}%\s+per\s+annum", lower, re.IGNORECASE):
        issues.append("Mesne profits are pleaded as an interest-rate-only claim instead of a profits/use-and-occupation claim.")
    if "order xx rule 12" not in lower:
        issues.append("Possession draft omits the Order XX Rule 12 CPC inquiry footing for mesne profits.")
    if "past mesne profits" not in lower or (
        "future mesne profits" not in lower and "inquiry under order xx rule 12" not in lower
    ):
        issues.append("Possession draft does not clearly separate past mesne profits from future inquiry relief.")
    if re.search(r"cause of action[^.\n]{0,180}first arose[^.\n]{0,100}notice", lower, re.IGNORECASE):
        issues.append("Possession draft incorrectly anchors the first accrual of cause of action to the legal notice date.")
    if "person in possession" in lower and "recovery of possession" in lower:
        issues.append("Possession draft says the plaintiff is already in possession while also seeking recovery of possession.")

    return issues


def _injunction_consistency_issues(text: str, cause_type: str) -> List[str]:
    if not text or get_family(cause_type) != "injunction":
        return []

    lower = text.lower()
    issues: List[str] = []
    property_based = any(
        token in lower
        for token in (
            "agricultural land",
            "survey no",
            "survey number",
            "suit property",
            "immovable property",
            "revenue record",
            "mutation",
            "pahani",
            "rtc",
            "adangal",
        )
    )
    has_section_16 = bool(re.search(r"\bsection\s+16\b", text, re.IGNORECASE))
    has_situs_jurisdiction = bool(
        re.search(r"(property|land|suit property|agricultural land)[^.\n]{0,140}\b(situated|situate)\b", lower, re.IGNORECASE)
    )

    if "with interest and costs" in lower:
        issues.append("Injunction draft title still uses the generic 'WITH INTEREST AND COSTS' damages template.")
    if re.search(r"(?m)^INTEREST\b", text):
        issues.append("Bare injunction draft still contains a standalone INTEREST section.")
    if re.search(
        r"(code\s+of\s+civil\s+procedure[^.\n]{0,100}\bsection\s+34\b|\bsection\s+34\b[^.\n]{0,100}code\s+of\s+civil\s+procedure)",
        lower,
        re.IGNORECASE,
    ):
        issues.append("Bare injunction draft incorrectly cites Section 34 CPC / interest footing.")
    if re.search(r"pass a decree[^.\n]{0,200}(sum of rs|towards damages)", lower, re.IGNORECASE):
        issues.append("Bare injunction prayer still contains a generic money-damages decree.")
    if property_based and (
        "carries on business / resides" in lower
        or re.search(r"territorial jurisdiction[^.\n]{0,180}defendant[^.\n]{0,80}resides", lower)
    ):
        issues.append("Property injunction draft pleads Section 20-style residence/cause-of-action jurisdiction instead of immovable-property situs jurisdiction.")
    if property_based and not has_section_16 and not has_situs_jurisdiction:
        issues.append("Property injunction draft does not clearly plead property-situs jurisdiction under Section 16 CPC.")

    if cause_type == "permanent_injunction" and not re.search(r"\bsection(?:s)?\b[^.\n]{0,40}\b38\b", text, re.IGNORECASE):
        issues.append("Permanent injunction draft omits the Section 38 Specific Relief Act footing.")
    if cause_type == "mandatory_injunction" and not re.search(r"\bsection(?:s)?\b[^.\n]{0,40}\b39\b", text, re.IGNORECASE):
        issues.append("Mandatory injunction draft omits the Section 39 Specific Relief Act footing.")

    return issues


def _easement_consistency_issues(text: str, cause_type: str) -> List[str]:
    if not text or cause_type != "easement":
        return []

    lower = text.lower()
    issues: List[str] = []
    has_section_16 = bool(re.search(r"\bsection\s+16\b", text, re.IGNORECASE))
    has_situs_jurisdiction = bool(
        re.search(r"(property|pathway|passage|land|servient|dominant)[^.\n]{0,140}\b(situated|situate)\b", lower)
    )

    if "suit for suit for" in lower:
        issues.append("Easement draft title still duplicates the 'SUIT FOR' prefix.")
    if re.search(r"(?m)^INTEREST\b", text):
        issues.append("Easement draft still contains a standalone INTEREST section.")
    if re.search(r"pass a decree[^.\n]{0,220}(sum of rs|towards damages)", lower, re.IGNORECASE):
        issues.append("Easement prayer still falls back to a generic money-damages decree.")
    if "easements act" not in lower or not re.search(r"\bsection\s+15\b", text, re.IGNORECASE):
        issues.append("Easement draft omits the Indian Easements Act / Section 15 prescriptive footing.")
    has_section_34 = bool(re.search(r"\bsection(?:s)?\s+34\b", text, re.IGNORECASE))
    has_perm_injunction_track = "permanent injunction" in lower or bool(
        re.search(r"\bsection(?:s)?\s+38\b", text, re.IGNORECASE)
    )
    has_mand_injunction_track = "mandatory injunction" in lower or bool(
        re.search(r"\bsection(?:s)?\s+39\b", text, re.IGNORECASE)
    )

    if not has_section_34:
        issues.append("Easement draft omits the Section 34 Specific Relief Act declaration footing.")
    if not has_perm_injunction_track or not has_mand_injunction_track:
        issues.append("Easement draft omits the Sections 38 and 39 Specific Relief Act injunction footing.")
    if not has_section_16 and not has_situs_jurisdiction:
        issues.append("Easement draft does not clearly plead property-situs jurisdiction under Section 16 CPC.")
    if "dominant heritage" not in lower and "schedule a" not in lower:
        issues.append("Easement draft does not distinctly identify the dominant heritage.")
    if "servient" not in lower and "pathway" not in lower and "passage" not in lower and "schedule b" not in lower:
        issues.append("Easement draft does not distinctly identify the servient pathway / passage.")

    return issues


def _easement_blocking_violations(text: str, cause_type: str) -> List[str]:
    if not text or cause_type != "easement":
        return []

    lower = text.lower()
    violations: List[str] = []
    prayer_start = lower.rfind("prayer")
    prayer_text = lower[prayer_start:] if prayer_start >= 0 else lower

    if "suit for suit for" in lower:
        violations.append("EASEMENT_TEMPLATE_DRIFT: Draft title still duplicates the 'SUIT FOR' prefix.")
    if re.search(r"pass a decree[^.\n]{0,220}(sum of rs|towards damages)", prayer_text, re.IGNORECASE):
        violations.append("EASEMENT_TEMPLATE_DRIFT: Easement draft prayer fell back to a money-damages decree.")
    if not any(token in prayer_text for token in ("declaration", "declaring", "declare")):
        violations.append("EASEMENT_RELIEF_MISSING: Prayer omits declaration of easementary right.")
    if "mandatory injunction" not in prayer_text and "remove the obstruction" not in prayer_text:
        violations.append("EASEMENT_RELIEF_MISSING: Prayer omits mandatory injunction to remove obstruction.")
    if "permanent injunction" not in prayer_text and "restraining" not in prayer_text:
        violations.append("EASEMENT_RELIEF_MISSING: Prayer omits permanent injunction against future obstruction.")

    return violations


# ── Contract / Commercial family ────────────────────────────────────────────

_CONTRACT_CAUSE_TYPES = {
    "breach_of_contract",
    "breach_dealership_franchise",
    "breach_employment",
    "breach_construction",
    "agency_dispute",
    "supply_service_contract",
    "specific_performance",
    "rescission_contract",
    "injunction_negative_covenant",
    "rectification_instrument",
    "cancellation_instrument",
    "rera_homebuyer",
}


def _contract_consistency_issues(text: str, cause_type: str) -> List[str]:
    if not text or cause_type not in _CONTRACT_CAUSE_TYPES:
        return []

    lower = text.lower()
    issues: List[str] = []

    # S.73 vs S.74 mixing — mutually exclusive damage tracks
    has_s73 = bool(re.search(r"\bsection\s+73\b", text, re.IGNORECASE))
    has_s74 = bool(re.search(r"\bsection\s+74\b", text, re.IGNORECASE))
    if has_s73 and has_s74:
        issues.append(
            "Contract draft mixes Section 73 (unliquidated damages) and Section 74 "
            "(liquidated damages/penalty) — choose one track."
        )

    # Arbitration clause detection — if contract has arb clause, civil suit may be barred
    if re.search(r"\barbitration\s+clause\b", lower) and not re.search(r"\bsection\s+8\b[^.\n]{0,80}arbitration", lower):
        issues.append(
            "Contract mentions arbitration clause but does not address Section 8 "
            "Arbitration Act bar — court may refer to arbitration."
        )

    # S.12A CCRA 2018 — pre-institution mediation mandatory for commercial disputes
    if "commercial dispute" in lower or "commercial court" in lower:
        if not re.search(r"\bsection\s+12a\b", lower) and not re.search(r"\bpre.?institution\s+mediation\b", lower):
            issues.append(
                "Commercial dispute draft omits mandatory pre-institution mediation "
                "under Section 12A Commercial Courts Act, 2015."
            )

    # RERA homebuyer — exclusive RERA forum
    if cause_type == "rera_homebuyer":
        if not re.search(r"\brera\b|\breal estate.{0,30}regulatory\b", lower):
            issues.append("RERA homebuyer draft omits reference to RERA authority/forum.")

    # Specific performance — must plead readiness and willingness (S.16(c) SRA)
    if cause_type == "specific_performance":
        if not re.search(r"\breadiness\b|\bwilling(?:ness)?\b", lower):
            issues.append(
                "Specific performance draft omits the mandatory averment of "
                "readiness and willingness under Section 16(c) Specific Relief Act."
            )
        if not re.search(r"\bsection\s+(?:14|16)\b", text, re.IGNORECASE):
            issues.append(
                "Specific performance draft omits Section 14/16 Specific Relief Act footing."
            )

    # Workman exclusion — IDA workman should not file civil suit for termination
    if cause_type == "employment_termination":
        if re.search(r"\bworkm[ae]n\b|\bindustrial\s+disputes?\b", lower):
            issues.append(
                "Employment termination draft invokes workman/Industrial Disputes Act "
                "language — workman claims lie before Labour Court, not civil court."
            )

    # Guarantee vs indemnity confusion
    if cause_type in ("indemnity_claim", "indemnity_recovery") and re.search(r"\bsection\s+126\b", text, re.IGNORECASE):
        issues.append("Indemnity claim draft cites Section 126 (guarantee) instead of Section 124 (indemnity).")
    if cause_type in ("guarantee_invocation", "guarantee_recovery") and re.search(r"\bsection\s+124\b", text, re.IGNORECASE):
        issues.append("Guarantee invocation draft cites Section 124 (indemnity) instead of Section 126 (guarantee).")

    return issues


def _contract_blocking_violations(text: str, cause_type: str, decision: Dict[str, Any]) -> List[str]:
    """Contract-specific hard violations that should BLOCK drafting.

    Returns list of blocking issue strings. Empty = no blockers.
    """
    if not text or cause_type not in _CONTRACT_CAUSE_TYPES:
        return []

    lower = text.lower()
    violations: List[str] = []

    # 1. Invented arbitration clause status — draft asserts arb clause exists/doesn't exist
    #    without factual basis
    if re.search(
        r"(agreement[^.\n]{0,80}(contains|does not contain)[^.\n]{0,40}arbitration\s+clause"
        r"|no\s+arbitration\s+clause[^.\n]{0,40}(exists|present)"
        r"|there\s+is\s+no\s+arbitration\s+clause)",
        lower,
    ):
        violations.append(
            "INVENTED_FACT: Draft asserts arbitration clause status without factual basis. "
            "Do not invent facts about whether an arbitration clause exists."
        )

    # 2. Unsupported repudiatory breach — draft uses repudiatory/anticipatory breach
    #    but applicability compiler didn't allow it
    forbidden_doctrines = set(decision.get("forbidden_doctrines") or [])
    if forbidden_doctrines:
        if ("repudiatory_breach" in forbidden_doctrines or "repudiatory_breach_s39" in forbidden_doctrines):
            if re.search(r"\brepudiatory\s+breach\b", lower):
                violations.append(
                    "UNANCHORED_THEORY: Draft pleads repudiatory breach but facts do not show "
                    "refusal/renunciation/abandonment — only non-performance."
                )
        if ("anticipatory_breach" in forbidden_doctrines or "anticipatory_breach_s39" in forbidden_doctrines):
            if re.search(r"\banticipatory\s+breach\b", lower):
                violations.append(
                    "UNANCHORED_THEORY: Draft pleads anticipatory breach but facts do not show "
                    "advance refusal before the performance date."
                )

    # 3. Interest duplication — both S.34 pendente lite interest AND interest as damages head
    has_s34 = bool(re.search(r"\bsection\s+34\b", text, re.IGNORECASE))
    has_interest_damages = bool(re.search(
        r"(interest\s+on\s+delayed\s+payment|interest\s+as\s+damages|interest\s+on\s+principal)",
        lower,
    ))
    # Both in PRAYER section = duplication
    prayer_start = lower.rfind("prayer")
    if prayer_start >= 0:
        prayer_text = lower[prayer_start:]
        if "section 34" in prayer_text and re.search(r"interest\s+on\s+delayed", prayer_text):
            violations.append(
                "INTEREST_DUPLICATION: Prayer claims both Section 34 pendente lite interest "
                "AND separate interest-on-delayed-payment head — double counting."
            )

    # 4. Unsupported consequential loss — in prayer without foreseeability pleading
    forbidden_damages = set(decision.get("forbidden_damages") or [])
    if "consequential_loss" in forbidden_damages:
        if re.search(r"consequential\s+(loss|damage)", lower):
            prayer_text_check = lower[prayer_start:] if prayer_start >= 0 else lower
            if "consequential" in prayer_text_check:
                violations.append(
                    "UNANCHORED_DAMAGES: Draft claims consequential loss but facts do not show "
                    "the loss was foreseeable / within contemplation of parties under Section 73."
                )

    # 5. Specific-performance drift in a pure damages contract suit
    #    Only block if "specific performance" appears as a PRAYER relief.
    #    "Ready and willing" is a standard factual averment in any contract suit
    #    (Plaintiff performed its part) — not exclusive to specific performance.
    if cause_type != "specific_performance":
        prayer_start_sp = lower.rfind("prayer")
        if prayer_start_sp >= 0:
            prayer_text_sp = lower[prayer_start_sp:]
            if re.search(r"\bspecific\s+performance\b", prayer_text_sp):
                violations.append(
                    "UNANCHORED_THEORY: Prayer seeks specific performance in a pure damages "
                    "contract suit — wrong relief track."
                )

    return violations


# ── Money / Debt family ─────────────────────────────────────────────────────

_MONEY_CAUSE_TYPES = {
    "money_recovery_loan",
    "money_recovery_goods",
    "money_recovery_services",
    "money_recovery_advance",
    "money_recovery_deposit_refund",
    "money_recovery_rent_arrears",
    "failure_of_consideration",
    "deposit_refund",
    "summary_suit_instrument",
    "recovery_specific_movable",
    "suit_on_bond",
    "suit_for_wages",
    "quantum_meruit",
    "contribution_co_debtors",
    "guarantee_recovery",
    "indemnity_recovery",
    "vendor_unpaid_purchase_money",
    "profits_wrongfully_received",
    "cheque_bounce_civil",
    "insurance_claim",
    "arbitration_award_enforcement",
    "decree_execution_money",
    "banker_customer_dispute",
    "msmed_recovery",
    "unjust_enrichment",
}


def _money_consistency_issues(text: str, cause_type: str) -> List[str]:
    if not text or cause_type not in _MONEY_CAUSE_TYPES:
        return []

    lower = text.lower()
    issues: List[str] = []

    # Workman/IDA — money recovery should not mix IDA language
    if re.search(r"\bworkm[ae]n\b|\bindustrial\s+disputes?\b", lower) and cause_type not in ("decree_execution_money",):
        issues.append(
            "Money recovery draft invokes workman/Industrial Disputes Act language — "
            "workman dues lie before Labour Court."
        )

    # MSMED compliance — MSMED claims should cite MSMED Act
    if cause_type == "msmed_recovery":
        if not re.search(r"\bmsm(?:ed|e)\b|\bmicro.{0,20}small.{0,20}medium\b", lower):
            issues.append("MSMED recovery draft omits MSMED Act, 2006 footing.")

    # Cheque bounce — must reference S.138 NI Act
    if cause_type == "cheque_bounce_civil":
        if not re.search(r"\bsection\s+138\b", text, re.IGNORECASE):
            issues.append("Cheque bounce civil draft omits Section 138 Negotiable Instruments Act.")
        if not re.search(r"\bdemand\s+notice\b|\bstatutory\s+notice\b", lower):
            issues.append("Cheque bounce draft omits mandatory demand/statutory notice averment.")

    # Summary suit — must reference Order XXXVII CPC
    if cause_type in ("summary_suit", "summary_suit_instrument"):
        if not re.search(r"\border\s+xxxvii\b|\border\s+37\b", lower):
            issues.append("Summary suit draft omits Order XXXVII CPC footing.")

    # Guarantee vs indemnity confusion (also checked in contract gate for legacy codes)
    if cause_type in ("indemnity_recovery",) and re.search(r"\bsection\s+126\b", text, re.IGNORECASE):
        issues.append("Indemnity claim draft cites Section 126 (guarantee) instead of Section 124 (indemnity).")
    if cause_type in ("guarantee_recovery",) and re.search(r"\bsection\s+124\b", text, re.IGNORECASE):
        issues.append("Guarantee invocation draft cites Section 124 (indemnity) instead of Section 126 (guarantee).")

    # Interest rate — excessive interest (>24% in most states) is a red flag
    interest_match = re.search(r"(\d{2,})(?:\.\d+)?\s*%\s*(?:per\s+annum|p\.?\s*a\.?)", lower)
    if interest_match:
        rate = float(interest_match.group(1))
        if rate > 24:
            issues.append(
                f"Money recovery draft claims {rate}% interest per annum — "
                "courts typically cap at 18-24%. Verify contractual basis."
            )

    # Insurance claim — must reference Insurance Act or policy
    if cause_type == "insurance_claim":
        if not re.search(r"\binsurance\s+act\b|\bpolicy\s+(?:no|number)\b", lower):
            issues.append("Insurance claim draft omits Insurance Act/policy reference.")

    return issues


# ── Accounts / Relationship family ─────────────────────────────────────────

_ACCOUNTS_CAUSE_TYPES = {
    "rendition_of_accounts",
    "accounts_stated",
}


def _accounts_consistency_issues(text: str, cause_type: str) -> List[str]:
    """Consistency gate for accounts/relationship family."""
    if not text or cause_type not in _ACCOUNTS_CAUSE_TYPES:
        return []

    lower = text.lower()
    issues: List[str] = []

    # Must reference Order XX Rule 16 CPC (preliminary decree for accounts)
    if cause_type == "rendition_of_accounts":
        if not re.search(r"\border\s+xx\s+rule\s+16\b", lower):
            issues.append(
                "Rendition of accounts draft omits Order XX Rule 16 CPC "
                "footing for taking accounts."
            )

        # Must NOT use generic damages framing
        if re.search(r"\bdamages\s+(?:suffered|claimed|incurred)\b", lower):
            issues.append(
                "Rendition of accounts draft uses damages framing — this is "
                "an accounts suit, not a damages suit. Plead relationship, "
                "duty to account, and amount found due."
            )

        # Must seek preliminary decree
        if not re.search(r"\bpreliminary\s+decree\b", lower):
            issues.append(
                "Rendition of accounts draft omits prayer for a preliminary "
                "decree directing accounts to be taken."
            )

        # Must seek final decree for amount found due
        if not re.search(r"\b(?:final\s+decree|found\s+due|amount\s+found\s+due)\b", lower):
            issues.append(
                "Rendition of accounts draft does not clearly seek a final "
                "decree for the amount found due after accounts."
            )

        # Must plead the relationship basis
        if not re.search(
            r"\b(?:partner(?:ship)?|agent|agency|fiduciary|trust(?:ee)?|"
            r"joint\s+(?:business|venture)|managed|entrusted)\b", lower
        ):
            issues.append(
                "Rendition of accounts draft does not plead the relationship "
                "basis (agency/partnership/fiduciary/joint business) that "
                "creates the duty to account."
            )

        # Must NOT be titled as money recovery
        if re.search(r"\bsuit\s+for\s+(?:recovery\s+of\s+)?money\b", lower):
            issues.append(
                "Rendition of accounts suit incorrectly titled as money "
                "recovery suit — title should reflect rendition of accounts."
            )

    return issues


# ── Partition / Co-ownership family ─────────────────────────────────────────

_PARTITION_CAUSE_TYPES = {
    "partition",
    "partition_ancestral",
}


def _partition_consistency_issues(text: str, cause_type: str) -> List[str]:
    if not text or cause_type not in _PARTITION_CAUSE_TYPES:
        return []

    lower = text.lower()
    issues: List[str] = []

    # Order XX Rule 18 — two-stage decree (preliminary + final)
    if not re.search(r"\border\s+xx\s+rule\s+18\b", lower):
        issues.append(
            "Partition draft omits Order XX Rule 18 CPC (two-stage preliminary + final decree)."
        )

    # Pre vs post-2005 coparcenary — Vineeta Sharma v Kumar (2020)
    has_hindu_succession = bool(re.search(r"\bhindu\s+succession\s+act\b", lower))
    has_section_6 = bool(re.search(r"\bsection\s+6\b", text, re.IGNORECASE))
    has_2005_amendment = bool(re.search(r"\b2005\s+amendment\b|\bamendment\s+(?:of\s+)?2005\b", lower))
    if has_hindu_succession and has_section_6:
        # If citing S.6 but not mentioning 2005 amendment context, flag
        if not has_2005_amendment and not re.search(r"\bvineeta\s+sharma\b", lower):
            issues.append(
                "Partition draft cites Section 6 Hindu Succession Act but does not "
                "clarify pre/post-2005 coparcenary position (Vineeta Sharma v Kumar, 2020)."
            )

    # Art 110 limitation — partition of joint family property
    has_art_110 = bool(re.search(r"\barticle\s+110\b", text, re.IGNORECASE))
    has_art_65 = bool(re.search(r"\barticle\s+65\b", text, re.IGNORECASE))
    if has_art_65 and not has_art_110:
        issues.append(
            "Partition draft cites Article 65 (general) instead of Article 110 "
            "(partition of joint family property — 12 years from exclusion)."
        )

    # Situs jurisdiction — partition of immovable property requires S.16 CPC
    has_section_16 = bool(re.search(r"\bsection\s+16\b", text, re.IGNORECASE))
    if not has_section_16:
        issues.append("Partition draft does not plead situs jurisdiction under Section 16 CPC.")

    # Genealogy table — partition suits should include family tree
    if not re.search(r"\bgenealog(?:y|ical)\b|\bfamily\s+tree\b|\bpedigree\b", lower):
        issues.append("Partition draft omits genealogy table/family tree — essential for partition suits.")

    # Share computation — must indicate shares
    if not re.search(r"\bshare\b|\b1/\d\b|\bone.?(?:half|third|fourth|fifth)\b", lower):
        issues.append("Partition draft does not clearly state the shares of each co-owner/coparcener.")

    return issues


# ── Tenancy / Rent family ───────────────────────────────────────────────────

_TENANCY_CAUSE_TYPES = {
    "eviction",
    "rent_arrears",
    "mesne_profits_post_tenancy",
}


def _tenancy_consistency_issues(text: str, cause_type: str) -> List[str]:
    if not text or cause_type not in _TENANCY_CAUSE_TYPES:
        return []

    lower = text.lower()
    issues: List[str] = []

    # Rent Act protection — if tenant is protected under state rent act, civil suit may be barred
    has_rent_act = bool(re.search(
        r"\brent\s+(?:control|act|controller)\b|\brent\s+court\b", lower
    ))
    if has_rent_act:
        if not re.search(r"\bexempt\b|\bnot\s+(?:covered|protected|applicable)\b|\bexclud(?:e|ed)\b", lower):
            issues.append(
                "Tenancy draft references Rent Act but does not address whether "
                "premises are exempt/excluded — if Rent Act applies, civil court "
                "jurisdiction may be barred."
            )

    # S.106 TPA — notice requirement for lease termination
    if cause_type == "eviction":
        if not re.search(r"\bsection\s+106\b", text, re.IGNORECASE):
            issues.append(
                "Eviction draft omits Section 106 Transfer of Property Act "
                "(notice to determine lease)."
            )
        if not re.search(r"\bnotice\b[^.\n]{0,100}\b(?:quit|vacate|determine)\b", lower):
            issues.append(
                "Eviction draft does not plead notice to quit/vacate — "
                "mandatory prerequisite for eviction."
            )

    # Rent arrears — must quantify arrears period and amount
    if cause_type == "rent_arrears":
        if not re.search(r"\b(?:arrears?|unpaid\s+rent)\b", lower):
            issues.append("Rent arrears draft omits averment of arrears/unpaid rent.")
        if not re.search(r"\brs\.?\s*\d|₹\s*\d|\brunning\s+month\b", lower):
            issues.append(
                "Rent arrears draft does not quantify the arrears amount or period."
            )

    # Mesne profits post-tenancy — needs Order XX Rule 12 footing
    if cause_type == "mesne_profits_post_tenancy":
        if "order xx rule 12" not in lower:
            issues.append(
                "Mesne profits post-tenancy draft omits Order XX Rule 12 CPC "
                "inquiry footing."
            )

    return issues


# ── Tort / Civil Wrong family ───────────────────────────────────────────────

_TORT_CAUSE_TYPES = {
    "defamation",
    "defamation_civil",  # alias compat
    "negligence",
    "negligence_personal_injury",
    "negligence_property_damage",
    "nuisance",
    "nuisance_private",
    "nuisance_public",
    "trespass_to_person",
    "trespass_to_goods",
    "trespass_goods_movable",
    "conversion",
    "false_imprisonment",
    "false_imprisonment_civil",
    "malicious_prosecution",
    "malicious_prosecution_civil",
    "medical_negligence",
    "product_liability",
    "strict_liability",
    "professional_negligence",
    "business_disparagement",
    "fraud_misrepresentation_standalone",
    "wrongful_seizure_compensation",
    "illegal_distress_compensation",
    "tortious_interference_contract",
    "compensation_act_under_enactment",
}

# Short limitation torts — 1-year limitation under Limitation Act 1963
_TORT_SHORT_LIMITATION = {
    "defamation": ("Article 75", r"\barticle\s+75\b"),
    "false_imprisonment_civil": ("Article 74", r"\barticle\s+74\b"),
    "malicious_prosecution_civil": ("Article 77", r"\barticle\s+77\b"),
    "nuisance": ("Article 73", r"\barticle\s+73\b"),
    "compensation_act_under_enactment": ("Article 72", r"\barticle\s+72\b"),
}


def _tort_consistency_issues(text: str, cause_type: str) -> List[str]:
    if not text or cause_type not in _TORT_CAUSE_TYPES:
        return []

    lower = text.lower()
    issues: List[str] = []

    # Short limitation check — defamation/false imprisonment/malicious prosecution have 1-year limit
    if cause_type in _TORT_SHORT_LIMITATION:
        expected_article, pattern = _TORT_SHORT_LIMITATION[cause_type]
        if not re.search(pattern, text, re.IGNORECASE):
            issues.append(
                f"{cause_type.replace('_', ' ').title()} draft does not cite "
                f"{expected_article} (1-year limitation) — verify limitation pleading."
            )

    # Defamation — must plead special damage or innuendo for slander
    if cause_type == "defamation":
        if re.search(r"\bslander\b", lower) and not re.search(r"\bspecial\s+damage\b", lower):
            issues.append(
                "Defamation (slander) draft does not plead special damage — "
                "required unless words are actionable per se."
            )

    # Medical negligence — MACT exclusion (motor accident claims go to MACT)
    if cause_type == "medical_negligence":
        if re.search(r"\bmotor\s+(?:accident|vehicle)\b|\bmact\b", lower):
            issues.append(
                "Medical negligence draft mixes Motor Accident Claims Tribunal "
                "language — MACT claims lie before MACT, not civil court."
            )
        # Bolam test / duty of care
        if not re.search(r"\bduty\s+of\s+care\b|\bstandard\s+of\s+care\b|\bbolam\b|\bnegligence\b", lower):
            issues.append(
                "Medical negligence draft omits duty/standard of care averment."
            )

    # Negligence — must plead duty, breach, causation, damage
    if cause_type == "negligence":
        negligence_elements = {
            "duty": r"\bduty\s+(?:of\s+care|to\b)",
            "breach": r"\bbreach(?:ed)?\b",
            "damage": r"\bdamage[sd]?\b|\bloss\b|\binjur(?:y|ies)\b",
        }
        for element, pattern in negligence_elements.items():
            if not re.search(pattern, lower):
                issues.append(
                    f"Negligence draft omits the '{element}' element — "
                    "duty, breach, causation, and damage must all be pleaded."
                )

    # Nuisance — public nuisance needs special damage or AG authorization
    if cause_type == "nuisance_public":
        if not re.search(r"\bspecial\s+damage\b|\battorney\s+general\b|\badvocate\s+general\b", lower):
            issues.append(
                "Public nuisance draft does not plead special damage or "
                "Attorney/Advocate General authorization — required for civil action."
            )

    # Product liability — Consumer Protection Act may be exclusive forum
    if cause_type == "product_liability":
        if re.search(r"\bconsumer\s+protection\s+act\b|\bconsumer\s+forum\b|\bconsumer\s+commission\b", lower):
            issues.append(
                "Product liability draft references Consumer forum — "
                "verify if Consumer Protection Act provides exclusive remedy."
            )

    return issues


def civil_consistency_gate_node(state: DraftingState) -> Command:
    """Semantic consistency gate — flags issues for review, does NOT block.

    Checks: possession/injunction consistency + prayer completeness + theory anchoring.
    All deterministic, zero LLM calls.
    """
    classify = _as_dict(state.get("classify"))
    decision = _as_dict(state.get("civil_decision"))

    if classify.get("law_domain") != "Civil" or decision.get("status") != "resolved":
        return Command(update={"civil_gate_issues": []}, goto="evidence_anchoring")

    text = _extract_draft_text(state)
    cause_type = decision.get("resolved_cause_type", "")
    lkb_brief = _as_dict(state.get("lkb_brief"))
    plan = _as_dict(state.get("civil_draft_plan")) or _as_dict(state.get("plan_ir"))

    # Family-specific consistency checks
    issues = _possession_consistency_issues(text, cause_type)
    issues.extend(_injunction_consistency_issues(text, cause_type))
    issues.extend(_easement_consistency_issues(text, cause_type))
    issues.extend(_contract_consistency_issues(text, cause_type))
    issues.extend(_money_consistency_issues(text, cause_type))
    issues.extend(_accounts_consistency_issues(text, cause_type))
    issues.extend(_partition_consistency_issues(text, cause_type))
    issues.extend(_tenancy_consistency_issues(text, cause_type))
    issues.extend(_tort_consistency_issues(text, cause_type))

    # Prayer completeness check (required_reliefs from decision/plan, not raw lkb_brief)
    issues.extend(_prayer_completeness_issues(text, decision, plan))

    # Forbidden statute/relief enforcement — check draft doesn't cite forbidden items
    hard_violations = _forbidden_content_violations(text, decision)

    # Contract-specific blocking violations (invented facts, unanchored theory, duplication)
    hard_violations.extend(_contract_blocking_violations(text, cause_type, decision))
    hard_violations.extend(_easement_blocking_violations(text, cause_type))

    # Theory anchoring check (doctrines → LKB/provisions/user)
    from ..gates.theory_anchoring import legal_theory_anchoring_gate
    user_request = (state.get("user_request") or "").strip()
    mandatory_provisions = _as_dict(state.get("mandatory_provisions"))
    verified_provisions = mandatory_provisions.get("verified_provisions") or []
    theory_result = legal_theory_anchoring_gate(text, lkb_brief, verified_provisions, user_request)
    for flag in theory_result.flags:
        issues.append(flag)

    # Build issue dicts — hard violations get "blocking" severity
    issue_dicts = []
    for issue in hard_violations:
        issue_dicts.append({
            "type": "civil_consistency",
            "severity": "blocking",
            "issue": issue,
            "fix": "Remove forbidden content from draft.",
        })
    for issue in issues:
        issue_dicts.append({
            "type": "civil_consistency",
            "severity": "legal",
            "issue": issue,
            "fix": "Review and correct the legal track.",
        })

    total = len(issues) + len(hard_violations)
    if total:
        logger.info(
            "[CIVIL_CONSISTENCY_GATE] flagged %d issues (%d blocking) | cause=%s",
            total, len(hard_violations), cause_type,
        )
    else:
        logger.info("[CIVIL_CONSISTENCY_GATE] passed | cause=%s", cause_type)

    # Hard violations block drafting — forbidden statute/relief in draft is a fatal error
    if hard_violations:
        blocked = _build_blocked_artifact(
            classify, "CONSISTENCY GATE — FORBIDDEN CONTENT",
            hard_violations,
        )
        return Command(
            update={
                "civil_gate_issues": issue_dicts,
                "errors": hard_violations,
                "draft": blocked,
                "final_draft": blocked,
            },
            goto=END,
        )

    # Non-blocking issues flagged for downstream review
    return Command(update={"civil_gate_issues": issue_dicts}, goto="evidence_anchoring")

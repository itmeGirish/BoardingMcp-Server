"""Legal Knowledge Base (LKB) — structured legal lookup for law selection.

v5.0: All entries flat — no conditional resolution needed.
Intake LLM classifies into specific sub-types (e.g., recovery_of_possession_tenant).

Usage:
    from app.agents.drafting_agents.lkb import lookup, lookup_multi

    entry = lookup("Civil", "recovery_of_possession_tenant")
    entries = lookup_multi("Civil", ["breach_of_contract", "money_recovery_loan"])
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ....config import logger
from .limitation import (
    build_limitation_verified_provision,
    get_limitation_reference_details,
    limitation_full_citation,
    limitation_requires_citation,
    limitation_short_citation,
    normalize_coa_type,
)


# ---------------------------------------------------------------------------
# Supersession Map — repealed Acts → current replacement
# ---------------------------------------------------------------------------

SUPERSEDED_ACTS: Dict[str, str] = {
    "Specific Relief Act, 1877": "Specific Relief Act, 1963",
    "Specific Relief Act 1877": "Specific Relief Act, 1963",
    "Indian Penal Code, 1860": "Bharatiya Nyaya Sanhita, 2023",
    "Indian Penal Code 1860": "Bharatiya Nyaya Sanhita, 2023",
    "Code of Criminal Procedure, 1973": "Bharatiya Nagarik Suraksha Sanhita, 2023",
    "Code of Criminal Procedure 1973": "Bharatiya Nagarik Suraksha Sanhita, 2023",
    "Indian Evidence Act, 1872": "Bharatiya Sakshya Adhiniyam, 2023",
    "Indian Evidence Act 1872": "Bharatiya Sakshya Adhiniyam, 2023",
    "Evidence Act, 1872": "Bharatiya Sakshya Adhiniyam, 2023",
    "Evidence Act 1872": "Bharatiya Sakshya Adhiniyam, 2023",
}


def is_superseded(act_name: str) -> bool:
    """Check if an Act has been superseded by a newer Act."""
    if not act_name:
        return False
    normalized = act_name.strip().rstrip(".")
    return normalized in SUPERSEDED_ACTS


def get_current_act(act_name: str) -> str:
    """Get the current replacement Act, or return the original if not superseded."""
    if not act_name:
        return act_name
    normalized = act_name.strip().rstrip(".")
    return SUPERSEDED_ACTS.get(normalized, act_name)


# ---------------------------------------------------------------------------
# Residuary articles — always dropped when a specific article exists
# ---------------------------------------------------------------------------

RESIDUARY_ARTICLES = {"113"}  # Limitation Act 1963 — catch-all


# ---------------------------------------------------------------------------
# Registry — domain → {cause_type → entry}
# ---------------------------------------------------------------------------

_REGISTRY: Dict[str, Dict[str, dict]] = {}
_SUPPORTED_LKB_DOMAINS = ("Civil", "Criminal", "Family", "Corporate", "IP", "Other")

# ---------------------------------------------------------------------------
# Alias map — common LLM near-misses → correct LKB key
# v5.0: updated for flat cause types (no more generic recovery_of_possession)
# ---------------------------------------------------------------------------

_CAUSE_TYPE_ALIASES: Dict[str, str] = {
    # recovery_of_possession aliases → now map to specific sub-types
    "property_law": "recovery_of_possession_trespasser",
    "eviction_unauthorized_occupation": "recovery_of_possession_trespasser",
    "eviction_plaint": "recovery_of_possession_tenant",
    "possession_suit": "recovery_of_possession_trespasser",
    "recovery_possession": "recovery_of_possession_trespasser",
    "suit_for_possession": "recovery_of_possession_trespasser",
    "recovery_of_possession": "recovery_of_possession_trespasser",
    # eviction aliases
    "eviction_tenant": "eviction",
    "eviction_rent_control": "eviction",
    "tenant_eviction": "eviction",
    # money recovery aliases
    "money_recovery": "money_recovery_loan",
    "loan_recovery": "money_recovery_loan",
    "debt_recovery": "money_recovery_loan",
    # breach aliases
    "breach_contract": "breach_of_contract",
    "contract_breach": "breach_of_contract",
    # dealership / franchise aliases
    "commercial_dispute": "breach_dealership_franchise",
    "dealership_termination": "breach_dealership_franchise",
    "franchise_termination": "breach_dealership_franchise",
    "dealership_dispute": "breach_dealership_franchise",
    "distributor_termination": "breach_dealership_franchise",
    # injunction aliases
    "injunction": "permanent_injunction",
    "injunction_suit": "permanent_injunction",
    # defamation aliases
    "defamation_suit": "defamation",
    "civil_defamation": "defamation",
    # v5.0: old compound entries → new flat entries
    "guarantee_indemnity_recovery": "guarantee_recovery",
    "tortious_negligence": "negligence_personal_injury",
    "mortgage_foreclosure_sale": "mortgage_foreclosure",
}


def register_domain(domain: str, entries: Dict[str, dict]) -> None:
    """Register all cause type entries for a legal domain."""
    _REGISTRY[domain.lower()] = entries
    logger.info("[LKB] registered %d entries for domain=%s", len(entries), domain)


def _lookup_in_entries(domain_entries: Dict[str, dict], cause_type: str) -> Optional[dict]:
    entry = domain_entries.get(cause_type)
    if entry:
        return entry

    # Try alias map
    aliased = _CAUSE_TYPE_ALIASES.get(cause_type)
    if aliased:
        entry = domain_entries.get(aliased)
        if entry:
            return entry

    return None


def lookup(domain: str, cause_type: str) -> Optional[dict]:
    """Look up a single cause type entry. No cross-domain fallback — domain boundaries are hard."""
    normalized_domain = (domain or "").lower()
    domain_entries = _REGISTRY.get(normalized_domain, {})
    entry = _lookup_in_entries(domain_entries, cause_type)
    if entry:
        logger.info("[LKB] hit: domain=%s cause_type=%s", domain, cause_type)
        return entry

    logger.warning("[LKB] miss: domain=%s cause_type=%s (no cross-domain fallback)", domain, cause_type)
    return None


def lookup_multi(domain: str, cause_types: List[str]) -> List[dict]:
    """Look up multiple cause types and return all found entries."""
    results = []
    for ct in cause_types:
        entry = lookup(domain, ct)
        if entry:
            results.append(entry)
    logger.info(
        "[LKB] multi-lookup: domain=%s requested=%d found=%d",
        domain, len(cause_types), len(results),
    )
    return results


def merge_entries(entries: List[dict]) -> dict:
    """Merge multiple LKB entries into a combined legal brief.

    Primary entry = first in list. Subsequent entries are alternatives.
    """
    if not entries:
        return {}
    if len(entries) == 1:
        return entries[0]

    primary = entries[0].copy()

    # Merge acts (deduplicate)
    all_acts = list(primary.get("primary_acts", []))
    seen_acts = {(a["act"], tuple(a["sections"])) for a in all_acts}
    for entry in entries[1:]:
        for act in entry.get("primary_acts", []):
            key = (act["act"], tuple(act["sections"]))
            if key not in seen_acts:
                seen_acts.add(key)
                all_acts.append(act)
    primary["primary_acts"] = all_acts

    # Merge damages categories (deduplicate)
    all_damages = list(primary.get("damages_categories", []))
    for entry in entries[1:]:
        for d in entry.get("damages_categories", []):
            if d not in all_damages:
                all_damages.append(d)
    primary["damages_categories"] = all_damages

    # Merge defensive points
    all_defensive = list(primary.get("defensive_points", []))
    for entry in entries[1:]:
        for d in entry.get("defensive_points", []):
            if d not in all_defensive:
                all_defensive.append(d)
    primary["defensive_points"] = all_defensive

    # Keep primary's limitation, court_rules, coa_type
    # Add alternative limitations
    alt_limitations = []
    for entry in entries[1:]:
        lim = entry.get("limitation")
        if lim and lim != primary.get("limitation"):
            alt_limitations.append(lim)
    if alt_limitations:
        primary["alternative_limitations"] = alt_limitations

    return primary


def get_all_cause_types(domain: str) -> List[str]:
    """List all registered cause types for a domain."""
    return list(_REGISTRY.get(domain.lower(), {}).keys())


def filter_superseded_provisions(provisions: List[dict]) -> List[dict]:
    """Remove provisions citing superseded/repealed Acts."""
    filtered = []
    for p in provisions:
        act = p.get("act", "")
        if is_superseded(act):
            logger.info(
                "[LKB] filtered superseded provision: %s %s → %s",
                p.get("section", ""), act, get_current_act(act),
            )
            continue
        filtered.append(p)
    return filtered


def apply_specificity_rule(limitation_article: Optional[str], lkb_article: Optional[str]) -> str:
    """Apply specific-before-residuary rule for limitation articles.

    If pipeline selected a residuary article (113) but LKB has a specific one,
    use the LKB article instead.
    """
    if not lkb_article:
        return limitation_article or "UNKNOWN"

    if limitation_article in RESIDUARY_ARTICLES and lkb_article not in RESIDUARY_ARTICLES:
        logger.info(
            "[LKB] specificity rule: replacing residuary Article %s with specific Article %s",
            limitation_article, lkb_article,
        )
        return lkb_article

    return limitation_article or lkb_article


# ---------------------------------------------------------------------------
# Keyword-based cause type inference (fallback when LLM doesn't classify)
# ---------------------------------------------------------------------------

def _score_keywords(text, keywords):
    return sum(1.0 for kw in keywords if kw.lower() in text)


def infer_cause_type(doc_type, user_request, topics=None):
    """Infer cause_type from keywords when LLM classification is missing."""
    text = f"{doc_type} {user_request} {' '.join(topics or [])}".lower()
    domain_entries = _REGISTRY.get("civil", {})
    best, best_score = "", 0.0
    for code, entry in domain_entries.items():
        score = _score_keywords(text, entry.get("doc_type_keywords", []))
        if code == "money_recovery_loan" and ("advance" in text and ("fail" in text or "refund" in text)):
            score -= 0.5
        if code == "declaration_title" and ("possession" in text or "vacate" in text):
            score -= 0.5
        if code == "permanent_injunction" and ("declaration" in text or "title" in text):
            score -= 0.25
        if code == "summary_suit_instrument" and "order 37" in text:
            score += 0.75
        if code == "specific_performance" and "agreement to sell" in text:
            score += 0.5
        if code.startswith("recovery_of_possession") and ("unauthorized occupation" in text or "vacate" in text):
            score += 0.5
        if code.startswith("recovery_of_possession") and ("encroach" in text and "damages" in text and "possession" not in text):
            score -= 0.25
        if score > best_score:
            best, best_score = code, score
    if not best or best_score <= 0:
        return "", 0.0
    total = max(len(domain_entries[best].get("doc_type_keywords", [])), 1)
    return best, min(best_score / total, 0.70)


# ---------------------------------------------------------------------------
# Auto-register domains on import
# ---------------------------------------------------------------------------
from .causes import SUBSTANTIVE_CAUSES  # noqa: E402

# Register only for Civil — domain boundaries are hard.
# Other domains (Criminal, Family, Corporate, IP) need their own knowledge bases.
register_domain("Civil", SUBSTANTIVE_CAUSES)

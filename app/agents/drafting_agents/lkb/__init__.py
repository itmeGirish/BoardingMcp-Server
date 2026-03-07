"""Legal Knowledge Base (LKB) — structured legal lookup replacing noisy RAG for law selection.

LKB provides deterministic answers to questions that are NOT search questions:
  - Which Act applies?       → lookup, not search
  - Which limitation article? → rule, not search
  - Which court format?      → calculation, not search
  - Which damages categories? → mapping, not search

RAG still provides statutory TEXT. LKB provides the CORRECT law to cite.

Usage:
    from app.agents.drafting_agents.lkb import lookup, lookup_multi

    entry = lookup("Civil", "breach_of_contract")
    entries = lookup_multi("Civil", ["breach_of_contract", "money_recovery"])
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from ....config import logger


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

# ---------------------------------------------------------------------------
# Alias map — common LLM near-misses → correct LKB key
# ---------------------------------------------------------------------------

_CAUSE_TYPE_ALIASES: Dict[str, str] = {
    # recovery_of_possession aliases
    "property_law": "recovery_of_possession",
    "eviction_unauthorized_occupation": "recovery_of_possession",
    "eviction_plaint": "recovery_of_possession",
    "possession_suit": "recovery_of_possession",
    "recovery_possession": "recovery_of_possession",
    "suit_for_possession": "recovery_of_possession",
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
    # injunction aliases
    "injunction": "permanent_injunction",
    "injunction_suit": "permanent_injunction",
    # defamation aliases
    "defamation_suit": "defamation",
    "civil_defamation": "defamation",
}


def register_domain(domain: str, entries: Dict[str, dict]) -> None:
    """Register all cause type entries for a legal domain."""
    _REGISTRY[domain.lower()] = entries
    logger.info("[LKB] registered %d entries for domain=%s", len(entries), domain)


def lookup(domain: str, cause_type: str) -> Optional[dict]:
    """Look up a single cause type entry. Falls back to alias map for near-misses."""
    domain_entries = _REGISTRY.get(domain.lower(), {})
    entry = domain_entries.get(cause_type)
    if entry:
        logger.info("[LKB] hit: domain=%s cause_type=%s", domain, cause_type)
        return entry

    # Try alias map
    aliased = _CAUSE_TYPE_ALIASES.get(cause_type)
    if aliased:
        entry = domain_entries.get(aliased)
        if entry:
            logger.info("[LKB] hit via alias: domain=%s %s → %s", domain, cause_type, aliased)
            return entry

    logger.warning("[LKB] miss: domain=%s cause_type=%s", domain, cause_type)
    return entry


def lookup_multi(domain: str, cause_types: List[str]) -> List[dict]:
    """Look up multiple cause types and return all found entries."""
    domain_entries = _REGISTRY.get(domain.lower(), {})
    results = []
    for ct in cause_types:
        entry = domain_entries.get(ct)
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
# Conditional field resolver
# ---------------------------------------------------------------------------

# Keyword map: resolve_by key → [(condition_value, [keywords]), ...]
# Order matters: more specific matches FIRST.
_INFERENCE_MAP: Dict[str, list] = {
    "occupancy_type": [
        ("tenant_holding_over", ["holding over", "accepted rent after expiry", "assented to continued"]),
        ("tenant_determined", ["tenant", "lease", "lessee", "tenancy", "rent", "lease expired", "lease expiry"]),
        ("licensee_revoked", ["license", "licensee", "permissive", "leave and license", "permission"]),
        ("trespasser", ["trespass", "encroach", "squat", "unauthorized entry"]),
    ],
    "loan_character": [
        ("lender_gave_cheque", ["cheque", "check", "banker's cheque", "demand draft"]),
        ("payable_on_demand_under_agreement", ["on demand", "payable on demand", "demand loan"]),
        ("simple_loan", ["loan", "lent", "advance", "hand loan", "borrowed"]),
    ],
    "repayment_date_fixed": [
        (True, ["fixed date", "repayment date", "due date", "payable on", "repayment on"]),
        (False, ["on demand", "no date", "oral loan", "hand loan"]),
    ],
    "credit_period_fixed": [
        (True, ["credit period", "payment terms", "net 30", "net 60", "credit of"]),
        (False, ["no credit", "cash", "immediate payment"]),
    ],
    "statement_medium": [
        ("written_or_published", ["written", "social media", "newspaper", "publication", "email", "letter", "post", "article", "blog", "whatsapp", "sms", "message"]),
        ("oral_only", ["oral", "spoken", "verbal", "said", "uttered", "shouted"]),
    ],
    "eviction_ground": [
        ("default_rent", ["default", "arrears", "non-payment", "unpaid rent"]),
        ("personal_need", ["personal need", "bonafide need", "own use", "bona fide"]),
        ("subletting", ["sublet", "subletting", "sub-let", "unauthorized occupant"]),
        ("misuse", ["misuse", "change of use", "nuisance", "illegal activity"]),
    ],
    "state": [
        ("Karnataka", ["karnataka", "bengaluru", "bangalore", "mysuru", "mysore", "hubli"]),
        ("Maharashtra", ["maharashtra", "mumbai", "pune", "nagpur", "thane"]),
        ("Tamil Nadu", ["tamil nadu", "chennai", "madras", "coimbatore", "madurai"]),
        ("Delhi", ["delhi", "new delhi"]),
        ("Telangana", ["telangana", "hyderabad", "secunderabad"]),
        ("Uttar Pradesh", ["uttar pradesh", "lucknow", "kanpur", "agra", "varanasi", "allahabad", "prayagraj", "meerut", "noida", "ghaziabad"]),
        ("West Bengal", ["west bengal", "kolkata", "calcutta", "howrah", "durgapur", "asansol", "siliguri"]),
        ("Andhra Pradesh", ["andhra pradesh", "visakhapatnam", "vizag", "vijayawada", "guntur", "tirupati", "kurnool", "nellore"]),
        ("Gujarat", ["gujarat", "ahmedabad", "surat", "vadodara", "baroda", "rajkot", "gandhinagar"]),
        ("Rajasthan", ["rajasthan", "jaipur", "jodhpur", "kota", "bikaner", "ajmer", "udaipur"]),
    ],
    "credit_period_status": [
        ("fixed_credit_period", ["credit period", "payment terms", "net 30", "net 60", "net 90", "credit of", "payable within"]),
        ("no_fixed_credit_period", ["no credit", "cash", "immediate payment", "on delivery", "cod"]),
    ],
    "deposit_refund_trigger": [
        ("payable_on_demand", ["on demand", "payable on demand", "demand loan", "security deposit", "rent deposit", "caution deposit"]),
        ("event_triggered_refund", ["tenancy ended", "lease expired", "lease terminated", "advance", "token", "earnest", "booking amount", "sale cancelled", "agreement terminated"]),
    ],
    "instrument_type": [
        ("cheque", ["cheque", "check", "banker's cheque", "demand draft"]),
        ("promissory_note_payable_on_demand", ["promissory note", "pronote", "pro-note"]),
        ("bill_of_exchange_payable_on_demand", ["bill of exchange", "hundi", "bill payable"]),
    ],
    "movable_acquisition": [
        ("lost_stolen_converted", ["stolen", "lost", "converted", "misappropriated", "theft", "conversion", "wrongfully taken"]),
        ("other_wrongful_taking", ["detained", "withheld", "refused to return", "bailment", "entrusted", "deposited", "custody", "pledged"]),
    ],
    "ouster_status": [
        ("ouster_or_exclusion_alleged", ["ouster", "ousted", "dispossessed", "thrown out", "locked out", "denied entry", "excluded"]),
        ("joint_possession_case", ["joint possession", "co-owner", "coparcener", "undivided", "joint family"]),
        ("erroneous_prior_partition", ["erroneous partition", "wrong partition", "fraudulent partition", "illegal partition", "partition set aside"]),
    ],
    "relief_form": [
        ("declaration_plus_injunction", ["declaration", "declare", "title", "declare and restrain", "declare right"]),
        ("injunction_only", ["injunction", "restrain", "prohibit", "stop", "enjoin"]),
    ],
    "mortgage_relief": [
        ("foreclosure", ["foreclosure", "foreclose", "extinguish equity"]),
        ("sale", ["sale", "sell", "auction", "realise mortgage"]),
    ],
    "negligence_injury_type": [
        ("personal_injury_or_bodily_harm", ["injury", "bodily harm", "personal injury", "accident", "hurt", "disabled", "fracture", "medical negligence", "death"]),
        ("property_damage_or_economic_loss", ["property damage", "economic loss", "financial loss", "loss of profit", "damage to goods", "vehicle damage"]),
    ],
    "forum_track": [
        ("special_rent_forum", ["rent control", "rent controller", "rent court", "rent tribunal", "eviction petition"]),
        ("ordinary_tpa_suit", ["civil court", "civil suit", "tpa", "transfer of property"]),
    ],
    "trespass_relief": [
        ("possession_based_on_title", ["title", "owner", "ownership", "title deed", "sale deed", "patta"]),
        ("possession_based_on_prior_possession", ["prior possession", "dispossessed", "trespass", "encroach", "squat", "was in possession"]),
        ("damages_only", ["damages only", "compensation", "loss only", "no possession"]),
    ],
    "dissolution_status": [
        ("accounts_after_dissolution", ["already dissolved", "dissolved", "dissolution deed", "notice of dissolution", "after dissolution"]),
        ("court_dissolution_of_subsisting_firm", ["seek dissolution", "judicial dissolution", "dissolve the firm", "subsisting firm", "running firm"]),
    ],
    "guarantee_or_indemnity_type": [
        ("indemnity", ["indemnity", "indemnifier", "indemnified", "hold harmless", "indemnification"]),
        ("guarantee", ["guarantee", "guarantor", "surety", "bank guarantee", "performance guarantee", "letter of credit"]),
    ],
}


def _infer_condition(resolve_by: str, context: str) -> Union[str, bool, None]:
    """Infer condition value from user context text using keyword matching."""
    ctx = context.lower()
    rules = _INFERENCE_MAP.get(resolve_by, [])
    for value, keywords in rules:
        if any(kw in ctx for kw in keywords):
            return value
    return None  # no match → caller uses _default


def _matches_when(when: Any, condition_value: Any) -> bool:
    """Check if a rule's 'when' matches the inferred condition value."""
    if isinstance(when, list):
        return condition_value in when
    if isinstance(when, bool):
        return condition_value is when
    return str(when) == str(condition_value)


def resolve_conditional(field: Any, context: str) -> Any:
    """Resolve a single conditional field based on context text.

    If field is not conditional (no _type: "conditional"), returns it unchanged.
    If conditional but can't resolve, returns _default.
    """
    if not isinstance(field, dict) or field.get("_type") != "conditional":
        return field

    resolve_by = field.get("_resolve_by", "")
    rules = field.get("_rules", [])
    default = field.get("_default")

    condition_value = _infer_condition(resolve_by, context)
    if condition_value is None:
        logger.info("[LKB] conditional: no match for resolve_by=%s → using default", resolve_by)
        return default

    for rule in rules:
        if _matches_when(rule.get("when"), condition_value):
            logger.info(
                "[LKB] conditional: resolve_by=%s matched=%s",
                resolve_by, condition_value,
            )
            return rule.get("then", default)

    logger.info("[LKB] conditional: resolve_by=%s value=%s no rule matched → default", resolve_by, condition_value)
    return default


def resolve_entry(entry: dict, context: str) -> dict:
    """Resolve ALL conditional fields in an LKB entry.

    Walks top-level fields. If any has _type: "conditional", resolves it.
    Returns a new dict with all conditionals resolved to flat values.
    """
    if not entry or not context:
        return entry

    resolved = {}
    for key, value in entry.items():
        resolved[key] = resolve_conditional(value, context)

    return resolved


# ---------------------------------------------------------------------------
# Auto-register domains on import
# ---------------------------------------------------------------------------
from .civil import CIVIL_CAUSE_TYPES  # noqa: E402

register_domain("Civil", CIVIL_CAUSE_TYPES)

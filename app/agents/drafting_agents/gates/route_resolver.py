"""
Route Resolver Gate  (CLAUD.md Step 4C) -- Rule-based, NO LLM calls.

Resolves conflicts between the rule_classifier (Step 4A) and the
llm_classifier (Step 4B) outputs, producing a single resolved route
with the determined doc_type, court_type, legal_domain, and the list
of agents required for downstream processing.
"""


# ---------------------------------------------------------------------------
# Proceeding types that require research + citation agents
# ---------------------------------------------------------------------------

_RESEARCH_PROCEEDING_TYPES = frozenset([
    "writ petition",
    "quash",
    "bail",
    "appeal",
    "revision",
])

# Agents that are always included regardless of document type
_BASE_AGENTS = [
    "template_pack",
    "compliance",
    "localization",
    "prayer",
]

# Extra agents triggered by certain proceeding types
_RESEARCH_AGENTS = [
    "research_agent",
    "citation_agent",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _determine_agents(proceeding_type: str | None) -> list[str]:
    """
    Build the list of required agents based on the proceeding type.

    Always includes base agents; adds research/citation agents when the
    proceeding type is one of the research-heavy categories.
    """
    agents = list(_BASE_AGENTS)

    if proceeding_type and proceeding_type.lower().strip() in _RESEARCH_PROCEEDING_TYPES:
        # Insert research agents before the base agents so they run first
        agents = list(_RESEARCH_AGENTS) + agents

    return agents


def _pick_winner(
    rule_val: str | None,
    rule_conf: float,
    llm_val: str | None,
    llm_conf: float,
    field_name: str,
) -> tuple[str | None, bool, dict | None]:
    """
    Decide which classifier's value to use for a single field.

    Returns:
        (chosen_value, needs_clarification, conflict_detail_or_None)
    """
    # Both agree
    if rule_val and llm_val and rule_val.lower().strip() == llm_val.lower().strip():
        return rule_val, False, None

    # Only one has a value
    if rule_val and not llm_val:
        return rule_val, False, None
    if llm_val and not rule_val:
        return llm_val, False, None

    # Neither has a value
    if not rule_val and not llm_val:
        return None, True, {
            "field": field_name,
            "reason": "neither_classifier_produced_value",
            "rule_guess": None,
            "llm_guess": None,
        }

    # Conflict: both have different values
    # Prefer rule_classifier if its confidence >= 0.80
    if rule_conf >= 0.80:
        return rule_val, False, {
            "field": field_name,
            "reason": "conflict_resolved_by_rule_classifier_confidence",
            "rule_guess": rule_val,
            "rule_confidence": rule_conf,
            "llm_guess": llm_val,
            "llm_confidence": llm_conf,
        }

    # Prefer llm_classifier if its confidence >= 0.85
    if llm_conf >= 0.85:
        return llm_val, False, {
            "field": field_name,
            "reason": "conflict_resolved_by_llm_classifier_confidence",
            "rule_guess": rule_val,
            "rule_confidence": rule_conf,
            "llm_guess": llm_val,
            "llm_confidence": llm_conf,
        }

    # Unresolvable conflict -- flag for clarification
    return None, True, {
        "field": field_name,
        "reason": "unresolvable_conflict",
        "rule_guess": rule_val,
        "rule_confidence": rule_conf,
        "llm_guess": llm_val,
        "llm_confidence": llm_conf,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_route(
    rule_classification: dict,
    llm_classification: dict,
) -> dict:
    """
    Route Resolver gate (Step 4C).

    Merges outputs of rule_classifier (4A) and llm_classifier (4B) into a
    single authoritative route.  Pure rule-based -- no LLM calls.

    Args:
        rule_classification: Output dict from ``classify_by_rules``.
            Expected keys: doc_type_guess, court_type_guess,
            legal_domain_guess, confidence.
        llm_classification:  Output dict from the LLM classifier.
            Expected keys: doc_type, court_type, legal_domain,
            proceeding_type, draft_goal, language, draft_style,
            confidence.

    Returns:
        dict with keys:
            gate               - "route_resolver"
            passed             - bool
            resolved_route     - {doc_type, court_type, legal_domain,
                                  proceeding_type, draft_goal, language,
                                  draft_style}
            agents_required    - list[str]
            needs_clarification - bool
            conflict_details   - dict (per-field conflict info)
    """
    rule_conf = float(rule_classification.get("confidence", 0.0))
    llm_conf = float(llm_classification.get("confidence", 0.0))

    conflict_details: dict[str, dict] = {}
    any_clarification = False

    # --- Resolve doc_type ---
    doc_type, doc_clar, doc_conflict = _pick_winner(
        rule_classification.get("doc_type_guess"),
        rule_conf,
        llm_classification.get("doc_type"),
        llm_conf,
        "doc_type",
    )
    if doc_clar:
        any_clarification = True
    if doc_conflict:
        conflict_details["doc_type"] = doc_conflict

    # --- Resolve court_type ---
    court_type, court_clar, court_conflict = _pick_winner(
        rule_classification.get("court_type_guess"),
        rule_conf,
        llm_classification.get("court_type"),
        llm_conf,
        "court_type",
    )
    if court_clar:
        any_clarification = True
    if court_conflict:
        conflict_details["court_type"] = court_conflict

    # --- Resolve legal_domain ---
    legal_domain, domain_clar, domain_conflict = _pick_winner(
        rule_classification.get("legal_domain_guess"),
        rule_conf,
        llm_classification.get("legal_domain"),
        llm_conf,
        "legal_domain",
    )
    if domain_clar:
        any_clarification = True
    if domain_conflict:
        conflict_details["legal_domain"] = domain_conflict

    # --- Fields only available from LLM classifier (no conflict possible) ---
    proceeding_type = llm_classification.get("proceeding_type")
    draft_goal = llm_classification.get("draft_goal")
    language = llm_classification.get("language", "English")
    draft_style = llm_classification.get("draft_style", "formal")

    # --- Compute merged confidence ---
    # If both agree on doc_type, confidence = max of both
    rule_doc = (rule_classification.get("doc_type_guess") or "").lower().strip()
    llm_doc = (llm_classification.get("doc_type") or "").lower().strip()
    if rule_doc and llm_doc and rule_doc == llm_doc:
        merged_confidence = max(rule_conf, llm_conf)
    else:
        merged_confidence = max(rule_conf, llm_conf)

    merged_confidence = round(merged_confidence, 2)

    # --- Determine required agents ---
    agents_required = _determine_agents(proceeding_type)

    # --- Build resolved route ---
    resolved_route = {
        "doc_type": doc_type,
        "court_type": court_type,
        "legal_domain": legal_domain,
        "proceeding_type": proceeding_type,
        "draft_goal": draft_goal,
        "language": language,
        "draft_style": draft_style,
        "confidence": merged_confidence,
    }

    # Gate passes only if we have at least a doc_type and no clarification needed
    passed = (doc_type is not None) and (not any_clarification)

    return {
        "gate": "route_resolver",
        "passed": passed,
        "resolved_route": resolved_route,
        "agents_required": agents_required,
        "needs_clarification": any_clarification,
        "conflict_details": conflict_details,
    }

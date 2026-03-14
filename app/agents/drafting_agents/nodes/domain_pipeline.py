from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END
from langgraph.types import Command

from ....config import logger, settings
from ..plugins import get_domain_plugin, resolve_domain_plugin
from ..states import DomainDecision, DraftPlanIR, DraftingState
from ._utils import _as_dict


def _next_context_node() -> str:
    """Always route to enrichment — RAG disconnected (code kept, not called)."""
    return "enrichment"


def _rewrite_goto(goto: str, mapping: Dict[str, str]) -> str:
    return mapping.get(goto, goto)


def _mirror_civil_decision(plugin_key: str, law_domain: str, decision: Dict[str, Any]) -> Dict[str, Any]:
    return DomainDecision(
        enabled=bool(decision.get("enabled")),
        plugin_key=plugin_key,
        law_domain=law_domain or None,
        family=decision.get("family"),
        subtype=decision.get("resolved_cause_type") or decision.get("original_cause_type"),
        relationship_track=decision.get("relationship_track"),
        status=decision.get("status", "not_applicable"),
        draft_strategy=decision.get("draft_strategy", "free_text"),
        template_eligible=bool(decision.get("template_eligible")),
        maintainability_checks=list(decision.get("maintainability_checks") or []),
        ambiguity_flags=list(decision.get("ambiguity_flags") or []),
        blocking_issues=list(decision.get("blocking_issues") or []),
        limitation=dict(decision.get("limitation") or {}),
        allowed_statutes=list(decision.get("allowed_statutes") or []),
        forbidden_statutes=list(decision.get("forbidden_statutes") or []),
        allowed_reliefs=list(decision.get("allowed_reliefs") or []),
        forbidden_reliefs=list(decision.get("forbidden_reliefs") or []),
        allowed_damages=list(decision.get("allowed_damages") or []),
        forbidden_damages=list(decision.get("forbidden_damages") or []),
        allowed_doctrines=list(decision.get("allowed_doctrines") or []),
        forbidden_doctrines=list(decision.get("forbidden_doctrines") or []),
        filtered_red_flags=list(decision.get("filtered_red_flags") or []),
        route_reason=decision.get("route_reason", ""),
        confidence=float(decision.get("confidence") or 0.0),
    ).model_dump()


def _mirror_civil_plan(plugin_key: str, law_domain: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    return DraftPlanIR(
        plugin_key=plugin_key,
        law_domain=law_domain or None,
        family=plan.get("family"),
        subtype=plan.get("cause_type"),
        relationship_track=plan.get("relationship_track"),
        route_reason=plan.get("route_reason", ""),
        required_sections=list(plan.get("required_sections") or []),
        required_reliefs=list(plan.get("required_reliefs") or []),
        optional_reliefs=list(plan.get("optional_reliefs") or []),
        required_averments=list(plan.get("required_averments") or []),
        mandatory_inline_sections=list(plan.get("mandatory_inline_sections") or []),
        maintainability_checks=list(plan.get("maintainability_checks") or []),
        limitation=dict(plan.get("limitation") or {}),
        verified_provisions=list(plan.get("verified_provisions") or []),
        evidence_checklist=list(plan.get("evidence_checklist") or []),
        red_flags=list(plan.get("red_flags") or []),
        missing_fields=list(plan.get("missing_fields") or []),
        constraints={
            "cause_type": plan.get("cause_type", ""),
            "relationship_track": plan.get("relationship_track"),
            "allowed_statutes": list(plan.get("allowed_statutes") or []),
            "forbidden_statutes": list(plan.get("forbidden_statutes") or []),
            "allowed_reliefs": list(plan.get("allowed_reliefs") or []),
            "forbidden_reliefs": list(plan.get("forbidden_reliefs") or []),
            "allowed_damages": list(plan.get("allowed_damages") or []),
            "forbidden_damages": list(plan.get("forbidden_damages") or []),
            "allowed_doctrines": list(plan.get("allowed_doctrines") or []),
            "forbidden_doctrines": list(plan.get("forbidden_doctrines") or []),
            "filtered_red_flags": list(plan.get("filtered_red_flags") or []),
        },
    ).model_dump()


def domain_router_node(state: DraftingState) -> Command:
    classify = _as_dict(state.get("classify"))
    law_domain = classify.get("law_domain", "")
    plugin = resolve_domain_plugin(law_domain)
    plugin_key = plugin.key if plugin else None
    logger.info("[DOMAIN_ROUTER] law_domain=%s plugin=%s", law_domain or "unknown", plugin_key or "none")
    return Command(update={"domain_plugin": plugin_key}, goto="domain_decision_compiler")


def domain_decision_compiler_node(state: DraftingState) -> Command:
    classify = _as_dict(state.get("classify"))
    law_domain = classify.get("law_domain", "")
    plugin_key = state.get("domain_plugin")
    plugin = get_domain_plugin(str(plugin_key)) if plugin_key else None

    if not plugin:
        decision = DomainDecision(
            enabled=False,
            plugin_key=None,
            law_domain=law_domain or None,
            status="not_applicable",
            route_reason=f"No domain plugin registered for law_domain={law_domain or 'unknown'}.",
            blocking_issues=[f"Domain '{law_domain or 'unknown'}' is not supported. Only Civil domain has a registered plugin."],
        )
        blocked_artifact = {
            "draft_artifacts": [{
                "doc_type": classify.get("doc_type", "unsupported"),
                "title": "UNSUPPORTED DOMAIN",
                "text": (
                    f"UNSUPPORTED DOMAIN: {law_domain or 'unknown'}\n\n"
                    f"The drafting pipeline currently supports only Civil domain.\n"
                    f"Domain '{law_domain or 'unknown'}' does not have a registered plugin.\n\n"
                    f"No draft was generated to prevent unverified legal output."
                ),
                "placeholders_used": [],
                "citations_used": [],
            }]
        }
        logger.warning("[DOMAIN_DECISION] blocking unsupported domain=%s", law_domain or "unknown")
        return Command(
            update={
                "decision_ir": decision.model_dump(),
                "plan_ir": None,
                "domain_gate_issues": [{"type": "unsupported_domain", "severity": "blocking", "issue": f"Domain '{law_domain or 'unknown'}' not supported."}],
                "errors": [f"Domain '{law_domain or 'unknown'}' not supported."],
                "draft": blocked_artifact,
                "final_draft": blocked_artifact,
            },
            goto=END,
        )

    result = plugin.decision_node(state)
    update = dict(result.update or {})
    if plugin.key == "civil":
        update["decision_ir"] = _mirror_civil_decision(plugin.key, law_domain, _as_dict(update.get("civil_decision")))
    update["domain_plugin"] = plugin.key
    goto = _rewrite_goto(result.goto, {"civil_ambiguity_gate": "domain_ambiguity_gate"})
    return Command(update=update, goto=goto)


def domain_ambiguity_gate_node(state: DraftingState) -> Command:
    plugin_key = state.get("domain_plugin")
    plugin = get_domain_plugin(str(plugin_key)) if plugin_key else None
    if not plugin:
        return Command(update={"domain_gate_issues": []}, goto=_next_context_node())

    result = plugin.ambiguity_gate_node(state)
    update = dict(result.update or {})
    if plugin.key == "civil":
        update["domain_gate_issues"] = list(update.get("civil_gate_issues") or [])
    return Command(update=update, goto=result.goto)


def domain_plan_compiler_node(state: DraftingState) -> Command:
    classify = _as_dict(state.get("classify"))
    law_domain = classify.get("law_domain", "")
    plugin_key = state.get("domain_plugin")
    plugin = get_domain_plugin(str(plugin_key)) if plugin_key else None

    if not plugin:
        return Command(update={"plan_ir": None}, goto="domain_draft_router")

    result = plugin.plan_compiler_node(state)
    update = dict(result.update or {})
    if plugin.key == "civil":
        update["plan_ir"] = _mirror_civil_plan(plugin.key, law_domain, _as_dict(update.get("civil_draft_plan")))
    goto = _rewrite_goto(result.goto, {"civil_draft_router": "domain_draft_router"})
    return Command(update=update, goto=goto)


def domain_draft_router_node(state: DraftingState) -> Command:
    plugin_key = state.get("domain_plugin")
    plugin = get_domain_plugin(str(plugin_key)) if plugin_key else None
    if not plugin:
        logger.info("[DOMAIN_DRAFT_ROUTER] no plugin resolved -> draft_freetext")
        return Command(goto="draft_freetext")
    return plugin.draft_router_node(state)


def domain_consistency_gate_node(state: DraftingState) -> Command:
    plugin_key = state.get("domain_plugin")
    plugin = get_domain_plugin(str(plugin_key)) if plugin_key else None
    if not plugin:
        return Command(update={"domain_gate_issues": []}, goto="evidence_anchoring")

    result = plugin.consistency_gate_node(state)
    update = dict(result.update or {})
    if plugin.key == "civil":
        update["domain_gate_issues"] = list(update.get("civil_gate_issues") or [])
    return Command(update=update, goto=result.goto)

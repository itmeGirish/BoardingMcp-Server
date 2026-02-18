"""
Legal Drafting Pipeline — Entry Point

Assembles the legal drafting workflow:
  - Supervisor (chat entry point)
  - 12 pipeline gate nodes (deterministic, NO LLM)
  - 11 sub-agent graphs (LLM-powered)
  - Fan-out/fan-in parallel execution (Steps 8.1-8.3)
  - Conditional execution (Steps 9.1-9.2)

Registered in langgraph.json as:
    "legal_drafting_agent": "app.agents.drafting_agents.legal_drafting:legal_drafting_graph"
"""
from functools import partial
from .graphs.supervisor import create_graph
from .states.legal_drafting import LegalDraftingState
from .prompts.supervisor import SUPERVISOR_SYSTEM_PROMPT
from .tools.supervisor import BACKEND_TOOLS, BACKEND_TOOL_NAMES, DELEGATION_TOOL_MAP
from .nodes.supervisor import call_model_node, route_after_tool

# ── Pipeline gate nodes (deterministic, NO LLM) ──
from .nodes.pipeline_gates import (
    security_gate_node,
    fact_validation_gate_node,
    rule_classifier_gate_node,
    route_resolver_gate_node,
    clarification_gate_node,
    mistake_rules_fetch_node,
    citation_validation_gate_node,
    context_merge_gate_node,
    fact_traceability_gate_node,
    staging_rules_node,
    promotion_gate_node,
    export_gate_node,
    should_clarify,
)

# ── Sub-agent graphs (LLM-powered) ──
from .sub_agents.intake_agent import intake_graph
from .sub_agents.fact_extraction_agent import fact_extraction_graph
from .sub_agents.llm_classifier_agent import llm_classifier_graph
from .sub_agents.template_pack_agent import template_pack_graph
from .sub_agents.compliance_agent import compliance_graph
from .sub_agents.localization_agent import localization_graph
from .sub_agents.prayer_agent import prayer_graph
from .sub_agents.research_agent import research_graph
from .sub_agents.citation_agent import citation_graph
from .sub_agents.drafting_agent import drafting_graph
from .sub_agents.review_agent import review_graph


def _create_call_model_node_with_dependencies():
    return partial(
        call_model_node,
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        tools=BACKEND_TOOLS,
        tool_names_set=BACKEND_TOOL_NAMES,
        delegation_tool_map=DELEGATION_TOOL_MAP,
    )


def _create_route_after_tool_func():
    return partial(
        route_after_tool,
        delegation_tool_map=DELEGATION_TOOL_MAP,
    )


def _assemble_graph():
    # All LLM-powered sub-agents
    sub_agents = {
        "intake": intake_graph,
        "fact_extraction": fact_extraction_graph,
        "llm_classifier": llm_classifier_graph,
        "template_pack": template_pack_graph,
        "compliance": compliance_graph,
        "localization": localization_graph,
        "prayer": prayer_graph,
        "research": research_graph,
        "citation": citation_graph,
        "drafting": drafting_graph,
        "review": review_graph,
    }

    # All deterministic pipeline gate nodes
    pipeline_gates = {
        "security_gate": security_gate_node,
        "fact_validation_gate": fact_validation_gate_node,
        "rule_classifier_gate": rule_classifier_gate_node,
        "route_resolver_gate": route_resolver_gate_node,
        "clarification_gate": clarification_gate_node,
        "mistake_rules_fetch": mistake_rules_fetch_node,
        "citation_validation_gate": citation_validation_gate_node,
        "context_merge_gate": context_merge_gate_node,
        "fact_traceability_gate": fact_traceability_gate_node,
        "staging_rules": staging_rules_node,
        "promotion_gate": promotion_gate_node,
        "export_gate": export_gate_node,
        "should_clarify": should_clarify,
    }

    return create_graph(
        state_class=LegalDraftingState,
        call_model_node_func=_create_call_model_node_with_dependencies(),
        tools=BACKEND_TOOLS,
        route_after_tool_func=_create_route_after_tool_func(),
        sub_agents=sub_agents,
        pipeline_gates=pipeline_gates,
    )


# Create singleton — referenced in langgraph.json
legal_drafting_graph = _assemble_graph()

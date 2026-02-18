"""
LangGraph workflow structure for the 18-step Legal Drafting Pipeline.

Graph Structure:
  START → call_model (supervisor chat)
            ↓ (delegates via tools)
          tool_node → route_after_tool
            ↓
  Pipeline (deterministic 18-step flow):
    security_gate → intake → fact_validation_gate →
    rule_classifier_gate → llm_classifier → route_resolver_gate →
    clarification_gate → (if needs_clarification → call_model) →
    mistake_rules_fetch → template_pack →
    ┌── compliance ──┐
    ├── localization ─┤  (parallel fan-out / fan-in)
    └── prayer ──────┘
    → optional_router → [research → citation] (conditional) →
    citation_validation_gate → context_merge_gate →
    drafting → fact_traceability_gate → review →
    staging_rules → promotion_gate → export_gate → END

Fan-out/fan-in: compliance, localization, prayer run in PARALLEL.
Conditional: research + citation only run if route requires them.
"""
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from ....config import logger


def create_graph(
    state_class,
    call_model_node_func,
    tools,
    route_after_tool_func=None,
    sub_agents: dict = None,
    pipeline_gates: dict = None,
):
    """
    Create the 18-step legal drafting pipeline graph.

    Args:
        state_class: LegalDraftingState class
        call_model_node_func: Supervisor call_model (for chat + clarification)
        tools: Supervisor backend tools
        route_after_tool_func: Post-tool routing function
        sub_agents: Dict of compiled sub-agent graphs
        pipeline_gates: Dict of gate node functions
    """
    logger.info("Creating 18-step legal drafting pipeline graph...")

    sub_agents = sub_agents or {}
    pipeline_gates = pipeline_gates or {}

    workflow = StateGraph(state_class)

    # ── Core supervisor nodes ──
    workflow.add_node("call_model", call_model_node_func)
    workflow.add_node("tool_node", ToolNode(tools=tools))

    # ── Pipeline gate nodes (deterministic, NO LLM) ──
    gate_names = [
        "security_gate", "fact_validation_gate", "rule_classifier_gate",
        "route_resolver_gate", "clarification_gate", "mistake_rules_fetch",
        "citation_validation_gate", "context_merge_gate",
        "fact_traceability_gate",
        "staging_rules", "promotion_gate", "export_gate",
    ]
    for gate_name in gate_names:
        if gate_name in pipeline_gates:
            workflow.add_node(gate_name, pipeline_gates[gate_name])
            logger.info(f"  Pipeline gate registered: {gate_name}")

    # ── Sub-agent nodes (LLM-powered) ──
    for agent_name, agent_graph in sub_agents.items():
        workflow.add_node(agent_name, agent_graph)
        logger.info(f"  Sub-agent registered: {agent_name}")

    # ── Optional router node ──
    async def optional_router_node(state):
        """Merge point after parallel agents. Routes to optional agents."""
        logger.info("[Pipeline] Optional router: evaluating research/citation need")
        return {"drafting_phase": "OPTIONAL_AGENTS"}

    workflow.add_node("optional_router", optional_router_node)

    # ── Entry point ──
    workflow.set_entry_point("call_model")

    # ══════════════════════════════════════════════════════════════
    # EDGES: 18-step pipeline flow
    # ══════════════════════════════════════════════════════════════

    # ── Supervisor chat → tool_node routing ──
    if route_after_tool_func:
        possible_targets = ["call_model", "security_gate"] + list(sub_agents.keys())
        workflow.add_conditional_edges(
            "tool_node",
            route_after_tool_func,
            possible_targets,
        )
    else:
        workflow.add_edge("tool_node", "call_model")

    # ── Step 1 → Step 2: Security Gate → Intake ──
    workflow.add_edge("security_gate", "intake")

    # ── Step 2 → Step 3: Intake → Fact Validation ──
    workflow.add_edge("intake", "fact_validation_gate")

    # ── Step 3 → Step 4A: Fact Validation → Rule Classifier ──
    workflow.add_edge("fact_validation_gate", "rule_classifier_gate")

    # ── Step 4A → Step 4B: Rule Classifier → LLM Classifier ──
    workflow.add_edge("rule_classifier_gate", "llm_classifier")

    # ── Step 4B → Step 4C: LLM Classifier → Route Resolver ──
    workflow.add_edge("llm_classifier", "route_resolver_gate")

    # ── Step 4C → Step 5: Route Resolver → Clarification Check ──
    workflow.add_edge("route_resolver_gate", "clarification_gate")

    # ── Step 5: Clarification → conditional (pause or continue) ──
    should_clarify = pipeline_gates.get("should_clarify")
    if should_clarify:
        workflow.add_conditional_edges(
            "clarification_gate",
            should_clarify,
            ["call_model", "mistake_rules_fetch"],
        )

    # ── Step 6 → Step 7: Mistake Rules → Template Pack ──
    workflow.add_edge("mistake_rules_fetch", "template_pack")

    # ── Step 7 → Steps 8.1-8.3: Template Pack → PARALLEL Fan-Out ──
    # Fan-out: template_pack → compliance, localization, prayer (PARALLEL)
    parallel_agents = ["compliance", "localization", "prayer"]
    for agent_name in parallel_agents:
        if agent_name in sub_agents:
            workflow.add_edge("template_pack", agent_name)
            logger.info(f"  Fan-out: template_pack → {agent_name}")

    # ── Steps 8.1-8.3 → Fan-In: All parallel agents → optional_router ──
    for agent_name in parallel_agents:
        if agent_name in sub_agents:
            workflow.add_edge(agent_name, "optional_router")
            logger.info(f"  Fan-in: {agent_name} → optional_router")

    # ── Steps 9.1-9.2: Optional agents (conditional) ──
    def route_optional(state) -> str:
        resolved = state.get("resolved_route", {})
        agents_required = resolved.get("agents_required", []) if isinstance(resolved, dict) else []
        needs_research = any(a in agents_required for a in ["research_agent", "research"])
        if needs_research and "research" in sub_agents:
            return "research"
        return "citation_validation_gate"

    workflow.add_conditional_edges(
        "optional_router",
        route_optional,
        ["research", "citation_validation_gate"],
    )

    # ── Research → Citation or Citation Validation ──
    if "research" in sub_agents:
        def route_after_research(state) -> str:
            resolved = state.get("resolved_route", {})
            agents_required = resolved.get("agents_required", []) if isinstance(resolved, dict) else []
            needs_citation = any(a in agents_required for a in ["citation_agent", "citation"])
            if needs_citation:
                return "citation"
            return "citation_validation_gate"

        workflow.add_conditional_edges(
            "research",
            route_after_research,
            ["citation", "citation_validation_gate"],
        )

    # ── Citation → Citation Validation ──
    if "citation" in sub_agents:
        workflow.add_edge("citation", "citation_validation_gate")

    # ── Step 10 → Step 11: Citation Validation → Context Merge ──
    workflow.add_edge("citation_validation_gate", "context_merge_gate")

    # ── Step 11 → Step 12: Context Merge → Drafting ──
    workflow.add_edge("context_merge_gate", "drafting")

    # ── Step 12 → Step 12B: Drafting → Fact Traceability Gate ──
    workflow.add_edge("drafting", "fact_traceability_gate")

    # ── Step 12B → Step 13: Fact Traceability → Review ──
    workflow.add_edge("fact_traceability_gate", "review")

    # ── Step 13 → Step 14: Review → Staging Rules ──
    workflow.add_edge("review", "staging_rules")

    # ── Steps 14 → 15-17: Staging → Promotion ──
    workflow.add_edge("staging_rules", "promotion_gate")

    # ── Steps 15-17 → Step 18: Promotion → Export ──
    workflow.add_edge("promotion_gate", "export_gate")

    # ── Step 18: Export → END ──
    workflow.add_edge("export_gate", END)

    # ── Compile ──
    graph = workflow.compile()
    logger.info("18-step legal drafting pipeline graph created successfully")
    return graph


__all__ = ["create_graph"]

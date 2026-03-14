from __future__ import annotations

"""
Drafting graph wiring.

Routing: all node-to-node transitions are handled by Command(goto=...) inside each node.
Only the START -> intake edge is declared here.

Checkpointer: opt-in via `get_drafting_graph(use_checkpointer=True)`.
Without a checkpointer the graph works as a stateless one-shot pipeline
and does NOT require a thread_id in the invocation config.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.types import RetryPolicy

from .nodes import (
    civil_ambiguity_gate_node,
    civil_case_resolver_node,
    civil_consistency_gate_node,
    civil_draft_plan_compiler_node,
    civil_draft_router_node,
    classifier_node,
    court_fee_node,
    domain_ambiguity_gate_node,
    domain_consistency_gate_node,
    domain_decision_compiler_node,
    domain_draft_router_node,
    domain_plan_compiler_node,
    domain_router_node,
    draft_freetext_node,
    draft_template_fill_node,
    enrichment_node,
    evidence_anchoring_node,
    intake_classify_node,
    intake_node,
    lkb_compliance_node,
    postprocess_node,
    rag_domain_node,
    review_node,
    citation_validator_node,
)
from .states import DraftingState

_RETRY_POLICY = RetryPolicy(max_attempts=3)


def get_drafting_graph(use_checkpointer: bool = False):
    """Build and compile the drafting workflow graph.

    Routing (all via Command(goto=...) inside nodes):

    v9.0 pipeline (2 LLM calls, deterministic enrichment):
      START -> intake_classify (1 LLM) -> domain_router -> domain_decision_compiler
        -> domain_ambiguity_gate -> enrichment (LKB-only, 0 LLM, 0 API)
        -> domain_plan_compiler -> domain_draft_router
        -> draft_template_fill|draft_freetext (1 LLM) -> domain_consistency_gate
        -> evidence_anchoring -> lkb_compliance
        -> postprocess -> citation_validator -> END (review skipped by default)

    Disconnected (code preserved, not called):
      - RAG node (ragDomain.py) — Qdrant retrieval, no longer in pipeline path
      - court_fee node (courtFeeSearch.py) — Brave web search, never routed to
      - websearch tools (tools/websearch.py) — preserved for future re-enablement

    Legacy civil-* nodes remain registered for backward compatibility and tests.

    Set DRAFTING_SKIP_REVIEW=false in .env to re-enable review.

    Args:
        use_checkpointer: When True, compiles with MemorySaver for thread-level
            state persistence. Callers must then pass
            config={"configurable": {"thread_id": "..."}} on every invoke.
            Defaults to False (stateless one-shot mode).
    """
    graph = StateGraph(DraftingState)

    # Context gathering
    graph.add_node("intake_classify", intake_classify_node, retry_policy=_RETRY_POLICY)
    graph.add_node("domain_router", domain_router_node, retry_policy=_RETRY_POLICY)
    graph.add_node("domain_decision_compiler", domain_decision_compiler_node, retry_policy=_RETRY_POLICY)
    graph.add_node("domain_ambiguity_gate", domain_ambiguity_gate_node, retry_policy=_RETRY_POLICY)
    graph.add_node("rag", rag_domain_node, retry_policy=_RETRY_POLICY)
    graph.add_node("enrichment", enrichment_node, retry_policy=_RETRY_POLICY)

    # Backward compatibility nodes
    graph.add_node("intake", intake_node, retry_policy=_RETRY_POLICY)
    graph.add_node("classify", classifier_node, retry_policy=_RETRY_POLICY)
    graph.add_node("court_fee", court_fee_node, retry_policy=_RETRY_POLICY)
    graph.add_node("civil_case_resolver", civil_case_resolver_node, retry_policy=_RETRY_POLICY)
    graph.add_node("civil_ambiguity_gate", civil_ambiguity_gate_node, retry_policy=_RETRY_POLICY)

    # Drafting
    graph.add_node("domain_plan_compiler", domain_plan_compiler_node, retry_policy=_RETRY_POLICY)
    graph.add_node("domain_draft_router", domain_draft_router_node, retry_policy=_RETRY_POLICY)
    graph.add_node("draft_freetext", draft_freetext_node, retry_policy=_RETRY_POLICY)
    graph.add_node("draft_template_fill", draft_template_fill_node, retry_policy=_RETRY_POLICY)

    # Backward compatibility drafting nodes
    graph.add_node("civil_draft_plan_compiler", civil_draft_plan_compiler_node, retry_policy=_RETRY_POLICY)
    graph.add_node("civil_draft_router", civil_draft_router_node, retry_policy=_RETRY_POLICY)

    # Validation
    graph.add_node("domain_consistency_gate", domain_consistency_gate_node, retry_policy=_RETRY_POLICY)
    graph.add_node("evidence_anchoring", evidence_anchoring_node, retry_policy=_RETRY_POLICY)
    graph.add_node("lkb_compliance", lkb_compliance_node, retry_policy=_RETRY_POLICY)
    graph.add_node("postprocess", postprocess_node, retry_policy=_RETRY_POLICY)
    graph.add_node("citation_validator", citation_validator_node, retry_policy=_RETRY_POLICY)

    # Backward compatibility validation node
    graph.add_node("civil_consistency_gate", civil_consistency_gate_node, retry_policy=_RETRY_POLICY)

    # Review
    graph.add_node("review", review_node, retry_policy=_RETRY_POLICY)

    # Entry: merged intake+classify -> domain routing
    graph.add_edge(START, "intake_classify")

    checkpointer = MemorySaver() if use_checkpointer else None
    return graph.compile(checkpointer=checkpointer)


drafting_graph = get_drafting_graph()
legal_drafting_graph = drafting_graph

__all__ = ["get_drafting_graph", "drafting_graph", "legal_drafting_graph"]

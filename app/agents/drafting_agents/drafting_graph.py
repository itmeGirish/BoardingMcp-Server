from __future__ import annotations

"""
Drafting graph wiring.

Routing: all node-to-node transitions are handled by Command(goto=...) inside each node.
Only the START → intake edge is declared here.

Checkpointer: opt-in via `get_drafting_graph(use_checkpointer=True)`.
Without a checkpointer the graph works as a stateless one-shot pipeline
and does NOT require a thread_id in the invocation config.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.types import RetryPolicy

from .nodes import (
    classifier_node, court_fee_node, enrichment_node,
    intake_node, intake_classify_node, rag_domain_node, review_node,
    postprocess_node,
    draft_freetext_node,
    draft_template_fill_node,
    citation_validator_node, evidence_anchoring_node,
    lkb_compliance_node,
)
from .states import DraftingState

_RETRY_POLICY = RetryPolicy(max_attempts=3)


def get_drafting_graph(use_checkpointer: bool = False):
    """Build and compile the drafting workflow graph.

    Routing (all via Command(goto=...) inside nodes):

    Speed-optimized pipeline (40-50s target):
      START → intake_classify (merged) → rag → enrichment (+ court_fee parallel)
        → draft_freetext → evidence_anchoring → lkb_compliance
        → postprocess → citation_validator → END (review skipped by default)

    Set DRAFTING_SKIP_REVIEW=false in .env to re-enable review.

    Args:
        use_checkpointer: When True, compiles with MemorySaver for thread-level
            state persistence. Callers must then pass
            config={"configurable": {"thread_id": "..."}} on every invoke.
            Defaults to False (stateless one-shot mode).
    """
    graph = StateGraph(DraftingState)

    # Context gathering — merged intake+classify saves one LLM call (~10s)
    graph.add_node("intake_classify", intake_classify_node, retry_policy=_RETRY_POLICY)
    graph.add_node("rag", rag_domain_node, retry_policy=_RETRY_POLICY)
    graph.add_node("enrichment", enrichment_node, retry_policy=_RETRY_POLICY)
    # Kept for backward compat — enrichment now runs court_fee in parallel internally
    graph.add_node("intake", intake_node, retry_policy=_RETRY_POLICY)
    graph.add_node("classify", classifier_node, retry_policy=_RETRY_POLICY)
    graph.add_node("court_fee", court_fee_node, retry_policy=_RETRY_POLICY)

    # Drafting
    graph.add_node("draft_freetext", draft_freetext_node, retry_policy=_RETRY_POLICY)
    graph.add_node("draft_template_fill", draft_template_fill_node, retry_policy=_RETRY_POLICY)

    # Validation
    graph.add_node("evidence_anchoring", evidence_anchoring_node, retry_policy=_RETRY_POLICY)
    graph.add_node("lkb_compliance", lkb_compliance_node, retry_policy=_RETRY_POLICY)
    graph.add_node("postprocess", postprocess_node, retry_policy=_RETRY_POLICY)
    graph.add_node("citation_validator", citation_validator_node, retry_policy=_RETRY_POLICY)

    # Review
    graph.add_node("review", review_node, retry_policy=_RETRY_POLICY)

    # Entry: merged intake+classify → rag
    graph.add_edge(START, "intake_classify")

    checkpointer = MemorySaver() if use_checkpointer else None
    return graph.compile(checkpointer=checkpointer)


# Stateless singleton for API/route imports (no thread_id required).
drafting_graph = get_drafting_graph()

# Backward compatibility alias.
legal_drafting_graph = drafting_graph

__all__ = ["get_drafting_graph", "drafting_graph", "legal_drafting_graph"]

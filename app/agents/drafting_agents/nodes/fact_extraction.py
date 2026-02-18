"""
Fact Extraction node for legal drafting workflow.

Model: Kimi K2.5 (via DRAFTING_MODELS["fact_extraction"])
"""
from ..base_agent import DraftingBaseAgentNode


class FactExtractionAgentNode(DraftingBaseAgentNode):
    agent_name = "fact_extraction"
    max_iterations = 10


_node = FactExtractionAgentNode()
call_model_node = _node.call_model_node

__all__ = ["call_model_node"]

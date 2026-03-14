from __future__ import annotations

from .base import DomainPlugin
from ..nodes.civil_decision import (
    civil_ambiguity_gate_node,
    civil_case_resolver_node,
    civil_consistency_gate_node,
    civil_draft_plan_compiler_node,
    civil_draft_router_node,
)


CIVIL_PLUGIN = DomainPlugin(
    key="civil",
    law_domains=("Civil",),
    decision_node=civil_case_resolver_node,
    ambiguity_gate_node=civil_ambiguity_gate_node,
    plan_compiler_node=civil_draft_plan_compiler_node,
    draft_router_node=civil_draft_router_node,
    consistency_gate_node=civil_consistency_gate_node,
)

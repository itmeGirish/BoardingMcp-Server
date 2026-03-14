from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from langgraph.types import Command

from ..states import DraftingState


NodeFn = Callable[[DraftingState], Command]


@dataclass(frozen=True)
class DomainPlugin:
    key: str
    law_domains: tuple[str, ...]
    decision_node: NodeFn
    ambiguity_gate_node: NodeFn
    plan_compiler_node: NodeFn
    draft_router_node: NodeFn
    consistency_gate_node: NodeFn

    def supports(self, law_domain: str) -> bool:
        return (law_domain or "") in self.law_domains


def first_matching_plugin(plugins: Iterable[DomainPlugin], law_domain: str) -> Optional[DomainPlugin]:
    for plugin in plugins:
        if plugin.supports(law_domain):
            return plugin
    return None

from __future__ import annotations

from typing import Dict, Optional

from .base import DomainPlugin, first_matching_plugin
from .civil import CIVIL_PLUGIN


_PLUGINS: Dict[str, DomainPlugin] = {
    CIVIL_PLUGIN.key: CIVIL_PLUGIN,
}


def get_domain_plugin(key: Optional[str]) -> Optional[DomainPlugin]:
    if not key:
        return None
    return _PLUGINS.get(key)


def resolve_domain_plugin(law_domain: str) -> Optional[DomainPlugin]:
    return first_matching_plugin(_PLUGINS.values(), law_domain)


def list_domain_plugins() -> Dict[str, DomainPlugin]:
    return dict(_PLUGINS)


__all__ = [
    "DomainPlugin",
    "get_domain_plugin",
    "resolve_domain_plugin",
    "list_domain_plugins",
]

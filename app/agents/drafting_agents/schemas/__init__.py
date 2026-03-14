"""Document type schemas — v11.0 scalable pipeline.

Each schema defines the STRUCTURE of a legal document type:
- Section order + per-section instructions
- Filing metadata (filed_by, annexure_prefix, verification_type)
- Filing rules (deadline, court fee, etc.)

Schemas are INDEPENDENT of cause type. Same schema works for ALL 92 cause types.
One schema per document type. 12 schemas cover all civil documents.

Usage:
    from app.agents.drafting_agents.schemas import get_schema, list_schemas

    schema = get_schema("plaint")
    all_codes = list_schemas()
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ....config import logger

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_SCHEMA_REGISTRY: Dict[str, dict] = {}
_SCHEMA_ALIASES: Dict[str, str] = {
    "money_recovery_plaint": "plaint",
    "specific_performance_plaint": "plaint",
    "partition_plaint": "plaint",
    "permanent_injunction_plaint": "plaint",
    "mandatory_injunction_plaint": "plaint",
    "eviction_plaint": "plaint",
    "damages_plaint": "plaint",
}


def register_schemas(schemas: Dict[str, dict]) -> None:
    """Register document type schemas."""
    _SCHEMA_REGISTRY.update(schemas)
    logger.info("[SCHEMAS] registered %d document schemas", len(schemas))


def get_schema(document_type: str) -> Optional[dict]:
    """Look up a document schema by code."""
    normalized = (document_type or "").strip().lower().replace(" ", "_").replace("-", "_")
    schema = _SCHEMA_REGISTRY.get(normalized)
    if schema is None:
        alias = _SCHEMA_ALIASES.get(normalized)
        if alias:
            schema = _SCHEMA_REGISTRY.get(alias)
    if schema is None and normalized.endswith("_plaint"):
        schema = _SCHEMA_REGISTRY.get("plaint")
    if schema:
        logger.info("[SCHEMAS] hit: document_type=%s normalized=%s", document_type, normalized)
    else:
        logger.warning("[SCHEMAS] miss: document_type=%s normalized=%s", document_type, normalized)
    return schema


def list_schemas() -> List[str]:
    """List all registered document type codes."""
    return list(_SCHEMA_REGISTRY.keys())


def _apply_runtime_fixes() -> None:
    """Normalize schema metadata that needs runtime-safe corrections."""
    written_statement = _SCHEMA_REGISTRY.get("written_statement")
    if written_statement:
        filing_rules = written_statement.setdefault("filing_rules", {})
        filing_rules["filing_deadline"] = (
            "Ordinarily within 30 days from service of summons; in regular civil suits "
            "the court may extend time beyond 30 days and ordinarily up to 90 days for "
            "recorded reasons, while commercial disputes carry a strict outer limit of "
            "120 days from service under the Commercial Courts Act"
        )


# ---------------------------------------------------------------------------
# Auto-register on import
# ---------------------------------------------------------------------------
from .trial_court import SCHEMAS as _TRIAL_COURT  # noqa: E402
from .applications import SCHEMAS as _APPLICATIONS  # noqa: E402
from .appellate import SCHEMAS as _APPELLATE  # noqa: E402
from .execution import SCHEMAS as _EXECUTION  # noqa: E402

register_schemas(_TRIAL_COURT)
register_schemas(_APPLICATIONS)
register_schemas(_APPELLATE)
register_schemas(_EXECUTION)
_apply_runtime_fixes()

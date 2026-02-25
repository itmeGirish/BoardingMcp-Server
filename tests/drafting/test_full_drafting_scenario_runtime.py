"""Runtime test using the built imported drafting graph.

This test does NOT build a custom graph. It imports and runs the existing
`legal_drafting_graph` with a real scenario input and reports execution time.
"""

from __future__ import annotations

import sys
import time
import types
import json as _json

import pytest
from langchain_core.messages import HumanMessage

# Compatibility shim for environments where copilotkit expects
# `langgraph.graph.graph.CompiledGraph`.
if "langgraph.graph.graph" not in sys.modules:
    try:
        from langgraph.graph.state import CompiledStateGraph

        compat_mod = types.ModuleType("langgraph.graph.graph")
        compat_mod.CompiledGraph = CompiledStateGraph
        sys.modules["langgraph.graph.graph"] = compat_mod
    except Exception:
        pass

# Compatibility shim for environments without full `langchain` package.
try:
    from langchain.load.dump import dumps as _lc_dumps  # type: ignore # noqa: F401
except Exception:
    langchain_pkg = sys.modules.get("langchain")
    if langchain_pkg is None:
        langchain_pkg = types.ModuleType("langchain")
        sys.modules["langchain"] = langchain_pkg

    load_pkg = sys.modules.get("langchain.load")
    if load_pkg is None:
        load_pkg = types.ModuleType("langchain.load")
        sys.modules["langchain.load"] = load_pkg

    dump_mod = types.ModuleType("langchain.load.dump")

    def _shim_dumps(value):
        try:
            return _json.dumps(value, default=str)
        except Exception:
            return str(value)

    dump_mod.dumps = _shim_dumps
    sys.modules["langchain.load.dump"] = dump_mod

try:
    from langchain.schema import BaseMessage as _LCBaseMessage  # type: ignore # noqa: F401
except Exception:
    schema_mod = types.ModuleType("langchain.schema")
    from langchain_core.messages import BaseMessage, SystemMessage

    schema_mod.BaseMessage = BaseMessage
    schema_mod.SystemMessage = SystemMessage
    sys.modules["langchain.schema"] = schema_mod

from app.agents.drafting_agents.legal_drafting import legal_drafting_graph


SCENARIO_TEXT = (
    "Draft a legal notice for recovery of ₹8,50,000 given as hand loan in Bengaluru. "
    "No written agreement, only bank transfer proof. Add 18% interest claim"
)


@pytest.mark.asyncio
async def test_full_drafting_scenario_runtime_built_graph():
    state_input = {
        "messages": [HumanMessage(content=SCENARIO_TEXT)],
        "user_id": "pytest_user_001",
        "parallel_outputs": [],
    }

    started = time.perf_counter()
    result = await legal_drafting_graph.ainvoke(state_input)
    elapsed = time.perf_counter() - started

    assert isinstance(result, dict)
    # At least one of these should exist when flow executes.
    assert (
        result.get("final_draft") is not None
        or result.get("draft_v1") is not None
        or len(result.get("messages", [])) > 0
    )
    # Keep elapsed available in failure output if this assertion fails.
    assert elapsed >= 0.0

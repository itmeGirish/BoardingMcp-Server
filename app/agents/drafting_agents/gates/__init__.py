"""v7.0 Verification Gates — deterministic, zero LLM calls.

All 6 gates run sequentially on the draft text. Each may modify the draft.
"""
from .theory_anchoring import legal_theory_anchoring_gate, DOCTRINE_PATTERNS
from .procedural_prerequisites import procedural_prerequisites_gate, PREREQUISITES

__all__ = [
    "legal_theory_anchoring_gate",
    "DOCTRINE_PATTERNS",
    "procedural_prerequisites_gate",
    "PREREQUISITES",
]

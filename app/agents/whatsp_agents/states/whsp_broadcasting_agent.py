"""
State definitions for broadcasting workflow

This module defines all TypedDict classes for type-safe state management
across the broadcasting workflow steps.
"""

from typing import TypedDict, Optional, List, Dict, Any
from copilotkit import CopilotKitState


class BroadcastingAgentState(CopilotKitState):
    """
    Main agent state for LangGraph broadcasting workflow.

    Inherits from CopilotKitState which provides:
    - messages: List of conversation messages
    - Additional CopilotKit-specific fields
    """
    pass


__all__ = [
    "BroadcastingAgentState",
]

"""
State definitions for Analytics & Optimization Agent.

Handles the post-delivery analytics phase:
- Broadcast delivery metrics from DB
- WABA-level analytics via MCP (get_waba_analytics)
- Messaging health & quality monitoring via MCP (get_messaging_health_status)
- AI-powered optimization recommendations

NOTE: Cost tracking is excluded for now (future enhancement).
"""

from typing import Optional, Literal
from copilotkit import CopilotKitState


AnalyticsStatus = Literal[
    "PENDING",                  # Awaiting analytics request
    "FETCHING_METRICS",         # Pulling delivery metrics from DB
    "ANALYZING_HEALTH",         # Checking messaging health & quality
    "GENERATING_RECOMMENDATIONS",  # AI optimization suggestions
    "COMPLETED",                # Analytics report ready
    "FAILED",                   # Analytics retrieval failed
]


class AnalyticsAgentState(CopilotKitState):
    """
    State for the Analytics & Optimization Agent sub-graph.

    Inherits from CopilotKitState which provides:
    - messages: Chat message history
    """
    broadcast_job_id: Optional[str]
    user_id: Optional[str]
    project_id: Optional[str]
    analytics_status: Optional[AnalyticsStatus]
    error_message: Optional[str]


__all__ = [
    "AnalyticsStatus",
    "AnalyticsAgentState",
]

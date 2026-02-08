"""
State definitions for Compliance Agent.

Handles the COMPLIANCE_CHECK phase of the broadcast workflow:
- Opt-in verification and consent tracking
- Suppression list filtering (global, campaign, temporary, bounce)
- Time window restrictions (TRAI India 9AM-9PM, GDPR EU, etc.)
- WhatsApp Business Policy enforcement
- Messaging tier and account health checks
"""

from typing import TypedDict, Optional, List, Dict, Any, Literal
from copilotkit import CopilotKitState


ComplianceStatus = Literal[
    "PENDING",              # Awaiting compliance checks
    "CHECKING_OPTIN",       # Verifying opt-in consent
    "FILTERING_SUPPRESSION", # Filtering suppression lists
    "CHECKING_TIME_WINDOW", # Validating time window restrictions
    "CHECKING_HEALTH",      # Checking account health via MCP
    "PASSED",               # All compliance checks passed
    "FAILED",               # Compliance checks failed
]


class ComplianceAgentState(CopilotKitState):
    """
    State for the Compliance Agent sub-graph.

    Inherits from CopilotKitState which provides:
    - messages: Chat message history
    """
    broadcast_job_id: Optional[str]
    user_id: Optional[str]
    project_id: Optional[str]
    compliance_status: Optional[ComplianceStatus]
    error_message: Optional[str]


__all__ = [
    "ComplianceStatus",
    "ComplianceAgentState",
]

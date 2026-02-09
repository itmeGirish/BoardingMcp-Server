"""
State definitions for Content Creation Agent.

Handles the CONTENT_CREATION and PENDING_APPROVAL phases:
- AI-powered template generation (text, image, video, document)
- Template submission to WhatsApp for approval
- Approval status polling and rejection analysis
- Dynamic personalization with variables
- Template deletion by ID or name
"""

from typing import Optional, Literal
from copilotkit import CopilotKitState


ContentCreationStatus = Literal[
    "PENDING",              # Awaiting content creation
    "LISTING_TEMPLATES",    # Fetching available templates
    "GENERATING",           # AI generating template content
    "SUBMITTING",           # Submitting template to WhatsApp
    "AWAITING_APPROVAL",    # Template pending WhatsApp approval
    "APPROVED",             # Template approved, ready to use
    "REJECTED",             # Template rejected, needs fix
    "COMPLETED",            # Template selected and ready
    "FAILED",               # Content creation failed
]


class ContentCreationAgentState(CopilotKitState):
    """
    State for the Content Creation Agent sub-graph.

    Inherits from CopilotKitState which provides:
    - messages: Chat message history
    """
    broadcast_job_id: Optional[str]
    user_id: Optional[str]
    project_id: Optional[str]
    content_creation_status: Optional[ContentCreationStatus]
    error_message: Optional[str]


__all__ = [
    "ContentCreationStatus",
    "ContentCreationAgentState",
]

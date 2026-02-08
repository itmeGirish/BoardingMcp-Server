"""
State definitions for broadcasting supervisor workflow

This module defines all TypedDict classes for type-safe state management
across the broadcasting workflow phases.
"""

from typing import TypedDict, Optional, List, Dict, Any, Literal
from copilotkit import CopilotKitState


# ============================================
# BROADCAST PHASE TYPE
# ============================================

BroadcastPhase = Literal[
    "INITIALIZED",
    "DATA_PROCESSING",
    "COMPLIANCE_CHECK",
    "SEGMENTATION",
    "CONTENT_CREATION",
    "PENDING_APPROVAL",
    "READY_TO_SEND",
    "SENDING",
    "PAUSED",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
]


# ============================================
# SUPPORTING STATE TYPES
# ============================================

class ContactData(TypedDict):
    """State for contact data upload and validation"""
    phone_numbers: List[str]
    total_count: int
    valid_count: int
    invalid_count: int
    validation_errors: Optional[List[str]]


class SegmentData(TypedDict):
    """State for audience segmentation"""
    segment_name: str
    segment_criteria: Optional[str]
    contact_count: int


class TemplateData(TypedDict):
    """State for template selection/creation"""
    template_id: Optional[str]
    template_name: str
    template_status: Optional[str]  # APPROVED, PENDING, REJECTED
    template_category: str          # MARKETING, UTILITY, AUTHENTICATION
    template_language: str


class BroadcastProgress(TypedDict):
    """State for tracking send progress"""
    total_messages: int
    sent_count: int
    delivered_count: int
    failed_count: int
    pending_count: int


# ============================================
# INTER-AGENT MESSAGE SCHEMA
# ============================================

AgentPriority = Literal["normal", "high", "urgent"]

class AgentMessage(TypedDict):
    """
    Schema for inter-agent communication within the broadcast workflow.

    Used by the supervisor to coordinate messages between processing stages
    (e.g., data_processing -> compliance, compliance -> segmentation).

    Fields:
        message_id: Unique identifier for this message (UUID)
        source_agent: The agent/phase that produced this message
        target_agent: The agent/phase that should consume this message
        broadcast_id: The broadcast job ID this message belongs to
        payload: Arbitrary data passed between agents
        timestamp: ISO 8601 formatted timestamp
        priority: Message priority level (normal, high, urgent)
    """
    message_id: str
    source_agent: str
    target_agent: str
    broadcast_id: str
    payload: Dict[str, Any]
    timestamp: str
    priority: AgentPriority


# ============================================
# MAIN AGENT STATE
# ============================================

class BroadcastingAgentState(CopilotKitState):
    """
    Main agent state for Broadcasting Supervisor LangGraph workflow.

    Inherits from CopilotKitState which provides:
    - messages: List of conversation messages
    - Additional CopilotKit-specific fields

    Broadcasting-specific fields track the state machine:
    - broadcast_phase: Current phase in the state machine
    - broadcast_job_id: ID of the persisted BroadcastJob record
    - user_id: The user running this broadcast
    - error_message: Last error if in FAILED state
    """
    broadcast_phase: Optional[BroadcastPhase]
    broadcast_job_id: Optional[str]
    user_id: Optional[str]
    error_message: Optional[str]


__all__ = [
    "BroadcastPhase",
    "AgentPriority",
    "AgentMessage",
    "ContactData",
    "SegmentData",
    "TemplateData",
    "BroadcastProgress",
    "BroadcastingAgentState",
]

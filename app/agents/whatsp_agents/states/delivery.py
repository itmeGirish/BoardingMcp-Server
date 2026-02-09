"""
State definitions for Delivery Agent.

Handles the SENDING phase of the broadcast workflow:
- Rate limiting by WhatsApp tier
- Multi-priority queue management (5 levels)
- Retry logic with exponential backoff
- Delivery status tracking (sent, delivered, read, failed)
- Error code handling (131026, 131047, 130429, etc.)
- send_lite_message first (business policy), fallback to send_message
"""

from typing import Optional, Literal
from copilotkit import CopilotKitState


DeliveryStatus = Literal[
    "PENDING",              # Awaiting dispatch
    "PREPARING_QUEUE",      # Building priority queues
    "SENDING_LITE",         # Sending via marketing lite (priority)
    "SENDING_TEMPLATE",     # Sending via template message
    "RETRYING",             # Retrying failed messages
    "PAUSED",               # Dispatch paused by user
    "COMPLETED",            # All messages processed
    "FAILED",               # Delivery failed
]


class DeliveryAgentState(CopilotKitState):
    """
    State for the Delivery Agent sub-graph.

    Inherits from CopilotKitState which provides:
    - messages: Chat message history
    """
    broadcast_job_id: Optional[str]
    user_id: Optional[str]
    project_id: Optional[str]
    delivery_status: Optional[DeliveryStatus]
    error_message: Optional[str]


__all__ = [
    "DeliveryStatus",
    "DeliveryAgentState",
]

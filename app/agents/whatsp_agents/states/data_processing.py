"""
State definitions for Data Processing Agent.
Handles the DATA_PROCESSING phase of the broadcast workflow:
- Beginner flow (first_broadcasting check + FB verification)
- File parsing (Excel/CSV)
- Phone validation & E.164 normalization
- Multi-stage duplicate detection
- Data quality scoring
"""

from typing import TypedDict, Optional, List, Dict, Any, Literal
from copilotkit import CopilotKitState


ProcessingStatus = Literal[
    "PENDING",          # Awaiting contact data
    "BEGINNER_CHECK",   # Checking first_broadcasting / FB verification
    "PARSING",          # Parsing uploaded file
    "VALIDATING",       # Validating phone numbers
    "DEDUPLICATING",    # Running dedup pipeline
    "SCORING",          # Quality scoring
    "COMPLETED",        # Processing done
    "FAILED",           # Unrecoverable error
]


class DataProcessingAgentState(CopilotKitState):
    """
    State for the Data Processing Agent sub-graph.

    Inherits from CopilotKitState which provides:
    - messages: Chat message history
    - Additional CopilotKit fields

    Custom fields track the processing pipeline status.
    """
    broadcast_job_id: Optional[str]
    user_id: Optional[str]
    project_id: Optional[str]
    processing_status: Optional[ProcessingStatus]
    is_beginner: Optional[bool]
    error_message: Optional[str]


__all__ = [
    "ProcessingStatus",
    "DataProcessingAgentState",
]

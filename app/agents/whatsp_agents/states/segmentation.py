"""
State definitions for Segmentation Agent.

Handles the SEGMENTATION phase of the broadcast workflow:
- Behavioral, demographic, lifecycle analysis
- 24-hour window detection (free service window)
- Timezone clustering for optimal delivery timing
- Frequency capping to prevent message fatigue
"""

from typing import Optional, Literal
from copilotkit import CopilotKitState


SegmentationStatus = Literal[
    "PENDING",              # Awaiting segmentation
    "ANALYZING",            # Analyzing contact data
    "DETECTING_WINDOWS",    # Detecting 24-hr service windows
    "CLUSTERING_TIMEZONES", # Grouping by timezone
    "CHECKING_FREQUENCY",   # Checking frequency caps
    "COMPLETED",            # Segmentation complete
    "FAILED",               # Segmentation failed
]


class SegmentationAgentState(CopilotKitState):
    """
    State for the Segmentation Agent sub-graph.

    Inherits from CopilotKitState which provides:
    - messages: Chat message history
    """
    broadcast_job_id: Optional[str]
    user_id: Optional[str]
    project_id: Optional[str]
    segmentation_status: Optional[SegmentationStatus]
    error_message: Optional[str]


__all__ = [
    "SegmentationStatus",
    "SegmentationAgentState",
]

# app/database/postgresql/models/broadcast_job.py
"""BroadcastJob model for tracking broadcast campaign lifecycle."""
from sqlmodel import SQLModel, Field
from sqlalchemy import Text
from typing import Optional
from datetime import datetime


class BroadcastJob(SQLModel, table=True):
    """
    Persists broadcast campaign state through the 12-phase state machine.

    Tracks the entire lifecycle of a broadcast:
    - Phase transitions (INITIALIZED -> DATA_PROCESSING -> ... -> COMPLETED)
    - Contact data (validated phone numbers stored as JSON)
    - Segmentation info
    - Template selection
    - Send progress counters
    - Error details

    Phase values: INITIALIZED, DATA_PROCESSING, COMPLIANCE_CHECK, SEGMENTATION,
    CONTENT_CREATION, PENDING_APPROVAL, READY_TO_SEND, SENDING, PAUSED,
    COMPLETED, FAILED, CANCELLED
    """
    __tablename__ = "broadcast_jobs"

    id: str = Field(primary_key=True)
    user_id: str = Field(index=True)
    project_id: str = Field(index=True)

    # State machine
    phase: str = Field(default="INITIALIZED")
    previous_phase: Optional[str] = Field(default=None)

    # Contact data
    contacts_data: Optional[str] = Field(default=None, sa_type=Text)  # JSON array of phone numbers
    total_contacts: int = Field(default=0)
    valid_contacts: int = Field(default=0)
    invalid_contacts: int = Field(default=0)

    # Compliance
    compliance_status: Optional[str] = Field(default=None)  # "passed", "failed"
    compliance_details: Optional[str] = Field(default=None, sa_type=Text)  # JSON

    # Segmentation
    segments_data: Optional[str] = Field(default=None, sa_type=Text)  # JSON array of segments

    # Template
    template_id: Optional[str] = Field(default=None)
    template_name: Optional[str] = Field(default=None)
    template_language: Optional[str] = Field(default=None)
    template_category: Optional[str] = Field(default=None)
    template_status: Optional[str] = Field(default=None)  # APPROVED, PENDING, REJECTED

    # Send progress
    sent_count: int = Field(default=0)
    delivered_count: int = Field(default=0)
    failed_count: int = Field(default=0)
    pending_count: int = Field(default=0)

    # Error tracking
    error_message: Optional[str] = Field(default=None, sa_type=Text)
    error_details: Optional[str] = Field(default=None, sa_type=Text)  # JSON

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_sending_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    is_active: bool = Field(default=True)

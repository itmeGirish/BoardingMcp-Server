"""DraftingSession model for tracking legal drafting workflow lifecycle."""
from sqlmodel import SQLModel, Field
from sqlalchemy import Text
from typing import Optional
from datetime import datetime


class DraftingSession(SQLModel, table=True):
    """
    Persists legal drafting session state through the workflow phases.

    Phase values: INITIALIZED, INTAKE, FACT_EXTRACTION, RESEARCH,
    DRAFTING, REVIEW, REVISION, COMPLETED, FAILED
    """
    __tablename__ = "drafting_sessions"

    id: str = Field(primary_key=True)
    user_id: str = Field(index=True)

    # State machine
    phase: str = Field(default="INITIALIZED")
    previous_phase: Optional[str] = Field(default=None)

    # Document metadata
    document_type: Optional[str] = Field(default=None)  # motion, brief, contract, demand_letter, etc.
    jurisdiction: Optional[str] = Field(default=None)
    court_type: Optional[str] = Field(default=None)
    case_category: Optional[str] = Field(default=None)
    case_title: Optional[str] = Field(default=None)

    # Draft output
    draft_content: Optional[str] = Field(default=None, sa_type=Text)

    # Error tracking
    error_message: Optional[str] = Field(default=None, sa_type=Text)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True)

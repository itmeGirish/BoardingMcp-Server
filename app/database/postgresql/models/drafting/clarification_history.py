"""ClarificationHistory model for tracking intake Q&A exchanges."""
from sqlmodel import SQLModel, Field
from sqlalchemy import JSON
from typing import Optional, Dict, List, Any
from datetime import datetime


class ClarificationHistory(SQLModel, table=True):
    """
    Records clarification questions asked during intake and user responses.

    Each row represents one round of Q&A within a session, ordered by step_number.
    """
    __tablename__ = "clarification_history"

    id: str = Field(primary_key=True)
    session_id: str = Field(index=True)

    # Step ordering
    step_number: int = Field()

    # Q&A content (stored as JSON arrays/objects)
    questions: Dict[str, Any] = Field(sa_type=JSON)
    user_responses: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)

    # Timestamps
    asked_at: datetime = Field(default_factory=datetime.now)
    responded_at: Optional[datetime] = Field(default=None)

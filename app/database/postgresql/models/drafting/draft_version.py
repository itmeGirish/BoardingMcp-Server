"""DraftVersion model for tracking versioned draft outputs per session."""
from sqlmodel import SQLModel, Field
from sqlalchemy import Text, UniqueConstraint
from typing import Optional
from datetime import datetime


class DraftVersion(SQLModel, table=True):
    """
    Stores each version of a generated draft within a session.

    A session may produce multiple draft versions through revision cycles.
    The (session_id, version_number) pair is unique.
    """
    __tablename__ = "draft_versions"
    __table_args__ = (
        UniqueConstraint("session_id", "version_number", name="uq_session_version"),
    )

    id: str = Field(primary_key=True)
    session_id: str = Field(index=True)

    # Versioning
    version_number: int = Field()

    # Draft content
    draft_content: str = Field(sa_type=Text)

    # Quality metrics
    quality_score: Optional[float] = Field(default=None)
    court_readiness: Optional[str] = Field(default=None, max_length=50)
    generated_by: Optional[str] = Field(default=None, max_length=100)
    word_count: Optional[int] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)

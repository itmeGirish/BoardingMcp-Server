"""VerifiedCitation model for storing validated legal citations."""
from sqlmodel import SQLModel, Field
from sqlalchemy import Text, JSON
from typing import Optional, Dict, Any
from datetime import datetime


class VerifiedCitation(SQLModel, table=True):
    """
    Stores verified legal citations with source attribution and hash dedup.

    Citations are validated against legal databases before being used in drafts.
    The citation_hash column ensures no duplicate citations are stored.
    """
    __tablename__ = "verified_citations"

    id: str = Field(primary_key=True)

    # Citation content
    citation_text: str = Field(sa_type=Text)
    case_name: str = Field(max_length=500)
    year: Optional[int] = Field(default=None)
    court: Optional[str] = Field(default=None, max_length=200)
    holding: Optional[str] = Field(default=None, sa_type=Text)

    # Deduplication
    citation_hash: str = Field(max_length=64, unique=True)

    # Source tracking
    source_db: Optional[str] = Field(default=None, max_length=100)
    source_url: Optional[str] = Field(default=None, sa_type=Text)

    # Timestamps
    verified_at: datetime = Field(default_factory=datetime.now)

    # Flexible metadata (named citation_metadata to avoid SQLAlchemy reserved 'metadata')
    citation_metadata: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)

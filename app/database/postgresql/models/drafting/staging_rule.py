"""StagingRule model for new patterns awaiting promotion (anti-pollution)."""
from sqlmodel import SQLModel, Field
from sqlalchemy import Text
from typing import Optional
from datetime import datetime


class StagingRule(SQLModel, table=True):
    """
    New legal patterns awaiting promotion to main_rules.

    Patterns are promoted when occurrence_count >= 3.
    Case-specific content (names, addresses, case numbers) must be
    filtered out before staging.
    """
    __tablename__ = "staging_rules"

    id: str = Field(primary_key=True)

    rule_type: str = Field()          # template_pattern, citation_pattern, section_structure
    jurisdiction: Optional[str] = Field(default=None)
    court_type: Optional[str] = Field(default=None)
    case_category: Optional[str] = Field(default=None)
    document_type: str = Field()      # motion, brief, contract, demand_letter, etc.
    rule_content: str = Field(sa_type=Text)  # JSON pattern

    occurrence_count: int = Field(default=1)
    first_seen_at: datetime = Field(default_factory=datetime.now)
    last_seen_at: datetime = Field(default_factory=datetime.now)
    is_promoted: bool = Field(default=False)

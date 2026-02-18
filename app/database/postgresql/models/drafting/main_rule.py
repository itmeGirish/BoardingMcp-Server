"""MainRule model for promoted legal patterns (self-improving system)."""
from sqlmodel import SQLModel, Field
from sqlalchemy import Text
from typing import Optional
from datetime import datetime


class MainRule(SQLModel, table=True):
    """
    Promoted legal patterns that have been validated through the staging pipeline.

    Rules are promoted from staging_rules when occurrence_count >= 3.
    Never write directly to this table — use staging -> promotion workflow.
    """
    __tablename__ = "main_rules"

    id: str = Field(primary_key=True)

    rule_type: str = Field()          # template_pattern, citation_pattern, section_structure
    jurisdiction: Optional[str] = Field(default=None)
    court_type: Optional[str] = Field(default=None)
    case_category: Optional[str] = Field(default=None)
    document_type: str = Field()      # motion, brief, contract, demand_letter, etc.
    rule_content: str = Field(sa_type=Text)  # JSON pattern

    occurrence_count: int = Field(default=0)
    promoted_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True)

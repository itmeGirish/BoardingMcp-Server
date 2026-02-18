"""DraftingValidation model for gate pass/fail audit trail."""
from sqlmodel import SQLModel, Field
from sqlalchemy import Text
from typing import Optional
from datetime import datetime


class DraftingValidation(SQLModel, table=True):
    """
    Records the result of each validation gate (pass/fail) with details.

    Gates are non-LLM rule-based checks.
    """
    __tablename__ = "drafting_validations"

    id: str = Field(primary_key=True)
    session_id: str = Field(index=True)

    gate_name: str = Field()  # fact_completeness, jurisdiction, citation_confidence, draft_quality
    passed: bool = Field()
    details: Optional[str] = Field(default=None, sa_type=Text)  # JSON with specific failures

    created_at: datetime = Field(default_factory=datetime.now)

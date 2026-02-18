"""DraftingFact model for storing extracted facts with source attribution."""
from sqlmodel import SQLModel, Field
from sqlalchemy import Text
from typing import Optional
from datetime import datetime


class DraftingFact(SQLModel, table=True):
    """
    Stores extracted facts from user chat with confidence scores.

    Facts must have confidence >= 0.75 or a source_doc_id to be used in drafting.
    """
    __tablename__ = "drafting_facts"

    id: str = Field(primary_key=True)
    session_id: str = Field(index=True)

    # Fact content
    fact_type: str = Field()  # party, date, amount, claim, evidence, statute, jurisdiction, etc.
    fact_key: str = Field()   # e.g., "plaintiff_name", "filing_date", "contract_amount"
    fact_value: str = Field(sa_type=Text)

    # Source attribution
    confidence: float = Field(default=0.0)  # 0.0-1.0
    source_doc_id: Optional[str] = Field(default=None)
    source_message_idx: Optional[int] = Field(default=None)
    is_verified: bool = Field(default=False)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)

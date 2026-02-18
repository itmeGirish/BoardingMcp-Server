"""AgentOutput model for storing intermediate agent outputs (audit trail)."""
from sqlmodel import SQLModel, Field
from sqlalchemy import Text
from datetime import datetime


class AgentOutput(SQLModel, table=True):
    """
    Stores intermediate outputs from each agent for audit trail.

    Every agent writes its output here before passing to the next stage.
    """
    __tablename__ = "agent_outputs"

    id: str = Field(primary_key=True)
    session_id: str = Field(index=True)

    agent_name: str = Field()      # intake, fact_extraction, research, drafting, review
    output_type: str = Field()     # facts, citations, draft, review_notes
    output_data: str = Field(sa_type=Text)  # JSON blob

    created_at: datetime = Field(default_factory=datetime.now)

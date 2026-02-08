# app/database/postgresql/models/suppression_list.py
"""SuppressionList model for managing phone numbers excluded from broadcasts.

Per doc section 3.3.4:
- Global Suppression: Numbers that should never receive any message
- Campaign Suppression: Numbers excluded from specific campaigns
- Temporary Suppression: Time-limited exclusions (PAUSE requests)
- Bounce List: Numbers that consistently fail delivery
"""
from sqlmodel import SQLModel, Field
from sqlalchemy import Text
from typing import Optional
from datetime import datetime


class SuppressionList(SQLModel, table=True):
    """
    Phone numbers excluded from broadcasts.

    Types:
    - global: Never send any message (hard opt-out, legal block)
    - campaign: Excluded from specific campaigns only
    - temporary: Time-limited exclusion (e.g., PAUSE for 30 days)
    - bounce: Consistently fails delivery (number not on WhatsApp)
    - competitor: Optional exclusion of competitor contacts
    """
    __tablename__ = "suppression_lists"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    phone_e164: str = Field(index=True)

    # Type: global, campaign, temporary, bounce, competitor
    suppression_type: str = Field(index=True)

    # Reason for suppression
    reason: Optional[str] = Field(default=None, sa_type=Text)

    # For campaign-specific suppression
    broadcast_job_id: Optional[str] = Field(default=None, index=True)

    # For temporary suppression (e.g., PAUSE keyword = 30 days)
    expires_at: Optional[datetime] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True, index=True)

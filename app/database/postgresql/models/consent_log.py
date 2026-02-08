# app/database/postgresql/models/consent_log.py
"""ConsentLog model for tracking opt-in/opt-out lifecycle.

Per doc section 3.3.2 & 3.3.3:
- Opt-in sources: Website form, WhatsApp keyword, QR code, Click-to-WhatsApp ad, Manual import
- Opt-out keywords: STOP, UNSUBSCRIBE, PAUSE, STOP PROMO, START
- Audit trail: Immutable log of all consent events
"""
from sqlmodel import SQLModel, Field
from sqlalchemy import Text
from typing import Optional
from datetime import datetime


class ConsentLog(SQLModel, table=True):
    """
    Immutable audit trail of all consent events (opt-in, opt-out, pause, resume).

    Every consent change is logged as a new row - records are never updated.
    This provides a complete audit trail for TRAI, GDPR, and WhatsApp compliance.
    """
    __tablename__ = "consent_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    phone_e164: str = Field(index=True)  # Contact phone in E.164 format

    # Consent action: OPT_IN, OPT_OUT, PAUSE, RESUME, OPT_OUT_MARKETING
    action: str = Field(index=True)

    # Source of consent event
    # OPT_IN sources: website_form, whatsapp_keyword, qr_code, ctwa_ad, manual_import
    # OPT_OUT sources: keyword_stop, keyword_unsubscribe, keyword_pause, keyword_stop_promo, api, admin
    source: str = Field(default="")

    # The keyword that triggered this event (e.g., "STOP", "START")
    keyword: Optional[str] = Field(default=None)

    # Additional context
    ip_address: Optional[str] = Field(default=None)
    consent_text: Optional[str] = Field(default=None, sa_type=Text)  # Text shown to user at opt-in
    broadcast_job_id: Optional[str] = Field(default=None, index=True)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

# app/database/postgresql/models/template_creation.py
"""TemplateCreation model for tracking WhatsApp message template lifecycle."""
from sqlmodel import SQLModel, Field
from sqlalchemy import Text, JSON
from typing import Optional, Dict, Any, List
from datetime import datetime


class TemplateCreation(SQLModel, table=True):
    """
    Tracks WhatsApp message templates created, submitted, and managed by users.

    Stores the full template lifecycle:
    - Creation and submission to WhatsApp for approval
    - Approval/rejection status from WhatsApp
    - Template components (header, body, footer, buttons, carousel)
    - Usage tracking for broadcasts
    - Quality ratings from WhatsApp

    Template categories: MARKETING, UTILITY, AUTHENTICATION
    Template statuses: PENDING, APPROVED, REJECTED, PAUSED, DISABLED, DELETED
    """
    __tablename__ = "template_creations"

    # Primary identification
    id: Optional[int] = Field(default=None, primary_key=True)
    template_id: str = Field(index=True)  # WhatsApp template ID from API
    user_id: str = Field(index=True)
    business_id: str = Field(index=True)
    project_id: Optional[str] = Field(default=None, index=True)

    # Template core fields
    name: str = Field(index=True)
    category: str  # MARKETING, UTILITY, AUTHENTICATION
    language: str  # e.g., "en_US", "en", "hi"
    status: str = Field(default="PENDING", index=True)  # PENDING, APPROVED, REJECTED, PAUSED, DISABLED, DELETED

    # Template content (stored as JSON)
    components: Optional[List[Dict[str, Any]]] = Field(default=None, sa_type=JSON)

    # Rejection details
    rejected_reason: Optional[str] = Field(default=None, sa_type=Text)

    # Quality metrics from WhatsApp
    quality_rating: Optional[str] = Field(default=None)  # GREEN, YELLOW, RED
    quality_score: Optional[float] = Field(default=None)

    # Usage tracking
    usage_count: int = Field(default=0)
    last_used_at: Optional[datetime] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = Field(default=None)
    approved_at: Optional[datetime] = Field(default=None)
    is_active: bool = Field(default=True)

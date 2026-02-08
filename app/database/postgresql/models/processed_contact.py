# app/database/postgresql/models/processed_contact.py
"""ProcessedContact model for storing validated broadcast contacts.

Maps to the ProcessedContact output schema from the Data Processing Agent:
    phone_e164, name, email, country_code, quality_score,
    custom_fields, source_row, validation_errors
"""
from sqlmodel import SQLModel, Field
from sqlalchemy import JSON
from typing import Optional, Dict, Any, List
from datetime import datetime


class ProcessedContact(SQLModel, table=True):
    """
    Stores validated and scored contacts for a broadcast campaign.

    Created during the DATA_PROCESSING phase by the data processing pipeline.
    Each record represents one contact that was parsed, validated, deduplicated,
    and quality-scored.
    """
    __tablename__ = "processed_contacts"

    id: Optional[int] = Field(default=None, primary_key=True)
    broadcast_job_id: str = Field(index=True)
    user_id: str = Field(index=True)

    # E.164 normalized phone number (+919876543210)
    phone_e164: str = Field(index=True)
    name: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    country_code: str = Field(default="")  # IN, US, etc.

    # Quality score (0-100)
    quality_score: int = Field(default=0)

    # Dynamic attributes from the uploaded file
    custom_fields: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)

    # Original file row number for traceability
    source_row: Optional[int] = Field(default=None)

    # List of warning/validation strings
    validation_errors: Optional[List[str]] = Field(default=None, sa_type=JSON)

    # Duplicate tracking
    is_duplicate: bool = Field(default=False)
    duplicate_of: Optional[str] = Field(default=None)  # Phone number it duplicates

    created_at: datetime = Field(default_factory=datetime.utcnow)

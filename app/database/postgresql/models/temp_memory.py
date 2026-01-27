# app/database/postgresql/models/temp_memory.py
"""TempMemory model for storing runtime and onboarding-related details including JWT tokens."""
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class TempMemory(SQLModel, table=True):
    """
    Model for storing temporary notes, JWT tokens, and runtime onboarding details.

    This table tracks:
    - User/business/project associations
    - JWT and verification tokens (including email, password, base64_token)
    - Broadcasting status flags

    The first_broadcasting flag indicates if this is the very first broadcast
    for a user/project. It is set to True on initial insert after verification
    and set to False for subsequent broadcasting actions.
    """
    __tablename__ = "temporary_notes"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    business_id: str = Field(index=True)
    project_id: str = Field(index=True)

    # JWT Token fields (merged from jwt_tokens table)
    email: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)
    base64_token: Optional[str] = Field(default=None)  # <email>:<password>:<projectId> encoded in base64
    jwt_token: Optional[str] = Field(default=None)  # The actual JWT bearer token from API
    verification_token: Optional[str] = Field(default=None)

    # Broadcasting status flags
    first_broadcasting: bool = Field(default=True)  # True on first verification, False for subsequent
    broadcasting_status: bool = Field(default=True)  # True when broadcasting is active

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

"""Pydantic model for Update Business Details response."""
from typing import Optional, List
from pydantic import BaseModel, Field


class BusinessDetailsData(BaseModel):
    """Business details data model."""
    id: str
    active: bool
    display_name: str
    project_ids: List[str]
    user_name: str
    business_id: str
    email: str
    created_at: int
    updated_at: int
    company: str
    contact: str
    currency: str
    timezone: str
    partner_id: str
    type: str
    createdOn: str
    companySize: int
    password: bool


class UpdateBusinessDetailsResponse(BaseModel):
    """Response model for update business details endpoint."""
    success: bool
    data: Optional[BusinessDetailsData] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    details: Optional[dict] = None
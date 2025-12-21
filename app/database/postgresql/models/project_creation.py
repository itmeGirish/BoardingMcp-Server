from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import JSON


class WABusinessProfile(BaseModel):
    """Embedded WhatsApp Business Profile"""
    address: Optional[str] = None
    description: Optional[str] = None
    email: Optional[str] = None
    vertical: Optional[str] = None
    websites: list[str] = []


class Project_Creation(SQLModel, table=True):
    __tablename__ = "projects_creation"
    
    project_id: str = Field(primary_key=True)
    name: str
    project_owner_id: str = Field(index=True)
    partner_id: str = Field(index=True)
    plan_activated_on: Optional[int] = None
    status: str = Field(default="active", index=True)
    sandbox: bool = Field(default=False)
    active_plan: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    plan_renewal_on: Optional[int] = None
    scheduled_subscription_changes: Optional[str] = None
    mau_quota: int = Field(default=0)
    mau_usage: int = Field(default=0)
    credit: int = Field(default=0)
    
    # WhatsApp fields
    wa_number: Optional[str] = None
    wa_messaging_tier: Optional[str] = None
    wa_display_name_status: Optional[str] = None
    wa_display_name: Optional[str] = None
    wa_quality_rating: Optional[str] = None
    wa_about: Optional[str] = None
    wa_display_image: Optional[str] = None
    wa_business_profile: Optional[dict] = Field(default=None, sa_type=JSON)
    
    # Business fields
    fb_business_manager_status: Optional[str] = None
    billing_currency: str = Field(default="INR")
    timezone: str = Field(default="Asia/Calcutta GMT+05:30")
    
    # Subscription fields
    subscription_started_on: Optional[int] = None
    is_whatsapp_verified: bool = Field(default=False)
    subscription_status: Optional[str] = None
    applied_for_waba: bool = Field(default=False)
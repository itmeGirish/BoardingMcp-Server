from sqlmodel import SQLModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, UTC
from sqlalchemy import JSON, BigInteger


class ProjectCreation(SQLModel, table=True):
    __tablename__ = "project_creations"

    id: str = Field(primary_key=True)
    user_id: str = Field(index=True)
    business_id: str = Field(index=True)
    partner_id: Optional[str] = Field(default=None, index=True)
    
    # Project details
    name: str
    type: str = Field(default="project")
    status: Optional[str] = Field(default="active")
    sandbox: bool = Field(default=False)
    active_plan: Optional[str] = Field(default="NONE")
    
    # Plan and subscription - Changed to BigInteger
    plan_activated_on: Optional[int] = Field(default=None, sa_type=BigInteger)
    plan_renewal_on: Optional[int] = Field(default=None, sa_type=BigInteger)
    scheduled_subscription_changes: Optional[str] = Field(default=None)
    subscription_started_on: Optional[int] = Field(default=None, sa_type=BigInteger)
    subscription_status: Optional[str] = Field(default=None)
    
    # Usage and billing
    mau_quota: Optional[int] = Field(default=None)
    mau_usage: Optional[int] = Field(default=None)
    credit: Optional[int] = Field(default=None)
    billing_currency: str = Field(default="INR")
    timezone: str = Field(default="Asia/Calcutta GMT+05:30")
    
    # WhatsApp details
    wa_number: Optional[str] = Field(default=None)
    wa_messaging_tier: Optional[str] = Field(default=None)
    wa_display_name: Optional[str] = Field(default=None)
    wa_display_name_status: Optional[str] = Field(default=None)
    wa_quality_rating: Optional[str] = Field(default=None)
    wa_about: Optional[str] = Field(default=None)
    wa_display_image: Optional[str] = Field(default=None)
    wa_business_profile: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)
    waba_app_status: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)
    
    # Verification status
    fb_business_manager_status: Optional[str] = Field(default=None)
    is_whatsapp_verified: bool = Field(default=False)
    applied_for_waba: Optional[bool] = Field(default=None)
    
    # Timestamps - Changed to BigInteger
    created_at: Optional[int] = Field(default=None, sa_type=BigInteger)
    updated_at: Optional[int] = Field(default=None, sa_type=BigInteger)
    local_created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    local_updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
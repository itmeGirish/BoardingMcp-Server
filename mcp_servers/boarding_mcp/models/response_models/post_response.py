# response_model.py

"""Pydantic models for Business Creation Response."""

from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any


from typing import Optional, List, Union
from pydantic import BaseModel, Field, ConfigDict


# #This is the response model for business creation
# class BusinessCreationResponse(BaseModel):
#     id: str
#     user_id: str
#     onboarding_id: str
#     active: bool
#     display_name: str
#     project_ids: list[str]
#     user_name: str
#     business_id: str
#     email: str
#     created_at: datetime
#     updated_at: datetime
#     company: str
#     contact: str
#     currency: str
#     timezone: str
#     type: str

#     class ConfigDict:
#         from_attributes = True

# Response model for list of business creations
# class BusinessCreationListResponse(BaseModel):
#     total: int
#     data: list[BusinessCreationResponse]



# Response model including user details
class BusinessCreationWithUserResponse(BaseModel):
    id: str
    user_id: str
    onboarding_id: str
    active: bool
    display_name: str
    project_ids: list[str]
    user_name: str
    business_id: str
    email: str
    created_at: datetime
    updated_at: datetime
    company: str
    contact: str
    currency: str
    timezone: str
    type: str
    # user: UserResponse | None = None

    class ConfigDict:
        from_attributes = True

#Busienss creation Data

class BusinessCreationData(BaseModel):
    """Model for business creation response data."""
    
    id: str
    active: bool
    display_name: str = Field(alias="display_name")
    project_ids: List[str] = Field(default_factory=list)
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
    created_on: str = Field(alias="createdOn")
    company_size: int = Field(alias="companySize")
    password: bool
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore"
    }


class BusinessCreationResponse(BaseModel):
    """Model for the full business creation API response."""
    
    success: bool
    data: Optional[BusinessCreationData] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    
    model_config = {
        "extra": "ignore"
    }




#Create_project



class WABusinessProfile(BaseModel):
    """WhatsApp Business Profile details."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    address: Optional[str] = None
    description: Optional[str] = None
    email: Optional[str] = None
    vertical: Optional[str] = None
    websites: Optional[List[str]] = None


class ProjectResponse(BaseModel):
    """Response model for project data from AiSensy API."""
    
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    
    type: Optional[str] = None
    id: str
    name: Optional[str] = None
    project_owner_id: Optional[str] = Field(default=None, alias="project_owner_id")
    partner_id: Optional[str] = Field(default=None, alias="partner_id")
    plan_activated_on: Optional[int] = Field(default=None, alias="plan_activated_on")
    status: Optional[str] = None
    sandbox: Optional[bool] = None
    active_plan: Optional[str] = Field(default=None, alias="active_plan")
    created_at: Optional[int] = Field(default=None, alias="created_at")
    updated_at: Optional[int] = Field(default=None, alias="updated_at")
    plan_renewal_on: Optional[int] = Field(default=None, alias="plan_renewal_on")
    scheduled_subscription_changes: Optional[str] = Field(default=None, alias="scheduled_subscription_changes")
    mau_quota: Optional[int] = Field(default=None, alias="mau_quota")
    mau_usage: Optional[int] = Field(default=None, alias="mau_usage")
    credit: Optional[int] = None
    wa_number: Optional[str] = Field(default=None, alias="wa_number")
    wa_messaging_tier: Optional[str] = Field(default=None, alias="wa_messaging_tier")
    wa_display_name_status: Optional[str] = Field(default=None, alias="wa_display_name_status")
    fb_business_manager_status: Optional[str] = Field(default=None, alias="fb_business_manager_status")
    wa_display_name: Optional[str] = Field(default=None, alias="wa_display_name")
    wa_quality_rating: Optional[str] = Field(default=None, alias="wa_quality_rating")
    wa_about: Optional[str] = Field(default=None, alias="wa_about")
    wa_display_image: Optional[str] = Field(default=None, alias="wa_display_image")
    wa_business_profile: Optional[WABusinessProfile] = Field(default=None, alias="wa_business_profile")
    waba_app_status: Optional[Dict[str, Any]] = Field(default=None, alias="waba_app_status")
    billing_currency: Optional[str] = Field(default=None, alias="billing_currency")
    timezone: Optional[str] = None
    subscription_started_on: Optional[int] = Field(default=None, alias="subscription_started_on")
    is_whatsapp_verified: Optional[bool] = Field(default=None, alias="is_whatsapp_verified")
    subscription_status: Optional[str] = Field(default=None, alias="subscription_status")
    applied_for_waba: Optional[bool] = Field(default=None, alias="applied_for_waba")


class ProjectAPIResponse(BaseModel):
    """Response model for project API operations (single or list)."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    success: bool
    data: Optional[Union[ProjectResponse, List[ProjectResponse]]] = None
    error: Optional[str] = None
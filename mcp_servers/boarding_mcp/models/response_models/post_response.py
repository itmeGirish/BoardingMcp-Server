# response_model.py
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any

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


"""Pydantic models for Business Creation Response."""

from typing import List, Optional
from pydantic import BaseModel, Field


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
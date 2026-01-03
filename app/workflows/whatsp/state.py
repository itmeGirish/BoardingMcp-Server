"""State definitions for onboarding workflow"""

from typing import Dict, TypedDict, Any, Optional


class CreateBusinessProfileState(TypedDict):
    """State for business profile creation"""
    display_name: str
    email: str
    company: str
    contact: str
    timezone: str
    currency: str
    company_size: str
    password: str
    user_id: str
    onboarding_id: str


class CreateProjectState(TypedDict):
    """State for project creation"""
    name: str
    user_id: str


class EmbeddedSignupUrlState(TypedDict):
    """State for embedded signup URL generation"""
    business_name: str
    business_email: str
    phone_code: int
    website: str
    street_address: str
    city: str
    state: str
    zip_postal: str
    country: str
    timezone: str
    display_name: str
    category: str
    description: Optional[str]
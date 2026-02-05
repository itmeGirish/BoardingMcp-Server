"""
State definitions for onboarding workflow

This module defines all TypedDict classes for type-safe state management
across the onboarding workflow steps.
"""

from typing import TypedDict, Optional
from copilotkit import CopilotKitState


class CreateBusinessProfileState(TypedDict):
    """State for business profile creation (Step 1)"""
    user_id: str
    display_name: str
    email: str
    company: str
    contact: str
    timezone: str
    currency: str
    company_size: str
    password: str
    onboarding_id: str


class CreateProjectState(TypedDict):
    """State for project creation (Step 2)"""
    user_id: str
    name: str


class EmbeddedSignupUrlState(TypedDict):
    """State for embedded signup URL generation (Step 3)"""
    user_id: str
    business_name: str
    business_email: str
    phone_code: int
    phone_number: str
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



class OnboardingAgentState(CopilotKitState):
    """
    Main agent state for LangGraph workflow.

    Inherits from CopilotKitState which provides:
    - messages: List of conversation messages
    - Additional CopilotKit-specific fields
    """
    pass


__all__ = [
    "CreateBusinessProfileState",
    "CreateProjectState",
    "EmbeddedSignupUrlState",
    "OnboardingAgentState",
]

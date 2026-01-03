from typing import Dict, TypedDict, Any

class Create_business_profileState(TypedDict):
    display_name:str
    email:str
    company:str
    contact:str
    timezone:str
    currency:str
    company_size:str
    password:str
    user_id:str
    onboarding_id:str

class CreateProjectState(TypedDict):
    name: str
    user_id:str

class EmbeddedSignupUrlState(TypedDict):
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

    

"""
Pydantic models for post MCP tool request validation.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator, EmailStr


class CreateBusinessProfileRequest(BaseModel):
    """Model for creating a business profile."""
    
    display_name: str = Field(
        ...,
        description="Display name for the business",
        min_length=1,
        max_length=100,
        examples=["CallHippo Support"]
    )
    email: str = Field(
        ...,
        description="Business email address",
        examples=["support@callhippo.com"]
    )
    company: str = Field(
        ...,
        description="Company name",
        min_length=1,
        max_length=100,
        examples=["CallHippo"]
    )
    contact: str = Field(
        ...,
        description="Contact number",
        min_length=1,
        examples=["918116856153"]
    )
    timezone: str = Field(
        ...,
        description="Timezone",
        examples=["Asia/Calcutta GMT+05:30"]
    )
    currency: str = Field(
        ...,
        description="Currency code",
        min_length=3,
        max_length=3,
        examples=["INR", "USD"]
    )
    company_size: str = Field(
        ...,
        description="Size of the company",
        examples=["10 - 20", "50 - 100"]
    )
    password: str = Field(
        ...,
        description="Password for the business account",
        min_length=8
    )
    user_id: str = Field(
        ...,
        description="User ID for the business profile"
    )
    onboarding_id: str = Field(
        ...,
        description="Onboarding ID for the business profile"
    )
    
    @field_validator("display_name", "company", "contact", "timezone", "company_size")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate fields are not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace")
        return v


class CreateProjectRequest(BaseModel):
    """Model for creating a project."""
    
    name: str = Field(
        ...,
        description="Name for the project",
        min_length=1,
        max_length=100,
        examples=["API TEST PROJECT 1"]
    )
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate project name."""
        v = v.strip()
        if not v:
            raise ValueError("Project name cannot be empty or whitespace")
        return v


class EmbeddedSignupUrlRequest(BaseModel):
    """Model for generating embedded signup URL."""
    
    business_id: str = Field(..., description="The business ID", min_length=1)
    assistant_id: str = Field(..., description="The assistant ID", min_length=1)
    business_name: str = Field(..., description="Name of the business", min_length=1)
    business_email: str = Field(..., description="Email of the business")
    phone_code: int = Field(..., description="Phone country code", ge=1, examples=[1, 91])
    phone_number: str = Field(..., description="Phone number", min_length=1)
    website: str = Field(..., description="Business website URL")
    street_address: str = Field(..., description="Street address", min_length=1)
    city: str = Field(..., description="City name", min_length=1)
    state: str = Field(..., description="State/Province code", min_length=1)
    zip_postal: str = Field(..., description="ZIP/Postal code", min_length=1)
    country: str = Field(..., description="Country code", min_length=2, max_length=2, examples=["US", "IN"])
    timezone: str = Field(..., description="Timezone", examples=["UTC-08:00"])
    display_name: str = Field(..., description="Display name for the phone", min_length=1)
    category: str = Field(..., description="Business category", examples=["ENTERTAIN"])
    description: Optional[str] = Field(default="", description="Optional description")
    
    @field_validator("business_id", "assistant_id", "business_name", "phone_number", 
                     "street_address", "city", "state", "zip_postal", "display_name")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate fields are not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace")
        return v


class SubmitWabaAppIdRequest(BaseModel):
    """Model for submitting WABA App ID."""
    
    assistant_id: str = Field(..., description="The assistant ID", min_length=1)
    waba_app_id: str = Field(..., description="The WABA App ID", min_length=1)
    
    @field_validator("assistant_id", "waba_app_id")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate fields are not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace")
        return v


class StartMigrationRequest(BaseModel):
    """Model for starting migration."""
    
    assistant_id: str = Field(..., description="The assistant ID", min_length=1)
    target_id: str = Field(..., description="The target ID for migration", min_length=1)
    country_code: str = Field(..., description="Country code", min_length=1, examples=["91", "1"])
    phone_number: str = Field(..., description="Phone number to migrate", min_length=1)
    
    @field_validator("assistant_id", "target_id", "country_code", "phone_number")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate fields are not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace")
        return v


class RequestOtpRequest(BaseModel):
    """Model for requesting OTP."""
    
    assistant_id: str = Field(..., description="The assistant ID", min_length=1)
    mode: str = Field(
        default="sms",
        description="OTP delivery mode",
        pattern="^(sms|voice)$",
        examples=["sms", "voice"]
    )
    
    @field_validator("assistant_id")
    @classmethod
    def validate_assistant_id(cls, v: str) -> str:
        """Validate assistant_id."""
        v = v.strip()
        if not v:
            raise ValueError("assistant_id cannot be empty or whitespace")
        return v


class VerifyOtpRequest(BaseModel):
    """Model for verifying OTP."""
    
    assistant_id: str = Field(..., description="The assistant ID", min_length=1)
    otp: str = Field(..., description="The OTP code to verify", min_length=4, max_length=10)
    
    @field_validator("assistant_id", "otp")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate fields are not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace")
        return v


class BusinessAssistantRequest(BaseModel):
    """Model for requests requiring business_id and assistant_id."""
    
    business_id: str = Field(..., description="The business ID", min_length=1)
    assistant_id: str = Field(..., description="The assistant ID", min_length=1)
    
    @field_validator("business_id", "assistant_id")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate fields are not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace")
        return v


class CtwaAdsDashboardRequest(BaseModel):
    """Model for generating CTWA Ads Manager Dashboard URL."""
    
    business_id: str = Field(..., description="The business ID", min_length=1)
    assistant_id: str = Field(..., description="The assistant ID", min_length=1)
    expires_in: int = Field(
        default=150000,
        description="URL expiration time in milliseconds",
        ge=1000,
        examples=[150000]
    )
    
    @field_validator("business_id", "assistant_id")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate fields are not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace")
        return v





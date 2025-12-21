"""
Pydantic models for MCP tool request validation for Direct API PATCH requests.
"""
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class UpdateBusinessProfilePictureRequest(BaseModel):
    """Model for update business profile picture request."""
    
    whatsapp_display_image: str = Field(
        ...,
        description="URL of the new profile picture",
        min_length=1,
        examples=["https://example.com/image.jpg"]
    )
    
    @field_validator("whatsapp_display_image")
    @classmethod
    def validate_whatsapp_display_image(cls, v: str) -> str:
        """Validate and sanitize whatsapp_display_image."""
        v = v.strip()
        if not v:
            raise ValueError("whatsapp_display_image cannot be empty or whitespace")
        return v


class UpdateBusinessProfileDetailsRequest(BaseModel):
    """Model for update business profile details request."""
    
    whatsapp_about: Optional[str] = Field(
        default=None,
        description="WhatsApp about/status text",
        examples=["My WhatsApp"]
    )
    address: Optional[str] = Field(
        default=None,
        description="Business address",
        examples=["32/1 J Street, ABC"]
    )
    description: Optional[str] = Field(
        default=None,
        description="Business description",
        examples=["Official whatsapp account"]
    )
    vertical: Optional[str] = Field(
        default=None,
        description="Business vertical",
        examples=["HEALTH", "RETAIL"]
    )
    email: Optional[str] = Field(
        default=None,
        description="Business email",
        examples=["mybusiness@business.com"]
    )
    websites: Optional[List[str]] = Field(
        default=None,
        description="List of business website URLs",
        examples=[["https://yoursite.com"]]
    )
    whatsapp_display_image: Optional[str] = Field(
        default=None,
        description="URL of the profile picture"
    )
    
    @field_validator("whatsapp_about", "address", "description", "email")
    @classmethod
    def validate_string_fields(cls, v: Optional[str]) -> Optional[str]:
        """Validate and sanitize string fields."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class UpdateQrCodeRequest(BaseModel):
    """Model for update QR code request."""
    
    qr_code_id: str = Field(
        ...,
        description="The QR code ID to update",
        min_length=1,
        examples=["G4IVZHFAUJY311"]
    )
    prefilled_message: str = Field(
        ...,
        description="The new prefilled message for the QR code",
        min_length=1,
        examples=["Cyber Tuesday"]
    )
    
    @field_validator("qr_code_id", "prefilled_message")
    @classmethod
    def validate_required_fields(cls, v: str) -> str:
        """Validate and sanitize required fields."""
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace")
        return v


class UpdateFlowMetadataRequest(BaseModel):
    """Model for update flow metadata request."""
    
    flow_id: str = Field(
        ...,
        description="The flow ID to update",
        min_length=1,
        examples=["flow_abc123"]
    )
    name: Optional[str] = Field(
        default=None,
        description="New flow name",
        examples=["First Flow"]
    )
    categories: Optional[List[str]] = Field(
        default=None,
        description="New list of flow categories",
        examples=[["APPOINTMENT_BOOKING", "LEAD_GENERATION"]]
    )
    
    @field_validator("flow_id")
    @classmethod
    def validate_flow_id(cls, v: str) -> str:
        """Validate and sanitize flow_id."""
        v = v.strip()
        if not v:
            raise ValueError("flow_id cannot be empty or whitespace")
        return v
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate and sanitize name."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v
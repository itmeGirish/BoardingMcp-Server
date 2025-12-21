"""
Pydantic models for MCP tool request validation for Direct API GET requests.
"""
from pydantic import BaseModel, Field, field_validator


class TemplateIdRequest(BaseModel):
    """Model for requests that require a template_id."""
    
    template_id: str = Field(
        ...,
        description="The unique template identifier",
        min_length=1,
        examples=["156167230836488", "template_abc123"]
    )
    
    @field_validator("template_id")
    @classmethod
    def validate_template_id(cls, v: str) -> str:
        """Validate and sanitize template_id."""
        v = v.strip()
        if not v:
            raise ValueError("template_id cannot be empty or whitespace")
        return v


class UploadSessionIdRequest(BaseModel):
    """Model for requests that require an upload_session_id."""
    
    upload_session_id: str = Field(
        ...,
        description="The unique upload session identifier",
        min_length=1,
        examples=["session_abc123", "upload_67890xyz"]
    )
    
    @field_validator("upload_session_id")
    @classmethod
    def validate_upload_session_id(cls, v: str) -> str:
        """Validate and sanitize upload_session_id."""
        v = v.strip()
        if not v:
            raise ValueError("upload_session_id cannot be empty or whitespace")
        return v


class FlowIdRequest(BaseModel):
    """Model for requests that require a flow_id."""
    
    flow_id: str = Field(
        ...,
        description="The unique flow identifier",
        min_length=1,
        examples=["flow_abc123", "12345678"]
    )
    
    @field_validator("flow_id")
    @classmethod
    def validate_flow_id(cls, v: str) -> str:
        """Validate and sanitize flow_id."""
        v = v.strip()
        if not v:
            raise ValueError("flow_id cannot be empty or whitespace")
        return v


class PaymentConfigurationNameRequest(BaseModel):
    """Model for requests that require a configuration_name."""
    
    configuration_name: str = Field(
        ...,
        description="The payment configuration name",
        min_length=1,
        examples=["razorpay_config", "stripe_payment"]
    )
    
    @field_validator("configuration_name")
    @classmethod
    def validate_configuration_name(cls, v: str) -> str:
        """Validate and sanitize configuration_name."""
        v = v.strip()
        if not v:
            raise ValueError("configuration_name cannot be empty or whitespace")
        return v
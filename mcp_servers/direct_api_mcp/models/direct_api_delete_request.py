"""
Pydantic models for MCP tool request validation for Direct API DELETE requests.
"""
from pydantic import BaseModel, Field, field_validator


class DeleteWaTemplateByIdRequest(BaseModel):
    """Model for delete WA template by ID request."""
    
    template_id: str = Field(
        ...,
        description="The template ID to delete",
        min_length=1,
        examples=["156167230836488"]
    )
    template_name: str = Field(
        ...,
        description="The template name",
        min_length=1,
        examples=["mytemplate"]
    )
    
    @field_validator("template_id", "template_name")
    @classmethod
    def validate_fields(cls, v: str) -> str:
        """Validate and sanitize template fields."""
        v = v.strip()
        if not v:
            raise ValueError(f"Field cannot be empty or whitespace")
        return v


class DeleteWaTemplateByNameRequest(BaseModel):
    """Model for delete WA template by name request."""
    
    template_name: str = Field(
        ...,
        description="The template name to delete",
        min_length=1,
        examples=["my_template", "welcome_message"]
    )
    
    @field_validator("template_name")
    @classmethod
    def validate_template_name(cls, v: str) -> str:
        """Validate and sanitize template_name."""
        v = v.strip()
        if not v:
            raise ValueError("template_name cannot be empty or whitespace")
        return v


class DeleteMediaByIdRequest(BaseModel):
    """Model for delete media by ID request."""
    
    media_id: str = Field(
        ...,
        description="The media ID to delete",
        min_length=1,
        examples=["media_abc123"]
    )
    
    @field_validator("media_id")
    @classmethod
    def validate_media_id(cls, v: str) -> str:
        """Validate and sanitize media_id."""
        v = v.strip()
        if not v:
            raise ValueError("media_id cannot be empty or whitespace")
        return v


class DeleteFlowRequest(BaseModel):
    """Model for delete flow request."""
    
    flow_id: str = Field(
        ...,
        description="The flow ID to delete",
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
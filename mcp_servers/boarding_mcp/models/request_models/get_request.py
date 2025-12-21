"""
Pydantic models for MCP tool request validation for GET request.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ProjectIdRequest(BaseModel):
    """Model for requests that require a project_id."""
    
    project_id: str = Field(
        ...,
        description="The unique project identifier",
        min_length=1,
        examples=["proj_abc123", "67890xyz"]
    )
    
    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, v: str) -> str:
        """Validate and sanitize project_id."""
        v = v.strip()
        if not v:
            raise ValueError("project_id cannot be empty or whitespace")
        return v


class BusinessProjectsRequest(BaseModel):
    """Model for fetching business projects with optional field filters."""
    
    fields: Optional[str] = Field(
        default=None,
        description="Comma-separated list of fields to include in response",
        examples=["name,status", "name,status,createdAt"]
    )
    additional_fields: Optional[str] = Field(
        default=None,
        description="Comma-separated list of additional fields to include",
        examples=["metadata", "settings,metadata"]
    )
    
    @field_validator("fields", "additional_fields")
    @classmethod
    def validate_fields(cls, v: Optional[str]) -> Optional[str]:
        """Validate and sanitize field parameters."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v
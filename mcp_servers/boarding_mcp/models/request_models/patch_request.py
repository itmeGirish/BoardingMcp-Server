"""
Pydantic models for MCP tool request validation for patch request.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class UpdateBusinessDetailsRequest(BaseModel):
    """Model for updating business details."""
    
    display_name: Optional[str] = Field(
        default=None,
        description="New display name for the business",
        max_length=100,
        examples=["Akira"]
    )
    company: Optional[str] = Field(
        default=None,
        description="New company name",
        max_length=100,
        examples=["Aisensy"]
    )
    contact: Optional[str] = Field(
        default=None,
        description="New contact number",
        examples=["918645614148"]
    )
    
    @field_validator("display_name", "company", "contact")
    @classmethod
    def validate_not_empty_if_provided(cls, v: Optional[str]) -> Optional[str]:
        """Validate fields are not empty if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Field cannot be empty or whitespace if provided")
        return v
    
    def has_updates(self) -> bool:
        """Check if at least one field is provided for update."""
        return any([
            self.display_name is not None,
            self.company is not None,
            self.contact is not None
        ])


from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import ARRAY, Text

if TYPE_CHECKING:
    from .user_table import User


# Business Creation Model
class BusinessCreation(SQLModel, table=True):
    __tablename__ = "business_creations"

    id: str = Field(primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    onboarding_id: str = Field(index=True)
    active: bool = Field(default=True)
    display_name: str
    project_ids: list[str] = Field(default=[], sa_type=ARRAY(Text))
    user_name: str
    business_id: str = Field(index=True)
    email: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    company: str
    contact: str
    currency: str = Field(default="INR")
    timezone: str = Field(default="Asia/Calcutta")
    type: str = Field(default="owner")

    # Relationship - only keep user relationship
    user: Optional["User"] = Relationship(back_populates="business_creations")
    
    # REMOVED: project_creations relationship
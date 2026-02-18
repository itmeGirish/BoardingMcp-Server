"""PromotionLog model for staging -> main promotion audit trail."""
from sqlmodel import SQLModel, Field
from datetime import datetime


class PromotionLog(SQLModel, table=True):
    """
    Audit trail for rule promotions from staging_rules to main_rules.
    """
    __tablename__ = "promotion_logs"

    id: str = Field(primary_key=True)
    staging_rule_id: str = Field(index=True)
    main_rule_id: str = Field(index=True)
    promoted_at: datetime = Field(default_factory=datetime.now)
    occurrence_count_at_promotion: int = Field()

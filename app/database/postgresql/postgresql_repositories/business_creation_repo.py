from __future__ import annotations
from typing import Optional
from datetime import datetime
from dataclasses import dataclass
from sqlmodel import Session
from ..models import BusinessCreation
from ....config.logging import logger


@dataclass
class BusinessCreationRepository:
    session: Session

    def create(
        self,
        id: str,
        user_id: str,
        onboarding_id: str,
        display_name: str,
        project_ids: list[str],
        user_name: str,
        business_id: str,
        email: str,
        company: str,
        contact: str,
        currency: Optional[str] = "INR",
        timezone: Optional[str] = "Asia/Calcutta",
        type: Optional[str] = "owner"
    ) -> BusinessCreation | None:
        try:
            business_creation = BusinessCreation(
                id=id,
                user_id=user_id,
                onboarding_id=onboarding_id,
                display_name=display_name,
                project_ids=project_ids,
                user_name=user_name,
                business_id=business_id,
                email=email,
                company=company,
                contact=contact,
                currency=currency,
                timezone=timezone,
                type=type,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            self.session.add(business_creation)
            self.session.commit()
            self.session.refresh(business_creation)
            logger.info(f"BusinessCreation Inserted: {id}")
            return business_creation
        
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to insert BusinessCreation: {e}")
            raise e
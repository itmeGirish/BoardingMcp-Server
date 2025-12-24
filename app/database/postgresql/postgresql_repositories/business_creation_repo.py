"""Business Creation Repository."""
from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass
from sqlmodel import Session, select
from ..models import BusinessCreation
from app import logger


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

    def get_by_id(self, id: str) -> BusinessCreation | None:
        """Get a business creation record by ID."""
        try:
            statement = select(BusinessCreation).where(BusinessCreation.id == id)
            result = self.session.exec(statement).first()
            return result
        except Exception as e:
            logger.error(f"Failed to get BusinessCreation by id {id}: {e}")
            raise e

    def get_by_user_id(self, user_id: str) -> List[BusinessCreation]:
        """Get all business creation records for a user."""
        try:
            statement = select(BusinessCreation).where(BusinessCreation.user_id == user_id)
            results = self.session.exec(statement).all()
            return list(results)
        except Exception as e:
            logger.error(f"Failed to get BusinessCreation by user_id {user_id}: {e}")
            raise e

    def get_ids_by_user_id(self, user_id: str) -> List[dict]:
        """Get only id and business_id for a user."""
        try:
            statement = select(
                BusinessCreation.id, 
                BusinessCreation.business_id
            ).where(BusinessCreation.user_id == user_id)
            results = self.session.exec(statement).all()
            return [{"id": r[0], "business_id": r[1]} for r in results]
        except Exception as e:
            logger.error(f"Failed to get IDs by user_id {user_id}: {e}")
            raise e

    def get_by_email(self, email: str) -> BusinessCreation | None:
        """Get a business creation record by email."""
        try:
            statement = select(BusinessCreation).where(BusinessCreation.email == email)
            result = self.session.exec(statement).first()
            return result
        except Exception as e:
            logger.error(f"Failed to get BusinessCreation by email {email}: {e}")
            raise e

    def get_all(self) -> List[BusinessCreation]:
        """Get all business creation records."""
        try:
            statement = select(BusinessCreation)
            results = self.session.exec(statement).all()
            return list(results)
        except Exception as e:
            logger.error(f"Failed to get all BusinessCreation records: {e}")
            raise e

    def get_by_business_id(self, business_id: str) -> BusinessCreation | None:
        """Get a business creation record by business_id."""
        try:
            statement = select(BusinessCreation).where(BusinessCreation.business_id == business_id)
            result = self.session.exec(statement).first()
            return result
        except Exception as e:
            logger.error(f"Failed to get BusinessCreation by business_id {business_id}: {e}")
            raise e
    
    def get_everything_by_id(self, user_id: str) -> Optional[dict]:
        """Get all fields of a business creation record by ID as a dictionary."""
        try:
            statement = select(BusinessCreation).where(BusinessCreation.user_id == user_id)
            result = self.session.exec(statement).first()
            return result.model_dump() if result else None
        except Exception as e:
            logger.error(f"Failed to get everything for BusinessCreation by id {id}: {e}")
            raise e
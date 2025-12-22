"""Project Creation Repository."""
from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from sqlmodel import Session, select
from ..models import ProjectCreation
from app import logger


@dataclass
class ProjectCreationRepository:
    session: Session

    def create(
        self,
        id: str,
        user_id: str,
        business_id: str,
        name: str,
        partner_id: Optional[str] = None,
        type: str = "project",
        status: Optional[str] = "active",
        sandbox: bool = False,
        active_plan: Optional[str] = "NONE",
        plan_activated_on: Optional[int] = None,
        plan_renewal_on: Optional[int] = None,
        scheduled_subscription_changes: Optional[str] = None,
        subscription_started_on: Optional[int] = None,
        subscription_status: Optional[str] = None,
        mau_quota: Optional[int] = None,
        mau_usage: Optional[int] = None,
        credit: Optional[int] = None,
        billing_currency: str = "INR",
        timezone: str = "Asia/Calcutta GMT+05:30",
        wa_number: Optional[str] = None,
        wa_messaging_tier: Optional[str] = None,
        wa_display_name: Optional[str] = None,
        wa_display_name_status: Optional[str] = None,
        wa_quality_rating: Optional[str] = None,
        wa_about: Optional[str] = None,
        wa_display_image: Optional[str] = None,
        wa_business_profile: Optional[Dict[str, Any]] = None,
        waba_app_status: Optional[Dict[str, Any]] = None,
        fb_business_manager_status: Optional[str] = None,
        is_whatsapp_verified: bool = False,
        applied_for_waba: Optional[bool] = None,
        created_at: Optional[int] = None,
        updated_at: Optional[int] = None,
    ) -> ProjectCreation | None:
        try:
            project_creation = ProjectCreation(
                id=id,
                user_id=user_id,
                business_id=business_id,
                name=name,
                partner_id=partner_id,
                type=type,
                status=status,
                sandbox=sandbox,
                active_plan=active_plan,
                plan_activated_on=plan_activated_on,
                plan_renewal_on=plan_renewal_on,
                scheduled_subscription_changes=scheduled_subscription_changes,
                subscription_started_on=subscription_started_on,
                subscription_status=subscription_status,
                mau_quota=mau_quota,
                mau_usage=mau_usage,
                credit=credit,
                billing_currency=billing_currency,
                timezone=timezone,
                wa_number=wa_number,
                wa_messaging_tier=wa_messaging_tier,
                wa_display_name=wa_display_name,
                wa_display_name_status=wa_display_name_status,
                wa_quality_rating=wa_quality_rating,
                wa_about=wa_about,
                wa_display_image=wa_display_image,
                wa_business_profile=wa_business_profile,
                waba_app_status=waba_app_status,
                fb_business_manager_status=fb_business_manager_status,
                is_whatsapp_verified=is_whatsapp_verified,
                applied_for_waba=applied_for_waba,
                created_at=created_at,
                updated_at=updated_at,
                local_created_at=datetime.utcnow(),
                local_updated_at=datetime.utcnow(),
            )
            self.session.add(project_creation)
            self.session.commit()
            self.session.refresh(project_creation)
            logger.info(f"ProjectCreation Inserted: {id}")
            return project_creation

        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to insert ProjectCreation: {e}")
            raise e

    def get_by_id(self, id: str) -> ProjectCreation | None:
        """Get a project creation record by ID."""
        try:
            statement = select(ProjectCreation).where(ProjectCreation.id == id)
            result = self.session.exec(statement).first()
            return result
        except Exception as e:
            logger.error(f"Failed to get ProjectCreation by id {id}: {e}")
            raise e

    def get_by_user_id(self, user_id: str) -> List[ProjectCreation]:
        """Get all project creation records for a user."""
        try:
            statement = select(ProjectCreation).where(ProjectCreation.user_id == user_id)
            results = self.session.exec(statement).all()
            return list(results)
        except Exception as e:
            logger.error(f"Failed to get ProjectCreation by user_id {user_id}: {e}")
            raise e

    def get_by_business_id(self, business_id: str) -> List[ProjectCreation]:
        """Get all project creation records for a business."""
        try:
            statement = select(ProjectCreation).where(ProjectCreation.business_id == business_id)
            results = self.session.exec(statement).all()
            return list(results)
        except Exception as e:
            logger.error(f"Failed to get ProjectCreation by business_id {business_id}: {e}")
            raise e

    def get_ids_by_user_id(self, user_id: str) -> List[dict]:
        """Get only id, name and business_id for a user."""
        try:
            statement = select(
                ProjectCreation.id,
                ProjectCreation.name,
                ProjectCreation.business_id
            ).where(ProjectCreation.user_id == user_id)
            results = self.session.exec(statement).all()
            return [{"id": r[0], "name": r[1], "business_id": r[2]} for r in results]
        except Exception as e:
            logger.error(f"Failed to get IDs by user_id {user_id}: {e}")
            raise e

    def get_ids_by_business_id(self, business_id: str) -> List[dict]:
        """Get only id and name for a business."""
        try:
            statement = select(
                ProjectCreation.id,
                ProjectCreation.name
            ).where(ProjectCreation.business_id == business_id)
            results = self.session.exec(statement).all()
            return [{"id": r[0], "name": r[1]} for r in results]
        except Exception as e:
            logger.error(f"Failed to get IDs by business_id {business_id}: {e}")
            raise e

    def get_by_name(self, name: str) -> ProjectCreation | None:
        """Get a project creation record by name."""
        try:
            statement = select(ProjectCreation).where(ProjectCreation.name == name)
            result = self.session.exec(statement).first()
            return result
        except Exception as e:
            logger.error(f"Failed to get ProjectCreation by name {name}: {e}")
            raise e

    def get_all(self) -> List[ProjectCreation]:
        """Get all project creation records."""
        try:
            statement = select(ProjectCreation)
            results = self.session.exec(statement).all()
            return list(results)
        except Exception as e:
            logger.error(f"Failed to get all ProjectCreation records: {e}")
            raise e

    def update(self, id: str, **kwargs) -> ProjectCreation | None:
        """Update a project creation record."""
        try:
            project = self.get_by_id(id)
            if not project:
                logger.warning(f"ProjectCreation not found for update: {id}")
                return None

            for key, value in kwargs.items():
                if hasattr(project, key):
                    setattr(project, key, value)

            project.local_updated_at = datetime.utcnow()
            self.session.add(project)
            self.session.commit()
            self.session.refresh(project)
            logger.info(f"ProjectCreation Updated: {id}")
            return project

        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update ProjectCreation {id}: {e}")
            raise e

    def delete(self, id: str) -> bool:
        """Delete a project creation record."""
        try:
            project = self.get_by_id(id)
            if not project:
                logger.warning(f"ProjectCreation not found for delete: {id}")
                return False

            self.session.delete(project)
            self.session.commit()
            logger.info(f"ProjectCreation Deleted: {id}")
            return True

        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to delete ProjectCreation {id}: {e}")
            raise e

    def get_by_partner_id(self, partner_id: str) -> List[ProjectCreation]:
        """Get all project creation records for a partner."""
        try:
            statement = select(ProjectCreation).where(ProjectCreation.partner_id == partner_id)
            results = self.session.exec(statement).all()
            return list(results)
        except Exception as e:
            logger.error(f"Failed to get ProjectCreation by partner_id {partner_id}: {e}")
            raise e

    def get_active_projects(self, user_id: str) -> List[ProjectCreation]:
        """Get all active projects for a user."""
        try:
            statement = select(ProjectCreation).where(
                ProjectCreation.user_id == user_id,
                ProjectCreation.status == "active"
            )
            results = self.session.exec(statement).all()
            return list(results)
        except Exception as e:
            logger.error(f"Failed to get active projects for user_id {user_id}: {e}")
            raise e
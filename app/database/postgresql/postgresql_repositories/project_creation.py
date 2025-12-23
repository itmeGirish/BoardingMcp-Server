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
    
    def get_all_projects_by_user_id(self, user_id: str) -> List[tuple[str, str, str]]:
        """Get all (name, id, business_id) tuples for a given user_id."""
        try:
            statement = select(
                ProjectCreation.name,
                ProjectCreation.id,
                ProjectCreation.business_id).where(ProjectCreation.user_id == user_id)
            results = self.session.exec(statement).all()
            return list(results)
        except Exception as e:
            logger.error(f"Failed to get projects for user_id {user_id}: {e}")
            raise e
    
    def get_project_by_user_id(self, user_id: str) -> Optional[tuple[str, str, str]]:
        """Get name, id, and business_id for a given user_id."""
        try:
            statement = select(
            ProjectCreation.name,
            ProjectCreation.id,
            ProjectCreation.business_id).where(ProjectCreation.user_id == user_id)
            result = self.session.exec(statement).first()
            return result  # Returns (name, id, business_id) or None
        except Exception as e:
            logger.error(f"Failed to get project for user_id {user_id}: {e}")
            raise e

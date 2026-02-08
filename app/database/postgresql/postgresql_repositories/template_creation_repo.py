"""TemplateCreation Repository for WhatsApp template lifecycle management."""
from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass
from sqlmodel import Session, select
from ..models.template_creation import TemplateCreation
from app import logger


@dataclass
class TemplateCreationRepository:
    """Repository for TemplateCreation CRUD operations."""
    session: Session

    def create(
        self,
        template_id: str,
        user_id: str,
        business_id: str,
        name: str,
        category: str,
        language: str,
        components: list = None,
        project_id: str = None,
        status: str = "PENDING",
    ) -> TemplateCreation:
        """
        Create a new template record after submission to WhatsApp.

        Args:
            template_id: WhatsApp template ID returned from API
            user_id: User who created the template
            business_id: Business the template belongs to
            name: Template name
            category: MARKETING, UTILITY, or AUTHENTICATION
            language: Language code (e.g., "en_US")
            components: Template components list (header, body, footer, buttons)
            project_id: Optional project ID
            status: Initial status (default PENDING)

        Returns:
            Created TemplateCreation record
        """
        try:
            logger.info("=" * 60)
            logger.info("TEMPLATE CREATION REPOSITORY - CREATE")
            logger.info(f"  template_id: {template_id}")
            logger.info(f"  user_id: {user_id}")
            logger.info(f"  business_id: {business_id}")
            logger.info(f"  name: {name}")
            logger.info(f"  category: {category}")
            logger.info(f"  language: {language}")
            logger.info(f"  status: {status}")

            template = TemplateCreation(
                template_id=template_id,
                user_id=user_id,
                business_id=business_id,
                project_id=project_id,
                name=name,
                category=category,
                language=language,
                status=status,
                components=components,
                submitted_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            self.session.add(template)
            self.session.commit()
            self.session.refresh(template)

            logger.info(f"  Template record created: id={template.id}")
            logger.info("=" * 60)
            return template

        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to create template record: {e}")
            raise e

    def get_by_template_id(self, template_id: str) -> Optional[dict]:
        """Get template by WhatsApp template ID."""
        try:
            statement = select(TemplateCreation).where(
                TemplateCreation.template_id == template_id,
                TemplateCreation.is_active == True
            )
            record = self.session.exec(statement).first()
            if record:
                return self._to_dict(record)
            return None
        except Exception as e:
            logger.error(f"Failed to get template {template_id}: {e}")
            raise e

    def get_by_user_id(self, user_id: str) -> List[dict]:
        """Get all active templates for a user, most recent first."""
        try:
            statement = select(TemplateCreation).where(
                TemplateCreation.user_id == user_id,
                TemplateCreation.is_active == True
            ).order_by(TemplateCreation.updated_at.desc())
            records = self.session.exec(statement).all()
            return [self._to_dict(r) for r in records]
        except Exception as e:
            logger.error(f"Failed to get templates for user {user_id}: {e}")
            raise e

    def get_by_business_id(self, business_id: str) -> List[dict]:
        """Get all active templates for a business."""
        try:
            statement = select(TemplateCreation).where(
                TemplateCreation.business_id == business_id,
                TemplateCreation.is_active == True
            ).order_by(TemplateCreation.updated_at.desc())
            records = self.session.exec(statement).all()
            return [self._to_dict(r) for r in records]
        except Exception as e:
            logger.error(f"Failed to get templates for business {business_id}: {e}")
            raise e

    def get_by_user_and_status(self, user_id: str, status: str) -> List[dict]:
        """Get templates for a user filtered by status (APPROVED, PENDING, REJECTED, etc.)."""
        try:
            statement = select(TemplateCreation).where(
                TemplateCreation.user_id == user_id,
                TemplateCreation.status == status,
                TemplateCreation.is_active == True
            ).order_by(TemplateCreation.updated_at.desc())
            records = self.session.exec(statement).all()
            return [self._to_dict(r) for r in records]
        except Exception as e:
            logger.error(f"Failed to get templates for user {user_id} with status {status}: {e}")
            raise e

    def get_by_user_and_category(self, user_id: str, category: str) -> List[dict]:
        """Get templates for a user filtered by category (MARKETING, UTILITY, AUTHENTICATION)."""
        try:
            statement = select(TemplateCreation).where(
                TemplateCreation.user_id == user_id,
                TemplateCreation.category == category,
                TemplateCreation.is_active == True
            ).order_by(TemplateCreation.updated_at.desc())
            records = self.session.exec(statement).all()
            return [self._to_dict(r) for r in records]
        except Exception as e:
            logger.error(f"Failed to get templates for user {user_id} with category {category}: {e}")
            raise e

    def update_status(
        self,
        template_id: str,
        status: str,
        rejected_reason: str = None
    ) -> bool:
        """
        Update template approval status.

        Args:
            template_id: WhatsApp template ID
            status: New status (APPROVED, REJECTED, PAUSED, DISABLED)
            rejected_reason: Reason for rejection (if REJECTED)

        Returns:
            True if updated successfully
        """
        try:
            record = self._get_record_by_template_id(template_id)
            if not record:
                logger.warning(f"Template not found: {template_id}")
                return False

            record.status = status
            record.rejected_reason = rejected_reason
            record.updated_at = datetime.utcnow()

            if status == "APPROVED":
                record.approved_at = datetime.utcnow()

            self.session.commit()
            logger.info(f"Template {template_id}: status updated to {status}")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update template status for {template_id}: {e}")
            raise e

    def update_components(self, template_id: str, components: list) -> bool:
        """Update template components after editing."""
        try:
            record = self._get_record_by_template_id(template_id)
            if not record:
                return False

            record.components = components
            record.status = "PENDING"  # Re-submitted for approval after edit
            record.updated_at = datetime.utcnow()
            self.session.commit()
            logger.info(f"Template {template_id}: components updated, status reset to PENDING")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update components for {template_id}: {e}")
            raise e

    def update_quality(
        self, template_id: str, quality_rating: str, quality_score: float = None
    ) -> bool:
        """Update template quality metrics from WhatsApp."""
        try:
            record = self._get_record_by_template_id(template_id)
            if not record:
                return False

            record.quality_rating = quality_rating
            record.quality_score = quality_score
            record.updated_at = datetime.utcnow()
            self.session.commit()
            logger.info(f"Template {template_id}: quality updated to {quality_rating}")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update quality for {template_id}: {e}")
            raise e

    def increment_usage(self, template_id: str) -> bool:
        """Increment the usage counter and update last_used_at."""
        try:
            record = self._get_record_by_template_id(template_id)
            if not record:
                return False

            record.usage_count += 1
            record.last_used_at = datetime.utcnow()
            record.updated_at = datetime.utcnow()
            self.session.commit()
            logger.info(f"Template {template_id}: usage count incremented to {record.usage_count}")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to increment usage for {template_id}: {e}")
            raise e

    def soft_delete(self, template_id: str) -> bool:
        """Soft delete a template (set is_active=False, status=DELETED)."""
        try:
            record = self._get_record_by_template_id(template_id)
            if not record:
                return False

            record.is_active = False
            record.status = "DELETED"
            record.updated_at = datetime.utcnow()
            self.session.commit()
            logger.info(f"Template {template_id}: soft deleted")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to delete template {template_id}: {e}")
            raise e

    def _get_record_by_template_id(self, template_id: str) -> Optional[TemplateCreation]:
        """Get raw TemplateCreation record by WhatsApp template ID."""
        statement = select(TemplateCreation).where(
            TemplateCreation.template_id == template_id
        )
        return self.session.exec(statement).first()

    def _to_dict(self, record: TemplateCreation) -> dict:
        """Convert TemplateCreation record to dictionary."""
        return {
            "id": record.id,
            "template_id": record.template_id,
            "user_id": record.user_id,
            "business_id": record.business_id,
            "project_id": record.project_id,
            "name": record.name,
            "category": record.category,
            "language": record.language,
            "status": record.status,
            "components": record.components,
            "rejected_reason": record.rejected_reason,
            "quality_rating": record.quality_rating,
            "quality_score": record.quality_score,
            "usage_count": record.usage_count,
            "last_used_at": record.last_used_at.isoformat() if record.last_used_at else None,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            "submitted_at": record.submitted_at.isoformat() if record.submitted_at else None,
            "approved_at": record.approved_at.isoformat() if record.approved_at else None,
            "is_active": record.is_active,
        }

"""BroadcastJob Repository for broadcast campaign persistence and state management."""
from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass
from sqlmodel import Session, select
from ..models.broadcast_job import BroadcastJob
from app import logger


# Valid state transitions for the broadcast state machine
ALLOWED_TRANSITIONS = {
    # LLM may skip intermediate phase updates, so SCHEDULED and FAILED are reachable
    # from any active (pre-send) phase to handle compliance time window blocks.
    "INITIALIZED": {"DATA_PROCESSING", "COMPLIANCE_CHECK", "SCHEDULED", "FAILED"},
    "DATA_PROCESSING": {"COMPLIANCE_CHECK", "SCHEDULED", "FAILED"},
    "COMPLIANCE_CHECK": {"SEGMENTATION", "SCHEDULED", "FAILED"},
    "SEGMENTATION": {"CONTENT_CREATION", "FAILED"},
    "CONTENT_CREATION": {"PENDING_APPROVAL", "READY_TO_SEND", "FAILED"},
    "PENDING_APPROVAL": {"READY_TO_SEND", "CONTENT_CREATION", "FAILED"},
    "READY_TO_SEND": {"SENDING", "CANCELLED"},
    "SCHEDULED": {"COMPLIANCE_CHECK", "CANCELLED", "FAILED"},
    "SENDING": {"COMPLETED", "PAUSED", "FAILED"},
    "PAUSED": {"SENDING", "CANCELLED"},
    "COMPLETED": set(),
    "FAILED": set(),
    "CANCELLED": set(),
}


@dataclass
class BroadcastJobRepository:
    """Repository for BroadcastJob CRUD operations."""
    session: Session

    def create_broadcast_job(
        self, job_id: str, user_id: str, project_id: str, phase: str = "INITIALIZED"
    ) -> BroadcastJob:
        """Create a new broadcast job record."""
        try:
            logger.info("=" * 60)
            logger.info("BROADCAST JOB REPOSITORY - CREATE")
            logger.info(f"  job_id: {job_id}")
            logger.info(f"  user_id: {user_id}")
            logger.info(f"  project_id: {project_id}")
            logger.info(f"  phase: {phase}")

            job = BroadcastJob(
                id=job_id,
                user_id=user_id,
                project_id=project_id,
                phase=phase,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.session.add(job)
            self.session.commit()
            self.session.refresh(job)

            logger.info(f"  Broadcast job created: {job_id}")
            logger.info("=" * 60)
            return job

        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to create broadcast job: {e}")
            raise e

    def get_by_id(self, job_id: str) -> Optional[dict]:
        """Get broadcast job by ID."""
        try:
            statement = select(BroadcastJob).where(
                BroadcastJob.id == job_id,
                BroadcastJob.is_active == True
            )
            record = self.session.exec(statement).first()
            if record:
                return self._to_dict(record)
            return None
        except Exception as e:
            logger.error(f"Failed to get broadcast job {job_id}: {e}")
            raise e

    def get_active_by_user(self, user_id: str) -> List[dict]:
        """Get all active broadcast jobs for a user, most recent first."""
        try:
            statement = select(BroadcastJob).where(
                BroadcastJob.user_id == user_id,
                BroadcastJob.is_active == True,
            ).order_by(BroadcastJob.updated_at.desc())
            records = self.session.exec(statement).all()
            return [self._to_dict(r) for r in records]
        except Exception as e:
            logger.error(f"Failed to get broadcast jobs for user {user_id}: {e}")
            raise e

    def update_phase(
        self, job_id: str, new_phase: str, error_message: Optional[str] = None,
        scheduled_for: Optional[datetime] = None
    ) -> bool:
        """
        Update the broadcast phase (state transition).

        Validates transition against ALLOWED_TRANSITIONS map.
        Automatically sets timestamps for SENDING/terminal phases.
        Sets scheduled_for when transitioning to SCHEDULED.
        """
        try:
            record = self._get_record(job_id)
            if not record:
                logger.warning(f"Broadcast job not found: {job_id}")
                return False

            current_phase = record.phase
            allowed = ALLOWED_TRANSITIONS.get(current_phase, set())
            if new_phase not in allowed:
                logger.error(
                    f"Invalid transition: {current_phase} -> {new_phase}. "
                    f"Allowed: {allowed}"
                )
                return False

            record.previous_phase = current_phase
            record.phase = new_phase
            record.error_message = error_message
            record.updated_at = datetime.utcnow()

            if new_phase == "SCHEDULED" and scheduled_for:
                record.scheduled_for = scheduled_for
                logger.info(f"Broadcast {job_id}: scheduled for {scheduled_for.isoformat()}")
            if new_phase == "SENDING" and not record.started_sending_at:
                record.started_sending_at = datetime.utcnow()
            if new_phase in ("COMPLETED", "FAILED", "CANCELLED"):
                record.completed_at = datetime.utcnow()

            self.session.commit()
            logger.info(f"Broadcast {job_id}: {current_phase} -> {new_phase}")
            return True

        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update phase for {job_id}: {e}")
            raise e

    def update_contacts(
        self, job_id: str, contacts_data: str, total: int, valid: int, invalid: int
    ) -> bool:
        """Store validated contacts data (JSON string of phone numbers)."""
        try:
            record = self._get_record(job_id)
            if not record:
                return False

            record.contacts_data = contacts_data
            record.total_contacts = total
            record.valid_contacts = valid
            record.invalid_contacts = invalid
            record.updated_at = datetime.utcnow()
            self.session.commit()
            logger.info(f"Broadcast {job_id}: contacts updated (total={total}, valid={valid}, invalid={invalid})")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update contacts for {job_id}: {e}")
            raise e

    def update_template(
        self, job_id: str, template_id: str, template_name: str,
        template_language: str, template_category: str, template_status: str
    ) -> bool:
        """Store selected template info."""
        try:
            record = self._get_record(job_id)
            if not record:
                return False

            record.template_id = template_id
            record.template_name = template_name
            record.template_language = template_language
            record.template_category = template_category
            record.template_status = template_status
            record.updated_at = datetime.utcnow()
            self.session.commit()
            logger.info(f"Broadcast {job_id}: template set to {template_name} ({template_status})")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update template for {job_id}: {e}")
            raise e

    def update_compliance(
        self, job_id: str, compliance_status: str, compliance_details: Optional[str] = None
    ) -> bool:
        """Store compliance check results."""
        try:
            record = self._get_record(job_id)
            if not record:
                return False

            record.compliance_status = compliance_status
            record.compliance_details = compliance_details
            record.updated_at = datetime.utcnow()
            self.session.commit()
            logger.info(f"Broadcast {job_id}: compliance={compliance_status}")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update compliance for {job_id}: {e}")
            raise e

    def update_segments(self, job_id: str, segments_data: str) -> bool:
        """Store segmentation data (JSON string)."""
        try:
            record = self._get_record(job_id)
            if not record:
                return False

            record.segments_data = segments_data
            record.updated_at = datetime.utcnow()
            self.session.commit()
            logger.info(f"Broadcast {job_id}: segments updated")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update segments for {job_id}: {e}")
            raise e

    def update_send_progress(self, job_id: str, sent: int, failed: int) -> bool:
        """Update send progress counters."""
        try:
            record = self._get_record(job_id)
            if not record:
                return False

            record.sent_count = sent
            record.failed_count = failed
            record.pending_count = record.valid_contacts - sent - failed
            record.updated_at = datetime.utcnow()
            self.session.commit()
            logger.info(f"Broadcast {job_id}: sent={sent}, failed={failed}, pending={record.pending_count}")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update send progress for {job_id}: {e}")
            raise e

    def _get_record(self, job_id: str) -> Optional[BroadcastJob]:
        """Get raw BroadcastJob record by ID."""
        statement = select(BroadcastJob).where(BroadcastJob.id == job_id)
        return self.session.exec(statement).first()

    def _to_dict(self, record: BroadcastJob) -> dict:
        """Convert BroadcastJob record to dictionary."""
        return {
            "id": record.id,
            "user_id": record.user_id,
            "project_id": record.project_id,
            "phase": record.phase,
            "previous_phase": record.previous_phase,
            "contacts_data": record.contacts_data,
            "total_contacts": record.total_contacts,
            "valid_contacts": record.valid_contacts,
            "invalid_contacts": record.invalid_contacts,
            "compliance_status": record.compliance_status,
            "segments_data": record.segments_data,
            "template_id": record.template_id,
            "template_name": record.template_name,
            "template_language": record.template_language,
            "template_category": record.template_category,
            "template_status": record.template_status,
            "sent_count": record.sent_count,
            "delivered_count": record.delivered_count,
            "failed_count": record.failed_count,
            "pending_count": record.pending_count,
            "error_message": record.error_message,
            "scheduled_for": record.scheduled_for.isoformat() if record.scheduled_for else None,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            "started_sending_at": record.started_sending_at.isoformat() if record.started_sending_at else None,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
            "is_active": record.is_active,
        }

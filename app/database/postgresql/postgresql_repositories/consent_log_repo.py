"""ConsentLog Repository for opt-in/opt-out audit trail management."""
from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass
from sqlmodel import Session, select
from ..models.consent_log import ConsentLog
from app import logger


@dataclass
class ConsentLogRepository:
    """Repository for ConsentLog CRUD operations."""
    session: Session

    def log_consent(
        self,
        user_id: str,
        phone_e164: str,
        action: str,
        source: str = "",
        keyword: str = None,
        ip_address: str = None,
        consent_text: str = None,
        broadcast_job_id: str = None,
    ) -> ConsentLog:
        """
        Log a consent event (opt-in, opt-out, pause, resume).

        Args:
            user_id: Business user ID
            phone_e164: Contact phone in E.164 format
            action: OPT_IN, OPT_OUT, PAUSE, RESUME, OPT_OUT_MARKETING
            source: Source of the event (website_form, keyword_stop, etc.)
            keyword: Trigger keyword if applicable (STOP, START, etc.)
            ip_address: IP address for web-based opt-ins
            consent_text: Text shown to user at opt-in time
            broadcast_job_id: Associated broadcast job if applicable

        Returns:
            Created ConsentLog record
        """
        try:
            record = ConsentLog(
                user_id=user_id,
                phone_e164=phone_e164,
                action=action,
                source=source,
                keyword=keyword,
                ip_address=ip_address,
                consent_text=consent_text,
                broadcast_job_id=broadcast_job_id,
                created_at=datetime.utcnow(),
            )
            self.session.add(record)
            self.session.commit()
            self.session.refresh(record)
            logger.info(f"Consent logged: {action} for {phone_e164} (source: {source})")
            return record
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to log consent: {e}")
            raise e

    def get_latest_consent(self, user_id: str, phone_e164: str) -> Optional[dict]:
        """Get the most recent consent action for a phone number."""
        try:
            statement = select(ConsentLog).where(
                ConsentLog.user_id == user_id,
                ConsentLog.phone_e164 == phone_e164,
            ).order_by(ConsentLog.created_at.desc())
            record = self.session.exec(statement).first()
            return self._to_dict(record) if record else None
        except Exception as e:
            logger.error(f"Failed to get latest consent for {phone_e164}: {e}")
            raise e

    def is_opted_in(self, user_id: str, phone_e164: str) -> bool:
        """
        Check if a phone number is currently opted in.

        Looks at the latest consent action:
        - OPT_IN or RESUME = opted in
        - OPT_OUT, PAUSE, OPT_OUT_MARKETING = not opted in
        """
        latest = self.get_latest_consent(user_id, phone_e164)
        if not latest:
            return True  # No consent record = assume opted in (manual import)
        return latest["action"] in ("OPT_IN", "RESUME")

    def get_opted_out_phones(self, user_id: str) -> set:
        """Get set of all currently opted-out phone numbers for a user."""
        try:
            # Get the latest action per phone using a subquery approach
            statement = select(ConsentLog).where(
                ConsentLog.user_id == user_id,
            ).order_by(ConsentLog.phone_e164, ConsentLog.created_at.desc())

            records = self.session.exec(statement).all()

            # Deduplicate to latest action per phone
            latest_by_phone = {}
            for r in records:
                if r.phone_e164 not in latest_by_phone:
                    latest_by_phone[r.phone_e164] = r.action

            opted_out = {
                phone for phone, action in latest_by_phone.items()
                if action in ("OPT_OUT", "PAUSE", "OPT_OUT_MARKETING")
            }
            return opted_out
        except Exception as e:
            logger.error(f"Failed to get opted-out phones: {e}")
            raise e

    def get_audit_trail(self, user_id: str, phone_e164: str) -> List[dict]:
        """Get complete consent history for a phone number."""
        try:
            statement = select(ConsentLog).where(
                ConsentLog.user_id == user_id,
                ConsentLog.phone_e164 == phone_e164,
            ).order_by(ConsentLog.created_at.desc())
            records = self.session.exec(statement).all()
            return [self._to_dict(r) for r in records]
        except Exception as e:
            logger.error(f"Failed to get audit trail for {phone_e164}: {e}")
            raise e

    def _to_dict(self, record: ConsentLog) -> dict:
        return {
            "id": record.id,
            "user_id": record.user_id,
            "phone_e164": record.phone_e164,
            "action": record.action,
            "source": record.source,
            "keyword": record.keyword,
            "ip_address": record.ip_address,
            "consent_text": record.consent_text,
            "broadcast_job_id": record.broadcast_job_id,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }

"""SuppressionList Repository for managing excluded phone numbers."""
from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass
from sqlmodel import Session, select
from ..models.suppression_list import SuppressionList
from app import logger


@dataclass
class SuppressionListRepository:
    """Repository for SuppressionList CRUD operations."""
    session: Session

    def add(
        self,
        user_id: str,
        phone_e164: str,
        suppression_type: str,
        reason: str = None,
        broadcast_job_id: str = None,
        expires_at: datetime = None,
    ) -> SuppressionList:
        """
        Add a phone number to the suppression list.

        Args:
            user_id: Business user ID
            phone_e164: Phone in E.164 format
            suppression_type: global, campaign, temporary, bounce, competitor
            reason: Why this number is suppressed
            broadcast_job_id: For campaign-specific suppression
            expires_at: For temporary suppression (e.g., PAUSE = 30 days)

        Returns:
            Created SuppressionList record
        """
        try:
            # Check if already suppressed with same type
            existing = self._get_active(user_id, phone_e164, suppression_type)
            if existing:
                logger.info(f"Already suppressed: {phone_e164} ({suppression_type})")
                return existing

            record = SuppressionList(
                user_id=user_id,
                phone_e164=phone_e164,
                suppression_type=suppression_type,
                reason=reason,
                broadcast_job_id=broadcast_job_id,
                expires_at=expires_at,
                created_at=datetime.utcnow(),
                is_active=True,
            )
            self.session.add(record)
            self.session.commit()
            self.session.refresh(record)
            logger.info(f"Suppression added: {phone_e164} ({suppression_type})")
            return record
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to add suppression: {e}")
            raise e

    def remove(self, user_id: str, phone_e164: str, suppression_type: str = None) -> bool:
        """
        Remove a phone from suppression (deactivate).

        Args:
            user_id: Business user ID
            phone_e164: Phone in E.164 format
            suppression_type: If specified, only remove this type. Otherwise remove all.

        Returns:
            True if any records were deactivated
        """
        try:
            if suppression_type:
                records = [self._get_active(user_id, phone_e164, suppression_type)]
                records = [r for r in records if r]
            else:
                statement = select(SuppressionList).where(
                    SuppressionList.user_id == user_id,
                    SuppressionList.phone_e164 == phone_e164,
                    SuppressionList.is_active == True,
                )
                records = list(self.session.exec(statement).all())

            if not records:
                return False

            for r in records:
                r.is_active = False
            self.session.commit()
            logger.info(f"Suppression removed: {phone_e164} ({len(records)} records)")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to remove suppression: {e}")
            raise e

    def get_suppressed_phones(self, user_id: str, suppression_types: list = None) -> set:
        """
        Get all actively suppressed phone numbers for a user.

        Args:
            user_id: Business user ID
            suppression_types: Filter by types (default: all types)

        Returns:
            Set of E.164 phone numbers that are suppressed
        """
        try:
            now = datetime.utcnow()
            statement = select(SuppressionList.phone_e164).where(
                SuppressionList.user_id == user_id,
                SuppressionList.is_active == True,
            )

            if suppression_types:
                statement = statement.where(
                    SuppressionList.suppression_type.in_(suppression_types)
                )

            records = self.session.exec(statement).all()

            # Filter out expired temporary suppressions
            result = set()
            for phone in records:
                result.add(phone)

            # Also clean up expired temporary suppressions
            self._cleanup_expired(user_id, now)

            return result
        except Exception as e:
            logger.error(f"Failed to get suppressed phones: {e}")
            raise e

    def is_suppressed(self, user_id: str, phone_e164: str) -> bool:
        """Check if a phone number is currently suppressed."""
        try:
            now = datetime.utcnow()
            statement = select(SuppressionList).where(
                SuppressionList.user_id == user_id,
                SuppressionList.phone_e164 == phone_e164,
                SuppressionList.is_active == True,
            )
            records = self.session.exec(statement).all()

            for r in records:
                # Temporary suppressions may have expired
                if r.suppression_type == "temporary" and r.expires_at and r.expires_at < now:
                    r.is_active = False
                    continue
                return True

            self.session.commit()
            return False
        except Exception as e:
            logger.error(f"Failed to check suppression for {phone_e164}: {e}")
            raise e

    def get_suppression_summary(self, user_id: str) -> dict:
        """Get a summary of suppression list counts by type."""
        try:
            statement = select(SuppressionList).where(
                SuppressionList.user_id == user_id,
                SuppressionList.is_active == True,
            )
            records = self.session.exec(statement).all()

            counts = {}
            for r in records:
                counts[r.suppression_type] = counts.get(r.suppression_type, 0) + 1

            return {
                "total": len(records),
                "by_type": counts,
            }
        except Exception as e:
            logger.error(f"Failed to get suppression summary: {e}")
            raise e

    def bulk_add_bounce(self, user_id: str, phones: list, reason: str = "delivery_failed") -> int:
        """Bulk add phone numbers to bounce suppression list."""
        try:
            count = 0
            for phone in phones:
                existing = self._get_active(user_id, phone, "bounce")
                if not existing:
                    record = SuppressionList(
                        user_id=user_id,
                        phone_e164=phone,
                        suppression_type="bounce",
                        reason=reason,
                        created_at=datetime.utcnow(),
                        is_active=True,
                    )
                    self.session.add(record)
                    count += 1
            self.session.commit()
            logger.info(f"Bulk bounce suppression: {count} phones added")
            return count
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to bulk add bounce: {e}")
            raise e

    def _get_active(self, user_id: str, phone_e164: str, suppression_type: str) -> Optional[SuppressionList]:
        """Get active suppression record for a phone and type."""
        statement = select(SuppressionList).where(
            SuppressionList.user_id == user_id,
            SuppressionList.phone_e164 == phone_e164,
            SuppressionList.suppression_type == suppression_type,
            SuppressionList.is_active == True,
        )
        return self.session.exec(statement).first()

    def _cleanup_expired(self, user_id: str, now: datetime):
        """Deactivate expired temporary suppressions."""
        statement = select(SuppressionList).where(
            SuppressionList.user_id == user_id,
            SuppressionList.suppression_type == "temporary",
            SuppressionList.is_active == True,
            SuppressionList.expires_at != None,
            SuppressionList.expires_at < now,
        )
        expired = self.session.exec(statement).all()
        for r in expired:
            r.is_active = False
        if expired:
            self.session.commit()
            logger.info(f"Cleaned up {len(expired)} expired temporary suppressions")

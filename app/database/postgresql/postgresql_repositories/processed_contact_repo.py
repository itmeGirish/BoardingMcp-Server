"""ProcessedContact Repository for bulk contact storage and retrieval."""
from __future__ import annotations
from typing import List
from datetime import datetime
from dataclasses import dataclass
from sqlmodel import Session, select, func
from ..models.processed_contact import ProcessedContact
from app import logger


@dataclass
class ProcessedContactRepository:
    """Repository for ProcessedContact CRUD operations."""
    session: Session

    def bulk_create(
        self,
        contacts: list,
        broadcast_job_id: str,
        user_id: str,
    ) -> int:
        """
        Bulk insert processed contacts into the database.

        Args:
            contacts: List of dicts with keys: phone_e164, name, email,
                      country_code, quality_score, custom_fields, source_row,
                      validation_errors, is_duplicate, duplicate_of
            broadcast_job_id: The broadcast job these contacts belong to
            user_id: User who owns this broadcast

        Returns:
            int: Number of records created
        """
        try:
            logger.info(f"Bulk inserting {len(contacts)} processed contacts for job {broadcast_job_id}")

            records = []
            for c in contacts:
                record = ProcessedContact(
                    broadcast_job_id=broadcast_job_id,
                    user_id=user_id,
                    phone_e164=c.get("phone_e164", ""),
                    name=c.get("name"),
                    email=c.get("email"),
                    country_code=c.get("country_code", ""),
                    quality_score=c.get("quality_score", 0),
                    custom_fields=c.get("custom_fields"),
                    source_row=c.get("source_row"),
                    validation_errors=c.get("validation_errors"),
                    is_duplicate=c.get("is_duplicate", False),
                    duplicate_of=c.get("duplicate_of"),
                    created_at=datetime.utcnow(),
                )
                records.append(record)

            self.session.add_all(records)
            self.session.commit()

            logger.info(f"Successfully inserted {len(records)} processed contacts")
            return len(records)

        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to bulk insert processed contacts: {e}")
            raise e

    def get_by_broadcast_job(self, broadcast_job_id: str) -> List[dict]:
        """Get all processed contacts for a broadcast job."""
        try:
            statement = select(ProcessedContact).where(
                ProcessedContact.broadcast_job_id == broadcast_job_id
            ).order_by(ProcessedContact.source_row)
            records = self.session.exec(statement).all()
            return [self._to_dict(r) for r in records]
        except Exception as e:
            logger.error(f"Failed to get contacts for job {broadcast_job_id}: {e}")
            raise e

    def get_valid_phones_by_job(self, broadcast_job_id: str) -> List[str]:
        """
        Get list of valid (non-duplicate) E.164 phone numbers for a broadcast job.

        Returns:
            List of E.164 phone strings ready for sending
        """
        try:
            statement = select(ProcessedContact.phone_e164).where(
                ProcessedContact.broadcast_job_id == broadcast_job_id,
                ProcessedContact.is_duplicate == False,
                ProcessedContact.phone_e164 != "",
            )
            records = self.session.exec(statement).all()
            return list(records)
        except Exception as e:
            logger.error(f"Failed to get valid phones for job {broadcast_job_id}: {e}")
            raise e

    def get_quality_summary(self, broadcast_job_id: str) -> dict:
        """
        Get quality score summary/distribution for a broadcast job.

        Returns:
            dict with keys: total, avg_score, high_count, medium_count,
            low_count, duplicate_count, country_breakdown
        """
        try:
            statement = select(ProcessedContact).where(
                ProcessedContact.broadcast_job_id == broadcast_job_id
            )
            records = self.session.exec(statement).all()

            if not records:
                return {
                    "total": 0, "avg_score": 0,
                    "high_count": 0, "medium_count": 0, "low_count": 0,
                    "duplicate_count": 0, "country_breakdown": {},
                }

            scores = [r.quality_score for r in records if not r.is_duplicate]
            countries = {}
            dup_count = 0

            for r in records:
                if r.is_duplicate:
                    dup_count += 1
                else:
                    cc = r.country_code or "UNKNOWN"
                    countries[cc] = countries.get(cc, 0) + 1

            avg_score = sum(scores) / len(scores) if scores else 0

            return {
                "total": len(records),
                "valid_count": len(scores),
                "avg_score": round(avg_score, 1),
                "high_count": sum(1 for s in scores if s >= 70),
                "medium_count": sum(1 for s in scores if 40 <= s < 70),
                "low_count": sum(1 for s in scores if s < 40),
                "duplicate_count": dup_count,
                "country_breakdown": countries,
            }

        except Exception as e:
            logger.error(f"Failed to get quality summary for job {broadcast_job_id}: {e}")
            raise e

    def _to_dict(self, record: ProcessedContact) -> dict:
        """Convert ProcessedContact record to dictionary."""
        return {
            "id": record.id,
            "broadcast_job_id": record.broadcast_job_id,
            "user_id": record.user_id,
            "phone_e164": record.phone_e164,
            "name": record.name,
            "email": record.email,
            "country_code": record.country_code,
            "quality_score": record.quality_score,
            "custom_fields": record.custom_fields,
            "source_row": record.source_row,
            "validation_errors": record.validation_errors,
            "is_duplicate": record.is_duplicate,
            "duplicate_of": record.duplicate_of,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }

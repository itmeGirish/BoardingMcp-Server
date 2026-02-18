"""Repository for VerifiedCitation operations (citation tracking and dedup).

The verified_citations table is a global citation store (no session_id).
Citations are looked up by citation_hash for dedup and verification.
"""
from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass
from sqlmodel import Session, select
from ...models.drafting import VerifiedCitation
from app import logger


@dataclass
class VerifiedCitationRepository:
    """Repository for storing and retrieving verified legal citations."""
    session: Session

    def create(
        self,
        citation_id: str,
        citation_text: str,
        case_name: str,
        citation_hash: str,
        year: Optional[int] = None,
        court: Optional[str] = None,
        holding: Optional[str] = None,
        source_db: Optional[str] = None,
        source_url: Optional[str] = None,
        verified: bool = True,
    ) -> VerifiedCitation:
        """Create a new verified citation record.

        Args:
            citation_id:   UUID primary key.
            citation_text: Full citation string.
            case_name:     Case name (e.g. "Smith v Jones").
            citation_hash: Unique hash for dedup (SHA-256 of citation_text).
            year:          Year of the citation.
            court:         Court name.
            holding:       Summary of the holding.
            source_db:     Name of the source database (e.g. "SCC Online").
            source_url:    URL to the source.
            verified:      If True, sets verified_at to now.
        """
        try:
            citation = VerifiedCitation(
                id=citation_id,
                citation_text=citation_text,
                case_name=case_name,
                citation_hash=citation_hash,
                year=year,
                court=court,
                holding=holding,
                source_db=source_db,
                source_url=source_url,
                verified_at=datetime.now() if verified else None,
            )
            self.session.add(citation)
            self.session.commit()
            self.session.refresh(citation)
            logger.info(f"[VerifiedCitation] Created citation {citation_id} (hash={citation_hash})")
            return citation
        except Exception as e:
            self.session.rollback()
            logger.error(f"[VerifiedCitation] Failed to create citation: {e}")
            raise

    def get_all_verified(self) -> List[dict]:
        """Get all verified citations (verified_at is not null)."""
        try:
            statement = select(VerifiedCitation).where(
                VerifiedCitation.verified_at.isnot(None),
            ).order_by(VerifiedCitation.verified_at)
            records = self.session.exec(statement).all()
            return [self._to_dict(r) for r in records]
        except Exception as e:
            logger.error(f"[VerifiedCitation] Failed to get verified citations: {e}")
            raise

    def get_all_hashes(self) -> set[str]:
        """Get all verified citation hashes as a set (for hash-based lookup)."""
        try:
            statement = select(VerifiedCitation.citation_hash).where(
                VerifiedCitation.verified_at.isnot(None),
            )
            rows = self.session.exec(statement).all()
            return set(rows)
        except Exception as e:
            logger.error(f"[VerifiedCitation] Failed to get citation hashes: {e}")
            raise

    def verify_by_hash(self, verification_hash: str) -> Optional[dict]:
        """Lookup a citation by its verification hash."""
        try:
            statement = select(VerifiedCitation).where(
                VerifiedCitation.citation_hash == verification_hash
            )
            record = self.session.exec(statement).first()
            if record:
                return self._to_dict(record)
            return None
        except Exception as e:
            logger.error(f"[VerifiedCitation] Failed to verify by hash {verification_hash}: {e}")
            raise

    def mark_verified(self, citation_id: str) -> bool:
        """Mark a citation as verified by setting verified_at timestamp."""
        try:
            statement = select(VerifiedCitation).where(VerifiedCitation.id == citation_id)
            record = self.session.exec(statement).first()
            if not record:
                return False
            record.verified_at = datetime.now()
            self.session.commit()
            logger.info(f"[VerifiedCitation] Marked citation {citation_id} as verified")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"[VerifiedCitation] Failed to mark citation verified: {e}")
            raise

    def get_by_hash(self, verification_hash: str) -> Optional[dict]:
        """Find a citation by its verification hash."""
        try:
            statement = select(VerifiedCitation).where(
                VerifiedCitation.citation_hash == verification_hash
            )
            record = self.session.exec(statement).first()
            if record:
                return self._to_dict(record)
            return None
        except Exception as e:
            logger.error(f"[VerifiedCitation] Failed to get citation by hash {verification_hash}: {e}")
            raise

    def _to_dict(self, record: VerifiedCitation) -> dict:
        """Convert a VerifiedCitation ORM record to a dict."""
        return {
            "id": record.id,
            "citation_text": record.citation_text,
            "case_name": record.case_name,
            "year": record.year,
            "court": record.court,
            "holding": record.holding,
            "citation_hash": record.citation_hash,
            "source_db": record.source_db,
            "source_url": record.source_url,
            "verified_at": record.verified_at.isoformat() if record.verified_at else None,
        }

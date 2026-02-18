"""Repository for DraftVersion operations (versioned draft tracking)."""
from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass
from sqlmodel import Session, select
from ...models.drafting import DraftVersion
from app import logger


@dataclass
class DraftVersionRepository:
    """Repository for storing and retrieving versioned draft outputs."""
    session: Session

    def create(
        self,
        version_id: str,
        session_id: str,
        version_number: int,
        draft_content: str,
        quality_score: Optional[float] = None,
        court_readiness: Optional[str] = None,
        word_count: Optional[int] = None,
        agent_name: Optional[str] = None,
    ) -> DraftVersion:
        """Create a new draft version record."""
        try:
            version = DraftVersion(
                id=version_id,
                session_id=session_id,
                version_number=version_number,
                draft_content=draft_content,
                quality_score=quality_score,
                court_readiness=court_readiness,
                word_count=word_count,
                generated_by=agent_name,
                created_at=datetime.now(),
            )
            self.session.add(version)
            self.session.commit()
            self.session.refresh(version)
            logger.info(
                f"[DraftVersion] Created version {version_number} for session {session_id}"
            )
            return version
        except Exception as e:
            self.session.rollback()
            logger.error(f"[DraftVersion] Failed to create version: {e}")
            raise

    def get_by_session(self, session_id: str) -> List[dict]:
        """Get all draft versions for a session, ordered by version number."""
        try:
            statement = select(DraftVersion).where(
                DraftVersion.session_id == session_id
            ).order_by(DraftVersion.version_number)
            records = self.session.exec(statement).all()
            return [
                {
                    "id": r.id,
                    "session_id": r.session_id,
                    "version_number": r.version_number,
                    "draft_content": r.draft_content,
                    "quality_score": r.quality_score,
                    "court_readiness": r.court_readiness,
                    "generated_by": r.generated_by,
                    "word_count": r.word_count,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]
        except Exception as e:
            logger.error(f"[DraftVersion] Failed to get versions for session {session_id}: {e}")
            raise

    def get_latest(self, session_id: str) -> Optional[dict]:
        """Get the latest draft version for a session (highest version_number)."""
        try:
            statement = select(DraftVersion).where(
                DraftVersion.session_id == session_id
            ).order_by(DraftVersion.version_number.desc())
            record = self.session.exec(statement).first()
            if record:
                return {
                    "id": record.id,
                    "session_id": record.session_id,
                    "version_number": record.version_number,
                    "draft_content": record.draft_content,
                    "quality_score": record.quality_score,
                    "court_readiness": record.court_readiness,
                    "generated_by": record.generated_by,
                    "word_count": record.word_count,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                }
            return None
        except Exception as e:
            logger.error(f"[DraftVersion] Failed to get latest version for session {session_id}: {e}")
            raise

    def get_by_id(self, version_id: str) -> Optional[dict]:
        """Get a single draft version by its ID."""
        try:
            statement = select(DraftVersion).where(DraftVersion.id == version_id)
            record = self.session.exec(statement).first()
            if record:
                return {
                    "id": record.id,
                    "session_id": record.session_id,
                    "version_number": record.version_number,
                    "draft_content": record.draft_content,
                    "quality_score": record.quality_score,
                    "court_readiness": record.court_readiness,
                    "generated_by": record.generated_by,
                    "word_count": record.word_count,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                }
            return None
        except Exception as e:
            logger.error(f"[DraftVersion] Failed to get version {version_id}: {e}")
            raise

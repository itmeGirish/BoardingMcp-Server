"""Repository for DraftingSession CRUD and phase transitions."""
from __future__ import annotations
from typing import Optional
from datetime import datetime
from dataclasses import dataclass
from sqlmodel import Session, select
from ...models.drafting import DraftingSession
from app import logger


# Valid phase transitions (18-step pipeline)
VALID_TRANSITIONS = {
    "INITIALIZED": ["SECURITY", "FAILED"],
    "SECURITY": ["INTAKE", "FAILED"],
    "INTAKE": ["FACT_VALIDATION", "FAILED"],
    "FACT_VALIDATION": ["CLASSIFICATION", "PAUSED", "FAILED"],
    "CLASSIFICATION": ["ROUTE_RESOLUTION", "FAILED"],
    "ROUTE_RESOLUTION": ["CLARIFICATION", "FAILED"],
    "CLARIFICATION": ["TEMPLATE_PACK", "PAUSED", "FAILED"],
    "TEMPLATE_PACK": ["PARALLEL_AGENTS", "FAILED"],
    "PARALLEL_AGENTS": ["OPTIONAL_AGENTS", "FAILED"],
    "OPTIONAL_AGENTS": ["CITATION_VALIDATION", "FAILED"],
    "CITATION_VALIDATION": ["CONTEXT_MERGE", "FAILED"],
    "CONTEXT_MERGE": ["DRAFTING", "PAUSED", "FAILED"],
    "DRAFTING": ["REVIEW", "FAILED"],
    "REVIEW": ["STAGING_RULES", "FAILED"],
    "STAGING_RULES": ["PROMOTION", "FAILED"],
    "PROMOTION": ["EXPORT", "FAILED"],
    "EXPORT": ["COMPLETED", "FAILED"],
    "COMPLETED": [],
    "PAUSED": [
        "SECURITY", "INTAKE", "FACT_VALIDATION", "CLASSIFICATION",
        "ROUTE_RESOLUTION", "CLARIFICATION", "TEMPLATE_PACK",
        "PARALLEL_AGENTS", "OPTIONAL_AGENTS", "CITATION_VALIDATION",
        "CONTEXT_MERGE", "DRAFTING", "REVIEW", "STAGING_RULES",
        "PROMOTION", "EXPORT", "FAILED",
    ],
    "FAILED": ["INITIALIZED"],
}


@dataclass
class DraftingSessionRepository:
    """Repository for DraftingSession operations."""
    session: Session

    def create(
        self,
        session_id: str,
        user_id: str,
        document_type: Optional[str] = None,
    ) -> DraftingSession:
        """Create a new drafting session in INITIALIZED phase."""
        try:
            drafting_session = DraftingSession(
                id=session_id,
                user_id=user_id,
                phase="INITIALIZED",
                document_type=document_type,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                is_active=True,
            )
            self.session.add(drafting_session)
            self.session.commit()
            self.session.refresh(drafting_session)
            logger.info(f"[DraftingSession] Created session {session_id} for user {user_id}")
            return drafting_session
        except Exception as e:
            self.session.rollback()
            logger.error(f"[DraftingSession] Failed to create session: {e}")
            raise

    def get_by_id(self, session_id: str) -> Optional[dict]:
        """Get drafting session by ID."""
        try:
            statement = select(DraftingSession).where(
                DraftingSession.id == session_id,
                DraftingSession.is_active == True,
            )
            record = self.session.exec(statement).first()
            if record:
                return {
                    "id": record.id,
                    "user_id": record.user_id,
                    "phase": record.phase,
                    "previous_phase": record.previous_phase,
                    "document_type": record.document_type,
                    "jurisdiction": record.jurisdiction,
                    "court_type": record.court_type,
                    "case_category": record.case_category,
                    "case_title": record.case_title,
                    "draft_content": record.draft_content,
                    "error_message": record.error_message,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                    "updated_at": record.updated_at.isoformat() if record.updated_at else None,
                }
            return None
        except Exception as e:
            logger.error(f"[DraftingSession] Failed to get session {session_id}: {e}")
            raise

    def update_phase(
        self,
        session_id: str,
        new_phase: str,
        error_message: Optional[str] = None,
    ) -> bool:
        """Update session phase with transition validation."""
        try:
            statement = select(DraftingSession).where(
                DraftingSession.id == session_id,
                DraftingSession.is_active == True,
            )
            record = self.session.exec(statement).first()
            if not record:
                logger.warning(f"[DraftingSession] Session {session_id} not found")
                return False

            # Validate transition
            allowed = VALID_TRANSITIONS.get(record.phase, [])
            if new_phase not in allowed:
                logger.warning(
                    f"[DraftingSession] Invalid transition {record.phase} -> {new_phase}. "
                    f"Allowed: {allowed}"
                )
                return False

            record.previous_phase = record.phase
            record.phase = new_phase
            record.error_message = error_message
            record.updated_at = datetime.now()

            self.session.commit()
            logger.info(f"[DraftingSession] Phase updated: {record.previous_phase} -> {new_phase}")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"[DraftingSession] Failed to update phase: {e}")
            raise

    def update_metadata(
        self,
        session_id: str,
        jurisdiction: Optional[str] = None,
        court_type: Optional[str] = None,
        case_category: Optional[str] = None,
        case_title: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> bool:
        """Update session metadata (jurisdiction, court, etc.)."""
        try:
            statement = select(DraftingSession).where(
                DraftingSession.id == session_id,
                DraftingSession.is_active == True,
            )
            record = self.session.exec(statement).first()
            if not record:
                return False

            if jurisdiction is not None:
                record.jurisdiction = jurisdiction
            if court_type is not None:
                record.court_type = court_type
            if case_category is not None:
                record.case_category = case_category
            if case_title is not None:
                record.case_title = case_title
            if document_type is not None:
                record.document_type = document_type
            record.updated_at = datetime.now()

            self.session.commit()
            logger.info(f"[DraftingSession] Metadata updated for session {session_id}")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"[DraftingSession] Failed to update metadata: {e}")
            raise

    def save_draft(self, session_id: str, draft_content: str) -> bool:
        """Save generated draft content."""
        try:
            statement = select(DraftingSession).where(
                DraftingSession.id == session_id,
                DraftingSession.is_active == True,
            )
            record = self.session.exec(statement).first()
            if not record:
                return False

            record.draft_content = draft_content
            record.updated_at = datetime.now()
            self.session.commit()
            logger.info(f"[DraftingSession] Draft saved for session {session_id}")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"[DraftingSession] Failed to save draft: {e}")
            raise

    def pause_session(self, session_id: str, reason: str = None) -> bool:
        """Pause a session (set phase=PAUSED, persist reason)."""
        try:
            statement = select(DraftingSession).where(
                DraftingSession.id == session_id,
                DraftingSession.is_active == True,
            )
            record = self.session.exec(statement).first()
            if not record:
                return False

            record.previous_phase = record.phase
            record.phase = "PAUSED"
            record.error_message = reason or f"Paused from {record.previous_phase}"
            record.updated_at = datetime.now()

            self.session.commit()
            logger.info(
                f"[DraftingSession] Session {session_id} paused "
                f"(was {record.previous_phase}): {reason}"
            )
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"[DraftingSession] Failed to pause session: {e}")
            raise

    def resume_session(self, session_id: str, resume_to_phase: str = None) -> bool:
        """Resume a paused session. Defaults to resuming from previous_phase."""
        try:
            statement = select(DraftingSession).where(
                DraftingSession.id == session_id,
                DraftingSession.is_active == True,
            )
            record = self.session.exec(statement).first()
            if not record:
                return False
            if record.phase != "PAUSED":
                logger.warning(
                    f"[DraftingSession] Session {session_id} is not paused "
                    f"(phase={record.phase})"
                )
                return False

            target = resume_to_phase or record.previous_phase or "CLARIFICATION"
            record.previous_phase = "PAUSED"
            record.phase = target
            record.error_message = None
            record.updated_at = datetime.now()

            self.session.commit()
            logger.info(
                f"[DraftingSession] Session {session_id} resumed to {target}"
            )
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"[DraftingSession] Failed to resume session: {e}")
            raise

    def get_active_by_user(self, user_id: str) -> Optional[dict]:
        """Get the most recent active session for a user."""
        try:
            statement = select(DraftingSession).where(
                DraftingSession.user_id == user_id,
                DraftingSession.is_active == True,
            ).order_by(DraftingSession.updated_at.desc())
            record = self.session.exec(statement).first()
            if record:
                return self.get_by_id(record.id)
            return None
        except Exception as e:
            logger.error(f"[DraftingSession] Failed to get active session for user {user_id}: {e}")
            raise

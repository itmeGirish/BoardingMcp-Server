"""Repository for ClarificationHistory operations (intake Q&A tracking)."""
from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass
from sqlmodel import Session, select
from sqlalchemy import func
from ...models.drafting import ClarificationHistory
from app import logger


@dataclass
class ClarificationHistoryRepository:
    """Repository for recording and retrieving clarification Q&A exchanges."""
    session: Session

    def create(
        self,
        clarification_id: str,
        session_id: str,
        question: str,
        field_name: str,
        asked_at: Optional[datetime] = None,
    ) -> ClarificationHistory:
        """Record a clarification question asked during intake."""
        try:
            # Auto-increment step_number per session
            count_stmt = select(func.count(ClarificationHistory.id)).where(
                ClarificationHistory.session_id == session_id
            )
            current_count = self.session.exec(count_stmt).one()
            step_number = current_count + 1

            clarification = ClarificationHistory(
                id=clarification_id,
                session_id=session_id,
                step_number=step_number,
                questions={"question": question, "field_name": field_name},
                user_responses=None,
                asked_at=asked_at or datetime.now(),
                responded_at=None,
            )
            self.session.add(clarification)
            self.session.commit()
            self.session.refresh(clarification)
            logger.info(
                f"[ClarificationHistory] Recorded question for field '{field_name}' "
                f"in session {session_id}"
            )
            return clarification
        except Exception as e:
            self.session.rollback()
            logger.error(f"[ClarificationHistory] Failed to create clarification: {e}")
            raise

    def record_response(
        self,
        clarification_id: str,
        response: str,
        responded_at: Optional[datetime] = None,
    ) -> bool:
        """Record the user's response to a clarification question."""
        try:
            statement = select(ClarificationHistory).where(
                ClarificationHistory.id == clarification_id
            )
            record = self.session.exec(statement).first()
            if not record:
                logger.error(
                    f"[ClarificationHistory] Clarification {clarification_id} not found"
                )
                return False
            record.user_responses = {"response": response}
            record.responded_at = responded_at or datetime.now()
            self.session.commit()
            logger.info(
                f"[ClarificationHistory] Response recorded for clarification {clarification_id}"
            )
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"[ClarificationHistory] Failed to record response: {e}")
            raise

    def get_pending(self, session_id: str) -> List[dict]:
        """Get all unanswered clarifications for a session."""
        try:
            statement = select(ClarificationHistory).where(
                ClarificationHistory.session_id == session_id,
                ClarificationHistory.responded_at.is_(None),
            ).order_by(ClarificationHistory.asked_at)
            records = self.session.exec(statement).all()
            return [
                {
                    "id": r.id,
                    "session_id": r.session_id,
                    "step_number": r.step_number,
                    "questions": r.questions,
                    "asked_at": r.asked_at.isoformat() if r.asked_at else None,
                }
                for r in records
            ]
        except Exception as e:
            logger.error(
                f"[ClarificationHistory] Failed to get pending clarifications "
                f"for session {session_id}: {e}"
            )
            raise

    def get_by_session(self, session_id: str) -> List[dict]:
        """Get all clarifications (answered and unanswered) for a session."""
        try:
            statement = select(ClarificationHistory).where(
                ClarificationHistory.session_id == session_id
            ).order_by(ClarificationHistory.asked_at)
            records = self.session.exec(statement).all()
            return [
                {
                    "id": r.id,
                    "session_id": r.session_id,
                    "step_number": r.step_number,
                    "questions": r.questions,
                    "user_responses": r.user_responses,
                    "asked_at": r.asked_at.isoformat() if r.asked_at else None,
                    "responded_at": r.responded_at.isoformat() if r.responded_at else None,
                }
                for r in records
            ]
        except Exception as e:
            logger.error(
                f"[ClarificationHistory] Failed to get clarifications "
                f"for session {session_id}: {e}"
            )
            raise

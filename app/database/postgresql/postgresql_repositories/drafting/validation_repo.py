"""Repository for DraftingValidation CRUD operations (gate results)."""
from __future__ import annotations
from typing import List
from datetime import datetime
from dataclasses import dataclass
from sqlmodel import Session, select
from ...models.drafting import DraftingValidation
from app import logger


@dataclass
class ValidationRepository:
    """Repository for storing and retrieving validation gate results."""
    session: Session

    def create(
        self,
        validation_id: str,
        session_id: str,
        gate_name: str,
        passed: bool,
        details: str = None,
    ) -> DraftingValidation:
        """Record a gate validation result."""
        try:
            validation = DraftingValidation(
                id=validation_id,
                session_id=session_id,
                gate_name=gate_name,
                passed=passed,
                details=details,
                created_at=datetime.now(),
            )
            self.session.add(validation)
            self.session.commit()
            self.session.refresh(validation)
            status = "PASSED" if passed else "FAILED"
            logger.info(f"[Validation] Gate {gate_name} {status} for session {session_id}")
            return validation
        except Exception as e:
            self.session.rollback()
            logger.error(f"[Validation] Failed to record gate result: {e}")
            raise

    def get_by_session(self, session_id: str) -> List[dict]:
        """Get all validation results for a session."""
        try:
            statement = select(DraftingValidation).where(
                DraftingValidation.session_id == session_id
            ).order_by(DraftingValidation.created_at)
            records = self.session.exec(statement).all()
            return [
                {
                    "id": r.id,
                    "gate_name": r.gate_name,
                    "passed": r.passed,
                    "details": r.details,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]
        except Exception as e:
            logger.error(f"[Validation] Failed to get validations: {e}")
            raise

    def all_gates_passed(self, session_id: str) -> bool:
        """Check if all gates for a session have passed."""
        try:
            statement = select(DraftingValidation).where(
                DraftingValidation.session_id == session_id
            )
            records = self.session.exec(statement).all()
            if not records:
                return False
            return all(r.passed for r in records)
        except Exception as e:
            logger.error(f"[Validation] Failed to check gates: {e}")
            raise

"""Repository for DraftingFact CRUD operations."""
from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass
from sqlmodel import Session, select
from ...models.drafting import DraftingFact
from app import logger


@dataclass
class DraftingFactRepository:
    """Repository for DraftingFact operations."""
    session: Session

    def create(
        self,
        fact_id: str,
        session_id: str,
        fact_type: str,
        fact_key: str,
        fact_value: str,
        confidence: float = 0.0,
        source_doc_id: Optional[str] = None,
        source_message_idx: Optional[int] = None,
    ) -> DraftingFact:
        """Create a single fact record."""
        try:
            fact = DraftingFact(
                id=fact_id,
                session_id=session_id,
                fact_type=fact_type,
                fact_key=fact_key,
                fact_value=fact_value,
                confidence=confidence,
                source_doc_id=source_doc_id,
                source_message_idx=source_message_idx,
                is_verified=False,
                created_at=datetime.now(),
            )
            self.session.add(fact)
            self.session.commit()
            self.session.refresh(fact)
            logger.info(f"[DraftingFact] Created fact {fact_key} for session {session_id}")
            return fact
        except Exception as e:
            self.session.rollback()
            logger.error(f"[DraftingFact] Failed to create fact: {e}")
            raise

    def bulk_create(self, facts: List[dict], session_id: str) -> int:
        """Bulk insert facts for a session. Returns count of inserted facts."""
        try:
            count = 0
            for f in facts:
                fact = DraftingFact(
                    id=f["id"],
                    session_id=session_id,
                    fact_type=f["fact_type"],
                    fact_key=f["fact_key"],
                    fact_value=f["fact_value"],
                    confidence=f.get("confidence", 0.0),
                    source_doc_id=f.get("source_doc_id"),
                    source_message_idx=f.get("source_message_idx"),
                    is_verified=f.get("is_verified", False),
                    created_at=datetime.now(),
                )
                self.session.add(fact)
                count += 1
            self.session.commit()
            logger.info(f"[DraftingFact] Bulk inserted {count} facts for session {session_id}")
            return count
        except Exception as e:
            self.session.rollback()
            logger.error(f"[DraftingFact] Failed to bulk insert facts: {e}")
            raise

    def get_by_session(self, session_id: str) -> List[dict]:
        """Get all facts for a session."""
        try:
            statement = select(DraftingFact).where(
                DraftingFact.session_id == session_id
            ).order_by(DraftingFact.created_at)
            records = self.session.exec(statement).all()
            return [
                {
                    "id": r.id,
                    "session_id": r.session_id,
                    "fact_type": r.fact_type,
                    "fact_key": r.fact_key,
                    "fact_value": r.fact_value,
                    "confidence": r.confidence,
                    "source_doc_id": r.source_doc_id,
                    "source_message_idx": r.source_message_idx,
                    "is_verified": r.is_verified,
                }
                for r in records
            ]
        except Exception as e:
            logger.error(f"[DraftingFact] Failed to get facts for session {session_id}: {e}")
            raise

    def get_verified_facts(self, session_id: str, min_confidence: float = 0.75) -> List[dict]:
        """Get facts that meet the confidence threshold or have source attribution."""
        try:
            statement = select(DraftingFact).where(
                DraftingFact.session_id == session_id,
            )
            records = self.session.exec(statement).all()
            return [
                {
                    "id": r.id,
                    "fact_type": r.fact_type,
                    "fact_key": r.fact_key,
                    "fact_value": r.fact_value,
                    "confidence": r.confidence,
                    "source_doc_id": r.source_doc_id,
                    "is_verified": r.is_verified,
                }
                for r in records
                if r.confidence >= min_confidence or r.source_doc_id is not None
            ]
        except Exception as e:
            logger.error(f"[DraftingFact] Failed to get verified facts: {e}")
            raise

    def mark_verified(self, fact_id: str) -> bool:
        """Mark a fact as verified."""
        try:
            statement = select(DraftingFact).where(DraftingFact.id == fact_id)
            record = self.session.exec(statement).first()
            if not record:
                return False
            record.is_verified = True
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"[DraftingFact] Failed to mark fact verified: {e}")
            raise

"""Repository for PromotionLog operations (audit trail for promotions)."""
from __future__ import annotations
from typing import List
from datetime import datetime
from dataclasses import dataclass
import uuid
from sqlmodel import Session, select
from ...models.drafting import PromotionLog
from app import logger


@dataclass
class PromotionLogRepository:
    """Repository for recording staging -> main rule promotions."""
    session: Session

    def create(
        self,
        staging_rule_id: str,
        main_rule_id: str,
        occurrence_count_at_promotion: int,
    ) -> PromotionLog:
        """Record a promotion event."""
        try:
            log = PromotionLog(
                id=str(uuid.uuid4()),
                staging_rule_id=staging_rule_id,
                main_rule_id=main_rule_id,
                promoted_at=datetime.now(),
                occurrence_count_at_promotion=occurrence_count_at_promotion,
            )
            self.session.add(log)
            self.session.commit()
            self.session.refresh(log)
            logger.info(
                f"[PromotionLog] Recorded promotion: staging={staging_rule_id} -> main={main_rule_id}"
            )
            return log
        except Exception as e:
            self.session.rollback()
            logger.error(f"[PromotionLog] Failed to record promotion: {e}")
            raise

    def get_by_session(self, staging_rule_id: str = None, main_rule_id: str = None) -> List[dict]:
        """Get promotion logs filtered by staging or main rule ID."""
        try:
            statement = select(PromotionLog)
            if staging_rule_id:
                statement = statement.where(PromotionLog.staging_rule_id == staging_rule_id)
            if main_rule_id:
                statement = statement.where(PromotionLog.main_rule_id == main_rule_id)
            statement = statement.order_by(PromotionLog.promoted_at.desc())

            records = self.session.exec(statement).all()
            return [
                {
                    "id": r.id,
                    "staging_rule_id": r.staging_rule_id,
                    "main_rule_id": r.main_rule_id,
                    "promoted_at": r.promoted_at.isoformat() if r.promoted_at else None,
                    "occurrence_count_at_promotion": r.occurrence_count_at_promotion,
                }
                for r in records
            ]
        except Exception as e:
            logger.error(f"[PromotionLog] Failed to get logs: {e}")
            raise

"""Repository for StagingRule operations (anti-pollution pipeline)."""
from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass
import uuid
from sqlmodel import Session, select
from ...models.drafting import StagingRule
from app import logger

# Promotion threshold
PROMOTION_THRESHOLD = 3


@dataclass
class StagingRuleRepository:
    """Repository for staging rules awaiting promotion to main_rules."""
    session: Session

    def add_or_increment(
        self,
        rule_type: str,
        document_type: str,
        rule_content: str,
        jurisdiction: Optional[str] = None,
        court_type: Optional[str] = None,
        case_category: Optional[str] = None,
    ) -> dict:
        """
        Add a new staging rule or increment occurrence_count if similar exists.

        Returns dict with rule info and whether it's ready for promotion.
        """
        try:
            # Check for existing similar rule
            statement = select(StagingRule).where(
                StagingRule.rule_type == rule_type,
                StagingRule.document_type == document_type,
                StagingRule.rule_content == rule_content,
                StagingRule.is_promoted == False,
            )
            if jurisdiction:
                statement = statement.where(StagingRule.jurisdiction == jurisdiction)
            if court_type:
                statement = statement.where(StagingRule.court_type == court_type)

            existing = self.session.exec(statement).first()

            if existing:
                existing.occurrence_count += 1
                existing.last_seen_at = datetime.now()
                self.session.commit()

                ready = existing.occurrence_count >= PROMOTION_THRESHOLD
                logger.info(
                    f"[StagingRule] Incremented rule {existing.id} to count={existing.occurrence_count} "
                    f"(promotion ready: {ready})"
                )
                return {
                    "id": existing.id,
                    "occurrence_count": existing.occurrence_count,
                    "ready_for_promotion": ready,
                    "is_new": False,
                }
            else:
                rule = StagingRule(
                    id=str(uuid.uuid4()),
                    rule_type=rule_type,
                    jurisdiction=jurisdiction,
                    court_type=court_type,
                    case_category=case_category,
                    document_type=document_type,
                    rule_content=rule_content,
                    occurrence_count=1,
                    first_seen_at=datetime.now(),
                    last_seen_at=datetime.now(),
                    is_promoted=False,
                )
                self.session.add(rule)
                self.session.commit()
                self.session.refresh(rule)
                logger.info(f"[StagingRule] Created new staging rule {rule.id}")
                return {
                    "id": rule.id,
                    "occurrence_count": 1,
                    "ready_for_promotion": False,
                    "is_new": True,
                }
        except Exception as e:
            self.session.rollback()
            logger.error(f"[StagingRule] Failed to add/increment rule: {e}")
            raise

    def get_ready_for_promotion(self) -> List[StagingRule]:
        """Get all staging rules that meet the promotion threshold."""
        try:
            statement = select(StagingRule).where(
                StagingRule.occurrence_count >= PROMOTION_THRESHOLD,
                StagingRule.is_promoted == False,
            )
            return list(self.session.exec(statement).all())
        except Exception as e:
            logger.error(f"[StagingRule] Failed to get promotion-ready rules: {e}")
            raise

    def mark_promoted(self, staging_rule_id: str) -> bool:
        """Mark a staging rule as promoted."""
        try:
            statement = select(StagingRule).where(StagingRule.id == staging_rule_id)
            record = self.session.exec(statement).first()
            if not record:
                return False
            record.is_promoted = True
            self.session.commit()
            logger.info(f"[StagingRule] Marked {staging_rule_id} as promoted")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"[StagingRule] Failed to mark promoted: {e}")
            raise

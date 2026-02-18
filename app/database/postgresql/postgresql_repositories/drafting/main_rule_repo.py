"""Repository for MainRule operations (promoted patterns)."""
from __future__ import annotations
from typing import List, Optional
from dataclasses import dataclass
from sqlmodel import Session, select
from ...models.drafting import MainRule
from app import logger


@dataclass
class MainRuleRepository:
    """Repository for querying promoted legal pattern rules."""
    session: Session

    def get_rules_for_document(
        self,
        document_type: str,
        jurisdiction: Optional[str] = None,
        court_type: Optional[str] = None,
        case_category: Optional[str] = None,
    ) -> List[dict]:
        """Get applicable promoted rules for a document type + context."""
        try:
            statement = select(MainRule).where(
                MainRule.document_type == document_type,
                MainRule.is_active == True,
            )
            if jurisdiction:
                statement = statement.where(
                    (MainRule.jurisdiction == jurisdiction) | (MainRule.jurisdiction == None)
                )
            if court_type:
                statement = statement.where(
                    (MainRule.court_type == court_type) | (MainRule.court_type == None)
                )
            if case_category:
                statement = statement.where(
                    (MainRule.case_category == case_category) | (MainRule.case_category == None)
                )

            records = self.session.exec(statement).all()
            return [
                {
                    "id": r.id,
                    "rule_type": r.rule_type,
                    "jurisdiction": r.jurisdiction,
                    "court_type": r.court_type,
                    "document_type": r.document_type,
                    "rule_content": r.rule_content,
                    "occurrence_count": r.occurrence_count,
                }
                for r in records
            ]
        except Exception as e:
            logger.error(f"[MainRule] Failed to get rules: {e}")
            raise

    def create_from_promotion(
        self,
        rule_id: str,
        rule_type: str,
        document_type: str,
        rule_content: str,
        occurrence_count: int,
        jurisdiction: Optional[str] = None,
        court_type: Optional[str] = None,
        case_category: Optional[str] = None,
    ) -> MainRule:
        """Create a new main rule (called only from promotion pipeline)."""
        try:
            from datetime import datetime
            rule = MainRule(
                id=rule_id,
                rule_type=rule_type,
                jurisdiction=jurisdiction,
                court_type=court_type,
                case_category=case_category,
                document_type=document_type,
                rule_content=rule_content,
                occurrence_count=occurrence_count,
                promoted_at=datetime.now(),
                is_active=True,
            )
            self.session.add(rule)
            self.session.commit()
            self.session.refresh(rule)
            logger.info(f"[MainRule] Promoted rule {rule_id} ({rule_type})")
            return rule
        except Exception as e:
            self.session.rollback()
            logger.error(f"[MainRule] Failed to create promoted rule: {e}")
            raise

"""Repository for AgentOutput CRUD operations (audit trail)."""
from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass
from sqlmodel import Session, select
from ...models.drafting import AgentOutput
from app import logger


@dataclass
class AgentOutputRepository:
    """Repository for storing and retrieving agent intermediate outputs."""
    session: Session

    def create(
        self,
        output_id: str,
        session_id: str,
        agent_name: str,
        output_type: str,
        output_data: str,
    ) -> AgentOutput:
        """Store an agent's output for audit trail."""
        try:
            output = AgentOutput(
                id=output_id,
                session_id=session_id,
                agent_name=agent_name,
                output_type=output_type,
                output_data=output_data,
                created_at=datetime.now(),
            )
            self.session.add(output)
            self.session.commit()
            self.session.refresh(output)
            logger.info(f"[AgentOutput] Stored {agent_name}/{output_type} for session {session_id}")
            return output
        except Exception as e:
            self.session.rollback()
            logger.error(f"[AgentOutput] Failed to store output: {e}")
            raise

    def get_by_session(self, session_id: str) -> List[dict]:
        """Get all agent outputs for a session (full audit trail)."""
        try:
            statement = select(AgentOutput).where(
                AgentOutput.session_id == session_id
            ).order_by(AgentOutput.created_at)
            records = self.session.exec(statement).all()
            return [
                {
                    "id": r.id,
                    "agent_name": r.agent_name,
                    "output_type": r.output_type,
                    "output_data": r.output_data,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]
        except Exception as e:
            logger.error(f"[AgentOutput] Failed to get outputs for session {session_id}: {e}")
            raise

    def get_by_agent(self, session_id: str, agent_name: str) -> List[dict]:
        """Get outputs for a specific agent in a session."""
        try:
            statement = select(AgentOutput).where(
                AgentOutput.session_id == session_id,
                AgentOutput.agent_name == agent_name,
            ).order_by(AgentOutput.created_at)
            records = self.session.exec(statement).all()
            return [
                {
                    "id": r.id,
                    "output_type": r.output_type,
                    "output_data": r.output_data,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]
        except Exception as e:
            logger.error(f"[AgentOutput] Failed to get {agent_name} outputs: {e}")
            raise

    def get_latest_by_type(self, session_id: str, output_type: str) -> Optional[dict]:
        """Get the most recent output of a specific type for a session."""
        try:
            statement = select(AgentOutput).where(
                AgentOutput.session_id == session_id,
                AgentOutput.output_type == output_type,
            ).order_by(AgentOutput.created_at.desc())
            record = self.session.exec(statement).first()
            if record:
                return {
                    "id": record.id,
                    "agent_name": record.agent_name,
                    "output_type": record.output_type,
                    "output_data": record.output_data,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                }
            return None
        except Exception as e:
            logger.error(f"[AgentOutput] Failed to get latest {output_type}: {e}")
            raise

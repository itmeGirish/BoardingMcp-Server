# user_creation_repo.py
from __future__ import annotations
from datetime import datetime
from dataclasses import dataclass
from sqlmodel import Session
from ..models import User
from ....config.logging import logger


@dataclass
class UserCreationRepository:
    session: Session

    def create(
        self,
        id: str,
        name: str,
        email: str
    ) -> User | None:
        try:
            user = User(
                id=id,
                name=name,
                email=email,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)
            logger.info(f"User created: {id}")
            return user
        
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to create User: {e}")
            raise e



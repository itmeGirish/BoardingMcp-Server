"""Memory Repository for storing and retrieving temporary notes and runtime details."""
from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass
from sqlmodel import Session, select
from ..models import TempMemory
from app import logger


@dataclass
class MemoryRepository:
    """Repository for TempMemory (temporary_notes) CRUD operations."""
    session: Session

    def create_on_verification_success(
        self,
        user_id: str,
        business_id: str,
        project_id: str,
        jwt_token: str,
        email: Optional[str] = None,
        password: Optional[str] = None,
        base64_token: Optional[str] = None,
        verification_token: Optional[str] = None,
    ) -> TempMemory | None:
        """
        Create a new temporary_notes record after successful verification.

        This is called when verification is successful. It:
        1. Checks if a record already exists for this user/project
        2. If exists: Updates the existing record (first_broadcasting = False)
        3. If not exists: Creates new record (first_broadcasting = True)

        Args:
            user_id: User ID
            business_id: Business ID
            project_id: Project ID
            jwt_token: The generated JWT bearer token
            email: Email used for JWT token generation
            password: Password used for JWT token generation
            base64_token: Base64 encoded <email>:<password>:<projectId>
            verification_token: Optional verification token

        Returns:
            TempMemory: The created or updated record
        """
        try:
            logger.info("=" * 60)
            logger.info("MEMORY REPOSITORY - CREATE ON VERIFICATION SUCCESS")
            logger.info("=" * 60)
            logger.info(f"  user_id: {user_id}")
            logger.info(f"  business_id: {business_id}")
            logger.info(f"  project_id: {project_id}")
            logger.info(f"  email: {email}")
            logger.info(f"  base64_token: {base64_token[:30]}..." if base64_token and len(base64_token) > 30 else f"  base64_token: {base64_token}")
            logger.info(f"  jwt_token: {jwt_token[:30]}..." if jwt_token and len(jwt_token) > 30 else f"  jwt_token: {jwt_token}")

            # Check if record already exists for this user/project
            existing = self._get_existing_record(user_id, project_id)

            if existing:
                # Update existing record - this is NOT first broadcasting
                logger.info("  Existing record found - updating (first_broadcasting = False)...")
                existing.email = email
                existing.password = password
                existing.base64_token = base64_token
                existing.jwt_token = jwt_token
                existing.verification_token = verification_token
                existing.first_broadcasting = False  # Not first broadcasting anymore
                existing.broadcasting_status = True
                existing.updated_at = datetime.utcnow()
                existing.is_active = True

                self.session.add(existing)
                self.session.commit()
                self.session.refresh(existing)

                logger.info("=" * 60)
                logger.info("✓ TEMP MEMORY UPDATED (Subsequent Broadcasting)")
                logger.info(f"  - Record ID: {existing.id}")
                logger.info(f"  - first_broadcasting: False")
                logger.info(f"  - broadcasting_status: True")
                logger.info("=" * 60)

                return existing
            else:
                # Create new record - this IS first broadcasting
                logger.info("  No existing record - creating new (first_broadcasting = True)...")
                temp_memory = TempMemory(
                    user_id=user_id,
                    business_id=business_id,
                    project_id=project_id,
                    email=email,
                    password=password,
                    base64_token=base64_token,
                    jwt_token=jwt_token,
                    verification_token=verification_token,
                    first_broadcasting=True,  # First time broadcasting
                    broadcasting_status=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    is_active=True
                )

                self.session.add(temp_memory)
                self.session.commit()
                self.session.refresh(temp_memory)

                logger.info("=" * 60)
                logger.info("✓ TEMP MEMORY CREATED (First Broadcasting)")
                logger.info(f"  - Record ID: {temp_memory.id}")
                logger.info(f"  - first_broadcasting: True")
                logger.info(f"  - broadcasting_status: True")
                logger.info("=" * 60)

                return temp_memory

        except Exception as e:
            self.session.rollback()
            logger.error("=" * 60)
            logger.error("✗ TEMP MEMORY INSERT/UPDATE FAILED!")
            logger.error(f"  Error: {e}")
            logger.error("=" * 60)
            raise e

    def _get_existing_record(self, user_id: str, project_id: str) -> Optional[TempMemory]:
        """Get existing active record for a user/project combination."""
        statement = select(TempMemory).where(
            TempMemory.user_id == user_id,
            TempMemory.project_id == project_id,
            TempMemory.is_active == True
        )
        return self.session.exec(statement).first()

    def get_by_user_and_project(self, user_id: str, project_id: str) -> Optional[dict]:
        """
        Get temporary notes record by user_id and project_id.

        Args:
            user_id: User ID to search for
            project_id: Project ID to search for

        Returns:
            dict: Record details or None if not found
        """
        try:
            logger.info(f"Fetching temp memory for user_id={user_id}, project_id={project_id}")

            record = self._get_existing_record(user_id, project_id)

            if record:
                logger.info(f"✓ Temp memory found for user_id={user_id}")
                return {
                    "id": record.id,
                    "user_id": record.user_id,
                    "business_id": record.business_id,
                    "project_id": record.project_id,
                    "email": record.email,
                    "password": record.password,
                    "base64_token": record.base64_token,
                    "jwt_token": record.jwt_token,
                    "verification_token": record.verification_token,
                    "first_broadcasting": record.first_broadcasting,
                    "broadcasting_status": record.broadcasting_status,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                    "updated_at": record.updated_at.isoformat() if record.updated_at else None,
                    "is_active": record.is_active
                }

            logger.warning(f"No temp memory found for user_id={user_id}, project_id={project_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to get temp memory for user_id={user_id}, project_id={project_id}: {e}")
            raise e

    def get_by_user_id(self, user_id: str) -> Optional[dict]:
        """
        Get the most recent active temp memory for a given user_id.

        Args:
            user_id: User ID to search for

        Returns:
            dict: Record details or None if not found
        """
        try:
            logger.info(f"Fetching temp memory for user_id={user_id}")

            statement = select(TempMemory).where(
                TempMemory.user_id == user_id,
                TempMemory.is_active == True
            ).order_by(TempMemory.updated_at.desc())

            record = self.session.exec(statement).first()

            if record:
                logger.info(f"✓ Temp memory found for user_id={user_id}")
                return {
                    "id": record.id,
                    "user_id": record.user_id,
                    "business_id": record.business_id,
                    "project_id": record.project_id,
                    "email": record.email,
                    "password": record.password,
                    "base64_token": record.base64_token,
                    "jwt_token": record.jwt_token,
                    "verification_token": record.verification_token,
                    "first_broadcasting": record.first_broadcasting,
                    "broadcasting_status": record.broadcasting_status,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                    "updated_at": record.updated_at.isoformat() if record.updated_at else None,
                    "is_active": record.is_active
                }

            logger.warning(f"No temp memory found for user_id={user_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to get temp memory for user_id={user_id}: {e}")
            raise e

    def get_by_project_id(self, project_id: str) -> Optional[dict]:
        """
        Get temp memory for a given project_id.

        Args:
            project_id: Project ID to search for

        Returns:
            dict: Record details or None if not found
        """
        try:
            logger.info(f"Fetching temp memory for project_id={project_id}")

            statement = select(TempMemory).where(
                TempMemory.project_id == project_id,
                TempMemory.is_active == True
            ).order_by(TempMemory.updated_at.desc())

            record = self.session.exec(statement).first()

            if record:
                logger.info(f"✓ Temp memory found for project_id={project_id}")
                return {
                    "id": record.id,
                    "user_id": record.user_id,
                    "business_id": record.business_id,
                    "project_id": record.project_id,
                    "email": record.email,
                    "password": record.password,
                    "base64_token": record.base64_token,
                    "jwt_token": record.jwt_token,
                    "verification_token": record.verification_token,
                    "first_broadcasting": record.first_broadcasting,
                    "broadcasting_status": record.broadcasting_status,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                    "updated_at": record.updated_at.isoformat() if record.updated_at else None,
                    "is_active": record.is_active
                }

            logger.warning(f"No temp memory found for project_id={project_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to get temp memory for project_id={project_id}: {e}")
            raise e

    def is_first_broadcasting(self, user_id: str, project_id: str) -> bool:
        """
        Check if this is the first broadcasting for a user/project.

        Args:
            user_id: User ID
            project_id: Project ID

        Returns:
            bool: True if first broadcasting, False otherwise
        """
        try:
            record = self._get_existing_record(user_id, project_id)
            if record:
                return record.first_broadcasting
            # No record exists yet, so if created it would be first broadcasting
            return True
        except Exception as e:
            logger.error(f"Failed to check first_broadcasting: {e}")
            return True  # Default to True if check fails

    def update_broadcasting_status(
        self,
        user_id: str,
        project_id: str,
        broadcasting_status: bool
    ) -> bool:
        """
        Update the broadcasting_status for a user/project.

        Args:
            user_id: User ID
            project_id: Project ID
            broadcasting_status: New broadcasting status

        Returns:
            bool: True if updated successfully
        """
        try:
            record = self._get_existing_record(user_id, project_id)
            if record:
                record.broadcasting_status = broadcasting_status
                record.updated_at = datetime.utcnow()
                self.session.commit()
                logger.info(f"✓ Updated broadcasting_status to {broadcasting_status} for user_id={user_id}")
                return True
            logger.warning(f"No record found to update broadcasting_status for user_id={user_id}")
            return False
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to update broadcasting_status: {e}")
            raise e

    def mark_not_first_broadcasting(self, user_id: str, project_id: str) -> bool:
        """
        Mark that first broadcasting has been completed for a user/project.

        Args:
            user_id: User ID
            project_id: Project ID

        Returns:
            bool: True if updated successfully
        """
        try:
            record = self._get_existing_record(user_id, project_id)
            if record:
                record.first_broadcasting = False
                record.updated_at = datetime.utcnow()
                self.session.commit()
                logger.info(f"✓ Marked first_broadcasting=False for user_id={user_id}")
                return True
            logger.warning(f"No record found to mark not first broadcasting for user_id={user_id}")
            return False
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to mark not first broadcasting: {e}")
            raise e

    def deactivate(self, user_id: str, project_id: str) -> bool:
        """
        Deactivate a temp memory record.

        Args:
            user_id: User ID
            project_id: Project ID

        Returns:
            bool: True if deactivated successfully
        """
        try:
            record = self._get_existing_record(user_id, project_id)
            if record:
                record.is_active = False
                record.updated_at = datetime.utcnow()
                self.session.commit()
                logger.info(f"✓ Deactivated temp memory for user_id={user_id}, project_id={project_id}")
                return True
            return False
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to deactivate temp memory: {e}")
            raise e

    def get_all_by_user_id(self, user_id: str) -> List[dict]:
        """
        Get all temp memory records for a user_id.

        Args:
            user_id: User ID to search for

        Returns:
            List[dict]: List of record details
        """
        try:
            statement = select(TempMemory).where(
                TempMemory.user_id == user_id
            ).order_by(TempMemory.updated_at.desc())

            records = self.session.exec(statement).all()

            return [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "business_id": r.business_id,
                    "project_id": r.project_id,
                    "email": r.email,
                    "password": r.password,
                    "base64_token": r.base64_token,
                    "jwt_token": r.jwt_token,
                    "verification_token": r.verification_token,
                    "first_broadcasting": r.first_broadcasting,
                    "broadcasting_status": r.broadcasting_status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                    "is_active": r.is_active
                }
                for r in records
            ]
        except Exception as e:
            logger.error(f"Failed to get all temp memory for user_id={user_id}: {e}")
            raise e

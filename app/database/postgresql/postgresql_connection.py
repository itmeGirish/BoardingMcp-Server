from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, create_engine
from ...config.settings import settings
from ...config.logging import logger

# PostgreSQL connection setup
DATABASE_URL = f"postgresql+psycopg://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"

engine = create_engine(DATABASE_URL)
logger.info(f"Connecting to database at {settings.db_host}:{settings.db_port}/{settings.db_name}")


def get_session():
    logger.debug("Creating database session")
    with Session(engine) as session:
        yield session
    logger.debug("Database session closed")


SessionDep = Annotated[Session, Depends(get_session)]
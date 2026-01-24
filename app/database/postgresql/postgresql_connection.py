from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, create_engine
from ...config.settings import settings
from ...config.logging import logger
from contextlib import contextmanager



# PostgreSQL connection setup
DATABASE_URL = f"postgresql+psycopg://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"

print("Connecting to database with URL:", DATABASE_URL)

engine = create_engine(DATABASE_URL)
logger.info(f"Connecting to database at {settings.db_host}:{settings.db_port}/{settings.db_name}")



@contextmanager
def get_session():
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()

SessionDep = Annotated[Session, Depends(get_session)]
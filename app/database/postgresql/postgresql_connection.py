from contextlib import contextmanager
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, create_engine

from ...config.logging import logger
from ...config.settings import settings



# PostgreSQL connection setup
DATABASE_URL = (
    f"postgresql+psycopg://{settings.db_user}:{settings.db_password}"
    f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
)

engine = create_engine(DATABASE_URL)
logger.info(
    "Connecting to database at %s:%s/%s as user %s",
    settings.db_host,
    settings.db_port,
    settings.db_name,
    settings.db_user,
)



@contextmanager
def get_session():
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()

SessionDep = Annotated[Session, Depends(get_session)]

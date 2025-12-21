from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel
from .postgresql_connection import engine
from .models import User,BusinessCreation, Project_Creation

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    print("Database and tables created.")


if __name__ == "__main__":
    create_db_and_tables()




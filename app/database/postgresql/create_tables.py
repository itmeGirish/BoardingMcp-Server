# app/database/postgresql/create_tables.py
from sqlmodel import SQLModel
from .postgresql_connection import engine
from .models import User, BusinessCreation, ProjectCreation  # Import all models


def create_all_tables():
    """Create all tables in the database."""
    SQLModel.metadata.create_all(engine)
    print("All tables created successfully!")


if __name__ == "__main__":
    create_all_tables()
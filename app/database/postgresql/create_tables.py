# app/database/postgresql/create_tables.py
"""
Script to drop all existing tables and recreate them with the latest schema.

WARNING: This will DELETE ALL DATA in the database tables!
"""
from sqlmodel import SQLModel
from .postgresql_connection import engine
from .models import User, BusinessCreation, ProjectCreation, TempMemory  # Import all models


def drop_all_tables():
    """Drop all tables in the database."""
    print("=" * 60)
    print("WARNING: Dropping all tables...")
    print("=" * 60)
    SQLModel.metadata.drop_all(engine)
    print("All tables dropped successfully!")


def create_all_tables():
    """Create all tables in the database."""
    print("=" * 60)
    print("Creating all tables with latest schema...")
    print("=" * 60)
    SQLModel.metadata.create_all(engine)
    print("All tables created successfully!")
    print("=" * 60)
    print("Tables created:")
    print("  - users")
    print("  - business_creations (with password column)")
    print("  - project_creations")
    print("  - temporary_notes (for JWT tokens, runtime/broadcasting status)")
    print("=" * 60)


def recreate_all_tables():
    """Drop and recreate all tables (useful for schema changes)."""
    print("\n" + "=" * 60)
    print("RECREATING ALL DATABASE TABLES")
    print("=" * 60 + "\n")

    drop_all_tables()
    print()
    create_all_tables()

    print("\nDatabase schema updated successfully!")


if __name__ == "__main__":
    recreate_all_tables()

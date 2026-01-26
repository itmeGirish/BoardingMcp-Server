# test_connection.py
"""
Test script to verify database connection and CRUD operations.
"""
from .postgresql_connection import get_session
from .postgresql_repositories import UserCreationRepository, BusinessCreationRepository


def test_database_operations():
    """Test creating user and business records."""
    print("\n" + "=" * 60)
    print("TESTING DATABASE CONNECTION AND CRUD OPERATIONS")
    print("=" * 60 + "\n")

    # Use context manager syntax
    with get_session() as session:
        # 1. Create User first
        print("Step 1: Creating User...")
        user_repo = UserCreationRepository(session=session)
        user = user_repo.create(
            id="user1",
            name="Girish",
            email="agentstape@gmail.com"
        )
        print(f"  User created: {user.id}")

        # 2. Then create BusinessCreation (with password)
        print("\nStep 2: Creating BusinessCreation (with password)...")
        business_repo = BusinessCreationRepository(session=session)
        business = business_repo.create(
            id="123",
            user_id="user1",
            onboarding_id="onb_7891",
            display_name="My Business",
            project_ids=["6798e0ab6c6d490c0e356d1d"],
            user_name="AgentsTape",
            business_id="6798e0ab6c6d490c0e356d18",
            email="agentstape@gmail.com",
            company="Acme Inc",
            contact="919042689009",
            password="Agents@123"  # New password field
        )
        print(f"  BusinessCreation created: {business.id}")

        # 3. Verify password was saved
        print("\nStep 3: Verifying credentials retrieval...")
        credentials = business_repo.get_credentials_by_user_id("user1")
        if credentials:
            print(f"  Email: {credentials.get('email')}")
            print(f"  Password: {'*' * len(credentials.get('password', '')) if credentials.get('password') else 'None'}")
            print("  Credentials retrieved successfully!")
        else:
            print("  Failed to retrieve credentials!")

    print("\n" + "=" * 60)
    print("DATABASE TEST COMPLETED SUCCESSFULLY!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    test_database_operations()

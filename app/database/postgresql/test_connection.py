# test_connection.py
"""
Test script to verify database connection and CRUD operations.
"""
from .postgresql_connection import get_session
from .postgresql_repositories import (
    UserCreationRepository,
    BusinessCreationRepository,
    ProjectCreationRepository,

)


def test_database_operations():
    """Test creating user, business, and project records."""
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

        # 3. Create ProjectCreation
        print("\nStep 3: Creating ProjectCreation...")
        project_repo = ProjectCreationRepository(session=session)
        project = project_repo.create(
            id="6798e0ab6c6d490c0e356d1d",  # Same as project_ids in business
            user_id="user1",
            business_id="6798e0ab6c6d490c0e356d18",
            name="Tesla_car",
            partner_id="partner_001",
            type="project",
            status="active",
            sandbox=False,
            active_plan="STARTER",
            billing_currency="INR",
            timezone="Asia/Calcutta GMT+05:30",
            wa_number="+919042689009",
            wa_display_name="AgentsTape Business",
            wa_quality_rating="GREEN",
            fb_business_manager_status="VERIFIED",
            is_whatsapp_verified=True,
            applied_for_waba=True
        )
        print(f"  ProjectCreation created: {project.id}")
        print(f"  Project name: {project.name}")

        # 4. Verify credentials retrieval
        print("\nStep 4: Verifying credentials retrieval...")
        credentials = business_repo.get_credentials_by_user_id("user1")
        if credentials:
            print(f"  Email: {credentials.get('email')}")
            print(f"  Password: {'*' * len(credentials.get('password', '')) if credentials.get('password') else 'None'}")
            print("  Credentials retrieved successfully!")
        else:
            print("  Failed to retrieve credentials!")

        # 5. Verify project retrieval by user_id
        print("\nStep 5: Verifying project retrieval by user_id...")
        project_data = project_repo.get_project_by_user_id("user1")
        if project_data:
            name, project_id, business_id = project_data
            print(f"  Project Name: {name}")
            print(f"  Project ID: {project_id}")
            print(f"  Business ID: {business_id}")
            print("  Project retrieved successfully!")
        else:
            print("  Failed to retrieve project!")

        # 6. Create JWT Token
    #     print("\nStep 6: Creating JWT Token...")
    #     jwt_repo = JwtTokenRepository(session=session)
    #     import base64
    #     base64_token = base64.b64encode(
    #         "agentstape@gmail.com:Agents@123:6798e0ab6c6d490c0e356d1d".encode()
    #     ).decode()
    #     jwt_token = jwt_repo.create(
    #         user_id="user1",
    #         project_id="6798e0ab6c6d490c0e356d1d",
    #         email="agentstape@gmail.com",
    #         password="Agents@123",
    #         base64_token=base64_token,
    #         jwt_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidXNlcjEiLCJwcm9qZWN0X2lkIjoiNjc5OGUwYWI2YzZkNDkwYzBlMzU2ZDFkIn0.dummy_signature"
    #     )
    #     print(f"  JWT Token created with ID: {jwt_token.id}")
    #     print(f"  Base64 Token: {base64_token[:30]}...")

    #     # 7. Verify JWT token retrieval by user_id and project_id
    #     print("\nStep 7: Verifying JWT token retrieval...")
    #     token_data = jwt_repo.get_token_by_user_and_project("user1", "6798e0ab6c6d490c0e356d1d")
    #     if token_data:
    #         print(f"  User ID: {token_data.get('user_id')}")
    #         print(f"  Project ID: {token_data.get('project_id')}")
    #         print(f"  Email: {token_data.get('email')}")
    #         print(f"  JWT Token: {token_data.get('jwt_token')[:50]}...")
    #         print("  JWT token retrieved successfully!")
    #     else:
    #         print("  Failed to retrieve JWT token!")

    #     # 8. Verify JWT token retrieval by user_id only
    #     print("\nStep 8: Verifying JWT token retrieval by user_id only...")
    #     token_by_user = jwt_repo.get_token_by_user_id("user1")
    #     if token_by_user:
    #         print(f"  Found JWT token for user_id: user1")
    #         print("  JWT token by user_id retrieved successfully!")
    #     else:
    #         print("  Failed to retrieve JWT token by user_id!")

    # print("\n" + "=" * 60)
    # print("DATABASE TEST COMPLETED SUCCESSFULLY!")
    # print("=" * 60 + "\n")


if __name__ == "__main__":
    test_database_operations()

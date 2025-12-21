from .postgresql_connection import engine,get_session
from sqlmodel import create_engine, text, Session

# with Session(engine) as session:
#     result = session.exec(text("""
#         SELECT table_name 
#         FROM information_schema.tables 
#         WHERE table_schema = 'public'
#     """))
#     tables = result.all()
    
#     print(f"Tables in Agentsteer_db: {len(tables)}")
#     print(f"Names: {', '.join(t[0] for t in tables)}")
# test_connection.py

from .postgresql_connection import get_session
from .postgresql_repositories import UserCreationRepository, BusinessCreationRepository


session = next(get_session())

# 1. Create User first
# user_repo = UserCreationRepository(session=session)
# user = user_repo.create(
#     id="user_456",
#     name="John Doe",
#     email="john@example.com"
# )
# print(f"User created: {user.id}")

# # 2. Then create BusinessCreation
business_repo = BusinessCreationRepository(session=session)
business = business_repo.create(
    id="123",
    user_id="user_456",
    onboarding_id="onb_789",
    display_name="My Business",
    project_ids=["proj_1", "proj_2"],
    user_name="john@example.com",
    business_id="biz_001",
    email="john@example.com",
    company="Acme Inc",
    contact="919876543210"
)
print(f"BusinessCreation created: {business.id}")

session.close()
from app.database.postgresql.postgresql_connection import get_session
from app.database.postgresql.postgresql_repositories import BusinessCreationRepository
from app.database.postgresql.postgresql_repositories import ProjectCreationRepository

# with get_session() as session:
#     business_repo = ProjectCreationRepository(session=session)
    
#     user_id = "user_45618"
#     ids = business_repo.get_project_by_user_id(user_id)

#     print(ids)



with get_session() as session:
    business_repo = BusinessCreationRepository(session=session)
    
    user_id = "user_45618"
    ids = business_repo.get_everything_by_id(user_id)

    print(ids)



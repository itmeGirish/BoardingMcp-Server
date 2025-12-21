from app.database.postgresql.postgresql_connection import get_session
from app.database.postgresql.postgresql_repositories import BusinessCreationRepository

with get_session() as session:
    business_repo = BusinessCreationRepository(session=session)
    
    user_id = "user_456"
    ids = business_repo.get_ids_by_user_id(user_id)
    
    print(f"\nIDs for user_id: {user_id}\n")
    for record in ids:
        print(f"  ID: {record['id']}")
        print(f"  Business ID: {record['business_id']}")
        print(f"  {'-'*30}")

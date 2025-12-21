"""Quick script to read BusinessCreation by user_id."""
from app.database.postgresql.postgresql_connection import get_session
from app.database.postgresql.postgresql_repositories import BusinessCreationRepository

with get_session() as session:
    business_repo = BusinessCreationRepository(session=session)
    
    user_id = "user_456"
    businesses = business_repo.get_by_user_id(user_id)
    
    print(f"\n{'='*60}")
    print(f"Businesses for user_id: {user_id}")
    print(f"Total Records: {len(businesses)}")
    print(f"{'='*60}\n")
    
    for i, record in enumerate(businesses, 1):
        print(f"Record #{i}")
        print(f"  ID:            {record.id}")
        print(f"  User ID:       {record.user_id}")
        print(f"  Onboarding ID: {record.onboarding_id}")
        print(f"  Display Name:  {record.display_name}")
        print(f"  User Name:     {record.user_name}")
        print(f"  Email:         {record.email}")
        print(f"  Company:       {record.company}")
        print(f"  Business ID:   {record.business_id}")
        print(f"  Contact:       {record.contact}")
        print(f"  Project IDs:   {record.project_ids}")
        print(f"  Currency:      {record.currency}")
        print(f"  Timezone:      {record.timezone}")
        print(f"  Type:          {record.type}")
        print(f"  Active:        {record.active}")
        print(f"  Created At:    {record.created_at}")
        print(f"  Updated At:    {record.updated_at}")
        print(f"  {'-'*50}\n")
"""
Shared fixtures for integration tests.

Provides database session, test data constants, and cleanup utilities
for the WhatsApp Broadcasting Agent test suite.
"""
import base64
import pytest
from app.database.postgresql.postgresql_connection import get_session
from app.database.postgresql.postgresql_repositories import (
    MemoryRepository,
    BroadcastJobRepository,
)
from app.database.postgresql.postgresql_repositories.processed_contact_repo import (
    ProcessedContactRepository,
)
from app.database.postgresql.postgresql_repositories.template_creation_repo import (
    TemplateCreationRepository,
)


# ============================================
# TEST CONSTANTS - Bedzee pg connector platform
# ============================================

USER_ID = "user1"
PROJECT_ID = "6798e0ab6c6d490c0e356d1d"
BUSINESS_ID = "6798e0ab6c6d490c0e356d18"
EMAIL = "agentstape@gmail.com"
PASSWORD = "Agents@123"

# Contacts from docs/Broacsting - Sheet1.csv
CSV_CONTACTS = [
    {"name": "Girish", "phone": "8861832522"},
    {"name": "Vamsi", "phone": "9177604610"},
    {"name": "Santhu", "phone": "9353578022"},
    {"name": "Mahesh", "phone": "8297347120"},
]

CSV_PHONE_NUMBERS = [c["phone"] for c in CSV_CONTACTS]

# E.164 normalized (Indian numbers)
E164_PHONES = [
    "+918861832522",
    "+919177604610",
    "+919353578022",
    "+918297347120",
]

# Template for broadcasting
TEST_TEMPLATE = {
    "template_id": "test_bedzee_broadcast_001",
    "name": "bedzee_broadcast_promo",
    "category": "MARKETING",
    "language": "en_US",
    "components": [
        {
            "type": "BODY",
            "text": "Hello {{1}}, check out our latest offers on Bedzee! Visit us today.",
            "example": {"body_text": [["Customer"]]},
        }
    ],
}


# ============================================
# FIXTURES
# ============================================

@pytest.fixture
def db_session():
    """Provide a database session for tests."""
    with get_session() as session:
        yield session


@pytest.fixture
def broadcast_repo(db_session):
    """Provide BroadcastJobRepository."""
    return BroadcastJobRepository(session=db_session)


@pytest.fixture
def contact_repo(db_session):
    """Provide ProcessedContactRepository."""
    return ProcessedContactRepository(session=db_session)


@pytest.fixture
def template_repo(db_session):
    """Provide TemplateCreationRepository."""
    return TemplateCreationRepository(session=db_session)


@pytest.fixture
def memory_repo(db_session):
    """Provide MemoryRepository."""
    return MemoryRepository(session=db_session)


@pytest.fixture
def jwt_token():
    """Generate a dummy JWT token for testing."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_broadcasting_token"


@pytest.fixture
def base64_token():
    """Generate base64 token from test credentials."""
    raw = f"{EMAIL}:{PASSWORD}:{PROJECT_ID}"
    return base64.b64encode(raw.encode()).decode()

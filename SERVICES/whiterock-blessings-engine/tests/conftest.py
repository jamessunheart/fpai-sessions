"""
WhiteRock Blessings Engine - Test Configuration
Fixtures for pytest-asyncio testing.
"""

import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.database import Base, get_db
from app.config import settings
from app.auth import hash_password, create_access_token, create_refresh_token
from app.models import Member, MembershipTier, DisclosureVersion, CommunityCapacity

# Test database URL - use SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def client(test_session) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with overridden database dependency."""
    
    async def override_get_db():
        yield test_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def seed_data(test_session: AsyncSession):
    """Seed the test database with required reference data."""
    # Add membership tiers
    tiers = [
        MembershipTier(name="seedling", cora_threshold=0, cora_cap=1000, description="New member"),
        MembershipTier(name="sprout", cora_threshold=500, cora_cap=2500, description="Active participant"),
        MembershipTier(name="steward", cora_threshold=2000, cora_cap=5000, description="Committed member"),
        MembershipTier(name="elder", cora_threshold=5000, cora_cap=10000, description="Senior member"),
    ]
    for tier in tiers:
        test_session.add(tier)
    
    # Add disclosure version
    disclosure = DisclosureVersion(
        version="1.0.0",
        disclosure_text="Test disclosure text for 508(c)(1)(A) compliance.",
        is_current=True
    )
    test_session.add(disclosure)
    
    # Add community capacity
    capacity = CommunityCapacity(
        capacity_level="high",
        updated_by="test"
    )
    test_session.add(capacity)
    
    await test_session.commit()


@pytest.fixture
async def test_member(test_session: AsyncSession, seed_data) -> Member:
    """Create a test member."""
    member = Member(
        email="test@example.com",
        password_hash=hash_password("testpass123"),
        full_name="Test User",
        phone="555-1234",
        address_line1="123 Test St",
        city="Test City",
        state="TS",
        zip_code="12345",
        profile_complete=True,
        membership_tier="seedling",
        cora_balance=100,
        cora_cap=1000
    )
    test_session.add(member)
    await test_session.commit()
    await test_session.refresh(member)
    return member


@pytest.fixture
async def test_admin(test_session: AsyncSession, seed_data) -> Member:
    """Create a test admin member."""
    admin = Member(
        email="admin@example.com",
        password_hash=hash_password("adminpass123"),
        full_name="Admin User",
        profile_complete=True,
        membership_tier="elder",
        cora_balance=5000,
        cora_cap=10000,
        is_admin=True,
        is_committee=True
    )
    test_session.add(admin)
    await test_session.commit()
    await test_session.refresh(admin)
    return admin


@pytest.fixture
def member_token(test_member: Member) -> str:
    """Generate access token for test member."""
    return create_access_token({
        "sub": str(test_member.id),
        "email": test_member.email,
        "tier": test_member.membership_tier,
        "is_admin": False,
        "is_committee": False,
        "is_auditor": False
    })


@pytest.fixture
def admin_token(test_admin: Member) -> str:
    """Generate access token for test admin."""
    return create_access_token({
        "sub": str(test_admin.id),
        "email": test_admin.email,
        "tier": test_admin.membership_tier,
        "is_admin": True,
        "is_committee": True,
        "is_auditor": False
    })


@pytest.fixture
def auth_headers(member_token: str) -> dict:
    """Authorization headers for test member."""
    return {"Authorization": f"Bearer {member_token}"}


@pytest.fixture
def admin_headers(admin_token: str) -> dict:
    """Authorization headers for test admin."""
    return {"Authorization": f"Bearer {admin_token}"}




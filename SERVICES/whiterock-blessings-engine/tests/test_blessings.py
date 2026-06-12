"""
WhiteRock Blessings Engine - Blessing Endpoint Tests
Tests for blessing requests and state machine enforcement.
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Member, BlessingRequest


@pytest.fixture
async def eligible_member(test_session: AsyncSession, seed_data) -> Member:
    """Create a member eligible for blessings (>30 days, disclosure signed)."""
    from app.auth import hash_password
    
    member = Member(
        email="eligible@example.com",
        password_hash=hash_password("testpass123"),
        full_name="Eligible User",
        address_line1="123 Test St",
        city="Test City",
        state="TS",
        zip_code="12345",
        profile_complete=True,
        disclosure_signed_at=datetime.utcnow(),
        disclosure_version="1.0.0",
        membership_tier="seedling",
        cora_balance=100,
        cora_cap=1000,
        # Set created_at to >30 days ago
        created_at=datetime.utcnow() - timedelta(days=45)
    )
    test_session.add(member)
    await test_session.commit()
    await test_session.refresh(member)
    return member


@pytest.fixture
def eligible_token(eligible_member: Member) -> str:
    """Generate token for eligible member."""
    from app.auth import create_access_token
    return create_access_token({
        "sub": str(eligible_member.id),
        "email": eligible_member.email,
        "tier": eligible_member.membership_tier,
        "is_admin": False,
        "is_committee": False,
        "is_auditor": False
    })


@pytest.fixture
def eligible_headers(eligible_token: str) -> dict:
    """Headers for eligible member."""
    return {"Authorization": f"Bearer {eligible_token}"}


@pytest.mark.asyncio
async def test_check_eligibility_new_member(client: AsyncClient, auth_headers):
    """Test new member is not eligible for blessings."""
    response = await client.get("/blessings/eligibility", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["eligible"] == False
    # Should have reasons like disclosure_not_signed or member_under_30_days


@pytest.mark.asyncio
async def test_check_eligibility_eligible_member(client: AsyncClient, eligible_headers):
    """Test eligible member passes eligibility check."""
    response = await client.get("/blessings/eligibility", headers=eligible_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["eligible"] == True
    assert len(data["reasons"]) == 0
    assert data["community_capacity"] in ["high", "medium", "low", "paused"]


@pytest.mark.asyncio
async def test_create_blessing_request(client: AsyncClient, eligible_headers):
    """Test creating a blessing request."""
    response = await client.post("/blessings/request",
        headers=eligible_headers,
        json={
            "category": "housing",
            "description": "Need help with rent payment due to medical expenses",
            "amount_requested_cents": 150000,
            "vendor_name": "ABC Apartments",
            "vendor_contact": "555-1234"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "housing"
    assert data["status"] == "pending"  # Auto-transitions from draft
    assert data["amount_requested_cents"] == 150000
    assert len(data["state_history"]) == 1  # draft -> pending


@pytest.mark.asyncio
async def test_create_blessing_request_ineligible(client: AsyncClient, auth_headers):
    """Test ineligible member cannot create blessing request."""
    response = await client.post("/blessings/request",
        headers=auth_headers,
        json={
            "category": "food",
            "description": "Need help with groceries"
        }
    )
    
    assert response.status_code == 400
    assert "not eligible" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_my_blessings(client: AsyncClient, eligible_headers):
    """Test getting member's own blessing requests."""
    # First create a request
    await client.post("/blessings/request",
        headers=eligible_headers,
        json={
            "category": "utilities",
            "description": "Need help with electric bill"
        }
    )
    
    # Then get the list
    response = await client.get("/blessings/me", headers=eligible_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "requests" in data
    assert len(data["requests"]) >= 1


@pytest.mark.asyncio
async def test_committee_view_pending(client: AsyncClient, admin_headers, eligible_headers):
    """Test committee can view pending requests."""
    # Create a request
    await client.post("/blessings/request",
        headers=eligible_headers,
        json={
            "category": "medical",
            "description": "Medical expense assistance needed"
        }
    )
    
    # Committee views pending
    response = await client.get("/blessings/pending", headers=admin_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "requests" in data


@pytest.mark.asyncio
async def test_blessing_state_transition(client: AsyncClient, admin_headers, eligible_headers, test_session):
    """Test committee can transition blessing states."""
    # Create a request
    create_response = await client.post("/blessings/request",
        headers=eligible_headers,
        json={
            "category": "housing",
            "description": "Rent assistance needed",
            "amount_requested_cents": 100000
        }
    )
    blessing_id = create_response.json()["id"]
    
    # Transition to committee_review
    response = await client.put(f"/blessings/{blessing_id}/transition",
        headers=admin_headers,
        json={
            "new_status": "committee_review"
        }
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "committee_review"


@pytest.mark.asyncio
async def test_cannot_approve_without_compliance_flag(client: AsyncClient, admin_headers, eligible_headers):
    """Test approval requires compliance flag."""
    # Create and transition to committee_review
    create_response = await client.post("/blessings/request",
        headers=eligible_headers,
        json={"category": "food", "description": "Food assistance"}
    )
    blessing_id = create_response.json()["id"]
    
    await client.put(f"/blessings/{blessing_id}/transition",
        headers=admin_headers,
        json={"new_status": "committee_review"}
    )
    
    # Try to approve without compliance flag
    response = await client.put(f"/blessings/{blessing_id}/transition",
        headers=admin_headers,
        json={
            "new_status": "approved",
            "compliance_flag": False,
            "amount_approved_cents": 50000
        }
    )
    
    assert response.status_code == 400
    assert "compliance" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_state_transition_rejected(client: AsyncClient, admin_headers, eligible_headers):
    """Test invalid state transitions are rejected."""
    # Create a request (auto-transitions to pending)
    create_response = await client.post("/blessings/request",
        headers=eligible_headers,
        json={"category": "emergency", "description": "Emergency assistance"}
    )
    blessing_id = create_response.json()["id"]
    
    # Try to skip committee_review and go directly to approved
    response = await client.put(f"/blessings/{blessing_id}/transition",
        headers=admin_headers,
        json={
            "new_status": "approved",
            "compliance_flag": True,
            "amount_approved_cents": 25000
        }
    )
    
    assert response.status_code == 400
    assert "invalid transition" in response.json()["detail"].lower()




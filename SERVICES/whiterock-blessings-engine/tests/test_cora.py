"""
WhiteRock Blessings Engine - CORA Endpoint Tests
Tests for CORA vitality credit management.
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Member


@pytest.mark.asyncio
async def test_get_cora_balance(client: AsyncClient, auth_headers):
    """Test getting CORA balance."""
    response = await client.get("/cora/balance", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "balance" in data
    assert "cap" in data
    assert "tier" in data
    assert "decay_warning" in data
    assert "transaction_history" in data


@pytest.mark.asyncio
async def test_get_cora_tiers(client: AsyncClient, seed_data):
    """Test getting CORA tier definitions (public endpoint)."""
    response = await client.get("/cora/tiers")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 4  # seedling, sprout, steward, elder
    
    # Verify tier structure
    for tier in data:
        assert "name" in tier
        assert "threshold" in tier
        assert "cap" in tier
        assert "privileges" in tier


@pytest.mark.asyncio
async def test_cora_tiers_cached(client: AsyncClient, seed_data):
    """Test that CORA tiers endpoint returns cache headers."""
    response = await client.get("/cora/tiers")
    
    assert response.status_code == 200
    # Second request should be cached
    response2 = await client.get("/cora/tiers")
    assert response2.status_code == 200


@pytest.mark.asyncio
async def test_admin_grant_cora(client: AsyncClient, admin_headers, test_member):
    """Test admin can grant CORA credits."""
    response = await client.post("/cora/grant",
        headers=admin_headers,
        json={
            "member_id": test_member.id,
            "amount": 50,
            "transaction_type": "admin_adjustment",
            "description": "Test grant"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["new_balance"] == test_member.cora_balance + 50


@pytest.mark.asyncio
async def test_non_admin_cannot_grant_cora(client: AsyncClient, auth_headers, test_member):
    """Test non-admin cannot grant CORA credits."""
    response = await client.post("/cora/grant",
        headers=auth_headers,
        json={
            "member_id": test_member.id,
            "amount": 50,
            "transaction_type": "admin_adjustment"
        }
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cora_cap_enforced(client: AsyncClient, admin_headers, test_member, test_session):
    """Test CORA grants respect cap."""
    # Grant more than the cap allows
    response = await client.post("/cora/grant",
        headers=admin_headers,
        json={
            "member_id": test_member.id,
            "amount": 5000,  # More than cap (1000)
            "transaction_type": "admin_adjustment"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    # Should be capped at member's max
    assert data["new_balance"] <= test_member.cora_cap


@pytest.mark.asyncio
async def test_decay_preview_admin_only(client: AsyncClient, admin_headers, auth_headers):
    """Test decay preview is admin-only."""
    # Admin can access
    response_admin = await client.get("/cora/decay-preview", headers=admin_headers)
    assert response_admin.status_code == 200
    
    # Non-admin cannot
    response_member = await client.get("/cora/decay-preview", headers=auth_headers)
    assert response_member.status_code == 403


@pytest.mark.asyncio
async def test_cora_circulation_admin_only(client: AsyncClient, admin_headers, auth_headers):
    """Test circulation stats are admin-only."""
    response_admin = await client.get("/cora/circulation", headers=admin_headers)
    assert response_admin.status_code == 200
    
    data = response_admin.json()
    assert "total_circulation" in data
    assert "average_per_member" in data


class TestCoraDecayLogic:
    """Tests for CORA decay business logic."""
    
    @pytest.mark.asyncio
    async def test_decay_calculation(self, test_session: AsyncSession, test_member):
        """Test CORA decay is calculated correctly (10% rate)."""
        from app.services.cora_service import CoraService
        
        # Set member as inactive for 13 months
        test_member.last_engagement_date = datetime.utcnow() - timedelta(days=400)
        test_member.cora_balance = 100
        await test_session.commit()
        
        service = CoraService(test_session)
        decay_event = await service.decay_cora(test_member.id, months_inactive=13)
        
        assert decay_event is not None
        assert decay_event.amount_decayed == 10  # 10% of 100
        assert decay_event.balance_after == 90
    
    @pytest.mark.asyncio
    async def test_no_decay_for_active_members(self, test_session: AsyncSession, test_member):
        """Test active members don't decay."""
        from app.services.cora_service import CoraService
        
        # Set member as recently active
        test_member.last_engagement_date = datetime.utcnow()
        await test_session.commit()
        
        service = CoraService(test_session)
        members = await service.get_members_for_decay()
        
        # Test member should not be in decay list
        member_ids = [m.id for m in members]
        assert test_member.id not in member_ids




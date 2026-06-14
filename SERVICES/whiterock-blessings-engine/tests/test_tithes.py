"""
WhiteRock Blessings Engine - Tithe Endpoint Tests
Tests for tithe submission and disclosure compliance.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_submit_tithe_requires_disclosure(client: AsyncClient, auth_headers, seed_data):
    """Test tithe submission requires disclosure acknowledgment."""
    response = await client.post("/tithes",
        headers=auth_headers,
        json={
            "amount_cents": 10000,
            "payment_method_id": "pm_test_123",
            "disclosure_acknowledged": False,
            "disclosure_scrolled": False,
            "disclosure_version": "1.0.0"
        }
    )
    
    # Should fail validation because disclosure not acknowledged
    assert response.status_code == 422 or response.status_code == 400


@pytest.mark.asyncio
async def test_submit_tithe_success(client: AsyncClient, auth_headers, seed_data):
    """Test successful tithe submission with proper disclosure."""
    response = await client.post("/tithes",
        headers=auth_headers,
        json={
            "amount_cents": 5000,
            "payment_method_id": "pm_test_123",
            "disclosure_acknowledged": True,
            "disclosure_scrolled": True,
            "disclosure_version": "1.0.0"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["amount_cents"] == 5000
    assert data["disclosure_version"] == "1.0.0"


@pytest.mark.asyncio
async def test_submit_tithe_wrong_disclosure_version(client: AsyncClient, auth_headers, seed_data):
    """Test tithe fails with outdated disclosure version."""
    response = await client.post("/tithes",
        headers=auth_headers,
        json={
            "amount_cents": 5000,
            "payment_method_id": "pm_test_123",
            "disclosure_acknowledged": True,
            "disclosure_scrolled": True,
            "disclosure_version": "0.9.0"  # Wrong version
        }
    )
    
    assert response.status_code == 400
    assert "version" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_my_tithes(client: AsyncClient, auth_headers):
    """Test getting member's tithe history."""
    response = await client.get("/tithes/me", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "tithes" in data
    assert "total_contributed_cents" in data


@pytest.mark.asyncio
async def test_tithe_requires_auth(client: AsyncClient, seed_data):
    """Test tithe endpoints require authentication."""
    response = await client.post("/tithes", json={
        "amount_cents": 5000,
        "payment_method_id": "pm_test",
        "disclosure_acknowledged": True,
        "disclosure_scrolled": True,
        "disclosure_version": "1.0.0"
    })
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_tithe_receipt(client: AsyncClient, auth_headers, seed_data):
    """Test getting tithe receipt after submission."""
    # First submit a tithe
    submit_response = await client.post("/tithes",
        headers=auth_headers,
        json={
            "amount_cents": 10000,
            "payment_method_id": "pm_test_456",
            "disclosure_acknowledged": True,
            "disclosure_scrolled": True,
            "disclosure_version": "1.0.0"
        }
    )
    
    if submit_response.status_code == 200:
        tithe_id = submit_response.json()["id"]
        
        # Get the receipt
        receipt_response = await client.get(
            f"/tithes/{tithe_id}/receipt",
            headers=auth_headers
        )
        
        assert receipt_response.status_code == 200
        assert "text/html" in receipt_response.headers.get("content-type", "")




"\"\"\"Integration tests for Treasury Growth System.\"\"\""
import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.main import app
from app.models import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_treasury.db"


@pytest.fixture(scope="module")
def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL)

    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_models())
    yield engine
    asyncio.run(engine.dispose())


@pytest.fixture()
def session_factory(test_engine):
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture()
def client(session_factory):
    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_asset_creation_and_listing(client: TestClient):
    asset_payload = {
        "name": "Growth Fund",
        "type": "equity",
        "value": "100000.00",
        "risk_level": "medium",
    }
    response = client.post("/assets", json=asset_payload)
    assert response.status_code == 201
    asset = response.json()
    assert asset["name"] == "Growth Fund"

    list_response = client.get("/assets")
    assert list_response.status_code == 200
    assets = list_response.json()
    assert len(assets) >= 1
    assert any(item["id"] == asset["id"] for item in assets)


def test_transaction_flow(client: TestClient):
    asset_payload = {
        "name": "Income Trust",
        "type": "bond",
        "value": "50000.00",
        "risk_level": "low",
    }
    asset_resp = client.post("/assets", json=asset_payload)
    asset_id = asset_resp.json()["id"]

    tx_payload = {
        "asset_id": asset_id,
        "amount": "2500.00",
        "type": "buy",
    }
    tx_resp = client.post("/transactions", json=tx_payload)
    assert tx_resp.status_code == 201
    transaction = tx_resp.json()
    assert transaction["asset_id"] == asset_id

    list_resp = client.get("/transactions")
    assert list_resp.status_code == 200
    transactions = list_resp.json()
    assert any(tx["id"] == transaction["id"] for tx in transactions)


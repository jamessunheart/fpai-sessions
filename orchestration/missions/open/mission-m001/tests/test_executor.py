"""Integration tests for Autonomous Executor."""
import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.main import app
from app.models import Base

TEST_DB_URL = "sqlite+aiosqlite:///./test_executor.db"


@pytest.fixture(scope="module")
def engine():
    engine = create_async_engine(TEST_DB_URL)

    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_models())
    yield engine
    asyncio.run(engine.dispose())


@pytest.fixture()
def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture()
def client(session_factory):
    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_message_ingest_and_status_update(client: TestClient):
    payload = {
        "from_service": "orchestrator",
        "payload": {
            "task_id": "task-123",
            "action": "execute_ai_model",
            "data": {"model_input": "foo"},
        },
    }
    resp = client.post("/message", json=payload)
    assert resp.status_code == 202
    task = resp.json()
    assert task["status"] == "pending"

    status_update = {
        "status": "completed",
        "result": {"output": "bar"},
    }

    update_resp = client.post(f"/tasks/{task['task_id']}/status", json=status_update)
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["status"] == "completed"
    assert updated["result"] == {"output": "bar"}

    list_resp = client.get("/tasks")
    assert list_resp.status_code == 200
    assert any(item["task_id"] == task["task_id"] for item in list_resp.json())


"""Cross-tenant isolation integration test.

Uses ``testcontainers`` to spin up Postgres with pgvector, applies migrations,
and verifies that RLS truly prevents one tenant from reading another's rows.

Skips when Docker is unavailable. Run explicitly with:

    pytest -m integration tests/test_rls_isolation.py
"""
from __future__ import annotations

import asyncio
import os
import pathlib
import uuid

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def pg_container():
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip("testcontainers not installed")

    try:
        pg = PostgresContainer("pgvector/pgvector:pg16")
        pg.start()
    except Exception as e:
        pytest.skip(f"Docker not available: {e}")

    try:
        yield pg
    finally:
        pg.stop()


@pytest.fixture(scope="module")
def dsn(pg_container):
    url = pg_container.get_connection_url()
    # testcontainers returns psycopg2 DSN; rewrite for asyncpg
    return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")


@pytest.fixture(scope="module")
def db_ready(pg_container, dsn):
    """Apply migrations + ensure RLS is enforceable by a non-superuser role."""
    import psycopg

    raw_dsn = pg_container.get_connection_url().replace("postgresql+psycopg2://", "postgresql://")
    migrations = pathlib.Path(__file__).parent.parent / "db" / "migrations"

    with psycopg.connect(raw_dsn, autocommit=True) as conn:
        for sql_path in sorted(migrations.glob("*.sql")):
            conn.execute(sql_path.read_text())

        # Create a non-superuser application role so RLS policies actually bite.
        conn.execute("CREATE ROLE app_user LOGIN PASSWORD 'app' NOINHERIT")
        conn.execute("GRANT USAGE ON SCHEMA public TO app_user")
        conn.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user")
        conn.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user")
    return True


@pytest.fixture(scope="module")
def app_dsn(pg_container, db_ready):
    """DSN that authenticates as the non-superuser app role."""
    base = pg_container.get_connection_url().replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    # swap user:pw component
    # Example: postgresql+asyncpg://test:test@127.0.0.1:5432/test → postgresql+asyncpg://app:app@127.0.0.1:5432/test
    auth_and_host = base.split("://", 1)[1]
    _, host_and_db = auth_and_host.split("@", 1)
    return f"postgresql+asyncpg://app:app@{host_and_db}"


def _configure_settings(dsn: str):
    os.environ["DATABASE_URL"] = dsn
    # Force settings module to re-read
    from shared import config as cfg
    cfg.Settings.model_config  # touch to ensure pydantic available
    cfg._cached_settings = None  # type: ignore[attr-defined]


async def _seed_two_tenants(dsn: str) -> tuple[str, str]:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(dsn, pool_pre_ping=True)
    tid_a, tid_b = str(uuid.uuid4()), str(uuid.uuid4())
    async with engine.begin() as conn:
        await conn.execute(text("SET LOCAL app.is_superuser = 'true'"))
        for tid, slug in [(tid_a, "tenant-a"), (tid_b, "tenant-b")]:
            await conn.execute(
                text(
                    """
                    INSERT INTO tenants (id, slug, name, plan, status)
                    VALUES (CAST(:tid AS uuid), :slug, :name, 'pro', 'active')
                    """
                ),
                {"tid": tid, "slug": slug, "name": slug},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO conversations (tenant_id, channel, direction, status)
                    VALUES (CAST(:tid AS uuid), 'voice', 'inbound', 'open')
                    """
                ),
                {"tid": tid},
            )
    await engine.dispose()
    return tid_a, tid_b


async def _assert_isolation(dsn: str, tid_a: str, tid_b: str) -> None:
    _configure_settings(dsn)
    # Re-import so shared.db uses the new DSN
    import importlib

    import shared.db as dbmod

    importlib.reload(dbmod)
    from sqlalchemy import text

    async with dbmod.tenant_session(tid_a) as s:
        a_count = (await s.execute(text("SELECT count(*) FROM conversations"))).scalar_one()

    async with dbmod.tenant_session(tid_b) as s:
        b_count = (await s.execute(text("SELECT count(*) FROM conversations"))).scalar_one()

    assert a_count == 1, f"tenant A must see exactly 1 row, saw {a_count}"
    assert b_count == 1, f"tenant B must see exactly 1 row, saw {b_count}"

    async with dbmod.tenant_session(tid_a) as s:
        cross = (
            await s.execute(
                text("SELECT count(*) FROM conversations WHERE tenant_id = CAST(:t AS uuid)"),
                {"t": tid_b},
            )
        ).scalar_one()
    assert cross == 0, "RLS must hide tenant B's rows from tenant A"

    async with dbmod.tenant_session(None, superuser=True) as s:
        total = (await s.execute(text("SELECT count(*) FROM conversations"))).scalar_one()
    assert total == 2, f"superuser context must see both rows, saw {total}"


def test_cross_tenant_rls(app_dsn: str):
    async def runner():
        tid_a, tid_b = await _seed_two_tenants(app_dsn)
        await _assert_isolation(app_dsn, tid_a, tid_b)

    asyncio.run(runner())

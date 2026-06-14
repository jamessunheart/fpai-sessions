import os
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

import asyncpg
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Droplet 18 Registry (PostgreSQL)")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://registry18_user:Reg18_db_P@ss_2025!@localhost:5432/registry18",
)

HEARTBEAT_TTL_SECONDS = 180  # 3 minutes


class RegisterRequest(BaseModel):
    name: str
    fqdn: str
    ip: str
    role: str
    env: str
    version: str
    cost_hour: float = Field(0.0, ge=0)


class HeartbeatRequest(BaseModel):
    id: str  # fqdn
    status: Literal["healthy", "down", "unknown"] = "healthy"
    cpu: Optional[float] = Field(None, ge=0, le=100)
    mem: Optional[float] = Field(None, ge=0, le=100)
    disk: Optional[float] = Field(None, ge=0, le=100)


@app.on_event("startup")
async def startup_event():
    """
    Create a connection pool and ensure the droplets table exists.
    """
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")

    app.state.pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)

    async with app.state.pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS droplets (
                fqdn TEXT PRIMARY KEY,
                name TEXT,
                ip TEXT,
                role TEXT,
                env TEXT,
                version TEXT,
                cost_hour DOUBLE PRECISION,
                status TEXT,
                cpu DOUBLE PRECISION,
                mem DOUBLE PRECISION,
                disk DOUBLE PRECISION,
                last_seen TIMESTAMPTZ
            );
            """
        )


@app.on_event("shutdown")
async def shutdown_event():
    pool = getattr(app.state, "pool", None)
    if pool:
        await pool.close()


@app.get("/health")
async def health():
    """Simple health ping for Registry 18."""
    return {
        "id": 18,
        "name": "Registry v2 (Droplet 18)",
        "status": "active",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/registry/register")
async def registry_register(req: RegisterRequest):
    """
    Register or update a droplet in the registry database.
    """
    now = datetime.now(timezone.utc)

    query = """
    INSERT INTO droplets (fqdn, name, ip, role, env, version, cost_hour, status, cpu, mem, disk, last_seen)
    VALUES ($1, $2, $3, $4, $5, $6, $7, 'healthy', 0, 0, 0, $8)
    ON CONFLICT (fqdn) DO UPDATE
    SET name = EXCLUDED.name,
        ip = EXCLUDED.ip,
        role = EXCLUDED.role,
        env = EXCLUDED.env,
        version = EXCLUDED.version,
        cost_hour = EXCLUDED.cost_hour,
        last_seen = EXCLUDED.last_seen;
    """

    async with app.state.pool.acquire() as conn:
        await conn.execute(
            query,
            req.fqdn,
            req.name,
            req.ip,
            req.role,
            req.env,
            req.version,
            req.cost_hour,
            now,
        )

    return {"id": req.fqdn, "registered_at": now.isoformat()}


@app.post("/registry/heartbeat")
async def registry_heartbeat(hb: HeartbeatRequest):
    """
    Heartbeat endpoint. Updates metrics and last_seen.
    If droplet isn't registered yet, create a minimal record.
    """
    now = datetime.now(timezone.utc)

    async with app.state.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT fqdn FROM droplets WHERE fqdn = $1", hb.id
        )

        if row is None:
            # Create minimal record
            await conn.execute(
                """
                INSERT INTO droplets (fqdn, name, ip, role, env, version,
                                      cost_hour, status, cpu, mem, disk, last_seen)
                VALUES ($1, $1, '', '', '', '', 0.0, $2, $3, $4, $5, $6)
                """,
                hb.id,
                "healthy" if hb.status == "healthy" else hb.status,
                hb.cpu or 0.0,
                hb.mem or 0.0,
                hb.disk or 0.0,
                now,
            )
        else:
            await conn.execute(
                """
                UPDATE droplets
                SET status = $2,
                    cpu = COALESCE($3, cpu),
                    mem = COALESCE($4, mem),
                    disk = COALESCE($5, disk),
                    last_seen = $6
                WHERE fqdn = $1
                """,
                hb.id,
                "healthy" if hb.status == "healthy" else hb.status,
                hb.cpu,
                hb.mem,
                hb.disk,
                now,
            )

    return {"status": "ok", "updated_at": now.isoformat()}


@app.get("/dashboard")
async def dashboard():
    """
    Returns aggregated summary and droplet list,
    with TTL-based down detection.
    """
    now = datetime.now(timezone.utc)
    summary = {
        "total": 0,
        "healthy": 0,
        "down": 0,
        "cost_hour_total": 0.0,
    }
    droplets_list = []

    async with app.state.pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM droplets")

    for d in rows:
        last_seen = d["last_seen"] or (now - timedelta(days=1))
        seconds_since = (now - last_seen).total_seconds()
        status = d["status"] or "unknown"

        if seconds_since > HEARTBEAT_TTL_SECONDS:
            status = "down"

        summary["total"] += 1
        if status == "healthy":
            summary["healthy"] += 1
        elif status == "down":
            summary["down"] += 1

        summary["cost_hour_total"] += float(d["cost_hour"] or 0.0)

        droplets_list.append(
            {
                "fqdn": d["fqdn"],
                "status": status,
                "cpu": float(d["cpu"] or 0.0),
                "mem": float(d["mem"] or 0.0),
                "env": d["env"] or "",
                "role": d["role"] or "",
                "version": d["version"] or "",
                "last_seen": last_seen.isoformat(),
            }
        )

    return {"summary": summary, "droplets": droplets_list}


@app.get("/registry/discover")
async def registry_discover():
    """
    Returns full droplet directory for Orchestrator/Dashboard.
    """
    async with app.state.pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT fqdn, name, ip, role, env, version, cost_hour, status, cpu, mem, disk, last_seen
            FROM droplets
            ORDER BY fqdn;
            """
        )

    return [
        {
            "fqdn": d["fqdn"],
            "name": d["name"],
            "ip": d["ip"],
            "role": d["role"],
            "env": d["env"],
            "version": d["version"],
            "cost_hour": float(d["cost_hour"] or 0.0),
            "status": d["status"],
            "cpu": float(d["cpu"] or 0.0),
            "mem": float(d["mem"] or 0.0),
            "disk": float(d["disk"] or 0.0),
            "last_seen": (d["last_seen"] or datetime.now(timezone.utc)).isoformat(),
        }
        for d in rows
    ]

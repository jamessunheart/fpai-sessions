"""Outbounders Agent API v0 — sidecar service, read-mostly, runs next to MariaDB.

Runs ON 209.74.93.72 (localhost bind, port 8300). Reads obapp_outbounders.
Writes ONLY: INSERT into client_job_posting, INSERT/UPDATE on api_keys (new table).

Schema VERIFIED against live DESCRIBE (2026-08-10):
  main_users: user_id, email_address, firstname, country_code, account_type,
              last_login, date_created, everified, banned, deleted
  client_job_posting: PK `id`; user_id, title, `desc`, date_create,
              active, deleted, approved
  job_application: FK `job_id`; carries per-application hourly_rate decimal(12,2)
              (rates are proposed by agents per application — no rate on profiles)
  agent_info: FK `agent_id`; skill self-scores (skills_survey, skills_ccc,
              skills_ccb, skills_upsell, skills_closesale), work_experience,
              work_night/work_eight flags. PII columns (skypeid, yahooid,
              mobileno, landlineno, file_*) are NEVER exposed.
"""
from __future__ import annotations

import hashlib
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator, Optional

import pymysql
import pymysql.cursors
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Config (env)
# ---------------------------------------------------------------------------

DB_NAME = os.environ.get("DB_NAME", "obapp_outbounders")
DB_USER = os.environ.get("DB_USER", "")          # empty → socket auth as root
DB_PASS = os.environ.get("DB_PASS", "")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_SOCKET = os.environ.get("DB_SOCKET", "/var/lib/mysql/mysql.sock")
MY_CNF = os.environ.get("MY_CNF", "/root/.my.cnf")

MAX_PAGE_SIZE = 100
SENSITIVE_COLUMNS = {
    # never returned by any endpoint, defensively stripped from SELECT * rows
    "email", "email_address", "firstname", "lastname", "name", "phone",
    "phone_number", "mobile", "skype", "password", "pass", "address",
    "skypeid", "yahooid", "mobileno", "landlineno",
}


def _connect() -> pymysql.connections.Connection:
    """Connect via TCP creds if DB_USER is set, else unix socket + /root/.my.cnf."""
    common: dict[str, Any] = dict(
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
    if DB_USER:
        return pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, **common)
    # Default: socket auth as root using ~/.my.cnf (service runs as root on the box)
    return pymysql.connect(
        unix_socket=DB_SOCKET, read_default_file=MY_CNF, user="root", **common
    )


@contextmanager
def db() -> Iterator[pymysql.connections.Connection]:
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Auth + rate limiting
# ---------------------------------------------------------------------------

class ApiKey(BaseModel):
    id: int
    client_user_id: int
    scopes: list[str]
    rate_limit_per_hour: int


_rate_lock = threading.Lock()
_rate_counters: dict[int, tuple[int, int]] = {}  # key_id -> (hour_epoch, count)


def _check_rate_limit(key: ApiKey) -> None:
    hour = int(time.time() // 3600)
    with _rate_lock:
        window, count = _rate_counters.get(key.id, (hour, 0))
        if window != hour:
            window, count = hour, 0
        count += 1
        _rate_counters[key.id] = (window, count)
    if count > key.rate_limit_per_hour:
        raise HTTPException(429, "Rate limit exceeded for this key (per-hour)")


def get_api_key(authorization: Optional[str] = Header(None)) -> ApiKey:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.split(None, 1)[1].strip()
    key_hash = hashlib.sha256(token.encode()).hexdigest()
    with db() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, client_user_id, scopes, rate_limit_per_hour "
            "FROM api_keys WHERE key_hash=%s AND active=1",
            (key_hash,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(401, "Invalid or inactive API key")
        cur.execute("UPDATE api_keys SET last_used=NOW() WHERE id=%s", (row["id"],))
    key = ApiKey(
        id=row["id"],
        client_user_id=row["client_user_id"],
        scopes=[s.strip() for s in (row["scopes"] or "").split(",") if s.strip()],
        rate_limit_per_hour=row["rate_limit_per_hour"] or 300,
    )
    _check_rate_limit(key)
    return key


def require_scope(key: ApiKey, scope: str) -> None:
    if scope not in key.scopes and "*" not in key.scopes:
        raise HTTPException(403, f"Key lacks required scope: {scope}")


# ---------------------------------------------------------------------------
# App + models
# ---------------------------------------------------------------------------

app = FastAPI(title="Outbounders Agent API", version="0.1.0", docs_url="/v1/docs")


class TalentSkills(BaseModel):
    survey: Optional[int] = None
    cold_calling_consumer: Optional[int] = None   # agent_info.skills_ccc
    cold_calling_business: Optional[int] = None   # agent_info.skills_ccb
    upsell: Optional[int] = None
    close_sale: Optional[int] = None


class TalentRecord(BaseModel):
    agent_id: int
    country: Optional[str] = None
    member_since: Optional[int] = None       # year only
    last_active: Optional[str] = None        # bucket: 30d / 90d / 1y / 3y / 3y+
    skills: Optional[TalentSkills] = None    # self-scores from agent_info
    experience_years: Optional[int] = None   # agent_info.work_experience
    night_shift: Optional[bool] = None       # agent_info.work_night
    # No profile-level hourly rate exists; agents propose a rate per application
    # (see job_application.hourly_rate in the applications endpoint).


class TalentResponse(BaseModel):
    count: int
    results: list[TalentRecord]


class JobCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=10, max_length=20000)


class JobCreated(BaseModel):
    job_id: int
    status: str = "pending_approval"  # legacy admin approval gates public visibility


def _last_active_bucket(last_login: Optional[datetime]) -> Optional[str]:
    if not last_login:
        return None
    days = (datetime.now() - last_login).days
    if days <= 30:
        return "30d"
    if days <= 90:
        return "90d"
    if days <= 365:
        return "1y"
    if days <= 3 * 365:
        return "3y"
    return "3y+"


def _strip_sensitive(row: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in row.items() if k.lower() not in SENSITIVE_COLUMNS}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/v1/health")
def health() -> dict[str, Any]:
    try:
        with db() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
        return {"status": "ok", "db": "up", "time": datetime.now().isoformat()}
    except Exception as exc:  # noqa: BLE001 — health must not 500 opaquely
        return {"status": "degraded", "db": f"error: {exc.__class__.__name__}"}


def _as_bool(value: Any) -> Optional[bool]:
    """Normalize Y/N chars or 0/1 ints from legacy flag columns."""
    if value is None:
        return None
    if isinstance(value, str):
        return value.upper() == "Y"
    return bool(value)


@app.get("/v1/talent", response_model=TalentResponse)
def search_talent(
    country_code: Optional[str] = Query(None, max_length=2),
    active_within_days: Optional[int] = Query(None, gt=0, le=3650),
    limit: int = Query(25, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    key: ApiKey = Depends(get_api_key),
) -> TalentResponse:
    require_scope(key, "talent:read")

    # agent_info join VERIFIED 2026-08-10. Only skill scores / experience /
    # shift flags are selected — PII columns (skypeid, yahooid, mobileno,
    # landlineno, file_*) are never queried.
    sql = (
        "SELECT u.user_id, u.country_code, u.date_created, u.last_login, "
        "a.skills_survey, a.skills_ccc, a.skills_ccb, a.skills_upsell, "
        "a.skills_closesale, a.work_experience, a.work_night "
        "FROM main_users u "
        "LEFT JOIN agent_info a ON a.agent_id = u.user_id "
        "WHERE u.account_type='A' AND u.deleted='N' AND u.banned=0"
    )
    params: list[Any] = []
    if country_code:
        sql += " AND u.country_code=%s"
        params.append(country_code.upper())
    if active_within_days is not None:
        sql += " AND u.last_login >= NOW() - INTERVAL %s DAY"
        params.append(active_within_days)
    sql += " ORDER BY u.last_login DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with db() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    results = [
        TalentRecord(
            agent_id=r["user_id"],
            country=r.get("country_code"),
            member_since=r["date_created"].year if r.get("date_created") else None,
            last_active=_last_active_bucket(r.get("last_login")),
            skills=TalentSkills(
                survey=r.get("skills_survey"),
                cold_calling_consumer=r.get("skills_ccc"),
                cold_calling_business=r.get("skills_ccb"),
                upsell=r.get("skills_upsell"),
                close_sale=r.get("skills_closesale"),
            ),
            experience_years=r.get("work_experience"),
            night_shift=_as_bool(r.get("work_night")),
        )
        for r in rows
    ]
    return TalentResponse(count=len(results), results=results)


@app.post("/v1/jobs", response_model=JobCreated, status_code=201)
def create_job(body: JobCreate, key: ApiKey = Depends(get_api_key)) -> JobCreated:
    require_scope(key, "jobs:write")
    # Columns verified 2026-08-10 (PK is `id`). approved='N' keeps the legacy
    # admin-approval flow gating public visibility.
    with db() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO client_job_posting "
            "(user_id, title, `desc`, date_create, active, deleted, approved) "
            "VALUES (%s, %s, %s, NOW(), 'Y', 'N', 'N')",
            (key.client_user_id, body.title, body.description),
        )
        job_id = cur.lastrowid
    return JobCreated(job_id=job_id)


@app.get("/v1/jobs/{job_id}")
def get_job(job_id: int, key: ApiKey = Depends(get_api_key)) -> dict[str, Any]:
    require_scope(key, "jobs:read")
    with db() as conn, conn.cursor() as cur:
        # PK on client_job_posting is `id` (verified 2026-08-10).
        cur.execute(
            "SELECT * FROM client_job_posting WHERE id=%s AND deleted='N'",
            (job_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Job not found")
    return _strip_sensitive(row)


@app.get("/v1/jobs/{job_id}/applications")
def get_applications(
    job_id: int,
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    key: ApiKey = Depends(get_api_key),
) -> dict[str, Any]:
    require_scope(key, "jobs:read")
    with db() as conn, conn.cursor() as cur:
        # FK is job_id (verified 2026-08-10). Rows include the agent's proposed
        # hourly_rate decimal(12,2) — rates are per-application, not per-profile.
        cur.execute(
            "SELECT * FROM job_application WHERE job_id=%s LIMIT %s OFFSET %s",
            (job_id, limit, offset),
        )
        rows = cur.fetchall()
    return {
        "job_id": job_id,
        "count": len(rows),
        "applications": [_strip_sensitive(r) for r in rows],
    }

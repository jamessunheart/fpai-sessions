"""
Zen Village — Team / Workers module.

Stores a roster of people who are part of the Village rhythm: their telegram
ID, role, today's top-3 priorities, blockers, hours available, and last
check-in. JSON-first so the bot has zero-deps reads; mirrors to NocoDB if a
table id is configured.

Public API:
  /api/team/workers              GET   list (optionally filter active=1)
  /api/team/workers              POST  upsert worker (admin token)
  /api/team/workers/{tg_id}      GET   single worker
  /api/team/workers/{tg_id}      DELETE
  /api/team/checkin              POST  record a check-in (top_3, blockers,
                                       hours_today) — bot calls this
  /api/team/active-today         GET   workers who checked in today
  /api/team/blockers             GET   non-empty blockers, freshest first
  /api/team/digest               GET   computed AM/PM digest payload
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import urllib.parse as _uparse
import urllib.request as _ureq
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel, Field

logger = logging.getLogger("zen_village.team")
router = APIRouter()

DATA_DIR = Path("/opt/fpai/apps/zen-village/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
WORKERS_FILE = DATA_DIR / "workers.json"
CHECKINS_FILE = DATA_DIR / "checkins.json"

ADMIN_TOKEN = os.environ.get("ZV_AFFILIATES_ADMIN_TOKEN", "").strip()
NOCODB_URL = os.environ.get("NOCODB_URL", "http://127.0.0.1:8080").rstrip("/")
NOCODB_TOKEN = os.environ.get("NOCODB_API_TOKEN", "")
# Optional tables for Telegram/team data write-back.
NOCODB_WORKERS_TABLE = os.environ.get("NOCODB_WORKERS_TABLE_ID", "")
NOCODB_CHECKINS_TABLE = os.environ.get("NOCODB_CHECKINS_TABLE_ID", "")


# ─── persistence ──────────────────────────────────────────────────────────
def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _save(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(path)


def _noco_upsert(table_id: str, where_field: str, where_value: str, payload: dict) -> None:
    """Best-effort upsert into NocoDB table; never raises."""
    if not (NOCODB_TOKEN and table_id and where_value):
        return
    try:
        where = f"({where_field},eq,{where_value})"
        list_url = f"{NOCODB_URL}/api/v2/tables/{table_id}/records?where={_uparse.quote(where, safe='()%,=')}&limit=1&fields=Id,{where_field}"
        req = _ureq.Request(list_url, headers={"xc-token": NOCODB_TOKEN})
        with _ureq.urlopen(req, timeout=5) as r:
            rows = json.loads(r.read().decode()).get("list") or []
        if rows:
            payload["Id"] = rows[0]["Id"]
            req = _ureq.Request(
                f"{NOCODB_URL}/api/v2/tables/{table_id}/records",
                data=json.dumps([payload]).encode(),
                method="PATCH",
                headers={"xc-token": NOCODB_TOKEN, "Content-Type": "application/json"},
            )
        else:
            req = _ureq.Request(
                f"{NOCODB_URL}/api/v2/tables/{table_id}/records",
                data=json.dumps(payload).encode(),
                method="POST",
                headers={"xc-token": NOCODB_TOKEN, "Content-Type": "application/json"},
            )
        _ureq.urlopen(req, timeout=6).read()
    except Exception as e:
        logger.warning("team noco upsert failed table=%s key=%s: %s", table_id, where_value, e)


def _sync_worker_to_nocodb(worker: dict) -> None:
    if not NOCODB_WORKERS_TABLE:
        return
    payload = {
        "WorkerId": worker.get("telegram_id", ""),
        "Name": worker.get("name", ""),
        "Role": worker.get("role", ""),
        "Status": worker.get("status", "active"),
        "TelegramId": worker.get("telegram_id", ""),
        "Timezone": worker.get("timezone", ""),
        "TargetHours": float(worker.get("hours_per_day_target", 0) or 0),
        "Notes": worker.get("notes", ""),
        "UpdatedAt": worker.get("updated_at") or datetime.utcnow().isoformat(),
    }
    _noco_upsert(NOCODB_WORKERS_TABLE, "WorkerId", payload["WorkerId"], payload)


def _sync_checkin_to_nocodb(checkin: dict, worker: dict | None = None) -> None:
    if not NOCODB_CHECKINS_TABLE:
        return
    worker = worker or get_worker(checkin.get("telegram_id", "")) or {}
    payload = {
        "CheckinId": checkin.get("id", ""),
        "WorkerId": checkin.get("telegram_id", ""),
        "WorkerName": worker.get("name", ""),
        "Role": worker.get("role", ""),
        "Kind": checkin.get("kind", ""),
        "Top3": " | ".join(checkin.get("top_3") or [])[:1000],
        "Blockers": checkin.get("blockers", ""),
        "HoursToday": float(checkin.get("hours_today") or 0),
        "FreeText": checkin.get("free_text", ""),
        "Timestamp": checkin.get("timestamp", ""),
        "Date": checkin.get("date", ""),
        "Status": "Logged",
    }
    _noco_upsert(NOCODB_CHECKINS_TABLE, "CheckinId", payload["CheckinId"], payload)


# ─── auth ─────────────────────────────────────────────────────────────────
def require_admin(x_admin_token: Optional[str] = Header(None)) -> None:
    if not ADMIN_TOKEN or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(401, "Admin token required")


# ─── models ───────────────────────────────────────────────────────────────
class Worker(BaseModel):
    telegram_id: str = Field(..., description="Telegram user id (numeric string)")
    name: str
    role: str = "helper"
    status: str = "active"  # active | paused | offboarded
    timezone: str = "America/Costa_Rica"
    hours_per_day_target: float = 6.0
    notes: str = ""


class CheckIn(BaseModel):
    telegram_id: str
    top_3: List[str] = Field(default_factory=list, description="Up to 3 priorities")
    blockers: str = ""
    hours_today: Optional[float] = None
    free_text: str = ""  # raw original message
    kind: str = "morning"  # morning | evening | adhoc


# ─── helpers ──────────────────────────────────────────────────────────────
def _today() -> str:
    return date.today().isoformat()


def _is_active(w: dict) -> bool:
    return (w.get("status") or "active") == "active"


def _checkin_iso_today(c: dict) -> bool:
    ts = c.get("timestamp") or ""
    return ts[:10] == _today()


def get_worker(tg_id: str) -> Optional[dict]:
    return _load(WORKERS_FILE).get(str(tg_id))


def list_workers(active: bool = True) -> List[dict]:
    rows = list(_load(WORKERS_FILE).values())
    if active:
        rows = [w for w in rows if _is_active(w)]
    return sorted(rows, key=lambda w: w.get("name", ""))


def upsert_worker(w: Worker) -> dict:
    workers = _load(WORKERS_FILE)
    existing = workers.get(w.telegram_id, {})
    record = {
        **existing,
        "telegram_id": str(w.telegram_id),
        "name": w.name.strip(),
        "role": w.role.strip(),
        "status": w.status.strip(),
        "timezone": w.timezone.strip(),
        "hours_per_day_target": float(w.hours_per_day_target),
        "notes": (w.notes or "").strip(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    record.setdefault("created_at", datetime.utcnow().isoformat())
    workers[w.telegram_id] = record
    _save(WORKERS_FILE, workers)
    _sync_worker_to_nocodb(record)
    return record


def remove_worker(tg_id: str) -> bool:
    workers = _load(WORKERS_FILE)
    if tg_id in workers:
        del workers[tg_id]
        _save(WORKERS_FILE, workers)
        return True
    return False


def record_checkin(c: CheckIn) -> dict:
    checkins = _load(CHECKINS_FILE)
    cid = f"chk_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(3)}"
    record = {
        "id": cid,
        "telegram_id": str(c.telegram_id),
        "top_3": [s for s in (c.top_3 or []) if s][:3],
        "blockers": (c.blockers or "").strip(),
        "hours_today": c.hours_today,
        "free_text": (c.free_text or "").strip()[:2000],
        "kind": (c.kind or "morning").strip(),
        "timestamp": datetime.utcnow().isoformat(),
        "date": _today(),
    }
    checkins[cid] = record
    _save(CHECKINS_FILE, checkins)
    _sync_checkin_to_nocodb(record, worker=get_worker(record["telegram_id"]))
    return record


def latest_checkin_for(tg_id: str, on_date: Optional[str] = None) -> Optional[dict]:
    """Most recent check-in for a worker (optionally filtered to a date)."""
    rows = [
        c for c in _load(CHECKINS_FILE).values()
        if str(c.get("telegram_id")) == str(tg_id)
        and (on_date is None or c.get("date") == on_date)
    ]
    if not rows:
        return None
    return max(rows, key=lambda c: c.get("timestamp", ""))


def workers_active_today() -> List[dict]:
    """Workers who have a check-in today."""
    today = _today()
    out: list[dict] = []
    for w in list_workers():
        c = latest_checkin_for(w["telegram_id"], today)
        if c:
            out.append({**w, "_checkin": c})
    return out


def workers_quiet_for(days: int = 2) -> List[dict]:
    """Active workers with no check-in in the last N days."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    out: list[dict] = []
    for w in list_workers():
        c = latest_checkin_for(w["telegram_id"])
        if not c or (c.get("date") or "") < cutoff:
            out.append({**w, "_last_checkin": c})
    return out


def all_blockers_today() -> List[dict]:
    today = _today()
    out: list[dict] = []
    for w in list_workers():
        c = latest_checkin_for(w["telegram_id"], today)
        if c and (c.get("blockers") or "").strip():
            out.append({"worker": w, "checkin": c})
    return out


def compute_digest() -> dict:
    """The 8am / 6pm summary payload. UI-friendly strings included."""
    active = workers_active_today()
    quiet = workers_quiet_for(2)
    blockers = all_blockers_today()
    total_hours = sum(
        float(w.get("_checkin", {}).get("hours_today") or 0)
        for w in active
    )

    def _line(w: dict) -> str:
        c = w.get("_checkin", {}) or {}
        top = c.get("top_3") or []
        topline = " · ".join(top[:3]) if top else "(no priorities given)"
        h = c.get("hours_today")
        hours = f"{h:g}h" if isinstance(h, (int, float)) else "—"
        return f"<b>{w.get('name','?')}</b> ({hours}) — {topline}"

    return {
        "date": _today(),
        "active_count": len(active),
        "quiet_count": len(quiet),
        "blocker_count": len(blockers),
        "total_hours_today": round(total_hours, 1),
        "active_workers": [_line(w) for w in active],
        "blockers_lines": [
            f"<b>{b['worker']['name']}</b>: {b['checkin']['blockers']}"
            for b in blockers
        ],
        "quiet_workers": [
            {"name": w["name"], "telegram_id": w["telegram_id"],
             "last_seen": (w.get("_last_checkin") or {}).get("date") or "never"}
            for w in quiet
        ],
    }


# ─── HTTP endpoints ────────────────────────────────────────────────────────
@router.get("/workers")
async def http_list_workers(active: int = 1):
    return {"workers": list_workers(active=bool(active))}


@router.post("/workers", dependencies=[Depends(require_admin)])
async def http_upsert_worker(w: Worker):
    return {"worker": upsert_worker(w), "status": "ok"}


@router.get("/workers/{telegram_id}")
async def http_get_worker(telegram_id: str):
    w = get_worker(telegram_id)
    if not w:
        raise HTTPException(404, "Worker not found")
    return {"worker": w, "today": latest_checkin_for(telegram_id, _today())}


@router.delete("/workers/{telegram_id}", dependencies=[Depends(require_admin)])
async def http_delete_worker(telegram_id: str):
    return {"removed": remove_worker(telegram_id)}


@router.post("/checkin")
async def http_checkin(c: CheckIn):
    if not get_worker(c.telegram_id):
        raise HTTPException(404, "Worker not registered. Admin must add them first.")
    return {"checkin": record_checkin(c), "status": "ok"}


@router.get("/active-today")
async def http_active_today():
    return {"active": workers_active_today(), "date": _today()}


@router.get("/blockers")
async def http_blockers():
    return {"blockers": all_blockers_today(), "date": _today()}


@router.get("/quiet")
async def http_quiet(days: int = Query(2, ge=1, le=14)):
    return {"quiet": workers_quiet_for(days), "days": days}


@router.get("/digest")
async def http_digest():
    return compute_digest()


@router.get("/source-status")
async def http_source_status():
    return {
        "local": {
            "workers_file": str(WORKERS_FILE),
            "checkins_file": str(CHECKINS_FILE),
            "workers_count": len(_load(WORKERS_FILE)),
            "checkins_count": len(_load(CHECKINS_FILE)),
        },
        "nocodb": {
            "enabled": bool(NOCODB_TOKEN),
            "url": NOCODB_URL if NOCODB_TOKEN else "",
            "workers_table_configured": bool(NOCODB_WORKERS_TABLE),
            "checkins_table_configured": bool(NOCODB_CHECKINS_TABLE),
        },
    }

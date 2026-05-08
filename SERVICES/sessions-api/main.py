"""sessions-api — track active Claude / dev sessions across projects.

A tiny FastAPI service that any Claude session (or dev workspace) can
push state to. Returns a list for the founder's "what am I in the
middle of?" Telegram view.

The Game plays itself, signal layer extension: each session announces
its own state without the founder needing to query me.

Endpoints:
  POST /update      — push session state for a project
  GET  /list        — return all known session states (sorted by recency)
  GET  /project/{slug} — return state for one project
  GET  /health

Storage:
  /var/lib/full-potential/sessions/{project-slug}.json

Privacy:
  - Session states may include project paths; treat as low-sensitivity
    but not public-broadcastable. The /list endpoint requires a token
    matching SESSIONS_TOKEN env var (so only the founder + bot see it).
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

DATA_DIR = Path(os.environ.get("SESSIONS_DATA_DIR", "/var/lib/full-potential/sessions"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
TOKEN = os.environ.get("SESSIONS_TOKEN", "").strip()  # if empty, /list and /update are open (dev mode)

app = FastAPI(title="Sessions API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*", "X-Sessions-Token"],
)


def _check_token(token: Optional[str]) -> None:
    if TOKEN and token != TOKEN:
        raise HTTPException(status_code=401, detail="invalid token")


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "unknown"


class SessionUpdate(BaseModel):
    project: str = Field(..., min_length=1, max_length=80)
    cwd: Optional[str] = Field(None, max_length=400)
    quest: Optional[str] = Field(None, max_length=400)
    next_move: Optional[str] = Field(None, max_length=400)
    status: Optional[str] = Field("active", max_length=24)  # active | paused | complete | blocked
    loop_number: Optional[int] = None
    highlights: Optional[list[str]] = Field(default_factory=list)
    branch: Optional[str] = Field(None, max_length=120)
    last_commit: Optional[str] = Field(None, max_length=200)

    @validator("project", "quest", "next_move", "branch")
    def _no_html(cls, v):
        if v is None:
            return v
        if re.search(r"[<>]", v):
            raise ValueError("contains forbidden characters")
        return v.strip()


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "data_dir": str(DATA_DIR), "sessions": _count()}


@app.post("/update")
async def update_session(
    req: SessionUpdate,
    x_sessions_token: Optional[str] = Header(None),
) -> dict:
    _check_token(x_sessions_token)
    slug = _slug(req.project)
    out = DATA_DIR / f"{slug}.json"
    now = datetime.now().isoformat()
    existing: dict = {}
    if out.exists():
        try:
            existing = json.loads(out.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    state = {
        **existing,
        "project": req.project,
        "slug": slug,
        "cwd": req.cwd,
        "quest": req.quest,
        "next_move": req.next_move,
        "status": req.status or "active",
        "loop_number": req.loop_number,
        "highlights": req.highlights or [],
        "branch": req.branch,
        "last_commit": req.last_commit,
        "started_at": existing.get("started_at", now),
        "last_activity": now,
    }
    out.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"ok": True, "slug": slug, "state": state}


@app.get("/list")
async def list_sessions(
    x_sessions_token: Optional[str] = Header(None),
) -> dict:
    _check_token(x_sessions_token)
    sessions = []
    for p in DATA_DIR.glob("*.json"):
        try:
            sessions.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    sessions.sort(key=lambda s: s.get("last_activity", ""), reverse=True)
    return {"count": len(sessions), "sessions": sessions}


@app.get("/project/{slug}")
async def get_session(
    slug: str,
    x_sessions_token: Optional[str] = Header(None),
) -> dict:
    _check_token(x_sessions_token)
    out = DATA_DIR / f"{slug}.json"
    if not out.exists():
        raise HTTPException(status_code=404, detail="not found")
    return json.loads(out.read_text(encoding="utf-8"))


def _count() -> int:
    return sum(1 for _ in DATA_DIR.glob("*.json"))

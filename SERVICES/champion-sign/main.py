"""champion-sign — webhook that receives World Peace Agreement signatures.

A tiny FastAPI service. Receives a POST from the Sign-the-Agreement form
on https://fullpotential.com/game, validates, writes the signed Champion
markdown file, and returns the assigned Champion number.

The Game plays itself: signatures land directly in the substrate. No
founder in the loop for the manual-commit step.

Endpoints:
  POST /sign   — receive a signature
  GET  /list   — return JSON of public Champions

Storage:
  /var/lib/full-potential/champions/{YYYY-MM-DD}_{slug}.md
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

DATA_DIR = Path(os.environ.get("CHAMPION_DATA_DIR", "/var/lib/full-potential/champions"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Champion Sign", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://fullpotential.com",
        "https://www.fullpotential.com",
        "https://fullpotential.ai",
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Simple in-memory rate limiter: 3 signs per IP per hour
_rate_log: dict[str, list[float]] = {}
RATE_WINDOW = 3600
RATE_LIMIT = 3


def _check_rate(ip: str) -> bool:
    now = time.time()
    history = _rate_log.get(ip, [])
    history = [t for t in history if now - t < RATE_WINDOW]
    if len(history) >= RATE_LIMIT:
        _rate_log[ip] = history
        return False
    history.append(now)
    _rate_log[ip] = history
    return True


class SignRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    handle: Optional[str] = Field(None, max_length=60)
    email: Optional[str] = Field(None, max_length=120)
    witness: Optional[str] = Field(None, max_length=120)
    public: bool = True
    why: Optional[str] = Field(None, max_length=2000)
    # Honeypot — bots fill this; humans don't see it
    company: Optional[str] = Field(None, max_length=120)

    @validator("name", "handle", "email", "witness")
    def _no_html(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if re.search(r"[<>]", v):
            raise ValueError("contains forbidden characters")
        return v.strip()


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "data_dir": str(DATA_DIR), "champions": _count_champions()}


@app.post("/sign")
async def sign(req: SignRequest, request: Request) -> dict:
    # Honeypot — silently accept but don't write
    if req.company:
        return {"ok": True, "champion_number": 0, "honeypot": True}

    ip = request.client.host if request.client else "unknown"
    if not _check_rate(ip):
        raise HTTPException(status_code=429, detail="Too many signatures from this address. Try again later.")

    today = datetime.now().strftime("%Y-%m-%d")
    slug = re.sub(r"[^a-z0-9]+", "-", req.name.lower()).strip("-") or "unnamed"
    fname = f"{today}_{slug}.md"
    out = DATA_DIR / fname

    # If a same-named signature exists today, suffix
    if out.exists():
        for i in range(2, 100):
            alt = DATA_DIR / f"{today}_{slug}-{i}.md"
            if not alt.exists():
                out = alt
                break

    champion_number = _count_champions() + 1

    md = _render_md(req, champion_number, today)
    out.write_text(md, encoding="utf-8")

    # Append to a JSON-lines audit log
    audit = DATA_DIR / "audit.jsonl"
    with audit.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.now().isoformat(),
            "champion_number": champion_number,
            "name": req.name,
            "public": req.public,
            "ip": ip,
            "filename": fname,
        }) + "\n")

    return {
        "ok": True,
        "champion_number": champion_number,
        "filename": fname,
        "message": f"Welcome, {req.name.split()[0]}. You are Coherent Champion #{champion_number}.",
    }


@app.get("/list")
async def list_champions() -> dict:
    """Return JSON of all PUBLIC champions, ordered by champion_number."""
    champions = []
    for p in sorted(DATA_DIR.glob("*.md")):
        try:
            text = p.read_text(encoding="utf-8")
            fm = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
            if not fm:
                continue
            data: dict = {}
            for line in fm.group(1).split("\n"):
                m = re.match(r"^([a-z_]+):\s*(.*)$", line)
                if m:
                    key, val = m.group(1), m.group(2).strip().strip('"')
                    if val.lower() == "true":
                        val = True
                    elif val.lower() == "false":
                        val = False
                    data[key] = val
            if not data.get("public"):
                continue
            # Strip email for privacy on public roll
            data.pop("email", None)
            champions.append(data)
        except Exception:
            continue
    champions.sort(key=lambda c: int(c.get("champion_number", 99999)) if str(c.get("champion_number", "")).isdigit() else 99999)
    return {"count": len(champions), "champions": champions}


def _count_champions() -> int:
    return sum(1 for p in DATA_DIR.glob("*.md") if not p.name.startswith("."))


def _render_md(req: SignRequest, num: int, today: str) -> str:
    name = req.name
    why_block = f"\n## Why I am signing\n\n{req.why}\n" if req.why else ""
    return f"""---
champion_id: {today}_{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}
champion_number: {num}
date_signed: {today}
name: {name}
handle: {req.handle or ''}
email: {req.email or ''}
witness: {req.witness or ''}
public: {str(req.public).lower()}
status: signed
manifesto_version: v1.0
source: webhook
---

# Coherent Champion #{num} — {name}

I, **{name}**, having read the Coherent Champions of CHRIST Manifesto v1.0, sign the World Peace Agreement.

## I agree

- to practice peace in thought, word, and action
- to reduce unnecessary suffering
- to seek understanding before hatred
- to repair where I have caused harm
- to protect life, truth, beauty, and future generations
- to become trustworthy with intelligence, influence, and resources
- that peace must become visible through action

*Signed not in perfection, but in sincere participation.*
{why_block}
## Witness

{req.witness or '(no witness named at signing)'}

## Visibility

This signature is **{'PUBLIC' if req.public else 'PRIVATE'}** — {'I consent to appearing on the public Champions Roll.' if req.public else 'private signing; not listed publicly.'}

---

*Date: {today}*
*Source: webhook signature at https://fullpotential.com/game*
"""

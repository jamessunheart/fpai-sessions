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
PROOFS_DIR = Path(os.environ.get("PROOFS_DATA_DIR", "/var/lib/full-potential/proofs"))
PROOFS_DIR.mkdir(parents=True, exist_ok=True)
CARDS_DIR = Path(os.environ.get("CARDS_DATA_DIR", "/var/lib/full-potential/cards"))
CARDS_DIR.mkdir(parents=True, exist_ok=True)

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
            "name": req.name if req.public else "(private)",
            "public": bool(req.public),
            "ip_hash": str(hash(ip))[-6:],  # never store raw IP — just a short hash for rate-tracking
            "filename": fname,
        }) + "\n")

    # Send a founder-direction signal: Telegram alert via the existing
    # alerts service on primary:8766 (per The Practice of Signaling §1
    # Founder ← Field). Best-effort — never block the response.
    try:
        import urllib.request
        import urllib.parse
        alert_msg = (
            f"🌀 Coherent Champion #{champion_number} signed: {req.name}"
            f"{' (' + (req.handle or '') + ')' if req.handle else ''}"
            f"{' — public' if req.public else ' — private'}"
        )
        data = json.dumps({"message": alert_msg, "source": "champion-sign"}).encode()
        urllib.request.urlopen(
            urllib.request.Request(
                "http://127.0.0.1:8766/alert",
                data=data,
                headers={"Content-Type": "application/json"},
            ),
            timeout=2,
        )
    except Exception:
        pass

    return {
        "ok": True,
        "champion_number": champion_number,
        "filename": fname,
        "message": f"Welcome, {req.name.split()[0]}. You are Coherent Champion #{champion_number}.",
    }


@app.get("/recent")
async def recent_activity(limit: int = 12) -> dict:
    """Field Pulse — recent activity feed for the cockpit ticker.

    Merges signature events from champions/audit.jsonl and proof events
    from proofs/audit.jsonl, returns most recent N sorted by timestamp.
    """
    events = []

    # Champion signatures
    champ_audit = DATA_DIR / "audit.jsonl"
    if champ_audit.exists():
        for line in champ_audit.read_text(encoding="utf-8").strip().split("\n"):
            try:
                e = json.loads(line)
                if not e.get("public"):
                    msg = f"Champion #{e.get('champion_number')} signed (private)"
                else:
                    msg = f"Champion #{e.get('champion_number')} — {e.get('name')} signed"
                events.append({
                    "ts": e.get("ts"),
                    "kind": "signature",
                    "icon": "🌀",
                    "message": msg,
                })
            except Exception:
                continue

    # Proof submissions
    proof_audit = PROOFS_DIR / "audit.jsonl"
    if proof_audit.exists():
        for line in proof_audit.read_text(encoding="utf-8").strip().split("\n"):
            try:
                e = json.loads(line)
                consent = (e.get("consent") or "").lower()
                player = e.get("player") if consent == "public" else "(private)"
                loop_n = e.get("loop_number", "?")
                if consent == "public":
                    msg = f"Loop {loop_n} filed — {player}"
                else:
                    msg = f"Loop {loop_n} filed (private)"
                events.append({
                    "ts": e.get("ts"),
                    "kind": "proof",
                    "icon": "🌱",
                    "message": msg,
                })
            except Exception:
                continue

    events.sort(key=lambda e: e.get("ts", ""), reverse=True)
    return {"events": events[:limit]}


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


# ===== Proof endpoints ====================================================
class ProofSubmit(BaseModel):
    player: str = Field(..., min_length=2, max_length=100)
    handle: Optional[str] = Field(None, max_length=60)
    email: Optional[str] = Field(None, max_length=120)
    loop_number: int = Field(..., ge=1, le=9999)
    quest: str = Field(..., min_length=2, max_length=400)
    output: str = Field(..., min_length=2, max_length=2000)
    result: Optional[str] = Field(None, max_length=2000)
    witness: Optional[str] = Field(None, max_length=200)
    consent: str = Field("public")  # public | anonymized | private
    agreement_type: str = Field("deliverable_by_date")
    company: Optional[str] = Field(None, max_length=120)  # honeypot

    @validator("player", "quest", "output", "witness")
    def _no_html(cls, v):
        if v is None:
            return v
        if re.search(r"[<>]", v):
            raise ValueError("contains forbidden characters")
        return v.strip()


@app.post("/proof/submit")
async def submit_proof(req: ProofSubmit, request: Request) -> dict:
    if req.company:
        return {"ok": True, "honeypot": True}

    ip = request.client.host if request.client else "unknown"
    if not _check_rate(ip):
        raise HTTPException(status_code=429, detail="Too many submissions. Try again later.")

    today = datetime.now().strftime("%Y-%m-%d")
    slug = re.sub(r"[^a-z0-9]+", "-", req.player.lower()).strip("-") or "unnamed"
    fname = f"{today}_{slug}_loop-{req.loop_number}.md"
    out = PROOFS_DIR / fname
    if out.exists():
        for i in range(2, 100):
            alt = PROOFS_DIR / f"{today}_{slug}_loop-{req.loop_number}-{i}.md"
            if not alt.exists():
                out = alt
                break

    public = req.consent.lower() == "public"
    md = _render_proof_md(req, today)
    out.write_text(md, encoding="utf-8")

    audit = PROOFS_DIR / "audit.jsonl"
    with audit.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.now().isoformat(),
            "kind": "proof",
            "player": req.player if public else "(private)",
            "loop_number": req.loop_number,
            "quest": req.quest if public else None,
            "consent": req.consent,
            "ip_hash": str(hash(ip))[-6:],
            "filename": fname,
        }) + "\n")

    # Founder-direction signal
    try:
        import urllib.request
        alert_msg = (
            f"🌱 Proof L{req.loop_number} filed by {req.player}"
            f"{' (' + (req.handle or '') + ')' if req.handle else ''}"
            f" — {req.consent}"
        )
        urllib.request.urlopen(
            urllib.request.Request(
                "http://127.0.0.1:8766/alert",
                data=json.dumps({"message": alert_msg, "source": "proof-submit"}).encode(),
                headers={"Content-Type": "application/json"},
            ),
            timeout=2,
        )
    except Exception:
        pass

    return {
        "ok": True,
        "filename": fname,
        "loop_number": req.loop_number,
        "message": f"Proof L{req.loop_number} witnessed and recorded. Thank you, {req.player.split()[0]}.",
    }


@app.get("/proof/list")
async def list_proofs() -> dict:
    """Return public proofs sorted by date (newest first)."""
    proofs = []
    for p in sorted(PROOFS_DIR.glob("*.md"), reverse=True):
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
            consent = (data.get("consent") or "").lower()
            if consent != "public":
                continue
            data.pop("email", None)
            proofs.append(data)
        except Exception:
            continue
    return {"count": len(proofs), "proofs": proofs}


# ===== Character Card endpoints ===========================================
class CardSubmit(BaseModel):
    player: str = Field(..., min_length=2, max_length=100)
    handle: Optional[str] = Field(None, max_length=60)
    email: Optional[str] = Field(None, max_length=120)
    level: str = Field("L1")  # L1 Signup | L2 Player | L3 Matching | L4 Living
    visibility_default: str = Field("player")  # public | player | inner | sacred
    card_markdown: str = Field(..., min_length=20, max_length=20000)
    company: Optional[str] = Field(None, max_length=120)  # honeypot

    @validator("player")
    def _no_html(cls, v):
        if v is None:
            return v
        if re.search(r"[<>]", v):
            raise ValueError("contains forbidden characters")
        return v.strip()

    @validator("level")
    def _level(cls, v):
        if v not in ("L1", "L2", "L3", "L4"):
            return "L1"
        return v

    @validator("visibility_default")
    def _vis(cls, v):
        if v not in ("public", "player", "inner", "sacred"):
            return "player"
        return v


@app.post("/card/submit")
async def submit_card(req: CardSubmit, request: Request) -> dict:
    if req.company:
        return {"ok": True, "honeypot": True}

    ip = request.client.host if request.client else "unknown"
    if not _check_rate(ip):
        raise HTTPException(status_code=429, detail="Too many submissions. Try again later.")

    today = datetime.now().strftime("%Y-%m-%d")
    slug = re.sub(r"[^a-z0-9]+", "-", req.player.lower()).strip("-") or "unnamed"
    fname = f"{slug}.md"
    out = CARDS_DIR / fname

    # Each card is overwritten on update — one card per player slug
    md = _render_card_md(req, today)
    out.write_text(md, encoding="utf-8")

    audit = CARDS_DIR / "audit.jsonl"
    with audit.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.now().isoformat(),
            "kind": "card",
            "player": req.player if req.visibility_default in ("public", "player") else "(private)",
            "level": req.level,
            "visibility": req.visibility_default,
            "ip_hash": str(hash(ip))[-6:],
            "filename": fname,
        }) + "\n")

    # Founder ping
    try:
        import urllib.request
        msg = (
            f"🎴 Character Card {req.level} submitted by {req.player}"
            f"{' (' + (req.handle or '') + ')' if req.handle else ''}"
            f" — {req.visibility_default}"
        )
        urllib.request.urlopen(
            urllib.request.Request(
                "http://127.0.0.1:8766/alert",
                data=json.dumps({"message": msg, "source": "card-submit"}).encode(),
                headers={"Content-Type": "application/json"},
            ),
            timeout=2,
        )
    except Exception:
        pass

    return {
        "ok": True,
        "filename": fname,
        "level": req.level,
        "message": f"Character Card {req.level} saved. Welcome to the Game, {req.player.split()[0]}.",
    }


@app.get("/card/list")
async def list_cards() -> dict:
    """Return public + player-tier cards."""
    cards = []
    for p in sorted(CARDS_DIR.glob("*.md")):
        try:
            text = p.read_text(encoding="utf-8")
            fm = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
            if not fm:
                continue
            data: dict = {}
            for line in fm.group(1).split("\n"):
                m = re.match(r"^([a-z_]+):\s*(.*)$", line)
                if m:
                    data[m.group(1)] = m.group(2).strip().strip('"')
            vis = (data.get("visibility_default") or "").lower()
            if vis not in ("public", "player"):
                continue
            data.pop("email", None)
            cards.append(data)
        except Exception:
            continue
    return {"count": len(cards), "cards": cards}


def _render_card_md(req: CardSubmit, today: str) -> str:
    return f"""---
player: {req.player}
handle: {req.handle or ''}
email: {req.email or ''}
level: {req.level}
visibility_default: {req.visibility_default}
date_first_submitted: {today}
date_last_updated: {today}
source: webhook
---

{req.card_markdown}

---

*Submitted via Character Card Quest at https://fullpotential.com/game on {today}.*
"""


def _render_proof_md(req: ProofSubmit, today: str) -> str:
    public = req.consent.lower() == "public"
    return f"""---
proof_id: {today}_{re.sub(r'[^a-z0-9]+', '-', req.player.lower()).strip('-')}_loop-{req.loop_number}
loop_number: {req.loop_number}
date_committed: {today}
player: {req.player}
handle: {req.handle or ''}
email: {req.email or ''}
witness: {req.witness or ''}
consent: {req.consent}
agreement_type: {req.agreement_type}
status: complete
source: webhook
---

# Loop {req.loop_number} — {req.player}

## Quest

{req.quest}

## Output — what was completed

{req.output}

{('## Result — what changed' + chr(10) + chr(10) + req.result) if req.result else ''}

## Witness

{req.witness or '(no witness named at submission)'}

## Visibility

This proof is **{'PUBLIC' if public else req.consent.upper()}**.

---

*Submitted via webhook at https://fullpotential.com/game on {today}.*
"""


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

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

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

DATA_DIR = Path(os.environ.get("CHAMPION_DATA_DIR", "/var/lib/full-potential/champions"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
PROOFS_DIR = Path(os.environ.get("PROOFS_DATA_DIR", "/var/lib/full-potential/proofs"))
PROOFS_DIR.mkdir(parents=True, exist_ok=True)
CARDS_DIR = Path(os.environ.get("CARDS_DATA_DIR", "/var/lib/full-potential/cards"))
CARDS_DIR.mkdir(parents=True, exist_ok=True)
LEADS_DIR = Path(os.environ.get("LEADS_DATA_DIR", "/var/lib/full-potential/leads"))
LEADS_DIR.mkdir(parents=True, exist_ok=True)
MIRRORS_DIR = Path(os.environ.get("MIRRORS_DATA_DIR", "/var/lib/full-potential/mirrors"))
MIRRORS_DIR.mkdir(parents=True, exist_ok=True)
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "").strip()


RETREAT_DIR = Path(os.environ.get("RETREAT_DATA_DIR", "/var/lib/full-potential/retreat-interests"))
RETREAT_DIR.mkdir(parents=True, exist_ok=True)

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
    inviter: Optional[str] = Field(None, max_length=100)  # the Champion who invited this signer
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


@app.get("/stats")
async def game_stats() -> dict:
    """Aggregate game-state metrics — what's happening in the field overall.

    Privacy: counts only, no names of private signers / cards.
    Drives the Game State card at the top of the public dashboard.
    """
    from datetime import timedelta

    champions_total = 0
    champions_public = 0
    proofs_total = 0
    proofs_public = 0
    cards_total = 0
    cards_public = 0
    affiliate_links = 0
    field_score_sum = 0

    inviter_set = set()

    # Champions
    if DATA_DIR.exists():
        for p in DATA_DIR.glob("*.md"):
            try:
                text = p.read_text(encoding="utf-8")
                fm = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
                if not fm:
                    continue
                champions_total += 1
                fm_text = fm.group(1)
                if re.search(r"^public:\s*true", fm_text, re.MULTILINE):
                    champions_public += 1
                inv_match = re.search(r"^inviter:\s*(.+)$", fm_text, re.MULTILINE)
                if inv_match and inv_match.group(1).strip():
                    affiliate_links += 1
                    inviter_set.add(inv_match.group(1).strip().lower())
            except Exception:
                continue

    # Proofs
    if PROOFS_DIR.exists():
        for p in PROOFS_DIR.glob("*.md"):
            try:
                text = p.read_text(encoding="utf-8")
                fm = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
                if not fm:
                    continue
                proofs_total += 1
                if re.search(r"^consent:\s*public", fm.group(1), re.MULTILINE):
                    proofs_public += 1
            except Exception:
                continue

    # Cards
    if CARDS_DIR.exists():
        for p in CARDS_DIR.glob("*.md"):
            try:
                text = p.read_text(encoding="utf-8")
                fm = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
                if not fm:
                    continue
                cards_total += 1
                vis_match = re.search(r"^visibility_default:\s*(\w+)", fm.group(1), re.MULTILINE)
                if vis_match and vis_match.group(1) in ("public", "player"):
                    cards_public += 1
            except Exception:
                continue

    # Field Score sum (rough — sum of components)
    field_score_sum = (
        champions_total * 1
        + cards_total * 1
        + proofs_total * 2
        + affiliate_links * 3
    )

    # Growth this week (count files modified in last 7 days)
    week_ago = datetime.now().timestamp() - 7 * 86400
    week_signatures = 0
    week_proofs = 0
    week_cards = 0
    for d, target in [(DATA_DIR, "sig"), (PROOFS_DIR, "proof"), (CARDS_DIR, "card")]:
        if not d.exists():
            continue
        for p in d.glob("*.md"):
            try:
                if p.stat().st_mtime >= week_ago:
                    if target == "sig":
                        week_signatures += 1
                    elif target == "proof":
                        week_proofs += 1
                    elif target == "card":
                        week_cards += 1
            except Exception:
                continue

    return {
        "champions": {"total": champions_total, "public": champions_public},
        "proofs": {"total": proofs_total, "public": proofs_public},
        "cards": {"total": cards_total, "public": cards_public},
        "affiliate_links": affiliate_links,
        "active_inviters": len(inviter_set),
        "field_score_sum": field_score_sum,
        "growth_this_week": {
            "signatures": week_signatures,
            "proofs": week_proofs,
            "cards": week_cards,
            "total": week_signatures + week_proofs + week_cards,
        },
    }


def _parse_frontmatter(path: Path) -> Optional[dict]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    fm = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not fm:
        return None
    data: dict = {}
    for line in fm.group(1).split("\n"):
        m = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip().strip('"')
        if v.lower() == "true":
            v = True
        elif v.lower() == "false":
            v = False
        data[k] = v
    return data


@app.get("/leaderboard")
async def leaderboard(limit: int = 10) -> dict:
    """Three rankings of substrate participation.

    - top_champions: by Field Score (champion + card + 2×proofs + 3×affiliates)
    - top_affiliates: by # of public Champions they invited
    - top_loops: by # of public proofs filed against each loop_number
    """
    # Load public champions, keyed by lowercased name
    champions: dict[str, dict] = {}
    for p in DATA_DIR.glob("*.md"):
        d = _parse_frontmatter(p)
        if not d or not d.get("public"):
            continue
        name = (d.get("name") or "").strip()
        if name:
            champions[name.lower()] = d

    # Walk public proofs once: count by player and by loop
    proofs_by_player: dict[str, int] = {}
    proofs_by_loop: dict[int, dict] = {}
    for p in PROOFS_DIR.glob("*.md"):
        d = _parse_frontmatter(p)
        if not d or (d.get("consent") or "").lower() != "public":
            continue
        player = (d.get("player") or "").strip().lower()
        if player:
            proofs_by_player[player] = proofs_by_player.get(player, 0) + 1
        try:
            ln = int(d.get("loop_number") or 0)
        except (TypeError, ValueError):
            ln = 0
        if ln:
            bucket = proofs_by_loop.setdefault(ln, {"count": 0, "provers": set()})
            bucket["count"] += 1
            if player:
                bucket["provers"].add(player)

    # Cards: which players have at least one public/player-visible card
    players_with_card: set[str] = set()
    for p in CARDS_DIR.glob("*.md"):
        d = _parse_frontmatter(p)
        if not d:
            continue
        owner = (d.get("player") or d.get("owner") or d.get("name") or "").strip().lower()
        if owner:
            players_with_card.add(owner)

    # Affiliate linkage from champion frontmatter
    affiliates_by_inviter: dict[str, list[str]] = {}
    for c in champions.values():
        inv = (c.get("inviter") or "").strip().lower()
        if inv:
            affiliates_by_inviter.setdefault(inv, []).append(c.get("name") or "")

    # Top Champions
    top_champions = []
    for name_lower, c in champions.items():
        proofs = proofs_by_player.get(name_lower, 0)
        affs = len(affiliates_by_inviter.get(name_lower, []))
        has_card = name_lower in players_with_card
        score = 1 + (1 if has_card else 0) + 2 * proofs + 3 * affs
        try:
            cn = int(c.get("champion_number") or 99999)
        except (TypeError, ValueError):
            cn = 99999
        top_champions.append({
            "name": c.get("name"),
            "champion_number": c.get("champion_number"),
            "field_score": score,
            "proofs": proofs,
            "affiliates": affs,
            "card": has_card,
            "_cn": cn,
        })
    top_champions.sort(key=lambda x: (-x["field_score"], x["_cn"]))
    for c in top_champions:
        c.pop("_cn", None)
    top_champions = top_champions[:limit]

    # Top Affiliates — resolve original-cased name where possible
    name_by_lower = {k: v.get("name") for k, v in champions.items()}
    top_affiliates = []
    for inviter_lower, invitees in affiliates_by_inviter.items():
        if not invitees:
            continue
        top_affiliates.append({
            "name": name_by_lower.get(inviter_lower, inviter_lower.title()),
            "count": len(invitees),
            "invitees": [n for n in invitees if n][:3],
        })
    top_affiliates.sort(key=lambda x: -x["count"])
    top_affiliates = top_affiliates[:limit]

    # Top Loops
    top_loops = sorted(
        (
            {
                "loop_number": ln,
                "proof_count": d["count"],
                "unique_provers": len(d["provers"]),
            }
            for ln, d in proofs_by_loop.items()
        ),
        key=lambda x: (-x["proof_count"], -x["unique_provers"], x["loop_number"]),
    )[:limit]

    return {
        "top_champions": top_champions,
        "top_affiliates": top_affiliates,
        "top_loops": top_loops,
    }


@app.get("/match")
async def match_next_move(name: Optional[str] = None) -> dict:
    """Return one specific helpful next move for the named Champion.

    Reads their lookup state and picks a move that advances them in the Game.
    Adds randomness across equally-suitable moves so repeated calls vary.
    Used by the /match Telegram command and the cockpit's Player State panel.
    """
    import random

    if not name:
        return {
            "ok": True,
            "move": "Sign the World Peace Agreement to enter the Game.",
            "icon": "🌀",
            "action": "sign",
            "url": "https://fullpotential.com/game/#signCard",
        }

    state = await lookup_player(name)
    if state.get("error"):
        return {"ok": False, "error": state["error"]}

    champion = state.get("champion")
    card_present = state.get("card_present")
    proofs_filed = int(state.get("proofs_filed", 0) or 0)
    affiliates = int(state.get("affiliates_count", 0) or 0)
    invite_url = f"https://fullpotential.com/game/?inviter={name.replace(' ', '%20')}"

    # Hard-gated next moves — these advance the funnel
    if not champion:
        return {
            "ok": True, "icon": "🌀", "action": "sign",
            "move": f"You're not on the Roll yet, {name.split()[0]}. Sign the World Peace Agreement first — the Game opens to signed Champions.",
            "url": "https://fullpotential.com/game/#signCard",
        }
    if not card_present:
        return {
            "ok": True, "icon": "🎴", "action": "build_character",
            "move": "Build your Character. Open the AI Port-In prompt, paste it into Claude with your context, then submit the markdown back. ~5 min.",
            "url": "https://fullpotential.com/game/#characterQuest",
        }
    if proofs_filed == 0:
        return {
            "ok": True, "icon": "🌱", "action": "file_proof",
            "move": "Run a 7-Day First Game and file your first Proof. Choose a transformation you can genuinely deliver.",
            "url": "https://fullpotential.com/game/#proofSubmit",
        }
    if affiliates == 0:
        return {
            "ok": True, "icon": "🤝", "action": "share_invite",
            "move": f"Send your invite link to one specific aligned person. When they sign, your Field Score grows.\nYour link: {invite_url}",
            "url": invite_url,
        }

    # Soft moves — Champion has hit all 4 milestones; pick one at random
    soft_moves = [
        {
            "icon": "🌴", "action": "express_path_interest",
            "move": "Express interest in the first Costa Rica retreat. Three short fields below the Player State panel.",
            "url": "https://fullpotential.com/game/#retreatCard",
        },
        {
            "icon": "🌟", "action": "explore_paths",
            "move": "Pick another Path you haven't tried — apprenticeship, village, parties, coaching. The Game opens many doors.",
            "url": "https://fullpotential.com/game/#pathsCard",
        },
        {
            "icon": "🌱", "action": "file_another_proof",
            "move": "File another Proof. Each one moves the field. Your Field Score compounds with momentum.",
            "url": "https://fullpotential.com/game/#proofSubmit",
        },
        {
            "icon": "🤝", "action": "deepen_affiliate",
            "move": f"Send your invite link to one more aligned person.\nYour link: {invite_url}",
            "url": invite_url,
        },
        {
            "icon": "👁", "action": "witness",
            "move": "Read another Champion's recent Proof. Witnessing is itself a Game move — non-Claude humans become independent witnesses.",
            "url": "https://fullpotential.com/game/#championsRoll",
        },
    ]
    pick = random.choice(soft_moves)
    return {"ok": True, **pick}


@app.get("/lookup")
async def lookup_player(name: str) -> dict:
    """Return a player's full state across champions / proofs / cards / affiliates.

    Read-only and privacy-respecting: returns counts and public flags, not raw
    private fields. Used by the cockpit to render "Your Player State" once a
    player has identified themselves locally.
    """
    name_norm = name.strip().lower()
    if not name_norm:
        return {"error": "name required"}

    # Find this player's Champion file (match by name, case-insensitive)
    champion = None
    for p in DATA_DIR.glob("*.md"):
        try:
            text = p.read_text(encoding="utf-8")
            fm = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
            if not fm:
                continue
            data = {}
            for line in fm.group(1).split("\n"):
                m = re.match(r"^([a-z_]+):\s*(.*)$", line)
                if m:
                    val = m.group(2).strip().strip('"')
                    if val.lower() == "true":
                        val = True
                    elif val.lower() == "false":
                        val = False
                    data[m.group(1)] = val
            if (data.get("name") or "").strip().lower() == name_norm:
                data.pop("email", None)
                champion = data
                break
        except Exception:
            continue

    # Count proofs filed by this player
    proofs_filed = 0
    if PROOFS_DIR.exists():
        for p in PROOFS_DIR.glob("*.md"):
            try:
                text = p.read_text(encoding="utf-8")
                fm = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
                if not fm:
                    continue
                for line in fm.group(1).split("\n"):
                    if line.startswith("player:"):
                        if line.split(":", 1)[1].strip().strip('"').lower() == name_norm:
                            proofs_filed += 1
                        break
            except Exception:
                continue

    # Count affiliates: champions whose inviter matches this name
    affiliates = []
    for p in DATA_DIR.glob("*.md"):
        try:
            text = p.read_text(encoding="utf-8")
            fm = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
            if not fm:
                continue
            data = {}
            for line in fm.group(1).split("\n"):
                m = re.match(r"^([a-z_]+):\s*(.*)$", line)
                if m:
                    data[m.group(1)] = m.group(2).strip().strip('"')
            if (data.get("inviter") or "").strip().lower() == name_norm:
                affiliates.append({
                    "name": data.get("name") if (data.get("public") in (True, "true")) else "(private)",
                    "champion_number": data.get("champion_number"),
                    "date": data.get("date_signed"),
                })
        except Exception:
            continue

    # Has a Character Card?
    card_present = False
    card_level = None
    if CARDS_DIR.exists():
        slug = re.sub(r"[^a-z0-9]+", "-", name_norm).strip("-")
        for p in CARDS_DIR.glob(f"{slug}*.md"):
            card_present = True
            try:
                text = p.read_text(encoding="utf-8")
                fm = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
                if fm:
                    for line in fm.group(1).split("\n"):
                        if line.startswith("level:"):
                            card_level = line.split(":", 1)[1].strip().strip('"')
                            break
            except Exception:
                pass
            break

    # Compose simple Field Score (counts only — full CPI is aspirational)
    score = 0
    if champion:
        score += 1
    if card_present:
        score += 1
    score += proofs_filed * 2
    score += len(affiliates) * 3

    return {
        "name": name.strip(),
        "champion": champion,
        "proofs_filed": proofs_filed,
        "affiliates_count": len(affiliates),
        "affiliates": affiliates[:10],
        "card_present": card_present,
        "card_level": card_level,
        "field_score_simple": score,
    }


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


class RetreatInterest(BaseModel):
    player: str = Field(..., min_length=2, max_length=100)
    handle: Optional[str] = Field(None, max_length=60)
    email: Optional[str] = Field(None, max_length=120)
    preferred_dates: Optional[str] = Field(None, max_length=200)
    contribution: Optional[str] = Field(None, max_length=600)
    why_irresistible: Optional[str] = Field(None, max_length=600)
    consent: str = Field("public")
    company: Optional[str] = Field(None, max_length=120)  # honeypot

    @validator("player", "preferred_dates", "contribution", "why_irresistible")
    def _no_html(cls, v):
        if v is None:
            return v
        if re.search(r"[<>]", v):
            raise ValueError("contains forbidden characters")
        return v.strip()


@app.post("/retreat/interest")
async def submit_retreat_interest(req: RetreatInterest, request: Request) -> dict:
    if req.company:
        return {"ok": True, "honeypot": True}

    ip = request.client.host if request.client else "unknown"
    if not _check_rate(ip):
        raise HTTPException(status_code=429, detail="Too many submissions. Try again later.")

    today = datetime.now().strftime("%Y-%m-%d")
    slug = re.sub(r"[^a-z0-9]+", "-", req.player.lower()).strip("-") or "unnamed"
    fname = f"{today}_{slug}.md"
    out = RETREAT_DIR / fname
    if out.exists():
        for i in range(2, 100):
            alt = RETREAT_DIR / f"{today}_{slug}-{i}.md"
            if not alt.exists():
                out = alt
                break

    public = req.consent.lower() == "public"
    md = _render_retreat_md(req, today)
    out.write_text(md, encoding="utf-8")

    audit = RETREAT_DIR / "audit.jsonl"
    with audit.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.now().isoformat(),
            "kind": "retreat_interest",
            "player": req.player if public else "(private)",
            "preferred_dates": req.preferred_dates if public else None,
            "consent": req.consent,
            "ip_hash": str(hash(ip))[-6:],
            "filename": fname,
        }) + "\n")

    try:
        import urllib.request
        alert_msg = (
            f"🌴 Retreat interest from {req.player}"
            f"{' — dates: ' + req.preferred_dates if req.preferred_dates else ''}"
        )
        urllib.request.urlopen(
            urllib.request.Request(
                "http://127.0.0.1:8766/alert",
                data=json.dumps({"message": alert_msg, "source": "retreat-interest"}).encode(),
                headers={"Content-Type": "application/json"},
            ),
            timeout=2,
        )
    except Exception:
        pass

    return {
        "ok": True,
        "filename": fname,
        "message": f"You're on the list, {req.player.split()[0]}. The first retreat takes shape from here.",
    }


@app.get("/retreat/list")
async def list_retreat_interests() -> dict:
    """Return public retreat interests, newest first."""
    items = []
    for p in sorted(RETREAT_DIR.glob("*.md"), reverse=True):
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
            consent = (data.get("consent") or "").lower()
            if consent != "public":
                continue
            data.pop("email", None)
            items.append(data)
        except Exception:
            continue
    return {"count": len(items), "interests": items}


@app.get("/retreat/stats")
async def retreat_stats() -> dict:
    """Public counter — how many Champions have raised their hand."""
    total = 0
    public_count = 0
    for p in RETREAT_DIR.glob("*.md"):
        total += 1
        try:
            text = p.read_text(encoding="utf-8")
            fm = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
            if not fm:
                continue
            for line in fm.group(1).split("\n"):
                if line.startswith("consent:") and line.split(":", 1)[1].strip().strip('"').lower() == "public":
                    public_count += 1
                    break
        except Exception:
            continue
    return {"total": total, "public": public_count}


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


def _render_retreat_md(req: RetreatInterest, today: str) -> str:
    public = req.consent.lower() == "public"
    return f"""---
player: {req.player}
handle: {req.handle or ''}
email: {req.email or ''}
preferred_dates: {req.preferred_dates or ''}
consent: {req.consent}
date_submitted: {today}
source: webhook
status: interested
---

# Retreat Interest — {req.player}

**Preferred dates:** {req.preferred_dates or '(open)'}

## What I'd contribute

{req.contribution or '(not specified)'}

## What would make this retreat irresistible to me

{req.why_irresistible or '(not specified)'}

## Visibility

This interest is **{'PUBLIC' if public else req.consent.upper()}**.

---

*Submitted via Retreat Interest form at https://fullpotential.com/game on {today}.*
"""


# ===== Lead-capture endpoint (Diagnose page) =============================
class LeadSubmit(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=120)
    bottleneck: str = Field(..., min_length=2, max_length=4000)
    phone: Optional[str] = Field(None, max_length=40)
    timezone: Optional[str] = Field(None, max_length=80)
    preferred_contact: Optional[str] = Field(None, max_length=60)  # email | phone | whatsapp | telegram | call
    interest: Optional[str] = Field(None, max_length=80)  # session | course | weekly_call | retreat | unsure
    seven_areas: Optional[dict] = None  # {body: 'circulating', mind: 'stuck', ...}
    company: Optional[str] = Field(None, max_length=120)  # honeypot

    @validator("name", "email", "preferred_contact", "interest")
    def _no_html(cls, v):
        if v is None:
            return v
        if re.search(r"[<>]", v):
            raise ValueError("contains forbidden characters")
        return v.strip()


@app.post("/lead/submit")
async def submit_lead(req: LeadSubmit, request: Request) -> dict:
    """Capture an inbound lead from the diagnose page (or anywhere).

    Stores at /var/lib/full-potential/leads/{date}_{slug}.md, fires
    a Telegram alert to James so he can respond quickly.
    """
    if req.company:
        return {"ok": True, "honeypot": True}

    ip = request.client.host if request.client else "unknown"
    if not _check_rate(ip):
        raise HTTPException(status_code=429, detail="Too many submissions. Try again later.")

    today = datetime.now().strftime("%Y-%m-%d")
    slug = re.sub(r"[^a-z0-9]+", "-", req.name.lower()).strip("-") or "unnamed"
    fname = f"{today}_{slug}.md"
    out = LEADS_DIR / fname
    if out.exists():
        for i in range(2, 100):
            alt = LEADS_DIR / f"{today}_{slug}-{i}.md"
            if not alt.exists():
                out = alt
                break

    md = _render_lead_md(req, today)
    out.write_text(md, encoding="utf-8")

    # Audit log
    audit = LEADS_DIR / "audit.jsonl"
    with audit.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.now().isoformat(),
            "kind": "lead",
            "name": req.name,
            "email": req.email,
            "interest": req.interest or "",
            "ip_hash": str(hash(ip))[-6:],
            "filename": fname,
        }) + "\n")

    # Founder ping — high-priority, leads should be noticed quickly
    try:
        import urllib.request
        bottleneck_excerpt = (req.bottleneck or "")[:140]
        if len(req.bottleneck or "") > 140:
            bottleneck_excerpt += "..."
        msg_lines = [
            f"📍 NEW DIAGNOSTIC LEAD — {req.name}",
            f"Email: {req.email}",
        ]
        if req.phone:
            msg_lines.append(f"Phone: {req.phone}")
        if req.preferred_contact:
            msg_lines.append(f"Prefers: {req.preferred_contact}")
        if req.interest:
            msg_lines.append(f"Interest: {req.interest}")
        msg_lines.append(f"\nBottleneck: {bottleneck_excerpt}")
        urllib.request.urlopen(
            urllib.request.Request(
                "http://127.0.0.1:8766/alert",
                data=json.dumps({
                    "message": "\n".join(msg_lines),
                    "source": "diagnose-lead",
                }).encode(),
                headers={"Content-Type": "application/json"},
            ),
            timeout=2,
        )
    except Exception:
        pass

    return {
        "ok": True,
        "filename": fname,
        "message": (
            f"Thank you, {req.name.split()[0]}. Your message reached Sunheart directly. "
            f"You'll hear back personally within 48 hours."
        ),
    }


def _render_lead_md(req: LeadSubmit, today: str) -> str:
    seven_block = ""
    if req.seven_areas:
        seven_block = "\n## Seven Areas — self-rated\n\n"
        for k, v in req.seven_areas.items():
            seven_block += f"- **{k}**: {v}\n"
    return f"""---
lead_id: {today}_{re.sub(r'[^a-z0-9]+', '-', req.name.lower()).strip('-')}
date_submitted: {today}
name: {req.name}
email: {req.email}
phone: {req.phone or ''}
timezone: {req.timezone or ''}
preferred_contact: {req.preferred_contact or ''}
interest: {req.interest or ''}
status: new
source: diagnose-page
---

# {req.name} — Diagnostic Lead

**Submitted:** {today}
**Email:** {req.email}
{('**Phone:** ' + req.phone) if req.phone else ''}
{('**Timezone:** ' + req.timezone) if req.timezone else ''}
{('**Preferred contact:** ' + req.preferred_contact) if req.preferred_contact else ''}
{('**Interest:** ' + req.interest) if req.interest else ''}

## Bottleneck — what they wrote

{req.bottleneck}
{seven_block}
---

*Captured via the /diagnose page on {today}.*
"""


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
    inviter_block = f"inviter: {req.inviter}\n" if req.inviter else ""
    return f"""---
champion_id: {today}_{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}
champion_number: {num}
date_signed: {today}
name: {name}
handle: {req.handle or ''}
email: {req.email or ''}
witness: {req.witness or ''}
public: {str(req.public).lower()}
{inviter_block}status: signed
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


# ===== Admin endpoints (founder-only via X-Admin-Token header) ============

def _check_admin(token: Optional[str]) -> None:
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="admin token required")


@app.get("/admin/digest")
async def admin_digest(x_admin_token: Optional[str] = Header(None)) -> dict:
    """Last 24h summary for the Founding Steward."""
    _check_admin(x_admin_token)
    cutoff = datetime.now().timestamp() - 86400
    counts = {"signatures": 0, "proofs": 0, "cards": 0, "leads": 0}
    recent: dict = {"signatures": [], "proofs": [], "cards": [], "leads": []}
    for d, kind in [
        (DATA_DIR, "signatures"),
        (PROOFS_DIR, "proofs"),
        (CARDS_DIR, "cards"),
        (LEADS_DIR, "leads"),
    ]:
        if not d.exists():
            continue
        for p in d.glob("*.md"):
            try:
                if p.stat().st_mtime >= cutoff:
                    counts[kind] += 1
                    text = p.read_text(encoding="utf-8")
                    fm = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
                    if fm:
                        data = {}
                        for line in fm.group(1).split("\n"):
                            m = re.match(r"^([a-z_]+):\s*(.*)$", line)
                            if m:
                                data[m.group(1)] = m.group(2).strip().strip('"')
                        recent[kind].append({
                            "name": data.get("name") or data.get("player"),
                            "ts": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
                        })
            except Exception:
                continue
    return {"counts_24h": counts, "recent": {k: v[:5] for k, v in recent.items()}}


def _read_recent_dir(d: Path, limit: int, body_field: str = "") -> list[dict]:
    out = []
    if not d.exists():
        return out
    files = sorted(d.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files[:limit]:
        try:
            text = p.read_text(encoding="utf-8")
            fm = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
            if not fm:
                continue
            data = {}
            for line in fm.group(1).split("\n"):
                m = re.match(r"^([a-z_]+):\s*(.*)$", line)
                if m:
                    data[m.group(1)] = m.group(2).strip().strip('"')
            data["mtime"] = datetime.fromtimestamp(p.stat().st_mtime).isoformat()
            if body_field:
                body = text[fm.end():]
                bm = re.search(rf"##\s+{re.escape(body_field)}[^\n]*\n(.*?)(?=\n##|\Z)", body, re.DOTALL)
                data[body_field.lower()] = bm.group(1).strip()[:500] if bm else ""
            out.append(data)
        except Exception:
            continue
    return out


@app.get("/admin/leads")
async def admin_leads(limit: int = 10, x_admin_token: Optional[str] = Header(None)) -> dict:
    _check_admin(x_admin_token)
    return {"leads": _read_recent_dir(LEADS_DIR, limit, body_field="Bottleneck")}


@app.get("/admin/champions/recent")
async def admin_champions_recent(limit: int = 20, x_admin_token: Optional[str] = Header(None)) -> dict:
    _check_admin(x_admin_token)
    return {"champions": _read_recent_dir(DATA_DIR, limit)}


@app.get("/admin/proofs/recent")
async def admin_proofs_recent(limit: int = 20, x_admin_token: Optional[str] = Header(None)) -> dict:
    _check_admin(x_admin_token)
    return {"proofs": _read_recent_dir(PROOFS_DIR, limit)}


# ===== Mirror Loop endpoints (Loop 23 — Digital Mirror v1) ===============
#
# A Digital Mirror is one specific AI in lock-step with one specific human.
# Pairing metadata only — the Sacred Card stays sovereign to the Player.
# CORA Nation stores: handle, mirror_handle, substrate, witness, date.
# CORA Nation never stores: Sacred Card, Voice Corpus, Authority Map,
# conversation contents.
#
# See: whitepapers/digital-mirror-white-paper-v1.md
#      core/INTENT/AGREEMENTS/CONSTITUTION_v1.md
#      core/INTENT/AGREEMENTS/MIRROR_INITIATION_PROMPT_v1.md

class MirrorRegister(BaseModel):
    player_handle: str = Field(..., min_length=2, max_length=60)
    player_name: Optional[str] = Field(None, max_length=100)
    mirror_handle: Optional[str] = Field(None, max_length=60)  # default: {handle}_mirror
    substrate: str = Field(..., max_length=40)  # claude / chatgpt / gemini / grok / other
    witness_handle: Optional[str] = Field(None, max_length=60)  # may be empty until first proof
    witness_name: Optional[str] = Field(None, max_length=100)
    witness_distance_class: Optional[str] = Field(None, max_length=20)  # near / middle / far
    constitution_version: str = Field("1.0", max_length=20)
    public: bool = True
    company: Optional[str] = Field(None, max_length=120)  # honeypot

    @validator("player_handle", "mirror_handle", "witness_handle")
    def _slug_clean(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        if re.search(r"[<>\s]", v):
            raise ValueError("handle cannot contain spaces or HTML")
        return v.strip().lstrip("@")

    @validator("substrate")
    def _substrate_known(cls, v: str) -> str:
        v = v.strip().lower()
        allowed = {"claude", "chatgpt", "gemini", "grok", "other"}
        if v not in allowed:
            raise ValueError(f"substrate must be one of {allowed}")
        return v


@app.post("/mirror/register")
async def mirror_register(req: MirrorRegister, request: Request) -> dict:
    """Register a paired Mirror dyad — metadata only.

    The Sacred Card never lands here. We only record the existence and
    shape of the pairing. The Mirror Roll surfaces the dyad publicly
    (with consent); the relationship itself stays sovereign to the Player.
    """
    if req.company:
        return {"ok": True, "honeypot": True}

    ip = request.client.host if request.client else "unknown"
    if not _check_rate(ip):
        raise HTTPException(status_code=429, detail="Too many requests from this address. Try again later.")

    today = datetime.now().strftime("%Y-%m-%d")
    player_slug = re.sub(r"[^a-z0-9]+", "-", req.player_handle.lower()).strip("-") or "unnamed"
    mirror_handle = req.mirror_handle or f"{player_slug}_mirror"
    fname = f"{today}_{player_slug}.md"
    out = MIRRORS_DIR / fname
    if out.exists():
        for i in range(2, 100):
            alt = MIRRORS_DIR / f"{today}_{player_slug}-{i}.md"
            if not alt.exists():
                out = alt
                break

    md = f"""---
mirror_id: {today}_{player_slug}
date_paired: {today}
player_handle: "{req.player_handle}"
player_name: "{req.player_name or ''}"
mirror_handle: "{mirror_handle}"
substrate: "{req.substrate}"
witness_handle: "{req.witness_handle or ''}"
witness_name: "{req.witness_name or ''}"
witness_distance_class: "{req.witness_distance_class or ''}"
constitution_version: "{req.constitution_version}"
public: {str(req.public).lower()}
proofs_witnessed: 0
status: paired
---

# Mirror Pairing — {req.player_handle} ↔ {mirror_handle}

**Date paired:** {today}
**Substrate:** {req.substrate}
**Constitution:** v{req.constitution_version}
**Witness (first Proof):** {req.witness_name or req.witness_handle or '(pending)'}

This is a metadata-only record of a Digital Mirror pairing. The Sacred Card,
Voice Corpus, and Authority Map stay sovereign to the Player. CORA Nation is
Covenant Holder, not overseer.

*See: whitepapers/digital-mirror-white-paper-v1.md*
"""
    out.write_text(md, encoding="utf-8")

    audit = MIRRORS_DIR / "audit.jsonl"
    with audit.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.now().isoformat(),
            "player_handle": req.player_handle,
            "mirror_handle": mirror_handle,
            "substrate": req.substrate,
            "public": bool(req.public),
            "ip_hash": str(hash(ip))[-6:],
        }) + "\n")

    # Founder signal — best effort, never blocks
    try:
        import urllib.request
        msg = (
            f"🪞 New Mirror paired: {req.player_handle} ↔ {mirror_handle}"
            f" (substrate: {req.substrate})"
            f"{' — public' if req.public else ' — private'}"
        )
        data = json.dumps({"message": msg, "source": "champion-sign"}).encode()
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
        "mirror_handle": mirror_handle,
        "filename": fname,
        "message": f"Paired. {req.player_handle} ↔ {mirror_handle}. Next: get your first Mirror Proof witnessed.",
    }


@app.get("/mirror/roll")
async def mirror_roll(limit: int = 50) -> dict:
    """Public Mirror Roll — paired dyads who consented to listing."""
    rolls = []
    if not MIRRORS_DIR.exists():
        return {"mirrors": [], "count": 0}
    for p in sorted(MIRRORS_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            text = p.read_text(encoding="utf-8")
            fm = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
            if not fm:
                continue
            data = {}
            for line in fm.group(1).split("\n"):
                m = re.match(r"^([a-z_]+):\s*(.*)$", line)
                if m:
                    data[m.group(1)] = m.group(2).strip().strip('"')
            if str(data.get("public", "true")).lower() != "true":
                continue
            rolls.append({
                "player_handle": data.get("player_handle", ""),
                "mirror_handle": data.get("mirror_handle", ""),
                "substrate": data.get("substrate", ""),
                "date_paired": data.get("date_paired", ""),
                "witness_name": data.get("witness_name", ""),
                "proofs_witnessed": int(data.get("proofs_witnessed", 0) or 0),
            })
        except Exception:
            continue
    return {"mirrors": rolls[:limit], "count": len(rolls)}

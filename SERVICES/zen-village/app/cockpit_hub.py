"""
Zen Village — Cockpit Hub (Phase 2)

Single source of truth listing every admin surface (receipts, applicants,
bookings, wallet, etc.) PLUS a built-in user/role registry so admins can
add team members and grant per-surface access in the browser.

Design choices:
  * Surfaces are declared in `SURFACES` (this file) — appending one row
    catalogs a new admin tool.
  * Users live in /etc/zen-village/cockpit-users.json (root-owned, 0600).
    Schema: see _DEFAULT_USERS below.
  * Passwords are hashed with hashlib.scrypt (built-in, no extra deps).
  * Sessions are random 32-byte tokens stored in users.json (one active
    session per user). Sent as `X-Session-Token` header.
  * The legacy admin token (ZV_AFFILIATES_ADMIN_TOKEN) is still accepted
    as a back-door owner credential — used for bootstrap and emergency
    recovery if everyone forgets their password.
  * Roles:
      - owner  : full access, can manage users, can't be demoted
      - admin  : full access, can manage users
      - member : sees only assigned surfaces, can't manage users
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Body, Header, HTTPException, Query

router = APIRouter()

# ─── catalog ──────────────────────────────────────────────────────────────
SURFACES: list[dict[str, Any]] = [
    {
        "id": "receipts",
        "name": "Receipts (Accounting)",
        "icon": "🧾",
        "blurb": "Halley's receipt loop — view, edit, AI-parse Telegram intakes from @zenvillagebot.",
        "url": "https://brain.zenvillagecr.com/accounting/",
        "health_url": "https://brain.zenvillagecr.com/accounting/",
        "auth": "nginx basic-auth · per-user role",
        "tags": ["finance", "telegram"],
        "provider": "brain (162.0.208.88)",
    },
    {
        "id": "submissions",
        "name": "Submissions Cockpit",
        "icon": "📥",
        "blurb": "Triage incoming applicants & inquiries — practitioner, work-exchange, retreat, support.",
        "url": "https://zenvillagecr.com/admin/submissions",
        "health_url": "https://zenvillagecr.com/admin/submissions",
        "auth": "shared admin token (localStorage)",
        "tags": ["leads", "people"],
        "provider": "zen-village (198.54.123.234)",
    },
    {
        "id": "bookings",
        "name": "Bookings",
        "icon": "🛏️",
        "blurb": "Reservations, structures, check-ins. Calendar + per-stay invoicing.",
        "url": "https://zenvillagecr.com/booking-admin",
        "health_url": "https://zenvillagecr.com/booking-admin",
        "auth": "shared admin token",
        "tags": ["finance", "guests"],
        "provider": "zen-village",
    },
    {
        "id": "topups",
        "name": "Zen Wallet · Top-ups",
        "icon": "💰",
        "blurb": "Issue Zen credits — manual top-ups, refunds, ledger.",
        "url": "https://zenvillagecr.com/admin/topups",
        "health_url": "https://zenvillagecr.com/admin/topups",
        "auth": "shared admin token",
        "tags": ["finance", "wallet"],
        "provider": "zen-village",
    },
    {
        "id": "items",
        "name": "Zen Store · Items",
        "icon": "🛍️",
        "blurb": "Manage store inventory, prices, availability for in-village purchases.",
        "url": "https://zenvillagecr.com/admin/items",
        "health_url": "https://zenvillagecr.com/admin/items",
        "auth": "shared admin token",
        "tags": ["commerce"],
        "provider": "zen-village",
    },
    {
        "id": "affiliates",
        "name": "Affiliates",
        "icon": "🤝",
        "blurb": "Affiliate program — commissions, payouts, partner codes.",
        "url": "https://zenvillagecr.com/admin/affiliates",
        "health_url": "https://zenvillagecr.com/admin/affiliates",
        "auth": "shared admin token",
        "tags": ["finance", "growth"],
        "provider": "zen-village",
    },
    {
        "id": "events",
        "name": "Events / RSVPs",
        "icon": "🎟️",
        "blurb": "World Peace Weekend, retreats, workshops — RSVPs, ticket scans, capacity.",
        "url": "https://zenvillagecr.com/admin/event",
        "health_url": "https://zenvillagecr.com/admin/event",
        "auth": "shared admin token",
        "tags": ["events", "growth"],
        "provider": "zen-village",
    },
    {
        "id": "inbox",
        "name": "Unified Inbox",
        "icon": "📬",
        "blurb": "Cross-channel message stream — Telegram, web forms, emails to one queue.",
        "url": "https://zenvillagecr.com/admin/inbox",
        "health_url": "https://zenvillagecr.com/admin/inbox",
        "auth": "shared admin token",
        "tags": ["leads", "people"],
        "provider": "zen-village",
    },
    {
        "id": "crm",
        "name": "NocoDB (raw mirror)",
        "icon": "🗄️",
        "blurb": "Spreadsheet view of every form submission — durable backup, raw payloads.",
        "url": "https://crm.zenvillagecr.com/dashboard/",
        "health_url": "https://crm.zenvillagecr.com/dashboard/",
        "auth": "NocoDB native login",
        "tags": ["data", "backup"],
        "provider": "external (NocoDB cloud)",
    },
    {
        "id": "telegram-bot",
        "name": "Telegram Bot",
        "icon": "🤖",
        "blurb": "@zenvillagebot — receipts, accounting, daily pulse digests.",
        "url": "https://t.me/zenvillagebot",
        "health_url": None,
        "auth": "Telegram user-ID allowlist",
        "tags": ["telegram", "operations"],
        "provider": "brain",
    },
]
SURFACE_IDS = {s["id"] for s in SURFACES}


# ─── users registry ───────────────────────────────────────────────────────
USERS_FILE = Path(os.environ.get(
    "ZV_COCKPIT_USERS_FILE", "/etc/zen-village/cockpit-users.json"
))

VALID_ROLES = {"owner", "admin", "member"}
SESSION_TTL_HOURS = 24 * 14  # 2 weeks


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash_password(password: str) -> str:
    """Hash with hashlib.scrypt (Python stdlib, no extra deps).
    Format: scrypt$<n>$<r>$<p>$<salt_hex>$<hash_hex>"""
    if not password or len(password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    n, r, p = 16384, 8, 1
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=32
    )
    return f"scrypt${n}${r}${p}${salt.hex()}${h.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    if not password or not stored or not stored.startswith("scrypt$"):
        return False
    try:
        _, n, r, p, salt_hex, hash_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=salt,
            n=int(n), r=int(r), p=int(p), dklen=len(expected),
        )
        return secrets.compare_digest(actual, expected)
    except Exception:
        return False


def _ensure_users_file() -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if USERS_FILE.exists():
        return
    # Bootstrap with a single owner whose password is the legacy admin token
    # (so admins always have a recovery path through env + restart).
    bootstrap_token = (
        os.environ.get("ZV_AFFILIATES_ADMIN_TOKEN")
        or os.environ.get("ZV_COCKPIT_TOKEN")
        or secrets.token_urlsafe(24)
    )
    initial = {
        "users": [{
            "username": "sunheart",
            "display_name": "James Sunheart",
            "email": "",
            "password_hash": _hash_password(bootstrap_token[:32]),
            "role": "owner",
            "surfaces": ["*"],
            "created_at": _now_iso(),
            "created_by": "system",
            "last_login_at": None,
            "session_token": None,
            "session_expires_at": None,
        }]
    }
    USERS_FILE.write_text(json.dumps(initial, indent=2, ensure_ascii=False))
    try:
        os.chmod(USERS_FILE, 0o600)
    except Exception:
        pass


def _read_users() -> dict:
    _ensure_users_file()
    try:
        return json.loads(USERS_FILE.read_text())
    except Exception:
        return {"users": []}


def _write_users(d: dict) -> None:
    tmp = USERS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    tmp.replace(USERS_FILE)
    try:
        os.chmod(USERS_FILE, 0o600)
    except Exception:
        pass


def _find_user(username: str) -> Optional[dict]:
    if not username:
        return None
    u = username.strip().lower()
    for row in _read_users().get("users", []):
        if (row.get("username") or "").lower() == u:
            return row
    return None


def _save_user(user: dict) -> None:
    data = _read_users()
    users = data.get("users", [])
    uname = (user.get("username") or "").lower()
    out = []
    replaced = False
    for row in users:
        if (row.get("username") or "").lower() == uname:
            out.append(user)
            replaced = True
        else:
            out.append(row)
    if not replaced:
        out.append(user)
    data["users"] = out
    _write_users(data)


def _public_user(user: dict) -> dict:
    """User dict safe to return to the browser — no password hash, no token."""
    return {
        "username": user.get("username"),
        "display_name": user.get("display_name") or user.get("username"),
        "email": user.get("email") or "",
        "role": user.get("role") or "member",
        "surfaces": user.get("surfaces") or [],
        "created_at": user.get("created_at"),
        "created_by": user.get("created_by"),
        "last_login_at": user.get("last_login_at"),
        "has_password": bool(user.get("password_hash")),
    }


# ─── auth ─────────────────────────────────────────────────────────────────
def _legacy_token() -> str:
    return (
        os.environ.get("ZV_COCKPIT_TOKEN")
        or os.environ.get("ZV_AFFILIATES_ADMIN_TOKEN")
        or ""
    )


def _resolve_caller(
    x_admin_token: Optional[str],
    x_session_token: Optional[str],
) -> dict:
    """Identify the caller. Returns a synthetic user dict with `role`,
    `username`, `surfaces`, and `via` ('token' | 'session').
    Raises 401 if neither credential is valid."""
    # 1) Session token (preferred — tied to a real user record).
    if x_session_token:
        for row in _read_users().get("users", []):
            if not row.get("session_token"):
                continue
            if not secrets.compare_digest(
                str(row["session_token"]), str(x_session_token)
            ):
                continue
            exp = row.get("session_expires_at")
            if exp and exp < _now_iso():
                continue
            return {**row, "via": "session"}
    # 2) Legacy admin token — implicit owner.
    legacy = _legacy_token()
    if legacy and x_admin_token and secrets.compare_digest(
        str(x_admin_token), str(legacy)
    ):
        return {
            "username": "_legacy_token",
            "display_name": "Legacy Admin Token",
            "role": "owner",
            "surfaces": ["*"],
            "via": "token",
        }
    raise HTTPException(401, "Sign in required")


def _require_admin(caller: dict) -> None:
    if caller.get("role") not in ("owner", "admin"):
        raise HTTPException(403, "Admin or owner role required")


def _can_see(caller: dict, surface_id: str) -> bool:
    surfaces = caller.get("surfaces") or []
    return "*" in surfaces or surface_id in surfaces


# ─── status pings ─────────────────────────────────────────────────────────
_PING_CACHE: dict[str, dict[str, Any]] = {}
_PING_TTL_SEC = 60.0
_PING_TIMEOUT = 4.0


async def _ping_one(client: httpx.AsyncClient, surface: dict) -> dict:
    sid = surface["id"]
    health_url = surface.get("health_url")
    if not health_url:
        return {
            "id": sid, "status": "external", "code": None, "ms": 0,
            "checked_at": _now_iso(),
        }
    cached = _PING_CACHE.get(sid)
    if cached and (time.time() - cached.get("_ts", 0) < _PING_TTL_SEC):
        return {k: v for k, v in cached.items() if not k.startswith("_")}
    started = time.perf_counter()
    code: Optional[int] = None
    err: Optional[str] = None
    try:
        r = await client.head(health_url, timeout=_PING_TIMEOUT, follow_redirects=True)
        if r.status_code in (404, 405) or r.status_code >= 500:
            r = await client.get(
                health_url, timeout=_PING_TIMEOUT, follow_redirects=True,
                headers={"Range": "bytes=0-1"},
            )
        code = r.status_code
    except httpx.HTTPError as e:
        err = type(e).__name__
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    is_up = code is not None and code < 500 and code != 404
    out = {
        "id": sid,
        "status": "up" if is_up else "down",
        "code": code, "ms": elapsed_ms, "error": err,
        "checked_at": _now_iso(),
    }
    _PING_CACHE[sid] = {**out, "_ts": time.time()}
    return out


# ─── endpoints — auth ─────────────────────────────────────────────────────
@router.post("/api/cockpit/login")
async def login(payload: dict = Body(...)):
    """Sign in with username + password. Returns a session token for the browser."""
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    if not username or not password:
        raise HTTPException(400, "username and password required")
    user = _find_user(username)
    if not user or not _verify_password(password, user.get("password_hash") or ""):
        # Keep the message vague to avoid username enumeration.
        raise HTTPException(401, "Invalid username or password")
    # Mint a fresh session.
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc).timestamp() + SESSION_TTL_HOURS * 3600
    user["session_token"] = token
    user["session_expires_at"] = datetime.fromtimestamp(
        expires, timezone.utc
    ).isoformat(timespec="seconds")
    user["last_login_at"] = _now_iso()
    _save_user(user)
    return {
        "session_token": token,
        "expires_at": user["session_expires_at"],
        "user": _public_user(user),
    }


@router.post("/api/cockpit/logout")
async def logout(
    x_admin_token: Optional[str] = Header(default=None),
    x_session_token: Optional[str] = Header(default=None),
):
    """Invalidate the current session."""
    try:
        caller = _resolve_caller(x_admin_token, x_session_token)
    except HTTPException:
        return {"ok": True}
    if caller.get("via") == "session" and caller.get("username"):
        u = _find_user(caller["username"])
        if u:
            u["session_token"] = None
            u["session_expires_at"] = None
            _save_user(u)
    return {"ok": True}


@router.get("/api/cockpit/me")
async def whoami(
    x_admin_token: Optional[str] = Header(default=None),
    x_session_token: Optional[str] = Header(default=None),
):
    caller = _resolve_caller(x_admin_token, x_session_token)
    return {
        "username": caller.get("username"),
        "display_name": caller.get("display_name") or caller.get("username"),
        "role": caller.get("role"),
        "surfaces": caller.get("surfaces") or [],
        "via": caller.get("via"),
    }


@router.get("/api/cockpit/legacy-token")
async def legacy_token_for_surface(
    x_admin_token: Optional[str] = Header(default=None),
    x_session_token: Optional[str] = Header(default=None),
):
    """Bridge for legacy surfaces (e.g. /admin/submissions, /booking-admin)
    that still gate on ZV_AFFILIATES_ADMIN_TOKEN. If the caller is signed in
    via cockpit session AND has admin/owner role, return the legacy token so
    the legacy frontend can stash it in its own localStorage transparently.
    """
    caller = _resolve_caller(x_admin_token, x_session_token)
    if caller.get("role") not in ("owner", "admin"):
        raise HTTPException(403, "admin or owner role required")
    legacy = _legacy_token()
    if not legacy:
        raise HTTPException(503, "Legacy admin token not configured")
    return {"token": legacy}


# ─── endpoints — surfaces + status ────────────────────────────────────────
@router.get("/api/cockpit/surfaces")
async def list_surfaces(
    x_admin_token: Optional[str] = Header(default=None),
    x_session_token: Optional[str] = Header(default=None),
):
    """Return only the surfaces the caller is allowed to see."""
    caller = _resolve_caller(x_admin_token, x_session_token)
    visible = [s for s in SURFACES if _can_see(caller, s["id"])]
    # Decorate each surface with its grantee list (only the admin sees this
    # detail; members see an empty list to avoid leaking team makeup).
    if caller.get("role") in ("owner", "admin"):
        users = _read_users().get("users", [])
        grantees: dict[str, list[str]] = {sid: [] for sid in SURFACE_IDS}
        for u in users:
            uname = u.get("username") or ""
            for s in (u.get("surfaces") or []):
                if s == "*":
                    for sid in SURFACE_IDS:
                        grantees[sid].append(uname)
                elif s in grantees:
                    grantees[s].append(uname)
        for s in visible:
            s = s  # not used
        out_surfaces = [{**s, "users": grantees.get(s["id"], [])} for s in visible]
    else:
        out_surfaces = [{**s, "users": []} for s in visible]
    return {
        "viewer": {
            "username": caller.get("username"),
            "display_name": caller.get("display_name") or caller.get("username"),
            "role": caller.get("role"),
            "is_admin": caller.get("role") in ("owner", "admin"),
        },
        "surfaces": out_surfaces,
        "fetched_at": _now_iso(),
    }


@router.get("/api/cockpit/status")
async def status_all(
    x_admin_token: Optional[str] = Header(default=None),
    x_session_token: Optional[str] = Header(default=None),
    refresh: bool = Query(False),
):
    caller = _resolve_caller(x_admin_token, x_session_token)
    if refresh:
        _PING_CACHE.clear()
    visible = [s for s in SURFACES if _can_see(caller, s["id"])]
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *[_ping_one(client, s) for s in visible], return_exceptions=False
        )
    by_id = {r["id"]: r for r in results}
    summary = {
        "up": sum(1 for r in results if r["status"] == "up"),
        "down": sum(1 for r in results if r["status"] == "down"),
        "external": sum(1 for r in results if r["status"] == "external"),
        "total": len(results),
    }
    return {"summary": summary, "by_id": by_id, "checked_at": _now_iso()}


# ─── endpoints — user management ──────────────────────────────────────────
@router.get("/api/cockpit/users")
async def list_users(
    x_admin_token: Optional[str] = Header(default=None),
    x_session_token: Optional[str] = Header(default=None),
):
    caller = _resolve_caller(x_admin_token, x_session_token)
    _require_admin(caller)
    users = _read_users().get("users", [])
    return {
        "users": [_public_user(u) for u in users],
        "count": len(users),
    }


def _validate_surfaces(value: Any) -> list[str]:
    """Normalise + validate a `surfaces` field. Accepts ['*'] or a list of
    known surface ids."""
    if value in (None, "", []):
        return []
    if isinstance(value, str):
        value = [v.strip() for v in value.split(",") if v.strip()]
    if not isinstance(value, list):
        raise HTTPException(400, "surfaces must be a list")
    out = []
    for v in value:
        s = str(v).strip()
        if s == "*":
            return ["*"]
        if s not in SURFACE_IDS:
            raise HTTPException(400, f"Unknown surface id: {s!r}")
        out.append(s)
    return sorted(set(out))


def _validate_role(value: Any) -> str:
    s = str(value or "member").strip().lower()
    if s not in VALID_ROLES:
        raise HTTPException(400, f"role must be one of {sorted(VALID_ROLES)}")
    return s


_USERNAME_OK = lambda s: bool(s) and s.replace("-", "").replace("_", "").isalnum() and 2 <= len(s) <= 32


@router.post("/api/cockpit/users")
async def create_user(
    payload: dict = Body(...),
    x_admin_token: Optional[str] = Header(default=None),
    x_session_token: Optional[str] = Header(default=None),
):
    caller = _resolve_caller(x_admin_token, x_session_token)
    _require_admin(caller)
    username = str(payload.get("username") or "").strip().lower()
    if not _USERNAME_OK(username):
        raise HTTPException(400, "username must be 2–32 alphanumerics, '-' or '_'")
    if _find_user(username):
        raise HTTPException(409, "Username already exists")
    role = _validate_role(payload.get("role"))
    if role == "owner" and caller.get("role") != "owner":
        raise HTTPException(403, "Only an owner can create another owner")
    surfaces = _validate_surfaces(payload.get("surfaces") or [])
    if role in ("owner", "admin") and not surfaces:
        surfaces = ["*"]
    password = str(payload.get("password") or "").strip()
    generated = False
    if not password:
        password = secrets.token_urlsafe(12)
        generated = True
    user = {
        "username": username,
        "display_name": str(payload.get("display_name") or username).strip()[:80],
        "email": str(payload.get("email") or "").strip()[:120],
        "password_hash": _hash_password(password),
        "role": role,
        "surfaces": surfaces,
        "created_at": _now_iso(),
        "created_by": caller.get("username") or caller.get("via") or "unknown",
        "last_login_at": None,
        "session_token": None,
        "session_expires_at": None,
    }
    _save_user(user)
    out = _public_user(user)
    out["initial_password"] = password if generated else None
    return out


@router.patch("/api/cockpit/users/{username}")
async def update_user(
    username: str,
    payload: dict = Body(...),
    x_admin_token: Optional[str] = Header(default=None),
    x_session_token: Optional[str] = Header(default=None),
):
    caller = _resolve_caller(x_admin_token, x_session_token)
    _require_admin(caller)
    user = _find_user(username)
    if not user:
        raise HTTPException(404, "User not found")
    # Only owners can change owners.
    if user.get("role") == "owner" and caller.get("role") != "owner":
        raise HTTPException(403, "Only an owner can edit an owner")
    if "display_name" in payload:
        user["display_name"] = str(payload["display_name"] or "").strip()[:80] or user["username"]
    if "email" in payload:
        user["email"] = str(payload["email"] or "").strip()[:120]
    if "role" in payload:
        new_role = _validate_role(payload["role"])
        if new_role == "owner" and caller.get("role") != "owner":
            raise HTTPException(403, "Only an owner can promote to owner")
        if user.get("role") == "owner" and new_role != "owner":
            owners = sum(
                1 for u in _read_users().get("users", []) if u.get("role") == "owner"
            )
            if owners <= 1:
                raise HTTPException(400, "Can't demote the last owner")
        user["role"] = new_role
    if "surfaces" in payload:
        user["surfaces"] = _validate_surfaces(payload["surfaces"])
    _save_user(user)
    return _public_user(user)


@router.post("/api/cockpit/users/{username}/password")
async def set_password(
    username: str,
    payload: dict = Body(default={}),
    x_admin_token: Optional[str] = Header(default=None),
    x_session_token: Optional[str] = Header(default=None),
):
    """Reset a user's password. Either set `password` explicitly or omit
    it to receive a freshly-generated one."""
    caller = _resolve_caller(x_admin_token, x_session_token)
    user = _find_user(username)
    if not user:
        raise HTTPException(404, "User not found")
    is_self = (
        caller.get("username") and
        caller.get("username").lower() == user.get("username", "").lower()
    )
    if not is_self:
        _require_admin(caller)
        if user.get("role") == "owner" and caller.get("role") != "owner":
            raise HTTPException(403, "Only an owner can reset an owner's password")
    new_password = str(payload.get("password") or "").strip()
    generated = False
    if not new_password:
        new_password = secrets.token_urlsafe(12)
        generated = True
    user["password_hash"] = _hash_password(new_password)
    # Force a re-login so old sessions die.
    user["session_token"] = None
    user["session_expires_at"] = None
    _save_user(user)
    return {
        "ok": True,
        "username": user["username"],
        "new_password": new_password if generated or is_self else new_password,
    }


@router.delete("/api/cockpit/users/{username}")
async def delete_user(
    username: str,
    x_admin_token: Optional[str] = Header(default=None),
    x_session_token: Optional[str] = Header(default=None),
):
    caller = _resolve_caller(x_admin_token, x_session_token)
    _require_admin(caller)
    user = _find_user(username)
    if not user:
        raise HTTPException(404, "User not found")
    if user.get("role") == "owner":
        owners = sum(
            1 for u in _read_users().get("users", []) if u.get("role") == "owner"
        )
        if owners <= 1:
            raise HTTPException(400, "Can't delete the last owner")
        if caller.get("role") != "owner":
            raise HTTPException(403, "Only an owner can delete an owner")
    if caller.get("username") and caller["username"].lower() == username.lower():
        raise HTTPException(400, "Can't delete yourself; ask another admin")
    data = _read_users()
    data["users"] = [
        u for u in data.get("users", [])
        if (u.get("username") or "").lower() != username.lower()
    ]
    _write_users(data)
    return {"ok": True, "deleted": username}

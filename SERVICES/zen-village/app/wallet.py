"""
Zen Wallet — email-keyed persistent wallet over the UC ledger.

- Sign-up / sign-in by email + magic link (no password).
- Wallet balance is stored on the canonical fp-credits-gateway as UC.
- This module owns:
    * wallet profiles (name, email, created_at, ref code at sign-up)
    * pending top-up records for manual rails (Venmo / Zelle / cash / BTC)
    * QR codes that link guests into /wallet and /buy flows
    * affiliate hooks on confirmed top-ups and purchases
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import io
import json
import logging
import os
import secrets
import smtplib
import time
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path
from typing import Optional

import httpx
import qrcode
from fastapi import APIRouter, HTTPException, Header, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, EmailStr, Field

from app.credits import (
    ZC_LABEL_PLURAL,
    ZC_SHORT,
    ensure_account,
    format_zc,
    gateway_balance_uc,
    gateway_credit_uc,
    gateway_debit_uc,
    gateway_recent_transactions,
    wallet_id_for_email,
)
from app.topup_rails import (
    calc_bonus,
    credits_for,
    get_rail,
    hydrate_instructions,
    list_rails,
)

try:
    from app.affiliates import try_convert as affiliates_convert  # type: ignore
except Exception:
    affiliates_convert = None  # type: ignore

try:
    from app.affiliates import (  # type: ignore
        sweep_pending_commissions_to_wallet as _aff_sweep,
        link_partner_sponsor as _aff_link_sponsor,
    )
except Exception:
    _aff_sweep = None  # type: ignore
    _aff_link_sponsor = None  # type: ignore

logger = logging.getLogger("zen_wallet")

router = APIRouter()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
WALLETS_FILE = DATA_DIR / "wallets.json"
TOPUPS_FILE = DATA_DIR / "topups.json"

BASE_URL = os.getenv("ZV_PUBLIC_BASE", os.getenv("ZEN_PASS_BASE_URL", "https://zenvillagecr.com")).rstrip("/")
WALLET_SECRET = (
    os.getenv("ZV_WALLET_SECRET")
    or os.getenv("CREDITS_GATEWAY_KEY")
    or "zen-wallet-dev-secret-CHANGE-ME"
)
_ADMIN_TOKENS = {
    t for t in (
        os.getenv("ZV_ADMIN_TOKEN", ""),
        os.getenv("ZV_AFFILIATES_ADMIN_TOKEN", ""),
        os.getenv("ZEN_PASS_ADMIN_SECRET", "zenpass2026"),
    ) if t
}
COOKIE_NAME = "zv_wallet"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
MAGIC_LINK_TTL = 60 * 30  # 30 minutes

MAIL_HOST = os.getenv("MAIL_RELAY_HOST", "localhost")
MAIL_PORT = int(os.getenv("MAIL_RELAY_PORT", "25"))
MAIL_FROM = os.getenv("ZV_WALLET_MAIL_FROM", os.getenv("ZEN_PASS_MAIL_FROM", "wallet@zenvillagecr.com"))
MAIL_FROM_NAME = os.getenv("ZV_WALLET_MAIL_FROM_NAME", "Zen Village Wallet")
MAIL_REPLY_TO = os.getenv("ZV_WALLET_MAIL_REPLY_TO", "hello@zenvillagecr.com")


# ── JSON store helpers ──────────────────────────────────────────────────────

def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f) or []
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _save(path: Path, rows: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def _norm_email(email: str) -> str:
    return (email or "").strip().lower()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_profile(email: str) -> Optional[dict]:
    e = _norm_email(email)
    if not e:
        return None
    for p in _load(WALLETS_FILE):
        if p.get("email") == e:
            return p
    return None


def upsert_profile(email: str, *, name: str = "", ref: str = "") -> dict:
    e = _norm_email(email)
    if not e:
        raise ValueError("email required")
    rows = _load(WALLETS_FILE)
    for p in rows:
        if p.get("email") == e:
            if name and not p.get("name"):
                p["name"] = name
            if ref and not p.get("ref"):
                p["ref"] = ref
            p["updated_at"] = _now_iso()
            _save(WALLETS_FILE, rows)
            return p
    profile = {
        "email": e,
        "name": name or "",
        "ref": (ref or "").upper().strip() or "",
        "wallet_id": wallet_id_for_email(e),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    rows.append(profile)
    _save(WALLETS_FILE, rows)
    return profile


# ── Token signing (magic link + session cookie) ─────────────────────────────

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _sign(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    body = _b64(raw)
    sig = hmac.new(WALLET_SECRET.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def _verify(token: str, *, max_age: int) -> Optional[dict]:
    try:
        body, sig = token.split(".", 1)
        expected = hmac.new(WALLET_SECRET.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(_b64d(body).decode("utf-8"))
        if not isinstance(data, dict):
            return None
        iat = int(data.get("iat") or 0)
        if iat <= 0:
            return None
        if time.time() - iat > max_age:
            return None
        return data
    except Exception:
        return None


def _make_magic_token(email: str, *, name: str = "", ref: str = "") -> str:
    return _sign({
        "kind": "magic",
        "email": _norm_email(email),
        "name": name,
        "ref": (ref or "").upper().strip(),
        "iat": int(time.time()),
        "nonce": secrets.token_hex(8),
    })


def _make_session_token(email: str, *, name: str = "") -> str:
    return _sign({
        "kind": "session",
        "email": _norm_email(email),
        "name": name,
        "iat": int(time.time()),
    })


def _read_session(request: Request) -> Optional[dict]:
    tok = request.cookies.get(COOKIE_NAME, "")
    if not tok:
        return None
    data = _verify(tok, max_age=COOKIE_MAX_AGE)
    if not data or data.get("kind") != "session":
        return None
    return data


def _set_session_cookie(response, email: str, name: str = "") -> None:
    token = _make_session_token(email, name=name)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=True,
        path="/",
    )


# ── Email (magic link + receipts) ────────────────────────────────────────────

def _send_email_sync(to_email: str, subject: str, html: str, text: str = "") -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = formataddr((MAIL_FROM_NAME, MAIL_FROM))
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["Reply-To"] = MAIL_REPLY_TO
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="zenvillage.live")
        if text:
            msg.attach(MIMEText(text, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP(MAIL_HOST, MAIL_PORT, timeout=15) as s:
            s.sendmail(MAIL_FROM, [to_email], msg.as_string())
        return True
    except Exception as e:
        logger.warning("[zen-wallet mail] send failed to %s: %s", to_email, e)
        return False


async def _send_email(to_email: str, subject: str, html: str, text: str = "") -> bool:
    return await asyncio.to_thread(_send_email_sync, to_email, subject, html, text)


def _magic_link_email_html(magic_url: str, name: str) -> str:
    greeting = f"Hi {name}," if name else "Welcome to Zen Village,"
    return f"""<!doctype html>
<html><body style="font-family:-apple-system,Segoe UI,sans-serif;background:#0d1117;color:#e6edf3;padding:32px;">
<div style="max-width:560px;margin:auto;background:#161b22;border:1px solid #30363d;border-radius:14px;padding:36px;">
  <h1 style="margin:0 0 8px;color:#7ee787;font-size:22px;">{ZC_LABEL_PLURAL}</h1>
  <p style="margin:0 0 24px;color:#8b949e;">Your wallet is ready.</p>
  <p>{greeting}</p>
  <p>Tap the button to open your wallet. The link works once and expires in 30 minutes.</p>
  <p style="margin:28px 0;text-align:center;">
    <a href="{magic_url}" style="background:#7ee787;color:#0d1117;text-decoration:none;padding:14px 28px;border-radius:8px;font-weight:600;display:inline-block;">Open my wallet</a>
  </p>
  <p style="font-size:13px;color:#8b949e;">Or paste this URL into your browser:<br><span style="word-break:break-all;">{magic_url}</span></p>
  <p style="font-size:12px;color:#6e7681;margin-top:32px;">If you didn't request this, ignore this email.</p>
</div></body></html>"""


def _magic_link_email_text(magic_url: str, name: str) -> str:
    return (
        f"{name and ('Hi ' + name + ',') or 'Welcome to Zen Village,'}\n\n"
        f"Open your Zen Wallet (link expires in 30 min):\n{magic_url}\n\n"
        f"If you didn't request this, ignore this email."
    )


# ── Models ──────────────────────────────────────────────────────────────────

class WalletStartRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = ""
    ref: Optional[str] = ""


class TopupRequest(BaseModel):
    rail_id: str
    amount_usd: float = Field(..., gt=0, le=25000)


class TopupConfirmRequest(BaseModel):
    received_amount_usd: Optional[float] = None
    notes: Optional[str] = ""


class PurchaseRequest(BaseModel):
    item_id: str
    quantity: int = Field(1, ge=1, le=20)
    note: Optional[str] = ""


# ── Wallet auth flow ────────────────────────────────────────────────────────

@router.post("/start")
async def wallet_start(payload: WalletStartRequest, request: Request):
    """Begin sign-in: capture email, send magic link."""
    email = _norm_email(payload.email)
    name = (payload.name or "").strip()
    ref = (payload.ref or request.cookies.get("zv_ref") or "").upper().strip()

    upsert_profile(email, name=name, ref=ref)

    token = _make_magic_token(email, name=name, ref=ref)
    magic_url = f"{BASE_URL}/api/wallet/verify?token={token}"

    sent = await _send_email(
        email,
        f"Open your Zen Wallet ({ZC_SHORT})",
        _magic_link_email_html(magic_url, name),
        _magic_link_email_text(magic_url, name),
    )
    return {
        "ok": True,
        "message": "Magic link sent. Check your inbox.",
        "email": email,
        "sent": bool(sent),
    }


@router.get("/verify")
async def wallet_verify(token: str = Query(...)):
    """Consume a magic-link token → set session cookie → redirect to /wallet."""
    data = _verify(token, max_age=MAGIC_LINK_TTL)
    if not data or data.get("kind") != "magic":
        return RedirectResponse(f"{BASE_URL}/wallet?expired=1", status_code=302)
    email = _norm_email(data.get("email") or "")
    name = (data.get("name") or "").strip()
    ref = (data.get("ref") or "").upper().strip()
    if not email:
        return RedirectResponse(f"{BASE_URL}/wallet?expired=1", status_code=302)

    profile = upsert_profile(email, name=name, ref=ref)
    await ensure_account(profile["wallet_id"], email=email, name=name or email)

    # ─── Affiliate wiring ───────────────────────────────────────────────────
    # If this wallet's email matches a partner record, link the sponsor (the
    # ?ref the wallet came in with) and sweep any commissions that have been
    # accruing while the partner had no wallet to deposit into.
    try:
        if _aff_link_sponsor and ref:
            _aff_link_sponsor(email, ref)
        if _aff_sweep:
            sweep = _aff_sweep(email)
            if sweep.get("swept"):
                logger.info(
                    "wallet sign-up sweep: %s commissions, %s ZC → %s",
                    sweep["swept"], sweep["total_zc"], email,
                )
    except Exception as e:
        logger.warning("affiliate link/sweep failed for %s: %s", email, e)

    resp = RedirectResponse(f"{BASE_URL}/wallet", status_code=302)
    _set_session_cookie(resp, email, name=name or profile.get("name", ""))
    return resp


@router.post("/logout")
async def wallet_logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE_NAME, path="/")
    return resp


@router.get("/me")
async def wallet_me(request: Request):
    sess = _read_session(request)
    if not sess:
        raise HTTPException(status_code=401, detail="not signed in")
    email = sess["email"]
    profile = get_profile(email) or upsert_profile(email, name=sess.get("name", ""))
    wallet_id = profile["wallet_id"]
    balance_uc = await gateway_balance_uc(wallet_id)
    txns = await gateway_recent_transactions(wallet_id, limit=25)

    pending = [
        t for t in _load(TOPUPS_FILE)
        if t.get("email") == email and t.get("status") == "pending"
    ]

    # Earnings panel — surface partner code + lifetime/pending if this email
    # owns one or more partner records.
    earnings = None
    try:
        from app.affiliates import _load as _aff_load, PARTNERS_FILE, COMMISSIONS_FILE  # type: ignore
        partners = _aff_load(PARTNERS_FILE)
        my = [
            (code, p) for code, p in partners.items()
            if (p.get("email") or "").strip().lower() == email.lower()
        ]
        if my:
            commissions = _aff_load(COMMISSIONS_FILE)
            my_codes = {code for code, _ in my}
            mine = [c for c in commissions.values() if c.get("partner_code") in my_codes]
            paid = sum(float(c.get("commission_amount", 0)) for c in mine if c.get("status") == "paid")
            pending_zc = sum(float(c.get("commission_amount", 0)) for c in mine if c.get("status") == "pending")
            tier1_count = sum(1 for c in mine if c.get("role") in ("sourcer", "closer", "producer"))
            tier2_count = sum(1 for c in mine if c.get("role") == "tier2_sponsor")
            earnings = {
                "partner_codes": [code for code, _ in my],
                "primary_code": my[0][0],
                "lifetime_paid_zc": round(paid, 2),
                "pending_zc": round(pending_zc, 2),
                "total_commissions": len(mine),
                "tier1_count": tier1_count,
                "tier2_count": tier2_count,
                "share_url": f"https://zenvillagecr.com/?ref={my[0][0]}",
            }
    except Exception as e:
        logger.debug("earnings panel skipped: %s", e)

    return {
        "ok": True,
        "email": email,
        "name": profile.get("name", ""),
        "wallet_id": wallet_id,
        "balance_zc": round(balance_uc, 2),
        "balance_label": format_zc(balance_uc),
        "transactions": txns,
        "pending_topups": pending,
        "ref": profile.get("ref", ""),
        "earnings": earnings,
    }


# ── Top-up flow ─────────────────────────────────────────────────────────────

@router.get("/rails")
async def wallet_rails():
    rails = list_rails()
    public = []
    for r in rails:
        public.append({
            "id": r["id"],
            "name": r["name"],
            "type": r["type"],
            "fee_pct": r["fee_pct"],
            "bonus_rate": r["bonus_rate"],
            "min_usd": r.get("min_usd", 5),
            "max_usd": r.get("max_usd", 5000),
            "instant": r["type"] == "instant",
        })
    return {"ok": True, "rails": public}


@router.post("/topup")
async def wallet_topup(payload: TopupRequest, request: Request):
    sess = _read_session(request)
    if not sess:
        raise HTTPException(status_code=401, detail="not signed in")
    rail = get_rail(payload.rail_id)
    if not rail:
        raise HTTPException(status_code=400, detail="unknown rail")
    if payload.amount_usd < rail.get("min_usd", 5):
        raise HTTPException(status_code=400, detail=f"min ${rail.get('min_usd', 5)}")
    if payload.amount_usd > rail.get("max_usd", 5000):
        raise HTTPException(status_code=400, detail=f"max ${rail.get('max_usd', 5000)}")

    email = sess["email"]
    profile = get_profile(email) or upsert_profile(email, name=sess.get("name", ""))
    ref = (uuid.uuid4().hex[:8]).upper()
    expected = credits_for(rail["id"], payload.amount_usd)

    record = {
        "ref": ref,
        "email": email,
        "wallet_id": profile["wallet_id"],
        "rail_id": rail["id"],
        "rail_name": rail["name"],
        "rail_type": rail["type"],
        "amount_usd": float(payload.amount_usd),
        "bonus_zc": expected["bonus"],
        "total_zc": expected["total"],
        "status": "pending",
        "created_at": _now_iso(),
        "confirmed_at": "",
        "confirmed_by": "",
        "notes": "",
        "partner_code": profile.get("ref", ""),
    }
    rows = _load(TOPUPS_FILE)
    rows.append(record)
    _save(TOPUPS_FILE, rows)

    instructions = hydrate_instructions(rail, ref)
    return {
        "ok": True,
        "ref": ref,
        "rail": rail["id"],
        "rail_name": rail["name"],
        "instant": rail["type"] == "instant",
        "amount_usd": record["amount_usd"],
        "bonus_zc": record["bonus_zc"],
        "total_zc": record["total_zc"],
        "instructions": instructions,
        "status": "pending",
    }


# ── Admin: top-up confirm / cancel / list ───────────────────────────────────

def _require_admin(token_header: str) -> None:
    if not token_header or token_header not in _ADMIN_TOKENS:
        raise HTTPException(status_code=403, detail="admin token required")


@router.get("/topups")
async def wallet_topups_list(
    status: Optional[str] = Query("pending"),
    limit: int = Query(50, ge=1, le=500),
    x_admin_token: str = Header(""),
):
    _require_admin(x_admin_token)
    rows = _load(TOPUPS_FILE)
    if status and status != "all":
        rows = [r for r in rows if r.get("status") == status]
    rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return {"ok": True, "count": len(rows), "topups": rows[:limit]}


@router.post("/topups/{ref}/confirm")
async def wallet_topup_confirm(
    ref: str,
    payload: TopupConfirmRequest,
    x_admin_token: str = Header(""),
):
    _require_admin(x_admin_token)
    rows = _load(TOPUPS_FILE)
    target = None
    for r in rows:
        if r.get("ref") == ref:
            target = r
            break
    if not target:
        raise HTTPException(status_code=404, detail="topup not found")
    if target.get("status") == "confirmed":
        return {"ok": True, "already_confirmed": True, "topup": target}
    if target.get("status") == "cancelled":
        raise HTTPException(status_code=400, detail="topup is cancelled")

    received = float(payload.received_amount_usd or target["amount_usd"])
    bonus = calc_bonus(target["rail_id"], received)
    total_zc = round(received + bonus, 2)

    profile = get_profile(target["email"]) or upsert_profile(target["email"])
    await ensure_account(profile["wallet_id"], email=target["email"], name=profile.get("name", ""))
    res = await gateway_credit_uc(
        profile["wallet_id"],
        total_zc,
        f"Zen Wallet top-up via {target['rail_name']} (ref {ref})",
        metadata={
            "kind": "wallet_topup",
            "rail": target["rail_id"],
            "ref": ref,
            "amount_usd": received,
            "bonus_zc": bonus,
            "partner_code": target.get("partner_code", ""),
        },
    )
    if not res.get("ok"):
        raise HTTPException(status_code=502, detail=f"ledger credit failed: {res.get('error')}")

    target["status"] = "confirmed"
    target["confirmed_at"] = _now_iso()
    target["confirmed_by"] = "admin"
    target["received_amount_usd"] = received
    target["bonus_zc"] = bonus
    target["total_zc"] = total_zc
    target["notes"] = (payload.notes or "").strip()[:500]
    _save(TOPUPS_FILE, rows)

    if affiliates_convert and target.get("partner_code"):
        try:
            affiliates_convert(
                target["partner_code"],
                "credits_topup",
                received,
                guest_email=target["email"],
                source_id=f"wallet_topup:{ref}",
                booking_details=f"Wallet top-up via {target['rail_name']}",
            )
        except Exception as e:
            logger.warning("affiliate try_convert on topup %s failed: %s", ref, e)

    return {"ok": True, "topup": target}


@router.post("/topups/{ref}/cancel")
async def wallet_topup_cancel(
    ref: str,
    x_admin_token: str = Header(""),
):
    _require_admin(x_admin_token)
    rows = _load(TOPUPS_FILE)
    for r in rows:
        if r.get("ref") == ref:
            if r.get("status") == "confirmed":
                raise HTTPException(status_code=400, detail="already confirmed")
            r["status"] = "cancelled"
            r["confirmed_at"] = _now_iso()
            _save(TOPUPS_FILE, rows)
            return {"ok": True, "topup": r}
    raise HTTPException(status_code=404, detail="topup not found")


# ── QR codes ────────────────────────────────────────────────────────────────

def _qr_png(target_url: str, *, box_size: int = 10, border: int = 2) -> bytes:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(target_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0d1117", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@router.get("/qr/new")
async def wallet_qr_new(ref: str = Query(""), size: int = Query(10, ge=4, le=20)):
    url = f"{BASE_URL}/wallet/new"
    if ref:
        url += f"?ref={ref.upper().strip()}"
    png = _qr_png(url, box_size=size)
    return StreamingResponse(io.BytesIO(png), media_type="image/png")


@router.get("/qr/buy/{item_id}")
async def wallet_qr_buy(item_id: str, size: int = Query(10, ge=4, le=20)):
    url = f"{BASE_URL}/buy?item={item_id}"
    png = _qr_png(url, box_size=size)
    return StreamingResponse(io.BytesIO(png), media_type="image/png")


# ── Wallet-driven purchase (Zen Store / Zen Menu) ───────────────────────────

@router.get("/items")
async def wallet_items_proxy(event_id: str = Query("default")):
    """Public list of purchasable items. Reads from zen_pass items table."""
    import sqlite3 as _sql
    db_path = DATA_DIR / "zen_pass.db"
    if not db_path.exists():
        return {"ok": True, "items": []}
    conn = _sql.connect(str(db_path))
    conn.row_factory = _sql.Row
    rows = conn.execute(
        "SELECT * FROM items WHERE active = 1" + (" AND event_id = ?" if event_id else ""),
        ([event_id] if event_id else []),
    ).fetchall()
    conn.close()
    items = []
    for r in rows:
        d = dict(r)
        items.append({
            "id": d.get("id"),
            "name": d.get("name"),
            "description": d.get("description") or "",
            "price_zc": float(d.get("price_credits") or 0),
            "category": d.get("category") or "general",
            "image_url": d.get("image_url") or "",
            "emoji": d.get("emoji") or "",
            "stock": d.get("stock"),
            "buy_url": f"{BASE_URL}/buy?item={d.get('id')}",
        })
    return {"ok": True, "items": items}


@router.get("/items/{item_id}")
async def wallet_item_get(item_id: str):
    import sqlite3 as _sql
    db_path = DATA_DIR / "zen_pass.db"
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="item not found")
    conn = _sql.connect(str(db_path))
    conn.row_factory = _sql.Row
    row = conn.execute(
        "SELECT * FROM items WHERE id = ? AND active = 1", (item_id,)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="item not found")
    d = dict(row)
    return {
        "ok": True,
        "id": d.get("id"),
        "name": d.get("name"),
        "description": d.get("description") or "",
        "price_zc": float(d.get("price_credits") or 0),
        "category": d.get("category") or "general",
        "image_url": d.get("image_url") or "",
        "emoji": d.get("emoji") or "",
        "stock": d.get("stock"),
    }


@router.post("/purchase")
async def wallet_purchase(payload: PurchaseRequest, request: Request):
    """Buy an item using Zen Credits from the signed-in wallet."""
    sess = _read_session(request)
    if not sess:
        raise HTTPException(status_code=401, detail="not signed in")

    import sqlite3 as _sql
    db_path = DATA_DIR / "zen_pass.db"
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="store not available")

    qty = payload.quantity
    conn = _sql.connect(str(db_path))
    conn.row_factory = _sql.Row
    item_row = conn.execute(
        "SELECT * FROM items WHERE id = ? AND active = 1", (payload.item_id,)
    ).fetchone()
    if not item_row:
        conn.close()
        raise HTTPException(status_code=404, detail="item not available")
    if item_row["stock"] is not None and item_row["stock"] >= 0 and item_row["stock"] < qty:
        conn.close()
        raise HTTPException(status_code=409, detail=f"only {item_row['stock']} left")

    total_price = float(item_row["price_credits"]) * qty
    item_name = item_row["name"]

    profile = get_profile(sess["email"]) or upsert_profile(sess["email"], name=sess.get("name", ""))
    balance = await gateway_balance_uc(profile["wallet_id"])
    if balance < total_price:
        conn.close()
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient Zen Credits. Need {total_price}, have {balance:.2f}. Top up your wallet.",
        )

    description = f"Purchased: {item_name}" + (f" x{qty}" if qty > 1 else "")
    if payload.note:
        description += f" — {payload.note[:120]}"

    debit = await gateway_debit_uc(
        profile["wallet_id"],
        total_price,
        description,
        metadata={
            "kind": "wallet_purchase",
            "item_id": payload.item_id,
            "quantity": qty,
            "email": sess["email"],
        },
    )
    if not debit.get("ok"):
        conn.close()
        raise HTTPException(status_code=502, detail=f"debit failed: {debit.get('error')}")

    txn_id = uuid.uuid4().hex[:12]
    now = _now_iso()
    conn.execute(
        "INSERT INTO transactions (id, pass_id, item_id, type, amount, description, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (txn_id, profile["wallet_id"], payload.item_id, "purchase", total_price, description, now),
    )
    if item_row["stock"] is not None and item_row["stock"] >= 0:
        conn.execute("UPDATE items SET stock = stock - ? WHERE id = ?", (qty, payload.item_id))
    conn.commit()
    conn.close()

    new_balance = await gateway_balance_uc(profile["wallet_id"])

    if affiliates_convert and profile.get("ref"):
        try:
            affiliates_convert(
                profile["ref"],
                "spend",
                total_price,
                guest_email=sess["email"],
                source_id=f"wallet_spend:{txn_id}",
                booking_details=f"Spend: {item_name}",
            )
        except Exception as e:
            logger.warning("affiliate try_convert on purchase %s failed: %s", txn_id, e)

    try:
        from app.telegram_send import send_to_admins  # type: ignore
        emoji = item_row["emoji"] or "🌿"
        send_to_admins(
            f"{emoji} <b>Wallet purchase</b>\n"
            f"{item_name}{(' x' + str(qty)) if qty > 1 else ''} — {total_price:.0f} ZC\n"
            f"Buyer: {sess['email']}\n"
            f"Balance after: {new_balance:.0f} ZC"
        )
    except Exception:
        pass

    return {
        "ok": True,
        "transaction_id": txn_id,
        "item": item_name,
        "quantity": qty,
        "charged_zc": total_price,
        "balance_zc": round(new_balance, 2),
    }


# ── Internal helper for purchase flow (called from zen_pass) ────────────────

async def credit_wallet_from_purchase(
    email: str,
    amount_usd: float,
    *,
    item_id: str = "",
    item_name: str = "",
    rail: str = "stripe_card",
) -> dict:
    """Credit a wallet from a completed payment (e.g. Stripe checkout).
    Returns the gateway response. Idempotency must be enforced by the caller.
    """
    profile = get_profile(email) or upsert_profile(email)
    bonus = calc_bonus(rail, amount_usd) if rail else 0.0
    total_zc = round(float(amount_usd) + bonus, 2)
    await ensure_account(profile["wallet_id"], email=email, name=profile.get("name", ""))
    return await gateway_credit_uc(
        profile["wallet_id"],
        total_zc,
        f"Zen Wallet credit ({item_name or 'top-up'})",
        metadata={
            "kind": "wallet_credit",
            "item_id": item_id,
            "amount_usd": float(amount_usd),
            "bonus_zc": bonus,
            "rail": rail,
        },
    )

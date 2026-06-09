"""
Zen Pass — Credits-powered digital pass system for Zen Village.

Guests buy credits (via Stripe, Venmo, PayPal, crypto), get a personal
QR-coded pass, and use it for event check-in and item purchases.
"""

import asyncio
import hashlib
import io
import json
import os
import smtplib
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path
from typing import Optional

import httpx
import qrcode
import stripe
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr

router = APIRouter()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "zen_pass.db"
BASE_URL = os.getenv("ZEN_PASS_BASE_URL", "https://zenvillagecr.com")
CREDITS_GATEWAY = os.getenv("CREDITS_GATEWAY_URL", "http://127.0.0.1:8765")
CREDITS_API_KEY = os.getenv("CREDITS_GATEWAY_KEY", "")
STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# NocoDB sync (Passes table) — best-effort mirror of the SQLite source of truth.
NOCODB_URL = os.getenv("NOCODB_URL", "http://127.0.0.1:8080").rstrip("/")
NOCODB_TOKEN = os.getenv("NOCODB_API_TOKEN", "")
NOCODB_PASSES_TABLE = os.getenv("NOCODB_PASSES_TABLE_ID", "")


def _sync_pass_to_nocodb(pass_id: str) -> None:
    """Upsert one pass row from SQLite into NocoDB. Never raises."""
    if not (NOCODB_TOKEN and NOCODB_PASSES_TABLE and pass_id):
        return
    try:
        import urllib.request as _ureq
        import urllib.parse as _uparse
        conn = _db()
        row = conn.execute("SELECT * FROM passes WHERE id = ?", (pass_id,)).fetchone()
        conn.close()
        if not row:
            return
        d = dict(row)
        stage = (d.get("stage") or "complete").lower()
        if stage not in ("incomplete", "complete", "cancelled"):
            stage = "complete"
        pay_status = (d.get("payment_status") or "pending").lower()
        if pay_status not in ("pending", "paid", "refunded"):
            pay_status = "pending"
        role = (d.get("role") or "guest").lower()
        if role not in ("guest", "volunteer", "crew", "practitioner", "vip"):
            role = "guest"
        payload = {
            "PassId": d.get("id") or "",
            "EventId": d.get("event_id") or "",
            "Stage": stage,
            "PaymentStatus": pay_status,
            "Waitlisted": bool(d.get("waitlisted")),
            "CheckedIn": bool(d.get("checked_in")),
            "Role": role,
            "Name": (d.get("name") or "")[:255],
            "Email": (d.get("email") or "")[:255],
            "Phone": (d.get("phone") or "")[:64],
            "PaymentMethod": (d.get("payment_method") or "")[:64],
            "AmountIntended": float(d.get("amount_intended") or 0),
            "AmountPaid": float(d.get("amount_paid") or 0),
            "Notes": (d.get("notes") or "")[:8000],
            "CreatedAt": d.get("created_at") or "",
            "CheckedInAt": d.get("checked_in_at") or None,
        }
        # Try to find existing row with same PassId
        where = _uparse.quote(f"(PassId,eq,{pass_id})")
        list_url = f"{NOCODB_URL}/api/v2/tables/{NOCODB_PASSES_TABLE}/records?where={where}&limit=1&fields=Id,PassId"
        req = _ureq.Request(list_url, headers={"xc-token": NOCODB_TOKEN})
        existing = json.loads(_ureq.urlopen(req, timeout=5).read()).get("list", [])
        if existing and existing[0].get("Id"):
            # PATCH — update existing row
            payload_with_id = dict(payload)
            payload_with_id["Id"] = existing[0]["Id"]
            req2 = _ureq.Request(
                f"{NOCODB_URL}/api/v2/tables/{NOCODB_PASSES_TABLE}/records",
                data=json.dumps([payload_with_id]).encode(),
                method="PATCH",
                headers={"xc-token": NOCODB_TOKEN, "Content-Type": "application/json"},
            )
            _ureq.urlopen(req2, timeout=5).read()
        else:
            req2 = _ureq.Request(
                f"{NOCODB_URL}/api/v2/tables/{NOCODB_PASSES_TABLE}/records",
                data=json.dumps(payload).encode(),
                method="POST",
                headers={"xc-token": NOCODB_TOKEN, "Content-Type": "application/json"},
            )
            _ureq.urlopen(req2, timeout=5).read()
    except Exception as e:
        print(f"[zen-pass] nocodb sync failed for {pass_id}: {e}")
ADMIN_SECRET = os.getenv("ZEN_PASS_ADMIN_SECRET", "zenpass2026")

# Mail relay (Brevo via local Postfix on port 25). Override per env if needed.
MAIL_HOST = os.getenv("MAIL_RELAY_HOST", "localhost")
MAIL_PORT = int(os.getenv("MAIL_RELAY_PORT", "25"))
MAIL_FROM = os.getenv("ZEN_PASS_MAIL_FROM", "peace@fullpotential.com")
MAIL_FROM_NAME = os.getenv("ZEN_PASS_MAIL_FROM_NAME", "Zen Village")
MAIL_REPLY_TO = os.getenv("ZEN_PASS_MAIL_REPLY_TO", "hello@zenvillagecr.com")

# Frictionless item-buy URL: scanning an item's QR code opens this URL with
# ?item={id}. The /buy/ page handles checkout against the user's pass balance.
ITEM_BUY_URL = os.getenv("ZEN_PASS_BUY_URL", "https://zenvillage.live/buy/?item=")

# Credits issued per USD donated. Generosity multiplier — set >1.0 to thank
# donors with bonus credits ("you donated $50, here's 60 to spend at the gathering").
CREDIT_RATIO = float(os.getenv("ZEN_PASS_CREDIT_RATIO", "1.0"))

# Per-event landing URLs (override via DB notes/metadata in future; static for now).
EVENT_LANDING_URLS = {
    "world-peace-weekend": "https://zenvillage.live/peace",           # legacy event_id
    "world-peace-gathering-2026-05-31": "https://zenvillage.live/peace",
    "default": "https://zenvillagecr.com",
}
EVENT_THANKS_URLS = {
    "world-peace-weekend": "https://zenvillage.live/peace/thanks/?pass={PASS_ID}",
    "world-peace-gathering-2026-05-31": "https://zenvillage.live/peace/thanks/?pass={PASS_ID}",
    "default": f"{BASE_URL}/pass/{{PASS_ID}}",
}

PAYMENT_METHODS = {
    "stripe": {"name": "Credit / Debit Card", "type": "instant"},
    "venmo": {"name": "Venmo", "address": "@James-Stinson-65", "type": "manual"},
    "paypal": {"name": "PayPal", "address": "james@fullpotential.com", "type": "manual"},
    "btc": {"name": "Bitcoin", "address": "13tXYGWCZWgPoZ8WZXi7vTt2kwax2ekpz7", "type": "manual"},
    "cash": {"name": "Cash (at event)", "type": "manual"},
}

if STRIPE_SECRET:
    stripe.api_key = STRIPE_SECRET


# ── Database ─────────────────────────────────────────────────────────────────

def _db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_pass_db():
    conn = _db()
    # Idempotent: ensure partner_code column exists for affiliates
    try:
        conn.execute("ALTER TABLE passes ADD COLUMN partner_code TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS passes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT DEFAULT '',
            credits_account TEXT DEFAULT '',
            balance_usd REAL DEFAULT 0,
            payment_method TEXT DEFAULT '',
            payment_status TEXT DEFAULT 'pending',
            amount_paid REAL DEFAULT 0,
            amount_intended REAL DEFAULT 0,
            checked_in INTEGER DEFAULT 0,
            checked_in_at TEXT DEFAULT '',
            event_id TEXT DEFAULT 'default',
            notes TEXT DEFAULT '',
            stage TEXT DEFAULT 'incomplete',
            waitlisted INTEGER DEFAULT 0,
            confirmation_sent_at TEXT DEFAULT '',
            followup_sent_at TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            date TEXT DEFAULT '',
            description TEXT DEFAULT '',
            price_usd REAL DEFAULT 0,
            capacity INTEGER DEFAULT 0,
            location TEXT DEFAULT 'Zen Village, Chirripó, Costa Rica',
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            price_credits REAL NOT NULL,
            category TEXT DEFAULT 'general',
            image_url TEXT DEFAULT '',
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            pass_id TEXT NOT NULL,
            item_id TEXT DEFAULT '',
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
    """)
    # Seed default event if none exists
    row = conn.execute("SELECT COUNT(*) as c FROM events").fetchone()
    if row["c"] == 0:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO events (id, name, date, description, price_usd, capacity, created_at) VALUES (?,?,?,?,?,?,?)",
            ("default", "Zen Village Experience", "", "An immersive reset in the mountains of Costa Rica. River, sauna, fire, nature, and space to reconnect.", 0, 50, now),
        )
        conn.commit()
    # Lightweight migrations for existing DBs (idempotent).
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(passes)").fetchall()}
    for col, ddl in [
        ("amount_intended", "ALTER TABLE passes ADD COLUMN amount_intended REAL DEFAULT 0"),
        ("stage", "ALTER TABLE passes ADD COLUMN stage TEXT DEFAULT 'complete'"),
        ("waitlisted", "ALTER TABLE passes ADD COLUMN waitlisted INTEGER DEFAULT 0"),
        ("confirmation_sent_at", "ALTER TABLE passes ADD COLUMN confirmation_sent_at TEXT DEFAULT ''"),
        ("followup_sent_at", "ALTER TABLE passes ADD COLUMN followup_sent_at TEXT DEFAULT ''"),
        ("role", "ALTER TABLE passes ADD COLUMN role TEXT DEFAULT 'guest'"),
    ]:
        if col not in cols:
            try: conn.execute(ddl)
            except Exception: pass
    item_cols = {r["name"] for r in conn.execute("PRAGMA table_info(items)").fetchall()}
    for col, ddl in [
        ("stock", "ALTER TABLE items ADD COLUMN stock INTEGER DEFAULT -1"),
        ("emoji", "ALTER TABLE items ADD COLUMN emoji TEXT DEFAULT ''"),
        ("event_id", "ALTER TABLE items ADD COLUMN event_id TEXT DEFAULT 'default'"),
    ]:
        if col not in item_cols:
            try: conn.execute(ddl)
            except Exception: pass
    txn_cols = {r["name"] for r in conn.execute("PRAGMA table_info(transactions)").fetchall()}
    for col, ddl in [
        ("fulfilled", "ALTER TABLE transactions ADD COLUMN fulfilled INTEGER DEFAULT 0"),
        ("fulfilled_at", "ALTER TABLE transactions ADD COLUMN fulfilled_at TEXT DEFAULT ''"),
    ]:
        if col not in txn_cols:
            try: conn.execute(ddl)
            except Exception: pass
    conn.commit()
    conn.close()


# ── Email (via local Postfix → Brevo) ────────────────────────────────────────

def _send_email_sync(to_email: str, subject: str, html: str, text: Optional[str] = None) -> bool:
    """Blocking SMTP send. Use _send_email() in async contexts."""
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
        print(f"[zen-pass mail] send failed to {to_email}: {e}")
        return False


async def _send_email(to_email: str, subject: str, html: str, text: Optional[str] = None) -> bool:
    return await asyncio.to_thread(_send_email_sync, to_email, subject, html, text)


def _landing_url(event_id: str) -> str:
    return EVENT_LANDING_URLS.get(event_id, EVENT_LANDING_URLS["default"])


def _thanks_url(event_id: str, pass_id: str) -> str:
    tpl = EVENT_THANKS_URLS.get(event_id, EVENT_THANKS_URLS["default"])
    return tpl.replace("{PASS_ID}", pass_id)


def _ical_for(event: dict, pass_id: str) -> str:
    # Loose times — caller can refine in event.notes later.
    dt_start = "20260502T220000Z"
    dt_end = "20260504T020000Z"
    return "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Zen Village//Zen Pass//EN",
        "BEGIN:VEVENT", f"UID:{pass_id}@zenvillage.live",
        f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART:{dt_start}", f"DTEND:{dt_end}",
        f"SUMMARY:{event.get('name', 'Zen Village')}",
        f"LOCATION:{event.get('location', 'Zen Village, Costa Rica')}",
        f"URL:{_landing_url(event.get('id', 'default'))}",
        "END:VEVENT", "END:VCALENDAR",
    ])


def _confirmation_email_html(p: dict, event: dict) -> str:
    landing = _landing_url(event.get("id", "default"))
    thanks = _thanks_url(event.get("id", "default"), p["id"])
    paid_line = ""
    if (p.get("amount_paid") or 0) > 0:
        paid_line = f"<p style='margin:12px 0;'>Contribution received: <strong>${p['amount_paid']:.0f}</strong> · thank you 🤍</p>"
    elif (p.get("amount_intended") or 0) > 0 and p.get("payment_method") not in ("stripe", "cash"):
        paid_line = f"<p style='margin:12px 0;color:#a87426;'>Awaiting your <strong>${p['amount_intended']:.0f}</strong> contribution via <strong>{p.get('payment_method','')}</strong> — reference <code>ZenPass-{p['id']}</code>.</p>"
    return f"""<!DOCTYPE html><html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;background:#f9f5ee;margin:0;padding:32px 16px;color:#1a1530;">
<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:16px;padding:32px 28px;box-shadow:0 20px 40px -16px rgba(26,21,48,.15);">
  <p style="font-family:Georgia,serif;color:#6ba89f;font-style:italic;margin:0 0 4px;">✓ confirmed</p>
  <h1 style="font-family:Georgia,serif;font-weight:400;font-size:34px;margin:0 0 4px;">You're in, {p['name'].split(' ')[0]}.</h1>
  <p style="color:#5b557a;margin:0 0 22px;">{event.get('name','')} · {event.get('date','')}</p>
  {paid_line}
  <div style="background:linear-gradient(135deg,rgba(155,124,199,.08),rgba(232,200,122,.08));border:1px dashed rgba(26,21,48,.12);border-radius:14px;padding:20px;text-align:center;margin:18px 0;">
    <p style="font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:#5b557a;margin:0 0 6px;">Your ticket</p>
    <p style="font-family:ui-monospace,monospace;font-size:22px;letter-spacing:.15em;margin:0 0 14px;">{p['id']}</p>
    <a href="{thanks}" style="display:inline-block;background:#1a1530;color:#f9f5ee;padding:12px 24px;border-radius:999px;text-decoration:none;font-size:13px;letter-spacing:.1em;text-transform:uppercase;">View ticket + QR →</a>
  </div>
  <p style="margin:18px 0 6px;"><strong>📅 When:</strong> {event.get('date','')}</p>
  <p style="margin:6px 0;"><strong>📍 Where:</strong> {event.get('location','Zen Village, Costa Rica')}</p>
  <p style="margin:6px 0;"><strong>🌿 Bring:</strong> A potluck dish for Sunday · open heart · clothes for river + cool nights</p>
  <p style="color:#5b557a;font-size:13px;margin:24px 0 0;line-height:1.6;">We'll send directions + the arrival flow a few days before. Reply to this email any time — questions, dietary needs, anything.</p>
  <p style="font-family:Georgia,serif;font-style:italic;color:#9b7cc7;margin:28px 0 0;text-align:center;">peace lives here ✿</p>
  <p style="text-align:center;color:#5b557a;font-size:12px;margin:8px 0 0;"><a href="{landing}" style="color:#9b7cc7;">{landing.replace('https://','')}</a></p>
</div></body></html>"""


def _followup_email_html(p: dict, event: dict) -> str:
    thanks = _thanks_url(event.get("id", "default"), p["id"])
    landing = _landing_url(event.get("id", "default"))
    return f"""<!DOCTYPE html><html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;background:#f9f5ee;margin:0;padding:32px 16px;color:#1a1530;">
<div style="max-width:520px;margin:0 auto;background:#fff;border-radius:16px;padding:32px 28px;box-shadow:0 20px 40px -16px rgba(26,21,48,.15);">
  <p style="font-family:Georgia,serif;color:#9b7cc7;font-style:italic;margin:0 0 4px;">a gentle nudge</p>
  <h1 style="font-family:Georgia,serif;font-weight:400;font-size:30px;margin:0 0 14px;">Hi {p['name'].split(' ')[0]} — your spot is still held 🤍</h1>
  <p style="color:#5b557a;line-height:1.6;">You started signing up for <strong>{event.get('name','')}</strong> ({event.get('date','')}) but didn't quite finish. Your spot is still saved.</p>
  <p style="color:#5b557a;line-height:1.6;">If you'd like to lock it in (or even just say "I'm coming, I'll pay at the gate"), it takes 30 seconds:</p>
  <p style="text-align:center;margin:24px 0;"><a href="{thanks}" style="display:inline-block;background:#1a1530;color:#f9f5ee;padding:14px 28px;border-radius:999px;text-decoration:none;font-size:13px;letter-spacing:.1em;text-transform:uppercase;">Finish my RSVP →</a></p>
  <p style="color:#5b557a;font-size:13px;line-height:1.6;">Or just reply to this email and we'll handle it for you. No pressure — but the field is gathering and we'd love you in it.</p>
  <p style="font-family:Georgia,serif;font-style:italic;color:#9b7cc7;margin:24px 0 0;text-align:center;">see you at the river ✿</p>
  <p style="text-align:center;color:#5b557a;font-size:12px;margin:6px 0 0;"><a href="{landing}" style="color:#9b7cc7;">{landing.replace('https://','')}</a></p>
</div></body></html>"""


def _short_id():
    return uuid.uuid4().hex[:10].upper()


# ── Models ───────────────────────────────────────────────────────────────────

class PassCreate(BaseModel):
    partner_code: Optional[str] = ""  # affiliates: filled from ?ref= cookie or query
    name: str
    email: EmailStr
    phone: str = ""
    payment_method: str = "stripe"
    amount: float = 0
    event_id: str = "default"
    guests: int = 1
    notes: str = ""
    success_url: str = ""
    cancel_url: str = ""

class PaymentConfirm(BaseModel):
    pass_id: str
    amount: float
    method: str = ""
    admin_key: str = ""

class ItemCreate(BaseModel):
    name: str
    description: str = ""
    price_credits: float
    category: str = "general"
    emoji: str = ""
    image_url: str = ""
    stock: int = -1   # -1 = unlimited
    event_id: str = "default"

class ItemUpdate(BaseModel):
    name: str = ""
    description: str = ""
    price_credits: float = -1
    category: str = ""
    emoji: str = ""
    image_url: str = ""
    stock: int = -2   # -2 sentinel "no change", -1 = unlimited, >=0 = stock count
    active: int = -1  # -1 sentinel "no change", 0 or 1 otherwise
    event_id: str = ""

class ItemPurchase(BaseModel):
    pass_id: str
    item_id: str
    quantity: int = 1
    note: str = ""

class RewardCredits(BaseModel):
    amount: float
    reason: str = "Volunteer / community contribution"

class EventUpdate(BaseModel):
    name: str = ""
    date: str = ""
    description: str = ""
    price_usd: float = 0
    capacity: int = 0


# ── QR Generation ────────────────────────────────────────────────────────────

def generate_qr_png(data: str) -> bytes:
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a2e1a", back_color="#faf9f5")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


# ── Credits Gateway helpers ──────────────────────────────────────────────────

async def _gateway_create_account(pass_id: str, name: str, email: str = ""):
    """Create an account in the FP Credits Gateway. Required before crediting.
    Idempotent: returns existing account if it already exists."""
    if not CREDITS_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            payload = {
                "account_id": f"zenpass:{pass_id}",
                "account_type": "user",
                "display_name": name or pass_id,
            }
            if email:
                payload["email"] = email
            resp = await c.post(f"{CREDITS_GATEWAY}/api/accounts", json=payload,
                                headers={"X-API-Key": CREDITS_API_KEY})
            if resp.status_code < 300:
                return resp.json()
            # 409 = already exists, fine
            if resp.status_code == 409:
                return {"existed": True}
            print(f"[gateway create_account] {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"[gateway create_account] failed: {e}")
        return None


async def _gateway_ensure_account(pass_id: str, name: str = "", email: str = ""):
    """Idempotently make sure the gateway account exists. No-op if it does."""
    if not CREDITS_API_KEY:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            resp = await c.get(f"{CREDITS_GATEWAY}/api/accounts/zenpass:{pass_id}",
                               headers={"X-API-Key": CREDITS_API_KEY})
            if resp.status_code < 300:
                return True
            if resp.status_code != 404:
                return False
            # Need to create it
            payload = {
                "account_id": f"zenpass:{pass_id}",
                "account_type": "user",
                "display_name": name or pass_id,
            }
            if email:
                payload["email"] = email
            resp = await c.post(f"{CREDITS_GATEWAY}/api/accounts", json=payload,
                                headers={"X-API-Key": CREDITS_API_KEY})
            if resp.status_code < 300 or resp.status_code == 409:
                return True
            print(f"[gateway ensure_account] {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"[gateway ensure_account] failed: {e}")
        return False


async def _gateway_credit(pass_id: str, amount: float, description: str = "",
                          apply_ratio: bool = True, name: str = "", email: str = ""):
    """Credit Zen Credits to a pass account.
    If apply_ratio=True, USD amount is multiplied by CREDIT_RATIO (default 1.0).
    Auto-creates the gateway account if missing."""
    if not CREDITS_API_KEY:
        return None
    if amount <= 0:
        return None
    await _gateway_ensure_account(pass_id, name, email)
    try:
        credits = amount * (CREDIT_RATIO if apply_ratio else 1.0)
        async with httpx.AsyncClient(timeout=10) as c:
            resp = await c.post(f"{CREDITS_GATEWAY}/api/credit", json={
                "account_id": f"zenpass:{pass_id}", "amount": credits,
                "credit_type": "uc",
                "reason": (description or f"Zen Credits ({credits:.2f})")[:500],
            }, headers={"X-API-Key": CREDITS_API_KEY})
            if resp.status_code < 300:
                return resp.json()
            print(f"[gateway credit] {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"[gateway credit] failed: {e}")
        return None


async def _gateway_balance(pass_id: str) -> float:
    if not CREDITS_API_KEY:
        return 0
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            resp = await c.get(f"{CREDITS_GATEWAY}/api/balance/zenpass:{pass_id}",
                               headers={"X-API-Key": CREDITS_API_KEY})
            if resp.status_code < 300:
                data = resp.json() or {}
                balances = data.get("balances") or {}
                if "uc" in balances:
                    return float(balances.get("uc") or 0)
                return float(data.get("balance",
                       data.get("total_value_usd",
                       data.get("amount", 0))))
    except Exception as e:
        print(f"[gateway balance] failed: {e}")
    return 0


async def _gateway_debit(pass_id: str, amount: float, description: str = ""):
    if not CREDITS_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            resp = await c.post(f"{CREDITS_GATEWAY}/api/debit", json={
                "account_id": f"zenpass:{pass_id}", "amount": amount,
                "credit_type": "uc",
                "reason": (description or f"Debit {amount}")[:500]
            }, headers={"X-API-Key": CREDITS_API_KEY})
            return resp.json() if resp.status_code < 300 else None
    except Exception:
        return None


# ── Telegram notification ────────────────────────────────────────────────────

async def _notify_james(text: str):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post("http://127.0.0.1:8550/api/v1/brain/notify", json={
                "source": "zen-pass", "subject": "Zen Pass", "message": text
            })
    except Exception:
        pass


# ── API Routes ───────────────────────────────────────────────────────────────

@router.get("/api/pass/event")
async def get_event(event_id: str = "default", list: int = 0):
    """Single-event lookup (default) or a lightweight directory of all events.

    - GET /api/pass/event             → details for the 'default' event
    - GET /api/pass/event?event_id=X  → details for event X
    - GET /api/pass/event?list=1      → {events: [...]} for every active event
    """
    conn = _db()
    if list:
        rows = conn.execute(
            "SELECT * FROM events WHERE active = 1 ORDER BY date ASC, created_at DESC"
        ).fetchall()
        conn.close()
        return {"events": [dict(r) for r in rows]}
    row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Event not found")
    return dict(row)


@router.post("/api/pass/event")
async def update_event(data: EventUpdate, admin_key: str = ""):
    if admin_key != ADMIN_SECRET:
        raise HTTPException(403, "Invalid admin key")
    conn = _db()
    fields, vals = [], []
    if data.name:
        fields.append("name = ?"); vals.append(data.name)
    if data.date:
        fields.append("date = ?"); vals.append(data.date)
    if data.description:
        fields.append("description = ?"); vals.append(data.description)
    if data.price_usd:
        fields.append("price_usd = ?"); vals.append(data.price_usd)
    if data.capacity:
        fields.append("capacity = ?"); vals.append(data.capacity)
    if fields:
        vals.append("default")
        conn.execute(f"UPDATE events SET {', '.join(fields)} WHERE id = ?", vals)
        conn.commit()
    conn.close()
    return {"success": True}


@router.post("/api/pass/create")
async def create_pass(data: PassCreate):
    now = datetime.now(timezone.utc).isoformat()

    conn = _db()

    # Capacity check (don't block existing email re-submits — they're already counted).
    event = conn.execute("SELECT * FROM events WHERE id = ?", (data.event_id,)).fetchone()
    capacity = (event["capacity"] if event else 0) or 0
    if capacity > 0:
        confirmed_or_held = conn.execute(
            """SELECT COUNT(*) AS c FROM passes
               WHERE event_id = ? AND waitlisted = 0
                 AND email != ?""",
            (data.event_id, data.email)
        ).fetchone()["c"]
        will_waitlist = confirmed_or_held >= capacity
    else:
        will_waitlist = False

    # If email already exists for this event → update instead of duplicate.
    existing = conn.execute(
        "SELECT * FROM passes WHERE email = ? AND event_id = ?",
        (data.email, data.event_id)
    ).fetchone()

    if existing:
        pass_id = existing["id"]
        # Update fields the client provided (name/phone/method/amount/notes/guests).
        notes_text = data.notes
        if data.guests and data.guests > 1:
            notes_text = (f"guests={data.guests}; " + notes_text).strip("; ")
        new_stage = "complete" if (data.amount or 0) > 0 or data.payment_method in ("cash", "stripe") and data.amount == 0 else existing["stage"] or "incomplete"
        # Heuristic: if amount > 0, they've made a contribution choice → stage='complete'
        if (data.amount or 0) > 0 or data.payment_method == "cash":
            new_stage = "complete"
        conn.execute(
            """UPDATE passes SET name=?, phone=?, payment_method=?, amount_intended=?,
                   notes=COALESCE(NULLIF(?,''), notes), stage=?, updated_at=?
               WHERE id=?""",
            (data.name, data.phone, data.payment_method, data.amount or 0,
             notes_text, new_stage, now, pass_id)
        )
        conn.commit()
        is_existing = True
    else:
        pass_id = _short_id()
        notes_text = data.notes
        if data.guests and data.guests > 1:
            notes_text = (f"guests={data.guests}; " + notes_text).strip("; ")
        # Stage: if zero-amount + cash/method-not-yet-chosen, treat as incomplete-soft-save.
        # If amount>0 OR cash, treat as complete commitment.
        is_complete = (data.amount or 0) > 0 or data.payment_method == "cash"
        stage = "complete" if is_complete else "incomplete"
        conn.execute(
            """INSERT INTO passes
               (id, name, email, phone, payment_method, amount_paid, amount_intended,
                event_id, notes, stage, waitlisted, partner_code, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pass_id, data.name, data.email, data.phone, data.payment_method, 0,
             data.amount or 0, data.event_id, notes_text, stage,
             1 if will_waitlist else 0, (data.partner_code or "").upper().strip(), now, now)
        )
        conn.commit()
        is_existing = False
    conn.close()

    if not is_existing:
        await _gateway_create_account(pass_id, data.name, data.email or "")

    # Per-event landing/thanks URLs — World Peace tickets land on the event-themed page.
    thanks_for_pass = _thanks_url(data.event_id, pass_id)

    result = {
        "success": True,
        "pass_id": pass_id,
        "pass_url": thanks_for_pass,
        "existing": is_existing,
        "waitlisted": will_waitlist,
    }

    if data.payment_method == "stripe" and data.amount > 0 and STRIPE_SECRET:
        # Append paid=1 / cancelled=1 to the event thanks URL, preserving any existing query string.
        sep = "&" if "?" in thanks_for_pass else "?"
        success_url = data.success_url or f"{thanks_for_pass}{sep}paid=1"
        cancel_url = data.cancel_url or f"{thanks_for_pass}{sep}cancelled=1"
        # Allow caller to use {PASS_ID} placeholder in their custom URLs
        success_url = success_url.replace("{PASS_ID}", pass_id)
        cancel_url = cancel_url.replace("{PASS_ID}", pass_id)
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"Zen Pass — {data.name}"},
                    "unit_amount": int(data.amount * 100),
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"pass_id": pass_id, "amount": str(data.amount)},
            customer_email=data.email,
        )
        result["checkout_url"] = session.url
    elif data.payment_method != "stripe" and data.amount > 0:
        pm = PAYMENT_METHODS.get(data.payment_method, {})
        result["payment_info"] = {
            "method": pm.get("name", data.payment_method),
            "address": pm.get("address", ""),
            "amount": data.amount,
            "reference": f"ZenPass-{pass_id}",
            "note": f"Please include 'ZenPass-{pass_id}' in your payment note.",
        }

    # Telegram + confirmation email — only on completed RSVPs
    # (skip on step-1 incomplete soft saves to avoid noise; they get followup later).
    conn = _db()
    pass_row = conn.execute("SELECT * FROM passes WHERE id = ?", (pass_id,)).fetchone()
    event_row = conn.execute("SELECT * FROM events WHERE id = ?", (data.event_id,)).fetchone()
    conn.close()
    p_dict = dict(pass_row) if pass_row else {}
    e_dict = dict(event_row) if event_row else {"id": data.event_id, "name": data.event_id}

    is_complete = (p_dict.get("stage") == "complete") and not is_existing
    is_progressing = is_existing and ((data.amount or 0) > 0 or data.payment_method == "cash")

    if is_complete or is_progressing:
        # Send confirmation email (only once per pass).
        if not p_dict.get("confirmation_sent_at"):
            try:
                ok = await _send_email(
                    to_email=data.email,
                    subject=f"You're in — {e_dict.get('name', 'Zen Village')}",
                    html=_confirmation_email_html(p_dict, e_dict),
                )
                if ok:
                    conn = _db()
                    conn.execute(
                        "UPDATE passes SET confirmation_sent_at = ? WHERE id = ?",
                        (datetime.now(timezone.utc).isoformat(), pass_id)
                    )
                    conn.commit()
                    conn.close()
                    result["email_sent"] = True
            except Exception as e:
                print(f"[zen-pass] confirmation email failed: {e}")

        await _notify_james(
            f"{'NEW' if not is_existing else 'COMPLETED'} ZEN PASS\n"
            f"{data.name} ({data.email})\n"
            f"Event: {e_dict.get('name','')}\n"
            f"Method: {data.payment_method} | Amount: ${data.amount}\n"
            f"Pass: {thanks_for_pass}"
        )
    elif not is_existing:
        # Step-1 soft save — quiet ping so James knows interest exists.
        await _notify_james(
            f"NEW INTEREST (step 1)\n{data.name} ({data.email})\n"
            f"Event: {e_dict.get('name','')}\n"
            f"They started the RSVP. Auto-followup in 30 min if not completed."
        )

    try:
        _sync_pass_to_nocodb(pass_id)
    except Exception as _e:
        print(f"[zen-pass] nocodb sync raised (caught): {_e}")
    return result


# ── One-tap quick-checkout (no form on our side) ─────────────────────────────
@router.get("/api/pass/quick-checkout")
async def quick_checkout(
    request: Request,
    event_id: str = "default",
    amount: float = 0,
    ref: str = "",
):
    """One-tap → Stripe Checkout. Used by the /peace page so guests can scan,
    tap a tier, and land directly on Stripe (Apple Pay / Google Pay / card).
    Stripe collects the email + name; our webhook backfills the pass row when
    payment completes.
    """
    if not STRIPE_SECRET:
        raise HTTPException(503, "Stripe not configured")
    if amount <= 0:
        raise HTTPException(400, "Amount must be > 0 for quick-checkout")

    # Pull ?ref= from query first, then cookie, then header
    partner_code = (ref or request.cookies.get("zv_ref") or "").upper().strip()
    partner_code = "".join(ch for ch in partner_code if ch.isalnum() or ch in "_-")[:40]

    # Create a placeholder pass — name/email get backfilled from Stripe webhook.
    pass_id = _short_id()
    now = datetime.now(timezone.utc).isoformat()
    placeholder_email = f"pending+{pass_id.lower()}@zenvillagecr.com"

    conn = _db()
    conn.execute(
        """INSERT INTO passes
           (id, name, email, phone, payment_method, amount_paid, amount_intended,
            event_id, notes, stage, waitlisted, partner_code, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (pass_id, "", placeholder_email, "", "stripe", 0,
         float(amount), event_id, "quick-checkout", "incomplete",
         0, partner_code, now, now)
    )
    conn.commit()

    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    conn.close()
    event_name = event["name"] if event else event_id

    thanks_for_pass = _thanks_url(event_id, pass_id)
    sep = "&" if "?" in thanks_for_pass else "?"
    success_url = f"{thanks_for_pass}{sep}paid=1"
    cancel_url = f"{thanks_for_pass}{sep}cancelled=1"

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"{event_name} — contribution"},
                "unit_amount": int(round(amount * 100)),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"pass_id": pass_id, "amount": str(amount), "event_id": event_id},
        # No customer_email — let Stripe collect it; webhook backfills our row.
    )
    # 302 redirect: scanner → Stripe in one step.
    return RedirectResponse(session.url, status_code=302)


# ── Public rails list (for the /peace contribution flow) ────────────────────
@router.get("/api/pass/rails")
async def list_payment_rails():
    """Returns all available payment rails (instant + manual) for the
    /peace contribution flow. Each rail has id, name, type, and brief copy."""
    from app.topup_rails import list_rails

    # Friendly metadata layered on top of the canonical rail list.
    META = {
        "stripe_card":    {"emoji": "💳", "blurb": "Card · Apple Pay · Google Pay",   "tag": "Instant"},
        "venmo":          {"emoji": "💚", "blurb": "Friends & Family — no fees",      "tag": "No fees"},
        "paypal_friends": {"emoji": "💙", "blurb": "Friends & Family — no fees",      "tag": "No fees"},
        "wise":           {"emoji": "🌐", "blurb": "International transfer",          "tag": "Low fees"},
        "btc":            {"emoji": "₿",  "blurb": "Bitcoin on-chain",                "tag": "Crypto"},
        "cash":           {"emoji": "💵", "blurb": "Cash at the gate",                "tag": "In person"},
    }
    DISPLAY_ORDER = [
        "stripe_card", "venmo", "paypal_friends", "wise", "btc", "cash",
    ]

    out = []
    rails_by_id = {r["id"]: r for r in list_rails()}
    for rid in DISPLAY_ORDER:
        r = rails_by_id.get(rid)
        if not r:
            continue
        m = META.get(rid, {})
        out.append({
            "id": r["id"],
            "name": r["name"],
            "type": r["type"],  # "instant" | "manual"
            "emoji": m.get("emoji", "•"),
            "blurb": m.get("blurb", ""),
            "tag": m.get("tag", ""),
            "min_usd": r.get("min_usd", 5),
            "max_usd": r.get("max_usd", 5000),
        })
    return {"ok": True, "rails": out}


# ── Manual-rail pledge (Venmo / PayPal / Zelle / Wise / Crypto / Cash) ──────
class ManualPledgeRequest(BaseModel):
    event_id: str = "default"
    amount: float
    rail_id: str  # venmo | paypal_friends | paypal_goods | zelle | wise | btc | solana_usdc | cash
    email: EmailStr
    name: str = ""
    ref: str = ""


@router.post("/api/pass/manual-pledge")
async def manual_pledge(payload: ManualPledgeRequest, request: Request):
    """Records a contribution pledge for a manual payment rail. Returns the
    rail's payment instructions + a unique reference code so admin can match
    the inbound payment. Confirmation flips the pass to 'paid' via /topup
    confirm in the Telegram bot or admin dashboard.
    """
    from app.topup_rails import get_rail, hydrate_instructions

    rail = get_rail(payload.rail_id)
    if not rail:
        raise HTTPException(400, f"Unknown rail: {payload.rail_id}")
    if payload.amount < (rail.get("min_usd") or 0):
        raise HTTPException(400, f"Min for {rail['name']} is ${rail.get('min_usd')}")
    if payload.amount > (rail.get("max_usd") or 1e9):
        raise HTTPException(400, f"Max for {rail['name']} is ${rail.get('max_usd')}")

    partner_code = (payload.ref or request.cookies.get("zv_ref") or "").upper().strip()
    partner_code = "".join(ch for ch in partner_code if ch.isalnum() or ch in "_-")[:40]

    now = datetime.now(timezone.utc).isoformat()
    pass_id = _short_id()
    ref_code = f"WPW-{pass_id}"

    conn = _db()
    existing = conn.execute(
        "SELECT id FROM passes WHERE email = ? AND event_id = ?",
        (payload.email, payload.event_id),
    ).fetchone()
    if existing:
        pass_id = existing["id"]
        ref_code = f"WPW-{pass_id}"
        conn.execute(
            """UPDATE passes SET name=COALESCE(NULLIF(?,''), name),
                   payment_method=?, amount_intended=?, stage='complete',
                   notes=COALESCE(NULLIF(?,''), notes), updated_at=?
               WHERE id=?""",
            (payload.name, payload.rail_id, payload.amount,
             f"manual:{payload.rail_id}", now, pass_id),
        )
    else:
        conn.execute(
            """INSERT INTO passes
               (id, name, email, phone, payment_method, amount_paid, amount_intended,
                event_id, notes, stage, waitlisted, partner_code, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pass_id, payload.name, payload.email, "", payload.rail_id, 0,
             payload.amount, payload.event_id, f"manual:{payload.rail_id}",
             "complete", 0, partner_code, now, now),
        )
    conn.commit()
    event = conn.execute("SELECT * FROM events WHERE id = ?", (payload.event_id,)).fetchone()
    conn.close()
    e_dict = dict(event) if event else {"id": payload.event_id, "name": payload.event_id}

    if not existing:
        await _gateway_create_account(pass_id, payload.name, payload.email)

    instructions = hydrate_instructions(rail, ref_code)

    # Email guest the instructions so they have it to refer to.
    try:
        body_html = f"""
        <div style="font-family:Georgia,serif;max-width:560px;margin:0 auto;padding:24px;color:#2a2018">
          <h2 style="color:#1a2e1a;font-weight:400;font-size:28px">Almost there.</h2>
          <p>Thanks for choosing {rail['name']} for your <strong>{e_dict.get('name','contribution')}</strong> contribution.</p>
          <div style="background:#f5f2e8;border-left:3px solid #c4a35a;padding:16px 20px;margin:20px 0;border-radius:0 8px 8px 0">
            <div style="font-size:13px;letter-spacing:.18em;text-transform:uppercase;color:#7a6f63;margin-bottom:8px">Send <strong style="color:#1a2e1a;font-size:18px">${payload.amount:.0f}</strong></div>
            <div style="font-size:15px;line-height:1.5;color:#2a2018">{instructions}</div>
          </div>
          <p style="font-size:13px;color:#7a6f63">Your reference is <strong style="color:#1a2e1a;font-family:monospace">{ref_code}</strong>. We confirm once we see it land.</p>
          <p style="margin-top:24px">See you Saturday. 🤍<br><em>— Zen Village</em></p>
        </div>"""
        await _send_email(
            to_email=payload.email,
            subject=f"How to send your contribution — {e_dict.get('name','Zen Village')}",
            html=body_html,
        )
    except Exception as e:
        print(f"[zen-pass] manual-pledge email failed: {e}")

    await _notify_james(
        f"PLEDGE — {rail['name']}\n"
        f"{payload.email}\n"
        f"Amount: ${payload.amount}\n"
        f"Ref: {ref_code}\n"
        f"Pass: {pass_id}\n"
        f"Confirm in bot: /topup confirm {ref_code}"
    )

    try:
        _sync_pass_to_nocodb(pass_id)
    except Exception:
        pass

    return {
        "success": True,
        "pass_id": pass_id,
        "reference": ref_code,
        "rail": {"id": rail["id"], "name": rail["name"]},
        "amount": payload.amount,
        "instructions": instructions,
    }


# ── Heart-tier (zero-amount) one-tap signup ──────────────────────────────────
class QuickRSVPRequest(BaseModel):
    event_id: str = "default"
    email: EmailStr
    name: str = ""
    ref: str = ""


@router.post("/api/pass/quick-rsvp")
async def quick_rsvp(payload: QuickRSVPRequest, request: Request):
    """Zero-cost RSVP — for the Heart $0 tier. Email-only, no checkout."""
    partner_code = (payload.ref or request.cookies.get("zv_ref") or "").upper().strip()
    partner_code = "".join(ch for ch in partner_code if ch.isalnum() or ch in "_-")[:40]

    now = datetime.now(timezone.utc).isoformat()
    conn = _db()
    existing = conn.execute(
        "SELECT id FROM passes WHERE email = ? AND event_id = ?",
        (payload.email, payload.event_id),
    ).fetchone()
    if existing:
        pass_id = existing["id"]
        conn.execute(
            "UPDATE passes SET stage='complete', updated_at=?, name=COALESCE(NULLIF(?,''), name) WHERE id=?",
            (now, payload.name, pass_id),
        )
    else:
        pass_id = _short_id()
        conn.execute(
            """INSERT INTO passes
               (id, name, email, phone, payment_method, amount_paid, amount_intended,
                event_id, notes, stage, waitlisted, partner_code, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pass_id, payload.name, payload.email, "", "cash", 0, 0,
             payload.event_id, "Heart tier — RSVP only", "complete", 0,
             partner_code, now, now),
        )
    conn.commit()
    event = conn.execute("SELECT * FROM events WHERE id = ?", (payload.event_id,)).fetchone()
    conn.close()
    e_dict = dict(event) if event else {"id": payload.event_id, "name": payload.event_id}

    if not existing:
        await _gateway_create_account(pass_id, payload.name, payload.email)

    try:
        await _send_email(
            to_email=payload.email,
            subject=f"You're in — {e_dict.get('name', 'Zen Village')}",
            html=_confirmation_email_html(
                {"id": pass_id, "name": payload.name, "email": payload.email,
                 "amount_paid": 0, "amount_intended": 0},
                e_dict,
            ),
        )
    except Exception as e:
        print(f"[zen-pass] heart confirmation email failed: {e}")

    await _notify_james(
        f"HEART RSVP\n{payload.email}\nEvent: {e_dict.get('name','')}\nPass: {pass_id}"
    )

    try:
        _sync_pass_to_nocodb(pass_id)
    except Exception:
        pass

    return {"success": True, "pass_id": pass_id}


# ── PATCH endpoint for progressive RSVP updates ──────────────────────────────

class PassUpdate(BaseModel):
    name: str = ""
    phone: str = ""
    payment_method: str = ""
    amount: float = -1
    notes: str = ""
    stage: str = ""

@router.patch("/api/pass/{pass_id}")
async def update_pass(pass_id: str, data: PassUpdate):
    conn = _db()
    row = conn.execute("SELECT * FROM passes WHERE id = ?", (pass_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Pass not found")
    fields, vals = [], []
    if data.name: fields.append("name=?"); vals.append(data.name)
    if data.phone: fields.append("phone=?"); vals.append(data.phone)
    if data.payment_method: fields.append("payment_method=?"); vals.append(data.payment_method)
    if data.amount >= 0: fields.append("amount_intended=?"); vals.append(data.amount)
    if data.notes: fields.append("notes=?"); vals.append(data.notes)
    if data.stage in ("incomplete", "complete", "cancelled"): fields.append("stage=?"); vals.append(data.stage)
    if fields:
        vals.append(datetime.now(timezone.utc).isoformat())
        vals.append(pass_id)
        conn.execute(f"UPDATE passes SET {', '.join(fields)}, updated_at=? WHERE id=?", vals)
        conn.commit()
    conn.close()
    try:
        _sync_pass_to_nocodb(pass_id)
    except Exception as _e:
        print(f"[zen-pass] nocodb sync raised on update (caught): {_e}")
    return {"success": True, "pass_id": pass_id}


# ── Cancel endpoint (so abandoned reservations can free capacity) ────────────

@router.post("/api/pass/{pass_id}/cancel")
async def cancel_pass(pass_id: str):
    conn = _db()
    row = conn.execute("SELECT * FROM passes WHERE id = ?", (pass_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Pass not found")
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("UPDATE passes SET stage='cancelled', updated_at=? WHERE id=?", (now, pass_id))
    conn.commit()
    conn.close()
    await _notify_james(f"CANCELLED · {row['name']} ({row['email']}) · pass {pass_id}")
    return {"success": True}


# ── Payment confirmation (admin) ─────────────────────────────────────────────

@router.post("/api/pass/confirm-payment")
async def confirm_payment(data: PaymentConfirm):
    if data.admin_key != ADMIN_SECRET:
        raise HTTPException(403, "Invalid admin key")

    conn = _db()
    row = conn.execute("SELECT * FROM passes WHERE id = ?", (data.pass_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Pass not found")

    now = datetime.now(timezone.utc).isoformat()
    method = data.method or row["payment_method"]
    new_total = (row["amount_paid"] or 0) + data.amount

    conn.execute(
        "UPDATE passes SET payment_status = 'paid', amount_paid = ?, payment_method = ?, updated_at = ? WHERE id = ?",
        (new_total, method, now, data.pass_id)
    )
    conn.execute(
        "INSERT INTO transactions (id, pass_id, type, amount, description, created_at) VALUES (?,?,?,?,?,?)",
        (_short_id(), data.pass_id, "payment", data.amount, f"Payment confirmed ({method})", now)
    )
    conn.commit()
    conn.close()

    await _gateway_credit(data.pass_id, data.amount, f"Payment via {method}")
    # affiliates conversion hook (event/credits)
    try:
        from app.affiliates import try_convert as _aff_convert
        pcode = (row["partner_code"] if "partner_code" in row.keys() else "") or ""
        if pcode:
            _aff_convert(
                partner_code=pcode,
                booking_type="event",
                booking_amount=float(data.amount or 0),
                guest_email=row["email"] or "",
                source_id=f"pass:{data.pass_id}",
                booking_details=f"Pass payment via {method}",
            )
    except Exception as _e:
        logger.warning(f"affiliates pass hook failed: {_e}") if 'logger' in globals() else print(f"affiliates pass hook failed: {_e}")

    return {"success": True, "new_balance": new_total}


# ── Stripe webhook ───────────────────────────────────────────────────────────

@router.post("/api/pass/stripe-webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(400, "Invalid webhook")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        pass_id = session.get("metadata", {}).get("pass_id")
        amount = float(session.get("metadata", {}).get("amount", 0))

        # Stripe collects email + name during quick-checkout — backfill them
        # so the pass row reflects the real guest, not the placeholder.
        cust = session.get("customer_details") or {}
        cust_email = (cust.get("email") or session.get("customer_email") or "").strip()
        cust_name = (cust.get("name") or "").strip()
        cust_phone = (cust.get("phone") or "").strip()

        if pass_id and amount > 0:
            conn = _db()
            now = datetime.now(timezone.utc).isoformat()

            # Pull existing row to know if we're upgrading a placeholder.
            existing = conn.execute("SELECT email, name, phone FROM passes WHERE id = ?", (pass_id,)).fetchone()
            is_placeholder = bool(existing and (existing["email"] or "").startswith("pending+"))

            updates = ["payment_status = 'paid'",
                       "amount_paid = amount_paid + ?",
                       "payment_method = 'stripe'",
                       "stage = 'complete'",
                       "updated_at = ?"]
            params = [amount, now]
            if cust_email and (is_placeholder or not (existing and existing["email"])):
                updates.append("email = ?"); params.append(cust_email)
            if cust_name and (is_placeholder or not (existing and existing["name"])):
                updates.append("name = ?"); params.append(cust_name)
            if cust_phone and (is_placeholder or not (existing and existing["phone"])):
                updates.append("phone = ?"); params.append(cust_phone)
            params.append(pass_id)

            conn.execute(f"UPDATE passes SET {', '.join(updates)} WHERE id = ?", params)
            conn.execute(
                "INSERT INTO transactions (id, pass_id, type, amount, description, created_at) VALUES (?,?,?,?,?,?)",
                (_short_id(), pass_id, "payment", amount, "Stripe checkout completed", now)
            )
            conn.commit()

            # Send confirmation email now that we have a real address.
            row = conn.execute("SELECT * FROM passes WHERE id = ?", (pass_id,)).fetchone()
            event_row = conn.execute("SELECT * FROM events WHERE id = ?", (row["event_id"],)).fetchone() if row else None
            conn.close()
            if row and (row["email"] or "").strip() and not (row["email"] or "").startswith("pending+"):
                if not row["confirmation_sent_at"]:
                    try:
                        await _send_email(
                            to_email=row["email"],
                            subject=f"You're in — {(event_row['name'] if event_row else 'Zen Village')}",
                            html=_confirmation_email_html(dict(row), dict(event_row) if event_row else {"id": row["event_id"], "name": row["event_id"]}),
                        )
                        conn = _db()
                        conn.execute("UPDATE passes SET confirmation_sent_at = ? WHERE id = ?", (datetime.now(timezone.utc).isoformat(), pass_id))
                        conn.commit()
                        conn.close()
                    except Exception as e:
                        print(f"[zen-pass] post-payment confirmation email failed: {e}")

            await _gateway_credit(pass_id, amount, "Stripe payment")
            await _notify_james(
                f"PAYMENT RECEIVED\nPass: {pass_id}\n"
                f"{cust_name or '(no name)'} · {cust_email or '(no email)'}\n"
                f"Amount: ${amount}\nMethod: Stripe (card / Apple Pay / Google Pay)"
            )

            try:
                conn2 = _db()
                row2 = conn2.execute("SELECT email, partner_code FROM passes WHERE id = ?", (pass_id,)).fetchone()
                conn2.close()
                if row2 and (row2["partner_code"] or ""):
                    from app.affiliates import try_convert as _aff_convert
                    _aff_convert(
                        partner_code=row2["partner_code"],
                        booking_type="event",
                        booking_amount=float(amount),
                        guest_email=row2["email"] or "",
                        source_id=f"pass:{pass_id}",
                        booking_details="Pass payment via Stripe",
                    )
            except Exception as _e:
                print(f"affiliates stripe hook failed: {_e}")


    return {"received": True}


# ── Check-in ─────────────────────────────────────────────────────────────────

# ── Items + Frictionless Purchase ────────────────────────────────────────────

@router.post("/api/pass/items")
async def create_item(data: ItemCreate, admin_key: str = ""):
    if admin_key != ADMIN_SECRET:
        raise HTTPException(403, "Invalid admin key")
    item_id = _short_id()
    now = datetime.now(timezone.utc).isoformat()
    conn = _db()
    conn.execute(
        """INSERT INTO items (id, name, description, price_credits, category,
                              emoji, image_url, stock, event_id, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (item_id, data.name, data.description, data.price_credits, data.category,
         data.emoji, data.image_url, data.stock, data.event_id, now)
    )
    conn.commit()
    conn.close()
    return {"success": True, "item_id": item_id,
            "qr_url": f"{BASE_URL}/api/pass/items/{item_id}/qr",
            "buy_url": f"{ITEM_BUY_URL}{item_id}"}


@router.patch("/api/pass/items/{item_id}")
async def update_item(item_id: str, data: ItemUpdate, admin_key: str = ""):
    if admin_key != ADMIN_SECRET:
        raise HTTPException(403, "Invalid admin key")
    conn = _db()
    row = conn.execute("SELECT id FROM items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Item not found")
    fields, vals = [], []
    if data.name: fields.append("name=?"); vals.append(data.name)
    if data.description: fields.append("description=?"); vals.append(data.description)
    if data.price_credits >= 0: fields.append("price_credits=?"); vals.append(data.price_credits)
    if data.category: fields.append("category=?"); vals.append(data.category)
    if data.emoji: fields.append("emoji=?"); vals.append(data.emoji)
    if data.image_url: fields.append("image_url=?"); vals.append(data.image_url)
    if data.stock != -2: fields.append("stock=?"); vals.append(data.stock)
    if data.active != -1: fields.append("active=?"); vals.append(data.active)
    if data.event_id: fields.append("event_id=?"); vals.append(data.event_id)
    if fields:
        vals.append(item_id)
        conn.execute(f"UPDATE items SET {', '.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()
    return {"success": True, "item_id": item_id}


@router.delete("/api/pass/items/{item_id}")
async def delete_item(item_id: str, admin_key: str = ""):
    if admin_key != ADMIN_SECRET:
        raise HTTPException(403, "Invalid admin key")
    conn = _db()
    conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return {"success": True}


@router.get("/api/pass/items")
async def list_items(event_id: str = "", include_inactive: int = 0):
    conn = _db()
    where = []
    params = []
    if not include_inactive:
        where.append("active = 1")
    if event_id:
        where.append("event_id = ?")
        params.append(event_id)
    sql = "SELECT * FROM items"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY category, name"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    items = []
    for r in rows:
        d = dict(r)
        d["buy_url"] = f"{ITEM_BUY_URL}{d['id']}"
        items.append(d)
    return {"items": items}


@router.get("/api/pass/items/{item_id}")
async def get_item(item_id: str):
    conn = _db()
    row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Item not found")
    d = dict(row)
    d["buy_url"] = f"{ITEM_BUY_URL}{item_id}"
    return d


@router.get("/api/pass/items/{item_id}/qr")
async def item_qr(item_id: str):
    """QR code for the item — encodes the frictionless /buy/?item={id} URL.
    Scanning this with a phone camera opens the buy page directly."""
    png = generate_qr_png(f"{ITEM_BUY_URL}{item_id}")
    return StreamingResponse(io.BytesIO(png), media_type="image/png",
                             headers={"Cache-Control": "public, max-age=86400"})


@router.post("/api/pass/purchase")
async def purchase_item(data: ItemPurchase):
    """Frictionless item purchase. Debits Zen Credits from the pass account
    via the credits gateway. Decrements stock if stock is being tracked.
    Notifies staff via Telegram so they can prepare the order."""
    qty = max(1, data.quantity or 1)
    conn = _db()
    pass_row = conn.execute("SELECT * FROM passes WHERE id = ?", (data.pass_id,)).fetchone()
    item_row = conn.execute("SELECT * FROM items WHERE id = ? AND active = 1", (data.item_id,)).fetchone()
    if not pass_row:
        conn.close()
        raise HTTPException(404, "Pass not found — please scan the wristband or enter your pass ID")
    if not item_row:
        conn.close()
        raise HTTPException(404, "Item not available right now")

    if item_row["stock"] is not None and item_row["stock"] >= 0 and item_row["stock"] < qty:
        conn.close()
        raise HTTPException(409, f"Sold out — only {item_row['stock']} left")

    total_price = item_row["price_credits"] * qty
    description = f"Purchased: {item_row['name']}" + (f" x{qty}" if qty > 1 else "")
    if data.note:
        description += f" — {data.note}"

    debit_result = await _gateway_debit(data.pass_id, total_price, description)
    if not debit_result:
        conn.close()
        raise HTTPException(402, f"Insufficient Zen Credits. Need {total_price}, please top up or ask staff to reward you credits.")

    now = datetime.now(timezone.utc).isoformat()
    txn_id = _short_id()
    conn.execute(
        "INSERT INTO transactions (id, pass_id, item_id, type, amount, description, created_at) VALUES (?,?,?,?,?,?,?)",
        (txn_id, data.pass_id, data.item_id, "purchase", total_price, description, now)
    )
    if item_row["stock"] is not None and item_row["stock"] >= 0:
        conn.execute("UPDATE items SET stock = stock - ? WHERE id = ?", (qty, data.item_id))
    conn.commit()
    conn.close()

    new_balance = await _gateway_balance(data.pass_id)

    # Notify staff so they can prepare the order
    emoji = item_row["emoji"] or "🌿"
    await _notify_james(
        f"{emoji} ORDER · {pass_row['name']}\n"
        f"{item_row['name']}{(' x' + str(qty)) if qty > 1 else ''} ({total_price} credits)\n"
        f"{('note: ' + data.note) if data.note else ''}\n"
        f"Pass: {data.pass_id} · balance after: {new_balance:.0f}"
    )

    return {
        "success": True,
        "item": item_row["name"],
        "quantity": qty,
        "charged": total_price,
        "balance": new_balance,
        "transaction_id": txn_id,
    }


# ── Balance / top-up ─────────────────────────────────────────────────────────

@router.get("/api/pass/{pass_id}/balance")
async def pass_balance(pass_id: str):
    conn = _db()
    row = conn.execute("SELECT id, name FROM passes WHERE id = ?", (pass_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Pass not found")
    bal = await _gateway_balance(pass_id)
    return {"pass_id": pass_id, "name": row["name"], "balance": bal}


@router.post("/api/pass/{pass_id}/reward-credits")
async def reward_credits(pass_id: str, data: RewardCredits, admin_key: str = ""):
    """Admin-issued credit grant. Use this for volunteers, gifting, special-case
    abundance. Records as a transaction so it appears in /manage/#orders."""
    if admin_key != ADMIN_SECRET:
        raise HTTPException(403, "Invalid admin key")
    conn = _db()
    row = conn.execute("SELECT * FROM passes WHERE id = ?", (pass_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Pass not found")
    conn.close()

    description = f"Reward: {data.reason}"
    credit_result = await _gateway_credit(pass_id, data.amount, description, apply_ratio=False)

    now = datetime.now(timezone.utc).isoformat()
    conn = _db()
    conn.execute(
        "INSERT INTO transactions (id, pass_id, type, amount, description, created_at) VALUES (?,?,?,?,?,?)",
        (_short_id(), pass_id, "reward", data.amount, description, now)
    )
    conn.commit()
    conn.close()

    bal = await _gateway_balance(pass_id)
    await _notify_james(
        f"🎁 CREDITS REWARDED\n{row['name']} (+{data.amount} credits)\n"
        f"Reason: {data.reason}\nNew balance: {bal:.0f}"
    )
    return {"success": True, "balance": bal, "credit_result": credit_result}


# ── Admin: Guest list ────────────────────────────────────────────────────────

@router.get("/api/pass/admin/guests")
async def admin_guests(admin_key: str = "", event_id: str = "default"):
    if admin_key != ADMIN_SECRET:
        raise HTTPException(403, "Invalid admin key")
    conn = _db()
    rows = conn.execute(
        "SELECT * FROM passes WHERE event_id = ? ORDER BY created_at DESC", (event_id,)
    ).fetchall()
    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

    total_paid = conn.execute(
        "SELECT COALESCE(SUM(amount_paid), 0) as total FROM passes WHERE event_id = ? AND payment_status = 'paid'",
        (event_id,)
    ).fetchone()["total"]
    confirmed = sum(1 for r in rows if (r["stage"] or "complete") == "complete" and not r["waitlisted"])
    incomplete = sum(1 for r in rows if (r["stage"] or "") == "incomplete")
    cancelled = sum(1 for r in rows if (r["stage"] or "") == "cancelled")
    waitlisted = sum(1 for r in rows if r["waitlisted"])
    checked_in = sum(1 for r in rows if r["checked_in"])
    pending_payment = sum(1 for r in rows if r["payment_status"] != "paid" and (r["stage"] or "complete") == "complete")
    conn.close()

    return {
        "event": dict(event) if event else {},
        "guests": [dict(r) for r in rows],
        "stats": {
            "total_guests": len(rows),
            "confirmed": confirmed,
            "incomplete": incomplete,
            "waitlisted": waitlisted,
            "cancelled": cancelled,
            "checked_in": checked_in,
            "pending_payment": pending_payment,
            "total_revenue": total_paid,
            "capacity": event["capacity"] if event else 0,
        }
    }


@router.get("/api/pass/admin/events")
async def admin_events(admin_key: str = ""):
    """Multi-event dashboard summary."""
    if admin_key != ADMIN_SECRET:
        raise HTTPException(403, "Invalid admin key")
    conn = _db()
    events = conn.execute("SELECT * FROM events ORDER BY created_at DESC").fetchall()
    out = []
    for e in events:
        rows = conn.execute(
            "SELECT * FROM passes WHERE event_id = ?", (e["id"],)
        ).fetchall()
        revenue = conn.execute(
            "SELECT COALESCE(SUM(amount_paid), 0) AS t FROM passes WHERE event_id = ?", (e["id"],)
        ).fetchone()["t"]
        ed = dict(e)
        ed["stats"] = {
            "total": len(rows),
            "confirmed": sum(1 for r in rows if (r["stage"] or "complete") == "complete" and not r["waitlisted"]),
            "incomplete": sum(1 for r in rows if (r["stage"] or "") == "incomplete"),
            "waitlisted": sum(1 for r in rows if r["waitlisted"]),
            "checked_in": sum(1 for r in rows if r["checked_in"]),
            "revenue": revenue,
        }
        out.append(ed)
    conn.close()
    return {"events": out}


@router.get("/api/pass/admin/transactions")
async def admin_transactions(admin_key: str = "", txn_type: str = "",
                             only_unfulfilled: int = 0, limit: int = 200,
                             since: str = ""):
    if admin_key != ADMIN_SECRET:
        raise HTTPException(403, "Invalid admin key")
    conn = _db()
    where, params = [], []
    if txn_type:
        where.append("t.type = ?")
        params.append(txn_type)
    if only_unfulfilled:
        where.append("(t.fulfilled IS NULL OR t.fulfilled = 0)")
        where.append("t.type = 'purchase'")
    if since:
        where.append("t.created_at >= ?")
        params.append(since)
    sql = """SELECT t.*, p.name AS guest_name, p.email AS guest_email,
                    i.name AS item_name, i.emoji AS item_emoji
             FROM transactions t
             LEFT JOIN passes p ON t.pass_id = p.id
             LEFT JOIN items i ON t.item_id = i.id"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY t.created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return {"transactions": [dict(r) for r in rows]}


@router.post("/api/pass/admin/transactions/{txn_id}/fulfill")
async def admin_fulfill_transaction(txn_id: str, admin_key: str = "",
                                    fulfilled: int = 1):
    if admin_key != ADMIN_SECRET:
        raise HTTPException(403, "Invalid admin key")
    conn = _db()
    row = conn.execute("SELECT * FROM transactions WHERE id = ?", (txn_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Transaction not found")
    now = datetime.now(timezone.utc).isoformat() if fulfilled else ""
    conn.execute(
        "UPDATE transactions SET fulfilled = ?, fulfilled_at = ? WHERE id = ?",
        (1 if fulfilled else 0, now, txn_id)
    )
    conn.commit()
    conn.close()
    return {"success": True}


@router.get("/api/pass/admin/treasury")
async def admin_treasury(admin_key: str = "", since: str = "", until: str = "",
                         event_id: str = ""):
    """Treasury / financial overview for the admin portal.
    - Total credits issued (rewards + payments)
    - Total credits spent (purchases)
    - Per-item revenue (top sellers)
    - Per-category breakdown
    - Top buyers (passes with highest spend)
    - Optional date range (since/until ISO strings) and event filter.
    """
    if admin_key != ADMIN_SECRET:
        raise HTTPException(403, "Invalid admin key")

    def _join_filter(prefix=""):
        """Returns (clause, params) where clause is appended to a WHERE that
        already has at least one condition. prefix is e.g. 'AND ' or '' depending."""
        parts, params = [], []
        if since:
            parts.append("t.created_at >= ?"); params.append(since)
        if until:
            parts.append("t.created_at <= ?"); params.append(until)
        if event_id:
            parts.append("p.event_id = ?"); params.append(event_id)
        return (prefix + " AND ".join(parts) if parts else ""), params

    conn = _db()

    # Total credits issued (payments + rewards = flowing IN to passes)
    extra, params = _join_filter("AND ")
    issued = conn.execute(
        f"""SELECT COALESCE(SUM(t.amount),0) AS total, COUNT(*) AS count
            FROM transactions t LEFT JOIN passes p ON t.pass_id = p.id
            WHERE t.type IN ('payment','reward') {extra}""",
        params
    ).fetchone()

    # Total credits spent on items (purchases)
    extra, params = _join_filter("AND ")
    spent = conn.execute(
        f"""SELECT COALESCE(SUM(t.amount),0) AS total, COUNT(*) AS count
            FROM transactions t LEFT JOIN passes p ON t.pass_id = p.id
            WHERE t.type = 'purchase' {extra}""",
        params
    ).fetchone()

    # Per-item revenue (left join from items so unsold items still appear with 0)
    extra, params = _join_filter("AND ")
    per_item = conn.execute(
        f"""SELECT i.id, i.name, i.emoji, i.category, i.price_credits, i.stock,
                   COALESCE(SUM(t.amount),0) AS revenue,
                   COUNT(t.id) AS sales
            FROM items i
            LEFT JOIN transactions t ON t.item_id = i.id AND t.type='purchase'
            LEFT JOIN passes p ON t.pass_id = p.id
            WHERE 1=1 {extra}
            GROUP BY i.id ORDER BY revenue DESC""",
        params
    ).fetchall()

    # Per-category
    extra, params = _join_filter("AND ")
    by_category = conn.execute(
        f"""SELECT i.category, COALESCE(SUM(t.amount),0) AS revenue, COUNT(t.id) AS sales
            FROM items i
            LEFT JOIN transactions t ON t.item_id = i.id AND t.type='purchase'
            LEFT JOIN passes p ON t.pass_id = p.id
            WHERE 1=1 {extra}
            GROUP BY i.category ORDER BY revenue DESC""",
        params
    ).fetchall()

    # Top buyers
    extra, params = _join_filter("AND ")
    top_buyers = conn.execute(
        f"""SELECT p.id, p.name, p.email,
                   COALESCE(SUM(t.amount),0) AS spent,
                   COUNT(t.id) AS purchases
            FROM passes p
            LEFT JOIN transactions t ON t.pass_id = p.id AND t.type='purchase'
            WHERE 1=1 {extra}
            GROUP BY p.id HAVING purchases > 0 ORDER BY spent DESC LIMIT 20""",
        params
    ).fetchall()

    # Inventory summary (no time filter — current state of items table)
    inv = conn.execute(
        """SELECT COUNT(*) AS items_total,
                  SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END) AS items_active,
                  SUM(CASE WHEN stock = 0 THEN 1 ELSE 0 END) AS sold_out,
                  SUM(CASE WHEN stock > 0 AND stock <= 3 THEN 1 ELSE 0 END) AS low_stock
           FROM items"""
    ).fetchone()

    # Outstanding orders (no time filter — current to-prep queue)
    outstanding = conn.execute(
        """SELECT COUNT(*) AS c FROM transactions
           WHERE type = 'purchase' AND (fulfilled IS NULL OR fulfilled = 0)"""
    ).fetchone()["c"]

    conn.close()
    return {
        "filters": {"since": since, "until": until, "event_id": event_id},
        "issued": dict(issued),
        "spent": dict(spent),
        "outstanding_orders": outstanding,
        "circulating": (issued["total"] or 0) - (spent["total"] or 0),
        "per_item": [dict(r) for r in per_item],
        "by_category": [dict(r) for r in by_category],
        "top_buyers": [dict(r) for r in top_buyers],
        "inventory": dict(inv) if inv else {},
    }


# ── Admin: broadcast email to event attendees ────────────────────────────────

class BroadcastRequest(BaseModel):
    event_id: str
    subject: str
    body_html: str
    audience: str = "confirmed"   # "confirmed" | "all" | "incomplete" | "waitlisted"

@router.post("/api/pass/admin/broadcast")
async def admin_broadcast(data: BroadcastRequest, admin_key: str = ""):
    if admin_key != ADMIN_SECRET:
        raise HTTPException(403, "Invalid admin key")
    conn = _db()
    if data.audience == "all":
        rows = conn.execute("SELECT * FROM passes WHERE event_id = ? AND email != ''", (data.event_id,)).fetchall()
    elif data.audience == "incomplete":
        rows = conn.execute("SELECT * FROM passes WHERE event_id = ? AND stage = 'incomplete'", (data.event_id,)).fetchall()
    elif data.audience == "waitlisted":
        rows = conn.execute("SELECT * FROM passes WHERE event_id = ? AND waitlisted = 1", (data.event_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM passes WHERE event_id = ? AND stage = 'complete' AND waitlisted = 0", (data.event_id,)).fetchall()
    conn.close()
    sent = 0
    for r in rows:
        ok = await _send_email(r["email"], data.subject, data.body_html)
        if ok: sent += 1
    return {"success": True, "sent": sent, "audience_size": len(rows)}


# ── Followup Engine: nudge incomplete RSVPs ──────────────────────────────────
#
# Runs in a background daemon thread inside the FastAPI process. Looks for
# passes with stage='incomplete' older than 30 minutes that have not yet
# received a followup email, and sends one nudge.

_FOLLOWUP_THREAD_STARTED = False

def _followup_loop():
    while True:
        try:
            time.sleep(60)  # poll every minute
            cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
            conn = _db()
            rows = conn.execute(
                """SELECT * FROM passes
                   WHERE stage = 'incomplete'
                     AND COALESCE(followup_sent_at,'') = ''
                     AND created_at < ?
                   LIMIT 25""",
                (cutoff,)
            ).fetchall()
            conn.close()
            for r in rows:
                p = dict(r)
                conn = _db()
                e = conn.execute("SELECT * FROM events WHERE id = ?", (p["event_id"],)).fetchone()
                conn.close()
                event = dict(e) if e else {"id": p["event_id"], "name": p["event_id"]}
                ok = _send_email_sync(
                    p["email"],
                    f"Your spot is still held — {event.get('name','Zen Village')}",
                    _followup_email_html(p, event),
                )
                conn = _db()
                conn.execute(
                    "UPDATE passes SET followup_sent_at = ? WHERE id = ?",
                    (datetime.now(timezone.utc).isoformat(), p["id"])
                )
                conn.commit()
                conn.close()
                # Also Telegram-ping James about the incomplete record so he can
                # follow up personally if the tone calls for it.
                try:
                    asyncio.run(_notify_james(
                        f"⏰ FOLLOWUP NUDGE SENT\n{p['name']} ({p['email']})\n"
                        f"Event: {event.get('name','')}\n"
                        f"Started signup but didn't finish. Sent gentle email."
                    ))
                except Exception:
                    pass
                print(f"[followup] sent nudge to {p['email']} (pass {p['id']})  ok={ok}")
        except Exception as e:
            print(f"[followup] loop error: {e}")
            time.sleep(60)


def start_followup_engine():
    global _FOLLOWUP_THREAD_STARTED
    if _FOLLOWUP_THREAD_STARTED:
        return
    t = threading.Thread(target=_followup_loop, daemon=True, name="zen-pass-followup")
    t.start()
    _FOLLOWUP_THREAD_STARTED = True
    print("[zen-pass] followup engine started")


# ── Pass lookup (dynamic — must come after all static /api/pass/ routes) ──────

@router.get("/api/pass/event-qr/{event_id}")
async def event_qr(event_id: str = "default"):
    png = generate_qr_png(f"{BASE_URL}/pass?event={event_id}")
    return StreamingResponse(io.BytesIO(png), media_type="image/png",
                             headers={"Cache-Control": "public, max-age=86400"})


@router.get("/api/pass/{pass_id}")
async def get_pass(pass_id: str):
    conn = _db()
    row = conn.execute("SELECT * FROM passes WHERE id = ?", (pass_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Pass not found")
    p = dict(row)
    p["pass_url"] = _thanks_url(p.get("event_id", "default"), pass_id)
    p["qr_url"] = f"{BASE_URL}/api/pass/{pass_id}/qr"
    return p


@router.get("/api/pass/{pass_id}/qr")
async def pass_qr(pass_id: str):
    conn = _db()
    row = conn.execute("SELECT id, event_id FROM passes WHERE id = ?", (pass_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Pass not found")
    # QR encodes the event-themed thanks URL when applicable so a wristband scan
    # lands the holder on the prettiest, on-brand version of their ticket.
    png = generate_qr_png(_thanks_url(row["event_id"] or "default", pass_id))
    return StreamingResponse(io.BytesIO(png), media_type="image/png",
                             headers={"Cache-Control": "public, max-age=86400"})


@router.post("/api/pass/{pass_id}/checkin")
async def checkin(pass_id: str, admin_key: str = ""):
    if admin_key != ADMIN_SECRET:
        raise HTTPException(403, "Invalid admin key")
    conn = _db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("UPDATE passes SET checked_in = 1, checked_in_at = ?, updated_at = ? WHERE id = ?", (now, now, pass_id))
    conn.commit()
    conn.close()
    try:
        _sync_pass_to_nocodb(pass_id)
    except Exception as _e:
        print(f"[zen-pass] nocodb sync raised on checkin (caught): {_e}")
    return {"success": True, "checked_in_at": now}


# ── Frontend page routes ─────────────────────────────────────────────────────

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "public"

@router.get("/pass", response_class=HTMLResponse)
async def pass_landing():
    p = FRONTEND_DIR / "event.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return HTMLResponse("<h1>Zen Pass</h1><p>Page not found</p>")


@router.get("/pass/{pass_id}", response_class=HTMLResponse)
async def pass_view(pass_id: str):
    p = FRONTEND_DIR / "pass.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return HTMLResponse("<h1>Pass not found</h1>")


@router.get("/pay/{item_id}", response_class=HTMLResponse)
async def pay_item_page(item_id: str):
    p = FRONTEND_DIR / "pay.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return HTMLResponse("<h1>Pay</h1><p>Page not found</p>")


@router.get("/admin/event", response_class=HTMLResponse)
async def admin_event_page():
    p = FRONTEND_DIR / "admin-event.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return HTMLResponse("<h1>Event Admin</h1><p>Page not found</p>")

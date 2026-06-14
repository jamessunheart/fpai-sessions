#!/usr/bin/env python3
"""
Zen Village Brain — Telegram bot.

Single bot, three surfaces:
  • Admin DM (you)         → /today /bookings /money /partners /blockers /workers /quiet /digest
  • Worker DM (everyone)   → /checkin (free-text or guided), /done, /blocker, /me
  • Village Pulse group    → bot posts AM (8am) + PM (6pm) digests into Topics

Admins are recognized by ZV_TG_ADMIN_IDS. Workers are recognized by their
telegram_id being in /opt/fpai/apps/zen-village/data/workers.json.

Long-poll, no webhook needed. Run as a systemd service.

Env (already in /etc/zen-village/telegram-notify.env):
  TELEGRAM_BOT_TOKEN          required
  ZV_TG_ADMIN_IDS             comma-separated user ids who get admin commands
  ZV_TG_PULSE_CHAT_ID         (optional) supergroup chat id for digests
  ZV_TG_PULSE_TOPIC_BOOKINGS  (optional) message_thread_id
  ZV_TG_PULSE_TOPIC_FINANCIALS
  ZV_TG_PULSE_TOPIC_WORKERS
  ZV_TG_PULSE_TOPIC_GENERAL
  ZV_NOTIFY_LABEL             (optional) display name
  ZV_API_BASE                 (optional, default http://127.0.0.1:8770)
"""

from __future__ import annotations

import html as _html
import json
import logging
import os
import re
import sys
import time
import urllib.parse
import urllib.request


def escape_html(s: object) -> str:
    """Safe-by-default HTML escape for Telegram parse_mode=HTML."""
    return _html.escape(str(s) if s is not None else "", quote=False)
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("zv-bot")

# ─── config ───────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
ADMIN_IDS = {
    s.strip() for s in (os.environ.get("ZV_TG_ADMIN_IDS") or "").split(",") if s.strip()
}
ACCOUNTING_IDS_ENV = {
    s.strip() for s in (os.environ.get("ZV_TG_ACCOUNTING_IDS") or "").split(",") if s.strip()
}
PULSE_CHAT_ID = (os.environ.get("ZV_TG_PULSE_CHAT_ID") or "").strip()
PULSE_TOPICS = {
    "bookings": (os.environ.get("ZV_TG_PULSE_TOPIC_BOOKINGS") or "").strip(),
    "financials": (os.environ.get("ZV_TG_PULSE_TOPIC_FINANCIALS") or "").strip(),
    "workers": (os.environ.get("ZV_TG_PULSE_TOPIC_WORKERS") or "").strip(),
    "general": (os.environ.get("ZV_TG_PULSE_TOPIC_GENERAL") or "").strip(),
}
LABEL = (os.environ.get("ZV_NOTIFY_LABEL") or "Zen Village").strip()
API_BASE = (os.environ.get("ZV_API_BASE") or "http://127.0.0.1:8770").rstrip("/")
ADMIN_TOKEN = (os.environ.get("ZV_AFFILIATES_ADMIN_TOKEN") or "").strip()

DATA_DIR = Path("/opt/fpai/apps/zen-village/data")
WORKERS_FILE = DATA_DIR / "workers.json"
CHECKINS_FILE = DATA_DIR / "checkins.json"
INQUIRIES_FILE = DATA_DIR / "inquiries.json"
PARTNERS_FILE = DATA_DIR / "partners.json"
COMMISSIONS_FILE = DATA_DIR / "commissions.json"
APPLICATIONS_DIR = DATA_DIR / "applications"
BOT_STATE_FILE = DATA_DIR / "bot_state.json"
CONTACTS_FILE = DATA_DIR / "bot_contacts.json"
ACCOUNTING_ROOT = Path(os.environ.get("ZV_ACCOUNTING_ROOT", "/opt/zen-village/accounting-intake"))

if not BOT_TOKEN:
    log.error("TELEGRAM_BOT_TOKEN is missing")
    sys.exit(1)

API = f"https://api.telegram.org/bot{BOT_TOKEN}"
TZ_CR = timezone(timedelta(hours=-6))  # Costa Rica, no DST


# ─── tiny http helpers ────────────────────────────────────────────────────
def tg(method: str, **payload) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{API}/{method}",
        data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        log.warning("tg %s failed: %s", method, e)
        return {"ok": False, "error": str(e)}


def http_get(path: str, **params) -> dict:
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        log.warning("api GET %s failed: %s", path, e)
        return {"_error": str(e)}


def http_post(path: str, payload: dict, admin: bool = False) -> dict:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if admin and ADMIN_TOKEN:
        headers["x-admin-token"] = ADMIN_TOKEN
    req = urllib.request.Request(f"{API_BASE}{path}", data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        log.warning("api POST %s failed: %s", path, e)
        return {"_error": str(e)}


def http_get_admin(path: str, **params) -> dict:
    """GET with X-Admin-Token. Used for /admin/* endpoints."""
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {}
    if ADMIN_TOKEN:
        headers["x-admin-token"] = ADMIN_TOKEN
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        log.warning("api GET (admin) %s failed: %s", path, e)
        return {"_error": str(e)}


def http_post_admin(path: str, payload: dict) -> dict:
    """POST JSON to admin endpoint with X-Admin-Token."""
    url = f"{API_BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if ADMIN_TOKEN:
        headers["x-admin-token"] = ADMIN_TOKEN
    req = urllib.request.Request(
        url, data=json.dumps(payload or {}).encode("utf-8"),
        method="POST", headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        log.warning("api POST (admin) %s failed: %s", path, e)
        return {"_error": str(e)}


def load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception as e:
        log.warning("load %s failed: %s", path, e)
    return default


def save_json(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(path)


def load_state() -> dict:
    return load_json(BOT_STATE_FILE, {})


def save_state(state: dict) -> None:
    save_json(BOT_STATE_FILE, state)


def pulse_config() -> dict:
    """Pulse config from bot_state first, then env fallback."""
    st = load_state()
    p = st.get("pulse", {}) if isinstance(st, dict) else {}
    topics = p.get("topics", {}) if isinstance(p, dict) else {}
    return {
        "chat_id": str(p.get("chat_id") or PULSE_CHAT_ID or "").strip(),
        "topics": {
            "bookings": str(topics.get("bookings") or PULSE_TOPICS.get("bookings") or "").strip(),
            "financials": str(topics.get("financials") or PULSE_TOPICS.get("financials") or "").strip(),
            "workers": str(topics.get("workers") or PULSE_TOPICS.get("workers") or "").strip(),
            "general": str(topics.get("general") or PULSE_TOPICS.get("general") or "").strip(),
        },
    }


def digest_hours() -> tuple[int, int]:
    """AM/PM digest hours in Costa Rica time, configurable from chat."""
    st = load_state()
    d = st.get("digest_hours", {}) if isinstance(st, dict) else {}
    try:
        am = int(d.get("am", 8))
    except Exception:
        am = 8
    try:
        pm = int(d.get("pm", 18))
    except Exception:
        pm = 18
    am = max(0, min(23, am))
    pm = max(0, min(23, pm))
    return am, pm


def set_digest_hours(am: int, pm: int) -> None:
    st = load_state()
    st["digest_hours"] = {"am": int(am), "pm": int(pm)}
    save_state(st)


def record_contact(user: dict, chat: dict) -> None:
    """Store recent contact metadata so admin can /contacts then /promote."""
    uid = str(user.get("id") or "").strip()
    if not uid:
        return
    contacts = load_json(CONTACTS_FILE, {})
    username = (user.get("username") or "").strip()
    first = (user.get("first_name") or "").strip()
    last = (user.get("last_name") or "").strip()
    name = (f"{first} {last}".strip() or username or f"user_{uid}")
    contacts[uid] = {
        **contacts.get(uid, {}),
        "telegram_id": uid,
        "name": name,
        "username": username,
        "chat_type": (chat.get("type") or "").strip(),
        "chat_title": (chat.get("title") or "").strip(),
        "last_seen_at": datetime.utcnow().isoformat(),
    }
    save_json(CONTACTS_FILE, contacts)


def list_recent_contacts(limit: int = 30) -> list[dict]:
    rows = list(load_json(CONTACTS_FILE, {}).values())
    rows.sort(key=lambda r: r.get("last_seen_at", ""), reverse=True)
    return rows[:limit]


# ─── accounting / receipts helpers ────────────────────────────────────────
def accounting_ids() -> set[str]:
    st = load_state()
    extra = set(str(x).strip() for x in (st.get("accounting_ids") or []) if str(x).strip())
    return set(ACCOUNTING_IDS_ENV) | extra


def is_accounting(uid: str) -> bool:
    return is_admin(uid) or str(uid) in accounting_ids()


def authorize_accounting_id(tg_id: str) -> None:
    st = load_state()
    ids = set(str(x).strip() for x in (st.get("accounting_ids") or []) if str(x).strip())
    ids.add(str(tg_id).strip())
    st["accounting_ids"] = sorted(ids)
    save_state(st)


def _safe_name(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    return name[:120] or "file"


def _acct_month_dir(ts: datetime | None = None) -> Path:
    ts = ts or datetime.utcnow()
    d = ACCOUNTING_ROOT / ts.strftime("%Y-%m")
    d.mkdir(parents=True, exist_ok=True)
    try:
        ACCOUNTING_ROOT.chmod(0o700)
        d.chmod(0o700)
    except Exception:
        pass
    return d


def _acct_append(entry: dict) -> None:
    d = _acct_month_dir(datetime.utcnow())
    f = d / "intake.jsonl"
    with f.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _acct_read_recent(limit: int = 20, who: str = "") -> list[dict]:
    return _acct_search(limit=limit, query=who)


def _acct_iter_entries() -> list[dict]:
    rows: list[dict] = []
    month_dirs = sorted([p for p in ACCOUNTING_ROOT.glob("20??-??") if p.is_dir()], reverse=True)
    for md in month_dirs:
        f = md / "intake.jsonl"
        if not f.exists():
            continue
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for line in reversed(lines):
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def _to_date(v: str) -> Optional[date]:
    s = (v or "").strip()
    if len(s) >= 10:
        s = s[:10]
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


def _acct_search(
    *,
    limit: int = 20,
    query: str = "",
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> list[dict]:
    q = (query or "").strip().lower()
    out: list[dict] = []
    for row in _acct_iter_entries():
        d = _to_date(str(row.get("timestamp") or ""))
        if start and (not d or d < start):
            continue
        if end and (not d or d > end):
            continue
        if q:
            hay = " ".join([
                str(row.get("id") or ""),
                str(row.get("user_name") or ""),
                str(row.get("username") or ""),
                str(row.get("user_id") or ""),
                str(row.get("note") or ""),
                str(row.get("file_name") or ""),
            ]).lower()
            if q not in hay:
                continue
        out.append(row)
        if len(out) >= max(1, min(limit, 2000)):
            break
    return out


def _commission_search(
    *,
    limit: int = 20,
    query: str = "",
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> list[dict]:
    raw = load_json(COMMISSIONS_FILE, {})
    rows = list(raw.values()) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
    q = (query or "").strip().lower()
    rows.sort(key=lambda c: str(c.get("timestamp") or ""), reverse=True)
    out: list[dict] = []
    for c in rows:
        d = _to_date(str(c.get("timestamp") or c.get("paid_at") or ""))
        if start and (not d or d < start):
            continue
        if end and (not d or d > end):
            continue
        if q:
            hay = " ".join([
                str(c.get("id") or ""),
                str(c.get("source_id") or ""),
                str(c.get("partner_code") or ""),
                str(c.get("guest_email") or ""),
                str(c.get("booking_type") or ""),
                str(c.get("status") or ""),
                str(c.get("booking_details") or ""),
            ]).lower()
            if q not in hay:
                continue
        out.append(c)
        if len(out) >= max(1, min(limit, 2000)):
            break
    return out


def _parse_number_token(token: str) -> Optional[float]:
    t = (token or "").strip().replace(" ", "")
    if not t:
        return None
    sign = -1 if t.startswith("-") else 1
    t = t.lstrip("+-")
    if not t:
        return None
    if "," in t and "." in t:
        # whichever separator appears last is likely decimal.
        if t.rfind(".") > t.rfind(","):
            t = t.replace(",", "")
        else:
            t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        parts = t.split(",")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            t = "".join(parts)  # thousands commas
        else:
            t = t.replace(",", ".")
    try:
        return sign * float(t)
    except Exception:
        return None


def _extract_amount(text: str) -> Optional[float]:
    """Best-effort amount extraction from free-text note."""
    s = text or ""
    # Prefer currency-annotated values first.
    m = re.search(r"(?:\$|₡|usd|crc|colones?)\s*(-?\d[\d.,]*)", s, re.I)
    if m:
        v = _parse_number_token(m.group(1))
        if v is not None:
            return abs(v)
    # Fallback: first numeric token.
    m = re.search(r"(-?\d[\d.,]*)", s)
    if m:
        v = _parse_number_token(m.group(1))
        if v is not None:
            return abs(v)
    return None


def _detect_currency(text: str) -> str:
    s = (text or "").lower()
    if "₡" in s or "crc" in s or "colon" in s:
        return "CRC"
    if "$" in s or "usd" in s or "dollar" in s:
        return "USD"
    return "UNK"


def _detect_flow(text: str) -> str:
    s = (text or "").lower()
    out_words = (
        "paid", "spent", "expense", "cost", "purchase", "bought",
        "vendor", "reimburse", "withdraw", "outflow", "bill", "invoice",
    )
    in_words = (
        "received", "income", "sale", "sold", "deposit", "payment from",
        "wire in", "credit", "refund", "inflow",
    )
    out_hit = any(w in s for w in out_words)
    in_hit = any(w in s for w in in_words)
    if out_hit and not in_hit:
        return "out"
    if in_hit and not out_hit:
        return "in"
    return "unknown"


def _add_money(bucket: dict[str, float], currency: str, amount: float) -> None:
    if amount <= 0:
        return
    c = currency if currency in ("USD", "CRC") else "UNK"
    bucket[c] = round(float(bucket.get(c, 0.0)) + float(amount), 2)


def _fmt_money(bucket: dict[str, float]) -> str:
    if not bucket:
        return "—"
    parts: list[str] = []
    for c in ("USD", "CRC", "UNK"):
        v = float(bucket.get(c, 0.0))
        if v > 0:
            parts.append(f"{c} {v:,.2f}")
    return " | ".join(parts) if parts else "—"


def _booking_payment_rollup(start: date, end: date) -> dict:
    out = http_get("/api/bookings/") or {}
    rows = out.get("bookings", out) if isinstance(out, dict) else out
    if not isinstance(rows, list):
        rows = []
    paid_total = 0.0
    partial_total = 0.0
    paid_count = 0
    partial_count = 0
    for b in rows:
        d = _to_date(str(b.get("created_at") or b.get("check_in") or b.get("start_date") or ""))
        if not d or d < start or d > end:
            continue
        ps = str(b.get("payment_status") or "").lower()
        amt = float(b.get("total_amount") or b.get("amount") or 0)
        if ps == "paid":
            paid_total += amt
            paid_count += 1
        elif ps == "partial":
            partial_total += amt
            partial_count += 1
    return {
        "paid_total": round(paid_total, 2),
        "paid_count": paid_count,
        "partial_total": round(partial_total, 2),
        "partial_count": partial_count,
    }


def _money_window_rollup(start: date, end: date) -> dict:
    receipts = _acct_search(limit=1000, start=start, end=end)
    inflow: dict[str, float] = {}
    outflow: dict[str, float] = {}
    unknown: dict[str, float] = {}
    parsed_count = 0
    for r in receipts:
        note = str(r.get("note") or "")
        amt = _extract_amount(note)
        if amt is None:
            continue
        parsed_count += 1
        cur = _detect_currency(note)
        flow = _detect_flow(note)
        if flow == "in":
            _add_money(inflow, cur, amt)
        elif flow == "out":
            _add_money(outflow, cur, amt)
        else:
            _add_money(unknown, cur, amt)

    comm = _commission_search(limit=1000, start=start, end=end)
    paid_comm_out = sum(float(c.get("commission_amount") or 0) for c in comm if str(c.get("status") or "").lower() == "paid")
    pending_now = _commission_search(limit=1000, query="status pending")
    pending_now_total = sum(float(c.get("commission_amount") or 0) for c in pending_now if str(c.get("status") or "").lower() == "pending")

    bookings = _booking_payment_rollup(start, end)
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "receipts_count": len(receipts),
        "parsed_count": parsed_count,
        "inflow": inflow,
        "outflow": outflow,
        "unknown": unknown,
        "comm_paid_out": round(paid_comm_out, 2),
        "comm_pending_now": round(pending_now_total, 2),
        "booking_paid_in": bookings["paid_total"],
        "booking_paid_count": bookings["paid_count"],
        "booking_partial_total": bookings["partial_total"],
        "booking_partial_count": bookings["partial_count"],
    }


def _tg_file_path(file_id: str) -> str:
    r = tg("getFile", file_id=file_id)
    if not r.get("ok"):
        raise RuntimeError(f"getFile failed: {r}")
    return (r.get("result") or {}).get("file_path") or ""


def _download_telegram_file(file_id: str, target_dir: Path, preferred_name: str) -> str:
    fp = _tg_file_path(file_id)
    if not fp:
        raise RuntimeError("missing file_path")
    ext = Path(fp).suffix or Path(preferred_name).suffix
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base = _safe_name(Path(preferred_name).stem)
    out = target_dir / f"{ts}_{base}{ext}"
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}"
    with urllib.request.urlopen(url, timeout=20) as r:
        out.write_bytes(r.read())
    return str(out)


# ─── send helpers ─────────────────────────────────────────────────────────
def send(chat_id, text: str, *, parse_mode: str = "HTML",
         thread_id=None, reply_markup=None) -> dict:
    payload = {
        "chat_id": chat_id,
        "text": text[:4000],
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if thread_id:
        payload["message_thread_id"] = int(thread_id)
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg("sendMessage", **payload)


def send_to_pulse(text: str, topic: str = "general") -> dict:
    cfg = pulse_config()
    pulse_chat_id = cfg.get("chat_id")
    if not pulse_chat_id:
        return {"ok": False, "error": "no pulse chat configured"}
    thread = (cfg.get("topics", {}) or {}).get((topic or "general").lower()) or None
    return send(pulse_chat_id, text, thread_id=thread)


# ─── identity ─────────────────────────────────────────────────────────────
def is_admin(uid) -> bool:
    return str(uid) in ADMIN_IDS


def is_worker(uid) -> bool:
    workers = load_json(WORKERS_FILE, {})
    w = workers.get(str(uid))
    return bool(w) and (w.get("status") or "active") == "active"


# ─── data helpers (shared with app/team.py logic) ─────────────────────────
def today_iso() -> str:
    return date.today().isoformat()


def list_workers(active_only: bool = True) -> list[dict]:
    rows = list(load_json(WORKERS_FILE, {}).values())
    if active_only:
        rows = [w for w in rows if (w.get("status") or "active") == "active"]
    return sorted(rows, key=lambda w: w.get("name") or "")


def latest_checkin(tg_id: str, on_date: Optional[str] = None) -> Optional[dict]:
    rows = [
        c for c in load_json(CHECKINS_FILE, {}).values()
        if str(c.get("telegram_id")) == str(tg_id)
        and (on_date is None or c.get("date") == on_date)
    ]
    if not rows:
        return None
    return max(rows, key=lambda c: c.get("timestamp", ""))


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return (s or "worker")[:24]


def find_worker(query: str) -> Optional[dict]:
    q = (query or "").strip().lower()
    if not q:
        return None
    workers = load_json(WORKERS_FILE, {})
    if q in workers:
        return workers[q]
    values = list(workers.values())
    for w in values:
        if (w.get("telegram_id") or "").lower() == q:
            return w
    for w in values:
        if (w.get("name") or "").strip().lower() == q:
            return w
    for w in values:
        if q in (w.get("name") or "").lower():
            return w
    return None


def ensure_whatsapp_worker(name: str, role: str = "helper", hours: float = 6.0) -> tuple[Optional[dict], bool]:
    """Create a synthetic worker (wa_*) when the person isn't on Telegram yet."""
    existing = find_worker(name)
    if existing:
        return existing, False

    workers = load_json(WORKERS_FILE, {})
    base = f"wa_{_slug(name)}"
    tg_id = base
    n = 2
    while tg_id in workers:
        tg_id = f"{base}_{n}"
        n += 1

    r = http_post(
        "/api/team/workers",
        {
            "telegram_id": tg_id,
            "name": name.strip(),
            "role": role.strip() or "helper",
            "hours_per_day_target": float(hours),
        },
        admin=True,
    )
    if r.get("status") == "ok" and r.get("worker"):
        return r["worker"], True
    return None, False


def parse_checkin_text(text: str) -> dict:
    """Parse a free-text check-in message. Looking for:
       1. A bulleted/numbered list (1. ..., - ..., • ...) → top_3
       2. 'Blockers:' / 'Stuck:' line → blockers
       3. Hours like '6h' or 'Hours: 6' → hours_today
       Anything else stays as free_text.
    """
    text = (text or "").strip()
    top_3: list[str] = []
    blockers = ""
    hours = None
    bullet_re = re.compile(r"^\s*(?:[-•*]|[0-9]+[.)])\s+(.{2,200})", re.M)
    for m in bullet_re.finditer(text):
        if len(top_3) < 3:
            top_3.append(m.group(1).strip().rstrip(".,"))
    for line in text.splitlines():
        low = line.lower().strip()
        for k in ("blockers:", "stuck:", "blocker:", "issue:"):
            if low.startswith(k):
                blockers = line.split(":", 1)[1].strip()
                break
    hr = re.search(r"(?:hours[:=]\s*|\b)(\d+(?:\.\d+)?)\s*h(?:rs?|ours?)?\b", text, re.I)
    if hr:
        try:
            hours = float(hr.group(1))
        except Exception:
            hours = None
    return {"top_3": top_3, "blockers": blockers, "hours_today": hours,
            "free_text": text[:2000]}


def _ops_summary(days: int = 7) -> dict:
    d = http_get("/api/ops/summary", days=days)
    return d if isinstance(d, dict) and not d.get("_error") else {}


# ─── ADMIN COMMANDS (you) ─────────────────────────────────────────────────
def cmd_today(uid, chat_id, args, msg):
    days = 7
    ops = _ops_summary(days)
    digest = (ops.get("team") if ops else None) or http_get("/api/team/digest")

    if ops and ((ops.get("source") or {}).get("nocodb_connected")):
        noco = ops.get("nocodb", {}) or {}
        recent = noco.get("recent", {}) or {}
        totals = noco.get("totals", {}) or {}
        by_type = noco.get("inquiries_by_type", {}) or {}
        comm = noco.get("commissions", {}) or {}
        bookings = f"{recent.get('bookings', 0)} recent · {totals.get('bookings', 0)} total"
        top_types = ", ".join(f"{n} {t}" for t, n in sorted(by_type.items(), key=lambda x: -x[1])[:3])
        inq = f"{recent.get('inquiries', 0)} recent · {top_types or '(none)'}"
        pending_count = int(comm.get("pending_count", 0) or 0)
        pending_tail = f" ({pending_count} records)" if pending_count else ""
        money = (
            f"${float(comm.get('pending_total', 0)):.2f} pending"
            f"{pending_tail}"
            f" · ${float(comm.get('paid_recent_total', 0)):.2f} paid/{days}d"
        )
        partners = f"{totals.get('partners', 0)} in NocoDB CRM"
        source_note = (
            "Source: <b>NocoDB + local team</b>"
            f" · commissions: <b>{(comm.get('source') or 'unknown')}</b>"
        )
    else:
        bookings = _bookings_summary(days)
        inq = _inquiries_summary(days)
        money = _money_summary(days)
        partners = _partners_summary()
        source_note = "Source: <b>local JSON fallback</b>"

    parts = [
        f"<b>{LABEL} — {date.today().strftime('%a %b %d')}</b>",
        source_note,
        "",
        f"<b>Workers</b>  active today: {digest.get('active_count',0)}"
        f" · quiet: {digest.get('quiet_count',0)}"
        f" · blockers: {digest.get('blocker_count',0)}"
        f" · hours: {digest.get('total_hours_today',0)}h",
    ]
    if digest.get("active_workers"):
        parts.append("")
        parts.extend(digest["active_workers"][:6])
    if digest.get("blockers_lines"):
        parts.append("")
        parts.append("<b>Blockers</b>")
        parts.extend(["• " + b for b in digest["blockers_lines"]])

    parts += ["", f"<b>Bookings (7d)</b>  {bookings}"]
    parts += [f"<b>Inquiries (7d)</b>  {inq}"]
    parts += [f"<b>Money (7d)</b>  {money}"]
    parts += [f"<b>Partners</b>  {partners}"]
    if ops and ops.get("warnings"):
        parts += ["", "<b>Warnings</b>"]
        parts.extend([f"• {w}" for w in ops.get("warnings", [])[:3]])
    parts += ["", "<i>/bookings /money /records /partners /workers /blockers /quiet /source /digest</i>"]
    send(chat_id, "\n".join(parts))


def cmd_bookings(uid, chat_id, args, msg):
    days = _arg_int(args, default=14)
    since = (date.today() - timedelta(days=days)).isoformat()
    out = http_get("/api/bookings/", since=since) or {}
    rows = out.get("bookings", out) if isinstance(out, dict) else out
    if not isinstance(rows, list):
        rows = []
    confirmed = [b for b in rows if (b.get("status") or "").lower() == "confirmed"]
    holds = [b for b in rows if (b.get("status") or "").lower() == "hold"]

    lines = [
        f"<b>Bookings — last {days} days</b>",
        f"Total: {len(rows)} · Confirmed: {len(confirmed)} · Holds: {len(holds)}",
    ]
    for b in rows[:10]:
        nm = (b.get("guest_name") or b.get("name") or "?")[:24]
        st = (b.get("status") or "?")[:10]
        sd = (b.get("start_date") or b.get("check_in") or "?")[:10]
        ed = (b.get("end_date") or b.get("check_out") or "?")[:10]
        amt = b.get("total_amount") or b.get("amount") or 0
        lines.append(f"• {nm}  {sd}→{ed}  ${amt}  [{st}]")
    if not rows:
        lines.append("(no bookings in window — check /api/bookings/)")
    send(chat_id, "\n".join(lines))


def cmd_money(uid, chat_id, args, msg):
    start, end, query, label = _extract_window(args, default_days=30)
    days = max(1, (end - start).days + 1)
    ops = _ops_summary(days)
    noco = (ops.get("nocodb", {}) if ops else {}) or {}
    by_type = noco.get("inquiries_by_type", {}) or {}
    recent_count = (noco.get("recent", {}) or {}).get("inquiries", 0)
    comm_meta = (noco.get("commissions", {}) if noco else {}) or {}

    win = _money_window_rollup(start, end)
    today = date.today()
    week = _money_window_rollup(today - timedelta(days=6), today)
    month = _money_window_rollup(today.replace(day=1), today)

    source = "NocoDB + local ledgers" if ops and ((ops.get("source") or {}).get("nocodb_connected")) else "local ledgers"
    lines = [
        f"<b>Money — {label}</b>",
        f"Period: {start.isoformat()} → {end.isoformat()}",
        f"Source: {source}",
        "",
        "<b>Money in (tracked)</b>",
        f"• Booking payments marked paid: USD {win['booking_paid_in']:,.2f} ({win['booking_paid_count']} bookings)",
        f"• Receipt/intake notes marked incoming: {_fmt_money(win['inflow'])}",
        "",
        "<b>Money out (tracked)</b>",
        f"• Receipt/intake notes marked expense: {_fmt_money(win['outflow'])}",
        f"• Partner commissions paid in period: USD {win['comm_paid_out']:,.2f}",
        "",
        "<b>Obligations / pipeline</b>",
        f"• Partner commissions pending now: USD {win['comm_pending_now']:,.2f}",
        f"• Inquiries in period: {recent_count}",
    ]
    for t, n in sorted(by_type.items(), key=lambda x: -x[1]):
        lines.append(f"  · {t}: {n}")

    lines += [
        "",
        "<b>Expense cadence (consolidated)</b>",
        f"• Daily (today): receipts {_fmt_money(week['outflow'] if False else _money_window_rollup(today, today)['outflow'])} + commissions paid USD {_money_window_rollup(today, today)['comm_paid_out']:,.2f}",
        f"• Weekly (last 7d): receipts {_fmt_money(week['outflow'])} + commissions paid USD {week['comm_paid_out']:,.2f}",
        f"• Monthly (MTD): receipts {_fmt_money(month['outflow'])} + commissions paid USD {month['comm_paid_out']:,.2f}",
        "",
        f"Parsing coverage: {win['parsed_count']}/{win['receipts_count']} receipt entries had parseable amounts "
        f"(unclassified amounts: {_fmt_money(win['unknown'])}).",
        "Use /more for line-item detail.",
    ]

    if query:
        lines += ["", f"Applied text filter: <code>{query}</code>"]
    if comm_meta.get("source"):
        lines += [f"Commissions source-of-truth: {comm_meta.get('source')} "
                  f"(NocoDB mirror pending: ${float(comm_meta.get('mirror_pending_total', 0)):.2f})"]
    if ops and ops.get("warnings"):
        lines += ["", "Warnings:"]
        lines += [f"  • {w}" for w in ops.get("warnings", [])[:3]]
    send(chat_id, "\n".join(lines))


def _send_records_report(chat_id, *, start: date, end: date, query: str, label: str, limit: int = 20) -> None:
    rows_receipts = _acct_search(limit=limit, query=query, start=start, end=end)
    rows_comm = _commission_search(limit=limit, query=query, start=start, end=end)

    lines = [
        f"<b>Records — {label}</b>",
        f"Query: <code>{query or '(none)'}</code>",
        f"Range: {start.isoformat()} → {end.isoformat()}",
        "",
        f"<b>Receipts/intake</b>: {len(rows_receipts)}",
    ]
    show_each = max(5, min(15, limit // 2))
    if rows_receipts:
        for r in rows_receipts[:show_each]:
            ts = (r.get("timestamp") or "")[0:16].replace("T", " ")
            who = (r.get("user_name") or r.get("username") or r.get("user_id") or "?")[:20]
            note = (r.get("note") or "").replace("\n", " ").strip()
            note = (note[:70] + "…") if len(note) > 70 else (note or "(no note)")
            fn = r.get("file_name") or ""
            lines.append(
                f"• {ts} · <b>{who}</b> · {r.get('kind','text')} · <code>{r.get('id','')}</code>\n"
                f"  {note}{f' · file: {fn}' if fn else ''}"
            )
    else:
        lines.append("(no receipt/intake rows)")

    lines += ["", f"<b>Commissions</b>: {len(rows_comm)}"]
    if rows_comm:
        for c in rows_comm[:show_each]:
            ts = (c.get("timestamp") or "")[:16].replace("T", " ")
            cid = c.get("id") or "?"
            status = (c.get("status") or "?").lower()
            amt = float(c.get("commission_amount") or 0)
            p = c.get("partner_code") or "?"
            btype = c.get("booking_type") or "?"
            src = c.get("source_id") or "-"
            lines.append(
                f"• {ts} · <code>{cid}</code> · {status} · ${amt:,.2f} · {btype} · {p}\n"
                f"  src: {src}"
            )
    else:
        lines.append("(no commission rows)")

    lines += ["", "Tip: /records halley last 7 days | /records source_id abc123 | /more money last month"]
    send(chat_id, "\n".join(lines))


def cmd_records(uid, chat_id, args, msg):
    """Unified records lookup (receipts + commissions) in natural language."""
    raw = (args or "").strip()
    limit = 20
    m = re.search(r"(?:^|\s)(\d{1,3})\s*$", raw)
    if m:
        limit = max(5, min(100, int(m.group(1))))
        raw = raw[:m.start()].strip()
    start, end, query, label = _extract_window(raw, default_days=30)
    _send_records_report(chat_id, start=start, end=end, query=query, label=label, limit=limit)


def cmd_more(uid, chat_id, args, msg):
    """Deep-dive details for money/records in natural language."""
    raw = (args or "").strip()
    start, end, query, label = _extract_window(raw, default_days=30)
    _send_records_report(chat_id, start=start, end=end, query=query, label=label, limit=60)


def cmd_partners(uid, chat_id, args, msg):
    partners = load_json(PARTNERS_FILE, {})
    active = [p for p in partners.values() if (p.get("status") or "active") == "active"]
    paused = [p for p in partners.values() if p.get("status") == "paused"]
    by_earned = sorted(active, key=lambda p: -float(p.get("total_earned") or 0))[:8]
    lines = [
        f"<b>Partners</b>",
        f"Active: {len(active)} · Paused: {len(paused)} · Total: {len(partners)}",
        "",
        "<b>Top earners</b>",
    ]
    if not by_earned:
        lines.append("(no active partners with earnings yet)")
    for p in by_earned:
        code = p.get("code") or p.get("partner_code") or "?"
        nm = (p.get("name") or "")[:22]
        earned = float(p.get("total_earned") or 0)
        pending = float(p.get("pending_payout") or 0)
        refs = int(p.get("total_referrals") or 0)
        lines.append(f"• <code>{code}</code> {nm} — ${earned:.0f} earned · ${pending:.0f} pending · {refs} refs")
    send(chat_id, "\n".join(lines))


def cmd_source(uid, chat_id, args, msg):
    """Show whether Telegram reports are pulling from NocoDB or local files."""
    days = _arg_int(args, default=7)
    ops = _ops_summary(days)
    if not ops:
        send(chat_id, "Could not fetch /api/ops/summary right now.")
        return
    src = ops.get("source", {}) or {}
    noco = ops.get("nocodb", {}) or {}
    totals = noco.get("totals", {}) or {}
    recent = noco.get("recent", {}) or {}
    comm = noco.get("commissions", {}) or {}
    lines = [
        "<b>Data source status</b>",
        f"NocoDB connected: <b>{'yes' if src.get('nocodb_connected') else 'no'}</b>",
        f"Window: {ops.get('window_days', days)} days (cutoff {ops.get('cutoff_date', '?')})",
        "",
        "<b>NocoDB totals</b>",
        f"Bookings: {totals.get('bookings', 0)}",
        f"Inquiries: {totals.get('inquiries', 0)}",
        f"Applications: {totals.get('applications', 0)}",
        f"Partners: {totals.get('partners', 0)}",
        f"Commissions: {totals.get('commissions', 0)}",
        "",
        "<b>Recent window</b>",
        f"Bookings: {recent.get('bookings', 0)}",
        f"Inquiries: {recent.get('inquiries', 0)}",
        f"Applications: {recent.get('applications', 0)}",
        f"Commission source: {comm.get('source', 'unknown')}",
        f"Commission pending: ${float(comm.get('pending_total', 0)):.2f}",
        f"Commission mirror pending (NocoDB): ${float(comm.get('mirror_pending_total', 0)):.2f}",
        f"Commission paid/{days}d: ${float(comm.get('paid_recent_total', 0)):.2f}",
        "",
        "If NocoDB shows 'no', bot falls back to local JSON files.",
    ]
    send(chat_id, "\n".join(lines))


def cmd_workers(uid, chat_id, args, msg):
    workers = list_workers()
    lines = [f"<b>Workers — {len(workers)} active</b>"]
    for w in workers:
        c = latest_checkin(w["telegram_id"])
        last = "never"
        top = ""
        if c:
            last = c.get("date") or "?"
            top_list = c.get("top_3") or []
            top = " · ".join(top_list[:2]) if top_list else "(no priorities)"
        nm = w.get("name") or "?"
        role = w.get("role") or "helper"
        lines.append(f"• <b>{nm}</b> ({role}) — last: {last} {('· ' + top) if top else ''}")
    if not workers:
        lines.append("(no workers yet — see /addworker)")
    lines.append("")
    lines.append("<i>/addworker tg_id name role — register someone</i>")
    send(chat_id, "\n".join(lines))


def cmd_blockers(uid, chat_id, args, msg):
    digest = http_get("/api/team/digest")
    lines = ["<b>Blockers (today)</b>"]
    if digest.get("blockers_lines"):
        lines.extend(["• " + b for b in digest["blockers_lines"]])
    else:
        lines.append("(no blockers logged today)")
    send(chat_id, "\n".join(lines))


def cmd_quiet(uid, chat_id, args, msg):
    days = _arg_int(args, default=2)
    out = http_get("/api/team/quiet", days=days)
    quiet = out.get("quiet", []) if isinstance(out, dict) else []
    lines = [f"<b>Quiet — no check-in in {days}+ days</b>"]
    if not quiet:
        lines.append("(everyone has checked in recently)")
    for w in quiet:
        last = (w.get("_last_checkin") or {}).get("date") or "never"
        lines.append(f"• <b>{w.get('name')}</b>  (last: {last})")
    send(chat_id, "\n".join(lines))


def cmd_addworker(uid, chat_id, args, msg):
    """/addworker <telegram_id> <name> [role]   — register a worker."""
    parts = (args or "").split(maxsplit=2)
    if len(parts) < 2:
        send(chat_id, "Usage: <code>/addworker &lt;telegram_id&gt; &lt;name&gt; [role]</code>")
        return
    tg_id = parts[0].strip()
    name = parts[1].strip()
    role = parts[2].strip() if len(parts) > 2 else "helper"
    r = http_post("/api/team/workers",
                  {"telegram_id": tg_id, "name": name, "role": role},
                  admin=True)
    if r.get("status") == "ok":
        send(chat_id, f"✓ Registered <b>{name}</b> (id <code>{tg_id}</code>, role: {role})")
    else:
        send(chat_id, f"Could not register: <code>{r}</code>")


def cmd_wa_mode(uid, chat_id, args, msg):
    send(
        chat_id,
        (
            "<b>WhatsApp-friendly mode</b>\n"
            "You can run operations without a Telegram Pulse group.\n\n"
            "1) Keep team chatting in WhatsApp.\n"
            "2) In your DM here, log each worker update with:\n"
            "<code>/checkinfor Name</code> then new lines for priorities, blockers, hours.\n\n"
            "<i>Example</i>\n"
            "<code>/checkinfor Atlas\n"
            "1. Call 3 retreat leads\n"
            "2. Confirm next guest arrival\n"
            "3. Publish retreat reel\n"
            "Blockers: need final ad creatives\n"
            "Hours: 6h</code>\n\n"
            "Then use <code>/today</code>, <code>/blockers</code>, <code>/workers</code> as usual."
        ),
    )


def cmd_addwa(uid, chat_id, args, msg):
    """Create a placeholder worker for someone still on WhatsApp.
    Usage:
      /addwa Name
      /addwa Name | role | hours
    """
    raw = (args or "").strip()
    if not raw:
        send(chat_id, "Usage: <code>/addwa Name</code> or <code>/addwa Name | role | hours</code>")
        return
    if "|" in raw:
        p = [x.strip() for x in raw.split("|")]
        name = p[0] if p else ""
        role = p[1] if len(p) > 1 and p[1] else "helper"
        try:
            hours = float(p[2]) if len(p) > 2 and p[2] else 6.0
        except Exception:
            hours = 6.0
    else:
        name, role, hours = raw, "helper", 6.0
    if not name:
        send(chat_id, "Missing worker name.")
        return
    w, created = ensure_whatsapp_worker(name, role=role, hours=hours)
    if not w:
        send(chat_id, "Could not create worker placeholder right now.")
        return
    if created:
        send(chat_id, f"✓ Added WhatsApp worker <b>{w.get('name')}</b> as <b>{w.get('role')}</b> "
                      f"(id <code>{w.get('telegram_id')}</code>)")
    else:
        send(chat_id, f"Already exists: <b>{w.get('name')}</b> (id <code>{w.get('telegram_id')}</code>)")


def cmd_checkinfor(uid, chat_id, args, msg):
    """Log a worker update you received via WhatsApp.

    Preferred form:
      /checkinfor Name
      1. ...
      2. ...
      3. ...
      Blockers: ...
      Hours: 6h
    """
    raw = (args or "").strip()
    if not raw:
        send(chat_id, "Usage:\n<code>/checkinfor Name</code> then newline details.\n"
                      "Or one-line: <code>/checkinfor Name | p1; p2; p3 | blocker | 6</code>")
        return

    name = ""
    body = ""
    if "\n" in raw:
        lines = raw.splitlines()
        name = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
    elif "|" in raw:
        p = [x.strip() for x in raw.split("|")]
        name = p[0] if p else ""
        priorities = [s.strip() for s in (p[1].split(";") if len(p) > 1 else []) if s.strip()]
        blockers = p[2].strip() if len(p) > 2 else ""
        hours = p[3].strip() if len(p) > 3 else ""
        lines = [f"{i+1}. {x}" for i, x in enumerate(priorities[:3])]
        if blockers:
            lines.append(f"Blockers: {blockers}")
        if hours:
            lines.append(f"Hours: {hours}h")
        body = "\n".join(lines).strip()
    else:
        send(chat_id, "Need details after the name. Example:\n"
                      "<code>/checkinfor Atlas</code>\n"
                      "1. ...\n2. ...\n3. ...\nBlockers: ...\nHours: 6h")
        return

    if not name:
        send(chat_id, "Missing worker name in /checkinfor.")
        return
    if not body:
        send(chat_id, "Missing check-in body (top 3 / blockers / hours).")
        return

    worker = find_worker(name)
    created = False
    if not worker:
        worker, created = ensure_whatsapp_worker(name, role="helper", hours=6.0)
    if not worker:
        send(chat_id, "Could not resolve worker. Try /addwa first.")
        return

    parsed = parse_checkin_text(body)
    payload = {"telegram_id": worker["telegram_id"], **parsed, "kind": "morning"}
    r = http_post("/api/team/checkin", payload)
    if r.get("status") != "ok":
        send(chat_id, f"Could not save check-in: <code>{r}</code>")
        return

    c = r.get("checkin", {})
    top = c.get("top_3") or []
    lines = [
        f"✓ Logged for <b>{worker.get('name')}</b>{' (new worker auto-created)' if created else ''}",
        f"ID: <code>{worker.get('telegram_id')}</code>",
    ]
    if top:
        lines.append("Top 3:")
        lines.extend([f"  {i+1}. {t}" for i, t in enumerate(top)])
    if c.get("blockers"):
        lines.append(f"Blocker: <i>{c.get('blockers')}</i>")
    if c.get("hours_today") is not None:
        lines.append(f"Hours: {c.get('hours_today'):g}")
    send(chat_id, "\n".join(lines))


def cmd_contacts(uid, chat_id, args, msg):
    rows = list_recent_contacts(limit=40)
    lines = ["<b>Recent contacts</b> (message the bot once, then /promote):"]
    if not rows:
        lines.append("(none yet)")
    for r in rows:
        rid = r.get("telegram_id")
        name = (r.get("name") or "?")[:28]
        uname = ("@" + r.get("username")) if r.get("username") else ""
        seen = (r.get("last_seen_at") or "").replace("T", " ")[:16]
        lines.append(f"• <code>{rid}</code> {name} {uname} · {seen}")
    lines.append("")
    lines.append("<i>/promote telegram_id [role] [hours]</i>")
    send(chat_id, "\n".join(lines))


def cmd_promote(uid, chat_id, args, msg):
    """Promote a recent contact into Worker roster.
    Usage: /promote 123456789 gardener 6
    """
    parts = (args or "").split()
    if not parts:
        send(chat_id, "Usage: <code>/promote &lt;telegram_id&gt; [role] [hours]</code>")
        return
    tg_id = parts[0].strip()
    role = parts[1].strip() if len(parts) >= 2 else "helper"
    try:
        hours = float(parts[2]) if len(parts) >= 3 else 6.0
    except Exception:
        hours = 6.0

    contact = load_json(CONTACTS_FILE, {}).get(tg_id, {})
    name = (contact.get("name") or contact.get("username") or f"Worker {tg_id[-4:]}").strip()
    r = http_post(
        "/api/team/workers",
        {
            "telegram_id": tg_id,
            "name": name,
            "role": role,
            "hours_per_day_target": hours,
        },
        admin=True,
    )
    if r.get("status") != "ok":
        send(chat_id, f"Could not promote <code>{tg_id}</code>: <code>{r}</code>")
        return

    send(chat_id, f"✓ Promoted <b>{name}</b> (<code>{tg_id}</code>) as <b>{role}</b>, target {hours:g}h/day")
    send(
        tg_id,
        (
            f"👋 You are now onboarded in {LABEL} Ops as <b>{role}</b>.\n\n"
            "Use <code>/checkin</code> each morning with your top 3 priorities, "
            "blockers, and hours for today."
        ),
    )


def cmd_pulse_setup(uid, chat_id, args, msg):
    """Wizard-less setup from inside Telegram chat.

    In the Pulse supergroup:
      /pulse_setup chat
    In each topic:
      /pulse_setup bookings
      /pulse_setup financials
      /pulse_setup workers
      /pulse_setup general
    """
    chat = msg.get("chat", {}) or {}
    ctype = chat.get("type") or ""
    if ctype not in ("group", "supergroup"):
        send(chat_id, "Run this inside your Pulse group/topics.")
        return

    slot = (args or "").strip().lower()
    thread = msg.get("message_thread_id")
    st = load_state()
    pulse = st.setdefault("pulse", {})
    topics = pulse.setdefault("topics", {})
    pulse["chat_id"] = str(chat_id)  # always set group id when command is run

    if slot in ("chat", "group"):
        save_state(st)
        send(chat_id, "✓ Pulse group saved. Now run /pulse_setup <code>bookings</code>, "
                      "<code>financials</code>, <code>workers</code>, and <code>general</code> "
                      "inside each topic thread.")
        return

    if slot not in ("bookings", "financials", "workers", "general"):
        send(chat_id, "Usage in group/topics:\n"
                      "<code>/pulse_setup chat</code>\n"
                      "<code>/pulse_setup bookings</code>\n"
                      "<code>/pulse_setup financials</code>\n"
                      "<code>/pulse_setup workers</code>\n"
                      "<code>/pulse_setup general</code>")
        return

    if not thread:
        send(chat_id, f"Run <code>/pulse_setup {slot}</code> from inside that Topic thread.")
        return

    topics[slot] = str(thread)
    save_state(st)
    send(chat_id, f"✓ Saved topic <b>{slot}</b> → thread <code>{thread}</code>")


def cmd_pulse_status(uid, chat_id, args, msg):
    cfg = pulse_config()
    chat = cfg.get("chat_id") or ""
    topics = cfg.get("topics", {}) or {}
    req = ("bookings", "financials", "workers", "general")
    ready = bool(chat) and all(topics.get(k) for k in req)
    lines = [
        "<b>Pulse config</b>",
        f"Group chat_id: <code>{chat or '(unset)'}</code>",
    ]
    for k in req:
        v = topics.get(k) or "(unset)"
        mark = "✓" if topics.get(k) else "…"
        lines.append(f"{mark} {k}: <code>{v}</code>")
    lines.append("")
    lines.append("Status: <b>READY</b> ✅" if ready else "Status: <b>INCOMPLETE</b> ⚠")
    lines.append("Use /pulse_setup in the group/topics to fill missing values.")
    send(chat_id, "\n".join(lines))


def cmd_digest_times(uid, chat_id, args, msg):
    """Set or show digest times in CR time.
    Usage:
      /digest_times          -> show
      /digest_times 8 18     -> AM 08:00, PM 18:00
      /digest_times reset    -> defaults 8 / 18
    """
    current_am, current_pm = digest_hours()
    raw = (args or "").strip().lower()
    if not raw:
        send(chat_id, f"Current digest times (CR): AM <b>{current_am:02d}:00</b>, PM <b>{current_pm:02d}:00</b>\n"
                      "Set with: <code>/digest_times 8 18</code>")
        return
    if raw in ("reset", "default"):
        set_digest_hours(8, 18)
        send(chat_id, "✓ Digest times reset to 08:00 and 18:00 (Costa Rica).")
        return
    parts = raw.split()
    if len(parts) != 2:
        send(chat_id, "Usage: <code>/digest_times 8 18</code>")
        return
    try:
        am = int(parts[0]); pm = int(parts[1])
    except Exception:
        send(chat_id, "Hours must be integers 0-23. Example: <code>/digest_times 8 18</code>")
        return
    if not (0 <= am <= 23 and 0 <= pm <= 23):
        send(chat_id, "Hours must be between 0 and 23.")
        return
    set_digest_hours(am, pm)
    send(chat_id, f"✓ Digest times updated: AM <b>{am:02d}:00</b>, PM <b>{pm:02d}:00</b> (CR)")


def cmd_pulse_test(uid, chat_id, args, msg):
    cfg = pulse_config()
    if not cfg.get("chat_id"):
        send(chat_id, "<b>Pulse not configured.</b>\n"
                      "In your supergroup run:\n"
                      "<code>/pulse_setup chat</code>\n"
                      "Then in each topic:\n"
                      "<code>/pulse_setup bookings</code>\n"
                      "<code>/pulse_setup financials</code>\n"
                      "<code>/pulse_setup workers</code>\n"
                      "<code>/pulse_setup general</code>\n\n"
                      "Use <code>/pulse_status</code> to verify.")
        return
    topic = (args or "general").strip().lower()
    r = send_to_pulse(f"<b>Pulse test — {topic}</b>\nFrom {LABEL} brain.", topic=topic)
    send(chat_id, f"Sent to pulse [{topic}]: ok={r.get('ok')}")


def cmd_getchatid(uid, chat_id, args, msg):
    """Print this chat's id and the message_thread_id of the topic the user
    sent /getchatid in. Use this when configuring Pulse."""
    cid = msg.get("chat", {}).get("id")
    ctype = msg.get("chat", {}).get("type")
    title = msg.get("chat", {}).get("title") or ""
    thread = msg.get("message_thread_id")
    text = (
        f"<b>Chat info</b>\n"
        f"chat_id: <code>{cid}</code>\n"
        f"type: <code>{ctype}</code>\n"
        f"title: <code>{title}</code>\n"
        f"thread_id: <code>{thread or '(none — main)'}</code>\n\n"
        "Quick setup in chat:\n"
        "<code>/pulse_setup chat</code> in the main group, then\n"
        "<code>/pulse_setup bookings</code>, <code>/pulse_setup financials</code>,\n"
        "<code>/pulse_setup workers</code>, <code>/pulse_setup general</code>\n"
        "inside each topic thread."
    )
    send(chat_id, text)


def cmd_whoami(uid, chat_id, args, msg):
    user = msg.get("from", {}) or {}
    username = ("@" + user.get("username")) if user.get("username") else "(no username)"
    roles = []
    if is_admin(uid):
        roles.append("admin")
    if is_worker(uid):
        roles.append("worker")
    if is_accounting(uid):
        roles.append("accounting")
    if not roles:
        roles.append("guest")
    send(
        chat_id,
        (
            "<b>Your identity</b>\n"
            f"user_id: <code>{uid}</code>\n"
            f"username: {username}\n"
            f"roles: <b>{', '.join(roles)}</b>"
        ),
    )


def cmd_authorize_accounting(uid, chat_id, args, msg):
    if not is_admin(uid):
        send(chat_id, "Only admins can authorize accounting users.")
        return
    target = (args or "").strip().split()[0] if (args or "").strip() else ""
    if not target:
        send(chat_id, "Usage: <code>/authorize_accounting &lt;telegram_user_id&gt;</code>")
        return
    authorize_accounting_id(target)
    send(chat_id, f"✓ Authorized accounting access for <code>{target}</code>.")
    send(target, f"✅ You are now authorized for {LABEL} accounting intake.\nTry <code>/accounting_help</code>.")


def cmd_accounting_help(uid, chat_id, args, msg):
    if not is_accounting(uid):
        send(chat_id, "Accounting lane is restricted. Ask Sunheart to run "
                      "<code>/authorize_accounting your_user_id</code>.")
        return
    send(
        chat_id,
        (
            "<b>Accounting / receipts intake</b>\n"
            "Text note:\n"
            "<code>/acct paid 18,000 CRC for cleaning supplies</code>\n\n"
            "Receipt photo/document:\n"
            "send image or file with caption <code>/acct vendor + amount + context</code>\n\n"
            "View latest:\n"
            "<code>/acct_last</code>\n"
            "Filter by person:\n"
            "<code>/receipts halley</code>\n"
        ),
    )


def cmd_acct(uid, chat_id, args, msg):
    if not is_accounting(uid):
        send(chat_id, "Accounting lane is restricted. Ask admin to authorize your user id.")
        return
    note = (args or "").strip()
    user = msg.get("from", {}) or {}
    uname = (user.get("username") or "").strip()
    first = (user.get("first_name") or "").strip()
    last = (user.get("last_name") or "").strip()
    display = (f"{first} {last}".strip() or uname or f"user_{uid}")

    file_id = ""
    file_name = ""
    kind = "text"
    if msg.get("photo"):
        ph = (msg.get("photo") or [])[-1]
        file_id = str(ph.get("file_id") or "")
        file_name = f"photo_{msg.get('message_id','')}.jpg"
        kind = "photo"
    elif msg.get("document"):
        doc = msg.get("document") or {}
        file_id = str(doc.get("file_id") or "")
        file_name = str(doc.get("file_name") or f"document_{msg.get('message_id','')}")
        kind = "document"

    if not note and not file_id:
        send(chat_id, "Usage: <code>/acct note or amount</code>\n"
                      "You can also attach a photo/doc with caption <code>/acct ...</code>.")
        return

    saved_path = ""
    if file_id:
        try:
            saved_path = _download_telegram_file(file_id, _acct_month_dir(), file_name or "receipt")
        except Exception as e:
            send(chat_id, f"Receipt save failed: <code>{e}</code>")
            return

    acct_id = f"acct_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{int(time.time()*1000)%100000:05d}"
    entry = {
        "id": acct_id,
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": str(uid),
        "username": uname,
        "user_name": display,
        "chat_id": str(chat_id),
        "message_id": msg.get("message_id"),
        "kind": kind,
        "note": note,
        "file_name": file_name,
        "file_path": saved_path,
    }
    _acct_append(entry)

    extra = f"\nfile: <code>{Path(saved_path).name}</code>" if saved_path else ""
    send(chat_id, f"✅ Saved accounting intake <code>{acct_id}</code>{extra}")

    # Notify admins of new accounting intake (except sender admin).
    preview = (note or "(no note)")[:180]
    for aid in ADMIN_IDS:
        if str(aid) == str(uid):
            continue
        send(aid, f"🧾 <b>Accounting intake</b> from {display}\n"
                  f"id: <code>{acct_id}</code>\n"
                  f"type: {kind}\n"
                  f"note: {preview}")


def cmd_acct_last(uid, chat_id, args, msg):
    if not is_accounting(uid):
        send(chat_id, "Accounting lane is restricted.")
        return
    raw = (args or "").strip()
    limit = 10
    if raw:
        m = re.search(r"(?:^|\s)(\d{1,3})\s*$", raw)
        if m:
            limit = max(1, min(100, int(m.group(1))))
            raw = raw[:m.start()].strip()

    start, end, query, label = _extract_window(raw, default_days=30)
    rows = _acct_search(limit=limit, query=query, start=start, end=end)
    title = f"<b>Latest receipts/intakes</b> ({label}){f' · filter: {query}' if query else ''}"
    lines = [title]
    if not rows:
        lines.append("(none found)")
        send(chat_id, "\n".join(lines))
        return
    for r in rows:
        ts = (r.get("timestamp") or "")[5:16].replace("T", " ")
        nm = (r.get("user_name") or r.get("username") or r.get("user_id") or "?")[:20]
        note = (r.get("note") or "").replace("\n", " ").strip()
        note = (note[:80] + "…") if len(note) > 80 else (note or "(no note)")
        fn = (r.get("file_name") or "")
        lines.append(f"• {ts} · <b>{nm}</b> · {r.get('kind','text')}\n"
                     f"  id: <code>{r.get('id','')}</code> · {note}"
                     f"{f' · file: {fn}' if fn else ''}")
    send(chat_id, "\n".join(lines))


# ─── WORKER COMMANDS ──────────────────────────────────────────────────────
def cmd_checkin(uid, chat_id, args, msg):
    if not is_worker(uid):
        send(chat_id, "You're not registered. Ask James to add you with /addworker.")
        return
    text = (args or "").strip()
    if not text:
        send(chat_id, (
            "<b>Morning check-in</b>\n"
            "Reply with your top 3 + any blockers:\n\n"
            "<i>Example:</i>\n"
            "1. Kitchen prep for guests arriving at 4pm\n"
            "2. Sauna stove repair\n"
            "3. Garden — beds 3 and 4\n"
            "Blockers: need a 1/2\" hose adapter from town\n"
            "Hours: 6h"
        ))
        return
    parsed = parse_checkin_text(text)
    payload = {"telegram_id": str(uid), **parsed, "kind": "morning"}
    r = http_post("/api/team/checkin", payload)
    if r.get("status") == "ok":
        c = r.get("checkin", {})
        top = c.get("top_3") or []
        ack_lines = [f"<b>Got it.</b> Top 3 logged:"]
        if top:
            ack_lines.extend([f"  {i+1}. {t}" for i, t in enumerate(top)])
        else:
            ack_lines.append("  (no numbered list found — your free text is saved)")
        if c.get("blockers"):
            ack_lines.append(f"\nBlocker: <i>{c['blockers']}</i> — surfaced to admins.")
        if c.get("hours_today") is not None:
            ack_lines.append(f"Hours today: {c['hours_today']:g}")
        send(chat_id, "\n".join(ack_lines))

        # Surface blockers immediately to admins
        if c.get("blockers"):
            w = load_json(WORKERS_FILE, {}).get(str(uid), {})
            for aid in ADMIN_IDS:
                send(aid, f"⚠ <b>Blocker</b> from {w.get('name', uid)}:\n{c['blockers']}")
    else:
        send(chat_id, f"Could not save check-in: <code>{r}</code>")


def cmd_done(uid, chat_id, args, msg):
    if not is_worker(uid):
        send(chat_id, "You're not registered as a worker.")
        return
    text = (args or "").strip()
    if not text:
        send(chat_id, "Usage: <code>/done what you finished</code>")
        return
    payload = {"telegram_id": str(uid), "free_text": f"DONE: {text}", "kind": "evening",
               "top_3": [], "blockers": ""}
    http_post("/api/team/checkin", payload)
    send(chat_id, f"✓ Logged: <i>{text}</i>")


def cmd_blocker(uid, chat_id, args, msg):
    if not is_worker(uid):
        send(chat_id, "You're not registered as a worker.")
        return
    text = (args or "").strip()
    if not text:
        send(chat_id, "Usage: <code>/blocker what's stuck</code>")
        return
    http_post("/api/team/checkin", {
        "telegram_id": str(uid), "free_text": f"BLOCKER: {text}",
        "kind": "adhoc", "top_3": [], "blockers": text,
    })
    w = load_json(WORKERS_FILE, {}).get(str(uid), {})
    for aid in ADMIN_IDS:
        send(aid, f"⚠ <b>Blocker</b> from {w.get('name', uid)}:\n{text}")
    send(chat_id, "✓ Flagged. Admins notified.")


def cmd_me(uid, chat_id, args, msg):
    w = load_json(WORKERS_FILE, {}).get(str(uid))
    if not w:
        send(chat_id, "You're not registered. Send your Telegram id "
                      f"(<code>{uid}</code>) to James to be added.")
        return
    c = latest_checkin(str(uid))
    lines = [
        f"<b>{w.get('name','?')}</b> ({w.get('role','helper')})",
        f"Status: {w.get('status','active')}",
    ]
    if c:
        lines.append(f"Last check-in: {c.get('date')} — {c.get('kind')}")
        if c.get("top_3"):
            lines.append("Top 3:")
            lines.extend([f"  {i+1}. {t}" for i, t in enumerate(c["top_3"])])
        if c.get("blockers"):
            lines.append(f"Blocker: <i>{c['blockers']}</i>")
    else:
        lines.append("No check-ins yet — try /checkin")
    send(chat_id, "\n".join(lines))


# ─── /topup — Zen Wallet top-up admin ─────────────────────────────────────

def cmd_topup(uid, chat_id, args, msg):
    """View, confirm, or cancel pending Zen Wallet top-ups."""
    if not is_admin(uid):
        send(chat_id, "Admins only.")
        return
    parts = (args or "").strip().split()

    if not parts:
        d = http_get_admin("/api/wallet/topups", status="pending", limit=20)
        if d.get("_error"):
            send(chat_id, f"Could not load top-ups: {d['_error']}")
            return
        rows = d.get("topups") or []
        if not rows:
            send(chat_id, "🟢 No pending top-ups.")
            return
        lines = [f"<b>Pending top-ups ({len(rows)})</b>", ""]
        for r in rows[:15]:
            when = (r.get("created_at") or "")[:16].replace("T", " ")
            lines.append(
                f"<code>{r.get('ref')}</code> · {r.get('email')}\n"
                f"  ${float(r.get('amount_usd',0)):.0f} via {r.get('rail_name')} → "
                f"<b>{float(r.get('total_zc',0)):.0f} ZC</b> · {when}"
            )
        lines += ["", "Confirm: <code>/topup confirm REF</code>",
                  "Cancel: <code>/topup cancel REF</code>"]
        send(chat_id, "\n".join(lines))
        return

    action = parts[0].lower()
    if action not in ("confirm", "cancel") or len(parts) < 2:
        send(chat_id, "Usage:\n<code>/topup</code>\n<code>/topup confirm REF [AMOUNT_USD]</code>\n<code>/topup cancel REF</code>")
        return

    ref = parts[1].upper().strip()
    payload = {}
    if action == "confirm" and len(parts) >= 3:
        try:
            payload["received_amount_usd"] = float(parts[2].replace("$", ""))
        except Exception:
            send(chat_id, "AMOUNT_USD must be a number.")
            return

    d = http_post(f"/api/wallet/topups/{ref}/{action}", payload, admin=True)
    if d.get("_error"):
        send(chat_id, f"Failed: {d['_error']}")
        return
    if not d.get("ok"):
        send(chat_id, f"Failed: {d.get('detail') or 'unknown'}")
        return
    t = d.get("topup") or {}
    if action == "confirm":
        send(chat_id,
             f"✅ Top-up <b>{ref}</b> confirmed.\n"
             f"{t.get('email')} credited <b>{float(t.get('total_zc',0)):.0f} ZC</b>.")
    else:
        send(chat_id, f"⛔ Top-up <b>{ref}</b> cancelled.")


# http_get_admin is defined at module top (single source of truth).


def cmd_invoice(uid, chat_id, args, msg):
    """Create + send a Stripe invoice from Telegram.

    Usage:
      /invoice <email> <amount_usd> <description...>

    Example:
      /invoice maya@example.com 2000 Zen Village retreat May 12-18
    """
    if not is_admin(uid):
        return
    parts = (args or "").split(maxsplit=2)
    if len(parts) < 3:
        send(chat_id,
             "Usage: <code>/invoice email amount description</code>\n\n"
             "Example: <code>/invoice maya@example.com 2000 Zen Village retreat May 12-18</code>")
        return
    email, amount_str, desc = parts
    try:
        amount = float(amount_str.replace("$", "").replace(",", ""))
    except Exception:
        send(chat_id, f"Couldn't parse amount: <code>{escape_html(amount_str)}</code>")
        return

    payload = {
        "email": email,
        "amount_usd": amount,
        "description": desc,
        "name": "",
        "due_days": 7,
    }
    r = http_post_admin("/api/admin/invoices/create", payload)
    if r.get("_error") or not r.get("ok"):
        send(chat_id, f"❌ Invoice failed: <code>{escape_html(r.get('_error') or 'unknown')[:300]}</code>")
        return
    send(chat_id,
         f"💸 Invoice sent to <code>{r.get('email')}</code>\n"
         f"<b>${r.get('amount_usd'):.2f}</b> · <i>{r.get('description')}</i>\n"
         f"<a href=\"{r.get('hosted_url')}\">Open in Stripe</a> · "
         f"<a href=\"{r.get('pdf')}\">PDF</a>")


def _cmd_backup(uid, chat_id):
    if not is_admin(uid):
        return
    s = http_get_admin("/api/admin/backup/status")
    if s.get("_error"):
        send(chat_id, f"❌ Backup status check failed: <code>{escape_html(s['_error'])[:200]}</code>")
        return
    icon = "✅" if s.get("ok") else "⚠️"
    age = s.get("age_hours", 0)
    mb = round((s.get("total_bytes") or 0) / 1024 / 1024, 1)
    msg = (
        f"{icon} <b>Backup status</b>\n"
        f"Latest: <code>{s.get('latest_stamp','—')}</code> ({age}h ago, {mb} MB)\n"
        f"Retained: {s.get('retention_count',0)} backups\n"
        f"<i>{s.get('schedule','')}</i>"
    )
    if s.get("files"):
        msg += "\n\n" + "\n".join(f"• {f['name']} — {round(f['bytes']/1024,1)} KB"
                                   for f in s["files"][:6])
    send(chat_id, msg)


def cmd_reply(uid, chat_id, args, msg):
    """Email a submission's owner directly from Telegram.

    Usage:
      /reply <token> <message…>

    Get the token from a new-submission ping (first 10 chars of the
    callback_data on the inline buttons), or run /inbox first to copy one.
    """
    if not is_admin(uid):
        return
    parts = (args or "").split(maxsplit=1)
    if len(parts) < 2:
        send(chat_id,
             "Usage: <code>/reply &lt;token&gt; &lt;message&gt;</code>\n\n"
             "Token is the 10-char id from /inbox or the inline-button keyboard. "
             "Tip: just hit ✓ Contacted instead if you don't need to write anything.")
        return
    token, message = parts[0].strip(), parts[1].strip()

    # Resolve token -> submission_key (same map the inline buttons use)
    keys_file = Path("/opt/fpai/apps/zen-village/data/notify_keys.json")
    submission_key = ""
    try:
        if keys_file.exists():
            submission_key = (json.loads(keys_file.read_text()) or {}).get(token, "")
    except Exception:
        pass
    if not submission_key:
        send(chat_id, f"Couldn't find submission for token <code>{token}</code>. "
                      "Token expired? Try /inbox.")
        return

    body = json.dumps({"key": submission_key, "message": message}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if ADMIN_TOKEN:
        headers["x-admin-token"] = ADMIN_TOKEN
    req = urllib.request.Request(
        f"{API_BASE}/api/admin/submissions/reply",
        data=body, method="POST", headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read().decode("utf-8"))
        send(chat_id,
             f"✓ Email sent to <code>{resp.get('to')}</code>\n"
             f"Subject: <i>{resp.get('subject')}</i>\n"
             f"Marked contacted.")
    except Exception as e:
        send(chat_id, f"❌ Reply failed: <code>{escape_html(str(e))[:200]}</code>")


def cmd_inbox(uid, chat_id, args, msg):
    """Show recent website submissions (inquiries + applications).

    /inbox                 → 10 most recent across all kinds
    /inbox 25              → 25 most recent
    /inbox practitioner    → just practitioner applications
    /inbox inquiry         → just inquiries
    /inbox stay            → just Stay-type inquiries (matches inquiry_type)
    """
    if not is_admin(uid):
        return
    raw = (args or "").strip()
    parts = raw.split()
    n = 10
    filt = ""
    for p in parts:
        if p.isdigit():
            n = max(1, min(int(p), 50))
        else:
            filt = p.lower()

    data = http_get_admin("/api/admin/submissions", limit=200)
    if data.get("_error"):
        send(chat_id, "Couldn't reach submissions API: <code>" + escape_html(data["_error"]) + "</code>")
        return
    rows = data.get("submissions", [])

    if filt:
        if filt in ("inquiry", "inquiries"):
            rows = [r for r in rows if r["kind"] == "inquiry"]
        elif filt in ("application", "applications", "apps"):
            rows = [r for r in rows if r["kind"] == "application"]
        else:
            rows = [r for r in rows if filt in (r.get("lane") or "").lower()]

    rows = rows[:n]
    if not rows:
        send(chat_id, f"No submissions match <b>{escape_html(filt or 'all')}</b>.")
        return

    stats = http_get_admin("/api/admin/submissions/stats")
    totals = stats.get("totals", {}) if not stats.get("_error") else {}
    head = (
        f"<b>📥 Inbox</b> · "
        f"{totals.get('inquiries', '?')} inquiries · "
        f"{totals.get('applications', '?')} applications"
    )
    if filt:
        head += f" · filter: <b>{escape_html(filt)}</b>"

    lines = [head, ""]
    for r in rows:
        when = (r.get("submitted_at") or "")[:16].replace("T", " ")
        kind = "❓"
        if r["kind"] == "inquiry": kind = "💬"
        elif r["kind"] == "application": kind = "🌱"
        elif r["kind"] == "booking": kind = "🛏"
        lane = r.get("lane") or ""
        name = r.get("name") or "—"
        email = r.get("email") or ""
        phone = r.get("phone") or ""
        msg_text = (r.get("message") or "").replace("\n", " ")[:120]
        line = f"{kind} <b>{escape_html(name)}</b> · {escape_html(lane)} · <i>{when}</i>"
        if email:
            line += f"\n  ✉ <code>{escape_html(email)}</code>"
        if phone:
            line += f" · ☎ <code>{escape_html(phone)}</code>"
        if msg_text:
            line += f"\n  <i>{escape_html(msg_text)}</i>"
        lines.append(line)

    lines.append("")
    lines.append('<i>Full UI: <a href="https://zenvillagecr.com/admin/submissions">/admin/submissions</a></i>')
    send(chat_id, "\n".join(lines))


# ─── shared command set ───────────────────────────────────────────────────
ADMIN_CMDS = {
    "today": cmd_today, "bookings": cmd_bookings, "money": cmd_money,
    "records": cmd_records, "partners": cmd_partners, "source": cmd_source,
    "workers": cmd_workers, "blockers": cmd_blockers,
    "quiet": cmd_quiet, "digest": cmd_today, "addworker": cmd_addworker,
    "wa_mode": cmd_wa_mode, "addwa": cmd_addwa, "checkinfor": cmd_checkinfor,
    "contacts": cmd_contacts, "promote": cmd_promote,
    "pulse_setup": cmd_pulse_setup, "pulse_status": cmd_pulse_status,
    "pulse_test": cmd_pulse_test, "digest_times": cmd_digest_times,
    "getchatid": cmd_getchatid, "authorize_accounting": cmd_authorize_accounting,
    "topup": cmd_topup, "topups": cmd_topup,
    "inbox": cmd_inbox, "submissions": cmd_inbox, "applications": cmd_inbox,
    "reply": cmd_reply,
    "invoice": cmd_invoice,
    "backup": lambda uid, chat_id, args, msg: _cmd_backup(uid, chat_id),
    "slipping": lambda uid, chat_id, args, msg: send(
        chat_id,
        _slipping_leads_block().lstrip() or "✓ No slipping leads. All open submissions are under 48h.",
    ) if is_admin(uid) else None,
}
WORKER_CMDS = {"checkin": cmd_checkin, "done": cmd_done, "blocker": cmd_blocker, "me": cmd_me}
SHARED_CMDS = {
    "whoami": cmd_whoami,
    "accounting_help": cmd_accounting_help,
    "acct": cmd_acct,
    "acct_last": cmd_acct_last,
    "receipts": cmd_acct_last,
}


def cmd_help(uid, chat_id, args, msg):
    if is_admin(uid):
        text = (
            "<b>Admin commands</b>\n"
            "/today — full daily snapshot\n"
            "/inbox [n|kind|lane] — newest website submissions (inquiries + applications)\n"
            "/reply &lt;token&gt; &lt;message&gt; — email a submitter directly (marks contacted)\n"
            "/slipping — leads still 'new' &gt; 48h\n"
            "/backup — last daily backup status\n"
            "/invoice email amount description — create + send Stripe invoice\n"
            "/bookings [days] — recent bookings\n"
            "/money [natural period] — pipeline + commissions\n"
            "/records [natural query] — receipts + commission records\n"
            "/partners — affiliate roster + top earners\n"
            "/source [days] — NocoDB vs local source status\n"
            "/workers — team roster + last check-in\n"
            "/blockers — today's blockers\n"
            "/quiet [days] — workers who've gone silent\n"
            "/addworker tg_id name [role] — register a worker\n"
            "/wa_mode — run ops while team stays on WhatsApp\n"
            "/addwa Name | role | hours — create WhatsApp-only worker placeholder\n"
            "/checkinfor Name + details — log worker update from WhatsApp\n"
            "/contacts — recent people who've messaged the bot\n"
            "/promote tg_id [role] [hours] — convert contact → worker\n"
            "/pulse_setup ... — one-step Pulse setup from Telegram\n"
            "/pulse_status — show Pulse readiness\n"
            "/digest_times [am pm] — show/set digest times\n"
            "/getchatid — discover chat &amp; topic ids (for Pulse setup)\n"
            "/pulse_test [topic] — send a test post to Pulse\n"
            "/authorize_accounting tg_id — allow accounting receipt intake\n"
            "/accounting_help — receipts command guide\n"
            "/acct ... — save accounting note (with optional photo/doc)\n"
            "/acct_last [natural query] [n] — latest accounting intakes\n"
            "/receipts [natural query] [n] — alias for /acct_last\n"
            "/topup [confirm|cancel REF] — Zen Wallet top-ups\n"
            "/whoami — show your telegram id + roles\n"
        )
    elif is_accounting(uid):
        text = (
            "<b>Accounting commands</b>\n"
            "/accounting_help — receipts flow guide\n"
            "/acct &lt;note&gt; — save note or receipt (with caption)\n"
            "/acct_last [natural query] [n] — latest receipts/intakes\n"
            "/receipts [natural query] [n] — same as /acct_last\n"
            "/whoami — show your telegram id + roles\n"
        )
    elif is_worker(uid):
        text = (
            "<b>Worker commands</b>\n"
            "/checkin — morning top 3 + blockers + hours\n"
            "/done &lt;text&gt; — log something finished\n"
            "/blocker &lt;text&gt; — flag a blocker now\n"
            "/me — your status\n"
            "/whoami — show your telegram id + roles\n"
        )
    else:
        text = (
            f"Hi! This is the {LABEL} brain.\n\n"
            f"You're not registered yet. Your Telegram id is "
            f"<code>{uid}</code> — share this with James to be added.\n\n"
            "Until then, you can DM the public site at "
            "<a href='https://zenvillagecr.com'>zenvillagecr.com</a>."
        )
    send(chat_id, text)


# ─── small data helpers for digest ────────────────────────────────────────
def _bookings_summary(days: int) -> str:
    out = http_get("/api/bookings/")
    rows = out.get("bookings", out) if isinstance(out, dict) else (out or [])
    if not isinstance(rows, list):
        return "(api unavailable)"
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    recent = [b for b in rows if (b.get("created_at") or b.get("start_date") or "")[:10] >= cutoff]
    confirmed = [b for b in recent if (b.get("status") or "").lower() == "confirmed"]
    return f"{len(recent)} new · {len(confirmed)} confirmed"


def _inquiries_summary(days: int) -> str:
    inq = load_json(INQUIRIES_FILE, [])
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    recent = [i for i in inq if (i.get("timestamp") or "")[:10] >= cutoff]
    types = {}
    for i in recent:
        t = i.get("inquiry_type") or "Other"
        types[t] = types.get(t, 0) + 1
    bits = ", ".join(f"{n} {t}" for t, n in sorted(types.items(), key=lambda x: -x[1])[:4])
    return f"{len(recent)} total · {bits or '(none)'}"


def _money_summary(days: int) -> str:
    commissions = list(load_json(COMMISSIONS_FILE, {}).values())
    pending = sum(float(c.get("commission_amount") or 0) for c in commissions if c.get("status") == "pending")
    return f"${pending:,.0f} commissions pending"


def _partners_summary() -> str:
    p = load_json(PARTNERS_FILE, {})
    active = sum(1 for v in p.values() if (v.get("status") or "active") == "active")
    return f"{active} active / {len(p)} total"


def _arg_int(args: str, default: int) -> int:
    try:
        return int((args or "").strip().split()[0])
    except Exception:
        return default


def _extract_window(args: str, default_days: int = 30) -> tuple[date, date, str, str]:
    """Parse natural-language time windows.

    Supports:
      - last 7 days / last 2 weeks / last 3 months
      - today / yesterday / this week / this month / last week / last month
      - since 2026-04-01
      - from 2026-04-01 to 2026-04-15
      - on 2026-04-12

    Returns: start_date, end_date, leftover_query, label
    """
    raw = (args or "").strip()
    lower = raw.lower()
    today = date.today()

    start = today - timedelta(days=max(1, default_days) - 1)
    end = today
    label = f"last {default_days} days"
    clean = raw

    def _strip_span(s: str, span: tuple[int, int]) -> str:
        return (s[:span[0]] + " " + s[span[1]:]).strip()

    # explicit ranges first
    m = re.search(r"\bfrom\s+(\d{4}-\d{2}-\d{2})\s+(?:to|until|through)\s+(\d{4}-\d{2}-\d{2})\b", lower)
    if m:
        a = _to_date(m.group(1)); b = _to_date(m.group(2))
        if a and b:
            start, end = (a, b) if a <= b else (b, a)
            label = f"{start.isoformat()} to {end.isoformat()}"
            clean = _strip_span(clean, m.span())
    else:
        m = re.search(r"\b(\d{4}-\d{2}-\d{2})\s+(?:to|until|through)\s+(\d{4}-\d{2}-\d{2})\b", lower)
        if m:
            a = _to_date(m.group(1)); b = _to_date(m.group(2))
            if a and b:
                start, end = (a, b) if a <= b else (b, a)
                label = f"{start.isoformat()} to {end.isoformat()}"
                clean = _strip_span(clean, m.span())

    if label == f"last {default_days} days":
        m = re.search(r"\bsince\s+(\d{4}-\d{2}-\d{2})\b", lower)
        if m:
            a = _to_date(m.group(1))
            if a:
                start, end = a, today
                label = f"since {a.isoformat()}"
                clean = _strip_span(clean, m.span())

    if label == f"last {default_days} days":
        m = re.search(r"\bon\s+(\d{4}-\d{2}-\d{2})\b", lower)
        if m:
            a = _to_date(m.group(1))
            if a:
                start = end = a
                label = f"on {a.isoformat()}"
                clean = _strip_span(clean, m.span())

    if label == f"last {default_days} days":
        m = re.search(r"\blast\s+(\d{1,3})\s*(day|days|d|week|weeks|w|month|months|m)\b", lower)
        if m:
            n = max(1, int(m.group(1)))
            unit = m.group(2)
            days = n
            if unit.startswith("w"):
                days = n * 7
            elif unit.startswith("m"):
                days = n * 30
            start = today - timedelta(days=days - 1)
            end = today
            label = f"last {days} days"
            clean = _strip_span(clean, m.span())

    if label == f"last {default_days} days":
        if re.search(r"\btoday\b", lower):
            start = end = today
            label = "today"
            clean = re.sub(r"\btoday\b", " ", clean, flags=re.I)
        elif re.search(r"\byesterday\b", lower):
            start = end = today - timedelta(days=1)
            label = "yesterday"
            clean = re.sub(r"\byesterday\b", " ", clean, flags=re.I)
        elif re.search(r"\bthis week\b", lower):
            start = today - timedelta(days=today.weekday())
            end = today
            label = "this week"
            clean = re.sub(r"\bthis week\b", " ", clean, flags=re.I)
        elif re.search(r"\blast week\b", lower):
            last_week_end = today - timedelta(days=today.weekday() + 1)
            start = last_week_end - timedelta(days=6)
            end = last_week_end
            label = "last week"
            clean = re.sub(r"\blast week\b", " ", clean, flags=re.I)
        elif re.search(r"\bthis month\b", lower):
            start = today.replace(day=1)
            end = today
            label = "this month"
            clean = re.sub(r"\bthis month\b", " ", clean, flags=re.I)
        elif re.search(r"\blast month\b", lower):
            first_this = today.replace(day=1)
            end = first_this - timedelta(days=1)
            start = end.replace(day=1)
            label = "last month"
            clean = re.sub(r"\blast month\b", " ", clean, flags=re.I)

    clean = re.sub(r"\s+", " ", clean).strip(" ,;|")
    return start, end, clean, label


# ─── digest scheduler ─────────────────────────────────────────────────────
def maybe_post_digests() -> None:
    """Post AM/PM digest at configured CR hours (default 08:00 / 18:00)."""
    state = load_json(BOT_STATE_FILE, {})
    now = datetime.now(TZ_CR)
    today = now.date().isoformat()
    am_hour, pm_hour = digest_hours()

    if am_hour <= now.hour < am_hour + 1 and state.get("am_digest_date") != today:
        post_am_digest()
        state["am_digest_date"] = today
        save_json(BOT_STATE_FILE, state)
        # Once a day, ask the cockpit to send 48h auto-followup emails to
        # leads still 'new'. Idempotent server-side.
        try:
            r = http_post_admin("/api/admin/submissions/run-auto-followup", {})
            n = (r or {}).get("count", 0)
            if n:
                log.info(f"auto-followup: sent {n} emails")
        except Exception as e:
            log.warning(f"auto-followup trigger failed: {e}")
    elif pm_hour <= now.hour < pm_hour + 1 and state.get("pm_digest_date") != today:
        post_pm_digest()
        state["pm_digest_date"] = today
        save_json(BOT_STATE_FILE, state)


def _slipping_leads_block() -> str:
    """Render a 'leads slipping' block from the cockpit API. Empty when nothing
    is slipping so the digest stays quiet."""
    data = http_get_admin("/api/admin/submissions", limit=200, status="new")
    if data.get("_error"):
        return ""
    rows = data.get("submissions", []) or []
    now = datetime.utcnow()
    slipping = []
    for r in rows:
        ts = (r.get("submitted_at") or "")[:19]
        try:
            age_h = (now - datetime.fromisoformat(ts)).total_seconds() / 3600
        except Exception:
            continue
        if age_h > 48:
            slipping.append((age_h, r))
    if not slipping:
        return ""
    slipping.sort(key=lambda t: -t[0])
    lines = [f"\n\n<b>⏰ Leads slipping (still 'new' &gt; 48h)</b>"]
    for age_h, r in slipping[:6]:
        days = int(age_h // 24)
        age_label = f"{days}d ago" if days >= 1 else f"{int(age_h)}h ago"
        name = r.get("name") or "—"
        kind = r.get("lane") or r.get("kind") or ""
        email = r.get("email") or ""
        lines.append(f"• <b>{name}</b> · {kind} · <code>{email}</code> · <i>{age_label}</i>")
    lines.append('<i>Reach out · /admin/submissions</i>')
    return "\n".join(lines)


def post_am_digest() -> None:
    digest = http_get("/api/team/digest")
    bookings = _bookings_summary(7)
    inq = _inquiries_summary(7)
    msg = (
        f"<b>☀ {LABEL} — {date.today().strftime('%a %b %d')}</b>\n"
        f"Active workers: {digest.get('active_count',0)} · "
        f"Hours pledged: {digest.get('total_hours_today',0)}h · "
        f"Blockers: {digest.get('blocker_count',0)}\n"
    )
    if digest.get("active_workers"):
        msg += "\n" + "\n".join(digest["active_workers"][:6])
    msg += f"\n\n<b>Bookings (7d):</b> {bookings}\n<b>Inquiries (7d):</b> {inq}"
    if digest.get("blockers_lines"):
        msg += "\n\n<b>Blockers</b>\n" + "\n".join("• " + b for b in digest["blockers_lines"])
    msg += _slipping_leads_block()

    if pulse_config().get("chat_id"):
        send_to_pulse(msg, topic="general")
    for aid in ADMIN_IDS:
        send(aid, msg)

    # Quiet pings
    quiet = (http_get("/api/team/quiet", days=2) or {}).get("quiet", [])
    for w in quiet:
        send(w["telegram_id"],
             f"☀ Morning! Haven't heard from you in a couple days. "
             f"Send <code>/checkin</code> with your top 3 when you can.")


def post_pm_digest() -> None:
    digest = http_get("/api/team/digest")
    msg = (
        f"<b>🌙 {LABEL} — Evening pulse</b>\n"
        f"Workers active: {digest.get('active_count',0)} · "
        f"Open blockers: {digest.get('blocker_count',0)}"
    )
    if digest.get("blockers_lines"):
        msg += "\n\n<b>Open blockers</b>\n" + "\n".join("• " + b for b in digest["blockers_lines"])
    msg += "\n\n<i>What got done? Reply /done [text] in your DM.</i>"
    if pulse_config().get("chat_id"):
        send_to_pulse(msg, topic="general")
    for aid in ADMIN_IDS:
        send(aid, msg)


# ─── update dispatch ──────────────────────────────────────────────────────
def _answer_callback(callback_query_id: str, text: str = "", show_alert: bool = False) -> dict:
    return tg("answerCallbackQuery", callback_query_id=callback_query_id,
              text=text[:200], show_alert=show_alert)


def _edit_message_text(chat_id, message_id, text: str, parse_mode: str = "HTML") -> dict:
    return tg("editMessageText", chat_id=chat_id, message_id=message_id,
              text=text[:4000], parse_mode=parse_mode,
              disable_web_page_preview=True)


def handle_callback_query(cq: dict) -> None:
    """One-tap inline-button handlers from new-submission notifications."""
    cqid = cq.get("id")
    data = (cq.get("data") or "").strip()
    user = cq.get("from", {}) or {}
    uid = str(user.get("id") or "")
    msg = cq.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    message_id = msg.get("message_id")

    if not is_admin(uid):
        _answer_callback(cqid, "Not authorized.", show_alert=True)
        return

    parts = data.split(":", 2)
    if len(parts) != 3 or parts[0] != "sub":
        _answer_callback(cqid, "Unknown action.")
        return
    action, token = parts[1], parts[2]

    # Resolve token → submission_key via shared mapping file
    keys_file = Path("/opt/fpai/apps/zen-village/data/notify_keys.json")
    submission_key = ""
    try:
        if keys_file.exists():
            submission_key = (json.loads(keys_file.read_text()) or {}).get(token, "")
    except Exception:
        submission_key = ""
    if not submission_key:
        _answer_callback(cqid, "Submission expired (token cache rotated).", show_alert=True)
        return

    new_status = "contacted" if action == "contact" else "closed" if action == "close" else ""
    if not new_status:
        _answer_callback(cqid, "Unknown action.")
        return

    # POST to the admin API (uses ADMIN_TOKEN)
    body = json.dumps({"key": submission_key, "status": new_status}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if ADMIN_TOKEN:
        headers["x-admin-token"] = ADMIN_TOKEN
    req = urllib.request.Request(
        f"{API_BASE}/api/admin/submissions/status",
        data=body, method="POST", headers=headers,
    )
    try:
        urllib.request.urlopen(req, timeout=8).read()
    except Exception as e:
        log.warning("status update failed: %s", e)
        _answer_callback(cqid, "Couldn't save status.", show_alert=True)
        return

    label = "✓ Marked contacted" if new_status == "contacted" else "📁 Archived"
    _answer_callback(cqid, label)

    # Edit the message in-place to show the new status
    try:
        original = msg.get("text") or ""
        marker = f"\n\n— {label} by {user.get('first_name') or uid}"
        if original and "— ✓ Marked" not in original and "— 📁" not in original:
            _edit_message_text(chat_id, message_id, original + marker, parse_mode="HTML")
    except Exception as e:
        log.warning("edit message failed: %s", e)


def handle_update(upd: dict) -> None:
    cq = upd.get("callback_query")
    if cq:
        try:
            handle_callback_query(cq)
        except Exception as e:
            log.exception("callback handler crashed: %s", e)
        return
    msg = upd.get("message") or upd.get("edited_message")
    if not msg:
        return
    chat = msg.get("chat", {}) or {}
    chat_id = chat.get("id")
    user = msg.get("from", {}) or {}
    uid = str(user.get("id") or "")
    record_contact(user, chat)
    # For media posts we treat caption as command text (e.g. photo + /acct ...).
    text = (msg.get("text") or msg.get("caption") or "").strip()
    if not text:
        return

    # Command extraction: /cmd@bot args
    m = re.match(r"^/(\w+)(?:@\w+)?(?:\s+(.*))?$", text, re.S)
    if m:
        cmd, args = m.group(1).lower(), (m.group(2) or "").strip()
    else:
        cmd, args = "", text

    log.info("update from uid=%s chat=%s cmd=%s", uid, chat_id, cmd or "(text)")

    # Reject anything from unknown chat types (channels) other than configured Pulse
    pulse_chat_id = pulse_config().get("chat_id")
    if chat.get("type") in ("channel",) and str(chat_id) != str(pulse_chat_id or ""):
        return

    # Auth and dispatch
    if cmd in ("start", "help"):
        cmd_help(uid, chat_id, args, msg)
        return

    if cmd in SHARED_CMDS:
        SHARED_CMDS[cmd](uid, chat_id, args, msg)
        return

    if is_admin(uid) and cmd in ADMIN_CMDS:
        ADMIN_CMDS[cmd](uid, chat_id, args, msg)
        return

    # Lightweight NL routing for admins so slash commands are optional.
    if cmd == "" and is_admin(uid):
        low = text.lower()
        if any(k in low for k in ("receipt", "receipts", "record", "records", "transaction")):
            cmd_records(uid, chat_id, text, msg)
            return
        if any(k in low for k in ("money", "cash", "financial", "finance", "pipeline", "revenue")):
            cmd_money(uid, chat_id, text, msg)
            return
        if "source" in low and "data" in low:
            cmd_source(uid, chat_id, "", msg)
            return

    if cmd in WORKER_CMDS:
        WORKER_CMDS[cmd](uid, chat_id, args, msg)
        return

    # Anything else from a worker is treated as an ad-hoc check-in note
    if is_worker(uid) and cmd == "":
        cmd_checkin(uid, chat_id, text, msg)
        return

    if is_admin(uid):
        cmd_help(uid, chat_id, args, msg)
        return

    send(chat_id, "Hmm, I don't know that command. Try /help.")


# ─── main long-poll loop ──────────────────────────────────────────────────
def main() -> None:
    p = pulse_config()
    log.info("zv-bot starting · admins=%s · pulse=%s · api=%s",
             ", ".join(sorted(ADMIN_IDS)) or "(none)",
             p.get("chat_id") or "(unset)", API_BASE)

    me = tg("getMe")
    if not me.get("ok"):
        log.error("getMe failed: %s", me)
        sys.exit(2)
    log.info("bot identity: @%s (id=%s)", me["result"].get("username"), me["result"].get("id"))

    state = load_json(BOT_STATE_FILE, {})
    offset = int(state.get("offset", 0))

    while True:
        try:
            r = tg("getUpdates", offset=offset, timeout=25,
                   allowed_updates=["message", "edited_message", "callback_query"])
            if r.get("ok"):
                for upd in r.get("result", []):
                    offset = max(offset, int(upd["update_id"]) + 1)
                    try:
                        handle_update(upd)
                    except Exception as e:
                        log.exception("handler crashed: %s", e)
                # Re-read from disk so we don't clobber other writers
                # (e.g. maybe_post_digests writes am/pm_digest_date in another tick).
                state = load_json(BOT_STATE_FILE, {})
                state["offset"] = offset
                save_json(BOT_STATE_FILE, state)
            maybe_post_digests()
            # Reload state so our local copy reflects digest writes for next iter.
            state = load_json(BOT_STATE_FILE, {})
        except KeyboardInterrupt:
            log.info("shutdown")
            return
        except Exception as e:
            log.exception("loop error: %s", e)
            time.sleep(3)


if __name__ == "__main__":
    main()

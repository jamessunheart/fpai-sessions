"""
Zen Village — Admin Submissions Browser

Single API surface that lists every public website submission so admins can
reach out fast. Reads the local JSON files the inquiry/application handlers
already write — no NocoDB round-trip required (NocoDB stays as the durable
mirror, but the source of truth here is on-disk).

Sources:
  • Inquiries  (Stay / Retreat / Coherent Retreat / Support / Event …)
      /opt/fpai/apps/zen-village/data/inquiries.json
  • Applications  (practitioner / artist / creator / volunteer / work-exchange)
      /opt/fpai/apps/zen-village/data/applications/<lane>/_all.json
  • Bookings (light view)
      /opt/fpai/apps/zen-village/data/bookings.db  (sqlite, optional)

Auth model: same as receipts_admin — X-Admin-Token (ZV_ADMIN_TOKEN, falls back
to ZV_AFFILIATES_ADMIN_TOKEN). The HTML page prompts once, stores in
localStorage, and sends it on every fetch.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query

router = APIRouter()

DATA_DIR = Path(os.environ.get("ZV_DATA_DIR", "/opt/fpai/apps/zen-village/data"))
INQUIRIES_FILE = DATA_DIR / "inquiries.json"
APPLICATIONS_DIR = DATA_DIR / "applications"
BOOKINGS_DB = DATA_DIR / "bookings.db"
STATUS_FILE = DATA_DIR / "submission_status.json"

VALID_LANES = ("practitioner", "artist", "creator", "volunteer", "work-exchange")
VALID_STATUSES = ("new", "contacted", "closed")

# Strong test-row patterns. Anything matching is hidden by default; pass
# include_test=1 to surface them when QA-ing the form.
TEST_PATTERNS = (
    "@example.com", "@test.local", "@zenvillage.local",
    "@fullpotential.com",  # James's self-tests
    "smoketest", "wiretest", "fullpipe", "fullsync",
    "multi-sync", "multi-app", "lane test", "smoke recheck",
    "smoke prac", "booking form test", "test audit", "test guest",
    "test inquirer", "test booking", "test host", "retest 17",
    "creator-formtest", "vol-formtest", "artist-formtest",
    "prac-formtest", "e2e ",
)


def _is_test_row(r: dict) -> bool:
    bag = " ".join([
        (r.get("email") or "").lower(),
        (r.get("name") or "").lower(),
        (r.get("message") or "").lower(),
        ((r.get("raw") or {}).get("message") or "").lower() if isinstance(r.get("raw"), dict) else "",
    ])
    return any(p in bag for p in TEST_PATTERNS)


# ─── status tracking ─────────────────────────────────────────────────────────
def _load_status() -> dict:
    if not STATUS_FILE.exists():
        return {}
    try:
        return json.loads(STATUS_FILE.read_text())
    except Exception:
        return {}


def _save_status(d: dict) -> None:
    tmp = STATUS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    tmp.replace(STATUS_FILE)


def _key(row: dict) -> str:
    """Stable id for a submission: email+kind+lane+timestamp."""
    return "|".join([
        row.get("kind") or "",
        row.get("lane") or "",
        (row.get("email") or "").lower().strip(),
        (row.get("submitted_at") or "")[:19],
    ])


def _annotate_status(rows: list[dict]) -> list[dict]:
    statuses = _load_status()
    for r in rows:
        k = _key(r)
        s = statuses.get(k) or {}
        r["_key"] = k
        r["track_status"] = s.get("status") or "new"
        r["track_note"] = s.get("note") or ""
        r["track_updated_at"] = s.get("updated_at") or ""
    return rows


def _admin_token() -> str:
    return (
        os.environ.get("ZV_ADMIN_TOKEN")
        or os.environ.get("ZV_AFFILIATES_ADMIN_TOKEN")
        or ""
    )


def _require_admin(
    x_admin_token: Optional[str],
    x_session_token: Optional[str] = None,
) -> None:
    """Authorize a caller for the Submissions surface.

    Two accepted credentials:
      1. The shared legacy admin token (ZV_AFFILIATES_ADMIN_TOKEN) — owner
         back-door, paste-the-token flow.
      2. A cockpit session token (X-Session-Token) belonging to a user who
         has been granted the `submissions` surface in the cockpit registry.
         This is what lets a scoped `member` (e.g. Suri) in without ever
         handing the master token to their browser.
    """
    expected = _admin_token()
    if expected and x_admin_token and x_admin_token == expected:
        return
    # Cockpit session path — resolve the user and check their surface grant.
    if x_session_token:
        try:
            from app.cockpit_hub import _resolve_caller, _can_see
            caller = _resolve_caller(None, x_session_token)
            if _can_see(caller, "submissions"):
                return
            raise HTTPException(403, "Submissions surface not granted")
        except HTTPException:
            raise
        except Exception:
            pass
    if not expected:
        raise HTTPException(503, "Admin token not configured")
    raise HTTPException(401, "Invalid admin token")


def _load_inquiries() -> list[dict]:
    if not INQUIRIES_FILE.exists():
        return []
    try:
        rows = json.loads(INQUIRIES_FILE.read_text())
    except Exception:
        return []
    out = []
    for r in rows:
        src = r.get("_source") if isinstance(r.get("_source"), dict) else {}
        out.append({
            "kind": "inquiry",
            "id": r.get("id") or "",
            "lane": r.get("inquiry_type") or "Stay",
            "name": r.get("name") or "",
            "email": r.get("email") or "",
            "phone": r.get("phone") or "",
            "message": r.get("message") or "",
            "dates": r.get("dates") or "",
            "guests": r.get("guests") or "",
            "accommodation": r.get("accommodation") or "",
            "payment_method": r.get("payment_method") or "",
            "partner_code": r.get("partner_code") or "",
            "source": _humanize_source(src, r.get("partner_code") or ""),
            "submitted_at": r.get("timestamp") or "",
            "status": r.get("status") or "new",
            "raw": r,
        })
    return out


def _humanize_source(src: dict, raw_partner: str = "") -> str:
    """Return a short human label like 'Instagram (Atlas)' or 'Direct'."""
    if not src and not raw_partner:
        return ""
    if not isinstance(src, dict):
        src = {}
    bits = []
    src_name = src.get("utm_source") or ""
    if src_name:
        bits.append(src_name)
    elif src.get("referrer"):
        try:
            from urllib.parse import urlparse
            host = urlparse(src["referrer"]).netloc.replace("www.", "")
            if host and "zenvillage" not in host:
                bits.append(host)
        except Exception:
            pass
    if not bits:
        bits.append("direct")
    ref = src.get("ref") or src.get("cookie_ref") or raw_partner
    if ref:
        bits.append(f"ref={ref}")
    return " · ".join(bits)


def _load_applications(lane_filter: Optional[str] = None) -> list[dict]:
    out = []
    if not APPLICATIONS_DIR.exists():
        return out
    lanes = [lane_filter] if lane_filter and lane_filter in VALID_LANES else VALID_LANES
    for lane in lanes:
        master = APPLICATIONS_DIR / lane / "_all.json"
        if not master.exists():
            continue
        try:
            rows = json.loads(master.read_text())
        except Exception:
            rows = []
        for r in rows:
            offering = (
                r.get("offering")
                or r.get("contribution")
                or r.get("intentions")
                or r.get("why_zen_village")
                or r.get("anything_else")
                or ""
            )
            src = r.get("_source") if isinstance(r.get("_source"), dict) else {}
            out.append({
                "kind": "application",
                "id": r.get("_file") or "",
                "lane": lane,
                "name": r.get("name") or r.get("full_name") or r.get("nickname") or "",
                "email": r.get("email") or "",
                "phone": r.get("phone") or r.get("whatsapp") or "",
                "telegram": r.get("telegram") or r.get("telegram_handle") or "",
                "country": r.get("country") or r.get("nationality") or r.get("current_location") or "",
                "message": offering[:600],
                "instagram": r.get("instagram") or "",
                "website": r.get("website") or "",
                "source": _humanize_source(src, r.get("partner_code") or ""),
                "submitted_at": r.get("submitted_at") or "",
                "status": r.get("status") or "new",
                "raw": r,
            })
    return out


def _load_bookings(limit: int = 50) -> list[dict]:
    if not BOOKINGS_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(BOOKINGS_DB))
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM bookings ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception:
        return []
    out = []
    for r in rows:
        out.append({
            "kind": "booking",
            "id": r.get("id") or "",
            "lane": "Booking",
            "name": r.get("guest_name") or "",
            "email": r.get("guest_email") or "",
            "phone": r.get("guest_phone") or "",
            "country": r.get("guest_country") or "",
            "dates": f"{r.get('check_in','')} → {r.get('check_out','')}",
            "accommodation": r.get("structure_id") or "",
            "total": r.get("total_amount") or 0,
            "payment_status": r.get("payment_status") or "",
            "partner_code": r.get("partner_code") or "",
            "submitted_at": r.get("created_at") or "",
            "status": r.get("status") or "pending",
            "raw": r,
        })
    return out


def _sort_newest(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: r.get("submitted_at") or "", reverse=True)


# ─── API ─────────────────────────────────────────────────────────────────────

@router.get("/api/admin/submissions")
async def list_all(
    x_admin_token: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    kind: Optional[str] = Query(None, description="inquiry|application|booking|all"),
    lane: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="new|contacted|closed"),
    include_test: int = Query(0, description="1 to include test/QA rows"),
    limit: int = Query(500, ge=1, le=2000),
):
    """Combined feed. Default returns real inquiries + applications, newest first."""
    _require_admin(x_admin_token, x_session_token)

    rows: list[dict] = []
    k = (kind or "all").lower()

    if k in ("all", "inquiry"):
        rows.extend(_load_inquiries())
    if k in ("all", "application"):
        rows.extend(_load_applications(lane_filter=lane))
    if k == "booking":
        rows.extend(_load_bookings(limit=limit))

    if not include_test:
        rows = [r for r in rows if not _is_test_row(r)]

    rows = _sort_newest(rows)
    rows = _annotate_status(rows)
    if status and status in VALID_STATUSES:
        rows = [r for r in rows if r["track_status"] == status]
    rows = rows[:limit]
    return {
        "count": len(rows),
        "kinds": sorted({r["kind"] for r in rows}),
        "lanes": sorted({r["lane"] for r in rows if r.get("lane")}),
        "submissions": rows,
    }


@router.get("/api/admin/backup/status")
async def backup_status(
    x_admin_token: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
):
    """Report on the latest daily backup so we know it's actually running."""
    _require_admin(x_admin_token, x_session_token)
    from pathlib import Path as _P
    import os
    base = _P("/opt/fpai/backups/zen-village")
    if not base.exists():
        return {"ok": False, "message": "no backup directory yet"}
    backups = sorted(
        [d for d in base.iterdir() if d.is_dir() and d.name.startswith("20")],
        key=lambda p: p.name, reverse=True,
    )
    if not backups:
        return {"ok": False, "message": "no backups present"}
    latest = backups[0]
    age_h = (datetime.utcnow().timestamp() - latest.stat().st_mtime) / 3600
    files = []
    total = 0
    for f in latest.iterdir():
        if f.is_file():
            sz = f.stat().st_size
            total += sz
            files.append({"name": f.name, "bytes": sz})
    return {
        "ok": age_h < 36,  # red if last backup > 36h
        "latest_stamp": latest.name,
        "age_hours": round(age_h, 1),
        "total_bytes": total,
        "files": files,
        "retention_count": len(backups),
        "schedule": "daily 03:30 Costa Rica via /opt/fpai/scripts/zv-daily-backup.sh",
    }


@router.post("/api/admin/submissions/run-auto-followup")
async def run_auto_followup(
    x_admin_token: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
):
    """Send a soft follow-up email to every submission that is still 'new'
    and was submitted between 48h and 7d ago. Idempotent: marks each row as
    contacted with note 'auto-followup' so it never fires twice.
    """
    _require_admin(x_admin_token, x_session_token)
    from app.mail import send_followup_48h

    statuses = _load_status()
    rows = _load_inquiries() + _load_applications()
    now = datetime.utcnow()
    sent = []
    skipped = 0
    for r in rows:
        if _is_test_row(r):
            continue
        if not r.get("email"):
            continue
        ts = (r.get("submitted_at") or "")[:19]
        try:
            submitted = datetime.fromisoformat(ts)
        except Exception:
            continue
        age_h = (now - submitted).total_seconds() / 3600
        if not (48 <= age_h <= 24 * 7):
            skipped += 1
            continue
        key = _key(r)
        cur = statuses.get(key, {})
        # Skip if it's already been contacted, or already had a followup.
        if cur.get("status") and cur.get("status") != "new":
            continue
        if (cur.get("note") or "").startswith("auto-followup"):
            continue
        ok = send_followup_48h(r.get("name") or "", r["email"],
                               r.get("lane") or r.get("kind") or "")
        if ok:
            sent.append({"email": r["email"], "lane": r.get("lane"),
                         "age_h": round(age_h, 1)})
            statuses[key] = {
                "status": "new",
                "note": f"auto-followup at {age_h:.0f}h",
                "updated_at": datetime.utcnow().isoformat(),
            }
    _save_status(statuses)
    return {"ok": True, "sent": sent, "count": len(sent), "skipped": skipped}


@router.post("/api/admin/submissions/reply")
async def reply_to_submission(
    payload: dict,
    x_admin_token: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
):
    """Send a real email to the person behind a submission, then mark contacted.

    Body: {"key": "<row key>", "message": "<plain text reply>", "subject": "<optional>"}
    From-address defaults to hello@zenvillagecr.com (configurable per admin in
    the future).
    """
    _require_admin(x_admin_token, x_session_token)
    key = (payload.get("key") or "").strip()
    message = (payload.get("message") or "").strip()
    if not key or not message:
        raise HTTPException(400, "key and message required")

    # Look up the row to find email + name
    target = None
    for r in (_load_inquiries() + _load_applications()):
        if _key(r) == key:
            target = r
            break
    if not target:
        raise HTTPException(404, "submission not found for that key")
    if not target.get("email"):
        raise HTTPException(400, "submission has no email on file")

    name = (target.get("name") or "").split(" ")[0] or "there"
    label = (target.get("lane") or target.get("kind") or "submission")
    subject = (payload.get("subject")
               or f"Re: your {label} — Zen Village")
    text = f"Hi {name},\n\n{message}\n\nWith care,\nJames\nZen Village\n"
    html_msg = (
        f"<div style='font-family:-apple-system,BlinkMacSystemFont,Inter,sans-serif;"
        f"max-width:560px;margin:0 auto;padding:32px 24px;color:#2a2520'>"
        f"<p style='font-size:16px;line-height:1.7'>Hi {name},</p>"
        f"<p style='font-size:15px;line-height:1.7;color:#4a4035;white-space:pre-wrap'>"
        f"{message}</p>"
        f"<p style='font-size:15px;line-height:1.7'>With care,<br/><b>James</b><br/>"
        f"<span style='color:#9a8e74'>Zen Village · Pavones, Costa Rica</span></p>"
        f"</div>"
    )

    from app.mail import send_email
    ok = send_email(target["email"], subject, html_msg, text)
    if not ok:
        raise HTTPException(502, "email relay rejected the message")

    # Mark contacted
    statuses = _load_status()
    statuses[key] = {
        "status": "contacted",
        "note": (payload.get("note") or message[:200]),
        "updated_at": datetime.utcnow().isoformat(),
    }
    _save_status(statuses)
    return {"ok": True, "to": target["email"], "subject": subject}


@router.post("/api/admin/submissions/status")
async def set_status(
    payload: dict,
    x_admin_token: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
):
    """Mark a submission as new/contacted/closed.

    Body: {"key": "<row key>", "status": "contacted", "note": "<optional>"}
    Get the key from the row's `_key` field on /api/admin/submissions output.
    """
    _require_admin(x_admin_token, x_session_token)
    key = (payload.get("key") or "").strip()
    new_status = (payload.get("status") or "").strip().lower()
    note = (payload.get("note") or "").strip()
    if not key:
        raise HTTPException(400, "key required")
    if new_status not in VALID_STATUSES:
        raise HTTPException(400, f"status must be one of {VALID_STATUSES}")
    statuses = _load_status()
    statuses[key] = {
        "status": new_status,
        "note": note,
        "updated_at": datetime.utcnow().isoformat(),
    }
    _save_status(statuses)
    return {"ok": True, "key": key, "status": new_status}


@router.get("/api/admin/submissions/stats")
async def stats(
    x_admin_token: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    include_test: int = Query(0),
):
    """KPIs for the cockpit. Real-only by default."""
    from datetime import timedelta
    _require_admin(x_admin_token, x_session_token)
    inq = _load_inquiries()
    apps = _load_applications()
    if not include_test:
        inq = [r for r in inq if not _is_test_row(r)]
        apps = [r for r in apps if not _is_test_row(r)]

    all_rows = _annotate_status(_sort_newest(inq + apps))

    now = datetime.utcnow()
    def _age_h(r):
        try:
            return (now - datetime.fromisoformat((r.get("submitted_at") or "")[:19])).total_seconds() / 3600
        except Exception:
            return 99999.0

    last_24h = sum(1 for r in all_rows if _age_h(r) < 24)
    last_7d = sum(1 for r in all_rows if _age_h(r) < 24 * 7)
    last_30d = sum(1 for r in all_rows if _age_h(r) < 24 * 30)
    new_count = sum(1 for r in all_rows if r["track_status"] == "new")
    contacted = sum(1 for r in all_rows if r["track_status"] == "contacted")
    closed = sum(1 for r in all_rows if r["track_status"] == "closed")
    # Slipping = still "new" and >48h old
    slipping = [r for r in all_rows if r["track_status"] == "new" and _age_h(r) > 48]

    by_inquiry_type: dict[str, int] = {}
    for r in inq:
        by_inquiry_type[r["lane"]] = by_inquiry_type.get(r["lane"], 0) + 1
    by_app_lane: dict[str, int] = {}
    for r in apps:
        by_app_lane[r["lane"]] = by_app_lane.get(r["lane"], 0) + 1

    last_inq = (_sort_newest(inq)[:1] or [{}])[0].get("submitted_at", "") or None
    last_app = (_sort_newest(apps)[:1] or [{}])[0].get("submitted_at", "") or None

    return {
        "totals": {
            "inquiries": len(inq),
            "applications": len(apps),
            "all": len(all_rows),
        },
        "windows": {
            "last_24h": last_24h,
            "last_7d": last_7d,
            "last_30d": last_30d,
        },
        "by_status": {
            "new": new_count,
            "contacted": contacted,
            "closed": closed,
            "slipping_count": len(slipping),
        },
        "inquiries_by_type": by_inquiry_type,
        "applications_by_lane": by_app_lane,
        "latest_inquiry_at": last_inq,
        "latest_application_at": last_app,
        "generated_at": datetime.utcnow().isoformat(),
    }

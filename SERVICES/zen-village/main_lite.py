"""
Zen Village - Booking Server + Brain
Serves static pages + booking/inquiry APIs.
Brain module receives routed AI signals and takes real actions.
Port: 8770
"""

from fastapi import FastAPI, Request, Query, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional
import json
import logging
import os
import urllib.parse as _uparse
import urllib.request as _ureq

logger = logging.getLogger("zen_village")

BASE_DIR = Path("/opt/fpai/apps/zen-village")
FRONTEND_DIR = BASE_DIR / "frontend" / "public"

app = FastAPI(
    title="Zen Village",
    description="Booking & accommodation management for Zen Village CR",
    version="2.0.0",
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://zenvillagecr.com",
        "https://www.zenvillagecr.com",
        "https://zenvillage.live",
        "https://www.zenvillage.live",
        "https://fullpotential.ai",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount images (auto-create empty dir so the service survives a deploy that
# accidentally dropped the folder via --delete; see incident 2026-05-18).
_images_dir = FRONTEND_DIR / "images"
_images_dir.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=str(_images_dir)), name="images")

# Mount /qr for partner referral QR PNGs (e.g. /qr/ATLAS.png)
_qr_dir = FRONTEND_DIR / "qr"
_qr_dir.mkdir(parents=True, exist_ok=True)
app.mount("/qr", StaticFiles(directory=str(_qr_dir)), name="qr")

# === affiliates ?ref= cookie middleware ===
@app.middleware("http")
async def _zv_ref_cookie(request, call_next):
    """If incoming URL has ?ref=CODE, set zv_ref cookie on the response."""
    code = (request.query_params.get("ref") or "").upper().strip()
    response = await call_next(request)
    if code and len(code) <= 32 and code.isalnum():
        try:
            from app.affiliates import _config as _aff_cfg
            days = int(_aff_cfg().get("cookie_days", 90))
        except Exception:
            days = 90
        response.set_cookie(
            "zv_ref", code, max_age=days*24*60*60,
            httponly=False, samesite="lax", path="/",
        )
    return response
# === end affiliates middleware ===


# Import the working modules
from app.accommodations_config import (
    get_accommodation, get_all_accommodations, get_zones, get_current_season, SEASON_CONFIG
)
from app.booking_models import (
    create_booking, get_booking, list_bookings, update_booking, delete_booking,
    check_availability, get_booked_dates, get_calendar_data,
)
from app.ical_sync import (
    add_ical_source, list_ical_sources, delete_ical_source,
    sync_ical_source, sync_all_ical, generate_ical_export,
    add_blocked_dates, remove_blocked_dates
)
from app.inquiries import router as inquiries_router
from app.zen_pass import router as zen_pass_router, init_pass_db, start_followup_engine
from app.affiliates import router as affiliates_router, try_convert as affiliates_convert
from app.team import router as team_router, compute_digest as team_digest
from app.wallet import router as wallet_router
from app.receipts_admin import router as receipts_admin_router
from app.submissions_admin import router as submissions_admin_router
from app.invoices import router as invoices_router
from app.cockpit_hub import router as cockpit_router

app.include_router(inquiries_router, prefix="/api/inquiries", tags=["Inquiries"])
app.include_router(zen_pass_router, tags=["Zen Pass"])
app.include_router(affiliates_router, prefix="/api/affiliates", tags=["Affiliates"])
app.include_router(team_router, prefix="/api/team", tags=["Team"])
app.include_router(wallet_router, prefix="/api/wallet", tags=["Wallet"])
app.include_router(receipts_admin_router, tags=["Admin Receipts"])
app.include_router(submissions_admin_router, tags=["Admin Submissions"])
app.include_router(invoices_router, tags=["Admin Invoices"])
app.include_router(cockpit_router, tags=["Cockpit"])

# === Cockpit static page (restored 2026-05-23) ===
@app.get("/cockpit", response_class=HTMLResponse, include_in_schema=False)
async def _cockpit_page():
    p = FRONTEND_DIR / "cockpit.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return HTMLResponse("cockpit.html missing", status_code=404)



# ─── Health ───────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "zen-village", "version": "2.0.0", "ts": datetime.utcnow().isoformat()}


@app.get("/api/status")
async def api_status():
    return {"status": "operational", "booking_api": True, "season": get_current_season()}


# ─── Ops Summary (NocoDB + local team digest) ─────────────────────────────
_OPS_NOCODB_URL = os.environ.get("NOCODB_URL", "http://127.0.0.1:8080").rstrip("/")
_OPS_NOCODB_TOKEN = os.environ.get("NOCODB_API_TOKEN", "")
_OPS_TABLES = {
    "applications": os.environ.get("NOCODB_TABLE_ID", ""),
    "inquiries": os.environ.get("NOCODB_INQUIRIES_TABLE_ID", ""),
    "bookings": os.environ.get("NOCODB_BOOKINGS_TABLE_ID", ""),
    "partners": os.environ.get("NOCODB_PARTNERS_TABLE_ID", ""),
    "commissions": os.environ.get("NOCODB_COMMISSIONS_TABLE_ID", ""),
}
_OPS_DATA_DIR = BASE_DIR / "data"
_OPS_COMMISSIONS_FILE = _OPS_DATA_DIR / "commissions.json"


def _ops_noco_records(table_id: str, *, limit: int = 100, sort: str = "-CreatedAt", fields: str = "") -> dict:
    if not (_OPS_NOCODB_TOKEN and table_id):
        return {}
    q = {"limit": str(max(1, min(limit, 500))), "sort": sort}
    if fields:
        q["fields"] = fields
    url = f"{_OPS_NOCODB_URL}/api/v2/tables/{table_id}/records?{_uparse.urlencode(q)}"
    try:
        req = _ureq.Request(url, headers={"xc-token": _OPS_NOCODB_TOKEN})
        with _ureq.urlopen(req, timeout=7) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        logger.warning("ops noco read failed table=%s: %s", table_id, e)
        return {}


def _ops_noco_total(table_id: str) -> int:
    d = _ops_noco_records(table_id, limit=1)
    return int(((d.get("pageInfo") or {}).get("totalRows")) or 0)


def _ops_local_rows(path: Path) -> list[dict]:
    try:
        if not path.exists():
            return []
        raw = json.loads(path.read_text())
        return list(raw.values()) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
    except Exception as e:
        logger.warning("ops local read failed path=%s: %s", path, e)
        return []


def _vdate(row: dict, *keys: str) -> str:
    """Return YYYY-MM-DD from first populated field in keys."""
    for k in keys:
        v = str(row.get(k) or "").strip()
        if len(v) >= 10:
            return v[:10]
    return ""


@app.get("/api/ops/summary")
async def ops_summary(days: int = Query(7, ge=1, le=90)):
    """Operational summary for the Telegram brain.

    Pulls from:
      - NocoDB (bookings/inquiries/applications/partners/commissions)
      - local team digest (/api/team equivalent)
    """
    cutoff = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
    team = team_digest()

    connected = bool(_OPS_NOCODB_TOKEN)
    totals = {k: _ops_noco_total(tid) for k, tid in _OPS_TABLES.items() if tid}

    # Recent windows
    inq_rows = (_ops_noco_records(_OPS_TABLES.get("inquiries", ""), limit=300).get("list") or []) if connected else []
    app_rows = (_ops_noco_records(_OPS_TABLES.get("applications", ""), limit=300).get("list") or []) if connected else []
    book_rows = (_ops_noco_records(_OPS_TABLES.get("bookings", ""), limit=300).get("list") or []) if connected else []
    com_rows = (_ops_noco_records(_OPS_TABLES.get("commissions", ""), limit=500).get("list") or []) if connected else []

    recent_inq = [r for r in inq_rows if _vdate(r, "SubmittedAt", "CreatedAt", "created_at") >= cutoff]
    recent_apps = [r for r in app_rows if _vdate(r, "SubmittedAt", "CreatedAt", "created_at") >= cutoff]
    recent_books = [r for r in book_rows if _vdate(r, "CreatedAt", "created_at", "StartDate", "CheckIn") >= cutoff]

    by_type: dict[str, int] = {}
    for r in recent_inq:
        t = (r.get("Type") or r.get("inquiry_type") or "Other").strip() or "Other"
        by_type[t] = by_type.get(t, 0) + 1

    # NocoDB commission mirror (can lag if sync/update fails)
    noco_pending_total = 0.0
    noco_paid_recent_total = 0.0
    for c in com_rows:
        amt = float(c.get("CommissionAmount") or c.get("commission_amount") or 0)
        status = str(c.get("Status") or c.get("status") or "").lower()
        if status == "pending":
            noco_pending_total += amt
        if status == "paid" and _vdate(c, "PaidAt", "paid_at", "Timestamp", "timestamp", "CreatedAt") >= cutoff:
            noco_paid_recent_total += amt

    # Local commissions are the authoritative source for payout status.
    local_com_rows = _ops_local_rows(_OPS_COMMISSIONS_FILE)
    local_status_counts: dict[str, int] = {}
    local_pending_total = 0.0
    local_paid_recent_total = 0.0
    local_pending_count = 0
    for c in local_com_rows:
        status = str(c.get("status") or "").lower() or "unknown"
        local_status_counts[status] = local_status_counts.get(status, 0) + 1
        amt = float(c.get("commission_amount") or 0)
        if status == "pending":
            local_pending_total += amt
            local_pending_count += 1
        if status == "paid" and _vdate(c, "paid_at", "timestamp", "created_at") >= cutoff:
            local_paid_recent_total += amt

    comm_source = "local_json" if local_com_rows else ("nocodb_mirror" if connected else "unavailable")
    pending_total = local_pending_total if comm_source == "local_json" else noco_pending_total
    paid_recent_total = local_paid_recent_total if comm_source == "local_json" else noco_paid_recent_total
    warnings: list[str] = []
    if comm_source == "local_json" and connected and abs(local_pending_total - noco_pending_total) > 0.01:
        warnings.append(
            "Commission mirror mismatch: using local commissions.json as source of truth; "
            "NocoDB commission table appears stale."
        )

    return {
        "window_days": days,
        "cutoff_date": cutoff,
        "source": {
            "nocodb_connected": connected,
            "nocodb_url": _OPS_NOCODB_URL if connected else "",
            "tables_configured": {k: bool(v) for k, v in _OPS_TABLES.items()},
        },
        "team": team,
        "nocodb": {
            "totals": {
                "bookings": totals.get("bookings", 0),
                "inquiries": totals.get("inquiries", 0),
                "applications": totals.get("applications", 0),
                "partners": totals.get("partners", 0),
                "commissions": totals.get("commissions", 0),
            },
            "recent": {
                "bookings": len(recent_books),
                "inquiries": len(recent_inq),
                "applications": len(recent_apps),
            },
            "inquiries_by_type": by_type,
            "commissions": {
                "source": comm_source,
                "pending_total": round(pending_total, 2),
                "paid_recent_total": round(paid_recent_total, 2),
                "pending_count": int(local_pending_count if comm_source == "local_json" else 0),
                "status_counts": local_status_counts if comm_source == "local_json" else {},
                "mirror_pending_total": round(noco_pending_total, 2) if connected else 0.0,
            },
        },
        "warnings": warnings,
    }


# ─── Accommodations ──────────────────────────────────────
@app.get("/api/bookings/accommodations")
async def list_accommodations():
    season = get_current_season()
    accs = get_all_accommodations()
    enriched = []
    for a in accs:
        item = {**a, "current_season": season}
        if season == "green":
            item["current_nightly"] = a.get("green_nightly", a["nightly_rate"])
            item["current_weekly"] = a.get("green_weekly", a["weekly_rate"])
            item["current_monthly"] = a.get("green_monthly", a["monthly_rate"])
        else:
            item["current_nightly"] = a["nightly_rate"]
            item["current_weekly"] = a["weekly_rate"]
            item["current_monthly"] = a["monthly_rate"]
        enriched.append(item)
    return {"accommodations": enriched, "zones": get_zones(), "season": season}


@app.get("/api/bookings/accommodations/{acc_id}")
async def get_single_accommodation(acc_id: str):
    acc = get_accommodation(acc_id)
    if not acc:
        raise HTTPException(404, "Accommodation not found")
    return acc


# ─── Availability ─────────────────────────────────────────
@app.get("/api/bookings/availability/{structure_id}")
async def check_structure_availability(
    structure_id: str,
    check_in: str = Query(...),
    check_out: str = Query(...),
):
    acc = get_accommodation(structure_id)
    if not acc:
        raise HTTPException(404, "Accommodation not found")
    try:
        in_d = date.fromisoformat(check_in)
        out_d = date.fromisoformat(check_out)
        if out_d <= in_d:
            raise HTTPException(400, "Check-out must be after check-in")
    except ValueError:
        raise HTTPException(400, "Invalid date format")

    available = check_availability(structure_id, check_in, check_out)
    nights = (out_d - in_d).days
    season = get_current_season()
    rate = acc.get("green_nightly", acc["nightly_rate"]) if season == "green" else acc["nightly_rate"]
    subtotal = rate * nights

    return {
        "structure_id": structure_id,
        "accommodation": acc["name"],
        "check_in": check_in,
        "check_out": check_out,
        "nights": nights,
        "available": available,
        "season": season,
        "pricing": {
            "nightly_rate": rate,
            "cleaning_fee": acc["cleaning_fee"],
            "subtotal": subtotal,
            "total": subtotal + acc["cleaning_fee"],
        },
    }


@app.get("/api/bookings/availability/{structure_id}/dates")
async def get_unavailable_dates(
    structure_id: str,
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    booked = get_booked_dates(structure_id, start_date, end_date)
    return {"structure_id": structure_id, "unavailable_dates": booked}


# ─── Booking CRUD ─────────────────────────────────────────
from pydantic import BaseModel, EmailStr


class BookingCreate(BaseModel):
    structure_id: str
    guest_name: str
    guest_email: EmailStr
    guest_phone: str = ""
    guest_country: str = "Unknown"
    check_in: str
    check_out: str
    special_requests: str = ""
    source: str = "direct"
    partner_code: Optional[str] = None
    discount_percent: float = 0


class BookingUpdate(BaseModel):
    status: Optional[str] = None
    payment_status: Optional[str] = None
    notes: Optional[str] = None
    special_requests: Optional[str] = None


@app.post("/api/bookings/")
async def create_new_booking(data: BookingCreate):
    acc = get_accommodation(data.structure_id)
    if not acc:
        raise HTTPException(404, "Accommodation not found")
    if not check_availability(data.structure_id, data.check_in, data.check_out):
        raise HTTPException(409, "Dates not available")

    season = get_current_season()
    rate = acc.get("green_nightly", acc["nightly_rate"]) if season == "green" else acc["nightly_rate"]

    bdata = data.model_dump()
    bdata["nightly_rate"] = rate
    bdata["cleaning_fee"] = acc["cleaning_fee"]
    booking = create_booking(bdata)
    try:
        if booking:
            _sync_booking_to_nocodb(booking.__dict__, accommodation_title=acc.get("title") or acc.get("name"))
            # affiliates conversion hook
            try:
                bd = booking.__dict__
                affiliates_convert(
                    partner_code=bd.get("partner_code") or "",
                    booking_type="stay",
                    booking_amount=float(bd.get("total_amount") or 0),
                    guest_email=bd.get("guest_email") or "",
                    source_id=str(bd.get("id") or ""),
                    booking_details=(acc.get("title") or acc.get("name") or "") + " " + str(bd.get("check_in") or "") + " -> " + str(bd.get("check_out") or ""),
                )
            except Exception as _e:
                logger.warning(f"affiliates booking hook failed: {_e}")
    except Exception as e:
        logger.warning(f"nocodb booking sync raised (caught): {e}")
    return {"message": "Booking created", "booking": booking.__dict__ if booking else None}


@app.get("/api/bookings/")
async def get_all_bookings(
    status: Optional[str] = None,
    source: Optional[str] = None,
    structure_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = Query(default=200, le=500),
):
    bookings = list_bookings(
        structure_id=structure_id, status=status, source=source,
        from_date=from_date, to_date=to_date, limit=limit,
    )
    return {"count": len(bookings), "bookings": [b.__dict__ for b in bookings]}


@app.get("/api/bookings/calendar")
async def calendar_view(
    month: int = Query(default=None, ge=1, le=12),
    year: int = Query(default=None, ge=2020, le=2030),
):
    now = datetime.now()
    month = month or now.month
    year = year or now.year
    cal = get_calendar_data(year, month)
    accs = get_all_accommodations()
    return {"month": month, "year": year, "accommodations": accs, **cal}


@app.get("/api/bookings/{booking_id}")
async def get_single_booking(booking_id: str):
    b = get_booking(booking_id)
    if not b:
        raise HTTPException(404, "Booking not found")
    return b.__dict__


@app.put("/api/bookings/{booking_id}")
async def update_single_booking(booking_id: str, updates: BookingUpdate):
    b = get_booking(booking_id)
    if not b:
        raise HTTPException(404, "Booking not found")
    udata = {k: v for k, v in updates.model_dump().items() if v is not None}
    updated = update_booking(booking_id, udata)
    return {"message": "Booking updated", "booking": updated.__dict__ if updated else None}


@app.delete("/api/bookings/{booking_id}")
async def cancel_booking(booking_id: str):
    b = get_booking(booking_id)
    if not b:
        raise HTTPException(404, "Booking not found")
    update_booking(booking_id, {"status": "cancelled"})
    return {"message": "Booking cancelled", "booking_id": booking_id}


# ─── Blocked Dates ────────────────────────────────────────
class BlockedDatesCreate(BaseModel):
    structure_id: str
    start_date: str
    end_date: str
    reason: str = ""


@app.post("/api/bookings/blocked")
async def block_dates(data: BlockedDatesCreate):
    acc = get_accommodation(data.structure_id)
    if not acc:
        raise HTTPException(404, "Accommodation not found")
    result = add_blocked_dates(data.structure_id, data.start_date, data.end_date, data.reason)
    return result


@app.delete("/api/bookings/blocked/{block_id}")
async def unblock_dates(block_id: str):
    if remove_blocked_dates(block_id):
        return {"message": "Blocked dates removed"}
    raise HTTPException(404, "Not found")


# ─── iCal ─────────────────────────────────────────────────
@app.get("/api/bookings/ical/export")
async def ical_export(structure_id: Optional[str] = None):
    ical = generate_ical_export(structure_id)
    return Response(content=ical, media_type="text/calendar",
                    headers={"Content-Disposition": "attachment; filename=zenvillage.ics"})


# ═══════════════════════════════════════════════════════════
# BRAIN — Receives routed AI signals and takes real actions
# ═══════════════════════════════════════════════════════════

BRAIN_DATA_DIR = BASE_DIR / "data" / "brain"

@app.on_event("startup")
async def init_brain():
    BRAIN_DATA_DIR.mkdir(parents=True, exist_ok=True)
    (BRAIN_DATA_DIR / "signals").mkdir(exist_ok=True)
    (BRAIN_DATA_DIR / "decisions").mkdir(exist_ok=True)
    (BRAIN_DATA_DIR / "actions").mkdir(exist_ok=True)
    logger.info("Zen Village Brain initialized")
    init_pass_db()
    logger.info("Zen Pass DB initialized")
    start_followup_engine()
    logger.info("Zen Pass followup engine started")


@app.post("/api/brain/signal")
async def receive_signal(request: Request):
    """Receive a routed signal from FP Index and take action.

    This is the endpoint that makes Zen Village a brain, not just a booking site.
    When the scanner detects something relevant, it routes here.
    The brain decides what to do and does it.
    """
    payload = await request.json()
    signal_type = payload.get("type", "general")
    signal_id = payload.get("signal_id", f"sig-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
    title = payload.get("title", "")
    summary = payload.get("summary", "")
    impact = payload.get("impact", 0)
    suggested_action = payload.get("suggested_action", "")

    signal_file = BRAIN_DATA_DIR / "signals" / f"{signal_id}.json"
    signal_file.write_text(json.dumps({
        **payload,
        "received_at": datetime.utcnow().isoformat(),
        "processed": False,
    }, indent=2))

    actions_taken = []

    if signal_type == "model_drop":
        actions_taken.extend(await _brain_handle_model_drop(signal_id, title, summary, impact))

    elif signal_type == "pricing_change":
        actions_taken.extend(await _brain_handle_pricing(signal_id, title, summary, impact))

    elif signal_type == "trend":
        actions_taken.extend(await _brain_handle_trend(signal_id, title, summary, impact))

    else:
        decision = {
            "signal_id": signal_id,
            "type": signal_type,
            "decision": "logged",
            "reason": f"Signal noted for review: {title[:100]}",
            "timestamp": datetime.utcnow().isoformat(),
        }
        (BRAIN_DATA_DIR / "decisions" / f"{signal_id}.json").write_text(
            json.dumps(decision, indent=2)
        )
        actions_taken.append({"action": "logged", "detail": "Signal stored for review"})

    signal_file.write_text(json.dumps({
        **payload,
        "received_at": datetime.utcnow().isoformat(),
        "processed": True,
        "actions_taken": actions_taken,
    }, indent=2))

    logger.info(f"[BRAIN] Signal {signal_type}: '{title[:60]}' → {len(actions_taken)} actions")

    return {
        "status": "processed",
        "signal_id": signal_id,
        "signal_type": signal_type,
        "actions_taken": actions_taken,
    }


async def _brain_handle_model_drop(signal_id: str, title: str, summary: str, impact: float) -> list:
    """A new AI model dropped. What does Zen Village do?

    Real actions:
    1. Log a tech review decision (which tools/workshops might change)
    2. If high impact, update the retreats page note about available AI
    3. Queue a pricing review if it affects costs
    """
    actions = []

    decision = {
        "signal_id": signal_id,
        "type": "model_drop",
        "title": title,
        "impact": impact,
        "decision": "tech_review_queued",
        "reason": f"New model may affect retreat workshops or internal tooling",
        "timestamp": datetime.utcnow().isoformat(),
    }

    if impact >= 0.8:
        decision["priority"] = "high"
        decision["auto_action"] = "Update retreat tech offerings page"

        retreats_note = BRAIN_DATA_DIR / "actions" / f"retreats-update-{signal_id}.json"
        retreats_note.write_text(json.dumps({
            "action": "update_retreat_tech",
            "signal": title,
            "note": f"High-impact model detected: {title}. Review retreat AI workshop content.",
            "suggested_update": summary[:300],
            "created_at": datetime.utcnow().isoformat(),
            "status": "pending",
        }, indent=2))
        actions.append({
            "action": "retreat_tech_review",
            "detail": f"High-impact model: queued retreat content update",
            "priority": "high",
        })

    (BRAIN_DATA_DIR / "decisions" / f"{signal_id}.json").write_text(
        json.dumps(decision, indent=2)
    )
    actions.append({"action": "tech_review_queued", "detail": title[:100]})

    return actions


async def _brain_handle_pricing(signal_id: str, title: str, summary: str, impact: float) -> list:
    """AI pricing changed. Review whether Zen Village costs are affected."""
    actions = []

    season = get_current_season()
    accs = get_all_accommodations()
    current_pricing = {a["name"]: a.get("base_price", 0) for a in accs}

    decision = {
        "signal_id": signal_id,
        "type": "pricing_review",
        "title": title,
        "current_season": season,
        "current_accommodations": len(accs),
        "decision": "pricing_review_logged",
        "reason": f"AI pricing signal may affect retreat tool costs",
        "current_pricing_snapshot": current_pricing,
        "timestamp": datetime.utcnow().isoformat(),
    }

    (BRAIN_DATA_DIR / "decisions" / f"{signal_id}.json").write_text(
        json.dumps(decision, indent=2)
    )
    actions.append({
        "action": "pricing_review",
        "detail": f"Current season: {season}, {len(accs)} accommodations tracked",
    })

    return actions


async def _brain_handle_trend(signal_id: str, title: str, summary: str, impact: float) -> list:
    """Community trend detected. Consider for retreat programming."""
    actions = []

    decision = {
        "signal_id": signal_id,
        "type": "programming_review",
        "title": title,
        "decision": "trend_noted",
        "reason": f"Community interest signal for retreat content planning",
        "timestamp": datetime.utcnow().isoformat(),
    }

    if impact >= 0.6:
        decision["suggestion"] = f"Consider adding workshop/session related to: {title[:100]}"
        actions.append({
            "action": "workshop_suggestion",
            "detail": f"Trend with impact {impact:.2f}: consider for programming",
        })

    (BRAIN_DATA_DIR / "decisions" / f"{signal_id}.json").write_text(
        json.dumps(decision, indent=2)
    )
    actions.append({"action": "trend_logged", "detail": title[:100]})

    return actions


@app.get("/api/brain/status")
async def brain_status():
    """What has the brain done? Show signals received, decisions made, actions taken."""
    signals_dir = BRAIN_DATA_DIR / "signals"
    decisions_dir = BRAIN_DATA_DIR / "decisions"
    actions_dir = BRAIN_DATA_DIR / "actions"

    signal_count = len(list(signals_dir.glob("*.json"))) if signals_dir.exists() else 0
    decision_count = len(list(decisions_dir.glob("*.json"))) if decisions_dir.exists() else 0
    action_count = len(list(actions_dir.glob("*.json"))) if actions_dir.exists() else 0

    recent_signals = []
    if signals_dir.exists():
        files = sorted(signals_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)[:10]
        for f in files:
            try:
                data = json.loads(f.read_text())
                recent_signals.append({
                    "id": data.get("signal_id", f.stem),
                    "type": data.get("type", "unknown"),
                    "title": data.get("title", "")[:80],
                    "processed": data.get("processed", False),
                    "actions": len(data.get("actions_taken", [])),
                    "received_at": data.get("received_at", ""),
                })
            except Exception:
                pass

    pending_actions = []
    if actions_dir.exists():
        for f in sorted(actions_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)[:10]:
            try:
                data = json.loads(f.read_text())
                if data.get("status") == "pending":
                    pending_actions.append({
                        "action": data.get("action", "unknown"),
                        "signal": data.get("signal", "")[:80],
                        "created_at": data.get("created_at", ""),
                    })
            except Exception:
                pass

    return {
        "brain": "zen_village",
        "status": "active",
        "signals_received": signal_count,
        "decisions_made": decision_count,
        "actions_queued": action_count,
        "pending_actions": pending_actions,
        "recent_signals": recent_signals,
    }


@app.get("/api/brain/decisions")
async def brain_decisions():
    """List all decisions the brain has made."""
    decisions_dir = BRAIN_DATA_DIR / "decisions"
    if not decisions_dir.exists():
        return {"decisions": []}

    decisions = []
    for f in sorted(decisions_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)[:50]:
        try:
            decisions.append(json.loads(f.read_text()))
        except Exception:
            pass

    return {"count": len(decisions), "decisions": decisions}


# ─── Static Pages ─────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def homepage():
    return FileResponse(FRONTEND_DIR / "index.html", media_type="text/html")


@app.get("/book", response_class=HTMLResponse)
@app.get("/booking", response_class=HTMLResponse)
async def booking_page():
    p = FRONTEND_DIR / "booking.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return RedirectResponse("/")


@app.get("/partners", response_class=HTMLResponse)
async def partners_page():
    p = FRONTEND_DIR / "partners.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return RedirectResponse("/")


@app.get("/who", response_class=HTMLResponse)
async def who_page():
    p = FRONTEND_DIR / "who.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return RedirectResponse("/")


@app.get("/inquire", response_class=HTMLResponse)
async def inquire_page():
    p = FRONTEND_DIR / "inquire.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return RedirectResponse("/")


@app.get("/reminder", response_class=HTMLResponse)
async def reminder_page():
    p = FRONTEND_DIR / "reminder.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return RedirectResponse("/")


@app.get("/retreats", response_class=HTMLResponse)
async def retreats_index_page():
    p = FRONTEND_DIR / "retreats-index.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    legacy = FRONTEND_DIR / "retreats.html"
    if legacy.exists():
        return FileResponse(legacy, media_type="text/html")
    return RedirectResponse("/host")


@app.get("/coherent", response_class=HTMLResponse)
@app.get("/retreat", response_class=HTMLResponse)
@app.get("/fp-retreat", response_class=HTMLResponse)
@app.get("/coherent-retreat", response_class=HTMLResponse)
async def coherent_page():
    p = FRONTEND_DIR / "coherent.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return RedirectResponse("/")


@app.get("/events", response_class=HTMLResponse)
async def events_page():
    p = FRONTEND_DIR / "events.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return RedirectResponse("/")


@app.get("/peace", response_class=HTMLResponse)
@app.get("/world-peace", response_class=HTMLResponse)
@app.get("/world-peace-weekend", response_class=HTMLResponse)
async def peace_page():
    p = FRONTEND_DIR / "peace.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return RedirectResponse("/events")


@app.get("/peace/qr.png")
@app.get("/peace/qr")
async def peace_qr(ref: str = "", size: int = 10):
    """QR code that resolves to the /peace contribution page.
    Optional ?ref=ATLAS adds partner attribution to the cookie.
    Optional ?size=N controls box size (4-20, default 10)."""
    import qrcode
    import io
    from fastapi.responses import StreamingResponse

    size = max(4, min(int(size or 10), 20))
    base = "https://zenvillagecr.com/peace"
    ref_clean = "".join(ch for ch in (ref or "").upper() if ch.isalnum() or ch in "_-")[:40]
    target = f"{base}?ref={ref_clean}" if ref_clean else base
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=size,
        border=2,
    )
    qr.add_data(target)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a2e1a", back_color="#faf9f5")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="image/png",
        headers={"Cache-Control": "public, max-age=300"},
    )


@app.get("/peace/poster", response_class=HTMLResponse)
async def peace_poster():
    p = FRONTEND_DIR / "peace-poster.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return RedirectResponse("/peace")


@app.get("/support", response_class=HTMLResponse)
@app.get("/donate", response_class=HTMLResponse)
async def support_page():
    p = FRONTEND_DIR / "support.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return RedirectResponse("/")


@app.get("/membership", response_class=HTMLResponse)
async def membership_page():
    p = FRONTEND_DIR / "membership.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return RedirectResponse("/")


@app.get("/wallet", response_class=HTMLResponse)
async def wallet_page():
    p = FRONTEND_DIR / "wallet.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return RedirectResponse("/")


@app.get("/wallet/new", response_class=HTMLResponse)
async def wallet_new_page():
    p = FRONTEND_DIR / "wallet-new.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return RedirectResponse("/wallet")


@app.get("/store", response_class=HTMLResponse)
async def store_page():
    p = FRONTEND_DIR / "store.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return RedirectResponse("/")


@app.get("/menu", response_class=HTMLResponse)
async def menu_page():
    p = FRONTEND_DIR / "menu.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return RedirectResponse("/store")


@app.get("/buy", response_class=HTMLResponse)
async def buy_page():
    p = FRONTEND_DIR / "buy.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return RedirectResponse("/store")


@app.get("/admin/items", response_class=HTMLResponse)
async def admin_items_page():
    p = FRONTEND_DIR / "admin-items.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return HTMLResponse("<h1>Admin · Items</h1><p>Page not found</p>", status_code=404)


@app.get("/admin/topups", response_class=HTMLResponse)
async def admin_topups_page():
    p = FRONTEND_DIR / "admin-topups.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return HTMLResponse("<h1>Admin · Top-ups</h1><p>Page not found</p>", status_code=404)


@app.get("/admin/receipts", response_class=HTMLResponse)
async def admin_receipts_page():
    p = FRONTEND_DIR / "receipts-admin.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return HTMLResponse("<h1>Accounting · Receipts</h1><p>Page not found</p>", status_code=404)


@app.get("/booking-admin", response_class=HTMLResponse)
async def booking_admin():
    p = FRONTEND_DIR / "booking-admin.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return HTMLResponse("<h1>Booking Admin</h1><p>Page not found</p>", status_code=404)



# Static assets for /apply pages
@app.get("/apply-shared.css")
async def apply_shared_css():
    p = FRONTEND_DIR / "apply-shared.css"
    if p.exists():
        return FileResponse(p, media_type="text/css")
    raise HTTPException(status_code=404)


@app.get("/apply-submit.js")
async def apply_submit_js():
    p = FRONTEND_DIR / "apply-submit.js"
    if p.exists():
        return FileResponse(p, media_type="application/javascript")
    raise HTTPException(status_code=404)


# === APPLICATION LANES (Practitioners / Artists / Volunteers / Creators) ===

APPLICATIONS_DIR = BASE_DIR / "data" / "applications"
APPLICATIONS_DIR.mkdir(parents=True, exist_ok=True)

VALID_LANES = {"practitioner", "artist", "volunteer", "creator", "work-exchange"}


# === TELEGRAM NOTIFICATIONS FOR APPLICATIONS ===
import os, asyncio, urllib.parse, urllib.request

_TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
_TG_ADMIN_IDS = [
    int(x.strip()) for x in (os.environ.get("ZV_TG_ADMIN_IDS", "")).split(",")
    if x.strip().isdigit()
]
_TG_NOTIFY_LABEL = os.environ.get("ZV_NOTIFY_LABEL", "ZenVillage")


def _tg_send_sync(chat_id: int, text: str, reply_markup: dict = None) -> None:
    if not _TG_TOKEN:
        return
    try:
        if reply_markup:
            payload = {
                "chat_id": chat_id,
                "text": text[:4000],
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "reply_markup": reply_markup,
            }
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{_TG_TOKEN}/sendMessage",
                data=json.dumps(payload).encode(),
                method="POST",
                headers={"Content-Type": "application/json"},
            )
        else:
            data = urllib.parse.urlencode({
                "chat_id": chat_id,
                "text": text[:4000],
                "disable_web_page_preview": "true",
            }).encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{_TG_TOKEN}/sendMessage",
                data=data,
                method="POST",
            )
        urllib.request.urlopen(req, timeout=8).read()
    except Exception as e:
        logger.warning(f"telegram notify failed for {chat_id}: {e}")


def _notify_application(lane: str, data: dict) -> None:
    if not _TG_TOKEN or not _TG_ADMIN_IDS:
        return
    name = (data.get("name") or data.get("full_name") or data.get("nickname") or "Anonymous").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    location = (data.get("location") or data.get("current_location") or "").strip()
    intent = (
        data.get("intentions")
        or data.get("why_zen_village")
        or data.get("story")
        or data.get("offering")
        or data.get("contribution")
        or ""
    ).strip()
    intent = (intent[:300] + "...") if len(intent) > 300 else intent
    lane_label = lane.replace("-", " ").title()
    body_lines = [
        f"<b>📥 New {lane_label} Application</b>",
        f"From: <b>{name}</b>",
    ]
    if email:
        body_lines.append(f"Email: <code>{email}</code>")
    if phone:
        body_lines.append(f"Phone: <code>{phone}</code>")
    if location:
        body_lines.append(f"Location: {location}")
    if intent:
        body_lines.append("")
        body_lines.append(f"<i>{intent}</i>")
    text = "\n".join(body_lines)

    # Build same submission key the cockpit uses so the buttons can mark
    # it contacted/closed.
    try:
        from app.telegram_send import submission_action_keyboard
        submission_key = "|".join([
            "application",
            lane,
            email.lower(),
            (data.get("submitted_at") or "")[:19],
        ])
        keyboard = submission_action_keyboard(submission_key)
    except Exception:
        keyboard = None

    for cid in _TG_ADMIN_IDS:
        _tg_send_sync(cid, text, reply_markup=keyboard)


# === NocoDB sync (Applications CRM) ============================================
# Mirrors every accepted application into NocoDB so ops can sort/tag/comment in
# a real CRM. JSON files remain the canonical store; NocoDB is a derived view.

_NOCODB_URL = os.environ.get("NOCODB_URL", "http://127.0.0.1:8080").rstrip("/")
_NOCODB_TOKEN = os.environ.get("NOCODB_API_TOKEN", "")
_NOCODB_TABLE_ID = os.environ.get("NOCODB_TABLE_ID", "")


def _sync_application_to_nocodb(lane: str, data: dict, app_id: str) -> None:
    """Upsert one application row into NocoDB. Never raises."""
    if not (_NOCODB_TOKEN and _NOCODB_TABLE_ID):
        return
    try:
        offering = data.get("offering") or data.get("contribution") or data.get("intentions") or ""
        headline = (offering[:140] + "…") if len(offering) > 140 else offering
        notes_parts = []
        for k in ("intentions", "why_zen_village", "story", "offering", "contribution",
                  "experience", "skills", "availability", "duration", "dates",
                  "location", "current_location", "instagram", "website"):
            v = data.get(k)
            if v:
                notes_parts.append(f"{k}: {v}")
        notes = "\n".join(notes_parts)[:8000]
        tags = ",".join(t for t in [
            data.get("modality") or data.get("art_form") or data.get("medium"),
            data.get("experience_level"),
        ] if t)
        payload = {
            "ApplicationId": app_id,
            "Lane": lane,
            "Status": "New",
            "Name": (data.get("name") or data.get("full_name") or data.get("nickname") or "").strip()[:255],
            "Email": (data.get("email") or "").strip()[:255],
            "Phone": (data.get("phone") or "").strip()[:64],
            "Telegram": (data.get("telegram") or data.get("telegram_handle") or "").strip()[:128],
            "Country": (data.get("country") or data.get("nationality") or "").strip()[:128],
            "Headline": headline,
            "Notes": notes,
            "Tags": tags[:255],
            "RawPayload": json.dumps(data, ensure_ascii=False, default=str)[:8000],
            "SubmittedAt": data.get("submitted_at") or datetime.utcnow().isoformat(),
            "Source": data.get("_source") or "/api/applications",
        }
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{_NOCODB_URL}/api/v2/tables/{_NOCODB_TABLE_ID}/records",
            data=body, method="POST",
            headers={
                "xc-token": _NOCODB_TOKEN,
                "Content-Type": "application/json",
            },
        )
        urllib.request.urlopen(req, timeout=5).read()
    except Exception as e:
        logger.warning(f"nocodb sync failed for {app_id}: {e}")


_NOCODB_BOOKINGS_TABLE = os.environ.get("NOCODB_BOOKINGS_TABLE_ID", "")


def _sync_booking_to_nocodb(booking: dict, accommodation_title: str = None) -> None:
    """Mirror booking into NocoDB. Never raises."""
    if not (_NOCODB_TOKEN and _NOCODB_BOOKINGS_TABLE):
        return
    try:
        status = (booking.get("status") or "pending").lower()
        status_map = {"pending": "Pending", "confirmed": "Confirmed", "checked_in": "CheckedIn",
                      "checkedin": "CheckedIn", "completed": "Completed", "cancelled": "Cancelled",
                      "canceled": "Cancelled", "hold": "Hold"}
        payment_status = (booking.get("payment_status") or "pending").lower()
        source = (booking.get("source") or "direct").lower()
        if source not in ("direct", "airbnb", "booking.com", "partner"):
            source = "other"
        payload = {
            "BookingId": booking.get("id") or "",
            "Status": status_map.get(status, "Pending"),
            "PaymentStatus": payment_status if payment_status in ("pending","partial","paid","refunded") else "pending",
            "Source": source,
            "GuestName": (booking.get("guest_name") or "")[:255],
            "Email": (booking.get("guest_email") or "")[:255],
            "Phone": (booking.get("guest_phone") or "")[:64],
            "Country": (booking.get("guest_country") or "")[:128],
            "Accommodation": (accommodation_title or booking.get("structure_id") or "")[:128],
            "CheckIn": booking.get("check_in") or None,
            "CheckOut": booking.get("check_out") or None,
            "Nights": booking.get("nights") or 0,
            "NightlyRate": booking.get("nightly_rate") or 0,
            "CleaningFee": booking.get("cleaning_fee") or 0,
            "TotalAmount": booking.get("total_amount") or 0,
            "PartnerCode": (booking.get("partner_code") or "")[:64],
            "SpecialRequests": (booking.get("special_requests") or "")[:8000],
            "Notes": (booking.get("notes") or "")[:8000],
            "CreatedAt": booking.get("created_at") or datetime.utcnow().isoformat(),
        }
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{_NOCODB_URL}/api/v2/tables/{_NOCODB_BOOKINGS_TABLE}/records",
            data=body, method="POST",
            headers={"xc-token": _NOCODB_TOKEN, "Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5).read()
    except Exception as e:
        logger.warning(f"nocodb booking sync failed for {booking.get('id','?')}: {e}")
# === end NocoDB sync ============================================================


# Gateway page
@app.get("/apply", response_class=HTMLResponse)
async def apply_gateway():
    p = FRONTEND_DIR / "apply.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return HTMLResponse("<h1>Apply</h1><p>Page not found</p>", status_code=404)


# Lane-specific pages
@app.get("/apply/{lane}", response_class=HTMLResponse)
async def apply_lane_page(lane: str):
    if lane not in VALID_LANES:
        return RedirectResponse(url="/apply", status_code=302)
    p = FRONTEND_DIR / f"apply-{lane}.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return HTMLResponse(f"<h1>Apply · {lane}</h1><p>Page not found</p>", status_code=404)


# Honeypot field name. Real users don't see it, bots auto-fill it.
HONEYPOT_FIELD = "website_url_extra"


def _looks_like_spam(data: dict) -> bool:
    """Cheap signals: honeypot filled, message all-URL, message > 5 URLs, etc."""
    if (data.get(HONEYPOT_FIELD) or "").strip():
        return True
    msg = (data.get("message") or data.get("intentions") or
           data.get("why_zen_village") or data.get("offering") or "")
    if msg.count("http") >= 5:
        return True
    # Bots often paste cyrillic/CJK promo blobs
    if len(msg) > 1000 and msg.count("<a href") > 2:
        return True
    return False


# Unified submission endpoint
@app.post("/api/applications/{lane}")
async def submit_application(lane: str, request: Request):
    """Store application for a given lane as timestamped JSON."""
    if lane not in VALID_LANES:
        raise HTTPException(status_code=404, detail=f"Unknown lane: {lane}")
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if _looks_like_spam(data):
        # Pretend success so the bot moves on. Don't persist, don't notify.
        logger.info(f"spam blocked (lane={lane}, email={data.get('email','?')})")
        return {"success": True, "status": "ok", "lane": lane, "message": "Application received"}

    data["lane"] = lane
    data["submitted_at"] = datetime.utcnow().isoformat()
    data["status"] = "new"
    
    # Save per-lane directory
    lane_dir = APPLICATIONS_DIR / lane
    lane_dir.mkdir(parents=True, exist_ok=True)
    
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = (data.get("name", "unknown") or "unknown").replace(" ", "_").replace("/", "_")[:30]
    filename = f"{ts}_{safe_name}.json"
    app_file = lane_dir / filename
    app_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    
    # Append to master list for this lane
    master = lane_dir / "_all.json"
    all_apps = []
    if master.exists():
        try:
            all_apps = json.loads(master.read_text())
        except Exception:
            all_apps = []
    data["_file"] = filename
    all_apps.append(data)
    master.write_text(json.dumps(all_apps, indent=2, ensure_ascii=False))
    
    # Also maintain global list across all lanes
    global_master = APPLICATIONS_DIR / "_all_lanes.json"
    global_apps = []
    if global_master.exists():
        try:
            global_apps = json.loads(global_master.read_text())
        except Exception:
            global_apps = []
    global_apps.append(data)
    global_master.write_text(json.dumps(global_apps, indent=2, ensure_ascii=False))
    
    logger.info(f"New {lane} application: {data.get('name', 'unknown')} ({data.get('email', '')})")
    app_id = f"{lane}-{ts}-{safe_name}"[:60] or filename
    try:
        _sync_application_to_nocodb(lane, data, app_id)
    except Exception as e:
        logger.warning(f"nocodb sync raised (caught): {e}")
    try:
        _notify_application(lane, data)
    except Exception as e:
        logger.warning(f"telegram notify failed: {e}")
    try:
        from app.mail import send_auto_acknowledgment
        send_auto_acknowledgment(
            lane,
            data.get("name") or data.get("full_name") or data.get("nickname") or "",
            data.get("email") or "",
        )
    except Exception as e:
        logger.warning(f"auto-ack failed: {e}")
    return {"success": True, "status": "ok", "lane": lane, "message": "Application received"}


@app.get("/api/applications/{lane}")
async def list_lane_applications(lane: str):
    """List all applications for a given lane."""
    if lane == "all":
        global_master = APPLICATIONS_DIR / "_all_lanes.json"
        if global_master.exists():
            try:
                apps = json.loads(global_master.read_text())
                return {"applications": apps, "count": len(apps), "lane": "all"}
            except Exception:
                pass
        return {"applications": [], "count": 0, "lane": "all"}
    
    if lane not in VALID_LANES:
        raise HTTPException(status_code=404, detail=f"Unknown lane: {lane}")
    
    master = APPLICATIONS_DIR / lane / "_all.json"
    if master.exists():
        try:
            apps = json.loads(master.read_text())
            return {"applications": apps, "count": len(apps), "lane": lane}
        except Exception:
            return {"applications": [], "count": 0, "lane": lane}
    return {"applications": [], "count": 0, "lane": lane}




# === WORK EXCHANGE ALIASES (homepage hero links here) ===
@app.get("/work-exchange")
async def work_exchange_page():
    # Standalone /work-exchange has been folded into the unified /apply gateway.
    # 301-redirect keeps old links + SEO clean.
    return RedirectResponse(url="/apply/work-exchange", status_code=301)


@app.post("/api/work-exchange/submit")
async def work_exchange_submit(request: Request):
    """Alias for legacy form. Routes through the unified application handler."""
    return await submit_application("work-exchange", request)


# === APPLICATION HUB FOR ADMIN (Telegram /inbox links here) ===
@app.get("/applications")
async def applications_dashboard():
    """Quick text dump of all recent applications across all lanes."""
    from fastapi.responses import PlainTextResponse
    out = []
    for lane in sorted(VALID_LANES):
        master = APPLICATIONS_DIR / lane / "_all.json"
        if not master.exists():
            continue
        try:
            apps = json.loads(master.read_text())
        except Exception:
            apps = []
        out.append(f"=== {lane} ({len(apps)}) ===")
        for a in apps[-10:]:
            ts = a.get("submitted_at", "")[:19]
            who = a.get("name") or a.get("full_name") or a.get("email", "?")
            out.append(f"  {ts}  {who}")
        out.append("")
    return PlainTextResponse("\n".join(out) or "no applications yet")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8770)


@app.get("/admin/affiliates", response_class=HTMLResponse)
async def admin_affiliates_page():
    p = BASE_DIR / "static" / "admin" / "affiliates.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return HTMLResponse("<h1>Admin page missing</h1>", status_code=404)

@app.get("/admin/submissions", response_class=HTMLResponse)
async def admin_submissions_page():
    """Unified browser of every public website submission (inquiries +
    applications). Token-gated client-side via /api/admin/submissions."""
    p = FRONTEND_DIR / "admin-submissions.html"
    if p.exists():
        return FileResponse(p, media_type="text/html")
    return HTMLResponse("<h1>Admin page missing</h1>", status_code=404)

@app.get("/admin/inbox", response_class=HTMLResponse)
async def admin_submissions_alias():
    return await admin_submissions_page()

@app.get("/host", response_class=HTMLResponse)
async def host_page():
    p = FRONTEND_DIR / "host.html"
    return FileResponse(p, media_type="text/html") if p.exists() else HTMLResponse("Not found", status_code=404)

@app.get("/host-a-retreat", response_class=HTMLResponse)
async def host_a_retreat_alias():
    return await host_page()

@app.get("/partner", response_class=HTMLResponse)
async def partner_signup_page():
    p = FRONTEND_DIR / "partner.html"
    return FileResponse(p, media_type="text/html") if p.exists() else HTMLResponse("Not found", status_code=404)

@app.get("/share", response_class=HTMLResponse)
async def share_alias():
    return await partner_signup_page()

@app.get("/affiliate", response_class=HTMLResponse)
async def affiliate_alias():
    return await partner_signup_page()


"""app/main.py — Apprentice Gateway FastAPI app.

Stripe checkout + webhook + provisioning for Champion Stack Apprentice.
See SPEC.md for full design.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

import httpx
import stripe
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

from . import character_provisioning, db, provisioning

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("apprentice")

# Config
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "").strip()
FOUNDING_CAP = int(os.environ.get("FOUNDING_CAP", "30"))
CHARACTER_FOUNDING_CAP = int(os.environ.get("CHARACTER_FOUNDING_CAP", "7"))
LANDING_BASE_URL = os.environ.get("LANDING_BASE_URL", "https://fullpotential.com")
CHECKOUT_SUCCESS_URL = os.environ.get(
    "CHECKOUT_SUCCESS_URL", f"{LANDING_BASE_URL}/apprentice/welcome"
)
CHECKOUT_CANCEL_URL = os.environ.get(
    "CHECKOUT_CANCEL_URL", f"{LANDING_BASE_URL}/apprentice/"
)
PRODUCTS_FILE = Path(
    os.environ.get("APPRENTICE_PRODUCTS_FILE", "/etc/apprentice-gateway-products.json")
)

# Static files
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def _load_products() -> dict:
    """Load price IDs from setup_stripe.py output."""
    if not PRODUCTS_FILE.exists():
        log.warning("products file not found at %s", PRODUCTS_FILE)
        return {}
    try:
        return json.loads(PRODUCTS_FILE.read_text())
    except Exception as e:
        log.error("failed to read products file: %s", e)
        return {}


# Initialize Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
else:
    log.warning("STRIPE_SECRET_KEY not set; checkout will fail until env is configured")

# Initialize DB
db.migrate()

# App
app = FastAPI(title="Apprentice Gateway", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://fullpotential.com",
        "https://www.fullpotential.com",
        "https://fullpotential.ai",
        "http://localhost:8773",
        "http://127.0.0.1:8773",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/apprentice/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── Models ───────────────────────────────────────────────────────────────────


class CheckoutRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)
    want_founding: bool = False
    inviter: Optional[str] = Field(None, max_length=100)


class CharacterApplicationRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)
    work: str = Field(..., min_length=20, max_length=2000)
    why: str = Field(..., min_length=20, max_length=2000)
    link: Optional[str] = Field(None, max_length=500)
    inviter: Optional[str] = Field(None, max_length=100)
    agreed_terms: bool = False
    agreed_privacy: bool = False
    agreed_at: Optional[str] = None


class CharacterCheckoutRequest(BaseModel):
    """Admin-initiated checkout link generation for an ACCEPTED application."""
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)
    want_codesign: bool = False
    work: Optional[str] = Field(None, max_length=2000)
    vision_link: Optional[str] = Field(None, max_length=500)
    inviter: Optional[str] = Field(None, max_length=100)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _require_admin(token: Optional[str]) -> None:
    if not ADMIN_TOKEN:
        raise HTTPException(503, "admin token not configured")
    if not token or token != ADMIN_TOKEN:
        raise HTTPException(401, "invalid admin token")


# ── Public endpoints ─────────────────────────────────────────────────────────


@app.get("/health")
async def health() -> dict:
    products = _load_products()
    return {
        "ok": True,
        "service": "apprentice-gateway",
        "version": "0.1.0",
        "stripe_mode": products.get("mode", "unknown"),
        "stripe_configured": bool(STRIPE_SECRET_KEY) and bool(products),
        "founding_filled": db.count_founding(),
        "founding_cap": FOUNDING_CAP,
        "total_active": db.count_active(),
        "provision_flags": provisioning.FLAGS,
    }


@app.get("/apprentice/seats")
async def seats() -> dict:
    """Live founding-30 counter for the landing page."""
    filled = db.count_founding()
    return {
        "founding_filled": filled,
        "founding_cap": FOUNDING_CAP,
        "founding_available": max(0, FOUNDING_CAP - filled),
        "total_active": db.count_active(),
    }


@app.post("/apprentice/checkout")
async def create_checkout(req: CheckoutRequest) -> dict:
    """Create a Stripe Checkout Session.

    Always includes the $97/mo subscription line item.
    Adds $497 founding line item if want_founding=True AND cap not yet reached.
    """
    if not STRIPE_SECRET_KEY:
        raise HTTPException(503, "Stripe not configured")
    products = _load_products()
    if not products:
        raise HTTPException(503, "Stripe products not initialized; run setup_stripe.py")

    line_items = [
        {"price": products["monthly"]["price_id"], "quantity": 1},
    ]

    want_founding = req.want_founding
    if want_founding:
        if db.count_founding() >= FOUNDING_CAP:
            log.info("founding cap reached; declining founding line item for %s", req.email)
            want_founding = False
        else:
            line_items.append(
                {"price": products["founding"]["price_id"], "quantity": 1}
            )

    metadata = {
        "name": req.name,
        "want_founding": "1" if want_founding else "0",
    }
    if req.inviter:
        metadata["inviter"] = req.inviter

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=line_items,
            customer_email=req.email,
            success_url=CHECKOUT_SUCCESS_URL + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=CHECKOUT_CANCEL_URL,
            metadata=metadata,
            subscription_data={"metadata": metadata},
            allow_promotion_codes=True,
        )
    except stripe.error.StripeError as e:
        log.error("Stripe checkout creation failed: %s", e)
        raise HTTPException(502, f"Stripe error: {e!s}")

    return {"checkout_url": session.url, "session_id": session.id}


@app.post("/apprentice/webhook")
async def stripe_webhook(request: Request, background: BackgroundTasks) -> dict:
    """Stripe webhook receiver. HMAC-verified."""
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(503, "webhook secret not configured")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        log.error("webhook signature verification failed: %s", e)
        raise HTTPException(400, "invalid webhook")

    event_id = event["id"]
    event_type = event["type"]

    # Idempotency guard
    if db.already_processed(event_id):
        log.info("event %s already processed; skipping", event_id)
        return {"ok": True, "skipped": True}

    obj = event["data"]["object"]
    email_for_log: Optional[str] = None

    if event_type == "checkout.session.completed":
        # First-time provisioning (apprentice OR character — branch on metadata.tier)
        email = (obj.get("customer_details") or {}).get("email") or obj.get("customer_email")
        if not email:
            log.error("checkout.session.completed missing email; event_id=%s", event_id)
            db.record_event(event_id, event_type, None)
            return {"ok": True, "skipped": True}

        email = email.lower().strip()
        email_for_log = email
        metadata = obj.get("metadata") or {}
        name = metadata.get("name") or email.split("@")[0]
        tier = metadata.get("tier", "apprentice")
        inviter = metadata.get("inviter")
        stripe_customer_id = obj.get("customer") or ""
        stripe_subscription_id = obj.get("subscription") or None

        if tier == "character":
            want_codesign = metadata.get("want_codesign") == "1"
            work = metadata.get("work")
            vision_link = metadata.get("vision_link")

            log.info(
                "provisioning new character email=%s codesign=%s", email, want_codesign
            )

            db.upsert_character(
                email=email,
                name=name,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
                founding=want_codesign,  # founding = paid co-design fee for v0.1
                co_design_fee_paid=want_codesign,
                inviter=inviter,
                work=work,
                vision_link=vision_link,
            )

            # Update related application row(s) to status=paid
            for app_row in db.list_character_applications():
                if app_row["email"].lower().strip() == email and app_row["status"] in (
                    "accepted",
                    "pending",
                ):
                    db.update_character_application_status(
                        app_row["id"], "paid", "Stripe checkout completed"
                    )

            background.add_task(
                character_provisioning.provision_character,
                email,
                name,
                want_codesign,
                work,
                vision_link,
            )
        else:
            want_founding = metadata.get("want_founding") == "1"

            log.info("provisioning new apprentice email=%s founding=%s", email, want_founding)

            db.upsert_apprentice(
                email=email,
                name=name,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
                founding=want_founding,
                inviter=inviter,
            )

            background.add_task(
                provisioning.provision_apprentice, email, name, want_founding
            )

    elif event_type == "customer.subscription.updated":
        # Status change (e.g., past_due, active, paused)
        status = obj.get("status")
        customer_id = obj.get("customer")
        sub_id = obj.get("id")
        active = status in ("active", "trialing")
        matched = False
        for a in db.list_apprentices():
            if a["stripe_customer_id"] == customer_id:
                email_for_log = a["email"]
                db.mark_subscription(a["email"], subscription_id=sub_id, active=active)
                log.info("subscription %s for %s set active=%s", status, a["email"], active)
                matched = True
                break
        if not matched:
            for c in db.list_characters():
                if c["stripe_customer_id"] == customer_id:
                    email_for_log = c["email"]
                    db.mark_character_subscription(
                        c["email"], subscription_id=sub_id, active=active
                    )
                    log.info(
                        "character subscription %s for %s set active=%s",
                        status, c["email"], active,
                    )
                    break

    elif event_type == "customer.subscription.deleted":
        # Cancellation finalized (after period ends)
        customer_id = obj.get("customer")
        sub_id = obj.get("id")
        matched = False
        for a in db.list_apprentices():
            if a["stripe_customer_id"] == customer_id:
                email_for_log = a["email"]
                db.mark_subscription(a["email"], subscription_id=sub_id, active=False)
                log.info("subscription deleted for %s", a["email"])
                matched = True
                break
        if not matched:
            for c in db.list_characters():
                if c["stripe_customer_id"] == customer_id:
                    email_for_log = c["email"]
                    db.mark_character_subscription(
                        c["email"], subscription_id=sub_id, active=False
                    )
                    log.info("character subscription deleted for %s", c["email"])
                    break

    db.record_event(event_id, event_type, email_for_log)
    return {"ok": True}


@app.get("/apprentice/status/{email}")
async def apprentice_status(email: str) -> dict:
    rec = db.get_apprentice(email)
    if not rec:
        raise HTTPException(404, "no apprentice with that email")
    return {
        "email": rec["email"],
        "name": rec["name"],
        "tier": rec["tier"],
        "active": bool(rec["active"]),
        "founding": bool(rec["founding"]),
        "founding_number": rec["founding_number"],
        "provision_state": rec["provision_state"],
        "created_at": rec["created_at"],
    }


@app.get("/apprentice/")
async def landing_page():
    """Serve the landing page if available."""
    page = STATIC_DIR / "apprentice.html"
    if page.exists():
        return FileResponse(page)
    return JSONResponse({"error": "landing page not yet deployed"}, status_code=404)


@app.get("/apprentice/welcome")
async def welcome_page(session_id: Optional[str] = None):
    """Post-checkout welcome page."""
    page = STATIC_DIR / "welcome.html"
    if page.exists():
        return FileResponse(page)
    # Fallback inline response
    return JSONResponse(
        {
            "ok": True,
            "message": (
                "Welcome to the Champion Stack Apprentice. Your provisioning is "
                "running in the background. Check your email and Telegram for next steps."
            ),
            "session_id": session_id,
        }
    )


# ── Character tier endpoints ─────────────────────────────────────────────────


@app.get("/character/")
async def character_landing_page():
    """Serve the Character tier landing page."""
    page = STATIC_DIR / "character.html"
    if page.exists():
        return FileResponse(page)
    return JSONResponse({"error": "landing page not yet deployed"}, status_code=404)


@app.get("/character/seats")
async def character_seats() -> dict:
    """Live founding-7 counter for the Character landing page."""
    filled = db.count_founding_characters()
    return {
        "founding_filled": filled,
        "founding_cap": CHARACTER_FOUNDING_CAP,
        "founding_available": max(0, CHARACTER_FOUNDING_CAP - filled),
        "total_active": db.count_active_characters(),
    }


@app.post("/character/apply")
async def character_apply(req: CharacterApplicationRequest) -> dict:
    """Receive a Character tier application (no payment yet).

    Per Decision Frameworks Domain 5 (brand-frame · public-surface stability),
    Character tier is application-gated. James reviews; admin endpoint then
    generates a Stripe checkout link for accepted candidates.
    """
    if not req.agreed_terms or not req.agreed_privacy:
        raise HTTPException(400, "must agree to terms + privacy")

    app_row = db.create_character_application(
        email=req.email,
        name=req.name,
        work=req.work,
        why=req.why,
        link=req.link,
        inviter=req.inviter,
        agreed_terms=req.agreed_terms,
        agreed_privacy=req.agreed_privacy,
        agreed_at=req.agreed_at,
    )

    # Best-effort alert to James (Telegram) — non-blocking
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"{character_provisioning.ALERTS_URL}/send",
                json={
                    "channel": "telegram",
                    "recipient": "default",
                    "message": (
                        f"🟡 New Character application\n"
                        f"{req.name} <{req.email}>\n"
                        f"Work: {req.work[:200]}\n"
                        f"Link: {req.link or '—'}\n"
                        f"Why: {req.why[:200]}\n"
                        f"Inviter: {req.inviter or '—'}\n"
                        f"Review: /admin/character/applications"
                    ),
                },
            )
    except Exception:
        log.exception("failed to alert james on new application (non-fatal)")

    log.info("character application id=%s email=%s", app_row.get("id"), req.email)
    return {
        "ok": True,
        "application_id": app_row.get("id"),
        "message": (
            "Application received. James reviews founding-cohort applications "
            "personally. Expect a response within 2-4 days — either a Stripe "
            "checkout link to start, or a candid note about a better path for you."
        ),
    }


@app.post("/character/checkout")
async def character_checkout(
    req: CharacterCheckoutRequest,
    x_admin_token: Optional[str] = Header(None),
) -> dict:
    """Generate a Stripe checkout link for an ACCEPTED Character application.

    Admin-only — James (or Ember acting as proxy) calls this AFTER reviewing
    the application. Returns a checkout URL to forward to the candidate.
    """
    _require_admin(x_admin_token)

    if not STRIPE_SECRET_KEY:
        raise HTTPException(503, "Stripe not configured")
    products = _load_products()
    if not products or "character_monthly" not in products:
        raise HTTPException(503, "Character Stripe products not initialized; run setup_stripe.py")

    line_items = [
        {"price": products["character_monthly"]["price_id"], "quantity": 1},
    ]

    want_codesign = req.want_codesign
    if want_codesign:
        if db.count_founding_characters() >= CHARACTER_FOUNDING_CAP:
            log.info(
                "character founding cap reached; declining codesign line item for %s",
                req.email,
            )
            want_codesign = False
        else:
            line_items.append(
                {"price": products["character_codesign"]["price_id"], "quantity": 1}
            )

    metadata = {
        "name": req.name,
        "want_codesign": "1" if want_codesign else "0",
        "tier": "character",
    }
    if req.inviter:
        metadata["inviter"] = req.inviter
    if req.work:
        metadata["work"] = req.work[:500]
    if req.vision_link:
        metadata["vision_link"] = req.vision_link[:500]

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=line_items,
            customer_email=req.email,
            success_url=f"{LANDING_BASE_URL}/character/welcome"
            + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=f"{LANDING_BASE_URL}/character/",
            metadata=metadata,
            subscription_data={"metadata": metadata},
            allow_promotion_codes=True,
        )
    except stripe.error.StripeError as e:
        log.error("Stripe character checkout creation failed: %s", e)
        raise HTTPException(502, f"Stripe error: {e!s}")

    return {"checkout_url": session.url, "session_id": session.id}


@app.get("/character/welcome")
async def character_welcome_page(session_id: Optional[str] = None):
    """Post-checkout Character welcome page."""
    page = STATIC_DIR / "character_welcome.html"
    if page.exists():
        return FileResponse(page)
    return JSONResponse(
        {
            "ok": True,
            "message": (
                "Welcome, Character. Your provisioning is running in the "
                "background. Check your email and Telegram for your identity "
                "stack scaffold, brain-server credentials, and first 1:1 booking link."
            ),
            "session_id": session_id,
        }
    )


@app.get("/character/status/{email}")
async def character_status(email: str) -> dict:
    rec = db.get_character(email)
    if not rec:
        raise HTTPException(404, "no character with that email")
    return {
        "email": rec["email"],
        "name": rec["name"],
        "tier": rec["tier"],
        "active": bool(rec["active"]),
        "founding": bool(rec["founding"]),
        "founding_number": rec["founding_number"],
        "co_design_fee_paid": bool(rec["co_design_fee_paid"]),
        "provision_state": rec["provision_state"],
        "created_at": rec["created_at"],
    }


# ── Admin endpoints ──────────────────────────────────────────────────────────


@app.get("/admin/apprentices")
async def admin_list(x_admin_token: Optional[str] = Header(None)) -> dict:
    _require_admin(x_admin_token)
    return {"apprentices": db.list_apprentices()}


@app.post("/admin/replay-provisioning/{email}")
async def admin_replay(
    email: str,
    background: BackgroundTasks,
    x_admin_token: Optional[str] = Header(None),
) -> dict:
    _require_admin(x_admin_token)
    rec = db.get_apprentice(email)
    if not rec:
        raise HTTPException(404, "no apprentice with that email")
    background.add_task(
        provisioning.provision_apprentice,
        rec["email"],
        rec["name"],
        bool(rec["founding"]),
    )
    return {"ok": True, "replaying": True, "email": email}


@app.post("/admin/refund/{stripe_session_id}")
async def admin_refund(
    stripe_session_id: str,
    x_admin_token: Optional[str] = Header(None),
) -> dict:
    _require_admin(x_admin_token)
    if not STRIPE_SECRET_KEY:
        raise HTTPException(503, "Stripe not configured")
    try:
        session = stripe.checkout.Session.retrieve(stripe_session_id)
        payment_intent = session.payment_intent
        if not payment_intent:
            raise HTTPException(400, "no payment intent on session")
        refund = stripe.Refund.create(payment_intent=payment_intent)
        return {"ok": True, "refund_id": refund.id, "status": refund.status}
    except stripe.error.StripeError as e:
        raise HTTPException(502, f"Stripe error: {e!s}")


# ── Character admin endpoints ────────────────────────────────────────────────


@app.get("/admin/character/applications")
async def admin_character_applications(
    status: Optional[str] = None,
    x_admin_token: Optional[str] = Header(None),
) -> dict:
    _require_admin(x_admin_token)
    return {"applications": db.list_character_applications(status=status)}


@app.post("/admin/character/applications/{app_id}/accept")
async def admin_accept_character(
    app_id: int,
    x_admin_token: Optional[str] = Header(None),
    note: Optional[str] = None,
) -> dict:
    _require_admin(x_admin_token)
    db.update_character_application_status(app_id, "accepted", note)
    return {"ok": True, "application_id": app_id, "status": "accepted"}


@app.post("/admin/character/applications/{app_id}/decline")
async def admin_decline_character(
    app_id: int,
    x_admin_token: Optional[str] = Header(None),
    note: Optional[str] = None,
) -> dict:
    _require_admin(x_admin_token)
    db.update_character_application_status(app_id, "declined", note)
    return {"ok": True, "application_id": app_id, "status": "declined"}


@app.get("/admin/characters")
async def admin_list_characters(x_admin_token: Optional[str] = Header(None)) -> dict:
    _require_admin(x_admin_token)
    return {"characters": db.list_characters()}


@app.post("/admin/character/replay-provisioning/{email}")
async def admin_replay_character(
    email: str,
    background: BackgroundTasks,
    x_admin_token: Optional[str] = Header(None),
) -> dict:
    _require_admin(x_admin_token)
    rec = db.get_character(email)
    if not rec:
        raise HTTPException(404, "no character with that email")
    background.add_task(
        character_provisioning.provision_character,
        rec["email"],
        rec["name"],
        bool(rec["founding"]),
        rec.get("work"),
        rec.get("vision_link"),
    )
    return {"ok": True, "replaying": True, "email": email}


# ── Root ─────────────────────────────────────────────────────────────────────


@app.get("/")
async def root() -> dict:
    return {
        "service": "apprentice-gateway",
        "version": "0.2.0",
        "docs": "/docs",
        "tiers": ["apprentice", "character"],
        "landing": {
            "apprentice": "/apprentice/",
            "character": "/character/",
        },
    }

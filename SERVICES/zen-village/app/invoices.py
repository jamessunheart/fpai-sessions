"""
Zen Village — Stripe invoice generator.

Lets admins create + send a real Stripe invoice to anyone (e.g. a retreat
guest, a coherent attendee, a sponsor) from the cockpit or Telegram.

POST /api/admin/invoices/create
{
  "email": "guest@example.com",
  "name":  "Guest Name",
  "amount_usd": 2000,           // dollars; multiplied to cents server-side
  "description": "Zen Village retreat — May 12–18",
  "memo":        "Optional note shown on the invoice (max 500c)",
  "due_days":    7              // optional; default 7
}

Response:
  {"ok": true, "invoice_id": "in_...", "hosted_url": "...", "pdf": "..."}

Only admins (X-Admin-Token) may call. We persist a copy under
/data/invoices/<id>.json for the cockpit to render later.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

try:
    import stripe  # type: ignore
except Exception:
    stripe = None  # type: ignore

router = APIRouter()

ADMIN_TOKEN_ENV = "ZV_AFFILIATES_ADMIN_TOKEN"
DATA_DIR = Path(os.getenv("ZV_DATA_DIR", "/opt/fpai/apps/zen-village/data"))
INVOICE_DIR = DATA_DIR / "invoices"
INVOICE_DIR.mkdir(parents=True, exist_ok=True)


def _require_admin(token: Optional[str]) -> None:
    expected = (os.getenv(ADMIN_TOKEN_ENV) or "").strip()
    if not expected or (token or "").strip() != expected:
        raise HTTPException(401, "admin token required")


def _stripe_ready() -> bool:
    if stripe is None:
        return False
    key = os.getenv("STRIPE_SECRET_KEY", "")
    if not key:
        return False
    stripe.api_key = key
    return True


@router.post("/api/admin/invoices/create")
async def create_invoice(payload: dict, x_admin_token: Optional[str] = Header(None)):
    _require_admin(x_admin_token)
    if not _stripe_ready():
        raise HTTPException(503, "Stripe not configured (STRIPE_SECRET_KEY missing)")

    email = (payload.get("email") or "").strip().lower()
    name = (payload.get("name") or "").strip()
    description = (payload.get("description") or "Zen Village").strip()
    memo = (payload.get("memo") or "").strip()[:500]
    try:
        amount_usd = float(payload.get("amount_usd") or 0)
    except Exception:
        raise HTTPException(400, "amount_usd must be a number")
    due_days = int(payload.get("due_days") or 7)

    if not email or "@" not in email:
        raise HTTPException(400, "valid email required")
    if amount_usd < 1:
        raise HTTPException(400, "amount_usd must be ≥ 1")

    cents = int(round(amount_usd * 100))

    # Find or create customer
    try:
        existing = stripe.Customer.search(query=f"email:'{email}'", limit=1)
        if existing.data:
            customer = existing.data[0]
            if name and not customer.get("name"):
                stripe.Customer.modify(customer.id, name=name)
        else:
            customer = stripe.Customer.create(email=email, name=name or None)
    except Exception as e:
        raise HTTPException(502, f"stripe customer error: {e}")

    # Create invoice item, then invoice, then finalize+send
    try:
        stripe.InvoiceItem.create(
            customer=customer.id,
            amount=cents,
            currency="usd",
            description=description,
        )
        invoice = stripe.Invoice.create(
            customer=customer.id,
            collection_method="send_invoice",
            days_until_due=due_days,
            description=memo or description,
            footer="Thank you for supporting the village. Reply to this email if anything's off.",
            auto_advance=False,
        )
        invoice = stripe.Invoice.finalize_invoice(invoice.id)
        stripe.Invoice.send_invoice(invoice.id)
    except Exception as e:
        raise HTTPException(502, f"stripe invoice error: {e}")

    record = {
        "id": invoice.id,
        "customer_id": customer.id,
        "email": email,
        "name": name,
        "amount_usd": amount_usd,
        "description": description,
        "memo": memo,
        "hosted_url": invoice.hosted_invoice_url,
        "pdf": invoice.invoice_pdf,
        "status": invoice.status,
        "created_at": datetime.utcnow().isoformat(),
    }
    (INVOICE_DIR / f"{invoice.id}.json").write_text(json.dumps(record, indent=2))

    return {"ok": True, **record}


@router.get("/api/admin/invoices")
async def list_invoices(x_admin_token: Optional[str] = Header(None), limit: int = 25):
    _require_admin(x_admin_token)
    files = sorted(INVOICE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for f in files[:limit]:
        try:
            out.append(json.loads(f.read_text()))
        except Exception:
            continue
    return {"ok": True, "invoices": out, "count": len(out)}

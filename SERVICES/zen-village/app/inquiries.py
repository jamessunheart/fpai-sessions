"""
Zen Village Inquiry Handler
Receives booking inquiries and:
1. Saves to database
2. Sends email notification to james@fullpotential.com
3. Sends Telegram notification via FPI brain
4. Returns confirmation to user with payment instructions
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import json
import secrets
import smtplib
import httpx
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

router = APIRouter()

DATA_DIR = Path("/opt/fpai/apps/zen-village/data")
DATA_DIR.mkdir(exist_ok=True)
INQUIRIES_FILE = DATA_DIR / "inquiries.json"

PAYMENT_METHODS = {
    "paypal": {"name": "PayPal (Friends & Family)", "address": "james@fullpotential.com"},
    "venmo": {"name": "Venmo (Friends & Family)", "address": "@James-Stinson-65"},
    "wise": {"name": "Wise", "address": "https://wise.com/pay/business/coranationchurch"},
    "btc": {"name": "Bitcoin (BTC)", "address": "13tXYGWCZWgPoZ8WZXi7vTt2kwax2ekpz7"},
    "sol": {"name": "Solana (SOL)", "address": "9YfypYoQZPj5L33tFTR5Ek4LgJUTSyx8JskGehyP6tsb"},
    "usdt_eth": {"name": "USDT (Ethereum)", "address": "0x2718e06abefa37947c7ea63c8746e4f14777aacb"},
    "bank_transfer": {"name": "Bank Transfer", "address": "Provided after confirmation"},
    "other": {"name": "Other", "address": "To be discussed"},
}

class InquiryRequest(BaseModel):
    name: str
    email: EmailStr
    inquiry_type: str = "Stay"
    dates: Optional[str] = None
    guests: Optional[str] = None
    accommodation: Optional[str] = None
    message: Optional[str] = None
    phone: Optional[str] = None
    partner_code: Optional[str] = None
    payment_method: Optional[str] = None

def load_inquiries():
    if INQUIRIES_FILE.exists():
        with open(INQUIRIES_FILE, "r") as f:
            return json.load(f)
    return []

def save_inquiry(inquiry: dict):
    inquiries = load_inquiries()
    inquiries.append(inquiry)
    with open(INQUIRIES_FILE, "w") as f:
        json.dump(inquiries, f, indent=2)


# === NocoDB sync (Inquiries CRM) ============================================
import urllib.request as _ureq

_NOCODB_URL = os.environ.get("NOCODB_URL", "http://127.0.0.1:8080").rstrip("/")
_NOCODB_TOKEN = os.environ.get("NOCODB_API_TOKEN", "")
_NOCODB_INQUIRIES_TABLE = os.environ.get("NOCODB_INQUIRIES_TABLE_ID", "")


def _sync_inquiry_to_nocodb(inq: dict) -> None:
    """Mirror inquiry into NocoDB. Never raises."""
    if not (_NOCODB_TOKEN and _NOCODB_INQUIRIES_TABLE):
        return
    try:
        type_label = (inq.get("inquiry_type") or "Stay").strip()
        # Map to NocoDB single-select options. Order matters — "Coherent Retreat"
        # must hit "Retreat" before falling through. New homepage lanes
        # (Coherent Retreat, Support) are mapped explicitly so admin filters
        # surface them cleanly.
        type_value = "Stay"
        lt = type_label.lower()
        if "coherent" in lt or "fp retreat" in lt:
            type_value = "Retreat"
        elif lt in ("support", "donate", "donation"):
            type_value = "Other"
        else:
            for opt in ("Stay", "Retreat", "Event", "Other"):
                if lt == opt.lower() or opt.lower() in lt:
                    type_value = opt
                    break
        payload = {
            "InquiryId": inq.get("id") or "",
            "Type": type_value,
            "Status": "New",
            "Name": (inq.get("name") or "")[:255],
            "Email": (inq.get("email") or "")[:255],
            "Phone": (inq.get("phone") or "")[:64],
            "Dates": (inq.get("dates") or "")[:255],
            "Guests": (inq.get("guests") or "")[:64],
            "Accommodation": (inq.get("accommodation") or "")[:255],
            "Message": (inq.get("message") or "")[:8000],
            "PaymentMethod": (inq.get("payment_method") or "")[:64],
            "PartnerCode": (inq.get("partner_code") or "")[:64],
            "SubmittedAt": inq.get("timestamp") or datetime.now().isoformat(),
            "Source": "/api/inquiries/submit",
        }
        req = _ureq.Request(
            _NOCODB_URL + "/api/v2/tables/" + _NOCODB_INQUIRIES_TABLE + "/records",
            data=json.dumps(payload).encode(),
            method="POST",
            headers={"xc-token": _NOCODB_TOKEN, "Content-Type": "application/json"},
        )
        _ureq.urlopen(req, timeout=5).read()
    except Exception as e:
        print("nocodb inquiry sync failed: " + str(e))
# === end NocoDB sync ========================================================


async def notify_telegram(inquiry: dict):
    """Send instant Telegram notification to admins when a booking inquiry arrives.

    Uses app.telegram_send (direct api.telegram.org call). The previous
    implementation called fp-index/api/v1/brain/notify which didn't exist
    and silently returned {sent:false}.
    """
    try:
        from app.telegram_send import (
            send_to_admins, send_to_pulse, submission_action_keyboard,
        )
        def _f(key: str, default: str = "") -> str:
            v = inquiry.get(key)
            return v if v else default

        itype = _f("inquiry_type", "Stay")
        # Mirror Pulse Topic: Coherent/Stay → Bookings, Support → Financials
        topic = "financials" if itype.lower().startswith("support") else "bookings"
        partner = _f("partner_code")
        lines = [
            f"<b>📥 New {itype} inquiry</b>",
            f"From: <b>{_f('name', 'Anonymous')}</b>",
            f"Email: <code>{_f('email', '')}</code>",
        ]
        if _f("phone"):
            lines.append("Phone/WhatsApp: <code>" + _f("phone") + "</code>")
        if _f("dates"):
            lines.append("Dates: " + _f("dates"))
        if _f("guests"):
            lines.append("Guests: " + _f("guests"))
        if _f("message"):
            lines.append("\n<i>" + _f("message")[:600] + "</i>")
        if partner:
            lines.append(f"\nReferred by: <code>{partner}</code>")
        msg = "\n".join(lines)

        # Build same submission key the cockpit uses so the buttons can mark
        # it contacted/closed.
        submission_key = "|".join([
            "inquiry",
            itype,
            (_f("email", "") or "").lower().strip(),
            (inquiry.get("timestamp") or "")[:19],
        ])
        keyboard = submission_action_keyboard(submission_key)

        send_to_admins(msg, reply_markup=keyboard)
        send_to_pulse(msg, topic=topic)
    except Exception as e:
        print("Telegram notify failed: " + str(e))


def send_email_notification(inquiry: dict):
    try:
        # Coerce Optional fields (None) to readable defaults — Pydantic stores
        # missing optional fields as None, not missing-from-dict.
        def _f(key: str, default: str = "") -> str:
            v = inquiry.get(key)
            return v if v else default

        name = _f("name", "Anonymous")
        email = _f("email", "")
        inquiry_type = _f("inquiry_type", "Stay")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "New " + inquiry_type + " Inquiry: " + name
        msg["From"] = "noreply@zenvillagecr.com"
        msg["To"] = "james@fullpotential.com"

        pm = _f("payment_method", "not specified")
        pm_info = PAYMENT_METHODS.get(pm, {})
        pm_display = pm_info.get("name", pm) if pm_info else pm

        text = (
            "NEW ZEN VILLAGE BOOKING INQUIRY\n"
            "=================================\n"
            "Type: " + inquiry_type + "\n"
            "Name: " + name + "\n"
            "Email: " + email + "\n"
            "Phone: " + _f("phone", "Not provided") + "\n"
            "Dates: " + _f("dates", "Flexible") + "\n"
            "Guests: " + _f("guests", "Not specified") + "\n"
            "Accommodation: " + _f("accommodation", "Not specified") + "\n"
            "Payment Method: " + pm_display + "\n"
            "Partner Code: " + _f("partner_code", "Direct") + "\n\n"
            "Message:\n" + _f("message", "No message") + "\n\n"
            "---\nReceived: " + _f("timestamp", "") + "\n"
            "Reply to: " + email + "\n"
        )

        html = (
            '<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">'
            '<div style="background:#1a2e1a;color:#faf9f5;padding:20px;text-align:center;">'
            '<h1 style="margin:0;">New ' + inquiry_type + ' Inquiry</h1></div>'
            '<div style="padding:20px;background:#f0f4ec;">'
            '<table style="width:100%;border-collapse:collapse;">'
            '<tr><td style="padding:8px 0;font-weight:bold;width:140px;">Name:</td><td>' + name + '</td></tr>'
            '<tr><td style="padding:8px 0;font-weight:bold;">Email:</td><td><a href="mailto:' + email + '">' + email + '</a></td></tr>'
            '<tr><td style="padding:8px 0;font-weight:bold;">Phone:</td><td>' + _f("phone", "Not provided") + '</td></tr>'
            '<tr><td style="padding:8px 0;font-weight:bold;">Dates:</td><td>' + _f("dates", "Flexible") + '</td></tr>'
            '<tr><td style="padding:8px 0;font-weight:bold;">Guests:</td><td>' + _f("guests", "Not specified") + '</td></tr>'
            '<tr><td style="padding:8px 0;font-weight:bold;">Accommodation:</td><td>' + _f("accommodation", "Not specified") + '</td></tr>'
            '</table>'
            '<div style="margin-top:16px;padding:14px;background:#fffdf5;border-radius:8px;border:2px solid #c4a35a;">'
            '<strong style="color:#c4a35a;">Payment: ' + pm_display + '</strong></div>'
            '<div style="margin-top:16px;padding:15px;background:white;border-radius:8px;">'
            '<strong>Message:</strong><br>' + _f("message", "No message") + '</div>'
            '<div style="margin-top:20px;text-align:center;">'
            '<a href="mailto:' + email + '?subject=Re: Your Zen Village Booking" '
            'style="display:inline-block;padding:12px 24px;background:#c4a35a;color:#1a2e1a;text-decoration:none;border-radius:8px;font-weight:bold;">'
            'Reply to ' + name + '</a></div></div></body></html>'
        )

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP("localhost", 25) as server:
            server.sendmail(msg["From"], [msg["To"]], msg.as_string())
        return True
    except Exception as e:
        print("Email send failed: " + str(e))
        return False

@router.post("/submit")
async def submit_inquiry(inquiry: InquiryRequest, background_tasks: BackgroundTasks):
    # Honeypot: bots tend to paste URLs into the message. Real humans almost
    # never. If the message has 5+ URLs, swallow silently.
    msg = (inquiry.message or "")
    if msg.count("http") >= 5:
        return {"success": True, "message": "Thank you! Your booking request has been received."}
    inquiry_data = {
        # 6-char hex nonce keeps IDs unique even when 2 forms submit
        # in the same second (homepage lane chooser fires multiple).
        "id": "inq_" + datetime.now().strftime('%Y%m%d%H%M%S') + "_" + secrets.token_hex(3),
        "name": inquiry.name,
        "email": inquiry.email,
        "inquiry_type": inquiry.inquiry_type,
        "dates": inquiry.dates,
        "guests": inquiry.guests,
        "accommodation": inquiry.accommodation,
        "message": inquiry.message,
        "phone": inquiry.phone,
        "payment_method": inquiry.payment_method,
        "partner_code": inquiry.partner_code,
        "timestamp": datetime.now().isoformat(),
        "status": "new"
    }
    save_inquiry(inquiry_data)
    background_tasks.add_task(_sync_inquiry_to_nocodb, inquiry_data)
    background_tasks.add_task(send_email_notification, inquiry_data)
    background_tasks.add_task(notify_telegram, inquiry_data)

    # Auto-acknowledgment so guests know we got their message.
    try:
        from app.mail import send_auto_acknowledgment
        background_tasks.add_task(
            send_auto_acknowledgment,
            inquiry_data["inquiry_type"],
            inquiry_data.get("name") or "",
            inquiry_data.get("email") or "",
        )
    except Exception as e:
        print("auto-ack scheduling failed: " + str(e))

    pm = inquiry.payment_method or "paypal"
    pm_info = PAYMENT_METHODS.get(pm, PAYMENT_METHODS["other"])

    return {
        "success": True,
        "message": "Thank you! Your booking request has been received. We will confirm availability within 24 hours.",
        "inquiry_id": inquiry_data["id"],
        "payment_info": {
            "method": pm_info["name"],
            "address": pm_info["address"],
            "note": "Please wait for our confirmation before sending payment."
        }
    }

@router.get("/list")
async def list_inquiries():
    return {"inquiries": load_inquiries()}

@router.get("/payment-methods")
async def get_payment_methods():
    return {"payment_methods": PAYMENT_METHODS}

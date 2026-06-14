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

# Co-stewards BCC'd on every inquiry notification (closes affiliate-visibility gap).
# Override via ZV_COSTEWARDS env var (comma-separated). Empty string disables.
_COSTEWARDS_ENV = os.environ.get("ZV_COSTEWARDS")
if _COSTEWARDS_ENV is not None:
    CO_STEWARDS = [e.strip() for e in _COSTEWARDS_ENV.split(",") if e.strip()]
else:
    CO_STEWARDS = ["atlas@zenvillagecr.com", "halley@zenvillagecr.com"]

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
        pm = _f("payment_method")
        accommodation = _f("accommodation")

        # Paid-intent detection — reservation came through /reset/pay (user
        # picked a package + payment method, not a soft inquiry).
        # Distinct header so James can spot real buyers vs cold leads in TG.
        is_paid_intent = bool(pm) and ("reset retreat" in itype.lower() or "jungle exhale" in itype.lower())

        if is_paid_intent:
            pm_info = PAYMENT_METHODS.get(pm, {})
            pm_label = pm_info.get("name", pm)
            header = f"<b>💰 PAID-INTENT RESERVATION — {itype}</b>"
        else:
            header = f"<b>📥 New {itype} inquiry</b>"

        lines = [
            header,
            f"From: <b>{_f('name', 'Anonymous')}</b>",
            f"Email: <code>{_f('email', '')}</code>",
        ]
        if _f("phone"):
            lines.append("Phone/WhatsApp: <code>" + _f("phone") + "</code>")
        if _f("dates"):
            lines.append("Dates: " + _f("dates"))
        if _f("guests"):
            lines.append("Guests: " + _f("guests"))
        if is_paid_intent:
            if accommodation:
                lines.append(f"📦 Package: <b>{accommodation}</b>")
            lines.append(f"💳 Pay method: <b>{pm_label}</b>")
            if partner:
                lines.append(f"🤝 Affiliate: <code>{partner}</code> (commission on confirm)")
        if _f("message"):
            lines.append("\n<i>" + _f("message")[:600] + "</i>")
        if partner and not is_paid_intent:
            lines.append(f"\nReferred by: <code>{partner}</code>")
        if is_paid_intent:
            lines.append(f"\n<i>Reference: {inquiry.get('id', '')}</i>")
            lines.append("<i>Action: watch inbox for payment receipt, then mark sale via /api/affiliates/convert</i>")
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


def notify_partner_on_referral(inquiry: dict):
    """If inquiry has a partner_code, email that partner about the lead.

    Silent skip cases (each logs why):
    - No partner_code on the inquiry
    - Partner code not found in partners.json
    - Partner status is not 'active'
    - Partner has no email address on file
    """
    try:
        code = (inquiry.get("partner_code") or "").upper().strip()
        if not code:
            return False

        from app.affiliates import (
            _load as _aff_load,
            PARTNERS_FILE,
            partner_dashboard_token,
        )
        partners = _aff_load(PARTNERS_FILE)
        partner = partners.get(code)
        if not partner:
            print("partner notify skipped: unknown code " + code)
            return False
        if (partner.get("status") or "active") != "active":
            print("partner notify skipped: code " + code + " is not active")
            return False

        partner_email = (partner.get("email") or "").strip()
        if not partner_email:
            print("partner notify skipped: code " + code + " has no email")
            return False

        partner_name = partner.get("name") or code
        token = partner_dashboard_token(code)
        site_base = (os.environ.get("ZV_SITE_BASE") or "https://zenvillagecr.com").rstrip("/")
        dashboard_url = site_base + "/reset/me?code=" + code + "&token=" + token

        def _f(key: str, default: str = "") -> str:
            v = inquiry.get(key)
            return v if v else default

        name = _f("name", "Anonymous")
        guest_email = _f("email", "")
        inquiry_type = _f("inquiry_type", "Stay")
        pm = _f("payment_method", "")
        pm_info = PAYMENT_METHODS.get(pm, {})
        pm_display = pm_info.get("name", pm) if pm_info else pm
        is_paid_intent = bool(pm) and (
            "reset retreat" in inquiry_type.lower() or "jungle exhale" in inquiry_type.lower()
        )

        subject_prefix = "💰 PAID intent" if is_paid_intent else "📥 New lead"
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject_prefix + " from your ref " + code + " — " + name
        msg["From"] = "noreply@zenvillagecr.com"
        msg["To"] = partner_email
        msg["Reply-To"] = "james@fullpotential.com"

        text_lines = [
            "Hi " + partner_name + ",",
            "",
            "Someone just used your referral code " + code + " on zenvillagecr.com/reset.",
            "",
            "Type: " + inquiry_type,
            "From: " + name,
            "Email: " + guest_email,
            "Phone: " + _f("phone", "Not provided"),
            "Dates: " + _f("dates", "Flexible"),
            "Guests: " + _f("guests", "Not specified"),
            "Accommodation: " + _f("accommodation", "Not specified"),
        ]
        if is_paid_intent:
            text_lines.append("Payment method: " + pm_display)
            text_lines.append("")
            text_lines.append("** Paid-intent reservation. ** Commission lands once James confirms payment.")
        text_lines.extend([
            "",
            "See all your leads + commissions: " + dashboard_url,
            "",
            "Questions? Reply to this email — it goes to James.",
            "",
            "— Zen Village",
        ])
        text = "\n".join(text_lines)

        header_color = "#c4a35a" if is_paid_intent else "#1a2e1a"
        header_label = "💰 Paid-intent reservation" if is_paid_intent else "📥 New lead"

        rows_html = (
            '<tr><td style="padding:6px 0;font-weight:bold;width:140px;">Type:</td><td>' + inquiry_type + '</td></tr>'
            '<tr><td style="padding:6px 0;font-weight:bold;">Name:</td><td>' + name + '</td></tr>'
            '<tr><td style="padding:6px 0;font-weight:bold;">Email:</td><td><a href="mailto:' + guest_email + '">' + guest_email + '</a></td></tr>'
            '<tr><td style="padding:6px 0;font-weight:bold;">Phone:</td><td>' + _f("phone", "Not provided") + '</td></tr>'
            '<tr><td style="padding:6px 0;font-weight:bold;">Dates:</td><td>' + _f("dates", "Flexible") + '</td></tr>'
            '<tr><td style="padding:6px 0;font-weight:bold;">Guests:</td><td>' + _f("guests", "Not specified") + '</td></tr>'
            '<tr><td style="padding:6px 0;font-weight:bold;">Accommodation:</td><td>' + _f("accommodation", "Not specified") + '</td></tr>'
        )
        if is_paid_intent:
            rows_html += '<tr><td style="padding:6px 0;font-weight:bold;">Payment:</td><td>' + pm_display + '</td></tr>'

        commission_note = ""
        if is_paid_intent:
            commission_note = (
                '<div style="margin-top:16px;padding:14px;background:#fffdf5;border-radius:8px;border:2px solid #c4a35a;">'
                '<strong style="color:#c4a35a;">💰 Paid-intent reservation</strong><br>'
                'Commission will land once James confirms payment receipt.</div>'
            )

        html = (
            '<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">'
            '<div style="background:' + header_color + ';color:#faf9f5;padding:20px;text-align:center;">'
            '<h1 style="margin:0;font-size:20px;">' + header_label + '</h1>'
            '<div style="margin-top:6px;opacity:0.85;font-size:14px;">From your ref code <strong>' + code + '</strong></div></div>'
            '<div style="padding:20px;background:#f0f4ec;">'
            '<p style="margin-top:0;">Hi <strong>' + partner_name + '</strong>,</p>'
            '<p>Someone just used your referral code on zenvillagecr.com/reset.</p>'
            '<table style="width:100%;border-collapse:collapse;background:white;padding:12px;border-radius:8px;">'
            + rows_html +
            '</table>'
            + commission_note +
            '<div style="margin-top:20px;text-align:center;">'
            '<a href="' + dashboard_url + '" style="display:inline-block;padding:12px 24px;background:#1a2e1a;color:#faf9f5;text-decoration:none;border-radius:8px;font-weight:bold;">'
            'See all your leads + commissions →</a></div>'
            '<p style="margin-top:20px;font-size:13px;color:#666;">Questions? Reply to this email — it goes to James.</p>'
            '<p style="font-size:13px;color:#666;text-align:center;margin-top:30px;">— Zen Village</p>'
            '</div></body></html>'
        )

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP("localhost", 25) as server:
            server.sendmail(msg["From"], [partner_email], msg.as_string())
        print("partner notify sent: " + code + " → " + partner_email)
        return True
    except Exception as e:
        print("Partner notify failed: " + str(e))
        return False


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

        recipients = [msg["To"]] + list(CO_STEWARDS)
        with smtplib.SMTP("localhost", 25) as server:
            server.sendmail(msg["From"], recipients, msg.as_string())
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
    background_tasks.add_task(notify_partner_on_referral, inquiry_data)

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

"""
Zen Village Inquiry Handler
Receives booking inquiries and:
1. Saves to database
2. Sends email notification to james@fullpotential.com
3. Returns confirmation to user with payment instructions
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

router = APIRouter()

DATA_DIR = Path("/opt/fpai/apps/zen-village/data")
DATA_DIR.mkdir(exist_ok=True)
INQUIRIES_FILE = DATA_DIR / "inquiries.json"

PAYMENT_METHODS = {
    "paypal": {"name": "PayPal", "address": "james@fullpotential.com"},
    "venmo": {"name": "Venmo", "address": "@James-Stinson-65"},
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

def send_email_notification(inquiry: dict):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"New {inquiry['inquiry_type']} Inquiry: {inquiry['name']}"
        msg["From"] = "noreply@zenvillagecr.com"
        msg["To"] = "james@fullpotential.com"

        pm = inquiry.get('payment_method', 'not specified')
        pm_info = PAYMENT_METHODS.get(pm, {})
        pm_display = pm_info.get('name', pm) if pm_info else pm
        
        text = f"""
NEW ZEN VILLAGE BOOKING INQUIRY
=================================
Type: {inquiry['inquiry_type']}
Name: {inquiry['name']}
Email: {inquiry['email']}
Phone: {inquiry.get('phone', 'Not provided')}
Dates: {inquiry.get('dates', 'Flexible')}
Guests: {inquiry.get('guests', 'Not specified')}
Accommodation: {inquiry.get('accommodation', 'Not specified')}
Payment Method: {pm_display}
Partner Code: {inquiry.get('partner_code', 'Direct')}

Message:
{inquiry.get('message', 'No message')}

---
Received: {inquiry['timestamp']}
Reply to: {inquiry['email']}
"""
        
        html = f"""<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
<div style="background:#1a2e1a;color:#faf9f5;padding:20px;text-align:center;">
    <h1 style="margin:0;">New {inquiry['inquiry_type']} Inquiry</h1>
</div>
<div style="padding:20px;background:#f0f4ec;">
    <table style="width:100%;border-collapse:collapse;">
        <tr><td style="padding:8px 0;font-weight:bold;width:140px;">Name:</td><td>{inquiry['name']}</td></tr>
        <tr><td style="padding:8px 0;font-weight:bold;">Email:</td><td><a href="mailto:{inquiry['email']}">{inquiry['email']}</a></td></tr>
        <tr><td style="padding:8px 0;font-weight:bold;">Phone:</td><td>{inquiry.get('phone', 'Not provided')}</td></tr>
        <tr><td style="padding:8px 0;font-weight:bold;">Dates:</td><td>{inquiry.get('dates', 'Flexible')}</td></tr>
        <tr><td style="padding:8px 0;font-weight:bold;">Guests:</td><td>{inquiry.get('guests', 'Not specified')}</td></tr>
        <tr><td style="padding:8px 0;font-weight:bold;">Accommodation:</td><td>{inquiry.get('accommodation', 'Not specified')}</td></tr>
        <tr><td style="padding:8px 0;font-weight:bold;">Partner:</td><td>{inquiry.get('partner_code', 'Direct')}</td></tr>
    </table>
    
    <div style="margin-top:16px;padding:14px;background:#fffdf5;border-radius:8px;border:2px solid #c4a35a;">
        <strong style="color:#c4a35a;">💰 Payment: {pm_display}</strong>
    </div>
    
    <div style="margin-top:16px;padding:15px;background:white;border-radius:8px;">
        <strong>Message:</strong><br>{inquiry.get('message', 'No message')}
    </div>
    
    <div style="margin-top:20px;text-align:center;">
        <a href="mailto:{inquiry['email']}?subject=Re: Your Zen Village Booking" 
           style="display:inline-block;padding:12px 24px;background:#c4a35a;color:#1a2e1a;text-decoration:none;border-radius:8px;font-weight:bold;">
            Reply to {inquiry['name']}
        </a>
    </div>
</div>
</body></html>"""
        
        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))
        
        with smtplib.SMTP("localhost", 25) as server:
            server.sendmail(msg["From"], [msg["To"]], msg.as_string())
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False

@router.post("/submit")
async def submit_inquiry(inquiry: InquiryRequest, background_tasks: BackgroundTasks):
    inquiry_data = {
        "id": f"inq_{datetime.now().strftime('%Y%m%d%H%M%S')}",
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
    background_tasks.add_task(send_email_notification, inquiry_data)

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

@router.get("/test")
async def test_email():
    test_inquiry = {
        "id": "test", "name": "Test User", "email": "test@test.com",
        "inquiry_type": "Test", "dates": "Test", "guests": "Test",
        "accommodation": "Test", "message": "This is a test email.",
        "phone": "N/A", "payment_method": "paypal",
        "partner_code": None, "timestamp": datetime.now().isoformat()
    }
    success = send_email_notification(test_inquiry)
    return {"email_sent": success}

@router.get("/payment-methods")
async def get_payment_methods():
    """Public endpoint returning accepted payment methods"""
    return {"payment_methods": PAYMENT_METHODS}

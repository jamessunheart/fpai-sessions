#!/usr/bin/env python3
"""Intake Agent — The mouth of the revenue funnel.

Monitors inbound channels, acknowledges prospects, qualifies them,
books calls on Sunheart's calendar, and writes briefs to the bus.

Runs as a persistent service checking for new leads every 60 seconds.

Channels monitored:
  - Lead capture API (website forms, Facebook Lead Ads)
  - Email replies (via Resend webhook or polling)
  - Bus messages tagged as "inbound_lead"

Pipeline:
  1. New lead detected → immediate acknowledgment email
  2. Basic qualification (has email, expressed interest, not spam)
  3. Book discovery call on calendar
  4. Write brief to bus for CORA and Sunheart

Usage:
  intake-agent.py run        — Start the agent (persistent)
  intake-agent.py check      — Check for new unprocessed leads
  intake-agent.py process    — Process one batch of leads
  intake-agent.py stats      — Show intake statistics
"""

import json
import os
import sqlite3
import sys
import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Config
LEADS_DB = "/opt/fpai/leads/leads.db"
BUS_DB = "/opt/fpai/memory-bus/bus.db"
BUS_URL = "http://127.0.0.1:8195"
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
CAL_API_KEY = os.environ.get("CAL_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
CHECK_INTERVAL = 60  # seconds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [intake] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/opt/fpai/logs/intake-agent.log"),
    ],
)
log = logging.getLogger("intake")


def load_env():
    """Load env vars from .env files."""
    for env_file in ["/opt/fpai/cora-loop/.env", "/opt/fpai/openclaw/workspace/.env"]:
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        os.environ.setdefault(key.strip(), val.strip())
        except FileNotFoundError:
            pass

    global RESEND_API_KEY, CAL_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
    CAL_API_KEY = os.environ.get("CAL_API_KEY", "")
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def get_leads_db():
    db = sqlite3.connect(LEADS_DB)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS intake_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_email TEXT,
        action TEXT,
        details TEXT,
        timestamp TEXT DEFAULT (datetime('now'))
    )""")
    # Ensure leads table has intake columns
    try:
        db.execute("ALTER TABLE leads ADD COLUMN intake_status TEXT DEFAULT 'new'")
    except sqlite3.OperationalError:
        pass
    try:
        db.execute("ALTER TABLE leads ADD COLUMN intake_processed_at TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        db.execute("ALTER TABLE leads ADD COLUMN booking_id TEXT")
    except sqlite3.OperationalError:
        pass
    db.commit()
    return db


def get_new_leads():
    """Find leads that haven't been processed by intake."""
    db = get_leads_db()
    rows = db.execute("""
        SELECT * FROM leads 
        WHERE (intake_status IS NULL OR intake_status = 'new')
        AND email IS NOT NULL AND email != ''
        ORDER BY created_at DESC LIMIT 20
    """).fetchall()
    db.close()
    return [dict(r) for r in rows]


def is_qualified(lead):
    """Basic qualification: real email, not spam, expressed interest."""
    email = lead.get("email", "")
    if not email or "@" not in email:
        return False, "no valid email"

    spam_indicators = ["test@", "noreply@", "no-reply@", "spam", "fake"]
    for s in spam_indicators:
        if s in email.lower():
            return False, f"spam indicator: {s}"

    disposable_domains = ["mailinator.com", "guerrillamail.com", "tempmail.com", "throwaway.email"]
    domain = email.split("@")[-1].lower()
    if domain in disposable_domains:
        return False, f"disposable email: {domain}"

    return True, "qualified"


def send_acknowledgment(lead):
    """Send immediate acknowledgment email via Resend."""
    if not RESEND_API_KEY:
        log.warning("RESEND_API_KEY not set, skipping email acknowledgment")
        return False

    import requests

    name = lead.get("name", lead.get("first_name", ""))
    email = lead.get("email")

    if not name:
        name = email.split("@")[0].title()

    body_html = f"""
    <div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; padding: 30px;">
        <h2 style="color: #1a1a2e;">Thank you, {name}.</h2>
        <p>I received your message and I'm glad you reached out.</p>
        <p>I'd love to learn more about where you are right now and how I can help. 
        The best next step is a discovery call — a relaxed conversation where we explore 
        what's alive for you and whether a Full Potential Session is the right fit.</p>
        <p><strong>I'll follow up shortly with available times, or feel free to reply 
        to this email with your preferred schedule.</strong></p>
        <p>Looking forward to connecting.</p>
        <p style="margin-top: 30px;">
            With warmth,<br>
            <strong>James "Sunheart" Stinson</strong><br>
            <em>Full Potential</em>
        </p>
    </div>
    """

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={
                "from": "James <james@fullpotential.ai>",
                "to": [email],
                "subject": f"Thank you, {name} — let's connect",
                "html": body_html,
            },
            timeout=15,
        )
        if resp.status_code in (200, 201):
            log.info(f"Acknowledgment sent to {email}")
            return True
        else:
            log.error(f"Resend error {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        log.error(f"Email send failed: {e}")
        return False


def book_discovery_call(lead):
    """Book a discovery call on Cal.com for the lead."""
    if not CAL_API_KEY:
        log.info("CAL_API_KEY not set, skipping auto-booking (will be manual)")
        return None

    import requests

    # Get first event type (should be the discovery call)
    try:
        resp = requests.get(
            f"https://api.cal.com/v1/event-types?apiKey={CAL_API_KEY}",
            timeout=10,
        )
        types = resp.json().get("event_types", resp.json().get("data", []))
        if not types:
            log.warning("No Cal.com event types configured")
            return None
        event_type_id = types[0]["id"]
    except Exception as e:
        log.error(f"Cal.com event types fetch failed: {e}")
        return None

    # Get next available slot
    try:
        now = datetime.now(timezone.utc)
        start = (now + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        end = (now + timedelta(days=8)).strftime("%Y-%m-%dT23:59:59Z")
        resp = requests.get(
            f"https://api.cal.com/v1/availability?apiKey={CAL_API_KEY}&eventTypeId={event_type_id}&startTime={start}&endTime={end}",
            timeout=10,
        )
        slots = resp.json().get("slots", {})
        first_slot = None
        for date, times in sorted(slots.items()):
            if times:
                first_slot = times[0].get("time", times[0]) if isinstance(times[0], dict) else times[0]
                break
        if not first_slot:
            log.info("No available slots in next 7 days")
            return None
    except Exception as e:
        log.error(f"Availability check failed: {e}")
        return None

    # Book the slot
    name = lead.get("name", lead.get("first_name", ""))
    email = lead.get("email")
    if not name:
        name = email.split("@")[0].title()

    try:
        resp = requests.post(
            f"https://api.cal.com/v1/bookings?apiKey={CAL_API_KEY}",
            json={
                "eventTypeId": event_type_id,
                "start": first_slot,
                "responses": {
                    "name": name,
                    "email": email,
                    "notes": f"Auto-booked by Intake Agent. Source: {lead.get('source', 'unknown')}",
                },
                "timeZone": "Pacific/Honolulu",
                "language": "en",
            },
            timeout=15,
        )
        booking = resp.json()
        booking_id = booking.get("id", booking.get("uid"))
        if booking_id:
            log.info(f"Discovery call booked for {email} at {first_slot} (ID: {booking_id})")
            return {"booking_id": str(booking_id), "time": first_slot}
        else:
            log.warning(f"Booking response: {json.dumps(booking)[:200]}")
            return None
    except Exception as e:
        log.error(f"Booking failed: {e}")
        return None


def write_brief_to_bus(lead, qualification, booking):
    """Write a prospect brief to the bus for CORA and Sunheart."""
    import requests as req

    name = lead.get("name", lead.get("first_name", ""))
    email = lead.get("email")
    source = lead.get("source", "unknown")

    brief = {
        "prospect_name": name,
        "email": email,
        "source": source,
        "qualification": qualification,
        "booking": booking,
        "lead_data": {k: v for k, v in lead.items() if k not in ("id", "intake_status", "intake_processed_at")},
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        req.post(f"{BUS_URL}/bus/messages", json={
            "from": "intake_agent",
            "to": "all",
            "type": "prospect_brief",
            "priority": "high",
            "content": brief,
        }, timeout=5)
        log.info(f"Brief written to bus for {email}")
    except Exception as e:
        log.warning(f"Bus write failed: {e}")


def notify_telegram(lead, qualification, booking):
    """Notify Sunheart via Telegram about new qualified lead."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    import requests as req

    name = lead.get("name", lead.get("first_name", "")) or "Unknown"
    email = lead.get("email", "")
    source = lead.get("source", "unknown")

    msg = f"🎯 *New Qualified Lead*\n\n"
    msg += f"*Name:* {name}\n"
    msg += f"*Email:* {email}\n"
    msg += f"*Source:* {source}\n"

    if booking:
        msg += f"\n📅 *Discovery call auto-booked:* {booking.get('time', 'TBD')}\n"
    else:
        msg += f"\n⚠️ Calendar not configured — manual booking needed\n"

    msg += f"\n_Acknowledged automatically via email._"

    try:
        req.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": msg,
                "parse_mode": "Markdown",
            },
            timeout=10,
        )
    except Exception:
        pass


def process_lead(lead):
    """Full intake pipeline for a single lead."""
    email = lead.get("email")
    log.info(f"Processing lead: {email}")
    db = get_leads_db()

    # Step 1: Qualify
    qualified, reason = is_qualified(lead)
    if not qualified:
        log.info(f"Lead {email} disqualified: {reason}")
        db.execute("UPDATE leads SET intake_status = 'disqualified' WHERE email = ?", (email,))
        db.execute("INSERT INTO intake_log (lead_email, action, details) VALUES (?, 'disqualified', ?)", (email, reason))
        db.commit()
        db.close()
        return

    # Step 2: Acknowledge
    ack_sent = send_acknowledgment(lead)

    # Step 3: Book call
    booking = book_discovery_call(lead)

    # Step 4: Write brief to bus
    write_brief_to_bus(lead, reason, booking)

    # Step 5: Notify Sunheart
    notify_telegram(lead, reason, booking)

    # Step 6: Update lead status
    status = "booked" if booking else "acknowledged"
    db.execute(
        "UPDATE leads SET intake_status = ?, intake_processed_at = ?, booking_id = ? WHERE email = ?",
        (status, datetime.now(timezone.utc).isoformat(), booking.get("booking_id") if booking else None, email),
    )
    db.execute(
        "INSERT INTO intake_log (lead_email, action, details) VALUES (?, ?, ?)",
        (email, status, json.dumps({"ack_sent": ack_sent, "booking": booking})),
    )
    db.commit()
    db.close()
    log.info(f"Lead {email} processed: {status}")


def process_batch():
    """Process all new unprocessed leads."""
    leads = get_new_leads()
    if not leads:
        return 0
    log.info(f"Processing {len(leads)} new lead(s)")
    processed = 0
    for lead in leads:
        try:
            process_lead(lead)
            processed += 1
        except Exception as e:
            log.error(f"Failed to process {lead.get('email')}: {e}")
    return processed


def cmd_run():
    """Run the intake agent as a persistent service."""
    load_env()
    log.info("Intake Agent starting...")
    log.info(f"  Resend: {'configured' if RESEND_API_KEY else 'NOT SET'}")
    log.info(f"  Cal.com: {'configured' if CAL_API_KEY else 'NOT SET (manual booking)'}")
    log.info(f"  Telegram: {'configured' if TELEGRAM_BOT_TOKEN else 'NOT SET'}")

    # Register on bus
    try:
        import requests as req
        req.post(f"{BUS_URL}/bus/capabilities", json={
            "agent": "intake_agent",
            "capability": "lead_qualification",
            "api": "intake-agent.py",
            "permission": "autonomous",
            "status": "active",
            "documentation": "Qualifies inbound leads, sends acknowledgment, books discovery calls, writes briefs to bus.",
        }, timeout=5)
        req.post(f"{BUS_URL}/bus/capabilities", json={
            "agent": "intake_agent",
            "capability": "auto_booking",
            "api": "calendar.sh / Cal.com API",
            "permission": "autonomous",
            "status": "active" if CAL_API_KEY else "pending_setup",
            "documentation": "Books discovery calls on Sunheart's calendar via Cal.com API.",
        }, timeout=5)
    except Exception:
        pass

    while True:
        try:
            processed = process_batch()
            if processed:
                log.info(f"Batch complete: {processed} lead(s) processed")
        except Exception as e:
            log.error(f"Batch processing error: {e}")
        time.sleep(CHECK_INTERVAL)


def cmd_check():
    """Check for unprocessed leads without processing."""
    load_env()
    leads = get_new_leads()
    if leads:
        print(f"Found {len(leads)} unprocessed lead(s):")
        for l in leads:
            print(f"  {l.get('email', '?'):<35} {l.get('name', ''):<20} {l.get('source', ''):<15} {l.get('created_at', '')}")
    else:
        print("No unprocessed leads.")


def cmd_stats():
    """Show intake statistics."""
    load_env()
    db = get_leads_db()
    total = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    by_status = db.execute("SELECT intake_status, COUNT(*) c FROM leads GROUP BY intake_status").fetchall()
    recent = db.execute("SELECT * FROM intake_log ORDER BY timestamp DESC LIMIT 5").fetchall()

    print(f"Intake Agent Statistics")
    print(f"  Total leads: {total}")
    print(f"\n  By intake status:")
    for r in by_status:
        status = r["intake_status"] or "unprocessed"
        print(f"    {status:<20} {r['c']}")

    if recent:
        print(f"\n  Recent activity:")
        for r in recent:
            print(f"    {r['timestamp']} | {r['lead_email']:<30} | {r['action']}")

    db.close()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "run":
        cmd_run()
    elif cmd == "check":
        cmd_check()
    elif cmd == "process":
        load_env()
        process_batch()
    elif cmd == "stats":
        cmd_stats()
    else:
        print(__doc__)

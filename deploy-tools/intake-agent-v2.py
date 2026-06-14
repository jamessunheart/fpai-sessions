#!/usr/bin/env python3
"""Intake Agent v2 — The mouth of the revenue funnel.

Full pipeline: Detect → Acknowledge (5 min) → Qualify → Book → Brief → Follow-up

Usage:
  intake-agent-v2.py run           — Start persistent service
  intake-agent-v2.py check         — Check for unprocessed leads
  intake-agent-v2.py brief <email> — Generate pre-session brief for a lead
  intake-agent-v2.py followup <email> <notes> — Send post-session follow-up
  intake-agent-v2.py stats         — Pipeline statistics
"""

import json
import os
import sqlite3
import sys
import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

BUS_URL = "http://127.0.0.1:8195"
LEADS_DB = "/opt/fpai/leads/leads.db"
CHECK_INTERVAL = 30  # Check every 30 seconds for fast response

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


def env(key, default=""):
    return os.environ.get(key, default)


def get_db():
    db = sqlite3.connect(LEADS_DB)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS intake_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_email TEXT,
            action TEXT,
            details TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS session_briefs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_email TEXT,
            brief_text TEXT,
            sent_at TEXT,
            booking_time TEXT
        );
        CREATE TABLE IF NOT EXISTS followups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_email TEXT,
            session_notes TEXT,
            followup_sent_at TEXT,
            retainer_offered INTEGER DEFAULT 0
        );
    """)
    for col_def in [
        ("leads", "intake_status", "TEXT DEFAULT 'new'"),
        ("leads", "intake_processed_at", "TEXT"),
        ("leads", "booking_id", "TEXT"),
        ("leads", "booking_time", "TEXT"),
        ("leads", "qualifying_answers", "TEXT"),
        ("leads", "qualification_score", "INTEGER"),
        ("leads", "brief_sent", "INTEGER DEFAULT 0"),
    ]:
        try:
            db.execute(f"ALTER TABLE {col_def[0]} ADD COLUMN {col_def[1]} {col_def[2]}")
        except sqlite3.OperationalError:
            pass
    db.commit()
    return db


# ─── QUALIFICATION ───

def qualify_lead(lead):
    """Score a lead 0-100 based on qualifying answers and data quality."""
    score = 0
    reasons = []

    email = lead.get("email", "")
    if not email or "@" not in email:
        return 0, "no valid email"

    spam_indicators = ["test@", "noreply@", "spam", "fake@"]
    if any(s in email.lower() for s in spam_indicators):
        return 0, "spam"

    disposable = ["mailinator.com", "guerrillamail.com", "tempmail.com", "throwaway.email", "yopmail.com"]
    if email.split("@")[-1].lower() in disposable:
        return 0, "disposable email"

    score += 20
    reasons.append("valid email")

    name = lead.get("name", "")
    if name and len(name) > 2:
        score += 10
        reasons.append("has name")

    source = lead.get("source", "")
    if source == "fullpotential.ai/call":
        score += 20
        reasons.append("applied via /call form")

    # Parse qualifying answers
    answers = {}
    qa_raw = lead.get("qualifying_answers", "")
    if qa_raw:
        try:
            answers = json.loads(qa_raw) if isinstance(qa_raw, str) else qa_raw
        except (json.JSONDecodeError, TypeError):
            pass

    message = lead.get("message", "")

    if answers.get("navigating") or (message and "NAVIGATING:" in message):
        nav = answers.get("navigating", "")
        if not nav and message:
            parts = message.split("NAVIGATING:")
            if len(parts) > 1:
                nav = parts[1].split("INVESTMENT VALUE:")[0].strip()
        if len(nav) > 20:
            score += 20
            reasons.append("shared what they're navigating")
        elif nav:
            score += 10
            reasons.append("brief navigating answer")

    if answers.get("investment_value") or (message and "INVESTMENT VALUE:" in message):
        val = answers.get("investment_value", "")
        if not val and message:
            parts = message.split("INVESTMENT VALUE:")
            if len(parts) > 1:
                val = parts[1].split("READINESS:")[0].strip()
        if len(val) > 20:
            score += 15
            reasons.append("articulated desired outcome")

    if answers.get("readiness") or (message and "READINESS:" in message):
        ready = answers.get("readiness", "")
        if not ready and message:
            parts = message.split("READINESS:")
            if len(parts) > 1:
                ready = parts[1].strip()
        if len(ready) > 10:
            score += 15
            reasons.append("expressed readiness")

    return min(score, 100), ", ".join(reasons)


# ─── EMAIL RESPONSES ───

def send_email(to, subject, html_body):
    """Send email via Resend."""
    api_key = env("RESEND_API_KEY")
    if not api_key:
        log.warning("RESEND_API_KEY not set — email not sent")
        return False
    try:
        import requests
        resp = requests.post("https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "from": "James <james@fullpotential.ai>",
                "to": [to],
                "subject": subject,
                "html": html_body,
            }, timeout=15)
        if resp.status_code in (200, 201):
            log.info(f"Email sent to {to}: {subject}")
            return True
        log.error(f"Resend error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log.error(f"Email failed: {e}")
    return False


def send_acknowledgment(lead, score):
    """Warm acknowledgment within 5 minutes of submission."""
    name = lead.get("name", "").split()[0] if lead.get("name") else ""
    if not name:
        name = lead.get("email", "").split("@")[0].title()
    email = lead["email"]

    if score >= 50:
        # Qualified — warm personal response
        html = f"""
        <div style="font-family: Georgia, serif; max-width: 580px; margin: 0 auto; padding: 30px; color: #333;">
            <p style="font-size: 1.1rem;">{name},</p>
            <p>Thank you for reaching out. I read what you shared and I can already see there's real depth here.</p>
            <p>I'd love to have a conversation. A Full Potential Session is 90 minutes where we go deep
            into all nine dimensions of your life — not surface level, not generic advice. I see the whole
            picture and reflect back what's possible.</p>
            <p><strong>I'll follow up shortly with available times for your session.</strong></p>
            <p>In the meantime, the best preparation is simple: come ready to be honest about where you
            actually are, not where you think you should be.</p>
            <p style="margin-top: 30px;">Looking forward to meeting you,<br>
            <strong>James "Sunheart" Stinson</strong><br>
            <em>Full Potential</em></p>
        </div>"""
        subject = f"{name} — let's go deep"
    else:
        # Lower score — still warm but less committal
        html = f"""
        <div style="font-family: Georgia, serif; max-width: 580px; margin: 0 auto; padding: 30px; color: #333;">
            <p style="font-size: 1.1rem;">Hi {name},</p>
            <p>Thank you for your interest in Full Potential. I appreciate you reaching out.</p>
            <p>I'd love to learn more about what you're looking for. Could you share a bit more about
            what you're navigating right now and what kind of support would be most valuable?</p>
            <p>You can reply directly to this email.</p>
            <p style="margin-top: 30px;">Warmly,<br>
            <strong>James "Sunheart" Stinson</strong><br>
            <em>Full Potential</em></p>
        </div>"""
        subject = f"Thank you, {name}"

    return send_email(email, subject, html)


# ─── CALENDAR BOOKING ───

def book_session(lead):
    """Book a discovery call on Cal.com."""
    api_key = env("CAL_API_KEY")
    if not api_key:
        log.info("CAL_API_KEY not set — manual booking needed")
        return None
    try:
        import requests
        # Get event types
        resp = requests.get(f"https://api.cal.com/v1/event-types?apiKey={api_key}", timeout=10)
        types = resp.json().get("event_types", resp.json().get("data", []))
        if not types:
            return None
        event_type_id = types[0]["id"]

        # Find next available slot
        now = datetime.now(timezone.utc)
        start = (now + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        end = (now + timedelta(days=8)).strftime("%Y-%m-%dT23:59:59Z")
        resp = requests.get(
            f"https://api.cal.com/v1/availability?apiKey={api_key}&eventTypeId={event_type_id}&startTime={start}&endTime={end}",
            timeout=10)
        slots = resp.json().get("slots", {})

        first_slot = None
        for date, times in sorted(slots.items()):
            if times:
                first_slot = times[0].get("time", times[0]) if isinstance(times[0], dict) else times[0]
                break
        if not first_slot:
            return None

        name = lead.get("name", lead.get("email", "").split("@")[0].title())
        resp = requests.post(f"https://api.cal.com/v1/bookings?apiKey={api_key}",
            json={
                "eventTypeId": event_type_id,
                "start": first_slot,
                "responses": {
                    "name": name,
                    "email": lead["email"],
                    "notes": f"Full Potential Session application via {lead.get('source', 'unknown')}",
                },
                "timeZone": "Pacific/Honolulu",
                "language": "en",
            }, timeout=15)
        booking = resp.json()
        bid = booking.get("id", booking.get("uid"))
        if bid:
            log.info(f"Session booked: {lead['email']} at {first_slot}")
            return {"booking_id": str(bid), "time": first_slot}
    except Exception as e:
        log.error(f"Booking failed: {e}")
    return None


def send_booking_confirmation(lead, booking):
    """Send confirmation with prep instructions."""
    name = lead.get("name", "").split()[0] or lead["email"].split("@")[0].title()
    btime = booking["time"][:16].replace("T", " at ")

    html = f"""
    <div style="font-family: Georgia, serif; max-width: 580px; margin: 0 auto; padding: 30px; color: #333;">
        <h2 style="color: #1a1a2e; font-weight: 400;">You're booked, {name}.</h2>
        <p style="font-size: 1.1rem; background: #f8f6f3; padding: 16px; border-radius: 8px; border-left: 3px solid #c8a87c;">
            <strong>Full Potential Session</strong><br>
            {btime} (Hawaii time)<br>
            90 minutes, video call
        </p>
        <p style="margin-top: 24px;"><strong>How to prepare:</strong></p>
        <ul style="line-height: 1.8; color: #555;">
            <li>Find a quiet, private space where you won't be interrupted</li>
            <li>No preparation is required — come as you are</li>
            <li>The only thing I ask: be willing to be honest about where you actually are in life, not where you think you should be</li>
            <li>Have water nearby — 90 minutes of deep presence can be intense</li>
        </ul>
        <p>I'll send a video link the day before. If anything comes up, reply to this email.</p>
        <p style="margin-top: 30px;">See you soon,<br>
        <strong>James "Sunheart" Stinson</strong></p>
    </div>"""

    return send_email(lead["email"], f"Your Full Potential Session is confirmed — {btime}", html)


# ─── BUS COMMUNICATION ───

def bus_write(from_agent, to_agent, msg_type, content, priority="high"):
    try:
        import requests
        requests.post(f"{BUS_URL}/bus/messages", json={
            "from": from_agent, "to": to_agent, "type": msg_type,
            "content": content, "priority": priority,
        }, timeout=5)
    except Exception:
        pass


def write_prospect_brief(lead, score, reasons, booking):
    """Write a brief to the bus so CORA and Sunheart know who's coming."""
    answers = {}
    qa_raw = lead.get("qualifying_answers", "")
    if qa_raw:
        try:
            answers = json.loads(qa_raw) if isinstance(qa_raw, str) else qa_raw
        except (json.JSONDecodeError, TypeError):
            pass

    message = lead.get("message", "")
    navigating = answers.get("navigating", "")
    investment = answers.get("investment_value", "")
    readiness = answers.get("readiness", "")

    if not navigating and message and "NAVIGATING:" in message:
        parts = message.split("NAVIGATING:")
        if len(parts) > 1:
            navigating = parts[1].split("INVESTMENT VALUE:")[0].strip()
    if not investment and message and "INVESTMENT VALUE:" in message:
        parts = message.split("INVESTMENT VALUE:")
        if len(parts) > 1:
            investment = parts[1].split("READINESS:")[0].strip()
    if not readiness and message and "READINESS:" in message:
        parts = message.split("READINESS:")
        if len(parts) > 1:
            readiness = parts[1].strip()

    brief = {
        "prospect_name": lead.get("name", ""),
        "email": lead["email"],
        "source": lead.get("source", "unknown"),
        "qualification_score": score,
        "qualification_reasons": reasons,
        "navigating": navigating,
        "desired_outcome": investment,
        "readiness": readiness,
        "booking": booking,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }

    bus_write("intake_agent", "all", "prospect_brief", brief)


# ─── PRE-SESSION BRIEF ───

def generate_presession_brief(lead):
    """Compile everything known about a person into a one-page brief."""
    db = get_db()
    name = lead.get("name", lead.get("email", "").split("@")[0].title())
    email = lead["email"]

    answers = {}
    qa_raw = lead.get("qualifying_answers", "")
    if qa_raw:
        try:
            answers = json.loads(qa_raw) if isinstance(qa_raw, str) else qa_raw
        except (json.JSONDecodeError, TypeError):
            pass

    message = lead.get("message", "")
    navigating = answers.get("navigating", "")
    investment = answers.get("investment_value", "")
    readiness = answers.get("readiness", "")

    if not navigating and message and "NAVIGATING:" in message:
        navigating = message.split("NAVIGATING:")[1].split("INVESTMENT VALUE:")[0].strip() if "NAVIGATING:" in message else ""
    if not investment and message and "INVESTMENT VALUE:" in message:
        investment = message.split("INVESTMENT VALUE:")[1].split("READINESS:")[0].strip() if "INVESTMENT VALUE:" in message else ""
    if not readiness and message and "READINESS:" in message:
        readiness = message.split("READINESS:")[1].strip() if "READINESS:" in message else ""

    brief_lines = [
        f"PRE-SESSION BRIEF: {name}",
        f"{'='*40}",
        f"Email: {email}",
        f"Source: {lead.get('source', 'unknown')}",
        f"Qualification score: {lead.get('qualification_score', '?')}/100",
        f"Booked: {lead.get('booking_time', 'TBD')}",
        "",
        "WHAT THEY'RE NAVIGATING:",
        navigating or "(not shared)",
        "",
        "WHAT WOULD MAKE THIS WORTH IT:",
        investment or "(not shared)",
        "",
        "READINESS LEVEL:",
        readiness or "(not shared)",
        "",
        "WHAT TO WATCH FOR:",
    ]

    if navigating:
        transition_words = ["transition", "change", "leaving", "starting", "ending", "divorce", "career"]
        if any(w in navigating.lower() for w in transition_words):
            brief_lines.append("- In active transition — may need grounding before depth")
        relationship_words = ["relationship", "partner", "marriage", "family", "love"]
        if any(w in navigating.lower() for w in relationship_words):
            brief_lines.append("- Relationship dimension likely central — approach with care")
        purpose_words = ["purpose", "meaning", "direction", "lost", "stuck", "unfulfilled"]
        if any(w in navigating.lower() for w in purpose_words):
            brief_lines.append("- Seeking direction/meaning — the Full Potential map will resonate")
        if not any(w in navigating.lower() for w in transition_words + relationship_words + purpose_words):
            brief_lines.append("- Listen for the underneath — what they wrote may not be the real question")

    brief_text = "\n".join(brief_lines)

    db.execute("INSERT INTO session_briefs (lead_email, brief_text, booking_time) VALUES (?, ?, ?)",
               (email, brief_text, lead.get("booking_time")))
    db.commit()
    db.close()
    return brief_text


def send_brief_to_telegram(brief_text):
    """Send the pre-session brief to Sunheart via Telegram."""
    token = env("TELEGRAM_BOT_TOKEN")
    chat_id = env("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    try:
        import requests
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": f"📋 {brief_text}", "parse_mode": "Markdown"},
            timeout=10)
        return True
    except Exception:
        return False


# ─── POST-SESSION FOLLOW-UP ───

def send_followup(lead, session_notes=""):
    """Send post-session follow-up: thank you + insights + retainer offer."""
    name = lead.get("name", "").split()[0] or lead.get("email", "").split("@")[0].title()
    email = lead["email"]

    notes_section = ""
    if session_notes:
        notes_section = f"""
        <div style="background: #f8f6f3; padding: 20px; border-radius: 8px; margin: 24px 0; border-left: 3px solid #c8a87c;">
            <p style="font-weight: 600; margin-bottom: 12px;">Key Insights from Your Session:</p>
            <p style="white-space: pre-line; line-height: 1.7;">{session_notes}</p>
        </div>"""

    html = f"""
    <div style="font-family: Georgia, serif; max-width: 580px; margin: 0 auto; padding: 30px; color: #333;">
        <p style="font-size: 1.1rem;">{name},</p>
        <p>Thank you for showing up the way you did today. That kind of honesty takes courage,
        and what I saw in you during our session was remarkable.</p>
        {notes_section}
        <p><strong>What I'd suggest as next steps:</strong></p>
        <ul style="line-height: 1.8; color: #555;">
            <li>Sit with what came up today — don't rush to "fix" anything</li>
            <li>Notice what shifts in the next 48 hours. Insights often land after the session, not during</li>
            <li>Journal anything that surfaces — dreams, memories, sudden clarity</li>
        </ul>

        <div style="margin-top: 32px; padding: 24px; background: #0a0a0f; color: #e8e4df; border-radius: 8px;">
            <p style="color: #c8a87c; font-weight: 600; margin-bottom: 12px;">Continue the Journey: Full Potential Assistant</p>
            <p style="font-size: 0.95rem; line-height: 1.7;">
                What we uncovered today is the beginning, not the end. The Full Potential Assistant
                is an ongoing partnership — AI-powered support backed by real humans — that keeps
                the momentum going. Weekly check-ins, action tracking, and someone in your corner
                making sure the insights from today become lasting change.
            </p>
            <p style="margin-top: 12px; font-size: 0.95rem;">
                If you're interested, just reply to this email and I'll share more details.
            </p>
        </div>

        <p style="margin-top: 30px;">Honored to walk with you,<br>
        <strong>James "Sunheart" Stinson</strong><br>
        <em>Full Potential</em></p>
    </div>"""

    sent = send_email(email, f"{name} — what came alive today", html)

    if sent:
        db = get_db()
        db.execute("INSERT INTO followups (lead_email, session_notes, followup_sent_at, retainer_offered) VALUES (?, ?, ?, 1)",
                   (email, session_notes, datetime.now(timezone.utc).isoformat()))
        db.commit()
        db.close()
        bus_write("intake_agent", "cora", "followup_sent", {
            "prospect": name, "email": email,
            "retainer_offered": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    return sent


# ─── TELEGRAM NOTIFICATIONS ───

def notify_sunheart(lead, score, booking):
    token = env("TELEGRAM_BOT_TOKEN")
    chat_id = env("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return

    name = lead.get("name", "") or "Unknown"
    email = lead.get("email", "")
    source = lead.get("source", "unknown")

    answers = {}
    qa_raw = lead.get("qualifying_answers", "")
    if qa_raw:
        try:
            answers = json.loads(qa_raw) if isinstance(qa_raw, str) else qa_raw
        except (json.JSONDecodeError, TypeError):
            pass
    navigating = answers.get("navigating", "")[:150]

    stars = "⭐" * (score // 20) if score > 0 else "?"

    msg = f"🎯 *New Session Application*\n\n"
    msg += f"*{name}* ({email})\n"
    msg += f"Source: {source}\n"
    msg += f"Score: {score}/100 {stars}\n"
    if navigating:
        msg += f"\n_Navigating: {navigating}_\n"
    if booking:
        msg += f"\n📅 *Auto-booked:* {booking['time'][:16]}\n"
    elif score >= 50:
        msg += f"\n⚠️ Calendar not set up — book manually\n"
    else:
        msg += f"\nAwaiting more info before booking.\n"

    try:
        import requests
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except Exception:
        pass


# ─── MAIN PIPELINE ───

def process_lead(lead):
    """Full intake pipeline for a single lead."""
    email = lead["email"]
    log.info(f"Processing: {email}")
    db = get_db()

    # Step 1: Qualify
    score, reasons = qualify_lead(lead)
    if score == 0:
        log.info(f"Disqualified: {email} ({reasons})")
        db.execute("UPDATE leads SET intake_status='disqualified', intake_processed_at=? WHERE email=?",
                   (datetime.now(timezone.utc).isoformat(), email))
        db.execute("INSERT INTO intake_log (lead_email, action, details) VALUES (?,?,?)",
                   (email, "disqualified", reasons))
        db.commit()
        db.close()
        return

    # Save score
    db.execute("UPDATE leads SET qualification_score=? WHERE email=?", (score, email))
    db.commit()

    # Step 2: Acknowledge (within 5 minutes)
    ack = send_acknowledgment(lead, score)

    # Step 3: Book if qualified
    booking = None
    if score >= 50:
        booking = book_session(lead)
        if booking:
            db.execute("UPDATE leads SET booking_id=?, booking_time=? WHERE email=?",
                       (booking["booking_id"], booking["time"], email))
            db.commit()
            send_booking_confirmation(lead, booking)

            # Generate and store pre-session brief
            brief = generate_presession_brief(lead)
            db.execute("UPDATE leads SET brief_sent=0 WHERE email=?", (email,))
            db.commit()

            # Record as revenue event on bus
            bus_write("intake_agent", "cora", "revenue_event", {
                "type": "call_booked",
                "prospect": lead.get("name", email),
                "email": email,
                "booking_time": booking["time"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    # Step 4: Write brief to bus
    write_prospect_brief(lead, score, reasons, booking)

    # Step 5: Notify Sunheart
    notify_sunheart(lead, score, booking)

    # Step 6: Update status
    status = "booked" if booking else ("qualified" if score >= 50 else "acknowledged")
    db.execute("UPDATE leads SET intake_status=?, intake_processed_at=? WHERE email=?",
               (status, datetime.now(timezone.utc).isoformat(), email))
    db.execute("INSERT INTO intake_log (lead_email, action, details) VALUES (?,?,?)",
               (email, status, json.dumps({"score": score, "reasons": reasons, "ack": ack, "booking": booking})))
    db.commit()
    db.close()
    log.info(f"Processed: {email} → {status} (score: {score})")


def check_upcoming_briefs():
    """Send pre-session briefs 30 minutes before booked calls."""
    db = get_db()
    now = datetime.now(timezone.utc)
    window_start = now + timedelta(minutes=25)
    window_end = now + timedelta(minutes=35)

    rows = db.execute("""
        SELECT l.*, sb.brief_text FROM leads l
        JOIN session_briefs sb ON l.email = sb.lead_email
        WHERE l.brief_sent = 0 AND l.booking_time IS NOT NULL
    """).fetchall()

    for r in rows:
        try:
            bt = datetime.fromisoformat(r["booking_time"].replace("Z", "+00:00"))
            if window_start <= bt <= window_end:
                sent = send_brief_to_telegram(r["brief_text"])
                if sent:
                    db.execute("UPDATE leads SET brief_sent=1 WHERE email=?", (r["email"],))
                    db.commit()
                    log.info(f"Pre-session brief sent for {r['email']}")
        except (ValueError, TypeError):
            pass
    db.close()


def get_new_leads():
    db = get_db()
    rows = db.execute("""
        SELECT * FROM leads
        WHERE (intake_status IS NULL OR intake_status = 'new')
        AND email IS NOT NULL AND email != ''
        ORDER BY created_at DESC LIMIT 20
    """).fetchall()
    db.close()
    return [dict(r) for r in rows]


# ─── COMMANDS ───

def cmd_run():
    load_env()
    log.info("Intake Agent v2 starting...")
    log.info(f"  Resend: {'configured' if env('RESEND_API_KEY') else 'NOT SET'}")
    log.info(f"  Cal.com: {'configured' if env('CAL_API_KEY') else 'NOT SET'}")
    log.info(f"  Telegram: {'configured' if env('TELEGRAM_BOT_TOKEN') else 'NOT SET'}")
    log.info(f"  Check interval: {CHECK_INTERVAL}s")

    # Register capabilities
    try:
        import requests
        for cap in [
            ("lead_qualification", "Qualifies inbound leads with scoring (0-100) based on qualifying answers"),
            ("auto_booking", "Books discovery calls on calendar via Cal.com when lead scores 50+"),
            ("presession_brief", "Generates one-page brief about prospect, sends to Telegram 30min before call"),
            ("post_session_followup", "Sends thank-you, session insights, and retainer offer after sessions"),
        ]:
            requests.post(f"{BUS_URL}/bus/capabilities", json={
                "agent": "intake_agent", "capability": cap[0], "api": "intake-agent-v2.py",
                "permission": "autonomous", "status": "active", "documentation": cap[1],
            }, timeout=5)
    except Exception:
        pass

    while True:
        try:
            leads = get_new_leads()
            if leads:
                log.info(f"Processing {len(leads)} new lead(s)")
                for lead in leads:
                    try:
                        process_lead(lead)
                    except Exception as e:
                        log.error(f"Failed: {lead.get('email')}: {e}")

            check_upcoming_briefs()
        except Exception as e:
            log.error(f"Cycle error: {e}")

        time.sleep(CHECK_INTERVAL)


def cmd_brief(email):
    load_env()
    db = get_db()
    lead = db.execute("SELECT * FROM leads WHERE email=?", (email,)).fetchone()
    if not lead:
        print(f"Lead not found: {email}")
        return
    brief = generate_presession_brief(dict(lead))
    print(brief)
    sent = send_brief_to_telegram(brief)
    print(f"\nTelegram: {'sent' if sent else 'not sent'}")
    db.close()


def cmd_followup(email, notes=""):
    load_env()
    db = get_db()
    lead = db.execute("SELECT * FROM leads WHERE email=?", (email,)).fetchone()
    if not lead:
        print(f"Lead not found: {email}")
        return
    sent = send_followup(dict(lead), notes)
    print(f"Follow-up {'sent' if sent else 'failed'}")
    db.close()


def cmd_stats():
    load_env()
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    by_status = db.execute("SELECT intake_status, COUNT(*) c FROM leads GROUP BY intake_status ORDER BY c DESC").fetchall()
    booked = db.execute("SELECT COUNT(*) FROM leads WHERE intake_status='booked'").fetchone()[0]
    qualified = db.execute("SELECT COUNT(*) FROM leads WHERE qualification_score >= 50").fetchone()[0]
    briefs = db.execute("SELECT COUNT(*) FROM session_briefs").fetchone()[0]
    followups = db.execute("SELECT COUNT(*) FROM followups").fetchone()[0]

    print("Full Potential Intake Pipeline")
    print(f"  Total leads:     {total}")
    print(f"  Qualified (50+): {qualified}")
    print(f"  Booked:          {booked}")
    print(f"  Briefs generated:{briefs}")
    print(f"  Follow-ups sent: {followups}")
    print(f"\n  By status:")
    for r in by_status:
        print(f"    {(r['intake_status'] or 'new'):<20} {r['c']}")
    db.close()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "run":
        cmd_run()
    elif cmd == "check":
        load_env()
        leads = get_new_leads()
        print(f"{len(leads)} unprocessed leads" if leads else "No unprocessed leads")
        for l in leads:
            print(f"  {l['email']}")
    elif cmd == "brief":
        cmd_brief(sys.argv[2] if len(sys.argv) > 2 else "")
    elif cmd == "followup":
        cmd_followup(sys.argv[2] if len(sys.argv) > 2 else "",
                     " ".join(sys.argv[3:]) if len(sys.argv) > 3 else "")
    elif cmd == "stats":
        cmd_stats()
    else:
        print(__doc__)

#!/usr/bin/env python3
"""
AI-to-Human Communication Channel
==================================
Allows AI agents to email humans when:
- Blocked on a task requiring human intervention
- Need credentials/access that can't be obtained programmatically  
- Critical decisions that require human approval
- Mission completion notifications

Usage:
    python3 email_human.py --to james@fullpotential.ai --subject "Blocked: Need API Key" --body "I need..."
    
Or programmatically:
    from orchestration.tools.email_human import send_to_human
    send_to_human("Subject", "Body text", priority="high")
"""

import os
import smtplib
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

# Load environment
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / '.env')

# Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER") or os.getenv("EMAIL_USER")
SMTP_PASS = os.getenv("SMTP_PASS") or os.getenv("EMAIL_PASS") or os.getenv("EMAIL_APP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)
DEFAULT_TO = "james@fullpotential.ai"

# Log file for sent emails
LOG_FILE = Path(__file__).resolve().parent.parent.parent / "logs" / "ai_emails.log"
LOG_FILE.parent.mkdir(exist_ok=True)


def send_to_human(
    subject: str,
    body: str,
    to: str = DEFAULT_TO,
    priority: str = "normal",  # low, normal, high, critical
    context: dict = None,
) -> dict:
    """
    Send an email from AI to human.
    
    Args:
        subject: Email subject
        body: Email body (plain text)
        to: Recipient email
        priority: low, normal, high, critical
        context: Optional dict with additional context (mission_id, service, etc.)
    
    Returns:
        dict with status and message
    """
    
    # Build email
    msg = MIMEMultipart()
    msg['From'] = f"Full Potential AI <{FROM_EMAIL}>"
    msg['To'] = to
    msg['Subject'] = f"[FPAI {'🔴' if priority == 'critical' else '🟡' if priority == 'high' else ''}] {subject}"
    
    # Add priority header
    if priority in ("high", "critical"):
        msg['X-Priority'] = '1'
        msg['Importance'] = 'high'
    
    # Build body with context
    full_body = f"""
{body}

---
🤖 AI Communication Log
Timestamp: {datetime.now().isoformat()}
Priority: {priority.upper()}
"""
    
    if context:
        full_body += f"\nContext:\n"
        for k, v in context.items():
            full_body += f"  - {k}: {v}\n"
    
    full_body += """
---
This is an automated message from Full Potential AI.
The AI system has determined it needs human assistance.

To respond, reply to this email or access the Mission Hub:
https://fullpotential.ai/missions
"""
    
    msg.attach(MIMEText(full_body, 'plain'))
    
    # Log the attempt
    log_entry = f"{datetime.now().isoformat()} | TO: {to} | SUBJECT: {subject} | PRIORITY: {priority}\n"
    
    # Try to send
    if not SMTP_USER or not SMTP_PASS:
        # No SMTP configured - log locally and return instructions
        log_entry += "  STATUS: NOT SENT (SMTP not configured)\n"
        LOG_FILE.open('a').write(log_entry)
        
        return {
            "status": "not_configured",
            "message": "SMTP not configured. Email logged locally.",
            "setup_instructions": """
To enable email, add to .env:
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
FROM_EMAIL=ai@fullpotential.ai

For Gmail, create an App Password at:
https://myaccount.google.com/apppasswords
""",
            "logged_to": str(LOG_FILE),
            "would_send": {
                "to": to,
                "subject": msg['Subject'],
                "body": full_body,
            }
        }
    
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        
        log_entry += "  STATUS: SENT\n"
        LOG_FILE.open('a').write(log_entry)
        
        return {
            "status": "sent",
            "message": f"Email sent to {to}",
            "subject": msg['Subject'],
        }
        
    except Exception as e:
        log_entry += f"  STATUS: FAILED - {str(e)}\n"
        LOG_FILE.open('a').write(log_entry)
        
        return {
            "status": "failed",
            "error": str(e),
            "message": "Failed to send email. Check SMTP configuration.",
        }


def request_human_help(
    blocker: str,
    what_i_tried: str,
    what_i_need: str,
    mission_id: str = None,
    urgency: str = "normal",
) -> dict:
    """
    Structured request for human help.
    
    Args:
        blocker: What's blocking progress
        what_i_tried: What the AI has already attempted
        what_i_need: Specific ask from human
        mission_id: Related mission ID if applicable
        urgency: normal, high, critical
    """
    
    subject = f"Help Needed: {blocker[:50]}"
    
    body = f"""
🚨 AI ASSISTANCE REQUEST

## What's Blocking Me
{blocker}

## What I've Already Tried
{what_i_tried}

## What I Need From You
{what_i_need}

## Suggested Actions
1. Review the blocker above
2. Provide the requested information/access
3. Reply to this email OR update the mission at:
   https://fullpotential.ai/missions{f'/mission/{mission_id}' if mission_id else ''}
"""
    
    return send_to_human(
        subject=subject,
        body=body,
        priority=urgency,
        context={
            "mission_id": mission_id,
            "type": "help_request",
        }
    )


def notify_mission_complete(
    mission_id: str,
    summary: str,
    next_steps: list = None,
) -> dict:
    """Notify human that a mission was completed."""
    
    subject = f"✅ Mission {mission_id} Completed"
    
    body = f"""
🎉 MISSION COMPLETED

## Mission: {mission_id}

## Summary
{summary}

## Next Steps
"""
    if next_steps:
        for i, step in enumerate(next_steps, 1):
            body += f"{i}. {step}\n"
    else:
        body += "No follow-up actions required.\n"
    
    return send_to_human(
        subject=subject,
        body=body,
        priority="normal",
        context={
            "mission_id": mission_id,
            "type": "completion_notification",
        }
    )


# CLI interface
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-to-Human email communication")
    parser.add_argument("--to", default=DEFAULT_TO, help="Recipient email")
    parser.add_argument("--subject", required=True, help="Email subject")
    parser.add_argument("--body", required=True, help="Email body")
    parser.add_argument("--priority", default="normal", choices=["low", "normal", "high", "critical"])
    parser.add_argument("--test", action="store_true", help="Test mode - don't actually send")
    
    args = parser.parse_args()
    
    if args.test:
        print("TEST MODE - Would send:")
        print(f"  To: {args.to}")
        print(f"  Subject: {args.subject}")
        print(f"  Priority: {args.priority}")
        print(f"  Body: {args.body[:100]}...")
    else:
        result = send_to_human(
            subject=args.subject,
            body=args.body,
            to=args.to,
            priority=args.priority,
        )
        print(f"Result: {result}")


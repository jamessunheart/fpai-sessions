"""
Zen Village — Unified outbound email helper.

Reuses the same SMTP relay (Brevo via local Postfix on port 25) that zen_pass
and wallet already trust. Centralized so auto-acknowledgments, follow-ups,
and admin replies all go out under the same identity, headers, and unsubscribe
discipline.

Key calls:
    send_email(to, subject, html, text)
    send_auto_acknowledgment(kind, payload)   # kind = "inquiry" | "application"
    send_followup_48h(submission_row)
"""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid
from typing import Optional

MAIL_HOST = os.getenv("MAIL_RELAY_HOST", "localhost")
MAIL_PORT = int(os.getenv("MAIL_RELAY_PORT", "25"))
MAIL_FROM = os.getenv("ZV_MAIL_FROM", os.getenv("ZEN_PASS_MAIL_FROM", "hello@zenvillagecr.com"))
MAIL_FROM_NAME = os.getenv("ZV_MAIL_FROM_NAME", "Zen Village")
MAIL_REPLY_TO = os.getenv("ZV_MAIL_REPLY_TO", os.getenv("ZEN_PASS_MAIL_REPLY_TO", "hello@zenvillagecr.com"))


def send_email(
    to_email: str,
    subject: str,
    html: str,
    text: Optional[str] = None,
    *,
    from_addr: Optional[str] = None,
    from_name: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> bool:
    """Blocking SMTP send. Returns True on accept by relay."""
    if not to_email or "@" not in to_email:
        return False
    try:
        from_a = from_addr or MAIL_FROM
        from_n = from_name or MAIL_FROM_NAME
        rep    = reply_to  or MAIL_REPLY_TO
        msg = MIMEMultipart("alternative")
        msg["From"] = formataddr((from_n, from_a))
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["Reply-To"] = rep
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="zenvillagecr.com")
        if text:
            msg.attach(MIMEText(text, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP(MAIL_HOST, MAIL_PORT, timeout=15) as s:
            s.sendmail(from_a, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"[zv-mail] send failed to {to_email}: {e}")
        return False


# ─── auto-acknowledgment templates ──────────────────────────────────────────

_FOOTER_HTML = """
<hr style="border:none;border-top:1px solid #e6e0d4;margin:32px 0 16px"/>
<p style="color:#9a8e74;font-size:12px;line-height:1.5;margin:0">
  Zen Village · Pavones, Costa Rica<br/>
  <a href="https://zenvillagecr.com" style="color:#6b5d3e">zenvillagecr.com</a>
  &nbsp;·&nbsp;
  Reply directly to this email — a real human will read it.
</p>
"""


def _render(intro: str, name: str, lane: str = "") -> tuple[str, str]:
    name_safe = (name or "friend").split(" ")[0]
    html = f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Inter',system-ui,sans-serif;
            max-width:560px;margin:0 auto;padding:32px 24px;color:#2a2520">
  <p style="font-size:18px;line-height:1.5;margin-top:0">Hi {name_safe},</p>
  <p style="font-size:15px;line-height:1.7;color:#4a4035">{intro}</p>
  <p style="font-size:15px;line-height:1.7;color:#4a4035">
    We read every submission with care. If there's a fit, we'll reach out within
    a week — usually sooner. Most conversations start with a 30-minute call.
  </p>
  <p style="font-size:15px;line-height:1.7;color:#4a4035;margin-bottom:0">
    With care,<br/>
    <b>James &amp; the Zen Village team</b>
  </p>
  {_FOOTER_HTML}
</div>
"""
    text = f"""Hi {name_safe},

{intro}

We read every submission with care. If there's a fit, we'll reach out within a week — usually sooner. Most conversations start with a 30-minute call.

With care,
James & the Zen Village team
zenvillagecr.com
"""
    return html, text


_INTRO_BY_KIND = {
    # Inquiries
    "Stay": "Thanks for reaching out about visiting the village. We received your inquiry and the right person will get back to you shortly.",
    "Retreat": "Thanks for reaching out about a retreat at Zen Village. We received your inquiry and the team holding that container will be in touch.",
    "Coherent Retreat": "Thanks for reaching out about the Coherent Retreat. This is a focused, intimate container — we'll get back to you within a week with details, dates, and the next step.",
    "Support": "Thank you for choosing to support Zen Village. We received your message and will reach out personally to share what your support is making possible.",
    "Event": "Thanks for inquiring about the event. We'll be in touch shortly with details and confirmation.",
    "general": "Thanks for reaching out — your message landed safely.",
    # Applications
    "practitioner": "Thanks for offering to hold space at Zen Village. A practitioner residency is a real container, and we read every application with care.",
    "artist": "Thanks for sharing your work with us. We read every artist application carefully.",
    "creator": "Thanks for sharing your project. We read every creator submission carefully.",
    "volunteer": "Thanks for offering to volunteer. We read every application carefully.",
    "work-exchange": "Thanks for applying for a work exchange at the village. Spots are limited and we read every application with care.",
}


def send_auto_acknowledgment(kind_or_lane: str, name: str, email: str) -> bool:
    """Send the auto-ack appropriate to the inquiry type / application lane."""
    if not email:
        return False
    intro = _INTRO_BY_KIND.get(kind_or_lane) or _INTRO_BY_KIND["general"]
    is_app = kind_or_lane in ("practitioner", "artist", "creator", "volunteer", "work-exchange")
    label = kind_or_lane.replace("-", " ").title() if is_app else kind_or_lane
    subject = f"We received your {label} {'application' if is_app else 'inquiry'}"
    html, text = _render(intro, name, kind_or_lane)
    return send_email(email, subject, html, text)


def send_followup_48h(name: str, email: str, kind_or_lane: str) -> bool:
    """Soft follow-up for leads that have been 'new' for 48h+."""
    if not email:
        return False
    name_safe = (name or "there").split(" ")[0]
    is_app = kind_or_lane in ("practitioner", "artist", "creator", "volunteer", "work-exchange")
    label = kind_or_lane.replace("-", " ").title() if is_app else kind_or_lane
    subject = f"Following up on your {label} {'application' if is_app else 'inquiry'}"
    html, text = _render(
        f"I wanted to follow up — is your {label.lower()} {'application' if is_app else 'inquiry'} still on your mind? "
        f"Happy to jump on a quick call this week if you'd like to talk it through. Just reply to this email and I'll send a few times.",
        name_safe,
        kind_or_lane,
    )
    return send_email(email, subject, html, text)

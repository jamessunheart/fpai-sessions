"""
Email Delivery — Daily AI Frontier Briefing
=============================================

Sends the daily Claude-synthesized briefing to ALL active
subscribers (free, pro, premium). The daily briefing is the
growth hook — restricting it gates nothing at zero paid subs.
Uses local Postfix via SMTP.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone

from sqlalchemy import select

from .models.database import async_session, EmailSubscriberRow

logger = logging.getLogger("fp_index.email_delivery")

FROM_ADDRESS = "intelligence@fullpotential.ai"
FROM_NAME = "FP Index Intelligence"


def _build_briefing_email(briefing: dict, tier: str = "pro") -> tuple[str, str, str]:
    """Build email subject, plain text, and HTML body from briefing data."""
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    headline = briefing.get("headline", "Today's AI Frontier Briefing")
    body_text = briefing.get("body", "")
    fp_score = briefing.get("fp_line_score", "—")
    momentum = briefing.get("momentum", "→")

    subject = f"FP Index Daily: {headline}"

    plain = f"""Full Potential Index — Daily Briefing
{date_str}

FP LINE SCORE: {fp_score} {momentum}

{headline}

{body_text}

---
View the full intelligence feed: https://fullpotential.ai/intelligence
Frontier Basket allocation: https://fullpotential.ai/invest
Gap opportunities: https://fullpotential.ai/opportunities

You're receiving this as an FP Index {tier.title()} subscriber.
Manage your subscription at https://fullpotential.ai/subscribe/manage
"""

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#06060b;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
<div style="max-width:600px;margin:0 auto;padding:32px 20px">

<div style="text-align:center;margin-bottom:24px">
  <span style="color:#00d4ff;font-size:0.75rem;font-weight:600;letter-spacing:0.15em">FULL POTENTIAL INDEX</span>
  <div style="color:#666;font-size:0.75rem;margin-top:4px">{date_str}</div>
</div>

<div style="text-align:center;margin-bottom:28px;padding:20px;background:#0e0e16;border:1px solid rgba(255,255,255,0.06);border-radius:12px">
  <div style="color:#666;font-size:0.7rem;letter-spacing:0.1em;margin-bottom:6px">FP LINE SCORE</div>
  <div style="font-size:2.4rem;font-weight:700;color:#00d4ff">{fp_score}</div>
  <div style="color:#888;font-size:0.8rem">{momentum}</div>
</div>

<div style="color:#e0e0e0;font-size:1.1rem;font-weight:600;margin-bottom:16px;line-height:1.4;border-left:3px solid #d4a017;padding-left:14px">
  {headline}
</div>

<div style="color:#b0b0b0;font-size:0.9rem;line-height:1.7;white-space:pre-wrap">{body_text}</div>

<div style="margin-top:28px;text-align:center">
  <a href="https://fullpotential.ai/intelligence" style="display:inline-block;padding:12px 28px;background:#00d4ff;color:#000;text-decoration:none;border-radius:6px;font-size:0.85rem;font-weight:600">View Full Intelligence Feed →</a>
</div>

<div style="margin-top:20px;text-align:center">
  <a href="https://fullpotential.ai/invest" style="color:#00d4ff;text-decoration:none;font-size:0.8rem">Allocation Report</a>
  &nbsp;·&nbsp;
  <a href="https://fullpotential.ai/opportunities" style="color:#00d4ff;text-decoration:none;font-size:0.8rem">Gap Opportunities</a>
  &nbsp;·&nbsp;
  <a href="https://fullpotential.ai/careers" style="color:#00d4ff;text-decoration:none;font-size:0.8rem">Career Intelligence</a>
</div>

<div style="margin-top:32px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.06);text-align:center;color:#555;font-size:0.7rem">
  You're receiving this as an FP Index {tier.title()} subscriber.<br>
  <a href="https://fullpotential.ai/subscribe/manage" style="color:#666">Manage subscription</a>
</div>

</div>
</body>
</html>"""

    return subject, plain, html


def _send_email(to_address: str, subject: str, plain: str, html: str) -> bool:
    """Send an email via local Postfix SMTP."""
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{FROM_NAME} <{FROM_ADDRESS}>"
    msg["To"] = to_address
    msg["Subject"] = subject
    msg["List-Unsubscribe"] = "<https://fullpotential.ai/subscribe/manage>"

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP("localhost", 25) as smtp:
            smtp.sendmail(FROM_ADDRESS, [to_address], msg.as_string())
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_address}: {e}")
        return False


async def send_daily_briefing() -> dict:
    """Send the daily briefing to ALL active subscribers (free, pro, premium)."""
    from .engine import FPIndexEngine

    engine = FPIndexEngine()
    briefing = await engine.get_latest_briefing()

    if not briefing:
        logger.warning("No briefing available for email delivery")
        return {"sent": 0, "failed": 0, "reason": "no_briefing"}

    fp_line = await engine.compute_fp_line()
    briefing_data = {
        "headline": briefing.get("headline", ""),
        "body": briefing.get("body", ""),
        "fp_line_score": fp_line.overall_score,
        "momentum": f"{'↑' if fp_line.momentum > 0 else '↓' if fp_line.momentum < 0 else '→'} {abs(fp_line.momentum):.1f}",
    }

    async with async_session() as db:
        subscribers = (await db.execute(
            select(EmailSubscriberRow).where(
                EmailSubscriberRow.active == True,
            )
        )).scalars().all()

    if not subscribers:
        logger.info("No active subscribers to email")
        return {"sent": 0, "failed": 0, "subscribers": 0}

    sent = 0
    failed = 0

    for sub in subscribers:
        subject, plain, html = _build_briefing_email(briefing_data, sub.tier or "free")
        if _send_email(sub.email, subject, plain, html):
            sent += 1
        else:
            failed += 1

    logger.info(f"Daily briefing sent: {sent} delivered, {failed} failed out of {len(subscribers)} subscribers")
    return {"sent": sent, "failed": failed, "subscribers": len(subscribers)}

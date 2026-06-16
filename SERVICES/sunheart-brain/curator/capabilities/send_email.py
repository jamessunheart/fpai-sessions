"""Brevo-backed email capability."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone

import httpx

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email_address(address: str) -> bool:
    return bool(EMAIL_RE.match((address or "").strip()))


async def send_email(params: dict) -> dict:
    """Send one email through Brevo's SMTP API.

    Tests inject this provider; live use requires BREVO_API_KEY in curator.env.
    """
    to_address = str(params["to"]).strip()
    if not validate_email_address(to_address):
        raise ValueError("to must be a valid email address")

    api_key = os.environ.get("BREVO_API_KEY")
    if not api_key:
        raise RuntimeError("BREVO_API_KEY is not configured")

    from_email = (
        params.get("from")
        or os.environ.get("CAPABILITY_FROM_EMAIL")
        or os.environ.get("BREVO_FROM_EMAIL")
        or "relay@fullpotential.ai"
    )
    from_name = (
        params.get("from_name")
        or os.environ.get("CAPABILITY_FROM_NAME")
        or os.environ.get("BREVO_FROM_NAME")
        or "Full Potential AI"
    )
    body = str(params["body"]).strip()
    payload = {
        "sender": {"email": from_email, "name": from_name},
        "to": [{"email": to_address}],
        "subject": str(params["subject"]).strip(),
        "textContent": body,
        "htmlContent": _plain_to_html(body),
        "tags": ["capability-send-email"],
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": api_key,
            },
            json=payload,
        )
        response.raise_for_status()
    result = response.json()
    return {
        "provider": "brevo",
        "tracking_id": result.get("messageId"),
        "to": to_address,
        "subject": payload["subject"],
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


def _plain_to_html(text: str) -> str:
    escaped = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>\n")
    )
    return f"<p>{escaped}</p>"

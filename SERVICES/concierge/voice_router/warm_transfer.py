"""Warm-transfer via Twilio: redirect the live call to Dial the chosen agent.

Uses the Twilio REST API to update the in-flight call with new TwiML.
"""
from __future__ import annotations

from typing import Optional

from twilio.rest import Client

from shared.config import settings
from shared.logging import get_logger

log = get_logger("voice-router.warm-transfer")


def _client() -> Optional[Client]:
    if not (settings.twilio_account_sid and settings.twilio_auth_token):
        return None
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


async def redirect_to_agent(
    call_sid: str, agent_phone_e164: str, whisper_text: str | None = None
) -> bool:
    """Update an in-flight Twilio call to Dial the agent number.

    Returns True if the update was accepted.
    """
    client = _client()
    if client is None:
        log.warn("twilio_not_configured")
        return False

    # Whisper plays to the agent only before they're bridged to the caller.
    whisper_twiml = ""
    if whisper_text:
        whisper_twiml = (
            f'<Say voice="alice">{_escape(whisper_text)}</Say>'
        )

    twiml = (
        "<Response>"
        '<Dial answerOnBridge="true" timeout="25">'
        f'<Number url="data:application/xml,{_url_escape(whisper_twiml)}">'
        f"{agent_phone_e164}"
        "</Number>"
        "</Dial>"
        "</Response>"
    )
    try:
        client.calls(call_sid).update(twiml=twiml)
        return True
    except Exception as e:
        log.error("warm_transfer_failed", err=str(e), call_sid=call_sid)
        return False


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _url_escape(s: str) -> str:
    from urllib.parse import quote

    return quote(s, safe="")

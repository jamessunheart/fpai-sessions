"""app/character_provisioning.py — Character-tier provisioning chain.

Per the Character SPEC, when a new Character signs up (via accepted application
+ Stripe checkout completion), we automatically provision:

  1. brain-account     → POST sunheart-brain admin to create full-tier user
  2. identity-stack    → template the 7-file identity stack to their vision
  3. tg-invite         → invite to @characters founder-circle channel
  4. welcome-packet    → personalized Haiku-drafted welcome with first 1:1 link
  5. narrator-bootstrap → register Narrator agent to observe the substrate

Each step is feature-flagged. Each is idempotent. Each logs to provision_log.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

from . import db

log = logging.getLogger("character.provisioning")

# Feature flags (default OFF until verified)
FLAGS = {
    "brain_account": os.environ.get("CHAR_PROVISION_BRAIN_ACCOUNT", "0") == "1",
    "identity_stack": os.environ.get("CHAR_PROVISION_IDENTITY_STACK", "0") == "1",
    "tg_invite": os.environ.get("CHAR_PROVISION_TG_INVITE", "0") == "1",
    "welcome_packet": os.environ.get("CHAR_PROVISION_WELCOME_PACKET", "0") == "1",
    "narrator_bootstrap": os.environ.get("CHAR_PROVISION_NARRATOR", "0") == "1",
}

# Downstream services
BRAIN_URL = os.environ.get("BRAIN_URL", "http://127.0.0.1:8000")
BRAIN_ADMIN_TOKEN = os.environ.get("BRAIN_ADMIN_TOKEN", "")

TG_BOT_URL = os.environ.get("TG_BOT_URL", "http://127.0.0.1:8766")
TG_BOT_ADMIN_TOKEN = os.environ.get("TG_BOT_ADMIN_TOKEN", "")
TG_CHARACTER_CHANNEL = os.environ.get("TG_CHARACTER_CHANNEL", "@characters")

MAIL_URL = os.environ.get("MAIL_URL", "http://127.0.0.1:8770")
MAIL_ADMIN_TOKEN = os.environ.get("MAIL_ADMIN_TOKEN", "")

NARRATOR_URL = os.environ.get("NARRATOR_URL", "http://127.0.0.1:8771")
NARRATOR_ADMIN_TOKEN = os.environ.get("NARRATOR_ADMIN_TOKEN", "")

ALERTS_URL = os.environ.get("ALERTS_URL", "http://127.0.0.1:8766")

# Booking link (Cal.com or static form URL)
FIRST_ONEONE_BOOKING_URL = os.environ.get(
    "CHAR_BOOKING_URL", "https://cal.com/jamessunheart/character-onboarding"
)


async def _step_brain_account(email: str, name: str, work: Optional[str]) -> tuple[str, str]:
    if not FLAGS["brain_account"]:
        return ("skipped", "CHAR_PROVISION_BRAIN_ACCOUNT=0")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{BRAIN_URL}/admin/users/create",
                json={
                    "email": email,
                    "name": name,
                    "role": "character",
                    "tier": "character",
                    "context_seed": work or "",
                },
                headers={"X-Admin-Token": BRAIN_ADMIN_TOKEN},
            )
        if r.status_code in (200, 201, 409):
            return ("success", f"brain returned {r.status_code}")
        return ("failed", f"brain returned {r.status_code}: {r.text[:200]}")
    except Exception as e:
        return ("failed", f"exception: {e!r}")


async def _step_identity_stack(
    email: str, name: str, work: Optional[str], vision_link: Optional[str]
) -> tuple[str, str]:
    """Template the 7-file identity stack to their vision via brain admin endpoint."""
    if not FLAGS["identity_stack"]:
        return ("skipped", "CHAR_PROVISION_IDENTITY_STACK=0")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{BRAIN_URL}/admin/character/template-identity",
                json={
                    "email": email,
                    "name": name,
                    "work": work or "",
                    "vision_link": vision_link or "",
                    "template_set": "substrate_features_v1",
                },
                headers={"X-Admin-Token": BRAIN_ADMIN_TOKEN},
            )
        if r.status_code in (200, 201):
            return ("success", f"identity stack templated")
        return ("failed", f"brain returned {r.status_code}: {r.text[:200]}")
    except Exception as e:
        return ("failed", f"exception: {e!r}")


async def _step_tg_invite(email: str, name: str) -> tuple[str, str]:
    if not FLAGS["tg_invite"]:
        return ("skipped", "CHAR_PROVISION_TG_INVITE=0")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{TG_BOT_URL}/admin/invite-to-channel",
                json={
                    "email": email,
                    "channel": TG_CHARACTER_CHANNEL,
                    "name": name,
                },
                headers={"X-Admin-Token": TG_BOT_ADMIN_TOKEN},
            )
        if r.status_code == 200:
            return ("success", "tg invite queued")
        return ("failed", f"tg returned {r.status_code}: {r.text[:200]}")
    except Exception as e:
        return ("failed", f"exception: {e!r}")


async def _step_welcome_packet(
    email: str, name: str, founding: bool, work: Optional[str]
) -> tuple[str, str]:
    if not FLAGS["welcome_packet"]:
        return ("skipped", "CHAR_PROVISION_WELCOME_PACKET=0")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{MAIL_URL}/admin/send-welcome",
                json={
                    "to": email,
                    "name": name,
                    "template": "character_welcome",
                    "founding": founding,
                    "personalization": {"work": work or ""},
                    "booking_link": FIRST_ONEONE_BOOKING_URL,
                },
                headers={"X-Admin-Token": MAIL_ADMIN_TOKEN},
            )
        if r.status_code == 200:
            return ("success", "welcome packet queued")
        return ("failed", f"mail returned {r.status_code}: {r.text[:200]}")
    except Exception as e:
        return ("failed", f"exception: {e!r}")


async def _step_narrator_bootstrap(email: str, name: str) -> tuple[str, str]:
    if not FLAGS["narrator_bootstrap"]:
        return ("skipped", "CHAR_PROVISION_NARRATOR=0")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{NARRATOR_URL}/admin/register-subject",
                json={"email": email, "name": name, "subject_type": "character"},
                headers={"X-Admin-Token": NARRATOR_ADMIN_TOKEN},
            )
        if r.status_code in (200, 201):
            return ("success", "narrator registered")
        return ("failed", f"narrator returned {r.status_code}: {r.text[:200]}")
    except Exception as e:
        return ("failed", f"exception: {e!r}")


async def _alert_james(email: str, summary: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"{ALERTS_URL}/send",
                json={
                    "channel": "telegram",
                    "recipient": "default",
                    "message": f"🟣 Character provisioning needs attention\n{email}\n{summary}",
                },
            )
    except Exception:
        pass


async def provision_character(
    email: str,
    name: str,
    founding: bool,
    work: Optional[str] = None,
    vision_link: Optional[str] = None,
) -> str:
    """Run the 5-step Character provisioning chain."""
    results: dict[str, tuple[str, str]] = {}

    steps = [
        ("brain_account", _step_brain_account(email, name, work)),
        ("identity_stack", _step_identity_stack(email, name, work, vision_link)),
        ("tg_invite", _step_tg_invite(email, name)),
        ("welcome_packet", _step_welcome_packet(email, name, founding, work)),
        ("narrator_bootstrap", _step_narrator_bootstrap(email, name)),
    ]

    for step_name, coro in steps:
        status, detail = await coro
        results[step_name] = (status, detail)
        db.log_provision_step(email, f"character.{step_name}", status, detail)
        log.info("character provision step=%s email=%s status=%s", step_name, email, status)

    successes = sum(1 for s, _ in results.values() if s == "success")
    skipped = sum(1 for s, _ in results.values() if s == "skipped")
    failed = sum(1 for s, _ in results.values() if s == "failed")

    if failed == 0:
        state = "complete"
    elif successes + skipped > 0:
        state = "partial"
    else:
        state = "failed"

    db.set_character_provision_state(email, state)

    if failed > 0:
        failed_steps = [k for k, (s, _) in results.items() if s == "failed"]
        await _alert_james(email, f"failed steps: {', '.join(failed_steps)} · state={state}")

    return state

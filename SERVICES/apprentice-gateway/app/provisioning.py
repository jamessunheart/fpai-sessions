"""app/provisioning.py — 4-step provisioning chain for new paid apprentices.

Each step is feature-flagged via env. Each is idempotent and safe to retry.

Steps:
  1. champion_card  → POST to champion-sign admin, set tier: apprentice
  2. brain_account  → POST to sunheart-brain admin, create user
  3. tg_invite      → POST to TG bot admin, add user to @apprentices channel
  4. welcome_email  → POST to mail pipeline with Haiku-drafted welcome
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

from . import db

log = logging.getLogger("apprentice.provisioning")

# Feature flags (default OFF in production until verified)
FLAGS = {
    "champion_card": os.environ.get("PROVISION_CHAMPION_CARD", "0") == "1",
    "brain_account": os.environ.get("PROVISION_BRAIN_ACCOUNT", "0") == "1",
    "tg_invite": os.environ.get("PROVISION_TG_INVITE", "0") == "1",
    "welcome_email": os.environ.get("PROVISION_WELCOME_EMAIL", "0") == "1",
}

# Downstream service URLs (overridable via env)
CHAMPION_SIGN_URL = os.environ.get("CHAMPION_SIGN_URL", "http://127.0.0.1:8770")
CHAMPION_SIGN_ADMIN_TOKEN = os.environ.get("CHAMPION_SIGN_ADMIN_TOKEN", "")

BRAIN_URL = os.environ.get("BRAIN_URL", "http://127.0.0.1:8000")
BRAIN_ADMIN_TOKEN = os.environ.get("BRAIN_ADMIN_TOKEN", "")

TG_BOT_URL = os.environ.get("TG_BOT_URL", "http://127.0.0.1:8766")
TG_BOT_ADMIN_TOKEN = os.environ.get("TG_BOT_ADMIN_TOKEN", "")
TG_APPRENTICE_CHANNEL = os.environ.get("TG_APPRENTICE_CHANNEL", "@apprentices")

MAIL_URL = os.environ.get("MAIL_URL", "http://127.0.0.1:8770")
MAIL_ADMIN_TOKEN = os.environ.get("MAIL_ADMIN_TOKEN", "")

# Telegram alert for provisioning failures
ALERTS_URL = os.environ.get("ALERTS_URL", "http://127.0.0.1:8766")


async def _step_champion_card(email: str, name: str, founding: bool) -> tuple[str, str]:
    """Update Champion card with tier: apprentice. Returns (status, detail)."""
    if not FLAGS["champion_card"]:
        return ("skipped", "PROVISION_CHAMPION_CARD=0")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{CHAMPION_SIGN_URL}/admin/set-tier",
                json={
                    "email": email,
                    "tier": "apprentice",
                    "founding": founding,
                },
                headers={"X-Admin-Token": CHAMPION_SIGN_ADMIN_TOKEN},
            )
        if r.status_code == 200:
            return ("success", f"champion-sign returned 200")
        return ("failed", f"champion-sign returned {r.status_code}: {r.text[:200]}")
    except Exception as e:
        return ("failed", f"exception: {e!r}")


async def _step_brain_account(email: str, name: str) -> tuple[str, str]:
    """Create brain-server account."""
    if not FLAGS["brain_account"]:
        return ("skipped", "PROVISION_BRAIN_ACCOUNT=0")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{BRAIN_URL}/admin/users/create",
                json={
                    "email": email,
                    "name": name,
                    "role": "apprentice",
                },
                headers={"X-Admin-Token": BRAIN_ADMIN_TOKEN},
            )
        if r.status_code in (200, 201, 409):  # 409 = already exists, fine
            return ("success", f"brain returned {r.status_code}")
        return ("failed", f"brain returned {r.status_code}: {r.text[:200]}")
    except Exception as e:
        return ("failed", f"exception: {e!r}")


async def _step_tg_invite(email: str, name: str) -> tuple[str, str]:
    """Send TG invite link via bot."""
    if not FLAGS["tg_invite"]:
        return ("skipped", "PROVISION_TG_INVITE=0")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{TG_BOT_URL}/admin/invite-to-channel",
                json={
                    "email": email,
                    "channel": TG_APPRENTICE_CHANNEL,
                    "name": name,
                },
                headers={"X-Admin-Token": TG_BOT_ADMIN_TOKEN},
            )
        if r.status_code == 200:
            return ("success", "tg invite queued")
        return ("failed", f"tg returned {r.status_code}: {r.text[:200]}")
    except Exception as e:
        return ("failed", f"exception: {e!r}")


async def _step_welcome_email(email: str, name: str, founding: bool) -> tuple[str, str]:
    """Send Haiku-drafted welcome email."""
    if not FLAGS["welcome_email"]:
        return ("skipped", "PROVISION_WELCOME_EMAIL=0")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{MAIL_URL}/admin/send-welcome",
                json={
                    "to": email,
                    "name": name,
                    "template": "apprentice_welcome",
                    "founding": founding,
                },
                headers={"X-Admin-Token": MAIL_ADMIN_TOKEN},
            )
        if r.status_code == 200:
            return ("success", "welcome email queued")
        return ("failed", f"mail returned {r.status_code}: {r.text[:200]}")
    except Exception as e:
        return ("failed", f"exception: {e!r}")


async def _alert_james(email: str, summary: str) -> None:
    """Best-effort TG alert to James on provisioning failure."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"{ALERTS_URL}/send",
                json={
                    "channel": "telegram",
                    "recipient": "default",
                    "message": f"🟠 Apprentice provisioning needs attention\n{email}\n{summary}",
                },
            )
    except Exception:
        pass


async def provision_apprentice(email: str, name: str, founding: bool) -> str:
    """Run the 4-step provisioning chain.

    Returns the final provision_state: 'complete' | 'partial' | 'failed'.
    """
    results: dict[str, tuple[str, str]] = {}

    steps = [
        ("champion_card", _step_champion_card(email, name, founding)),
        ("brain_account", _step_brain_account(email, name)),
        ("tg_invite", _step_tg_invite(email, name)),
        ("welcome_email", _step_welcome_email(email, name, founding)),
    ]

    for step_name, coro in steps:
        status, detail = await coro
        results[step_name] = (status, detail)
        db.log_provision_step(email, step_name, status, detail)
        log.info("provision step=%s email=%s status=%s", step_name, email, status)

    successes = sum(1 for s, _ in results.values() if s == "success")
    skipped = sum(1 for s, _ in results.values() if s == "skipped")
    failed = sum(1 for s, _ in results.values() if s == "failed")

    # State logic:
    # - All success or skipped → complete
    # - Some success/skipped + some failed → partial
    # - All failed → failed
    if failed == 0:
        state = "complete"
    elif successes + skipped > 0:
        state = "partial"
    else:
        state = "failed"

    db.set_provision_state(email, state)

    # Alert James if anything failed
    if failed > 0:
        failed_steps = [k for k, (s, _) in results.items() if s == "failed"]
        await _alert_james(email, f"failed steps: {', '.join(failed_steps)} · state={state}")

    return state

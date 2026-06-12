#!/usr/bin/env python3
"""Read-only email adapter for the comms hub.

V1 is fixture-first. Live email read is deliberately not implemented here; a
future scoped pass can add a provider-specific reader behind explicit
James-owned credentials. There is no send path in this module.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class EmailReadNotConfigured(RuntimeError):
    """Raised when live email read is requested without an explicit fixture."""


def ingest_fixture(path: Path | str) -> list[dict[str, Any]]:
    """Load a list of email-like message dictionaries from JSON."""
    fixture_path = Path(path)
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("email fixture must be a JSON list")
    return [normalize_message(item, index) for index, item in enumerate(data, start=1)]


def ingest_read_only(*, fixture: Path | str | None = None) -> list[dict[str, Any]]:
    """Return read-only email messages.

    Without a fixture, this refuses unless James has explicitly set an email
    read credential env. Even then V1 raises because no live provider adapter is
    wired in this spec.
    """
    if fixture:
        return ingest_fixture(fixture)
    if not os.environ.get("FPAI_EMAIL_READ_TOKEN"):
        return []
    raise EmailReadNotConfigured("live email read needs a scoped provider adapter; V1 is fixture-backed only")


def normalize_message(raw: dict[str, Any], index: int = 1) -> dict[str, Any]:
    """Normalize loose fixture data into the comms message shape."""
    if not isinstance(raw, dict):
        raise ValueError("email fixture item must be an object")
    sender = str(raw.get("from") or raw.get("sender") or "").strip()
    subject = str(raw.get("subject") or "").strip()
    body = str(raw.get("body") or raw.get("text") or "").strip()
    message_id = str(raw.get("id") or f"email-{index}").strip()
    if not sender:
        raise ValueError(f"message {message_id} requires sender/from")
    if not subject and not body:
        raise ValueError(f"message {message_id} requires subject or body")
    return {
        "id": message_id,
        "channel": "email",
        "from": sender,
        "to": str(raw.get("to") or "").strip(),
        "subject": subject,
        "body": body,
        "received_at": str(raw.get("received_at") or "").strip(),
    }


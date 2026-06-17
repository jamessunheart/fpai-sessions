#!/usr/bin/env python3
"""Seed-contact API helpers for the pre-profiler.

This module is intentionally standalone so a live FastAPI service can mount
`router` later without this build editing a production app.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable

from tools.outreach import pre_profiler, profile_store
from tools.probe import rate_governor


@dataclass(frozen=True)
class SeedContactRequest:
    name: str
    email: str | None = None
    channel: str | None = None
    notes: str | None = None
    url_hints: tuple[str, ...] = ()


def normalize_seed_payload(payload: dict[str, Any]) -> SeedContactRequest:
    hints = payload.get("url_hints") or []
    if isinstance(hints, str):
        hints = [hints]
    elif isinstance(hints, dict):
        hints = [str(value) for value in hints.values() if value]
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("name is required")
    return SeedContactRequest(
        name=name,
        email=str(payload.get("email") or "").strip() or None,
        channel=str(payload.get("channel") or "").strip() or None,
        notes=str(payload.get("notes") or "").strip() or None,
        url_hints=tuple(str(value).strip() for value in hints if str(value).strip()),
    )


def seed_and_profile(
    payload: dict[str, Any],
    *,
    conn: Any | None = None,
    connector: Callable[[], Any] = rate_governor.connect_from_env,
    profiler: Callable[..., pre_profiler.ContactProfile] = pre_profiler.profile_and_store,
) -> dict[str, Any]:
    request = normalize_seed_payload(payload)
    own_conn = conn is None
    db = conn or connector()
    try:
        contact_id = profile_store.seed_contact(db, **asdict(request))
        contact = {
            "id": contact_id,
            "name": request.name,
            "email": request.email,
            "channel": request.channel,
            "notes": request.notes,
            "url_hints": request.url_hints,
        }
        profile = profiler(contact, conn=db)
    finally:
        if own_conn and hasattr(db, "close"):
            db.close()
    return {
        "contact_id": contact_id,
        "profile": asdict(profile),
        "draft": {
            "subject": profile.suggested_subject,
            "body": profile.suggested_body,
        },
        "send_status": "not_sent",
    }


try:  # pragma: no cover - depends on live service deps.
    from fastapi import APIRouter

    router = APIRouter(prefix="/api/contacts", tags=["contacts"])

    @router.post("/seed")
    def seed_contact(payload: dict[str, Any]) -> dict[str, Any]:
        return seed_and_profile(payload)

except Exception:  # pragma: no cover - keeps tests independent from FastAPI.
    router = None

"""Calendar booking capability providers."""
from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx


async def book_calendar(params: dict) -> dict:
    """Create a calendar event via Cal.com when CALCOM_API_KEY is configured."""
    api_key = os.environ.get("CALCOM_API_KEY")
    if not api_key:
        raise RuntimeError("CALCOM_API_KEY is not configured")

    attendees = params.get("attendees_optional") or []
    if isinstance(attendees, str):
        attendees = [attendees]
    payload = {
        "title": params["title"],
        "start": _iso_start(params),
        "lengthInMinutes": int(params["duration"]),
        "attendees": [{"email": email} for email in attendees if email],
        "metadata": {"source": "fpai-capability-book-calendar"},
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            os.environ.get("CALCOM_EVENT_URL", "https://api.cal.com/v1/bookings"),
            params={"apiKey": api_key},
            json=payload,
        )
        response.raise_for_status()
    result = response.json()
    event = result.get("booking") if isinstance(result.get("booking"), dict) else result
    event_id = event.get("id") or event.get("uid") or event.get("bookingId")
    return {
        "provider": "cal.com",
        "event_id": str(event_id) if event_id is not None else "",
        "event_url": event.get("videoCallUrl") or event.get("rescheduleUrl") or event.get("url") or "",
        "title": params["title"],
        "start": payload["start"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def cancel_event(event_id: str) -> dict:
    api_key = os.environ.get("CALCOM_API_KEY")
    if not api_key:
        raise RuntimeError("CALCOM_API_KEY is not configured")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.delete(
            f"https://api.cal.com/v1/bookings/{event_id}",
            params={"apiKey": api_key, "cancellationReason": "User requested /undo"},
        )
        response.raise_for_status()
    return {"cancelled": True, "event_id": event_id}


def _iso_start(params: dict) -> str:
    value = str(params.get("start") or "").strip()
    if value:
        return value
    date = str(params["date"]).strip()
    time = str(params["time"]).strip()
    joined = f"{date}T{time}"
    if joined.endswith("Z") or "+" in joined[10:]:
        return joined
    return joined + ":00Z" if len(time) == 5 else joined + "Z"

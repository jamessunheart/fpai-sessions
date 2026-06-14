"""Claude Haiku 4.5 work-claim parser (text + vision).

Parses incoming group-chat messages and decides whether they represent a
work-of-proof claim. Vision-capable: when a photo accompanies the message,
the image is included in the Haiku request as a content block.

Cost: ~$0.001 per call at Haiku rates. Per-call cost logged to audit.

Phoenix discipline: this module is TRANSPORT, not STORAGE. The raw message is
already persisted to `group_messages` BEFORE this module is invoked. If
Anthropic API is down, the calling code MUST still leave the row in place so
a background retry worker can pick it up.

Env:
    ANTHROPIC_API_KEY    required at runtime (loaded from /etc/fp-game-bot/
                         fp-game-bot.env on the server, or process env)
    HAIKU_MODEL          override (default: claude-haiku-4-5-20251001)
"""
from __future__ import annotations

import json
import os
import base64
from pathlib import Path
from typing import Any

import httpx

HAIKU_MODEL = os.environ.get("HAIKU_MODEL", "claude-haiku-4-5-20251001")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE = os.environ.get(
    "ANTHROPIC_BASE_URL", "https://api.anthropic.com"
)

# Per-token Haiku 4.5 published rates (USD). Update if Anthropic changes prices.
HAIKU_INPUT_COST_PER_MTOK = 1.00
HAIKU_OUTPUT_COST_PER_MTOK = 5.00


from . import mechanics

_RATE = mechanics.WC_RATE_PER_HOUR
_CAP_HRS = mechanics.WC_WEEKLY_CAP_HOURS
_CAP_AMT = mechanics.WC_WEEKLY_CAP_AMOUNT

SYSTEM_PROMPT = (
    "You parse WhatsApp group-chat messages from Zen Village to detect when "
    "a volunteer claims a \"work-of-proof\" — hours actually worked or a "
    "visible task completed.\n\n"
    "Zen Village runs a two-tier membership model (v8): Shared Room / "
    "Glamping at $400/week and Private Room at $600/week. Tier is assigned "
    "by Zen Village, not chosen by the volunteer.\n\n"
    f"Volunteers earn Zen Village Work Credits (ZWC) at 1 hr = ${_RATE} ZWC. "
    f"Hard weekly cap: {_CAP_HRS} hrs × ${_RATE} = ${_CAP_AMT} ZWC max per "
    f"week — exactly enough to cover the $400 Shared invoice. Private Room "
    f"volunteers cover the remaining $200 gap through a discretionary ZV "
    f"bonus (typical for strong priority delivery) or in cash / CORA. Hours "
    f"beyond {_CAP_HRS} do NOT earn additional ZWC, but help complete "
    "priorities which earn CORA bonuses. Eligible labor includes: cleaning, "
    "cooking, gardening, painting, construction, content production "
    "(filming, editing, posting), supporting fellow villagers, repairs, "
    "errands, kitchen work, dish-washing, laundry, animal care, maintenance, "
    "organizing, teaching."
) + """

Priority tags:
- P1 — highest-priority weekly priority (most important)
- P2 — second priority
- P3 — third priority
None if not stated.

You return strict JSON with these exact keys:
{
  "is_work_claim": bool,
  "actor": string or null,
  "activity": string or null,
  "hours_claimed": number or null,
  "priority_tag": "P1" | "P2" | "P3" | null,
  "evidence_type": "photo" | "video" | "voice" | "none",
  "confidence": number between 0.0 and 1.0,
  "raw_extracted_text": string
}

Rules:
- "is_work_claim" is true ONLY if a specific labor activity is asserted with at least an implied time investment.
- Pure social messages (greetings, banter, questions, planning, opinions, photos with no work claim) → is_work_claim=false, confidence=0.95+.
- If a photo is attached and clearly shows recent labor (a clean kitchen, a freshly weeded garden, a stack of finished laundry, etc.) AND the text supports it, set evidence_type accordingly and raise confidence.
- "actor": extract the volunteer name if mentioned in first-person ("I just cleaned"), or the displayName field if available, or null.
- "hours_claimed": parse numbers. "2 hours" → 2.0. "30 minutes" → 0.5. "all morning" → 3.0 (rough estimate, lower confidence). If unclear, use null and lower confidence.
- "raw_extracted_text": the verbatim or near-verbatim text describing the work.
- "confidence" reflects parsing certainty, NOT trust of the claim (witness approval is the trust layer).
- DO NOT return any wrapper text, commentary, or markdown. JSON only."""


def _haiku_headers() -> dict[str, str]:
    return {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }


def _build_user_content(
    text: str,
    sender_display_name: str | None,
    image_b64: str | None,
    image_media_type: str | None,
) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = []
    if image_b64 and image_media_type:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image_media_type,
                    "data": image_b64,
                },
            }
        )
    framed = (
        f"Sender displayName: {sender_display_name or 'unknown'}\n"
        f"Message text: {text or '(no text — image only)'}\n\n"
        "Parse and return ONLY the JSON object per the schema."
    )
    content.append({"type": "text", "text": framed})
    return content


def _estimate_cost(usage: dict[str, Any] | None) -> float:
    if not usage:
        return 0.0
    in_tok = usage.get("input_tokens", 0) or 0
    out_tok = usage.get("output_tokens", 0) or 0
    return (
        in_tok * HAIKU_INPUT_COST_PER_MTOK / 1_000_000
        + out_tok * HAIKU_OUTPUT_COST_PER_MTOK / 1_000_000
    )


def _empty_result(reason: str) -> dict[str, Any]:
    return {
        "is_work_claim": False,
        "actor": None,
        "activity": None,
        "hours_claimed": None,
        "priority_tag": None,
        "evidence_type": "none",
        "confidence": 0.0,
        "raw_extracted_text": "",
        "_parser_error": reason,
        "_cost_usd": 0.0,
    }


def _load_image(image_path: str | None) -> tuple[str | None, str | None]:
    """Read a local media file and return (base64, media_type)."""
    if not image_path:
        return None, None
    p = Path(image_path)
    if not p.exists():
        return None, None
    ext = p.suffix.lower()
    media_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(ext)
    if not media_type:
        return None, None
    try:
        return base64.b64encode(p.read_bytes()).decode("ascii"), media_type
    except Exception:
        return None, None


async def parse_work_claim(
    text: str,
    image_url: str | None = None,
    sender_display_name: str | None = None,
) -> dict[str, Any]:
    """Call Haiku to classify a group message.

    `image_url` is interpreted as a local filesystem path (we already
    downloaded the media via Evolution API). If the file isn't readable, the
    call proceeds text-only.
    """
    if not ANTHROPIC_API_KEY:
        return _empty_result("ANTHROPIC_API_KEY not set")

    image_b64, media_type = _load_image(image_url)

    user_content = _build_user_content(
        text=text or "",
        sender_display_name=sender_display_name,
        image_b64=image_b64,
        image_media_type=media_type,
    )

    payload = {
        "model": HAIKU_MODEL,
        "max_tokens": 512,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_content}],
    }

    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                f"{ANTHROPIC_BASE}/v1/messages",
                json=payload,
                headers=_haiku_headers(),
            )
    except Exception as e:
        return _empty_result(f"http_exception: {type(e).__name__}: {e}")

    if r.status_code != 200:
        return _empty_result(f"api_{r.status_code}: {r.text[:200]}")

    body = r.json()
    raw_text = ""
    for block in body.get("content", []):
        if block.get("type") == "text":
            raw_text += block.get("text", "")
    raw_text = raw_text.strip()
    cost = _estimate_cost(body.get("usage"))

    # Best-effort JSON extraction
    parsed: dict[str, Any] | None = None
    try:
        parsed = json.loads(raw_text)
    except Exception:
        # Try to extract first {...} block
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(raw_text[start : end + 1])
            except Exception:
                parsed = None

    if not isinstance(parsed, dict):
        out = _empty_result(f"unparseable_json: {raw_text[:120]}")
        out["_cost_usd"] = cost
        return out

    # Normalize / fill missing keys defensively
    result: dict[str, Any] = {
        "is_work_claim": bool(parsed.get("is_work_claim", False)),
        "actor": parsed.get("actor") or None,
        "activity": parsed.get("activity") or None,
        "hours_claimed": parsed.get("hours_claimed"),
        "priority_tag": parsed.get("priority_tag") or None,
        "evidence_type": parsed.get("evidence_type") or "none",
        "confidence": float(parsed.get("confidence") or 0.0),
        "raw_extracted_text": parsed.get("raw_extracted_text") or text or "",
        "_cost_usd": cost,
        "_model": HAIKU_MODEL,
    }
    # Sanity: hours_claimed must be a number or None
    if result["hours_claimed"] is not None:
        try:
            result["hours_claimed"] = float(result["hours_claimed"])
        except Exception:
            result["hours_claimed"] = None
    # Sanity: priority_tag normalized
    if result["priority_tag"]:
        pt = str(result["priority_tag"]).upper().strip()
        result["priority_tag"] = pt if pt in ("P1", "P2", "P3") else None
    return result

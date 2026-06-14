"""app/ai/vision.py — receipt/photo OCR via OpenAI vision.

Stub for Phase 1: returns a ParsedIntent or None. The TG handler will run the
photo through this and present a confirm dialog before writing.

Phase 2: support Claude vision too, plus PDF page-by-page.
"""
from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone

import httpx

from ..config import settings
from .parse import ParsedIntent, _coerce

log = logging.getLogger("streasury.vision")


VISION_SYSTEM = """You read a receipt photo and return a JSON object describing
the transaction. Same schema as the parser:

{
  "amount": <total paid, positive number>,
  "direction": "out",                       // receipts are almost always expenses
  "currency": "<ISO-4217 if visible, else USD>",
  "category": "<best guess: groceries, food, fuel, hosting, travel, misc>",
  "vendor": "<merchant name from the top of the receipt>",
  "account_slug": null,
  "occurred_at": "<ISO-8601 if a date is on the receipt>",
  "note": "<one short sentence summary>",
  "confidence": <0.0-1.0>
}

If the image is not a receipt, return {"confidence": 0.0, "amount": 0,
"direction": "out", "currency": "USD", "category": "misc", "vendor": null,
"account_slug": null, "occurred_at": null, "note": "not a receipt"}.
"""


async def parse_receipt(image_bytes: bytes, *, mime: str = "image/jpeg") -> ParsedIntent | None:
    if not settings.openai_api_key:
        return None
    b64 = base64.b64encode(image_bytes).decode("ascii")
    payload = {
        "model": settings.openai_vision_model,
        "max_tokens": 400,
        "temperature": 0.0,
        "messages": [
            {"role": "system", "content": VISION_SYSTEM},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract the receipt JSON."},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            },
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "content-type": "application/json",
                },
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
        raw = (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
    except Exception as e:
        log.warning("vision call failed: %s", e)
        return None

    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0]
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        d = json.loads(raw[start:end + 1])
    except Exception as e:
        log.warning("vision json parse failed: %s", e)
        return None
    return _coerce(d, datetime.now(timezone.utc))

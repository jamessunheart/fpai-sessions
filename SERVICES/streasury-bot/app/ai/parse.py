"""app/ai/parse.py — natural-language → structured txn intent.

Used by both free-text messages ("got 600 from acme today") and voice
transcripts. Falls back to a regex parser if the AI call fails so the bot
keeps working when the network is flaky.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from . import llm

log = logging.getLogger("streasury.parse")


PARSE_SYSTEM = """You convert a short natural-language money statement into a
structured intent. Return ONLY a JSON object with this shape:

{
  "amount": <number, positive>,           // absolute value of the money
  "direction": "in" | "out",              // 'in' for income, 'out' for expense
  "currency": "USD",                       // ISO 4217 or crypto ticker; default USD
  "category": "groceries"|"hosting"|"revenue"|"ai"|"travel"|"misc"|<freeform>,
  "vendor": "<counterparty or null>",
  "account_slug": "<best guess account slug or null>",
  "occurred_at": "<ISO-8601 timestamp or null>",
  "note": "<one short sentence summarising the entry>",
  "confidence": <0.0-1.0>
}

Rules:
- If the input is ambiguous (no amount, no direction), set confidence < 0.5.
- If the user said 'today' / 'yesterday', resolve relative to the supplied
  reference timestamp.
- If they didn't say where the money came from / went to, leave vendor null.
- Do not invent numbers. If you can't extract an amount, set "amount": 0
  and "confidence": 0.0.
"""


@dataclass
class ParsedIntent:
    amount: float
    direction: str
    currency: str
    category: str
    vendor: str | None
    account_slug: str | None
    occurred_at: datetime | None
    note: str
    confidence: float

    @property
    def signed_amount(self) -> float:
        return self.amount if self.direction == "in" else -self.amount

    def to_dict(self) -> dict[str, Any]:
        return {
            "amount": self.amount,
            "direction": self.direction,
            "currency": self.currency,
            "category": self.category,
            "vendor": self.vendor,
            "account_slug": self.account_slug,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "note": self.note,
            "confidence": self.confidence,
        }


def _coerce(d: dict, now: datetime) -> ParsedIntent:
    occurred_at: datetime | None = None
    raw = d.get("occurred_at")
    if raw:
        try:
            occurred_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            occurred_at = None
    occurred_at = occurred_at or now
    return ParsedIntent(
        amount=float(d.get("amount") or 0),
        direction=(d.get("direction") or "out").lower(),
        currency=(d.get("currency") or "USD").upper(),
        category=(d.get("category") or "misc").lower(),
        vendor=d.get("vendor") or None,
        account_slug=d.get("account_slug") or None,
        occurred_at=occurred_at,
        note=d.get("note") or "",
        confidence=float(d.get("confidence") or 0),
    )


# Cheap fallback parser: "<verb> <number> <category> [vendor]"
_FALLBACK_RX = re.compile(
    r"(?P<verb>spent|paid|bought|got|received|earned|made|sent|gave)\s+"
    r"\$?(?P<amount>[\d,]+(?:\.\d+)?)\s*"
    r"(?P<rest>.*)",
    re.IGNORECASE,
)
_INCOME_VERBS = {"got", "received", "earned", "made"}


def fallback_parse(text: str, now: datetime) -> ParsedIntent | None:
    m = _FALLBACK_RX.search(text)
    if not m:
        return None
    amount = float(m.group("amount").replace(",", ""))
    verb = m.group("verb").lower()
    rest = (m.group("rest") or "").strip().strip(".,")
    direction = "in" if verb in _INCOME_VERBS else "out"
    category = (rest.split()[0] if rest else "misc").lower()
    vendor = None
    if " for " in rest:
        vendor = rest.split(" for ", 1)[1].strip() or None
    elif " from " in rest:
        vendor = rest.split(" from ", 1)[1].strip() or None
    return ParsedIntent(
        amount=amount,
        direction=direction,
        currency="USD",
        category=category or "misc",
        vendor=vendor,
        account_slug=None,
        occurred_at=now,
        note=text.strip(),
        confidence=0.4,  # low — regex fallback
    )


async def parse_intent(text: str) -> ParsedIntent | None:
    """Best-effort parse. Returns None only if both AI and regex fail."""
    now = datetime.now(timezone.utc)
    user = f"Reference timestamp: {now.isoformat()}\n\nUser said: {text!r}"
    try:
        result = await llm.claude(PARSE_SYSTEM, user, max_tokens=400, temperature=0.0)
        raw = result.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0]
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            return _coerce(json.loads(raw[start:end + 1]), now)
    except Exception as e:
        log.warning("AI parse failed, falling back to regex: %s", e)
    return fallback_parse(text, now)

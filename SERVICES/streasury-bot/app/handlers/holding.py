"""/holding — set crypto/stock holding quantity, valued via CoinGecko."""
from __future__ import annotations

import logging

import httpx

from .. import ledger, telegram
from ..config import settings

log = logging.getLogger("streasury.holding")


COINGECKO_IDS = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "ton": "the-open-network",
    "usdt": "tether",
    "usdc": "usd-coin",
}


async def fetch_unit_usd(slug: str) -> float | None:
    cg_id = COINGECKO_IDS.get(slug.lower())
    if not cg_id:
        return None
    url = f"{settings.coingecko_base}/simple/price"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, params={"ids": cg_id, "vs_currencies": "usd"})
            r.raise_for_status()
            return float((r.json().get(cg_id) or {}).get("usd") or 0) or None
    except Exception as e:
        log.warning("coingecko fetch failed for %s: %s", slug, e)
        return None


async def cmd_holding(_chat_id: int, args: str) -> str:
    parts = (args or "").strip().split()
    if len(parts) < 2:
        return (
            "Usage: <code>/holding SLUG QUANTITY</code>\n"
            "Examples: <code>/holding btc 0.42</code>, <code>/holding sol 120</code>"
        )
    slug = parts[0].lower()
    try:
        qty = float(parts[1])
    except ValueError:
        return f"Couldn't parse quantity: <code>{telegram.esc(parts[1])}</code>"
    unit_usd = await fetch_unit_usd(slug)
    row = await ledger.upsert_holding(slug, qty, last_unit_usd=unit_usd)
    msg = f"✅ <code>{telegram.esc(slug)}</code> = {qty:,.6f}"
    if row["last_unit_usd"]:
        usd = qty * row["last_unit_usd"]
        msg += f" <i>(~${usd:,.2f} @ ${row['last_unit_usd']:,.2f})</i>"
    return msg

"""
Top-up rails for Zen Wallet.

Ordered by net fee impact (lowest cost to the village first). Each rail can be
either:
  - 'instant'  : automated (Stripe, Solana via ZendLink). Webhook credits the
                 wallet automatically.
  - 'manual'   : guest pays out-of-band (Venmo F&F, Zelle, cash, BTC). Admin
                 confirms via /topup confirm in the Telegram bot.

bonus_rate: extra Zen Credits gifted on top of the dollar amount, paid by the
village to incentivize low-fee rails (e.g. 0.05 = 5% bonus).
"""

from __future__ import annotations

import os
from typing import Optional

# Rails — least to most fee-cost to the village.
# Ordering matters: this is the order shown to guests on /wallet.
RAILS = [
    {
        "id": "cash",
        "name": "Cash (in person)",
        "type": "manual",
        "fee_pct": 0.0,
        "bonus_rate": 0.05,
        "instructions": "Pay cash at the front desk. We'll confirm and credit your wallet within minutes.",
        "min_usd": 5,
        "max_usd": 5000,
    },
    {
        "id": "venmo",
        "name": "Venmo (Friends & Family)",
        "type": "manual",
        "fee_pct": 0.0,
        "bonus_rate": 0.04,
        "instructions": "Send to @James-Stinson-65 marked Friends & Family. Note: {REF}.",
        "min_usd": 10,
        "max_usd": 3000,
    },
    {
        "id": "btc",
        "name": "Bitcoin (on-chain)",
        "type": "manual",
        "fee_pct": 0.0,
        "bonus_rate": 0.03,
        "instructions": "Send BTC equivalent to: 13tXYGWCZWgPoZ8WZXi7vTt2kwax2ekpz7 — DM us at @zenvillagecr or message Atlas with your reference {REF} so we can confirm.",
        "min_usd": 25,
        "max_usd": 25000,
    },
    {
        "id": "paypal_friends",
        "name": "PayPal (Friends & Family)",
        "type": "manual",
        "fee_pct": 0.0,
        "bonus_rate": 0.02,
        "instructions": "Send to james@fullpotential.com marked Friends & Family. Note: {REF}.",
        "min_usd": 10,
        "max_usd": 3000,
    },
    {
        "id": "wise",
        "name": "Wise",
        "type": "manual",
        "fee_pct": 0.0,
        "bonus_rate": 0.02,
        "instructions": "Pay via Wise: {WISE_LINK}. Reference: {REF}. We'll confirm once it lands.",
        "min_usd": 10,
        "max_usd": 10000,
    },
    {
        "id": "stripe_card",
        "name": "Credit / Debit card",
        "type": "instant",
        "fee_pct": 0.029,
        "bonus_rate": 0.0,
        "instructions": "Auto-credited via Stripe checkout after card payment.",
        "min_usd": 5,
        "max_usd": 10000,
        "requires_zendlink": True,
    },
]


def _addresses() -> dict:
    return {
        "WISE_LINK": os.getenv("WISE_LINK", "https://wise.com/pay/business/coranationchurch"),
    }


def hydrate_instructions(rail: dict, ref: str) -> str:
    text = rail.get("instructions", "")
    repl = {"REF": ref or "—", **_addresses()}
    for k, v in repl.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def list_rails(include_instant: bool = True, include_manual: bool = True) -> list[dict]:
    out = []
    for r in RAILS:
        if r["type"] == "instant" and not include_instant:
            continue
        if r["type"] == "manual" and not include_manual:
            continue
        out.append(dict(r))
    return out


def get_rail(rail_id: str) -> Optional[dict]:
    for r in RAILS:
        if r["id"] == rail_id:
            return dict(r)
    return None


def calc_bonus(rail_id: str, amount_usd: float) -> float:
    r = get_rail(rail_id)
    if not r:
        return 0.0
    return round(float(amount_usd) * float(r.get("bonus_rate") or 0), 2)


def credits_for(rail_id: str, amount_usd: float) -> dict:
    """Return {usd, bonus, total} where total = usd + bonus (in ZC = USD)."""
    bonus = calc_bonus(rail_id, amount_usd)
    return {
        "usd": float(amount_usd),
        "bonus": bonus,
        "total": round(float(amount_usd) + bonus, 2),
    }

"""/log /expense /income — direct, structured entry."""
from __future__ import annotations

import shlex
from datetime import datetime, timezone

from .. import ledger, telegram
from ..config import settings


def _esc(s: str) -> str:
    return telegram.esc(s)


def _parse_amount(token: str) -> float | None:
    try:
        return float(token.replace(",", "").replace("$", "").lstrip("+"))
    except ValueError:
        return None


async def cmd_log(chat_id: int, args: str, *, force_sign: int | None = None) -> str:
    """
    /log <amount> <category> [account] [vendor or "note"]
    /expense  → force_sign=-1
    /income   → force_sign=+1
    """
    if not args.strip():
        return (
            "<b>Usage</b>\n"
            "  <code>/log AMOUNT CATEGORY [ACCOUNT] [\"NOTE\"]</code>\n"
            "  <code>/expense AMOUNT CATEGORY [ACCOUNT] [\"NOTE\"]</code>\n"
            "  <code>/income AMOUNT CATEGORY [ACCOUNT] [\"NOTE\"]</code>\n\n"
            "Positive amount = income, negative = expense (unless using /expense or /income)."
        )
    try:
        parts = shlex.split(args)
    except ValueError:
        parts = args.split()
    if len(parts) < 2:
        return "Need at least an amount and a category. Try /log 100 revenue stripe."
    amount = _parse_amount(parts[0])
    if amount is None:
        return f"Couldn't parse amount: <code>{_esc(parts[0])}</code>"
    if force_sign is not None:
        amount = abs(amount) * force_sign
    category = parts[1].lower()
    account_slug = parts[2] if len(parts) > 2 else "default"
    note: str | None = None
    vendor: str | None = None
    if len(parts) > 3:
        rest = " ".join(parts[3:]).strip()
        if rest:
            note = rest
            vendor = rest.split(",", 1)[0][:80]

    result = await ledger.insert_txn(
        ledger.TxnInsert(
            account_slug=account_slug,
            amount=amount,
            currency=settings.default_currency,
            category=category,
            vendor=vendor,
            note=note,
            occurred_at=datetime.now(timezone.utc),
            source="manual",
        )
    )
    if result.get("duplicate"):
        return (
            "⚠️ Already logged a transaction with the same date+amount+vendor. "
            "If this is a real second entry, add a distinguishing vendor or use /import."
        )

    sign = "+" if amount >= 0 else "−"
    return (
        f"✅ Logged: <code>{_esc(account_slug)}</code> "
        f"{sign}{abs(amount):,.2f} {settings.default_currency} · "
        f"<i>{_esc(category)}</i>"
        + (f" · <i>{_esc(note)}</i>" if note else "")
    )

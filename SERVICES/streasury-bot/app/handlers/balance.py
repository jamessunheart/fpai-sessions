"""/balance and /accounts."""
from __future__ import annotations

from .. import ledger, telegram
from ..reports.formatters import render_balances


def _esc(s: str) -> str:
    return telegram.esc(s)


async def cmd_balance(_chat_id: int, _args: str) -> str:
    rows = await ledger.list_accounts(include_archived=False)
    return render_balances(rows)


async def cmd_accounts(_chat_id: int, args: str) -> str:
    parts = (args or "").strip().split()
    if not parts or parts[0] == "list":
        rows = await ledger.list_accounts(include_archived=True)
        if not rows:
            return "No accounts yet."
        lines = ["<b>📒 Accounts</b>"]
        for r in rows:
            tag = " <i>(archived)</i>" if r["archived"] else ""
            lines.append(
                f"  • <code>{_esc(r['slug'])}</code> ({_esc(r['currency'])}, "
                f"{_esc(r['kind'])}) — {r['balance']:,.2f}{tag}"
            )
        return "\n".join(lines)

    sub = parts[0]
    if sub == "add":
        if len(parts) < 2:
            return "Usage: <code>/accounts add SLUG [CURRENCY] [KIND]</code>"
        slug = parts[1]
        currency = parts[2] if len(parts) > 2 else "USD"
        kind = parts[3] if len(parts) > 3 else "cash"
        await ledger.ensure_account(slug, currency=currency.upper(), kind=kind.lower())
        return f"✅ Account <code>{_esc(slug)}</code> ready ({_esc(currency.upper())} / {_esc(kind)})."
    if sub == "archive":
        if len(parts) < 2:
            return "Usage: <code>/accounts archive SLUG</code>"
        ok = await ledger.archive_account(parts[1], True)
        return "✅ archived" if ok else "Account not found."
    if sub == "unarchive":
        if len(parts) < 2:
            return "Usage: <code>/accounts unarchive SLUG</code>"
        ok = await ledger.archive_account(parts[1], False)
        return "✅ unarchived" if ok else "Account not found."

    return "Unknown subcommand. Try: <code>/accounts list | add | archive | unarchive</code>"

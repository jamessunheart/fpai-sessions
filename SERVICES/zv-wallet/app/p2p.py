"""Peer-to-peer CORA transfer module.

Implements v4.1 agreement section: Peer-to-Peer Transfers.

Features (v0.1):
  1. /transfer @user <amount> [memo...]      -- wallet-to-wallet CORA move
  2. /history                                 -- last 10 personal transactions
  3. Large-transfer flag (>=500 CORA)         -- visibility-only steward notification
  4. NO third-party exchange integration      -- explicit reject in API
  5. NO ZV-side exchange (no cash↔CORA swap)  -- documented, enforced

Governance flag: any change to the transfer rules requires CORA Nation
governance approval (not Ember/Forge unilateral). Tracked via GOVERNANCE_LOCKED.
"""
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime, timezone

from .db import conn, audit_log, now_iso


# ----- Constants ---------------------------------------------------------

LARGE_TRANSFER_THRESHOLD = 500           # CORA units; flag-only, not gated
AUDIT_LOG_PATH = Path(
    os.environ.get(
        "ZV_WALLET_LARGE_XFER_LOG",
        os.path.expanduser("~/.config/fpai/zv_wallet/large_transfer_audit.log"),
    )
)
HISTORY_DEFAULT_LIMIT = 10

# Governance lock — only flips via CORA Nation governance vote.
# Ember/Forge must NOT modify these rules unilaterally; this constant
# exists so any future PR touching it is visibly reviewable.
GOVERNANCE_LOCKED = {
    "no_third_party_exchange": True,
    "no_zv_side_cash_exchange": True,
    "peer_to_peer_only": True,
}

REJECT_EXCHANGE_REASON = (
    "ZV Wallet does not integrate with any third-party exchange. "
    "CORA is peer-to-peer only between members. "
    "Any change requires CORA Nation governance approval."
)

DISCLAIMER = (
    "ℹ️ *CORA is a peer-to-peer recognition unit only.*\n"
    "• Transfers happen wallet-to-wallet between members\n"
    "• No cash exchange inside ZV channels (no buying/selling CORA)\n"
    "• No third-party exchanges connected\n"
    "• Governance changes require CORA Nation vote"
)


# ----- Schema additions --------------------------------------------------

P2P_SCHEMA = """
CREATE TABLE IF NOT EXISTS p2p_transfers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  from_phone TEXT NOT NULL,
  to_phone TEXT NOT NULL,
  amount INTEGER NOT NULL,           -- CORA units, positive
  memo TEXT,
  ts TEXT NOT NULL,
  large_flag INTEGER NOT NULL DEFAULT 0,
  steward_notified INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_p2p_from ON p2p_transfers(from_phone, ts);
CREATE INDEX IF NOT EXISTS idx_p2p_to ON p2p_transfers(to_phone, ts);
"""


def init_p2p_schema() -> None:
    with conn() as c:
        c.executescript(P2P_SCHEMA)


# ----- Core transfer logic ------------------------------------------------

class TransferError(Exception):
    pass


def _resolve_phone(token: str) -> str | None:
    """Resolve '@user' or display name or raw phone to canonical phone.

    v0.1: prefer exact phone match; fall back to display_name LIKE; strip '@'.
    """
    raw = token.strip().lstrip("@")
    with conn() as c:
        # Try phone first (E.164 with or without leading +)
        r = c.execute(
            "SELECT phone FROM users WHERE phone = ? OR phone = ? LIMIT 1",
            (raw, "+" + raw.lstrip("+"))
        ).fetchone()
        if r:
            return r["phone"]
        # Fallback: display_name match (case-insensitive)
        r = c.execute(
            "SELECT phone FROM users WHERE LOWER(display_name) = LOWER(?) LIMIT 1",
            (raw,)
        ).fetchone()
        if r:
            return r["phone"]
    return None


def _get_balance(phone: str) -> int:
    with conn() as c:
        r = c.execute("SELECT balance FROM cora_balances WHERE phone = ?", (phone,)).fetchone()
    return r["balance"] if r else 0


def _audit_large_transfer(transfer: dict) -> None:
    """Append to the large-transfer file audit log (in addition to DB audit)."""
    try:
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG_PATH.open("a") as f:
            f.write(
                f"{transfer['ts']}\tid={transfer['id']}\t"
                f"from={transfer['from_phone']}\tto={transfer['to_phone']}\t"
                f"amount={transfer['amount']}\tmemo={transfer.get('memo') or ''}\n"
            )
    except OSError as e:
        # Don't break the transfer if the audit file is unwritable.
        audit_log("system", "large_xfer_audit_write_failed", str(transfer["id"]), str(e))


def execute_transfer(
    from_phone: str,
    to_token: str,
    amount: int,
    memo: str | None = None,
) -> dict:
    """Move `amount` CORA from sender to receiver.

    Returns a dict describing the transfer. Raises TransferError on failure.
    """
    if amount <= 0:
        raise TransferError("Amount must be positive.")
    if amount > 10_000_000:
        raise TransferError("Amount exceeds sanity ceiling (10M).")

    to_phone = _resolve_phone(to_token)
    if not to_phone:
        raise TransferError(f"Could not resolve recipient: {to_token}")
    if to_phone == from_phone:
        raise TransferError("Cannot transfer to yourself.")

    sender_bal = _get_balance(from_phone)
    if sender_bal < amount:
        raise TransferError(f"Insufficient balance. Have {sender_bal}, need {amount}.")

    ts = now_iso()
    large = 1 if amount >= LARGE_TRANSFER_THRESHOLD else 0

    with conn() as c:
        # Ensure both balance rows exist
        c.execute(
            """INSERT INTO cora_balances (phone, balance, lifetime_earned, lifetime_spent, updated_at)
               VALUES (?, 0, 0, 0, ?)
               ON CONFLICT(phone) DO NOTHING""",
            (from_phone, ts),
        )
        c.execute(
            """INSERT INTO cora_balances (phone, balance, lifetime_earned, lifetime_spent, updated_at)
               VALUES (?, 0, 0, 0, ?)
               ON CONFLICT(phone) DO NOTHING""",
            (to_phone, ts),
        )

        # Debit sender
        c.execute(
            """UPDATE cora_balances
               SET balance = balance - ?, lifetime_spent = lifetime_spent + ?, updated_at = ?
               WHERE phone = ?""",
            (amount, amount, ts, from_phone),
        )
        sender_after = c.execute(
            "SELECT balance FROM cora_balances WHERE phone = ?", (from_phone,)
        ).fetchone()["balance"]

        # Credit receiver
        c.execute(
            """UPDATE cora_balances
               SET balance = balance + ?, lifetime_earned = lifetime_earned + ?, updated_at = ?
               WHERE phone = ?""",
            (amount, amount, ts, to_phone),
        )
        receiver_after = c.execute(
            "SELECT balance FROM cora_balances WHERE phone = ?", (to_phone,)
        ).fetchone()["balance"]

        # Insert transfer record
        cur = c.execute(
            """INSERT INTO p2p_transfers
               (from_phone, to_phone, amount, memo, ts, large_flag)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (from_phone, to_phone, amount, memo, ts, large),
        )
        transfer_id = cur.lastrowid

        # Mirror in cora_ledger for unified history
        c.execute(
            """INSERT INTO cora_ledger (phone, delta, reason, ref_id, balance_after, ts)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (from_phone, -amount, f"p2p_send_to_{to_phone}", transfer_id, sender_after, ts),
        )
        c.execute(
            """INSERT INTO cora_ledger (phone, delta, reason, ref_id, balance_after, ts)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (to_phone, amount, f"p2p_recv_from_{from_phone}", transfer_id, receiver_after, ts),
        )

    audit_log(from_phone, "p2p_transfer", str(transfer_id),
              f"{amount} CORA -> {to_phone} | memo={memo or ''}")

    record = {
        "id": transfer_id,
        "from_phone": from_phone,
        "to_phone": to_phone,
        "amount": amount,
        "memo": memo,
        "ts": ts,
        "large_flag": large,
        "sender_balance_after": sender_after,
        "receiver_balance_after": receiver_after,
    }

    if large:
        _audit_large_transfer(record)

    return record


# ----- History queries ---------------------------------------------------

def personal_history(phone: str, limit: int = HISTORY_DEFAULT_LIMIT) -> list[dict]:
    """Last N transactions involving this phone (in OR out), newest-first."""
    with conn() as c:
        rows = c.execute(
            """SELECT id, from_phone, to_phone, amount, memo, ts, large_flag
               FROM p2p_transfers
               WHERE from_phone = ? OR to_phone = ?
               ORDER BY id DESC LIMIT ?""",
            (phone, phone, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def all_transfers(
    limit: int = 200,
    counterparty: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> list[dict]:
    """Steward read-only view across all P2P transfers, with filters."""
    q = "SELECT id, from_phone, to_phone, amount, memo, ts, large_flag FROM p2p_transfers WHERE 1=1"
    params: list = []
    if counterparty:
        q += " AND (from_phone = ? OR to_phone = ?)"
        params.extend([counterparty, counterparty])
    if since:
        q += " AND ts >= ?"
        params.append(since)
    if until:
        q += " AND ts <= ?"
        params.append(until)
    q += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with conn() as c:
        rows = c.execute(q, params).fetchall()
    return [dict(r) for r in rows]


def pending_steward_notifications(limit: int = 50) -> list[dict]:
    """Large transfers not yet notified to steward channel."""
    with conn() as c:
        rows = c.execute(
            """SELECT id, from_phone, to_phone, amount, memo, ts
               FROM p2p_transfers
               WHERE large_flag = 1 AND steward_notified = 0
               ORDER BY id ASC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_steward_notified(transfer_id: int) -> None:
    with conn() as c:
        c.execute(
            "UPDATE p2p_transfers SET steward_notified = 1 WHERE id = ?",
            (transfer_id,),
        )


# ----- Formatting -------------------------------------------------------

def format_history(rows: list[dict], me: str) -> str:
    if not rows:
        return "_No transactions yet._"
    lines = [f"*Last {len(rows)} transactions:*"]
    for r in rows:
        if r["from_phone"] == me:
            direction = "→"
            other = r["to_phone"]
            sign = "-"
        else:
            direction = "←"
            other = r["from_phone"]
            sign = "+"
        memo = f" · _{r['memo']}_" if r.get("memo") else ""
        flag = " ⚑" if r.get("large_flag") else ""
        lines.append(f"  #{r['id']} {direction} {other} · {sign}{r['amount']} CORA{flag}{memo}")
    return "\n".join(lines)


def format_transfer_confirmation(rec: dict, perspective: str) -> str:
    """Confirmation message tailored for sender or receiver."""
    if perspective == "sender":
        return (
            f"✓ Sent {rec['amount']} CORA → {rec['to_phone']}"
            f"{' · memo: ' + rec['memo'] if rec.get('memo') else ''}\n"
            f"Balance: {rec['sender_balance_after']} CORA"
            f"{' · ⚑ flagged (visibility only)' if rec.get('large_flag') else ''}"
        )
    return (
        f"💌 Received {rec['amount']} CORA from {rec['from_phone']}"
        f"{' · memo: ' + rec['memo'] if rec.get('memo') else ''}\n"
        f"Balance: {rec['receiver_balance_after']} CORA"
    )

"""ROI ledger — daily cost-vs-engagement row for @sunheartbrain_bot.

Ported from Adam's adam-roi-ledger.sh. The disciplined piece is the alert
thresholds: many bot replies with zero James interactions = a runaway loop
talking to itself; that pattern is what burned tokens on metaclaw before it
was killed (2026-04-30).

Sources:
    brain_index.tg_messages — role/at/chat_id, last 24h
        bot replies (role='bot', chat=owner)  → claude_calls proxy
        owner messages (role='user', chat=owner) → james_interactions

Output:
    /var/lib/sh-brain/roi.jsonl — one JSON row per run, append-only

Alerts (sent via curator.telegram.send):
    bot_out > 50 AND james_in == 0  → self_throttle
    bot_out > 100                   → high_burn
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import telegram as tg
from ..db import connect

log = logging.getLogger("curator.roi")


LEDGER_PATH = Path(os.environ.get("SH_ROI_LEDGER", "/var/lib/sh-brain/roi.jsonl"))
COST_PER_CALL_USD = float(os.environ.get("SH_ROI_COST_PER_CALL_USD", "0.03"))
SELF_THROTTLE_THRESHOLD = int(os.environ.get("SH_ROI_SELF_THROTTLE", "50"))
HIGH_BURN_THRESHOLD = int(os.environ.get("SH_ROI_HIGH_BURN", "100"))
OWNER_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


async def run(run_id: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    row = await _gather(now)

    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    if row["alerts"]:
        await _alert(row)

    log.info("roi run=%s row=%s", run_id, json.dumps(row))
    return row


async def _gather(now: datetime) -> dict[str, Any]:
    bot_out = 0
    james_in = 0
    bot_out_total = 0
    james_in_total = 0
    if OWNER_CHAT_ID:
        try:
            async with connect() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT role, COUNT(*)::int
                          FROM brain_index.tg_messages
                         WHERE chat_id = %s
                           AND at > NOW() - INTERVAL '24 hours'
                         GROUP BY role
                        """,
                        (OWNER_CHAT_ID,),
                    )
                    counts = dict(await cur.fetchall())
                    bot_out = int(counts.get("bot", 0) or 0)
                    james_in = int(counts.get("user", 0) or 0)

                    await cur.execute(
                        """
                        SELECT role, COUNT(*)::int
                          FROM brain_index.tg_messages
                         WHERE chat_id = %s
                         GROUP BY role
                        """,
                        (OWNER_CHAT_ID,),
                    )
                    totals = dict(await cur.fetchall())
                    bot_out_total = int(totals.get("bot", 0) or 0)
                    james_in_total = int(totals.get("user", 0) or 0)
        except Exception as e:
            log.warning("roi tg_messages query failed: %s", e)

    est_cost = round(bot_out * COST_PER_CALL_USD, 4)
    value_proxy = round(james_in / bot_out, 4) if bot_out > 0 else None

    alerts: list[str] = []
    if bot_out > SELF_THROTTLE_THRESHOLD and james_in == 0:
        alerts.append("self_throttle_no_james")
    if bot_out > HIGH_BURN_THRESHOLD:
        alerts.append("high_burn")

    return {
        "schema": "sh_brain_roi_v1",
        "ts_utc": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "date": now.date().isoformat(),
        "bot_replies_24h": bot_out,
        "james_messages_24h": james_in,
        "claude_call_proxy": bot_out,
        "est_cost_usd_24h": est_cost,
        "cost_per_call_usd": COST_PER_CALL_USD,
        "value_proxy_james_per_bot_reply": value_proxy,
        "totals_lifetime": {"bot": bot_out_total, "user": james_in_total},
        "alerts": alerts,
    }


async def _alert(row: dict[str, Any]) -> None:
    if not tg.enabled():
        return
    cost = row["est_cost_usd_24h"]
    bot = row["bot_replies_24h"]
    james = row["james_messages_24h"]
    alert_lines = []
    if "high_burn" in row["alerts"]:
        alert_lines.append(f"🔥 <b>HIGH BURN</b> — {bot} bot replies in 24h (~${cost:.2f})")
    if "self_throttle_no_james" in row["alerts"]:
        alert_lines.append(
            f"⚠️ <b>SELF-THROTTLE</b> — {bot} bot replies but {james} from James. "
            "Bot may be talking to itself."
        )
    if not alert_lines:
        return
    body = (
        "🚨 <b>Brain ROI alert</b>\n\n"
        + "\n".join(alert_lines)
        + f"\n\n<i>Source: {tg._esc(str(LEDGER_PATH))}</i>"
    )
    await tg.send(body)

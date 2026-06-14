"""ZV Work Credit Group Observer v0.1.

Observes a designated WhatsApp group chat ("Zen Village Work Credits"), parses
incoming messages for work-of-proof claims via Claude Haiku 4.5 (text + vision),
queues a pending Work Credit attribution, then waits for a witness to approve or
reject via WhatsApp reaction (✅ / ❌).

Phoenix discipline (raw-first):
    Every group message is persisted to `group_messages` BEFORE parsing. If the
    Anthropic API is down, the raw row stays in place (parsed=0) so a future
    background worker can pick it up. Approved balances live in our DB —
    Evolution API or even WhatsApp itself disappearing doesn't lose anything.

State machine:
    inbound text/image  -> persist raw -> parse -> if work_claim & conf > 0.7
        -> insert pending row + bot inline-replies (quote-reply) with the
           pending offer ("react ✅ to approve")
        -> on `messages.reaction` from witness role:
            ✅ -> move to approved · credit WC · refresh leaderboard
            ❌ -> move to rejected · post decline reason

Manual override:
    Any witness can post `!credit @user Xhr <activity>` in the group to bypass
    the parser. Same approval pipeline (auto-approved on the !credit itself).

Classification:
    Group messages default `COUNCIL-RESTRICTED`. Leaderboard exposes only
    aggregated sanitized stats (PUBLIC tier).
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from . import evo, mechanics
from .db import conn, now_iso, audit_log
from .work_parser import parse_work_claim

# Allow only the configured ZV group(s) to drive credit awards.
# If empty, ALL groups are observed (useful for first-onboarding QR test).
ALLOWED_GROUP_JIDS = {
    g.strip()
    for g in os.environ.get("ZV_GROUP_JIDS", "").split(",")
    if g.strip()
}

CONFIDENCE_THRESHOLD = float(os.environ.get("ZV_PARSER_CONFIDENCE", "0.7"))
# v8: rate = $20/hr, weekly cap = 20 hrs / $400 ZWC (sourced from mechanics)
# Note: $400 ZWC/wk exactly covers the Shared/Glamping $400 invoice in v8.
# Private Room volunteers cover the $200 gap via ZV-discretionary ZWC bonus
# (typical at Sunday Seal for strong delivery) or cash/CORA from wallet.
WC_PER_HOUR = mechanics.WC_RATE_PER_HOUR

REACTION_APPROVE = {"✅", "👍", "✔️", "✅️"}
REACTION_REJECT = {"❌", "👎", "🚫"}

OVERRIDE_PATTERN = re.compile(
    r"^!credit\s+@?(\S+)\s+([\d.]+)\s*hr?s?\s+(.+)$",
    re.IGNORECASE,
)


# ---------- public API ----------


async def process_message(data: dict[str, Any]) -> None:
    """Entry point: a group-chat `messages.upsert` event from Evolution API.

    `data` is the inner Evolution payload (already unwrapped from the outer
    webhook envelope). The caller (main.handle_inbound) is responsible for
    routing DMs to the existing wallet handler; this function only handles
    group messages.
    """
    msg = data if data.get("key") else (
        data.get("messages", [{}])[0]
        if isinstance(data.get("messages"), list)
        else data
    )
    key = msg.get("key") or {}
    if key.get("fromMe"):
        return  # ignore our own outgoing

    remote = key.get("remoteJid") or ""
    if not remote.endswith("@g.us"):
        return  # not a group; caller should not have routed here

    if ALLOWED_GROUP_JIDS and remote not in ALLOWED_GROUP_JIDS:
        # Group not whitelisted — still log it for observability, then exit
        await _persist_raw(msg, parsed=1, note="group_not_allowed")
        return

    # The actual sender inside a group lives in key.participant (a @s.whatsapp.net jid)
    sender_jid = key.get("participant") or remote
    display_name = msg.get("pushName") or msg.get("verifiedBizName") or ""

    body_msg = msg.get("message") or {}
    text = (
        body_msg.get("conversation")
        or (body_msg.get("extendedTextMessage") or {}).get("text")
        or (body_msg.get("imageMessage") or {}).get("caption")
        or (body_msg.get("videoMessage") or {}).get("caption")
        or ""
    )

    media_path = None
    media_type = None
    if "imageMessage" in body_msg:
        media_type = "image"
        media_path = await evo.download_media(key.get("id") or "")
    elif "videoMessage" in body_msg:
        media_type = "video"
        media_path = await evo.download_media(key.get("id") or "")
    elif "audioMessage" in body_msg:
        media_type = "audio"
        media_path = await evo.download_media(key.get("id") or "")

    # 1. PHOENIX: persist raw FIRST
    message_id = key.get("id") or ""
    await _persist_raw(
        msg,
        sender_jid=sender_jid,
        display_name=display_name,
        text=text,
        media_path=media_path,
        media_type=media_type,
    )

    # 2. Manual override path — witness can bypass parser
    override = _try_override(text)
    if override is not None:
        if not _is_witness(sender_jid):
            await evo.send_text(
                remote,
                "_Witness role required to use `!credit` override. "
                "Existing pending entries still flow via parser._",
            )
            return
        await _record_override(
            group_jid=remote,
            witness_jid=sender_jid,
            witness_display_name=display_name,
            target_handle=override["target"],
            hours=override["hours"],
            activity=override["activity"],
            source_message_id=message_id,
        )
        return

    # 3. PARSE via Haiku
    parsed = await parse_work_claim(
        text=text,
        image_url=media_path,
        sender_display_name=display_name,
    )

    # Mark the row as parsed (regardless of outcome). If Anthropic failed,
    # leave parsed=0 so a future retry worker can pick it up.
    parser_failed = bool(parsed.get("_parser_error"))
    if not parser_failed:
        _mark_parsed(message_id)

    audit_log(
        sender_jid,
        "group_msg_parsed",
        message_id,
        json.dumps(
            {
                "is_work_claim": parsed.get("is_work_claim"),
                "confidence": parsed.get("confidence"),
                "cost_usd": parsed.get("_cost_usd"),
                "error": parsed.get("_parser_error"),
            }
        ),
    )

    if not parsed.get("is_work_claim"):
        return  # banter / greetings / planning — nothing to do

    conf = float(parsed.get("confidence") or 0.0)
    if conf <= CONFIDENCE_THRESHOLD:
        # Low confidence — ask for clarification (inline, in the group)
        reply = (
            "🤔 Couldn't parse clearly · please clarify hours + activity · "
            "or witness override: `!credit @user 2hr <activity>`"
        )
        await evo.send_text(remote, reply)
        return

    # 4. Insert pending row + bot reply
    hours = float(parsed.get("hours_claimed") or 0.0)
    if hours <= 0:
        # No hours could be extracted at high confidence — also clarify
        await evo.send_text(
            remote,
            "🤔 I can see a work claim but couldn't read hours · "
            "please reply with a number of hours, or use "
            "`!credit @user 2hr <activity>`",
        )
        return

    # Compute ZWC with v8 weekly-cap awareness. We check the actor's
    # running week balance and clamp the pending amount so a single witness
    # approval can't exceed $400 ZWC for the week. Overage hours still help
    # complete priorities (which earn CORA bonuses).
    raw_wc = int(round(hours * WC_PER_HOUR))
    weekly_already = _week_to_date_wc(sender_jid)
    cap_remaining = max(mechanics.WC_WEEKLY_CAP_AMOUNT - weekly_already, 0)
    wc_amount = min(raw_wc, cap_remaining)
    capped = wc_amount < raw_wc

    activity = (parsed.get("activity") or "(unspecified)").strip()
    evidence = parsed.get("evidence_type") or "none"

    pending_id = _insert_pending(
        source_message_id=message_id,
        group_jid=remote,
        actor_jid=sender_jid,
        actor_display_name=display_name,
        activity=activity,
        hours=hours,
        wc_amount=wc_amount,
        evidence_type=evidence,
        confidence=conf,
        parser_json=json.dumps(parsed),
    )

    cap_note = ""
    if capped:
        cap_note = (
            f"\n⚠️ weekly cap reached · raw {raw_wc} ZWC clamped to "
            f"{wc_amount} ZWC (cap ${mechanics.WC_WEEKLY_CAP_AMOUNT}/wk · "
            f"overage helps priorities → CORA)"
        )
    reply_text = (
        f"🪙 Pending: {wc_amount} ZWC for {hours:g}hr {activity}{cap_note}\n"
        f"witness react ✅ to approve · ❌ to reject"
    )
    sent = await evo.send_text(remote, reply_text)
    bot_msg_id = _extract_sent_message_id(sent)
    if bot_msg_id:
        _attach_bot_reply_id(pending_id, bot_msg_id)


async def process_reaction(data: dict[str, Any]) -> None:
    """Handle `messages.reaction` events from Evolution API.

    Evolution shapes vary; we look for a reactor jid + the message_id of
    whatever they reacted to (which we expect to be either the bot's pending
    offer OR the original work-claim message).
    """
    reaction_payload = (
        data.get("reaction")
        or (data.get("message") or {}).get("reactionMessage")
        or data
    )
    key = data.get("key") or reaction_payload.get("key") or {}
    reactor_jid = key.get("participant") or reaction_payload.get("participant") or ""
    group_jid = key.get("remoteJid") or ""
    if not group_jid.endswith("@g.us"):
        return

    emoji = (
        reaction_payload.get("text")
        or reaction_payload.get("reaction")
        or reaction_payload.get("emoji")
        or ""
    )
    # The message that was reacted to
    target = reaction_payload.get("key") or {}
    target_mid = target.get("id") or reaction_payload.get("targetMessageId") or ""

    if not (emoji and target_mid):
        return

    pending = _find_pending_by_target(target_mid)
    if not pending:
        return  # reaction on something we're not tracking — ignore

    if not _is_witness(reactor_jid):
        # Politely note that only witnesses count
        await evo.send_text(
            group_jid,
            "_Only witness role can approve · current reaction not counted._",
        )
        return

    witness_display = _display_name_for(reactor_jid) or "witness"

    if emoji in REACTION_APPROVE:
        await _approve_pending(
            pending=pending,
            witness_jid=reactor_jid,
            witness_display_name=witness_display,
            group_jid=group_jid,
        )
    elif emoji in REACTION_REJECT:
        await _reject_pending(
            pending=pending,
            witness_jid=reactor_jid,
            witness_display_name=witness_display,
            group_jid=group_jid,
            reason=None,
        )


# ---------- persistence ----------


async def _persist_raw(
    msg: dict[str, Any],
    sender_jid: str | None = None,
    display_name: str | None = None,
    text: str | None = None,
    media_path: str | None = None,
    media_type: str | None = None,
    parsed: int = 0,
    note: str | None = None,
) -> None:
    key = msg.get("key") or {}
    group_jid = key.get("remoteJid") or ""
    message_id = key.get("id") or ""
    sender_jid = sender_jid or key.get("participant") or group_jid
    ts = int(msg.get("messageTimestamp") or msg.get("timestamp") or time.time())
    if not text and not media_path:
        body_msg = msg.get("message") or {}
        text = (
            body_msg.get("conversation")
            or (body_msg.get("extendedTextMessage") or {}).get("text")
            or ""
        )
    raw_json = json.dumps(msg)[:6000]
    with conn() as c:
        try:
            c.execute(
                """INSERT OR IGNORE INTO group_messages
                   (group_jid, sender_jid, sender_display_name, message_id,
                    message_text, media_url, media_type, timestamp,
                    raw_event_json, parsed)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    group_jid,
                    sender_jid,
                    display_name,
                    message_id,
                    text,
                    media_path,
                    media_type,
                    ts,
                    raw_json,
                    parsed,
                ),
            )
        except Exception as e:
            audit_log("system", "group_msg_persist_error", message_id, str(e)[:200])
    if note:
        audit_log(sender_jid or "?", "group_msg_note", message_id, note)


def _mark_parsed(message_id: str) -> None:
    if not message_id:
        return
    with conn() as c:
        c.execute(
            "UPDATE group_messages SET parsed = 1 WHERE message_id = ?",
            (message_id,),
        )


def _insert_pending(
    source_message_id: str,
    group_jid: str,
    actor_jid: str,
    actor_display_name: str,
    activity: str,
    hours: float,
    wc_amount: int,
    evidence_type: str,
    confidence: float,
    parser_json: str,
) -> int:
    with conn() as c:
        cur = c.execute(
            """INSERT INTO work_credit_pending
               (source_message_id, group_jid, actor_jid, actor_display_name,
                activity, hours_claimed, wc_amount, evidence_type,
                parser_confidence, parser_extracted_json, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (
                source_message_id,
                group_jid,
                actor_jid,
                actor_display_name,
                activity,
                hours,
                wc_amount,
                evidence_type,
                confidence,
                parser_json,
            ),
        )
        pid = cur.lastrowid
    audit_log(actor_jid, "wc_pending_created", str(pid), f"{wc_amount} ZWC · {activity}")
    return pid


def _attach_bot_reply_id(pending_id: int, bot_msg_id: str) -> None:
    with conn() as c:
        c.execute(
            "UPDATE work_credit_pending SET bot_reply_message_id = ? WHERE id = ?",
            (bot_msg_id, pending_id),
        )


def _find_pending_by_target(target_message_id: str) -> dict[str, Any] | None:
    """Return the pending row whose original source OR bot-reply matches."""
    with conn() as c:
        r = c.execute(
            """SELECT * FROM work_credit_pending
               WHERE status = 'pending'
                 AND (source_message_id = ? OR bot_reply_message_id = ?)
               ORDER BY id DESC LIMIT 1""",
            (target_message_id, target_message_id),
        ).fetchone()
    return dict(r) if r else None


async def _approve_pending(
    pending: dict[str, Any],
    witness_jid: str,
    witness_display_name: str,
    group_jid: str,
) -> None:
    now = int(time.time())
    actor_jid = pending["actor_jid"]
    wc = int(pending["wc_amount"])
    activity = pending["activity"]
    hours = pending["hours_claimed"]
    with conn() as c:
        c.execute(
            """UPDATE work_credit_pending
               SET status='approved', witness_jid=?, witness_display_name=?,
                   approved_at=?
               WHERE id=? AND status='pending'""",
            (witness_jid, witness_display_name, now, pending["id"]),
        )
        # Credit the actor's WC balance. The v0.1 production schema is
        # CORA-only; the v0.2 dual-ledger migration introduces
        # `work_credits_balances`. To avoid coupling this observer to that
        # migration's timing, we credit via the audit log + a derived view.
        # If the v0.2 table already exists, we credit there too.
        _credit_wc_balance(c, actor_jid, wc, pending["id"])
        new_balance = _read_wc_balance(c, actor_jid)
    actor_display = pending.get("actor_display_name") or actor_jid.split("@")[0]
    msg = (
        f"✅ {actor_display} credited {wc} ZWC by {witness_display_name} · "
        f"running balance: {new_balance} ZWC"
    )
    await evo.send_text(group_jid, msg)
    audit_log(witness_jid, "wc_approved", str(pending["id"]),
              f"{wc} WC -> {actor_jid} for {hours}hr {activity}")
    _publish_leaderboard_event("approved", pending, witness_display_name, new_balance)


async def _reject_pending(
    pending: dict[str, Any],
    witness_jid: str,
    witness_display_name: str,
    group_jid: str,
    reason: str | None,
) -> None:
    now = int(time.time())
    with conn() as c:
        c.execute(
            """UPDATE work_credit_pending
               SET status='rejected', witness_jid=?, witness_display_name=?,
                   witness_reason=?, rejected_at=?
               WHERE id=? AND status='pending'""",
            (witness_jid, witness_display_name, reason, now, pending["id"]),
        )
    actor_display = pending.get("actor_display_name") or "?"
    reason_part = f" · {reason}" if reason else ""
    msg = f"❌ Not credited · {witness_display_name} declined{reason_part}"
    await evo.send_text(group_jid, msg)
    audit_log(witness_jid, "wc_rejected", str(pending["id"]),
              f"{actor_display} · {reason or 'no reason'}")
    _publish_leaderboard_event("rejected", pending, witness_display_name, None)


def _credit_wc_balance(c, actor_jid: str, wc: int, ref_id: int) -> None:
    """Credit WC. If the v0.2 work_credits_balances table exists, write there.

    Otherwise, the canonical record is the sum of approved
    `work_credit_pending` rows for this actor (computed on read). The audit
    log entry remains the source of truth in either case.
    """
    try:
        c.execute(
            """INSERT INTO work_credits_balances (phone, balance, lifetime_earned, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(phone) DO UPDATE SET
                 balance = balance + excluded.balance,
                 lifetime_earned = lifetime_earned + excluded.lifetime_earned,
                 updated_at = excluded.updated_at""",
            (actor_jid, wc, wc, now_iso()),
        )
        c.execute(
            """INSERT INTO work_credits_ledger
               (phone, delta, reason, ref_id, balance_after, ts)
               VALUES (?, ?, ?, ?,
                       (SELECT balance FROM work_credits_balances WHERE phone = ?),
                       ?)""",
            (actor_jid, wc, "group_observer_approved", ref_id, actor_jid, now_iso()),
        )
    except Exception:
        # v0.2 schema not yet applied — that's fine, derive from pending table
        pass


def _week_to_date_wc(actor_jid: str) -> int:
    """Return the ZWC already credited to this actor since the most-recent
    Sunday 00:00 (witness/seal-cycle boundary per v8 §6 Sunday Seal).

    Used to enforce the v8 hard weekly cap of $400 ZWC per actor per week.
    """
    if not actor_jid:
        return 0
    # Compute the Unix timestamp of the most-recent Sunday 00:00 local.
    # We treat Sunday as the boundary because Sunday Seal locks the week.
    import datetime as _dt
    now_dt = _dt.datetime.now()
    # weekday(): Monday=0, Sunday=6
    days_since_sunday = (now_dt.weekday() + 1) % 7
    sunday = (now_dt - _dt.timedelta(days=days_since_sunday)).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    week_start_ts = int(sunday.timestamp())
    with conn() as c:
        r = c.execute(
            """SELECT COALESCE(SUM(wc_amount), 0) AS w
               FROM work_credit_pending
               WHERE actor_jid = ?
                 AND status = 'approved'
                 AND COALESCE(approved_at, 0) >= ?""",
            (actor_jid, week_start_ts),
        ).fetchone()
    return int((r["w"] if r else 0) or 0)


def _read_wc_balance(c, actor_jid: str) -> int:
    """Derived ZWC balance: prefer v0.2 table, else sum approved pending rows."""
    try:
        r = c.execute(
            "SELECT balance FROM work_credits_balances WHERE phone = ?",
            (actor_jid,),
        ).fetchone()
        if r:
            return int(r["balance"])
    except Exception:
        pass
    r = c.execute(
        """SELECT COALESCE(SUM(wc_amount), 0) AS b
           FROM work_credit_pending
           WHERE actor_jid = ? AND status = 'approved'""",
        (actor_jid,),
    ).fetchone()
    return int(r["b"] if r else 0)


# ---------- roles ----------


def _is_witness(jid: str) -> bool:
    if not jid:
        return False
    with conn() as c:
        r = c.execute(
            "SELECT role FROM member_roles WHERE jid = ?", (jid,)
        ).fetchone()
    return bool(r and r["role"] in ("witness", "steward"))


def _display_name_for(jid: str) -> str | None:
    with conn() as c:
        r = c.execute(
            "SELECT display_name FROM member_roles WHERE jid = ?", (jid,)
        ).fetchone()
    return r["display_name"] if r else None


# ---------- manual override ----------


def _try_override(text: str | None) -> dict[str, Any] | None:
    if not text:
        return None
    m = OVERRIDE_PATTERN.match(text.strip())
    if not m:
        return None
    target, hours_str, activity = m.group(1), m.group(2), m.group(3)
    try:
        hours = float(hours_str)
    except ValueError:
        return None
    return {"target": target, "hours": hours, "activity": activity.strip()}


async def _record_override(
    group_jid: str,
    witness_jid: str,
    witness_display_name: str,
    target_handle: str,
    hours: float,
    activity: str,
    source_message_id: str,
) -> None:
    """Witness-issued manual credit. Auto-approved (override == witness intent)."""
    # Resolve target handle -> jid. v0.1 heuristic: if target_handle looks like a
    # phone (digits), assume `<digits>@s.whatsapp.net`. Otherwise treat as
    # display_name and look up in member_roles.
    actor_jid = _resolve_handle_to_jid(target_handle)
    actor_display = (
        _display_name_for(actor_jid) or target_handle
        if actor_jid
        else target_handle
    )
    if not actor_jid:
        # Couldn't resolve — still record as pending under the handle string so
        # nothing is lost. A steward can fix the JID later in the DB.
        actor_jid = target_handle
    # v8: apply weekly cap to override path too. Witness !credit bypasses
    # the parser confidence gate but still respects the $400/wk ZWC ceiling
    # unless the witness is a steward AND explicitly uses an `!credit-override`
    # tag (out-of-scope here; for now, hard cap applies even to !credit).
    raw_wc = int(round(hours * WC_PER_HOUR))
    weekly_already = _week_to_date_wc(actor_jid)
    cap_remaining = max(mechanics.WC_WEEKLY_CAP_AMOUNT - weekly_already, 0)
    wc = min(raw_wc, cap_remaining)
    pending_id = _insert_pending(
        source_message_id=source_message_id,
        group_jid=group_jid,
        actor_jid=actor_jid,
        actor_display_name=actor_display,
        activity=activity,
        hours=hours,
        wc_amount=wc,
        evidence_type="override",
        confidence=1.0,
        parser_json=json.dumps({"override": True, "issued_by": witness_jid}),
    )
    # Auto-approve immediately
    pending = {
        "id": pending_id,
        "actor_jid": actor_jid,
        "actor_display_name": actor_display,
        "wc_amount": wc,
        "hours_claimed": hours,
        "activity": activity,
    }
    await _approve_pending(
        pending=pending,
        witness_jid=witness_jid,
        witness_display_name=witness_display_name,
        group_jid=group_jid,
    )


def _resolve_handle_to_jid(handle: str) -> str | None:
    """Best-effort resolve `@alice` or digits to a JID."""
    h = handle.lstrip("@").strip()
    if h.isdigit() and len(h) >= 7:
        return f"{h}@s.whatsapp.net"
    with conn() as c:
        r = c.execute(
            "SELECT jid FROM member_roles WHERE LOWER(display_name) = LOWER(?)",
            (h,),
        ).fetchone()
    return r["jid"] if r else None


# ---------- leaderboard event hook ----------


def _publish_leaderboard_event(
    kind: str,
    pending: dict[str, Any],
    witness_display: str | None,
    new_balance: int | None,
) -> None:
    """Hook point: write a marker so the PWA leaderboard knows to refresh.

    v0.1 is poll-based (10s on the client). This audit_log entry is enough
    signal — no push channel needed yet.
    """
    audit_log(
        "system",
        f"leaderboard_event_{kind}",
        str(pending.get("id")),
        json.dumps(
            {
                "actor": pending.get("actor_display_name"),
                "wc": pending.get("wc_amount"),
                "hours": pending.get("hours_claimed"),
                "activity": pending.get("activity"),
                "witness": witness_display,
                "balance": new_balance,
            }
        )[:500],
    )


# ---------- evo response helper ----------


def _extract_sent_message_id(send_resp: Any) -> str | None:
    """Pull the message_id from an Evolution API sendText response.

    Shape varies; we try the common locations.
    """
    if not isinstance(send_resp, dict):
        return None
    # Common shapes:
    for path in (
        ("key", "id"),
        ("message", "key", "id"),
        ("data", "key", "id"),
        ("messageInfo", "key", "id"),
    ):
        node: Any = send_resp
        ok = True
        for p in path:
            if isinstance(node, dict) and p in node:
                node = node[p]
            else:
                ok = False
                break
        if ok and isinstance(node, str):
            return node
    return None


# ---------- leaderboard read API (called from main.py) ----------


def leaderboard_snapshot(week_seconds: int = 7 * 24 * 3600) -> dict[str, Any]:
    """Aggregate read for `/api/leaderboard`. PUBLIC tier — sanitized only."""
    now = int(time.time())
    week_start = now - week_seconds
    with conn() as c:
        top = c.execute(
            """SELECT actor_display_name,
                      actor_jid,
                      SUM(wc_amount) AS wc_total,
                      COUNT(*) AS activity_count
               FROM work_credit_pending
               WHERE status='approved' AND approved_at >= ?
               GROUP BY actor_jid
               ORDER BY wc_total DESC
               LIMIT 10""",
            (week_start,),
        ).fetchall()
        ticker = c.execute(
            """SELECT approved_at, actor_display_name, activity,
                      hours_claimed, wc_amount, witness_display_name
               FROM work_credit_pending
               WHERE status='approved' AND approved_at >= ?
               ORDER BY approved_at DESC
               LIMIT 10""",
            (week_start,),
        ).fetchall()
        total_row = c.execute(
            """SELECT COALESCE(SUM(wc_amount), 0) AS t
               FROM work_credit_pending
               WHERE status='approved' AND approved_at >= ?""",
            (week_start,),
        ).fetchone()
        pending_row = c.execute(
            """SELECT COUNT(*) AS c FROM work_credit_pending WHERE status='pending'"""
        ).fetchone()

    def _sanitize_actor(name: str | None, jid: str | None) -> str:
        if name:
            return name
        if jid:
            tail = jid.split("@", 1)[0]
            # Mask middle digits for privacy
            if len(tail) > 4:
                return tail[:2] + "***" + tail[-2:]
            return "anon"
        return "anon"

    return {
        "top": [
            {
                "actor": _sanitize_actor(r["actor_display_name"], r["actor_jid"]),
                "wc_total": int(r["wc_total"] or 0),
                "activity_count": int(r["activity_count"] or 0),
            }
            for r in top
        ],
        "ticker": [
            {
                "approved_at": int(r["approved_at"] or 0),
                "actor": _sanitize_actor(r["actor_display_name"], None),
                "activity": r["activity"],
                "hours": float(r["hours_claimed"] or 0.0),
                "wc": int(r["wc_amount"] or 0),
                "witness": r["witness_display_name"] or "witness",
            }
            for r in ticker
        ],
        "total_wc": int(total_row["t"] or 0),
        "pending_count": int(pending_row["c"] or 0),
        "generated_at": now,
        "window_seconds": week_seconds,
    }

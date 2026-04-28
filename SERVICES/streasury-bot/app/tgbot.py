"""app/tgbot.py — long-poll Telegram worker.

Owner-only. Routes:
  /help, /start                           → help text
  /log, /expense, /income                 → handlers.log
  /balance                                → handlers.balance
  /accounts                               → handlers.balance
  /holding                                → handlers.holding
  /kpi                                    → handlers.kpi
  /report                                 → handlers.report
  /ask                                    → handlers.ask (single AI)
  /council                                → handlers.ask (Claude × OpenAI + synthesis)
  /import                                 → handlers.import_ (next CSV upload)
  /recent                                 → recent transactions
  /whoami                                 → echoes the sender's TG ID (auth diag)
  <photo>                                 → vision parse → confirm-then-write
  <voice>                                 → whisper → parse → confirm-then-write
  <document .csv>                         → handlers.import_
  <free text>                             → ai.parse → confirm-then-write
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from . import ledger, telegram
from .ai import parse as nlparse
from .ai import vision, voice
from .config import settings
from .handlers import (
    ask as h_ask,
    balance as h_balance,
    holding as h_holding,
    import_ as h_import,
    kpi as h_kpi,
    log as h_log,
    report as h_report,
)

log = logging.getLogger("streasury.tgbot")


# ─── pending-confirmation state ───────────────────────────────────────────────
# In-memory: any pending AI-parsed intent or CSV-import that the user hasn't
# confirmed yet. Keyed by tg user id. Cleared on confirm/cancel/timeout.
PENDING: dict[int, dict] = {}
PENDING_TTL_SECONDS = 600


def _set_pending(user_id: int, kind: str, payload: dict) -> None:
    PENDING[user_id] = {"kind": kind, "payload": payload, "ts": time.time()}


def _get_pending(user_id: int) -> dict | None:
    p = PENDING.get(user_id)
    if not p:
        return None
    if time.time() - p["ts"] > PENDING_TTL_SECONDS:
        PENDING.pop(user_id, None)
        return None
    return p


def _clear_pending(user_id: int) -> None:
    PENDING.pop(user_id, None)


# ─── offset persistence ───────────────────────────────────────────────────────
def _offset_path() -> Path:
    return Path(settings.offset_file)


def _load_offset() -> int:
    try:
        p = _offset_path()
        return int(p.read_text().strip()) if p.exists() else 0
    except Exception:
        return 0


def _save_offset(offset: int) -> None:
    try:
        p = _offset_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(str(offset))
    except Exception as e:
        log.warning("offset save failed: %s", e)


# ─── help ────────────────────────────────────────────────────────────────────
HELP_TEXT = (
    "<b>STreasury_Bot</b> — your sovereign treasury.\n\n"
    "<b>Log</b>\n"
    "  <code>/log AMT CATEGORY [ACCOUNT] [\"NOTE\"]</code>\n"
    "  <code>/expense AMT CATEGORY [ACCOUNT] [\"NOTE\"]</code>\n"
    "  <code>/income  AMT CATEGORY [ACCOUNT] [\"NOTE\"]</code>\n"
    "  Or just talk: <i>“spent 80 on gas”</i>, send a receipt photo, or a voice note.\n\n"
    "<b>See</b>\n"
    "  <code>/balance</code> — per-account + USD total\n"
    "  <code>/accounts list | add SLUG [CCY] [KIND] | archive SLUG</code>\n"
    "  <code>/holding SLUG QTY</code> (auto USD valuation)\n"
    "  <code>/recent [N]</code>\n"
    "  <code>/report week | month | ytd | 30d | 90d</code>\n\n"
    "<b>Track KPIs</b>\n"
    "  <code>/kpi set NAME VALUE [UNIT] [\"NOTE\"]</code>\n"
    "  <code>/kpi show NAME</code> · <code>/kpi list</code>\n\n"
    "<b>Ask</b>\n"
    "  <code>/ask &lt;question&gt;</code> — one AI, fast\n"
    "  <code>/council &lt;question&gt;</code> — Claude × GPT + synthesis\n\n"
    "<b>Import</b>\n"
    "  Upload a CSV with <i>date</i> + <i>amount</i> columns.\n\n"
    "<b>Misc</b>\n"
    "  <code>/whoami</code> · <code>/help</code>"
)


# ─── auth ─────────────────────────────────────────────────────────────────────
def _is_owner(user_id: int) -> bool:
    return settings.owner_tg_id and user_id == settings.owner_tg_id


# ─── confirm formatter ────────────────────────────────────────────────────────
def _intent_summary(intent: nlparse.ParsedIntent) -> str:
    sign = "+" if intent.direction == "in" else "−"
    vendor = f" · <i>{telegram.esc(intent.vendor)}</i>" if intent.vendor else ""
    acct = telegram.esc(intent.account_slug or "default")
    when = intent.occurred_at.strftime("%Y-%m-%d") if intent.occurred_at else "today"
    return (
        f"<b>Parsed</b>\n"
        f"  {sign}{intent.amount:,.2f} {telegram.esc(intent.currency)} · "
        f"<i>{telegram.esc(intent.category)}</i>{vendor}\n"
        f"  account: <code>{acct}</code> · {when} "
        f"<i>(confidence {intent.confidence:.0%})</i>\n"
    )


def _confirm_keyboard(token: str) -> dict:
    return {
        "inline_keyboard": [[
            {"text": "✅ Confirm", "callback_data": f"i:{token}:yes"},
            {"text": "❌ Cancel",  "callback_data": f"i:{token}:no"},
        ]]
    }


# ─── handlers ────────────────────────────────────────────────────────────────
async def _handle_command(text: str, *, chat_id: int, user_id: int) -> None:
    cmd, _, rest = text.partition(" ")
    cmd = cmd.lstrip("/").split("@", 1)[0].lower()
    args = rest.strip()

    if cmd in ("help", "start"):
        await telegram.send(chat_id, HELP_TEXT)
        return
    if cmd == "whoami":
        await telegram.send(chat_id, f"You are <code>{user_id}</code>. Owner: <code>{settings.owner_tg_id}</code>")
        return
    if cmd == "log":
        await telegram.send(chat_id, await h_log.cmd_log(chat_id, args))
        return
    if cmd == "expense":
        await telegram.send(chat_id, await h_log.cmd_log(chat_id, args, force_sign=-1))
        return
    if cmd == "income":
        await telegram.send(chat_id, await h_log.cmd_log(chat_id, args, force_sign=+1))
        return
    if cmd == "balance":
        await telegram.send(chat_id, await h_balance.cmd_balance(chat_id, args))
        return
    if cmd == "accounts":
        await telegram.send(chat_id, await h_balance.cmd_accounts(chat_id, args))
        return
    if cmd == "holding":
        await telegram.send(chat_id, await h_holding.cmd_holding(chat_id, args))
        return
    if cmd == "kpi":
        await telegram.send(chat_id, await h_kpi.cmd_kpi(chat_id, args))
        return
    if cmd == "report":
        await telegram.send(chat_id, await h_report.cmd_report(chat_id, args))
        return
    if cmd == "ask":
        await telegram.send(chat_id, await h_ask.cmd_ask(chat_id, args, tg_user_id=user_id))
        return
    if cmd == "council":
        await telegram.send(chat_id, "🧠 Convening Claude × GPT council… (~20-40s)")
        claude_msg, openai_msg, synth_msg, _ = await h_ask.cmd_council(chat_id, args, tg_user_id=user_id)
        if openai_msg:
            await telegram.send(chat_id, claude_msg)
            await telegram.send(chat_id, openai_msg)
            await telegram.send(chat_id, synth_msg)
        else:
            await telegram.send(chat_id, claude_msg)  # error path
        return
    if cmd == "recent":
        try:
            n = int(args) if args.strip().isdigit() else 10
        except ValueError:
            n = 10
        rows = await ledger.list_recent_txns(limit=max(1, min(n, 50)))
        if not rows:
            await telegram.send(chat_id, "No transactions yet.")
            return
        lines = ["<b>🧾 Recent</b>"]
        for r in rows:
            sign = "+" if r["amount"] >= 0 else "−"
            ts = r["occurred_at"].strftime("%m-%d") if r["occurred_at"] else ""
            v = f" · <i>{telegram.esc(r['vendor'])}</i>" if r["vendor"] else ""
            lines.append(
                f"  <code>{ts}</code> {sign}{abs(r['amount']):,.2f} {telegram.esc(r['currency'])} "
                f"· <i>{telegram.esc(r['category'])}</i> · <code>{telegram.esc(r['account'])}</code>{v}"
            )
        await telegram.send(chat_id, "\n".join(lines))
        return
    if cmd == "import":
        await telegram.send(chat_id, "Send me a CSV file as a Telegram document. I'll preview, dedupe, and import it.")
        return

    await telegram.send(chat_id, f"Unknown command: /{telegram.esc(cmd)}. Try /help.")


async def _handle_text(text: str, *, chat_id: int, user_id: int) -> None:
    """Plain text: yes/no for pending confirms, otherwise NL parse."""
    t = text.strip().lower()
    pending = _get_pending(user_id)
    if pending and t in ("yes", "y", "confirm", "ok"):
        await _confirm_pending(user_id, chat_id)
        return
    if pending and t in ("no", "n", "cancel", "stop"):
        _clear_pending(user_id)
        await telegram.send(chat_id, "Cancelled.")
        return

    intent = await nlparse.parse_intent(text)
    if not intent or intent.amount == 0 or intent.confidence < 0.3:
        await telegram.send(
            chat_id,
            "I couldn't extract a transaction from that. Try <code>/help</code>, "
            "or be explicit: <i>spent 80 on gas</i> / <i>got 600 from acme</i>.",
        )
        return
    await _present_intent(chat_id, user_id, intent, source="text")


async def _present_intent(chat_id: int, user_id: int, intent: nlparse.ParsedIntent, *, source: str) -> None:
    intent.account_slug = intent.account_slug or "default"
    if settings.auto_confirm and intent.confidence >= 0.7:
        await _write_intent(chat_id, intent, source=source)
        return
    token = f"{user_id}-{int(time.time())}"
    _set_pending(user_id, "intent", {"intent": intent.to_dict(), "source": source})
    await telegram.send(
        chat_id,
        _intent_summary(intent) + "\nReply <b>yes</b> to confirm, <b>no</b> to cancel.",
        reply_markup=_confirm_keyboard(token),
    )


async def _write_intent(chat_id: int, intent: nlparse.ParsedIntent, *, source: str) -> None:
    occurred_at = intent.occurred_at or datetime.now(timezone.utc)
    result = await ledger.insert_txn(ledger.TxnInsert(
        account_slug=intent.account_slug or "default",
        amount=intent.signed_amount,
        currency=intent.currency,
        category=intent.category,
        vendor=intent.vendor,
        note=intent.note,
        occurred_at=occurred_at,
        source=source,
    ))
    if result.get("duplicate"):
        await telegram.send(chat_id, "⚠️ Looks like a duplicate (same date+amount+vendor). Skipped.")
        return
    sign = "+" if intent.signed_amount >= 0 else "−"
    await telegram.send(
        chat_id,
        f"✅ Logged: {sign}{abs(intent.signed_amount):,.2f} {telegram.esc(intent.currency)} "
        f"· <i>{telegram.esc(intent.category)}</i>"
        f"{(' · ' + telegram.esc(intent.vendor)) if intent.vendor else ''}",
    )


async def _confirm_pending(user_id: int, chat_id: int) -> None:
    p = _get_pending(user_id)
    if not p:
        await telegram.send(chat_id, "Nothing to confirm.")
        return
    if p["kind"] == "intent":
        d = p["payload"]["intent"]
        intent = nlparse.ParsedIntent(
            amount=float(d["amount"]),
            direction=d["direction"],
            currency=d["currency"],
            category=d["category"],
            vendor=d["vendor"],
            account_slug=d["account_slug"] or "default",
            occurred_at=datetime.fromisoformat(d["occurred_at"]) if d.get("occurred_at") else None,
            note=d["note"],
            confidence=float(d["confidence"]),
        )
        _clear_pending(user_id)
        await _write_intent(chat_id, intent, source=p["payload"].get("source", "text"))
        return
    _clear_pending(user_id)
    await telegram.send(chat_id, "Cancelled (unknown pending kind).")


async def _handle_photo(msg: dict, *, chat_id: int, user_id: int) -> None:
    photos = msg.get("photo") or []
    if not photos:
        return
    largest = max(photos, key=lambda p: (p.get("width", 0) * p.get("height", 0)))
    file_id = largest.get("file_id")
    if not file_id:
        return
    await telegram.send(chat_id, "📷 Reading the receipt…")
    raw = await telegram.download_file(file_id)
    if not raw:
        await telegram.send(chat_id, "Couldn't download the image.")
        return
    intent = await vision.parse_receipt(raw)
    if not intent or intent.amount == 0 or intent.confidence < 0.3:
        await telegram.send(chat_id, "Couldn't read a transaction off that. Try a clearer photo or just type it.")
        return
    await _present_intent(chat_id, user_id, intent, source="photo")


async def _handle_voice(msg: dict, *, chat_id: int, user_id: int) -> None:
    file_id = (msg.get("voice") or msg.get("audio") or {}).get("file_id")
    if not file_id:
        return
    await telegram.send(chat_id, "🎙️ Transcribing…")
    raw = await telegram.download_file(file_id)
    if not raw:
        await telegram.send(chat_id, "Couldn't download the voice note.")
        return
    text = await voice.transcribe(raw)
    if not text:
        await telegram.send(chat_id, "Whisper didn't return anything. Try typing it.")
        return
    await telegram.send(chat_id, f"<i>heard:</i> {telegram.esc(text)}")
    intent = await nlparse.parse_intent(text)
    if not intent or intent.amount == 0 or intent.confidence < 0.3:
        await telegram.send(chat_id, "I heard you, but couldn't extract a transaction.")
        return
    await _present_intent(chat_id, user_id, intent, source="voice")


async def _handle_document(msg: dict, *, chat_id: int, user_id: int) -> None:
    doc = msg.get("document") or {}
    file_id = doc.get("file_id")
    name = doc.get("file_name") or "upload.csv"
    if not file_id:
        return
    if not name.lower().endswith(".csv"):
        await telegram.send(chat_id, "I only handle CSV right now (PDF coming in Phase 2).")
        return
    await telegram.send(chat_id, f"📥 Importing <code>{telegram.esc(name)}</code>…")
    raw = await telegram.download_file(file_id)
    if not raw:
        await telegram.send(chat_id, "Couldn't download the file.")
        return
    account_slug = name.split(".")[0].lower()
    result = await h_import.import_csv_bytes(name, raw, account_slug)
    await telegram.send(chat_id, h_import.render_import_summary(result))


async def _handle_callback(cb: dict) -> None:
    cb_id = cb.get("id")
    user_id = (cb.get("from") or {}).get("id")
    chat_id = ((cb.get("message") or {}).get("chat") or {}).get("id")
    data = cb.get("data") or ""
    if not _is_owner(int(user_id or 0)):
        await telegram.answer_callback(cb_id, "Not authorized.", alert=True)
        return
    if not data.startswith("i:"):
        await telegram.answer_callback(cb_id, "Unknown action.")
        return
    _, _token, action = data.split(":", 2)
    if action == "yes":
        await telegram.answer_callback(cb_id, "✅ Logging…")
        await _confirm_pending(int(user_id), int(chat_id))
    else:
        _clear_pending(int(user_id))
        await telegram.answer_callback(cb_id, "❌ Cancelled")
        await telegram.send(int(chat_id), "Cancelled.")


# ─── update dispatch ─────────────────────────────────────────────────────────
async def _handle_update(u: dict) -> None:
    cb = u.get("callback_query")
    if cb:
        try:
            await _handle_callback(cb)
        except Exception as e:
            log.exception("callback failed: %s", e)
        return

    msg = u.get("message")
    if not msg:
        return
    user_id = int((msg.get("from") or {}).get("id") or 0)
    chat_id = int((msg.get("chat") or {}).get("id") or 0)
    if not _is_owner(user_id):
        log.info("ignoring non-owner user %s", user_id)
        return

    if msg.get("photo"):
        await _handle_photo(msg, chat_id=chat_id, user_id=user_id)
        return
    if msg.get("voice") or msg.get("audio"):
        await _handle_voice(msg, chat_id=chat_id, user_id=user_id)
        return
    if msg.get("document"):
        await _handle_document(msg, chat_id=chat_id, user_id=user_id)
        return

    text = (msg.get("text") or "").strip()
    if not text:
        return
    try:
        if text.startswith("/"):
            await _handle_command(text, chat_id=chat_id, user_id=user_id)
        else:
            await _handle_text(text, chat_id=chat_id, user_id=user_id)
    except Exception as e:
        log.exception("handler failed: %s", e)
        await telegram.send(chat_id, f"⚠️ error: {telegram.esc(str(e)[:300])}")


# ─── main loop ────────────────────────────────────────────────────────────────
async def _poll(client: httpx.AsyncClient, offset: int) -> list[dict]:
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getUpdates"
    try:
        r = await client.get(url, params={
            "offset": offset,
            "timeout": 25,
            "allowed_updates": json.dumps(["message", "callback_query"]),
        }, timeout=35)
    except httpx.TimeoutException:
        return []
    except Exception as e:
        log.warning("getUpdates error: %s", e)
        await asyncio.sleep(2)
        return []
    if r.status_code != 200:
        log.warning("getUpdates %s: %s", r.status_code, r.text[:200])
        await asyncio.sleep(5)
        return []
    return r.json().get("result", []) or []


async def run_forever() -> None:
    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN not set")
    if not settings.owner_tg_id:
        log.warning("OWNER_TG_ID not set — bot will accept NO messages until configured.")
    log.info("streasury-bot starting; owner=%s", settings.owner_tg_id)
    offset = _load_offset()
    async with httpx.AsyncClient() as client:
        while True:
            updates = await _poll(client, offset)
            for u in updates:
                uid = int(u.get("update_id") or 0)
                if uid >= offset:
                    offset = uid + 1
                try:
                    await _handle_update(u)
                except Exception as e:
                    log.exception("update failed: %s", e)
            if updates:
                _save_offset(offset)

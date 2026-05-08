"""fp-game-bot — @fullpotentialgamebot Telegram bot.

The Game's player-facing bot. Handles:
  /start    — welcome + orientation
  /help     — list commands
  /sign     — multi-turn flow to sign the World Peace Agreement
  /card     — submit / update Character Card markdown
  /proof    — multi-turn flow to file a Proof Loop
  /stats    — your Player State (Champion #, loops, affiliates, score, stage)
  /field    — aggregate Field State (counts across the whole game)
  /invite   — your unique invite URL
  /whoami   — show your saved name + chat info
  /cancel   — cancel any in-progress flow

All state lives in /var/lib/full-potential/* on the substrate via the
champion-sign API at https://fullpotential.com/api/champion/*. The bot is
just a thin Telegram-facing surface on top of that substrate.

Per The Game Plays Itself + The Practice of Signaling.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import httpx

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("fp-game-bot")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    log.error("TELEGRAM_BOT_TOKEN not set — exiting")
    sys.exit(1)

API_BASE = os.environ.get("CHAMPION_API_URL", "https://fullpotential.com/api/champion").rstrip("/")
GAME_URL = os.environ.get("GAME_URL", "https://fullpotential.com/game")
OFFSET_FILE = Path(os.environ.get("OFFSET_FILE", "/var/lib/fp-game-bot/offset"))
OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)

# In-memory per-chat conversation state {chat_id: {flow, step, data}}
STATE: dict[int, dict] = {}

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


# ─── Telegram helpers ──────────────────────────────────────────────────────

async def tg_send(client: httpx.AsyncClient, chat_id: int, text: str,
                   parse_mode: str = "HTML",
                   reply_markup: Optional[dict] = None) -> None:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False,
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        await client.post(f"{TG_API}/sendMessage", json=payload, timeout=10)
    except Exception as e:
        log.warning("send failed: %s", e)


def esc(s) -> str:
    if s is None:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _load_offset() -> int:
    try:
        return int(OFFSET_FILE.read_text().strip()) if OFFSET_FILE.exists() else 0
    except Exception:
        return 0


def _save_offset(offset: int) -> None:
    try:
        OFFSET_FILE.write_text(str(offset))
    except Exception as e:
        log.warning("offset save failed: %s", e)


# ─── Substrate API calls ───────────────────────────────────────────────────

async def api_post(client: httpx.AsyncClient, path: str, payload: dict) -> dict:
    r = await client.post(f"{API_BASE}{path}", json=payload, timeout=15)
    if r.status_code == 200:
        return r.json()
    raise httpx.HTTPStatusError(f"{r.status_code}: {r.text[:200]}", request=r.request, response=r)


async def api_get(client: httpx.AsyncClient, path: str, params: dict | None = None) -> dict:
    r = await client.get(f"{API_BASE}{path}", params=params or {}, timeout=10)
    if r.status_code == 200:
        return r.json()
    raise httpx.HTTPStatusError(f"{r.status_code}: {r.text[:200]}", request=r.request, response=r)


# ─── Command handlers ──────────────────────────────────────────────────────

WELCOME = """🎮 <b>Welcome to the Full Potential Game.</b>

Reality is already a game. This is the guide for those who know.

A proof-based operating system for human potential. Coherent Champions of CHRIST sign the World Peace Agreement, build a Character Card, run a 7-Day proof loop, and earn Field Score through witnessed reality.

<b>Commands</b>
  /sign — sign the World Peace Agreement
  /card — submit your Character Card
  /proof — file a 7-Day Proof Loop
  /stats — your Player State
  /field — live game-state metrics
  /invite — your unique invite link
  /whoami — what name you're registered as
  /help — show this menu

Ready? Type <code>/sign</code> to start, or <code>/field</code> to see what's happening in the game right now.

<i>Web: <a href="https://fullpotential.com/game">fullpotential.com/game</a></i>
"""

HELP_TEXT = WELCOME


async def cmd_start(client, chat_id: int, args: str) -> None:
    STATE.pop(chat_id, None)  # clear any in-progress flow
    await tg_send(client, chat_id, WELCOME)


async def cmd_help(client, chat_id: int, args: str) -> None:
    await tg_send(client, chat_id, HELP_TEXT)


async def cmd_cancel(client, chat_id: int, args: str) -> None:
    state = STATE.pop(chat_id, None)
    if state:
        await tg_send(client, chat_id, "↩️ Cancelled. Type /help to see commands.")
    else:
        await tg_send(client, chat_id, "Nothing to cancel. Type /help to see commands.")


async def cmd_field(client, chat_id: int, args: str) -> None:
    try:
        d = await api_get(client, "/stats")
    except Exception as e:
        await tg_send(client, chat_id, f"⚠️ Couldn't reach the substrate: {esc(e)}")
        return
    msg = (
        "⚡ <b>FIELD STATE</b>\n\n"
        f"🌀 <b>{d.get('champions', {}).get('total', 0)}</b> Champions signed\n"
        f"🎴 <b>{d.get('cards', {}).get('total', 0)}</b> Character Cards built\n"
        f"🌱 <b>{d.get('proofs', {}).get('total', 0)}</b> Proofs filed\n"
        f"🤝 <b>{d.get('affiliate_links', 0)}</b> Affiliate connections\n"
        f"📊 <b>{d.get('field_score_sum', 0)}</b> Field Score sum\n"
        f"📈 <b>+{d.get('growth_this_week', {}).get('total', 0)}</b> this week\n\n"
        f"<i>Live at <a href=\"{GAME_URL}\">fullpotential.com/game</a></i>"
    )
    await tg_send(client, chat_id, msg)


async def cmd_stats(client, chat_id: int, args: str, name_override: Optional[str] = None) -> None:
    name = name_override or _saved_name(chat_id) or args.strip()
    if not name:
        await tg_send(client, chat_id,
            "I don't know your name yet. Reply with: <code>/whoami YourName</code> "
            "or <code>/sign</code> to sign first.")
        return
    try:
        d = await api_get(client, "/lookup", {"name": name})
    except Exception as e:
        await tg_send(client, chat_id, f"⚠️ Lookup failed: {esc(e)}")
        return
    if not d.get("champion"):
        await tg_send(client, chat_id,
            f"No Champion found for <b>{esc(name)}</b>. Type /sign to become one — "
            f"or check the spelling.")
        return
    c = d["champion"]
    stage, glyph = _compute_stage(d)
    next_action = _next_action(d)
    msg = (
        f"🎮 <b>{esc(c.get('name'))}</b>\n"
        f"{glyph} <b>{stage}</b>\n\n"
        f"Champion #<b>{esc(c.get('champion_number'))}</b> · signed {esc(c.get('date_signed'))}\n"
        f"🎴 Card: <b>{('present (' + esc(d.get('card_level') or '?') + ')') if d.get('card_present') else 'not yet built'}</b>\n"
        f"🌱 Proofs filed: <b>{d.get('proofs_filed', 0)}</b>\n"
        f"🤝 Affiliates signed: <b>{d.get('affiliates_count', 0)}</b>\n"
        f"📊 Field Score: <b>{d.get('field_score_simple', 0)}</b>\n\n"
        f"<i>→ {next_action}</i>"
    )
    await tg_send(client, chat_id, msg)


def _compute_stage(d: dict) -> tuple[str, str]:
    has_champ = bool(d.get("champion"))
    has_card = bool(d.get("card_present"))
    proofs = d.get("proofs_filed", 0)
    aff = d.get("affiliates_count", 0)
    if not has_champ:
        return ("Visitor", "👋")
    if not has_card:
        return ("Guest", "👥")
    if proofs == 0:
        return ("Player", "🎮")
    if proofs < 3:
        return ("Apprentice", "🎓")
    if aff < 3:
        return ("Steward", "🌱")
    if proofs < 10 or aff < 10:
        return ("Builder", "🏗")
    return ("Legend", "👑")


def _next_action(d: dict) -> str:
    if not d.get("champion"):
        return "Type /sign to become a Coherent Champion."
    if not d.get("card_present"):
        return "Type /card to build your Character Card (next stage: Player)."
    if d.get("proofs_filed", 0) == 0:
        return "Type /proof to file your first 7-Day Game (next: Apprentice)."
    if d.get("affiliates_count", 0) == 0:
        return "Type /invite to get your invite link — bring others into the field."
    return "You're moving. File the next proof, witness another player, ascend the path."


async def cmd_invite(client, chat_id: int, args: str) -> None:
    name = _saved_name(chat_id)
    if not name:
        await tg_send(client, chat_id,
            "I don't know your name yet. Type /sign first, or "
            "<code>/whoami YourName</code> to register.")
        return
    from urllib.parse import quote
    url = f"{GAME_URL}?inviter={quote(name)}"
    msg = (
        f"🤝 <b>Your invite link</b>\n\n"
        f"<code>{esc(url)}</code>\n\n"
        f"Share with anyone aligned. When they sign through this URL, they're "
        f"credited as your affiliate and your Field Score grows by <b>+3</b>.\n\n"
        f"<i>Don't recruit — invite. Resonance, not pressure.</i>"
    )
    await tg_send(client, chat_id, msg)


async def cmd_whoami(client, chat_id: int, args: str) -> None:
    if args.strip():
        # Set name
        _save_name(chat_id, args.strip())
        await tg_send(client, chat_id,
            f"✓ Saved as <b>{esc(args.strip())}</b>. Type /stats to see your Player State.")
        return
    name = _saved_name(chat_id)
    if name:
        await tg_send(client, chat_id,
            f"You're registered as <b>{esc(name)}</b> in this chat (#{chat_id}).\n\n"
            f"To change: <code>/whoami New Name</code>")
    else:
        await tg_send(client, chat_id,
            f"No name set yet for this chat (#{chat_id}). "
            f"Type <code>/whoami YourName</code> or /sign to register.")


# ─── /sign multi-turn flow ─────────────────────────────────────────────────

async def cmd_sign(client, chat_id: int, args: str) -> None:
    STATE[chat_id] = {"flow": "sign", "step": "name", "data": {}}
    await tg_send(client, chat_id,
        "📜 <b>Sign the World Peace Agreement</b>\n\n"
        "<i>I agree to practice peace in thought, word, and action.\n"
        "I agree to reduce unnecessary suffering.\n"
        "I agree to seek understanding before hatred.\n"
        "I agree to repair where I have caused harm.\n"
        "I agree to protect life, truth, beauty, and future generations.\n"
        "I agree to become trustworthy with intelligence, influence, and resources.\n"
        "I agree that peace must become visible through action.\n\n"
        "Signed not in perfection, but in sincere participation.</i>\n\n"
        "Reply with <b>your name</b> (the name you'll be known by on the Champions Roll). "
        "Type /cancel to back out anytime.")


async def handle_sign_step(client, chat_id: int, text: str) -> None:
    state = STATE[chat_id]
    step = state["step"]
    data = state["data"]

    if step == "name":
        if len(text) < 2 or len(text) > 100:
            await tg_send(client, chat_id, "Names should be 2-100 characters. Try again, or /cancel.")
            return
        data["name"] = text
        state["step"] = "public"
        await tg_send(client, chat_id,
            f"✓ Name: <b>{esc(text)}</b>\n\n"
            f"Should your signature be <b>public</b> (visible on the Champions Roll) "
            f"or <b>private</b>? Reply <code>public</code> or <code>private</code>.")
        return

    if step == "public":
        choice = text.strip().lower()
        if choice not in ("public", "private", "p", "pub", "priv"):
            await tg_send(client, chat_id, "Reply <code>public</code> or <code>private</code>.")
            return
        data["public"] = choice in ("public", "p", "pub")
        state["step"] = "why"
        await tg_send(client, chat_id,
            "Optional: <b>one sentence — why are you signing?</b>\n"
            "Reply with your reason, or type <code>skip</code>.")
        return

    if step == "why":
        if text.strip().lower() not in ("skip", "-", "none"):
            data["why"] = text[:1000]
        # Submit
        try:
            payload = {"name": data["name"], "public": data["public"]}
            if data.get("why"):
                payload["why"] = data["why"]
            r = await api_post(client, "/sign", payload)
            num = r.get("champion_number", "?")
            _save_name(chat_id, data["name"])
            STATE.pop(chat_id, None)
            await tg_send(client, chat_id,
                f"✨ <b>Signed.</b>\n\n"
                f"Welcome, <b>{esc(data['name'].split()[0])}</b>. You are <b>Coherent Champion #{num}</b>.\n\n"
                f"<i>Your file is on the substrate. The Roll grows by one.</i>\n\n"
                f"<b>Next moves:</b>\n"
                f"• Type /card to build your Character Card (5 min, AI-assisted)\n"
                f"• Type /invite to get your unique invite URL\n"
                f"• Type /stats to see your Player State")
        except Exception as e:
            STATE.pop(chat_id, None)
            await tg_send(client, chat_id, f"⚠️ Signing failed: {esc(e)}\nTry /sign again.")
        return


# ─── /card simple flow (paste markdown) ────────────────────────────────────

async def cmd_card(client, chat_id: int, args: str) -> None:
    name = _saved_name(chat_id)
    if not name:
        await tg_send(client, chat_id,
            "Sign first with /sign, or set your name with <code>/whoami YourName</code>.")
        return
    STATE[chat_id] = {"flow": "card", "step": "level", "data": {"player": name}}
    await tg_send(client, chat_id,
        "🎴 <b>Character Card</b>\n\n"
        "Easiest way: paste the AI Port-In prompt from the Game page into Claude/GPT, "
        "let it draft your card, then paste the result here.\n\n"
        "Get the prompt: <a href=\"" + GAME_URL + "#characterCardQuest\">fullpotential.com/game</a>\n\n"
        "First — what level? Reply with one:\n"
        "  <code>L1</code> Signup (5 min · live + discoverable)\n"
        "  <code>L2</code> Player (15 min · matchable)\n"
        "  <code>L3</code> Matching (30 min · team-formable)\n"
        "  <code>L4</code> Living (ongoing)")


async def handle_card_step(client, chat_id: int, text: str) -> None:
    state = STATE[chat_id]
    step = state["step"]
    data = state["data"]

    if step == "level":
        lvl = text.strip().upper()
        if lvl not in ("L1", "L2", "L3", "L4"):
            await tg_send(client, chat_id, "Reply <code>L1</code>, <code>L2</code>, <code>L3</code>, or <code>L4</code>.")
            return
        data["level"] = lvl
        state["step"] = "visibility"
        await tg_send(client, chat_id,
            "Visibility default? Reply with one:\n"
            "  <code>public</code> — syndicates to social media\n"
            "  <code>player</code> — visible to other Game players (recommended default)\n"
            "  <code>inner</code> — Witness Roster only\n"
            "  <code>sacred</code> — only you + your AI")
        return

    if step == "visibility":
        v = text.strip().lower()
        if v not in ("public", "player", "inner", "sacred"):
            await tg_send(client, chat_id,
                "Reply <code>public</code>, <code>player</code>, <code>inner</code>, or <code>sacred</code>.")
            return
        data["visibility_default"] = v
        state["step"] = "markdown"
        await tg_send(client, chat_id,
            "Now paste your <b>Character Card markdown</b> (the full output from your AI). "
            "It can be long — Telegram handles it. Just paste and send.\n\n"
            "Or type /cancel.")
        return

    if step == "markdown":
        if len(text) < 30:
            await tg_send(client, chat_id,
                "That looks short for a card. Paste the full markdown your AI drafted, or /cancel.")
            return
        data["card_markdown"] = text[:20000]
        try:
            r = await api_post(client, "/card/submit", data)
            STATE.pop(chat_id, None)
            await tg_send(client, chat_id,
                f"✨ <b>Card saved.</b>\n\n"
                f"{esc(r.get('message', ''))}\n\n"
                f"<i>You can update it anytime — type /card again with the same name.</i>\n\n"
                f"Next: type /proof to file your first 7-Day Game.")
        except Exception as e:
            STATE.pop(chat_id, None)
            await tg_send(client, chat_id, f"⚠️ Submit failed: {esc(e)}")
        return


# ─── /proof multi-turn flow ────────────────────────────────────────────────

async def cmd_proof(client, chat_id: int, args: str) -> None:
    name = _saved_name(chat_id)
    if not name:
        await tg_send(client, chat_id,
            "Sign first with /sign so I know who you are.")
        return
    STATE[chat_id] = {"flow": "proof", "step": "loop", "data": {"player": name}}
    await tg_send(client, chat_id,
        "🌱 <b>File a Proof Loop</b>\n\n"
        "What loop number is this? Reply with a number (e.g. <code>1</code> for your first proof).")


async def handle_proof_step(client, chat_id: int, text: str) -> None:
    state = STATE[chat_id]
    step = state["step"]
    data = state["data"]

    if step == "loop":
        try:
            n = int(text.strip())
            if n < 1 or n > 9999:
                raise ValueError()
        except Exception:
            await tg_send(client, chat_id, "Reply with a positive number, e.g. <code>1</code>.")
            return
        data["loop_number"] = n
        state["step"] = "quest"
        await tg_send(client, chat_id,
            "What was the <b>Quest</b>? One sentence — the transformation you set out to deliver.")
        return

    if step == "quest":
        if len(text) < 5:
            await tg_send(client, chat_id, "Need a real sentence. Try again or /cancel.")
            return
        data["quest"] = text[:400]
        state["step"] = "output"
        await tg_send(client, chat_id,
            "What was the <b>Output</b>? What was actually completed / shipped / delivered.")
        return

    if step == "output":
        if len(text) < 5:
            await tg_send(client, chat_id, "Need a real description. Try again or /cancel.")
            return
        data["output"] = text[:2000]
        state["step"] = "result"
        await tg_send(client, chat_id,
            "What was the <b>Result</b>? What changed (optional). Type <code>skip</code> if not now.")
        return

    if step == "result":
        if text.strip().lower() not in ("skip", "-", "none"):
            data["result"] = text[:2000]
        state["step"] = "witness"
        await tg_send(client, chat_id,
            "Who <b>witnessed</b> this? Name or @ (optional). Type <code>skip</code> to file without one.")
        return

    if step == "witness":
        if text.strip().lower() not in ("skip", "-", "none"):
            data["witness"] = text[:200]
        state["step"] = "consent"
        await tg_send(client, chat_id,
            "<b>Visibility:</b> reply with one:\n"
            "  <code>public</code> — appears on Field Pulse + Public Proofs\n"
            "  <code>anonymized</code> — referenceable, name not shown\n"
            "  <code>private</code> — your ledger only")
        return

    if step == "consent":
        c = text.strip().lower()
        if c not in ("public", "anonymized", "private"):
            await tg_send(client, chat_id,
                "Reply <code>public</code>, <code>anonymized</code>, or <code>private</code>.")
            return
        data["consent"] = c
        try:
            r = await api_post(client, "/proof/submit", data)
            STATE.pop(chat_id, None)
            await tg_send(client, chat_id,
                f"🌱 <b>Proof L{data['loop_number']} filed.</b>\n\n"
                f"{esc(r.get('message', ''))}\n\n"
                f"<i>It's on the substrate. The Field Pulse will show it within seconds.</i>\n\n"
                f"Type /stats to see your updated Player State.")
        except Exception as e:
            STATE.pop(chat_id, None)
            await tg_send(client, chat_id, f"⚠️ Submit failed: {esc(e)}")
        return


# ─── Per-chat name persistence ─────────────────────────────────────────────
# Stored locally; lightweight SQLite-style flat file.

NAMES_FILE = Path("/var/lib/fp-game-bot/names.json")


def _load_names() -> dict:
    if NAMES_FILE.exists():
        try:
            return json.loads(NAMES_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_names(names: dict) -> None:
    NAMES_FILE.parent.mkdir(parents=True, exist_ok=True)
    NAMES_FILE.write_text(json.dumps(names, indent=2))


def _saved_name(chat_id: int) -> Optional[str]:
    return _load_names().get(str(chat_id))


def _save_name(chat_id: int, name: str) -> None:
    names = _load_names()
    names[str(chat_id)] = name
    _save_names(names)


# ─── Update dispatch ───────────────────────────────────────────────────────

COMMAND_HANDLERS = {
    "start": cmd_start,
    "help": cmd_help,
    "cancel": cmd_cancel,
    "field": cmd_field,
    "stats": cmd_stats,
    "invite": cmd_invite,
    "whoami": cmd_whoami,
    "sign": cmd_sign,
    "card": cmd_card,
    "proof": cmd_proof,
}

FLOW_HANDLERS = {
    "sign": handle_sign_step,
    "card": handle_card_step,
    "proof": handle_proof_step,
}


async def handle_update(client: httpx.AsyncClient, update: dict) -> None:
    msg = update.get("message")
    if not msg:
        return
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    if not chat_id:
        return
    text = (msg.get("text") or "").strip()
    if not text:
        return

    # In-progress multi-turn flow takes precedence
    state = STATE.get(chat_id)
    if state and not text.startswith("/"):
        flow = state.get("flow")
        handler = FLOW_HANDLERS.get(flow)
        if handler:
            try:
                await handler(client, chat_id, text)
            except Exception as e:
                log.exception("flow handler error")
                await tg_send(client, chat_id, f"⚠️ Error: {esc(e)}\nType /cancel and try again.")
            return

    # Slash command
    if text.startswith("/"):
        parts = text[1:].split(maxsplit=1)
        cmd = parts[0].lower().split("@")[0]  # strip @bot suffix
        args = parts[1] if len(parts) > 1 else ""
        handler = COMMAND_HANDLERS.get(cmd)
        if handler:
            try:
                await handler(client, chat_id, args)
            except Exception as e:
                log.exception("command handler error")
                await tg_send(client, chat_id, f"⚠️ Error: {esc(e)}")
        else:
            await tg_send(client, chat_id, f"Unknown command: /{esc(cmd)}. Type /help to see commands.")
        return

    # Plain text outside a flow → give them a hint
    await tg_send(client, chat_id,
        "Type /help to see commands. The Game runs through commands, not free text — yet.")


# ─── Main loop ─────────────────────────────────────────────────────────────

async def main():
    log.info("fp-game-bot starting; api=%s game_url=%s", API_BASE, GAME_URL)
    offset = _load_offset()
    async with httpx.AsyncClient() as client:
        while True:
            try:
                r = await client.get(f"{TG_API}/getUpdates", params={
                    "offset": offset,
                    "timeout": 25,
                    "allowed_updates": json.dumps(["message"]),
                }, timeout=35)
                if r.status_code != 200:
                    log.warning("getUpdates %s: %s", r.status_code, r.text[:200])
                    await asyncio.sleep(5)
                    continue
                updates = r.json().get("result", []) or []
                for u in updates:
                    await handle_update(client, u)
                    offset = u.get("update_id", 0) + 1
                if updates:
                    _save_offset(offset)
            except httpx.TimeoutException:
                continue
            except Exception as e:
                log.warning("loop error: %s", e)
                await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())

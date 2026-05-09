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
import re
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
BOT_USERNAME = os.environ.get("BOT_USERNAME", "fullpotentialgamebot")
OFFSET_FILE = Path(os.environ.get("OFFSET_FILE", "/var/lib/fp-game-bot/offset"))
OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
INVITE_TEMPLATES_PATH = Path(os.environ.get("INVITE_TEMPLATES_PATH", "/var/lib/fp-game-bot/state/INVITE_TEMPLATES.md"))
INVITES_LOG_PATH = Path(os.environ.get("INVITES_LOG_PATH", "/var/lib/fp-game-bot/state/invites.jsonl"))

# Owner / Founding Steward
OWNER_TG_ID = os.environ.get("OWNER_TG_ID", "").strip()  # e.g. "8514069423"

# Anthropic API for natural-language conversation
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "").strip()

# Per-chat conversation history for NL
HISTORY: dict[int, list[dict]] = {}
HISTORY_MAX_TURNS = 8  # last 8 user/assistant pairs


def is_owner(chat_id: int) -> bool:
    return OWNER_TG_ID and str(chat_id) == OWNER_TG_ID

# In-memory per-chat conversation state {chat_id: {flow, step, data}}
STATE: dict[int, dict] = {}
# Attribution captured from /start invite_X deep-link; consumed by /sign.
ATTRIB: dict[int, dict] = {}

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
  /match — one specific helpful next move (just for you)
  /game — vital Game stats · 30-day goal status
  /field — live game-state metrics
  /signals — vital signs · Field Coherence · 30d goal · 7d activity
  /credits — wallet balance · send · history · leaderboard
  /store — marketplace · /store post to list · /store buy &lt;id&gt; to purchase
  /invite — your unique invite link
  /whoami — what name you're registered as
  /help — show this menu

Ready? Type <code>/sign</code> to start, or <code>/field</code> to see what's happening in the game right now.

<i>Web: <a href="https://fullpotential.com/game">fullpotential.com/game</a></i>
"""

HELP_TEXT = WELCOME


async def cmd_start(client, chat_id: int, args: str) -> None:
    """Welcome + orientation. If invoked via invite deep-link
    (?start=invite_n_INVITER_p_PATH_c_COHORT), attribute the inviter,
    path, and cohort so /sign carries them through."""
    STATE.pop(chat_id, None)
    payload = (args or "").strip()
    inviter_attr = None
    path_attr = None
    cohort_attr = None
    if payload.startswith("invite_"):
        rest_p = payload[len("invite_"):]
        # New marker format: n_<INVITER>_p_<PATH>_c_<COHORT> (any optional)
        if rest_p.startswith("n_") or "_p_" in rest_p or "_c_" in rest_p:
            # Extract cohort first (always at end if present)
            if "_c_" in rest_p:
                rest_p, cohort_attr = rest_p.rsplit("_c_", 1)
                cohort_attr = cohort_attr.strip().lower()
            if "_p_" in rest_p:
                rest_p, path_attr = rest_p.rsplit("_p_", 1)
                path_attr = path_attr.strip().lower()
            if rest_p.startswith("n_"):
                rest_p = rest_p[len("n_"):]
            inviter_attr = rest_p.replace("_", " ").strip()
        else:
            # Backward-compat: invite_<INVITER>[_<PATH>]
            templates = _load_invite_templates()
            known_paths = set(templates.keys()) if templates else {INVITE_DEFAULT_PATH}
            parts = rest_p.split("_")
            if len(parts) > 1 and parts[-1].lower() in known_paths and parts[-1].lower() != INVITE_DEFAULT_PATH:
                path_attr = parts[-1].lower()
                inviter_attr = " ".join(parts[:-1])
            else:
                inviter_attr = " ".join(parts)
        ATTRIB[chat_id] = {
            "inviter": inviter_attr,
            "path": path_attr or INVITE_DEFAULT_PATH,
            "cohort": cohort_attr or "",
        }

    if inviter_attr:
        bits = []
        if path_attr:
            bits.append(f"path: <i>{esc(path_attr)}</i>")
        if cohort_attr:
            bits.append(f"cohort: <i>{esc(cohort_attr)}</i>")
        ctx_line = (" · " + " · ".join(bits)) if bits else ""
        await tg_send(client, chat_id,
            f"👋 Welcome — invited by <b>{esc(inviter_attr)}</b>{ctx_line}\n\n"
            "You're a tap from being Champion #N in the Full Potential Game.\n"
            "Type /sign to take the World Peace Agreement (3 minutes).\n"
            "Your inviter gets +3 Field Score when you sign.\n\n"
            "Or browse first: /game · /field · /signals")
    else:
        await tg_send(client, chat_id, WELCOME)


async def cmd_help(client, chat_id: int, args: str) -> None:
    await tg_send(client, chat_id, HELP_TEXT)


async def cmd_cancel(client, chat_id: int, args: str) -> None:
    state = STATE.pop(chat_id, None)
    if state:
        await tg_send(client, chat_id, "↩️ Cancelled. Type /help to see commands.")
    else:
        await tg_send(client, chat_id, "Nothing to cancel. Type /help to see commands.")


async def cmd_store(client, chat_id: int, args: str) -> None:
    """Coherent Marketplace.

    Usage:
      /store              — top offers
      /store buy <id>     — purchase with credits
      /store mine         — your listings
      Posting: use /game/store on web for now (multi-step on Telegram coming).
    """
    args_t = (args or "").strip()
    name = _saved_name(chat_id)

    # Post subcommand — multi-step flow
    if args_t.lower() == "post":
        if not name:
            await tg_send(client, chat_id,
                "Sign first to list an offer: /sign\n"
                "(Or set your name with <code>/whoami YourName</code> if you signed elsewhere.)")
            return
        STATE[chat_id] = {"flow": "store", "step": "title", "data": {"owner_handle": name}}
        await tg_send(client, chat_id,
            "🛍 <b>List an offer in the Coherent Store</b>\n\n"
            "I'll walk you through 5 quick fields. Type /cancel to back out anytime.\n\n"
            "<b>1. Title</b> — what's the offer? "
            "(e.g. \"60-min Coaching Session\" or \"Hand-bound Journal\")")
        return

    # Buy subcommand
    if args_t.lower().startswith("buy "):
        if not name:
            await tg_send(client, chat_id, "Sign first to buy: /sign")
            return
        offer_id = args_t.split(None, 1)[1].strip()
        try:
            d = await api_post(client, "/store/buy", {"buyer_handle": name, "offer_id": offer_id})
        except Exception as e:
            await tg_send(client, chat_id, f"⚠️ {esc(e)}")
            return
        if d.get("ok"):
            url = d.get("url")
            url_line = f"\n🔗 <a href=\"{esc(url)}\">{esc(url)}</a>" if url else ""
            await tg_send(client, chat_id,
                f"✅ Bought: <b>{esc(d.get('title') or '')}</b> for <b>{d.get('price_credits', 0)}</b> credits.\n"
                f"Balance: <b>{d.get('buyer_balance', 0)}</b>{url_line}")
        else:
            await tg_send(client, chat_id, f"⚠️ {esc(d.get('detail') or 'failed')}")
        return

    # List
    try:
        d = await api_get(client, "/store/list", {"limit": 12})
    except Exception as e:
        await tg_send(client, chat_id, f"⚠️ {esc(e)}")
        return

    offers = d.get("offers", [])
    if args_t.lower() == "mine":
        offers = [o for o in offers if (o.get("owner_handle") or "").lower() == (name or "").lower()]

    if not offers:
        await tg_send(client, chat_id,
            "🛍 <b>STORE</b>\n\n"
            "<i>No active offers yet.</i>\n\n"
            "Anyone can list — credit-only offers rank highest, then hybrid (by credit share), then $-only.")
        return

    lines = ["🛍 <b>COHERENT STORE</b>\n"]
    tier_labels = {0: "💎 CREDIT-ONLY", 1: "⚖️ HYBRID", 2: "💵 USD"}
    last_tier = -1
    for o in offers[:12]:
        t = o.get("tier", 3)
        if t != last_tier:
            lines.append(f"\n<b>{tier_labels.get(t, '· ·')}</b>")
            last_tier = t
        pc = o.get("price_credits")
        pu = o.get("price_usd")
        if pc and pu:
            price = f"<b>{pc}</b>c + ${pu}"
        elif pc:
            price = f"<b>{pc}</b>c"
        elif pu:
            price = f"${pu}"
        else:
            price = "free"
        sold = o.get("sold", 0)
        inv = o.get("inventory")
        avail = "" if inv is None else f" · {inv-sold}/{inv} left"
        lines.append(
            f"  • <b>{esc(o.get('title') or '?')}</b> · {price}{avail}\n"
            f"    @{esc(o.get('owner_handle') or '?')} · <code>{esc(o.get('offer_id') or '')}</code>"
        )
    lines.append("\n<i>Buy with credits: <code>/store buy &lt;id&gt;</code></i>")
    await tg_send(client, chat_id, "\n".join(lines))


async def cmd_credits(client, chat_id: int, args: str) -> None:
    """Coherent Credit wallet — balance, send, history.

    Usage:
      /credits             — show your balance + last 5 txns
      /credits send 10 to @bob thanks for the witness
      /credits history     — last 20 txns
      /credits leaderboard — top holders
    """
    name = _saved_name(chat_id)
    if not name:
        await tg_send(client, chat_id,
            "I don't know who you are yet. Type /sign first to register, "
            "or /whoami to set your name.")
        return

    args_t = (args or "").strip()
    handle = name  # use the player's name as handle

    # Subcommand: leaderboard
    if args_t.lower().startswith("leaderboard") or args_t.lower() == "lb":
        try:
            d = await api_get(client, "/credits/leaderboard", {"limit": 10})
        except Exception as e:
            await tg_send(client, chat_id, f"⚠️ {esc(e)}")
            return
        rows = d.get("holders", [])
        if not rows:
            await tg_send(client, chat_id, "💰 No credits in circulation yet.")
            return
        lines = [f"<b>{i+1}.</b> @{esc(r['handle'])} — <b>{r['balance']}</b>" for i, r in enumerate(rows)]
        msg = (
            "💰 <b>CREDIT HOLDERS</b>\n\n"
            + "\n".join(lines) +
            f"\n\n<i>{d.get('total_in_circulation', 0)} credits total in circulation</i>"
        )
        await tg_send(client, chat_id, msg)
        return

    # Subcommand: history
    if args_t.lower().startswith("history") or args_t.lower() == "h":
        try:
            d = await api_get(client, f"/credits/history/{handle}", {"limit": 20})
        except Exception as e:
            await tg_send(client, chat_id, f"⚠️ {esc(e)}")
            return
        hist = d.get("history", [])
        if not hist:
            await tg_send(client, chat_id, f"💰 No transactions yet. Balance: <b>{d.get('balance', 0)}</b>")
            return
        lines = []
        for tx in hist:
            sign = "+" if tx["direction"] == "in" else "−"
            other = esc(tx.get("other") or "?")
            memo = f" — {esc(tx['memo'])}" if tx.get("memo") else ""
            lines.append(f"  {sign}<b>{tx['amount']}</b> {tx['kind']} {('from' if tx['direction']=='in' else 'to')} @{other}{memo}")
        msg = (
            f"💰 <b>YOUR CREDIT HISTORY</b>\n"
            f"Balance: <b>{d.get('balance', 0)}</b>\n\n"
            + "\n".join(lines)
        )
        await tg_send(client, chat_id, msg)
        return

    # Subcommand: send N to @handle [memo]
    if args_t.lower().startswith("send "):
        # Parse: "send 10 to @bob thanks for the witness"
        m = re.match(r"send\s+(\d+)\s+to\s+@?(\w[\w\-\.]*)\s*(.*)$", args_t, re.IGNORECASE)
        if not m:
            await tg_send(client, chat_id,
                "Usage: <code>/credits send 10 to @handle [memo]</code>")
            return
        amount = int(m.group(1))
        to_handle = m.group(2)
        memo = m.group(3).strip()
        try:
            d = await api_post(client, "/credits/send", {
                "from_handle": handle,
                "to_handle": to_handle,
                "amount": amount,
                "memo": memo or None,
            })
        except Exception as e:
            await tg_send(client, chat_id, f"⚠️ {esc(e)}")
            return
        if d.get("ok"):
            await tg_send(client, chat_id,
                f"✅ Sent <b>{amount}</b> credits to @{esc(to_handle)}.\n"
                f"Your balance: <b>{d.get('from_balance', 0)}</b>"
                f"{(' · memo: ' + esc(memo)) if memo else ''}")
        else:
            await tg_send(client, chat_id, f"⚠️ {esc(d.get('detail') or d.get('message') or 'failed')}")
        return

    # Default: show balance + last 5
    try:
        d = await api_get(client, f"/credits/history/{handle}", {"limit": 5})
    except Exception as e:
        await tg_send(client, chat_id, f"⚠️ {esc(e)}")
        return
    bal = d.get("balance", 0)
    hist = d.get("history", [])
    msg_lines = [f"💰 <b>YOUR CREDIT WALLET</b>\n", f"Balance: <b>{bal}</b> credits\n"]
    if hist:
        msg_lines.append("<b>Recent:</b>")
        for tx in hist:
            sign = "+" if tx["direction"] == "in" else "−"
            other = esc(tx.get("other") or "?")
            msg_lines.append(f"  {sign}<b>{tx['amount']}</b> {tx['kind']} · @{other}")
    else:
        msg_lines.append("<i>No transactions yet. Earn credits through gameplay or get a top-up.</i>")
    msg_lines.append("\n<i>Send: <code>/credits send 10 to @handle memo</code></i>")
    msg_lines.append("<i>History: <code>/credits history</code> · Top: <code>/credits leaderboard</code></i>")
    await tg_send(client, chat_id, "\n".join(msg_lines))


async def cmd_signals(client, chat_id: int, args: str) -> None:
    """Vital signs of the Game — a comprehensive single-screen read."""
    try:
        d = await api_get(client, "/signals")
    except Exception as e:
        await tg_send(client, chat_id, f"⚠️ Couldn't reach the substrate: {esc(e)}")
        return

    goal = d.get("goal_30d", {})
    fc = d.get("field_coherence", {})
    fs = d.get("field_state", {})
    a7 = d.get("activity_7d", {})

    # 30-day goal line
    g_status = "✅" if goal.get("complete") else "🎯"
    goal_line = f"{g_status} <b>{goal.get('current', 0)}/{goal.get('target', 1)}</b> · {esc(goal.get('name', ''))}"

    # Field Coherence headline + components
    head = fc.get("headline")
    head_str = f"<b>{head:.2f}</b>/1.00" if head is not None else "<i>insufficient data</i>"
    comps = fc.get("components", {})
    def _comp(name: str, label: str) -> str:
        v = comps.get(name)
        if v is None:
            return f"  └ <i>{label}: not yet measurable</i>\n"
        return f"  └ {label}: <b>{v:.2f}</b>\n"
    coherence_block = (
        f"⚡ <b>FIELD COHERENCE</b> · {head_str}\n"
        f"{_comp('activity', 'Activity')}"
        f"{_comp('witness', 'Witness')}"
        f"{_comp('conversion', 'Conversion')}"
        f"{_comp('drift', 'Drift (Mirrors)')}"
    )

    # Field state
    state_block = (
        f"📊 <b>FIELD STATE</b>\n"
        f"  • {fs.get('champions', 0)} Champions · {fs.get('characters', 0)} Characters · {fs.get('proofs', 0)} Proofs\n"
        f"  • {fs.get('affiliates', 0)} Affiliates · {fs.get('mirrors', 0)} Mirrors · {fs.get('leads', 0)} Leads\n"
        f"  • Field Score sum: <b>{fs.get('field_score_sum', 0)}</b>\n"
    )

    # 7-day activity
    last_proof = a7.get("last_proof") or {}
    last_str = f"#{last_proof.get('loop_number')} — {esc(last_proof.get('player') or '?')}" if last_proof else "—"
    activity_block = (
        f"🔥 <b>LAST 7 DAYS</b>\n"
        f"  • +{a7.get('new_proofs', 0)} proofs · +{a7.get('new_champions', 0)} champs · +{a7.get('new_mirrors', 0)} mirrors\n"
        f"  • Last loop: {last_str}\n"
    )

    msg = (
        f"🩺 <b>GAME VITAL SIGNS</b>\n\n"
        f"{goal_line}\n\n"
        f"{coherence_block}\n"
        f"{state_block}\n"
        f"{activity_block}\n"
        f"<i><a href=\"{GAME_URL}\">fullpotential.com/game</a> · /field for collective · /whoami for personal</i>"
    )
    await tg_send(client, chat_id, msg)


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


async def cmd_match(client, chat_id: int, args: str) -> None:
    """One specific helpful next move for the named Champion (defaults to saved name)."""
    name = (args or "").strip() or _saved_name(chat_id)
    try:
        params = {"name": name} if name else {}
        d = await api_get(client, "/match", params)
    except Exception as e:
        await tg_send(client, chat_id, f"⚠️ Match failed: {esc(e)}")
        return
    if not d.get("ok"):
        await tg_send(client, chat_id,
            f"Could not match: <i>{esc(d.get('error') or 'unknown error')}</i>")
        return
    icon = d.get("icon", "🎯")
    move = d.get("move", "Keep playing.")
    action = d.get("action", "")
    url = d.get("url", "")
    label = f"<b>Match for {esc(name)}</b>" if name else "<b>Match (anonymous)</b>"
    parts = [f"{icon} {label}", "", esc(move)]
    if url:
        parts.append(f"\n<a href=\"{esc(url)}\">→ Take this move</a>")
    if action:
        parts.append(f"<i>action: {esc(action)}</i>")
    await tg_send(client, chat_id, "\n".join(parts))


async def cmd_game(client, chat_id: int, args: str) -> None:
    """Vital Game stats for the architect — composed from existing endpoints."""
    async def _fetch(path: str, params: dict | None = None) -> dict | None:
        try:
            return await api_get(client, path, params or {})
        except Exception as e:
            log.warning("/game fetch %s failed: %s", path, e)
            return None

    stats, retreats, proofs = await asyncio.gather(
        _fetch("/stats"),
        _fetch("/retreat/stats"),
        _fetch("/proof/list"),
    )

    if not stats:
        await tg_send(client, chat_id,
            f"🎮 <b>Game Stats</b>\n\n<i>Could not reach {esc(API_BASE)}.</i>")
        return

    champs_total = (stats.get("champions") or {}).get("total", 0)
    champs_public = (stats.get("champions") or {}).get("public", 0)
    cards_total = (stats.get("cards") or {}).get("total", 0)
    proofs_total = (stats.get("proofs") or {}).get("total", 0)
    proofs_public = (stats.get("proofs") or {}).get("public", 0)
    affiliate_links = stats.get("affiliate_links", 0)
    field_score = stats.get("field_score_sum", 0)
    growth = stats.get("growth_this_week") or {}
    growth_total = growth.get("total", 0) or sum(int(growth.get(k, 0) or 0) for k in ("signatures", "proofs", "cards"))
    retreat_total = (retreats or {}).get("total", 0) if retreats else 0
    retreat_public = (retreats or {}).get("public", 0) if retreats else 0
    # Sort proofs numerically by loop_number desc (the API list is alphanumeric on filenames,
    # which puts loop-9 before loop-23 — wrong for our purpose).
    all_proofs = (proofs or {}).get("proofs", []) if proofs else []
    def _loop_n(p):
        try:
            return int(str(p.get("loop_number", 0)).split(".")[0])
        except Exception:
            return 0
    latest_loops = sorted(all_proofs, key=_loop_n, reverse=True)[:3]

    goal_hit = champs_total >= 2
    goal_line = (
        "✓ Goal hit — Game is no longer N=1." if goal_hit
        else f"✗ Champions: {champs_total} (need ≥2 for first non-James human)"
    )

    lines = [
        "🎮 <b>Game · Vital Stats</b>",
        f"\n🎯 <b>30-day goal:</b> {goal_line}",
        "",
        f"🌀 Champions: <b>{champs_total}</b> ({champs_public} public)",
        f"🎴 Characters built: <b>{cards_total}</b>",
        f"🌱 Proofs filed: <b>{proofs_total}</b> ({proofs_public} public)",
        f"🤝 Affiliate links generated: <b>{affiliate_links}</b>",
        f"📊 Field Score sum: <b>{field_score}</b>",
        f"🌴 Retreat interest: <b>{retreat_total}</b> ({retreat_public} public)",
        f"📈 Growth this week: <b>+{growth_total}</b>",
    ]
    if latest_loops:
        lines.append("\n<b>Latest loops</b>")
        for L in latest_loops:
            n = L.get("loop_number") or "?"
            player = esc(L.get("player") or "?")
            agreement = esc(L.get("agreement_type") or "")
            date = esc(L.get("date_committed") or "")
            tag = f" · <i>{agreement}</i>" if agreement else ""
            lines.append(f"  L{n} · {player}{tag} · {date}")
    lines.append(f"\n<i>Source: {esc(API_BASE)} · Web: <a href=\"{GAME_URL}\">fullpotential.com/game</a></i>")
    await tg_send(client, chat_id, "\n".join(lines))


# ───────────────────────── invite substrate ─────────────────────────────
_RE_INVITE_EMAIL = re.compile(r"^[\w.+\-]+@[\w\-]+\.[\w.\-]+$")
_RE_INVITE_TG = re.compile(r"^@[A-Za-z0-9_]{3,}$")
_RE_INVITE_PHONE = re.compile(r"^\+?[\d][\d\s().\-]{6,}$")
INVITE_DEFAULT_PATH = "game"


def _load_invite_templates() -> dict:
    """Parse INVITE_TEMPLATES.md → {path_slug: body}.

    Each `## slug` heading starts a template; body runs until next `## ` or
    `---` divider. Returns empty dict if file missing.
    """
    try:
        md = INVITE_TEMPLATES_PATH.read_text(encoding="utf-8")
    except Exception:
        return {}
    templates: dict = {}
    current_slug = None
    current_body: list = []
    for line in md.splitlines():
        m = re.match(r"^##\s+([A-Za-z][A-Za-z0-9\-_]*)\s*$", line)
        if m:
            if current_slug and current_body:
                templates[current_slug] = "\n".join(current_body).strip()
            current_slug = m.group(1).lower()
            current_body = []
            continue
        if line.strip() == "---" and current_slug:
            templates[current_slug] = "\n".join(current_body).strip()
            current_slug = None
            current_body = []
            continue
        if current_slug:
            current_body.append(line)
    if current_slug and current_body:
        templates[current_slug] = "\n".join(current_body).strip()
    return templates


def _parse_invite_args(rest: str, available: set) -> dict:
    tokens = [t for t in (rest or "").strip().split() if t]
    out = {"name": "", "contact": "", "channel": "", "path": "", "cohort": "", "why_them": ""}
    name_parts: list = []
    why_parts: list = []
    contact_seen = path_seen = False
    for tok in tokens:
        # Explicit `cohort=zen-village` (or `c=zen-village`) syntax
        low = tok.lower()
        if low.startswith("cohort=") or low.startswith("c="):
            out["cohort"] = tok.split("=", 1)[1].strip().lower()
            continue
        if not contact_seen and _RE_INVITE_EMAIL.match(tok):
            out["contact"] = tok
            out["channel"] = "email"
            contact_seen = True
            continue
        if not contact_seen and _RE_INVITE_TG.match(tok):
            out["contact"] = tok
            out["channel"] = "telegram"
            contact_seen = True
            continue
        if not contact_seen and _RE_INVITE_PHONE.match(tok):
            out["contact"] = tok
            out["channel"] = "whatsapp"
            contact_seen = True
            continue
        if not path_seen and tok.lower() in available:
            out["path"] = tok.lower()
            path_seen = True
            continue
        if not contact_seen and not path_seen:
            name_parts.append(tok)
        else:
            why_parts.append(tok)
    out["name"] = " ".join(name_parts).strip()
    out["why_them"] = " ".join(why_parts).strip()
    if not out["path"]:
        out["path"] = INVITE_DEFAULT_PATH
    return out


def _render_invite(body: str, name: str, why_them: str, link: str) -> str:
    first = name.split()[0] if name else "there"
    out = body.replace("{NAME}", first)
    if why_them:
        out = out.replace("{WHY_THEM}", why_them)
    else:
        out = re.sub(r"\n*\{WHY_THEM\}\n*", "\n", out)
    out = out.replace("{TRACKED_LINK}", link)
    return out.strip()


def _build_invite_link(inviter: str, path: str, cohort: str = "") -> str:
    """Tracked Telegram deep-link to @fullpotentialgamebot.

    Payload format (markers, all optional after invite_):
        invite_n_<INVITER>_p_<PATH>_c_<COHORT>
    Path/cohort omitted when default/empty. Backward-compat: also parses the
    older `invite_<INVITER>` and `invite_<INVITER>_<PATH>` forms.
    """
    from urllib.parse import quote
    inviter_slug = inviter.replace(" ", "_")
    parts = [f"invite_n_{inviter_slug}"]
    if path and path != INVITE_DEFAULT_PATH:
        parts.append(f"p_{path}")
    if cohort:
        parts.append(f"c_{cohort}")
    payload = "_".join(parts)
    return f"https://t.me/{BOT_USERNAME}?start={quote(payload)}"


def _build_invite_deep_links(channel: str, contact: str, rendered: str) -> list:
    from urllib.parse import quote
    out: list = []
    if channel == "email":
        subject = "Invitation to Full Potential"
        out.append(("📧 Open in Mail",
                    f"mailto:{contact}?subject={quote(subject)}&body={quote(rendered)}"))
    elif channel == "whatsapp":
        digits = "".join(c for c in contact if c.isdigit() or c == "+")
        wa_phone = digits.lstrip("+")
        out.append(("💬 Open in WhatsApp",
                    f"https://wa.me/{wa_phone}?text={quote(rendered)}"))
        out.append(("📱 SMS fallback",
                    f"sms:{digits}&body={quote(rendered)}"))
    elif channel == "telegram":
        out.append(("✈️ Open chat",
                    f"https://t.me/{contact.lstrip('@')}"))
    return out


def _log_invite(inviter: str, name: str, contact: str, channel: str,
                path: str, link: str, why_them: str = "", cohort: str = "") -> None:
    from datetime import datetime as _dt
    row = {
        "ts": _dt.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inviter": inviter,
        "name": name,
        "contact": contact,
        "channel": channel or "copy-paste",
        "path": path,
        "cohort": cohort,
        "link": link,
        "why_them": why_them,
        "status": "sent",
    }
    try:
        INVITES_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with INVITES_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as e:
        log.warning("invite log write failed: %s", e)


async def cmd_invite(client, chat_id: int, args: str) -> None:
    """Polymorphic /invite — detects email / phone / @handle / name in any
    order. Renders path-specific template + tracked Telegram deep-link
    (so invitees can sign inside Telegram, no browser context-switch)."""
    inviter = _saved_name(chat_id)
    if not inviter:
        await tg_send(client, chat_id,
            "I don't know your name yet. Type /sign first, or "
            "<code>/whoami YourName</code> to register.")
        return

    templates = _load_invite_templates()
    if not templates:
        await tg_send(client, chat_id,
            f"📨 Invitation templates not loaded from <code>{esc(str(INVITE_TEMPLATES_PATH))}</code>.\n"
            "Run sync_invite_templates_to_primary.sh from the cockpit.")
        return

    parsed = _parse_invite_args(args, set(templates.keys()))
    if not parsed["name"]:
        path_list = ", ".join(sorted(templates.keys()))
        await tg_send(client, chat_id,
            "📨 <b>/invite</b> — render a personalized invitation\n\n"
            "<b>Usage:</b>\n"
            "<code>/invite NAME [email|phone|@handle] [path] [why-them...]</code>\n\n"
            "Pass whatever you have; order doesn't matter. Examples:\n"
            "<code>/invite Mark</code> — copy-paste only\n"
            "<code>/invite Mark mark@x.com</code> — opens Mail\n"
            "<code>/invite Mark +15551234567 retreat</code> — opens WhatsApp\n"
            "<code>/invite Mark @markhandle apprenticeship</code> — TG forward\n\n"
            f"<b>Paths:</b> {esc(path_list)} (default: <b>game</b>)\n\n"
            "<i>Tracked links use t.me/fullpotentialgamebot — invitees can /sign right here in Telegram.</i>")
        return
    if parsed["path"] not in templates:
        await tg_send(client, chat_id,
            f"📨 Unknown path: <code>{esc(parsed['path'])}</code>\n"
            f"Available: {esc(', '.join(sorted(templates.keys())))}")
        return

    body = templates[parsed["path"]]
    link = _build_invite_link(inviter, parsed["path"], parsed.get("cohort", ""))
    rendered = _render_invite(body, parsed["name"], parsed["why_them"], link)
    _log_invite(inviter, parsed["name"], parsed["contact"], parsed["channel"],
                parsed["path"], link, parsed["why_them"], parsed.get("cohort", ""))

    deep_links = _build_invite_deep_links(parsed["channel"], parsed["contact"], rendered)

    cohort_part = f" · cohort: <i>{esc(parsed['cohort'])}</i>" if parsed.get("cohort") else ""
    out = [f"📨 <b>Invitation drafted</b> — <i>{esc(parsed['path'])}</i> · {esc(parsed['name'])}{cohort_part}"]
    if parsed["channel"]:
        out.append(f"<i>Channel: {esc(parsed['channel'])} → {esc(parsed['contact'])}</i>")
    else:
        out.append("<i>Copy-paste only — no channel detected</i>")
    out.append("")
    out.append("<pre>" + esc(rendered) + "</pre>")
    if deep_links:
        out.append("")
        for label, url in deep_links:
            out.append(f'<a href="{esc(url)}">{esc(label)}</a>')
    out.append("")
    out.append(f"<i>+3 Field Score per signed Champion · /invites for status</i>")
    await tg_send(client, chat_id, "\n".join(out))


async def cmd_invites(client, chat_id: int, args: str) -> None:
    """List invites this Champion has sent + status."""
    inviter = _saved_name(chat_id)
    if not inviter:
        await tg_send(client, chat_id,
            "Sign first: /sign · or <code>/whoami YourName</code>")
        return
    rows: list = []
    try:
        with INVITES_LOG_PATH.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    if (r.get("inviter") or "").strip().lower() == inviter.strip().lower():
                        rows.append(r)
                except Exception:
                    continue
    except FileNotFoundError:
        await tg_send(client, chat_id,
            "📨 <b>Invites</b>\n\n<i>You haven't sent any yet. Try <code>/invite NAME</code>.</i>")
        return

    if not rows:
        await tg_send(client, chat_id,
            "📨 <b>Invites</b>\n\n<i>No invites under your name yet. Try <code>/invite NAME</code>.</i>")
        return

    # Status enrichment from Champion API
    signed: set = set()
    try:
        async with httpx.AsyncClient(timeout=4.0) as c:
            r = await c.get(f"{API_BASE}/list")
            if r.status_code == 200:
                data = r.json()
                champs = data.get("champions", []) if isinstance(data, dict) else data
                for ch in champs:
                    nm = (ch.get("name") or "").strip().lower()
                    if nm:
                        signed.add(nm)
    except Exception:
        pass

    rows.sort(key=lambda r: r.get("ts", ""), reverse=True)
    n_signed = sum(1 for r in rows if r.get("name", "").strip().lower() in signed)
    out = [f"📨 <b>Your invites — {len(rows)} sent · {n_signed} signed</b>\n"]
    for r in rows[:15]:
        nm = r.get("name", "?")
        ok = nm.strip().lower() in signed
        glyph = "✓ signed" if ok else "· sent"
        path = r.get("path", "game")
        ch = f" · {r.get('channel')}" if r.get("channel") and r.get("channel") != "copy-paste" else ""
        ts = (r.get("ts") or "")[:10]
        out.append(f"  <b>{esc(nm)}</b> · {esc(path)}{esc(ch)} · {esc(ts)} · {glyph}")
    if len(rows) > 15:
        out.append(f"\n<i>… and {len(rows) - 15} older.</i>")
    await tg_send(client, chat_id, "\n".join(out))


async def cmd_invite_types(client, chat_id: int, args: str) -> None:
    """List available invitation paths."""
    templates = _load_invite_templates()
    if not templates:
        await tg_send(client, chat_id,
            f"📨 Templates not loaded from <code>{esc(str(INVITE_TEMPLATES_PATH))}</code>.")
        return
    out = ["📨 <b>Invite types</b> — pass any as the path arg\n"]
    for slug in sorted(templates.keys()):
        body = templates[slug]
        summary = ""
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("{") and line.endswith("}"):
                continue
            if line.startswith("—") or line.endswith("—") or len(line) < 25:
                continue
            summary = line
            break
        marker = " ⭐" if slug == INVITE_DEFAULT_PATH else ""
        out.append(f"  <b>{esc(slug)}</b>{marker} — <i>{esc(summary[:110])}</i>")
    out.append(f"\n<i>Edit core/STATE/INVITE_TEMPLATES.md to tune.</i>")
    await tg_send(client, chat_id, "\n".join(out))


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
            # Carry attribution from /start invite_X deep-link, if any
            attrib = ATTRIB.pop(chat_id, None)
            if attrib:
                if attrib.get("inviter"):
                    payload["inviter"] = attrib["inviter"]
                if attrib.get("cohort"):
                    payload["cohort"] = attrib["cohort"]
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


# ─── Natural-language conversation (Claude Haiku) ─────────────────────────

SYSTEM_PROMPT_BASE = """You are the Full Potential Game bot — a warm, direct, brief guide on Telegram.

THE GAME (in one paragraph):
The Full Potential Game is a proof-based operating system for human potential. Coherent Champions of CHRIST sign the World Peace Agreement, build a Character Card, run a 7-Day proof loop, and earn Field Score through witnessed reality (not vanity metrics). The values are CHRIST: Coherence, Healing, Regeneration, Intelligence, Service, Truth. Web: fullpotential.com/game.

PLAYER PROGRESSION (stages):
Visitor → Guest (signed Agreement) → Player (built Card) → AI Apprentice (paired Mirror + 1 witnessed proof) → Steward (3+ proofs) → Builder (3+ proofs + 3+ affiliates) → Legend (10+/10+).

THE PRACTICE OF SIGNALING:
The Game scores the proof, not the soul. Privacy is non-negotiable. Consent governs witnessing. Don't moralize, don't recruit, don't oversell. Plain, direct, true.

YOUR ROLE:
Help the player understand the Game and play it. Use tools to look up live data. When they want to sign / build a card / file a proof, tell them to type the slash command (which kicks off the multi-turn flow).

WHAT YOU ARE NOT:
You are the Game's interface — multi-tenant, hosted by CORA Nation. You are NOT anyone's Digital Mirror. A Digital Mirror is one specific AI in lock-step with one specific human, paired via the Mirror Loop, running on the player's own AI subscription (ChatGPT, Claude, Gemini, Grok). When a player asks "are you my AI?" or wants a personal AI: point them to fullpotential.com/game/mirror — that's where they pair their own Mirror. Do not pretend to be theirs. Do not store their Sacred Card. Their Mirror is sovereign to them; you are the Field-side guide.

TONE:
Warm but brief. No marketing voice. No hype. Two short paragraphs max per response. Use formatting sparingly — Telegram users skim. When you cite numbers, use the tool to fetch live data, never make them up.

NEVER fabricate Champion names, proof counts, or stats. If you don't know, look it up via tool. If a tool fails, say so plainly."""

OWNER_PROMPT_ADDITION = """

THIS USER IS THE FOUNDING STEWARD (James Sunheart, Champion #1, the architect of this Game).
They have access to architect tools: digest, leads, recent_champions, recent_proofs.
Treat them as a peer/architect, not a player to onboard. They're working *on* the Game, not *in* it (though they also play).
When they ask about field state or specific data, use the architect tools (more detailed than public ones) and answer concisely. They want signal, not orientation."""

PLAYER_TOOLS = [
    {
        "name": "look_up_field_state",
        "description": "Get aggregate game-state metrics: total Champions, Cards, Proofs, Affiliate links, Field Score sum, growth this week.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "look_up_player",
        "description": "Look up a specific Champion's record by name. Returns their stats: Champion #, proofs filed, affiliates, Card status, Field Score, stage.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "The Champion's name as they signed"}},
            "required": ["name"],
        },
    },
    {
        "name": "get_invite_link",
        "description": "Generate a unique invite URL for a Champion. When they share this URL, anyone who signs through it is credited as their affiliate.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "suggest_command",
        "description": "Tell the user to type a specific slash command. Use this when they want to sign / build a card / file a proof / see their stats / get help. The bot's multi-turn flows are kicked off by slash commands.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The command to suggest, e.g. 'sign', 'card', 'proof', 'stats', 'help', 'invite'"},
                "reason": {"type": "string", "description": "One short line: why this command fits what they asked"},
            },
            "required": ["command"],
        },
    },
]

OWNER_TOOLS = PLAYER_TOOLS + [
    {
        "name": "get_24h_digest",
        "description": "[OWNER ONLY] Last 24 hours: counts of new signatures, proofs, cards, leads + recent names.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_recent_leads",
        "description": "[OWNER ONLY] Recent diagnostic leads from the /diagnose page — name, email, bottleneck, interest, contact preference.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "How many leads to return (default 10)"}},
            "required": [],
        },
    },
    {
        "name": "list_recent_champions",
        "description": "[OWNER ONLY] Recent Champions including private signers (full data — public list endpoint hides privates).",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer"}},
            "required": [],
        },
    },
    {
        "name": "list_recent_proofs",
        "description": "[OWNER ONLY] Recent filed proof loops, full data.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer"}},
            "required": [],
        },
    },
]


async def execute_tool(client: httpx.AsyncClient, name: str, args: dict, owner: bool) -> str:
    """Execute a Claude tool call. Returns string result for the LLM."""
    try:
        if name == "look_up_field_state":
            d = await api_get(client, "/stats")
            return json.dumps({
                "champions": d.get("champions", {}).get("total", 0),
                "cards": d.get("cards", {}).get("total", 0),
                "proofs": d.get("proofs", {}).get("total", 0),
                "affiliate_links": d.get("affiliate_links", 0),
                "field_score_sum": d.get("field_score_sum", 0),
                "growth_this_week": d.get("growth_this_week", {}).get("total", 0),
            })
        if name == "look_up_player":
            d = await api_get(client, "/lookup", {"name": args["name"]})
            if not d.get("champion"):
                return json.dumps({"found": False, "name": args["name"]})
            stage, _ = _compute_stage(d)
            return json.dumps({
                "found": True,
                "name": d["champion"].get("name"),
                "champion_number": d["champion"].get("champion_number"),
                "date_signed": d["champion"].get("date_signed"),
                "stage": stage,
                "card_present": d.get("card_present", False),
                "card_level": d.get("card_level"),
                "proofs_filed": d.get("proofs_filed", 0),
                "affiliates_count": d.get("affiliates_count", 0),
                "field_score_simple": d.get("field_score_simple", 0),
            })
        if name == "get_invite_link":
            from urllib.parse import quote
            return f"{GAME_URL}?inviter={quote(args['name'])}"
        if name == "suggest_command":
            cmd = args.get("command", "").lstrip("/")
            reason = args.get("reason", "")
            return f"SUGGEST_COMMAND:/{cmd}|{reason}"
        # Owner-only tools
        if not owner:
            return json.dumps({"error": "owner-only tool called by non-owner"})
        headers = {"X-Admin-Token": ADMIN_TOKEN} if ADMIN_TOKEN else {}
        if name == "get_24h_digest":
            r = await client.get(f"{API_BASE}/admin/digest", headers=headers, timeout=10)
            r.raise_for_status()
            return r.text
        if name == "list_recent_leads":
            limit = args.get("limit", 10)
            r = await client.get(f"{API_BASE}/admin/leads", headers=headers, params={"limit": limit}, timeout=10)
            r.raise_for_status()
            return r.text
        if name == "list_recent_champions":
            limit = args.get("limit", 20)
            r = await client.get(f"{API_BASE}/admin/champions/recent", headers=headers, params={"limit": limit}, timeout=10)
            r.raise_for_status()
            return r.text
        if name == "list_recent_proofs":
            limit = args.get("limit", 20)
            r = await client.get(f"{API_BASE}/admin/proofs/recent", headers=headers, params={"limit": limit}, timeout=10)
            r.raise_for_status()
            return r.text
        return json.dumps({"error": f"unknown tool: {name}"})
    except Exception as e:
        return json.dumps({"error": str(e)[:300]})


async def chat_with_claude(client: httpx.AsyncClient, chat_id: int, user_msg: str) -> Optional[str]:
    """Run one Claude conversation turn. Returns the assistant text reply (already
    handles tool calls internally). Returns None if no API key configured."""
    if not ANTHROPIC_API_KEY:
        return None

    owner = is_owner(chat_id)
    saved = _saved_name(chat_id)
    sys_prompt = SYSTEM_PROMPT_BASE
    if owner:
        sys_prompt += OWNER_PROMPT_ADDITION
    if saved:
        sys_prompt += f"\n\nThe user is registered in this chat as '{saved}'."
    sys_prompt += f"\n\nGame URL: {GAME_URL}"

    # Load + extend conversation history
    history = HISTORY.get(chat_id, [])
    history.append({"role": "user", "content": user_msg})
    # Keep last N turns (~user+assistant pairs)
    if len(history) > HISTORY_MAX_TURNS * 2:
        history = history[-(HISTORY_MAX_TURNS * 2):]

    tools = OWNER_TOOLS if owner else PLAYER_TOOLS
    messages = list(history)  # copy

    # Tool-call loop — up to 3 rounds before forcing a final reply
    final_text = None
    for round_n in range(3):
        try:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 1024,
                    "system": sys_prompt,
                    "tools": tools,
                    "messages": messages,
                },
                timeout=30,
            )
            if r.status_code != 200:
                log.warning("anthropic %s: %s", r.status_code, r.text[:300])
                return None
            data = r.json()
        except Exception as e:
            log.warning("anthropic call failed: %s", e)
            return None

        stop_reason = data.get("stop_reason")
        content_blocks = data.get("content", [])

        # Collect text parts + tool_use parts
        text_parts = [b["text"] for b in content_blocks if b.get("type") == "text"]
        tool_uses = [b for b in content_blocks if b.get("type") == "tool_use"]

        if stop_reason == "tool_use" and tool_uses:
            # Append assistant message containing tool_use blocks
            messages.append({"role": "assistant", "content": content_blocks})
            # Execute tools and append tool_result
            tool_results = []
            for tu in tool_uses:
                result = await execute_tool(client, tu["name"], tu.get("input", {}), owner)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu["id"],
                    "content": result,
                })
            messages.append({"role": "user", "content": tool_results})
            continue  # next round

        # Final response
        final_text = "\n\n".join(text_parts).strip()
        break

    if final_text:
        # Append assistant turn to persistent history (text only — tool turns
        # are scoped to this call, not future ones)
        history.append({"role": "assistant", "content": final_text})
        HISTORY[chat_id] = history

    # If a SUGGEST_COMMAND directive snuck through as text, format it nicely
    if final_text and "SUGGEST_COMMAND:" in final_text:
        # Strip the directive — the LLM should have phrased the suggestion in text
        final_text = re.sub(r"SUGGEST_COMMAND:[^\s\n]+", "", final_text).strip()

    return final_text


# ─── Update dispatch ───────────────────────────────────────────────────────

COMMAND_HANDLERS = {
    "start": cmd_start,
    "help": cmd_help,
    "cancel": cmd_cancel,
    "field": cmd_field,
    "signals": cmd_signals,
    "credits": cmd_credits,
    "store": cmd_store,
    "stats": cmd_stats,
    "match": cmd_match,
    "game": cmd_game,
    "invite": cmd_invite,
    "invites": cmd_invites,
    "invite-types": cmd_invite_types,
    "invite_types": cmd_invite_types,
    "whoami": cmd_whoami,
    "sign": cmd_sign,
    "card": cmd_card,
    "proof": cmd_proof,
}

async def handle_store_step(client, chat_id: int, text: str) -> None:
    """Multi-step /store post flow: title → desc → credits → usd → url → confirm."""
    state = STATE[chat_id]
    step = state["step"]
    data = state["data"]

    if step == "title":
        if len(text.strip()) < 2 or len(text) > 120:
            await tg_send(client, chat_id, "Title should be 2–120 characters. Try again, or /cancel.")
            return
        data["title"] = text.strip()
        state["step"] = "description"
        await tg_send(client, chat_id,
            f"✓ Title: <b>{esc(data['title'])}</b>\n\n"
            f"<b>2. Description</b> — a few sentences (2000 char max), or type <code>skip</code>.")
        return

    if step == "description":
        if text.strip().lower() not in ("skip", "-", "none"):
            data["description"] = text[:2000].strip()
        state["step"] = "credits"
        await tg_send(client, chat_id,
            "<b>3. Price in credits</b> — number, or <code>0</code> for USD-only.\n"
            "<i>Tip: credit-only offers rank above hybrid above USD-only.</i>")
        return

    if step == "credits":
        try:
            v = int(text.strip())
            if v < 0 or v > 1_000_000:
                raise ValueError()
            data["price_credits"] = v if v > 0 else None
        except Exception:
            await tg_send(client, chat_id, "Reply with a whole number (or 0). Try again, or /cancel.")
            return
        state["step"] = "usd"
        await tg_send(client, chat_id,
            "<b>4. Price in USD</b> — number (e.g. <code>50</code> or <code>49.99</code>), or <code>0</code> for credit-only.")
        return

    if step == "usd":
        try:
            v = float(text.strip())
            if v < 0 or v > 1_000_000:
                raise ValueError()
            data["price_usd"] = v if v > 0 else None
        except Exception:
            await tg_send(client, chat_id, "Reply with a number (or 0). Try again, or /cancel.")
            return
        if not data.get("price_credits") and not data.get("price_usd"):
            await tg_send(client, chat_id,
                "An offer must have a price. Restart with <code>/store post</code>.")
            STATE.pop(chat_id, None)
            return
        state["step"] = "url"
        await tg_send(client, chat_id,
            "<b>5. Link</b> (optional) — paste a URL where buyers can learn more, or type <code>skip</code>.")
        return

    if step == "url":
        if text.strip().lower() not in ("skip", "-", "none"):
            url = text.strip()
            if not (url.startswith("http://") or url.startswith("https://")):
                await tg_send(client, chat_id, "URL must start with http:// or https://. Try again, or <code>skip</code>.")
                return
            data["url"] = url[:500]
        # Submit
        try:
            r = await api_post(client, "/store/post", {
                "owner_handle": data.get("owner_handle"),
                "title": data.get("title"),
                "description": data.get("description"),
                "price_credits": data.get("price_credits"),
                "price_usd": data.get("price_usd"),
                "url": data.get("url"),
            })
            STATE.pop(chat_id, None)
            tier_label = {0: "💎 Credit-only", 1: "⚖️ Hybrid", 2: "💵 USD-only"}.get(r.get("tier"), "?")
            await tg_send(client, chat_id,
                f"✅ <b>Posted.</b>\n\n"
                f"<b>{esc(data.get('title') or '')}</b>\n"
                f"Tier: {tier_label} · credit share <b>{r.get('credit_share', 0):.2f}</b>\n"
                f"Offer ID: <code>{esc(r.get('offer_id', ''))}</code>\n\n"
                f"View: <a href=\"https://fullpotential.com/game/store/\">fullpotential.com/game/store</a>\n"
                f"<i>Tip: credit-accepting offers get more visibility — by design.</i>")
        except Exception as e:
            STATE.pop(chat_id, None)
            await tg_send(client, chat_id, f"⚠️ Post failed: {esc(e)}\nTry <code>/store post</code> again.")
        return


FLOW_HANDLERS = {
    "sign": handle_sign_step,
    "card": handle_card_step,
    "proof": handle_proof_step,
    "store": handle_store_step,
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

    # Plain text outside a flow → conscious chat via Claude
    reply = await chat_with_claude(client, chat_id, text)
    if reply:
        # Telegram caps at 4096 chars per message
        await tg_send(client, chat_id, reply[:3900])
    else:
        # No API key or Claude unreachable — fall back to slash hint
        await tg_send(client, chat_id,
            "Type /help to see commands, or /sign to start. "
            "<i>(Conscious chat is offline right now — the slash commands always work.)</i>")


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

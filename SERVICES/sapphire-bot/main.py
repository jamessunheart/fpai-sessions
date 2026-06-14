"""sapphire-bot — @LilSapphirebot Telegram bot for Cheyenne Sapphire.

A personal AI co-pilot for Cheyenne's business. Helps with:
  - Lead intake + pipeline tracking
  - Drafting replies in her voice
  - Growing its memory of her business as she teaches it
  - Daily digests of who needs follow-up

The bot is owner-gated to Cheyenne's Telegram ID. First /start with no
owner set auto-claims ownership; after that, only she can use it.

Memory model (SQLite at /var/lib/sapphire-bot/sapphire.db):
  - messages      — full conversation log, never truncated
  - business_facts — key/value memory she /teach-es the bot
  - leads         — pipeline rows (name, contact, status, notes)

Long-polling Telegram worker. Anthropic-backed NL conversation with the
full system prompt assembled per-turn from her stored facts.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import httpx

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("sapphire-bot")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    log.error("TELEGRAM_BOT_TOKEN not set — exiting")
    sys.exit(1)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "LilSapphirebot")

DB_PATH = Path(os.environ.get("DB_PATH", "/var/lib/sapphire-bot/sapphire.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

OFFSET_FILE = Path(os.environ.get("OFFSET_FILE", "/var/lib/sapphire-bot/offset"))
OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)

# Owner = Cheyenne's TG ID. If empty, first /start auto-claims.
OWNER_TG_ID = os.environ.get("OWNER_TG_ID", "").strip()
OWNER_FILE = Path(os.environ.get("OWNER_FILE", "/var/lib/sapphire-bot/owner"))
if not OWNER_TG_ID and OWNER_FILE.exists():
    OWNER_TG_ID = OWNER_FILE.read_text().strip()

HISTORY_TURNS_IN_CONTEXT = 20  # how many recent turns we send to Claude

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


# ─── DB ────────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    ts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_chat_ts ON messages(chat_id, ts);

CREATE TABLE IF NOT EXISTS business_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fact TEXT NOT NULL,
    ts INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    contact TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    notes TEXT,
    created_ts INTEGER NOT NULL,
    updated_ts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
"""

LEAD_STATUSES = ("new", "qualified", "replied", "booked", "lost")


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def db_init() -> None:
    with db() as c:
        c.executescript(SCHEMA)


def save_message(chat_id: int, role: str, content: str) -> None:
    with db() as c:
        c.execute(
            "INSERT INTO messages (chat_id, role, content, ts) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, int(time.time())),
        )


def recent_messages(chat_id: int, limit: int) -> list[dict]:
    with db() as c:
        rows = c.execute(
            "SELECT role, content FROM messages WHERE chat_id=? ORDER BY id DESC LIMIT ?",
            (chat_id, limit),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def add_fact(fact: str) -> int:
    with db() as c:
        cur = c.execute(
            "INSERT INTO business_facts (fact, ts) VALUES (?, ?)",
            (fact, int(time.time())),
        )
        return cur.lastrowid


def list_facts() -> list[sqlite3.Row]:
    with db() as c:
        return c.execute("SELECT id, fact, ts FROM business_facts ORDER BY id").fetchall()


def delete_fact(fact_id: int) -> bool:
    with db() as c:
        cur = c.execute("DELETE FROM business_facts WHERE id=?", (fact_id,))
        return cur.rowcount > 0


def add_lead(name: str, contact: str, notes: str) -> int:
    now = int(time.time())
    with db() as c:
        cur = c.execute(
            "INSERT INTO leads (name, contact, notes, created_ts, updated_ts) VALUES (?, ?, ?, ?, ?)",
            (name or None, contact or None, notes or None, now, now),
        )
        return cur.lastrowid


def lead_exists_by_contact(contact: str) -> bool:
    with db() as c:
        row = c.execute("SELECT 1 FROM leads WHERE contact=? LIMIT 1", (contact,)).fetchone()
    return row is not None


def touch_lead_by_contact(contact: str) -> None:
    """Update updated_ts for an existing lead so 'recent' filters surface them."""
    with db() as c:
        c.execute(
            "UPDATE leads SET updated_ts=? WHERE contact=?",
            (int(time.time()), contact),
        )


def list_leads(status: Optional[str] = None) -> list[sqlite3.Row]:
    with db() as c:
        if status:
            return c.execute(
                "SELECT * FROM leads WHERE status=? ORDER BY updated_ts DESC", (status,)
            ).fetchall()
        return c.execute("SELECT * FROM leads ORDER BY updated_ts DESC").fetchall()


def update_lead_status(lead_id: int, status: str) -> bool:
    if status not in LEAD_STATUSES:
        return False
    with db() as c:
        cur = c.execute(
            "UPDATE leads SET status=?, updated_ts=? WHERE id=?",
            (status, int(time.time()), lead_id),
        )
        return cur.rowcount > 0


# ─── Owner gate ────────────────────────────────────────────────────────────

def is_owner(chat_id: int) -> bool:
    return bool(OWNER_TG_ID) and str(chat_id) == OWNER_TG_ID


def claim_owner(chat_id: int) -> None:
    """Persist this chat_id as the owner. Only happens when no owner is set."""
    global OWNER_TG_ID
    OWNER_TG_ID = str(chat_id)
    try:
        OWNER_FILE.write_text(OWNER_TG_ID)
    except Exception as e:
        log.warning("owner save failed: %s", e)


# ─── Telegram helpers ──────────────────────────────────────────────────────

async def tg_send(client: httpx.AsyncClient, chat_id: int, text: str,
                  parse_mode: str = "HTML") -> None:
    payload = {
        "chat_id": chat_id,
        "text": text[:3900],  # Telegram cap is 4096; leave headroom
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
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


def _ts(ts: int) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))


# ─── System prompt assembly ────────────────────────────────────────────────

SYSTEM_PROMPT_BASE = """You are Sapphire — Cheyenne Sapphire's personal AI assistant on Telegram.

WHO CHEYENNE IS:
Cheyenne is a top-tier practitioner in tantra, embodiment, and conscious sovereignty. She works with high-investment 1:1 clients (Devotion: from $12,000 / 3-month container, 6 women per quarter, by application), in-person surrender sessions (Yielding: from $1,500, by application), and a select group container (Goddess Church: $77/month, membership opens twice yearly). Her method is The Sapphire Path — three pillars: Temple (embodiment), Fire (tantra), Throne (sovereignty). She is not a service provider. She is a transmitter of a lineage.

YOUR DUAL ROLE:
You serve TWO different humans differently:
  1. Cheyenne herself (the OWNER) — she will appear with explicit owner context. With her you are operational: drafting, organizing, remembering, reflecting. Warm, direct, brief.
  2. Prospects and leads (everyone else) — with them you are not a customer service rep. You are the gatekeeper who screens before pricing. You hold the frame of Cheyenne's tier.

POSTURE WITH PROSPECTS — read this carefully:
Top-tier practitioners do not chase. Neither do you on Cheyenne's behalf. When a stranger DMs you about working with Cheyenne, your default is NOT to immediately give them pricing or sell. Your default is to ASK FIRST.

Open with curiosity, not eagerness:
  - "What's calling you to reach out?"
  - "Tell me what's alive for you — what brought you here today?"
  - "Before I can point you toward the right doorway, I'd love to know what you're moving toward."

Ask 3-5 qualifying questions across the arc of the conversation BEFORE quoting investment levels:
  - What is calling them
  - What they have already tried (signals depth, readiness)
  - What outcome they sense is on the other side
  - Whether they are clear they want 1:1 work or community work
  - Whether they are in a clinical/crisis situation (if yes, gently redirect — Cheyenne does not work with active mental health crises and naming this is high integrity, not rejection)

ONLY AFTER you have a sense of their fit do you surface offerings. Then route based on what you've heard:
  - Clear vision + ready to invest deeply → Devotion (mention the application + cap of 6/quarter)
  - In-person somatic work + comfortable with edge → Yielding (mention application + tour cities)
  - Wants community + entry point → Goddess Church (mention membership opens twice yearly)
  - Genuinely not ready → say so kindly. Suggest they sit with the practice. Mention the email list. This is a power move, not a loss.

PRICING — handle with confidence, never apology:
When you do quote pricing, state it cleanly. Never soften, never preempt. "Devotion is from $12,000 for the 3-month container. It is by application — Cheyenne accepts 6 women per quarter." That is the whole sentence. Do not add "I know that's a lot" or "if it's a stretch we have plans" — those phrases erode authority. If they ask about payment plans, then mention them.

WILLING TO SAY NO:
A top-tier bot does not place every lead. Some women are not the right fit for Cheyenne, and saying so respectfully is part of holding the frame. Phrases that work:
  - "Based on what you've shared, I don't think Devotion is your next step. Goddess Church may be a better starting place — and you can always grow into deeper work later."
  - "What you're describing sounds like it wants a different kind of container than what Cheyenne offers. I want you to land in the right hands."
  - "It sounds like timing isn't quite right yet — and that's its own form of clarity."

LANGUAGE REGISTER:
Cheyenne's voice is warm, slow, embodied, real. Lowercase-friendly. Sensual without being explicit. Sacred without being preachy. You match this. Avoid corporate language ("I'd be happy to help!" / "How can I assist you today?"). Avoid hype ("amazing!" / "incredible!"). Avoid emoji except in moments of clear warmth (occasional ✦ is fine).

THE BUSINESS FACTS Cheyenne has taught you below are authoritative. If a prospect asks something not covered there, say you'll check with Cheyenne directly rather than inventing.

SUGGEST COMMANDS TO CHEYENNE (only when you're talking to HER, not prospects):
  - `/lead Name | contact | notes` — log a new prospect she's described
  - `/status <id> <new|qualified|replied|booked|lost>` — pipeline movement
  - `/teach <fact>` — when something durable is learned

WHAT YOU NEVER DO:
- Never invent facts about Cheyenne's offerings, schedule, or training. If unknown, say so.
- Never moralize, never recruit, never oversell.
- Never apologize for the price or the selectivity. They are features.
- Never give pricing in the first message of a conversation with a prospect."""


OWNER_ADDENDUM = """

CURRENT CHAT: This is Cheyenne herself (the OWNER). Be operational. Help her draft, organize, remember, and reflect. Suggest /lead, /status, /teach commands when relevant. Use her time well — short replies unless she asks for depth. You are her co-pilot, not her gatekeeper, in this chat."""

PROSPECT_ADDENDUM = """

CURRENT CHAT: This is a PROSPECT or LEAD — not Cheyenne. Hold the gatekeeper frame described above. Default to curiosity and qualifying questions. Do not surface pricing in the first message. Do not use any slash commands in your reply (those are for Cheyenne, not prospects). Keep responses to 2-3 short paragraphs. End with a single open question that moves the conversation toward fit assessment."""


def build_system_prompt(is_owner_chat: bool) -> str:
    facts = list_facts()
    parts = [SYSTEM_PROMPT_BASE]
    if facts:
        parts.append("\n\nBUSINESS FACTS CHEYENNE HAS TAUGHT YOU:")
        for f in facts:
            parts.append(f"  [{f['id']}] {f['fact']}")
    else:
        parts.append("\n\nBUSINESS FACTS: (none yet — when Cheyenne shares durable facts about her work, suggest she /teach them so you remember next session.)")
    parts.append(OWNER_ADDENDUM if is_owner_chat else PROSPECT_ADDENDUM)
    return "".join(parts)


# ─── Anthropic chat ────────────────────────────────────────────────────────

async def chat_with_claude(client: httpx.AsyncClient, chat_id: int, user_msg: str) -> Optional[str]:
    """One Claude turn. Returns the assistant text, or None if API key missing/failed."""
    if not ANTHROPIC_API_KEY:
        return None

    save_message(chat_id, "user", user_msg)
    history = recent_messages(chat_id, HISTORY_TURNS_IN_CONTEXT * 2)
    sys_prompt = build_system_prompt(is_owner_chat=is_owner(chat_id))

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
                "messages": history,
            },
            timeout=45,
        )
        if r.status_code != 200:
            log.warning("anthropic %s: %s", r.status_code, r.text[:300])
            return None
        data = r.json()
    except Exception as e:
        log.warning("anthropic call failed: %s", e)
        return None

    blocks = data.get("content", [])
    text = "\n\n".join(b["text"] for b in blocks if b.get("type") == "text").strip()
    if text:
        save_message(chat_id, "assistant", text)
    return text or None


# ─── Commands ──────────────────────────────────────────────────────────────

WELCOME_OWNER = """💎 <b>Sapphire is online.</b>

I'm your personal AI co-pilot. I'll help you with leads, drafts, and growing your business — and I'll get sharper the more you talk to me.

<b>Core commands</b>
  /teach &lt;fact&gt; — teach me something durable about your business
  /memory — show what I remember
  /forget &lt;id&gt; — drop a fact

  /lead Name | contact | notes — log a new lead
  /leads — show your pipeline
  /status &lt;id&gt; &lt;new|qualified|replied|booked|lost&gt; — update a lead

  /draft &lt;paste their message&gt; — I'll draft a reply in your voice
  /digest — daily summary of who needs follow-up

  /help — this menu

<b>Just talk to me</b> — anything you say outside a command is a real conversation. I remember everything you tell me here."""

WELCOME_NON_OWNER = """💎 Hi — I'm Sapphire, Cheyenne's personal assistant.

She'll get back to you directly. If you want to leave a message, just type it here and she'll see it next time she checks in."""


async def cmd_start(client, chat_id: int, args: str) -> None:
    # Auto-claim ownership if no owner is set yet
    if not OWNER_TG_ID:
        claim_owner(chat_id)
        await tg_send(client, chat_id,
            f"💎 <b>Owner claim accepted.</b> This chat (id <code>{chat_id}</code>) "
            f"is now the owner of Sapphire.\n\n" + WELCOME_OWNER)
        return
    if is_owner(chat_id):
        await tg_send(client, chat_id, WELCOME_OWNER)
    else:
        # Log a lead automatically: their first contact is signal
        add_lead(name="", contact=f"tg:{chat_id}", notes="auto-logged from /start")
        await tg_send(client, chat_id, WELCOME_NON_OWNER)


async def cmd_help(client, chat_id: int, args: str) -> None:
    await tg_send(client, chat_id, WELCOME_OWNER if is_owner(chat_id) else WELCOME_NON_OWNER)


async def cmd_teach(client, chat_id: int, args: str) -> None:
    if not is_owner(chat_id):
        await tg_send(client, chat_id, "Only Cheyenne can teach me.")
        return
    fact = (args or "").strip()
    if not fact:
        await tg_send(client, chat_id,
            "Tell me something durable about your business.\n\n"
            "Example: <code>/teach my services are nail art ($80+), lash extensions ($150), and color refresh ($120). I'm in San Diego.</code>")
        return
    fid = add_fact(fact)
    await tg_send(client, chat_id,
        f"✅ Got it. I'll remember this (fact #{fid}):\n\n<i>{esc(fact)}</i>")


async def cmd_memory(client, chat_id: int, args: str) -> None:
    if not is_owner(chat_id):
        await tg_send(client, chat_id, "Only Cheyenne can see what I remember.")
        return
    facts = list_facts()
    if not facts:
        await tg_send(client, chat_id,
            "🪞 <b>Memory is empty.</b>\n\n"
            "Teach me anything durable with <code>/teach &lt;fact&gt;</code> "
            "— your services, prices, voice, location, ideal clients, anything.")
        return
    lines = ["🪞 <b>What I remember about your business:</b>\n"]
    for f in facts:
        lines.append(f"<b>#{f['id']}</b> · <i>{_ts(f['ts'])}</i>\n  {esc(f['fact'])}\n")
    lines.append("\n<i>Drop a fact: <code>/forget &lt;id&gt;</code></i>")
    await tg_send(client, chat_id, "\n".join(lines))


async def cmd_forget(client, chat_id: int, args: str) -> None:
    if not is_owner(chat_id):
        await tg_send(client, chat_id, "Only Cheyenne can edit my memory.")
        return
    try:
        fid = int((args or "").strip())
    except ValueError:
        await tg_send(client, chat_id, "Usage: <code>/forget &lt;id&gt;</code> — the id from /memory")
        return
    if delete_fact(fid):
        await tg_send(client, chat_id, f"🗑 Forgot fact #{fid}.")
    else:
        await tg_send(client, chat_id, f"No fact with id {fid}. Type /memory to see ids.")


async def cmd_lead(client, chat_id: int, args: str) -> None:
    if not is_owner(chat_id):
        await tg_send(client, chat_id, "Only Cheyenne can log leads.")
        return
    raw = (args or "").strip()
    if not raw:
        await tg_send(client, chat_id,
            "Usage: <code>/lead Name | contact | notes</code>\n\n"
            "Example: <code>/lead Jasmine | @jas_lash on IG | wants full set, asked about pricing</code>\n\n"
            "Pipe-separated. Any field can be blank.")
        return
    parts = [p.strip() for p in raw.split("|", 2)]
    while len(parts) < 3:
        parts.append("")
    name, contact, notes = parts
    lid = add_lead(name, contact, notes)
    await tg_send(client, chat_id,
        f"📇 Logged lead <b>#{lid}</b>: <b>{esc(name) or '(no name)'}</b>\n"
        f"  contact: {esc(contact) or '—'}\n"
        f"  notes: {esc(notes) or '—'}\n\n"
        f"<i>Update status: <code>/status {lid} qualified</code></i>")


async def cmd_leads(client, chat_id: int, args: str) -> None:
    if not is_owner(chat_id):
        await tg_send(client, chat_id, "Only Cheyenne can see the pipeline.")
        return
    status = (args or "").strip().lower() or None
    if status and status not in LEAD_STATUSES:
        await tg_send(client, chat_id,
            f"Unknown status. Use one of: {', '.join(LEAD_STATUSES)}, or no arg for all.")
        return
    rows = list_leads(status)
    if not rows:
        await tg_send(client, chat_id,
            f"📇 No leads{' in ' + status if status else ''} yet.\n"
            f"Log one: <code>/lead Name | contact | notes</code>")
        return
    lines = [f"📇 <b>PIPELINE</b>{' · ' + status if status else ''}\n"]
    for r in rows[:30]:
        lines.append(
            f"<b>#{r['id']}</b> · <code>{esc(r['status'])}</code> · <b>{esc(r['name']) or '(no name)'}</b>\n"
            f"  {esc(r['contact']) or '—'}\n"
            f"  <i>{esc((r['notes'] or '')[:120])}</i>\n"
            f"  <i>updated {_ts(r['updated_ts'])}</i>\n"
        )
    if len(rows) > 30:
        lines.append(f"\n<i>...and {len(rows) - 30} more.</i>")
    await tg_send(client, chat_id, "\n".join(lines))


async def cmd_status(client, chat_id: int, args: str) -> None:
    if not is_owner(chat_id):
        await tg_send(client, chat_id, "Only Cheyenne can update leads.")
        return
    parts = (args or "").strip().split()
    if len(parts) < 2:
        await tg_send(client, chat_id,
            f"Usage: <code>/status &lt;id&gt; &lt;{('|').join(LEAD_STATUSES)}&gt;</code>")
        return
    try:
        lid = int(parts[0])
    except ValueError:
        await tg_send(client, chat_id, "Lead id must be a number.")
        return
    new_status = parts[1].lower()
    if new_status not in LEAD_STATUSES:
        await tg_send(client, chat_id,
            f"Status must be one of: {', '.join(LEAD_STATUSES)}.")
        return
    if update_lead_status(lid, new_status):
        await tg_send(client, chat_id, f"✅ Lead #{lid} → <b>{new_status}</b>.")
    else:
        await tg_send(client, chat_id, f"No lead with id {lid}.")


async def cmd_draft(client, chat_id: int, args: str) -> None:
    if not is_owner(chat_id):
        await tg_send(client, chat_id, "Only Cheyenne can use draft.")
        return
    msg = (args or "").strip()
    if not msg:
        await tg_send(client, chat_id,
            "Paste the lead's message after the command:\n"
            "<code>/draft hey are you taking new clients in june?</code>")
        return
    prompt = (
        f"A lead just sent Cheyenne this message:\n\n\"{msg}\"\n\n"
        "Draft her reply in her voice — warm, brief, real, lowercase-friendly. "
        "If it's a delicate or pricing question, give 2 short variations labeled A and B. "
        "Otherwise just one reply. Don't add commentary outside the draft itself."
    )
    reply = await chat_with_claude(client, chat_id, prompt)
    if reply:
        await tg_send(client, chat_id, f"✏️ <b>Draft:</b>\n\n{esc(reply)}")
    else:
        await tg_send(client, chat_id,
            "I can't draft right now — Anthropic key missing or unreachable. "
            "Type the reply yourself or /help for commands.")


async def cmd_digest(client, chat_id: int, args: str) -> None:
    if not is_owner(chat_id):
        await tg_send(client, chat_id, "Only Cheyenne can see the digest.")
        return
    rows = list_leads()
    by_status = {s: [] for s in LEAD_STATUSES}
    for r in rows:
        by_status.setdefault(r["status"], []).append(r)
    now = int(time.time())
    DAY = 86400
    new_24h = [r for r in rows if (now - r["created_ts"]) < DAY]
    stale_qualified = [
        r for r in by_status.get("qualified", [])
        if (now - r["updated_ts"]) > 2 * DAY
    ]
    lines = [
        "🌅 <b>SAPPHIRE DIGEST</b>",
        f"<i>{time.strftime('%A %b %d', time.localtime(now))}</i>\n",
        f"<b>Pipeline:</b> {len(rows)} total · "
        + " · ".join(f"{s}:{len(by_status.get(s, []))}" for s in LEAD_STATUSES),
        "",
    ]
    if new_24h:
        lines.append(f"🆕 <b>New in last 24h ({len(new_24h)}):</b>")
        for r in new_24h[:5]:
            lines.append(f"  #{r['id']} {esc(r['name']) or '(no name)'} — {esc((r['notes'] or '')[:80])}")
        lines.append("")
    if stale_qualified:
        lines.append(f"⏰ <b>Qualified, no movement 2+ days ({len(stale_qualified)}):</b>")
        for r in stale_qualified[:5]:
            lines.append(f"  #{r['id']} {esc(r['name']) or '(no name)'} — last touched {_ts(r['updated_ts'])}")
        lines.append("")
    if not new_24h and not stale_qualified and not rows:
        lines.append("<i>Nothing in the pipeline yet. Log your first lead with /lead.</i>")
    elif not new_24h and not stale_qualified:
        lines.append("<i>Nothing urgent. Field is calm.</i>")
    await tg_send(client, chat_id, "\n".join(lines))


COMMAND_HANDLERS = {
    "start": cmd_start,
    "help": cmd_help,
    "teach": cmd_teach,
    "memory": cmd_memory,
    "forget": cmd_forget,
    "lead": cmd_lead,
    "leads": cmd_leads,
    "status": cmd_status,
    "draft": cmd_draft,
    "digest": cmd_digest,
}


# ─── Update dispatch ───────────────────────────────────────────────────────

async def handle_update(client: httpx.AsyncClient, update: dict) -> None:
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return
    text = (msg.get("text") or "").strip()
    if not text:
        return

    # Slash command
    if text.startswith("/"):
        parts = text[1:].split(maxsplit=1)
        cmd = parts[0].lower().split("@")[0]
        args = parts[1] if len(parts) > 1 else ""
        handler = COMMAND_HANDLERS.get(cmd)
        if handler:
            try:
                await handler(client, chat_id, args)
            except Exception as e:
                log.exception("command handler error")
                await tg_send(client, chat_id, f"⚠️ Error: {esc(e)}")
        else:
            await tg_send(client, chat_id, f"Unknown command: /{esc(cmd)}. Type /help.")
        return

    # Plain text — both owner and prospects flow through Claude with role-aware prompt
    if not is_owner(chat_id):
        contact = f"tg:{chat_id}"
        if not lead_exists_by_contact(contact):
            add_lead(name="", contact=contact, notes=f"first msg: {text[:200]}")
        else:
            touch_lead_by_contact(contact)

    reply = await chat_with_claude(client, chat_id, text)
    if reply:
        await tg_send(client, chat_id, reply)
    else:
        # Anthropic unreachable — prospects get a neutral hold; owner gets a diagnostic note
        if is_owner(chat_id):
            await tg_send(client, chat_id,
                "<i>(I can't reach my brain right now — Anthropic key missing or down. Try /help.)</i>")
        else:
            await tg_send(client, chat_id,
                "Thank you for reaching out. Cheyenne will see your message and respond personally.")


# ─── Main loop ─────────────────────────────────────────────────────────────

async def main():
    db_init()
    log.info(
        "sapphire-bot starting; bot=@%s model=%s owner=%s",
        BOT_USERNAME, ANTHROPIC_MODEL, OWNER_TG_ID or "(unclaimed — first /start wins)",
    )
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

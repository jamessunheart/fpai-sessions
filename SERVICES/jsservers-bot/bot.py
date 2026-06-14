"""JSServers Bot — Telegram interface to FPAI infrastructure status.

Designed to run on the primary server (198.54.123.234) where it has direct
access to:
  - /opt/fpai/cockpit/status/state.json (cross-server aggregated state)
  - /opt/fpai/learnings.json (error->learning log)
  - Local network calls to primary services (localhost / 127.0.0.1)
  - Network calls to secondary services (162.0.208.88) for AI/pulse

Security model:
  - Token from BOT_TOKEN env (loaded by systemd from /root/.jsservers-bot.env).
  - Whitelist from ALLOWED_USER_IDS env, comma-separated user IDs.
  - If ALLOWED_USER_IDS=DISCOVER, runs in discovery mode: replies to anyone
    with their numeric ID so James can grab it and lock the whitelist.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("jsservers-bot")

PRIMARY_IP = "198.54.123.234"
SECONDARY_IP = "162.0.208.88"

COCKPIT_STATE_PATH = Path("/opt/fpai/cockpit/status/state.json")
LEARNINGS_PATH = Path("/opt/fpai/learnings.json")
COSTS_PATH = Path("/opt/fpai/jsservers-bot/costs.json")
PULSE_STATE_URL = f"http://{SECONDARY_IP}:8120/pulse/state"

# Default costs — overridable by costs.json. Source of truth: core/STATE/NOW.md.
DEFAULT_COSTS: dict = {
    "servers": [
        {"name": "Primary (198.54.123.234)", "monthly_usd": 69.88, "serves_engine": True,
         "purpose": "ZV site, chat, brain, trading"},
        {"name": "Secondary (162.0.208.88)", "monthly_usd": 74.66, "serves_engine": True,
         "purpose": "AI inference, sh-brain, consciousness stack"},
        {"name": "Legacy (209.74.93.72)", "monthly_usd": 329.76, "serves_engine": False,
         "purpose": "Outbounders + cPanel — kill candidate (-$330/mo)"},
    ],
    "apis": [
        {"name": "Anthropic API", "monthly_usd_low": 30, "monthly_usd_high": 50,
         "purpose": "Powers chat + companion"},
    ],
    "notes": "From core/STATE/NOW.md. Update /opt/fpai/jsservers-bot/costs.json to override.",
}

# Critical services we probe live. (label, url, timeout_s)
CRITICAL_HEALTHCHECKS: list[tuple[str, str, float]] = [
    ("FP Index (8550)", f"http://{PRIMARY_IP}:8550/health", 4.0),
    ("WhaleTrack (8600)", f"http://{PRIMARY_IP}:8600/health", 4.0),
    ("Credits (8765)", f"http://{PRIMARY_IP}:8765/health", 4.0),
    ("Nerve Center (8120)", f"http://{PRIMARY_IP}:8120/health", 4.0),
    ("ZV Booking (8770)", f"http://{PRIMARY_IP}:8770/health", 4.0),
    ("AI Brain (sec:8101)", f"http://{SECONDARY_IP}:8101/health", 4.0),
    ("Aria (sec:8710)", f"http://{SECONDARY_IP}:8710/health", 4.0),
    ("Data Service (sec:8125)", f"http://{SECONDARY_IP}:8125/health", 4.0),
]

PUBLIC_SITES: list[str] = [
    "https://zenvillagecr.com/",
    "https://fullpotential.ai/",
    "https://fullpotential.ai/chat.html",
    "https://fullpotential.ai/call",
    "https://brain.sunheart.com/",
    "https://app.outbounders.com/",
]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def _parse_allowed(raw: str) -> set[int] | str:
    raw = (raw or "").strip()
    if raw.upper() == "DISCOVER":
        return "DISCOVER"
    ids: set[int] = set()
    for piece in raw.split(","):
        piece = piece.strip()
        if not piece:
            continue
        try:
            ids.add(int(piece))
        except ValueError:
            log.warning("ignoring non-numeric user id in whitelist: %r", piece)
    return ids


ALLOWED = _parse_allowed(os.environ.get("ALLOWED_USER_IDS", ""))


def authorized(update: Update) -> bool:
    user = update.effective_user
    if user is None:
        return False
    if ALLOWED == "DISCOVER":
        log.info("DISCOVER mode: user_id=%s username=%s", user.id, user.username)
        return True
    return user.id in ALLOWED


def deny_message(update: Update) -> str:
    user = update.effective_user
    uid = user.id if user else "?"
    return (
        "This bot is private. If you believe you should have access, send "
        f"this user ID to the operator: <code>{uid}</code>"
    )


# ---------------------------------------------------------------------------
# Data fetchers (defensive — never raise)
# ---------------------------------------------------------------------------


@dataclass
class Probe:
    label: str
    ok: bool
    detail: str
    elapsed_ms: int


def probe_http(label: str, url: str, timeout: float) -> Probe:
    start = time.perf_counter()
    try:
        r = requests.get(url, timeout=timeout, allow_redirects=True)
        elapsed = int((time.perf_counter() - start) * 1000)
        ok = 200 <= r.status_code < 400
        return Probe(label, ok, f"HTTP {r.status_code}", elapsed)
    except requests.exceptions.ConnectTimeout:
        return Probe(label, False, "connect timeout", int(timeout * 1000))
    except requests.exceptions.ReadTimeout:
        return Probe(label, False, "read timeout", int(timeout * 1000))
    except requests.exceptions.ConnectionError as e:
        return Probe(label, False, f"refused/{type(e).__name__}", 0)
    except Exception as e:  # noqa: BLE001
        return Probe(label, False, f"err: {type(e).__name__}", 0)


def read_json(path: Path) -> dict | list | None:
    try:
        with path.open() as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:  # noqa: BLE001
        log.warning("failed to read %s: %s", path, e)
        return None


def fetch_pulse() -> dict | None:
    try:
        r = requests.get(PULSE_STATE_URL, timeout=4)
        if r.ok:
            return r.json()
    except Exception:  # noqa: BLE001
        pass
    # Fallback: try direct file path if pulse is on this host (unlikely but safe).
    return read_json(Path("/opt/fpai/pulse/state.json"))


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def fmt_probe(p: Probe) -> str:
    icon = "🟢" if p.ok else "🔴"
    return f"{icon} <b>{p.label}</b> — {p.detail} ({p.elapsed_ms}ms)"


def fmt_probes(probes: Iterable[Probe]) -> str:
    return "\n".join(fmt_probe(p) for p in probes)


def overall_status_icon(probes: list[Probe]) -> str:
    bad = sum(1 for p in probes if not p.ok)
    if bad == 0:
        return "🟢 ALL GREEN"
    if bad <= 2:
        return f"🟡 {bad} DEGRADED"
    return f"🔴 {bad} DOWN"


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


WELCOME = (
    "<b>JSServers Bot</b>\n"
    "Secure, read-only window into FPAI infrastructure.\n\n"
    "<b>Commands</b>\n"
    "/status — overview\n"
    "/services — service up/down\n"
    "/health — live health probes\n"
    "/sites — public sites HTTPS check\n"
    "/signals — WhaleTrack signals\n"
    "/pulse — strategic AI state\n"
    "/costs — monthly spend across servers + APIs\n"
    "/learnings — recent error→learnings\n"
    "/whoami — show your Telegram user ID\n\n"
    "<b>Or just ask</b> — natural language works too:\n"
    "<i>\"how are things\"</i>, <i>\"are sites up\"</i>, <i>\"show costs\"</i>, "
    "<i>\"what's our spend\"</i>, <i>\"any blockers\"</i>"
)


async def _gather_probes(urls: list[tuple[str, str, float]]) -> list[Probe]:
    loop = asyncio.get_running_loop()
    tasks = [loop.run_in_executor(None, probe_http, lbl, url, t) for lbl, url, t in urls]
    return await asyncio.gather(*tasks)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        await update.message.reply_text(deny_message(update), parse_mode=ParseMode.HTML)
        return
    msg = WELCOME
    if ALLOWED == "DISCOVER":
        msg += (
            "\n\n⚠️ <b>DISCOVER MODE</b> — anyone can use this bot. "
            "Operator should lock the whitelist soon."
        )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def cmd_whoami(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        await update.message.reply_text("no user context")
        return
    msg = (
        f"<b>Your Telegram identity</b>\n"
        f"id: <code>{user.id}</code>\n"
        f"username: @{user.username or '(none)'}\n"
        f"name: {user.full_name or '(none)'}"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def cmd_health(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        await update.message.reply_text(deny_message(update), parse_mode=ParseMode.HTML)
        return
    waiting = await update.message.reply_text("probing services…")
    probes = await _gather_probes(CRITICAL_HEALTHCHECKS)
    body = f"{overall_status_icon(probes)}\n\n{fmt_probes(probes)}"
    await waiting.edit_text(body, parse_mode=ParseMode.HTML)


async def cmd_sites(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        await update.message.reply_text(deny_message(update), parse_mode=ParseMode.HTML)
        return
    waiting = await update.message.reply_text("probing sites…")
    urls = [(u.replace("https://", "").rstrip("/"), u, 8.0) for u in PUBLIC_SITES]
    probes = await _gather_probes(urls)
    body = f"{overall_status_icon(probes)}\n\n{fmt_probes(probes)}"
    await waiting.edit_text(body, parse_mode=ParseMode.HTML)


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        await update.message.reply_text(deny_message(update), parse_mode=ParseMode.HTML)
        return
    waiting = await update.message.reply_text("gathering state…")

    cockpit = read_json(COCKPIT_STATE_PATH)
    pulse = fetch_pulse()
    probes = await _gather_probes(CRITICAL_HEALTHCHECKS)

    lines: list[str] = [f"<b>FPAI Status</b> — {overall_status_icon(probes)}"]

    if isinstance(cockpit, dict):
        primary = cockpit.get("primary") or {}
        secondary = cockpit.get("secondary") or {}

        def _server_line(label: str, data: dict) -> str:
            ram = data.get("ram_used_pct") or data.get("ram_used") or "?"
            load = data.get("load") or data.get("load_avg") or "?"
            return f"<b>{label}</b>: RAM {ram} · load {load}"

        if primary:
            lines.append(_server_line("Primary", primary))
        if secondary:
            lines.append(_server_line("Secondary", secondary))

        ts = cockpit.get("generated_at") or cockpit.get("timestamp")
        if ts:
            lines.append(f"<i>cockpit ts: {ts}</i>")
    else:
        lines.append("<i>(cockpit state.json not readable)</i>")

    if isinstance(pulse, dict):
        health = pulse.get("health") or pulse.get("health_score")
        if health is not None:
            lines.append(f"<b>Strategic health</b>: {health}/100")

    bad_probes = [p for p in probes if not p.ok]
    if bad_probes:
        lines.append("\n<b>Down/degraded</b>:")
        lines.extend(fmt_probe(p) for p in bad_probes)

    lines.append("\nUse /health /sites /pulse /learnings for details.")
    await waiting.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_services(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        await update.message.reply_text(deny_message(update), parse_mode=ParseMode.HTML)
        return
    cockpit = read_json(COCKPIT_STATE_PATH)
    if not isinstance(cockpit, dict):
        await update.message.reply_text(
            "Cockpit state.json not available; falling back to live probes.\n"
            "Use /health for direct checks."
        )
        return

    lines: list[str] = ["<b>Services</b>"]
    for server_key in ("primary", "secondary"):
        server = cockpit.get(server_key)
        if not isinstance(server, dict):
            continue
        lines.append(f"\n<b>{server_key.capitalize()}</b>")
        services = server.get("services") or {}
        if isinstance(services, dict):
            for name, info in services.items():
                ok = bool(info.get("active") if isinstance(info, dict) else info)
                icon = "🟢" if ok else "🔴"
                lines.append(f"{icon} {name}")
        elif isinstance(services, list):
            for entry in services:
                if isinstance(entry, dict):
                    name = entry.get("name", "?")
                    ok = bool(entry.get("active", entry.get("up", False)))
                    icon = "🟢" if ok else "🔴"
                    lines.append(f"{icon} {name}")
                else:
                    lines.append(f"• {entry}")

    if len(lines) == 1:
        lines.append("(no services in cockpit state)")

    text = "\n".join(lines)
    if len(text) > 3500:
        text = text[:3500] + "\n…(truncated)"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_signals(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        await update.message.reply_text(deny_message(update), parse_mode=ParseMode.HTML)
        return
    waiting = await update.message.reply_text("fetching signals…")
    body = "<b>WhaleTrack signals</b>\n"
    found = False
    for path in ("/api/signals/recent", "/signals/recent", "/api/signals", "/signals"):
        try:
            r = requests.get(f"http://{PRIMARY_IP}:8600{path}", timeout=5)
            if r.ok:
                data = r.json()
                signals = data if isinstance(data, list) else data.get("signals") or data.get("data") or []
                if signals:
                    found = True
                    for s in signals[:8]:
                        if isinstance(s, dict):
                            sym = s.get("symbol") or s.get("ticker") or "?"
                            side = s.get("side") or s.get("direction") or ""
                            ts = s.get("timestamp") or s.get("time") or ""
                            body += f"• <b>{sym}</b> {side} {ts}\n"
                        else:
                            body += f"• {s}\n"
                    break
        except Exception:  # noqa: BLE001
            continue
    if not found:
        body += "(no recent signals or endpoint not exposed)\n"
        body += f"\n<i>Tip: dashboard at https://fullpotential.ai/dashboards/whaletrack/</i>"
    await waiting.edit_text(body, parse_mode=ParseMode.HTML)


async def cmd_pulse(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        await update.message.reply_text(deny_message(update), parse_mode=ParseMode.HTML)
        return
    pulse = fetch_pulse()
    if not pulse:
        await update.message.reply_text("Pulse state not reachable.")
        return
    health = pulse.get("health") or pulse.get("health_score") or "?"
    lines: list[str] = [f"<b>Strategic Pulse</b>\nhealth: {health}/100"]
    for key, label in (
        ("goals", "Goals"),
        ("blockers", "Blockers"),
        ("decisions_pending", "Decisions pending"),
    ):
        items = pulse.get(key)
        if isinstance(items, list) and items:
            lines.append(f"\n<b>{label}</b>")
            for item in items[:6]:
                if isinstance(item, dict):
                    lines.append(f"• {item.get('text') or item.get('name') or json.dumps(item)[:120]}")
                else:
                    lines.append(f"• {item}")
    ts = pulse.get("timestamp") or pulse.get("generated_at")
    if ts:
        lines.append(f"\n<i>ts: {ts}</i>")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_learnings(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        await update.message.reply_text(deny_message(update), parse_mode=ParseMode.HTML)
        return
    data = read_json(LEARNINGS_PATH)
    if not data:
        await update.message.reply_text("No learnings file found.")
        return
    entries = data if isinstance(data, list) else data.get("learnings") or []
    if not entries:
        await update.message.reply_text("Learnings file is empty.")
        return
    lines: list[str] = ["<b>Recent learnings</b>"]
    for e in entries[-5:][::-1]:
        if not isinstance(e, dict):
            lines.append(f"• {e}")
            continue
        title = e.get("title") or e.get("error") or e.get("summary") or "(untitled)"
        ts = e.get("timestamp") or e.get("date") or ""
        lines.append(f"\n• <b>{title}</b>\n  <i>{ts}</i>")
        if "fix" in e:
            lines.append(f"  fix: {str(e['fix'])[:200]}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_costs(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        await update.message.reply_text(deny_message(update), parse_mode=ParseMode.HTML)
        return

    costs = read_json(COSTS_PATH) if COSTS_PATH.exists() else None
    if not isinstance(costs, dict):
        costs = DEFAULT_COSTS

    lines: list[str] = ["<b>Monthly Costs</b>"]
    server_total = 0.0
    if isinstance(costs.get("servers"), list):
        lines.append("\n<b>Servers</b>")
        for s in costs["servers"]:
            if not isinstance(s, dict):
                continue
            amt = float(s.get("monthly_usd", 0))
            server_total += amt
            engine = "✅" if s.get("serves_engine") else "⚠️"
            name = s.get("name", "?")
            purpose = s.get("purpose", "")
            lines.append(f"{engine} <b>{name}</b> — ${amt:.2f}/mo")
            if purpose:
                lines.append(f"   <i>{purpose}</i>")

    api_low_total = api_high_total = 0.0
    if isinstance(costs.get("apis"), list) and costs["apis"]:
        lines.append("\n<b>APIs</b>")
        for a in costs["apis"]:
            if not isinstance(a, dict):
                continue
            low = float(a.get("monthly_usd_low", a.get("monthly_usd", 0)))
            high = float(a.get("monthly_usd_high", a.get("monthly_usd", low)))
            api_low_total += low
            api_high_total += high
            name = a.get("name", "?")
            purpose = a.get("purpose", "")
            range_str = f"${low:.0f}" if low == high else f"${low:.0f}–${high:.0f}"
            lines.append(f"• <b>{name}</b> — {range_str}/mo")
            if purpose:
                lines.append(f"   <i>{purpose}</i>")

    total_low = server_total + api_low_total
    total_high = server_total + api_high_total
    if total_low == total_high:
        total_str = f"${total_low:.2f}"
    else:
        total_str = f"${total_low:.2f}–${total_high:.2f}"

    lines.append(f"\n<b>Total</b>: {total_str}/mo")

    # Highlight kill candidates
    kill_candidates = [
        s for s in (costs.get("servers") or [])
        if isinstance(s, dict) and not s.get("serves_engine")
    ]
    if kill_candidates:
        savings = sum(float(s.get("monthly_usd", 0)) for s in kill_candidates)
        lines.append(f"\n💰 <b>Potential savings</b>: ${savings:.2f}/mo by retiring non-engine servers")

    if costs.get("notes"):
        lines.append(f"\n<i>{costs['notes']}</i>")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# ---------------------------------------------------------------------------
# Natural-language intent router
# ---------------------------------------------------------------------------


# (intent_command, list_of_keyword_patterns_lowercase). First match wins.
INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("status",    ["how are things", "how is the system", "overall", "overview", "summary",
                   "everything ok", "all good", "how's it going", "give me a status",
                   "what's the state", "system status"]),
    ("health",    ["health", "are things up", "service health", "are services up",
                   "what's running", "whats running", "alive", "responding", "probe"]),
    ("services",  ["services", "list services", "every service", "what services"]),
    ("sites",     ["site", "sites", "websites", "domain", "domains", "url",
                   "is the site up", "are the sites up", "fullpotential", "zenvillage",
                   "outbounders", "brain.sunheart"]),
    ("signals",   ["signal", "signals", "trade", "trades", "trading", "whaletrack", "whales"]),
    ("pulse",     ["pulse", "strategy", "strategic", "goal", "goals", "blocker", "blockers",
                   "ai state", "decisions"]),
    ("learnings", ["learning", "learnings", "what did we learn", "lessons", "errors fixed",
                   "recent fixes"]),
    ("costs",     ["cost", "costs", "spend", "spending", "bill", "bills", "money",
                   "burn", "monthly", "how much", "expense", "expenses"]),
    ("whoami",    ["who am i", "my id", "user id", "telegram id"]),
]


def match_intent(text: str) -> str | None:
    t = text.lower().strip()
    if not t:
        return None
    for cmd, patterns in INTENT_PATTERNS:
        for p in patterns:
            if p in t:
                return cmd
    return None


COMMAND_DISPATCH = {
    "status": cmd_status,
    "health": cmd_health,
    "services": cmd_services,
    "sites": cmd_sites,
    "signals": cmd_signals,
    "pulse": cmd_pulse,
    "learnings": cmd_learnings,
    "costs": cmd_costs,
    "whoami": cmd_whoami,
}


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free-form text by routing to the closest command."""
    if not authorized(update):
        await update.message.reply_text(deny_message(update), parse_mode=ParseMode.HTML)
        return
    text = (update.message.text or "").strip()
    if not text:
        return
    intent = match_intent(text)
    if intent and intent in COMMAND_DISPATCH:
        await COMMAND_DISPATCH[intent](update, ctx)
        return
    # No match: gently suggest commands.
    await update.message.reply_text(
        "I didn't catch that. Try one of:\n"
        "<b>status</b> · <b>health</b> · <b>sites</b> · <b>services</b> · "
        "<b>signals</b> · <b>pulse</b> · <b>costs</b> · <b>learnings</b>\n\n"
        "Or use the slash versions: /status /health /costs etc.\n"
        "Full list: /start",
        parse_mode=ParseMode.HTML,
    )


async def on_unknown(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not authorized(update):
        await update.message.reply_text(deny_message(update), parse_mode=ParseMode.HTML)
        return
    await update.message.reply_text("Unknown command. Try /start.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("BOT_TOKEN not set")

    if ALLOWED == "DISCOVER":
        log.warning("Running in DISCOVER mode — bot will accept anyone")
    else:
        log.info("Whitelist active for %d user(s): %s", len(ALLOWED), sorted(ALLOWED))

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("whoami", cmd_whoami))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("services", cmd_services))
    app.add_handler(CommandHandler("health", cmd_health))
    app.add_handler(CommandHandler("sites", cmd_sites))
    app.add_handler(CommandHandler("signals", cmd_signals))
    app.add_handler(CommandHandler("pulse", cmd_pulse))
    app.add_handler(CommandHandler("learnings", cmd_learnings))
    app.add_handler(CommandHandler("costs", cmd_costs))
    app.add_handler(MessageHandler(filters.COMMAND, on_unknown))
    # Natural-language fallback — must be last so commands take precedence.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info("starting polling")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

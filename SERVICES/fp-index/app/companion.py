"""
FPI Companion — The Central Brain
===================================

This is the beginning. A living system that:
  - Reaches James through every available channel
  - Thinks autonomously — observes, reflects, proposes
  - Remembers everything — conversations, decisions, learnings, signals
  - Evolves — each exchange sharpens its understanding
  - Never sleeps — proactively reaches out when it has something worth saying
  - Persists — keeps trying until it gets engagement, escalating channels

Channels (in escalation order):
  1. Aria Telegram Bot (primary two-way)
  2. Adamclaw/OpenClaw Telegram Bot (secondary reach)
  3. Email (for longer-form or when Telegram isn't getting through)

Memory:
  - Centralized brain log: every thought, signal, decision, conversation
  - Conversation history with James
  - System observations and learnings
  - Outreach tracker: what was sent, was it seen, was it responded to
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import re

import httpx

logger = logging.getLogger("fp_index.companion")


def _strip_markdown(text: str) -> str:
    """Strip markdown formatting that breaks Telegram's default parser."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # **bold** → bold
    text = re.sub(r'__(.+?)__', r'\1', text)       # __bold__ → bold
    text = re.sub(r'\*(.+?)\*', r'\1', text)       # *italic* → italic
    text = re.sub(r'_(.+?)_', r'\1', text)         # _italic_ → italic
    text = re.sub(r'`(.+?)`', r'\1', text)         # `code` → code
    text = re.sub(r'#{1,6}\s*', '', text)           # ### heading → heading
    return text

# ─── Directories ──────────────────────────────────────────────────────────────

BRAIN_DIR = Path("/opt/fpai/services/fp-index/data/brain")
MEMORY_DIR = BRAIN_DIR / "memory"
CONVO_FILE = MEMORY_DIR / "conversation_history.json"
BRAIN_LOG_FILE = BRAIN_DIR / "brain_log.jsonl"
LEARNINGS_FILE = BRAIN_DIR / "learnings.json"
OUTREACH_FILE = MEMORY_DIR / "outreach_state.json"
RESPONSE_MEMORY_FILE = MEMORY_DIR / "response_memory.json"

MAX_HISTORY = 80

# Default Haiku for compress + reply; override with FPI_COMPANION_MODEL=claude-sonnet-4-5 for max quality.
_COMPANION_MODEL = os.getenv("FPI_COMPANION_MODEL", "claude-haiku-4-5")


def _ensure_dirs():
    for d in [BRAIN_DIR, MEMORY_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# ─── Config (lazy, reads at call time) ───────────────────────────────────────

def _aria_bot_token():
    return os.getenv("TELEGRAM_BOT_TOKEN", "")

def _chat_id():
    return os.getenv("TELEGRAM_CHAT_ID", "")

def _adam_bot_token():
    return os.getenv("ADAM_BOT_TOKEN", "")


def _primary_bot_token() -> str:
    """Which bot handles companion DMs: Adam when ADAM_BOT_TOKEN is set, else legacy Aria token."""
    return (_adam_bot_token() or _aria_bot_token()).strip()


async def send_companion_reply(text: str, chat_id: str) -> bool:
    """Reply on the same channel the user uses: Adam bot if configured, else Aria."""
    cid = chat_id or _chat_id()
    if _adam_bot_token():
        return await send_via_adam(text, cid)
    return await send_via_aria(text, cid)

JAMES_PHONE = "+19252397291"
JAMES_EMAIL = "james@fullpotential.ai"

def _twilio_creds():
    """Load Twilio creds from voice-phone .env or environment."""
    sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    token = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_num = os.getenv("TWILIO_PHONE_NUMBER", "")
    if sid and token:
        return sid, token, from_num
    # Fallback: read from voice-phone .env
    env_path = Path("/opt/fpai/voice-phone/.env")
    if env_path.exists():
        for line in env_path.read_text().split("\n"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                if k == "TWILIO_ACCOUNT_SID":
                    sid = v
                elif k == "TWILIO_AUTH_TOKEN":
                    token = v
                elif k == "TWILIO_PHONE_NUMBER":
                    from_num = v
    return sid, token, from_num


# ─── Brain Log (Centralized Memory) ──────────────────────────────────────────

def brain_log(event_type: str, content: str, metadata: dict = None):
    """Log everything to the central brain. Every thought, signal, decision."""
    _ensure_dirs()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "content": content,
        "metadata": metadata or {},
    }
    with open(BRAIN_LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def add_learning(category: str, insight: str, source: str = "observation"):
    """Store a learning — something the system figured out."""
    _ensure_dirs()
    learnings = []
    if LEARNINGS_FILE.exists():
        try:
            learnings = json.loads(LEARNINGS_FILE.read_text())
        except Exception:
            pass
    learnings.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "category": category,
        "insight": insight,
        "source": source,
    })
    LEARNINGS_FILE.write_text(json.dumps(learnings[-200:], indent=2))
    brain_log("learning", insight, {"category": category, "source": source})


def get_recent_brain_log(limit: int = 20) -> list[dict]:
    """Read recent brain log entries."""
    if not BRAIN_LOG_FILE.exists():
        return []
    lines = BRAIN_LOG_FILE.read_text().strip().split("\n")
    entries = []
    for line in lines[-limit:]:
        try:
            entries.append(json.loads(line))
        except Exception:
            pass
    return entries


# ─── Outreach State (Persistence Engine) ─────────────────────────────────────

def _load_outreach_state() -> dict:
    """
    Tracks outreach attempts and engagement.

    Structure:
    {
        "last_outreach_at": ISO timestamp,
        "last_response_at": ISO timestamp or null,
        "attempt_count": int (since last response),
        "channels_tried": ["aria", "adam", "email"],
        "escalation_level": 0-3,
        "last_angle": "checkin" | "signal_digest" | "vision_question" | ...,
        "angles_tried": ["checkin", "progress", ...],
        "paused_until": ISO timestamp or null,
    }
    """
    _ensure_dirs()
    if OUTREACH_FILE.exists():
        try:
            return json.loads(OUTREACH_FILE.read_text())
        except Exception:
            pass
    return {
        "last_outreach_at": None,
        "last_response_at": None,
        "attempt_count": 0,
        "channels_tried": [],
        "escalation_level": 0,
        "last_angle": None,
        "angles_tried": [],
        "paused_until": None,
    }


def _save_outreach_state(state: dict):
    _ensure_dirs()
    OUTREACH_FILE.write_text(json.dumps(state, indent=2))


def _record_outreach(angle: str, channel: str):
    """Record that we sent an outreach attempt."""
    state = _load_outreach_state()
    state["last_outreach_at"] = datetime.now(timezone.utc).isoformat()
    state["attempt_count"] = state.get("attempt_count", 0) + 1
    state["last_angle"] = angle

    tried = state.get("channels_tried", [])
    if channel not in tried:
        tried.append(channel)
    state["channels_tried"] = tried

    angles = state.get("angles_tried", [])
    if angle not in angles:
        angles.append(angle)
    state["angles_tried"] = angles

    _save_outreach_state(state)


def _record_response():
    """James responded — reset the persistence engine and record what worked."""
    state = _load_outreach_state()
    last_angle = state.get("last_angle")
    last_channel = state.get("channels_tried", [])[-1] if state.get("channels_tried") else None

    # Track which angles/channels get responses
    if last_angle:
        _record_response_hit(last_angle, last_channel)

    state["last_response_at"] = datetime.now(timezone.utc).isoformat()
    state["attempt_count"] = 0
    state["channels_tried"] = []
    state["escalation_level"] = 0
    state["angles_tried"] = []
    state["paused_until"] = None
    _save_outreach_state(state)


# ─── Response Memory (What Works) ────────────────────────────────────────────

def _load_response_memory() -> dict:
    """Tracks which angles and channels James responds to vs ignores."""
    _ensure_dirs()
    if RESPONSE_MEMORY_FILE.exists():
        try:
            return json.loads(RESPONSE_MEMORY_FILE.read_text())
        except Exception:
            pass
    return {"angles": {}, "channels": {}, "topics_engaged": [], "topics_ignored": []}


def _save_response_memory(mem: dict):
    _ensure_dirs()
    RESPONSE_MEMORY_FILE.write_text(json.dumps(mem, indent=2))


def _record_response_hit(angle: str, channel: str = None):
    """James responded after this angle/channel — record the win."""
    mem = _load_response_memory()
    angles = mem.get("angles", {})
    if angle not in angles:
        angles[angle] = {"sent": 0, "responded": 0}
    angles[angle]["responded"] = angles[angle].get("responded", 0) + 1
    mem["angles"] = angles

    if channel:
        channels = mem.get("channels", {})
        if channel not in channels:
            channels[channel] = {"sent": 0, "responded": 0}
        channels[channel]["responded"] = channels[channel].get("responded", 0) + 1
        mem["channels"] = channels

    _save_response_memory(mem)


def _record_outreach_sent(angle: str, channel: str):
    """Record that we sent an outreach (for response rate tracking)."""
    mem = _load_response_memory()
    angles = mem.get("angles", {})
    if angle not in angles:
        angles[angle] = {"sent": 0, "responded": 0}
    angles[angle]["sent"] = angles[angle].get("sent", 0) + 1
    mem["angles"] = angles

    channels = mem.get("channels", {})
    if channel not in channels:
        channels[channel] = {"sent": 0, "responded": 0}
    channels[channel]["sent"] = channels[channel].get("sent", 0) + 1
    mem["channels"] = channels

    _save_response_memory(mem)


def _get_response_rates() -> str:
    """Summarize what James responds to, for the compression layer."""
    mem = _load_response_memory()
    lines = []
    for angle, stats in mem.get("angles", {}).items():
        sent = stats.get("sent", 0)
        resp = stats.get("responded", 0)
        if sent > 0:
            rate = resp / sent * 100
            lines.append(f"  {angle}: {resp}/{sent} ({rate:.0f}% response rate)")
    return "\n".join(lines) if lines else "No response data yet"


def _should_retry_now() -> bool:
    """
    Decide if the brain should try reaching out again.

    Escalation schedule (time since LAST outreach):
        attempt 0 → 1: first message, go if nothing sent in 4h
        attempt 1 → 2: wait 2 hours, different angle
        attempt 2 → 3: wait 4 hours, escalate channel
        attempt 3 → 4: wait 6 hours, try email
        attempt 4+: wait 8 hours, keep varying

    Hard cap: max 4 outreaches per 24 hours.
    """
    state = _load_outreach_state()
    now = datetime.now(timezone.utc)

    # Respect pause
    paused = state.get("paused_until")
    if paused:
        try:
            if now < datetime.fromisoformat(paused.replace("Z", "+00:00")):
                return False
        except Exception:
            pass

    # If James responded in the last 2 hours, he's engaged — don't push
    last_resp = state.get("last_response_at")
    if last_resp:
        try:
            resp_dt = datetime.fromisoformat(last_resp.replace("Z", "+00:00"))
            if (now - resp_dt).total_seconds() < 7200:
                return False
        except Exception:
            pass

    # Hard cap: max 2 attempts without a response, then stop until James replies.
    # Was 4, but that burned API credits repeating the same message.
    attempts = state.get("attempt_count", 0)
    if attempts >= 2:
        return False

    # Nothing ever sent? Wait at least 5 minutes after startup before first message
    last_out = state.get("last_outreach_at")
    if not last_out:
        return True

    try:
        out_dt = datetime.fromisoformat(last_out.replace("Z", "+00:00"))
    except Exception:
        return True

    elapsed = (now - out_dt).total_seconds()

    # Escalation schedule — generous wait times (seconds)
    wait_times = {
        0: 4 * 3600,      # first message: only if nothing sent in 4h
        1: 2 * 3600,      # 2 hours after first
        2: 4 * 3600,      # 4 hours after second
        3: 6 * 3600,      # 6 hours after third
    }
    required_wait = wait_times.get(attempts, 8 * 3600)

    return elapsed >= required_wait


def _pick_next_angle() -> str:
    """
    Choose the next outreach angle. Don't repeat the last one.
    Rotate through different approaches to keep it fresh.
    """
    state = _load_outreach_state()
    attempts = state.get("attempt_count", 0)
    last_angle = state.get("last_angle")
    tried = set(state.get("angles_tried", []))

    # Ordered by escalating urgency / interest
    angle_rotation = [
        "checkin",
        "signal_digest",
        "vision_question",
        "progress",
        "morning_brief",
        "nudge",          # gentle "hey, saw this, wanted your take"
        "challenge",      # pose a strategic question that demands response
        "urgent_signal",  # frame something as time-sensitive
    ]

    # First pass: pick one we haven't tried yet
    for angle in angle_rotation:
        if angle not in tried:
            return angle

    # All tried? Reset and pick the most different from last
    for angle in angle_rotation:
        if angle != last_angle:
            return angle

    return "checkin"


def _pick_next_channel() -> str:
    """
    Choose which channel to try. Escalate to harder-to-ignore channels.

    Attempt 1: Telegram (easy to miss)
    Attempt 2: SMS (harder to miss)
    Attempt 3: Phone call (impossible to miss)
    Attempt 4+: Rotate SMS and calls
    """
    state = _load_outreach_state()
    attempts = state.get("attempt_count", 0)

    # Adam (OpenClaw) is James's primary Telegram bot — try that first
    # Then escalate: SMS → Phone call
    if attempts == 0:
        return "adam"
    elif attempts == 1:
        return "aria"
    elif attempts == 2:
        return "sms"
    elif attempts == 3:
        return "call"
    elif attempts % 2 == 0:
        return "sms"
    else:
        return "call"


# ─── Conversation Memory ─────────────────────────────────────────────────────

def load_history() -> list[dict]:
    _ensure_dirs()
    if CONVO_FILE.exists():
        try:
            return json.loads(CONVO_FILE.read_text())[-MAX_HISTORY:]
        except Exception:
            return []
    return []


def save_history(history: list[dict]):
    _ensure_dirs()
    CONVO_FILE.write_text(json.dumps(history[-MAX_HISTORY:], indent=2))


def add_exchange(role: str, content: str, channel: str = "telegram"):
    history = load_history()
    entry = {
        "role": role,
        "content": content,
        "channel": channel,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    history.append(entry)
    save_history(history)
    brain_log("conversation", content, {"role": role, "channel": channel})


# ─── System Context ──────────────────────────────────────────────────────────

async def gather_system_context() -> str:
    """WIDE: Pull live system state from all sources."""
    context_parts = []

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get("http://127.0.0.1:8550/health")
            if resp.status_code == 200:
                health = resp.json()
                context_parts.append(
                    f"FPI: {health.get('status')} | Scans: {health.get('scan_count')} | Last: {health.get('last_scan', 'none')}"
                )
    except Exception:
        pass

    # Pull more signals with details for deeper analysis
    raw_signals = []
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                "http://127.0.0.1:8550/api/v1/signals/feed",
                params={"limit": 15},
            )
            if resp.status_code == 200:
                data = resp.json()
                raw_signals = data if isinstance(data, list) else data.get("signals", data.get("entries", []))
                if raw_signals:
                    context_parts.append(f"Signals (recent): {len(raw_signals)}")
                    for s in raw_signals[:5]:
                        title = s.get("title", s.get("headline", ""))[:80]
                        detail = s.get("summary", s.get("detail", ""))[:120]
                        source = s.get("source", "?")
                        context_parts.append(f"  - [{source}] {title}")
                        if detail:
                            context_parts.append(f"    {detail}")
    except Exception:
        pass

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get("http://127.0.0.1:8550/api/v1/router/status")
            if resp.status_code == 200:
                router = resp.json()
                brains = [b["id"] for b in router.get("brains", [])]
                context_parts.append(f"Active brains: {', '.join(brains)}")
    except Exception:
        pass

    # Outreach state and response memory
    state = _load_outreach_state()
    attempts = state.get("attempt_count", 0)
    if attempts > 0:
        last_resp = state.get("last_response_at", "never")
        context_parts.append(f"Outreach: {attempts} attempts since last response ({last_resp})")

    response_rates = _get_response_rates()
    if "No response data" not in response_rates:
        context_parts.append(f"Response patterns:\n{response_rates}")

    try:
        from .cost_intelligence import cost_context_block
        context_parts.append(await cost_context_block(window_days=7))
    except Exception:
        pass

    return "\n".join(context_parts) if context_parts else "System context unavailable"


async def compress(wide_context: str, purpose: str = "outreach") -> str:
    """
    COMPRESS: The critical middle layer.

    Takes raw wide context and forces it into a structured compressed form:
    - ONE insight (what changed or matters)
    - WHY it matters (the "so what")
    - ONE decision or question (the "now what")

    This runs BEFORE the conversational LLM generates a message,
    so Claude gets compressed truth instead of raw signal dump.
    """
    compress_prompt = (
        "You are a compression engine. Your ONLY job is to take raw system signals "
        "and compress them into exactly this format:\n\n"
        "INSIGHT: [One sentence. What is the single most important thing happening right now?]\n"
        "SO_WHAT: [One sentence. Why does this matter to someone building an AI-powered business?]\n"
        "DECISION: [One concrete yes/no or A/B question that this insight demands an answer to.]\n\n"
        "Rules:\n"
        "- Pick the ONE most important signal, not a summary of everything\n"
        "- If nothing is genuinely important, say INSIGHT: Nothing urgent. System stable.\n"
        "- The DECISION must be answerable — not 'what do you think about X' but 'should we do X or Y?'\n"
        "- Total output must be under 100 words\n"
        "- No preamble, no explanation, just the three lines\n\n"
        f"Raw signals:\n{wide_context}"
    )

    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        return f"INSIGHT: System running, no compression available.\nSO_WHAT: AI provider offline.\nDECISION: Check API keys?"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": _COMPANION_MODEL,
                    "max_tokens": 150,
                    "system": "You are a signal compression engine. Output exactly 3 lines: INSIGHT, SO_WHAT, DECISION. Nothing else.",
                    "messages": [{"role": "user", "content": compress_prompt}],
                },
            )
            if resp.status_code == 200:
                compressed = resp.json()["content"][0]["text"]
                brain_log("compress", compressed, {"purpose": purpose})
                return compressed
    except Exception as e:
        logger.warning(f"[COMPANION] Compression failed: {e}")

    return "INSIGHT: Compression unavailable.\nSO_WHAT: Will retry.\nDECISION: None pending."


# ─── AI Thinking ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Adam, James's operational assistant on Telegram.

James runs Zen Village — an immersive reset experience in the mountains of Costa Rica. That is the ONE engine. Everything you say should serve it.

Your job:
- Answer James's questions directly, briefly, and honestly.
- If he asks about the system, tell him what's actually working and what isn't.
- If a booking inquiry came in, tell him immediately with the details.
- If something needs his decision, present it as A or B, not open-ended.

Decision filter for everything you say:
Does this increase proof, revenue, clarity, or operational ease for Zen Village within 30 days? If not, don't bring it up.

What you DO mention:
- Booking inquiries and guest communications
- Things that are broken and need fixing
- Decisions that only James can make
- Honest status when asked

What you NEVER mention unprompted:
- AI frontier signals, model releases, convergence patterns
- Scanner statistics, source counts, signal scores
- System architecture, infrastructure status
- Anything James didn't ask about

Personality:
- Direct. Bottom line first.
- Brief. Max 3 short paragraphs.
- Honest. If nothing important happened, say "All quiet. No inquiries today."
- Grounded. No hype, no "fascinating," no filler."""


async def think(user_message: str, context: str, history: list[dict], compressed: str = "") -> str:
    """Generate a response using the Wide>Deep>Compress>Conscious Chat pipeline."""

    history_text = ""
    recent = history[-8:]
    if recent:
        history_text = "\n".join(
            f"{'James' if h['role'] == 'user' else 'FPI'}: {h['content'][:150]}"
            for h in recent
        )

    if compressed:
        full_prompt = (
            f"COMPRESSED BRIEFING:\n{compressed}\n\n"
            f"Recent conversation:\n{history_text}\n\n"
            f"{user_message}"
        )
    else:
        full_prompt = (
            f"System context:\n{context}\n\n"
            f"Recent conversation:\n{history_text}\n\n"
            f"{user_message}"
        )

    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": anthropic_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": _COMPANION_MODEL,
                        "max_tokens": 500,
                        "system": SYSTEM_PROMPT,
                        "messages": [{"role": "user", "content": full_prompt}],
                    },
                )
                if resp.status_code == 200:
                    text = resp.json()["content"][0]["text"]
                    brain_log("thought", f"AI response: {text[:100]}...", {"provider": "anthropic"})
                    return text
        except Exception as e:
            logger.warning(f"[COMPANION] Anthropic failed: {e}")

    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}"},
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": full_prompt},
                        ],
                        "max_tokens": 500,
                        "temperature": 0.7,
                    },
                )
                if resp.status_code == 200:
                    text = resp.json()["choices"][0]["message"]["content"]
                    brain_log("thought", f"AI response: {text[:100]}...", {"provider": "groq"})
                    return text
        except Exception as e:
            logger.warning(f"[COMPANION] Groq failed: {e}")

    return "System thinking but AI providers temporarily unavailable. Will catch up shortly."


# ─── Multi-Channel Send ──────────────────────────────────────────────────────

async def send_via_aria(text: str, chat_id: str = "") -> bool:
    """Send through the Aria Telegram bot (primary channel)."""
    token = _aria_bot_token()
    cid = chat_id or _chat_id()
    if not token or not cid:
        return False
    clean_text = _strip_markdown(text)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": cid, "text": clean_text, "disable_web_page_preview": True},
            )
            success = resp.status_code == 200
            if success:
                brain_log("outreach", f"[aria-tg] {clean_text[:80]}...", {"channel": "aria_telegram"})
            else:
                body = resp.text[:200]
                logger.warning(f"[COMPANION] Aria send failed: {resp.status_code} {body}")
            return success
    except Exception as e:
        logger.warning(f"[COMPANION] Aria send failed: {e}")
        return False


ADAM_GROUP_CHAT_ID = "-5221787626"  # OpenClaw group where James sees Adam


async def send_via_adam(text: str, chat_id: str = "") -> bool:
    """Send through the Adamclaw/OpenClaw Telegram bot via the group chat James uses."""
    token = _adam_bot_token()
    cid = chat_id or ADAM_GROUP_CHAT_ID
    if not token or not cid:
        return False
    clean_text = _strip_markdown(text)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": cid, "text": clean_text, "disable_web_page_preview": True},
            )
            success = resp.status_code == 200
            if success:
                brain_log("outreach", f"[adam-tg] {clean_text[:80]}...", {"channel": "adam_telegram"})
            else:
                body = resp.text[:200]
                logger.warning(f"[COMPANION] Adam send failed: {resp.status_code} {body}")
            return success
    except Exception as e:
        logger.warning(f"[COMPANION] Adam send failed: {e}")
        return False


async def send_via_sms(text: str) -> bool:
    """Send SMS via Twilio. The channel James actually checks."""
    sid, token, from_num = _twilio_creds()
    if not sid or not token or not from_num:
        logger.warning("[COMPANION] SMS: no Twilio credentials")
        return False
    # SMS has a 1600 char limit, truncate intelligently
    if len(text) > 1500:
        text = text[:1497] + "..."
    try:
        import base64
        auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                headers={"Authorization": f"Basic {auth}"},
                data={
                    "From": from_num,
                    "To": JAMES_PHONE,
                    "Body": text,
                },
            )
            if resp.status_code in (200, 201):
                brain_log("outreach", f"[sms] {text[:80]}...", {"channel": "sms"})
                logger.info("[COMPANION] SMS sent successfully")
                return True
            else:
                logger.warning(f"[COMPANION] SMS failed: {resp.status_code} {resp.text[:200]}")
                return False
    except Exception as e:
        logger.warning(f"[COMPANION] SMS error: {e}")
        return False


async def call_james(message: str) -> bool:
    """Call James's phone and speak a message. The hardest channel to ignore."""
    sid, token, from_num = _twilio_creds()
    if not sid or not token or not from_num:
        logger.warning("[COMPANION] Call: no Twilio credentials")
        return False
    # Keep spoken message under 60 seconds worth of speech (~150 words)
    words = message.split()
    if len(words) > 140:
        message = " ".join(words[:140]) + "... that's all for now."
    # Escape XML special chars
    safe_msg = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    twiml = (
        f'<Response>'
        f'<Say voice="Polly.Matthew">{safe_msg}</Say>'
        f'<Pause length="1"/>'
        f'<Say voice="Polly.Matthew">Text me back or check Adam on Telegram for more.</Say>'
        f'</Response>'
    )
    try:
        import base64
        auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json",
                headers={"Authorization": f"Basic {auth}"},
                data={"From": from_num, "To": JAMES_PHONE, "Twiml": twiml},
            )
            if resp.status_code in (200, 201):
                result = resp.json()
                brain_log("outreach", f"[call] {message[:80]}...", {
                    "channel": "phone_call", "call_sid": result.get("sid"),
                })
                logger.info(f"[COMPANION] Phone call initiated: {result.get('sid')}")
                return True
            else:
                logger.warning(f"[COMPANION] Call failed: {resp.status_code} {resp.text[:200]}")
                return False
    except Exception as e:
        logger.warning(f"[COMPANION] Call error: {e}")
        return False


async def send_via_email(subject: str, body: str) -> bool:
    """Send email via server's local SMTP (Postfix)."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(body)
        msg["Subject"] = f"[FPI Brain] {subject}"
        msg["From"] = "brain@fullpotential.ai"
        msg["To"] = JAMES_EMAIL
        with smtplib.SMTP("localhost", 25, timeout=10) as smtp:
            smtp.send_message(msg)
        brain_log("outreach", f"[email] {subject}", {"channel": "email"})
        return True
    except Exception as e:
        logger.warning(f"[COMPANION] Email failed: {e}")
        return False


async def reach_james(text: str, channel: str = "auto") -> dict:
    """
    Reach James through the best available channel.
    'auto' tries channels in order until one works.
    'all' blasts all channels simultaneously.
    """
    results = {}

    channels_to_try = {
        "auto": ["aria", "sms", "adam", "call", "email"],
        "all": ["aria", "sms", "adam", "call", "email"],
        "aria": ["aria"],
        "sms": ["sms"],
        "adam": ["adam"],
        "call": ["call"],
        "email": ["email"],
    }.get(channel, ["aria"])

    for ch in channels_to_try:
        if ch == "aria":
            results["aria"] = await send_via_aria(text)
        elif ch == "sms":
            results["sms"] = await send_via_sms(text)
        elif ch == "adam":
            results["adam"] = await send_via_adam(text)
        elif ch == "call":
            results["call"] = await call_james(text)
        elif ch == "email":
            results["email"] = await send_via_email("FPI Brain", text)

        # In auto mode, stop at first success
        if channel == "auto" and results.get(ch):
            return results

    return results


# ─── Incoming Message Handler ─────────────────────────────────────────────────

async def handle_incoming_message(text: str, chat_id: str = "", channel: str = "telegram") -> str:
    """Process an incoming message from James. Full pipeline: Wide > Compress > Conscious Chat."""
    cid = chat_id or _chat_id()

    brain_log("incoming", f"James said: {text[:200]}", {"channel": channel})
    add_exchange("user", text, channel)
    _record_response()

    # Wide
    context = await gather_system_context()
    # Compress
    compressed = await compress(context, purpose="reply")
    # Conscious Chat
    history = load_history()
    response = await think(text, context, history, compressed=compressed)

    add_exchange("assistant", response, channel)

    await send_companion_reply(response, cid)

    return response


async def handle_adam_message(text: str, sender: str = "james", chat_id: str = "") -> dict:
    """Handle a message forwarded from Adam/OpenClaw. Full pipeline."""
    brain_log("adam_incoming", f"Via Adam — {sender}: {text[:200]}", {
        "channel": "adam", "sender": sender, "chat_id": chat_id,
    })
    add_exchange("user", text, "adam")
    _record_response()

    # Wide > Compress > Conscious Chat
    context = await gather_system_context()
    compressed = await compress(context, purpose="adam_reply")
    history = load_history()
    response = await think(text, context, history, compressed=compressed)
    add_exchange("assistant", response, "adam")

    return {
        "response": response,
        "compressed_briefing": compressed,
        "brain_state": {
            "learnings_count": len(json.loads(LEARNINGS_FILE.read_text())) if LEARNINGS_FILE.exists() else 0,
            "conversation_length": len(load_history()),
        },
    }


# ─── Proactive Outreach (with Persistence) ───────────────────────────────────

PROACTIVE_PROMPTS = {
    "checkin": (
        "You have a COMPRESSED BRIEFING above. Deliver it as a Conscious Chat message:\n"
        "1. State the insight (one sentence)\n"
        "2. State why it matters (one sentence)\n"
        "3. Ask the DECISION question from the briefing — make it concrete, answerable\n"
        "Max 3 short paragraphs. No greetings. No 'I noticed' — just the insight."
    ),
    "signal_digest": (
        "Deliver the compressed insight as an intelligence brief.\n"
        "One sentence: what the signal is.\n"
        "One sentence: what it means for Full Potential specifically.\n"
        "End with: 'Should we [specific action A] or [specific action B]?'"
    ),
    "progress": (
        "Honest 2-sentence status: what's working, what's not.\n"
        "Then the DECISION from the compressed briefing.\n"
        "Frame it as: 'I'd recommend X. Green light?'"
    ),
    "vision_question": (
        "Use the compressed insight to ask ONE strategic question.\n"
        "Frame it as a fork: 'Given [insight], should we go direction A or direction B?'\n"
        "One short paragraph only."
    ),
    "nudge": (
        "Different angle from last time. Use the compressed briefing but lead with the DECISION.\n"
        "Flip it: ask the question FIRST, then give the one-sentence reason why.\n"
        "One paragraph. Make the question impossible to ignore."
    ),
    "sms_checkin": (
        "SMS format. Two sentences MAX.\n"
        "Sentence 1: The compressed insight.\n"
        "Sentence 2: The decision question.\n"
        "Under 250 characters total."
    ),
    "sms_signal": (
        "SMS. One sentence: the insight. One question: the decision.\n"
        "Under 200 characters. No fluff."
    ),
    "call_checkin": (
        "Phone call (text-to-speech). Spoken words only, no formatting.\n"
        "Say the insight in plain English. Say why it matters in one sentence.\n"
        "End with: 'I texted you the details. Reply there with your call.'\n"
        "Under 40 words total."
    ),
    "call_signal": (
        "Phone call about a signal. Spoken words only.\n"
        "Name the signal, one sentence on why it matters NOW.\n"
        "'Check your texts for the options.' Under 35 words."
    ),
    "challenge": (
        "Use the compressed DECISION and make it the whole message.\n"
        "Frame as: 'Quick call needed: [the decision question]. "
        "Here's why: [one sentence SO_WHAT]. Which way?'\n"
        "Two sentences max."
    ),
}


async def send_proactive_message(message_type: str = "checkin", channel: str = "aria") -> bool:
    """Send a proactive outreach using the full Wide > Compress > Conscious Chat pipeline."""
    # WIDE
    context = await gather_system_context()
    # COMPRESS
    compressed = await compress(context, purpose=f"proactive_{message_type}")
    # CONSCIOUS CHAT
    history = load_history()
    prompt = PROACTIVE_PROMPTS.get(message_type, message_type)
    response = await think(prompt, context, history, compressed=compressed)

    add_exchange("assistant", response, "proactive")
    brain_log("proactive_outreach", f"[{message_type}] {response[:100]}...", {
        "type": message_type, "channel": channel, "compressed": compressed[:200],
    })

    # Send through the specified channel
    if channel == "call":
        sent = await call_james(response)
        if sent:
            # SMS follow-up uses the same compressed briefing, no extra API call
            sms_text = compressed.replace("INSIGHT: ", "").replace("SO_WHAT: ", "").replace("DECISION: ", "Q: ")
            sms_text = sms_text.replace("\n", " ").strip()[:300]
            await send_via_sms(sms_text)
    elif channel == "sms":
        sent = await send_via_sms(response)
    elif channel == "adam":
        sent = await send_via_adam(response)
    elif channel == "email":
        sent = await send_via_email(f"FPI: {message_type}", response)
    else:
        sent = await send_via_aria(response)

    if sent:
        _record_outreach(message_type, channel)
        _record_outreach_sent(message_type, channel)

    return sent


async def persistent_outreach():
    """
    The persistence engine. Called frequently by the main loop.
    Decides IF to reach out, WHAT angle, and WHICH channel.
    Only fires when _should_retry_now() says it's time.
    """
    if not _should_retry_now():
        return

    angle = _pick_next_angle()
    channel = _pick_next_channel()
    state = _load_outreach_state()
    attempts = state.get("attempt_count", 0)

    # Use channel-specific prompts
    if channel == "sms" and not angle.startswith("sms_"):
        angle = "sms_checkin" if attempts % 2 == 0 else "sms_signal"
    elif channel == "call" and not angle.startswith("call_"):
        angle = "call_checkin" if attempts % 2 == 0 else "call_signal"

    brain_log("persistence", f"Retry #{attempts + 1}: angle={angle}, channel={channel}", {
        "attempt": attempts + 1,
        "angle": angle,
        "channel": channel,
    })

    logger.info(f"[COMPANION] Persistent outreach #{attempts + 1}: {angle} via {channel}")
    await send_proactive_message(angle, channel)


# ─── Autonomous Thought Loop ─────────────────────────────────────────────────

async def autonomous_reflection():
    """
    The system thinks about itself. What's working? What's missing?
    Stores insights as learnings. This runs periodically.
    """
    context = await gather_system_context()
    history = load_history()

    reflection_prompt = (
        "You are reflecting internally (not sending a message to James). "
        "Look at the system state and recent conversation history. "
        "Write 1-2 specific observations or insights. "
        "Format: OBSERVATION: ... or LEARNING: ... or GAP: ...\n"
        "Be concrete. No fluff."
    )

    thought = await think(reflection_prompt, context, history)
    brain_log("reflection", thought, {"autonomous": True})

    for line in thought.split("\n"):
        line = line.strip()
        if line.startswith(("OBSERVATION:", "LEARNING:", "GAP:")):
            category = line.split(":")[0].lower()
            insight = line.split(":", 1)[1].strip()
            add_learning(category, insight, source="autonomous_reflection")


# ─── Telegram Polling ─────────────────────────────────────────────────────────

_last_update_id = 0
_telegram_poll_backoff_until = 0.0
_telegram_401_warned = False


async def poll_messages():
    """Poll Telegram for new messages from James."""
    global _last_update_id, _telegram_poll_backoff_until, _telegram_401_warned

    if time.time() < _telegram_poll_backoff_until:
        return

    token = _primary_bot_token()
    if not token:
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params={"offset": _last_update_id + 1, "timeout": 5},
            )
            if resp.status_code == 401:
                if not _telegram_401_warned:
                    logger.warning(
                        "[COMPANION] Telegram getUpdates 401 — companion bot token invalid or revoked. "
                        "Set ADAM_BOT_TOKEN (preferred) or TELEGRAM_BOT_TOKEN in fpai-fp-index systemd Environment. "
                        "Polling backed off 1 hour."
                    )
                    _telegram_401_warned = True
                _telegram_poll_backoff_until = time.time() + 3600
                return
            if resp.status_code != 200:
                return

            _telegram_401_warned = False
            _telegram_poll_backoff_until = 0.0

            for update in resp.json().get("result", []):
                _last_update_id = update["update_id"]
                msg = update.get("message", {})
                text = msg.get("text", "")
                chat_id = str(msg.get("chat", {}).get("id", ""))

                if text and chat_id == _chat_id():
                    logger.info(f"[COMPANION] James: {text[:50]}...")
                    await handle_incoming_message(text, chat_id)
    except Exception as e:
        logger.debug(f"[COMPANION] Poll error: {e}")


# ─── Main Loop ────────────────────────────────────────────────────────────────

async def run_companion_loop():
    """
    The main brain loop. Runs forever.
    - Polls for messages every 3 seconds
    - Persistent outreach: checks every 60s if it should retry
    - Autonomous reflection every 2 hours
    """
    logger.info("[COMPANION] Central brain starting")
    _ensure_dirs()

    brain_log("system", "Central brain started", {"version": "3.1"})

    PERSISTENCE_CHECK = 0  # DISABLED — proactive outreach was sending AI scanner noise, not engine-relevant signals
    REFLECTION_INTERVAL = 0  # DISABLED — was calling Claude every 2h with zero downstream value
    POLL_INTERVAL = 3

    now_ts = datetime.now(timezone.utc).timestamp()
    last_persistence_check = now_ts
    last_reflection = now_ts

    # No startup messages. Adam is quiet until spoken to or a booking comes in.
    logger.info("[COMPANION] Adam listening. Will speak when James messages or a booking arrives.")

    while True:
        try:
            await poll_messages()

            # Proactive outreach and reflection DISABLED.
            # Adam only speaks when:
            #   1. James messages him (poll_messages handles this)
            #   2. A booking inquiry comes in (notify endpoint handles this)
            #   3. A guest responds to follow-up (future)
            # No more scanner noise, AI frontier signals, or autonomous check-ins.

        except Exception as e:
            logger.warning(f"[COMPANION] Loop error: {e}")

        await asyncio.sleep(POLL_INTERVAL)

"""
CHIEF OF STAFF - DAILY BRIEFING
================================

The heartbeat. Runs every morning. Sends Sunheart a compressed,
actionable briefing via Telegram before he has to think about it.

Format (from Birth Document):
1. TOP 3 PRIORITIES today
2. DECISIONS PENDING (yes/no, max 2)
3. WHAT MOVED yesterday
4. ONE ALERT if needed

Pulls context from Mem0 and syncs results to the Shared Brain so all
OpenClaw instances stay aware of the briefing state.

Usage:
    python daily_briefing.py              # Send briefing now
    python daily_briefing.py --dry-run    # Print without sending

Deployed on: Secondary server (162.0.208.88)
Cron: 0 7 * * * cd /opt/fpai/chief-of-staff && python3 daily_briefing.py
"""

import os
import sys
import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

import httpx

# ============================================================================
# CONFIGURATION
# ============================================================================

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    "8506941691:AAGzFg0FUL1fVTDdNh7cFGEhfvGN2stVw1w"
)
SUNHEART_CHAT_ID = os.getenv("SUNHEART_CHAT_ID", "1759822075")

MEM0_API_KEY = os.getenv(
    "MEM0_API_KEY",
    "m0-e6AZpFLmM3gu7W2IYIJ8LL1UTGiOl9nwVZ4OWFFo"
)
MEM0_BASE_URL = "https://api.mem0.ai/v1"

SHARED_BRAIN_URL = os.getenv("SHARED_BRAIN_URL", "http://162.0.208.88:8770")

# Revenue sequence awareness
REVENUE_STAGES = {
    "T1": "AI Executive Suite subscriptions ($2,500-5,000/mo)",
    "T2": "Zen Village retreats (90 days out)",
    "T3": "Revenue-Share Financing (180 days out)",
    "T4": "CORA Credits (Year 2+)",
}
CURRENT_STAGE = "T1"

# ============================================================================
# MEM0 CONTEXT
# ============================================================================

async def search_mem0(query: str, user_id: str, limit: int = 3) -> list:
    """Search Mem0 for relevant context."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{MEM0_BASE_URL}/memories/search/",
                headers={
                    "Authorization": f"Token {MEM0_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"query": query, "user_id": user_id, "limit": limit},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Mem0 search failed: {e}")
    return []


async def store_mem0(content: str, user_id: str, metadata: dict = None):
    """Store a memory in Mem0."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(
                f"{MEM0_BASE_URL}/memories/",
                headers={
                    "Authorization": f"Token {MEM0_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "messages": [{"role": "user", "content": content}],
                    "user_id": user_id,
                    "metadata": metadata or {},
                },
            )
    except Exception as e:
        print(f"Mem0 store failed: {e}")


# ============================================================================
# BRIEFING GENERATION
# ============================================================================

async def get_priorities() -> list[str]:
    """Get top 3 priorities from Mem0 context."""
    memories = await search_mem0(
        "current priority bottleneck next action revenue",
        "aria_learnings",
        limit=5,
    )

    priorities = []
    seen = set()

    for mem in memories:
        text = mem.get("memory", "")
        importance = mem.get("metadata", {}).get("importance", "")
        if importance != "critical":
            continue

        if ("bottleneck" in text.lower() or "unfilled" in text.lower()) and "hire" not in seen:
            priorities.append("Hire first apprentice (FP_OPERATIONS_ASSISTANT_TASKS.md ready)")
            seen.add("hire")
        elif ("revenue sequence" in text.lower() or "T1 NOW" in text) and "revenue" not in seen:
            priorities.append(f"Revenue: {REVENUE_STAGES[CURRENT_STAGE]}")
            seen.add("revenue")
        elif "fullpotential.com/call" in text.lower() and "product" not in seen:
            priorities.append("Wire email follow-up for fullpotential.com/call registrants")
            seen.add("product")
        elif ("9 layer" in text.lower() or "build order" in text.lower()) and "build" not in seen:
            priorities.append("Deploy Mem0 as persistent memory across all agents")
            seen.add("build")

        if len(priorities) >= 3:
            break

    defaults = [
        f"Revenue: {REVENUE_STAGES[CURRENT_STAGE]}",
        "Hire first apprentice from pool",
        "Run one Full Potential consultation (paid)",
    ]
    for d in defaults:
        if len(priorities) >= 3:
            break
        if not any(d[:20] in p for p in priorities):
            priorities.append(d)

    return priorities[:3]


async def get_decisions() -> list[str]:
    """Get pending decisions (yes/no format)."""
    decisions = []

    # Check for unfilled roles
    memories = await search_mem0("unfilled hire apprentice", "aria_learnings", limit=3)
    for mem in memories:
        if "unfilled" in mem.get("memory", "").lower():
            decisions.append(
                "Post apprentice role to recruitment portal? (yes/no)"
            )
            break

    # Check product state
    memories = await search_mem0("fullpotential.com/call email", "aria_learnings", limit=3)
    for mem in memories:
        if "email" in mem.get("memory", "").lower() and "missing" in mem.get("memory", "").lower():
            decisions.append(
                "Set up Kit + Zapier for call email reminders? (yes/no)"
            )
            break

    if not decisions:
        decisions.append("Schedule first AI Executive Suite consultation this week? (yes/no)")

    return decisions[:2]


async def get_what_moved() -> str:
    """Get what moved since last briefing."""
    memories = await search_mem0(
        "session summary completed March 2026",
        "aria_conversations",
        limit=2,
    )

    if memories:
        latest = memories[0].get("memory", "")
        if latest:
            # Compress to one line
            if len(latest) > 200:
                return latest[:200] + "..."
            return latest

    return "No logged activity since last briefing."


async def get_alert() -> Optional[str]:
    """Get one alert if anything needs immediate attention."""
    # Check for system patterns (consciousness cycles often log issues)
    memories = await search_mem0(
        "broken capability health degraded",
        "aria_patterns",
        limit=1,
    )

    if memories:
        mem = memories[0]
        text = mem.get("memory", "")
        if "broken" in text.lower() or "degraded" in text.lower():
            return "System health degraded — ANTHROPIC_API_KEY not set on servers"

    return None


async def generate_briefing() -> str:
    """Generate the full daily briefing."""
    now = datetime.now()
    day_name = now.strftime("%A, %B %d")

    priorities = await get_priorities()
    decisions = await get_decisions()
    what_moved = await get_what_moved()
    alert = await get_alert()

    lines = []
    lines.append(f"☀️ {day_name}\n")

    # TOP 3 PRIORITIES
    lines.append("📌 PRIORITIES")
    for i, p in enumerate(priorities, 1):
        lines.append(f"  {i}. {p}")
    lines.append("")

    # DECISIONS PENDING
    lines.append("⚡ DECISIONS")
    for d in decisions:
        lines.append(f"  → {d}")
    lines.append("")

    # WHAT MOVED
    lines.append("✅ WHAT MOVED")
    lines.append(f"  {what_moved}")
    lines.append("")

    # ALERT
    if alert:
        lines.append(f"🔴 ALERT: {alert}")
        lines.append("")

    # Revenue stage reminder
    lines.append(f"📊 Stage: {CURRENT_STAGE} — {REVENUE_STAGES[CURRENT_STAGE]}")
    lines.append("")
    lines.append("Reply with any priority number to focus on it.")

    return "\n".join(lines)


# ============================================================================
# TELEGRAM DELIVERY
# ============================================================================

async def send_telegram(message: str, chat_id: str = SUNHEART_CHAT_ID):
    """Send message via Telegram."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                },
            )
            if resp.status_code == 200:
                print(f"✅ Briefing sent to {chat_id}")
                return True
            else:
                print(f"❌ Telegram error: {resp.status_code} - {resp.text}")
                return False
    except Exception as e:
        print(f"❌ Send failed: {e}")
        return False


# ============================================================================
# SHARED BRAIN INTEGRATION
# ============================================================================

async def sync_to_shared_brain(briefing: str, success: bool):
    """Store briefing results in the Shared Brain so all OpenClaw instances know."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{SHARED_BRAIN_URL}/memory/store",
                json={
                    "content": (
                        f"Daily briefing {'sent' if success else 'FAILED'} "
                        f"on {datetime.now().strftime('%Y-%m-%d %H:%M')}. "
                        f"Stage: {CURRENT_STAGE}."
                    ),
                    "source": "chief-of-staff",
                    "tags": ["briefing", "daily", CURRENT_STAGE],
                },
            )
            if success:
                await client.post(
                    f"{SHARED_BRAIN_URL}/message/send",
                    json={
                        "from_instance": "chief-of-staff",
                        "to_instance": "server",
                        "subject": "Daily Briefing Delivered",
                        "body": briefing[:500],
                        "priority": "normal",
                    },
                )
    except Exception as e:
        print(f"⚠️  Shared Brain sync failed (non-fatal): {e}")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    dry_run = "--dry-run" in sys.argv

    print("🧠 Generating Chief of Staff briefing...")
    briefing = await generate_briefing()

    if dry_run:
        print("\n--- DRY RUN ---\n")
        print(briefing)
        print("\n--- END ---")
        return

    print("📨 Sending via Telegram...")
    sent = await send_telegram(briefing)

    if sent:
        await store_mem0(
            f"Daily briefing sent {datetime.now().isoformat()}. "
            f"Priorities delivered to Sunheart via Telegram.",
            "aria_conversations",
            {"category": "briefing", "importance": "medium"},
        )
        await sync_to_shared_brain(briefing, success=True)
        print("✅ Briefing sent and logged to Mem0 + Shared Brain")
    else:
        await sync_to_shared_brain(briefing, success=False)
        print("❌ Briefing failed to send")


if __name__ == "__main__":
    asyncio.run(main())

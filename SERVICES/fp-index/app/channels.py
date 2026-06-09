"""
Output Channels — The Voice
============================

The scanner is the ears. The signal router is the brain.
This module is the voice — delivering signals to humans where they are.

Channels:
  - Telegram: Instant alerts on your phone with priority formatting
  - Notion: Structured database entries for browsing/filtering/tracking
  - Email: Already exists via budget.py send_action_alert

All channels are optional — configure via env vars or runtime API.
If a channel isn't configured, it's silently skipped.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger("fp_index.channels")

# ─── Configuration (env vars or runtime) ──────────────────────────────────────

_telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
_telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
_notion_token: str = os.getenv("NOTION_API_TOKEN", "")
_notion_database_id: str = os.getenv("NOTION_SIGNALS_DB_ID", "")

# Stats
_tg_sent: int = 0
_tg_failed: int = 0
_notion_sent: int = 0
_notion_failed: int = 0


def configure_telegram(bot_token: str, chat_id: str):
    global _telegram_bot_token, _telegram_chat_id
    _telegram_bot_token = bot_token
    _telegram_chat_id = chat_id
    logger.info(f"[CHANNELS] Telegram configured (chat_id: {chat_id})")


def configure_notion(token: str, database_id: str):
    global _notion_token, _notion_database_id
    _notion_token = token
    _notion_database_id = database_id
    logger.info(f"[CHANNELS] Notion configured (db: {database_id[:8]}...)")


def get_channel_status() -> dict:
    return {
        "telegram": {
            "configured": bool(_telegram_bot_token and _telegram_chat_id),
            "sent": _tg_sent,
            "failed": _tg_failed,
        },
        "notion": {
            "configured": bool(_notion_token and _notion_database_id),
            "sent": _notion_sent,
            "failed": _notion_failed,
        },
    }


# ─── Priority formatting ─────────────────────────────────────────────────────

PRIORITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🟢",
}

SIGNAL_TYPE_EMOJI = {
    "model_drop": "🚀",
    "tool_release": "🔧",
    "research_paper": "📄",
    "benchmark_result": "📊",
    "framework_update": "📦",
    "market_shift": "📈",
    "security_incident": "🛡️",
    "pricing_change": "💰",
    "community_trend": "💬",
    "infrastructure": "🏗️",
}


# ─── TELEGRAM ─────────────────────────────────────────────────────────────────

async def send_telegram(
    signal_type: str,
    title: str,
    summary: str,
    impact_score: float,
    priority: str,
    source: str = "",
    source_url: str = "",
    suggested_actions: list[str] = None,
    signal_id: str = "",
) -> dict:
    """Send a formatted signal alert to Telegram."""
    global _tg_sent, _tg_failed

    if not _telegram_bot_token or not _telegram_chat_id:
        return {"sent": False, "reason": "telegram not configured"}

    type_emoji = SIGNAL_TYPE_EMOJI.get(signal_type, "📡")
    prio_emoji = PRIORITY_EMOJI.get(priority, "⚪")

    # Build the message
    lines = [
        f"{prio_emoji} *{priority.upper()}* | {type_emoji} {signal_type.replace('_', ' ').title()}",
        "",
        f"*{_escape_md(title)}*",
        "",
        f"_{_escape_md(summary[:300])}_",
        "",
        f"Impact: {'█' * int(impact_score * 10)}{'░' * (10 - int(impact_score * 10))} {impact_score:.0%}",
    ]

    if source:
        lines.append(f"Source: `{source}`")

    if source_url:
        lines.append(f"[View source]({source_url})")

    if suggested_actions:
        lines.append("")
        lines.append("*Suggested actions:*")
        for action in suggested_actions[:3]:
            lines.append(f"  • {_escape_md(action)}")

    message = "\n".join(lines)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{_telegram_bot_token}/sendMessage",
                json={
                    "chat_id": _telegram_chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
            )
            if resp.status_code == 200:
                _tg_sent += 1
                return {"sent": True, "channel": "telegram"}
            else:
                _tg_failed += 1
                error = resp.text[:200]
                logger.warning(f"[TELEGRAM] Send failed: {error}")
                return {"sent": False, "error": error}
    except Exception as e:
        _tg_failed += 1
        logger.warning(f"[TELEGRAM] Exception: {e}")
        return {"sent": False, "error": str(e)}


def _escape_md(text: str) -> str:
    """Escape Markdown special chars for Telegram."""
    for ch in ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]:
        text = text.replace(ch, f"\\{ch}")
    return text


# ─── NOTION ───────────────────────────────────────────────────────────────────

async def send_notion(
    signal_type: str,
    title: str,
    summary: str,
    impact_score: float,
    priority: str,
    source: str = "",
    source_url: str = "",
    suggested_actions: list[str] = None,
    signal_id: str = "",
    domains: list[str] = None,
) -> dict:
    """Create a page in a Notion database for this signal."""
    global _notion_sent, _notion_failed

    if not _notion_token or not _notion_database_id:
        return {"sent": False, "reason": "notion not configured"}

    domains = domains or []
    suggested_actions = suggested_actions or []

    properties = {
        "Title": {"title": [{"text": {"content": title[:200]}}]},
        "Signal Type": {"select": {"name": signal_type.replace("_", " ").title()}},
        "Priority": {"select": {"name": priority.title()}},
        "Impact Score": {"number": round(impact_score, 2)},
        "Source": {"rich_text": [{"text": {"content": source[:100]}}]},
        "Status": {"select": {"name": "New"}},
    }

    if source_url:
        properties["Source URL"] = {"url": source_url}

    if domains:
        properties["Domains"] = {
            "multi_select": [{"name": d[:50]} for d in domains[:5]]
        }

    children = []
    if summary:
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": summary[:2000]}}]
            }
        })

    if suggested_actions:
        children.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"text": {"content": "Suggested Actions"}}]
            }
        })
        for action in suggested_actions:
            children.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"text": {"content": action}}],
                    "checked": False,
                }
            })

    payload = {
        "parent": {"database_id": _notion_database_id},
        "properties": properties,
    }
    if children:
        payload["children"] = children

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.notion.com/v1/pages",
                json=payload,
                headers={
                    "Authorization": f"Bearer {_notion_token}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 200:
                _notion_sent += 1
                page_id = resp.json().get("id", "")
                return {"sent": True, "channel": "notion", "page_id": page_id}
            else:
                _notion_failed += 1
                error = resp.text[:200]
                logger.warning(f"[NOTION] Create failed: {error}")
                return {"sent": False, "error": error}
    except Exception as e:
        _notion_failed += 1
        logger.warning(f"[NOTION] Exception: {e}")
        return {"sent": False, "error": str(e)}


# ─── BROADCAST ────────────────────────────────────────────────────────────────

async def broadcast_signal(
    signal_type: str,
    title: str,
    summary: str,
    impact_score: float,
    priority: str,
    source: str = "",
    source_url: str = "",
    suggested_actions: list[str] = None,
    signal_id: str = "",
    domains: list[str] = None,
) -> dict:
    """Send a signal to ALL configured channels. Returns results per channel."""

    results = {}

    # Telegram
    tg = await send_telegram(
        signal_type=signal_type, title=title, summary=summary,
        impact_score=impact_score, priority=priority,
        source=source, source_url=source_url,
        suggested_actions=suggested_actions, signal_id=signal_id,
    )
    results["telegram"] = tg

    # Notion
    notion = await send_notion(
        signal_type=signal_type, title=title, summary=summary,
        impact_score=impact_score, priority=priority,
        source=source, source_url=source_url,
        suggested_actions=suggested_actions, signal_id=signal_id,
        domains=domains,
    )
    results["notion"] = notion

    sent_count = sum(1 for r in results.values() if r.get("sent"))
    if sent_count > 0:
        logger.info(f"[BROADCAST] '{title[:50]}' → {sent_count} channels")

    return results

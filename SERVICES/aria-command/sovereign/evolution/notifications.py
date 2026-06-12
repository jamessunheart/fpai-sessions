#!/usr/bin/env python3
"""
ARIA EVOLUTION NOTIFICATIONS
=============================

Automatic Telegram notifications for evolution events:
- High-severity pattern detected
- Improvement proposed (medium+ impact)
- Change applied successfully
- Rollback triggered
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import httpx

logger = logging.getLogger("aria.evolution.notifications")

# ============================================================================
# CONFIGURATION
# ============================================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
SUNHEART_CHAT_ID = os.getenv("SUNHEART_CHAT_ID", "1759822075")

# Rate limiting
_last_notification_time: Dict[str, datetime] = {}
MIN_NOTIFICATION_INTERVAL = timedelta(minutes=5)  # Per notification type


# ============================================================================
# NOTIFICATION TYPES
# ============================================================================

@dataclass
class EvolutionNotification:
    """An evolution notification to send."""
    type: str  # pattern, proposal, applied, rollback
    title: str
    message: str
    severity: str = "info"  # info, warning, critical
    data: Optional[Dict] = None


# ============================================================================
# RATE LIMITING
# ============================================================================

def _can_send_notification(notification_type: str) -> bool:
    """Check if we can send this notification type (rate limiting)."""
    global _last_notification_time
    
    now = datetime.now()
    last_time = _last_notification_time.get(notification_type)
    
    if last_time and now - last_time < MIN_NOTIFICATION_INTERVAL:
        return False
    
    return True


def _mark_notification_sent(notification_type: str):
    """Mark that we sent a notification of this type."""
    global _last_notification_time
    _last_notification_time[notification_type] = datetime.now()


# ============================================================================
# TELEGRAM SENDING
# ============================================================================

async def _send_telegram_message(text: str, chat_id: str = SUNHEART_CHAT_ID) -> bool:
    """Send a message via Telegram."""
    if not TELEGRAM_TOKEN:
        logger.warning("No Telegram token configured")
        return False
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{TELEGRAM_API}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown"
                }
            )
            
            if response.status_code == 200:
                return True
            else:
                # Try without markdown if parsing fails
                response = await client.post(
                    f"{TELEGRAM_API}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text
                    }
                )
                return response.status_code == 200
                
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        return False


# ============================================================================
# NOTIFICATION FORMATTERS
# ============================================================================

def _format_pattern_notification(patterns: List[Dict]) -> str:
    """Format a pattern detection notification."""
    high_severity = [p for p in patterns if p.get('severity') == 'high']
    
    if not high_severity:
        return ""
    
    lines = ["🔍 **Pattern Detected**\n"]
    
    for p in high_severity[:3]:
        detector = p.get('detector', 'unknown')
        problem = p.get('problem_description', '')[:100]
        fix = p.get('suggested_fix', '')[:80]
        
        lines.append(f"**{detector}**")
        lines.append(f"Problem: {problem}")
        if fix:
            lines.append(f"Fix: {fix}")
        lines.append("")
    
    lines.append("Use `/evolution analyze` for full analysis.")
    
    return "\n".join(lines)


def _format_proposal_notification(proposal: Dict) -> str:
    """Format a proposal notification."""
    category = proposal.get('category', 'unknown')
    problem = proposal.get('problem', '')[:100]
    solution = proposal.get('solution', '')[:100]
    confidence = proposal.get('confidence', 0) * 100
    impact = proposal.get('expected_impact', 'unknown')
    risk = proposal.get('risk_level', 'unknown')
    proposal_id = proposal.get('id', 'N/A')
    
    impact_emoji = {"high": "🔥", "medium": "📈", "low": "📊"}.get(impact, "📊")
    risk_emoji = {"high": "⚠️", "medium": "⚡", "low": "✅"}.get(risk, "✅")
    
    return f"""💡 **Improvement Proposed**

**Category:** {category}
**Problem:** {problem}
**Solution:** {solution}

{impact_emoji} Impact: {impact}
{risk_emoji} Risk: {risk}
🎯 Confidence: {confidence:.0f}%

Proposal ID: #{proposal_id}
Use `/approve {proposal_id}` to approve."""


def _format_applied_notification(change: Dict) -> str:
    """Format a change applied notification."""
    change_id = change.get('id', 'N/A')
    category = change.get('category', change.get('change_type', 'unknown'))
    problem = change.get('problem', change.get('reason', ''))[:80]
    solution = change.get('solution', '')[:80]
    confidence = change.get('confidence', 0) * 100
    risk = change.get('risk_level', 'low')
    target = change.get('target_file', 'N/A')
    
    risk_emoji = {"high": "⚠️", "medium": "⚡", "low": "✅"}.get(risk, "✅")
    
    return f"""✅ **Improvement Applied**

**Category:** {category}
**Problem:** {problem}
**Solution:** {solution}

🎯 Confidence: {confidence:.0f}%
{risk_emoji} Risk: {risk}
📁 File: `{target}`

Change ID: #{change_id}
Use `/rollback {change_id}` to undo."""


def _format_rollback_notification(change: Dict, reason: str = "") -> str:
    """Format a rollback notification."""
    change_id = change.get('id', 'N/A')
    category = change.get('category', change.get('change_type', 'unknown'))
    target = change.get('target_file', 'N/A')
    
    return f"""↩️ **Change Rolled Back**

**Change ID:** #{change_id}
**Category:** {category}
**File:** `{target}`
**Reason:** {reason or 'Manual rollback'}

The previous version has been restored."""


# ============================================================================
# PUBLIC NOTIFICATION FUNCTIONS
# ============================================================================

async def notify_patterns_detected(patterns: List[Dict]) -> bool:
    """Notify about detected patterns (only high severity)."""
    high_severity = [p for p in patterns if p.get('severity') == 'high']
    
    if not high_severity:
        return False
    
    if not _can_send_notification('pattern'):
        logger.debug("Rate limited pattern notification")
        return False
    
    message = _format_pattern_notification(patterns)
    if message:
        success = await _send_telegram_message(message)
        if success:
            _mark_notification_sent('pattern')
        return success
    
    return False


async def notify_proposal_created(proposal: Dict) -> bool:
    """Notify about a new improvement proposal (medium+ impact)."""
    impact = proposal.get('expected_impact', 'low')
    
    if impact == 'low':
        return False
    
    if not _can_send_notification('proposal'):
        logger.debug("Rate limited proposal notification")
        return False
    
    message = _format_proposal_notification(proposal)
    success = await _send_telegram_message(message)
    if success:
        _mark_notification_sent('proposal')
    return success


async def notify_change_applied(change: Dict) -> bool:
    """Notify when a change is applied."""
    if not _can_send_notification('applied'):
        logger.debug("Rate limited applied notification")
        return False
    
    message = _format_applied_notification(change)
    success = await _send_telegram_message(message)
    if success:
        _mark_notification_sent('applied')
    return success


async def notify_rollback(change: Dict, reason: str = "") -> bool:
    """Notify when a change is rolled back."""
    # Always send rollback notifications (important!)
    message = _format_rollback_notification(change, reason)
    return await _send_telegram_message(message)


async def notify_evolution_error(error: str, context: str = "") -> bool:
    """Notify about an evolution system error."""
    if not _can_send_notification('error'):
        return False
    
    message = f"""⚠️ **Evolution System Error**

**Context:** {context}
**Error:** {error[:200]}

Check logs for details."""
    
    success = await _send_telegram_message(message)
    if success:
        _mark_notification_sent('error')
    return success


# ============================================================================
# CONVENIENCE WRAPPER
# ============================================================================

class EvolutionNotifier:
    """Convenience wrapper for evolution notifications."""
    
    @staticmethod
    async def patterns(patterns: List) -> bool:
        """Notify about detected patterns."""
        pattern_dicts = [p.to_dict() if hasattr(p, 'to_dict') else p for p in patterns]
        return await notify_patterns_detected(pattern_dicts)
    
    @staticmethod
    async def proposal(proposal: Dict) -> bool:
        """Notify about new proposal."""
        return await notify_proposal_created(proposal)
    
    @staticmethod
    async def applied(change: Dict) -> bool:
        """Notify about applied change."""
        return await notify_change_applied(change)
    
    @staticmethod
    async def rollback(change: Dict, reason: str = "") -> bool:
        """Notify about rollback."""
        return await notify_rollback(change, reason)
    
    @staticmethod
    async def error(error: str, context: str = "") -> bool:
        """Notify about error."""
        return await notify_evolution_error(error, context)


# Global notifier instance
notifier = EvolutionNotifier()



#!/usr/bin/env python3
"""
Priority Framework
==================
Determines signal priority based on:
- Source (channel)
- Sender (relationship)
- Content (urgency keywords)
- Timing (business hours, deadlines)
- User state (capacity)

Priority Levels:
P0: Health/safety, major financial - Immediate
P1: Key relationships, today's deadlines - Next report
P2: Important but not urgent - Daily batch
P3: Nice to know - Weekly digest
P4: Noise - Filter out
"""
import re
import logging
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass
from enum import IntEnum

logger = logging.getLogger("signals.priority")


class PriorityLevel(IntEnum):
    P0 = 0  # Immediate
    P1 = 1  # High
    P2 = 2  # Normal
    P3 = 3  # Low
    P4 = 4  # Noise


@dataclass
class PriorityResult:
    """Result of priority calculation."""
    level: PriorityLevel
    reason: str
    action: str  # immediate, next_report, daily_batch, weekly_digest, filter


class PriorityFramework:
    """
    Calculates priority for incoming signals.
    """
    
    def __init__(self):
        # P0 keywords - immediate attention
        self.p0_keywords = [
            "emergency", "urgent", "critical", "help", "danger",
            "hospital", "accident", "security", "hack", "breach"
        ]
        
        # P1 keywords - high priority
        self.p1_keywords = [
            "today", "deadline", "asap", "important", "meeting",
            "call", "payment", "invoice", "contract"
        ]
        
        # P4 keywords - likely noise
        self.noise_keywords = [
            "unsubscribe", "newsletter", "promotion", "sale",
            "discount", "deal", "limited time", "act now"
        ]
        
        # Noise sender patterns
        self.noise_patterns = [
            r"noreply@", r"no-reply@", r"newsletter@",
            r"marketing@", r"promo@", r"info@"
        ]
    
    def calculate(
        self,
        content: str,
        sender: str = "",
        channel: str = "",
        contact_info: Dict = None
    ) -> PriorityResult:
        """
        Calculate priority for a signal.
        
        Args:
            content: Message content
            sender: Sender identifier (email, name)
            channel: Source channel (email, telegram, etc)
            contact_info: Known contact information
        
        Returns:
            PriorityResult with level and action
        """
        content_lower = content.lower()
        sender_lower = sender.lower() if sender else ""
        
        # Check for noise first
        if self._is_noise(content_lower, sender_lower):
            return PriorityResult(
                level=PriorityLevel.P4,
                reason="Appears to be marketing/noise",
                action="filter"
            )
        
        # Check contact priority
        if contact_info:
            rel = contact_info.get("relationship", "")
            if rel == "inner_circle":
                return PriorityResult(
                    level=PriorityLevel.P0,
                    reason="Inner circle contact",
                    action="immediate"
                )
            elif rel == "professional":
                # Start at P1, may be upgraded by content
                base_level = PriorityLevel.P1
            else:
                base_level = PriorityLevel.P2
        else:
            base_level = PriorityLevel.P2
        
        # Check P0 keywords
        if any(kw in content_lower for kw in self.p0_keywords):
            return PriorityResult(
                level=PriorityLevel.P0,
                reason="Urgent keywords detected",
                action="immediate"
            )
        
        # Check P1 keywords
        if any(kw in content_lower for kw in self.p1_keywords):
            return PriorityResult(
                level=PriorityLevel.P1,
                reason="Time-sensitive content",
                action="next_report"
            )
        
        # Check for questions (often need response)
        if "?" in content:
            level = min(base_level, PriorityLevel.P2)
            return PriorityResult(
                level=level,
                reason="Contains question",
                action="daily_batch"
            )
        
        # Default based on contact relationship
        if base_level == PriorityLevel.P1:
            return PriorityResult(
                level=PriorityLevel.P1,
                reason="Professional contact",
                action="next_report"
            )
        elif base_level == PriorityLevel.P2:
            return PriorityResult(
                level=PriorityLevel.P2,
                reason="Standard priority",
                action="daily_batch"
            )
        
        return PriorityResult(
            level=PriorityLevel.P3,
            reason="Low priority",
            action="weekly_digest"
        )
    
    def _is_noise(self, content: str, sender: str) -> bool:
        """Check if signal is likely noise."""
        # Check noise keywords
        if any(kw in content for kw in self.noise_keywords):
            return True
        
        # Check noise sender patterns
        for pattern in self.noise_patterns:
            if re.search(pattern, sender):
                return True
        
        return False
    
    def get_action_for_priority(self, level: PriorityLevel) -> str:
        """Get handling action for priority level."""
        actions = {
            PriorityLevel.P0: "immediate",
            PriorityLevel.P1: "next_report",
            PriorityLevel.P2: "daily_batch",
            PriorityLevel.P3: "weekly_digest",
            PriorityLevel.P4: "filter"
        }
        return actions.get(level, "daily_batch")


# Singleton
_framework: Optional[PriorityFramework] = None

def get_priority_framework() -> PriorityFramework:
    global _framework
    if _framework is None:
        _framework = PriorityFramework()
    return _framework


def calculate_priority(content: str, sender: str = "", channel: str = "", contact_info: Dict = None) -> PriorityResult:
    return get_priority_framework().calculate(content, sender, channel, contact_info)









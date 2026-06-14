"""
Signal Intelligence Engine - Categorizes and prioritizes signals
"""
import logging
from typing import Tuple
from datetime import datetime

from app.models import (
    Signal, SignalCategory, SignalType, SignalAction, SignalRequest
)
from app.config import settings

logger = logging.getLogger(__name__)


class SignalCategorizer:
    """
    Intelligence engine that applies decision filter and categorizes signals

    Decision Filter: Does this serve proof / revenue / clarity / ease
                    for the core offer in 30 days?
    """

    def __init__(self):
        self.decision_keywords = settings.decision_keywords

    def categorize(self, request: SignalRequest) -> Tuple[SignalCategory, SignalAction]:
        """
        Categorize a signal and determine action

        Returns:
            Tuple of (category, action)
        """
        # Apply decision filter first
        passes_filter = self._passes_decision_filter(request)

        if not passes_filter:
            # Doesn't serve 30-day goal - context only
            return SignalCategory.CONTEXT, SignalAction.LOG

        # Passes filter - categorize by urgency
        category = self._determine_urgency(request)
        action = self._determine_action(category)

        return category, action

    def _passes_decision_filter(self, request: SignalRequest) -> bool:
        """
        Apply 30-day decision filter

        Does this serve proof / revenue / clarity / ease for core offer?
        """
        text = f"{request.title} {request.description}".lower()
        data_str = str(request.data).lower()
        combined = f"{text} {data_str}"

        # Check for decision filter keywords
        for keyword in self.decision_keywords:
            if keyword.lower() in combined:
                logger.debug(f"Signal passes filter (keyword: {keyword})")
                return True

        # Check data for specific indicators
        if self._has_business_impact(request.data):
            return True

        logger.debug(f"Signal filtered out: {request.title}")
        return False

    def _has_business_impact(self, data: dict) -> bool:
        """Check if data indicates business impact"""
        indicators = [
            "revenue", "conversion", "booking", "payment",
            "user_count", "error_rate", "uptime"
        ]

        for key in data.keys():
            if any(ind in key.lower() for ind in indicators):
                return True

        return False

    def _determine_urgency(self, request: SignalRequest) -> SignalCategory:
        """
        Determine urgency level

        🔴 URGENT - Revenue blockers, critical failures, strategic decisions
        🟡 IMPORTANT - Non-critical issues, optimizations
        🟢 AUTO - Routine, already handled
        """
        # Use hint if provided and reasonable
        if request.urgency_hint:
            if request.urgency_hint in [SignalCategory.URGENT, SignalCategory.IMPORTANT]:
                return request.urgency_hint

        # Check for urgent indicators
        if self._is_urgent(request):
            return SignalCategory.URGENT

        # Check for auto-handleable
        if self._is_auto_handleable(request):
            return SignalCategory.AUTO

        # Default to important if passes filter
        return SignalCategory.IMPORTANT

    def _is_urgent(self, request: SignalRequest) -> bool:
        """Check if signal is urgent"""
        urgent_keywords = [
            "critical", "down", "failure", "blocked", "urgent",
            "security", "breach", "payment failed", "revenue drop"
        ]

        text = f"{request.title} {request.description}".lower()

        # Keyword check
        if any(keyword in text for keyword in urgent_keywords):
            return True

        # Data-based urgency checks
        data = request.data

        # Revenue drop
        if "revenue_change" in data:
            if data["revenue_change"] < -settings.URGENT_THRESHOLD_REVENUE_DROP:
                return True

        # Error rate
        if "error_rate" in data:
            if data["error_rate"] > settings.URGENT_THRESHOLD_ERROR_RATE:
                return True

        # Uptime
        if "uptime" in data:
            if data["uptime"] < settings.URGENT_THRESHOLD_UPTIME:
                return True

        # User-facing issues
        if data.get("user_facing", False) and request.type == SignalType.ERROR:
            return True

        return False

    def _is_auto_handleable(self, request: SignalRequest) -> bool:
        """Check if signal was auto-handled"""
        auto_keywords = [
            "auto-restarted", "auto-scaled", "self-healed",
            "automatically", "routine", "scheduled"
        ]

        text = f"{request.title} {request.description}".lower()

        if any(keyword in text for keyword in auto_keywords):
            return True

        # Check if data indicates auto-handling
        if request.data.get("auto_handled", False):
            return True

        return False

    def _determine_action(self, category: SignalCategory) -> SignalAction:
        """Determine what action to take based on category"""
        action_map = {
            SignalCategory.URGENT: SignalAction.ALERT,  # Telegram now
            SignalCategory.IMPORTANT: SignalAction.DIGEST,  # Daily digest
            SignalCategory.AUTO: SignalAction.LOG,  # Log only
            SignalCategory.CONTEXT: SignalAction.LOG,  # Log only
        }
        return action_map[category]

    def extract_action_items(self, signal: Signal) -> str:
        """Extract actionable items from signal"""
        if signal.category == SignalCategory.URGENT:
            return self._format_urgent_action(signal)
        elif signal.category == SignalCategory.IMPORTANT:
            return self._format_important_action(signal)
        else:
            return ""

    def _format_urgent_action(self, signal: Signal) -> str:
        """Format urgent action items"""
        actions = []

        # Extract actions from data
        if "suggested_actions" in signal.data:
            actions = signal.data["suggested_actions"]
        else:
            # Generic actions based on type
            if signal.type == SignalType.ERROR:
                actions = [
                    "Check service logs",
                    "Verify configuration",
                    "Consider rolling back recent changes"
                ]
            elif "revenue" in signal.title.lower():
                actions = [
                    "Check booking flow",
                    "Review recent changes",
                    "Verify payment processing"
                ]

        return "\n".join(f"• {action}" for action in actions)

    def _format_important_action(self, signal: Signal) -> str:
        """Format important action items"""
        if signal.type == SignalType.METRIC:
            return "Review and decide on next steps"
        elif signal.type == SignalType.EVENT:
            return "Acknowledge and track"
        else:
            return "Review when convenient"

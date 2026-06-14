"""
Pattern detection for automation suggestions
"""
import asyncio
from collections import Counter, defaultdict
from typing import List
from datetime import datetime, timedelta
import logging

from app.models import Signal, AutomationSuggestion
from app.config import settings

logger = logging.getLogger(__name__)


class PatternDetector:
    """Detect patterns in signals to suggest automations"""

    def __init__(self, signal_history: List[Signal]):
        self.signals = signal_history

    def detect_automation_opportunities(self) -> List[AutomationSuggestion]:
        """
        Find recurring patterns that could be automated

        Returns list of automation suggestions sorted by confidence
        """
        suggestions = []

        # Find recurring signal patterns
        patterns = self._find_recurring_patterns()

        for pattern, occurrences in patterns.items():
            if len(occurrences) >= settings.AUTO_SUGGEST_THRESHOLD:
                suggestion = self._create_suggestion(pattern, occurrences)
                if suggestion:
                    suggestions.append(suggestion)

        # Sort by confidence (frequency)
        suggestions.sort(key=lambda x: x.confidence, reverse=True)

        return suggestions

    def _find_recurring_patterns(self) -> dict:
        """Find recurring signal patterns"""
        # Group signals by similar titles (simple pattern matching)
        patterns = defaultdict(list)

        for signal in self.signals:
            # Normalize title for pattern matching
            pattern_key = self._normalize_for_pattern(signal.title)
            patterns[pattern_key].append(signal)

        # Only keep patterns with multiple occurrences
        return {k: v for k, v in patterns.items() if len(v) > 1}

    def _normalize_for_pattern(self, title: str) -> str:
        """
        Normalize title for pattern matching

        Examples:
          "Service X restarted" -> "service restarted"
          "Low memory on server-1" -> "low memory on server"
        """
        title_lower = title.lower()

        # Remove specific identifiers
        replacements = [
            (r'\d+', 'N'),  # Numbers
            (r'server-\w+', 'server'),
            (r'pod-\w+', 'pod'),
            (r'instance-\w+', 'instance'),
        ]

        import re
        for pattern, replacement in replacements:
            title_lower = re.sub(pattern, replacement, title_lower)

        # Keep only key words
        words = title_lower.split()
        key_words = [w for w in words if len(w) > 3]  # Filter short words

        return ' '.join(key_words[:5])  # Keep first 5 significant words

    def _create_suggestion(
        self, pattern: str, occurrences: List[Signal]
    ) -> AutomationSuggestion:
        """Create an automation suggestion from a pattern"""
        frequency = len(occurrences)
        confidence = min(frequency / 10.0, 1.0)  # Cap at 100%

        # Analyze what happened
        auto_handled_count = sum(1 for s in occurrences if s.category.value == "auto")

        # Generate suggestion text
        suggestion_text = self._generate_suggestion_text(
            pattern, frequency, auto_handled_count
        )

        return AutomationSuggestion(
            pattern=pattern,
            frequency=frequency,
            suggestion=suggestion_text,
            confidence=confidence,
            signals=[s.signal_id for s in occurrences[:10]]  # Keep refs to first 10
        )

    def _generate_suggestion_text(
        self, pattern: str, frequency: int, auto_handled: int
    ) -> str:
        """Generate suggestion text based on pattern analysis"""
        if auto_handled > 0:
            return (
                f"'{pattern}' occurred {frequency} times "
                f"({auto_handled} auto-handled). "
                f"Consider making this fully automatic."
            )
        else:
            return (
                f"'{pattern}' occurred {frequency} times recently. "
                f"Could this be automated?"
            )

    def detect_trends(self, hours: int = 24) -> dict:
        """Detect trends in signals over time"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_signals = [s for s in self.signals if s.timestamp >= cutoff]

        # Count by category
        category_counts = Counter(s.category.value for s in recent_signals)

        # Count by source
        source_counts = Counter(s.source for s in recent_signals)

        # Calculate rates
        hourly_rate = len(recent_signals) / hours if hours > 0 else 0

        return {
            "period_hours": hours,
            "total_signals": len(recent_signals),
            "hourly_rate": round(hourly_rate, 2),
            "by_category": dict(category_counts),
            "by_source": dict(source_counts),
            "top_sources": source_counts.most_common(5),
        }

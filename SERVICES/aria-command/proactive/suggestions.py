#!/usr/bin/env python3
"""
ARIA COMMAND CENTER - PROACTIVE SUGGESTIONS
============================================

Detect patterns and suggest improvements:
- Code optimizations
- Automation opportunities
- Security issues
- Performance improvements
"""

import os
import re
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger("aria.suggestions")


class SuggestionCategory(str, Enum):
    AUTOMATION = "automation"      # Repeated manual tasks
    OPTIMIZATION = "optimization"  # Performance improvements
    SECURITY = "security"          # Security issues
    COST = "cost"                  # Cost savings
    QUALITY = "quality"            # Code quality


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Suggestion:
    """A proactive suggestion."""
    id: str
    category: SuggestionCategory
    priority: Priority
    title: str
    description: str
    action: Optional[str] = None  # Suggested command/action
    impact: Optional[str] = None  # Expected impact
    effort: Optional[str] = None  # Estimated effort
    created_at: datetime = field(default_factory=datetime.now)
    
    def format_telegram(self) -> str:
        """Format for Telegram."""
        emoji = {
            "automation": "🔄",
            "optimization": "⚡",
            "security": "🔒",
            "cost": "💰",
            "quality": "✨"
        }[self.category.value]
        
        priority_indicator = {"low": "", "medium": "📌", "high": "⚠️", "urgent": "🚨"}[self.priority.value]
        
        msg = f"{emoji} {priority_indicator} **{self.title}**\n\n"
        msg += f"{self.description}\n"
        
        if self.impact:
            msg += f"\n📈 *Impact:* {self.impact}"
        if self.effort:
            msg += f"\n⏱️ *Effort:* {self.effort}"
        if self.action:
            msg += f"\n\n*Suggested action:*\n`{self.action}`"
        
        return msg


class SuggestionEngine:
    """
    Proactive suggestion engine.
    
    Analyzes patterns and generates improvement suggestions.
    """
    
    def __init__(self):
        self.suggestions: List[Suggestion] = []
        self.dismissed: set = set()
    
    def _generate_id(self, category: str, title: str) -> str:
        """Generate suggestion ID."""
        import hashlib
        return hashlib.md5(f"{category}{title}".encode()).hexdigest()[:8]
    
    def add_suggestion(self, suggestion: Suggestion):
        """Add a new suggestion."""
        # Don't add if dismissed
        if suggestion.id in self.dismissed:
            return
        
        # Don't add duplicates
        if any(s.id == suggestion.id for s in self.suggestions):
            return
        
        self.suggestions.append(suggestion)
        logger.info(f"New suggestion: {suggestion.title}")
    
    def dismiss_suggestion(self, suggestion_id: str):
        """Dismiss a suggestion."""
        self.dismissed.add(suggestion_id)
        self.suggestions = [s for s in self.suggestions if s.id != suggestion_id]
    
    def get_pending_suggestions(self, category: Optional[SuggestionCategory] = None) -> List[Suggestion]:
        """Get pending suggestions."""
        if category:
            return [s for s in self.suggestions if s.category == category]
        return self.suggestions
    
    # ========== ANALYSIS METHODS ==========
    
    async def analyze_repeated_commands(self, command_history: List[Dict]) -> List[Suggestion]:
        """Detect repeated commands that could be automated."""
        suggestions = []
        
        # Count command frequencies
        command_counts = {}
        for entry in command_history:
            cmd = entry.get("command", "")
            # Normalize command (remove variable parts)
            normalized = re.sub(r'\d+', 'N', cmd)
            normalized = re.sub(r'[a-f0-9]{8,}', 'HASH', normalized)
            command_counts[normalized] = command_counts.get(normalized, 0) + 1
        
        # Find frequently repeated commands
        for cmd, count in command_counts.items():
            if count >= 5:  # Repeated 5+ times
                suggestion = Suggestion(
                    id=self._generate_id("automation", cmd),
                    category=SuggestionCategory.AUTOMATION,
                    priority=Priority.MEDIUM,
                    title=f"Automate repeated command",
                    description=f"The command `{cmd[:50]}...` has been run {count} times. Consider automating it.",
                    action=f"/build create a scheduled task for: {cmd}",
                    impact="Save time on repetitive tasks",
                    effort="~10 minutes"
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    async def analyze_code_patterns(self, file_content: str, file_path: str) -> List[Suggestion]:
        """Analyze code for improvement opportunities."""
        suggestions = []
        
        # Check for TODO comments
        todos = re.findall(r'#\s*TODO:?\s*(.+)', file_content)
        if len(todos) > 3:
            suggestion = Suggestion(
                id=self._generate_id("quality", f"todos_{file_path}"),
                category=SuggestionCategory.QUALITY,
                priority=Priority.LOW,
                title=f"Address TODOs in {file_path}",
                description=f"Found {len(todos)} TODO comments:\n" + "\n".join(f"- {t[:50]}" for t in todos[:5]),
                impact="Better code quality",
                effort="Variable"
            )
            suggestions.append(suggestion)
        
        # Check for hardcoded credentials
        credential_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
        ]
        for pattern in credential_patterns:
            if re.search(pattern, file_content, re.IGNORECASE):
                suggestion = Suggestion(
                    id=self._generate_id("security", f"creds_{file_path}"),
                    category=SuggestionCategory.SECURITY,
                    priority=Priority.URGENT,
                    title=f"Hardcoded credentials in {file_path}",
                    description="Found what appears to be hardcoded credentials. Move to environment variables.",
                    action=f"/build move credentials to .env in {file_path}",
                    impact="Improved security",
                    effort="~15 minutes"
                )
                suggestions.append(suggestion)
                break
        
        # Check for missing error handling
        try_count = len(re.findall(r'\btry:', file_content))
        except_count = len(re.findall(r'\bexcept:', file_content))
        if try_count < 2 and file_content.count('await') > 5:
            suggestion = Suggestion(
                id=self._generate_id("quality", f"error_handling_{file_path}"),
                category=SuggestionCategory.QUALITY,
                priority=Priority.MEDIUM,
                title=f"Add error handling in {file_path}",
                description=f"File has {file_content.count('await')} async operations but limited try/except blocks.",
                impact="More resilient code",
                effort="~20 minutes"
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    async def analyze_service_health(self, metrics: Dict) -> List[Suggestion]:
        """Analyze service health metrics for suggestions."""
        suggestions = []
        
        for service, data in metrics.items():
            # Slow response times
            if data.get("response_time_ms", 0) > 1000:
                suggestion = Suggestion(
                    id=self._generate_id("optimization", f"slow_{service}"),
                    category=SuggestionCategory.OPTIMIZATION,
                    priority=Priority.MEDIUM,
                    title=f"Optimize {service} response time",
                    description=f"Service responding in {data['response_time_ms']:.0f}ms. Consider optimization.",
                    action=f"/logs {service} --performance",
                    impact="Faster response times",
                    effort="~30 minutes investigation"
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    async def analyze_cost_opportunities(self, cost_data: Dict) -> List[Suggestion]:
        """Analyze costs for savings opportunities."""
        suggestions = []
        
        # Check for idle expensive resources
        if cost_data.get("gpu_count", 0) > 0 and cost_data.get("gpu_utilization", 100) < 20:
            suggestion = Suggestion(
                id=self._generate_id("cost", "idle_gpus"),
                category=SuggestionCategory.COST,
                priority=Priority.HIGH,
                title="Release idle GPUs",
                description=f"GPU utilization at {cost_data.get('gpu_utilization', 0):.0f}%. Consider releasing unused instances.",
                action="/run secondary 'vastai show instances'",
                impact=f"Save ~${cost_data.get('gpu_daily_cost', 0):.2f}/day",
                effort="~5 minutes"
            )
            suggestions.append(suggestion)
        
        # Check for cost spikes
        if cost_data.get("daily_cost", 0) > cost_data.get("average_daily_cost", 0) * 1.5:
            suggestion = Suggestion(
                id=self._generate_id("cost", "cost_spike"),
                category=SuggestionCategory.COST,
                priority=Priority.HIGH,
                title="Cost spike detected",
                description=f"Today's cost ${cost_data.get('daily_cost', 0):.2f} is 50%+ above average.",
                action="/status costs --breakdown",
                impact="Prevent overspending",
                effort="~10 minutes review"
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    async def analyze_builder_patterns(self, build_history: List[Dict]) -> List[Suggestion]:
        """Analyze build patterns for improvements."""
        suggestions = []
        
        # Check for frequent build failures
        recent_builds = build_history[-20:]
        failures = [b for b in recent_builds if not b.get("success")]
        
        if len(failures) > len(recent_builds) * 0.3:  # >30% failure rate
            suggestion = Suggestion(
                id=self._generate_id("quality", "build_failures"),
                category=SuggestionCategory.QUALITY,
                priority=Priority.HIGH,
                title="High build failure rate",
                description=f"{len(failures)}/{len(recent_builds)} recent builds failed. Review build process.",
                action="/pending",
                impact="More reliable builds",
                effort="~30 minutes review"
            )
            suggestions.append(suggestion)
        
        return suggestions


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_engine: Optional[SuggestionEngine] = None


def get_suggestion_engine() -> SuggestionEngine:
    """Get or create global suggestion engine."""
    global _engine
    if _engine is None:
        _engine = SuggestionEngine()
    return _engine


async def analyze_and_suggest(data: Dict, data_type: str) -> List[Suggestion]:
    """Analyze data and generate suggestions."""
    engine = get_suggestion_engine()
    
    if data_type == "commands":
        return await engine.analyze_repeated_commands(data.get("history", []))
    elif data_type == "code":
        return await engine.analyze_code_patterns(data.get("content", ""), data.get("path", ""))
    elif data_type == "health":
        return await engine.analyze_service_health(data)
    elif data_type == "costs":
        return await engine.analyze_cost_opportunities(data)
    elif data_type == "builds":
        return await engine.analyze_builder_patterns(data.get("history", []))
    
    return []


def get_top_suggestions(limit: int = 5) -> List[Suggestion]:
    """Get top priority suggestions."""
    engine = get_suggestion_engine()
    
    # Sort by priority
    priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    sorted_suggestions = sorted(
        engine.suggestions,
        key=lambda s: priority_order.get(s.priority.value, 4)
    )
    
    return sorted_suggestions[:limit]



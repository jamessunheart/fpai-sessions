"""
Digest and summary generation
"""
from datetime import datetime
from typing import List, Dict, Any
import logging
import httpx

from app.models import Signal, DailyDigest, DigestItem, SignalCategory
from app.intelligence.storage import signal_storage
from app.intelligence.patterns import PatternDetector
from app.config import settings

logger = logging.getLogger(__name__)


class DigestGenerator:
    """Generate daily digests and weekly summaries"""

    async def _fetch_revenue_summary(self) -> Dict[str, Any]:
        """Fetch revenue summary from streasury-bot"""
        try:
            # streasury-bot runs on secondary server (162.0.208.88:8620)
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "http://162.0.208.88:8620/api/revenue/summary?period=24h"
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch revenue summary: {e}")
        return None

    async def _fetch_system_health(self) -> Dict[str, Any]:
        """Fetch system health from proactive monitor"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:8108/status")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch system health: {e}")
        return None

    async def _fetch_cockpit_health(self) -> Dict[str, Any]:
        """Fetch cockpit health from primary server"""
        try:
            # Cockpit runs on primary (198.54.123.234)
            # TODO: Add /cockpit/status/health.json endpoint
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "http://198.54.123.234/cockpit/status/health.json"
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch cockpit health: {e}")
        return None

    async def generate_daily_digest(self) -> DailyDigest:
        """
        Generate daily briefing

        Format:
        - Urgent items (if any)
        - Important items needing attention
        - Auto-handled summary
        - Key metrics
        - Automation suggestions
        """
        # Get signals from last 24 hours
        urgent = await signal_storage.get_urgent()
        important = await signal_storage.get_important(hours=24)
        auto_handled = await signal_storage.get_auto_handled(hours=24)

        # Create digest items
        urgent_items = [self._signal_to_digest_item(s) for s in urgent if not s.user_response]
        important_items = [self._signal_to_digest_item(s) for s in important[:10]]  # Limit to 10

        # Get automation suggestions
        all_signals = list(signal_storage.signal_history)
        pattern_detector = PatternDetector(all_signals)
        auto_suggestions = pattern_detector.detect_automation_opportunities()
        suggestion_texts = [s.suggestion for s in auto_suggestions[:3]]  # Top 3

        # Auto-handled summary
        auto_summary = [
            f"{s.title}" for s in auto_handled[:10]
        ]

        # Fetch external data
        revenue_data = await self._fetch_revenue_summary()
        system_health = await self._fetch_system_health()
        cockpit_health = await self._fetch_cockpit_health()

        # Key metrics (placeholder - would come from actual monitoring)
        key_metrics = {
            "signals_processed": len(all_signals),
            "urgent_alerts": len(urgent),
            "auto_handled": len(auto_handled),
        }

        # Add revenue metrics
        if revenue_data:
            key_metrics["revenue_24h"] = revenue_data.get("total", 0)
            key_metrics["revenue_change_pct"] = revenue_data.get("change_pct", 0)
            key_metrics["revenue_30d"] = revenue_data.get("trailing_30d", 0)
            key_metrics["revenue_count"] = revenue_data.get("count", 0)

        # Add system health metrics
        if system_health:
            services = system_health.get("services", {})
            healthy_count = sum(
                1 for s in services.values() if s.get("status") == "healthy"
            )
            key_metrics["services_healthy"] = healthy_count
            key_metrics["services_total"] = system_health.get("total_services", 0)

        # Add cockpit health metrics (if available)
        if cockpit_health:
            key_metrics["primary_ram_free_gb"] = cockpit_health.get("primary", {}).get("ram_free_gb", 0)
            key_metrics["secondary_ram_free_gb"] = cockpit_health.get("secondary", {}).get("ram_free_gb", 0)

        return DailyDigest(
            urgent_items=urgent_items,
            important_items=important_items,
            auto_handled=auto_summary,
            key_metrics=key_metrics,
            automation_suggestions=suggestion_texts,
        )

    def _signal_to_digest_item(self, signal: Signal) -> DigestItem:
        """Convert signal to digest item"""
        return DigestItem(
            category=signal.category,
            title=signal.title,
            description=signal.description[:200],  # Truncate
            action_needed=self._extract_action(signal),
        )

    def _extract_action(self, signal: Signal) -> str:
        """Extract action needed from signal"""
        if signal.category == SignalCategory.URGENT:
            return "Immediate action required"
        elif signal.category == SignalCategory.IMPORTANT:
            return "Review and decide"
        else:
            return None

    def format_for_telegram(self, digest: DailyDigest) -> str:
        """
        Format daily digest for Telegram

        Returns nicely formatted message
        """
        lines = []

        # Header
        lines.append("☀️ *Daily Briefing*")
        lines.append(f"_{digest.date.strftime('%A, %B %d')}_")
        lines.append("")

        # Urgent items
        if digest.urgent_items:
            lines.append(f"🔴 *URGENT* ({len(digest.urgent_items)})")
            for item in digest.urgent_items:
                lines.append(f"• {item.title}")
            lines.append("")
        else:
            lines.append("🔴 *URGENT* (0)")
            lines.append("_All clear_")
            lines.append("")

        # Important items
        if digest.important_items:
            lines.append(f"🟡 *NEEDS ATTENTION* ({len(digest.important_items)})")
            for i, item in enumerate(digest.important_items[:5], 1):  # Top 5
                lines.append(f"{i}. {item.title}")
            if len(digest.important_items) > 5:
                lines.append(f"   _...and {len(digest.important_items) - 5} more_")
            lines.append("")

        # Auto-handled
        if digest.auto_handled:
            lines.append(f"🟢 *AUTO-HANDLED* ({len(digest.auto_handled)})")
            for item in digest.auto_handled[:3]:  # Top 3
                lines.append(f"• {item}")
            if len(digest.auto_handled) > 3:
                lines.append(f"• _...and {len(digest.auto_handled) - 3} more_")
            lines.append("")

        # Revenue (if available)
        if "revenue_24h" in digest.key_metrics:
            revenue = digest.key_metrics["revenue_24h"]
            change = digest.key_metrics.get("revenue_change_pct", 0)
            count = digest.key_metrics.get("revenue_count", 0)
            revenue_30d = digest.key_metrics.get("revenue_30d", 0)

            change_emoji = "↑" if change > 0 else "↓" if change < 0 else "→"
            lines.append("💰 *REVENUE (Last 24h)*")
            lines.append(f"• ${revenue:,.2f} ({count} transactions)")
            lines.append(f"• Trend: {change_emoji} {abs(change):.1f}% vs yesterday")
            lines.append(f"• Trailing 30d: ${revenue_30d:,.2f}")
            lines.append("")

        # System Health (if available)
        if "services_healthy" in digest.key_metrics:
            healthy = digest.key_metrics["services_healthy"]
            total = digest.key_metrics.get("services_total", 0)
            health_emoji = "✅" if healthy == total else "⚠️"

            lines.append(f"🖥️ *SYSTEM HEALTH* {health_emoji}")
            lines.append(f"• Services: {healthy}/{total} healthy")

            if "primary_ram_free_gb" in digest.key_metrics:
                primary_ram = digest.key_metrics["primary_ram_free_gb"]
                secondary_ram = digest.key_metrics.get("secondary_ram_free_gb", 0)
                lines.append(f"• Primary: {primary_ram:.1f}GB RAM free")
                if secondary_ram > 0:
                    lines.append(f"• Secondary: {secondary_ram:.1f}GB RAM free")
            lines.append("")

        # Other metrics
        other_metrics = {
            k: v for k, v in digest.key_metrics.items()
            if k not in ["revenue_24h", "revenue_change_pct", "revenue_30d", "revenue_count",
                        "services_healthy", "services_total", "primary_ram_free_gb", "secondary_ram_free_gb"]
        }
        if other_metrics:
            lines.append("📊 *OTHER METRICS*")
            for key, value in other_metrics.items():
                key_formatted = key.replace('_', ' ').title()
                lines.append(f"• {key_formatted}: {value}")
            lines.append("")

        # Automation suggestions
        if digest.automation_suggestions:
            lines.append("🤖 *AUTOMATION IDEAS*")
            for suggestion in digest.automation_suggestions:
                lines.append(f"• {suggestion}")

        return "\n".join(lines)

    async def generate_weekly_summary(self) -> str:
        """
        Generate weekly executive summary

        Format:
        - Highlights
        - Key metrics
        - Trends
        - Automation wins
        """
        # Get signals from last 7 days
        all_signals = list(signal_storage.signal_history)
        pattern_detector = PatternDetector(all_signals)
        trends = pattern_detector.detect_trends(hours=24*7)

        lines = []
        lines.append("📊 *Weekly Executive Summary*")
        lines.append("")

        # Highlights
        lines.append("*HIGHLIGHTS*")
        urgent_count = trends['by_category'].get('urgent', 0)
        auto_count = trends['by_category'].get('auto', 0)
        lines.append(f"• Signals processed: {trends['total_signals']}")
        lines.append(f"• Urgent alerts: {urgent_count}")
        lines.append(f"• Auto-handled: {auto_count}")
        lines.append("")

        # Top sources
        if trends['top_sources']:
            lines.append("*TOP SIGNAL SOURCES*")
            for source, count in trends['top_sources']:
                lines.append(f"• {source}: {count} signals")
            lines.append("")

        # Automation
        auto_suggestions = pattern_detector.detect_automation_opportunities()
        if auto_suggestions:
            lines.append("*AUTOMATION OPPORTUNITIES*")
            for suggestion in auto_suggestions[:3]:
                lines.append(f"• {suggestion.suggestion}")

        return "\n".join(lines)

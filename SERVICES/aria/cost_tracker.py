"""
Aria Cost Tracker - Self-Aware Operating Costs
===============================================

Tracks all AI costs in real-time and provides:
- Per-request cost tracking
- Daily/weekly/monthly summaries
- Cost optimization suggestions
- Automatic provider routing based on budget
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

logger = logging.getLogger("aria.costs")

# Cost data persistence
COST_DATA_FILE = Path("/opt/fpai/aria/data/cost_history.json")
COST_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)


class CostTier(str, Enum):
    FREE = "free"           # Local Ollama
    CHEAP = "cheap"         # Together API
    STANDARD = "standard"   # xAI Grok
    PREMIUM = "premium"     # OpenAI/Anthropic


# Provider cost tiers (per 1M tokens)
PROVIDER_COSTS = {
    "ollama": {"input": 0.0, "output": 0.0, "tier": CostTier.FREE},
    "together": {"input": 0.90, "output": 0.90, "tier": CostTier.CHEAP},
    "groq": {"input": 0.05, "output": 0.10, "tier": CostTier.CHEAP},
    "xai": {"input": 2.00, "output": 10.00, "tier": CostTier.STANDARD},
    "openai": {"input": 5.00, "output": 15.00, "tier": CostTier.PREMIUM},
    "anthropic": {"input": 15.00, "output": 75.00, "tier": CostTier.PREMIUM},
    "vertex": {"input": 1.25, "output": 5.00, "tier": CostTier.STANDARD},
}

# Daily budget settings (configurable)
DEFAULT_DAILY_BUDGET = 5.00  # $5/day default
BUDGET_WARNING_THRESHOLD = 0.8  # Warn at 80% of budget


@dataclass
class CostEntry:
    """Single cost entry."""
    timestamp: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    query_type: str  # simple, trading, creative, etc.
    latency_ms: float


@dataclass
class DailySummary:
    """Daily cost summary."""
    date: str
    total_cost: float
    total_requests: int
    by_provider: Dict[str, float]
    by_query_type: Dict[str, float]
    avg_cost_per_request: float
    free_requests: int
    paid_requests: int


class AriaCostTracker:
    """Tracks and optimizes Aria's operating costs."""
    
    def __init__(self, daily_budget: float = DEFAULT_DAILY_BUDGET):
        self.daily_budget = daily_budget
        self.entries: List[CostEntry] = []
        self.session_start = datetime.now()
        self.session_cost = 0.0
        self.session_requests = 0
        self._load_history()
    
    def _load_history(self):
        """Load cost history from file."""
        if COST_DATA_FILE.exists():
            try:
                with open(COST_DATA_FILE, 'r') as f:
                    data = json.load(f)
                    self.entries = [CostEntry(**e) for e in data.get("entries", [])[-1000:]]  # Keep last 1000
                    logger.info(f"Loaded {len(self.entries)} cost entries")
            except Exception as e:
                logger.error(f"Failed to load cost history: {e}")
                self.entries = []
    
    def _save_history(self):
        """Save cost history to file."""
        try:
            data = {
                "entries": [asdict(e) for e in self.entries[-1000:]],
                "last_updated": datetime.now().isoformat()
            }
            with open(COST_DATA_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cost history: {e}")
    
    def record(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        query_type: str = "general",
        latency_ms: float = 0
    ) -> float:
        """Record a cost entry and return the cost."""
        cost_info = PROVIDER_COSTS.get(provider, {"input": 1.0, "output": 1.0})
        
        cost = (input_tokens / 1_000_000) * cost_info["input"] + \
               (output_tokens / 1_000_000) * cost_info["output"]
        
        entry = CostEntry(
            timestamp=datetime.now().isoformat(),
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            query_type=query_type,
            latency_ms=latency_ms
        )
        
        self.entries.append(entry)
        self.session_cost += cost
        self.session_requests += 1
        
        # Save periodically (every 10 requests)
        if self.session_requests % 10 == 0:
            self._save_history()
        
        # Check budget warning
        daily_cost = self.get_today_cost()
        if daily_cost > self.daily_budget * BUDGET_WARNING_THRESHOLD:
            logger.warning(f"⚠️ Daily cost ${daily_cost:.2f} approaching budget ${self.daily_budget:.2f}")
        
        return cost
    
    def get_today_cost(self) -> float:
        """Get total cost for today."""
        today = datetime.now().date().isoformat()
        return sum(e.cost_usd for e in self.entries if e.timestamp.startswith(today))
    
    def get_today_requests(self) -> int:
        """Get total requests for today."""
        today = datetime.now().date().isoformat()
        return sum(1 for e in self.entries if e.timestamp.startswith(today))
    
    def get_session_stats(self) -> Dict:
        """Get current session statistics."""
        duration = (datetime.now() - self.session_start).total_seconds()
        return {
            "session_duration_minutes": round(duration / 60, 1),
            "session_cost_usd": round(self.session_cost, 6),
            "session_requests": self.session_requests,
            "avg_cost_per_request": round(self.session_cost / max(self.session_requests, 1), 6)
        }
    
    def get_daily_summary(self, date: Optional[str] = None) -> DailySummary:
        """Get summary for a specific day (default: today)."""
        if date is None:
            date = datetime.now().date().isoformat()
        
        day_entries = [e for e in self.entries if e.timestamp.startswith(date)]
        
        by_provider = {}
        by_query_type = {}
        free_requests = 0
        paid_requests = 0
        
        for e in day_entries:
            by_provider[e.provider] = by_provider.get(e.provider, 0) + e.cost_usd
            by_query_type[e.query_type] = by_query_type.get(e.query_type, 0) + e.cost_usd
            
            if e.cost_usd == 0:
                free_requests += 1
            else:
                paid_requests += 1
        
        total_cost = sum(e.cost_usd for e in day_entries)
        total_requests = len(day_entries)
        
        return DailySummary(
            date=date,
            total_cost=round(total_cost, 4),
            total_requests=total_requests,
            by_provider={k: round(v, 4) for k, v in by_provider.items()},
            by_query_type={k: round(v, 4) for k, v in by_query_type.items()},
            avg_cost_per_request=round(total_cost / max(total_requests, 1), 6),
            free_requests=free_requests,
            paid_requests=paid_requests
        )
    
    def get_weekly_summary(self) -> Dict:
        """Get cost summary for the last 7 days."""
        summaries = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).date().isoformat()
            summaries.append(asdict(self.get_daily_summary(date)))
        
        total_cost = sum(s["total_cost"] for s in summaries)
        total_requests = sum(s["total_requests"] for s in summaries)
        
        return {
            "period": "7 days",
            "total_cost_usd": round(total_cost, 2),
            "total_requests": total_requests,
            "avg_daily_cost": round(total_cost / 7, 2),
            "daily_budget": self.daily_budget,
            "budget_utilization": f"{(total_cost / (self.daily_budget * 7)) * 100:.1f}%",
            "days": summaries
        }
    
    def get_optimization_suggestions(self) -> List[Dict]:
        """Analyze usage and suggest cost optimizations."""
        suggestions = []
        
        # Analyze last 100 requests
        recent = self.entries[-100:] if len(self.entries) >= 100 else self.entries
        if not recent:
            return [{"type": "info", "message": "Not enough data yet for optimization suggestions."}]
        
        # Check premium provider usage
        premium_count = sum(1 for e in recent if e.provider in ["openai", "anthropic"])
        premium_cost = sum(e.cost_usd for e in recent if e.provider in ["openai", "anthropic"])
        
        if premium_count > len(recent) * 0.3:
            suggestions.append({
                "type": "high_priority",
                "message": f"Premium providers used {premium_count}/{len(recent)} times (${premium_cost:.2f}). "
                          f"Consider routing more queries to local Ollama (FREE) or Together API ($0.90/1M).",
                "potential_savings": f"Up to ${premium_cost * 0.8:.2f}"
            })
        
        # Check if local Ollama is being used
        ollama_count = sum(1 for e in recent if e.provider == "ollama")
        if ollama_count < len(recent) * 0.5:
            suggestions.append({
                "type": "medium_priority",
                "message": f"Local Ollama (FREE) used only {ollama_count}/{len(recent)} times. "
                          f"More simple queries could use local models.",
                "action": "Lower the character threshold for simple query routing."
            })
        
        # Check average cost per request
        avg_cost = sum(e.cost_usd for e in recent) / len(recent)
        if avg_cost > 0.01:  # More than $0.01 per request
            suggestions.append({
                "type": "info",
                "message": f"Average cost per request: ${avg_cost:.4f}. "
                          f"Target: <$0.005 (using more local models).",
                "current_monthly_estimate": f"${avg_cost * 1000 * 30:.2f}/month at 1000 requests/day"
            })
        
        # Check query type distribution
        query_types = {}
        for e in recent:
            query_types[e.query_type] = query_types.get(e.query_type, 0) + 1
        
        if query_types.get("simple", 0) < len(recent) * 0.3:
            suggestions.append({
                "type": "info",
                "message": "Few queries classified as 'simple'. "
                          "Expanding simple query detection could save costs.",
                "query_distribution": query_types
            })
        
        if not suggestions:
            suggestions.append({
                "type": "success",
                "message": "Cost optimization looking good! Local Ollama is being well-utilized."
            })
        
        return suggestions
    
    def should_use_free_tier(self) -> bool:
        """Check if we should force free tier due to budget constraints."""
        daily_cost = self.get_today_cost()
        return daily_cost >= self.daily_budget * 0.9  # 90% of budget
    
    def get_budget_status(self) -> Dict:
        """Get current budget status."""
        daily_cost = self.get_today_cost()
        remaining = max(0, self.daily_budget - daily_cost)
        
        return {
            "daily_budget_usd": self.daily_budget,
            "spent_today_usd": round(daily_cost, 4),
            "remaining_usd": round(remaining, 4),
            "utilization_percent": round((daily_cost / self.daily_budget) * 100, 1),
            "requests_today": self.get_today_requests(),
            "status": "ok" if daily_cost < self.daily_budget * 0.8 else 
                     "warning" if daily_cost < self.daily_budget else "exceeded",
            "force_free_tier": self.should_use_free_tier()
        }
    
    def format_cost_report(self) -> str:
        """Format a human-readable cost report for Aria to use."""
        budget = self.get_budget_status()
        session = self.get_session_stats()
        daily = self.get_daily_summary()
        suggestions = self.get_optimization_suggestions()
        
        report = f"""📊 **Aria Operating Costs**

**Today ({daily.date})**
• Spent: ${budget['spent_today_usd']:.4f} / ${budget['daily_budget_usd']:.2f} budget
• Requests: {daily.total_requests} ({daily.free_requests} free, {daily.paid_requests} paid)
• Status: {'✅ OK' if budget['status'] == 'ok' else '⚠️ WARNING' if budget['status'] == 'warning' else '🚨 EXCEEDED'}

**By Provider**
"""
        for provider, cost in sorted(daily.by_provider.items(), key=lambda x: -x[1]):
            emoji = "🆓" if cost == 0 else "💰"
            report += f"• {emoji} {provider}: ${cost:.4f}\n"
        
        report += f"""
**Session Stats**
• Duration: {session['session_duration_minutes']} minutes
• Cost: ${session['session_cost_usd']:.4f}
• Avg per request: ${session['avg_cost_per_request']:.6f}

**Optimization Tips**
"""
        for s in suggestions[:2]:  # Top 2 suggestions
            icon = "🔴" if s['type'] == 'high_priority' else "🟡" if s['type'] == 'medium_priority' else "💡"
            report += f"{icon} {s['message']}\n"
        
        return report
    
    def save(self):
        """Force save current data."""
        self._save_history()


# Singleton instance
_cost_tracker: Optional[AriaCostTracker] = None


def get_cost_tracker(daily_budget: float = DEFAULT_DAILY_BUDGET) -> AriaCostTracker:
    """Get or create the cost tracker."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = AriaCostTracker(daily_budget)
        logger.info(f"Cost tracker initialized (budget: ${daily_budget}/day)")
    return _cost_tracker


def record_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    query_type: str = "general",
    latency_ms: float = 0
) -> float:
    """Quick helper to record a cost."""
    tracker = get_cost_tracker()
    return tracker.record(provider, model, input_tokens, output_tokens, query_type, latency_ms)


# Test
if __name__ == "__main__":
    tracker = get_cost_tracker(daily_budget=5.0)
    
    # Simulate some requests
    print("Simulating requests...")
    tracker.record("ollama", "llama3.1:8b", 100, 50, "simple", 500)
    tracker.record("ollama", "llama3.1:8b", 200, 100, "conversation", 800)
    tracker.record("xai", "grok-4", 500, 200, "trading", 2000)
    tracker.record("together", "llama-3.3-70b", 300, 150, "creative", 1500)
    tracker.record("openai", "gpt-5.1", 400, 300, "complex", 1200)
    
    print("\n" + tracker.format_cost_report())
    
    print("\n=== Budget Status ===")
    print(json.dumps(tracker.get_budget_status(), indent=2))
    
    print("\n=== Optimization Suggestions ===")
    for s in tracker.get_optimization_suggestions():
        print(f"- [{s['type']}] {s['message']}")
    
    tracker.save()





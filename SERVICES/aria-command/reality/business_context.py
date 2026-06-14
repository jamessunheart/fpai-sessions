"""
Business Context Engine - Understands business state for decisions.

Aggregates metrics from trading, revenue, costs, and users
to provide context for AI decision-making.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger("aria.reality.business_context")


@dataclass
class TradingContext:
    """Current trading state."""
    total_positions: int = 0
    total_pnl: float = 0.0
    active_signals: int = 0
    market_sentiment: str = "neutral"
    risk_exposure: float = 0.0
    recent_trades: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RevenueContext:
    """Current revenue state."""
    monthly_revenue: float = 0.0
    monthly_costs: float = 0.0
    net_margin: float = 0.0
    active_subscriptions: int = 0
    pending_payments: int = 0


@dataclass
class InfrastructureContext:
    """Current infrastructure state."""
    primary_server_healthy: bool = True
    secondary_server_healthy: bool = True
    total_services: int = 0
    healthy_services: int = 0
    memory_usage_primary: float = 0.0
    memory_usage_secondary: float = 0.0
    monthly_infra_cost: float = 0.0


@dataclass
class ProjectContext:
    """Current project state."""
    active_projects: int = 0
    pending_tasks: int = 0
    completed_today: int = 0
    blockers: List[str] = field(default_factory=list)


@dataclass
class BusinessContext:
    """Complete business context."""
    timestamp: datetime = field(default_factory=datetime.now)
    
    trading: TradingContext = field(default_factory=TradingContext)
    revenue: RevenueContext = field(default_factory=RevenueContext)
    infrastructure: InfrastructureContext = field(default_factory=InfrastructureContext)
    project: ProjectContext = field(default_factory=ProjectContext)
    
    # Derived insights
    overall_health: str = "good"  # "good", "warning", "critical"
    top_priority: str = ""
    recommended_focus: str = ""
    
    def to_summary(self) -> str:
        """Generate a human-readable summary."""
        parts = [
            f"Business Context ({self.timestamp.strftime('%Y-%m-%d %H:%M')})",
            "",
            f"Overall Health: {self.overall_health.upper()}",
            "",
            "Trading:",
            f"  • Positions: {self.trading.total_positions}",
            f"  • PnL: ${self.trading.total_pnl:,.2f}",
            f"  • Sentiment: {self.trading.market_sentiment}",
            "",
            "Revenue:",
            f"  • Monthly: ${self.revenue.monthly_revenue:,.2f}",
            f"  • Costs: ${self.revenue.monthly_costs:,.2f}",
            f"  • Margin: {self.revenue.net_margin:.1%}",
            "",
            "Infrastructure:",
            f"  • Primary: {'✓' if self.infrastructure.primary_server_healthy else '✗'}",
            f"  • Secondary: {'✓' if self.infrastructure.secondary_server_healthy else '✗'}",
            f"  • Services: {self.infrastructure.healthy_services}/{self.infrastructure.total_services}",
            "",
            f"Top Priority: {self.top_priority}" if self.top_priority else "",
            f"Focus: {self.recommended_focus}" if self.recommended_focus else ""
        ]
        
        return "\n".join(filter(None, parts))


class BusinessContextEngine:
    """
    Aggregates business context from multiple sources.
    
    Used by AI to make better decisions based on current business state.
    """
    
    def __init__(self):
        self._cache: Optional[BusinessContext] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)
    
    async def get_context(self, force_refresh: bool = False) -> BusinessContext:
        """
        Get current business context.
        
        Uses caching to avoid repeated API calls.
        """
        if not force_refresh and self._is_cache_valid():
            return self._cache
        
        context = BusinessContext()
        
        # Gather all context in parallel
        await asyncio.gather(
            self._fetch_trading_context(context),
            self._fetch_revenue_context(context),
            self._fetch_infrastructure_context(context),
            self._fetch_project_context(context),
            return_exceptions=True
        )
        
        # Derive insights
        self._derive_insights(context)
        
        # Cache
        self._cache = context
        self._cache_time = datetime.now()
        
        return context
    
    async def _fetch_trading_context(self, context: BusinessContext):
        """Fetch trading context from WhaleTrack."""
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Positions
                response = await client.get("http://198.54.123.234:8601/api/positions")
                if response.status_code == 200:
                    data = response.json()
                    positions = data.get("positions", [])
                    context.trading.total_positions = len(positions)
                    context.trading.total_pnl = sum(p.get("pnl", 0) for p in positions)
                    context.trading.risk_exposure = sum(abs(p.get("size", 0) * p.get("leverage", 1)) for p in positions)
                
                # Signals
                response = await client.get("http://198.54.123.234:8601/api/signals")
                if response.status_code == 200:
                    data = response.json()
                    context.trading.active_signals = len(data.get("signals", []))
                
                # Market
                response = await client.get("http://198.54.123.234:8601/api/market/summary")
                if response.status_code == 200:
                    data = response.json()
                    context.trading.market_sentiment = data.get("sentiment", "neutral")
                    
        except Exception as e:
            logger.error(f"Failed to fetch trading context: {e}")
    
    async def _fetch_revenue_context(self, context: BusinessContext):
        """Fetch revenue context."""
        # Would integrate with revenue tracking system
        # For now, use placeholders
        context.revenue.monthly_revenue = 0
        context.revenue.monthly_costs = 0
        context.revenue.net_margin = 0
        context.revenue.active_subscriptions = 0
    
    async def _fetch_infrastructure_context(self, context: BusinessContext):
        """Fetch infrastructure context."""
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Primary server
                try:
                    response = await client.get("http://198.54.123.234:8601/health")
                    context.infrastructure.primary_server_healthy = response.status_code == 200
                except:
                    context.infrastructure.primary_server_healthy = False
                
                # Secondary server (local)
                try:
                    response = await client.get("http://localhost:8750/health")
                    context.infrastructure.secondary_server_healthy = response.status_code == 200
                except:
                    context.infrastructure.secondary_server_healthy = False
            
            # Memory usage
            try:
                import psutil
                memory = psutil.virtual_memory()
                context.infrastructure.memory_usage_secondary = memory.percent
            except:
                pass
                
        except Exception as e:
            logger.error(f"Failed to fetch infrastructure context: {e}")
    
    async def _fetch_project_context(self, context: BusinessContext):
        """Fetch project context from opportunity queue."""
        try:
            from proactive.opportunity_queue import get_opportunity_queue
            queue = get_opportunity_queue()
            summary = queue.get_summary()
            
            context.project.pending_tasks = summary.get("total_pending", 0)
            context.project.active_projects = summary.get("by_type", {}).get("feature", 0)
        except Exception as e:
            logger.error(f"Failed to fetch project context: {e}")
    
    def _derive_insights(self, context: BusinessContext):
        """Derive high-level insights from context."""
        warnings = []
        
        # Check trading
        if context.trading.total_pnl < -1000:
            warnings.append("significant trading losses")
        if context.trading.risk_exposure > 10000:
            warnings.append("high risk exposure")
        
        # Check infrastructure
        if not context.infrastructure.primary_server_healthy:
            warnings.append("primary server down")
        if not context.infrastructure.secondary_server_healthy:
            warnings.append("secondary server down")
        if context.infrastructure.memory_usage_secondary > 85:
            warnings.append("high memory usage")
        
        # Check revenue
        if context.revenue.monthly_costs > context.revenue.monthly_revenue > 0:
            warnings.append("costs exceed revenue")
        
        # Determine overall health
        if any(w in str(warnings) for w in ["down", "significant"]):
            context.overall_health = "critical"
        elif warnings:
            context.overall_health = "warning"
        else:
            context.overall_health = "good"
        
        # Determine priorities
        if not context.infrastructure.primary_server_healthy:
            context.top_priority = "Restore primary server"
            context.recommended_focus = "Infrastructure stability"
        elif context.trading.total_pnl < -500:
            context.top_priority = "Review trading positions"
            context.recommended_focus = "Risk management"
        elif context.project.pending_tasks > 20:
            context.top_priority = "Clear task backlog"
            context.recommended_focus = "Code quality improvements"
        else:
            context.top_priority = "Continue development"
            context.recommended_focus = "Feature development"
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache or not self._cache_time:
            return False
        return datetime.now() - self._cache_time < self._cache_ttl


# Singleton instance
_engine: Optional[BusinessContextEngine] = None

def get_business_context_engine() -> BusinessContextEngine:
    """Get or create business context engine instance."""
    global _engine
    if _engine is None:
        _engine = BusinessContextEngine()
    return _engine

async def get_business_context(force_refresh: bool = False) -> BusinessContext:
    """Get current business context."""
    engine = get_business_context_engine()
    return await engine.get_context(force_refresh)



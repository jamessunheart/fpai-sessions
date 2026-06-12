"""
ARIA MANIFESTATION TOOLS
========================

Tools for navigating the digital/physical dimensions.

These are Aria's hands in the material world:
- Treasury tracking
- System monitoring
- Trading intelligence
- Builder status
- Revenue tracking
"""

import os
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import httpx
import asyncio

logger = logging.getLogger("aria.manifestation")

# Service endpoints
PRIMARY_SERVER = os.getenv("PRIMARY_SERVER", "198.54.123.234")
SECONDARY_SERVER = os.getenv("SECONDARY_SERVER", "162.0.208.88")

WHALETRACK_MAGNET = f"http://{PRIMARY_SERVER}:8601/api"
NERVE_CENTER = f"http://{PRIMARY_SERVER}:8120"
DATA_SERVICE = f"http://{PRIMARY_SERVER}:8125"
AI_BRAIN = f"http://{SECONDARY_SERVER}:8101"
BUILDER_QUEUE = f"http://{SECONDARY_SERVER}:8101/builder"


@dataclass
class TreasurySnapshot:
    """Current treasury state."""
    timestamp: str
    total_value_usd: float
    positions: List[Dict]
    cash_available: float
    daily_pnl: float
    monthly_pnl: float
    burn_runway_months: float
    risk_flags: List[str]


@dataclass
class SystemHealth:
    """System health summary."""
    timestamp: str
    services_healthy: int
    services_unhealthy: int
    service_details: Dict[str, str]
    memory_percent: float
    disk_percent: float
    alerts: List[str]


@dataclass 
class TradeOpportunity:
    """A trading opportunity from Magnet."""
    symbol: str
    direction: str
    confidence: float
    entry: float
    stop_loss: float
    take_profit: float
    reasoning: str
    time_estimate: Optional[str]


@dataclass
class BuildStatus:
    """Builder queue status."""
    queued: int
    building: int
    completed_today: int
    failed_today: int
    current_task: Optional[str]


class ManifestationTools:
    """
    Aria's tools for navigating the physical/digital dimensions.
    
    These connect visions to actual system capabilities.
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
        logger.info("ManifestationTools initialized")
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    # ==================== TREASURY ====================
    
    async def get_treasury_snapshot(self) -> TreasurySnapshot:
        """
        Get current treasury state.
        
        This is the foundation - the fund must survive.
        """
        try:
            # Try to get from WhaleTrack
            positions = await self._fetch_positions()
            
            # Calculate totals
            total_value = sum(p.get("value_usd", 0) for p in positions)
            cash = next((p.get("value_usd", 0) for p in positions if p.get("symbol") == "USDC"), 0)
            
            # Calculate runway (estimate $10K/month burn)
            monthly_burn = 10000
            runway = total_value / monthly_burn if monthly_burn > 0 else 999
            
            # Risk flags
            risk_flags = []
            if runway < 6:
                risk_flags.append("⚠️ Runway < 6 months")
            if any(p.get("leverage", 0) > 2 for p in positions):
                risk_flags.append("⚠️ High leverage detected")
            
            return TreasurySnapshot(
                timestamp=datetime.utcnow().isoformat(),
                total_value_usd=total_value,
                positions=positions,
                cash_available=cash,
                daily_pnl=0,  # Would need historical data
                monthly_pnl=0,
                burn_runway_months=runway,
                risk_flags=risk_flags
            )
            
        except Exception as e:
            logger.error(f"Treasury fetch error: {e}")
            return TreasurySnapshot(
                timestamp=datetime.utcnow().isoformat(),
                total_value_usd=430000,  # Last known approximate
                positions=[],
                cash_available=0,
                daily_pnl=0,
                monthly_pnl=0,
                burn_runway_months=43,  # Estimate
                risk_flags=["⚠️ Could not fetch live data"]
            )
    
    async def _fetch_positions(self) -> List[Dict]:
        """Fetch positions from trading system."""
        try:
            response = await self.http.get(
                f"{WHALETRACK_MAGNET}/positions",
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get("positions", [])
        except:
            pass
        return []
    
    # ==================== TRADING INTELLIGENCE ====================
    
    async def get_trade_opportunity(self, symbol: str = None) -> Optional[TradeOpportunity]:
        """
        Get current best trade opportunity from Magnet.
        
        Remember: No leverage hunting. The fund must survive.
        """
        try:
            endpoint = f"{WHALETRACK_MAGNET}/signal"
            if symbol:
                endpoint += f"?symbol={symbol}"
            
            response = await self.http.get(endpoint, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                signal = data.get("signal", {})
                
                if signal and signal.get("confidence", 0) > 0.6:
                    return TradeOpportunity(
                        symbol=signal.get("symbol", symbol or "SOL"),
                        direction=signal.get("direction", "WAIT"),
                        confidence=signal.get("confidence", 0),
                        entry=signal.get("entry", 0),
                        stop_loss=signal.get("stop_loss", 0),
                        take_profit=signal.get("take_profit", 0),
                        reasoning=signal.get("reasoning", ""),
                        time_estimate=signal.get("time_to_target")
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Trade signal error: {e}")
            return None
    
    async def get_market_regime(self) -> Dict:
        """Get current market regime from intelligence system."""
        try:
            response = await self.http.get(
                f"{WHALETRACK_MAGNET}/regime",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except:
            pass
        
        return {
            "regime": "unknown",
            "confidence": 0,
            "recommendation": "Unable to determine - proceed with caution"
        }
    
    # ==================== SYSTEM HEALTH ====================
    
    async def get_system_health(self) -> SystemHealth:
        """Get overall system health."""
        service_status = {}
        alerts = []
        
        # Check key services
        services_to_check = [
            (f"http://{PRIMARY_SERVER}:8601/health", "WhaleTrack Magnet"),
            (f"http://{PRIMARY_SERVER}:8120/health", "Nerve Center"),
            (f"http://{SECONDARY_SERVER}:8101/health", "AI Brain"),
            (f"http://{SECONDARY_SERVER}:11434/", "Ollama"),
        ]
        
        healthy = 0
        unhealthy = 0
        
        for url, name in services_to_check:
            try:
                response = await self.http.get(url, timeout=5)
                if response.status_code == 200:
                    service_status[name] = "✅ healthy"
                    healthy += 1
                else:
                    service_status[name] = f"⚠️ status {response.status_code}"
                    unhealthy += 1
                    alerts.append(f"{name} returned {response.status_code}")
            except Exception as e:
                service_status[name] = "❌ unreachable"
                unhealthy += 1
                alerts.append(f"{name} unreachable")
        
        return SystemHealth(
            timestamp=datetime.utcnow().isoformat(),
            services_healthy=healthy,
            services_unhealthy=unhealthy,
            service_details=service_status,
            memory_percent=0,  # Would need system access
            disk_percent=0,
            alerts=alerts
        )
    
    # ==================== BUILDER ====================
    
    async def get_build_status(self) -> BuildStatus:
        """Get builder queue status."""
        try:
            response = await self.http.get(
                f"{AI_BRAIN}/builder/status",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return BuildStatus(
                    queued=data.get("pending", 0),
                    building=data.get("building", 0),
                    completed_today=data.get("completed_today", 0),
                    failed_today=data.get("failed_today", 0),
                    current_task=data.get("current_task")
                )
        except:
            pass
        
        return BuildStatus(
            queued=0,
            building=0,
            completed_today=0,
            failed_today=0,
            current_task=None
        )
    
    # ==================== INTEGRATED STATUS ====================
    
    async def get_full_status(self) -> Dict:
        """
        Get comprehensive status across all dimensions.
        
        This is for the daily brief.
        """
        # Fetch all in parallel
        treasury_task = self.get_treasury_snapshot()
        health_task = self.get_system_health()
        build_task = self.get_build_status()
        regime_task = self.get_market_regime()
        opportunity_task = self.get_trade_opportunity()
        
        treasury, health, build, regime, opportunity = await asyncio.gather(
            treasury_task, health_task, build_task, regime_task, opportunity_task,
            return_exceptions=True
        )
        
        # Build status report
        status = {
            "timestamp": datetime.utcnow().isoformat(),
            "treasury": {
                "total_usd": treasury.total_value_usd if isinstance(treasury, TreasurySnapshot) else 0,
                "runway_months": treasury.burn_runway_months if isinstance(treasury, TreasurySnapshot) else 0,
                "risk_flags": treasury.risk_flags if isinstance(treasury, TreasurySnapshot) else [],
            },
            "system": {
                "healthy": health.services_healthy if isinstance(health, SystemHealth) else 0,
                "unhealthy": health.services_unhealthy if isinstance(health, SystemHealth) else 0,
                "alerts": health.alerts if isinstance(health, SystemHealth) else [],
            },
            "builder": {
                "queued": build.queued if isinstance(build, BuildStatus) else 0,
                "building": build.building if isinstance(build, BuildStatus) else 0,
                "current": build.current_task if isinstance(build, BuildStatus) else None,
            },
            "market": {
                "regime": regime.get("regime") if isinstance(regime, dict) else "unknown",
                "opportunity": {
                    "symbol": opportunity.symbol,
                    "direction": opportunity.direction,
                    "confidence": opportunity.confidence,
                } if isinstance(opportunity, TradeOpportunity) else None,
            }
        }
        
        return status
    
    def format_status_for_telegram(self, status: Dict) -> str:
        """Format status for Telegram message."""
        lines = [
            "**⚡ System Status**",
            f"_{datetime.now().strftime('%H:%M UTC')}_\n",
        ]
        
        # Treasury
        treasury = status.get("treasury", {})
        lines.append("**💰 Treasury:**")
        lines.append(f"• Total: ${treasury.get('total_usd', 0):,.0f}")
        lines.append(f"• Runway: {treasury.get('runway_months', 0):.1f} months")
        if treasury.get("risk_flags"):
            for flag in treasury["risk_flags"]:
                lines.append(f"  {flag}")
        
        # System
        system = status.get("system", {})
        lines.append(f"\n**🖥️ System:**")
        lines.append(f"• Services: {system.get('healthy', 0)} healthy, {system.get('unhealthy', 0)} issues")
        if system.get("alerts"):
            for alert in system["alerts"][:3]:
                lines.append(f"  ⚠️ {alert}")
        
        # Market
        market = status.get("market", {})
        lines.append(f"\n**📊 Market:**")
        lines.append(f"• Regime: {market.get('regime', 'unknown')}")
        opp = market.get("opportunity")
        if opp:
            lines.append(f"• Signal: {opp['symbol']} {opp['direction']} ({opp['confidence']:.0%})")
        
        # Builder
        builder = status.get("builder", {})
        if builder.get("queued") or builder.get("building"):
            lines.append(f"\n**🔧 Builder:**")
            lines.append(f"• Queue: {builder.get('queued', 0)}, Building: {builder.get('building', 0)}")
        
        lines.append("\n_T1 = Revenue or Building Aria_")
        
        return "\n".join(lines)
    
    # ==================== ACTIONS ====================
    
    async def execute_trade(
        self,
        symbol: str,
        direction: str,
        size_usd: float,
        stop_loss: float,
        take_profit: float
    ) -> Dict:
        """
        Execute a trade through the trading system.
        
        CAUTION: This is real money. No leverage hunting.
        """
        # Sanity checks
        if size_usd > 10000:
            return {
                "success": False,
                "error": "Position size > $10K requires manual confirmation"
            }
        
        if direction not in ["LONG", "SHORT"]:
            return {
                "success": False,
                "error": f"Invalid direction: {direction}"
            }
        
        try:
            response = await self.http.post(
                f"{WHALETRACK_MAGNET}/execute",
                json={
                    "symbol": symbol,
                    "direction": direction,
                    "size_usd": size_usd,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "source": "aria_bridge"
                },
                timeout=30
            )
            
            return response.json()
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def queue_build_task(
        self,
        spec_content: str,
        priority: str = "normal"
    ) -> Dict:
        """Queue a build task for the autonomous builder."""
        try:
            response = await self.http.post(
                f"{AI_BRAIN}/builder/queue",
                json={
                    "spec": spec_content,
                    "priority": priority,
                    "source": "aria_bridge"
                },
                timeout=30
            )
            
            return response.json()
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Singleton
_tools: Optional[ManifestationTools] = None


async def get_manifestation_tools() -> ManifestationTools:
    """Get or create manifestation tools instance."""
    global _tools
    if _tools is None:
        _tools = ManifestationTools()
    return _tools



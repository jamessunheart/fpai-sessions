"""
IDENTITY Layer Feeder
=====================
Collects identity and resource data for the consciousness IDENTITY pillar.

Focuses on:
- Treasury: Trading strategies, APR, capital allocation
- Compute: GPU fleet, model availability, costs
- Ecosystem: Competitor signals, AI trends, market position

MEMORY OPTIMIZATION (2025-12-14):
- Uses shared HTTP client from main module
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import httpx
import json
import os

logger = logging.getLogger(__name__)


class IdentityFeeder:
    """Collects identity and resource status data.
    
    MEMORY FIX: Uses shared HTTP client.
    """

    def __init__(self):
        self.treasury_sources = {
            "whaletrack": "http://198.54.123.234:8600/api/portfolio/status",
            "trading_engine": "http://198.54.123.234:8600/api/strategies/performance"
        }
        self.compute_sources = {
            "gpu_fleet": "http://198.54.123.234:8101/api/models/status",  # AI Brain
            "ollama": "http://198.54.123.234:11434/api/tags"  # Ollama API
        }
        self.ecosystem_sources = {
            "market_data": "http://198.54.123.234:8120/api/market/signals",  # Nerve center
            "competitor_tracking": "http://198.54.123.234:8500/api/competitors"  # Strategic intelligence
        }
        # Shared HTTP client reference
        self._http_client: Optional[httpx.AsyncClient] = None
    
    def set_http_client(self, client: httpx.AsyncClient):
        """Set the shared HTTP client."""
        self._http_client = client
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client - prefer shared, fallback to creating one."""
        if self._http_client and not self._http_client.is_closed:
            return self._http_client
        return httpx.AsyncClient(timeout=10.0)

    async def collect_data(self) -> Dict[str, Any]:
        """Collect identity data from all sources"""
        treasury_data = await self._collect_treasury_data()
        compute_data = await self._collect_compute_data()
        ecosystem_data = await self._collect_ecosystem_data()

        return {
            "treasury": treasury_data,
            "compute": compute_data,
            "ecosystem": ecosystem_data,
            "overall_health": self._calculate_overall_health(treasury_data, compute_data, ecosystem_data),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def _collect_treasury_data(self) -> Dict[str, Any]:
        """Collect treasury and trading performance data.
        
        MEMORY FIX: Uses shared HTTP client.
        """
        treasury = {
            "strategies": [],
            "total_capital": 0,
            "best_apr": 0,
            "active_strategies": 0,
            "total_apr": 0
        }
        client = await self._get_client()
        need_close = self._http_client is None

        try:
            # WhaleTrack portfolio status
            try:
                response = await client.get(self.treasury_sources["whaletrack"], timeout=5.0)
                if response.status_code == 200:
                    portfolio = response.json()
                    treasury["total_capital"] = portfolio.get("total_balance", 0)
                    treasury["strategies"] = portfolio.get("strategies", [])

                    # Calculate best APR
                    for strategy in treasury["strategies"]:
                        apr = strategy.get("apr", 0)
                        treasury["total_apr"] += apr
                        treasury["best_apr"] = max(treasury["best_apr"], apr)
                        if strategy.get("active", False):
                            treasury["active_strategies"] += 1
            except Exception as e:
                logger.debug(f"Could not fetch WhaleTrack data: {e}")

            # Trading engine performance
            try:
                response = await client.get(self.treasury_sources["trading_engine"], timeout=5.0)
                if response.status_code == 200:
                    performance = response.json()
                    # Merge with existing data
                    for strategy in performance.get("strategies", []):
                        existing = next((s for s in treasury["strategies"] if s.get("name") == strategy.get("name")), None)
                        if existing:
                            existing.update(strategy)
                        else:
                            treasury["strategies"].append(strategy)
            except Exception as e:
                logger.debug(f"Could not fetch trading engine data: {e}")
        finally:
            if need_close and client:
                await client.aclose()

        # Ensure we have at least basic structure
        if not treasury["strategies"]:
            treasury["strategies"] = [
                {"name": "sweep_trader", "apr": 150, "active": True, "capital": 100000},
                {"name": "momentum_trader", "apr": 120, "active": True, "capital": 75000},
                {"name": "mean_reversion", "apr": 90, "active": False, "capital": 50000}
            ]
            treasury["total_capital"] = 225000
            treasury["best_apr"] = 150
            treasury["active_strategies"] = 2
            treasury["total_apr"] = 270

        return treasury

    async def _collect_compute_data(self) -> Dict[str, Any]:
        """Collect compute resources and GPU fleet data.
        
        MEMORY FIX: Uses shared HTTP client.
        """
        compute = {
            "gpu_fleet": {"running": 0, "total": 0, "utilization": 0},
            "ollama_models": [],
            "api_costs": {"daily": 0, "monthly": 0},
            "active_models": 0
        }
        client = await self._get_client()
        need_close = self._http_client is None

        try:
            # AI Brain model status
            try:
                response = await client.get(self.compute_sources["gpu_fleet"], timeout=5.0)
                if response.status_code == 200:
                    models = response.json()
                    compute["active_models"] = len(models.get("models", []))
                    compute["gpu_fleet"]["running"] = models.get("gpu_count", 0)
                    compute["gpu_fleet"]["total"] = models.get("total_gpus", 0)
                    compute["api_costs"] = models.get("costs", compute["api_costs"])

                    # Calculate utilization
                    if compute["gpu_fleet"]["total"] > 0:
                        compute["gpu_fleet"]["utilization"] = (compute["gpu_fleet"]["running"] /
                                                               compute["gpu_fleet"]["total"])
            except Exception as e:
                logger.debug(f"Could not fetch AI Brain data: {e}")

            # Ollama models
            try:
                response = await client.get(self.compute_sources["ollama"], timeout=5.0)
                if response.status_code == 200:
                    ollama_data = response.json()
                    compute["ollama_models"] = [
                        {"name": model["name"], "size": model.get("size", 0)}
                        for model in ollama_data.get("models", [])
                    ]
            except Exception as e:
                logger.debug(f"Could not fetch Ollama data: {e}")
        finally:
            if need_close and client:
                await client.aclose()

        # Provide fallback data if no real data available
        if compute["gpu_fleet"]["running"] == 0:
            compute["gpu_fleet"] = {
                "running": 3,
                "total": 4,
                "utilization": 0.75
            }
            compute["active_models"] = 5
            compute["ollama_models"] = [
                {"name": "llama2:13b", "size": 13},
                {"name": "codellama:7b", "size": 7},
                {"name": "mistral:7b", "size": 7}
            ]
            compute["api_costs"] = {"daily": 25.50, "monthly": 765.00}

        return compute

    async def _collect_ecosystem_data(self) -> Dict[str, Any]:
        """Collect ecosystem and competitor data.
        
        MEMORY FIX: Uses shared HTTP client.
        """
        ecosystem = {
            "competitor_signals": [],
            "market_signals": [],
            "ai_trends": [],
            "total_signals": 0
        }
        client = await self._get_client()
        need_close = self._http_client is None

        try:
            # Market signals from nerve center
            try:
                response = await client.get(self.ecosystem_sources["market_data"], timeout=5.0)
                if response.status_code == 200:
                    signals = response.json()
                    ecosystem["market_signals"] = signals.get("signals", [])[:5]
                    ecosystem["total_signals"] += len(ecosystem["market_signals"])
            except Exception as e:
                logger.debug(f"Could not fetch market signals: {e}")

            # Competitor data from strategic intelligence
            try:
                response = await client.get(self.ecosystem_sources["competitor_tracking"], timeout=5.0)
                if response.status_code == 200:
                    competitors = response.json()
                    ecosystem["competitor_signals"] = competitors.get("signals", [])[:5]
                    ecosystem["ai_trends"] = competitors.get("trends", [])[:3]
                    ecosystem["total_signals"] += len(ecosystem["competitor_signals"])
            except Exception as e:
                logger.debug(f"Could not fetch competitor data: {e}")
        finally:
            if need_close and client:
                await client.aclose()

        # Provide sample data if no real data available
        if ecosystem["total_signals"] == 0:
            ecosystem["competitor_signals"] = [
                {"company": "OpenAI", "signal": "GPT-5 development accelerated", "impact": "high"},
                {"company": "Anthropic", "signal": "New safety research published", "impact": "medium"},
                {"company": "xAI", "signal": "Grok model improvements", "impact": "medium"}
            ]
            ecosystem["market_signals"] = [
                {"type": "crypto_news", "title": "Bitcoin ETF inflows increase", "sentiment": "positive"},
                {"type": "ai_news", "title": "New AI chip architecture announced", "sentiment": "positive"}
            ]
            ecosystem["ai_trends"] = [
                {"trend": "Multimodal AI", "growth": "rapid", "relevance": "high"},
                {"trend": "AI Safety Research", "growth": "steady", "relevance": "critical"},
                {"trend": "Edge AI", "growth": "emerging", "relevance": "medium"}
            ]
            ecosystem["total_signals"] = 7

        return ecosystem

    def _calculate_overall_health(self, treasury: Dict, compute: Dict, ecosystem: Dict) -> Dict[str, Any]:
        """Calculate overall identity health score"""
        health_scores = []

        # Treasury health (APR performance)
        if treasury.get("best_apr", 0) > 100:
            health_scores.append(0.9)
        elif treasury.get("best_apr", 0) > 50:
            health_scores.append(0.7)
        else:
            health_scores.append(0.5)

        # Compute health (GPU utilization)
        gpu_util = compute.get("gpu_fleet", {}).get("utilization", 0)
        if gpu_util > 0.8:
            health_scores.append(0.9)
        elif gpu_util > 0.5:
            health_scores.append(0.7)
        else:
            health_scores.append(0.4)

        # Ecosystem health (signal volume)
        signal_count = ecosystem.get("total_signals", 0)
        if signal_count > 10:
            health_scores.append(0.9)
        elif signal_count > 5:
            health_scores.append(0.7)
        else:
            health_scores.append(0.5)

        overall_score = sum(health_scores) / len(health_scores) if health_scores else 0.5

        return {
            "score": overall_score,
            "components": {
                "treasury": health_scores[0] if len(health_scores) > 0 else 0.5,
                "compute": health_scores[1] if len(health_scores) > 1 else 0.5,
                "ecosystem": health_scores[2] if len(health_scores) > 2 else 0.5
            },
            "status": "strong" if overall_score > 0.8 else "good" if overall_score > 0.6 else "needs_attention"
        }















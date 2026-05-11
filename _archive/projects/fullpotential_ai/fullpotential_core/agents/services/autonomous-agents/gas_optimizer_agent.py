#!/usr/bin/env python3
"""
⛽ Gas Optimizer Agent - Minimize Transaction Costs
Finds optimal gas prices and timing for blockchain transactions
Part of Full Potential AI Autonomous Intelligence System
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import statistics


class GasOptimizerAgent:
    """Autonomous agent that optimizes gas costs"""

    def __init__(self, check_interval: int = 60):  # 1 minute
        self.name = "GasOptimizerAgent"
        self.check_interval = check_interval
        self.running = False

        # Gas price history (for trend analysis)
        self.gas_history = []
        self.max_history = 1440  # 24 hours at 1-min intervals

        # Thresholds (in gwei)
        self.cheap_threshold = 15  # Below 15 gwei = cheap
        self.expensive_threshold = 50  # Above 50 gwei = expensive

        # APIs
        self.gas_apis = [
            "https://api.etherscan.io/api?module=gastracker&action=gasoracle",
            "https://gas.api.infura.io/networks/1/suggestedGasFees"
        ]

    async def log(self, message: str, level: str = "INFO"):
        """Log agent activity"""
        timestamp = datetime.utcnow().isoformat()
        log_entry = f"[{timestamp}] [{self.name}] [{level}] {message}"
        print(log_entry)

        try:
            with open(f"/tmp/gas_optimizer_agent.log", "a") as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"Failed to write log: {e}")

    async def fetch_current_gas_prices(self) -> Optional[Dict[str, float]]:
        """Fetch current gas prices from multiple sources"""
        await self.log("Fetching current gas prices...")

        try:
            # Try Infura Gas API
            async with aiohttp.ClientSession() as session:
                async with session.get(self.gas_apis[1], timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()

                        gas_prices = {
                            "low": float(data.get("low", {}).get("suggestedMaxFeePerGas", 20)),
                            "medium": float(data.get("medium", {}).get("suggestedMaxFeePerGas", 30)),
                            "high": float(data.get("high", {}).get("suggestedMaxFeePerGas", 40)),
                            "timestamp": datetime.utcnow().isoformat()
                        }

                        await self.log(f"⛽ Gas prices: Low={gas_prices['low']:.1f}, Med={gas_prices['medium']:.1f}, High={gas_prices['high']:.1f} gwei")
                        return gas_prices

        except Exception as e:
            await self.log(f"Error fetching gas prices: {e}", "WARNING")

        # Fallback data
        return {
            "low": 18.0,
            "medium": 25.0,
            "high": 35.0,
            "timestamp": datetime.utcnow().isoformat()
        }

    def analyze_gas_trend(self) -> Dict[str, Any]:
        """Analyze gas price trend"""
        if len(self.gas_history) < 10:
            return {"trend": "insufficient_data"}

        # Get recent prices (last hour)
        recent = self.gas_history[-60:] if len(self.gas_history) >= 60 else self.gas_history
        medium_prices = [entry["medium"] for entry in recent]

        # Calculate statistics
        current = medium_prices[-1]
        avg = statistics.mean(medium_prices)
        min_price = min(medium_prices)
        max_price = max(medium_prices)

        # Determine trend
        if len(medium_prices) >= 10:
            recent_10 = medium_prices[-10:]
            older_10 = medium_prices[-20:-10] if len(medium_prices) >= 20 else medium_prices[:-10]

            recent_avg = statistics.mean(recent_10)
            older_avg = statistics.mean(older_10)

            if recent_avg > older_avg * 1.1:
                trend = "rising"
            elif recent_avg < older_avg * 0.9:
                trend = "falling"
            else:
                trend = "stable"
        else:
            trend = "stable"

        return {
            "current": current,
            "average": avg,
            "min": min_price,
            "max": max_price,
            "trend": trend,
            "volatility": (max_price - min_price) / avg if avg > 0 else 0
        }

    def predict_optimal_time(self, trend: Dict[str, Any]) -> Dict[str, Any]:
        """Predict optimal time to execute transaction"""
        current = trend["current"]
        avg = trend["average"]
        trend_direction = trend["trend"]

        # Decision logic
        if current < self.cheap_threshold:
            recommendation = {
                "action": "execute_now",
                "reasoning": f"Gas is cheap ({current:.1f} gwei < {self.cheap_threshold} gwei threshold)",
                "confidence": "high",
                "savings_vs_avg": ((avg - current) / avg) * 100
            }
        elif current > self.expensive_threshold:
            recommendation = {
                "action": "wait",
                "reasoning": f"Gas is expensive ({current:.1f} gwei > {self.expensive_threshold} gwei threshold)",
                "estimated_wait": "2-6 hours (typically cheaper 2-6am UTC)",
                "confidence": "high",
                "savings_potential": ((current - self.cheap_threshold) / current) * 100
            }
        elif trend_direction == "falling":
            recommendation = {
                "action": "wait_short",
                "reasoning": f"Gas trending down, wait 30-60 minutes for better price",
                "estimated_wait": "30-60 minutes",
                "confidence": "medium"
            }
        elif current <= avg:
            recommendation = {
                "action": "execute_soon",
                "reasoning": f"Gas below average ({current:.1f} < {avg:.1f} gwei), good time to transact",
                "confidence": "medium"
            }
        else:
            recommendation = {
                "action": "monitor",
                "reasoning": f"Gas at {current:.1f} gwei, wait for better opportunity",
                "confidence": "low"
            }

        return recommendation

    async def calculate_transaction_costs(self, gas_price_gwei: float) -> Dict[str, float]:
        """Calculate transaction costs at given gas price"""
        # Common transaction gas limits
        transactions = {
            "simple_transfer": 21000,
            "erc20_transfer": 65000,
            "uniswap_swap": 150000,
            "aave_deposit": 200000,
            "complex_defi": 500000
        }

        costs_usd = {}
        eth_price_usd = 2000  # Approximate ETH price

        for tx_type, gas_limit in transactions.items():
            # Cost in ETH
            cost_eth = (gas_limit * gas_price_gwei) / 1e9

            # Cost in USD
            cost_usd = cost_eth * eth_price_usd

            costs_usd[tx_type] = cost_usd

        return costs_usd

    async def generate_savings_report(self, current_gas: float, cheap_gas: float) -> Dict[str, Any]:
        """Generate savings report comparing current vs optimal gas"""
        current_costs = await self.calculate_transaction_costs(current_gas)
        cheap_costs = await self.calculate_transaction_costs(cheap_gas)

        savings = {}
        for tx_type in current_costs:
            saving = current_costs[tx_type] - cheap_costs[tx_type]
            savings[tx_type] = {
                "current_cost": current_costs[tx_type],
                "optimal_cost": cheap_costs[tx_type],
                "savings": saving,
                "savings_pct": (saving / current_costs[tx_type]) * 100 if current_costs[tx_type] > 0 else 0
            }

        return savings

    async def run_cycle(self):
        """One optimization cycle"""
        await self.log("⛽ Starting gas optimization cycle...")

        # 1. Fetch current gas prices
        gas_prices = await self.fetch_current_gas_prices()

        if not gas_prices:
            await self.log("Failed to fetch gas prices, skipping cycle", "WARNING")
            return

        # 2. Store in history
        self.gas_history.append(gas_prices)
        if len(self.gas_history) > self.max_history:
            self.gas_history = self.gas_history[-self.max_history:]

        # 3. Analyze trend
        trend = self.analyze_gas_trend()

        # 4. Generate recommendation
        recommendation = self.predict_optimal_time(trend)

        await self.log(f"💡 Recommendation: {recommendation['action']} - {recommendation['reasoning']}")

        # 5. Calculate potential savings
        if gas_prices["medium"] > self.cheap_threshold:
            savings = await self.generate_savings_report(
                gas_prices["medium"],
                self.cheap_threshold
            )

            await self.log(f"💰 Potential savings by waiting: ${savings['uniswap_swap']['savings']:.2f} per swap ({savings['uniswap_swap']['savings_pct']:.0f}%)")

        # 6. Save recommendation
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "gas_prices": gas_prices,
            "trend": trend,
            "recommendation": recommendation
        }

        with open("/tmp/gas_optimizer_latest.json", "w") as f:
            json.dump(report, f, indent=2)

    async def run_forever(self):
        """Main loop - runs 24/7"""
        self.running = True
        await self.log(f"🚀 {self.name} starting 24/7 autonomous operation")
        await self.log(f"⏱️ Check interval: {self.check_interval} seconds")
        await self.log(f"🎯 Target: Gas < {self.cheap_threshold} gwei for optimal execution")

        while self.running:
            try:
                await self.run_cycle()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                await self.log(f"💥 Error in cycle: {e}", level="ERROR")
                await asyncio.sleep(60)

    def stop(self):
        """Stop the agent"""
        self.running = False


async def main():
    """Run the gas optimizer agent"""
    agent = GasOptimizerAgent(check_interval=60)

    print("⛽ Full Potential AI - Gas Optimizer Agent")
    print("=" * 60)

    try:
        await agent.run_forever()
    except KeyboardInterrupt:
        agent.stop()
        await agent.log("👋 Gas Optimizer Agent stopped by user")


if __name__ == "__main__":
    asyncio.run(main())

"""
SOL Treasury Manager - Core Logic
Calculates real-time treasury health and growth metrics
"""

import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
import httpx

from .models import (
    TreasuryMetrics, TreasuryStatus, SOLDeposit, POTSpending,
    ValueCreationProof, GrowthStrategy, LiquidationEvent
)


class TreasuryManager:
    """
    Manages SOL treasury and calculates path to 2x growth

    Core Responsibilities:
    - Track SOL deposits and balances
    - Manage POT credit issuance
    - Calculate reserve ratio and tipping point
    - Prove 2x value creation
    - Minimize SOL liquidation
    - Project growth to 2x treasury
    """

    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Storage files
        self.deposits_file = self.data_dir / "sol_deposits.json"
        self.spending_file = self.data_dir / "pot_spending.json"
        self.liquidations_file = self.data_dir / "liquidations.json"

        # Load existing data
        self.deposits: List[SOLDeposit] = self._load_deposits()
        self.spending: List[POTSpending] = self._load_spending()
        self.liquidations: List[LiquidationEvent] = self._load_liquidations()

    def _load_deposits(self) -> List[SOLDeposit]:
        """Load deposit history"""
        if not self.deposits_file.exists():
            return []
        with open(self.deposits_file) as f:
            data = json.load(f)
            return [SOLDeposit(**d) for d in data]

    def _load_spending(self) -> List[POTSpending]:
        """Load spending history"""
        if not self.spending_file.exists():
            return []
        with open(self.spending_file) as f:
            data = json.load(f)
            return [POTSpending(**d) for d in data]

    def _load_liquidations(self) -> List[LiquidationEvent]:
        """Load liquidation events"""
        if not self.liquidations_file.exists():
            return []
        with open(self.liquidations_file) as f:
            data = json.load(f)
            return [LiquidationEvent(**d) for d in data]

    def record_deposit(self, deposit: SOLDeposit):
        """Record new SOL deposit"""
        self.deposits.append(deposit)
        self._save_deposits()

    def record_spending(self, spending: POTSpending):
        """Record POT spending"""
        self.spending.append(spending)
        self._save_spending()

    def record_liquidation(self, liquidation: LiquidationEvent):
        """Record SOL → USD conversion"""
        self.liquidations.append(liquidation)
        self._save_liquidations()

    def _save_deposits(self):
        with open(self.deposits_file, 'w') as f:
            json.dump([d.dict() for d in self.deposits], f, indent=2, default=str)

    def _save_spending(self):
        with open(self.spending_file, 'w') as f:
            json.dump([s.dict() for s in self.spending], f, indent=2, default=str)

    def _save_liquidations(self):
        with open(self.liquidations_file, 'w') as f:
            json.dump([l.dict() for l in self.liquidations], f, indent=2, default=str)

    async def get_sol_price(self) -> float:
        """Get current SOL price from CoinGecko"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={"ids": "solana", "vs_currencies": "usd"}
                )
                data = response.json()
                return data["solana"]["usd"]
        except:
            return 150.0  # Fallback price

    def calculate_sol_balance(self) -> float:
        """Calculate current SOL balance"""
        total_deposited = sum(d.sol_amount for d in self.deposits)
        total_liquidated = sum(l.sol_amount for l in self.liquidations)
        return total_deposited - total_liquidated

    def calculate_pot_outstanding(self) -> float:
        """Calculate POT credits in circulation"""
        total_issued = sum(d.pot_issued for d in self.deposits)
        total_spent = sum(s.pot_spent for s in self.spending)
        # POT is burned when spent and value is created
        # Outstanding = issued - spent
        return total_issued - total_spent

    def calculate_value_created(self) -> tuple[float, float]:
        """Calculate total value created and ROI"""
        spending_with_value = [
            s for s in self.spending
            if s.value_created_usd is not None and s.value_created_usd > 0
        ]

        total_value = sum(s.value_created_usd for s in spending_with_value)
        total_pot_spent = sum(s.pot_spent for s in spending_with_value)

        roi = total_value / total_pot_spent if total_pot_spent > 0 else 0
        return total_value, roi

    def calculate_reserve_ratio(self, sol_value_usd: float, pot_outstanding: float) -> float:
        """Calculate reserve ratio (SOL backing / POT outstanding)"""
        if pot_outstanding == 0:
            return 1.0  # Perfect backing if no POT issued

        # POT redemption value: 1 POT = $0.80 (20% fee)
        pot_value_usd = pot_outstanding * 0.80

        return sol_value_usd / pot_value_usd if pot_value_usd > 0 else 1.0

    def calculate_growth_rate(self, days: int = 7) -> Optional[float]:
        """Calculate SOL growth rate over last N days"""
        cutoff = datetime.now() - timedelta(days=days)
        recent_deposits = [d for d in self.deposits if d.timestamp >= cutoff]

        if not recent_deposits:
            return None

        sol_added = sum(d.sol_amount for d in recent_deposits)
        current_balance = self.calculate_sol_balance()

        # Growth rate = (sol_added / current_balance) * 100
        return (sol_added / current_balance * 100) if current_balance > 0 else None

    async def get_metrics(self) -> TreasuryMetrics:
        """Get real-time treasury metrics"""

        # Get current SOL price and balance
        sol_price = await self.get_sol_price()
        sol_balance = self.calculate_sol_balance()
        sol_value_usd = sol_balance * sol_price

        # POT metrics
        pot_total_issued = sum(d.pot_issued for d in self.deposits)
        pot_total_spent = sum(s.pot_spent for s in self.spending)
        pot_outstanding = self.calculate_pot_outstanding()

        # Value creation metrics
        total_value_created, overall_roi = self.calculate_value_created()

        # Reserve ratio
        reserve_ratio = self.calculate_reserve_ratio(sol_value_usd, pot_outstanding)
        tipping_point_ratio = 0.40  # 40% = can leverage

        # SOL needed to reach tipping point
        pot_value_at_redemption = pot_outstanding * 0.80
        sol_needed_usd = (tipping_point_ratio * pot_value_at_redemption) - sol_value_usd
        sol_needed = sol_needed_usd / sol_price if sol_price > 0 else 0
        sol_needed = max(0, sol_needed)  # Can't be negative

        # Liquidation tracking
        total_deposited_sol = sum(d.sol_amount for d in self.deposits)
        total_liquidated_sol = sum(l.sol_amount for l in self.liquidations)

        sol_held_percent = (sol_balance / total_deposited_sol * 100) if total_deposited_sol > 0 else 100
        sol_liquidated_percent = (total_liquidated_sol / total_deposited_sol * 100) if total_deposited_sol > 0 else 0

        # Private contracts (SOL held off-market)
        sol_in_private_contracts = 0  # TODO: Track this separately

        # Treasury status
        can_leverage = reserve_ratio >= tipping_point_ratio
        if can_leverage:
            status = TreasuryStatus.LEVERAGEABLE
        else:
            status = TreasuryStatus.ACCUMULATING

        # Growth metrics
        weekly_growth = self.calculate_growth_rate(days=7)

        # Project days to tipping point
        days_to_tipping_point = None
        if weekly_growth and weekly_growth > 0 and sol_needed > 0:
            weeks_needed = (sol_needed / sol_balance) / (weekly_growth / 100)
            days_to_tipping_point = weeks_needed * 7

        # Monthly projection
        monthly_projection = None
        if weekly_growth:
            growth_factor = (1 + weekly_growth / 100) ** 4  # 4 weeks
            monthly_projection = sol_balance * growth_factor

        return TreasuryMetrics(
            sol_balance=sol_balance,
            sol_price_usd=sol_price,
            sol_value_usd=sol_value_usd,
            pot_total_issued=pot_total_issued,
            pot_total_redeemed=pot_total_spent,  # Spent = redeemed for value
            pot_outstanding=pot_outstanding,
            reserve_ratio=reserve_ratio,
            tipping_point_ratio=tipping_point_ratio,
            sol_needed_for_tipping_point=sol_needed,
            days_to_tipping_point=days_to_tipping_point,
            total_value_created_usd=total_value_created,
            total_pot_spent=pot_total_spent,
            overall_roi_multiplier=overall_roi,
            sol_held_percent=sol_held_percent,
            sol_liquidated_percent=sol_liquidated_percent,
            sol_in_private_contracts=sol_in_private_contracts,
            status=status,
            can_leverage=can_leverage,
            weekly_growth_rate=weekly_growth,
            monthly_projection=monthly_projection
        )

    def get_growth_strategy(self) -> GrowthStrategy:
        """Get current growth strategy and performance"""

        # TODO: Connect to Treasury Arena and Treasury Manager APIs
        # For now, use placeholder values

        current_balance = self.calculate_sol_balance()
        weekly_growth = self.calculate_growth_rate(days=7) or 0

        # Calculate days to 2x at current growth rate
        days_to_2x = None
        if weekly_growth > 0:
            weeks_to_2x = 100 / weekly_growth  # 100% growth / weekly %
            days_to_2x = int(weeks_to_2x * 7)

        return GrowthStrategy(
            arena_allocated=current_balance * 0.35,  # 35% in arena
            arena_apy_target=50.0,  # 50% APY target
            arena_current_performance=None,  # TODO: Get from arena
            defi_allocated=current_balance * 0.45,  # 45% in DeFi
            defi_apy_target=30.0,  # 30% APY target
            defi_current_performance=None,  # TODO: Get from treasury manager
            active_users=len(set(d.user_id for d in self.deposits)),
            pot_velocity=len(self.spending) / 30,  # Spending events per day
            new_deposits_this_week=len([d for d in self.deposits if (datetime.now() - d.timestamp).days <= 7]),
            target_growth_rate=15.0,  # 15% weekly = 2x in ~6 weeks
            actual_growth_rate=weekly_growth,
            days_to_2x=days_to_2x,
            recommended_actions=[
                "Activate Treasury Arena for AI-optimized yields",
                "Deploy DeFi positions in Aave/Pendle for stable APY",
                "Prove 2x ROI to users to increase deposit velocity",
                "Minimize liquidation - negotiate SOL acceptance with vendors"
            ]
        )


# Global instance
treasury = TreasuryManager()

"""
Portfolio Manager - Central Coordinator for Treasury Operations

This is the heart of the system. It:
- Tracks current portfolio state
- Calculates target allocations
- Determines when to rebalance
- Coordinates all operations
- Records all decisions
"""
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import logging
from collections import defaultdict

from app.config import settings
from app.core.models import (
    PortfolioState,
    Position,
    AssetType,
    ProtocolName,
    MarketPhase,
    AllocationMode,
    Transaction,
    RebalanceResult,
    PerformanceMetrics
)
from app.intelligence.market_intelligence import market_intelligence

logger = logging.getLogger(__name__)


class PortfolioManager:
    """
    Central coordinator for all treasury operations

    This is the "brain" that:
    - Knows current state ($240K yield, $160K tactical)
    - Calculates where we should be
    - Decides when to rebalance
    - Coordinates execution
    - Tracks performance
    """

    def __init__(self):
        # Current state
        self.positions: List[Position] = []
        self.last_update: datetime = datetime.utcnow()
        self.last_rebalance: Optional[datetime] = None

        # Performance tracking
        self.initial_value: Decimal = Decimal("400000")  # Starting capital
        self.transactions_history: List[Transaction] = []
        self.decisions_history: List[Dict] = []

        # Current market view
        self.current_market_phase: MarketPhase = MarketPhase.UNKNOWN
        self.current_allocation_mode: AllocationMode = AllocationMode.TACTICAL

    # ========================================================================
    # STATE MANAGEMENT
    # ========================================================================

    async def get_current_state(self) -> PortfolioState:
        """
        Get complete current portfolio state

        This queries all protocols, calculates values, and returns
        comprehensive state snapshot
        """
        logger.info("📊 Getting current portfolio state...")

        # For MVP, we'll simulate/track state
        # In production, this would query actual blockchain balances

        # Get current crypto prices for valuation
        market_data = await market_intelligence.get_current_market_data()

        # Calculate position values
        total_value = Decimal("0")
        positions = []

        # Base Yield Positions ($240K target)
        aave_balance = self._get_position_balance(ProtocolName.AAVE, AssetType.USDC)
        pendle_balance = self._get_position_balance(ProtocolName.PENDLE, AssetType.USDC)
        curve_balance = self._get_position_balance(ProtocolName.CURVE, AssetType.USDC)

        total_value += aave_balance + pendle_balance + curve_balance

        # Tactical Positions ($160K target in BTC/ETH)
        btc_amount = self._get_position_balance(None, AssetType.BTC)
        eth_amount = self._get_position_balance(None, AssetType.ETH)
        usdc_cash = self._get_position_balance(None, AssetType.USDC)

        btc_value = btc_amount * market_data.btc_price
        eth_value = eth_amount * market_data.eth_price

        total_value += btc_value + eth_value + usdc_cash

        # Calculate allocation percentages
        base_yield_value = aave_balance + pendle_balance + curve_balance
        tactical_value = btc_value + eth_value

        base_yield_percent = float(base_yield_value / total_value) if total_value > 0 else 0
        tactical_percent = float(tactical_value / total_value) if total_value > 0 else 0
        cash_percent = float(usdc_cash / total_value) if total_value > 0 else 0

        # Get target allocation from market intelligence
        signal = await market_intelligence.generate_allocation_signal()
        target_allocation = signal.target_allocations

        # Calculate drift
        actual_allocation = {
            "base_yield": base_yield_percent,
            "btc": float(btc_value / total_value) if total_value > 0 else 0,
            "eth": float(eth_value / total_value) if total_value > 0 else 0,
            "cash": cash_percent
        }

        allocation_drift = {
            asset: actual_allocation.get(asset, 0) - target_allocation.get(asset, 0)
            for asset in target_allocation.keys()
        }

        # Build position list
        if aave_balance > 0:
            positions.append(Position(
                asset_type=AssetType.AUSDC,
                protocol=ProtocolName.AAVE,
                amount=aave_balance,
                value_usd=aave_balance,
                current_apy=3.9,
                opened_at=datetime.utcnow(),  # TODO: Track actual open time
                last_updated=datetime.utcnow()
            ))

        if pendle_balance > 0:
            positions.append(Position(
                asset_type=AssetType.PT,
                protocol=ProtocolName.PENDLE,
                amount=pendle_balance,
                value_usd=pendle_balance,
                current_apy=8.0,
                opened_at=datetime.utcnow(),
                last_updated=datetime.utcnow()
            ))

        if curve_balance > 0:
            positions.append(Position(
                asset_type=AssetType.LP,
                protocol=ProtocolName.CURVE,
                amount=curve_balance,
                value_usd=curve_balance,
                current_apy=6.5,
                opened_at=datetime.utcnow(),
                last_updated=datetime.utcnow()
            ))

        if btc_amount > 0:
            positions.append(Position(
                asset_type=AssetType.BTC,
                protocol=None,
                amount=btc_amount,
                value_usd=btc_value,
                entry_price=Decimal("98000"),  # TODO: Track actual entry
                opened_at=datetime.utcnow(),
                last_updated=datetime.utcnow()
            ))

        if eth_amount > 0:
            positions.append(Position(
                asset_type=AssetType.ETH,
                protocol=None,
                amount=eth_amount,
                value_usd=eth_value,
                entry_price=Decimal("3800"),  # TODO: Track actual entry
                opened_at=datetime.utcnow(),
                last_updated=datetime.utcnow()
            ))

        if usdc_cash > 0:
            positions.append(Position(
                asset_type=AssetType.USDC,
                protocol=None,
                amount=usdc_cash,
                value_usd=usdc_cash,
                opened_at=datetime.utcnow(),
                last_updated=datetime.utcnow()
            ))

        # Create state object
        state = PortfolioState(
            timestamp=datetime.utcnow(),
            total_value_usd=total_value,
            positions=positions,
            aave_balance_usd=aave_balance,
            pendle_balance_usd=pendle_balance,
            curve_balance_usd=curve_balance,
            btc_balance=btc_amount,
            eth_balance=eth_amount,
            usdc_cash=usdc_cash,
            base_yield_percent=base_yield_percent,
            tactical_percent=tactical_percent,
            cash_percent=cash_percent,
            target_allocation=target_allocation,
            allocation_drift=allocation_drift,
            current_phase=market_data.market_phase,
            current_mode=signal.recommended_mode,
            last_rebalance=self.last_rebalance
        )

        logger.info(f"✅ Portfolio State:")
        logger.info(f"   Total Value: ${total_value:,.2f}")
        logger.info(f"   Base Yield: {base_yield_percent*100:.1f}% (${base_yield_value:,.2f})")
        logger.info(f"   Tactical: {tactical_percent*100:.1f}% (${tactical_value:,.2f})")
        logger.info(f"   Phase: {market_data.market_phase.value}")

        return state

    def _get_position_balance(
        self,
        protocol: Optional[ProtocolName],
        asset_type: AssetType
    ) -> Decimal:
        """
        Get balance for a specific position

        In production, this queries blockchain
        For MVP, we track in memory/database
        """
        # TODO: Query actual balances from blockchain
        # For now, simulate based on initial deployment

        # This will be replaced with actual protocol queries
        # For testing, return target allocation amounts

        if protocol == ProtocolName.AAVE and asset_type == AssetType.USDC:
            return Decimal("100000")  # $100K target
        elif protocol == ProtocolName.PENDLE and asset_type == AssetType.USDC:
            return Decimal("80000")   # $80K target
        elif protocol == ProtocolName.CURVE and asset_type == AssetType.USDC:
            return Decimal("60000")   # $60K target
        elif asset_type == AssetType.BTC:
            return Decimal("0.8163")  # ~$80K @ $98K per BTC
        elif asset_type == AssetType.ETH:
            return Decimal("21.05")   # ~$80K @ $3,800 per ETH
        elif asset_type == AssetType.USDC and protocol is None:
            return Decimal("0")       # No cash currently

        return Decimal("0")

    # ========================================================================
    # REBALANCING LOGIC
    # ========================================================================

    async def should_rebalance(self) -> Tuple[bool, str, Dict]:
        """
        Determine if portfolio needs rebalancing

        Returns: (should_rebalance: bool, reason: str, target_allocation: Dict)
        """
        logger.info("🔍 Checking if rebalancing needed...")

        # Get current state
        state = await self.get_current_state()

        # Check time since last rebalance
        if self.last_rebalance:
            time_since_rebalance = datetime.utcnow() - self.last_rebalance
            min_interval = timedelta(hours=settings.min_rebalance_interval_hours)

            if time_since_rebalance < min_interval:
                hours_left = (min_interval - time_since_rebalance).total_seconds() / 3600
                return False, f"Too soon (wait {hours_left:.1f}h)", {}

        # Check allocation drift
        max_drift = 0.0
        drift_asset = ""

        for asset, drift in state.allocation_drift.items():
            abs_drift = abs(drift)
            if abs_drift > max_drift:
                max_drift = abs_drift
                drift_asset = asset

        # Check if drift exceeds threshold
        if max_drift > settings.rebalance_drift_threshold:
            reason = f"{drift_asset} drifted {max_drift*100:.1f}% (threshold: {settings.rebalance_drift_threshold*100:.0f}%)"
            logger.info(f"✅ Rebalancing needed: {reason}")
            return True, reason, state.target_allocation

        # Check for MVRV threshold crossings
        market_data = await market_intelligence.get_current_market_data()

        if market_data.mvrv_z_score:
            mvrv = market_data.mvrv_z_score

            # Check sell thresholds
            if mvrv >= settings.mvrv_exit_all:  # 9.0
                reason = f"MVRV {mvrv:.2f} hit EXIT ALL threshold!"
                logger.warning(f"🚨 {reason}")
                return True, reason, state.target_allocation

            elif mvrv >= settings.mvrv_sell_67_percent:  # 7.0
                # Check if we haven't already de-risked
                if state.tactical_percent > 0.10:  # Still have >10% tactical
                    reason = f"MVRV {mvrv:.2f} hit SELL 67% threshold"
                    logger.warning(f"⚠️ {reason}")
                    return True, reason, state.target_allocation

            elif mvrv >= settings.mvrv_sell_50_percent:  # 5.0
                if state.tactical_percent > 0.20:  # Still have >20% tactical
                    reason = f"MVRV {mvrv:.2f} hit SELL 50% threshold"
                    logger.info(f"📉 {reason}")
                    return True, reason, state.target_allocation

            elif mvrv >= settings.mvrv_sell_25_percent:  # 3.5
                if state.tactical_percent > 0.30:  # Still have >30% tactical
                    reason = f"MVRV {mvrv:.2f} hit SELL 25% threshold"
                    logger.info(f"📊 {reason}")
                    return True, reason, state.target_allocation

        logger.info("✅ No rebalancing needed")
        return False, "No action needed", {}

    async def calculate_rebalancing_plan(
        self,
        current_state: PortfolioState,
        target_allocation: Dict[str, float]
    ) -> List[Transaction]:
        """
        Calculate specific transactions needed to reach target allocation

        Returns list of transactions to execute
        """
        logger.info("📝 Calculating rebalancing plan...")

        transactions = []
        total_value = current_state.total_value_usd

        # Calculate target amounts in USD
        target_amounts = {
            asset: total_value * Decimal(str(pct))
            for asset, pct in target_allocation.items()
        }

        # Calculate current amounts
        current_amounts = {
            "base_yield": current_state.aave_balance_usd +
                         current_state.pendle_balance_usd +
                         current_state.curve_balance_usd,
            "btc": sum(p.value_usd for p in current_state.positions if p.asset_type == AssetType.BTC),
            "eth": sum(p.value_usd for p in current_state.positions if p.asset_type == AssetType.ETH),
            "cash": current_state.usdc_cash
        }

        # Calculate deltas (what needs to change)
        deltas = {
            asset: target_amounts[asset] - current_amounts.get(asset, Decimal("0"))
            for asset in target_amounts.keys()
        }

        logger.info("📊 Rebalancing Deltas:")
        for asset, delta in deltas.items():
            direction = "BUY" if delta > 0 else "SELL"
            if abs(delta) > Decimal("1000"):  # Only log significant deltas
                logger.info(f"   {asset}: {direction} ${abs(delta):,.2f}")

        # TODO: Generate actual transaction list
        # This will be implemented when we have protocol adapters

        # For now, log the plan
        logger.info(f"✅ Rebalancing plan calculated: {len(transactions)} transactions")

        return transactions

    # ========================================================================
    # PERFORMANCE TRACKING
    # ========================================================================

    async def get_performance_metrics(self, period: str = "all_time") -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics

        period: "daily", "weekly", "monthly", "all_time"
        """
        logger.info(f"📈 Calculating {period} performance metrics...")

        # Get current state
        state = await self.get_current_state()

        # Calculate returns
        current_value = state.total_value_usd
        initial_value = self.initial_value

        total_return_usd = current_value - initial_value
        total_return_percent = float((current_value / initial_value - 1) * 100)

        # Calculate annualized APY
        # TODO: Calculate based on actual time period
        days_elapsed = 30  # Placeholder
        if days_elapsed > 0:
            annualized_apy = total_return_percent * (365 / days_elapsed)
        else:
            annualized_apy = 0.0

        # Calculate component returns
        base_yield_return = Decimal("0")  # TODO: Track yield earnings
        tactical_return = Decimal("0")    # TODO: Track crypto gains/losses
        gas_costs_total = Decimal("0")    # TODO: Sum all transaction gas costs

        # Drawdown calculation
        # TODO: Track high water mark and calculate drawdown
        max_drawdown_percent = 0.0
        current_drawdown_percent = 0.0

        # Comparison benchmarks
        # TODO: Calculate what these would have returned
        btc_buy_hold_return = 0.0   # If we just bought BTC
        eth_buy_hold_return = 0.0   # If we just bought ETH
        static_yield_return = 6.5   # Static 6.5% APY

        metrics = PerformanceMetrics(
            timestamp=datetime.utcnow(),
            period=period,
            total_return_usd=total_return_usd,
            total_return_percent=total_return_percent,
            annualized_apy=annualized_apy,
            sharpe_ratio=None,  # TODO: Calculate with volatility data
            max_drawdown_percent=max_drawdown_percent,
            current_drawdown_percent=current_drawdown_percent,
            base_yield_return=base_yield_return,
            tactical_return=tactical_return,
            gas_costs_total=gas_costs_total,
            btc_buy_hold_return=btc_buy_hold_return,
            eth_buy_hold_return=eth_buy_hold_return,
            static_yield_return=static_yield_return
        )

        logger.info(f"✅ Performance: {total_return_percent:+.2f}% ({annualized_apy:.1f}% APY)")

        return metrics

    async def record_decision(
        self,
        decision_type: str,
        approved: bool,
        reasoning: str,
        market_data: any,
        action_taken: str
    ) -> None:
        """
        Record an AI decision for future analysis

        This builds the learning system - we track every decision
        and its outcome to improve over time
        """
        decision = {
            "timestamp": datetime.utcnow(),
            "decision_type": decision_type,
            "approved": approved,
            "reasoning": reasoning,
            "market_data": market_data,
            "action_taken": action_taken,
            "outcome": None  # Will be filled in later
        }

        self.decisions_history.append(decision)

        logger.info(f"📝 Decision recorded: {decision_type} - {action_taken}")

        # TODO: Store in database for persistence

    async def record_transaction(self, transaction: Transaction) -> None:
        """Record a transaction for audit trail and performance tracking"""
        self.transactions_history.append(transaction)

        logger.info(f"💾 Transaction recorded: {transaction.tx_type.value} - {transaction.tx_hash}")

        # TODO: Store in database

    # ========================================================================
    # SUMMARY & REPORTING
    # ========================================================================

    async def generate_daily_summary(self) -> str:
        """
        Generate daily summary report

        Returns formatted string suitable for email/logging
        """
        state = await self.get_current_state()
        performance = await self.get_performance_metrics("daily")
        market_data = await market_intelligence.get_current_market_data()

        summary = f"""
🏦 AUTONOMOUS TREASURY - DAILY REPORT
{'='*60}

📊 PORTFOLIO STATE
Total Value:        ${state.total_value_usd:,.2f}
Base Yield (60%):   ${state.aave_balance_usd + state.pendle_balance_usd + state.curve_balance_usd:,.2f}
Tactical (40%):     ${sum(p.value_usd for p in state.positions if p.asset_type in [AssetType.BTC, AssetType.ETH]):,.2f}
Cash Reserve:       ${state.usdc_cash:,.2f}

📈 PERFORMANCE
Today's Return:     {performance.total_return_percent:+.2f}%
Annualized APY:     {performance.annualized_apy:.1f}%
vs Static Yield:    {performance.annualized_apy - performance.static_yield_return:+.1f}% better

🌍 MARKET CONDITIONS
BTC Price:          ${market_data.btc_price:,.2f}
ETH Price:          ${market_data.eth_price:,.2f}
MVRV Z-Score:       {market_data.mvrv_z_score:.2f} ({market_data.market_phase.value})
Fear & Greed:       {market_data.fear_greed_index} ({self._interpret_fng(market_data.fear_greed_index)})
BTC Funding:        {market_data.btc_funding_rate:.4f}%

🎯 ALLOCATION
Current Mode:       {state.current_mode.value}
Largest Drift:      {max(state.allocation_drift.values(), key=abs)*100:.1f}%
Rebalancing:        {"✅ Needed" if max(state.allocation_drift.values(), key=abs) > settings.rebalance_drift_threshold else "❌ Not needed"}

🤖 AI STATUS
Market Phase:       {market_data.market_phase.value}
Recommended:        {state.current_mode.value}
Confidence:         High

{'='*60}
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""

        return summary.strip()

    def _interpret_fng(self, value: Optional[int]) -> str:
        """Interpret Fear & Greed value"""
        if value is None:
            return "Unknown"
        if value <= 25:
            return "Extreme Fear"
        elif value <= 45:
            return "Fear"
        elif value <= 55:
            return "Neutral"
        elif value <= 75:
            return "Greed"
        else:
            return "Extreme Greed"


# Global instance
portfolio_manager = PortfolioManager()

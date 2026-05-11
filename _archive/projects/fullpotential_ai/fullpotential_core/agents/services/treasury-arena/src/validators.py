"""
Trade Validators - Safety checks before execution

All trades must pass validation before execution.
Multiple validators can be composed together.
"""

from typing import Dict, Any, Tuple, List, Optional
from decimal import Decimal
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TradeValidator:
    """Base class for trade validators"""

    async def validate(
        self,
        agent: Any,  # TreasuryAgent instance
        trade: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a trade

        Args:
            agent: Agent submitting the trade
            trade: Trade details

        Returns:
            (is_valid: bool, error_message: Optional[str])
        """
        raise NotImplementedError


class PositionLimitValidator(TradeValidator):
    """
    Validates that trades don't exceed position limits

    Prevents single agent from taking excessive positions in any asset.
    """

    def __init__(self, db_connection):
        self.db = db_connection

    async def validate(
        self,
        agent: Any,
        trade: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if trade would exceed position limits

        Checks:
        1. Agent-specific position limits (if set)
        2. Default max position size
        3. Single trade size limits
        """
        agent_id = agent.agent_id
        trade_type = trade.get('trade_type')
        asset = trade.get('output_asset')  # Asset we're acquiring
        amount_usd = trade.get('expected_return', 0)  # Value in USD

        # Get position limits for this agent/asset
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT max_position_usd, max_trade_size_usd
            FROM position_limits
            WHERE agent_id = ? AND (asset = ? OR asset IS NULL)
            ORDER BY asset IS NULL  -- Specific limits take precedence
            LIMIT 1
        """, (agent_id, asset))

        limit_row = cursor.fetchone()

        if not limit_row:
            # No limits set - use defaults
            max_position = Decimal('100000')  # $100K default
            max_trade_size = Decimal('50000')  # $50K default
            logger.warning(f"No position limits set for {agent_id}/{asset}, using defaults")
        else:
            max_position = Decimal(str(limit_row[0]))
            max_trade_size = Decimal(str(limit_row[1]))

        # Check single trade size
        if Decimal(str(amount_usd)) > max_trade_size:
            return False, f"Trade size ${amount_usd:,.2f} exceeds max ${max_trade_size:,.2f}"

        # Calculate current position in this asset
        cursor.execute("""
            SELECT COALESCE(SUM(
                CASE
                    WHEN output_asset = ? AND status = 'success'
                    THEN actual_return
                    ELSE 0
                END
            ), 0) as current_position_usd
            FROM trades
            WHERE agent_id = ?
        """, (asset, agent_id))

        current_position = Decimal(str(cursor.fetchone()[0]))

        # Check if new trade would exceed position limit
        new_position = current_position + Decimal(str(amount_usd))
        if new_position > max_position:
            return False, (
                f"Position limit exceeded: current ${current_position:,.2f} + "
                f"trade ${amount_usd:,.2f} = ${new_position:,.2f} > "
                f"limit ${max_position:,.2f}"
            )

        logger.info(
            f"Position check passed: {asset} position ${new_position:,.2f} / ${max_position:,.2f}"
        )
        return True, None


class SlippageValidator(TradeValidator):
    """
    Validates that expected slippage is within tolerance

    Prevents execution if slippage would be too high.
    """

    def __init__(self, max_slippage: Decimal = Decimal('0.01')):
        """
        Args:
            max_slippage: Maximum allowed slippage (default 1%)
        """
        self.max_slippage = max_slippage

    async def validate(
        self,
        agent: Any,
        trade: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if slippage is acceptable

        For swaps only - deposits/withdrawals don't have slippage.
        """
        trade_type = trade.get('trade_type')

        # Only validate swaps
        if trade_type not in ['swap', 'buy', 'sell']:
            return True, None

        expected_slippage = trade.get('slippage', 0)

        if Decimal(str(expected_slippage)) > self.max_slippage * 100:  # Convert to percentage
            return False, (
                f"Slippage {expected_slippage:.2f}% exceeds "
                f"maximum {self.max_slippage * 100:.2f}%"
            )

        logger.info(f"Slippage check passed: {expected_slippage:.2f}%")
        return True, None


class CapitalValidator(TradeValidator):
    """
    Validates that agent has sufficient capital for trade

    Prevents overdrawing and maintains minimum capital balance.
    """

    def __init__(self, min_balance: Decimal = Decimal('1000')):
        """
        Args:
            min_balance: Minimum balance that must remain after trade
        """
        self.min_balance = min_balance

    async def validate(
        self,
        agent: Any,
        trade: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if agent has sufficient capital

        Checks:
        1. Agent has enough to cover trade
        2. Remaining balance >= min_balance
        """
        trade_cost = Decimal(str(trade.get('input_amount', 0)))
        gas_cost = Decimal(str(trade.get('gas_cost_usd', 0)))
        total_cost = trade_cost + gas_cost

        current_capital = agent.real_capital

        if current_capital < total_cost:
            return False, (
                f"Insufficient capital: need ${total_cost:,.2f}, "
                f"have ${current_capital:,.2f}"
            )

        remaining_capital = current_capital - total_cost
        if remaining_capital < self.min_balance:
            return False, (
                f"Trade would leave balance ${remaining_capital:,.2f} "
                f"below minimum ${self.min_balance:,.2f}"
            )

        logger.info(
            f"Capital check passed: ${current_capital:,.2f} - "
            f"${total_cost:,.2f} = ${remaining_capital:,.2f}"
        )
        return True, None


class DailyTradeCountValidator(TradeValidator):
    """
    Validates that agent hasn't exceeded daily trade limit

    Prevents runaway trading and excessive gas costs.
    """

    def __init__(self, db_connection, max_daily_trades: int = 100):
        """
        Args:
            db_connection: Database connection
            max_daily_trades: Maximum trades per day per agent
        """
        self.db = db_connection
        self.max_daily_trades = max_daily_trades

    async def validate(
        self,
        agent: Any,
        trade: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if agent has exceeded daily trade limit
        """
        agent_id = agent.agent_id
        today = datetime.utcnow().date()

        cursor = self.db.cursor()
        cursor.execute("""
            SELECT COUNT(*)
            FROM trades
            WHERE agent_id = ?
            AND DATE(submitted_at) = ?
        """, (agent_id, today))

        trades_today = cursor.fetchone()[0]

        if trades_today >= self.max_daily_trades:
            return False, (
                f"Daily trade limit reached: {trades_today}/{self.max_daily_trades} trades today"
            )

        logger.info(f"Daily trade count: {trades_today}/{self.max_daily_trades}")
        return True, None


class CompositeValidator(TradeValidator):
    """
    Composite validator that runs multiple validators

    All validators must pass for trade to be valid.
    """

    def __init__(self, validators: List[TradeValidator]):
        """
        Args:
            validators: List of validators to run
        """
        self.validators = validators

    async def validate(
        self,
        agent: Any,
        trade: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Run all validators in sequence

        Returns:
            (True, None) if all pass
            (False, error) if any fail (returns first failure)
        """
        for validator in self.validators:
            is_valid, error = await validator.validate(agent, trade)
            if not is_valid:
                validator_name = validator.__class__.__name__
                logger.warning(f"{validator_name} failed: {error}")
                return False, f"{validator_name}: {error}"

        logger.info(f"All {len(self.validators)} validators passed")
        return True, None


# Convenience function to create standard validator
def create_standard_validator(db_connection) -> CompositeValidator:
    """
    Create standard validator with all safety checks

    Args:
        db_connection: Database connection

    Returns:
        CompositeValidator with all standard validators
    """
    return CompositeValidator([
        CapitalValidator(min_balance=Decimal('1000')),
        SlippageValidator(max_slippage=Decimal('0.01')),  # 1%
        PositionLimitValidator(db_connection),
        DailyTradeCountValidator(db_connection, max_daily_trades=100)
    ])

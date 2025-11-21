"""
Trading Engine - Executes trades on behalf of Treasury Agents

CRITICAL: This component controls real capital.
All trades must be validated before execution.
Emergency stop must work instantly.
"""

import asyncio
import uuid
import sqlite3
import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .validators import TradeValidator, create_standard_validator
from .protocols.base import ProtocolAdapter
from .protocols.simulation import SimulationAdapter

logger = logging.getLogger(__name__)


class TradingEngineError(Exception):
    """Base exception for trading engine errors"""
    pass


class TradingDisabledError(TradingEngineError):
    """Raised when attempting to trade while engine is stopped"""
    pass


class ValidationError(TradingEngineError):
    """Raised when trade validation fails"""
    pass


class TradingEngine:
    """
    Core trading engine - Executes trades with safety controls

    Features:
    - Validates all trades before execution
    - Async execution with retry logic
    - Emergency stop/resume
    - Comprehensive logging
    - Position limit enforcement
    - Capital tracking
    """

    def __init__(
        self,
        db_path: str,
        protocols: Dict[str, ProtocolAdapter],
        validator: Optional[TradeValidator] = None
    ):
        """
        Initialize trading engine

        Args:
            db_path: Path to SQLite database
            protocols: Dict of protocol adapters {protocol_name: adapter}
            validator: Trade validator (uses standard validator if None)
        """
        self.db_path = db_path
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.protocols = protocols
        self.validator = validator or create_standard_validator(self.db)

        # Safety controls
        self.trading_enabled = True  # Can be disabled via emergency_stop()
        self.max_concurrent_trades = 10  # Limit parallel executions

        # Execution tracking
        self.pending_trades: Dict[str, asyncio.Task] = {}
        self.execution_lock = asyncio.Lock()

        logger.info("Trading Engine initialized")
        logger.info(f"Protocols loaded: {list(protocols.keys())}")
        logger.info(f"Trading enabled: {self.trading_enabled}")

    async def submit_trade(
        self,
        agent: Any,  # TreasuryAgent instance
        trade: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Submit a trade for execution

        Args:
            agent: Agent submitting the trade
            trade: Trade details
                {
                    'trade_type': str,  # swap, deposit, withdraw
                    'protocol': str,    # aave, uniswap, simulation
                    'input_asset': str,
                    'input_amount': Decimal,
                    'output_asset': str,
                    'expected_return': Decimal,
                    'gas_cost_usd': Decimal,
                    'slippage': Decimal (optional)
                }

        Returns:
            {
                'trade_id': str,
                'status': str,  # submitted, rejected
                'error': Optional[str]
            }

        Raises:
            TradingDisabledError: If trading is stopped
            ValidationError: If trade validation fails
        """
        # CRITICAL: Check if trading is enabled
        if not self.trading_enabled:
            logger.error("Trade rejected: Trading is disabled")
            raise TradingDisabledError("Trading is currently disabled via emergency stop")

        # Generate trade ID
        trade_id = str(uuid.uuid4())
        trade['trade_id'] = trade_id
        trade['agent_id'] = agent.agent_id

        logger.info(f"[{trade_id}] Trade submitted by {agent.agent_id}")

        # STEP 1: VALIDATE TRADE (CRITICAL - MUST HAPPEN BEFORE EXECUTION)
        is_valid, error = await self.validate_trade(agent, trade)

        if not is_valid:
            logger.error(f"[{trade_id}] Validation failed: {error}")
            self._log_trade_to_db(trade, 'failed', error=error)
            raise ValidationError(f"Trade validation failed: {error}")

        # STEP 2: Record trade as pending
        self._log_trade_to_db(trade, 'pending')

        # STEP 3: Execute trade asynchronously
        task = asyncio.create_task(self._execute_trade(agent, trade))
        async with self.execution_lock:
            self.pending_trades[trade_id] = task

        logger.info(f"[{trade_id}] Trade queued for execution")

        return {
            'trade_id': trade_id,
            'status': 'submitted',
            'error': None
        }

    async def validate_trade(
        self,
        agent: Any,
        trade: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate trade before execution

        CRITICAL: This must always be called before execute_trade()

        Args:
            agent: Agent submitting trade
            trade: Trade details

        Returns:
            (is_valid: bool, error_message: Optional[str])
        """
        logger.info(f"[{trade.get('trade_id')}] Validating trade...")

        # Run all validators
        is_valid, error = await self.validator.validate(agent, trade)

        if is_valid:
            logger.info(f"[{trade.get('trade_id')}] Validation passed ✓")
        else:
            logger.warning(f"[{trade.get('trade_id')}] Validation failed: {error}")

        return is_valid, error

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def _execute_trade(
        self,
        agent: Any,
        trade: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute trade with retry logic

        CRITICAL SAFETY:
        - Only called after validation passes
        - Retries on transient failures (network issues)
        - Updates capital ONLY on success
        - Logs all executions

        Args:
            agent: Agent instance
            trade: Trade details

        Returns:
            Execution result

        Raises:
            Exception: On execution failure (after retries)
        """
        trade_id = trade['trade_id']
        protocol_name = trade['protocol']
        trade_type = trade['trade_type']

        logger.info(f"[{trade_id}] Executing {trade_type} on {protocol_name}...")

        # Update status to executing
        self._update_trade_status(trade_id, 'executing')

        try:
            # Get protocol adapter
            if protocol_name not in self.protocols:
                raise TradingEngineError(f"Protocol '{protocol_name}' not found")

            protocol = self.protocols[protocol_name]

            # Execute trade based on type
            if trade_type == 'deposit':
                result = await protocol.deposit(
                    asset=trade['output_asset'],
                    amount=trade['input_amount']
                )
            elif trade_type == 'withdraw':
                result = await protocol.withdraw(
                    asset=trade['output_asset'],
                    amount=trade['input_amount']
                )
            elif trade_type in ['swap', 'buy', 'sell']:
                min_output = trade.get('min_output_amount')
                result = await protocol.swap(
                    input_asset=trade['input_asset'],
                    output_asset=trade['output_asset'],
                    input_amount=trade['input_amount'],
                    min_output_amount=min_output
                )
            else:
                raise TradingEngineError(f"Unknown trade type: {trade_type}")

            # Check if execution succeeded
            if not result.get('success'):
                error = result.get('error', 'Unknown error')
                logger.error(f"[{trade_id}] Execution failed: {error}")
                self._update_trade_status(trade_id, 'failed', error=error)
                raise TradingEngineError(f"Trade execution failed: {error}")

            # CRITICAL: Update agent capital ONLY on successful execution
            pnl = self._calculate_pnl(trade, result)
            agent.real_capital += pnl

            logger.info(f"[{trade_id}] Execution successful ✓")
            logger.info(f"[{trade_id}] P&L: ${pnl:,.2f} | New capital: ${agent.real_capital:,.2f}")

            # Update trade as successful
            self._update_trade_status(
                trade_id,
                'success',
                actual_return=result.get('output_amount'),
                gas_cost=result.get('gas_cost_usd'),
                tx_hash=result.get('tx_hash'),
                execution_price=result.get('execution_price')
            )

            # Remove from pending
            async with self.execution_lock:
                if trade_id in self.pending_trades:
                    del self.pending_trades[trade_id]

            return result

        except Exception as e:
            logger.error(f"[{trade_id}] Execution error: {str(e)}")
            self._update_trade_status(trade_id, 'failed', error=str(e))

            # Remove from pending
            async with self.execution_lock:
                if trade_id in self.pending_trades:
                    del self.pending_trades[trade_id]

            raise

    def _calculate_pnl(
        self,
        trade: Dict[str, Any],
        result: Dict[str, Any]
    ) -> Decimal:
        """
        Calculate P&L from trade

        Args:
            trade: Original trade details
            result: Execution result

        Returns:
            P&L in USD (positive = profit, negative = loss)
        """
        # For now, simplified: output - input - gas
        input_amount = Decimal(str(trade.get('input_amount', 0)))
        output_amount = Decimal(str(result.get('output_amount', 0)))
        gas_cost = Decimal(str(result.get('gas_cost_usd', 0)))

        # This is simplified - in reality would need to convert assets to USD
        # For simulation mode, assuming amounts are in USD equivalent
        pnl = output_amount - input_amount - gas_cost

        return pnl

    def emergency_stop(self):
        """
        EMERGENCY STOP - Immediately disable all trading

        CRITICAL SAFETY FEATURE
        - Call this if something goes wrong
        - Prevents any new trades from executing
        - Does NOT cancel already executing trades (can't reverse blockchain txs)
        """
        logger.critical("🚨 EMERGENCY STOP ACTIVATED 🚨")
        self.trading_enabled = False

        # Log to execution log
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO execution_log (trade_id, level, message)
            VALUES (?, ?, ?)
        """, ('system', 'critical', 'EMERGENCY STOP ACTIVATED'))
        self.db.commit()

        logger.critical(f"Trading disabled. {len(self.pending_trades)} trades still executing.")

    def emergency_resume(self):
        """
        Resume trading after emergency stop

        Use with caution - only after issue is resolved.
        """
        logger.warning("Resuming trading after emergency stop")
        self.trading_enabled = True

        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO execution_log (trade_id, level, message)
            VALUES (?, ?, ?)
        """, ('system', 'warning', 'Trading resumed after emergency stop'))
        self.db.commit()

        logger.info("Trading re-enabled ✓")

    def _log_trade_to_db(
        self,
        trade: Dict[str, Any],
        status: str,
        error: Optional[str] = None
    ):
        """
        Log trade to database

        Args:
            trade: Trade details
            status: Trade status
            error: Error message (if failed)
        """
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO trades (
                trade_id, agent_id, trade_type, status, protocol,
                input_asset, input_amount, output_asset, expected_return,
                gas_cost_usd, error_message, submitted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade['trade_id'],
            trade.get('agent_id'),
            trade['trade_type'],
            status,
            trade.get('protocol'),
            trade.get('input_asset'),
            float(trade.get('input_amount', 0)),
            trade.get('output_asset'),
            float(trade.get('expected_return', 0)),
            float(trade.get('gas_cost_usd', 0)),
            error,
            datetime.utcnow()
        ))
        self.db.commit()

    def _update_trade_status(
        self,
        trade_id: str,
        status: str,
        error: Optional[str] = None,
        actual_return: Optional[Decimal] = None,
        gas_cost: Optional[Decimal] = None,
        tx_hash: Optional[str] = None,
        execution_price: Optional[Decimal] = None
    ):
        """
        Update trade status in database

        Args:
            trade_id: Trade ID
            status: New status
            error: Error message (if failed)
            actual_return: Actual output amount
            gas_cost: Actual gas cost
            tx_hash: Blockchain transaction hash
            execution_price: Actual execution price
        """
        cursor = self.db.cursor()

        timestamp_field = f"{status}_at"
        if status == 'executing':
            timestamp_field = 'executed_at'

        cursor.execute(f"""
            UPDATE trades
            SET status = ?,
                {timestamp_field} = ?,
                error_message = COALESCE(?, error_message),
                actual_return = COALESCE(?, actual_return),
                gas_cost_usd = COALESCE(?, gas_cost_usd),
                tx_hash = COALESCE(?, tx_hash),
                execution_price = COALESCE(?, execution_price)
            WHERE trade_id = ?
        """, (
            status,
            datetime.utcnow(),
            error,
            float(actual_return) if actual_return else None,
            float(gas_cost) if gas_cost else None,
            tx_hash,
            float(execution_price) if execution_price else None,
            trade_id
        ))
        self.db.commit()

    async def get_status(self) -> Dict[str, Any]:
        """
        Get trading engine status

        Returns:
            {
                'trading_enabled': bool,
                'pending_trades': int,
                'protocols': List[str],
                'recent_executions': List[Dict]
            }
        """
        cursor = self.db.cursor()

        # Get recent executions
        cursor.execute("""
            SELECT trade_id, agent_id, trade_type, status, protocol,
                   input_amount, output_asset, actual_return, executed_at
            FROM trades
            ORDER BY submitted_at DESC
            LIMIT 10
        """)

        recent = [
            {
                'trade_id': row[0],
                'agent_id': row[1],
                'trade_type': row[2],
                'status': row[3],
                'protocol': row[4],
                'input_amount': row[5],
                'output_asset': row[6],
                'actual_return': row[7],
                'executed_at': row[8]
            }
            for row in cursor.fetchall()
        ]

        return {
            'trading_enabled': self.trading_enabled,
            'pending_trades': len(self.pending_trades),
            'protocols': list(self.protocols.keys()),
            'recent_executions': recent
        }

"""
Coracle Database Layer
=======================
PostgreSQL persistence for contracts, signals, and predictions.

Schema includes:
- signal_registry: Signal definitions and weights
- contract_generations: Trading contracts
- signal_snapshots: Historical signal data
- predictions: Prediction tracking for Brier score
- capacity_oracle: Capacity state per asset
"""
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import logging

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

from app.config import get_settings
from app.models import TradingContract, TradeOutcome, ContractGrade

logger = logging.getLogger(__name__)


# SQL Schema
SCHEMA_SQL = """
-- Signal Registry
CREATE TABLE IF NOT EXISTS signal_registry (
    id SERIAL PRIMARY KEY,
    signal_id VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(20) NOT NULL,
    tier VARCHAR(20) NOT NULL,
    weight DECIMAL(4,3) NOT NULL,
    update_frequency_ms INTEGER,
    description TEXT,
    calculation_logic JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Contract Generations
CREATE TABLE IF NOT EXISTS contract_generations (
    contract_id UUID PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    direction VARCHAR(5) NOT NULL,
    entry_price DECIMAL(20,8) NOT NULL,
    entry_type VARCHAR(20) NOT NULL,
    stop_loss_price DECIMAL(20,8) NOT NULL,
    stop_loss_distance_pct DECIMAL(8,4),
    take_profits JSONB NOT NULL,
    confidence_score DECIMAL(5,4) NOT NULL,
    grade CHAR(1) NOT NULL,
    confluence_multiplier DECIMAL(4,3),
    sacred_gate_passed BOOLEAN NOT NULL,
    sacred_gate_details JSONB,
    signals_snapshot JSONB,
    generated_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    outcome VARCHAR(20) DEFAULT 'PENDING',
    actual_exit_price DECIMAL(20,8),
    actual_pnl_pct DECIMAL(8,4),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Signal Snapshots (Time-series)
CREATE TABLE IF NOT EXISTS signal_snapshots (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    signals JSONB NOT NULL,
    source_availability JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Predictions (for Brier score tracking)
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    contract_id UUID REFERENCES contract_generations(contract_id),
    symbol VARCHAR(10) NOT NULL,
    direction VARCHAR(5) NOT NULL,
    predicted_probability DECIMAL(5,4) NOT NULL,
    actual_outcome INTEGER,  -- 1 = win, 0 = loss
    brier_contribution DECIMAL(8,6),
    created_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ
);

-- Capacity Oracle State
CREATE TABLE IF NOT EXISTS capacity_oracle (
    id SERIAL PRIMARY KEY,
    asset VARCHAR(10) UNIQUE NOT NULL,
    capacity_level VARCHAR(20) NOT NULL,
    max_position_pct DECIMAL(5,2) NOT NULL,
    contributing_signals JSONB,
    updated_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_contracts_symbol ON contract_generations(symbol);
CREATE INDEX IF NOT EXISTS idx_contracts_grade ON contract_generations(grade);
CREATE INDEX IF NOT EXISTS idx_contracts_generated ON contract_generations(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_contracts_outcome ON contract_generations(outcome);
CREATE INDEX IF NOT EXISTS idx_signals_symbol_time ON signal_snapshots(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_symbol ON predictions(symbol);
CREATE INDEX IF NOT EXISTS idx_predictions_resolved ON predictions(resolved_at);
"""


class Database:
    """
    Async PostgreSQL database interface.
    
    Handles connection pooling and provides methods for
    CRUD operations on contracts and signals.
    """
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False
    
    async def connect(self):
        """Connect to database and create pool."""
        if not ASYNCPG_AVAILABLE:
            logger.warning("asyncpg not available - database features disabled")
            return
        
        try:
            # Parse URL for asyncpg
            url = self.database_url.replace("postgresql+asyncpg://", "postgresql://")
            
            self.pool = await asyncpg.create_pool(
                url,
                min_size=2,
                max_size=10,
                command_timeout=30
            )
            
            # Initialize schema
            await self._init_schema()
            self._initialized = True
            
            logger.info("Database connected and initialized")
            
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            self._initialized = False
    
    async def disconnect(self):
        """Close database pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            self._initialized = False
    
    async def _init_schema(self):
        """Initialize database schema."""
        if not self.pool:
            return
        
        async with self.pool.acquire() as conn:
            await conn.execute(SCHEMA_SQL)
    
    @asynccontextmanager
    async def _get_conn(self):
        """Get connection from pool."""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        async with self.pool.acquire() as conn:
            yield conn
    
    # ========================================================================
    # CONTRACT OPERATIONS
    # ========================================================================
    
    async def save_contract(self, contract: TradingContract) -> bool:
        """Save a trading contract."""
        if not self._initialized:
            return False
        
        try:
            async with self._get_conn() as conn:
                await conn.execute("""
                    INSERT INTO contract_generations (
                        contract_id, symbol, direction, entry_price, entry_type,
                        stop_loss_price, stop_loss_distance_pct, take_profits,
                        confidence_score, grade, confluence_multiplier,
                        sacred_gate_passed, sacred_gate_details, signals_snapshot,
                        generated_at, expires_at, outcome
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                    ON CONFLICT (contract_id) DO UPDATE SET
                        outcome = EXCLUDED.outcome,
                        actual_exit_price = EXCLUDED.actual_exit_price,
                        actual_pnl_pct = EXCLUDED.actual_pnl_pct,
                        resolved_at = EXCLUDED.resolved_at
                """,
                    contract.contract_id,
                    contract.symbol,
                    contract.direction.value,
                    float(contract.entry_price),
                    contract.entry_type,
                    float(contract.stop_loss.price),
                    float(contract.stop_loss.distance_pct),
                    json.dumps([tp.dict() for tp in contract.take_profits]),
                    float(contract.confidence_score),
                    contract.grade.value,
                    float(contract.confluence_multiplier),
                    contract.sacred_gate.passed,
                    json.dumps(contract.sacred_gate.dict()),
                    json.dumps(contract.signals_snapshot),
                    contract.generated_at,
                    contract.expires_at,
                    contract.outcome.value
                )
            return True
            
        except Exception as e:
            logger.error(f"Failed to save contract: {e}")
            return False
    
    async def get_contract(self, contract_id: str) -> Optional[Dict]:
        """Get contract by ID."""
        if not self._initialized:
            return None
        
        try:
            async with self._get_conn() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM contract_generations WHERE contract_id = $1",
                    contract_id
                )
                return dict(row) if row else None
                
        except Exception as e:
            logger.error(f"Failed to get contract: {e}")
            return None
    
    async def list_contracts(
        self,
        symbol: Optional[str] = None,
        grade: Optional[str] = None,
        outcome: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """List contracts with filters."""
        if not self._initialized:
            return []
        
        try:
            async with self._get_conn() as conn:
                query = "SELECT * FROM contract_generations WHERE 1=1"
                params = []
                param_idx = 1
                
                if symbol:
                    query += f" AND symbol = ${param_idx}"
                    params.append(symbol)
                    param_idx += 1
                
                if grade:
                    query += f" AND grade = ${param_idx}"
                    params.append(grade)
                    param_idx += 1
                
                if outcome:
                    query += f" AND outcome = ${param_idx}"
                    params.append(outcome)
                    param_idx += 1
                
                query += f" ORDER BY generated_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
                params.extend([limit, offset])
                
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to list contracts: {e}")
            return []
    
    async def resolve_contract(
        self,
        contract_id: str,
        outcome: TradeOutcome,
        exit_price: float,
        pnl_pct: float
    ) -> bool:
        """Resolve a contract with outcome."""
        if not self._initialized:
            return False
        
        try:
            async with self._get_conn() as conn:
                await conn.execute("""
                    UPDATE contract_generations
                    SET outcome = $2, actual_exit_price = $3, 
                        actual_pnl_pct = $4, resolved_at = $5
                    WHERE contract_id = $1
                """,
                    contract_id,
                    outcome.value,
                    exit_price,
                    pnl_pct,
                    datetime.now(timezone.utc)
                )
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve contract: {e}")
            return False
    
    # ========================================================================
    # SIGNAL OPERATIONS
    # ========================================================================
    
    async def save_signal_snapshot(
        self,
        symbol: str,
        price: float,
        signals: Dict[str, Any],
        source_availability: Dict[str, bool]
    ) -> bool:
        """Save signal snapshot for historical analysis."""
        if not self._initialized:
            return False
        
        try:
            async with self._get_conn() as conn:
                await conn.execute("""
                    INSERT INTO signal_snapshots 
                    (symbol, timestamp, price, signals, source_availability)
                    VALUES ($1, $2, $3, $4, $5)
                """,
                    symbol,
                    datetime.now(timezone.utc),
                    price,
                    json.dumps(signals),
                    json.dumps(source_availability)
                )
            return True
            
        except Exception as e:
            logger.error(f"Failed to save signal snapshot: {e}")
            return False
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    async def get_contract_stats(self, symbol: Optional[str] = None) -> Dict:
        """Get contract performance statistics."""
        if not self._initialized:
            return {"error": "Database not connected"}
        
        try:
            async with self._get_conn() as conn:
                where = "WHERE resolved_at IS NOT NULL"
                params = []
                
                if symbol:
                    where += " AND symbol = $1"
                    params.append(symbol)
                
                row = await conn.fetchrow(f"""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                        AVG(actual_pnl_pct) as avg_pnl,
                        AVG(POWER(confidence_score - CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END, 2)) as brier_score
                    FROM contract_generations
                    {where}
                """, *params)
                
                total = row["total"] or 0
                wins = row["wins"] or 0
                
                return {
                    "total_contracts": total,
                    "wins": wins,
                    "win_rate": wins / total if total > 0 else 0,
                    "avg_pnl_pct": float(row["avg_pnl"] or 0),
                    "brier_score": float(row["brier_score"] or 0)
                }
                
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}


# Global database instance
_database: Optional[Database] = None


async def get_database() -> Database:
    """Get or create database instance."""
    global _database
    
    if _database is None:
        settings = get_settings()
        _database = Database(settings.database_url)
        await _database.connect()
    
    return _database



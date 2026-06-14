#!/usr/bin/env python3
"""
ALIGNMENT ECONOMICS - LEDGER STORAGE
=====================================

SQLite-based persistence for all positions, debts, and flows.
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict
from pathlib import Path

from models.core import (
    Position, PositionType,
    Debt, DebtClassification, DebtStatus,
    Flow, FlowPurpose,
    Institution, InstitutionType,
    SystemHealth
)

# ============================================================================
# DATABASE
# ============================================================================

DATA_DIR = Path(os.getenv("AE_DATA_DIR", "/opt/fpai/alignment-economics/data"))
DB_PATH = DATA_DIR / "ledger.db"


def get_db() -> sqlite3.Connection:
    """Get database connection."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Positions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id TEXT PRIMARY KEY,
            name TEXT,
            type TEXT,
            value TEXT,
            currency TEXT DEFAULT 'USD',
            source TEXT,
            holder TEXT DEFAULT 'steward',
            created_at TEXT,
            updated_at TEXT,
            last_flow_at TEXT,
            notes TEXT,
            tags TEXT,
            metadata TEXT
        )
    """)
    
    # Debts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS debts (
            id TEXT PRIMARY KEY,
            name TEXT,
            classification TEXT,
            principal TEXT,
            interest_rate TEXT,
            currency TEXT DEFAULT 'USD',
            lender TEXT,
            borrower TEXT DEFAULT 'steward',
            participation_score REAL DEFAULT 0.0,
            yield_accumulated TEXT DEFAULT '0',
            payments_made TEXT DEFAULT '0',
            status TEXT DEFAULT 'active',
            created_at TEXT,
            forgiven_at TEXT,
            notes TEXT,
            metadata TEXT
        )
    """)
    
    # Flows table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flows (
            id TEXT PRIMARY KEY,
            from_position TEXT,
            to_position TEXT,
            amount TEXT,
            currency TEXT DEFAULT 'USD',
            purpose TEXT,
            description TEXT,
            timestamp TEXT,
            approved_by TEXT DEFAULT 'steward',
            auto_approved INTEGER DEFAULT 0
        )
    """)
    
    # Institutions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS institutions (
            id TEXT PRIMARY KEY,
            name TEXT,
            type TEXT,
            ownership_stake TEXT DEFAULT '0',
            governance_influence REAL DEFAULT 0.0,
            cost_of_capital TEXT DEFAULT '0',
            total_exposure TEXT DEFAULT '0',
            created_at TEXT,
            notes TEXT
        )
    """)
    
    # Health snapshots table (for trending)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS health_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            capital_velocity REAL,
            circulation_efficiency REAL,
            idle_capital_ratio REAL,
            debt_resolution_rate REAL,
            stress_index REAL,
            liquidity_ratio REAL,
            total_capital TEXT,
            total_debt TEXT,
            calculated_at TEXT
        )
    """)
    
    conn.commit()
    conn.close()


# ============================================================================
# POSITION OPERATIONS
# ============================================================================

class PositionStore:
    """CRUD operations for positions."""
    
    @staticmethod
    def create(position: Position) -> Position:
        """Create a new position."""
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO positions 
            (id, name, type, value, currency, source, holder, 
             created_at, updated_at, last_flow_at, notes, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            position.id, position.name, position.type.value,
            str(position.value), position.currency, position.source,
            position.holder, position.created_at.isoformat(),
            position.updated_at.isoformat(),
            position.last_flow_at.isoformat() if position.last_flow_at else None,
            position.notes, json.dumps(position.tags),
            json.dumps(position.metadata)
        ))
        
        conn.commit()
        conn.close()
        return position
    
    @staticmethod
    def get(id: str) -> Optional[Position]:
        """Get a position by ID."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM positions WHERE id = ?", (id,))
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            return None
        
        return Position(
            id=row["id"],
            name=row["name"],
            type=PositionType(row["type"]),
            value=Decimal(row["value"]),
            currency=row["currency"],
            source=row["source"],
            holder=row["holder"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_flow_at=datetime.fromisoformat(row["last_flow_at"]) if row["last_flow_at"] else None,
            notes=row["notes"] or "",
            tags=json.loads(row["tags"]) if row["tags"] else [],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {}
        )
    
    @staticmethod
    def list_all() -> List[Position]:
        """List all positions."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM positions ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        positions = []
        for row in rows:
            positions.append(Position(
                id=row["id"],
                name=row["name"],
                type=PositionType(row["type"]),
                value=Decimal(row["value"]),
                currency=row["currency"],
                source=row["source"],
                holder=row["holder"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                last_flow_at=datetime.fromisoformat(row["last_flow_at"]) if row["last_flow_at"] else None,
                notes=row["notes"] or "",
                tags=json.loads(row["tags"]) if row["tags"] else [],
            ))
        return positions
    
    @staticmethod
    def update(position: Position) -> Position:
        """Update a position."""
        conn = get_db()
        cursor = conn.cursor()
        
        position.updated_at = datetime.now()
        
        cursor.execute("""
            UPDATE positions SET
                name = ?, type = ?, value = ?, currency = ?,
                source = ?, holder = ?, updated_at = ?,
                last_flow_at = ?, notes = ?, tags = ?, metadata = ?
            WHERE id = ?
        """, (
            position.name, position.type.value, str(position.value),
            position.currency, position.source, position.holder,
            position.updated_at.isoformat(),
            position.last_flow_at.isoformat() if position.last_flow_at else None,
            position.notes, json.dumps(position.tags),
            json.dumps(position.metadata), position.id
        ))
        
        conn.commit()
        conn.close()
        return position
    
    @staticmethod
    def get_idle() -> List[Position]:
        """Get positions that are idle (no flow > 7 days)."""
        all_positions = PositionStore.list_all()
        return [p for p in all_positions if p.is_idle and p.value > 0]
    
    @staticmethod
    def get_by_type(type: PositionType) -> List[Position]:
        """Get positions by type."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM positions WHERE type = ?", (type.value,))
        rows = cursor.fetchall()
        conn.close()
        
        return [Position(
            id=row["id"],
            name=row["name"],
            type=PositionType(row["type"]),
            value=Decimal(row["value"]),
            currency=row["currency"],
            source=row["source"],
            holder=row["holder"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_flow_at=datetime.fromisoformat(row["last_flow_at"]) if row["last_flow_at"] else None,
            notes=row["notes"] or "",
        ) for row in rows]


# ============================================================================
# DEBT OPERATIONS
# ============================================================================

class DebtStore:
    """CRUD operations for debts."""
    
    @staticmethod
    def create(debt: Debt) -> Debt:
        """Create a new debt."""
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO debts 
            (id, name, classification, principal, interest_rate, currency,
             lender, borrower, participation_score, yield_accumulated,
             payments_made, status, created_at, forgiven_at, notes, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            debt.id, debt.name, debt.classification.value,
            str(debt.principal), str(debt.interest_rate), debt.currency,
            debt.lender, debt.borrower, debt.participation_score,
            str(debt.yield_accumulated), str(debt.payments_made),
            debt.status.value, debt.created_at.isoformat(),
            debt.forgiven_at.isoformat() if debt.forgiven_at else None,
            debt.notes, json.dumps(debt.metadata)
        ))
        
        conn.commit()
        conn.close()
        return debt
    
    @staticmethod
    def get(id: str) -> Optional[Debt]:
        """Get a debt by ID."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM debts WHERE id = ?", (id,))
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            return None
        
        return Debt(
            id=row["id"],
            name=row["name"],
            classification=DebtClassification(row["classification"]),
            principal=Decimal(row["principal"]),
            interest_rate=Decimal(row["interest_rate"]),
            currency=row["currency"],
            lender=row["lender"],
            borrower=row["borrower"],
            participation_score=row["participation_score"],
            yield_accumulated=Decimal(row["yield_accumulated"]),
            payments_made=Decimal(row["payments_made"]),
            status=DebtStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            forgiven_at=datetime.fromisoformat(row["forgiven_at"]) if row["forgiven_at"] else None,
            notes=row["notes"] or "",
            metadata=json.loads(row["metadata"]) if row["metadata"] else {}
        )
    
    @staticmethod
    def list_active() -> List[Debt]:
        """List all active debts."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM debts WHERE status = 'active' ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [Debt(
            id=row["id"],
            name=row["name"],
            classification=DebtClassification(row["classification"]),
            principal=Decimal(row["principal"]),
            interest_rate=Decimal(row["interest_rate"]),
            currency=row["currency"],
            lender=row["lender"],
            borrower=row["borrower"],
            participation_score=row["participation_score"],
            yield_accumulated=Decimal(row["yield_accumulated"]),
            payments_made=Decimal(row["payments_made"]),
            status=DebtStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            forgiven_at=datetime.fromisoformat(row["forgiven_at"]) if row["forgiven_at"] else None,
            notes=row["notes"] or "",
        ) for row in rows]
    
    @staticmethod
    def update(debt: Debt) -> Debt:
        """Update a debt."""
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE debts SET
                name = ?, classification = ?, principal = ?,
                interest_rate = ?, currency = ?, lender = ?,
                borrower = ?, participation_score = ?,
                yield_accumulated = ?, payments_made = ?,
                status = ?, forgiven_at = ?, notes = ?, metadata = ?
            WHERE id = ?
        """, (
            debt.name, debt.classification.value, str(debt.principal),
            str(debt.interest_rate), debt.currency, debt.lender,
            debt.borrower, debt.participation_score,
            str(debt.yield_accumulated), str(debt.payments_made),
            debt.status.value,
            debt.forgiven_at.isoformat() if debt.forgiven_at else None,
            debt.notes, json.dumps(debt.metadata), debt.id
        ))
        
        conn.commit()
        conn.close()
        return debt
    
    @staticmethod
    def get_ready_for_forgiveness() -> List[Debt]:
        """Get all debts ready to be forgiven."""
        active = DebtStore.list_active()
        return [d for d in active if d.check_forgiveness_ready()[0]]
    
    @staticmethod
    def forgive(debt: Debt, reason: str = "") -> Debt:
        """Forgive a debt."""
        debt.status = DebtStatus.FORGIVEN
        debt.forgiven_at = datetime.now()
        debt.notes += f"\nForgiven: {reason} at {debt.forgiven_at.isoformat()}"
        return DebtStore.update(debt)


# ============================================================================
# FLOW OPERATIONS
# ============================================================================

class FlowStore:
    """CRUD operations for flows."""
    
    @staticmethod
    def create(flow: Flow) -> Flow:
        """Create a new flow."""
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO flows 
            (id, from_position, to_position, amount, currency,
             purpose, description, timestamp, approved_by, auto_approved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            flow.id, flow.from_position, flow.to_position,
            str(flow.amount), flow.currency, flow.purpose.value,
            flow.description, flow.timestamp.isoformat(),
            flow.approved_by, 1 if flow.auto_approved else 0
        ))
        
        conn.commit()
        conn.close()
        return flow
    
    @staticmethod
    def list_recent(days: int = 30) -> List[Flow]:
        """List recent flows."""
        conn = get_db()
        cursor = conn.cursor()
        since = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute(
            "SELECT * FROM flows WHERE timestamp > ? ORDER BY timestamp DESC",
            (since,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [Flow(
            id=row["id"],
            from_position=row["from_position"],
            to_position=row["to_position"],
            amount=Decimal(row["amount"]),
            currency=row["currency"],
            purpose=FlowPurpose(row["purpose"]),
            description=row["description"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            approved_by=row["approved_by"],
            auto_approved=bool(row["auto_approved"])
        ) for row in rows]
    
    @staticmethod
    def get_velocity(days: int = 30) -> float:
        """Calculate capital velocity (flows / total capital)."""
        conn = get_db()
        cursor = conn.cursor()
        
        # Total flows in period
        since = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute(
            "SELECT SUM(CAST(amount AS REAL)) as total FROM flows WHERE timestamp > ?",
            (since,)
        )
        total_flows = cursor.fetchone()["total"] or 0
        
        # Total capital
        cursor.execute("SELECT SUM(CAST(value AS REAL)) as total FROM positions")
        total_capital = cursor.fetchone()["total"] or 1  # Avoid div by zero
        
        conn.close()
        
        return total_flows / total_capital if total_capital > 0 else 0


# ============================================================================
# HEALTH CALCULATION
# ============================================================================

def calculate_health() -> SystemHealth:
    """Calculate current system health metrics."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Total capital
    cursor.execute("SELECT SUM(CAST(value AS REAL)) as total FROM positions")
    total_capital = Decimal(str(cursor.fetchone()["total"] or 0))
    
    # Total active debt
    cursor.execute(
        "SELECT SUM(CAST(principal AS REAL) - CAST(payments_made AS REAL)) as total "
        "FROM debts WHERE status = 'active'"
    )
    total_debt = Decimal(str(cursor.fetchone()["total"] or 0))
    
    conn.close()
    
    # Get other metrics
    all_positions = PositionStore.list_all()
    idle_positions = PositionStore.get_idle()
    active_debts = DebtStore.list_active()
    recent_flows = FlowStore.list_recent(30)
    
    # Calculate velocity
    velocity = FlowStore.get_velocity(30)
    
    # Idle capital ratio
    idle_value = sum(p.value for p in idle_positions)
    idle_ratio = float(idle_value / total_capital) if total_capital > 0 else 0
    
    # Circulation efficiency (capital that has flowed in last 30 days)
    flowed_capital = sum(f.amount for f in recent_flows)
    circ_efficiency = float(flowed_capital / total_capital) if total_capital > 0 else 0
    
    # Cash/liquid ratio
    cash_positions = PositionStore.get_by_type(PositionType.CASH)
    cash_value = sum(p.value for p in cash_positions)
    liquidity_ratio = float(cash_value / total_capital) if total_capital > 0 else 0
    
    # Stress index (composite)
    stress = min(1.0, (
        (idle_ratio * 0.3) +  # Idle capital is stress
        (float(total_debt / total_capital) * 0.4 if total_capital > 0 else 0) +  # Debt ratio
        ((1 - velocity) * 0.3)  # Low velocity is stress
    ))
    
    health = SystemHealth(
        capital_velocity=velocity,
        circulation_efficiency=circ_efficiency,
        idle_capital_ratio=idle_ratio,
        debt_resolution_rate=0,  # TODO: calculate from history
        default_rate=0,
        average_time_to_forgiveness=0,  # TODO: calculate from history
        stress_index=stress,
        liquidity_ratio=liquidity_ratio,
        total_capital=total_capital,
        total_debt=total_debt,
        net_position=total_capital - total_debt
    )
    
    return health


# ============================================================================
# INITIALIZATION
# ============================================================================

# Initialize DB on import
init_db()



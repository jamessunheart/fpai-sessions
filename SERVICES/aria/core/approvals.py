"""
ARIA APPROVAL SYSTEM
====================

Smart approval system for Aria's actions.

Decision categories:
- AUTO-APPROVE: Monitoring, reading, info queries, cost savings
- REQUIRES APPROVAL: Spending money, making changes, executing trades

Philosophy:
- Saving money = always good (auto)
- Spending money = needs justification (approval)
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
import httpx

logger = logging.getLogger("aria.approvals")

# Database
APPROVALS_DB = Path("/opt/fpai/aria/approvals.db")


class DecisionCategory(str, Enum):
    """Categories of decisions Aria can make."""
    MONITORING = "monitoring"      # Check status, read logs, view metrics
    INFORMATION = "information"    # Answer questions, explain systems
    SAVINGS = "savings"            # Scale down, stop unused services
    SPENDING = "spending"          # Add GPUs, deploy services, API calls
    CHANGES = "changes"            # Modify configs, restart services
    TRADING = "trading"            # Execute trades, change positions


# Which categories auto-approve
AUTO_APPROVE_CATEGORIES = {
    DecisionCategory.MONITORING,
    DecisionCategory.INFORMATION,
    DecisionCategory.SAVINGS,
}

# Which require human approval
REQUIRES_APPROVAL = {
    DecisionCategory.SPENDING,
    DecisionCategory.CHANGES,
    DecisionCategory.TRADING,
}


@dataclass
class Decision:
    """A decision that Aria wants to make."""
    id: str
    category: DecisionCategory
    action: str
    reason: str
    context: Dict[str, Any]
    estimated_cost: float = 0.0
    risk_level: str = "low"  # low, medium, high
    status: str = "pending"  # pending, approved, denied, executed, failed
    created_at: str = ""
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    executed_at: Optional[str] = None
    result: Optional[str] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
    
    def requires_approval(self) -> bool:
        """Check if this decision requires human approval."""
        return self.category in REQUIRES_APPROVAL
    
    def can_auto_approve(self) -> bool:
        """Check if this decision can be auto-approved."""
        return self.category in AUTO_APPROVE_CATEGORIES


class ApprovalSystem:
    """
    Manages Aria's decision-making with appropriate approvals.
    
    Features:
    - Auto-approve safe actions
    - Request approval for risky actions
    - Track decisions and outcomes
    - Notify via Telegram
    """
    
    def __init__(self, db_path: Path = APPROVALS_DB):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self.pending_decisions: Dict[str, Decision] = {}
        logger.info("ApprovalSystem initialized")
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                action TEXT NOT NULL,
                reason TEXT NOT NULL,
                context TEXT,
                estimated_cost REAL DEFAULT 0,
                risk_level TEXT DEFAULT 'low',
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                approved_at TEXT,
                approved_by TEXT,
                executed_at TEXT,
                result TEXT
            )
        """)
        
        c.execute("CREATE INDEX IF NOT EXISTS idx_decisions_status ON decisions(status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_decisions_category ON decisions(category)")
        
        conn.commit()
        conn.close()
    
    async def decide(
        self,
        category: DecisionCategory,
        action: str,
        reason: str,
        context: Dict[str, Any] = None,
        estimated_cost: float = 0.0,
        risk_level: str = "low"
    ) -> Decision:
        """
        Make a decision with appropriate approval flow.
        
        Returns:
            Decision object with status indicating if approved or pending
        """
        # Create decision
        decision = Decision(
            id=f"dec_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
            category=category,
            action=action,
            reason=reason,
            context=context or {},
            estimated_cost=estimated_cost,
            risk_level=risk_level
        )
        
        # Save to database
        self._save_decision(decision)
        
        # Check if auto-approve
        if decision.can_auto_approve():
            decision.status = "approved"
            decision.approved_at = datetime.utcnow().isoformat()
            decision.approved_by = "aria_auto"
            self._update_decision(decision)
            logger.info(f"✅ Auto-approved: {action}")
            return decision
        
        # Requires human approval
        decision.status = "pending"
        self.pending_decisions[decision.id] = decision
        
        # Notify human
        await self._notify_pending(decision)
        logger.info(f"📋 Awaiting approval: {action}")
        
        return decision
    
    async def approve(
        self,
        decision_id: str,
        approved_by: str = "user"
    ) -> Optional[Decision]:
        """Approve a pending decision."""
        decision = self._get_decision(decision_id)
        if not decision or decision.status != "pending":
            return None
        
        decision.status = "approved"
        decision.approved_at = datetime.utcnow().isoformat()
        decision.approved_by = approved_by
        
        self._update_decision(decision)
        self.pending_decisions.pop(decision_id, None)
        
        logger.info(f"✅ Approved by {approved_by}: {decision.action}")
        return decision
    
    async def deny(
        self,
        decision_id: str,
        denied_by: str = "user"
    ) -> Optional[Decision]:
        """Deny a pending decision."""
        decision = self._get_decision(decision_id)
        if not decision or decision.status != "pending":
            return None
        
        decision.status = "denied"
        decision.approved_by = denied_by  # Reuse field for who denied
        
        self._update_decision(decision)
        self.pending_decisions.pop(decision_id, None)
        
        logger.info(f"❌ Denied by {denied_by}: {decision.action}")
        return decision
    
    async def execute(
        self,
        decision: Decision,
        executor_fn: Any
    ) -> Decision:
        """
        Execute an approved decision.
        
        Args:
            decision: The approved decision
            executor_fn: Async function to execute the action
            
        Returns:
            Updated decision with execution result
        """
        if decision.status != "approved":
            decision.result = "Cannot execute: not approved"
            return decision
        
        try:
            result = await executor_fn()
            decision.status = "executed"
            decision.executed_at = datetime.utcnow().isoformat()
            decision.result = str(result) if result else "Success"
        except Exception as e:
            decision.status = "failed"
            decision.executed_at = datetime.utcnow().isoformat()
            decision.result = f"Error: {str(e)}"
            logger.error(f"Execution failed: {decision.action} - {e}")
        
        self._update_decision(decision)
        return decision
    
    async def _notify_pending(self, decision: Decision):
        """Notify about pending decision via Telegram."""
        message = self._format_decision_message(decision)
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    "http://162.0.208.88:8710/notify",
                    json={"message": message, "priority": "high"}
                )
        except Exception as e:
            logger.warning(f"Failed to notify: {e}")
    
    def _format_decision_message(self, decision: Decision) -> str:
        """Format decision for notification."""
        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(decision.risk_level, "⚪")
        
        lines = [
            f"🤔 ARIA DECISION REQUEST",
            f"",
            f"**Action:** {decision.action}",
            f"**Category:** {decision.category.value}",
            f"**Reason:** {decision.reason}",
            f"",
            f"Risk: {risk_emoji} {decision.risk_level.upper()}",
        ]
        
        if decision.estimated_cost > 0:
            lines.append(f"💰 Est. Cost: ${decision.estimated_cost:.2f}")
        
        lines.extend([
            f"",
            f"Reply with:",
            f"• /approve {decision.id}",
            f"• /deny {decision.id}"
        ])
        
        return "\n".join(lines)
    
    def _save_decision(self, decision: Decision):
        """Save decision to database."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO decisions 
            (id, category, action, reason, context, estimated_cost, risk_level, 
             status, created_at, approved_at, approved_by, executed_at, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision.id, decision.category.value, decision.action, decision.reason,
            json.dumps(decision.context), decision.estimated_cost, decision.risk_level,
            decision.status, decision.created_at, decision.approved_at,
            decision.approved_by, decision.executed_at, decision.result
        ))
        
        conn.commit()
        conn.close()
    
    def _update_decision(self, decision: Decision):
        """Update decision in database."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            UPDATE decisions 
            SET status = ?, approved_at = ?, approved_by = ?, 
                executed_at = ?, result = ?
            WHERE id = ?
        """, (
            decision.status, decision.approved_at, decision.approved_by,
            decision.executed_at, decision.result, decision.id
        ))
        
        conn.commit()
        conn.close()
    
    def _get_decision(self, decision_id: str) -> Optional[Decision]:
        """Get decision from database."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return Decision(
            id=row["id"],
            category=DecisionCategory(row["category"]),
            action=row["action"],
            reason=row["reason"],
            context=json.loads(row["context"]) if row["context"] else {},
            estimated_cost=row["estimated_cost"],
            risk_level=row["risk_level"],
            status=row["status"],
            created_at=row["created_at"],
            approved_at=row["approved_at"],
            approved_by=row["approved_by"],
            executed_at=row["executed_at"],
            result=row["result"]
        )
    
    def get_pending(self) -> List[Decision]:
        """Get all pending decisions."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("SELECT * FROM decisions WHERE status = 'pending' ORDER BY created_at DESC")
        rows = c.fetchall()
        conn.close()
        
        return [
            Decision(
                id=row["id"],
                category=DecisionCategory(row["category"]),
                action=row["action"],
                reason=row["reason"],
                context=json.loads(row["context"]) if row["context"] else {},
                estimated_cost=row["estimated_cost"],
                risk_level=row["risk_level"],
                status=row["status"],
                created_at=row["created_at"]
            )
            for row in rows
        ]
    
    def get_stats(self) -> Dict:
        """Get approval statistics."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT 
                status,
                COUNT(*) as count,
                SUM(estimated_cost) as total_cost
            FROM decisions 
            GROUP BY status
        """)
        
        stats = {row["status"]: {"count": row["count"], "cost": row["total_cost"] or 0}
                 for row in c.fetchall()}
        
        c.execute("""
            SELECT COUNT(*) as auto_approved 
            FROM decisions 
            WHERE approved_by = 'aria_auto'
        """)
        stats["auto_approved"] = c.fetchone()["auto_approved"]
        
        conn.close()
        return stats
    
    # ======================= HELPER METHODS =======================
    
    async def check_status(self, service: str = None) -> Decision:
        """Request to check status (auto-approved)."""
        return await self.decide(
            category=DecisionCategory.MONITORING,
            action=f"Check status{f' of {service}' if service else ''}",
            reason="Monitoring request",
            context={"service": service}
        )
    
    async def scale_down_resources(self, reason: str) -> Decision:
        """Request to scale down (auto-approved - saves money)."""
        return await self.decide(
            category=DecisionCategory.SAVINGS,
            action="Scale down unused resources",
            reason=reason,
            context={}
        )
    
    async def add_gpu(self, count: int, reason: str, cost_per_hour: float) -> Decision:
        """Request to add GPU (requires approval)."""
        return await self.decide(
            category=DecisionCategory.SPENDING,
            action=f"Add {count} GPU(s)",
            reason=reason,
            context={"count": count},
            estimated_cost=cost_per_hour * count,
            risk_level="medium" if count > 2 else "low"
        )
    
    async def execute_trade(
        self,
        symbol: str,
        side: str,
        amount: float,
        reason: str
    ) -> Decision:
        """Request to execute trade (requires approval)."""
        return await self.decide(
            category=DecisionCategory.TRADING,
            action=f"{side.upper()} {amount} {symbol}",
            reason=reason,
            context={"symbol": symbol, "side": side, "amount": amount},
            estimated_cost=0,
            risk_level="high"
        )
    
    async def modify_config(self, service: str, change: str, reason: str) -> Decision:
        """Request to modify configuration (requires approval)."""
        return await self.decide(
            category=DecisionCategory.CHANGES,
            action=f"Modify {service} config: {change}",
            reason=reason,
            context={"service": service, "change": change},
            risk_level="medium"
        )


# Singleton instance
_approvals: Optional[ApprovalSystem] = None


def get_approval_system() -> ApprovalSystem:
    """Get or create the global approval system instance."""
    global _approvals
    if _approvals is None:
        _approvals = ApprovalSystem()
    return _approvals



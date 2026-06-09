"""
WhiteRock Blessings Engine - Audit Service
Comprehensive audit logging for compliance.
"""

from datetime import datetime
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import AuditLog


class AuditService:
    """Service for audit logging."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log(
        self,
        action: str,
        entity_type: str,
        entity_id: int,
        actor_id: Optional[int] = None,
        actor_role: Optional[str] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        severity: str = "info"
    ) -> AuditLog:
        """
        Log an audit entry.
        
        Severity levels:
        - info: Normal operations
        - warning: Unusual but allowed operations
        - critical: Sensitive operations requiring review
        """
        entry = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            actor_role=actor_role,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            severity=severity
        )
        self.db.add(entry)
        await self.db.flush()
        return entry
    
    async def log_member_action(
        self,
        action: str,
        member_id: int,
        actor_id: int,
        actor_role: str,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log a member-related action."""
        return await self.log(
            action=action,
            entity_type="member",
            entity_id=member_id,
            actor_id=actor_id,
            actor_role=actor_role,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    async def log_tithe(
        self,
        tithe_id: int,
        member_id: int,
        amount_cents: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log a tithe submission."""
        return await self.log(
            action="tithe_submitted",
            entity_type="tithe",
            entity_id=tithe_id,
            actor_id=member_id,
            actor_role="member",
            new_values={
                "amount_cents": amount_cents,
                "member_id": member_id
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    async def log_cora_transaction(
        self,
        transaction_id: int,
        member_id: int,
        amount: int,
        transaction_type: str,
        granted_by: Optional[int] = None
    ) -> AuditLog:
        """Log a CORA transaction."""
        severity = "warning" if transaction_type == "admin_adjustment" else "info"
        return await self.log(
            action=f"cora_{transaction_type}",
            entity_type="cora_transaction",
            entity_id=transaction_id,
            actor_id=granted_by or member_id,
            actor_role="admin" if granted_by else "system",
            new_values={
                "member_id": member_id,
                "amount": amount,
                "transaction_type": transaction_type
            },
            severity=severity
        )
    
    async def log_blessing_state_change(
        self,
        blessing_id: int,
        old_state: str,
        new_state: str,
        actor_id: int,
        actor_role: str,
        compliance_flag: Optional[bool] = None,
        amount_approved_cents: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log a blessing state transition."""
        # Critical if approving or denying
        severity = "critical" if new_state in ["approved", "denied"] else "info"
        
        return await self.log(
            action=f"blessing_{old_state}_to_{new_state}",
            entity_type="blessing_request",
            entity_id=blessing_id,
            actor_id=actor_id,
            actor_role=actor_role,
            old_values={"status": old_state},
            new_values={
                "status": new_state,
                "compliance_flag": compliance_flag,
                "amount_approved_cents": amount_approved_cents
            },
            ip_address=ip_address,
            user_agent=user_agent,
            severity=severity
        )
    
    async def log_disbursement(
        self,
        disbursement_id: int,
        blessing_id: int,
        amount_cents: int,
        actor_id: int,
        payment_direct_to_vendor: bool,
        cash_to_member_override: bool = False,
        override_reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log a blessing disbursement."""
        # CRITICAL if cash to member override
        severity = "critical" if cash_to_member_override else "info"
        
        return await self.log(
            action="blessing_disbursed",
            entity_type="blessing_disbursement",
            entity_id=disbursement_id,
            actor_id=actor_id,
            actor_role="admin",
            new_values={
                "blessing_id": blessing_id,
                "amount_cents": amount_cents,
                "payment_direct_to_vendor": payment_direct_to_vendor,
                "cash_to_member_override": cash_to_member_override,
                "override_reason": override_reason
            },
            ip_address=ip_address,
            user_agent=user_agent,
            severity=severity
        )
    
    async def log_disclosure_signed(
        self,
        member_id: int,
        disclosure_version: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log disclosure acknowledgment."""
        return await self.log(
            action="disclosure_signed",
            entity_type="member",
            entity_id=member_id,
            actor_id=member_id,
            actor_role="member",
            new_values={
                "disclosure_version": disclosure_version,
                "timestamp": datetime.utcnow().isoformat()
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    async def get_logs(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        actor_id: Optional[int] = None,
        severity: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> list:
        """Query audit logs with filters."""
        query = select(AuditLog)
        
        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)
        if entity_id:
            query = query.where(AuditLog.entity_id == entity_id)
        if actor_id:
            query = query.where(AuditLog.actor_id == actor_id)
        if severity:
            query = query.where(AuditLog.severity == severity)
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
        
        query = query.order_by(AuditLog.created_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()




"""
WhiteRock Blessings Engine - CORA Service
CORA credit management with decay logic.

CORA represents "Community Vitality" - NOT monetary value.
CORA is NON-TRANSFERABLE by design.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import Member, CoraTransaction, CoraDecayEvent, TitheMilestone, MembershipTier
from app.config import settings
from app.services.audit_service import AuditService


class CoraService:
    """Service for CORA credit management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = AuditService(db)
    
    async def get_balance(self, member_id: int) -> int:
        """Get current CORA balance for a member."""
        result = await self.db.execute(
            select(Member.cora_balance).where(Member.id == member_id)
        )
        balance = result.scalar_one_or_none()
        return balance or 0
    
    async def get_cap(self, member_id: int) -> int:
        """Get CORA cap for a member."""
        result = await self.db.execute(
            select(Member.cora_cap).where(Member.id == member_id)
        )
        cap = result.scalar_one_or_none()
        return cap or 1000
    
    async def grant_cora(
        self,
        member_id: int,
        amount: int,
        transaction_type: str,
        description: Optional[str] = None,
        granted_by: Optional[int] = None
    ) -> Tuple[int, int]:
        """
        Grant CORA credits to a member.
        
        Returns:
            Tuple of (transaction_id, new_balance)
        """
        # Get member
        result = await self.db.execute(
            select(Member).where(Member.id == member_id)
        )
        member = result.scalar_one_or_none()
        
        if not member:
            raise ValueError(f"Member {member_id} not found")
        
        # Calculate new balance (respecting cap)
        new_balance = min(member.cora_balance + amount, member.cora_cap)
        actual_granted = new_balance - member.cora_balance
        
        if actual_granted <= 0:
            # Already at cap
            return 0, member.cora_balance
        
        # Create transaction
        transaction = CoraTransaction(
            member_id=member_id,
            amount=actual_granted,
            transaction_type=transaction_type,
            description=description,
            granted_by=granted_by
        )
        self.db.add(transaction)
        
        # Update member balance and engagement date
        member.cora_balance = new_balance
        member.last_engagement_date = datetime.utcnow()
        
        await self.db.flush()
        
        # Audit log
        await self.audit.log_cora_transaction(
            transaction_id=transaction.id,
            member_id=member_id,
            amount=actual_granted,
            transaction_type=transaction_type,
            granted_by=granted_by
        )
        
        # Check for tier upgrade
        await self._check_tier_upgrade(member)
        
        return transaction.id, new_balance
    
    async def decay_cora(
        self,
        member_id: int,
        months_inactive: int
    ) -> Optional[CoraDecayEvent]:
        """
        Apply CORA decay for inactive member.
        
        Returns:
            CoraDecayEvent if decay was applied, None otherwise
        """
        # Get member
        result = await self.db.execute(
            select(Member).where(Member.id == member_id)
        )
        member = result.scalar_one_or_none()
        
        if not member or member.cora_balance <= 0:
            return None
        
        # Calculate decay (10% of current balance)
        decay_amount = int(member.cora_balance * settings.CORA_DECAY_RATE)
        if decay_amount <= 0:
            decay_amount = 1  # Minimum decay of 1
        
        balance_before = member.cora_balance
        balance_after = max(0, balance_before - decay_amount)
        
        # Create decay event
        decay_event = CoraDecayEvent(
            member_id=member_id,
            amount_decayed=decay_amount,
            balance_before=balance_before,
            balance_after=balance_after,
            decay_reason="inactivity_12mo",
            months_inactive=months_inactive
        )
        self.db.add(decay_event)
        
        # Create transaction record
        transaction = CoraTransaction(
            member_id=member_id,
            amount=-decay_amount,
            transaction_type="decay_inactivity",
            description=f"Inactivity decay after {months_inactive} months"
        )
        self.db.add(transaction)
        
        # Update member balance
        member.cora_balance = balance_after
        
        await self.db.flush()
        
        # Audit log
        await self.audit.log_cora_transaction(
            transaction_id=transaction.id,
            member_id=member_id,
            amount=-decay_amount,
            transaction_type="decay_inactivity"
        )
        
        return decay_event
    
    async def get_members_for_decay(self) -> List[Member]:
        """Get members who have been inactive for >12 months and have CORA balance."""
        threshold_date = datetime.utcnow() - timedelta(days=365)
        
        result = await self.db.execute(
            select(Member).where(
                Member.is_active == True,
                Member.cora_balance > 0,
                Member.last_engagement_date < threshold_date
            )
        )
        return result.scalars().all()
    
    async def get_members_approaching_decay(self) -> List[dict]:
        """Get members approaching decay (within warning period)."""
        warning_start = datetime.utcnow() - timedelta(days=365 - settings.CORA_DECAY_WARNING_DAYS)
        threshold_date = datetime.utcnow() - timedelta(days=365)
        
        result = await self.db.execute(
            select(Member).where(
                Member.is_active == True,
                Member.cora_balance > 0,
                Member.last_engagement_date < warning_start,
                Member.last_engagement_date >= threshold_date,
                Member.decay_warning_sent_at.is_(None)
            )
        )
        members = result.scalars().all()
        
        decay_previews = []
        for member in members:
            days_until_decay = (member.last_engagement_date + timedelta(days=365) - datetime.utcnow()).days
            projected_decay = int(member.cora_balance * settings.CORA_DECAY_RATE)
            
            decay_previews.append({
                "id": member.id,
                "name": member.full_name,
                "months_inactive": (datetime.utcnow() - member.last_engagement_date).days // 30,
                "days_until_decay": max(0, days_until_decay),
                "current_balance": member.cora_balance,
                "projected_decay": projected_decay
            })
        
        return decay_previews
    
    async def mark_decay_warning_sent(self, member_id: int) -> None:
        """Mark that decay warning email was sent to member."""
        result = await self.db.execute(
            select(Member).where(Member.id == member_id)
        )
        member = result.scalar_one_or_none()
        if member:
            member.decay_warning_sent_at = datetime.utcnow()
    
    async def check_tithe_milestones(
        self,
        member_id: int,
        cumulative_cents: int
    ) -> int:
        """
        Check and grant CORA for reached tithe milestones.
        
        Returns:
            Total CORA granted for milestones
        """
        # Get milestones member hasn't reached yet
        result = await self.db.execute(
            select(TitheMilestone).where(
                TitheMilestone.cumulative_amount_cents <= cumulative_cents
            ).order_by(TitheMilestone.cumulative_amount_cents.asc())
        )
        milestones = result.scalars().all()
        
        # Get already granted milestone amounts for this member
        result = await self.db.execute(
            select(CoraTransaction).where(
                CoraTransaction.member_id == member_id,
                CoraTransaction.transaction_type == "tithe_milestone"
            )
        )
        existing_transactions = result.scalars().all()
        granted_milestones = set()
        for tx in existing_transactions:
            if tx.description:
                # Extract milestone amount from description
                try:
                    # Description format: "Tithe milestone: $X"
                    amount = int(tx.description.split("$")[1].replace(",", "").split()[0]) * 100
                    granted_milestones.add(amount)
                except (IndexError, ValueError):
                    pass
        
        total_granted = 0
        for milestone in milestones:
            if milestone.cumulative_amount_cents not in granted_milestones:
                _, _ = await self.grant_cora(
                    member_id=member_id,
                    amount=milestone.cora_grant,
                    transaction_type="tithe_milestone",
                    description=f"Tithe milestone: ${milestone.cumulative_amount_cents // 100:,}"
                )
                total_granted += milestone.cora_grant
        
        return total_granted
    
    async def _check_tier_upgrade(self, member: Member) -> None:
        """Check if member should be upgraded to a new tier."""
        result = await self.db.execute(
            select(MembershipTier).order_by(MembershipTier.cora_threshold.desc())
        )
        tiers = result.scalars().all()
        
        for tier in tiers:
            if member.cora_balance >= tier.cora_threshold:
                if member.membership_tier != tier.name:
                    member.membership_tier = tier.name
                    member.cora_cap = tier.cora_cap
                break
    
    async def get_transaction_history(
        self,
        member_id: int,
        limit: int = 20
    ) -> List[dict]:
        """Get CORA transaction history for a member."""
        result = await self.db.execute(
            select(CoraTransaction).where(
                CoraTransaction.member_id == member_id
            ).order_by(CoraTransaction.created_at.desc()).limit(limit)
        )
        transactions = result.scalars().all()
        
        return [
            {
                "id": tx.id,
                "amount": tx.amount,
                "type": tx.transaction_type,
                "description": tx.description,
                "created_at": tx.created_at.isoformat()
            }
            for tx in transactions
        ]
    
    async def get_total_circulation(self) -> int:
        """Get total CORA in circulation across all active members."""
        result = await self.db.execute(
            select(func.sum(Member.cora_balance)).where(Member.is_active == True)
        )
        total = result.scalar_one_or_none()
        return total or 0
    
    async def get_average_member_cora(self) -> float:
        """Get average CORA balance per active member."""
        result = await self.db.execute(
            select(func.avg(Member.cora_balance)).where(Member.is_active == True)
        )
        avg = result.scalar_one_or_none()
        return float(avg or 0)




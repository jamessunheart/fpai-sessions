"""
CRUD operations for voting weight tracking
"""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .database import VotingWeightDB, VotingEventDB, GovernanceSnapshotDB
from .models import WalletVotingPower, GovernanceStatus

logger = logging.getLogger(__name__)


async def add_votes(
    db: AsyncSession,
    wallet: str,
    votes: int,
    contract_id: str,
    event_type: str
) -> WalletVotingPower:
    """
    Add voting weight to a wallet (called when contract is minted).

    Typically adds 2 votes to holder_votes.
    """
    # Get or create wallet voting record
    stmt = select(VotingWeightDB).where(VotingWeightDB.wallet == wallet)
    result = await db.execute(stmt)
    voting_weight = result.scalar_one_or_none()

    if not voting_weight:
        # Create new record
        voting_weight = VotingWeightDB(
            wallet=wallet,
            total_votes=votes,
            holder_votes=votes,
            seller_votes=0,
            held_contracts=1,
            redeemed_contracts=0
        )
        db.add(voting_weight)
    else:
        # Update existing record
        voting_weight.total_votes += votes
        voting_weight.holder_votes += votes
        voting_weight.held_contracts += 1
        voting_weight.last_updated = datetime.utcnow()

    # Log event
    event = VotingEventDB(
        wallet=wallet,
        contract_id=contract_id,
        event_type=event_type,
        vote_change=votes,
        new_total_votes=voting_weight.total_votes
    )
    db.add(event)

    await db.flush()

    return WalletVotingPower(
        wallet=voting_weight.wallet,
        total_votes=voting_weight.total_votes,
        holder_votes=voting_weight.holder_votes,
        seller_votes=voting_weight.seller_votes,
        held_contracts=voting_weight.held_contracts,
        redeemed_contracts=voting_weight.redeemed_contracts
    )


async def update_votes(
    db: AsyncSession,
    wallet: str,
    contract_id: str,
    old_votes: int,
    new_votes: int,
    event_type: str
) -> WalletVotingPower:
    """
    Update voting weight when contract is redeemed.

    Typically transitions from 2 (holder) to 1 (seller).
    """
    # Get wallet voting record
    stmt = select(VotingWeightDB).where(VotingWeightDB.wallet == wallet)
    result = await db.execute(stmt)
    voting_weight = result.scalar_one_or_none()

    if not voting_weight:
        raise ValueError(f"Wallet {wallet} not found")

    # Calculate vote change
    vote_delta = new_votes - old_votes

    # Update voting power
    # Transition: holder_votes (2) → seller_votes (1)
    voting_weight.holder_votes -= old_votes
    voting_weight.seller_votes += new_votes
    voting_weight.total_votes += vote_delta
    voting_weight.held_contracts -= 1
    voting_weight.redeemed_contracts += 1
    voting_weight.last_updated = datetime.utcnow()

    # Log event
    event = VotingEventDB(
        wallet=wallet,
        contract_id=contract_id,
        event_type=event_type,
        vote_change=vote_delta,
        new_total_votes=voting_weight.total_votes
    )
    db.add(event)

    await db.flush()

    return WalletVotingPower(
        wallet=voting_weight.wallet,
        total_votes=voting_weight.total_votes,
        holder_votes=voting_weight.holder_votes,
        seller_votes=voting_weight.seller_votes,
        held_contracts=voting_weight.held_contracts,
        redeemed_contracts=voting_weight.redeemed_contracts
    )


async def get_wallet_voting_power(
    db: AsyncSession,
    wallet: str
) -> Optional[WalletVotingPower]:
    """Get voting power for a specific wallet."""
    stmt = select(VotingWeightDB).where(VotingWeightDB.wallet == wallet)
    result = await db.execute(stmt)
    voting_weight = result.scalar_one_or_none()

    if not voting_weight:
        return None

    return WalletVotingPower(
        wallet=voting_weight.wallet,
        total_votes=voting_weight.total_votes,
        holder_votes=voting_weight.holder_votes,
        seller_votes=voting_weight.seller_votes,
        held_contracts=voting_weight.held_contracts,
        redeemed_contracts=voting_weight.redeemed_contracts
    )


async def get_governance_status(db: AsyncSession) -> GovernanceStatus:
    """
    Calculate current system-wide governance metrics.

    This is the critical function that determines if holders maintain >51% control.
    """
    # Sum all votes
    stmt = select(
        func.sum(VotingWeightDB.total_votes).label('total_votes'),
        func.sum(VotingWeightDB.holder_votes).label('holder_votes'),
        func.sum(VotingWeightDB.seller_votes).label('seller_votes'),
        func.count(VotingWeightDB.id).label('total_wallets')
    )
    result = await db.execute(stmt)
    row = result.one()

    total_votes = row.total_votes or 0
    holder_votes = row.holder_votes or 0
    seller_votes = row.seller_votes or 0
    total_wallets = row.total_wallets or 0

    # Count holder vs seller wallets
    # Holder wallet: has held_contracts > 0
    # Seller wallet: has redeemed_contracts > 0 and held_contracts = 0
    holder_wallets_stmt = select(func.count(VotingWeightDB.id)).where(
        VotingWeightDB.held_contracts > 0
    )
    result = await db.execute(holder_wallets_stmt)
    holder_wallets = result.scalar() or 0

    seller_wallets_stmt = select(func.count(VotingWeightDB.id)).where(
        VotingWeightDB.held_contracts == 0,
        VotingWeightDB.redeemed_contracts > 0
    )
    result = await db.execute(seller_wallets_stmt)
    seller_wallets = result.scalar() or 0

    # Calculate holder control percentage
    if total_votes > 0:
        holder_control_percentage = (holder_votes / total_votes) * 100
    else:
        holder_control_percentage = 0.0

    # System is stable if holder control > 51%
    critical_threshold = 51.0
    is_stable = holder_control_percentage > critical_threshold
    margin_above_critical = holder_control_percentage - critical_threshold

    return GovernanceStatus(
        total_votes=total_votes,
        holder_votes=holder_votes,
        seller_votes=seller_votes,
        holder_control_percentage=round(holder_control_percentage, 2),
        is_stable=is_stable,
        critical_threshold=critical_threshold,
        margin_above_critical=round(margin_above_critical, 2),
        total_wallets=total_wallets,
        holder_wallets=holder_wallets,
        seller_wallets=seller_wallets
    )


async def get_top_voters(
    db: AsyncSession,
    limit: int = 10
) -> List[WalletVotingPower]:
    """Get top voters by total voting power."""
    stmt = select(VotingWeightDB).order_by(
        desc(VotingWeightDB.total_votes)
    ).limit(limit)
    result = await db.execute(stmt)
    voting_weights = result.scalars().all()

    return [
        WalletVotingPower(
            wallet=vw.wallet,
            total_votes=vw.total_votes,
            holder_votes=vw.holder_votes,
            seller_votes=vw.seller_votes,
            held_contracts=vw.held_contracts,
            redeemed_contracts=vw.redeemed_contracts
        )
        for vw in voting_weights
    ]


async def get_voting_history(
    db: AsyncSession,
    wallet: Optional[str] = None,
    limit: int = 20
) -> List[VotingEventDB]:
    """Get voting event history (optionally filtered by wallet)."""
    if wallet:
        stmt = select(VotingEventDB).where(
            VotingEventDB.wallet == wallet
        ).order_by(desc(VotingEventDB.timestamp)).limit(limit)
    else:
        stmt = select(VotingEventDB).order_by(
            desc(VotingEventDB.timestamp)
        ).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_governance_snapshot(db: AsyncSession) -> GovernanceSnapshotDB:
    """
    Create a snapshot of current governance metrics.

    Called periodically by background task for historical tracking.
    """
    governance = await get_governance_status(db)

    snapshot = GovernanceSnapshotDB(
        total_votes=governance.total_votes,
        holder_votes=governance.holder_votes,
        seller_votes=governance.seller_votes,
        holder_control_percentage=governance.holder_control_percentage,
        total_wallets=governance.total_wallets,
        holder_wallets=governance.holder_wallets,
        seller_wallets=governance.seller_wallets
    )
    db.add(snapshot)
    await db.flush()

    logger.info(f"Created governance snapshot: {governance.holder_control_percentage}% holder control")

    return snapshot

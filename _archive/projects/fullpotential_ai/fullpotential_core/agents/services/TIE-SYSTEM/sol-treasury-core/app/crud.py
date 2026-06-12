"""
CRUD operations for database
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import TreasuryTransactionDB
from app.models import TreasuryTransaction
from datetime import datetime


async def create_transaction(
    db: AsyncSession,
    transaction_id: str,
    wallet_address: str,
    type: str,
    amount_sol: float,
    status: str,
    tie_contract_value: Optional[float] = None
) -> TreasuryTransactionDB:
    """Create a new transaction record"""

    transaction = TreasuryTransactionDB(
        transaction_id=transaction_id,
        wallet_address=wallet_address,
        type=type,
        amount_sol=amount_sol,
        status=status,
        tie_contract_value=tie_contract_value,
        created_at=datetime.utcnow()
    )

    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)

    return transaction


async def get_transaction(
    db: AsyncSession,
    transaction_id: str
) -> Optional[TreasuryTransactionDB]:
    """Get a transaction by ID"""

    result = await db.execute(
        select(TreasuryTransactionDB).where(
            TreasuryTransactionDB.transaction_id == transaction_id
        )
    )

    return result.scalar_one_or_none()


async def get_transactions(
    db: AsyncSession,
    wallet_address: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[TreasuryTransaction]:
    """Get transaction history"""

    query = select(TreasuryTransactionDB).order_by(
        TreasuryTransactionDB.created_at.desc()
    )

    if wallet_address:
        query = query.where(TreasuryTransactionDB.wallet_address == wallet_address)

    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    transactions = result.scalars().all()

    return [TreasuryTransaction.model_validate(tx) for tx in transactions]


async def count_transactions(
    db: AsyncSession,
    wallet_address: Optional[str] = None
) -> int:
    """Count total transactions"""

    query = select(func.count()).select_from(TreasuryTransactionDB)

    if wallet_address:
        query = query.where(TreasuryTransactionDB.wallet_address == wallet_address)

    result = await db.execute(query)
    return result.scalar_one()


async def update_transaction_status(
    db: AsyncSession,
    transaction_id: str,
    status: str,
    confirmed_at: Optional[datetime] = None
) -> Optional[TreasuryTransactionDB]:
    """Update transaction status"""

    transaction = await get_transaction(db, transaction_id)

    if transaction:
        transaction.status = status
        if confirmed_at:
            transaction.confirmed_at = confirmed_at

        await db.commit()
        await db.refresh(transaction)

    return transaction

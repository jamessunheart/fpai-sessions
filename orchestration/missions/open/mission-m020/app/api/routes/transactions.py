"""Transaction endpoints."""
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import TransactionCreate, TransactionRead
from app.core.config import settings
from app.core.database import get_db
from app.models import Transaction
from app.telemetry import client as telemetry_client

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    tx_in: TransactionCreate,
    session: AsyncSession = Depends(get_db),
) -> Transaction:
    tx_data = tx_in.model_dump()
    transaction = Transaction(**tx_data)
    session.add(transaction)
    await session.commit()
    await session.refresh(transaction)
    if telemetry_client:
        telemetry_client.capture(
            settings.service_name,
            "transaction_logged",
            {
                "mission_id": settings.mission_id,
                "asset_id": str(transaction.asset_id),
                "transaction_id": str(transaction.id),
                "type": transaction.type,
                "amount": str(transaction.amount),
            },
        )
    return transaction


@router.get("", response_model=list[TransactionRead])
async def list_transactions(session: AsyncSession = Depends(get_db)) -> list[Transaction]:
    result = await session.execute(select(Transaction).order_by(Transaction.transaction_date.desc()))
    return result.scalars().all()


"""Pydantic schemas for transactions."""
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TransactionBase(BaseModel):
    asset_id: uuid.UUID
    amount: Decimal = Field(..., gt=0)
    type: str = Field(..., max_length=50)
    transaction_date: datetime | None = None


class TransactionCreate(TransactionBase):
    pass


class TransactionRead(TransactionBase):
    id: uuid.UUID
    transaction_date: datetime

    model_config = ConfigDict(from_attributes=True)


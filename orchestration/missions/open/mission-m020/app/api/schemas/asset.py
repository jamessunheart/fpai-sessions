"""Pydantic schemas for assets."""
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AssetBase(BaseModel):
    name: str = Field(..., max_length=255)
    type: str = Field(..., max_length=50)
    value: Decimal = Field(..., ge=0)
    risk_level: str = Field(..., max_length=50)


class AssetCreate(AssetBase):
    pass


class AssetRead(AssetBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


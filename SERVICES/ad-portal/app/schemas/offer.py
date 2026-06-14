"""
Offer Schemas
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class OfferBase(BaseModel):
    """Base offer fields"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: Decimal = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    offer_type: str = Field(default="coaching", max_length=50)
    landing_url: str = Field(..., min_length=1)
    thank_you_url: Optional[str] = None
    pixel_id: Optional[str] = None
    stripe_price_id: Optional[str] = None
    uc_price: Optional[Decimal] = None


class OfferCreate(OfferBase):
    """Schema for creating an offer"""
    pass


class OfferUpdate(BaseModel):
    """Schema for updating an offer"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = Field(None, max_length=3)
    offer_type: Optional[str] = Field(None, max_length=50)
    landing_url: Optional[str] = None
    thank_you_url: Optional[str] = None
    pixel_id: Optional[str] = None
    stripe_price_id: Optional[str] = None
    uc_price: Optional[Decimal] = None
    active: Optional[bool] = None


class OfferResponse(OfferBase):
    """Schema for offer response"""
    id: UUID
    active: bool
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    display_price: Optional[str] = None
    campaign_count: int = 0
    total_revenue: Decimal = Decimal("0.00")
    
    class Config:
        from_attributes = True


class OfferList(BaseModel):
    """Schema for list of offers"""
    offers: List[OfferResponse]
    total: int
    
    class Config:
        from_attributes = True



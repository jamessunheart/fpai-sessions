"""
Creative Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class CreativeBase(BaseModel):
    """Base creative fields"""
    name: Optional[str] = None
    creative_type: str = Field(default="single_image")
    headline: str = Field(..., min_length=1, max_length=255)
    primary_text: str = Field(..., min_length=1)
    description: Optional[str] = None
    call_to_action: str = Field(default="LEARN_MORE")
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    variation: str = Field(default="A", max_length=1)


class CreativeCreate(CreativeBase):
    """Schema for creating a creative"""
    campaign_id: UUID


class CreativeUpdate(BaseModel):
    """Schema for updating a creative"""
    name: Optional[str] = None
    headline: Optional[str] = Field(None, max_length=255)
    primary_text: Optional[str] = None
    description: Optional[str] = None
    call_to_action: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    variation: Optional[str] = Field(None, max_length=1)
    active: Optional[bool] = None


class CreativeMetrics(BaseModel):
    """Performance metrics for a creative"""
    impressions: int = 0
    clicks: int = 0
    spend: float = 0.0
    ctr: float = 0.0
    cpc: float = 0.0
    conversions: int = 0


class CreativeResponse(CreativeBase):
    """Schema for creative response"""
    id: UUID
    campaign_id: UUID
    meta_creative_id: Optional[str] = None
    meta_ad_id: Optional[str] = None
    active: bool
    created_at: datetime
    updated_at: datetime
    
    # Performance (optional)
    metrics: Optional[CreativeMetrics] = None
    
    class Config:
        from_attributes = True


class CreativeGenerate(BaseModel):
    """Schema for AI creative generation request"""
    offer_id: UUID
    tone: str = Field(default="professional", description="Tone: professional, casual, urgent, inspirational")
    num_variations: int = Field(default=3, ge=1, le=5)
    focus_points: Optional[List[str]] = Field(default=None, description="Key benefits to highlight")
    target_audience: Optional[str] = Field(default=None, description="Description of target audience")


class GeneratedCreative(BaseModel):
    """Schema for AI-generated creative"""
    variation: str
    headline: str
    primary_text: str
    description: str
    image_prompt: str  # Prompt for image generation
    reasoning: Optional[str] = None  # Why AI chose this approach


class CreativeGenerateResponse(BaseModel):
    """Response from AI creative generation"""
    creatives: List[GeneratedCreative]
    offer_name: str
    generated_at: datetime



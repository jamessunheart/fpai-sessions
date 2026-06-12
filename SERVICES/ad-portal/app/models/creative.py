"""
Creative Model - Ad creatives (copy, images, videos)
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class CreativeType(str, enum.Enum):
    """Creative format types"""
    SINGLE_IMAGE = "single_image"
    CAROUSEL = "carousel"
    VIDEO = "video"
    COLLECTION = "collection"


class CallToAction(str, enum.Enum):
    """Meta CTA button options"""
    LEARN_MORE = "LEARN_MORE"
    SIGN_UP = "SIGN_UP"
    BOOK_NOW = "BOOK_NOW"
    CONTACT_US = "CONTACT_US"
    GET_OFFER = "GET_OFFER"
    SHOP_NOW = "SHOP_NOW"
    SUBSCRIBE = "SUBSCRIBE"
    APPLY_NOW = "APPLY_NOW"


class Creative(Base):
    """
    Represents an ad creative (copy + media)
    """
    __tablename__ = "creatives"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    
    # Basic Info
    name = Column(String(255))
    creative_type = Column(String(50), default=CreativeType.SINGLE_IMAGE.value)
    
    # Ad Copy
    headline = Column(String(255), nullable=False)  # Main headline (40 char recommended)
    primary_text = Column(Text, nullable=False)  # Main body text (125 char recommended)
    description = Column(Text)  # Link description (30 char recommended)
    call_to_action = Column(String(50), default=CallToAction.LEARN_MORE.value)
    
    # Media
    image_url = Column(Text)  # URL to image
    video_url = Column(Text)  # URL to video
    thumbnail_url = Column(Text)  # Video thumbnail
    
    # Meta IDs (populated after creation)
    meta_creative_id = Column(String(100))
    meta_ad_id = Column(String(100))
    
    # A/B Testing
    variation = Column(String(1), default="A")  # A, B, C, etc.
    
    # Status
    active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="creatives")
    metrics = relationship("AdMetrics", back_populates="creative")
    
    def __repr__(self):
        return f"<Creative {self.name or self.headline[:30]} - Var {self.variation}>"
    
    @property
    def preview_text(self) -> str:
        """Short preview of ad copy"""
        return f"{self.headline}\n{self.primary_text[:50]}..."
    
    def to_meta_format(self) -> dict:
        """Convert to Meta Ads API format"""
        return {
            "title": self.headline,
            "body": self.primary_text,
            "description": self.description or "",
            "call_to_action_type": self.call_to_action,
            "link": None,  # Set by campaign
            "image_url": self.image_url,
        }



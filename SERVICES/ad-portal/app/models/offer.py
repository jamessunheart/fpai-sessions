"""
Offer Model - Coaching packages/products being advertised
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Numeric, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Offer(Base):
    """
    Represents a coaching offer/product that can be advertised
    """
    __tablename__ = "offers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    offer_type = Column(String(50), default="coaching")
    
    # URLs
    landing_url = Column(Text, nullable=False)
    thank_you_url = Column(Text)
    
    # Integration IDs
    pixel_id = Column(String(100))  # Meta Pixel ID for this offer
    stripe_price_id = Column(String(100))  # Stripe Price ID
    uc_price = Column(Numeric(10, 2))  # Price in UC credits
    
    # Status
    active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    campaigns = relationship("Campaign", back_populates="offer")
    conversions = relationship("Conversion", back_populates="offer")
    
    def __repr__(self):
        return f"<Offer {self.name} - ${self.price}>"
    
    @property
    def display_price(self) -> str:
        """Format price for display"""
        return f"${self.price:,.2f} {self.currency}"



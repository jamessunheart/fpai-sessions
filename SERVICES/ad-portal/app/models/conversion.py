"""
Conversion Model - Sales/revenue events
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Numeric, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class ConversionSource(str, enum.Enum):
    """Where the payment came from"""
    STRIPE = "stripe"
    UC_CREDITS = "uc_credits"
    MANUAL = "manual"


class Conversion(Base):
    """
    Represents a sale/conversion tracked from ads
    """
    __tablename__ = "conversions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"))
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id"))
    
    # Payment Info
    source = Column(String(20), nullable=False)  # stripe, uc_credits, manual
    external_id = Column(String(255))  # Payment intent ID, transaction ID, etc.
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    
    # Customer Info
    customer_email = Column(String(255))
    customer_name = Column(String(255))
    
    # Attribution (UTM tracking)
    utm_source = Column(String(100))
    utm_medium = Column(String(100))
    utm_campaign = Column(String(100))
    utm_content = Column(String(100))
    utm_term = Column(String(100))
    
    # Facebook Attribution
    fbclid = Column(String(255))  # Facebook Click ID
    fbc = Column(String(255))  # Facebook Cookie (fbc)
    fbp = Column(String(255))  # Facebook Browser ID (fbp)
    
    # Additional Data
    ip_address = Column(String(45))
    user_agent = Column(Text)
    landing_page = Column(Text)
    
    # Timestamps
    converted_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="conversions")
    offer = relationship("Offer", back_populates="conversions")
    
    def __repr__(self):
        return f"<Conversion ${self.amount} from {self.source}>"
    
    @property
    def is_attributed(self) -> bool:
        """Check if conversion has campaign attribution"""
        return self.campaign_id is not None or self.fbclid is not None
    
    def to_meta_event(self) -> dict:
        """Convert to Meta Conversions API format"""
        import hashlib
        
        def hash_value(val: str) -> str:
            """SHA256 hash for PII"""
            if not val:
                return None
            return hashlib.sha256(val.lower().strip().encode()).hexdigest()
        
        return {
            "event_name": "Purchase",
            "event_time": int(self.converted_at.timestamp()),
            "action_source": "website",
            "user_data": {
                "em": [hash_value(self.customer_email)] if self.customer_email else None,
                "fbc": self.fbc,
                "fbp": self.fbp,
                "client_ip_address": self.ip_address,
                "client_user_agent": self.user_agent,
            },
            "custom_data": {
                "currency": self.currency,
                "value": float(self.amount),
                "content_ids": [str(self.offer_id)] if self.offer_id else [],
                "content_type": "product",
            }
        }



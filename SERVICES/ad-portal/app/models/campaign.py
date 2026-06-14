"""
Campaign Model - Meta advertising campaigns
"""
import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Text, Numeric, Boolean, DateTime, Date, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class CampaignStatus(str, enum.Enum):
    """Campaign status options"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CampaignObjective(str, enum.Enum):
    """Meta campaign objectives"""
    CONVERSIONS = "OUTCOME_SALES"
    TRAFFIC = "OUTCOME_TRAFFIC"
    AWARENESS = "OUTCOME_AWARENESS"
    ENGAGEMENT = "OUTCOME_ENGAGEMENT"
    LEADS = "OUTCOME_LEADS"


class Campaign(Base):
    """
    Represents a Meta advertising campaign
    """
    __tablename__ = "campaigns"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id"), nullable=False)
    
    # Basic Info
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Meta IDs (populated after launch)
    meta_campaign_id = Column(String(100))
    meta_adset_id = Column(String(100))
    
    # Configuration
    objective = Column(String(50), default=CampaignObjective.CONVERSIONS.value)
    daily_budget = Column(Numeric(10, 2), nullable=False)
    lifetime_budget = Column(Numeric(10, 2))
    
    # Status
    status = Column(String(20), default=CampaignStatus.DRAFT.value)
    
    # Schedule
    start_date = Column(Date)
    end_date = Column(Date)
    
    # Targeting (stored as JSON)
    targeting = Column(JSONB, default={
        "age_min": 25,
        "age_max": 55,
        "genders": [1, 2],  # All genders
        "geo_locations": {"countries": ["US"]},
        "interests": []
    })
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    launched_at = Column(DateTime)
    
    # Relationships
    offer = relationship("Offer", back_populates="campaigns")
    creatives = relationship("Creative", back_populates="campaign", cascade="all, delete-orphan")
    metrics = relationship("AdMetrics", back_populates="campaign", cascade="all, delete-orphan")
    conversions = relationship("Conversion", back_populates="campaign")
    profit_reports = relationship("ProfitReport", back_populates="campaign")
    
    def __repr__(self):
        return f"<Campaign {self.name} - {self.status}>"
    
    @property
    def is_active(self) -> bool:
        """Check if campaign is currently running"""
        return self.status == CampaignStatus.ACTIVE.value
    
    @property
    def days_running(self) -> int:
        """Number of days campaign has been running"""
        if not self.launched_at:
            return 0
        return (datetime.utcnow() - self.launched_at).days
    
    @property
    def budget_spent_pct(self) -> float:
        """Percentage of lifetime budget spent (if set)"""
        if not self.lifetime_budget:
            return 0
        total_spend = sum(m.spend for m in self.metrics) if self.metrics else 0
        return (float(total_spend) / float(self.lifetime_budget)) * 100



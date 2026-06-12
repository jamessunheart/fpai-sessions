"""
Metrics Models - Ad performance and profit tracking
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from app.database import Base


class AdMetrics(Base):
    """
    Hourly/daily ad performance metrics from Meta
    """
    __tablename__ = "ad_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    creative_id = Column(UUID(as_uuid=True), ForeignKey("creatives.id"))
    
    # Time
    date = Column(Date, nullable=False)
    hour = Column(Integer)  # 0-23, NULL for daily rollup
    
    # Core Metrics
    impressions = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    link_clicks = Column(Integer, default=0)
    spend = Column(Numeric(10, 2), default=0)
    
    # Calculated Metrics (stored for quick queries)
    cpm = Column(Numeric(10, 4))  # Cost per 1000 impressions
    cpc = Column(Numeric(10, 4))  # Cost per click
    ctr = Column(Numeric(6, 4))   # Click-through rate
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('campaign_id', 'creative_id', 'date', 'hour', name='uq_metrics_campaign_date_hour'),
    )
    
    # Relationships
    campaign = relationship("Campaign", back_populates="metrics")
    creative = relationship("Creative", back_populates="metrics")
    
    def __repr__(self):
        return f"<AdMetrics {self.date} - ${self.spend}>"
    
    def calculate_derived_metrics(self):
        """Calculate CPM, CPC, CTR from raw metrics"""
        if self.impressions and self.impressions > 0:
            self.cpm = (float(self.spend) / self.impressions) * 1000
            self.ctr = (self.clicks / self.impressions) * 100
        if self.clicks and self.clicks > 0:
            self.cpc = float(self.spend) / self.clicks


class ProfitReport(Base):
    """
    Daily profit rollup by campaign
    """
    __tablename__ = "profit_reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id"))
    
    # Financial Metrics
    total_spend = Column(Numeric(10, 2), default=0)
    total_revenue = Column(Numeric(10, 2), default=0)
    conversion_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('date', 'campaign_id', name='uq_profit_date_campaign'),
    )
    
    # Relationships
    campaign = relationship("Campaign", back_populates="profit_reports")
    
    def __repr__(self):
        return f"<ProfitReport {self.date} - Profit: ${self.profit}>"
    
    @hybrid_property
    def profit(self) -> float:
        """Calculate profit (revenue - spend)"""
        return float(self.total_revenue or 0) - float(self.total_spend or 0)
    
    @hybrid_property
    def roas(self) -> float:
        """Calculate Return on Ad Spend"""
        if self.total_spend and float(self.total_spend) > 0:
            return float(self.total_revenue or 0) / float(self.total_spend)
        return 0.0
    
    @hybrid_property
    def cpa(self) -> float:
        """Calculate Cost per Acquisition"""
        if self.conversion_count and self.conversion_count > 0:
            return float(self.total_spend or 0) / self.conversion_count
        return 0.0
    
    @hybrid_property
    def margin_pct(self) -> float:
        """Calculate profit margin percentage"""
        if self.total_revenue and float(self.total_revenue) > 0:
            return (self.profit / float(self.total_revenue)) * 100
        return 0.0



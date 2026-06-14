"""SQLAlchemy models for Zend Payments."""
from sqlalchemy import Column, String, Float, DateTime, Boolean, Text, JSON, Enum, Index
from datetime import datetime

from .database import Base


class PaymentIntentRecord(Base):
    """Payment intent persistence."""
    __tablename__ = "payment_intents"

    intent_id = Column(String(64), primary_key=True)
    payer_id = Column(String(120), nullable=True, index=True)
    recipient_id = Column(String(120), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    rail_policy = Column(String(20), default="stripe_first")
    commons_contribution_pct = Column(Float, default=0.0)
    note = Column(Text, nullable=True)
    risk_score = Column(Float, default=0.0)
    confirm_level = Column(String(20), default="light")
    status = Column(String(20), default="pending", index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)
    settled_at = Column(DateTime, nullable=True)
    
    # ZendLink
    zend_link_code = Column(String(32), unique=True, index=True)
    
    # Stripe
    stripe_checkout_session_id = Column(String(128), nullable=True)
    stripe_payment_intent_id = Column(String(128), nullable=True)
    stripe_checkout_url = Column(Text, nullable=True)
    
    # Solana
    solana_payment_request = Column(Text, nullable=True)
    solana_tx_signature = Column(String(128), nullable=True)
    
    # Metadata
    extra_data = Column(JSON, default=dict)

    __table_args__ = (
        Index("ix_intents_status_expires", "status", "expires_at"),
    )


class ZendReceiptRecord(Base):
    """Settlement receipt persistence."""
    __tablename__ = "receipts"

    receipt_id = Column(String(64), primary_key=True)
    intent_id = Column(String(64), nullable=False, index=True)
    rail = Column(String(20), nullable=False)  # "stripe" | "solana"
    external_ref = Column(String(256), nullable=False, unique=True)
    amount_settled = Column(Float, nullable=False)
    commons_contributed = Column(Float, default=0.0)
    settled_at = Column(DateTime, default=datetime.utcnow)
    blessing_message = Column(Text, nullable=True)
    payer_id = Column(String(120), nullable=True)
    recipient_id = Column(String(120), nullable=False)
    extra_data = Column(JSON, default=dict)


class MerchantRecord(Base):
    """Merchant configuration for POS."""
    __tablename__ = "merchants"

    merchant_id = Column(String(64), primary_key=True)
    display_name = Column(String(200), nullable=False)
    contact_email = Column(String(200), nullable=True)
    default_commons_tithe_pct = Column(Float, default=0.0)
    stripe_account_id = Column(String(128), nullable=True)  # Connected account
    solana_wallet = Column(String(64), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    extra_data = Column(JSON, default=dict)





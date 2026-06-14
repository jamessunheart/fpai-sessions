from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class Email(Base):
    __tablename__ = "emails"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sender = Column(String, index=True)
    recipient = Column(String, index=True)
    subject = Column(String)
    
    # Content (Encrypted)
    raw_content_encrypted = Column(Text)  # The full raw source
    body_text = Column(Text) # Parsed text body
    
    # Meta
    received_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False)
    
    # Intelligence
    category = Column(String, default="uncategorized") # verification, invoice, alert, etc.
    urgency_score = Column(Integer, default=0)
    entities = Column(JSON, default=dict) # Extracted keys, codes, etc.
    
    # Status
    action_taken = Column(String, nullable=True) # forwarded, stored, verified
    action_details = Column(Text, nullable=True)

class CredentialsArtifact(Base):
    """Extracted secrets from emails"""
    __tablename__ = "artifacts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email_id = Column(String, index=True)
    service = Column(String) # e.g. OpenAI
    artifact_type = Column(String) # api_key, verification_code, password_reset
    value_encrypted = Column(String) # The actual secret
    created_at = Column(DateTime, default=datetime.utcnow)
    used = Column(Boolean, default=False)

class BlockedSender(Base):
    """Spam defense list"""
    __tablename__ = "blocked_senders"
    
    email = Column(String, primary_key=True)
    reason = Column(String, nullable=True)
    blocked_at = Column(DateTime, default=datetime.utcnow)

class RoutingRule(Base):
    """Smart Routing Logic"""
    __tablename__ = "routing_rules"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String) # e.g. "Forward Invoices to Finance"
    
    # Condition
    condition_type = Column(String) # keyword, sender, ai_category
    condition_value = Column(String) # "Invoice", "stripe.com", "Finance"
    
    # Action
    action_type = Column(String) # forward, webhook, notify_slack
    action_target = Column(String) # "finance@fullpotential.ai", "https://hooks.slack.com/..."
    
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

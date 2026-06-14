"""SQLAlchemy models for Zend Wallet."""
from sqlalchemy import Column, String, Float, DateTime, Text, Boolean, JSON, Integer, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func


Base = declarative_base()


class ZendInvite(Base):
    """Invite that holds an escrowed UC amount until claimed."""
    __tablename__ = "zend_invites"

    invite_code = Column(String, primary_key=True)  # short code
    sender_member_id = Column(String, nullable=False, index=True)
    contact = Column(String, nullable=True)  # phone/email/handle freeform
    amount_uc = Column(Float, nullable=False)
    note = Column(Text, nullable=True)

    escrow_account = Column(String, nullable=False)
    escrow_tx_id = Column(String, nullable=True)

    status = Column(String, default="pending")  # pending, claimed, cancelled
    claimed_by_member_id = Column(String, nullable=True, index=True)
    claimed_tx_id = Column(String, nullable=True)

    created_at = Column(DateTime, default=func.now())
    claimed_at = Column(DateTime, nullable=True)


Index("ix_zend_invites_status_created", ZendInvite.status, ZendInvite.created_at)


class ZendSendLog(Base):
    """Audit log for sends initiated through Zend Wallet."""
    __tablename__ = "zend_sends"

    id = Column(String, primary_key=True)
    from_member_id = Column(String, nullable=False, index=True)
    to_member_id = Column(String, nullable=True, index=True)
    invite_code = Column(String, nullable=True, index=True)
    amount_uc = Column(Float, nullable=False)
    note = Column(Text, nullable=True)

    transfer_tx_from = Column(String, nullable=True)
    transfer_tx_to = Column(String, nullable=True)

    created_at = Column(DateTime, default=func.now())
    extra_data = Column(JSON, nullable=True)



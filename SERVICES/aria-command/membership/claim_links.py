"""
CLAIM LINKS
============

Generate shareable links for gifts that can be sent via any channel:
- Email
- WhatsApp
- SMS
- Any messaging app

Usage:
  /gift link 100 Thanks for hosting!
  → Generates: https://fullpotential.ai/claim/abc123xyz

The link can be shared anywhere. When clicked:
1. Shows the gift amount and message
2. Presents PMA agreement
3. Friend enters email or connects Telegram
4. Credits deposited to their wallet
"""

import os
import uuid
import logging
import secrets
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger("aria.membership.claims")

# Configuration
CLAIM_BASE_URL = os.getenv("CLAIM_BASE_URL", "https://fullpotential.ai/claim")
CLAIM_EXPIRY_DAYS = int(os.getenv("CLAIM_EXPIRY_DAYS", "30"))


@dataclass
class ClaimLink:
    """A shareable claim link for a gift."""
    id: str
    code: str  # Short URL-safe code
    from_member: str
    from_name: str
    amount: float
    message: Optional[str] = None
    recipient_hint: Optional[str] = None  # email, phone, or name
    expires_at: str = ""
    claimed_by: Optional[str] = None
    claimed_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def url(self) -> str:
        return f"{CLAIM_BASE_URL}/{self.code}"
    
    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.now() > datetime.fromisoformat(self.expires_at)
    
    @property
    def is_claimed(self) -> bool:
        return self.claimed_by is not None


def generate_claim_code() -> str:
    """Generate a short, URL-safe claim code."""
    # 8 characters, alphanumeric, easy to type
    return secrets.token_urlsafe(6)[:8]


class ClaimLinkManager:
    """Manages claim links for sharing gifts via any channel."""
    
    def __init__(self):
        from .member_db import get_member_db
        self.db = get_member_db()
        self._ensure_table()
        logger.info("ClaimLinkManager initialized")
    
    def _ensure_table(self):
        """Ensure the claim_links table exists."""
        with self.db._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS claim_links (
                    id TEXT PRIMARY KEY,
                    code TEXT UNIQUE NOT NULL,
                    from_member TEXT NOT NULL,
                    from_name TEXT,
                    amount REAL NOT NULL,
                    message TEXT,
                    recipient_hint TEXT,
                    expires_at TEXT,
                    claimed_by TEXT,
                    claimed_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (from_member) REFERENCES members(id),
                    FOREIGN KEY (claimed_by) REFERENCES members(id)
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_claim_code ON claim_links(code);")
    
    def create_link(
        self,
        from_member_id: str,
        amount: float,
        message: Optional[str] = None,
        recipient_hint: Optional[str] = None
    ) -> Optional[ClaimLink]:
        """
        Create a shareable claim link.
        
        Args:
            from_member_id: Sender's member ID
            amount: Amount of UC to gift
            message: Optional gift message
            recipient_hint: Optional hint about recipient (email, name)
        
        Returns:
            ClaimLink or None if insufficient balance
        """
        # Check sender balance
        wallet = self.db.get_wallet(from_member_id)
        if not wallet or wallet.available_credits < amount:
            return None
        
        # Deduct from sender (hold in escrow)
        if not self.db.deduct_credits(from_member_id, amount):
            return None
        
        # Get sender info
        sender = self.db.get_member(from_member_id)
        from_name = sender.display_name or sender.telegram_username or "A member"
        
        # Create claim link
        claim = ClaimLink(
            id=str(uuid.uuid4()),
            code=generate_claim_code(),
            from_member=from_member_id,
            from_name=from_name,
            amount=amount,
            message=message,
            recipient_hint=recipient_hint,
            expires_at=(datetime.now() + timedelta(days=CLAIM_EXPIRY_DAYS)).isoformat()
        )
        
        # Save to database
        with self.db._get_connection() as conn:
            conn.execute("""
                INSERT INTO claim_links 
                (id, code, from_member, from_name, amount, message, recipient_hint, 
                 expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                claim.id, claim.code, claim.from_member, claim.from_name,
                claim.amount, claim.message, claim.recipient_hint,
                claim.expires_at, claim.created_at
            ))
        
        logger.info(f"Created claim link {claim.code}: {amount} UC from {from_name}")
        return claim
    
    def get_by_code(self, code: str) -> Optional[ClaimLink]:
        """Get a claim link by its code."""
        with self.db._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM claim_links WHERE code = ?",
                (code,)
            ).fetchone()
            
            if not row:
                return None
            
            return ClaimLink(
                id=row["id"],
                code=row["code"],
                from_member=row["from_member"],
                from_name=row["from_name"],
                amount=row["amount"],
                message=row["message"],
                recipient_hint=row["recipient_hint"],
                expires_at=row["expires_at"],
                claimed_by=row["claimed_by"],
                claimed_at=row["claimed_at"],
                created_at=row["created_at"]
            )
    
    def claim(self, code: str, claimer_member_id: str) -> tuple[bool, str]:
        """
        Claim a gift using its code.
        
        Args:
            code: The claim code
            claimer_member_id: The member claiming the gift
        
        Returns:
            (success, message)
        """
        claim = self.get_by_code(code)
        
        if not claim:
            return False, "Claim link not found"
        
        if claim.is_claimed:
            return False, "This gift has already been claimed"
        
        if claim.is_expired:
            return False, "This claim link has expired"
        
        # Don't let sender claim their own gift
        if claim.from_member == claimer_member_id:
            return False, "You can't claim your own gift"
        
        # Credit the claimer
        if not self.db.add_credits(claimer_member_id, claim.amount):
            return False, "Failed to credit your wallet"
        
        # Mark as claimed
        with self.db._get_connection() as conn:
            conn.execute("""
                UPDATE claim_links SET 
                    claimed_by = ?,
                    claimed_at = ?
                WHERE id = ?
            """, (claimer_member_id, datetime.now().isoformat(), claim.id))
        
        # Record transaction
        from .member_db import Transaction, TransactionType, TransactionStatus
        tx = Transaction(
            from_member=claim.from_member,
            to_member=claimer_member_id,
            amount=claim.amount,
            type=TransactionType.GIFT,
            status=TransactionStatus.COMPLETED,
            description=f"Gift claimed via link: {claim.message or 'No message'}",
            completed_at=datetime.now().isoformat()
        )
        self.db.create_transaction(tx)
        
        logger.info(f"Claim {code} claimed by {claimer_member_id}: {claim.amount} UC")
        return True, f"You received {claim.amount:.2f} UC from {claim.from_name}!"
    
    def cancel(self, code: str, requester_member_id: str) -> tuple[bool, str]:
        """
        Cancel a claim link and refund the sender.
        
        Only the sender can cancel.
        """
        claim = self.get_by_code(code)
        
        if not claim:
            return False, "Claim link not found"
        
        if claim.from_member != requester_member_id:
            return False, "Only the sender can cancel this gift"
        
        if claim.is_claimed:
            return False, "This gift has already been claimed"
        
        # Refund the sender
        if not self.db.add_credits(claim.from_member, claim.amount):
            return False, "Failed to refund"
        
        # Delete the claim
        with self.db._get_connection() as conn:
            conn.execute("DELETE FROM claim_links WHERE id = ?", (claim.id,))
        
        logger.info(f"Claim {code} cancelled, refunded {claim.amount} UC")
        return True, f"Gift cancelled. {claim.amount:.2f} UC refunded to your wallet."
    
    def get_pending_by_sender(self, member_id: str) -> list[ClaimLink]:
        """Get all unclaimed links created by a member."""
        with self.db._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM claim_links 
                WHERE from_member = ? AND claimed_by IS NULL
                ORDER BY created_at DESC
            """, (member_id,)).fetchall()
            
            return [ClaimLink(
                id=row["id"],
                code=row["code"],
                from_member=row["from_member"],
                from_name=row["from_name"],
                amount=row["amount"],
                message=row["message"],
                recipient_hint=row["recipient_hint"],
                expires_at=row["expires_at"],
                claimed_by=row["claimed_by"],
                claimed_at=row["claimed_at"],
                created_at=row["created_at"]
            ) for row in rows]
    
    def format_share_messages(self, claim: ClaimLink) -> Dict[str, str]:
        """
        Generate pre-formatted messages for different channels.
        
        Returns dict with keys: email_subject, email_body, whatsapp, sms, generic
        """
        amount = f"{claim.amount:.0f}" if claim.amount == int(claim.amount) else f"{claim.amount:.2f}"
        
        return {
            "email_subject": f"🎁 {claim.from_name} sent you {amount} UC credits!",
            
            "email_body": f"""Hi!

{claim.from_name} has sent you {amount} Universal Credits (UC) through the Conscious Wealth Fellowship.

{f'Message: "{claim.message}"' if claim.message else ''}

Click here to claim your gift:
{claim.url}

What are Universal Credits?
UC are credits you can use within the Full Potential ecosystem. You can hold them, use them for services, or even have them traded on your behalf in our Conscious Wealth Pool.

This link expires in {CLAIM_EXPIRY_DAYS} days.

- The Full Potential Team
""",
            
            "whatsapp": f"""🎁 *{claim.from_name} sent you {amount} UC!*

{f'_{claim.message}_' if claim.message else ''}

Claim your gift here:
{claim.url}

(This link expires in {CLAIM_EXPIRY_DAYS} days)""",
            
            "sms": f"{claim.from_name} sent you {amount} UC credits! Claim here: {claim.url}",
            
            "generic": f"""🎁 {claim.from_name} sent you {amount} UC!

{claim.message or ''}

Claim your gift: {claim.url}

Expires in {CLAIM_EXPIRY_DAYS} days."""
        }


# ============================================================================
# SINGLETON
# ============================================================================

_manager: Optional[ClaimLinkManager] = None


def get_claim_manager() -> ClaimLinkManager:
    """Get or create the claim link manager."""
    global _manager
    if _manager is None:
        _manager = ClaimLinkManager()
    return _manager









"""
MEMBER ONBOARDING
==================

Handles new member onboarding flow via Telegram.

Flow:
1. User receives gift or starts chat
2. Show PMA agreement summary
3. User accepts (inline button)
4. Create member account
5. Optionally show trading opt-in
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import httpx

from .member_db import MemberDB, get_member_db, Member, PendingGift
from .member_wallet import MemberWallet

logger = logging.getLogger("aria.membership.onboarding")

# Telegram config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


# ============================================================================
# PMA AGREEMENT TEXT
# ============================================================================

PMA_SUMMARY = """
📜 **CONSCIOUS WEALTH FELLOWSHIP**
**Private Membership Association Agreement**

By joining, you agree to:

✅ **Membership Terms**
• This is a private association, not a public service
• You're joining as a private member, not a customer
• All activities are private member-to-member transactions

✅ **Credit Terms**
• Universal Credits (UC) are internal membership credits
• 1 UC = $1 USD equivalent
• Credits are for use within the Fellowship

✅ **Trading Pool (Optional)**
• You may opt your credits into Aria's trading pool
• Returns distributed pro-rata to your share
• Capital is at risk - you may lose some or all
• You can withdraw anytime

✅ **Your Rights**
• Access to Fellowship services and tools
• Vote on Fellowship matters (future)
• Withdraw your credits anytime
• Leave the Fellowship anytime

_Full agreement: fullpotential.ai/pma-agreement_
"""

TRADING_SUMMARY = """
💰 **TRADING POOL PARTICIPATION**

By opting in, you understand:

⚠️ **Risks**
• Trading involves risk of loss
• Past performance doesn't guarantee future returns
• You may lose some or all of your credits
• This is NOT investment advice

📊 **How It Works**
• Your credits join the shared trading pool
• Aria trades on behalf of all pool members
• Returns distributed pro-rata to your share
• 10% of gains go to operations

✅ **Your Control**
• Opt out and withdraw anytime
• Check balance anytime with /balance
• See returns with /returns

_Full terms: fullpotential.ai/trading-terms_
"""


@dataclass
class OnboardingState:
    """Track onboarding state for a user."""
    telegram_id: int
    stage: str  # "start", "pma_shown", "pma_accepted", "trading_shown", "completed"
    pending_gift_id: Optional[str] = None
    referred_by: Optional[str] = None


class MemberOnboarding:
    """
    Handles member onboarding flow.
    
    Stages:
    1. start - Initial contact
    2. pma_shown - PMA agreement displayed
    3. pma_accepted - Member created
    4. trading_shown - Trading opt-in displayed
    5. completed - Fully onboarded
    """
    
    def __init__(self, db: MemberDB = None):
        self.db = db or get_member_db()
        self.active_onboardings: Dict[int, OnboardingState] = {}
    
    async def start_onboarding(
        self,
        telegram_id: int,
        telegram_username: Optional[str] = None,
        pending_gift_id: Optional[str] = None,
        referred_by: Optional[str] = None
    ) -> str:
        """
        Start the onboarding flow.
        
        Returns the initial message to send.
        """
        # Check if already a member
        existing = self.db.get_member_by_telegram(telegram_id)
        if existing:
            # Already a member, maybe accepting a gift
            if pending_gift_id:
                return await self._accept_gift(existing, pending_gift_id)
            
            return (
                f"Welcome back! 👋\n\n"
                f"You're already a member of the Fellowship.\n"
                f"Type /balance to see your wallet."
            )
        
        # Store onboarding state
        state = OnboardingState(
            telegram_id=telegram_id,
            stage="pma_shown",
            pending_gift_id=pending_gift_id,
            referred_by=referred_by
        )
        self.active_onboardings[telegram_id] = state
        
        # Return PMA agreement
        return PMA_SUMMARY
    
    def get_pma_buttons(self, gift_id: Optional[str] = None) -> list:
        """Get inline buttons for PMA agreement."""
        buttons = [
            [
                {"text": "📜 View Full Agreement", "url": "https://fullpotential.ai/pma-agreement"},
            ],
            [
                {"text": "✅ I Accept & Join", "callback_data": f"pma_accept:{gift_id or 'none'}"},
            ],
        ]
        
        if gift_id:
            buttons.append([
                {"text": "❌ Decline Gift", "callback_data": f"pma_decline:{gift_id}"}
            ])
        
        return buttons
    
    async def handle_pma_accept(
        self,
        telegram_id: int,
        telegram_username: Optional[str] = None,
        display_name: Optional[str] = None,
        gift_id: Optional[str] = None
    ) -> str:
        """
        Handle PMA acceptance.
        
        Creates member account and shows trading opt-in.
        """
        # Check not already a member
        existing = self.db.get_member_by_telegram(telegram_id)
        if existing:
            if gift_id and gift_id != "none":
                return await self._accept_gift(existing, gift_id)
            return "You're already a member! Type /balance to check your wallet."
        
        # Get onboarding state
        state = self.active_onboardings.get(telegram_id)
        referred_by = state.referred_by if state else None
        
        # Create member
        member = Member(
            id=None,
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            display_name=display_name or telegram_username,
            pma_agreed_at=datetime.now().isoformat(),
            referred_by=referred_by
        )
        
        member_id = self.db.create_member(member)
        logger.info(f"Created new member {member_id} (telegram: {telegram_id})")
        
        # Handle pending gift
        gift_message = ""
        if gift_id and gift_id != "none":
            wallet = MemberWallet(member_id, self.db)
            result = wallet.accept_pending_gift(gift_id)
            if result.success:
                gift = self.db.get_pending_gift(gift_id)
                gift_amount = gift.amount if gift else 0
                gift_message = f"\n\n🎁 You received {gift_amount:.2f} UC!"
                
                # Notify sender
                if gift:
                    sender = self.db.get_member(gift.from_member)
                    if sender:
                        await self._notify_gift_accepted(
                            sender.telegram_id,
                            telegram_username or str(telegram_id)
                        )
        
        # Update state
        if state:
            state.stage = "trading_shown"
        
        # Return welcome + trading opt-in
        return (
            f"🎉 **Welcome to the Fellowship!**{gift_message}\n\n"
            f"You're now a member of the Conscious Wealth Fellowship.\n\n"
            f"Would you like to put your credits to work?\n\n"
            + TRADING_SUMMARY
        )
    
    def get_trading_buttons(self) -> list:
        """Get inline buttons for trading opt-in."""
        return [
            [
                {"text": "📜 View Full Terms", "url": "https://fullpotential.ai/trading-terms"},
            ],
            [
                {"text": "💰 Yes, Trade My Credits", "callback_data": "trading_accept"},
                {"text": "💳 Keep as Credits", "callback_data": "trading_decline"},
            ],
        ]
    
    async def handle_trading_accept(self, telegram_id: int) -> str:
        """Handle trading opt-in acceptance."""
        member = self.db.get_member_by_telegram(telegram_id)
        if not member:
            return "Please join the Fellowship first."
        
        # Record trading agreement
        self.db.agree_to_trading(member.id)
        
        # Opt all credits into pool
        wallet = MemberWallet(member.id, self.db)
        balance = wallet.get_balance()
        
        if balance["available"] > 0:
            result = wallet.opt_into_pool(balance["available"])
            pool_message = f"\n\n{result.message}"
        else:
            pool_message = "\n\nYou have no credits yet. When you receive credits, you can add them to the pool with `/poolopt in`."
        
        # Clean up state
        if telegram_id in self.active_onboardings:
            del self.active_onboardings[telegram_id]
        
        return (
            f"✨ **You're all set!**\n\n"
            f"You've joined the Conscious Wealth Pool.{pool_message}\n\n"
            f"**Commands:**\n"
            f"• `/balance` - Check your wallet\n"
            f"• `/pool` - See pool status\n"
            f"• `/returns` - View your returns\n"
            f"• `/poolopt out` - Withdraw from pool"
        )
    
    async def handle_trading_decline(self, telegram_id: int) -> str:
        """Handle trading opt-in decline."""
        # Clean up state
        if telegram_id in self.active_onboardings:
            del self.active_onboardings[telegram_id]
        
        return (
            f"✅ **You're all set!**\n\n"
            f"Your credits will stay in your wallet.\n"
            f"You can opt into trading anytime with `/poolopt in`.\n\n"
            f"**Commands:**\n"
            f"• `/balance` - Check your wallet\n"
            f"• `/gift @user amount` - Send credits\n"
            f"• `/poolopt in` - Join trading pool"
        )
    
    async def handle_gift_decline(self, telegram_id: int, gift_id: str) -> str:
        """Handle gift decline."""
        gift = self.db.get_pending_gift(gift_id)
        if not gift:
            return "Gift not found or already processed."
        
        # Return credits to sender
        sender_wallet = MemberWallet(gift.from_member, self.db)
        self.db.add_credits(gift.from_member, gift.amount)
        
        # Delete pending gift
        self.db.delete_pending_gift(gift_id)
        
        # Notify sender
        sender = self.db.get_member(gift.from_member)
        if sender:
            await self._notify_gift_declined(
                sender.telegram_id,
                gift.to_telegram_username or str(gift.to_telegram_id),
                gift.amount
            )
        
        # Clean up state
        if telegram_id in self.active_onboardings:
            del self.active_onboardings[telegram_id]
        
        return "Gift declined. The sender has been notified."
    
    async def _accept_gift(self, member: Member, gift_id: str) -> str:
        """Accept a gift for an existing member."""
        wallet = MemberWallet(member.id, self.db)
        result = wallet.accept_pending_gift(gift_id)
        
        if result.success:
            gift = self.db.get_pending_gift(gift_id)
            
            # Notify sender
            if gift:
                sender = self.db.get_member(gift.from_member)
                if sender:
                    await self._notify_gift_accepted(
                        sender.telegram_id,
                        member.telegram_username or str(member.telegram_id)
                    )
            
            return (
                f"🎁 {result.message}\n\n"
                f"Type /balance to see your wallet."
            )
        else:
            return f"❌ {result.message}"
    
    async def _notify_gift_accepted(self, sender_telegram_id: int, recipient_name: str):
        """Notify sender that gift was accepted."""
        await self._send_telegram(
            sender_telegram_id,
            f"✅ @{recipient_name} accepted your gift!"
        )
    
    async def _notify_gift_declined(
        self,
        sender_telegram_id: int,
        recipient_name: str,
        amount: float
    ):
        """Notify sender that gift was declined."""
        await self._send_telegram(
            sender_telegram_id,
            f"❌ @{recipient_name} declined your gift.\n"
            f"Your {amount:.2f} UC has been refunded."
        )
    
    async def _send_telegram(self, chat_id: int, text: str):
        """Send a Telegram message."""
        if not TELEGRAM_TOKEN:
            return
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": "Markdown"
                    }
                )
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")


# ============================================================================
# SINGLETON
# ============================================================================

_onboarding: Optional[MemberOnboarding] = None


def get_onboarding() -> MemberOnboarding:
    """Get or create the onboarding instance."""
    global _onboarding
    if _onboarding is None:
        _onboarding = MemberOnboarding()
    return _onboarding

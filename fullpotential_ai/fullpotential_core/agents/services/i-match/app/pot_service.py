"""
POTENTIAL (POT) Token Service
Manages internal currency transactions, rewards, and spending
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
import json


class POTService:
    """Service for managing POTENTIAL token transactions"""

    # POT Earning Rates (how much users earn for various actions)
    EARNING_RATES = {
        # Provider earnings
        "provider_profile_creation": 50,
        "provider_first_response": 25,
        "provider_engagement_base": lambda deal_value: int(deal_value * 0.05),  # 5% of deal
        "provider_rating_bonus": 100,  # If rating >= 4.5 stars
        "provider_referral": 500,
        "provider_content": 100,  # Average, varies by content type

        # Seeker earnings
        "seeker_profile_creation": 25,
        "seeker_first_engagement": 100,
        "seeker_rating": 10,
        "seeker_testimonial": 50,
        "seeker_success_story": 200,
        "seeker_referral": 250,

        # Universal earnings
        "daily_login": 1,
        "bug_report": 100,
        "feature_suggestion": 50,
    }

    # POT Spending Costs (how much features cost)
    SPENDING_COSTS = {
        "premium_match": 100,  # Match with 10 providers instead of 3
        "rush_match": 200,     # Expedited matching (<12 hours)
        "re_match": 50,        # Get new matches if first didn't work
        "custom_criteria_match": 150,

        "profile_boost_month": 500,  # Appear first in matches for 1 month
        "verified_badge": 1000,       # One-time verification badge
        "featured_listing_week": 300,
        "analytics_month": 200,
        "priority_support_month": 100,

        "workshop": lambda pot_price: pot_price,  # Variable pricing
        "event": lambda pot_price: pot_price,
        "premium_content_month": 200,
        "consulting": 500,
    }

    # Redemption rate (POT to USD conversion)
    REDEMPTION_RATE = 0.80  # 1 POT = $0.80 (20% platform fee)

    def __init__(self, db: Session):
        self.db = db

    def get_user_balance(self, user_id: int) -> int:
        """Get current POT balance for user"""
        from app.models import User  # Import here to avoid circular dependency

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        return user.pot_balance

    def award_pot(
        self,
        user_id: int,
        category: str,
        amount: Optional[int] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Award POT tokens to a user for a specific action

        Args:
            user_id: ID of user receiving POT
            category: Category of earning (e.g., 'provider_profile_creation')
            amount: Amount of POT to award (if None, use EARNING_RATES)
            reference_type: Type of related record (e.g., 'engagement', 'rating')
            reference_id: ID of related record
            description: Human-readable description
            metadata: Additional context as JSON

        Returns:
            Transaction record as dict
        """
        from app.models import User, POTTransaction

        # Get amount from earning rates if not provided
        if amount is None:
            earning = self.EARNING_RATES.get(category)
            if callable(earning):
                raise ValueError(f"Category {category} requires amount parameter")
            if earning is None:
                raise ValueError(f"Unknown earning category: {category}")
            amount = earning

        # Get user and current balance
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        balance_before = user.pot_balance
        balance_after = balance_before + amount

        # Create transaction record
        transaction = POTTransaction(
            user_id=user_id,
            amount=amount,
            transaction_type="earn",
            category=category,
            description=description or f"Earned {amount} POT for {category}",
            reference_type=reference_type,
            reference_id=reference_id,
            balance_before=balance_before,
            balance_after=balance_after,
            metadata=metadata
        )
        self.db.add(transaction)

        # Update user balances
        user.pot_balance = balance_after
        user.total_pot_earned += amount

        self.db.commit()
        self.db.refresh(transaction)

        return {
            "transaction_id": transaction.id,
            "user_id": user_id,
            "amount": amount,
            "category": category,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "created_at": transaction.created_at
        }

    def spend_pot(
        self,
        user_id: int,
        category: str,
        amount: Optional[int] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        burn: bool = True  # Most spending burns tokens (deflationary)
    ) -> Dict[str, Any]:
        """
        Deduct POT tokens from user for spending on platform features

        Args:
            user_id: ID of user spending POT
            category: Category of spending (e.g., 'premium_match')
            amount: Amount of POT to spend (if None, use SPENDING_COSTS)
            reference_type: Type of related record
            reference_id: ID of related record
            description: Human-readable description
            metadata: Additional context as JSON
            burn: Whether to burn tokens (remove from circulation) - default True

        Returns:
            Transaction record as dict

        Raises:
            ValueError: If user has insufficient balance
        """
        from app.models import User, POTTransaction

        # Get amount from spending costs if not provided
        if amount is None:
            cost = self.SPENDING_COSTS.get(category)
            if callable(cost):
                raise ValueError(f"Category {category} requires amount parameter")
            if cost is None:
                raise ValueError(f"Unknown spending category: {category}")
            amount = cost

        # Get user and check balance
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        balance_before = user.pot_balance
        if balance_before < amount:
            raise ValueError(
                f"Insufficient POT balance. Required: {amount}, Available: {balance_before}"
            )

        balance_after = balance_before - amount

        # Create transaction record
        transaction_type = "burn" if burn else "spend"
        transaction = POTTransaction(
            user_id=user_id,
            amount=-amount,  # Negative for spending
            transaction_type=transaction_type,
            category=category,
            description=description or f"Spent {amount} POT on {category}",
            reference_type=reference_type,
            reference_id=reference_id,
            balance_before=balance_before,
            balance_after=balance_after,
            metadata=metadata
        )
        self.db.add(transaction)

        # Update user balances
        user.pot_balance = balance_after
        user.total_pot_spent += amount
        if burn:
            user.total_pot_burned += amount

        self.db.commit()
        self.db.refresh(transaction)

        return {
            "transaction_id": transaction.id,
            "user_id": user_id,
            "amount": -amount,
            "category": category,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "burned": burn,
            "created_at": transaction.created_at
        }

    def redeem_pot_for_usd(
        self,
        user_id: int,
        pot_amount: int,
        payment_method: str = "bank_transfer",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Redeem POT tokens for USD (with 20% platform fee)

        Args:
            user_id: ID of user redeeming POT
            pot_amount: Amount of POT to redeem
            payment_method: How user wants to be paid
            metadata: Additional context (bank details, etc.)

        Returns:
            Redemption details including USD amount
        """
        from app.models import User

        # Check balance
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        if user.pot_balance < pot_amount:
            raise ValueError(
                f"Insufficient POT balance. Required: {pot_amount}, Available: {user.pot_balance}"
            )

        # Calculate USD payout (1 POT = $0.80 after 20% fee)
        usd_amount = pot_amount * self.REDEMPTION_RATE

        # Create redemption transaction (does not burn, but removes from circulation)
        redemption_metadata = {
            "payment_method": payment_method,
            "usd_amount": usd_amount,
            "redemption_rate": self.REDEMPTION_RATE,
            **(metadata or {})
        }

        transaction = self.spend_pot(
            user_id=user_id,
            category="pot_redemption",
            amount=pot_amount,
            reference_type="redemption",
            description=f"Redeemed {pot_amount} POT for ${usd_amount:.2f} USD",
            metadata=redemption_metadata,
            burn=False  # Redemption doesn't burn, but removes from user's balance
        )

        return {
            **transaction,
            "usd_amount": usd_amount,
            "payment_method": payment_method,
            "status": "pending"  # Pending manual payout processing
        }

    def get_transaction_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        transaction_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get POT transaction history for a user"""
        from app.models import POTTransaction

        query = self.db.query(POTTransaction).filter(
            POTTransaction.user_id == user_id
        )

        if transaction_type:
            query = query.filter(POTTransaction.transaction_type == transaction_type)

        query = query.order_by(POTTransaction.created_at.desc())
        query = query.limit(limit).offset(offset)

        transactions = query.all()

        return [
            {
                "id": t.id,
                "amount": t.amount,
                "transaction_type": t.transaction_type,
                "category": t.category,
                "description": t.description,
                "balance_after": t.balance_after,
                "created_at": t.created_at.isoformat() if t.created_at else None
            }
            for t in transactions
        ]

    def get_economy_stats(self) -> Dict[str, Any]:
        """Get overall POT economy statistics"""
        from app.models import User, POTTransaction

        total_users = self.db.query(func.count(User.id)).scalar()
        users_with_pot = self.db.query(func.count(User.id)).filter(
            User.pot_balance > 0
        ).scalar()

        total_in_circulation = self.db.query(
            func.sum(User.pot_balance)
        ).scalar() or 0

        total_earned = self.db.query(
            func.sum(User.total_pot_earned)
        ).scalar() or 0

        total_spent = self.db.query(
            func.sum(User.total_pot_spent)
        ).scalar() or 0

        total_burned = self.db.query(
            func.sum(User.total_pot_burned)
        ).scalar() or 0

        # Transactions in last 7 days
        seven_days_ago = datetime.now().timestamp() - (7 * 24 * 60 * 60)
        recent_transactions = self.db.query(func.count(POTTransaction.id)).filter(
            POTTransaction.created_at >= datetime.fromtimestamp(seven_days_ago)
        ).scalar()

        return {
            "total_users": total_users,
            "users_with_pot": users_with_pot,
            "participation_rate": f"{(users_with_pot / total_users * 100):.1f}%" if total_users > 0 else "0%",
            "total_pot_in_circulation": total_in_circulation,
            "total_pot_earned_all_time": total_earned,
            "total_pot_spent_all_time": total_spent,
            "total_pot_burned_all_time": total_burned,
            "burn_rate": f"{(total_burned / total_spent * 100):.1f}%" if total_spent > 0 else "0%",
            "transactions_last_7_days": recent_transactions
        }

    # Convenience methods for common earning scenarios

    def award_profile_creation(self, user_id: int, account_type: str) -> Dict[str, Any]:
        """Award POT for completing profile"""
        category = f"{account_type}_profile_creation"  # provider_profile_creation or seeker_profile_creation
        return self.award_pot(
            user_id=user_id,
            category=category,
            description=f"Completed {account_type} profile"
        )

    def award_first_response(self, user_id: int, match_id: int) -> Dict[str, Any]:
        """Award POT for provider's first response to a match"""
        return self.award_pot(
            user_id=user_id,
            category="provider_first_response",
            reference_type="match",
            reference_id=match_id,
            description="Responded to first match within 24 hours"
        )

    def award_engagement_bonus(
        self,
        user_id: int,
        account_type: str,
        engagement_id: int,
        deal_value_usd: Optional[float] = None
    ) -> Dict[str, Any]:
        """Award POT for completing an engagement"""
        if account_type == "provider" and deal_value_usd:
            # Provider gets 5% of deal value in POT
            amount = int(deal_value_usd * 0.05)
            category = "provider_engagement_base"
        elif account_type == "seeker":
            # Seeker gets flat 100 POT for first engagement
            amount = 100
            category = "seeker_first_engagement"
        else:
            raise ValueError("Invalid account_type or missing deal_value_usd")

        return self.award_pot(
            user_id=user_id,
            category=category,
            amount=amount,
            reference_type="engagement",
            reference_id=engagement_id,
            description=f"Completed engagement"
        )

    def award_rating_bonus(
        self,
        user_id: int,
        rating_id: int,
        rating_value: int,
        is_rater: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Award POT for giving or receiving a rating

        Args:
            user_id: User receiving POT
            rating_id: ID of rating record
            rating_value: Star rating (1-5)
            is_rater: True if user gave the rating, False if user received it

        Returns:
            Transaction dict if POT awarded, None otherwise
        """
        if is_rater:
            # Award POT for giving rating (always 10 POT)
            return self.award_pot(
                user_id=user_id,
                category="seeker_rating",
                reference_type="rating",
                reference_id=rating_id,
                description="Provided rating for engagement"
            )
        else:
            # Award bonus POT for receiving excellent rating (≥ 4.5 stars)
            if rating_value >= 5:  # 5 stars
                return self.award_pot(
                    user_id=user_id,
                    category="provider_rating_bonus",
                    reference_type="rating",
                    reference_id=rating_id,
                    description="Received 5-star rating"
                )
            # No POT for receiving lower ratings
            return None

    def charge_premium_match(self, user_id: int, seeker_id: int) -> Dict[str, Any]:
        """Charge user for premium match (10 providers instead of 3)"""
        return self.spend_pot(
            user_id=user_id,
            category="premium_match",
            reference_type="seeker",
            reference_id=seeker_id,
            description="Premium match with 10 providers",
            burn=True
        )

    def charge_profile_boost(
        self,
        user_id: int,
        provider_id: int,
        duration_days: int = 30
    ) -> Dict[str, Any]:
        """Charge provider for profile boost"""
        return self.spend_pot(
            user_id=user_id,
            category="profile_boost_month",
            reference_type="provider",
            reference_id=provider_id,
            description=f"Profile boost for {duration_days} days",
            burn=True,
            metadata={"duration_days": duration_days}
        )

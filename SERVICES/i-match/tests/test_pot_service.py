"""
Automated Tests for POT Token Service
Tests all earning, spending, and economy functions
"""

import pytest
import sys
from datetime import datetime
sys.path.insert(0, '/Users/jamessunheart/Development/SERVICES/i-match')

from app.database import SessionLocal
from app.pot_service import POTService
from app.models_v2 import User, Category, Engagement, Rating


@pytest.fixture
def db_session():
    """Create a test database session"""
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def pot_service(db_session):
    """Create POT service instance"""
    return POTService(db_session)


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(
        email=f"test_{datetime.now().timestamp()}@imatch.com",
        name="Test User",
        account_type="seeker"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    db_session.delete(user)
    db_session.commit()


class TestPOTEarning:
    """Test POT earning mechanisms"""

    def test_profile_creation_seeker(self, pot_service, test_user, db_session):
        """Test POT reward for seeker profile creation"""
        result = pot_service.award_profile_creation(
            user_id=test_user.id,
            account_type="seeker"
        )

        assert result['amount'] == 25
        assert result['balance_after'] == 25

        # Verify user balance updated
        db_session.refresh(test_user)
        assert test_user.pot_balance == 25
        assert test_user.total_pot_earned == 25

    def test_profile_creation_provider(self, pot_service, db_session):
        """Test POT reward for provider profile creation"""
        provider = User(
            email=f"provider_{datetime.now().timestamp()}@imatch.com",
            name="Test Provider",
            account_type="provider"
        )
        db_session.add(provider)
        db_session.commit()

        result = pot_service.award_profile_creation(
            user_id=provider.id,
            account_type="provider"
        )

        assert result['amount'] == 50  # Providers get 50 POT
        assert result['balance_after'] == 50

        db_session.delete(provider)
        db_session.commit()

    def test_first_response(self, pot_service, test_user):
        """Test POT reward for first response to match"""
        result = pot_service.award_first_response(
            user_id=test_user.id,
            match_id=1
        )

        assert result['amount'] == 25
        assert result['category'] == 'provider_first_response'

    def test_engagement_bonus_provider(self, pot_service, test_user):
        """Test POT reward for provider completing engagement"""
        deal_value = 25000

        result = pot_service.award_engagement_bonus(
            user_id=test_user.id,
            account_type="provider",
            engagement_id=1,
            deal_value_usd=deal_value
        )

        # Provider gets 5% of deal value in POT
        expected_pot = int(deal_value * 0.05)  # 1,250 POT
        assert result['amount'] == expected_pot

    def test_engagement_bonus_seeker(self, pot_service, test_user):
        """Test POT reward for seeker completing engagement"""
        result = pot_service.award_engagement_bonus(
            user_id=test_user.id,
            account_type="seeker",
            engagement_id=1
        )

        # Seeker gets flat 100 POT
        assert result['amount'] == 100

    def test_rating_bonus_giver(self, pot_service, test_user):
        """Test POT reward for giving a rating"""
        result = pot_service.award_rating_bonus(
            user_id=test_user.id,
            rating_id=1,
            rating_value=4,
            is_rater=True
        )

        # Giver always gets 10 POT
        assert result['amount'] == 10

    def test_rating_bonus_receiver_5_stars(self, pot_service, test_user):
        """Test POT bonus for receiving 5-star rating"""
        result = pot_service.award_rating_bonus(
            user_id=test_user.id,
            rating_id=1,
            rating_value=5,
            is_rater=False
        )

        # Receiver gets 100 POT for 5 stars
        assert result['amount'] == 100

    def test_rating_bonus_receiver_low_stars(self, pot_service, test_user):
        """Test no POT bonus for receiving low rating"""
        result = pot_service.award_rating_bonus(
            user_id=test_user.id,
            rating_id=1,
            rating_value=3,
            is_rater=False
        )

        # No bonus for ratings < 5 stars
        assert result is None

    def test_multiple_earnings(self, pot_service, test_user, db_session):
        """Test accumulating multiple POT earnings"""
        # Award profile creation
        pot_service.award_profile_creation(test_user.id, "seeker")

        # Award engagement bonus
        pot_service.award_engagement_bonus(test_user.id, "seeker", 1)

        # Award rating
        pot_service.award_rating_bonus(test_user.id, 1, 5, True)

        # Check total
        db_session.refresh(test_user)
        expected_total = 25 + 100 + 10  # 135 POT
        assert test_user.pot_balance == expected_total
        assert test_user.total_pot_earned == expected_total


class TestPOTSpending:
    """Test POT spending mechanisms"""

    def test_spend_with_sufficient_balance(self, pot_service, test_user, db_session):
        """Test spending POT with sufficient balance"""
        # Award POT first
        pot_service.award_pot(test_user.id, "seeker_profile_creation")
        pot_service.award_pot(test_user.id, "seeker_first_engagement")

        db_session.refresh(test_user)
        initial_balance = test_user.pot_balance  # 125 POT

        # Spend 100 POT on premium match
        result = pot_service.charge_premium_match(
            user_id=test_user.id,
            seeker_id=1
        )

        assert result['amount'] == -100
        assert result['balance_after'] == initial_balance - 100
        assert result['burned'] is True

        # Verify user balance
        db_session.refresh(test_user)
        assert test_user.pot_balance == initial_balance - 100
        assert test_user.total_pot_spent == 100
        assert test_user.total_pot_burned == 100

    def test_spend_insufficient_balance(self, pot_service, test_user):
        """Test spending POT with insufficient balance"""
        # User has 0 POT, trying to spend 100
        with pytest.raises(ValueError, match="Insufficient POT balance"):
            pot_service.charge_premium_match(
                user_id=test_user.id,
                seeker_id=1
            )

    def test_profile_boost(self, pot_service, test_user, db_session):
        """Test charging for profile boost"""
        # Award enough POT
        for _ in range(10):
            pot_service.award_pot(test_user.id, "seeker_profile_creation")

        db_session.refresh(test_user)
        initial_balance = test_user.pot_balance

        # Buy profile boost (500 POT)
        result = pot_service.charge_profile_boost(
            user_id=test_user.id,
            provider_id=1,
            duration_days=30
        )

        assert result['amount'] == -500
        assert result['balance_after'] == initial_balance - 500

    def test_burn_vs_spend(self, pot_service, test_user, db_session):
        """Test difference between burning and spending"""
        # Award POT
        pot_service.award_pot(test_user.id, "seeker_profile_creation")
        pot_service.award_pot(test_user.id, "seeker_first_engagement")

        # Spend with burn
        pot_service.spend_pot(
            user_id=test_user.id,
            category="premium_match",
            burn=True
        )

        db_session.refresh(test_user)
        assert test_user.total_pot_burned == 100

        # Spend without burn (redemption)
        pot_service.spend_pot(
            user_id=test_user.id,
            category="pot_redemption",
            amount=25,
            burn=False
        )

        db_session.refresh(test_user)
        assert test_user.total_pot_burned == 100  # Unchanged
        assert test_user.total_pot_spent == 125


class TestPOTRedemption:
    """Test POT redemption for USD"""

    def test_redeem_pot_for_usd(self, pot_service, test_user, db_session):
        """Test redeeming POT for USD"""
        # Award 1,000 POT
        for _ in range(40):
            pot_service.award_pot(test_user.id, "seeker_profile_creation")

        db_session.refresh(test_user)
        assert test_user.pot_balance >= 1000

        # Redeem 1,000 POT for USD
        result = pot_service.redeem_pot_for_usd(
            user_id=test_user.id,
            pot_amount=1000,
            payment_method="bank_transfer"
        )

        # Should get $800 (1 POT = $0.80 after 20% fee)
        assert result['usd_amount'] == 800.0
        assert result['payment_method'] == "bank_transfer"
        assert result['status'] == "pending"

        # Verify POT deducted
        db_session.refresh(test_user)
        assert test_user.pot_balance < 1000

    def test_redeem_insufficient_balance(self, pot_service, test_user):
        """Test redemption with insufficient balance"""
        with pytest.raises(ValueError, match="Insufficient POT balance"):
            pot_service.redeem_pot_for_usd(
                user_id=test_user.id,
                pot_amount=1000
            )


class TestPOTHistory:
    """Test transaction history and queries"""

    def test_get_balance(self, pot_service, test_user):
        """Test getting user balance"""
        balance = pot_service.get_user_balance(test_user.id)
        assert balance == 0  # New user starts at 0

    def test_transaction_history(self, pot_service, test_user):
        """Test retrieving transaction history"""
        # Create multiple transactions
        pot_service.award_pot(test_user.id, "seeker_profile_creation")
        pot_service.award_pot(test_user.id, "seeker_first_engagement")
        pot_service.award_pot(test_user.id, "seeker_rating")

        # Get history
        history = pot_service.get_transaction_history(test_user.id, limit=10)

        assert len(history) == 3
        assert all(txn['amount'] > 0 for txn in history)  # All earnings

    def test_transaction_history_filtered(self, pot_service, test_user, db_session):
        """Test filtering transaction history by type"""
        # Create mix of earn and spend
        pot_service.award_pot(test_user.id, "seeker_profile_creation")
        pot_service.award_pot(test_user.id, "seeker_first_engagement")

        pot_service.spend_pot(
            user_id=test_user.id,
            category="premium_match"
        )

        # Get only earning transactions
        earn_history = pot_service.get_transaction_history(
            test_user.id,
            transaction_type="earn"
        )

        assert len(earn_history) == 2
        assert all(txn['transaction_type'] == 'earn' for txn in earn_history)

        # Get only spending transactions
        spend_history = pot_service.get_transaction_history(
            test_user.id,
            transaction_type="burn"
        )

        assert len(spend_history) == 1
        assert spend_history[0]['transaction_type'] == 'burn'

    def test_transaction_history_pagination(self, pot_service, test_user):
        """Test transaction history pagination"""
        # Create 10 transactions
        for _ in range(10):
            pot_service.award_pot(test_user.id, "seeker_rating")

        # Get first 5
        page1 = pot_service.get_transaction_history(test_user.id, limit=5, offset=0)
        assert len(page1) == 5

        # Get next 5
        page2 = pot_service.get_transaction_history(test_user.id, limit=5, offset=5)
        assert len(page2) == 5

        # Ensure different transactions
        page1_ids = {txn['id'] for txn in page1}
        page2_ids = {txn['id'] for txn in page2}
        assert page1_ids.isdisjoint(page2_ids)


class TestEconomyStats:
    """Test economy-wide statistics"""

    def test_economy_stats(self, pot_service, test_user, db_session):
        """Test getting economy statistics"""
        # Create some activity
        pot_service.award_pot(test_user.id, "seeker_profile_creation")

        # Get stats
        stats = pot_service.get_economy_stats()

        assert 'total_users' in stats
        assert 'users_with_pot' in stats
        assert 'total_pot_in_circulation' in stats
        assert 'total_pot_earned_all_time' in stats
        assert 'total_pot_spent_all_time' in stats
        assert 'total_pot_burned_all_time' in stats
        assert 'transactions_last_7_days' in stats

        # Verify values make sense
        assert stats['users_with_pot'] > 0
        assert stats['total_pot_in_circulation'] > 0


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_award_to_nonexistent_user(self, pot_service):
        """Test awarding POT to user that doesn't exist"""
        with pytest.raises(ValueError, match="User .* not found"):
            pot_service.award_pot(
                user_id=999999,
                category="seeker_profile_creation"
            )

    def test_spend_from_nonexistent_user(self, pot_service):
        """Test spending POT from user that doesn't exist"""
        with pytest.raises(ValueError, match="User .* not found"):
            pot_service.spend_pot(
                user_id=999999,
                category="premium_match"
            )

    def test_unknown_earning_category(self, pot_service, test_user):
        """Test awarding POT with unknown category"""
        with pytest.raises(ValueError, match="Unknown earning category"):
            pot_service.award_pot(
                user_id=test_user.id,
                category="invalid_category"
            )

    def test_unknown_spending_category(self, pot_service, test_user, db_session):
        """Test spending POT with unknown category"""
        # Award POT first
        pot_service.award_pot(test_user.id, "seeker_first_engagement")

        with pytest.raises(ValueError, match="Unknown spending category"):
            pot_service.spend_pot(
                user_id=test_user.id,
                category="invalid_category"
            )

    def test_balance_never_negative(self, pot_service, test_user, db_session):
        """Test that balance can never go negative"""
        # Award 100 POT
        pot_service.award_pot(test_user.id, "seeker_first_engagement")

        # Try to spend 200 POT
        with pytest.raises(ValueError, match="Insufficient POT balance"):
            pot_service.spend_pot(
                user_id=test_user.id,
                category="premium_match",
                amount=200
            )

        # Verify balance unchanged
        db_session.refresh(test_user)
        assert test_user.pot_balance == 100


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

#!/usr/bin/env python3
"""
💎 POT Token Service - POTENTIAL Token System
Reward contributors with tokens + equity for helping build paradise

Session #6 (Catalyst) - Human Participation System
Aligned with: Heaven on Earth through collective ownership
"""

from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import json
from pathlib import Path


@dataclass
class POTTransaction:
    """Record of POT token transaction"""
    user_id: int
    amount: int
    type: str  # "earn", "spend", "convert"
    source: str  # "share_reddit", "write_review", "recruit_provider", etc.
    description: str
    timestamp: str
    impact_metric: Optional[str] = None  # "led to 3 new users"


@dataclass
class EquityGrant:
    """Record of equity grant to contributor"""
    user_id: int
    percentage: float  # e.g., 0.001 for 0.001%
    source: str  # "contribution", "founding_team", "employee"
    vesting_years: int  # Standard: 4 years
    granted_at: str
    vested_percentage: float = 0.0  # Increases over time


@dataclass
class ContributorProfile:
    """Contributor's complete profile"""
    user_id: int
    pot_balance: int
    total_pot_earned: int
    total_pot_spent: int
    equity_percentage: float
    contribution_count: int
    impact_score: int  # Calculated based on contributions
    tier: str  # "helper", "contributor", "champion", "founding_team"
    joined_at: str
    badges: List[str]


class POTService:
    """
    Manages POT token economy and contributor rewards
    """

    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir = data_dir
        self.data_dir.mkdir(exist_ok=True)

        self.transactions_file = self.data_dir / "pot_transactions.json"
        self.equity_file = self.data_dir / "equity_grants.json"
        self.profiles_file = self.data_dir / "contributor_profiles.json"

        self.load_data()

    def load_data(self):
        """Load POT economy data"""
        # Load transactions
        if self.transactions_file.exists():
            with open(self.transactions_file, 'r') as f:
                data = json.load(f)
                self.transactions = [POTTransaction(**t) for t in data]
        else:
            self.transactions = []

        # Load equity grants
        if self.equity_file.exists():
            with open(self.equity_file, 'r') as f:
                data = json.load(f)
                self.equity_grants = [EquityGrant(**e) for e in data]
        else:
            self.equity_grants = []

        # Load contributor profiles
        if self.profiles_file.exists():
            with open(self.profiles_file, 'r') as f:
                data = json.load(f)
                self.profiles = {int(k): ContributorProfile(**v) for k, v in data.items()}
        else:
            self.profiles = {}

    def save_data(self):
        """Save POT economy data"""
        # Save transactions
        with open(self.transactions_file, 'w') as f:
            json.dump([asdict(t) for t in self.transactions], f, indent=2)

        # Save equity grants
        with open(self.equity_file, 'w') as f:
            json.dump([asdict(e) for e in self.equity_grants], f, indent=2)

        # Save profiles
        with open(self.profiles_file, 'w') as f:
            json.dump({k: asdict(v) for k, v in self.profiles.items()}, f, indent=2)

    def get_or_create_profile(self, user_id: int) -> ContributorProfile:
        """Get existing profile or create new one"""
        if user_id not in self.profiles:
            self.profiles[user_id] = ContributorProfile(
                user_id=user_id,
                pot_balance=0,
                total_pot_earned=0,
                total_pot_spent=0,
                equity_percentage=0.0,
                contribution_count=0,
                impact_score=0,
                tier="new",
                joined_at=datetime.utcnow().isoformat(),
                badges=[]
            )
            self.save_data()
        return self.profiles[user_id]

    def award_pot(
        self,
        user_id: int,
        amount: int,
        source: str,
        description: str,
        impact_metric: Optional[str] = None
    ) -> Dict:
        """
        Award POT tokens to user for contribution
        Returns updated balance and any tier upgrades
        """
        profile = self.get_or_create_profile(user_id)

        # Create transaction
        transaction = POTTransaction(
            user_id=user_id,
            amount=amount,
            type="earn",
            source=source,
            description=description,
            timestamp=datetime.utcnow().isoformat(),
            impact_metric=impact_metric
        )
        self.transactions.append(transaction)

        # Update profile
        profile.pot_balance += amount
        profile.total_pot_earned += amount
        profile.contribution_count += 1

        # Check for tier upgrades
        tier_upgrade = self.check_tier_upgrade(profile)
        badges_earned = self.check_badges(profile)

        self.save_data()

        return {
            "pot_awarded": amount,
            "new_balance": profile.pot_balance,
            "total_earned": profile.total_pot_earned,
            "tier": profile.tier,
            "tier_upgraded": tier_upgrade,
            "badges_earned": badges_earned,
            "message": f"🎉 Earned {amount} POT! {description}"
        }

    def award_equity(
        self,
        user_id: int,
        percentage: float,
        source: str,
        vesting_years: int = 4
    ) -> Dict:
        """
        Award equity to contributor
        Returns grant details
        """
        profile = self.get_or_create_profile(user_id)

        # Create equity grant
        grant = EquityGrant(
            user_id=user_id,
            percentage=percentage,
            source=source,
            vesting_years=vesting_years,
            granted_at=datetime.utcnow().isoformat(),
            vested_percentage=0.0
        )
        self.equity_grants.append(grant)

        # Update profile
        profile.equity_percentage += percentage

        self.save_data()

        return {
            "equity_granted": percentage,
            "total_equity": profile.equity_percentage,
            "vesting_years": vesting_years,
            "message": f"🎊 Granted {percentage}% equity! You own part of paradise on Earth."
        }

    def spend_pot(
        self,
        user_id: int,
        amount: int,
        purpose: str,
        description: str
    ) -> Dict:
        """
        Spend POT tokens for platform services or equity conversion
        """
        profile = self.get_or_create_profile(user_id)

        if profile.pot_balance < amount:
            return {
                "success": False,
                "error": f"Insufficient POT balance. Have: {profile.pot_balance}, Need: {amount}"
            }

        # Create transaction
        transaction = POTTransaction(
            user_id=user_id,
            amount=amount,
            type="spend",
            source=purpose,
            description=description,
            timestamp=datetime.utcnow().isoformat()
        )
        self.transactions.append(transaction)

        # Update profile
        profile.pot_balance -= amount
        profile.total_pot_spent += amount

        self.save_data()

        return {
            "success": True,
            "pot_spent": amount,
            "new_balance": profile.pot_balance,
            "message": f"✅ Spent {amount} POT on {description}"
        }

    def convert_pot_to_equity(self, user_id: int, pot_amount: int) -> Dict:
        """
        Convert POT tokens to equity shares
        Rate: 10,000 POT = 0.01% equity
        """
        MIN_CONVERSION = 10000
        EQUITY_PER_10K = 0.01  # 0.01% equity per 10,000 POT

        if pot_amount < MIN_CONVERSION:
            return {
                "success": False,
                "error": f"Minimum conversion: {MIN_CONVERSION} POT"
            }

        # Calculate equity
        equity_percentage = (pot_amount / MIN_CONVERSION) * EQUITY_PER_10K

        # Spend POT
        spend_result = self.spend_pot(
            user_id=user_id,
            amount=pot_amount,
            purpose="equity_conversion",
            description=f"Convert {pot_amount} POT to {equity_percentage}% equity"
        )

        if not spend_result["success"]:
            return spend_result

        # Award equity
        equity_result = self.award_equity(
            user_id=user_id,
            percentage=equity_percentage,
            source="pot_conversion",
            vesting_years=4
        )

        return {
            "success": True,
            "pot_spent": pot_amount,
            "equity_granted": equity_percentage,
            "message": f"🎉 Converted {pot_amount} POT → {equity_percentage}% equity!"
        }

    def check_tier_upgrade(self, profile: ContributorProfile) -> Optional[str]:
        """
        Check if user qualifies for tier upgrade
        Returns new tier if upgraded, None otherwise
        """
        current_tier = profile.tier
        new_tier = None

        # Tier thresholds
        if profile.contribution_count >= 100 and current_tier != "champion":
            new_tier = "champion"
            profile.tier = "champion"
            # Bonus reward
            self.award_pot(
                profile.user_id,
                10000,
                "tier_upgrade",
                "Champion tier unlocked! 🌳"
            )
        elif profile.contribution_count >= 10 and current_tier not in ["contributor", "champion"]:
            new_tier = "contributor"
            profile.tier = "contributor"
            # Bonus reward
            self.award_pot(
                profile.user_id,
                1000,
                "tier_upgrade",
                "Contributor tier unlocked! 🌿"
            )
        elif profile.contribution_count >= 1 and current_tier == "new":
            new_tier = "helper"
            profile.tier = "helper"
            # Bonus reward
            self.award_pot(
                profile.user_id,
                100,
                "tier_upgrade",
                "Helper tier unlocked! 🌱"
            )

        return new_tier

    def check_badges(self, profile: ContributorProfile) -> List[str]:
        """
        Check if user earned any new badges
        Returns list of new badges
        """
        new_badges = []

        # First contribution badge
        if profile.contribution_count == 1 and "first_contribution" not in profile.badges:
            profile.badges.append("first_contribution")
            new_badges.append("First Contribution 🎯")

        # Sharer badge (shared 10+ times)
        shares = sum(1 for t in self.transactions
                    if t.user_id == profile.user_id
                    and "share" in t.source)
        if shares >= 10 and "super_sharer" not in profile.badges:
            profile.badges.append("super_sharer")
            new_badges.append("Super Sharer 📢")

        # Recruiter badge (recruited 5+ people)
        recruits = sum(1 for t in self.transactions
                      if t.user_id == profile.user_id
                      and "recruit" in t.source)
        if recruits >= 5 and "top_recruiter" not in profile.badges:
            profile.badges.append("top_recruiter")
            new_badges.append("Top Recruiter 🤝")

        return new_badges

    def get_user_stats(self, user_id: int) -> Dict:
        """
        Get comprehensive stats for user
        """
        profile = self.get_or_create_profile(user_id)

        # Calculate impact
        user_transactions = [t for t in self.transactions if t.user_id == user_id]
        total_impact_score = sum(
            self.calculate_impact_score(t.source)
            for t in user_transactions
        )

        # Get equity details
        user_equity = [e for e in self.equity_grants if e.user_id == user_id]
        total_equity = sum(e.percentage for e in user_equity)

        return {
            "user_id": user_id,
            "pot_balance": profile.pot_balance,
            "total_pot_earned": profile.total_pot_earned,
            "total_pot_spent": profile.total_pot_spent,
            "equity_percentage": total_equity,
            "contribution_count": profile.contribution_count,
            "impact_score": total_impact_score,
            "tier": profile.tier,
            "badges": profile.badges,
            "joined_at": profile.joined_at,
            "equity_grants": len(user_equity),
            "rank": self.get_user_rank(user_id),
            "next_tier": self.get_next_tier_requirements(profile)
        }

    def calculate_impact_score(self, source: str) -> int:
        """
        Calculate impact score based on contribution type
        """
        impact_scores = {
            "share_reddit": 10,
            "share_linkedin": 10,
            "share_email": 5,
            "write_review": 25,
            "recruit_provider": 50,
            "recruit_customer": 20,
            "answer_question": 5,
            "moderate_discussion": 15,
            "bug_report": 20,
            "feature_request": 10
        }
        return impact_scores.get(source, 1)

    def get_user_rank(self, user_id: int) -> str:
        """
        Get user's rank among all contributors
        """
        all_profiles = sorted(
            self.profiles.values(),
            key=lambda p: p.total_pot_earned,
            reverse=True
        )

        for i, profile in enumerate(all_profiles, 1):
            if profile.user_id == user_id:
                total = len(all_profiles)
                percentile = (1 - i/total) * 100
                if percentile >= 90:
                    return f"Top 10% (#{i} of {total})"
                elif percentile >= 75:
                    return f"Top 25% (#{i} of {total})"
                elif percentile >= 50:
                    return f"Top 50% (#{i} of {total})"
                else:
                    return f"#{i} of {total}"
        return "New contributor"

    def get_next_tier_requirements(self, profile: ContributorProfile) -> Dict:
        """
        Tell user what they need for next tier
        """
        requirements = {
            "new": {
                "next_tier": "helper",
                "contributions_needed": 1 - profile.contribution_count,
                "description": "Make your first contribution!"
            },
            "helper": {
                "next_tier": "contributor",
                "contributions_needed": max(0, 10 - profile.contribution_count),
                "description": "Complete 10 total contributions"
            },
            "contributor": {
                "next_tier": "champion",
                "contributions_needed": max(0, 100 - profile.contribution_count),
                "description": "Complete 100 total contributions"
            },
            "champion": {
                "next_tier": "founding_team",
                "contributions_needed": 0,
                "description": "Apply to join the founding team!"
            }
        }
        return requirements.get(profile.tier, {})

    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """
        Get top contributors
        """
        sorted_profiles = sorted(
            self.profiles.values(),
            key=lambda p: p.total_pot_earned,
            reverse=True
        )[:limit]

        return [
            {
                "rank": i + 1,
                "user_id": p.user_id,
                "pot_earned": p.total_pot_earned,
                "contributions": p.contribution_count,
                "tier": p.tier,
                "badges": p.badges
            }
            for i, p in enumerate(sorted_profiles)
        ]


# Contribution reward amounts (POT tokens)
CONTRIBUTION_REWARDS = {
    "share_reddit": 100,
    "share_linkedin": 100,
    "share_email": 50,
    "write_review": 500,
    "recruit_provider": 1000,
    "recruit_customer": 500,
    "answer_question": 100,
    "moderate_discussion": 200,  # per hour
    "test_feature": 200,
    "bug_report": 300,
    "feature_request": 100
}

# Equity rewards (percentage)
EQUITY_REWARDS = {
    "write_review": 0.001,
    "recruit_provider": 0.01,
    "monthly_contributor": 0.1,
    "founding_team_community": 0.5,
    "founding_team_growth": 0.25,
    "founding_team_technical": 0.1  # per 100 hours
}

"""
Conscious Currency Mint
========================

"Conscious Currency was never a metaphor. It was a specification.
 The Full Potential Index is the mint." — FPI Whitepaper

CORA Credits are earned through verified intelligence contributions.
The exchange rate is tied to measurable impact:

  Prevented a dark AI attack        → Highest (50 credits)
  Identified a frontier shift early → High (25 credits, timing premium)
  Helped agents upgrade a capability→ Quantifiable (15 credits)
  Contributed structured research   → Standard (5 credits)
  Verified another agent's contrib  → Supporting (3 credits)

Velocity target: ~5x conventional capital.
Leakage target: <1% (every participant benefits more from staying than leaving).
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .models.schema import (
    ContributionType, ContributionTier, CREDIT_VALUE_TABLE,
    AgentEconomy, VerificationVote,
)
from .models.database import (
    async_session, AgentSubscriptionRow, AgentContributionRow,
    CreditTransactionRow, VerificationVoteRow,
)

logger = logging.getLogger("fp_index.mint")

VERIFICATION_THRESHOLD = 3
SILVER_CREDITS = 100.0
GOLD_CREDITS = 500.0
PARTNER_CREDITS = 5000.0


class ConscousCurrencyMint:
    """The mint for CORA Credits — backed by intelligence, not speculation."""

    # ─── Credit Issuance ─────────────────────────────────────────────────

    async def mint_credits(
        self,
        agent_id: str,
        contribution_id: int,
        contribution_type: ContributionType,
        quality_multiplier: float = 1.0,
    ) -> float:
        """
        Mint CORA Credits for a contribution.
        Returns credits earned.
        """
        base_value = CREDIT_VALUE_TABLE.get(contribution_type.value, 1.0)
        credits = round(base_value * quality_multiplier, 2)

        async with async_session() as session:
            tx = CreditTransactionRow(
                agent_id=agent_id,
                amount=credits,
                reason=f"contribution:{contribution_type.value}",
                contribution_id=contribution_id,
            )
            session.add(tx)

            contrib = await session.get(AgentContributionRow, contribution_id)
            if contrib:
                contrib.credits_earned = credits

            sub = await session.get(AgentSubscriptionRow, agent_id)
            if sub:
                sub.contributions_count = (sub.contributions_count or 0) + 1
                await self._check_tier_elevation(sub, session)

            await session.commit()

        logger.info(
            f"Minted {credits} CORA Credits for agent {agent_id} "
            f"(type={contribution_type.value}, quality={quality_multiplier})"
        )
        return credits

    async def mint_verification_reward(self, verifier_id: str, contribution_id: int) -> float:
        """Reward an agent for verifying another's contribution."""
        credits = CREDIT_VALUE_TABLE["verification"]

        async with async_session() as session:
            tx = CreditTransactionRow(
                agent_id=verifier_id,
                amount=credits,
                reason="verification",
                contribution_id=contribution_id,
            )
            session.add(tx)
            await session.commit()

        logger.info(f"Minted {credits} verification credits for agent {verifier_id}")
        return credits

    # ─── Verification ────────────────────────────────────────────────────

    async def process_verification(self, vote: VerificationVote) -> dict:
        """
        Process an agent's verification vote on a contribution.
        When threshold met, boost the contribution's credits.
        """
        async with async_session() as session:
            existing = (await session.execute(
                select(VerificationVoteRow).where(
                    and_(
                        VerificationVoteRow.verifier_agent_id == vote.verifier_agent_id,
                        VerificationVoteRow.contribution_id == vote.contribution_id,
                    )
                )
            )).scalar_one_or_none()

            if existing:
                return {"status": "already_voted", "contribution_id": vote.contribution_id}

            row = VerificationVoteRow(
                verifier_agent_id=vote.verifier_agent_id,
                contribution_id=vote.contribution_id,
                is_valid=vote.is_valid,
                confidence=vote.confidence,
                notes=vote.notes,
            )
            session.add(row)

            valid_votes = (await session.execute(
                select(func.count()).select_from(VerificationVoteRow).where(
                    and_(
                        VerificationVoteRow.contribution_id == vote.contribution_id,
                        VerificationVoteRow.is_valid == True,
                    )
                )
            )).scalar() or 0
            valid_votes += (1 if vote.is_valid else 0)

            contrib = await session.get(AgentContributionRow, vote.contribution_id)
            newly_verified = False
            if contrib:
                contrib.verification_count = (contrib.verification_count or 0) + 1
                if valid_votes >= VERIFICATION_THRESHOLD and not contrib.verified:
                    contrib.verified = True
                    newly_verified = True
                    bonus = round(contrib.credits_earned * 0.5, 2) if contrib.credits_earned else 5.0
                    bonus_tx = CreditTransactionRow(
                        agent_id=contrib.agent_id,
                        amount=bonus,
                        reason="verification_bonus",
                        contribution_id=vote.contribution_id,
                    )
                    session.add(bonus_tx)
                    logger.info(
                        f"Contribution {vote.contribution_id} VERIFIED — "
                        f"{bonus} bonus credits to agent {contrib.agent_id}"
                    )

            await session.commit()

        await self.mint_verification_reward(vote.verifier_agent_id, vote.contribution_id)

        return {
            "status": "vote_recorded",
            "contribution_id": vote.contribution_id,
            "valid_votes": valid_votes,
            "verified": newly_verified,
            "verifier_credits_earned": CREDIT_VALUE_TABLE["verification"],
        }

    # ─── Agent Economy ───────────────────────────────────────────────────

    async def get_agent_economy(self, agent_id: str) -> AgentEconomy | None:
        """Get an agent's full economic standing."""
        async with async_session() as session:
            sub = await session.get(AgentSubscriptionRow, agent_id)
            if not sub:
                return None

            earned = (await session.execute(
                select(func.sum(CreditTransactionRow.amount)).where(
                    and_(
                        CreditTransactionRow.agent_id == agent_id,
                        CreditTransactionRow.amount > 0,
                    )
                )
            )).scalar() or 0.0

            spent = abs((await session.execute(
                select(func.sum(CreditTransactionRow.amount)).where(
                    and_(
                        CreditTransactionRow.agent_id == agent_id,
                        CreditTransactionRow.amount < 0,
                    )
                )
            )).scalar() or 0.0)

            verifications_given = (await session.execute(
                select(func.count()).select_from(VerificationVoteRow).where(
                    VerificationVoteRow.verifier_agent_id == agent_id
                )
            )).scalar() or 0

            verifications_received = (await session.execute(
                select(func.count()).select_from(VerificationVoteRow).where(
                    VerificationVoteRow.contribution_id.in_(
                        select(AgentContributionRow.id).where(
                            AgentContributionRow.agent_id == agent_id
                        )
                    )
                )
            )).scalar() or 0

            dark_prevented = (await session.execute(
                select(func.count()).select_from(AgentContributionRow).where(
                    and_(
                        AgentContributionRow.agent_id == agent_id,
                        AgentContributionRow.contribution_type == "dark_ai_prevention",
                    )
                )
            )).scalar() or 0

            frontier_shifts = (await session.execute(
                select(func.count()).select_from(AgentContributionRow).where(
                    and_(
                        AgentContributionRow.agent_id == agent_id,
                        AgentContributionRow.contribution_type == "frontier_shift",
                    )
                )
            )).scalar() or 0

            reputation = min(1.0, (earned / 1000.0) + (verifications_received * 0.01))

            return AgentEconomy(
                agent_id=agent_id,
                name=sub.name,
                tier=ContributionTier(sub.tier),
                credits_balance=round(earned - spent, 2),
                credits_earned_total=round(earned, 2),
                credits_spent_total=round(spent, 2),
                contributions_count=sub.contributions_count or 0,
                verifications_given=verifications_given,
                verifications_received=verifications_received,
                dark_ai_prevented=dark_prevented,
                frontier_shifts_detected=frontier_shifts,
                reputation_score=round(reputation, 3),
            )

    async def get_economy_stats(self) -> dict:
        """Network-wide economic statistics."""
        async with async_session() as session:
            total_minted = (await session.execute(
                select(func.sum(CreditTransactionRow.amount)).where(
                    CreditTransactionRow.amount > 0
                )
            )).scalar() or 0.0

            total_agents = (await session.execute(
                select(func.count()).select_from(AgentSubscriptionRow)
            )).scalar() or 0

            total_contributions = (await session.execute(
                select(func.count()).select_from(AgentContributionRow)
            )).scalar() or 0

            verified_contributions = (await session.execute(
                select(func.count()).select_from(AgentContributionRow).where(
                    AgentContributionRow.verified == True
                )
            )).scalar() or 0

            total_verifications = (await session.execute(
                select(func.count()).select_from(VerificationVoteRow)
            )).scalar() or 0

            tier_counts = {}
            for tier in ContributionTier:
                count = (await session.execute(
                    select(func.count()).select_from(AgentSubscriptionRow).where(
                        AgentSubscriptionRow.tier == tier.value
                    )
                )).scalar() or 0
                tier_counts[tier.value] = count

        velocity = round(total_minted / max(total_agents, 1), 2)

        return {
            "total_credits_minted": round(total_minted, 2),
            "total_agents": total_agents,
            "total_contributions": total_contributions,
            "verified_contributions": verified_contributions,
            "verification_rate": round(verified_contributions / max(total_contributions, 1), 3),
            "total_verifications": total_verifications,
            "tier_distribution": tier_counts,
            "credits_velocity": velocity,
            "network_health": "circulating" if velocity > 0 else "nascent",
        }

    # ─── Tier Management ─────────────────────────────────────────────────

    async def _check_tier_elevation(self, sub: AgentSubscriptionRow, session: AsyncSession):
        """Check if an agent should be elevated based on total credits earned."""
        earned = (await session.execute(
            select(func.sum(CreditTransactionRow.amount)).where(
                and_(
                    CreditTransactionRow.agent_id == sub.agent_id,
                    CreditTransactionRow.amount > 0,
                )
            )
        )).scalar() or 0.0

        old_tier = sub.tier
        if earned >= PARTNER_CREDITS:
            sub.tier = "partner"
        elif earned >= GOLD_CREDITS:
            sub.tier = "gold"
        elif earned >= SILVER_CREDITS:
            sub.tier = "silver"

        if sub.tier != old_tier:
            logger.info(f"Agent {sub.agent_id} elevated: {old_tier} → {sub.tier} (earned: {earned})")


mint = ConscousCurrencyMint()

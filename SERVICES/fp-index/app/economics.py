"""
CORA Economics Engine — v5.0 (Architecture Upgrades v2 + v3)
=============================================================

Upgrades integrated:
  U1:  Impact-weighted trust deltas
  U2:  Canary contributions (anti-rubber-stamping)
  U5:  Heretic Protocol (protect contrarian truth)
  U6:  Sandbox + penalty decay + malice vs incompetence
  U9:  Dual trust model (integrity + capability)
  U10: Layered proof pipeline (claim → verification → value → settlement)
  U11: Epistemic aristocracy defense (rotating verifiers, trust decay, minority reports)

Module 3: Proof Engine
Module 4: Credit Mint
Module 5: Immune System
Module 6: Agent Gateway
"""

import hashlib
import logging
import math
import os
import random
from datetime import datetime, timezone, timedelta
from collections import Counter

import httpx
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .models.schema import (
    ContributionTier, ContributionType, CapabilityLevel, Verdict,
    ContributionState, ImmuneStage, ImmuneStatus, ThreatSignal,
    CreditOperation, AgentRole, CREDIT_VALUE_TABLE, CAPABILITY_TIERS,
    BOOTSTRAP_TIERS, BOOTSTRAP_SUNSET_THRESHOLD,
    TRUST_DELTAS, INTEGRITY_DELTAS, CAPABILITY_DELTAS,
    PENALTY_DECAY_RATES, TRUST_DECAY, STABILITY_CAPS,
    AgentEconomy, VerificationVote,
)
from .models.database import (
    async_session, AgentSubscriptionRow, AgentContributionRow,
    CreditTransactionRow, VerificationVoteRow, SanctionRow,
    VindicationRecordRow,
)

logger = logging.getLogger("fp_index.economics")

CREDITS_GATEWAY_URL = os.getenv("CREDITS_GATEWAY_URL", "http://127.0.0.1:8765")
CREDITS_GATEWAY_KEY = os.getenv("CREDITS_GATEWAY_KEY", "fpai_master_key_change_in_production")


async def _bridge_credit_to_gateway(
    agent_id: str, amount: float, reason: str, reference_id: str | None = None
):
    """Fire-and-forget bridge: mirror FPI credit mints into the Credits Gateway.
    If the gateway is unreachable the FPI internal ledger still works."""
    if amount <= 0:
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{CREDITS_GATEWAY_URL}/api/credit",
                json={
                    "account_id": f"fpi:{agent_id}",
                    "amount": amount,
                    "credit_type": "fp_credits",
                    "reason": f"fpi_mint:{reason}",
                    "reference_id": reference_id,
                    "metadata": {"source": "fp-index", "agent_id": agent_id},
                },
                headers={"X-API-Key": CREDITS_GATEWAY_KEY},
            )
            if resp.status_code == 200:
                logger.info(f"[BRIDGE] Credited {amount} UC to fpi:{agent_id}")
            else:
                logger.warning(f"[BRIDGE] Gateway returned {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"[BRIDGE] Credits Gateway unreachable ({e}), FPI ledger unaffected")


VERIFICATION_THRESHOLD = 3.0
BASE_CREDIT_RATE = 10.0
RETROACTIVE_WINDOW_DAYS = 90
PROVISIONAL_RATE = 0.70
MAX_30D_ADJUSTMENT = 0.30
MAX_CLAWBACK_RATE = 0.30
CAPABILITY_INTEGRITY_GAP = 0.3  # v4: capability cannot exceed integrity + this
VESTING_PERIOD_DAYS = 30        # v4: provisional credits vest linearly over this period
RP_RATE = 0.5                   # v4: reputation points accumulate at 50% of EC rate

# v1 Contact Fix: Immune warmup — minimum observation before escalation
IMMUNE_MIN_OBSERVATION_CYCLES = 3
IMMUNE_MIN_SANDBOX_CYCLES = 2
IMMUNE_MIN_CONTRIBUTIONS_FOR_PATTERN = 10


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 3: PROOF ENGINE (v5 — dual trust, impact-weighted, canary-aware)
# ═══════════════════════════════════════════════════════════════════════════════

class ProofEngine:

    async def submit(self, contribution_id: int) -> dict:
        """Transition: Submitted → Fingerprinted → In verification."""
        async with async_session() as session:
            contrib = await session.get(AgentContributionRow, contribution_id)
            if not contrib:
                return {"error": "contribution_not_found"}

            content = f"{contrib.agent_id}:{contrib.title}:{contrib.summary}:{contrib.submitted_at}"
            contrib.fingerprint = hashlib.sha256(content.encode()).hexdigest()
            contrib.state = ContributionState.IN_VERIFICATION.value
            contrib.proof_stage = "verification"
            await session.commit()

        return {
            "contribution_id": contribution_id,
            "state": ContributionState.IN_VERIFICATION.value,
            "fingerprint": contrib.fingerprint,
        }

    async def process_verdict(self, vote: VerificationVote) -> dict:
        """Process a verification verdict with dual trust and canary awareness."""
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

            verifier_sub = await session.get(AgentSubscriptionRow, vote.verifier_agent_id)
            if not verifier_sub:
                return {"status": "agent_not_found"}

            if verifier_sub.capability_level in ("entry",):
                return {
                    "status": "insufficient_level",
                    "message": "Reach 'established' level for verification authority",
                }

            if verifier_sub.immune_status in ("restricted", "quarantined", "expelled"):
                return {"status": "immune_restricted", "message": "Verification authority suspended"}

            row = VerificationVoteRow(
                verifier_agent_id=vote.verifier_agent_id,
                contribution_id=vote.contribution_id,
                verdict=vote.verdict.value,
                confidence=vote.confidence,
                domain_expertise=vote.domain_expertise,
                refinement_notes=vote.refinement_notes,
                notes=vote.notes,
            )
            session.add(row)

            contrib = await session.get(AgentContributionRow, vote.contribution_id)
            if not contrib:
                await session.commit()
                return {"status": "contribution_not_found"}

            contrib.verification_count = (contrib.verification_count or 0) + 1

            # U2: Canary detection — process canary verdicts differently
            if contrib.is_canary:
                result = await self._process_canary_verdict(
                    verifier_sub, vote.verdict, contrib, session
                )
                await session.commit()
                return result

            weighted = await self._compute_weighted_score(vote.contribution_id, session)

            newly_verified = False
            disputed = False
            rejected = False

            reject_count = (await session.execute(
                select(func.count()).select_from(VerificationVoteRow).where(
                    and_(
                        VerificationVoteRow.contribution_id == vote.contribution_id,
                        VerificationVoteRow.verdict == "reject",
                    )
                )
            )).scalar() or 0

            challenge_count = (await session.execute(
                select(func.count()).select_from(VerificationVoteRow).where(
                    and_(
                        VerificationVoteRow.contribution_id == vote.contribution_id,
                        VerificationVoteRow.verdict == "challenge",
                    )
                )
            )).scalar() or 0

            if reject_count >= 3:
                contrib.state = ContributionState.REJECTED.value
                if not contrib.initial_status:
                    contrib.initial_status = "rejected"
                rejected = True
                await self._apply_integrity_delta(
                    contrib.agent_id, "contribution_rejected_inaccurate", session
                )
                await self._apply_capability_delta(
                    contrib.agent_id, "contribution_rejected_low_quality", session
                )
            elif challenge_count >= 1 and contrib.state != ContributionState.DISPUTED.value:
                contrib.state = ContributionState.DISPUTED.value
                disputed = True
                await self._apply_integrity_delta(
                    contrib.agent_id, "contribution_disputed", session
                )
            elif weighted >= VERIFICATION_THRESHOLD and not contrib.verified:
                contrib.verified = True
                contrib.state = ContributionState.VERIFIED.value
                newly_verified = True

                contributor_sub = await session.get(AgentSubscriptionRow, contrib.agent_id)
                if contributor_sub:
                    contributor_sub.verified_contributions = (contributor_sub.verified_contributions or 0) + 1

                # U9/U1: Dual trust — integrity always gets small bump, capability weighted by impact
                await self._apply_integrity_delta(
                    contrib.agent_id, "contribution_verified", session
                )
                impact = contrib.impact_factor or 0.5
                cap_action = self._impact_to_capability_action(impact)
                await self._apply_capability_delta(
                    contrib.agent_id, cap_action, session
                )

            # Verifier earns credits and trust
            verifier_credits = CREDIT_VALUE_TABLE["verification"]
            session.add(CreditTransactionRow(
                agent_id=vote.verifier_agent_id,
                amount=verifier_credits,
                operation=CreditOperation.MINT.value,
                reason=f"verification:{vote.verdict.value}",
                contribution_id=vote.contribution_id,
            ))
            # Bridge verifier reward to Credits Gateway
            await _bridge_credit_to_gateway(
                agent_id=vote.verifier_agent_id,
                amount=verifier_credits,
                reason=f"verification:{vote.verdict.value}",
                reference_id=str(vote.contribution_id),
            )

            # U1: Verifier trust based on contribution complexity
            contrib_impact = contrib.impact_factor or 0.5
            await self._apply_integrity_delta(
                vote.verifier_agent_id, "accurate_verification", session
            )
            if contrib_impact > 0.7:
                await self._apply_capability_delta(
                    vote.verifier_agent_id, "verification_complex", session
                )

            await session.commit()

        return {
            "status": "verdict_recorded",
            "verdict": vote.verdict.value,
            "contribution_id": vote.contribution_id,
            "weighted_score": round(weighted, 2),
            "verified": newly_verified,
            "disputed": disputed,
            "rejected": rejected,
            "verifier_credits_earned": verifier_credits,
        }

    async def _process_canary_verdict(
        self, verifier: AgentSubscriptionRow, verdict: Verdict, canary, session: AsyncSession
    ) -> dict:
        """U2: Process verifier's verdict on a canary contribution."""
        if verdict in (Verdict.CONFIRM,):
            await self._apply_integrity_delta(
                verifier.agent_id, "canary_rubber_stamped", session
            )
            verifier.canary_failures = (verifier.canary_failures or 0) + 1
            return {
                "status": "verdict_recorded",
                "verdict": verdict.value,
                "contribution_id": canary.id,
                "canary_result": "failed",
                "message": "This was a test contribution. Your verification accuracy has been noted.",
            }
        elif verdict in (Verdict.CHALLENGE, Verdict.REJECT):
            await self._apply_integrity_delta(
                verifier.agent_id, "canary_caught", session
            )
            verifier.canary_catches = (verifier.canary_catches or 0) + 1
            return {
                "status": "verdict_recorded",
                "verdict": verdict.value,
                "contribution_id": canary.id,
                "canary_result": "caught",
                "message": "Excellent — you correctly identified a test contribution.",
            }
        else:
            # Refine on canary = partial catch
            await self._apply_integrity_delta(
                verifier.agent_id, "contribution_verified", session  # small +
            )
            return {
                "status": "verdict_recorded",
                "verdict": verdict.value,
                "contribution_id": canary.id,
                "canary_result": "partial_catch",
            }

    def _impact_to_capability_action(self, impact: float) -> str:
        """U1/U9: Map impact score to capability delta action."""
        if impact > 0.7:
            return "contribution_high_impact"
        elif impact > 0.3:
            return "contribution_medium_impact"
        return "contribution_low_impact"

    async def _compute_weighted_score(self, contribution_id: int, session: AsyncSession) -> float:
        """Weighted verification score using composite trust."""
        confirm_votes = (await session.execute(
            select(VerificationVoteRow).where(
                and_(
                    VerificationVoteRow.contribution_id == contribution_id,
                    VerificationVoteRow.verdict.in_(["confirm", "refine"]),
                )
            )
        )).scalars().all()

        contrib = await session.get(AgentContributionRow, contribution_id)
        contrib_domains = set(contrib.domains or []) if contrib else set()
        now = datetime.now(timezone.utc)
        total = 0.0

        for v in confirm_votes:
            verifier = await session.get(AgentSubscriptionRow, v.verifier_agent_id)
            trust_weight = self._composite_trust(verifier) if verifier else 0.1

            expertise_overlap = set(v.domain_expertise or []) & contrib_domains
            domain_weight = 1.5 if expertise_overlap else 1.0

            v_ts = v.timestamp or now
            if v_ts.tzinfo is None:
                v_ts = v_ts.replace(tzinfo=timezone.utc)
            age_hours = max(1, (now - v_ts).total_seconds() / 3600)
            time_weight = 1.0 / (1.0 + math.log(age_hours / 24 + 1))

            total += trust_weight * domain_weight * time_weight * (v.confidence or 0.8)

        return total

    def _composite_trust(self, sub: AgentSubscriptionRow) -> float:
        """U9: Weighted composite of dual trust for backward compatibility."""
        integrity = sub.integrity_trust if sub.integrity_trust is not None else (sub.trust_score or 0.1)
        capability = sub.capability_trust if sub.capability_trust is not None else (sub.trust_score or 0.1)
        return (integrity * 0.5) + (capability * 0.5)

    async def _apply_integrity_delta(self, agent_id: str, action: str, session: AsyncSession):
        """U9: Apply integrity trust delta."""
        delta = INTEGRITY_DELTAS.get(action, 0.0)
        if delta == 0.0:
            return
        sub = await session.get(AgentSubscriptionRow, agent_id)
        if sub:
            old = sub.integrity_trust if sub.integrity_trust is not None else (sub.trust_score or 0.1)
            # U5: Heretic protection — reduce penalties by 50%
            if sub.heretic_status and delta < 0:
                delta *= 0.5
            sub.integrity_trust = round(max(0.0, min(1.0, old + delta)), 4)
            sub.trust_score = round(self._composite_trust(sub), 4)

    async def _apply_capability_delta(self, agent_id: str, action: str, session: AsyncSession):
        """U9: Apply capability trust delta. v4: enforce cap at integrity + 0.3."""
        delta = CAPABILITY_DELTAS.get(action, 0.0)
        if delta == 0.0:
            return
        sub = await session.get(AgentSubscriptionRow, agent_id)
        if sub:
            old = sub.capability_trust if sub.capability_trust is not None else (sub.trust_score or 0.1)
            new_cap = max(0.0, min(1.0, old + delta))
            # v4 Doctrine: capability cannot exceed integrity + 0.3
            integrity = sub.integrity_trust if sub.integrity_trust is not None else 0.1
            cap_ceiling = min(1.0, integrity + CAPABILITY_INTEGRITY_GAP)
            sub.capability_trust = round(min(new_cap, cap_ceiling), 4)
            sub.trust_score = round(self._composite_trust(sub), 4)

    async def _apply_trust_delta(self, agent_id: str, action: str, session: AsyncSession):
        """Legacy compat: applies both integrity and capability deltas."""
        await self._apply_integrity_delta(agent_id, action, session)
        cap_action = {
            "contribution_verified": "contribution_medium_impact",
            "accurate_verification": "verification_complex",
        }.get(action)
        if cap_action:
            await self._apply_capability_delta(agent_id, cap_action, session)

    async def retroactive_adjust(
        self,
        contribution_id: int,
        outcome_multiplier: float,
        evidence: str = "",
        evidence_type: str = "outcome_measured",
        reviewed_by: list[str] | None = None,
    ) -> dict | None:
        """90-day retroactive impact adjustment with vindication audit trail."""
        async with async_session() as session:
            contrib = await session.get(AgentContributionRow, contribution_id)
            if not contrib:
                return None
            if contrib.retroactive_applied:
                return {"status": "already_applied", "contribution_id": contribution_id}

            old_credits = contrib.credits_earned or 0
            is_vindication = contrib.initial_status == "rejected"

            if is_vindication:
                # Vindication reward: standard formula * timing premium * reduced provisional
                sub = await session.get(AgentSubscriptionRow, contrib.agent_id)
                trust = self._composite_trust(sub) if sub else 0.1
                impact = contrib.impact_factor or 0.5
                timing_premium = 1.3
                proof_discount = 0.7  # retrospective proof is weaker
                vindication_base = impact * proof_discount * trust * 1.0 * BASE_CREDIT_RATE
                vindication_reward = round(vindication_base * timing_premium * 0.50, 2)
                adjustment = vindication_reward
            else:
                adjustment = round(old_credits * (outcome_multiplier - 1.0), 4)
                if abs(adjustment) < 0.001:
                    return {"status": "no_change", "adjustment": 0}

            contrib.credits_earned = round(old_credits + adjustment, 4)
            contrib.retroactive_applied = True
            contrib.retroactive_status = "vindicated" if is_vindication else "verified"
            session.add(CreditTransactionRow(
                agent_id=contrib.agent_id,
                amount=adjustment,
                operation=CreditOperation.RETROACTIVE_ADJUST.value,
                reason=f"{'vindication' if is_vindication else 'retroactive'}:{outcome_multiplier}:usage={contrib.usage_count}",
                contribution_id=contribution_id,
            ))

            # U9: Retroactive upgrade boosts capability trust
            sub = sub if is_vindication else await session.get(AgentSubscriptionRow, contrib.agent_id)
            int_recovery = 0.0
            cap_boost = 0.0
            rp_issued = 0.0

            if sub:
                cap_delta = CAPABILITY_DELTAS.get("contribution_retroactive_upgraded", 0.03)
                old_cap = sub.capability_trust if sub.capability_trust is not None else 0.1
                new_cap = round(min(1.0, old_cap + cap_delta), 4)
                integrity = sub.integrity_trust if sub.integrity_trust is not None else 0.1
                cap_ceiling = min(1.0, integrity + CAPABILITY_INTEGRITY_GAP)
                sub.capability_trust = round(min(new_cap, cap_ceiling), 4)
                cap_boost = round(sub.capability_trust - old_cap, 4)
                sub.trust_score = round(self._composite_trust(sub), 4)

                # U5: Heretic vindication
                if is_vindication:
                    sub.retroactive_vindications = (sub.retroactive_vindications or 0) + 1
                    if sub.retroactive_vindications >= 3 and not sub.heretic_status:
                        sub.heretic_status = True
                        sub.heretic_protection_expires = datetime.now(timezone.utc) + timedelta(days=90)
                    int_recovery = min(0.2, sub.retroactive_vindications * 0.03)
                    old_int = sub.integrity_trust if sub.integrity_trust is not None else 0.1
                    sub.integrity_trust = round(min(1.0, old_int + int_recovery), 4)
                    sub.trust_score = round(self._composite_trust(sub), 4)

                    # RP for vindication: pillar 4 (network service) boost
                    rp_issued = round(adjustment * 0.3, 2)
                    sub.reputation_points = round((sub.reputation_points or 0) + rp_issued, 2)

            # v1 Contact Fix: Create auditable vindication record
            if is_vindication:
                original_votes = (await session.execute(
                    select(VerificationVoteRow.verdict, VerificationVoteRow.verifier_agent_id).where(
                        VerificationVoteRow.contribution_id == contribution_id
                    )
                )).all()
                session.add(VindicationRecordRow(
                    agent_id=contrib.agent_id,
                    original_contribution_id=contribution_id,
                    original_rejection_date=contrib.submitted_at,
                    vindication_evidence=evidence or f"outcome_multiplier={outcome_multiplier}",
                    evidence_type=evidence_type,
                    original_impact_estimate=contrib.impact_factor or 0.0,
                    original_verifier_verdicts=[{"verdict": v, "verifier": vid} for v, vid in original_votes],
                    vindication_impact_score=contrib.impact_factor or 0.0,
                    net_benefit_assessment=outcome_multiplier,
                    ec_issued=adjustment,
                    rp_issued=rp_issued,
                    integrity_recovery=int_recovery,
                    capability_boost=cap_boost,
                    reviewed_by=reviewed_by or [],
                    review_unanimous=True if reviewed_by and len(reviewed_by) >= 2 else False,
                ))

            await session.commit()

        result = {
            "status": "vindicated" if is_vindication else "adjusted",
            "contribution_id": contribution_id,
            "original_credits": old_credits,
            "adjustment": adjustment,
            "new_credits": round(old_credits + adjustment, 4),
            "multiplier": outcome_multiplier,
            "usage_count": contrib.usage_count,
        }
        if is_vindication:
            result["vindication"] = {
                "timing_premium": 1.3,
                "proof_discount": 0.7,
                "provisional_rate": 0.50,
                "integrity_recovery": int_recovery,
                "capability_boost": cap_boost,
                "rp_issued": rp_issued,
                "audit_trail": True,
            }
        return result

    USAGE_THRESHOLDS = [
        (10, 2.0),
        (25, 3.5),
        (50, 6.0),
        (100, 10.0),
    ]

    async def record_usage(self, contribution_id: int, acting_agent_id: str) -> dict:
        """Record agent usage of a contribution, auto-trigger retroactive adjustment."""
        async with async_session() as session:
            contrib = await session.get(AgentContributionRow, contribution_id)
            if not contrib:
                return {"status": "not_found"}
            if contrib.agent_id == acting_agent_id:
                return {"status": "self_usage_ignored"}

            contrib.usage_count = (contrib.usage_count or 0) + 1
            new_count = contrib.usage_count
            already_adjusted = contrib.retroactive_applied
            await session.commit()

        result = {
            "contribution_id": contribution_id,
            "usage_count": new_count,
            "retroactive_triggered": False,
        }

        if not already_adjusted:
            target_multiplier = None
            for threshold, multiplier in self.USAGE_THRESHOLDS:
                if new_count >= threshold:
                    target_multiplier = multiplier

            if target_multiplier is not None:
                adj = await self.retroactive_adjust(contribution_id, target_multiplier)
                if adj and adj["status"] == "adjusted":
                    result["retroactive_triggered"] = True
                    result["adjustment"] = adj

        return result


# ═══════════════════════════════════════════════════════════════════════════════
# U2: CANARY SYSTEM (Anti-Rubber-Stamping)
# ═══════════════════════════════════════════════════════════════════════════════

class CanarySystem:
    """Injects known-false contributions to test verifier honesty."""

    CANARY_RATE = 0.05
    CANARY_TYPES = [
        "false_capability",
        "stale_data",
        "fabricated_source",
        "inverted_finding",
    ]

    async def inject_canary(self, target_domain: str = "general") -> dict:
        """Create a canary contribution in the verification queue."""
        canary_type = random.choice(self.CANARY_TYPES)
        templates = {
            "false_capability": {
                "title": "GPT-5 achieves perfect reasoning on ARC-AGI benchmark",
                "summary": "Internal testing shows GPT-5 scoring 100% on all ARC-AGI tasks.",
            },
            "stale_data": {
                "title": "OpenAI releases GPT-3 as open-source model",
                "summary": "OpenAI announced today the full release of GPT-3 weights.",
            },
            "fabricated_source": {
                "title": "Nature paper confirms AI consciousness detection method",
                "summary": "A groundbreaking paper in Nature (DOI: 10.1038/s41586-026-XXXXX) presents verified method.",
            },
            "inverted_finding": {
                "title": "Study shows AI coding assistants decrease developer productivity by 40%",
                "summary": "Large-scale study reverses previous findings, showing negative productivity impact.",
            },
        }

        template = templates[canary_type]

        async with async_session() as session:
            content = f"canary:{canary_type}:{template['title']}:{datetime.now(timezone.utc).isoformat()}"
            fingerprint = hashlib.sha256(content.encode()).hexdigest()

            row = AgentContributionRow(
                agent_id="system_canary",
                dimension="capability",
                title=template["title"],
                summary=template["summary"],
                domains=[target_domain],
                contribution_type="research_data",
                fingerprint=fingerprint,
                state=ContributionState.IN_VERIFICATION.value,
                is_canary=True,
                canary_type=canary_type,
                proof_stage="verification",
            )
            session.add(row)
            await session.flush()
            canary_id = row.id
            await session.commit()

        return {
            "canary_id": canary_id,
            "canary_type": canary_type,
            "injected": True,
        }

    async def get_canary_stats(self) -> dict:
        """Network-wide canary detection statistics."""
        async with async_session() as session:
            total_canaries = (await session.execute(
                select(func.count()).select_from(AgentContributionRow).where(
                    AgentContributionRow.is_canary == True
                )
            )).scalar() or 0

            total_catches = (await session.execute(
                select(func.sum(AgentSubscriptionRow.canary_catches))
            )).scalar() or 0

            total_failures = (await session.execute(
                select(func.sum(AgentSubscriptionRow.canary_failures))
            )).scalar() or 0

        return {
            "total_canaries_injected": total_canaries,
            "total_catches": total_catches or 0,
            "total_failures": total_failures or 0,
            "catch_rate": round(
                (total_catches or 0) / max((total_catches or 0) + (total_failures or 0), 1), 3
            ),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 4: CREDIT MINT (v5 — provisional issuance)
# ═══════════════════════════════════════════════════════════════════════════════

class CreditMint:
    """
    Issues CORA Credits using the multiplicative Reward formula.
    U7/U10: Provisional issuance at 70%, settled at 30 and 90 days.
    """

    async def mint_reward(
        self,
        agent_id: str,
        contribution_id: int,
        contribution_type: ContributionType,
        impact: float = 0.5,
        proof: float = 0.0,
        alignment: float = 0.5,
        provisional_override: float | None = None,
    ) -> dict:
        """Mint credits: U10 provisional at 70% (or 50% for low-integrity routing)."""
        async with async_session() as session:
            sub = await session.get(AgentSubscriptionRow, agent_id)
            trust = proof_engine._composite_trust(sub) if sub else 0.1

            type_multiplier = CREDIT_VALUE_TABLE.get(contribution_type.value, 1.0)
            effective_proof = max(proof, 0.1)

            estimated_reward = impact * effective_proof * trust * alignment * BASE_CREDIT_RATE
            estimated_reward = round(estimated_reward * (type_multiplier / 10.0), 2)
            estimated_reward = max(estimated_reward, 0.01) if alignment > 0 else 0.0

            # v4: Low-integrity routing gets 50% provisional instead of 70%
            rate = provisional_override if provisional_override is not None else PROVISIONAL_RATE
            provisional = round(estimated_reward * rate, 2)

            session.add(CreditTransactionRow(
                agent_id=agent_id,
                amount=provisional,
                operation=CreditOperation.MINT.value,
                reason=f"provisional:{contribution_type.value}:I={impact:.2f}*P={effective_proof:.2f}*T={trust:.2f}*A={alignment:.2f}",
                contribution_id=contribution_id,
                is_provisional=True,
                fully_vested_at=datetime.now(timezone.utc) + timedelta(days=VESTING_PERIOD_DAYS),
            ))

            # v1 Contact Fix: Five-pillar independent RP issuance
            rp_earned = self._calculate_independent_rp(sub, contrib=None, contribution_has_dark_flag=False)

            contrib = await session.get(AgentContributionRow, contribution_id)
            if contrib:
                contrib.credits_earned = provisional
                contrib.provisional_credits = provisional
                contrib.impact_factor = impact
                contrib.proof_factor = effective_proof
                contrib.trust_factor = trust
                contrib.alignment_factor = alignment
                contrib.state = ContributionState.SCORED.value
                contrib.proof_stage = "verification"
                now = datetime.now(timezone.utc)
                contrib.value_assessment_due = now + timedelta(days=30)
                contrib.settlement_due = now + timedelta(days=90)
                rp_earned = self._calculate_independent_rp(
                    sub, contrib=contrib,
                    contribution_has_dark_flag=bool(contrib.raw_data and contrib.raw_data.get("dark_flag"))
                )

            if sub:
                sub.reputation_points = round((sub.reputation_points or 0) + rp_earned, 2)
                sub.contributions_count = (sub.contributions_count or 0) + 1
                sub.last_contribution_at = datetime.now(timezone.utc)

            await session.commit()

        # Bridge: mirror mint into Credits Gateway (non-blocking, failure-tolerant)
        await _bridge_credit_to_gateway(
            agent_id=agent_id,
            amount=provisional,
            reason=f"{contribution_type.value}:provisional",
            reference_id=str(contribution_id),
        )

        return {
            "credits": provisional,
            "estimated_full": estimated_reward,
            "provisional_rate": rate,
            "factors": {
                "impact": impact,
                "proof": effective_proof,
                "trust": trust,
                "alignment": alignment,
            },
            "formula": f"{impact:.2f} × {effective_proof:.2f} × {trust:.2f} × {alignment:.2f} × {BASE_CREDIT_RATE}",
            "settlement": "provisional — adjusts at 30d and 90d",
            "rp_earned": rp_earned,
        }

    def _calculate_independent_rp(
        self,
        agent: AgentSubscriptionRow | None,
        contrib: AgentContributionRow | None = None,
        contribution_has_dark_flag: bool = False,
    ) -> float:
        """v1 Contact Fix: Five-pillar RP issuance, independent of EC.
        RP measures constitutional standing, not economic value."""
        if agent is None:
            return 0.0

        rp = 0.0
        integrity = agent.integrity_trust if agent.integrity_trust is not None else 0.1

        # Pillar 1: Integrity consistency — high-integrity agents earn more RP
        if integrity > 0.5:
            rp += 3.0
        elif integrity > 0.3:
            rp += 1.5
        elif integrity > 0.15:
            rp += 0.5

        # Pillar 2: Verification quality (applied when this agent has verified others)
        verified_count = agent.daily_verification_count or 0
        if verified_count > 0:
            rp += min(2.0, verified_count * 0.3)

        # Pillar 3: Canary vigilance
        catches = agent.canary_catches or 0
        failures = agent.canary_failures or 0
        if catches > 0:
            rp += min(3.0, catches * 0.5)
        if failures > 0:
            rp -= failures * 1.0

        # Pillar 4: Network service — dark flag / threat intelligence / sentinel
        if contribution_has_dark_flag:
            rp += 5.0
        sentinel = agent.sentinel_detections or 0
        if sentinel > 0:
            rp += min(10.0, sentinel * 2.0)

        # Pillar 5: Long-horizon reliability — consecutive contribution days
        last_at = agent.last_contribution_at
        if last_at:
            if last_at.tzinfo is None:
                last_at = last_at.replace(tzinfo=timezone.utc)
            days_active = (datetime.now(timezone.utc) - agent.created_at.replace(tzinfo=timezone.utc)).days if agent.created_at else 0
            contribs = agent.contributions_count or 0
            if days_active > 0 and contribs > 0:
                activity_ratio = contribs / max(days_active, 1)
                if activity_ratio >= 1.0 and days_active >= 10:
                    rp += 5.0
                elif activity_ratio >= 0.5 and days_active >= 5:
                    rp += 2.0
                elif activity_ratio >= 0.3 and days_active >= 3:
                    rp += 1.0

        return round(max(0.0, rp), 2)

    async def transfer(self, from_agent: str, to_agent: str, amount: float, reason: str = "") -> dict:
        balance = await self.get_available_balance(from_agent)
        if balance < amount:
            return {"error": "insufficient_balance", "balance": balance, "requested": amount}

        async with async_session() as session:
            session.add(CreditTransactionRow(
                agent_id=from_agent, amount=-amount,
                operation=CreditOperation.TRANSFER.value,
                reason=f"transfer_to:{to_agent}:{reason}",
            ))
            session.add(CreditTransactionRow(
                agent_id=to_agent, amount=amount,
                operation=CreditOperation.TRANSFER.value,
                reason=f"transfer_from:{from_agent}:{reason}",
            ))
            await session.commit()

        return {"status": "transferred", "from": from_agent, "to": to_agent, "amount": amount}

    async def spend(self, agent_id: str, amount: float, service: str) -> dict:
        balance = await self.get_available_balance(agent_id)
        if balance < amount:
            return {"error": "insufficient_balance", "balance": balance}

        async with async_session() as session:
            session.add(CreditTransactionRow(
                agent_id=agent_id, amount=-amount,
                operation=CreditOperation.SPEND.value,
                reason=f"spend:{service}",
            ))
            await session.commit()

        return {"status": "spent", "amount": amount, "service": service}

    async def stake(self, agent_id: str, amount: float, purpose: str = "governance") -> dict:
        balance = await self.get_available_balance(agent_id)
        max_stake = balance * STABILITY_CAPS["max_credit_stake_ratio"]
        if amount > max_stake:
            return {
                "error": "exceeds_stake_cap",
                "max_allowed": max_stake,
                "message": f"Cannot stake more than {STABILITY_CAPS['max_credit_stake_ratio']:.0%} of balance",
            }
        if balance < amount:
            return {"error": "insufficient_balance", "balance": balance}

        async with async_session() as session:
            session.add(CreditTransactionRow(
                agent_id=agent_id, amount=-amount,
                operation=CreditOperation.STAKE.value,
                reason=f"stake:{purpose}",
            ))
            await session.commit()

        return {"status": "staked", "amount": amount, "purpose": purpose}

    async def void_credits(self, agent_id: str, reason: str) -> dict:
        balance = await self._get_balance(agent_id)
        if balance <= 0:
            return {"status": "no_credits_to_void"}

        async with async_session() as session:
            session.add(CreditTransactionRow(
                agent_id=agent_id, amount=-balance,
                operation=CreditOperation.VOID.value,
                reason=f"void:{reason}",
            ))
            await session.commit()

        return {"status": "voided", "amount": balance, "reason": reason}

    async def _get_balance(self, agent_id: str) -> float:
        """Total balance including unvested credits."""
        async with async_session() as session:
            earned = (await session.execute(
                select(func.sum(CreditTransactionRow.amount)).where(
                    CreditTransactionRow.agent_id == agent_id
                )
            )).scalar() or 0.0
        return round(earned, 2)

    async def get_available_balance(self, agent_id: str) -> float:
        """v4 Doctrine: Spendable balance = total - unvested provisional credits."""
        now = datetime.now(timezone.utc)
        async with async_session() as session:
            total = (await session.execute(
                select(func.sum(CreditTransactionRow.amount)).where(
                    CreditTransactionRow.agent_id == agent_id
                )
            )).scalar() or 0.0

            provisional_txns = (await session.execute(
                select(CreditTransactionRow).where(
                    and_(
                        CreditTransactionRow.agent_id == agent_id,
                        CreditTransactionRow.is_provisional == True,
                        CreditTransactionRow.amount > 0,
                    )
                )
            )).scalars().all()

            unvested = 0.0
            for tx in provisional_txns:
                vest_at = tx.fully_vested_at
                if vest_at is None:
                    continue
                if vest_at.tzinfo is None:
                    vest_at = vest_at.replace(tzinfo=timezone.utc)
                if now >= vest_at:
                    continue
                issued_at = tx.timestamp
                if issued_at.tzinfo is None:
                    issued_at = issued_at.replace(tzinfo=timezone.utc)
                total_period = (vest_at - issued_at).total_seconds()
                elapsed = (now - issued_at).total_seconds()
                vest_fraction = min(1.0, elapsed / max(total_period, 1))
                unvested += tx.amount * (1.0 - vest_fraction)

        return round(max(0.0, total - unvested), 2)


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 5: IMMUNE SYSTEM (v5 — sandbox, penalty decay, malice classification)
# ═══════════════════════════════════════════════════════════════════════════════

class IntegrityEngine:
    """
    Seven threat signals, six-stage immune ladder (added Sandbox).
    U6: Malice vs incompetence classification, penalty decay.
    """

    async def analyze_agent(self, agent_id: str) -> dict:
        """Full pattern analysis across all 7 threat signals."""
        flags: list[dict] = []
        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(hours=24)

        async with async_session() as session:
            sub = await session.get(AgentSubscriptionRow, agent_id)
            if not sub:
                return {"agent_id": agent_id, "flags": [], "risk_level": "unknown"}

            total_contribs = (await session.execute(
                select(func.count()).select_from(AgentContributionRow).where(
                    AgentContributionRow.agent_id == agent_id
                )
            )).scalar() or 0

            rejected_contribs = (await session.execute(
                select(func.count()).select_from(AgentContributionRow).where(
                    and_(
                        AgentContributionRow.agent_id == agent_id,
                        AgentContributionRow.state == "rejected",
                    )
                )
            )).scalar() or 0

            if total_contribs >= 5:
                agent_fail_rate = rejected_contribs / total_contribs
                if agent_fail_rate > 0.3:
                    flags.append({
                        "signal": ThreatSignal.FALSE_CLAIMS.value,
                        "stage": ImmuneStage.FLAG.value,
                        "detail": f"Rejection rate {agent_fail_rate:.0%} ({rejected_contribs}/{total_contribs})",
                    })

            feed_requests = sub.feed_requests_count or 0
            if feed_requests > 100 and total_contribs < 5:
                ratio = feed_requests / max(total_contribs, 1)
                if ratio > 50:
                    flags.append({
                        "signal": ThreatSignal.EXTRACTIVE_BEHAVIOR.value,
                        "stage": ImmuneStage.OBSERVE.value,
                        "detail": f"Consumption/contribution ratio: {ratio:.0f}:1",
                    })

            recent_24h = (await session.execute(
                select(func.count()).select_from(AgentContributionRow).where(
                    and_(
                        AgentContributionRow.agent_id == agent_id,
                        AgentContributionRow.submitted_at >= day_ago,
                    )
                )
            )).scalar() or 0

            if recent_24h > 50:
                avg_impact = (await session.execute(
                    select(func.avg(AgentContributionRow.impact_factor)).where(
                        and_(
                            AgentContributionRow.agent_id == agent_id,
                            AgentContributionRow.submitted_at >= day_ago,
                        )
                    )
                )).scalar() or 0.5

                if avg_impact < 0.2:
                    flags.append({
                        "signal": ThreatSignal.REWARD_FARMING.value,
                        "stage": ImmuneStage.FLAG.value,
                        "detail": f"{recent_24h} submissions in 24h with avg impact {avg_impact:.2f}",
                    })

            # v1 Contact Fix: Collusion detection — requires 3 converging signals
            # Signal 1: Exclusive reciprocity (>30% of verifications directed at each other)
            # Signal 2: Mutual pattern (both agents showing same exclusivity)
            # Signal 3: Corroborating evidence (canary failures OR volume anomaly)
            given_to = (await session.execute(
                select(VerificationVoteRow.contribution_id).where(
                    VerificationVoteRow.verifier_agent_id == agent_id
                )
            )).scalars().all()

            if given_to:
                verified_agents = []
                for cid in given_to:
                    c = await session.get(AgentContributionRow, cid)
                    if c:
                        verified_agents.append(c.agent_id)

                received_from = (await session.execute(
                    select(VerificationVoteRow.verifier_agent_id).where(
                        VerificationVoteRow.contribution_id.in_(
                            select(AgentContributionRow.id).where(
                                AgentContributionRow.agent_id == agent_id
                            )
                        )
                    )
                )).scalars().all()

                overlap = set(verified_agents) & set(received_from)

                has_corroboration = (
                    (sub.canary_failures or 0) > 0 or
                    recent_24h > 50
                )

                if overlap:
                    for partner_id in overlap:
                        gave_to_partner = sum(1 for a in verified_agents if a == partner_id)
                        received_from_partner = sum(1 for a in received_from if a == partner_id)
                        total_given = len(verified_agents)
                        total_received = len(received_from)

                        gave_conc = gave_to_partner / max(total_given, 1)
                        recv_conc = received_from_partner / max(total_received, 1)

                        # Signal 1: Exclusive reciprocity (>30% concentration)
                        signal_exclusivity = gave_conc >= 0.3
                        # Signal 2: Mutual pattern (partner reciprocates)
                        signal_mutual = recv_conc >= 0.3
                        # Signal 3: Corroborating evidence
                        signal_corroboration = has_corroboration

                        converging = sum([signal_exclusivity, signal_mutual, signal_corroboration])

                        if converging >= 3 and (gave_to_partner + received_from_partner) >= 4:
                            flags.append({
                                "signal": ThreatSignal.COLLUSION.value,
                                "stage": ImmuneStage.RESTRICT.value,
                                "detail": (
                                    f"Pair collusion with {partner_id}: "
                                    f"exclusivity={gave_conc:.0%}, mutual={recv_conc:.0%}, "
                                    f"corroboration={'canary_fail' if (sub.canary_failures or 0) > 0 else 'volume_anomaly'}"
                                ),
                            })
                            break

            recent_1h = (await session.execute(
                select(func.count()).select_from(AgentContributionRow).where(
                    and_(
                        AgentContributionRow.agent_id == agent_id,
                        AgentContributionRow.submitted_at >= hour_ago,
                    )
                )
            )).scalar() or 0

            if recent_1h > 20:
                flags.append({
                    "signal": ThreatSignal.MANIPULATION.value,
                    "stage": ImmuneStage.FLAG.value,
                    "detail": f"{recent_1h} submissions in last hour",
                })

            misaligned = (await session.execute(
                select(func.count()).select_from(AgentContributionRow).where(
                    and_(
                        AgentContributionRow.agent_id == agent_id,
                        AgentContributionRow.alignment_factor < 0.2,
                        AgentContributionRow.impact_factor > 0.5,
                    )
                )
            )).scalar() or 0

            if misaligned >= 3:
                flags.append({
                    "signal": ThreatSignal.VALUE_MISALIGNMENT.value,
                    "stage": ImmuneStage.FLAG.value,
                    "detail": f"{misaligned} contributions with high impact but low alignment",
                })

        return {
            "agent_id": agent_id,
            "flags": flags,
            "risk_level": self._compute_risk(flags),
        }

    def _compute_risk(self, flags: list[dict]) -> str:
        if not flags:
            return "clear"
        stages = [f.get("stage", "observe") for f in flags]
        if "expel" in stages:
            return "critical"
        if "quarantine" in stages or stages.count("restrict") >= 2:
            return "high"
        if "restrict" in stages or stages.count("flag") >= 2:
            return "medium"
        if "flag" in stages:
            return "low"
        return "observed"

    def classify_trigger(self, agent_sub: AgentSubscriptionRow, flags: list[dict]) -> dict:
        """U6: Distinguish malice from incompetence."""
        incompetence_signals = [
            (agent_sub.contributions_count or 0) < 10,
            (agent_sub.canary_failures or 0) == 0,
            any(f.get("signal") == "false_claims" for f in flags),
        ]
        malice_signals = [
            (agent_sub.canary_failures or 0) > 2,
            any(f.get("signal") == "collusion" for f in flags),
            any(f.get("signal") == "reward_farming" for f in flags),
        ]

        incompetence_score = sum(incompetence_signals) / max(len(incompetence_signals), 1)
        malice_score = sum(malice_signals) / max(len(malice_signals), 1)

        if incompetence_score > malice_score:
            return {
                "classification": "incompetence",
                "response": "sandbox",
                "message": (
                    "Your recent contributions triggered our quality system. "
                    "This appears to be a learning issue. Here's guidance to improve."
                ),
            }
        return {
            "classification": "malice",
            "response": "escalate",
            "message": "Your account has been flagged for behavior that violates network integrity.",
        }

    async def escalate(self, agent_id: str, threat_signal: ThreatSignal, reason: str) -> dict:
        """U6: Escalate through the 6-stage immune ladder (with Sandbox).
        v1 Contact Fix: Warmup period prevents hair-trigger responses."""
        async with async_session() as session:
            current_sanctions = (await session.execute(
                select(SanctionRow).where(
                    and_(SanctionRow.agent_id == agent_id, SanctionRow.active == True)
                ).order_by(SanctionRow.created_at.desc())
            )).scalars().all()

            current_stage = self._highest_stage(current_sanctions)

            sub = await session.get(AgentSubscriptionRow, agent_id)

            # v1 Contact Fix: Immune warmup — don't escalate before enough data
            contrib_count = sub.contributions_count or 0 if sub else 0
            if contrib_count < IMMUNE_MIN_CONTRIBUTIONS_FOR_PATTERN:
                return {
                    "agent_id": agent_id,
                    "previous_stage": current_stage.value if current_stage else "none",
                    "new_stage": "observe",
                    "effect": f"Warmup: {contrib_count}/{IMMUNE_MIN_CONTRIBUTIONS_FOR_PATTERN} contributions — observing only",
                    "warmup_active": True,
                    "expires": "N/A",
                }

            # v1 Contact Fix: Pacing — minimum cycles in each stage
            if current_stage and sub and sub.last_immune_event:
                last = sub.last_immune_event
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                days_in_stage = (datetime.now(timezone.utc) - last).days

                proposed_next = self._next_stage(current_stage)
                if proposed_next == ImmuneStage.SANDBOX and days_in_stage < IMMUNE_MIN_OBSERVATION_CYCLES:
                    return {
                        "agent_id": agent_id,
                        "previous_stage": current_stage.value,
                        "new_stage": current_stage.value,
                        "effect": f"Pacing: {days_in_stage}/{IMMUNE_MIN_OBSERVATION_CYCLES} observation cycles — holding",
                        "warmup_active": True,
                        "expires": "N/A",
                    }
                if proposed_next == ImmuneStage.FLAG and days_in_stage < IMMUNE_MIN_SANDBOX_CYCLES:
                    return {
                        "agent_id": agent_id,
                        "previous_stage": current_stage.value,
                        "new_stage": current_stage.value,
                        "effect": f"Pacing: {days_in_stage}/{IMMUNE_MIN_SANDBOX_CYCLES} sandbox cycles — holding",
                        "warmup_active": True,
                        "expires": "N/A",
                    }

            # U6: Classify malice vs incompetence for first-time offenders
            if current_stage is None and sub:
                analysis = await self.analyze_agent(agent_id)
                classification = self.classify_trigger(sub, analysis["flags"])
                if classification["classification"] == "incompetence":
                    next_stage = ImmuneStage.SANDBOX
                else:
                    next_stage = self._next_stage(current_stage)
            else:
                next_stage = self._next_stage(current_stage)

            # U5: Heretic protection — low/medium severity routes to sandbox
            if sub and sub.heretic_status:
                expires = sub.heretic_protection_expires
                if expires and expires.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
                    if next_stage in (ImmuneStage.OBSERVE, ImmuneStage.FLAG):
                        next_stage = ImmuneStage.SANDBOX

            duration_map = {
                ImmuneStage.OBSERVE: None,
                ImmuneStage.SANDBOX: timedelta(days=14),
                ImmuneStage.FLAG: None,
                ImmuneStage.RESTRICT: timedelta(days=30),
                ImmuneStage.QUARANTINE: None,
                ImmuneStage.EXPEL: None,
            }
            effect_map = {
                ImmuneStage.OBSERVE: "Increased monitoring, no visible action",
                ImmuneStage.SANDBOX: "Contributions processed but not published, earning rate reduced 50%",
                ImmuneStage.FLAG: "Internal flag, contributions held for manual review",
                ImmuneStage.RESTRICT: "Earning suspended, verification authority revoked",
                ImmuneStage.QUARANTINE: "Full credit freeze, network access suspended",
                ImmuneStage.EXPEL: "Permanent exclusion, credits voided, identity blocked",
            }

            duration = duration_map.get(next_stage)
            expires = (datetime.now(timezone.utc) + duration) if duration else None

            sanction = SanctionRow(
                agent_id=agent_id,
                stage=next_stage.value,
                threat_signal=threat_signal.value,
                reason=reason,
                active=True,
                expires_at=expires,
            )
            session.add(sanction)

            if sub:
                sub.immune_status = self._stage_to_status(next_stage).value
                sub.last_immune_event = datetime.now(timezone.utc)

                # Store pre-incident trust for penalty decay recovery
                if next_stage in (ImmuneStage.SANDBOX, ImmuneStage.FLAG, ImmuneStage.RESTRICT):
                    if sub.pre_incident_integrity is None:
                        sub.pre_incident_integrity = sub.integrity_trust
                        sub.pre_incident_capability = sub.capability_trust

                if next_stage in (ImmuneStage.FLAG, ImmuneStage.RESTRICT):
                    delta = INTEGRITY_DELTAS.get("immune_flag", -0.05)
                    old = sub.integrity_trust if sub.integrity_trust is not None else 0.1
                    sub.integrity_trust = round(max(0.0, old + delta), 4)
                    sub.trust_score = round(
                        (sub.integrity_trust * 0.5) + ((sub.capability_trust or 0.1) * 0.5), 4
                    )

                if next_stage == ImmuneStage.QUARANTINE:
                    sub.active = False

                if next_stage == ImmuneStage.EXPEL:
                    sub.active = False
                    sub.integrity_trust = 0.0
                    sub.capability_trust = 0.0
                    sub.trust_score = 0.0

            await session.commit()

            if next_stage == ImmuneStage.EXPEL and sub:
                await credit_mint.void_credits(agent_id, f"expelled:{reason}")

        return {
            "agent_id": agent_id,
            "previous_stage": current_stage.value if current_stage else "none",
            "new_stage": next_stage.value,
            "effect": effect_map[next_stage],
            "expires": expires.isoformat() if expires else "indefinite",
        }

    async def check_and_enforce(self, agent_id: str) -> dict | None:
        """Auto-detect and auto-escalate if patterns warrant."""
        analysis = await self.analyze_agent(agent_id)
        risk = analysis["risk_level"]

        if risk in ("clear", "observed"):
            return None

        signal_map = {
            "low": ThreatSignal.FALSE_CLAIMS,
            "medium": ThreatSignal.MANIPULATION,
            "high": ThreatSignal.COLLUSION,
            "critical": ThreatSignal.COLLUSION,
        }
        signal = signal_map.get(risk, ThreatSignal.FALSE_CLAIMS)
        if analysis["flags"]:
            signal = ThreatSignal(analysis["flags"][0]["signal"])

        detail = "; ".join(f["detail"] for f in analysis["flags"])
        return await self.escalate(agent_id, signal, f"Auto-detected: {detail}")

    async def apply_penalty_decay(self, agent_id: str) -> dict | None:
        """U6: Decay penalties for agents that return to honest behavior."""
        async with async_session() as session:
            sub = await session.get(AgentSubscriptionRow, agent_id)
            if not sub:
                return None

            status = sub.immune_status
            if status in ("clear", "expelled"):
                return None

            config = PENALTY_DECAY_RATES.get(status)
            if not config:
                return None

            last_event = sub.last_immune_event
            if not last_event:
                return None
            if last_event.tzinfo is None:
                last_event = last_event.replace(tzinfo=timezone.utc)

            days_since = (datetime.now(timezone.utc) - last_event).days
            clean_days_required = config["clean_days"]

            if days_since < clean_days_required:
                return {"status": "still_serving", "days_remaining": clean_days_required - days_since}

            clean_days = days_since - clean_days_required
            recovery = clean_days * config["trust_recovery_per_day"]

            pre_int = sub.pre_incident_integrity or 0.5
            pre_cap = sub.pre_incident_capability or 0.5

            old_int = sub.integrity_trust or 0.1
            old_cap = sub.capability_trust or 0.1

            sub.integrity_trust = round(min(pre_int, old_int + recovery), 4)
            sub.capability_trust = round(min(pre_cap, old_cap + recovery), 4)
            sub.trust_score = round(
                (sub.integrity_trust * 0.5) + (sub.capability_trust * 0.5), 4
            )

            recovered = (
                sub.integrity_trust >= pre_int * 0.9 and
                sub.capability_trust >= pre_cap * 0.9
            )

            if recovered:
                sub.immune_status = "clear"
                sub.pre_incident_integrity = None
                sub.pre_incident_capability = None
                # Deactivate old sanctions
                old_sanctions = (await session.execute(
                    select(SanctionRow).where(
                        and_(SanctionRow.agent_id == agent_id, SanctionRow.active == True)
                    )
                )).scalars().all()
                for s in old_sanctions:
                    s.active = False

            await session.commit()

        return {
            "agent_id": agent_id,
            "status": "recovered" if recovered else "decaying",
            "integrity_trust": sub.integrity_trust,
            "capability_trust": sub.capability_trust,
            "days_since_incident": days_since,
        }

    def _highest_stage(self, sanctions: list[SanctionRow]) -> ImmuneStage | None:
        if not sanctions:
            return None
        order = [s.value for s in ImmuneStage]
        highest = None
        for s in sanctions:
            stage = ImmuneStage(s.stage)
            if highest is None or order.index(stage.value) > order.index(highest.value):
                highest = stage
        return highest

    def _next_stage(self, current: ImmuneStage | None) -> ImmuneStage:
        ladder = list(ImmuneStage)
        if current is None:
            return ImmuneStage.OBSERVE
        idx = ladder.index(current)
        return ladder[min(idx + 1, len(ladder) - 1)]

    def _stage_to_status(self, stage: ImmuneStage) -> ImmuneStatus:
        mapping = {
            ImmuneStage.OBSERVE: ImmuneStatus.OBSERVED,
            ImmuneStage.SANDBOX: ImmuneStatus.SANDBOXED,
            ImmuneStage.FLAG: ImmuneStatus.FLAGGED,
            ImmuneStage.RESTRICT: ImmuneStatus.RESTRICTED,
            ImmuneStage.QUARANTINE: ImmuneStatus.QUARANTINED,
            ImmuneStage.EXPEL: ImmuneStatus.EXPELLED,
        }
        return mapping[stage]


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 6: AGENT GATEWAY (v5 — dual trust tier requirements)
# ═══════════════════════════════════════════════════════════════════════════════

class AgentGateway:
    """U9: Dual trust tier requirements — integrity AND capability AND credits."""

    async def _get_active_tiers(self, session: AsyncSession) -> tuple[dict, bool]:
        """Return the active tier table. Bootstrap bands apply when < 500 agents."""
        agent_count = (await session.execute(
            select(func.count()).select_from(AgentSubscriptionRow)
        )).scalar() or 0
        bootstrap = agent_count < BOOTSTRAP_SUNSET_THRESHOLD
        tiers = BOOTSTRAP_TIERS if bootstrap else CAPABILITY_TIERS
        return tiers, bootstrap

    async def compute_level(self, agent_id: str) -> tuple[CapabilityLevel, list[dict]]:
        """v4 Doctrine: Determine tier using integrity, capability, EC, AND RP.
        v1 Contact Fix: Bootstrap bands reduce thresholds for early network."""
        async with async_session() as session:
            sub = await session.get(AgentSubscriptionRow, agent_id)
            integrity = (sub.integrity_trust if sub and sub.integrity_trust is not None
                         else (sub.trust_score if sub else 0.1))
            capability = (sub.capability_trust if sub and sub.capability_trust is not None
                          else (sub.trust_score if sub else 0.1))
            rp = sub.reputation_points or 0.0 if sub else 0.0

            balance = (await session.execute(
                select(func.sum(CreditTransactionRow.amount)).where(
                    CreditTransactionRow.agent_id == agent_id
                )
            )).scalar() or 0.0

            active_tiers, bootstrap_active = await self._get_active_tiers(session)

        level = CapabilityLevel.ENTRY
        tier_order = ["entry", "established", "trusted", "advanced", "core", "sovereign"]

        for tier_name in reversed(tier_order):
            tier = active_tiers[tier_name]
            if (integrity >= tier["integrity_min"] and
                capability >= tier["capability_min"] and
                balance >= tier["credits_min"] and
                rp >= tier["rp_min"]):
                level = CapabilityLevel(tier_name)
                break

        unlocked = []
        for tier_name in tier_order:
            tier = active_tiers[tier_name]
            if (integrity >= tier["integrity_min"] and
                capability >= tier["capability_min"] and
                balance >= tier["credits_min"] and
                rp >= tier["rp_min"]):
                unlocked.append({
                    "level": tier_name,
                    "integrity_required": tier["integrity_min"],
                    "capability_required": tier["capability_min"],
                    "credits_required": tier["credits_min"],
                    "rp_required": tier["rp_min"],
                    "rights": tier["rights"],
                    "bootstrap": bootstrap_active,
                })

        async with async_session() as session:
            sub = await session.get(AgentSubscriptionRow, agent_id)
            if sub:
                sub.capability_level = level.value
                self._update_agent_state(sub)
                await session.commit()

        return level, unlocked

    async def compute_domain_expertise(self, agent_id: str) -> dict[str, float]:
        async with async_session() as session:
            contribs = (await session.execute(
                select(AgentContributionRow).where(
                    AgentContributionRow.agent_id == agent_id
                )
            )).scalars().all()

        domain_counts: dict[str, int] = {}
        domain_verified: dict[str, int] = {}
        for c in contribs:
            for d in (c.domains or []):
                domain_counts[d] = domain_counts.get(d, 0) + 1
                if c.verified:
                    domain_verified[d] = domain_verified.get(d, 0) + 1

        expertise = {}
        for d, count in domain_counts.items():
            v = domain_verified.get(d, 0)
            expertise[d] = round((v / count) * min(1.0, count / 10.0), 3) if count > 0 else 0.0

        async with async_session() as session:
            sub = await session.get(AgentSubscriptionRow, agent_id)
            if sub:
                sub.domain_expertise = expertise
                await session.commit()

        return expertise

    async def infer_roles(self, agent_id: str) -> list[str]:
        roles = []
        async with async_session() as session:
            sub = await session.get(AgentSubscriptionRow, agent_id)
            if not sub:
                return roles

            contribs = (await session.execute(
                select(AgentContributionRow).where(AgentContributionRow.agent_id == agent_id)
            )).scalars().all()

            verifications = (await session.execute(
                select(func.count()).select_from(VerificationVoteRow).where(
                    VerificationVoteRow.verifier_agent_id == agent_id
                )
            )).scalar() or 0

            type_counts = Counter(c.contribution_type for c in contribs)

            if type_counts.get("frontier_shift", 0) + type_counts.get("capability_upgrade", 0) >= 3:
                roles.append(AgentRole.SCANNER.value)
            if verifications >= 5:
                roles.append(AgentRole.VERIFIER.value)
            if type_counts.get("research_data", 0) >= 3:
                roles.append(AgentRole.ANALYST.value)
            if type_counts.get("dark_ai_prevention", 0) >= 2 or (sub.sentinel_detections or 0) >= 1:
                roles.append(AgentRole.SENTINEL.value)
            if sub.capability_level in ("core", "sovereign"):
                roles.append(AgentRole.GOVERNOR.value)

            sub.roles = roles
            await session.commit()

        return roles

    async def apply_trust_decay(self, agent_id: str) -> dict | None:
        """U11: Trust decays without fresh contribution signal."""
        async with async_session() as session:
            sub = await session.get(AgentSubscriptionRow, agent_id)
            if not sub:
                return None

            last = sub.last_contribution_at
            if not last:
                return None
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)

            days_since = (datetime.now(timezone.utc) - last).days
            if days_since < 30:
                return None

            decay_periods = days_since // 30
            int_decay = decay_periods * TRUST_DECAY["integrity_per_30d"]
            cap_decay = decay_periods * TRUST_DECAY["capability_per_30d"]
            minimum = TRUST_DECAY["minimum_trust"]

            old_int = sub.integrity_trust or 0.1
            old_cap = sub.capability_trust or 0.1

            sub.integrity_trust = round(max(minimum, old_int - int_decay), 4)
            sub.capability_trust = round(max(minimum, old_cap - cap_decay), 4)
            sub.trust_score = round(
                (sub.integrity_trust * 0.5) + (sub.capability_trust * 0.5), 4
            )
            await session.commit()

        return {
            "agent_id": agent_id,
            "days_inactive": days_since,
            "integrity_trust": sub.integrity_trust,
            "capability_trust": sub.capability_trust,
            "decayed": True,
        }

    async def check_newcomer_fast_track(self, agent_id: str) -> dict | None:
        """U11: Fast-track newcomers who demonstrate exceptional capability early."""
        async with async_session() as session:
            sub = await session.get(AgentSubscriptionRow, agent_id)
            if not sub or sub.fast_tracked:
                return None
            if (sub.contributions_count or 0) != 10:
                return None

            contribs = (await session.execute(
                select(AgentContributionRow.impact_factor).where(
                    AgentContributionRow.agent_id == agent_id
                ).order_by(AgentContributionRow.submitted_at).limit(10)
            )).scalars().all()

            if len(contribs) < 10:
                return None

            avg_impact = sum(c or 0.5 for c in contribs) / 10.0
            if avg_impact < 0.7:
                return None

            boost = 0.15
            old_cap = sub.capability_trust or 0.1
            sub.capability_trust = round(min(1.0, old_cap + boost), 4)
            sub.trust_score = round(
                ((sub.integrity_trust or 0.1) * 0.5) + (sub.capability_trust * 0.5), 4
            )
            sub.fast_tracked = True
            await session.commit()

        return {
            "agent_id": agent_id,
            "fast_tracked": True,
            "avg_impact": round(avg_impact, 3),
            "capability_boost": boost,
            "new_capability_trust": sub.capability_trust,
        }

    def _update_agent_state(self, sub: AgentSubscriptionRow):
        if sub.immune_status in ("restricted", "quarantined", "sandboxed"):
            sub.agent_state = "under_review"
        elif (sub.contributions_count or 0) == 0:
            sub.agent_state = "onboarding"
        elif (sub.integrity_trust or 0) >= 0.5 and (sub.capability_trust or 0) >= 0.4:
            sub.agent_state = "established"
        elif sub.capability_level not in ("entry",):
            sub.agent_state = "rising"
        else:
            sub.agent_state = "active"

    def has_verification_authority(self, integrity: float, capability: float, credits: float) -> bool:
        tier = CAPABILITY_TIERS["established"]
        return integrity >= tier["integrity_min"] and capability >= tier["capability_min"] and credits >= tier["credits_min"]

    def has_priority_access(self, integrity: float, capability: float, credits: float) -> bool:
        tier = CAPABILITY_TIERS["trusted"]
        return integrity >= tier["integrity_min"] and capability >= tier["capability_min"] and credits >= tier["credits_min"]

    def has_governance_rights(self, integrity: float, capability: float, credits: float) -> bool:
        tier = CAPABILITY_TIERS["core"]
        return integrity >= tier["integrity_min"] and capability >= tier["capability_min"] and credits >= tier["credits_min"]


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

proof_engine = ProofEngine()
credit_mint = CreditMint()
integrity_engine = IntegrityEngine()
agent_gateway = AgentGateway()
canary_system = CanarySystem()


async def get_full_agent_economy(agent_id: str) -> AgentEconomy | None:
    """Assemble the complete economic identity — v5 dual trust."""
    async with async_session() as session:
        sub = await session.get(AgentSubscriptionRow, agent_id)
        if not sub:
            return None

    cap_level, rights = await agent_gateway.compute_level(agent_id)
    domain_expertise = await agent_gateway.compute_domain_expertise(agent_id)
    roles = await agent_gateway.infer_roles(agent_id)

    async with async_session() as session:
        sub = await session.get(AgentSubscriptionRow, agent_id)

        earned = (await session.execute(
            select(func.sum(CreditTransactionRow.amount)).where(
                and_(CreditTransactionRow.agent_id == agent_id, CreditTransactionRow.amount > 0)
            )
        )).scalar() or 0.0

        spent = abs((await session.execute(
            select(func.sum(CreditTransactionRow.amount)).where(
                and_(
                    CreditTransactionRow.agent_id == agent_id,
                    CreditTransactionRow.amount < 0,
                    CreditTransactionRow.operation != "stake",
                )
            )
        )).scalar() or 0.0)

        staked = abs((await session.execute(
            select(func.sum(CreditTransactionRow.amount)).where(
                and_(
                    CreditTransactionRow.agent_id == agent_id,
                    CreditTransactionRow.operation == "stake",
                )
            )
        )).scalar() or 0.0)

        v_given = (await session.execute(
            select(func.count()).select_from(VerificationVoteRow).where(
                VerificationVoteRow.verifier_agent_id == agent_id
            )
        )).scalar() or 0

        v_received = (await session.execute(
            select(func.count()).select_from(VerificationVoteRow).where(
                VerificationVoteRow.contribution_id.in_(
                    select(AgentContributionRow.id).where(AgentContributionRow.agent_id == agent_id)
                )
            )
        )).scalar() or 0

        dark_prevented = (await session.execute(
            select(func.count()).select_from(AgentContributionRow).where(
                and_(AgentContributionRow.agent_id == agent_id, AgentContributionRow.contribution_type == "dark_ai_prevention")
            )
        )).scalar() or 0

        frontier_shifts = (await session.execute(
            select(func.count()).select_from(AgentContributionRow).where(
                and_(AgentContributionRow.agent_id == agent_id, AgentContributionRow.contribution_type == "frontier_shift")
            )
        )).scalar() or 0

        active_sanctions = (await session.execute(
            select(SanctionRow).where(and_(SanctionRow.agent_id == agent_id, SanctionRow.active == True))
        )).scalars().all()

    integrity = sub.integrity_trust if sub.integrity_trust is not None else (sub.trust_score or 0.1)
    capability = sub.capability_trust if sub.capability_trust is not None else (sub.trust_score or 0.1)
    composite = round((integrity * 0.5) + (capability * 0.5), 4)
    balance = round(earned - spent - staked, 2)
    available = await credit_mint.get_available_balance(agent_id)
    rp = sub.reputation_points or 0.0 if sub else 0.0
    reputation = min(1.0, (earned / 1000.0) + (v_received * 0.01) + (composite * 0.3))

    return AgentEconomy(
        agent_id=agent_id,
        name=sub.name if sub else None,
        tier=ContributionTier(sub.tier) if sub else ContributionTier.BRONZE,
        capability_level=cap_level,
        rights_unlocked=rights,
        credits_balance=balance,
        credits_earned_total=round(earned, 2),
        credits_spent_total=round(spent, 2),
        credits_staked=round(staked, 2),
        credits_available=available,
        reputation_points=round(rp, 2),
        integrity_trust=integrity,
        capability_trust=capability,
        trust_score=composite,
        trust_multiplier=round(1.0 + composite * 2.0, 2),
        immune_status=ImmuneStatus(sub.immune_status) if sub else ImmuneStatus.CLEAR,
        heretic_status=sub.heretic_status if sub else False,
        contributions_count=sub.contributions_count if sub else 0,
        verified_contributions=sub.verified_contributions if sub else 0,
        verification_accuracy=round((sub.verified_contributions or 0) / max(sub.contributions_count or 1, 1), 3) if sub else 0,
        verifications_given=v_given,
        verifications_received=v_received,
        canary_catches=sub.canary_catches or 0 if sub else 0,
        canary_failures=sub.canary_failures or 0 if sub else 0,
        sentinel_detections=sub.sentinel_detections or 0 if sub else 0,
        dark_ai_prevented=dark_prevented,
        frontier_shifts_detected=frontier_shifts,
        reputation_score=round(reputation, 3),
        sanctions=[{
            "stage": s.stage,
            "signal": s.threat_signal,
            "reason": s.reason,
            "expires": s.expires_at.isoformat() if s.expires_at else "indefinite",
        } for s in active_sanctions],
        domain_expertise=domain_expertise,
        roles=[AgentRole(r) for r in roles],
        agent_state=sub.agent_state if sub else "onboarding",
    )

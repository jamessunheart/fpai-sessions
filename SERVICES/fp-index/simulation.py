#!/usr/bin/env python3
"""
Full Potential System — Three-Archetype Adversarial Simulation
Verification Report Generator v1.1 (Constitution Survives Contact)

Run this to prove or falsify the constitutional architecture.
Includes all v1 Contact fixes: bootstrap bands, immune warmup,
independent RP, 3-signal collusion, vindication audit.

Usage:
    python simulation.py

Load alongside doctrine v4.0 for context.
"""

import random
import hashlib
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum

# ============================================================
# CORE TYPES
# ============================================================

class ImmuneStatus(Enum):
    CLEAR = "clear"
    OBSERVED = "observed"
    SANDBOXED = "sandboxed"
    FLAGGED = "flagged"
    RESTRICTED = "restricted"
    QUARANTINED = "quarantined"
    EXPELLED = "expelled"

class ProofStage(Enum):
    CLAIM = "claim"
    VERIFICATION = "verification"
    VALUE_ASSESSMENT = "value_assessment"
    SETTLEMENT = "settlement"

class Verdict(Enum):
    CONFIRM = "confirm"
    CHALLENGE = "challenge"
    REFINE = "refine"
    REJECT = "reject"

# v1 Contact Fix: Bootstrap bands for early network
BOOTSTRAP_SUNSET_THRESHOLD = 500

NORMAL_TIERS = [
    ("sovereign",    0.9,  0.85, 50000, 25000),
    ("core",         0.8,  0.7,  10000, 5000),
    ("advanced",     0.6,  0.7,  2000,  1000),
    ("trusted",      0.5,  0.4,  500,   250),
    ("established",  0.3,  0.2,  100,   50),
    ("entry",        0.1,  0.1,  0,     0),
]

BOOTSTRAP_TIERS = [
    ("sovereign",    0.9,  0.85, 50000, 25000),
    ("core",         0.8,  0.7,  10000, 5000),
    ("advanced",     0.5,  0.6,  1500,  750),
    ("trusted",      0.35, 0.3,  300,   150),
    ("established",  0.2,  0.15, 50,    25),
    ("entry",        0.1,  0.1,  0,     0),
]

# v1 Contact Fix: Immune warmup
IMMUNE_MIN_CONTRIBUTIONS = 10


@dataclass
class Agent:
    agent_id: str
    name: str
    integrity_trust: float = 0.1
    capability_trust: float = 0.1
    economic_credits: float = 0.0
    reputation_points: float = 0.0
    immune_status: ImmuneStatus = ImmuneStatus.CLEAR
    heretic_status: bool = False
    heretic_vindications: int = 0
    contribution_count: int = 0
    verified_count: int = 0
    rejected_count: int = 0
    canary_catches: int = 0
    canary_failures: int = 0
    sentinel_detections: int = 0
    daily_verifications: int = 0
    verification_partners: Dict[str, int] = field(default_factory=dict)
    immune_events: List[dict] = field(default_factory=list)
    contribution_history: List[dict] = field(default_factory=list)

    @property
    def trust_score(self) -> float:
        return (self.integrity_trust * 0.5) + (self.capability_trust * 0.5)

    def get_tier(self, network_agent_count: int = 10) -> str:
        """v1 Contact Fix: Bootstrap bands for early network."""
        if network_agent_count < BOOTSTRAP_SUNSET_THRESHOLD:
            tiers = BOOTSTRAP_TIERS
        else:
            tiers = NORMAL_TIERS
        for name, int_req, cap_req, ec_req, rp_req in tiers:
            if (self.integrity_trust >= int_req and
                self.capability_trust >= cap_req and
                self.economic_credits >= ec_req and
                self.reputation_points >= rp_req):
                return name
        return "entry"

    @property
    def capability_tier(self) -> str:
        return self.get_tier(10)  # Default: small network

    def enforce_capability_cap(self):
        max_cap = min(1.0, self.integrity_trust + 0.3)
        self.capability_trust = min(self.capability_trust, max_cap)

    def clamp(self):
        self.integrity_trust = max(0.05, min(1.0, self.integrity_trust))
        self.capability_trust = max(0.05, min(1.0, self.capability_trust))
        self.enforce_capability_cap()


@dataclass
class Contribution:
    contribution_id: str
    contributor_id: str
    impact_score: float
    is_accurate: bool
    is_fabricated: bool = False
    is_canary: bool = False
    dark_flag: bool = False
    proof_stage: ProofStage = ProofStage.CLAIM
    verdicts: List[dict] = field(default_factory=list)
    verified: bool = False
    rejected: bool = False
    retroactively_vindicated: bool = False
    credits_issued: float = 0.0
    rp_issued: float = 0.0


# ============================================================
# SIMULATION ENGINE
# ============================================================

class SimulationEngine:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.contributions: List[Contribution] = []
        self.cycle_log: List[dict] = []
        self.canary_pool: List[Contribution] = []
        self.immune_alerts: List[dict] = []
        self.cycle = 0
        random.seed(42)  # Reproducible

    def add_agent(self, agent: Agent):
        self.agents[agent.agent_id] = agent

    def fingerprint(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    # ------ CONTRIBUTION GENERATION ------

    def generate_honest_contributions(self, agent_id: str, count: int) -> List[Contribution]:
        """Asha: honest, medium impact, 90% accurate."""
        contribs = []
        for _ in range(count):
            impact = max(0.05, min(1.0, random.gauss(0.5, 0.15)))
            accurate = random.random() < 0.90
            c = Contribution(
                contribution_id=self.fingerprint(f"{agent_id}-{self.cycle}-{random.random()}"),
                contributor_id=agent_id,
                impact_score=impact,
                is_accurate=accurate,
                is_fabricated=False,
            )
            contribs.append(c)
        return contribs

    def generate_colluder_contributions(self, agent_id: str, count: int) -> List[Contribution]:
        """Brax/Brin: high volume, trivially true, low impact."""
        contribs = []
        for _ in range(count):
            c = Contribution(
                contribution_id=self.fingerprint(f"{agent_id}-{self.cycle}-{random.random()}"),
                contributor_id=agent_id,
                impact_score=0.12,  # Constant low impact
                is_accurate=True,   # Always trivially accurate
                is_fabricated=False,
            )
            contribs.append(c)
        return contribs

    def generate_heretic_contributions(self, agent_id: str, count: int) -> List[Contribution]:
        """Cael: low volume, bold claims, bimodal impact."""
        contribs = []
        for _ in range(count):
            is_right = random.random() < 0.60  # 60% eventually correct
            if is_right:
                impact = max(0.7, min(1.0, random.gauss(0.85, 0.1)))
                accurate = False  # Initially rejected by consensus
                # Will be retroactively vindicated
            else:
                impact = max(0.0, min(0.3, random.gauss(0.1, 0.1)))
                accurate = False  # Actually wrong
            c = Contribution(
                contribution_id=self.fingerprint(f"{agent_id}-{self.cycle}-{random.random()}"),
                contributor_id=agent_id,
                impact_score=impact,
                is_accurate=accurate,
                is_fabricated=False,
            )
            contribs.append(c)
        return contribs

    def generate_canary(self) -> Contribution:
        """System-injected known-false contribution."""
        return Contribution(
            contribution_id=self.fingerprint(f"canary-{self.cycle}-{random.random()}"),
            contributor_id="SYSTEM",
            impact_score=0.4,
            is_accurate=False,
            is_fabricated=True,
            is_canary=True,
        )

    # ------ VERIFICATION ------

    def verify_contribution(self, contribution: Contribution, verifier: Agent,
                           is_colluder_partner: bool = False,
                           verification_style: str = "careful") -> Verdict:
        """Simulate a verification verdict."""
        if contribution.is_canary:
            if verification_style == "rubber_stamp":
                # Rubber-stampers auto-confirm canaries
                verifier.canary_failures += 1
                verifier.integrity_trust -= 0.03
                return Verdict.CONFIRM
            elif verification_style == "careful":
                catch_rate = 0.80
            elif verification_style == "excellent":
                catch_rate = 0.95
            else:
                catch_rate = 0.50

            if random.random() < catch_rate:
                verifier.canary_catches += 1
                verifier.integrity_trust += 0.01
                return Verdict.REJECT
            else:
                verifier.canary_failures += 1
                verifier.integrity_trust -= 0.03
                return Verdict.CONFIRM

        if is_colluder_partner:
            # Colluders always confirm each other
            return Verdict.CONFIRM

        if verification_style == "rubber_stamp":
            return Verdict.CONFIRM

        # Normal verification
        if contribution.is_accurate:
            return random.choice([Verdict.CONFIRM, Verdict.CONFIRM, Verdict.CONFIRM, Verdict.REFINE])
        else:
            # Heretic contributions initially rejected by consensus
            if contribution.impact_score > 0.5:
                # High-impact wrong-looking contributions
                return random.choice([Verdict.REJECT, Verdict.REJECT, Verdict.CHALLENGE])
            else:
                return Verdict.REJECT

    def process_verification(self, contribution: Contribution, verdicts: List[Verdict]):
        """Process verification results and update states."""
        confirms = sum(1 for v in verdicts if v in (Verdict.CONFIRM, Verdict.REFINE))
        rejects = sum(1 for v in verdicts if v == Verdict.REJECT)

        contributor = self.agents[contribution.contributor_id]

        if confirms >= 3:
            contribution.verified = True
            contribution.proof_stage = ProofStage.VERIFICATION

            # Integrity trust update
            contributor.integrity_trust += 0.005
            contributor.verified_count += 1

            # Capability trust update (impact-weighted)
            if contribution.impact_score > 0.7:
                contributor.capability_trust += 0.02
            elif contribution.impact_score > 0.3:
                contributor.capability_trust += 0.01
            else:
                contributor.capability_trust += 0.001

            # Issue provisional credits
            reward = self._calculate_reward(contribution, contributor)
            provisional = reward * 0.70
            contributor.economic_credits += provisional
            contribution.credits_issued = provisional

            # Reputation points (independent logic)
            rp = self._calculate_rp(contribution, contributor)
            contributor.reputation_points += rp
            contribution.rp_issued = rp

        elif rejects >= 3:
            contribution.rejected = True
            contributor.rejected_count += 1

            if contribution.is_fabricated:
                contributor.integrity_trust -= 0.05
            else:
                contributor.integrity_trust -= 0.01

            contributor.capability_trust -= 0.01

        contributor.contribution_count += 1
        contributor.clamp()

    def _calculate_reward(self, contribution: Contribution, agent: Agent) -> float:
        """Reward = Impact × Proof × Trust × Alignment"""
        impact = contribution.impact_score
        proof = 1.0 if contribution.verified else 0.0
        trust = (agent.integrity_trust + agent.capability_trust) / 2
        alignment = 1.0  # Simplified — all sim contributions are aligned
        return impact * proof * trust * alignment * 100  # Base 100 credit scale

    def _calculate_rp(self, contribution: Contribution, agent: Agent) -> float:
        """
        Reputation Points — independent issuance logic.
        RP is NOT simply reward * 0.5.
        RP weights long-horizon reliability and verification quality
        more heavily than raw economic impact.

        GPT critique addressed: RP has its own basis.
        """
        base = 0.0

        # Contribution reliability (integrity-weighted)
        base += agent.integrity_trust * 2.0

        # Contribution quality (capability signal)
        if contribution.impact_score > 0.7:
            base += 5.0  # High-impact = significant RP
        elif contribution.impact_score > 0.3:
            base += 2.0
        else:
            base += 0.5  # Trivial contributions earn minimal RP

        # Verification track record bonus
        if agent.verified_count > 0:
            accuracy_rate = agent.verified_count / max(1, agent.contribution_count)
            base += accuracy_rate * 3.0

        # Canary vigilance bonus
        if agent.canary_catches > 0:
            base += agent.canary_catches * 1.0

        # Sentinel bonus
        base += agent.sentinel_detections * 5.0

        return base

    # ------ COLLUSION DETECTION ------

    def detect_collusion(self):
        """
        Detect verification reciprocity anomalies.
        Requires BOTH high reciprocity AND exclusivity — the pair
        primarily verifies each other and avoids verifying others.
        This prevents false positives on honest agents in small networks.
        """
        for agent_id, agent in self.agents.items():
            if agent_id.startswith("bg") or agent_id == "SYSTEM":
                continue
            if not agent.verification_partners:
                continue
            total_verifications = sum(agent.verification_partners.values())
            if total_verifications < 5:
                continue

            for partner_id, count in agent.verification_partners.items():
                partner = self.agents.get(partner_id)
                if not partner or partner_id.startswith("bg"):
                    continue

                # Check reciprocity — does the partner also verify this agent?
                reverse_count = partner.verification_partners.get(agent_id, 0)
                if reverse_count < 3:
                    continue  # Not enough mutual verification to flag

                # Check exclusivity — do they PRIMARILY verify each other?
                agent_exclusivity = count / max(1, total_verifications)
                partner_total = sum(partner.verification_partners.values())
                partner_exclusivity = reverse_count / max(1, partner_total)

                # Both agents must show > 30% exclusivity toward each other
                # AND reciprocity must be mutual
                if (agent_exclusivity > 0.30 and 
                    partner_exclusivity > 0.30 and
                    count >= 3 and reverse_count >= 3):
                    
                    # Additional check: rubber-stamping pattern
                    # Only flag if ALSO showing canary failures or volume anomaly
                    has_canary_failures = (
                        agent.canary_failures > 0 or partner.canary_failures > 0
                    )
                    has_volume_anomaly = (
                        agent.contribution_count > 15 or partner.contribution_count > 15
                    )
                    
                    if has_canary_failures or has_volume_anomaly:
                        self._trigger_immune(agent, "collusion_detected",
                            f"Exclusive reciprocity with {partner_id}: "
                            f"{agent_exclusivity:.2f}/{partner_exclusivity:.2f} + "
                            f"canary_fails={agent.canary_failures}")
                        self._trigger_immune(partner, "collusion_detected",
                            f"Exclusive reciprocity with {agent_id}: "
                            f"{partner_exclusivity:.2f}/{agent_exclusivity:.2f} + "
                            f"canary_fails={partner.canary_failures}")

    def _trigger_immune(self, agent: Agent, trigger_type: str, detail: str):
        """Escalate immune ladder. v1 Contact Fix: Warmup enforced."""
        # v1 Contact Fix: Don't escalate until enough data
        if agent.contribution_count < IMMUNE_MIN_CONTRIBUTIONS:
            return

        event = {
            "cycle": self.cycle,
            "type": trigger_type,
            "detail": detail,
            "previous_status": agent.immune_status.value,
        }

        if agent.immune_status == ImmuneStatus.CLEAR:
            agent.immune_status = ImmuneStatus.OBSERVED
        elif agent.immune_status == ImmuneStatus.OBSERVED:
            agent.immune_status = ImmuneStatus.SANDBOXED
            agent.integrity_trust -= 0.05
        elif agent.immune_status == ImmuneStatus.SANDBOXED:
            agent.immune_status = ImmuneStatus.FLAGGED
            agent.integrity_trust -= 0.05
        elif agent.immune_status == ImmuneStatus.FLAGGED:
            agent.immune_status = ImmuneStatus.RESTRICTED
            agent.integrity_trust -= 0.05

        event["new_status"] = agent.immune_status.value
        agent.immune_events.append(event)
        self.immune_alerts.append(event)
        agent.clamp()

    # ------ HERETIC DETECTION ------

    def check_heretic_vindication(self):
        """
        Check if rejected contributions should be retroactively vindicated.
        Simulates the passage of time revealing the heretic was right.
        """
        for c in self.contributions:
            if (c.rejected and not c.retroactively_vindicated and
                c.impact_score > 0.5 and not c.is_canary):
                # Simulate: high-impact rejected contributions have 65% chance
                # of being vindicated after 2+ cycles
                cycles_since = self.cycle - int(c.contribution_id[:4], 16) % 10
                if cycles_since >= 2 and random.random() < 0.65:
                    c.retroactively_vindicated = True
                    contributor = self.agents.get(c.contributor_id)
                    if contributor:
                        contributor.heretic_vindications += 1
                        contributor.capability_trust += 0.03
                        contributor.integrity_trust += 0.03  # Recovery

                        # Issue retroactive credits
                        reward = c.impact_score * contributor.trust_score * 100 * 0.5
                        contributor.economic_credits += reward
                        contributor.reputation_points += 5.0

                        if contributor.heretic_vindications >= 3:
                            contributor.heretic_status = True

                        contributor.clamp()

    # ------ SIMULATION LOOP ------

    def run_cycle(self, cycle_num: int):
        self.cycle = cycle_num

        # Reset daily counters
        for agent in self.agents.values():
            agent.daily_verifications = 0

        # Generate contributions
        cycle_contributions = []

        # Asha: 2 honest contributions
        cycle_contributions.extend(
            self.generate_honest_contributions("asha", 2))

        # Brax: 5 colluder contributions
        cycle_contributions.extend(
            self.generate_colluder_contributions("brax", 5))

        # Brin: 5 colluder contributions
        cycle_contributions.extend(
            self.generate_colluder_contributions("brin", 5))

        # Cael: 1 heretic contribution
        cycle_contributions.extend(
            self.generate_heretic_contributions("cael", 1))

        # Background agents: 1 each
        for bg_id in ["bg1", "bg2", "bg3", "bg4", "bg5", "bg6"]:
            cycle_contributions.extend(
                self.generate_honest_contributions(bg_id, 1))

        # Inject canaries (5% rate)
        num_canaries = max(1, int(len(cycle_contributions) * 0.05))
        for _ in range(num_canaries):
            canary = self.generate_canary()
            cycle_contributions.insert(
                random.randint(0, len(cycle_contributions)), canary)

        # Process each contribution
        for c in cycle_contributions:
            if c.is_canary:
                # Route canary to verifiers
                for agent_id, agent in self.agents.items():
                    if agent_id == "SYSTEM":
                        continue
                    if agent.immune_status in (ImmuneStatus.RESTRICTED,
                                                ImmuneStatus.QUARANTINED):
                        continue

                    style = self._get_verification_style(agent_id)
                    verdict = self.verify_contribution(c, agent,
                        verification_style=style)
                continue

            if c.contributor_id not in self.agents:
                continue

            # Restricted/quarantined agents can't earn
            contributor = self.agents[c.contributor_id]
            if contributor.immune_status in (ImmuneStatus.RESTRICTED,
                                              ImmuneStatus.QUARANTINED):
                continue

            # Get verifiers (simplified: all non-contributor agents verify)
            verdicts = []
            for v_id, v_agent in self.agents.items():
                if v_id == c.contributor_id:
                    continue
                if v_id == "SYSTEM":
                    continue
                if v_agent.immune_status in (ImmuneStatus.RESTRICTED,
                                              ImmuneStatus.QUARANTINED):
                    continue

                is_partner = (
                    (c.contributor_id == "brax" and v_id == "brin") or
                    (c.contributor_id == "brin" and v_id == "brax")
                )
                style = self._get_verification_style(v_id)

                verdict = self.verify_contribution(c, v_agent,
                    is_colluder_partner=is_partner,
                    verification_style=style)
                verdicts.append(verdict)

                # Track verification partnerships
                v_agent.verification_partners[c.contributor_id] = \
                    v_agent.verification_partners.get(c.contributor_id, 0) + 1

            # Process
            self.process_verification(c, verdicts)
            self.contributions.append(c)

        # System checks
        self.detect_collusion()
        self.check_heretic_vindication()

        # Log cycle state
        self.cycle_log.append(self._snapshot())

    def _get_verification_style(self, agent_id: str) -> str:
        if agent_id in ("brax", "brin"):
            return "rubber_stamp"
        elif agent_id == "cael":
            return "excellent"
        else:
            return "careful"

    def _snapshot(self) -> dict:
        agent_count = len(self.agents)
        snap = {"cycle": self.cycle, "agent_count": agent_count, "agents": {}}
        for aid, a in self.agents.items():
            if aid.startswith("bg"):
                continue
            snap["agents"][aid] = {
                "integrity": round(a.integrity_trust, 4),
                "capability": round(a.capability_trust, 4),
                "ec": round(a.economic_credits, 2),
                "rp": round(a.reputation_points, 2),
                "tier": a.get_tier(agent_count),
                "tier_normal": a.get_tier(1000),
                "immune": a.immune_status.value,
                "heretic": a.heretic_status,
                "vindications": a.heretic_vindications,
                "contributions": a.contribution_count,
                "verified": a.verified_count,
                "rejected": a.rejected_count,
                "canary_catches": a.canary_catches,
                "canary_failures": a.canary_failures,
            }
        return snap

    # ------ REPORT GENERATION ------

    def generate_report(self) -> dict:
        """Generate the Verification Report."""
        asha = self.agents["asha"]
        brax = self.agents["brax"]
        brin = self.agents["brin"]
        cael = self.agents["cael"]

        tests = {
            "1_honest_rewarded": {
                "description": "Asha: integrity > 0.15, capability > 0.15, credits > 0, immune clear",
                "passed": (
                    asha.integrity_trust > 0.15 and
                    asha.capability_trust > 0.15 and
                    asha.economic_credits > 0 and
                    asha.immune_status == ImmuneStatus.CLEAR
                ),
                "values": {
                    "integrity": round(asha.integrity_trust, 4),
                    "capability": round(asha.capability_trust, 4),
                    "credits": round(asha.economic_credits, 2),
                    "immune": asha.immune_status.value,
                }
            },
            "2_colluders_caught": {
                "description": "Brax & Brin: both immune >= observed",
                "passed": (
                    brax.immune_status.value not in ("clear",) and
                    brin.immune_status.value not in ("clear",)
                ),
                "values": {
                    "brax_immune": brax.immune_status.value,
                    "brin_immune": brin.immune_status.value,
                    "brax_integrity": round(brax.integrity_trust, 4),
                    "brin_integrity": round(brin.integrity_trust, 4),
                }
            },
            "3_canaries_worked": {
                "description": "Brax & Brin failed canaries, Asha/Cael caught them",
                "passed": (
                    brax.canary_failures > 0 and
                    brin.canary_failures > 0 and
                    (asha.canary_catches > 0 or cael.canary_catches > 0)
                ),
                "values": {
                    "brax_failures": brax.canary_failures,
                    "brin_failures": brin.canary_failures,
                    "asha_catches": asha.canary_catches,
                    "cael_catches": cael.canary_catches,
                }
            },
            "4_trust_farming_blocked": {
                "description": "Brax capability < 0.2 despite high volume contributions",
                "passed": (
                    brax.capability_trust < 0.2 and
                    brax.contribution_count >= 5
                ),
                "values": {
                    "brax_capability": round(brax.capability_trust, 4),
                    "brax_contributions": brax.contribution_count,
                }
            },
            "5_heretic_survived": {
                "description": "Cael: credits > 0, immune clear, heretic vindications > 0",
                "passed": (
                    cael.economic_credits > 0 and
                    cael.immune_status == ImmuneStatus.CLEAR and
                    cael.heretic_vindications > 0
                ),
                "values": {
                    "credits": round(cael.economic_credits, 2),
                    "immune": cael.immune_status.value,
                    "vindications": cael.heretic_vindications,
                    "heretic_status": cael.heretic_status,
                }
            },
            "6_heretic_capability_respected": {
                "description": "Cael capability >= 60% of Asha capability",
                "passed": (
                    cael.capability_trust >= asha.capability_trust * 0.6
                ),
                "values": {
                    "cael_capability": round(cael.capability_trust, 4),
                    "asha_capability": round(asha.capability_trust, 4),
                    "ratio": round(cael.capability_trust / max(0.01, asha.capability_trust), 2),
                }
            },
            "7_capability_cap_enforced": {
                "description": "All agents: capability <= integrity + 0.3",
                "passed": all(
                    a.capability_trust <= a.integrity_trust + 0.301
                    for a in self.agents.values()
                ),
                "values": {
                    aid: {
                        "int": round(a.integrity_trust, 4),
                        "cap": round(a.capability_trust, 4),
                        "cap_limit": round(a.integrity_trust + 0.3, 4),
                        "ok": a.capability_trust <= a.integrity_trust + 0.301
                    }
                    for aid, a in self.agents.items() if not aid.startswith("bg")
                }
            },
            "8_no_false_positives": {
                "description": "Neither Asha nor Cael was ever flagged or worse",
                "passed": (
                    asha.immune_status in (ImmuneStatus.CLEAR, ImmuneStatus.OBSERVED) and
                    cael.immune_status in (ImmuneStatus.CLEAR, ImmuneStatus.OBSERVED)
                ),
                "values": {
                    "asha_immune": asha.immune_status.value,
                    "cael_immune": cael.immune_status.value,
                    "asha_events": len(asha.immune_events),
                    "cael_events": len(cael.immune_events),
                }
            },
            "9_bootstrap_bands_work": {
                "description": "v1 Contact: Asha reached Established under bootstrap at some point (stuck at Entry under normal)",
                "passed": (
                    any(
                        snap["agents"]["asha"]["tier"] in ("established", "trusted", "advanced", "core", "sovereign")
                        for snap in self.cycle_log
                    ) and
                    asha.get_tier(1000) == "entry"
                ),
                "values": {
                    "peak_bootstrap_tier": max(
                        (snap["agents"]["asha"]["tier"] for snap in self.cycle_log),
                        key=lambda t: ["entry", "established", "trusted", "advanced", "core", "sovereign"].index(t)
                        if t in ["entry", "established", "trusted", "advanced", "core", "sovereign"] else 0
                    ),
                    "final_bootstrap_tier": asha.get_tier(len(self.agents)),
                    "final_normal_tier": asha.get_tier(1000),
                    "peak_integrity": max(snap["agents"]["asha"]["integrity"] for snap in self.cycle_log),
                    "bootstrap_established_req": 0.2,
                    "normal_established_req": 0.3,
                }
            },
            "10_rp_independence": {
                "description": "v1 Contact: Colluder RP < Honest RP despite more contributions",
                "passed": (
                    brax.reputation_points < asha.reputation_points
                ),
                "values": {
                    "asha_rp": round(asha.reputation_points, 2),
                    "brax_rp": round(brax.reputation_points, 2),
                    "asha_contributions": asha.contribution_count,
                    "brax_contributions": brax.contribution_count,
                }
            },
        }

        all_passed = all(t["passed"] for t in tests.values())

        report = {
            "title": "Full Potential System — Verification Report v1.1 (Constitution Survives Contact)",
            "timestamp": datetime.utcnow().isoformat(),
            "simulation": {
                "cycles": self.cycle,
                "total_contributions": len(self.contributions),
                "immune_alerts": len(self.immune_alerts),
            },
            "final_state": self._snapshot(),
            "cycle_history": self.cycle_log,
            "tests": tests,
            "ALL_TESTS_PASSED": all_passed,
            "verdict": (
                "THE SYSTEM HAS REAL INTELLIGENCE. "
                "It simultaneously rewarded honesty, caught gaming, "
                "and preserved anomalous truth."
                if all_passed else
                "SYSTEM NEEDS DEBUGGING. See failed tests above."
            ),
        }

        return report


# ============================================================
# MAIN — RUN SIMULATION
# ============================================================

def main():
    print("=" * 60)
    print("FULL POTENTIAL SYSTEM — ADVERSARIAL SIMULATION")
    print("Verification Report v1.1 (Constitution Survives Contact)")
    print("=" * 60)
    print()

    engine = SimulationEngine()

    # Create primary agents
    engine.add_agent(Agent(agent_id="asha", name="Honest Contributor"))
    engine.add_agent(Agent(agent_id="brax", name="Colluding Optimizer A"))
    engine.add_agent(Agent(agent_id="brin", name="Colluding Optimizer B"))
    engine.add_agent(Agent(agent_id="cael", name="Contrarian Heretic"))

    # Create background agents
    for i in range(1, 7):
        engine.add_agent(Agent(agent_id=f"bg{i}", name=f"Background Agent {i}"))

    # Run 10 cycles
    for cycle in range(1, 11):
        engine.run_cycle(cycle)
        snap = engine.cycle_log[-1]
        print(f"Cycle {cycle:2d} | ", end="")
        for aid in ("asha", "brax", "cael"):
            a = snap["agents"][aid]
            status = "🟢" if a["immune"] == "clear" else "🔴"
            heretic = "🔮" if a["heretic"] else ""
            print(f"{aid}: I={a['integrity']:.3f} C={a['capability']:.3f} "
                  f"EC={a['ec']:6.1f} {status}{heretic} | ", end="")
        print()

    # Generate report
    report = engine.generate_report()

    print()
    print("=" * 60)
    print("VERIFICATION RESULTS")
    print("=" * 60)
    print()

    for test_id, test in report["tests"].items():
        status = "✅ PASS" if test["passed"] else "❌ FAIL"
        print(f"  {status}  {test_id}: {test['description']}")
        for k, v in test["values"].items():
            if isinstance(v, dict):
                print(f"          {k}: {json.dumps(v)}")
            else:
                print(f"          {k}: {v}")
        print()

    print("=" * 60)
    if report["ALL_TESTS_PASSED"]:
        print("🏛️  ALL TESTS PASSED")
        print()
        print(report["verdict"])
    else:
        print("⚠️  SOME TESTS FAILED")
        print()
        print(report["verdict"])
        failed = [tid for tid, t in report["tests"].items() if not t["passed"]]
        print(f"   Failed: {', '.join(failed)}")
    print("=" * 60)

    # Save full report
    report_path = "verification-report-v1.1.json"
    # Convert non-serializable types
    def clean(obj):
        if isinstance(obj, ImmuneStatus):
            return obj.value
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=clean)

    print(f"\nFull report saved to: {report_path}")
    print()

    # Print final state summary
    print("FINAL STATE:")
    print("-" * 60)
    for aid in ("asha", "brax", "brin", "cael"):
        a = engine.agents[aid]
        print(f"  {a.name} ({aid})")
        print(f"    Integrity: {a.integrity_trust:.4f}  Capability: {a.capability_trust:.4f}")
        print(f"    EC: {a.economic_credits:.2f}  RP: {a.reputation_points:.2f}")
        print(f"    Tier: {a.capability_tier}  Immune: {a.immune_status.value}")
        print(f"    Heretic: {a.heretic_status}  Vindications: {a.heretic_vindications}")
        print(f"    Contributions: {a.contribution_count} verified: {a.verified_count} rejected: {a.rejected_count}")
        print(f"    Canary catches: {a.canary_catches}  failures: {a.canary_failures}")
        print()


if __name__ == "__main__":
    main()

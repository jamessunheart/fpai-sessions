#!/usr/bin/env python3
"""Conversation OS — layered identity (repetition ≠ human identity).

Six independent layers. Message repetition advances ONLY channel-address
stability. It NEVER resolves a human/entity. entity_resolved requires
DETERMINISTIC evidence; model confidence or repetition may at most *propose*
a link, never verify one.

  1. channel_identity_observed      — we saw this channel address
  2. channel_identity_stable        — same address seen repeatedly (>= threshold)
  3. entity_candidate               — a placeholder entity behind the channel
  4. entity_link_proposed           — model/heuristic PROPOSES a human link (unverified)
  5. entity_resolved                — deterministic evidence links to a real entity
  6. cross_channel_link_verified    — the entity is verified across ≥2 channels
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

_STABLE_MIN = 2  # repeated observations that make a channel address "stable"


@dataclass(frozen=True)
class DeterministicEvidence:
    """The ONLY things that may resolve a human/entity. All default False."""
    verified_contact_match: bool = False       # matches an existing verified contact
    authenticated_ownership: bool = False      # proven account ownership
    explicit_human_confirmation: bool = False  # a human explicitly confirmed
    verified_channel_linkage: bool = False     # previously verified channel link
    other_high_trust_proof: str | None = None  # named alternative proof
    verified_channels: frozenset[str] = field(default_factory=frozenset)


def assess(channel_address: str | None, observation_count: int,
           *, model_proposes_link: bool = False,
           evidence: DeterministicEvidence | None = None) -> dict[str, Any]:
    ev = evidence or DeterministicEvidence()
    addr = (channel_address or "").strip().lower()
    channel_id = "chan-" + hashlib.sha256(addr.encode()).hexdigest()[:12] if addr else None
    entity_cand = "entcand-" + hashlib.sha256(addr.encode()).hexdigest()[:12] if addr else None

    resolved = bool(
        ev.verified_contact_match or ev.authenticated_ownership
        or ev.explicit_human_confirmation or ev.verified_channel_linkage
        or ev.other_high_trust_proof)
    resolving_evidence = [k for k, v in {
        "verified_contact_match": ev.verified_contact_match,
        "authenticated_ownership": ev.authenticated_ownership,
        "explicit_human_confirmation": ev.explicit_human_confirmation,
        "verified_channel_linkage": ev.verified_channel_linkage,
        "other_high_trust_proof": bool(ev.other_high_trust_proof),
    }.items() if v]

    return {
        "channel_identity_observed": bool(addr),
        "channel_identity_stable": observation_count >= _STABLE_MIN,
        "observation_count": observation_count,
        "channel_id": channel_id,
        "entity_candidate": entity_cand,
        # a link may be PROPOSED by repetition/model — never counts as resolution
        "entity_link_proposed": bool(model_proposes_link or observation_count >= _STABLE_MIN),
        "entity_resolved": resolved,                       # deterministic evidence ONLY
        "resolving_evidence": resolving_evidence,
        "cross_channel_link_verified": len(ev.verified_channels) >= 2,
        "verified_channels": sorted(ev.verified_channels),
        "note": ("repetition proves a stable CHANNEL ADDRESS, not a human identity; "
                 "entity_resolved requires deterministic evidence"),
    }

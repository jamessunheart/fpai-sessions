"""Feature flag resolver.

Resolution order:
1. ``tenant_features`` row (tenant-specific override, source of truth).
2. Plan default (declared in ``PLAN_DEFAULTS`` below).
3. Global env-level default (``settings.feature_*``).

Features are stringly-typed to match the DB column; they must be declared here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings

# Canonical feature keys
FEATURES = {
    "inbound_voice",
    "inbound_sms",
    "inbound_chat",
    "inbound_email",
    "booking",
    "human_escalation",
    "realtime_voice",
    "outbound_campaigns",
    "outbound_ai_dialer",
    "skills_mesh_routing",
    "ai_qa",
    "auto_training",
    "conversational_admin",
    "recording",
    "warm_transfer",
    "voicemail_transcription",
}

PLAN_DEFAULTS: dict[str, dict[str, bool]] = {
    "starter": {
        "inbound_voice": True,
        "inbound_sms": True,
        "booking": True,
        "human_escalation": True,
        "realtime_voice": True,
        "recording": True,
        "warm_transfer": True,
        "voicemail_transcription": True,
        "ai_qa": True,
        "auto_training": True,
    },
    "pro": {
        "inbound_voice": True,
        "inbound_sms": True,
        "inbound_chat": True,
        "inbound_email": True,
        "booking": True,
        "human_escalation": True,
        "realtime_voice": True,
        "outbound_campaigns": True,
        "recording": True,
        "warm_transfer": True,
        "voicemail_transcription": True,
        "ai_qa": True,
        "auto_training": True,
        "conversational_admin": True,
    },
    "scale": {k: True for k in FEATURES},
}


@dataclass
class FeatureState:
    enabled: bool
    config: dict[str, Any]
    source: str  # 'tenant' | 'plan' | 'global'


async def get_feature(
    session: AsyncSession, feature_key: str, *, plan: str | None = None
) -> FeatureState:
    if feature_key not in FEATURES:
        raise ValueError(f"unknown feature: {feature_key}")

    row = (
        await session.execute(
            text(
                "SELECT enabled, config FROM tenant_features WHERE feature_key = :k LIMIT 1"
            ),
            {"k": feature_key},
        )
    ).first()
    if row is not None:
        return FeatureState(enabled=bool(row[0]), config=dict(row[1] or {}), source="tenant")

    if plan and plan in PLAN_DEFAULTS:
        if feature_key in PLAN_DEFAULTS[plan]:
            return FeatureState(
                enabled=PLAN_DEFAULTS[plan][feature_key], config={}, source="plan"
            )

    global_attr = f"feature_{feature_key}"
    if hasattr(settings, global_attr):
        return FeatureState(enabled=bool(getattr(settings, global_attr)), config={}, source="global")
    return FeatureState(enabled=False, config={}, source="global")


async def require_feature(
    session: AsyncSession, feature_key: str, *, plan: str | None = None
) -> FeatureState:
    state = await get_feature(session, feature_key, plan=plan)
    if not state.enabled:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=403, detail=f"feature '{feature_key}' not enabled for tenant"
        )
    return state

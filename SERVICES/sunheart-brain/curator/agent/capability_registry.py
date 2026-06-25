"""Capability registry and tenant capability request messages."""

from __future__ import annotations

from .user_agent import TIER_ORDER, UserAgent


CAPABILITY_REGISTRY = {
    "send_email": {
        "tier": "basic",
        "consent_required": True,
        "description": "Send email on your behalf",
    },
    "send_telegram": {
        "tier": "basic",
        "consent_required": True,
        "description": "Send Telegram messages for you",
    },
    "book_calendar": {
        "tier": "basic",
        "consent_required": True,
        "description": "Add events to your calendar",
    },
    "search_web": {
        "tier": "free",
        "consent_required": False,
        "description": "Search the web during chat",
    },
    "book_travel": {
        "tier": "pro",
        "consent_required": True,
        "description": "Search and book travel",
    },
    "send_sms": {
        "tier": "pro",
        "consent_required": True,
        "description": "Send SMS on your behalf",
    },
    "memory_export": {
        "tier": "basic",
        "consent_required": False,
        "description": "Export your conversation history",
    },
}


def request_capability(user_agent: UserAgent, capability: str) -> str:
    spec = CAPABILITY_REGISTRY.get(capability)
    if not spec:
        return f"Unknown capability: {capability}."

    required_tier = str(spec["tier"])
    if TIER_ORDER.get(user_agent.tier, 0) < TIER_ORDER[required_tier]:
        return (
            f"{spec['description']} requires the {required_tier} tier. "
            "Reply /upgrade to unlock it."
        )

    if spec["consent_required"] and not user_agent.capabilities.get(capability, False):
        return (
            f"Consent required: {spec['description']}. "
            f"Reply yes to grant {capability}."
        )

    return f"{capability} is available for your agent."

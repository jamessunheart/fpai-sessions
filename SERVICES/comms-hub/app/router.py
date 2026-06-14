from __future__ import annotations

from .config import Settings
from .models import DeliveryPlan, MessageRecord, Surface


def route_message(message: MessageRecord, settings: Settings, runtime_paused: bool = False) -> DeliveryPlan:
    reasons: list[str] = []
    if not settings.enabled:
        return DeliveryPlan(message_id=message.id, blocked=True, reasons=["COMMS_HUB_ENABLED=0"])
    if runtime_paused:
        return DeliveryPlan(message_id=message.id, blocked=True, reasons=["COMMS_HUB_RUNTIME_PAUSED=1"])
    if message.audience == "all" and not settings.broadcast_enabled:
        return DeliveryPlan(message_id=message.id, blocked=True, reasons=["COMMS_HUB_BROADCAST_ENABLED=0"])
    if message.audience == "builder" and message.source == "telegram" and not settings.builder_bridge_enabled:
        return DeliveryPlan(message_id=message.id, blocked=True, reasons=["COMMS_HUB_BUILDER_BRIDGE_ENABLED=0"])

    surfaces = list(message.route) if message.route else default_route(message, settings)
    filtered: list[Surface] = []
    for surface in surfaces:
        if surface == "obsidian" and not settings.obsidian_enabled:
            reasons.append("obsidian disabled")
            continue
        if surface == "telegram" and not (settings.tg_enabled and settings.tg_send_enabled):
            reasons.append("telegram send disabled")
            continue
        if surface == "voice" and not (settings.voice_enabled and settings.voice_reply_enabled):
            reasons.append("voice reply disabled")
            filtered.append("telegram" if settings.tg_enabled and settings.tg_send_enabled else "terminal")
            continue
        filtered.append(surface)
    return DeliveryPlan(message_id=message.id, surfaces=dedupe_surfaces(filtered), reasons=reasons)


def default_route(message: MessageRecord, settings: Settings) -> list[Surface]:
    if message.source in {"system", "builder"} and message.audience == "james":
        surfaces: list[Surface] = ["terminal"]
        if settings.obsidian_enabled:
            surfaces.append("obsidian")
        if message.source == "builder" and message.priority in {"high", "urgent"} and settings.tg_enabled and settings.tg_send_enabled:
            surfaces.append("telegram")
        return surfaces
    if message.source in {"telegram", "terminal", "obsidian"}:
        return ["inbox", "terminal"]
    return ["terminal"]


def dedupe_surfaces(surfaces: list[Surface]) -> list[Surface]:
    seen: set[Surface] = set()
    result: list[Surface] = []
    for surface in surfaces:
        if surface not in seen:
            seen.add(surface)
            result.append(surface)
    return result


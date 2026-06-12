from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI

from .adapters import obsidian, telegram, terminal, voice
from .config import Settings, load_settings
from .models import DeliveryAttempt, HealthResponse, MessageInput, MessageRecord
from .router import route_message
from .store import JsonlStore


def create_app(settings: Settings | None = None, store: JsonlStore | None = None) -> FastAPI:
    settings = settings or load_settings()
    store = store or JsonlStore(settings.var_dir)
    app = FastAPI(title="Comms Hub - James Interface", version=settings.version)
    app.state.settings = settings
    app.state.store = store

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        status = "healthy" if settings.enabled else "degraded"
        return HealthResponse(
            status=status,
            service=settings.service_name,
            version=settings.version,
            dry_run=settings.dry_run,
            runtime_paused=store.runtime_paused(),
        )

    @app.get("/capabilities")
    def capabilities() -> dict[str, Any]:
        return {
            "service_name": settings.service_name,
            "version": settings.version,
            "capabilities": ["routed-outbox", "routed-inbox", "terminal", "obsidian", "telegram", "voice-metadata"],
            "adapters": {
                "terminal": {"enabled": True},
                "obsidian": {"enabled": settings.obsidian_enabled},
                "telegram": telegram.adapter_state(settings),
                "voice": {"enabled": settings.voice_enabled, "reply_enabled": settings.voice_reply_enabled},
            },
        }

    @app.get("/state")
    def state() -> dict[str, Any]:
        raw = store.load_state()
        last_inbox = raw.get("last_inbox_at")
        stale = False
        if last_inbox:
            try:
                elapsed = datetime.now(timezone.utc).timestamp() - datetime.fromisoformat(last_inbox).timestamp()
                stale = elapsed > settings.stale_after_seconds
            except ValueError:
                stale = True
        return {
            "status": "active" if settings.enabled else "inactive",
            "mode": "dry_run" if settings.dry_run else "live",
            "runtime_paused": store.runtime_paused(),
            "outbox_count": len(store.outbox()),
            "inbox_count": len(store.inbox()),
            "delivery_log_count": len(store.delivery_log()),
            "last_inbox_at": last_inbox,
            "last_outbox_drain_at": raw.get("last_outbox_drain_at"),
            "telegram_last_update_id": raw.get("telegram_last_update_id"),
            "telegram_inbox_stale": stale,
            "telegram": telegram.adapter_state(settings),
        }

    @app.post("/outbox/publish")
    def publish(message: MessageInput) -> dict[str, Any]:
        record = store.append_outbox(message)
        plan = route_message(record, settings, store.runtime_paused())
        return {"queued": True, "message": record.model_dump(), "plan": plan.model_dump()}

    @app.post("/outbox/drain")
    def drain() -> dict[str, Any]:
        return drain_outbox(settings, store)

    @app.post("/inbox/poll")
    def poll() -> dict[str, Any]:
        return poll_inbox(settings, store)

    @app.post("/inbox/receive")
    def receive(message: MessageInput) -> dict[str, Any]:
        record = store.append_inbox(message)
        return {"received": True, "message": record.model_dump()}

    @app.post("/inbox/dispatch")
    def dispatch() -> dict[str, Any]:
        return dispatch_inbox(settings, store)

    @app.post("/tick")
    def tick() -> dict[str, Any]:
        return run_tick(settings, store)

    @app.post("/runtime/pause")
    def pause() -> dict[str, bool]:
        store.set_runtime_paused(True)
        return {"runtime_paused": True}

    @app.post("/runtime/resume")
    def resume() -> dict[str, bool]:
        store.set_runtime_paused(False)
        return {"runtime_paused": False}

    return app


def poll_inbox(settings: Settings, store: JsonlStore) -> dict[str, Any]:
    if not settings.enabled or store.runtime_paused():
        return {"polled": False, "records": [], "reason": "paused_or_disabled"}
    records = telegram.poll_updates(settings, store)
    return {"polled": True, "records": [record.model_dump() for record in records]}


def run_tick(settings: Settings, store: JsonlStore) -> dict[str, Any]:
    poll_result = poll_inbox(settings, store)
    dispatch_result = dispatch_inbox(settings, store)
    drain_result = drain_outbox(settings, store)
    return {
        "tick": True,
        "poll": poll_result,
        "dispatch": dispatch_result,
        "drain": drain_result,
    }


def drain_outbox(settings: Settings, store: JsonlStore) -> dict[str, Any]:
    if not settings.enabled:
        return {"drained": False, "reason": "COMMS_HUB_ENABLED=0", "attempts": []}
    if store.runtime_paused():
        return {"drained": False, "reason": "COMMS_HUB_RUNTIME_PAUSED=1", "attempts": []}
    if not settings.outbox_drain_enabled and not settings.dry_run:
        return {"drained": False, "reason": "COMMS_HUB_OUTBOX_DRAIN_ENABLED=0", "attempts": []}

    attempts: list[dict[str, Any]] = []
    with store.lock("drain"):
        for message in store.outbox():
            plan = route_message(message, settings, store.runtime_paused())
            if plan.blocked:
                attempt = DeliveryAttempt(
                    message_id=message.id,
                    surface="terminal",
                    status="blocked",
                    detail="; ".join(plan.reasons),
                    dry_run=settings.dry_run,
                )
                store.append_delivery(attempt)
                attempts.append(attempt.model_dump())
                continue
            for surface in plan.surfaces:
                result = deliver_surface(surface, message, settings)
                attempt = DeliveryAttempt(
                    message_id=message.id,
                    surface=surface,
                    status=result.status,
                    detail=result.detail,
                    dry_run=settings.dry_run,
                )
                store.append_delivery(attempt)
                attempts.append(attempt.model_dump())
    return {"drained": True, "attempts": attempts}


def dispatch_inbox(settings: Settings, store: JsonlStore) -> dict[str, Any]:
    if not settings.enabled:
        return {"dispatched": False, "reason": "COMMS_HUB_ENABLED=0", "attempts": []}
    if store.runtime_paused():
        resume_result = dispatch_resume_only(settings, store)
        if resume_result["attempts"]:
            return resume_result
        return {"dispatched": False, "reason": "COMMS_HUB_RUNTIME_PAUSED=1", "attempts": []}

    state = store.load_state()
    dispatched_ids = set(state.get("dispatched_inbox_ids", []))
    attempts: list[dict[str, Any]] = []

    with store.lock("dispatch"):
        for message in store.inbox():
            if message.id in dispatched_ids:
                continue
            attempt = dispatch_message(message, settings, store)
            store.append_delivery(attempt)
            attempts.append(attempt.model_dump())
            dispatched_ids.add(message.id)

        state = store.load_state()
        state["dispatched_inbox_ids"] = sorted(dispatched_ids)
        store.save_state(state)

    return {"dispatched": True, "attempts": attempts}


def dispatch_resume_only(settings: Settings, store: JsonlStore) -> dict[str, Any]:
    state = store.load_state()
    dispatched_ids = set(state.get("dispatched_inbox_ids", []))
    attempts: list[dict[str, Any]] = []

    with store.lock("dispatch"):
        for message in store.inbox():
            if message.id in dispatched_ids or not is_command(message, "/resume"):
                continue
            attempt = dispatch_message(message, settings, store)
            store.append_delivery(attempt)
            attempts.append(attempt.model_dump())
            dispatched_ids.add(message.id)

        state = store.load_state()
        state["dispatched_inbox_ids"] = sorted(dispatched_ids)
        store.save_state(state)

    return {"dispatched": True, "attempts": attempts}


def dispatch_message(message: MessageRecord, settings: Settings, store: JsonlStore) -> DeliveryAttempt:
    command_attempt = handle_system_command(message, settings, store)
    if command_attempt is not None:
        return command_attempt

    if message.audience == "builder" and not settings.builder_bridge_enabled:
        return DeliveryAttempt(
            message_id=message.id,
            surface="inbox",
            status="blocked",
            detail="COMMS_HUB_BUILDER_BRIDGE_ENABLED=0",
            dry_run=settings.dry_run,
        )
    if message.audience == "all" and not settings.broadcast_enabled:
        return DeliveryAttempt(
            message_id=message.id,
            surface="inbox",
            status="blocked",
            detail="COMMS_HUB_BROADCAST_ENABLED=0",
            dry_run=settings.dry_run,
        )

    target = message.audience
    if target == "builder" and message.metadata.get("builder_id"):
        target = f"builder:{message.metadata['builder_id']}"
    status = "dry_run" if settings.dry_run else "delivered"
    return DeliveryAttempt(
        message_id=message.id,
        surface="inbox",
        status=status,
        detail=f"would dispatch to {target}" if settings.dry_run else f"dispatched to {target}",
        dry_run=settings.dry_run,
    )


def handle_system_command(message: MessageRecord, settings: Settings, store: JsonlStore) -> DeliveryAttempt | None:
    if message.audience != "system":
        return None

    if is_command(message, "/system status") or is_command(message, "/status"):
        status = build_status_text(settings, store)
        store.append_outbox(MessageInput(
            source="system",
            audience="james",
            priority="normal",
            topic="system-status",
            body=status,
            route=reply_route(message),
            metadata=reply_metadata(message),
        ))
        return DeliveryAttempt(
            message_id=message.id,
            surface="inbox",
            status="dry_run" if settings.dry_run else "delivered",
            detail="handled /system status; queued reply",
            dry_run=settings.dry_run,
        )

    if is_command(message, "/pause"):
        store.set_runtime_paused(True)
        store.append_outbox(MessageInput(
            source="system",
            audience="james",
            priority="high",
            topic="runtime-paused",
            body="Comms hub runtime pause is now on. Normal dispatch and drain are blocked until /resume.",
            route=reply_route(message),
            metadata=reply_metadata(message),
        ))
        return DeliveryAttempt(
            message_id=message.id,
            surface="inbox",
            status="dry_run" if settings.dry_run else "delivered",
            detail="handled /pause; runtime paused",
            dry_run=settings.dry_run,
        )

    if is_command(message, "/resume"):
        store.set_runtime_paused(False)
        store.append_outbox(MessageInput(
            source="system",
            audience="james",
            priority="high",
            topic="runtime-resumed",
            body="Comms hub runtime pause is now off. Dispatch and drain may continue subject to kill switches.",
            route=reply_route(message),
            metadata=reply_metadata(message),
        ))
        return DeliveryAttempt(
            message_id=message.id,
            surface="inbox",
            status="dry_run" if settings.dry_run else "delivered",
            detail="handled /resume; runtime resumed",
            dry_run=settings.dry_run,
        )

    return None


def is_command(message: MessageRecord, command: str) -> bool:
    body = message.body.strip().lower()
    return body == command or body.startswith(command + " ")


def reply_route(message: MessageRecord) -> list[str]:
    if message.source == "telegram":
        return ["telegram"]
    if message.source == "obsidian":
        return ["obsidian"]
    return ["terminal"]


def reply_metadata(message: MessageRecord) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if "telegram_chat_id" in message.metadata:
        metadata["telegram_chat_id"] = message.metadata["telegram_chat_id"]
    return metadata


def build_status_text(settings: Settings, store: JsonlStore) -> str:
    raw = store.load_state()
    return (
        "Comms hub status: "
        f"enabled={settings.enabled}, "
        f"dry_run={settings.dry_run}, "
        f"paused={store.runtime_paused()}, "
        f"inbox={len(store.inbox())}, "
        f"outbox={len(store.outbox())}, "
        f"telegram_enabled={settings.tg_enabled}, "
        f"last_inbox_at={raw.get('last_inbox_at', '')}"
    )


def deliver_surface(surface: str, message: MessageRecord, settings: Settings):
    if surface == "terminal":
        return terminal.deliver(message, settings.dry_run)
    if surface == "obsidian":
        return obsidian.deliver(message, settings)
    if surface == "telegram":
        return telegram.send_message(message, settings)
    if surface == "voice":
        return voice.outbound_voice_reply(message, settings)
    return terminal.deliver(message, settings.dry_run)


app = create_app()

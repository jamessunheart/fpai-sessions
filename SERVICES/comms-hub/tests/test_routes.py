from __future__ import annotations

from app.config import Settings
from app.main import dispatch_inbox, run_tick
from app.models import MessageInput
from app.router import route_message
from app.store import JsonlStore


def record_for(tmp_path, message: MessageInput):
    return JsonlStore(tmp_path).create_record(message)


def test_system_to_james_defaults_to_terminal_and_obsidian_when_enabled(tmp_path):
    settings = Settings(var_dir=tmp_path, obsidian_enabled=True)
    record = record_for(tmp_path, MessageInput(source="system", audience="james", body="pulse"))

    plan = route_message(record, settings)

    assert plan.surfaces == ["terminal", "obsidian"]


def test_builder_to_james_urgent_can_include_telegram_when_enabled(tmp_path):
    settings = Settings(
        var_dir=tmp_path,
        tg_enabled=True,
        tg_send_enabled=True,
    )
    record = record_for(tmp_path, MessageInput(source="builder", audience="james", priority="urgent", body="help"))

    plan = route_message(record, settings)

    assert "telegram" in plan.surfaces


def test_james_to_builder_blocked_when_builder_bridge_disabled(tmp_path):
    settings = Settings(var_dir=tmp_path, builder_bridge_enabled=False)
    record = record_for(tmp_path, MessageInput(source="telegram", audience="builder", body="/builder go"))

    plan = route_message(record, settings)

    assert plan.blocked is True
    assert "COMMS_HUB_BUILDER_BRIDGE_ENABLED=0" in plan.reasons


def test_broadcast_blocked_when_disabled(tmp_path):
    settings = Settings(var_dir=tmp_path, broadcast_enabled=False)
    record = record_for(tmp_path, MessageInput(source="system", audience="all", body="broadcast"))

    plan = route_message(record, settings)

    assert plan.blocked is True
    assert "COMMS_HUB_BROADCAST_ENABLED=0" in plan.reasons


def test_dispatch_system_message_records_dry_run_attempt(tmp_path):
    settings = Settings(var_dir=tmp_path, dry_run=True)
    store = JsonlStore(tmp_path)
    record = store.append_inbox(MessageInput(source="telegram", audience="system", body="/system hi"))

    result = dispatch_inbox(settings, store)

    assert result["dispatched"] is True
    assert result["attempts"][0]["message_id"] == record.id
    assert result["attempts"][0]["status"] == "dry_run"
    assert "system" in result["attempts"][0]["detail"]


def test_dispatch_builder_blocked_until_bridge_enabled(tmp_path):
    settings = Settings(var_dir=tmp_path, builder_bridge_enabled=False)
    store = JsonlStore(tmp_path)
    store.append_inbox(MessageInput(source="telegram", audience="builder", body="/builder alpha fix", metadata={"builder_id": "alpha"}))

    result = dispatch_inbox(settings, store)

    assert result["attempts"][0]["status"] == "blocked"
    assert result["attempts"][0]["detail"] == "COMMS_HUB_BUILDER_BRIDGE_ENABLED=0"


def test_dispatch_marks_inbox_id_and_skips_duplicate(tmp_path):
    settings = Settings(var_dir=tmp_path)
    store = JsonlStore(tmp_path)
    record = store.append_inbox(MessageInput(source="telegram", audience="system", body="once"))

    first = dispatch_inbox(settings, store)
    second = dispatch_inbox(settings, store)

    assert len(first["attempts"]) == 1
    assert second["attempts"] == []
    assert record.id in store.load_state()["dispatched_inbox_ids"]


def test_system_status_queues_reply_to_outbox(tmp_path):
    settings = Settings(var_dir=tmp_path)
    store = JsonlStore(tmp_path)
    store.append_inbox(MessageInput(source="terminal", audience="system", body="/system status"))

    result = dispatch_inbox(settings, store)

    assert result["attempts"][0]["detail"] == "handled /system status; queued reply"
    replies = store.outbox()
    assert len(replies) == 1
    assert replies[0].topic == "system-status"
    assert "Comms hub status" in replies[0].body
    assert replies[0].route == ["terminal"]


def test_pause_command_sets_runtime_paused_and_queues_reply(tmp_path):
    settings = Settings(var_dir=tmp_path)
    store = JsonlStore(tmp_path)
    store.append_inbox(MessageInput(source="terminal", audience="system", body="/pause"))

    result = dispatch_inbox(settings, store)

    assert result["attempts"][0]["detail"] == "handled /pause; runtime paused"
    assert store.runtime_paused() is True
    assert store.outbox()[0].topic == "runtime-paused"


def test_resume_command_dispatches_even_while_paused(tmp_path):
    settings = Settings(var_dir=tmp_path)
    store = JsonlStore(tmp_path)
    store.set_runtime_paused(True)
    store.append_inbox(MessageInput(source="terminal", audience="system", body="/resume"))

    result = dispatch_inbox(settings, store)

    assert result["dispatched"] is True
    assert result["attempts"][0]["detail"] == "handled /resume; runtime resumed"
    assert store.runtime_paused() is False
    assert store.outbox()[0].topic == "runtime-resumed"


def test_tick_runs_poll_dispatch_and_drain(tmp_path):
    settings = Settings(var_dir=tmp_path)
    store = JsonlStore(tmp_path)
    store.append_inbox(MessageInput(source="terminal", audience="system", body="/system status"))

    result = run_tick(settings, store)

    assert result["tick"] is True
    assert result["poll"]["polled"] is True
    assert result["dispatch"]["attempts"][0]["detail"] == "handled /system status; queued reply"
    assert result["drain"]["attempts"][0]["surface"] == "terminal"

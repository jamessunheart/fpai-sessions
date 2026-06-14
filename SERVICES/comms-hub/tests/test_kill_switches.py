from __future__ import annotations

from app.config import Settings
from app.main import dispatch_inbox, drain_outbox
from app.models import MessageInput
from app.router import route_message
from app.store import JsonlStore


def test_global_disabled_blocks_drain_and_route(tmp_path):
    settings = Settings(var_dir=tmp_path, enabled=False)
    store = JsonlStore(tmp_path)
    record = store.append_outbox(MessageInput(body="blocked"))

    assert route_message(record, settings).blocked is True
    assert drain_outbox(settings, store)["drained"] is False


def test_dry_run_prevents_external_sends(tmp_path):
    settings = Settings(
        var_dir=tmp_path,
        dry_run=True,
        tg_enabled=True,
        tg_send_enabled=True,
        telegram_bot_token="123456789:tokenvaluebutnotreal",
        telegram_allowed_chat_ids={"42"},
    )
    store = JsonlStore(tmp_path)
    store.append_outbox(MessageInput(body="hi", route=["telegram"], metadata={"telegram_chat_id": "42"}))

    result = drain_outbox(settings, store)

    assert result["attempts"][0]["status"] == "dry_run"


def test_telegram_send_and_poll_switches_are_independent(tmp_path):
    settings = Settings(var_dir=tmp_path, tg_enabled=True, tg_send_enabled=False, tg_poll_enabled=True)
    record = JsonlStore(tmp_path).create_record(MessageInput(body="hi", route=["telegram"]))

    plan = route_message(record, settings)

    assert plan.surfaces == []
    assert "telegram send disabled" in plan.reasons


def test_runtime_pause_blocks_drain_without_environment_change(tmp_path):
    settings = Settings(var_dir=tmp_path)
    store = JsonlStore(tmp_path)
    store.append_outbox(MessageInput(body="paused"))
    store.set_runtime_paused(True)

    result = drain_outbox(settings, store)

    assert result["drained"] is False
    assert result["reason"] == "COMMS_HUB_RUNTIME_PAUSED=1"


def test_runtime_pause_blocks_dispatch_without_environment_change(tmp_path):
    settings = Settings(var_dir=tmp_path)
    store = JsonlStore(tmp_path)
    store.append_inbox(MessageInput(source="telegram", audience="system", body="paused"))
    store.set_runtime_paused(True)

    result = dispatch_inbox(settings, store)

    assert result["dispatched"] is False
    assert result["reason"] == "COMMS_HUB_RUNTIME_PAUSED=1"

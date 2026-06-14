from __future__ import annotations

from app.adapters import telegram
from app.config import Settings
from app.models import MessageInput
from app.store import JsonlStore


def test_no_token_means_disabled_state_not_crash(tmp_path):
    settings = Settings(var_dir=tmp_path, tg_enabled=True, telegram_bot_token="")

    state = telegram.adapter_state(settings)

    assert state["enabled"] is True
    assert state["token_present"] is False
    assert state["will_call_get_updates"] is False


def test_allowlist_rejects_unknown_chat_id(tmp_path):
    settings = Settings(
        var_dir=tmp_path,
        dry_run=True,
        tg_enabled=True,
        tg_send_enabled=True,
        telegram_bot_token="123456789:notarealtoken",
        telegram_allowed_chat_ids={"42"},
    )
    message = JsonlStore(tmp_path).create_record(MessageInput(body="hi", metadata={"telegram_chat_id": "99"}))

    result = telegram.send_message(message, settings)

    assert result.status == "blocked"
    assert "allowlisted" in result.detail


def test_update_checkpoint_prevents_duplicate_inbox_messages(tmp_path):
    settings = Settings(
        var_dir=tmp_path,
        tg_enabled=True,
        tg_poll_enabled=True,
        telegram_allowed_chat_ids={"42"},
    )
    store = JsonlStore(tmp_path)
    update = {"update_id": 7, "message": {"chat": {"id": 42}, "text": "/system hello"}}

    first = telegram.poll_updates(settings, store, [update])
    second = telegram.poll_updates(settings, store, [update])

    assert len(first) == 1
    assert second == []
    assert len(store.inbox()) == 1
    assert store.load_state()["telegram_last_update_id"] == 7


def test_adapter_never_logs_token_value(tmp_path):
    token = "123456789:supersecrettokenvalue12345"
    settings = Settings(
        var_dir=tmp_path,
        tg_enabled=True,
        tg_send_enabled=True,
        telegram_bot_token=token,
        telegram_allowed_chat_ids={"42"},
    )
    message = JsonlStore(tmp_path).create_record(MessageInput(body="hi", metadata={"telegram_chat_id": "42"}))

    result = telegram.send_message(message, settings)

    assert token not in result.detail


def test_live_send_calls_telegram_api_when_not_dry_run(tmp_path, monkeypatch):
    calls = []

    def fake_request(settings, method, payload):
        calls.append((method, payload))
        return {"ok": True, "result": {"message_id": 1}}

    monkeypatch.setattr(telegram, "telegram_api_request", fake_request)
    settings = Settings(
        var_dir=tmp_path,
        dry_run=False,
        tg_enabled=True,
        tg_send_enabled=True,
        telegram_bot_token="123456789:notarealtoken",
        telegram_allowed_chat_ids={"42"},
    )
    message = JsonlStore(tmp_path).create_record(MessageInput(body="live", metadata={"telegram_chat_id": "42"}))

    result = telegram.send_message(message, settings)

    assert result.status == "delivered"
    assert calls == [("sendMessage", {"chat_id": "42", "text": "live"})]


def test_dry_run_send_does_not_call_telegram_api(tmp_path, monkeypatch):
    calls = []

    def fake_request(settings, method, payload):
        calls.append((method, payload))
        return {"ok": True}

    monkeypatch.setattr(telegram, "telegram_api_request", fake_request)
    settings = Settings(
        var_dir=tmp_path,
        dry_run=True,
        tg_enabled=True,
        tg_send_enabled=True,
        telegram_bot_token="123456789:notarealtoken",
        telegram_allowed_chat_ids={"42"},
    )
    message = JsonlStore(tmp_path).create_record(MessageInput(body="dry", metadata={"telegram_chat_id": "42"}))

    result = telegram.send_message(message, settings)

    assert result.status == "dry_run"
    assert calls == []


def test_poll_updates_fetches_from_telegram_api_when_updates_not_injected(tmp_path, monkeypatch):
    def fake_request(settings, method, payload):
        return {
            "ok": True,
            "result": [
                {"update_id": 8, "message": {"chat": {"id": 42}, "text": "/status"}},
            ],
        }

    monkeypatch.setattr(telegram, "telegram_api_request", fake_request)
    settings = Settings(
        var_dir=tmp_path,
        tg_enabled=True,
        tg_poll_enabled=True,
        tg_live_poll_confirmed=True,
        telegram_bot_token="123456789:notarealtoken",
        telegram_allowed_chat_ids={"42"},
    )
    store = JsonlStore(tmp_path)

    records = telegram.poll_updates(settings, store)

    assert len(records) == 1
    assert records[0].body == "/status"
    assert store.load_state()["telegram_last_update_id"] == 8


def test_live_poll_requires_explicit_confirm(tmp_path, monkeypatch):
    calls = []

    def fake_request(settings, method, payload):
        calls.append((method, payload))
        return {"ok": True, "result": []}

    monkeypatch.setattr(telegram, "telegram_api_request", fake_request)
    settings = Settings(
        var_dir=tmp_path,
        tg_enabled=True,
        tg_poll_enabled=True,
        tg_live_poll_confirmed=False,
        telegram_bot_token="123456789:notarealtoken",
        telegram_allowed_chat_ids={"42"},
    )

    records = telegram.poll_updates(settings, JsonlStore(tmp_path))

    assert records == []
    assert calls == []
    assert telegram.adapter_state(settings)["will_call_get_updates"] is False

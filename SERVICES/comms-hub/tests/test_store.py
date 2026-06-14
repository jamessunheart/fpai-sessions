from __future__ import annotations

import pytest

from app.models import MessageInput
from app.store import JsonlStore, StoreError


def test_appends_valid_jsonl_records(store):
    record = store.append_outbox(MessageInput(body="hello"))

    records = store.outbox()
    assert len(records) == 1
    assert records[0].id == record.id
    assert records[0].body == "hello"


def test_rejects_malformed_messages(store):
    store.outbox_path.write_text("{not-json}\n")

    with pytest.raises(StoreError):
        store.outbox()


def test_preserves_append_only_behavior(store):
    store.append_outbox(MessageInput(body="one"))
    store.append_outbox(MessageInput(body="two"))

    assert [record.body for record in store.outbox()] == ["one", "two"]


def test_lock_prevents_concurrent_drain_corruption(tmp_path):
    store = JsonlStore(tmp_path)
    with store.lock("drain"):
        with pytest.raises(StoreError):
            with store.lock("drain"):
                pass


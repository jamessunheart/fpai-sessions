#!/usr/bin/env python3
"""Mock-based robustness tests for the provider-neutral observer.

No API key, no network, no real inbox — a scripted mock provider exercises
every failure mode. Safe to commit and run in CI. Synthetic addresses only
(example.invalid / mailsac.invalid), never a real public inbox.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shadow_adapter as sa
import provider_observer as po

INBOX = "REDACTED@mailsac.invalid"  # synthetic; real public address never committed


def _ev(mid, subj="synthetic test"):
    return {"message_id": mid, "date": "2026-07-10T18:00:00Z",
            "from": "synthetic@example.invalid", "to": "x@mailsac.invalid",
            "subject": subj, "thread_id": None}


class Mock:
    def __init__(self, ids, msgs, fail_list=None, fail_get=None):
        self.ids, self.msgs = ids, msgs
        self.fail_list, self.fail_get = fail_list, fail_get or {}

    def list_message_ids(self, inbox):
        if self.fail_list:
            raise self.fail_list
        return list(self.ids)

    def get_message(self, inbox, mid):
        if mid in self.fail_get:
            raise self.fail_get[mid]
        return self.msgs[mid]


def run(tmp: Path) -> None:
    store = tmp / "events.jsonl"

    m1 = Mock(["a"], {"a": _ev("<m-a@example.invalid>")})
    assert po.poll(m1, INBOX, store=store)["emitted"] == 1, "normal ingest"
    assert po.poll(m1, INBOX, store=store)["emitted"] == 0, "same msg re-poll dedups"

    m3 = Mock(["b", "b"], {"b": _ev("<m-b@example.invalid>")})
    r3 = po.poll(m3, INBOX, store=store)
    assert r3["listed"] == 2 and r3["emitted"] == 1, "dup-in-batch dedups"

    m4 = Mock(["c"], {"c": _ev("<m-c@example.invalid>")},
              fail_list=po.TransientProviderError("429"))
    assert po.poll(m4, INBOX, store=store).get("aborted") == 1, "transient-on-list aborts"
    m4.fail_list = None
    assert po.poll(m4, INBOX, store=store)["emitted"] == 1, "resumes after transient"

    m5 = Mock(["d"], {"d": {"subject": "no id"}})
    assert po.poll(m5, INBOX, store=store)["skipped"] == 1, "malformed payload skipped"

    m6 = Mock(["e"], {}, fail_get={"e": po.MessageVanished("gone")})
    assert po.poll(m6, INBOX, store=store)["skipped"] == 1, "vanished msg skipped"

    m7 = Mock(["f"], {"f": _ev("<m-f@example.invalid>")},
              fail_get={"f": po.TransientProviderError("429")})
    assert po.poll(m7, INBOX, store=store).get("aborted") == 1, "rate-limit-on-get aborts"

    (store.parent / ".disabled").touch()
    assert po.poll(m1, INBOX, store=store).get("disabled") == 1, "disable halts observation"
    (store.parent / ".disabled").unlink()

    ids = sorted(e["payload"]["message_id"] for e in sa.replay(store))
    assert ids == ["<m-a@example.invalid>", "<m-b@example.invalid>", "<m-c@example.invalid>"], ids
    print("ALL PROVIDER-OBSERVER ROBUSTNESS TESTS PASS:", ids)


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        run(Path(d))

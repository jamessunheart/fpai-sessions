#!/usr/bin/env python3
"""Conversation OS — remote provider observer (over-the-wire ingestion).

Provider-NEUTRAL by construction: the observer speaks a small Protocol
(list_message_ids / get_message) and maps provider payloads into the SAME
neutral msg dict shadow_adapter.normalize_email expects. No provider's field
names or quirks leak into the canonical Event model. Mailsac is ONE disposable
implementation (see MailsacProvider); it is a TEST adapter, never a production
channel recommendation.

Robustness contract (each independently tested):
  - poll same message twice        -> dedup (shadow_adapter dedup_key)
  - provider returns dup in a batch -> dedup within the poll
  - transient API failure / 429     -> abort batch cleanly, resumable, no partial corruption
  - malformed / incomplete payload  -> skip that message, keep going, emit nothing bad
  - message vanished before fetch   -> skip gracefully, no crash
Secrets: API key read from env MAILSAC_KEY (stored in ~/.config/fpai/credentials,
never committed/logged). The observer never prints addresses or bodies.
"""
from __future__ import annotations

import os
import urllib.error
import urllib.request
import json
from typing import Any, Protocol

from shadow_adapter import ingest, DEFAULT_STORE


class TransientProviderError(Exception):
    """API failure / rate-limit / timeout — abort batch, retry later. Not per-message."""


class MessageVanished(Exception):
    """Listed id no longer fetchable (retention/deletion) — skip this message."""


class MailProvider(Protocol):
    def list_message_ids(self, inbox: str) -> list[str]: ...
    def get_message(self, inbox: str, message_id: str) -> dict[str, Any]: ...


def _to_neutral(raw: dict[str, Any]) -> dict[str, Any]:
    """Provider-native payload -> neutral msg dict. Raises ValueError if unusable.

    Kept provider-neutral: expects already-normalized keys from the provider impl,
    so THIS function has no Mailsac knowledge. Provider impls do their own mapping.
    """
    if not isinstance(raw, dict):
        raise ValueError("payload not an object")
    message_id = raw.get("message_id")
    if not message_id:
        raise ValueError("missing message_id")  # incomplete payload -> skip
    return {
        "message_id": message_id,
        "date": raw.get("date"),
        "to": raw.get("to"),
        "from": raw.get("from"),
        "subject": raw.get("subject"),
        "thread_id": raw.get("thread_id"),
        "labels": ["inbound"],
    }


def poll(provider: MailProvider, inbox: str, *, source: str = "remote",
         tenant_id: str | None = "test", store=DEFAULT_STORE) -> dict[str, int]:
    """One resumable poll cycle. Per-message errors are isolated; transient
    errors abort the batch (resume next poll). Returns counts."""
    store_dir = store.parent
    if os.environ.get("CONVOS_OBSERVER_DISABLED") == "1" or (store_dir / ".disabled").exists():
        return {"listed": 0, "emitted": 0, "skipped": 0, "disabled": 1}
    try:
        ids = provider.list_message_ids(inbox)
    except TransientProviderError:
        return {"listed": 0, "emitted": 0, "skipped": 0, "aborted": 1}

    emitted = skipped = listed = 0
    seen_this_batch: set[str] = set()
    for mid in ids:
        listed += 1
        if mid in seen_this_batch:      # provider returned a dup within the batch
            continue
        seen_this_batch.add(mid)
        try:
            raw = provider.get_message(inbox, mid)
            msg = _to_neutral(raw)
        except TransientProviderError:
            return {"listed": listed, "emitted": emitted, "skipped": skipped, "aborted": 1}
        except (MessageVanished, ValueError):
            skipped += 1                # vanished OR malformed -> skip, keep going
            continue
        written, _ = ingest(msg, source=source, tenant_id=tenant_id, store=store)
        if written:
            emitted += 1
    return {"listed": listed, "emitted": emitted, "skipped": skipped, "disabled": 0}


class MailsacProvider:
    """Disposable TEST provider. All Mailsac-specific mapping lives HERE."""
    BASE = "https://mailsac.com/api"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("MAILSAC_KEY", "")

    def _get(self, path: str) -> Any:
        # UA header required — Mailsac 403s requests without a client UA.
        req = urllib.request.Request(
            self.BASE + path,
            headers={"Mailsac-Key": self.api_key, "User-Agent": "convos-observer/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                raise TransientProviderError(f"http {e.code}")
            if e.code == 404:
                raise MessageVanished(path)
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            raise TransientProviderError(str(e))

    def list_message_ids(self, inbox: str) -> list[str]:
        return [m["_id"] for m in self._get(f"/addresses/{inbox}/messages")]

    def get_message(self, inbox: str, message_id: str) -> dict[str, Any]:
        m = self._get(f"/addresses/{inbox}/messages/{message_id}")
        frm = (m.get("from") or [{}])[0].get("address")
        to = (m.get("to") or [{}])[0].get("address")
        return {  # -> neutral keys; no Mailsac field names escape this method
            "message_id": m.get("originalMessageId") or m.get("_id"),
            "date": m.get("received"),
            "from": frm, "to": to,
            "subject": m.get("subject"),
            "thread_id": (m.get("inReplyTo") or [None])[0] if m.get("inReplyTo") else None,
        }

#!/usr/bin/env python3
"""Conversation OS — live-inbox observer over a real Maildir (proof-1 path A).

Isolation model (satisfies "adapter failure cannot affect email delivery"):
  - DELIVERY  = an MTA writes RFC822 messages into a Maildir. Not our code.
  - OBSERVE   = this adapter polls the Maildir read-only and emits Events.
Two separate concerns. If the observer crashes, delivered mail is untouched
and is re-observed on the next poll. A cursor of processed message-ids gives
exactly-once emission across polls and delivery retries.

Real RFC822 is parsed (native Message-ID, References/thread, Date preserved).
No prod inbox, no creds, no network required — the Maildir IS the throwaway inbox.

Disable cleanly: set env CONVOS_OBSERVER_DISABLED=1 or create a `.disabled`
file in the store dir -> poll() observes nothing and emits nothing.
"""
from __future__ import annotations

import email
import email.utils
import mailbox
import os
from pathlib import Path
from typing import Any

from shadow_adapter import ingest, DEFAULT_STORE  # reuse canonical Event path


def _disabled(store_dir: Path) -> bool:
    return os.environ.get("CONVOS_OBSERVER_DISABLED") == "1" or (store_dir / ".disabled").exists()


def _msg_to_dict(msg: email.message.Message) -> dict[str, Any]:
    """RFC822 -> the neutral msg dict shadow_adapter.normalize_email expects."""
    date_hdr = msg.get("Date")
    occurred = None
    if date_hdr:
        try:
            occurred = email.utils.parsedate_to_datetime(date_hdr).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (TypeError, ValueError):
            occurred = date_hdr
    refs = msg.get("References") or msg.get("In-Reply-To")
    return {
        "message_id": (msg.get("Message-ID") or "").strip() or None,
        "date": occurred,
        "to": email.utils.parseaddr(msg.get("To", ""))[1] or None,
        "from": email.utils.parseaddr(msg.get("From", ""))[1] or None,
        "subject": msg.get("Subject"),
        "thread_id": (refs or "").split()[0].strip() if refs else None,
        "labels": ["inbound"],
    }


def poll(maildir_path: Path, *, source: str = "imap-test",
         tenant_id: str | None = "test", store: Path = DEFAULT_STORE) -> dict[str, int]:
    """One poll cycle. Read-only over the Maildir. Returns counts."""
    store_dir = store.parent
    if _disabled(store_dir):
        return {"observed": 0, "emitted": 0, "disabled": 1}
    box = mailbox.Maildir(str(maildir_path), create=True)
    observed = emitted = 0
    for key in box.iterkeys():
        observed += 1
        raw = box.get_bytes(key)
        msg = email.message_from_bytes(raw)
        written, _ = ingest(_msg_to_dict(msg), source=source, tenant_id=tenant_id, store=store)
        if written:
            emitted += 1
    return {"observed": observed, "emitted": emitted, "disabled": 0}

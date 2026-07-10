#!/usr/bin/env python3
"""Live over-the-wire trace via Mailsac (DISPOSABLE TEST ADAPTER — not a prod channel).

Preconditions:
  - MAILSAC_KEY in env (loaded from ~/.config/fpai/credentials/mailsac.env, gitignored).
Flow:
  generate unpredictable inbox -> (auto-send synthetic email via MX, or operator
  sends one) -> authenticated API poll -> canonical Event -> dedup on re-poll ->
  REDACTED trace to durable file -> delete test messages -> remind to rotate key.

Discipline (James 2026-07-10): public inbox, SYNTHETIC content only; no PII, links,
tokens, or attachments; never print/commit the key; redact address + body from
durable evidence; clean up after.
"""
from __future__ import annotations

import json
import os
import smtplib
import subprocess
import sys
import time
import uuid
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shadow_adapter as sa
import provider_observer as po

DURABLE = Path(__file__).resolve().parent / "live_trace_result.redacted.json"


def _redact_addr(addr: str) -> str:
    dom = addr.split("@", 1)[1] if "@" in addr else "?"
    return f"<redacted-8chars>@{dom}"


def _mx(domain: str) -> str | None:
    try:
        out = subprocess.run(["dig", "+short", "MX", domain], capture_output=True,
                             text=True, timeout=10).stdout.split()
        # lines like "5 in1.mailsac.com." -> take a host token
        hosts = [t.rstrip(".") for t in out if not t.replace(".", "").isdigit()]
        return hosts[0] if hosts else None
    except Exception:
        return None


def try_send(inbox: str) -> bool:
    """Best-effort synthetic send via direct-to-MX. Returns True if handed off."""
    mx = _mx("mailsac.com")
    if not mx:
        return False
    msg = EmailMessage()
    msg["From"] = "synthetic-sender@example.invalid"
    msg["To"] = inbox
    msg["Subject"] = "convos over-the-wire synthetic trace"
    msg["Message-ID"] = f"<convos-{uuid.uuid4().hex}@example.invalid>"
    msg.set_content("Synthetic non-sensitive test body. No PII. No links. No tokens.")
    try:
        with smtplib.SMTP(mx, 25, timeout=20) as s:
            s.send_message(msg)
        return True
    except Exception as e:
        print(f"[auto-send failed: {type(e).__name__}] — send one synthetic email manually",
              file=sys.stderr)
        return False


def main() -> int:
    key = os.environ.get("MAILSAC_KEY", "").strip()
    if not key:
        print("MAILSAC_KEY not set. Put it in ~/.config/fpai/credentials/mailsac.env "
              "(MAILSAC_KEY=...), source it, and re-run. Key is never committed/logged.",
              file=sys.stderr)
        return 2

    inbox = f"convos-{uuid.uuid4().hex[:16]}@mailsac.com"   # unpredictable
    print(f"[EPHEMERAL — do not store] test inbox: {inbox}", file=sys.stderr)
    provider = po.MailsacProvider(api_key=key)
    store = Path("/tmp") / f"convos_live_{uuid.uuid4().hex[:8]}" / "events.jsonl"

    handed_off = try_send(inbox)
    if not handed_off:
        print(f"Send a SYNTHETIC email to the address above from any external account, "
              f"then press Enter…", file=sys.stderr)
        try:
            input()
        except EOFError:
            pass

    # poll (bounded) until the message lands
    result = {}
    for attempt in range(20):
        result = po.poll(provider, inbox, source="mailsac", store=store)
        if result.get("emitted", 0) >= 1:
            break
        time.sleep(6)

    evs = sa.replay(store)
    if not evs:
        print("No Event captured within timeout.", file=sys.stderr)
        return 1

    # re-poll to prove dedup over the wire
    dedup = po.poll(provider, inbox, source="mailsac", store=store)

    ev = evs[0]
    redacted = {
        "event_id": ev["event_id"], "schema_version": ev["schema_version"],
        "source": ev["source"], "type": ev["type"],
        "occurred_at": ev["occurred_at"], "ingested_at": ev["ingested_at"],
        "trace_id": ev["trace_id"], "dedup_key_prefix": ev["dedup_key"][:12] + "…",
        "tenant_id": ev["tenant_id"],
        "payload_redacted": {
            "original_recipient": _redact_addr(ev["payload"]["original_recipient"] or "?@?"),
            "sender_identity": "example.invalid",
            "from": "<redacted>@example.invalid",
            "message_id": "<redacted-native-id>",
            "subject": "<redacted-synthetic-subject>",
            "thread_id": ev["payload"]["thread_id"],
        },
        "over_the_wire": True, "provider": "mailsac (disposable test adapter)",
        "dedup_on_repoll_emitted": dedup.get("emitted", None),  # expect 0
    }
    DURABLE.write_text(json.dumps(redacted, indent=2) + "\n")
    print(json.dumps(redacted, indent=2))

    # cleanup: delete test messages from the public inbox
    try:
        import urllib.request
        req = urllib.request.Request(
            f"https://mailsac.com/api/addresses/{inbox}/messages",
            headers={"Mailsac-Key": key}, method="DELETE")
        urllib.request.urlopen(req, timeout=15)
        print("[cleanup] deleted test messages from public inbox", file=sys.stderr)
    except Exception as e:
        print(f"[cleanup manual] delete messages for the inbox: {type(e).__name__}", file=sys.stderr)
    print("[reminder] rotate/delete the Mailsac API key now that the proof is done.",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

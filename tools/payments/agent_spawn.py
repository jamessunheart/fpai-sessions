#!/usr/bin/env python3
"""Spawn an agent namespace from a verified paid billing event.

The module does not call Stripe or any payment API. It accepts event payloads
from an already-configured billing webhook and writes idempotent namespace rows
only after the local live gates pass.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from tools.probe import rate_governor

try:
    from fastapi import FastAPI, Header, HTTPException, Request
except Exception:  # pragma: no cover - production dependency, tests use handlers directly.
    FastAPI = None  # type: ignore[assignment]
    Header = None  # type: ignore[assignment]
    HTTPException = Exception  # type: ignore[assignment]
    Request = Any  # type: ignore[assignment]


PAID_EVENT_TYPES = {
    "checkout.session.completed",
    "invoice.paid",
    "payment_intent.succeeded",
    "payment.succeeded",
}
EMAIL_RE = re.compile(r"[^<>,\s]+@[^<>,\s]+\.[^<>,\s]+")
SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class PaymentEvent:
    provider: str
    event_id: str
    event_type: str
    paid: bool
    amount_cents: int | None = None
    currency: str | None = None
    customer_email: str | None = None
    customer_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class SpawnResult:
    enabled: bool
    spawned: bool
    duplicate: bool
    namespace_id: str | None
    agent_id: str | None
    reason: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def connect_from_env() -> Any:
    return rate_governor.connect_from_env()


def normalize_email(value: str | None) -> str | None:
    match = EMAIL_RE.search(str(value or "").lower())
    return match.group(0) if match else None


def clean_provider(value: str | None) -> str:
    provider = SLUG_RE.sub("_", str(value or "stripe").strip().lower()).strip("_")
    return provider or "stripe"


def stable_slug(*parts: str | None, max_len: int = 48) -> str:
    source = "-".join(str(part or "") for part in parts if str(part or "").strip()) or "paid-member"
    slug = SLUG_RE.sub("-", source.strip().lower()).strip("-")
    return (slug or "paid-member")[:max_len].strip("-") or "paid-member"


def namespace_for_event(event: PaymentEvent) -> tuple[str, str]:
    owner = normalize_email(event.customer_email) or event.customer_id or event.event_id
    digest = hashlib.sha256(f"{event.provider}:{event.event_id}".encode("utf-8")).hexdigest()[:12]
    owner_slug = stable_slug(owner, max_len=36)
    namespace_id = f"agent_ns_{owner_slug}_{digest}"
    agent_id = f"agent_{digest}"
    return namespace_id, agent_id


def spawn_enabled(env: dict[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return values.get("PAYMENT_AGENT_SPAWN_ENABLED") == "1"


def webhook_secret(env: dict[str, str] | None = None) -> str:
    values = env if env is not None else os.environ
    return values.get("PAYMENT_AGENT_SPAWN_SECRET", "").strip()


def sign_body(body: bytes, *, secret: str, timestamp: str | None = None) -> str:
    stamp = timestamp or str(int(utc_now().timestamp()))
    digest = hmac.new(secret.encode("utf-8"), stamp.encode("utf-8") + b"." + body, hashlib.sha256).hexdigest()
    return f"t={stamp},v1={digest}"


def signature_valid(body: bytes, *, signature: str | None, secret: str) -> bool:
    if not secret or not signature:
        return False
    parts: dict[str, str] = {}
    for item in str(signature).split(","):
        if "=" in item:
            key, value = item.split("=", 1)
            parts[key.strip()] = value.strip()
    timestamp = parts.get("t")
    supplied = parts.get("v1")
    if not timestamp or not supplied:
        return False
    expected = sign_body(body, secret=secret, timestamp=timestamp).split("v1=", 1)[1]
    return hmac.compare_digest(supplied, expected)


def payment_event_from_payload(payload: dict[str, Any], *, provider: str = "stripe") -> PaymentEvent:
    event_type = str(payload.get("type") or payload.get("event_type") or "").strip()
    event_id = str(payload.get("id") or payload.get("event_id") or "").strip()
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    obj = data.get("object") if isinstance(data.get("object"), dict) else payload
    metadata = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else payload.get("metadata")
    paid = _paid_from_payload(event_type, obj, payload)
    email = (
        obj.get("customer_email")
        or _nested(obj, "customer_details", "email")
        or _nested(obj, "billing_details", "email")
        or payload.get("customer_email")
    )
    return PaymentEvent(
        provider=clean_provider(payload.get("provider") or provider),
        event_id=event_id,
        event_type=event_type,
        paid=paid,
        amount_cents=_int_or_none(obj.get("amount_total") or obj.get("amount_paid") or obj.get("amount") or payload.get("amount_cents")),
        currency=str(obj.get("currency") or payload.get("currency") or "").lower() or None,
        customer_email=normalize_email(str(email or "")),
        customer_id=str(obj.get("customer") or payload.get("customer_id") or "").strip() or None,
        metadata=metadata if isinstance(metadata, dict) else {},
    )


def _nested(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _paid_from_payload(event_type: str, obj: dict[str, Any], payload: dict[str, Any]) -> bool:
    if event_type not in PAID_EVENT_TYPES:
        return False
    if event_type == "checkout.session.completed":
        return obj.get("payment_status") == "paid" or payload.get("paid") is True
    if event_type == "invoice.paid":
        return obj.get("paid") is True or payload.get("paid") is True
    if event_type == "payment_intent.succeeded":
        return str(obj.get("status") or "") == "succeeded" or payload.get("paid") is True
    return bool(payload.get("paid", True))


def validate_payment_event(event: PaymentEvent) -> str | None:
    if not event.event_id:
        return "missing_event_id"
    if not event.event_type:
        return "missing_event_type"
    if event.event_type not in PAID_EVENT_TYPES:
        return "unsupported_event_type"
    if not event.paid:
        return "event_not_paid"
    if not (event.customer_email or event.customer_id):
        return "missing_customer_identity"
    return None


def ensure_tables(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS brain_index.payment_agent_spawns (
                id SERIAL PRIMARY KEY,
                provider TEXT NOT NULL,
                event_id TEXT NOT NULL UNIQUE,
                event_type TEXT NOT NULL,
                amount_cents INT,
                currency TEXT,
                customer_email TEXT,
                customer_id TEXT,
                namespace_id TEXT,
                agent_id TEXT,
                status TEXT NOT NULL DEFAULT 'spawned',
                metadata JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS brain_index.user_agents (
                id SERIAL PRIMARY KEY,
                agent_id TEXT NOT NULL UNIQUE,
                namespace_id TEXT NOT NULL UNIQUE,
                owner_email TEXT,
                owner_external_id TEXT,
                source_provider TEXT NOT NULL,
                source_event_id TEXT NOT NULL UNIQUE,
                access_level TEXT NOT NULL DEFAULT 'paid_member',
                status TEXT NOT NULL DEFAULT 'active',
                passport JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )


def existing_spawn(conn: Any, event_id: str) -> tuple[str | None, str | None] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT namespace_id, agent_id
              FROM brain_index.payment_agent_spawns
             WHERE event_id = %s
             LIMIT 1
            """,
            (event_id,),
        )
        row = cur.fetchone() if hasattr(cur, "fetchone") else None
    return (row[0], row[1]) if row else None


def write_spawn(conn: Any, event: PaymentEvent, *, now: datetime | None = None) -> tuple[str, str]:
    namespace_id, agent_id = namespace_for_event(event)
    current = now or utc_now()
    passport = {
        "agent_id": agent_id,
        "namespace_id": namespace_id,
        "created_from": "payment_event",
        "source_provider": event.provider,
        "source_event_id": event.event_id,
        "access_level": "paid_member",
        "customer_email": event.customer_email,
        "customer_id": event.customer_id,
    }
    metadata = event.metadata or {}
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO brain_index.user_agents
                (agent_id, namespace_id, owner_email, owner_external_id, source_provider,
                 source_event_id, access_level, status, passport, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'paid_member', 'active', %s, %s, %s)
            ON CONFLICT (source_event_id) DO NOTHING
            """,
            (
                agent_id,
                namespace_id,
                event.customer_email,
                event.customer_id,
                event.provider,
                event.event_id,
                json.dumps(passport, sort_keys=True),
                current,
                current,
            ),
        )
        cur.execute(
            """
            INSERT INTO brain_index.payment_agent_spawns
                (provider, event_id, event_type, amount_cents, currency, customer_email,
                 customer_id, namespace_id, agent_id, status, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'spawned', %s, %s)
            ON CONFLICT (event_id) DO NOTHING
            """,
            (
                event.provider,
                event.event_id,
                event.event_type,
                event.amount_cents,
                event.currency,
                event.customer_email,
                event.customer_id,
                namespace_id,
                agent_id,
                json.dumps(metadata, sort_keys=True),
                current,
            ),
        )
    return namespace_id, agent_id


def spawn_agent_namespace(
    event: PaymentEvent,
    *,
    conn: Any | None = None,
    connector: Callable[[], Any] = connect_from_env,
    env: dict[str, str] | None = None,
    now: datetime | None = None,
) -> SpawnResult:
    if not spawn_enabled(env):
        return SpawnResult(False, False, False, None, None, "spawn_disabled")
    invalid = validate_payment_event(event)
    if invalid:
        return SpawnResult(True, False, False, None, None, invalid)
    own_conn = conn is None
    try:
        db = conn or connector()
    except Exception:
        return SpawnResult(True, False, False, None, None, "db_unavailable")
    try:
        ensure_tables(db)
        existing = existing_spawn(db, event.event_id)
        if existing:
            return SpawnResult(True, False, True, existing[0], existing[1], "already_spawned")
        namespace_id, agent_id = write_spawn(db, event, now=now)
        return SpawnResult(True, True, False, namespace_id, agent_id, "spawned")
    finally:
        if own_conn and hasattr(db, "close"):
            db.close()


def handle_webhook_payload(
    body: bytes,
    *,
    signature: str | None = None,
    conn: Any | None = None,
    connector: Callable[[], Any] = connect_from_env,
    env: dict[str, str] | None = None,
    now: datetime | None = None,
) -> SpawnResult:
    values = env if env is not None else os.environ
    if not spawn_enabled(values):
        return SpawnResult(False, False, False, None, None, "spawn_disabled")
    secret = webhook_secret(values)
    if not signature_valid(body, signature=signature, secret=secret):
        return SpawnResult(True, False, False, None, None, "invalid_signature")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return SpawnResult(True, False, False, None, None, "invalid_json")
    event = payment_event_from_payload(payload)
    return spawn_agent_namespace(event, conn=conn, connector=connector, env=values, now=now)


def result_to_dict(result: SpawnResult) -> dict[str, Any]:
    return asdict(result)


app = FastAPI(title="FPAI Payment Agent Spawn Webhook") if FastAPI is not None else None

if app is not None:

    @app.post("/payments/agent-spawn")
    async def payment_agent_spawn(
        request: Request,
        x_fpai_payment_signature: str | None = Header(default=None, alias="X-FPAI-Payment-Signature"),
    ) -> dict[str, Any]:
        body = await request.body()
        result = handle_webhook_payload(body, signature=x_fpai_payment_signature)
        if result.reason == "spawn_disabled":
            raise HTTPException(status_code=403, detail="payment agent spawn disabled")
        if result.reason == "invalid_signature":
            raise HTTPException(status_code=401, detail="invalid payment signature")
        if result.reason in {"invalid_json", "missing_event_id", "missing_event_type"}:
            raise HTTPException(status_code=400, detail=result.reason)
        if result.reason == "db_unavailable":
            raise HTTPException(status_code=503, detail="database unavailable")
        return result_to_dict(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Spawn an agent namespace from a paid payment event JSON file.")
    parser.add_argument("event_json", help="Path to a billing webhook event JSON file, or '-' for stdin.")
    args = parser.parse_args(argv)
    if args.event_json == "-":
        import sys

        body = sys.stdin.buffer.read()
    else:
        with open(args.event_json, "rb") as fh:
            body = fh.read()
    payload = json.loads(body.decode("utf-8"))
    result = spawn_agent_namespace(payment_event_from_payload(payload))
    print(json.dumps(result_to_dict(result), sort_keys=True))
    return 0 if result.spawned or result.duplicate or not result.enabled else 1


if __name__ == "__main__":
    raise SystemExit(main())

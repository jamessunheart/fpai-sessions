"""Stripe subscription billing for Sunheart Brain.

The Stripe SDK is imported lazily so the rest of the curator can run in
environments where billing is disabled or dependencies are not installed.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

log = logging.getLogger("curator.billing.stripe")

PRICE_BASIC = os.environ.get("STRIPE_PRICE_BASIC_ID", "")
PRICE_PRO = os.environ.get("STRIPE_PRICE_PRO_ID", "")

TIER_FREE = "free"
TIER_BASIC = "basic"
TIER_PRO = "pro"
TIERS = {TIER_FREE, TIER_BASIC, TIER_PRO}
PAID_TIERS = {TIER_BASIC, TIER_PRO}
TIER_ORDER = {TIER_FREE: 0, TIER_BASIC: 1, TIER_PRO: 2}

TIER_LIMITS = {
    TIER_FREE: 10,
    TIER_BASIC: 100,
    TIER_PRO: None,
}

TIER_CAPABILITIES = {
    TIER_FREE: {"search_web"},
    TIER_BASIC: {"search_web", "email", "calendar"},
    TIER_PRO: {"search_web", "email", "calendar", "priority_routing", "all"},
}

CORA_AWARDS = {
    TIER_BASIC: 100,
    TIER_PRO: 500,
}

PRICE_BY_TIER = {
    TIER_BASIC: lambda: os.environ.get("STRIPE_PRICE_BASIC_ID", PRICE_BASIC),
    TIER_PRO: lambda: os.environ.get("STRIPE_PRICE_PRO_ID", PRICE_PRO),
}


class BillingError(RuntimeError):
    """Raised when a billing operation cannot be completed safely."""


class WebhookVerificationError(BillingError):
    """Raised before any DB write when Stripe signature verification fails."""


@dataclass(frozen=True)
class TierView:
    tier: str
    status: str
    daily_messages: int | None
    capabilities: tuple[str, ...]


def stripe_disabled() -> bool:
    return os.environ.get("STRIPE_DISABLE", "").strip().lower() in {"1", "true", "yes", "on"}


def normalize_tier(tier: str | None) -> str:
    value = (tier or TIER_FREE).strip().lower()
    if value not in TIERS:
        raise BillingError(f"unknown tier: {tier}")
    return value


def effective_tier(tier: str | None) -> str:
    if stripe_disabled():
        return TIER_BASIC
    return normalize_tier(tier)


def tier_view(tier: str | None, status: str | None = None) -> TierView:
    resolved = effective_tier(tier)
    return TierView(
        tier=resolved,
        status=status or ("testing_basic" if stripe_disabled() else resolved),
        daily_messages=TIER_LIMITS[resolved],
        capabilities=tuple(sorted(TIER_CAPABILITIES[resolved])),
    )


def can_use_capability(tier: str | None, capability: str) -> bool:
    caps = TIER_CAPABILITIES[effective_tier(tier)]
    return "all" in caps or capability in caps


def message_limit_for_tier(tier: str | None) -> int | None:
    return TIER_LIMITS[effective_tier(tier)]


def upgrade_prompt_for_limit() -> str:
    return (
        "You've used your 10 free messages today. Basic ($9/mo) gives you "
        "100/day + email + calendar. [Upgrade] or come back tomorrow."
    )


def upgrade_prompt_for_capability(capability: str) -> str:
    return (
        f"{capability} needs Basic or Pro. You're on Free. "
        "[Upgrade to Basic - $9/mo] or [See what Basic unlocks]."
    )


def _stripe() -> Any:
    try:
        import stripe  # type: ignore
    except Exception as exc:
        raise BillingError("stripe package is not installed") from exc
    api_key = os.environ.get("STRIPE_SECRET_KEY")
    if api_key:
        stripe.api_key = api_key
    return stripe


def _connect() -> Any:
    try:
        import psycopg  # type: ignore
    except Exception as exc:
        raise BillingError("psycopg package is not installed") from exc
    db_url = os.environ.get(
        "BRAIN_INDEX_DB_URL",
        "postgres://brain_index:changeme@127.0.0.1:25432/appflowy",
    )
    return psycopg.connect(db_url, autocommit=True)


_connect_factory: Callable[[], Any] = _connect
_stripe_factory: Callable[[], Any] = _stripe


def configure_for_tests(*, connect_factory: Callable[[], Any] | None = None, stripe_client: Any | None = None) -> None:
    """Inject fakes for focused unit tests."""
    global _connect_factory, _stripe_factory
    _connect_factory = connect_factory or _connect
    _stripe_factory = (lambda: stripe_client) if stripe_client is not None else _stripe


def _get(data: Any, *path: str, default: Any = None) -> Any:
    cur = data
    for key in path:
        if cur is None:
            return default
        if isinstance(cur, dict):
            cur = cur.get(key)
        else:
            cur = getattr(cur, key, None)
    return default if cur is None else cur


def _metadata(data: Any) -> dict[str, Any]:
    meta = _get(data, "metadata", default={})
    return meta if isinstance(meta, dict) else {}


def _tier_from_price_id(price_id: str | None) -> str | None:
    if price_id and price_id == os.environ.get("STRIPE_PRICE_BASIC_ID", PRICE_BASIC):
        return TIER_BASIC
    if price_id and price_id == os.environ.get("STRIPE_PRICE_PRO_ID", PRICE_PRO):
        return TIER_PRO
    return None


def _tier_from_subscription(obj: Any) -> str:
    meta_tier = _metadata(obj).get("tier")
    if meta_tier:
        return normalize_tier(str(meta_tier))
    price_id = _get(obj, "items", "data", default=[])
    if isinstance(price_id, list) and price_id:
        price_id = _get(price_id[0], "price", "id")
    else:
        price_id = _get(obj, "plan", "id")
    return _tier_from_price_id(str(price_id) if price_id else None) or TIER_FREE


def _execute(conn: Any, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        if cur.description:
            return list(cur.fetchall())
    return []


def _get_user(conn: Any, user_id: str) -> dict[str, Any] | None:
    rows = _execute(
        conn,
        """
        SELECT user_id, tier, subscription_status, stripe_customer_id,
               stripe_subscription_id, cora_balance, beacon_id,
               subscription_grace_until
          FROM brain_index.user_agents
         WHERE user_id = %s
        """,
        (user_id,),
    )
    if not rows:
        return None
    row = rows[0]
    return {
        "user_id": row[0],
        "tier": row[1],
        "subscription_status": row[2],
        "stripe_customer_id": row[3],
        "stripe_subscription_id": row[4],
        "cora_balance": row[5] or 0,
        "beacon_id": row[6],
        "subscription_grace_until": row[7],
    }


def _find_user_by_customer(conn: Any, customer_id: str | None) -> str | None:
    if not customer_id:
        return None
    rows = _execute(
        conn,
        "SELECT user_id FROM brain_index.user_agents WHERE stripe_customer_id = %s LIMIT 1",
        (customer_id,),
    )
    return str(rows[0][0]) if rows else None


def _upsert_user(
    conn: Any,
    *,
    user_id: str,
    tier: str,
    status: str,
    customer_id: str | None = None,
    subscription_id: str | None = None,
    grace_until: datetime | None = None,
) -> None:
    _execute(
        conn,
        """
        INSERT INTO brain_index.user_agents
            (user_id, tier, subscription_status, stripe_customer_id,
             stripe_subscription_id, subscription_grace_until, updated_at)
        VALUES
            (%s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (user_id) DO UPDATE SET
            tier = EXCLUDED.tier,
            subscription_status = EXCLUDED.subscription_status,
            stripe_customer_id = COALESCE(EXCLUDED.stripe_customer_id, user_agents.stripe_customer_id),
            stripe_subscription_id = COALESCE(EXCLUDED.stripe_subscription_id, user_agents.stripe_subscription_id),
            subscription_grace_until = EXCLUDED.subscription_grace_until,
            updated_at = NOW()
        """,
        (user_id, tier, status, customer_id, subscription_id, grace_until),
    )


def _award_cora(conn: Any, *, user_id: str, amount: int) -> None:
    if amount <= 0:
        return
    _execute(
        conn,
        """
        UPDATE brain_index.user_agents
           SET cora_balance = COALESCE(cora_balance, 0) + %s,
               updated_at = NOW()
         WHERE user_id = %s
        """,
        (amount, user_id),
    )


def _log_event(conn: Any, *, event_type: str, user_id: str | None, tier: str | None, customer_id: str | None, meta: dict[str, Any] | None = None) -> None:
    safe_meta = dict(meta or {})
    for forbidden in ("card", "payment_method_details", "number", "cvc"):
        safe_meta.pop(forbidden, None)
    _execute(
        conn,
        """
        INSERT INTO brain_index.ops_ledger (event, type, user_id, tier, stripe_customer_id, meta)
        VALUES ('stripe_webhook', %s, %s, %s, %s, %s::jsonb)
        """,
        (event_type, user_id, tier, customer_id, json.dumps(safe_meta, sort_keys=True)),
    )


def _record_beacon_event(beacon_id: str | None) -> None:
    if not beacon_id:
        return
    try:
        from tools.beacon.events import record_event  # type: ignore
    except Exception:
        return
    try:
        record_event(beacon_id, "paid_conversion")
    except Exception as exc:
        log.warning("beacon paid_conversion failed beacon=%s: %s", beacon_id, exc)


def _notify_subscription(user_id: str, tier: str, amount: int) -> None:
    if amount <= 0:
        return
    text = f"Welcome to {tier.capitalize()} — you earned {amount} CORA."
    try:
        from curator import telegram as tg
        asyncio.run(tg.send(text, chat_id=user_id))
    except RuntimeError:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(tg.send(text, chat_id=user_id))  # type: ignore[name-defined]
        except Exception:
            pass
    except Exception as exc:
        log.warning("subscription notification failed: %s", exc)


def _notify_payment_failed(user_id: str | None) -> None:
    try:
        from curator import telegram as tg
        msg = "Your subscription payment needs attention. Use /billing to update your card."
        if user_id:
            msg = "Your subscription payment needs attention. Use /billing to update your card."
        asyncio.run(tg.send(msg, chat_id=user_id))
    except RuntimeError:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(tg.send(msg, chat_id=user_id))  # type: ignore[name-defined]
        except Exception:
            pass
    except Exception as exc:
        log.warning("payment failure notification failed: %s", exc)


def create_checkout_session(user_id: str, tier: str = TIER_BASIC) -> str:
    tier = normalize_tier(tier)
    if tier not in PAID_TIERS:
        tier = TIER_BASIC
    if stripe_disabled():
        return f"https://billing.disabled.local/checkout/{tier}?user_id={user_id}"
    with _connect_factory() as conn:
        user = _get_user(conn, str(user_id))
    if user and user.get("stripe_customer_id") and user.get("subscription_status") in {"active", "trialing", "past_due"}:
        return get_portal_url(user_id)
    price_id = PRICE_BY_TIER[tier]()
    if not price_id:
        raise BillingError(f"missing Stripe price id for tier {tier}")
    stripe = _stripe_factory()
    success_url = os.environ.get("STRIPE_SUCCESS_URL", "https://brain.sunheart.com/billing/success")
    cancel_url = os.environ.get("STRIPE_CANCEL_URL", "https://brain.sunheart.com/billing/cancel")
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        metadata={"user_id": str(user_id), "tier": tier},
        client_reference_id=str(user_id),
        success_url=success_url,
        cancel_url=cancel_url,
    )
    url = _get(session, "url")
    if not url:
        raise BillingError("Stripe did not return a checkout URL")
    return str(url)


def upgrade_reply(user_id: str, tier: str = TIER_BASIC) -> str:
    requested = tier if tier in PAID_TIERS else TIER_BASIC
    url = create_checkout_session(user_id, requested)
    label = "Basic" if requested == TIER_BASIC else "Pro"
    return (
        f"{label} is open here: {url}\n"
        "Free stays useful. Upgrade only when the extra capacity helps."
    )


def get_portal_url(user_id: str) -> str:
    if stripe_disabled():
        return "https://billing.disabled.local/portal"
    with _connect_factory() as conn:
        user = _get_user(conn, str(user_id))
    customer_id = user.get("stripe_customer_id") if user else None
    if not customer_id:
        raise BillingError("No Stripe customer is linked to this user yet.")
    stripe = _stripe_factory()
    return_url = os.environ.get("STRIPE_PORTAL_RETURN_URL", "https://brain.sunheart.com")
    session = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    url = _get(session, "url")
    if not url:
        raise BillingError("Stripe did not return a portal URL")
    return str(url)


def get_user_tier(user_id: str) -> TierView:
    if stripe_disabled():
        return tier_view(TIER_BASIC, "testing_basic")
    with _connect_factory() as conn:
        user = _get_user(conn, str(user_id))
    if not user:
        return tier_view(TIER_FREE, "free")
    grace_until = user.get("subscription_grace_until")
    if user.get("subscription_status") == "cancelled":
        try:
            if grace_until and grace_until > datetime.now(timezone.utc):
                return tier_view(user.get("tier"), "cancelled_grace")
        except TypeError:
            pass
        return tier_view(TIER_FREE, "cancelled")
    return tier_view(user.get("tier"), user.get("subscription_status"))


def handle_webhook(payload: bytes, sig: str) -> None:
    stripe = _stripe_factory()
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not secret:
        raise WebhookVerificationError("STRIPE_WEBHOOK_SECRET is not configured")
    try:
        event = stripe.Webhook.construct_event(payload, sig, secret)
    except Exception as exc:
        raise WebhookVerificationError("invalid Stripe webhook signature") from exc

    event_type = str(_get(event, "type", default=""))
    obj = _get(event, "data", "object", default={})
    with _connect_factory() as conn:
        if event_type == "checkout.session.completed":
            _handle_checkout_completed(conn, event_type, obj)
        elif event_type == "customer.subscription.updated":
            _handle_subscription_updated(conn, event_type, obj)
        elif event_type == "customer.subscription.deleted":
            _handle_subscription_deleted(conn, event_type, obj)
        elif event_type == "invoice.payment_failed":
            _handle_invoice_payment_failed(conn, event_type, obj)
        else:
            _log_event(conn, event_type=event_type, user_id=None, tier=None, customer_id=None, meta={"ignored": True})


def _handle_checkout_completed(conn: Any, event_type: str, session: Any) -> None:
    meta = _metadata(session)
    user_id = str(meta.get("user_id") or _get(session, "client_reference_id") or "").strip()
    if not user_id:
        raise BillingError("checkout.session.completed missing user_id metadata")
    tier = normalize_tier(str(meta.get("tier") or TIER_BASIC))
    customer_id = str(_get(session, "customer", default="") or "")
    subscription_id = str(_get(session, "subscription", default="") or "")
    before = _get_user(conn, user_id)
    _upsert_user(
        conn,
        user_id=user_id,
        tier=tier,
        status="active",
        customer_id=customer_id or None,
        subscription_id=subscription_id or None,
    )
    award = CORA_AWARDS.get(tier, 0)
    already_awarded = (
        before
        and before.get("subscription_status") == "active"
        and before.get("stripe_subscription_id") == subscription_id
        and before.get("tier") == tier
    )
    if award and not already_awarded:
        _award_cora(conn, user_id=user_id, amount=award)
        _notify_subscription(user_id, tier, award)
        _record_beacon_event(before.get("beacon_id") if before else None)
    _log_event(
        conn,
        event_type=event_type,
        user_id=user_id,
        tier=tier,
        customer_id=customer_id or None,
        meta={"subscription_id": subscription_id or None},
    )


def _handle_subscription_updated(conn: Any, event_type: str, subscription: Any) -> None:
    customer_id = str(_get(subscription, "customer", default="") or "")
    user_id = str(_metadata(subscription).get("user_id") or _find_user_by_customer(conn, customer_id) or "").strip()
    tier = _tier_from_subscription(subscription)
    status = str(_get(subscription, "status", default="active") or "active")
    subscription_id = str(_get(subscription, "id", default="") or "")
    if user_id:
        _upsert_user(
            conn,
            user_id=user_id,
            tier=tier,
            status=status,
            customer_id=customer_id or None,
            subscription_id=subscription_id or None,
        )
    _log_event(conn, event_type=event_type, user_id=user_id or None, tier=tier, customer_id=customer_id or None, meta={"status": status})


def _handle_subscription_deleted(conn: Any, event_type: str, subscription: Any) -> None:
    customer_id = str(_get(subscription, "customer", default="") or "")
    user_id = str(_metadata(subscription).get("user_id") or _find_user_by_customer(conn, customer_id) or "").strip()
    subscription_id = str(_get(subscription, "id", default="") or "")
    grace_days = int(os.environ.get("STRIPE_CANCEL_GRACE_DAYS", "0") or "0")
    grace_until = datetime.now(timezone.utc) + timedelta(days=max(grace_days, 0))
    current = _get_user(conn, user_id) if user_id else None
    retained_tier = current.get("tier") if current and grace_days > 0 else TIER_FREE
    if user_id:
        _upsert_user(
            conn,
            user_id=user_id,
            tier=retained_tier or TIER_FREE,
            status="cancelled",
            customer_id=customer_id or None,
            subscription_id=subscription_id or None,
            grace_until=grace_until,
        )
    _log_event(
        conn,
        event_type=event_type,
        user_id=user_id or None,
        tier=retained_tier or TIER_FREE,
        customer_id=customer_id or None,
        meta={"subscription_id": subscription_id or None, "grace_until": grace_until.isoformat()},
    )


def _handle_invoice_payment_failed(conn: Any, event_type: str, invoice: Any) -> None:
    customer_id = str(_get(invoice, "customer", default="") or "")
    user_id = str(_metadata(invoice).get("user_id") or _find_user_by_customer(conn, customer_id) or "").strip()
    tier = None
    if user_id:
        current = _get_user(conn, user_id)
        tier = current.get("tier") if current else None
        _upsert_user(
            conn,
            user_id=user_id,
            tier=tier or TIER_FREE,
            status="past_due",
            customer_id=customer_id or None,
            subscription_id=str(_get(invoice, "subscription", default="") or "") or None,
        )
    _notify_payment_failed(user_id or None)
    _log_event(conn, event_type=event_type, user_id=user_id or None, tier=tier, customer_id=customer_id or None, meta={"invoice_id": _get(invoice, "id")})

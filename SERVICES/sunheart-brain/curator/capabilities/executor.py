"""Consent-gated live capability executor."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

try:
    import psycopg
    from psycopg.types.json import Jsonb
except Exception:  # pragma: no cover - psycopg exists in service env.
    psycopg = None  # type: ignore
    Jsonb = None  # type: ignore

from .book_calendar import book_calendar as live_book_calendar
from .book_calendar import cancel_event as live_cancel_event
from .send_email import send_email as live_send_email
from .send_email import validate_email_address
from .web_search import search_web as live_search_web


class PermissionDenied(Exception):
    """Raised when the user agent is not granted a capability."""


class CapabilityValidationError(ValueError):
    """Raised when capability params are missing or malformed."""


@dataclass
class CapabilityResult:
    success: bool
    output: Any
    action_taken: bool
    reversible: bool
    audit_id: int | str | None


Provider = Callable[[dict], Awaitable[dict]]


CAPABILITY_SCHEMAS: dict[str, dict[str, Any]] = {
    "search_web": {
        "required": {"query": str},
        "reversible": False,
        "requires_confirmation": True,
    },
    "send_email": {
        "required": {"to": str, "subject": str, "body": str},
        "reversible": False,
        "requires_confirmation": True,
        "requires_consent": True,
    },
    "book_calendar": {
        "required": {"title": str, "date": str, "time": str, "duration": int},
        "reversible": True,
        "requires_confirmation": True,
        "requires_calendar": True,
    },
    "travel_booking": {
        "required": {},
        "reversible": False,
        "stub": True,
    },
}


class CapabilityAuditStore:
    async def log(
        self,
        *,
        user_id: str,
        capability: str,
        params: dict,
        result: dict,
        success: bool,
        reversible: bool,
    ) -> int | str | None:
        from ..db import connect

        json_params = Jsonb(params) if Jsonb else params
        json_result = Jsonb(result) if Jsonb else result
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO brain_index.capability_log
                        (user_id, capability, params, result, success, reversible)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (user_id, capability, json_params, json_result, success, reversible),
                )
                row = await cur.fetchone()
                return row[0] if row else None

    async def has_email_consent(self, user_id: str) -> bool:
        from ..db import connect

        try:
            async with connect() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT 1
                          FROM brain_index.consent_log
                         WHERE user_id = %s
                           AND consent_type IN ('send_email', 'email_capability', 'capability:send_email')
                           AND COALESCE(revoked, false) = false
                         ORDER BY granted_at DESC NULLS LAST
                         LIMIT 1
                        """,
                        (user_id,),
                    )
                    return await cur.fetchone() is not None
        except Exception as exc:
            if _is_missing_table_or_column(exc):
                return False
            raise

    async def has_calendar_connection(self, user_id: str) -> bool:
        from ..db import connect

        try:
            async with connect() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT 1
                          FROM brain_index.connected_services
                         WHERE user_id = %s
                           AND calendar_provider IS NOT NULL
                           AND COALESCE(disabled, false) = false
                         LIMIT 1
                        """,
                        (user_id,),
                    )
                    return await cur.fetchone() is not None
        except Exception as exc:
            if _is_missing_table_or_column(exc):
                return False
            raise

    async def last_reversible_actions(self, user_id: str, *, limit: int = 3) -> list[dict]:
        from ..db import connect

        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id, capability, params, result, executed_at
                      FROM brain_index.capability_log
                     WHERE user_id = %s
                       AND reversible = true
                       AND success = true
                       AND reversed_at IS NULL
                     ORDER BY executed_at DESC
                     LIMIT %s
                    """,
                    (user_id, limit),
                )
                rows = await cur.fetchall()
        return [
            {
                "id": row[0],
                "capability": row[1],
                "params": row[2] or {},
                "result": row[3] or {},
                "executed_at": row[4],
            }
            for row in rows
        ]

    async def get_action(self, audit_id: int | str, user_id: str | None = None) -> dict | None:
        from ..db import connect

        where_user = "AND user_id = %s" if user_id is not None else ""
        values: tuple[Any, ...] = (audit_id, user_id) if user_id is not None else (audit_id,)
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"""
                    SELECT id, user_id, capability, params, result, success, reversible, reversed_at
                      FROM brain_index.capability_log
                     WHERE id = %s {where_user}
                     LIMIT 1
                    """,
                    values,
                )
                row = await cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "user_id": row[1],
            "capability": row[2],
            "params": row[3] or {},
            "result": row[4] or {},
            "success": row[5],
            "reversible": row[6],
            "reversed_at": row[7],
        }

    async def mark_reversed(self, audit_id: int | str, result: dict) -> None:
        from ..db import connect

        json_result = Jsonb(result) if Jsonb else result
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE brain_index.capability_log
                       SET reversed_at = now(),
                           result = COALESCE(result, '{}'::jsonb) || %s::jsonb
                     WHERE id = %s
                    """,
                    (json_result, audit_id),
                )


async def execute_capability(
    user_agent: Any,
    capability: str,
    params: dict,
    *,
    store: CapabilityAuditStore | None = None,
    providers: dict[str, Provider] | None = None,
) -> CapabilityResult:
    """Execute a granted capability and append an audit row."""
    store = store or CapabilityAuditStore()
    providers = providers or {}
    params = dict(params or {})
    user_id = _user_id(user_agent)

    if os.environ.get("CAPABILITIES_DISABLE", "").strip().lower() in {"1", "true", "yes"}:
        return CapabilityResult(
            success=False,
            output="Capabilities are currently offline.",
            action_taken=False,
            reversible=False,
            audit_id=None,
        )

    if not _can(user_agent, capability):
        raise PermissionDenied(f"user_agent cannot execute {capability}")

    schema = CAPABILITY_SCHEMAS.get(capability)
    if not schema:
        raise CapabilityValidationError(f"unknown capability: {capability}")
    if schema.get("stub"):
        result = {"status": "stub", "message": "Travel booking execution is deferred to d043."}
        audit_id = await store.log(
            user_id=user_id,
            capability=capability,
            params=params,
            result=result,
            success=False,
            reversible=False,
        )
        return CapabilityResult(False, result["message"], False, False, audit_id)

    _validate_params(capability, params)
    reversible = bool(schema.get("reversible"))

    if schema.get("requires_confirmation") and not _confirmed(params):
        result = {"status": "cancelled", "reason": "confirmation_required"}
        audit_id = await store.log(
            user_id=user_id,
            capability=capability,
            params=_redact_params(capability, params),
            result=result,
            success=False,
            reversible=reversible,
        )
        return CapabilityResult(False, result["reason"], False, reversible, audit_id)

    if schema.get("requires_consent") and not await store.has_email_consent(user_id):
        result = {"status": "blocked", "reason": "send_email consent is required"}
        audit_id = await store.log(
            user_id=user_id,
            capability=capability,
            params=_redact_params(capability, params),
            result=result,
            success=False,
            reversible=reversible,
        )
        return CapabilityResult(False, result["reason"], False, reversible, audit_id)

    if schema.get("requires_calendar") and not await store.has_calendar_connection(user_id):
        result = {"status": "blocked", "reason": "connected calendar is required"}
        audit_id = await store.log(
            user_id=user_id,
            capability=capability,
            params=_redact_params(capability, params),
            result=result,
            success=False,
            reversible=reversible,
        )
        return CapabilityResult(False, result["reason"], False, reversible, audit_id)

    provider = providers.get(capability) or _default_provider(capability)
    try:
        result = await provider(params)
        success = bool(result.get("success", True))
    except Exception as exc:
        result = {"status": "error", "error": str(exc)}
        success = False

    audit_id = await store.log(
        user_id=user_id,
        capability=capability,
        params=_redact_params(capability, params),
        result=result,
        success=success,
        reversible=reversible and success,
    )
    return CapabilityResult(
        success=success,
        output=_format_output(capability, result),
        action_taken=success,
        reversible=reversible and success,
        audit_id=audit_id,
    )


async def reverse_capability_action(
    audit_id: int | str,
    *,
    user_id: str | None = None,
    store: CapabilityAuditStore | None = None,
    cancel_provider: Callable[[str], Awaitable[dict]] | None = None,
) -> CapabilityResult:
    store = store or CapabilityAuditStore()
    action = await store.get_action(audit_id, user_id=user_id)
    if not action:
        return CapabilityResult(False, "I could not find that action.", False, False, audit_id)
    if not action["reversible"] or action["capability"] != "book_calendar":
        return CapabilityResult(
            False,
            "That action cannot be reversed.",
            False,
            False,
            audit_id,
        )
    if action.get("reversed_at"):
        return CapabilityResult(False, "That action was already reversed.", False, True, audit_id)

    result = action.get("result") or {}
    event_id = str(result.get("event_id") or "").strip()
    if not event_id:
        return CapabilityResult(False, "The calendar event id is missing.", False, True, audit_id)
    cancel = cancel_provider or live_cancel_event
    try:
        cancel_result = await cancel(event_id)
    except Exception as exc:
        return CapabilityResult(False, f"Calendar reversal failed: {exc}", False, True, audit_id)
    await store.mark_reversed(audit_id, {"reversal": cancel_result})
    return CapabilityResult(True, "Calendar event cancelled.", True, True, audit_id)


def _default_provider(capability: str) -> Provider:
    if capability == "search_web":
        async def _search(params: dict) -> dict:
            return {"results": await live_search_web(str(params["query"]))}
        return _search
    if capability == "send_email":
        return live_send_email
    if capability == "book_calendar":
        return live_book_calendar
    raise CapabilityValidationError(f"unknown capability: {capability}")


def _can(user_agent: Any, capability: str) -> bool:
    checker = getattr(user_agent, "can", None)
    return bool(checker and checker(capability))


def _user_id(user_agent: Any) -> str:
    return str(
        getattr(user_agent, "user_id", None)
        or getattr(user_agent, "id", None)
        or getattr(user_agent, "chat_id", None)
        or "unknown"
    )


def _confirmed(params: dict) -> bool:
    value = params.get("confirmed")
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"yes", "y", "true", "1", "confirmed"}


def _validate_params(capability: str, params: dict) -> None:
    required = CAPABILITY_SCHEMAS[capability]["required"]
    for key, typ in required.items():
        if key not in params or params[key] in (None, ""):
            raise CapabilityValidationError(f"{key} is required for {capability}")
        if typ is int:
            try:
                params[key] = int(params[key])
            except (TypeError, ValueError) as exc:
                raise CapabilityValidationError(f"{key} must be an integer") from exc
        elif not isinstance(params[key], typ):
            raise CapabilityValidationError(f"{key} must be {typ.__name__}")
    if capability == "send_email" and not validate_email_address(str(params["to"])):
        raise CapabilityValidationError("to must be a valid email address")
    if capability == "book_calendar" and int(params["duration"]) <= 0:
        raise CapabilityValidationError("duration must be greater than 0")


def _redact_params(capability: str, params: dict) -> dict:
    cleaned = dict(params)
    cleaned.pop("confirmed", None)
    return cleaned


def _format_output(capability: str, result: dict) -> Any:
    if result.get("success") is False or result.get("status") == "error":
        return result.get("error") or result.get("reason") or "Capability execution failed."
    if capability == "search_web":
        return result.get("results", [])
    if capability == "send_email":
        tracking = result.get("tracking_id") or result.get("message_id") or "unknown"
        return f"Email sent. Tracking ID: {tracking}"
    if capability == "book_calendar":
        title = result.get("title") or "Event"
        url = result.get("event_url") or ""
        suffix = f" {url}" if url else ""
        return f"{title} added to calendar.{suffix}"
    return result


def _is_missing_table_or_column(exc: Exception) -> bool:
    if psycopg is not None:
        missing = (
            getattr(psycopg.errors, "UndefinedTable", ()),
            getattr(psycopg.errors, "UndefinedColumn", ()),
        )
        if isinstance(exc, missing):
            return True
    text = str(exc).lower()
    return "does not exist" in text or "undefinedtable" in text or "undefinedcolumn" in text

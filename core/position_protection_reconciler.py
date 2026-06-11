#!/usr/bin/env python3
"""Idempotent protection reconciler for live Hyperliquid positions.

This module is intentionally adapter-shaped rather than SDK-shaped. The live
host can pass the existing Hyperliquid adapter object, while tests can use a
small fake. Failures are recorded as audit events and returned in the summary;
they do not raise out of the reconciler loop.
"""

from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

LOGGER = logging.getLogger("whaletrack.protection")

DEFAULT_AUDIT_LOG = Path(
    "/opt/fpai/services/whaletrack-magnet/data/live_trades/sweep_signal_real.jsonl"
)
DEFAULT_STOP_PCT = 0.025
DEFAULT_TARGET_PCT = 0.05


@dataclass(frozen=True)
class Position:
    symbol: str
    side: str
    size: float
    entry_price: float
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TriggerOrder:
    symbol: str
    kind: str
    trigger_price: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProtectionPlan:
    symbol: str
    side: str
    size: float
    stop_price: float
    target_price: float
    source: str


@dataclass
class ReconcileSummary:
    positions_seen: int = 0
    stops_placed: int = 0
    targets_placed: int = 0
    skipped: int = 0
    unconfirmed: int = 0
    errors: list[str] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors and self.unconfirmed == 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "positions_seen": self.positions_seen,
            "stops_placed": self.stops_placed,
            "targets_placed": self.targets_placed,
            "skipped": self.skipped,
            "unconfirmed": self.unconfirmed,
            "errors": list(self.errors),
            "events": list(self.events),
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_audit(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def _first_float(data: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def normalize_position(row: dict[str, Any]) -> Position | None:
    nested = row.get("position") if isinstance(row.get("position"), dict) else row
    symbol = str(
        nested.get("coin")
        or nested.get("symbol")
        or nested.get("asset")
        or nested.get("sym")
        or ""
    ).upper()
    if not symbol:
        return None
    size = _first_float(nested, "size", "szi", "qty", "quantity")
    if size is None or size == 0:
        return None
    entry = _first_float(nested, "entry_price", "entryPx", "entry", "avgEntryPx") or 0.0
    side = str(nested.get("side") or nested.get("dir") or "").lower()
    if side not in {"long", "short"}:
        side = "long" if size > 0 else "short"
    return Position(symbol=symbol, side=side, size=abs(size), entry_price=entry, raw=row)


def normalize_order(row: dict[str, Any]) -> TriggerOrder | None:
    nested = row.get("order") if isinstance(row.get("order"), dict) else row
    symbol = str(
        nested.get("coin")
        or nested.get("symbol")
        or nested.get("asset")
        or nested.get("sym")
        or ""
    ).upper()
    if not symbol:
        return None

    order_type = nested.get("orderType") or nested.get("type") or nested.get("tpsl") or ""
    trigger_type = order_type.get("trigger") if isinstance(order_type, dict) else {}
    tpsl = str(
        nested.get("tpsl")
        or (trigger_type or {}).get("tpsl")
        or ""
    ).lower()
    text = json.dumps(order_type).lower() if not isinstance(order_type, str) else order_type.lower()
    if "stop" in text or tpsl == "sl" or '"sl"' in text:
        kind = "stop"
    elif "take" in text or "profit" in text or tpsl == "tp" or '"tp"' in text:
        kind = "target"
    elif nested.get("triggerPx") or nested.get("trigger_price"):
        # Some HL frontend rows only reveal that it is a trigger order. Keep it
        # visible but do not count it as a stop or target without a type marker.
        kind = "trigger"
    else:
        return None

    trigger = _first_float(nested, "triggerPx", "trigger_price", "stopPx", "price")
    if trigger is None and isinstance(trigger_type, dict):
        trigger = _first_float(trigger_type, "triggerPx", "trigger_price", "stopPx", "price")
    return TriggerOrder(symbol=symbol, kind=kind, trigger_price=trigger, raw=row)


def _adapter_call(adapter: Any, *names: str) -> Any:
    for name in names:
        method = getattr(adapter, name, None)
        if callable(method):
            return method()
    raise AttributeError(f"adapter missing one of: {', '.join(names)}")


def list_positions(adapter: Any) -> list[Position]:
    rows = _adapter_call(adapter, "list_open_positions", "get_open_positions", "get_positions")
    positions: list[Position] = []
    for row in rows or []:
        if isinstance(row, dict):
            pos = normalize_position(row)
            if pos:
                positions.append(pos)
    return positions


def list_trigger_orders(adapter: Any) -> list[TriggerOrder]:
    rows = _adapter_call(adapter, "list_resting_orders", "list_open_orders", "get_open_orders")
    orders: list[TriggerOrder] = []
    for row in rows or []:
        if isinstance(row, dict):
            order = normalize_order(row)
            if order:
                orders.append(order)
    return orders


def load_latest_audit_entries(path: Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return latest
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        symbol = str(row.get("symbol") or row.get("sym") or row.get("coin") or "").upper()
        phase = str(row.get("phase") or "").lower()
        if symbol and phase in {"entry", "filled", "open", "entry_filled"}:
            latest[symbol] = row
    return latest


def build_plan(
    position: Position,
    audit_entry: dict[str, Any] | None,
    stop_pct: float = DEFAULT_STOP_PCT,
    target_pct: float = DEFAULT_TARGET_PCT,
) -> ProtectionPlan:
    stop = None
    target = None
    if audit_entry:
        stop = _first_float(audit_entry, "stop", "stop_loss", "stop_price", "sl")
        target = _first_float(audit_entry, "target", "take_profit", "target_price", "tp")
    source = "audit" if stop and target else "fallback_pct"

    entry = position.entry_price
    if entry <= 0:
        mark = _first_float(position.raw, "mark_price", "markPx", "mark") or 0.0
        entry = mark
    if entry <= 0:
        raise ValueError(f"{position.symbol}: cannot derive entry price for fallback protection")

    if position.side == "long":
        stop = stop or entry * (1 - stop_pct)
        target = target or entry * (1 + target_pct)
    else:
        stop = stop or entry * (1 + stop_pct)
        target = target or entry * (1 - target_pct)

    return ProtectionPlan(
        symbol=position.symbol,
        side=position.side,
        size=position.size,
        stop_price=round(float(stop), 8),
        target_price=round(float(target), 8),
        source=source,
    )


def has_order(orders: Iterable[TriggerOrder], symbol: str, kind: str) -> bool:
    return any(order.symbol == symbol.upper() and order.kind == kind for order in orders)


def _place(adapter: Any, method_name: str, plan: ProtectionPlan, price: float) -> Any:
    method = getattr(adapter, method_name)
    close_side = "sell" if plan.side == "long" else "buy"
    attempts = (
        lambda: method(plan.symbol, close_side, plan.size, price),
        lambda: method(symbol=plan.symbol, side=close_side, size=plan.size, trigger_price=price),
        lambda: method(symbol=plan.symbol, side=close_side, qty=plan.size, trigger_price=price),
        lambda: method(plan.symbol, plan.size, price),
    )
    last_error: Exception | None = None
    for attempt in attempts:
        try:
            return attempt()
        except TypeError as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    raise RuntimeError(f"{method_name} failed without an exception")


def _event(phase: str, plan: ProtectionPlan, **extra: Any) -> dict[str, Any]:
    event = {
        "ts": utc_now(),
        "phase": phase,
        "symbol": plan.symbol,
        "side": plan.side,
        "size": plan.size,
        "stop": plan.stop_price,
        "target": plan.target_price,
        "source": plan.source,
    }
    event.update(extra)
    return event


def reconcile_once(
    adapter: Any,
    audit_log: Path = DEFAULT_AUDIT_LOG,
    dry_run: bool = False,
    stop_pct: float = DEFAULT_STOP_PCT,
    target_pct: float = DEFAULT_TARGET_PCT,
    audit_writer: Callable[[dict[str, Any]], None] | None = None,
) -> ReconcileSummary:
    summary = ReconcileSummary()

    def record(event: dict[str, Any]) -> None:
        summary.events.append(event)
        if audit_writer:
            audit_writer(event)
        elif not dry_run:
            append_audit(audit_log, event)

    try:
        positions = list_positions(adapter)
        orders = list_trigger_orders(adapter)
        entries = load_latest_audit_entries(audit_log)
    except Exception as exc:  # noqa: BLE001 - must degrade loudly, not die silently.
        message = f"protection_inventory_failed: {exc}"
        LOGGER.exception(message)
        summary.errors.append(message)
        return summary

    summary.positions_seen = len(positions)
    for position in positions:
        try:
            plan = build_plan(position, entries.get(position.symbol), stop_pct, target_pct)
        except Exception as exc:  # noqa: BLE001
            message = f"{position.symbol}: plan_failed: {exc}"
            LOGGER.exception(message)
            summary.errors.append(message)
            continue

        missing_stop = not has_order(orders, position.symbol, "stop")
        missing_target = not has_order(orders, position.symbol, "target")
        if not missing_stop and not missing_target:
            summary.skipped += 1
            continue

        if dry_run:
            record(_event("protection_dry_run", plan, missing_stop=missing_stop, missing_target=missing_target))
            continue

        if missing_stop:
            try:
                _place(adapter, "place_stop_loss", plan, plan.stop_price)
                summary.stops_placed += 1
                record(_event("stop_reconciled", plan))
            except Exception as exc:  # noqa: BLE001
                message = f"{position.symbol}: stop_place_failed: {exc}"
                LOGGER.exception(message)
                summary.errors.append(message)
                record(_event("stop_unconfirmed", plan, error=str(exc)))

        if missing_target:
            try:
                _place(adapter, "place_take_profit", plan, plan.target_price)
                summary.targets_placed += 1
                record(_event("target_reconciled", plan))
            except Exception as exc:  # noqa: BLE001
                message = f"{position.symbol}: target_place_failed: {exc}"
                LOGGER.exception(message)
                summary.errors.append(message)
                record(_event("target_unconfirmed", plan, error=str(exc)))

        try:
            refreshed = list_trigger_orders(adapter)
            if missing_stop and not has_order(refreshed, position.symbol, "stop"):
                summary.unconfirmed += 1
                record(_event("stop_unconfirmed", plan, error="not_resting_after_place"))
            if missing_target and not has_order(refreshed, position.symbol, "target"):
                summary.unconfirmed += 1
                record(_event("target_unconfirmed", plan, error="not_resting_after_place"))
        except Exception as exc:  # noqa: BLE001
            message = f"{position.symbol}: confirmation_failed: {exc}"
            LOGGER.exception(message)
            summary.errors.append(message)
            summary.unconfirmed += 1
            record(_event("stop_unconfirmed", plan, error=message))

    return summary


def load_adapter(factory_path: str) -> Any:
    module_name, _, attr = factory_path.partition(":")
    if not module_name or not attr:
        raise ValueError("adapter factory must look like 'module:callable'")
    module = importlib.import_module(module_name)
    factory = getattr(module, attr)
    return factory() if callable(factory) else factory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="run one reconciliation pass")
    parser.add_argument("--dry-run", action="store_true", help="inventory and plan without placing orders")
    parser.add_argument("--interval", type=int, default=120, help="seconds between runs without --once")
    parser.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT_LOG)
    parser.add_argument("--stop-pct", type=float, default=DEFAULT_STOP_PCT)
    parser.add_argument("--target-pct", type=float, default=DEFAULT_TARGET_PCT)
    parser.add_argument(
        "--adapter",
        default=os.getenv("WHALETRACK_ADAPTER_FACTORY", "app.hyperliquid_sdk_adapter:HyperliquidSDKAdapter"),
        help="adapter factory as module:callable",
    )
    parser.add_argument("--json", action="store_true", help="print JSON summary")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    adapter = load_adapter(args.adapter)

    while True:
        summary = reconcile_once(
            adapter=adapter,
            audit_log=args.audit_log,
            dry_run=args.dry_run,
            stop_pct=args.stop_pct,
            target_pct=args.target_pct,
        )
        payload = summary.as_dict()
        if args.json:
            print(json.dumps(payload, sort_keys=True))
        elif not summary.ok:
            LOGGER.error("protection reconciliation degraded: %s", payload)
        else:
            LOGGER.info("protection reconciliation ok: %s", payload)
        if args.once:
            return 0 if summary.ok else 2
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())

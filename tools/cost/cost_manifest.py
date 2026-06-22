#!/usr/bin/env python3
"""Cost Truth Ledger v1.

Reads a manually verified fixed-cost manifest plus the existing metered tracker
ledger and emits one digest line. This never calls billing APIs and never
attributes flat-rate loops.
"""
from __future__ import annotations

import argparse
import calendar
import datetime as dt
import json
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = Path(__file__).with_name("fixed_cost_manifest.jsonl")
DEFAULT_METERED_LEDGER = Path.home() / ".config" / "fpai" / "cost" / "ledger.jsonl"
REQUIRED_FIELDS = (
    "item",
    "amount",
    "owner",
    "source",
    "verified_at",
    "renewal",
    "category",
    "confidence",
)
MONTHLY_BASELINE_DAYS = Decimal("30")
STALE_AFTER_DAYS = 30
DRIFT_THRESHOLD = Decimal("0.10")


@dataclass(frozen=True)
class FixedCost:
    item: str
    amount: Decimal
    owner: str
    source: str
    verified_at: dt.date
    renewal: str
    category: str
    confidence: str

    @property
    def monthly_amount(self) -> Decimal:
        if self.renewal == "monthly":
            return self.amount
        if self.renewal == "annual":
            return self.amount / Decimal("12")
        if self.renewal == "daily":
            return self.amount * MONTHLY_BASELINE_DAYS
        raise ValueError(f"unsupported renewal for {self.item}: {self.renewal}")


@dataclass(frozen=True)
class CostDigest:
    today_metered: Decimal
    fixed_monthly_total: Decimal
    fixed_daily_accrual: Decimal
    fixed_month_to_date_accrual: Decimal
    projected_monthly_burn: Decimal
    stale_source: bool
    drift_over_10pct: bool

    def line(self) -> str:
        return (
            "COST truth: "
            f"today-metered={money(self.today_metered)} | "
            f"monthly-fixed-accrual={money(self.fixed_month_to_date_accrual)} "
            f"(daily={money(self.fixed_daily_accrual)}, baseline={money(self.fixed_monthly_total)}/mo) | "
            f"projected-monthly-burn={money(self.projected_monthly_burn)} | "
            f"stale-source-flag={str(self.stale_source).lower()} | "
            f"drift>10%={str(self.drift_over_10pct).lower()} | "
            "source=James-verified estimates, not live billing; loops=flat-rate"
        )


def money(value: Decimal) -> str:
    cents = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"${cents}"


def parse_manifest(path: Path = DEFAULT_MANIFEST) -> list[FixedCost]:
    records: list[FixedCost] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSONL: {exc}") from exc
        missing = [field for field in REQUIRED_FIELDS if field not in raw]
        if missing:
            raise ValueError(f"{path}:{line_no}: missing fields: {', '.join(missing)}")
        try:
            amount = Decimal(str(raw["amount"]))
        except InvalidOperation as exc:
            raise ValueError(f"{path}:{line_no}: invalid amount: {raw['amount']!r}") from exc
        if amount < 0:
            raise ValueError(f"{path}:{line_no}: amount must be non-negative")
        try:
            verified_at = dt.date.fromisoformat(str(raw["verified_at"]))
        except ValueError as exc:
            raise ValueError(f"{path}:{line_no}: verified_at must be YYYY-MM-DD") from exc
        records.append(
            FixedCost(
                item=str(raw["item"]),
                amount=amount,
                owner=str(raw["owner"]),
                source=str(raw["source"]),
                verified_at=verified_at,
                renewal=str(raw["renewal"]),
                category=str(raw["category"]),
                confidence=str(raw["confidence"]),
            )
        )
    if not records:
        raise ValueError(f"{path}: manifest is empty")
    return records


def read_today_metered(ledger: Path = DEFAULT_METERED_LEDGER, today: dt.date | None = None) -> Decimal:
    today = today or dt.date.today()
    if not ledger.exists():
        return Decimal("0")
    total = Decimal("0")
    for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("billing") != "metered":
            continue
        if not str(row.get("timestamp", "")).startswith(today.isoformat()):
            continue
        try:
            total += Decimal(str(row.get("est_usd", "0")))
        except InvalidOperation:
            continue
    return total


def has_stale_source(records: Iterable[FixedCost], today: dt.date | None = None) -> bool:
    today = today or dt.date.today()
    return any((today - record.verified_at).days > STALE_AFTER_DAYS for record in records)


def build_digest(
    *,
    manifest: Path = DEFAULT_MANIFEST,
    metered_ledger: Path = DEFAULT_METERED_LEDGER,
    today: dt.date | None = None,
) -> CostDigest:
    today = today or dt.date.today()
    records = parse_manifest(manifest)
    fixed_monthly_total = sum((record.monthly_amount for record in records), Decimal("0"))
    fixed_daily_accrual = fixed_monthly_total / MONTHLY_BASELINE_DAYS
    fixed_month_to_date_accrual = fixed_daily_accrual * Decimal(min(today.day, 30))
    today_metered = read_today_metered(metered_ledger, today)
    days_in_month = Decimal(calendar.monthrange(today.year, today.month)[1])
    projected_monthly_burn = fixed_monthly_total + today_metered * days_in_month
    drift = False
    if fixed_monthly_total > 0:
        drift = ((projected_monthly_burn - fixed_monthly_total) / fixed_monthly_total) > DRIFT_THRESHOLD
    return CostDigest(
        today_metered=today_metered,
        fixed_monthly_total=fixed_monthly_total,
        fixed_daily_accrual=fixed_daily_accrual,
        fixed_month_to_date_accrual=fixed_month_to_date_accrual,
        projected_monthly_burn=projected_monthly_burn,
        stale_source=has_stale_source(records, today),
        drift_over_10pct=drift,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print one Cost Truth Ledger digest line.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--metered-ledger", type=Path, default=Path(os.environ.get("FPAI_COST_LEDGER", DEFAULT_METERED_LEDGER)))
    parser.add_argument("--today", help="Override date for tests, YYYY-MM-DD.")
    args = parser.parse_args(argv)

    today = dt.date.fromisoformat(args.today) if args.today else None
    digest = build_digest(manifest=args.manifest, metered_ledger=args.metered_ledger, today=today)
    print(digest.line())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

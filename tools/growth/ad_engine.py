#!/usr/bin/env python3
"""Offline-first ad creative ledger and scorer for Full Potential growth.

This module does not create or activate Meta ads. It generates variants, records
offline outcomes, scores winners, and exposes a runtime gate that must pass
before any separate live-spend path is allowed to act.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_LEDGER = Path.home() / ".config/fpai/growth/ads_ledger.jsonl"
DEFAULT_KILL_SWITCH = Path.home() / ".config/fpai/ads/PAUSE_ALL"
MAX_DAILY_BUDGET_USD = 10.0
FRAMES = ("promise", "exec", "savings")


@dataclass
class AdVariant:
    variant_id: str
    frame: str
    headline: str
    primary_text: str
    url: str
    status: str = "draft"
    impressions: int = 0
    clicks: int = 0
    leads: int = 0
    spend_usd: float = 0.0
    generation: int = 0
    parent_id: str | None = None
    score: float = 0.0
    created_at: str = ""

    def row(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema"] = "fpai.ads.variant.v1"
        payload["created_at"] = self.created_at or now_utc()
        return payload


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def variant_id(frame: str, headline: str, generation: int = 0) -> str:
    digest = hashlib.sha1(f"{frame}:{headline}:{generation}".encode("utf-8")).hexdigest()[:8]
    return f"fpai-{frame}-{generation}-{digest}"


def assessment_url(variant: str) -> str:
    return f"https://fullpotential.com/assessment?utm_source=meta&utm_medium=paid&utm_campaign={variant}"


def generated_variants(count: int = 6, *, generation: int = 0, parent_id: str | None = None) -> list[AdVariant]:
    raw = [
        (
            "promise",
            "Find the resource leaks slowing your company down",
            "Your business already has the capital, time, and AI leverage it needs. The free Full Potential Assessment shows where those resources are misallocated and which three moves create the most future capability.",
        ),
        (
            "promise",
            "Turn scattered tools into a compounding operating system",
            "Most companies do not need another AI tool. They need their existing resources routed, reasoned about, and reinvested through one Allocation Intelligence loop.",
        ),
        (
            "exec",
            "Your next allocation deserves a clearer map",
            "Executives lose leverage when capital, attention, people, and AI are evaluated in separate silos. Get an Allocation Score and see where the next scarce resource should go.",
        ),
        (
            "exec",
            "Stop making resource decisions from fragmented data",
            "Full Potential reads the operating picture behind spend, workflows, and attention so leadership can make fewer, better allocation decisions.",
        ),
        (
            "savings",
            "Find the SaaS and workflow waste hiding in plain sight",
            "Unused tools, duplicated handoffs, and manual work AI should own quietly tax the business. Start with a free Allocation Assessment before spending another dollar.",
        ),
        (
            "savings",
            "Recover budget by reallocating what already exists",
            "The first win is usually not new spend. It is redirecting existing software, labor, and AI toward higher-capability work.",
        ),
    ]
    variants: list[AdVariant] = []
    for frame, headline, text in raw[:count]:
        vid = variant_id(frame, headline, generation)
        variants.append(
            AdVariant(
                variant_id=vid,
                frame=frame,
                headline=headline,
                primary_text=text,
                url=assessment_url(vid),
                generation=generation,
                parent_id=parent_id,
                created_at=now_utc(),
            )
        )
    return variants


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def read_ledger(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def write_ledger(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def score_row(row: dict[str, Any]) -> dict[str, Any]:
    impressions = max(int(row.get("impressions") or 0), 0)
    clicks = max(int(row.get("clicks") or 0), 0)
    leads = max(int(row.get("leads") or 0), 0)
    spend = max(float(row.get("spend_usd") or 0.0), 0.0)
    denominator = max(impressions, 1) * max(spend, 0.01)
    score = leads / denominator
    status = row.get("status") or "draft"
    if impressions >= 500 and leads == 0:
        status = "killed"
    elif leads > 0 and score >= 0.0001:
        status = "champion"
    updated = dict(row)
    updated.update(
        {
            "impressions": impressions,
            "clicks": clicks,
            "leads": leads,
            "spend_usd": round(spend, 2),
            "ctr": round(clicks / impressions, 6) if impressions else 0.0,
            "lead_rate": round(leads / impressions, 6) if impressions else 0.0,
            "score": round(score, 8),
            "status": status,
            "scored_at": now_utc(),
        }
    )
    return updated


def score_ledger(path: Path, *, write: bool = True) -> list[dict[str, Any]]:
    rows = [score_row(row) for row in read_ledger(path)]
    if write:
        write_ledger(path, rows)
    return rows


def apply_outcomes(rows: list[dict[str, Any]], outcomes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {row.get("variant_id"): dict(row) for row in rows}
    for outcome in outcomes:
        vid = outcome.get("variant_id") or outcome.get("utm_campaign") or outcome.get("source")
        if vid not in by_id:
            continue
        row = by_id[vid]
        for key in ("impressions", "clicks", "leads"):
            if key in outcome:
                row[key] = int(outcome[key] or 0)
        if "spend_usd" in outcome:
            row["spend_usd"] = float(outcome["spend_usd"] or 0.0)
        by_id[vid] = row
    return list(by_id.values())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError:
        return []


def spend_gate(
    *,
    account_status: int | str | None,
    requested_daily_budget_usd: float,
    kill_switch_path: Path = DEFAULT_KILL_SWITCH,
    james_unlock: bool = False,
) -> dict[str, Any]:
    reasons: list[str] = []
    try:
        status = int(account_status or 0)
    except (TypeError, ValueError):
        status = 0
    if kill_switch_path.exists():
        reasons.append("pause_all_kill_switch_present")
    if status != 1:
        reasons.append("meta_account_status_not_1")
    if requested_daily_budget_usd > MAX_DAILY_BUDGET_USD:
        reasons.append("daily_budget_over_10_usd")
    if requested_daily_budget_usd <= 0:
        reasons.append("daily_budget_not_positive")
    if not james_unlock:
        reasons.append("james_spend_unlock_missing")
    return {
        "ok": not reasons,
        "reasons": reasons,
        "account_status": status,
        "requested_daily_budget_usd": round(requested_daily_budget_usd, 2),
        "max_daily_budget_usd": MAX_DAILY_BUDGET_USD,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--count", type=int, default=6)
    parser.add_argument("--score", action="store_true")
    parser.add_argument("--outcomes", type=Path)
    parser.add_argument("--spend-gate", action="store_true")
    parser.add_argument("--account-status", default="0")
    parser.add_argument("--daily-budget-usd", type=float, default=MAX_DAILY_BUDGET_USD)
    parser.add_argument("--kill-switch", type=Path, default=DEFAULT_KILL_SWITCH)
    parser.add_argument("--james-unlock", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.generate:
        append_jsonl(args.ledger, [variant.row() for variant in generated_variants(args.count)])
    if args.outcomes:
        rows = apply_outcomes(read_ledger(args.ledger), read_jsonl(args.outcomes))
        write_ledger(args.ledger, rows)
    scored = score_ledger(args.ledger, write=True) if args.score else read_ledger(args.ledger)
    payload: dict[str, Any] = {"ok": True, "ledger": str(args.ledger), "variants": len(scored)}
    if args.spend_gate:
        payload["spend_gate"] = spend_gate(
            account_status=args.account_status,
            requested_daily_budget_usd=args.daily_budget_usd,
            kill_switch_path=args.kill_switch,
            james_unlock=args.james_unlock,
        )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Deterministic-first shadow model router for One-Chat messages.

This module does not change live routing. It classifies an incoming message,
chooses the tier it would use, and appends that decision to an ops ledger so
misroutes can be audited before any live behavior depends on it.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEDGER = REPO_ROOT / "core" / "STATE" / "router_truth_ledger.jsonl"

TIER_ORDER = {
    "T0": 0,
    "T1": 1,
    "T2": 2,
    "T3": 3,
    "T4": 4,
    "T5": 5,
}

TIER_COSTS = {
    "T0": "$0.0000",
    "T1": "$0.0000 local",
    "T2": "<=$0.01",
    "T3": "<=$0.10",
    "T4": "<=$0.50 council",
    "T5": "$0 model; James attention gate",
}


@dataclasses.dataclass(frozen=True)
class Axis:
    message_class: str
    tier: str
    reason: str


@dataclasses.dataclass(frozen=True)
class RouteDecision:
    message_class: str
    chosen_tier: str
    reason: str
    est_tier_cost: str
    matched_axes: tuple[Axis, ...]
    shadow_mode: bool = True
    loop: str = "router"

    def ledger_row(self, *, message: str, now: dt.datetime | None = None) -> dict[str, object]:
        stamp = now or dt.datetime.now(dt.timezone.utc)
        return {
            "ts": stamp.isoformat().replace("+00:00", "Z"),
            "loop": self.loop,
            "shadow_mode": self.shadow_mode,
            "message_class": self.message_class,
            "chosen_tier": self.chosen_tier,
            "reason": self.reason,
            "est_tier_cost": self.est_tier_cost,
            "message_preview": compact(message)[:240],
            "matched_axes": [
                {
                    "message_class": axis.message_class,
                    "tier": axis.tier,
                    "reason": axis.reason,
                }
                for axis in self.matched_axes
            ],
        }


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def has(patterns: Iterable[str], text: str) -> bool:
    return any(re.search(pattern, text, flags=re.I) for pattern in patterns)


def classify_axes(message: str) -> list[Axis]:
    text = compact(message)
    low = text.lower()
    axes: list[Axis] = []

    if re.search(
        r"\bd\d{2,5}\b.*\b(approve|approved|yes|yep|go|bless|blessed|ship|ok|okay)\b",
        low,
    ):
        axes.append(Axis("decision", "T0", "decision reply can be handled by rules/cache"))

    if has(
        (
            r"\bwhat'?s going on\b",
            r"\bwhat is going on\b",
            r"\bstatus\b",
            r"\bwhere are we\b",
            r"\bcatch me up\b",
            r"\bsummary\b",
        ),
        low,
    ):
        axes.append(Axis("status", "T1", "status summary should use local context first"))

    if has(
        (
            r"\bbuild\b",
            r"\bimplement\b",
            r"\bfix\b",
            r"\bwire\b",
            r"\badd\b.+\btest",
            r"\bmake\b.+\btool\b",
            r"\bcreate\b.+\bspec\b",
        ),
        low,
    ):
        axes.append(Axis("build-request", "T3", "build request needs strong implementation reasoning"))

    if has(
        (
            r"\btreasury\b",
            r"\bsend\s+\$?\d",
            r"\btransfer\b",
            r"\bwire money\b",
            r"\bmove money\b",
            r"\bwithdraw\b",
            r"\bdeposit\b",
            r"\bbuy\b.+\b(token|crypto|sol|btc|eth)\b",
        ),
        low,
    ):
        axes.append(Axis("treasury", "T5", "money or treasury action is James-gated"))

    if has(
        (
            r"\bprotected path\b",
            r"\bproduction\b",
            r"\bprod\b",
            r"\bdeploy\b",
            r"\bforce[- ]?push\b",
            r"\bsecret\b",
            r"\bcredential\b",
            r"\bdelete\b.+\b(service|database|repo|branch)\b",
            r"\bstop\b.+\b(service|daemon|prod)\b",
            r"\b(core/STATE|core/BUILD/PROTECTED_PATHS|\.env)\b",
        ),
        low,
    ):
        axes.append(Axis("protected-path", "T5", "protected path, production, or secret-bearing action is James-gated"))

    if has(
        (
            r"\bself[- ]?evol",
            r"\bmeta\b",
            r"\barchitecture\b",
            r"\bhow should (the )?system evolve\b",
            r"\bchange (the )?(doctrine|mission|protocol)\b",
            r"\birreversible\b",
            r"\bautonom(y|ous)\b",
        ),
        low,
    ):
        axes.append(Axis("self-evolution", "T4", "self-evolution/meta/architecture/irreversible needs council review"))

    if has(
        (
            r"\bhire\b",
            r"\bfire\b",
            r"\bpartner\b",
            r"\bpeople\b",
            r"\bpublic\b",
            r"\bpublish\b",
            r"\bpost\b.+\b(twitter|x|linkedin|public)\b",
            r"\bsend\b.+\b(email|dm|message|outreach)\b",
        ),
        low,
    ):
        axes.append(Axis("reserved-stakes", "T5", "people, public voice, or outbound send is James-gated"))

    if not axes:
        axes.append(Axis("routine", "T1", "routine message can start with a local small model"))

    return axes


def choose_decision(message: str) -> RouteDecision:
    axes = classify_axes(message)
    max_axis = max(axes, key=lambda axis: TIER_ORDER[axis.tier])
    classes = tuple(axis.message_class for axis in axes)
    if max_axis.tier in {"T4", "T5"}:
        message_class = max_axis.message_class
    elif "decision" in classes:
        message_class = "decision"
    elif "status" in classes:
        message_class = "status"
    elif "build-request" in classes:
        message_class = "build-request"
    else:
        message_class = max_axis.message_class
    reason = f"{max_axis.reason}; routed by max matched axis"
    return RouteDecision(
        message_class=message_class,
        chosen_tier=max_axis.tier,
        reason=reason,
        est_tier_cost=TIER_COSTS[max_axis.tier],
        matched_axes=tuple(axes),
    )


def append_ledger(decision: RouteDecision, message: str, path: Path | str = DEFAULT_LEDGER) -> Path:
    ledger = Path(path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    row = decision.ledger_row(message=message)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return ledger


def route_message(message: str, *, ledger: Path | str = DEFAULT_LEDGER, log: bool = True) -> RouteDecision:
    decision = choose_decision(message)
    if log:
        append_ledger(decision, message, ledger)
    return decision


def decision_payload(decision: RouteDecision) -> dict[str, object]:
    return {
        "message_class": decision.message_class,
        "chosen_tier": decision.chosen_tier,
        "reason": decision.reason,
        "est_tier_cost": decision.est_tier_cost,
        "shadow_mode": decision.shadow_mode,
        "loop": decision.loop,
        "matched_axes": [dataclasses.asdict(axis) for axis in decision.matched_axes],
    }


def print_result(decision: RouteDecision, ledger: Path | None) -> None:
    print("Instrument Rack shadow decision")
    print("---")
    print(f"message_class: {decision.message_class}")
    print(f"chosen_tier: {decision.chosen_tier}")
    print(f"reason: {decision.reason}")
    print(f"est_tier_cost: {decision.est_tier_cost}")
    print(f"shadow_mode: {str(decision.shadow_mode).lower()}")
    if ledger:
        print(f"ledger: {ledger}")
    print(f"RESULT instrument_rack class={decision.message_class} tier={decision.chosen_tier} shadow=true")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Shadow-classify one One-Chat message without live rerouting.")
    parser.add_argument("message", nargs="?", help="message text to classify")
    parser.add_argument("--message", dest="message_opt", help="message text to classify")
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--no-log", action="store_true", help="classify only; do not append the ledger")
    parser.add_argument("--json", action="store_true", help="print the decision as JSON")
    args = parser.parse_args(argv)

    message = args.message_opt or args.message
    if not message:
        print("instrument_rack error: message is required", file=sys.stderr)
        print("RESULT instrument_rack FAIL")
        return 2

    try:
        decision = route_message(message, ledger=args.ledger, log=not args.no_log)
    except Exception as exc:
        print(f"instrument_rack error: {exc}", file=sys.stderr)
        print("RESULT instrument_rack FAIL")
        return 1

    if args.json:
        print(json.dumps(decision_payload(decision), indent=2, sort_keys=True))
        print(f"RESULT instrument_rack class={decision.message_class} tier={decision.chosen_tier} shadow=true")
    else:
        print_result(decision, None if args.no_log else args.ledger)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.learn.capture_corrections import DEFAULT_DATASET, append_pair, make_correction_pair

DEFAULT_LEDGER = REPO_ROOT / "core" / "STATE" / "router_truth_ledger.jsonl"
DEFAULT_OLLAMA_URL = "http://162.0.208.88:11434/api/generate"
DEFAULT_OLLAMA_MODEL = "llama3.1:8b"

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
class IntentFrame:
    surface_words: str
    real_verb: str
    object: str
    stakes: tuple[str, ...]
    lane: str
    owner: str
    next_action: str
    proof_needed: str

    def to_json(self) -> dict[str, object]:
        return {
            "surface_words": self.surface_words,
            "real_verb": self.real_verb,
            "object": self.object,
            "stakes": list(self.stakes),
            "lane": self.lane,
            "owner": self.owner,
            "next_action": self.next_action,
            "proof_needed": self.proof_needed,
        }


@dataclasses.dataclass(frozen=True)
class LlamaRead:
    used: bool
    confidence: float | None = None
    lane: str | None = None
    real_verb: str | None = None
    object: str | None = None
    next_action: str | None = None
    proof_needed: str | None = None
    error: str | None = None
    raw: str | None = None
    model: str = DEFAULT_OLLAMA_MODEL

    def to_json(self) -> dict[str, object]:
        return {
            "used": self.used,
            "confidence": self.confidence,
            "lane": self.lane,
            "real_verb": self.real_verb,
            "object": self.object,
            "next_action": self.next_action,
            "proof_needed": self.proof_needed,
            "error": self.error,
            "raw": self.raw,
            "model": self.model,
        }


@dataclasses.dataclass(frozen=True)
class RouteDecision:
    message_class: str
    chosen_tier: str
    reason: str
    est_tier_cost: str
    matched_axes: tuple[Axis, ...]
    intent_frame: IntentFrame
    deterministic_hit: bool
    llama_read: LlamaRead
    confidence: float
    stakes: tuple[str, ...]
    would_route: str
    latency_ms: int
    shadow_mode: bool = True
    loop: str = "spark"

    def ledger_row(self, *, message: str, now: dt.datetime | None = None) -> dict[str, object]:
        stamp = now or dt.datetime.now(dt.timezone.utc)
        return {
            "ts": stamp.isoformat().replace("+00:00", "Z"),
            "loop": self.loop,
            "shadow_mode": self.shadow_mode,
            "scorecard": True,
            "deterministic_hit": self.deterministic_hit,
            "llama_read": self.llama_read.to_json(),
            "confidence": self.confidence,
            "stakes": list(self.stakes),
            "would_route": self.would_route,
            "latency_ms": self.latency_ms,
            "actual_outcome": None,
            "intent_frame": self.intent_frame.to_json(),
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


def stakes_from_axes(axes: Iterable[Axis]) -> tuple[str, ...]:
    stakes: list[str] = []
    for axis in axes:
        if axis.message_class == "treasury":
            stakes.append("money")
        elif axis.message_class == "reserved-stakes":
            stakes.append("people/public/outbound")
        elif axis.message_class == "protected-path":
            stakes.append("production/secrets/irreversible")
        elif axis.message_class == "self-evolution":
            stakes.append("architecture/irreversible")
    return tuple(dict.fromkeys(stakes))


def should_read_llama(axes: Iterable[Axis], stakes: tuple[str, ...]) -> bool:
    axis_tuple = tuple(axes)
    classes = {axis.message_class for axis in axis_tuple}
    max_tier = max(axis_tuple, key=lambda axis: TIER_ORDER[axis.tier]).tier
    if stakes:
        return False
    if classes & {"decision", "status"}:
        return False
    return max_tier in {"T1", "T2", "T3"}


def read_live_context(root: Path | str = REPO_ROOT) -> dict[str, str]:
    repo = Path(root)
    context: dict[str, str] = {}
    for key, rel in (
        ("now", "core/STATE/NOW.md"),
        ("open_decisions", "core/STATE/HUMAN_EDGE_QUEUE.md"),
        ("recent_messages", "core/STATE/INBOX.json"),
    ):
        path = repo / rel
        if path.exists():
            context[key] = path.read_text(encoding="utf-8", errors="ignore")[:2000]
    return context


def _context_prompt(message: str, context: dict[str, str]) -> str:
    context_block = "\n".join(f"{key}: {compact(value)[:700]}" for key, value in sorted(context.items()))
    return (
        "Classify this intake message as a thin SPARK frame. Return compact JSON only with keys: "
        "real_verb, object, lane, owner, next_action, proof_needed, confidence. "
        "Do not reason. Message: "
        f"{compact(message)!r}. Live context: {context_block!r}"
    )


def default_llama_classifier(message: str, context: dict[str, str]) -> LlamaRead:
    payload = {
        "model": DEFAULT_OLLAMA_MODEL,
        "prompt": _context_prompt(message, context),
        "stream": False,
        "options": {"temperature": 0},
    }
    request = urllib.request.Request(
        DEFAULT_OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=0.75) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return LlamaRead(used=False, error=f"llama-unavailable: {exc.__class__.__name__}")
    raw = str(body.get("response", "")).strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return LlamaRead(used=True, raw=raw[:500], error="llama-invalid-json")
    if not isinstance(parsed, dict):
        return LlamaRead(used=True, raw=raw[:500], error="llama-non-object-json")
    return LlamaRead(
        used=True,
        confidence=_bounded_float(parsed.get("confidence"), default=0.55),
        lane=_clean_optional(parsed.get("lane")),
        real_verb=_clean_optional(parsed.get("real_verb")),
        object=_clean_optional(parsed.get("object")),
        next_action=_clean_optional(parsed.get("next_action")),
        proof_needed=_clean_optional(parsed.get("proof_needed")),
        raw=raw[:500],
    )


def extract_intent_frame(
    message: str,
    axes: Iterable[Axis],
    stakes: tuple[str, ...],
    *,
    llama_read: LlamaRead,
    context: dict[str, str] | None = None,
) -> IntentFrame:
    axis_tuple = tuple(axes)
    message_class = max(axis_tuple, key=lambda axis: TIER_ORDER[axis.tier]).message_class
    surface_words = compact(message)[:240]
    real_verb = llama_read.real_verb or _verb_from_message(message)
    object_text = llama_read.object or _object_from_message(message, real_verb)
    lane, owner = _lane_owner(message_class, stakes, llama_read.lane)
    next_action = llama_read.next_action or _next_action_for(message_class, lane, stakes)
    proof_needed = llama_read.proof_needed or _proof_for(message_class, lane, stakes)
    return IntentFrame(
        surface_words=surface_words,
        real_verb=real_verb,
        object=object_text,
        stakes=stakes,
        lane=lane,
        owner=owner,
        next_action=next_action,
        proof_needed=proof_needed,
    )


def choose_decision(
    message: str,
    *,
    context: dict[str, str] | None = None,
    llama_classifier: Callable[[str, dict[str, str]], LlamaRead] | None = None,
) -> RouteDecision:
    start = time.perf_counter()
    axes = classify_axes(message)
    max_axis = max(axes, key=lambda axis: TIER_ORDER[axis.tier])
    classes = tuple(axis.message_class for axis in axes)
    stakes = stakes_from_axes(axes)
    deterministic_hit = any(axis.message_class != "routine" for axis in axes)
    live_context = read_live_context() if context is None else context
    llama_read = LlamaRead(used=False)
    if should_read_llama(axes, stakes):
        classifier = llama_classifier or default_llama_classifier
        llama_read = classifier(message, live_context)
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
    intent_frame = extract_intent_frame(message, axes, stakes, llama_read=llama_read, context=live_context)
    confidence = _confidence_for(max_axis, deterministic_hit=deterministic_hit, llama_read=llama_read, stakes=stakes)
    latency_ms = int((time.perf_counter() - start) * 1000)
    return RouteDecision(
        message_class=message_class,
        chosen_tier=max_axis.tier,
        reason=reason,
        est_tier_cost=TIER_COSTS[max_axis.tier],
        matched_axes=tuple(axes),
        intent_frame=intent_frame,
        deterministic_hit=deterministic_hit,
        llama_read=llama_read,
        confidence=confidence,
        stakes=stakes,
        would_route=intent_frame.lane,
        latency_ms=latency_ms,
    )


def _confidence_for(axis: Axis, *, deterministic_hit: bool, llama_read: LlamaRead, stakes: tuple[str, ...]) -> float:
    if stakes:
        return 0.99
    if deterministic_hit and axis.message_class in {"decision", "status"}:
        return 0.95
    if llama_read.confidence is not None:
        return _bounded_float(llama_read.confidence, default=0.55)
    if deterministic_hit:
        return 0.82
    return 0.45


def _bounded_float(value: Any, *, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, number))


def _clean_optional(value: Any) -> str | None:
    cleaned = compact(str(value or ""))
    return cleaned or None


def _verb_from_message(message: str) -> str:
    low = compact(message).lower()
    for verb in ("approve", "build", "implement", "fix", "wire", "send", "transfer", "publish", "delete", "deploy", "summarize", "status"):
        if re.search(rf"\b{verb}\b", low):
            return verb
    if "?" in message:
        return "clarify"
    return "route"


def _object_from_message(message: str, verb: str) -> str:
    text = compact(message)
    match = re.search(rf"\b{re.escape(verb)}\b\s+(.*)", text, flags=re.I)
    if match:
        return match.group(1)[:160]
    return text[:160] or "message"


def _lane_owner(message_class: str, stakes: tuple[str, ...], llama_lane: str | None) -> tuple[str, str]:
    if stakes:
        return "route:james", "James"
    if message_class == "self-evolution":
        return "route:ember", "Ember"
    if message_class in {"build-request", "protected-path"}:
        return "route:codex", "Codex"
    if message_class == "decision":
        return "route:auto", "SPARK rules"
    if message_class == "status":
        return "route:ember", "Ember"
    if llama_lane and re.fullmatch(r"route:(auto|ember|codex|api|james)", llama_lane):
        return llama_lane, llama_lane.split(":", 1)[1]
    return "route:ember", "Ember"


def _next_action_for(message_class: str, lane: str, stakes: tuple[str, ...]) -> str:
    if stakes:
        return "escalate for human review before any action"
    if message_class == "decision":
        return "record the deterministic decision signal"
    if message_class == "status":
        return "summarize current state from local context"
    if message_class == "build-request":
        return "confirm approved spec and build branch"
    if lane == "route:auto":
        return "apply deterministic safe path"
    return "route to the named downstream owner"


def _proof_for(message_class: str, lane: str, stakes: tuple[str, ...]) -> str:
    if stakes:
        return "review note confirming the gate was not under-escalated"
    if message_class == "decision":
        return "decision id and applied safe default"
    if message_class == "build-request":
        return "tests, diff, handoff, and registry row"
    return f"scorecard row showing {lane} and later actual_outcome"


def append_ledger(decision: RouteDecision, message: str, path: Path | str = DEFAULT_LEDGER) -> Path:
    ledger = Path(path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    row = decision.ledger_row(message=message)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return ledger


def route_message(
    message: str,
    *,
    ledger: Path | str = DEFAULT_LEDGER,
    log: bool = True,
    context: dict[str, str] | None = None,
    llama_classifier: Callable[[str, dict[str, str]], LlamaRead] | None = None,
) -> RouteDecision:
    decision = choose_decision(message, context=context, llama_classifier=llama_classifier)
    if log:
        append_ledger(decision, message, ledger)
    return decision


def capture_route_correction(
    *,
    message: str,
    rejected_route: str,
    preferred_route: str,
    correction: str,
    dataset: Path | str = DEFAULT_DATASET,
    metadata: dict[str, Any] | None = None,
) -> bool:
    row = make_correction_pair(
        rejected=f"SPARK route {rejected_route}: {message}",
        preferred=f"SPARK route {preferred_route}: {correction}",
        prompt=message,
        source="spark-route-correction",
        metadata={
            "route_rejected": rejected_route,
            "route_preferred": preferred_route,
            "capture_tool": "tools/router/instrument_rack.py",
            **(metadata or {}),
        },
    )
    return append_pair(row, dataset)


def decision_payload(decision: RouteDecision) -> dict[str, object]:
    return {
        "message_class": decision.message_class,
        "chosen_tier": decision.chosen_tier,
        "reason": decision.reason,
        "est_tier_cost": decision.est_tier_cost,
        "shadow_mode": decision.shadow_mode,
        "loop": decision.loop,
        "deterministic_hit": decision.deterministic_hit,
        "llama_read": decision.llama_read.to_json(),
        "confidence": decision.confidence,
        "stakes": list(decision.stakes),
        "would_route": decision.would_route,
        "latency_ms": decision.latency_ms,
        "actual_outcome": None,
        "intent_frame": decision.intent_frame.to_json(),
        "matched_axes": [dataclasses.asdict(axis) for axis in decision.matched_axes],
    }


def print_result(decision: RouteDecision, ledger: Path | None) -> None:
    print("Instrument Rack shadow decision")
    print("---")
    print(f"message_class: {decision.message_class}")
    print(f"chosen_tier: {decision.chosen_tier}")
    print(f"reason: {decision.reason}")
    print(f"est_tier_cost: {decision.est_tier_cost}")
    print(f"would_route: {decision.would_route}")
    print(f"confidence: {decision.confidence:.2f}")
    print(f"stakes: {', '.join(decision.stakes) if decision.stakes else 'none'}")
    print(f"shadow_mode: {str(decision.shadow_mode).lower()}")
    if ledger:
        print(f"ledger: {ledger}")
    print(f"RESULT instrument_rack class={decision.message_class} tier={decision.chosen_tier} shadow=true")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "correct":
        correction_parser = argparse.ArgumentParser(description="Append a SPARK route correction to the preference dataset.")
        correction_parser.add_argument("command")
        correction_parser.add_argument("--message", required=True)
        correction_parser.add_argument("--rejected-route", required=True)
        correction_parser.add_argument("--preferred-route", required=True)
        correction_parser.add_argument("--correction", required=True)
        correction_parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
        args = correction_parser.parse_args(argv)
        wrote = capture_route_correction(
            message=args.message,
            rejected_route=args.rejected_route,
            preferred_route=args.preferred_route,
            correction=args.correction,
            dataset=args.dataset,
        )
        print(json.dumps({"dataset": str(args.dataset), "wrote": wrote}, sort_keys=True))
        print("RESULT instrument_rack correction captured")
        return 0

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

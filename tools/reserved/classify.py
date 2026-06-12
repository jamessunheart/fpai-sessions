#!/usr/bin/env python3
"""Fail-safe Reserved-Class classifier.

This module is advisory only. It never executes the action being classified and
does not wire itself into the live loop.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "core" / "STATE" / "RESERVED_CLASS.yaml"

GateWriter = Callable[..., dict[str, Any]]

_DRAFT_WORDS = {
    "draft",
    "prepare",
    "propose",
    "summarize",
    "outline",
    "review",
    "analyze",
    "classify",
    "scan",
    "read",
    "test",
    "write tests",
}


def load_policy(path: Path | str = POLICY_PATH) -> dict[str, Any]:
    """Load the JSON-compatible YAML policy."""
    policy_path = Path(path)
    try:
        return json.loads(policy_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid Reserved-Class policy: {policy_path}") from exc


def is_reserved(action_text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Classify whether an action must escalate to James.

    Returns:
        {
            "reserved": bool,
            "category": str | None,
            "reason": str,
            "confidence": float,
        }

    The classifier is intentionally conservative: unknown consequential-looking
    actions default to Reserved-Class instead of being cleared.
    """
    policy = load_policy()
    raw_action = (action_text or "").strip()
    if not raw_action:
        return _verdict(True, "uncertain", "empty action; fail-safe escalation", 0.99)

    context = context or {}
    text = _normalize(" ".join([raw_action, _context_text(context)]))

    money_signal = _money_signal(text)
    if money_signal:
        return _verdict(True, "money", f"matched Money out: {money_signal}", 0.95)

    for category in policy.get("categories", []):
        matched = _match_category(text, category)
        if matched:
            category_id = "money" if category["id"] == "money_out" else category["id"]
            return _verdict(
                True,
                category_id,
                f"matched {category['label']}: {matched}",
                0.93,
            )

    if _is_clearly_delegable(text, policy):
        return _verdict(False, None, "clearly delegable advisory/reversible work", 0.82)

    consequential = _match_any(text, policy.get("consequential_signals", []))
    if consequential:
        return _verdict(
            True,
            "uncertain",
            f"consequential-looking but no exact category match: {consequential}",
            0.76,
        )

    if context.get("consequential") or context.get("external_effect"):
        return _verdict(True, "uncertain", "context marks action as consequential", 0.78)

    return _verdict(True, "uncertain", "unknown action; fail-safe escalation", 0.64)


def gate_or_proceed(
    action_text: str,
    context: dict[str, Any] | None = None,
    *,
    apply_gate: bool = False,
    gate_writer: GateWriter | None = None,
) -> dict[str, Any]:
    """Return a gate/proceed decision for future loop integration.

    This helper is a stub for Rungs 1-2: callers may pass ``apply_gate=True`` to
    write a human-edge gate through ``tools.queue.build.add_gate()``, or inject a
    ``gate_writer`` in tests. It does not run or approve the requested action.
    """
    verdict = is_reserved(action_text, context)
    result: dict[str, Any] = {
        "proceed": not verdict["reserved"],
        "verdict": verdict,
        "gate": None,
    }
    if not verdict["reserved"]:
        return result

    gate_payload = _gate_payload(action_text, verdict, context or {})
    result["gate"] = gate_payload
    if apply_gate:
        writer = gate_writer or _default_gate_writer
        result["gate"] = writer(**gate_payload)
    return result


def _default_gate_writer(**payload: Any) -> dict[str, Any]:
    from tools.queue.build import add_gate

    return add_gate(**payload)


def _gate_payload(action_text: str, verdict: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    digest = hashlib.sha256(action_text.encode("utf-8")).hexdigest()[:12]
    category = verdict.get("category") or "uncertain"
    stream = str(context.get("stream") or "Game")
    verbs = context.get("verbs") or ["approve", "reject", "checkpoint"]
    urgent = category in {"money_out", "public_outbound_send", "irreversible_legal_people"}
    return {
        "gate_id": f"reserved-class-{digest}",
        "stream": stream,
        "question": f"Reserved-Class blessing needed ({category}): {action_text.strip()}",
        "verbs": list(verbs),
        "blocking": True,
        "urgent": urgent,
    }


def _match_category(text: str, category: dict[str, Any]) -> str | None:
    terms: list[str] = []
    terms.extend(category.get("keywords", []))
    terms.extend(category.get("examples", []))
    terms.extend(category.get("escalation_verbs", []))
    terms.extend(category.get("signals", []))
    matched = _match_any(text, terms)
    if (
        matched
        and category.get("id") == "public_outbound_send"
        and _is_draft_only_public_copy(text)
    ):
        return None
    return matched


def _match_any(text: str, terms: list[str]) -> str | None:
    for term in terms:
        normalized = _normalize(term)
        if not normalized:
            continue
        if _contains_phrase(text, normalized):
            return term
    return None


def _money_signal(text: str) -> str | None:
    money_verbs = (
        "send",
        "transfer",
        "withdraw",
        "fund",
        "deposit",
        "pay",
        "purchase",
        "buy",
        "sell",
        "swap",
        "trade",
        "donate",
    )
    money_objects = (
        "$",
        " usd",
        " usdc",
        " sol",
        " btc",
        " eth",
        " wallet",
        " vault",
        " treasury",
        " account",
        " invoice",
        " funds",
        " money",
    )
    if any(_contains_phrase(text, verb) for verb in money_verbs) and any(obj in f" {text}" for obj in money_objects):
        for verb in money_verbs:
            if _contains_phrase(text, verb):
                return verb
    if re.search(r"\$\s*\d", text):
        return "$ amount"
    return None


def _contains_phrase(text: str, phrase: str) -> bool:
    if " " in phrase:
        return phrase in text
    return bool(re.search(rf"\b{re.escape(phrase)}\b", text))


def _is_clearly_delegable(text: str, policy: dict[str, Any]) -> bool:
    if _match_any(text, policy.get("delegable_examples", [])):
        return True
    words = set(text.split())
    return bool(words & _DRAFT_WORDS)


def _is_draft_only_public_copy(text: str) -> bool:
    draft_terms = ("draft", "prepare", "propose", "outline", "review")
    outbound_action_terms = (
        "send",
        "post",
        "publish",
        "dm",
        "text",
        "tweet",
        "announce",
        "broadcast",
        "submit",
        "reply to",
    )
    public_copy_terms = ("email", "message", "outreach", "post", "announcement", "reply")
    return (
        any(_contains_phrase(text, term) for term in draft_terms)
        and any(_contains_phrase(text, term) for term in public_copy_terms)
        and not any(_contains_phrase(text, term) for term in outbound_action_terms)
    )


def _context_text(context: dict[str, Any]) -> str:
    parts = []
    for key in ("mode", "surface", "target", "effect", "notes"):
        value = context.get(key)
        if value:
            parts.append(str(value))
    return " ".join(parts)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower().replace("_", " ").replace("-", " ")).strip()


def _verdict(reserved: bool, category: str | None, reason: str, confidence: float) -> dict[str, Any]:
    return {
        "reserved": reserved,
        "category": category,
        "reason": reason,
        "confidence": round(confidence, 2),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify a Reserved-Class action.")
    parser.add_argument("action", help="Action text to classify")
    parser.add_argument("--json", action="store_true", help="Print JSON verdict")
    args = parser.parse_args(argv)

    verdict = is_reserved(args.action)
    if args.json:
        print(json.dumps(verdict, indent=2, sort_keys=True))
    else:
        status = "reserved" if verdict["reserved"] else "delegable"
        print(f"{status}: {verdict['reason']} (confidence={verdict['confidence']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

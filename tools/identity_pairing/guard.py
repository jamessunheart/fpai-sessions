#!/usr/bin/env python3
"""Verified AI/user pairing guard.

This module is deliberately small and side-effect-light: pure helpers evaluate
whether an observed account identity still matches a verified pairing, while
optional async DB helpers let live Telegram surfaces fail closed when
AI_PAIRING_ENFORCE=1. It never sends messages, mutates live accounts, or reads
secret files.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "ai-pairing-guard.v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON = REPO_ROOT / "core" / "BUILD" / "signals" / "ai_pairing_security.json"
DEFAULT_MD = REPO_ROOT / "core" / "BUILD" / "signals" / "ai_pairing_security.md"
VERIFIED_STATUSES = {"verified", "active"}
BLOCK_STATUSES = {"revoked", "suspended", "disabled", "compromised"}
STALE_DAYS_DEFAULT = 90


@dataclasses.dataclass(frozen=True)
class ObservedIdentity:
    provider: str
    provider_user_id: str
    chat_id: str
    username: str = ""
    first_name: str = ""
    last_name: str = ""

    @classmethod
    def from_telegram(cls, msg: dict[str, Any]) -> "ObservedIdentity":
        user = msg.get("from") or {}
        chat = msg.get("chat") or {}
        provider_user_id = str(user.get("id") or "")
        return cls(
            provider="telegram",
            provider_user_id=provider_user_id,
            chat_id=str(chat.get("id") or provider_user_id),
            username=str(user.get("username") or ""),
            first_name=str(user.get("first_name") or ""),
            last_name=str(user.get("last_name") or ""),
        )


@dataclasses.dataclass(frozen=True)
class PairingRecord:
    subject_id: str
    ai_agent: str
    provider: str
    provider_user_id: str
    chat_id: str
    status: str
    verified_at: dt.datetime | None = None
    assurance_level: int = 1
    identity_fingerprint: str = ""
    username: str = ""
    risk_flags: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class PairingDecision:
    allowed: bool
    action: str
    severity: int
    reasons: tuple[str, ...]
    subject_id: str = ""
    ai_agent: str = ""

    def to_json(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def utc_stamp(now: dt.datetime | None = None) -> str:
    return (now or utc_now()).astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(value: Any) -> dt.datetime | None:
    if not value:
        return None
    if isinstance(value, dt.datetime):
        parsed = value
    else:
        try:
            parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def identity_fingerprint(identity: ObservedIdentity, secret: str) -> str:
    """Stable HMAC fingerprint for drift checks without storing raw handles."""
    if not secret:
        raise ValueError("identity fingerprint secret is required")
    body = "|".join((
        identity.provider.lower(),
        identity.provider_user_id,
        identity.chat_id,
        identity.username.lower(),
    ))
    return hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()


def pairing_from_row(row: dict[str, Any]) -> PairingRecord:
    flags = row.get("risk_flags") or ()
    if isinstance(flags, str):
        try:
            parsed = json.loads(flags)
            flags = parsed if isinstance(parsed, list) else [flags]
        except json.JSONDecodeError:
            flags = [flags]
    return PairingRecord(
        subject_id=str(row.get("subject_id") or ""),
        ai_agent=str(row.get("ai_agent") or ""),
        provider=str(row.get("provider") or ""),
        provider_user_id=str(row.get("provider_user_id") or ""),
        chat_id=str(row.get("chat_id") or ""),
        status=str(row.get("status") or ""),
        verified_at=parse_time(row.get("verified_at")),
        assurance_level=int(row.get("assurance_level") or 1),
        identity_fingerprint=str(row.get("identity_fingerprint") or ""),
        username=str(row.get("username") or ""),
        risk_flags=tuple(str(item) for item in flags),
    )


def evaluate_pairing(
    pairing: PairingRecord | None,
    observed: ObservedIdentity,
    *,
    ai_agent: str,
    fingerprint_secret: str = "",
    now: dt.datetime | None = None,
    stale_days: int = STALE_DAYS_DEFAULT,
) -> PairingDecision:
    current = now or utc_now()
    reasons: list[str] = []
    action = "allow"
    severity = 0

    if pairing is None:
        return PairingDecision(False, "block", 6, ("no_verified_pairing",), ai_agent=ai_agent)

    if pairing.status.lower() in BLOCK_STATUSES:
        reasons.append(f"pairing_status_{pairing.status.lower()}")
    elif pairing.status.lower() not in VERIFIED_STATUSES:
        reasons.append("pairing_not_verified")

    if pairing.ai_agent and pairing.ai_agent != ai_agent:
        reasons.append("ai_agent_mismatch")
    if pairing.provider.lower() != observed.provider.lower():
        reasons.append("provider_mismatch")
    if pairing.provider_user_id != observed.provider_user_id:
        reasons.append("provider_user_id_mismatch")
    if pairing.chat_id and pairing.chat_id != observed.chat_id:
        reasons.append("chat_id_mismatch")
    if pairing.verified_at is None:
        reasons.append("missing_verified_at")
    elif (current - pairing.verified_at).days > stale_days:
        reasons.append("verification_stale")
    if pairing.assurance_level < 2:
        reasons.append("assurance_too_low")
    if pairing.risk_flags:
        reasons.append("risk_flags_present")

    if fingerprint_secret and pairing.identity_fingerprint:
        try:
            actual = identity_fingerprint(observed, fingerprint_secret)
            if not hmac.compare_digest(pairing.identity_fingerprint, actual):
                reasons.append("identity_fingerprint_mismatch")
        except ValueError:
            reasons.append("fingerprint_unavailable")
    elif pairing.identity_fingerprint:
        reasons.append("fingerprint_secret_missing")

    blocking = {
        "no_verified_pairing",
        "provider_mismatch",
        "provider_user_id_mismatch",
        "chat_id_mismatch",
        "identity_fingerprint_mismatch",
    }
    if any(reason in blocking for reason in reasons) or any(reason.startswith("pairing_status_") for reason in reasons):
        action = "block"
        severity = 6
    elif reasons:
        action = "challenge"
        severity = 4
    return PairingDecision(
        allowed=action == "allow",
        action=action,
        severity=severity,
        reasons=tuple(reasons),
        subject_id=pairing.subject_id,
        ai_agent=pairing.ai_agent or ai_agent,
    )


def detect_pairing_anomalies(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    by_provider_user: dict[tuple[str, str], set[str]] = {}
    by_chat: dict[tuple[str, str], set[str]] = {}
    duplicate_agents: dict[tuple[str, str], int] = {}
    findings: list[dict[str, Any]] = []
    for row in rows:
        pairing = pairing_from_row(row)
        if not pairing.provider_user_id:
            continue
        by_provider_user.setdefault((pairing.provider, pairing.provider_user_id), set()).add(pairing.subject_id)
        by_chat.setdefault((pairing.provider, pairing.chat_id), set()).add(pairing.subject_id)
        duplicate_agents[(pairing.ai_agent, pairing.subject_id)] = duplicate_agents.get((pairing.ai_agent, pairing.subject_id), 0) + 1
        if pairing.status.lower() in BLOCK_STATUSES:
            findings.append({
                "severity": 5,
                "title": "Blocked pairing remains present",
                "evidence": f"{pairing.ai_agent}:{pairing.subject_id}:{pairing.status}",
                "next_action": "Keep blocked rows out of authorization decisions and review recent events for attempted reuse.",
            })
    for (provider, provider_user_id), subjects in by_provider_user.items():
        if len(subjects) > 1:
            findings.append({
                "severity": 6,
                "title": "One provider user id is bound to multiple subjects",
                "evidence": f"{provider}:{provider_user_id} -> {sorted(subjects)}",
                "next_action": "Freeze the affected subjects until a human verifies which binding is current.",
            })
    for (provider, chat_id), subjects in by_chat.items():
        if chat_id and len(subjects) > 1:
            findings.append({
                "severity": 6,
                "title": "One chat id is bound to multiple subjects",
                "evidence": f"{provider}:{chat_id} -> {sorted(subjects)}",
                "next_action": "Treat this as possible account sharing or takeover and require re-verification.",
            })
    for (ai_agent, subject), count in duplicate_agents.items():
        if ai_agent and subject and count > 1:
            findings.append({
                "severity": 4,
                "title": "Duplicate AI-agent pairing rows",
                "evidence": f"{ai_agent}:{subject} count={count}",
                "next_action": "Collapse duplicate rows before enabling strict enforcement.",
            })
    return findings


def render_report(report: dict[str, Any]) -> str:
    lines = [
        "# AI Pairing Security Report",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Pairings scanned: {report['summary']['pairings_scanned']}",
        f"- Findings: {report['summary']['findings']}",
        f"- Max severity: {report['summary']['max_severity']}",
        "",
    ]
    if not report["findings"]:
        lines.append("No pairing anomalies found in the supplied data.")
    for finding in report["findings"]:
        lines.extend([
            f"## {finding['title']}",
            f"- Severity: {finding['severity']}",
            f"- Evidence: `{finding['evidence']}`",
            f"- Next: {finding['next_action']}",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def run_report(
    rows: Iterable[dict[str, Any]],
    *,
    json_path: Path = DEFAULT_JSON,
    markdown_path: Path = DEFAULT_MD,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    row_list = list(rows)
    findings = detect_pairing_anomalies(row_list)
    report = {
        "schema": SCHEMA,
        "generated_at": utc_stamp(now),
        "summary": {
            "pairings_scanned": len(row_list),
            "findings": len(findings),
            "max_severity": max((int(f["severity"]) for f in findings), default=0),
        },
        "findings": findings,
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_report(report), encoding="utf-8")
    return report


def enforcement_enabled() -> bool:
    return os.environ.get("AI_PAIRING_ENFORCE", "").strip().lower() in {"1", "true", "yes"}


def fingerprint_secret() -> str:
    return os.environ.get("AI_PAIRING_FINGERPRINT_SECRET", "")


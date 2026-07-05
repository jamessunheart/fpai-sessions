#!/usr/bin/env python3
"""Sandbox AI Voice Receptionist intake proof.

This module converts a transcript fixture into a review-ready appointment
payload. It never calls a phone, sends a message, or writes to a calendar.
"""
from __future__ import annotations

import argparse
import importlib.util as _ilu
import json
import re
from pathlib import Path
from typing import Any

try:
    from tools.allocation import capability_ledger
except ModuleNotFoundError:
    _LEDGER_PATH = Path(__file__).resolve().parents[2] / "tools" / "allocation" / "capability_ledger.py"
    _spec = _ilu.spec_from_file_location("fpai_capability_ledger", _LEDGER_PATH)
    if _spec is None or _spec.loader is None:
        raise
    capability_ledger = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(capability_ledger)


SCHEMA = "fpai.voice_receptionist.fixture.v1"
OPPORTUNITY_ID = "ai-voice-receptionist"
REQUIRED_FIELDS = ("caller_name", "caller_phone", "business_name", "service_requested", "requested_start")
MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
TZ_OFFSETS = {
    "pacific": "-07:00",
    "pt": "-07:00",
    "mountain": "-06:00",
    "central": "-05:00",
    "eastern": "-04:00",
}
TZ_NAMES = {
    "pacific": "America/Los_Angeles",
    "pt": "America/Los_Angeles",
    "mountain": "America/Denver",
    "central": "America/Chicago",
    "eastern": "America/New_York",
}


def load_fixture(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def transcript_text(fixture: dict[str, Any]) -> str:
    turns = fixture.get("transcript") or []
    if isinstance(turns, str):
        return turns
    lines = []
    for turn in turns:
        if isinstance(turn, dict):
            speaker = str(turn.get("speaker") or "").strip()
            text = str(turn.get("text") or "").strip()
            lines.append(f"{speaker}: {text}" if speaker else text)
        else:
            lines.append(str(turn))
    return "\n".join(lines)


def build_payload(fixture: dict[str, Any]) -> dict[str, Any]:
    text = transcript_text(fixture)
    extracted = extract_intake(text, fixture_date=str(fixture.get("fixture_date") or ""))
    missing = [field for field in REQUIRED_FIELDS if not extracted.get(field)]
    payload = {
        "schema": SCHEMA,
        "opportunity_id": OPPORTUNITY_ID,
        "fixture_id": fixture.get("fixture_id", "unnamed-fixture"),
        "mode": "sandbox_fixture",
        "status": "requires_human_review" if not missing else "incomplete_intake",
        "live_phone_number_touched": False,
        "live_send_performed": False,
        "calendar_write_performed": False,
        "marginal_cost_usd": 0,
        "caller": {
            "name": extracted.get("caller_name", ""),
            "phone": extracted.get("caller_phone", ""),
            "email": extracted.get("caller_email", ""),
        },
        "appointment_request": {
            "business_name": extracted.get("business_name", ""),
            "service_requested": extracted.get("service_requested", ""),
            "requested_start": extracted.get("requested_start", ""),
            "timezone": extracted.get("timezone", ""),
            "fallback_window": extracted.get("fallback_window", ""),
            "intake_problem": extracted.get("intake_problem", ""),
        },
        "quality_gate": {
            "required_fields": list(REQUIRED_FIELDS),
            "missing_fields": missing,
            "passed": not missing,
            "booking_confirmed": False,
            "reason": "sandbox proof creates an intake payload only; live availability and booking remain unwired",
        },
        "rollback": rollback_path(fixture.get("fixture_id", "unnamed-fixture")),
    }
    return payload


def extract_intake(text: str, *, fixture_date: str = "") -> dict[str, str]:
    normalized = " ".join(line.strip() for line in text.splitlines() if line.strip())
    return {
        "caller_name": _first_group(normalized, r"\bname is ([A-Z][A-Za-z .'-]+?)(?:\.|,| and\b)"),
        "caller_phone": normalize_phone(_first_group(normalized, r"\bphone is ([+()0-9 .-]{7,})")),
        "caller_email": _first_group(normalized, r"\bemail is ([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"),
        "business_name": _first_group(normalized, r"\bbusiness is ([A-Z][A-Za-z0-9 &'#.-]+?)(?:\.|,| and\b)"),
        "service_requested": _clean_service(_first_group(normalized, r"\bI need (?:an? )?(.+?)(?:\.|,| for\b)")),
        "requested_start": parse_requested_start(normalized, fixture_date=fixture_date),
        "timezone": parse_timezone(normalized),
        "fallback_window": _first_group(normalized, r"\bIf not, ([^.]+?) is fine\b"),
        "intake_problem": _first_group(normalized, r"\b(We miss calls[^.]+)\."),
    }


def rollback_path(fixture_id: str) -> dict[str, Any]:
    return {
        "available": True,
        "scope": "sandbox-only",
        "steps": [
            "Delete generated appointment payload artifacts for this fixture.",
            "Delete generated capability-ledger fixture rows for this spec.",
            "Revert this branch before merge if the payload contract is wrong.",
            "Keep telephony, SMS, calendar, and live-number adapters disconnected.",
        ],
        "runtime_hold": "No live runtime exists; do not wire a phone number or calendar without a new approved activation spec.",
        "fixture_id": fixture_id,
    }


def capability_learning_row(payload: dict[str, Any]) -> dict[str, Any]:
    passed = bool(payload.get("quality_gate", {}).get("passed"))
    return capability_ledger.capability_row(
        source_type="build_fixture",
        source_id="SPEC_d205_auto-spot-topple-ai-voice-recept",
        title="AI Voice Receptionist sandbox intake proof",
        scores={"knowledge_gained": 1 if passed else 0, "automation": 1 if passed else 0},
        expected_capability_gain={"knowledge_gained": 1, "automation": 1},
        reusable_intelligence="core/BUILD/results/SPEC_d205_auto-spot-topple-ai-voice-recept.result.md",
        basis=(
            "Fixture transcript produced the expected appointment-intake payload and rollback path. "
            "No live phone number, send, calendar write, outreach, or metered API call was used."
        ),
        reviewed_by="codex-sandbox-tests",
    )


def write_json(path: Path | str, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _first_group(text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.I)
    return match.group(1).strip() if match else ""


def _clean_service(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" .")


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return value.strip()


def parse_requested_start(text: str, *, fixture_date: str = "") -> str:
    match = re.search(
        r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+"
        r"([A-Za-z]+)\s+(\d{1,2})\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(AM|PM)\s+([A-Za-z]+)",
        text,
        flags=re.I,
    )
    if not match:
        return ""
    month_name, day, hour, minute, meridiem, tz_word = match.groups()
    month = MONTHS.get(month_name.lower())
    if not month:
        return ""
    year = fixture_date[:4] if re.match(r"\d{4}-", fixture_date) else "2026"
    hour_number = int(hour)
    if meridiem.lower() == "pm" and hour_number != 12:
        hour_number += 12
    if meridiem.lower() == "am" and hour_number == 12:
        hour_number = 0
    offset = TZ_OFFSETS.get(tz_word.lower(), "")
    if not offset:
        return ""
    return f"{year}-{month:02d}-{int(day):02d}T{hour_number:02d}:{int(minute or 0):02d}:00{offset}"


def parse_timezone(text: str) -> str:
    match = re.search(r"\bat\s+\d{1,2}(?::\d{2})?\s*(?:AM|PM)\s+([A-Za-z]+)", text, flags=re.I)
    if not match:
        return ""
    return TZ_NAMES.get(match.group(1).lower(), "")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--capability-ledger", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    payload = build_payload(load_fixture(args.fixture))
    if args.output:
        write_json(args.output, payload)
    if args.capability_ledger:
        capability_ledger.append_row(args.capability_ledger, capability_learning_row(payload))
    if args.json or not args.output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["quality_gate"]["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

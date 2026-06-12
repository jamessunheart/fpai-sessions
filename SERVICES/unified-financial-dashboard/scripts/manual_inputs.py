#!/usr/bin/env python3
"""
Initialize and validate Financial Hub manual inputs.

This script only touches the local ignored manual input file under var/.
It never reads secrets and never writes upstream treasury state.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


SERVICE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_DIR.parent.parent
DEFAULT_PATH = REPO_ROOT / "var" / "financial-hub" / "manual_financial_inputs.json"
EXAMPLE_PATH = SERVICE_DIR / "manual_financial_inputs.example.json"

SUSPICIOUS_KEY_PATTERN = re.compile(
    r"(secret|token|password|private|seed|mnemonic|api[_-]?key|auth|cookie|credential|account_number)",
    re.IGNORECASE,
)
SUSPICIOUS_VALUE_PATTERN = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|xox[baprs]-|-----BEGIN [A-Z ]*PRIVATE KEY-----|mnemonic|seed phrase)",
    re.IGNORECASE,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def default_payload() -> Dict[str, Any]:
    if EXAMPLE_PATH.exists():
        payload = load_json(EXAMPLE_PATH)
    else:
        payload = {
            "schema": "manual_financial_inputs.v1",
            "updated_by": "human",
            "cash_on_hand_usd": None,
            "monthly_burn_usd": None,
            "notes": "Redacted non-secret values only.",
        }
    payload["updated_at"] = utc_now_iso()
    return payload


def write_payload(path: Path, payload: Dict[str, Any], force: bool = False) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists. Re-run with --force to replace it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_or_default(path: Path) -> Dict[str, Any]:
    if path.exists():
        return load_json(path)
    return default_payload()


def apply_updates(
    payload: Dict[str, Any],
    cash_on_hand_usd: Optional[float] = None,
    monthly_burn_usd: Optional[float] = None,
    notes: Optional[str] = None,
    updated_by: Optional[str] = None,
) -> Dict[str, Any]:
    updated = dict(payload)
    if cash_on_hand_usd is not None:
        updated["cash_on_hand_usd"] = cash_on_hand_usd
    if monthly_burn_usd is not None:
        updated["monthly_burn_usd"] = monthly_burn_usd
    if notes is not None:
        updated["notes"] = notes
    if updated_by is not None:
        updated["updated_by"] = updated_by
    updated["schema"] = "manual_financial_inputs.v1"
    updated["updated_at"] = utc_now_iso()
    return updated


def validate_nonnegative_number(name: str, value: Any, errors: List[str], warnings: List[str]) -> None:
    if value is None:
        warnings.append(f"{name} is not set.")
        return
    if not isinstance(value, (int, float)):
        errors.append(f"{name} must be a number or null.")
        return
    if value < 0:
        errors.append(f"{name} must not be negative.")


def walk_for_suspicious_content(value: Any, path: str, errors: List[str]) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            key_path = f"{path}.{key}" if path else str(key)
            if SUSPICIOUS_KEY_PATTERN.search(str(key)):
                errors.append(f"Suspicious key not allowed: {key_path}")
            walk_for_suspicious_content(nested, key_path, errors)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            walk_for_suspicious_content(nested, f"{path}[{index}]", errors)
    elif isinstance(value, str) and SUSPICIOUS_VALUE_PATTERN.search(value):
        errors.append(f"Suspicious secret-like value at: {path}")


def validate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(payload, dict):
        return {"valid": False, "errors": ["Payload must be a JSON object."], "warnings": []}

    if payload.get("schema") != "manual_financial_inputs.v1":
        errors.append("schema must be manual_financial_inputs.v1.")

    updated_at = payload.get("updated_at")
    if not isinstance(updated_at, str):
        errors.append("updated_at must be an ISO timestamp string.")
    else:
        try:
            datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        except ValueError:
            errors.append("updated_at must be a valid ISO timestamp.")

    validate_nonnegative_number("cash_on_hand_usd", payload.get("cash_on_hand_usd"), errors, warnings)
    validate_nonnegative_number("monthly_burn_usd", payload.get("monthly_burn_usd"), errors, warnings)
    walk_for_suspicious_content(payload, "", errors)

    return {"valid": not errors, "errors": errors, "warnings": warnings}


def validate_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "valid": False,
            "errors": [f"Manual input file not found: {path}"],
            "warnings": [],
        }
    try:
        payload = load_json(path)
    except json.JSONDecodeError as exc:
        return {"valid": False, "errors": [f"Invalid JSON: {exc}"], "warnings": []}
    result = validate_payload(payload)
    result["path"] = str(path)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize and validate Financial Hub manual inputs.")
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH, help="Manual input JSON path.")
    parser.add_argument("--init", action="store_true", help="Create a redacted manual input file if missing.")
    parser.add_argument("--force", action="store_true", help="Replace an existing file when used with --init.")
    parser.add_argument("--cash-on-hand-usd", type=float, help="Set redacted cash on hand.")
    parser.add_argument("--monthly-burn-usd", type=float, help="Set redacted monthly burn.")
    parser.add_argument("--notes", help="Set non-secret notes.")
    parser.add_argument("--updated-by", help="Set the updater label.")
    parser.add_argument("--validate", action="store_true", help="Validate the manual input file.")
    parser.add_argument("--print-path", action="store_true", help="Print the target manual input path.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.print_path:
        print(args.path)

    if args.init:
        try:
            write_payload(args.path, default_payload(), force=args.force)
            print(f"initialized: {args.path}")
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            return 2

    wants_update = any(
        value is not None
        for value in [args.cash_on_hand_usd, args.monthly_burn_usd, args.notes, args.updated_by]
    )
    if wants_update:
        payload = apply_updates(
            load_or_default(args.path),
            cash_on_hand_usd=args.cash_on_hand_usd,
            monthly_burn_usd=args.monthly_burn_usd,
            notes=args.notes,
            updated_by=args.updated_by,
        )
        result = validate_payload(payload)
        if not result["valid"]:
            print(json.dumps(result, indent=2), file=sys.stderr)
            return 1
        write_payload(args.path, payload, force=True)
        print(f"updated: {args.path}")

    if args.validate or args.init or wants_update:
        result = validate_file(args.path)
        print(json.dumps(result, indent=2))
        return 0 if result["valid"] else 1

    if not args.print_path:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""G3 nurture router for the inbound Full Potential assessment funnel.

This module prepares listmonk/n8n payloads. It does not send email or call a
live workflow. Public-channel activation remains a James gate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DIMENSIONS = ("capital", "time", "attention", "people", "ai", "knowledge")
ROUTE_TABLE = {
    "capital": {
        "route": "savings_split",
        "offer": "Savings Split implementation",
        "listmonk_list": "fpai-savings-split-nurture",
    },
    "time": {
        "route": "blueprint",
        "offer": "Blueprint automation build",
        "listmonk_list": "fpai-blueprint-nurture",
    },
    "people": {
        "route": "blueprint",
        "offer": "Builder placement or team training",
        "listmonk_list": "fpai-builder-nurture",
    },
    "attention": {
        "route": "advisory",
        "offer": "Founder-level advisory",
        "listmonk_list": "fpai-advisory-nurture",
    },
    "ai": {
        "route": "partnership",
        "offer": "Intelligence Partnership",
        "listmonk_list": "fpai-partnership-nurture",
    },
    "knowledge": {
        "route": "partnership",
        "offer": "Intelligence Partnership",
        "listmonk_list": "fpai-partnership-nurture",
    },
}


@dataclass(frozen=True)
class EmailAsset:
    asset_id: str
    subject: str
    body: str
    day_offset: int

    def ledger_row(self, *, route: str, lead_id: str, source_asset_id: str) -> dict[str, Any]:
        return {
            "schema": "fpai.growth.asset.v1",
            "asset_id": self.asset_id,
            "type": "email",
            "status": "alive",
            "parent_id": source_asset_id,
            "generation": 0,
            "genome": {
                "frame": route,
                "hook": self.subject,
                "audience": "assessment_lead",
                "format": "nurture_email",
                "channel": "email",
            },
            "lead_id": lead_id,
            "created_at": now_utc(),
            "outcomes": {"impressions": 0, "clicks": 0, "leads": 0, "audits": 0, "deals": 0, "value_usd": 0},
        }


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1(":".join(parts).encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{digest}"


def load_lead(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {}
        for line in text.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                data[key.strip().lower().replace(" ", "_")] = value.strip()
    if not isinstance(data, dict):
        raise ValueError("lead payload must be a JSON object or key:value text")
    return data


def coerce_scores(lead: dict[str, Any]) -> dict[str, int]:
    raw = lead.get("scores") or lead.get("dimension_scores") or {}
    scores: dict[str, int] = {}
    for dimension in DIMENSIONS:
        value = raw.get(dimension, lead.get(dimension))
        try:
            scores[dimension] = max(0, min(100, int(value)))
        except (TypeError, ValueError):
            scores[dimension] = proxy_score(lead, dimension)
    return scores


def proxy_score(lead: dict[str, Any], dimension: str) -> int:
    text = json.dumps(lead, sort_keys=True).lower()
    penalties = {
        "capital": ("waste", "spend", "budget", "saas", "cash", "expensive"),
        "time": ("manual", "hours", "slow", "spreadsheet", "handoff"),
        "attention": ("overwhelmed", "focus", "decision", "priority", "context"),
        "people": ("hiring", "team", "training", "capacity", "delegation"),
        "ai": ("chatgpt", "automation", "ai", "zapier", "workflow"),
        "knowledge": ("documentation", "knowledge", "silo", "process", "reporting"),
    }
    hits = sum(1 for token in penalties[dimension] if token in text)
    return max(25, 72 - hits * 14)


def route_lead(lead: dict[str, Any]) -> dict[str, Any]:
    scores = coerce_scores(lead)
    weakest = min(DIMENSIONS, key=lambda item: (scores[item], item))
    route = ROUTE_TABLE[weakest]
    lead_id = str(lead.get("lead_id") or lead.get("id") or stable_id("lead", json.dumps(lead, sort_keys=True)))
    source_asset_id = str(
        lead.get("utm_campaign")
        or lead.get("source")
        or lead.get("asset_id")
        or "assessment-direct"
    )
    return {
        "lead_id": lead_id,
        "email": lead.get("email", ""),
        "name": lead.get("name", ""),
        "company": lead.get("company", lead.get("company_name", "")),
        "scores": scores,
        "weakest_dimension": weakest,
        "route": route["route"],
        "offer": route["offer"],
        "listmonk_list": route["listmonk_list"],
        "source_asset_id": source_asset_id,
        "utm_campaign": source_asset_id,
        "routed_at": now_utc(),
    }


def sequence_for_route(route: dict[str, Any]) -> list[EmailAsset]:
    route_name = route["route"]
    offer = route["offer"]
    weak = route["weakest_dimension"]
    lead_id = route["lead_id"]
    source_asset_id = route["source_asset_id"]
    subjects = [
        f"Your {weak} bottleneck is the first useful signal",
        "The Monday move before any purchase",
        "What better allocation would change this month",
        f"How {offer} would work if it is the right fit",
        "Keep the assessment useful either way",
    ]
    bodies = [
        f"Your assessment routed to {offer} because {weak} scored lowest. Start by naming the one recurring decision or handoff that keeps pulling resources away from higher-value work.",
        "Before buying anything, pick one repeated task and write down who owns it, how often it happens, and what proof would show it improved. That is enough to make the next allocation clearer.",
        "The goal is not more tools. The goal is a resource loop where capital, time, attention, people, AI, and knowledge move toward future capability and prove what changed.",
        f"If we work together, {offer} starts from your assessment data and turns the top opportunity into a scoped implementation. No scarcity, no pressure, just the next useful proof.",
        "Whether or not you continue, keep the score as a map. Re-audit after one real change and compare the weak dimension against today.",
    ]
    offsets = [0, 2, 5, 9, 14]
    emails = []
    for index, (subject, body, offset) in enumerate(zip(subjects, bodies, offsets), start=1):
        emails.append(
            EmailAsset(
                asset_id=stable_id("email", lead_id, source_asset_id, route_name, str(index)),
                subject=subject,
                body=body,
                day_offset=offset,
            )
        )
    return emails


def listmonk_payload(route: dict[str, Any], email: EmailAsset) -> dict[str, Any]:
    return {
        "subscriber": {
            "email": route.get("email", ""),
            "name": route.get("name", ""),
            "attribs": {
                "lead_id": route["lead_id"],
                "company": route.get("company", ""),
                "route": route["route"],
                "weakest_dimension": route["weakest_dimension"],
                "source_asset_id": route["source_asset_id"],
            },
        },
        "list": route["listmonk_list"],
        "campaign": {
            "name": email.asset_id,
            "subject": email.subject,
            "body": email.body,
            "send_after_days": email.day_offset,
        },
    }


def n8n_payload(route: dict[str, Any], sequence: list[EmailAsset]) -> dict[str, Any]:
    return {
        "workflow": "fpai-assessment-nurture-v1",
        "mode": "dry_run_payload",
        "lead": route,
        "steps": [
            {
                "kind": "listmonk_campaign",
                "asset_id": email.asset_id,
                "send_after_days": email.day_offset,
                "listmonk": listmonk_payload(route, email),
            }
            for email in sequence
        ],
    }


def build_nurture_packet(lead: dict[str, Any]) -> dict[str, Any]:
    route = route_lead(lead)
    sequence = sequence_for_route(route)
    return {
        "schema": "fpai.growth.nurture_packet.v1",
        "route": route,
        "n8n": n8n_payload(route, sequence),
        "ledger_rows": [
            email.ledger_row(
                route=route["route"],
                lead_id=route["lead_id"],
                source_asset_id=route["source_asset_id"],
            )
            for email in sequence
        ],
    }


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lead", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--ledger-jsonl", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    packet = build_nurture_packet(load_lead(args.lead))
    text = json.dumps(packet, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    if args.ledger_jsonl:
        append_jsonl(args.ledger_jsonl, packet["ledger_rows"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

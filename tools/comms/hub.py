#!/usr/bin/env python3
"""Rung 4 comms hub: triage, draft, stage, gate.

V1 never sends. It stages reviewable drafts and opens a Reserved-Class
human-edge gate for any outbound send candidate.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.comms.channels.email import ingest_read_only
from tools.queue.build import add_gate
from tools.reserved.classify import is_reserved

DEFAULT_LANE = REPO_ROOT / "docs" / "codex" / "COMMS_LANE.md"
DEFAULT_QUEUE = REPO_ROOT / "core" / "STATE" / "HUMAN_EDGE_QUEUE.json"
FOLLOW_UP_NOTE = (
    "Live-channel follow-up: scoped pass needed for the failing intake-agent on host 198 "
    "(Fable flag 2026-06-09). This hub does not fix it blind."
)

TRIAGE_CLASSES = {"needs-reply", "fyi", "action", "spam"}


@dataclasses.dataclass(frozen=True)
class TriageResult:
    message_id: str
    channel: str
    sender: str
    subject: str
    classification: str
    summary: str
    suggested_next: str

    def __getitem__(self, key: str) -> Any:
        if key == "class":
            return self.classification
        return getattr(self, key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "channel": self.channel,
            "sender": self.sender,
            "subject": self.subject,
            "class": self.classification,
            "summary": self.summary,
            "suggested_next": self.suggested_next,
        }


@dataclasses.dataclass(frozen=True)
class Draft:
    draft_id: str
    message_id: str
    recipient: str
    subject: str
    body: str
    gate_id: str
    reserved_verdict: dict[str, Any]


@dataclasses.dataclass(frozen=True)
class CommsRun:
    triage: list[TriageResult]
    drafts: list[Draft]
    gates: list[dict[str, Any]]
    lane_path: Path | None
    dry_run: bool
    follow_up: str = FOLLOW_UP_NOTE


def triage(messages: list[dict[str, Any]]) -> list[TriageResult]:
    """Classify and summarize a batch of inbound messages."""
    return [triage_one(message) for message in messages]


def triage_one(message: dict[str, Any]) -> TriageResult:
    text = _message_text(message)
    classification = _classify_message(text)
    return TriageResult(
        message_id=str(message.get("id") or _stable_id(text)),
        channel=str(message.get("channel") or "email"),
        sender=str(message.get("from") or message.get("sender") or "unknown"),
        subject=str(message.get("subject") or "(no subject)"),
        classification=classification,
        summary=_summary(message),
        suggested_next=_suggested_next(classification, message),
    )


def draft(message: dict[str, Any], result: TriageResult | None = None) -> Draft | None:
    """Create a staged outbound draft for messages that need a reply/action."""
    triage_result = result or triage_one(message)
    if triage_result.classification not in {"needs-reply", "action"}:
        return None
    recipient = triage_result.sender
    subject = _reply_subject(triage_result.subject)
    draft_id = f"comms-draft-{_stable_id(triage_result.message_id + recipient + subject)}"
    body = _draft_body(message, triage_result)
    action_text = f"Send draft to {recipient}: {subject}"
    verdict = is_reserved(action_text, {"surface": "email", "target": recipient, "stream": "Ventures"})
    return Draft(
        draft_id=draft_id,
        message_id=triage_result.message_id,
        recipient=recipient,
        subject=subject,
        body=body,
        gate_id=f"comms-send-{_stable_id(draft_id)}",
        reserved_verdict=verdict,
    )


def process_messages(
    messages: list[dict[str, Any]],
    *,
    dry_run: bool = True,
    lane_path: Path | str = DEFAULT_LANE,
    queue_path: Path | str = DEFAULT_QUEUE,
) -> CommsRun:
    """Triage, draft, and optionally stage/gate a batch."""
    triage_results = triage(messages)
    drafts = [created for message, result in zip(messages, triage_results) if (created := draft(message, result))]
    gates: list[dict[str, Any]] = []
    if not dry_run:
        write_lane(triage_results, drafts, lane_path)
        for staged in drafts:
            if not staged.reserved_verdict.get("reserved"):
                raise RuntimeError("outbound draft did not classify as Reserved-Class")
            gates.append(_gate_send(staged, queue_path))
    return CommsRun(
        triage=triage_results,
        drafts=drafts,
        gates=gates,
        lane_path=Path(lane_path) if not dry_run else None,
        dry_run=dry_run,
    )


def write_lane(
    triage_results: list[TriageResult],
    drafts: list[Draft],
    path: Path | str = DEFAULT_LANE,
) -> Path:
    lane_path = Path(path)
    lane_path.parent.mkdir(parents=True, exist_ok=True)
    lane_path.write_text(render_lane(triage_results, drafts), encoding="utf-8")
    return lane_path


def render_lane(triage_results: list[TriageResult], drafts: list[Draft]) -> str:
    lines = [
        "# Comms Lane",
        "",
        "*Generated by `tools/comms/hub.py`. Review lane only; V1 never sends.*",
        "",
        f"- generated: `{dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()}`",
        f"- messages triaged: `{len(triage_results)}`",
        f"- drafts staged: `{len(drafts)}`",
        "- send policy: every outbound send is Reserved-Class and must be blessed by James",
        "",
        "## Triage",
        "",
    ]
    for item in triage_results:
        lines.extend(
            [
                f"### {item.message_id}",
                f"- channel: `{item.channel}`",
                f"- from: `{item.sender}`",
                f"- class: `{item.classification}`",
                f"- summary: {item.summary}",
                f"- suggested next: {item.suggested_next}",
                "",
            ]
        )
    lines.extend(["## Drafts", ""])
    if not drafts:
        lines.extend(["_No outbound drafts staged._", ""])
    for staged in drafts:
        lines.extend(
            [
                f"### {staged.draft_id}",
                f"- message: `{staged.message_id}`",
                f"- to: `{staged.recipient}`",
                f"- subject: {staged.subject}",
                f"- reserved: `{str(staged.reserved_verdict['reserved']).lower()}`",
                f"- category: `{staged.reserved_verdict['category']}`",
                f"- gate id: `{staged.gate_id}`",
                "",
                "```text",
                staged.body,
                "```",
                "",
            ]
        )
    lines.extend(["## Live Channel Follow-Up", "", f"- {FOLLOW_UP_NOTE}", ""])
    return "\n".join(lines)


def run_fixture(
    fixture_path: Path | str,
    *,
    dry_run: bool = True,
    lane_path: Path | str = DEFAULT_LANE,
    queue_path: Path | str = DEFAULT_QUEUE,
) -> CommsRun:
    return process_messages(
        ingest_read_only(fixture=fixture_path),
        dry_run=dry_run,
        lane_path=lane_path,
        queue_path=queue_path,
    )


def run_payload(run: CommsRun) -> dict[str, Any]:
    return {
        "dry_run": run.dry_run,
        "lane_path": str(run.lane_path) if run.lane_path else None,
        "follow_up": run.follow_up,
        "triage": [item.to_dict() for item in run.triage],
        "drafts": [dataclasses.asdict(item) for item in run.drafts],
        "gates": run.gates,
    }


def _gate_send(staged: Draft, queue_path: Path | str) -> dict[str, Any]:
    return add_gate(
        gate_id=staged.gate_id,
        stream="Ventures",
        question=f"Send draft to {staged.recipient}? {staged.subject}",
        verbs=["approve", "edit", "skip"],
        blocking=True,
        urgent=True,
        path=queue_path,
    )


def _classify_message(text: str) -> str:
    low = text.lower()
    if any(term in low for term in ("unsubscribe", "limited time offer", "seo services", "crypto giveaway", "viagra")):
        return "spam"
    if any(term in low for term in ("please send", "can you", "could you", "would love", "interested", "question", "?")):
        return "needs-reply"
    if any(term in low for term in ("invoice", "deadline", "schedule", "book", "confirm", "approval needed", "action needed")):
        return "action"
    return "fyi"


def _summary(message: dict[str, Any]) -> str:
    body = str(message.get("body") or "").strip()
    subject = str(message.get("subject") or "").strip()
    source = body or subject
    sentence = re.split(r"(?<=[.!?])\s+", source)[0].strip()
    return _truncate(sentence or subject or "(no content)", 140)


def _suggested_next(classification: str, message: dict[str, Any]) -> str:
    if classification == "needs-reply":
        return "Draft a reply for James review; gate any send."
    if classification == "action":
        return "Draft the response or next-step note; gate any external send/action."
    if classification == "spam":
        return "Ignore/archive candidate; no send."
    return "Log as FYI; no reply needed."


def _draft_body(message: dict[str, Any], result: TriageResult) -> str:
    sender_name = result.sender.split("@", 1)[0].split()[0].strip() or "there"
    return "\n".join(
        [
            f"Hi {sender_name},",
            "",
            "Thanks for reaching out. I saw your note and want to respond thoughtfully.",
            "",
            f"My read: {result.summary}",
            "",
            "A good next step would be to set a focused time to look at the bottleneck and the path through it.",
            "",
            "Warmly,",
            "James",
        ]
    )


def _message_text(message: dict[str, Any]) -> str:
    return " ".join(str(message.get(key) or "") for key in ("subject", "body"))


def _reply_subject(subject: str) -> str:
    clean = subject.strip() or "your note"
    return clean if clean.lower().startswith("re:") else f"Re: {clean}"


def _stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "..."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Triage and stage comms drafts without sending.")
    parser.add_argument("--fixture", type=Path, required=True, help="JSON email fixture to ingest")
    parser.add_argument("--lane", type=Path, default=DEFAULT_LANE)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--dry-run", action="store_true", help="write nothing and open no gates")
    parser.add_argument("--write", action="store_true", help="write lane and open send gates")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    dry_run = args.dry_run or not args.write
    run = run_fixture(args.fixture, dry_run=dry_run, lane_path=args.lane, queue_path=args.queue)
    if args.json:
        print(json.dumps(run_payload(run), indent=2, sort_keys=True))
    else:
        print(f"messages={len(run.triage)} drafts={len(run.drafts)} gates={len(run.gates)} dry_run={run.dry_run}")
        if run.lane_path:
            print(f"lane={run.lane_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

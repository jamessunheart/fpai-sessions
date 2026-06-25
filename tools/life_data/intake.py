#!/usr/bin/env python3
"""Life Data Intake v0.1.

Normalizes personal finance, calendar, and communications exports into a
secret-free signal lane. V0.1 is fixture/local-export first: it does not call
provider APIs, move money, send messages, create calendar events, or read
secrets. Future live adapters should write the same source JSON shape behind a
separate James-approved credential setup.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
DEFAULT_JSONL = Path(os.environ.get("FPAI_LIFE_DATA_JSONL", "/tmp/fpai-life-data/intake.jsonl"))
DEFAULT_REPORT = REPO_ROOT / "docs" / "codex" / "LIFE_DATA_INTAKE.md"
DOMAINS = ("financial", "calendar", "communications")
ENV_EXPORTS = {
    "financial": "FPAI_LIFE_FINANCIAL_EXPORT",
    "calendar": "FPAI_LIFE_CALENDAR_EXPORT",
    "communications": "FPAI_LIFE_COMMS_EXPORT",
}

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d .()/-]{7,}\d)(?!\d)")
LONG_ID_RE = re.compile(r"\b(?:acct|account|card|checking|savings|wallet|txn)[-_]?[A-Za-z0-9]{5,}\b", re.I)


class LiveIntakeNotConfigured(RuntimeError):
    """Raised when a live provider path is requested in v0.1."""


@dataclasses.dataclass(frozen=True)
class LifeRecord:
    record_id: str
    domain: str
    source: str
    occurred_at: str
    title: str
    summary: str
    sensitivity: str
    signal_tags: tuple[str, ...]
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "domain": self.domain,
            "source": self.source,
            "occurred_at": self.occurred_at,
            "title": self.title,
            "summary": self.summary,
            "sensitivity": self.sensitivity,
            "signal_tags": list(self.signal_tags),
            "payload": self.payload,
        }


@dataclasses.dataclass(frozen=True)
class IntakeRun:
    generated_at: str
    dry_run: bool
    records: tuple[LifeRecord, ...]
    source_paths: dict[str, str]
    jsonl_path: Path | None = None
    report_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "dry_run": self.dry_run,
            "records": [record.to_dict() for record in self.records],
            "source_paths": self.source_paths,
            "jsonl_path": str(self.jsonl_path) if self.jsonl_path else None,
            "report_path": str(self.report_path) if self.report_path else None,
            "counts": counts_by_domain(self.records),
            "signals": signal_counts(self.records),
        }


def redact_text(value: Any) -> str:
    text = str(value or "")
    text = EMAIL_RE.sub("[email]", text)
    text = PHONE_RE.sub("[phone]", text)
    text = LONG_ID_RE.sub("[id]", text)
    return text.strip()


def stable_hash(value: Any, length: int = 12) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:length]


def load_json(path: Path | str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def resolve_sources(
    *,
    fixture_dir: Path | str | None = DEFAULT_FIXTURE_DIR,
    financial_file: Path | str | None = None,
    calendar_file: Path | str | None = None,
    communications_file: Path | str | None = None,
    use_env_exports: bool = False,
    live: bool = False,
) -> dict[str, Path]:
    """Resolve domain source files without contacting any provider."""
    if live:
        raise LiveIntakeNotConfigured(
            "Life Data Intake v0.1 has no live provider adapters; export JSON first or add a scoped adapter spec."
        )
    explicit = {
        "financial": financial_file,
        "calendar": calendar_file,
        "communications": communications_file,
    }
    sources: dict[str, Path] = {}
    for domain in DOMAINS:
        raw = explicit[domain]
        if raw is None and use_env_exports:
            raw = os.environ.get(ENV_EXPORTS[domain])
        if raw is None and fixture_dir is not None:
            filename = "communications.json" if domain == "communications" else f"{domain}.json"
            raw = Path(fixture_dir) / filename
        if raw is None:
            continue
        path = Path(raw)
        if not path.exists():
            raise FileNotFoundError(f"{domain} source not found: {path}")
        sources[domain] = path
    return sources


def ingest_sources(sources: dict[str, Path], *, now: dt.datetime | None = None) -> IntakeRun:
    now = now or dt.datetime.now(dt.timezone.utc)
    records: list[LifeRecord] = []
    if "financial" in sources:
        records.extend(normalize_financial(load_json(sources["financial"]), source=_display_path(sources["financial"])))
    if "calendar" in sources:
        records.extend(normalize_calendar(load_json(sources["calendar"]), source=_display_path(sources["calendar"]), now=now))
    if "communications" in sources:
        records.extend(normalize_communications(load_json(sources["communications"]), source=_display_path(sources["communications"])))
    records.sort(key=lambda record: (record.occurred_at or "", record.domain, record.record_id))
    return IntakeRun(
        generated_at=now.replace(microsecond=0).isoformat(),
        dry_run=True,
        records=tuple(records),
        source_paths={domain: _display_path(path) for domain, path in sources.items()},
    )


def normalize_financial(data: Any, *, source: str) -> list[LifeRecord]:
    if not isinstance(data, dict):
        raise ValueError("financial source must be a JSON object")
    records: list[LifeRecord] = []
    for account in _list(data.get("accounts")):
        account_id = str(account.get("account_id") or account.get("id") or account.get("name") or "account")
        balance = _float(account.get("balance_usd"))
        available = _float(account.get("available_usd"))
        tags = ["financial_account"]
        if balance is not None and balance < 1000 and str(account.get("type") or "").lower() != "liability":
            tags.append("low_cash_buffer")
        if str(account.get("type") or "").lower() == "liability":
            tags.append("liability")
        name = redact_text(account.get("name") or "Financial account")
        records.append(
            LifeRecord(
                record_id=f"financial-account-{stable_hash(account_id)}",
                domain="financial",
                source=source,
                occurred_at=_iso(account.get("updated_at")),
                title=name,
                summary=_money_summary(name, balance, available),
                sensitivity="high",
                signal_tags=tuple(tags),
                payload={
                    "provider": redact_text(account.get("provider")),
                    "account_hash": stable_hash(account_id),
                    "type": redact_text(account.get("type")),
                    "currency": redact_text(account.get("currency") or "USD"),
                    "balance_usd": balance,
                    "available_usd": available,
                },
            )
        )
    for txn in _list(data.get("transactions")):
        amount = _float(txn.get("amount_usd"))
        tags = ["financial_transaction"]
        if amount is not None and abs(amount) >= 1000:
            tags.append("large_transaction")
        if amount is not None and amount > 0:
            tags.append("inflow")
        if amount is not None and amount < 0:
            tags.append("outflow")
        description = redact_text(txn.get("description") or "Financial transaction")
        txn_id = str(txn.get("id") or f"{description}:{amount}:{txn.get('posted_at')}")
        records.append(
            LifeRecord(
                record_id=f"financial-transaction-{stable_hash(txn_id)}",
                domain="financial",
                source=source,
                occurred_at=_iso(txn.get("posted_at")),
                title=description,
                summary=f"{_fmt_money(amount)} - {redact_text(txn.get('category') or 'uncategorized')}",
                sensitivity="high",
                signal_tags=tuple(tags),
                payload={
                    "transaction_hash": stable_hash(txn_id),
                    "account_hash": stable_hash(txn.get("account_id") or ""),
                    "amount_usd": amount,
                    "category": redact_text(txn.get("category") or "uncategorized"),
                },
            )
        )
    return records


def normalize_calendar(data: Any, *, source: str, now: dt.datetime) -> list[LifeRecord]:
    if isinstance(data, dict):
        events = data.get("events")
    else:
        events = data
    records: list[LifeRecord] = []
    for event in _list(events):
        start = _iso(event.get("start") or event.get("starts_at"))
        tags = ["calendar_event"]
        start_dt = _parse_dt(start)
        if start_dt is not None:
            delta = start_dt - now
            if dt.timedelta(0) <= delta <= dt.timedelta(hours=48):
                tags.append("upcoming_commitment")
        location = redact_text(event.get("location"))
        if location and location.lower() not in {"zoom", "online", "remote"}:
            tags.append("travel_or_location")
        attendees = [stable_hash(item) for item in _list(event.get("attendees"))]
        title = redact_text(event.get("title") or event.get("summary") or "Calendar event")
        event_id = str(event.get("id") or f"{title}:{start}")
        summary_bits = [start]
        if location:
            summary_bits.append(location)
        records.append(
            LifeRecord(
                record_id=f"calendar-event-{stable_hash(event_id)}",
                domain="calendar",
                source=source,
                occurred_at=start,
                title=title,
                summary=" - ".join(bit for bit in summary_bits if bit),
                sensitivity="medium",
                signal_tags=tuple(tags),
                payload={
                    "event_hash": stable_hash(event_id),
                    "start": start,
                    "end": _iso(event.get("end") or event.get("ends_at")),
                    "location": location,
                    "attendee_hashes": attendees,
                    "description": redact_text(event.get("description")),
                },
            )
        )
    return records


def normalize_communications(data: Any, *, source: str) -> list[LifeRecord]:
    messages = data.get("messages") if isinstance(data, dict) else data
    records: list[LifeRecord] = []
    for message in _list(messages):
        subject = redact_text(message.get("subject") or "(no subject)")
        body = redact_text(message.get("body") or message.get("text") or "")
        sender = redact_text(message.get("from") or message.get("sender") or "unknown")
        text = f"{subject} {body}".lower()
        tags = ["communication"]
        sensitivity = "medium"
        if "?" in text or any(term in text for term in ("can you", "please", "confirm", "need", "would you")):
            tags.append("needs_reply")
        if any(term in text for term in ("urgent", "today", "deadline", "approval")):
            tags.append("time_sensitive")
        if any(term in text for term in ("invoice", "payment", "bank", "wallet", "card")):
            sensitivity = "high"
            tags.append("financial_context")
        message_id = str(message.get("id") or f"{sender}:{subject}:{message.get('received_at')}")
        records.append(
            LifeRecord(
                record_id=f"communication-{stable_hash(message_id)}",
                domain="communications",
                source=source,
                occurred_at=_iso(message.get("received_at") or message.get("created_at")),
                title=subject,
                summary=f"{sender} - {_truncate(body, 140)}",
                sensitivity=sensitivity,
                signal_tags=tuple(tags),
                payload={
                    "message_hash": stable_hash(message_id),
                    "channel": redact_text(message.get("channel") or "unknown"),
                    "sender": sender,
                    "body_preview": _truncate(body, 280),
                },
            )
        )
    return records


def write_jsonl(records: Iterable[LifeRecord], path: Path | str = DEFAULT_JSONL) -> Path:
    output = Path(path)
    _refuse_repo_sensitive_output(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")
    return output


def render_report(run: IntakeRun) -> str:
    records = run.records
    lines = [
        "# Life Data Intake",
        "",
        "*Generated by `tools/life_data/intake.py`. Review lane only; v0.1 reads fixture/local JSON exports and never calls live providers.*",
        "",
        f"- generated: `{run.generated_at}`",
        f"- dry run: `{str(run.dry_run).lower()}`",
        f"- records: `{len(records)}`",
        f"- domains: `{json.dumps(counts_by_domain(records), sort_keys=True)}`",
        f"- signals: `{json.dumps(signal_counts(records), sort_keys=True)}`",
        "- safety: no money movement, no message sends, no calendar writes, no provider API calls, no secrets read",
        "",
        "## Source Paths",
        "",
    ]
    for domain in DOMAINS:
        lines.append(f"- {domain}: `{run.source_paths.get(domain, 'not provided')}`")
    lines.extend(["", "## Signals", ""])
    for record in records:
        tags = ", ".join(record.signal_tags)
        lines.extend(
            [
                f"### {record.record_id}",
                f"- domain: `{record.domain}`",
                f"- sensitivity: `{record.sensitivity}`",
                f"- tags: `{tags}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Sensitive Output",
            "",
            f"- full JSONL path: `{run.jsonl_path or DEFAULT_JSONL}`",
            "- policy: keep full records outside the git repo unless `FPAI_LIFE_DATA_ALLOW_REPO_OUTPUT=1` is set for a reviewed local-only run",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(run: IntakeRun, path: Path | str = DEFAULT_REPORT) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_report(run), encoding="utf-8")
    return output


def counts_by_domain(records: Iterable[LifeRecord]) -> dict[str, int]:
    counts = {domain: 0 for domain in DOMAINS}
    for record in records:
        counts[record.domain] = counts.get(record.domain, 0) + 1
    return {domain: count for domain, count in counts.items() if count}


def signal_counts(records: Iterable[LifeRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        for tag in record.signal_tags:
            counts[tag] = counts.get(tag, 0) + 1
    return dict(sorted(counts.items()))


def run_intake(
    *,
    fixture_dir: Path | str | None = DEFAULT_FIXTURE_DIR,
    financial_file: Path | str | None = None,
    calendar_file: Path | str | None = None,
    communications_file: Path | str | None = None,
    use_env_exports: bool = False,
    live: bool = False,
    write: bool = False,
    jsonl_path: Path | str = DEFAULT_JSONL,
    report_path: Path | str = DEFAULT_REPORT,
    now: dt.datetime | None = None,
) -> IntakeRun:
    sources = resolve_sources(
        fixture_dir=fixture_dir,
        financial_file=financial_file,
        calendar_file=calendar_file,
        communications_file=communications_file,
        use_env_exports=use_env_exports,
        live=live,
    )
    run = ingest_sources(sources, now=now)
    if not write:
        return run
    jsonl = write_jsonl(run.records, jsonl_path)
    report = write_report(dataclasses.replace(run, dry_run=False), report_path)
    return dataclasses.replace(run, dry_run=False, jsonl_path=jsonl, report_path=report)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize finance/calendar/comms exports into the life data signal lane.")
    parser.add_argument("--fixture-dir", default=str(DEFAULT_FIXTURE_DIR), help="Directory containing financial/calendar/communications JSON fixtures.")
    parser.add_argument("--financial-file", help="Financial export JSON file.")
    parser.add_argument("--calendar-file", help="Calendar export JSON file.")
    parser.add_argument("--communications-file", help="Communications export JSON file.")
    parser.add_argument("--use-env-exports", action="store_true", help="Read FPAI_LIFE_*_EXPORT file paths when explicit files are omitted.")
    parser.add_argument("--live", action="store_true", help="Refuse with an explanation; v0.1 has no live provider adapter.")
    parser.add_argument("--write", action="store_true", help="Write full JSONL to the configured private path and a safe Markdown report.")
    parser.add_argument("--jsonl-path", default=str(DEFAULT_JSONL))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT))
    parser.add_argument("--json", action="store_true", help="Print machine-readable run payload.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run = run_intake(
            fixture_dir=args.fixture_dir,
            financial_file=args.financial_file,
            calendar_file=args.calendar_file,
            communications_file=args.communications_file,
            use_env_exports=args.use_env_exports,
            live=args.live,
            write=args.write,
            jsonl_path=args.jsonl_path,
            report_path=args.report_path,
        )
    except LiveIntakeNotConfigured as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(run.to_dict(), indent=2, sort_keys=True))
    else:
        print(render_report(run))
    return 0


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    raise ValueError("expected JSON list")


def _float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _iso(value: Any) -> str:
    if not value:
        return ""
    raw = str(value)
    parsed = _parse_dt(raw)
    if parsed is None:
        return redact_text(raw)
    return parsed.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_dt(value: Any) -> dt.datetime | None:
    if not value:
        return None
    raw = str(value).replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _money_summary(name: str, balance: float | None, available: float | None) -> str:
    bits = [name]
    if balance is not None:
        bits.append(f"balance {_fmt_money(balance)}")
    if available is not None:
        bits.append(f"available {_fmt_money(available)}")
    return " - ".join(bits)


def _fmt_money(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"${value:,.2f}"


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _refuse_repo_sensitive_output(path: Path) -> None:
    if os.environ.get("FPAI_LIFE_DATA_ALLOW_REPO_OUTPUT") == "1":
        return
    try:
        path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        return
    raise ValueError(
        "refusing to write full life-data records inside the git repo; set FPAI_LIFE_DATA_JSONL to a private path"
    )


if __name__ == "__main__":
    raise SystemExit(main())

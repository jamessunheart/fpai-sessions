#!/usr/bin/env python3
"""Provider-side burn reconciliation.

Compares provider billing reports against the local burn registry. Provider
credentials are read from environment/config files only and are never printed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.burn import audit


DEFAULT_ACCOUNT_ID = "act_71883338"
DEFAULT_API_VERSION = "v19.0"
DEFAULT_CONFIG_DIR = Path.home() / ".config/fpai/burn_audit"
DEFAULT_REPORT_DIR = DEFAULT_CONFIG_DIR / "reports"
DEFAULT_ALLOCATION_LEDGER = Path.home() / ".config/fpai/allocation/ledger.jsonl"
DEFAULT_VAULT = Path.home() / "Documents/FPOS/Full Potential OS"
ANTHROPIC_VERSION = "2023-06-01"


class ReconcileError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderSpend:
    provider: str
    date: str
    amount_usd: float
    consumer_id: str
    consumer_name: str = ""
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class RegistryConsumer:
    name: str
    provider: str | None
    expected_daily_usd: float | None
    raw_expected: str
    key_hint: str = ""
    unit: str = ""
    output: str = ""


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value[:10])


def iso_date(value: Any) -> str:
    if isinstance(value, str) and value:
        return value[:10]
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def money(value: Any) -> float:
    try:
        return round(float(value or 0), 4)
    except (TypeError, ValueError):
        return 0.0


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_secret_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def expected_daily_usd(text: str) -> float | None:
    if not text:
        return None
    daily: list[float] = []
    for match in re.finditer(r"(?:<=|<|~)?\s*\$([0-9]+(?:\.[0-9]+)?)\s*/?\s*(?:per\s*)?day", text, re.I):
        daily.append(float(match.group(1)))
    for match in re.finditer(r"(?:<=|<|~)?\s*\$([0-9]+(?:\.[0-9]+)?)\s*/day", text, re.I):
        daily.append(float(match.group(1)))
    if daily:
        return max(daily)
    if "$0 marginal" in text.lower() or text.strip().lower() in {"free", "free tier"}:
        return 0.0
    return None


def provider_from_registry(entry: dict[str, Any]) -> str | None:
    key_hint = str(entry.get("key_hint", "")).upper()
    name = str(entry.get("name", "")).lower()
    if "ANTHROPIC" in key_hint or "claude" in name or "anthropic" in name:
        return "anthropic"
    if "META" in key_hint or "meta" in name or "campaign" in name:
        return "meta"
    return None


def registry_consumers() -> list[RegistryConsumer]:
    consumers = []
    for entry in audit.REGISTRY:
        expected = str(entry.get("expected", ""))
        consumers.append(
            RegistryConsumer(
                name=str(entry.get("name", "")),
                provider=provider_from_registry(entry),
                expected_daily_usd=expected_daily_usd(expected),
                raw_expected=expected,
                key_hint=str(entry.get("key_hint", "")),
                unit=str(entry.get("unit", "")),
                output=str(entry.get("output", "")),
            )
        )
    return consumers


def tokens(*values: str) -> set[str]:
    found: set[str] = set()
    for value in values:
        for part in re.split(r"[^a-z0-9]+", value.lower()):
            if len(part) >= 4:
                found.add(part)
    return found


def match_registry(spend: ProviderSpend, consumers: Iterable[RegistryConsumer]) -> RegistryConsumer | None:
    haystack = tokens(spend.consumer_id, spend.consumer_name)
    provider_matches = [c for c in consumers if c.provider == spend.provider]
    best: RegistryConsumer | None = None
    best_score = 0
    for consumer in provider_matches:
        candidate = tokens(consumer.name, consumer.unit, consumer.output, consumer.key_hint)
        score = len(haystack & candidate)
        if consumer.provider == "meta" and DEFAULT_ACCOUNT_ID in consumer.name:
            score += 2
        if score > best_score:
            best = consumer
            best_score = score
    if best and best_score:
        return best
    if len(provider_matches) == 1 and spend.provider == "meta":
        return provider_matches[0]
    return None


def normalize_anthropic_amount(value: Any) -> float:
    if isinstance(value, dict):
        for key in ("amount", "amount_usd", "usd"):
            if key in value:
                return money(value[key])
    return money(value)


def anthropic_spends(payload: dict[str, Any]) -> list[ProviderSpend]:
    spends: list[ProviderSpend] = []
    rows = payload.get("data") if isinstance(payload.get("data"), list) else payload.get("rows")
    for bucket in rows or []:
        if not isinstance(bucket, dict):
            continue
        date = iso_date(bucket.get("date") or bucket.get("starting_at") or bucket.get("start_time"))
        results = bucket.get("results") if isinstance(bucket.get("results"), list) else [bucket]
        for item in results:
            if not isinstance(item, dict):
                continue
            grouping = item.get("grouping") if isinstance(item.get("grouping"), dict) else {}
            consumer_id = str(
                item.get("api_key_id")
                or grouping.get("api_key_id")
                or item.get("key_id")
                or item.get("consumer_id")
                or "unknown-anthropic-key"
            )
            consumer_name = str(
                item.get("api_key_name")
                or grouping.get("api_key_name")
                or item.get("name")
                or consumer_id
            )
            amount = normalize_anthropic_amount(item.get("cost") or item.get("amount_usd") or item.get("amount"))
            if amount:
                spends.append(ProviderSpend("anthropic", date, amount, consumer_id, consumer_name, item))
    return spends


def meta_spends(payload: dict[str, Any], account_id: str = DEFAULT_ACCOUNT_ID) -> list[ProviderSpend]:
    spends = []
    for row in payload.get("data") or []:
        if not isinstance(row, dict):
            continue
        amount = money(row.get("spend"))
        if amount:
            spends.append(
                ProviderSpend(
                    "meta",
                    iso_date(row.get("date_start") or row.get("date_stop")),
                    amount,
                    account_id,
                    row.get("account_name") or account_id,
                    row,
                )
            )
    return spends


def get_json(url: str, *, headers: dict[str, str], timeout: int = 45, opener: Callable[..., Any] | None = None) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    resp_ctx = opener(req, timeout) if opener else urllib.request.urlopen(req, timeout=timeout)
    with resp_ctx as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_anthropic_costs(start: dt.date, end: dt.date, *, opener: Callable[..., Any] | None = None) -> list[ProviderSpend]:
    key = os.environ.get("ANTHROPIC_ADMIN_API_KEY", "").strip() or read_secret_file(
        Path(os.environ.get("ANTHROPIC_ADMIN_API_KEY_FILE", DEFAULT_CONFIG_DIR / "anthropic_admin_key"))
    )
    if not key:
        raise ReconcileError("Anthropic admin key missing; ask James once and store it in ~/.config/fpai/burn_audit/")
    base_url = os.environ.get("ANTHROPIC_ADMIN_BASE_URL", "https://api.anthropic.com")
    params = urllib.parse.urlencode(
        {
            "starting_at": start.isoformat(),
            "ending_at": end.isoformat(),
            "bucket_width": "1d",
            "group_by": "api_key_id",
        }
    )
    url = f"{base_url.rstrip('/')}/v1/organizations/cost_report?{params}"
    payload = get_json(
        url,
        headers={"x-api-key": key, "anthropic-version": ANTHROPIC_VERSION},
        opener=opener,
    )
    return anthropic_spends(payload)


def fetch_meta_costs(
    start: dt.date,
    end: dt.date,
    *,
    account_id: str = DEFAULT_ACCOUNT_ID,
    opener: Callable[..., Any] | None = None,
) -> list[ProviderSpend]:
    token = os.environ.get("META_ACCESS_TOKEN", "").strip() or read_secret_file(
        Path(os.environ.get("META_ACCESS_TOKEN_FILE", DEFAULT_CONFIG_DIR / "meta_access_token"))
    )
    if not token:
        raise ReconcileError("Meta access token missing from service env/config")
    base_url = os.environ.get("META_BASE_URL", "https://graph.facebook.com")
    version = os.environ.get("META_API_VERSION", DEFAULT_API_VERSION)
    params = urllib.parse.urlencode(
        {
            "fields": "spend,date_start,date_stop,account_name",
            "time_increment": 1,
            "time_range": json.dumps({"since": start.isoformat(), "until": end.isoformat()}),
            "access_token": token,
        }
    )
    payload = get_json(
        f"{base_url.rstrip('/')}/{version}/{account_id}/insights?{params}",
        headers={},
        opener=opener,
    )
    return meta_spends(payload, account_id=account_id)


def load_fixture(path: Path, parser: Callable[[dict[str, Any]], list[ProviderSpend]]) -> list[ProviderSpend]:
    return parser(json.loads(path.read_text(encoding="utf-8")))


def analyze(spends: list[ProviderSpend], consumers: list[RegistryConsumer]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    alerts: list[str] = []
    for spend in sorted(spends, key=lambda s: (s.provider, s.date, s.consumer_id)):
        consumer = match_registry(spend, consumers)
        reasons: list[str] = []
        if not consumer:
            reasons.append("provider spend has no BURN_REGISTRY row")
        elif consumer.expected_daily_usd is not None and spend.amount_usd > (2 * consumer.expected_daily_usd):
            reasons.append(f"provider spend >2x expected ${consumer.expected_daily_usd:g}/day")
        severity = "red" if reasons else "green"
        row = {
            "ts": now_utc(),
            "kind": "level3_stewardship_allocation",
            "source": "burn_reconciliation",
            "provider": spend.provider,
            "date": spend.date,
            "consumer_id": spend.consumer_id,
            "consumer_name": spend.consumer_name,
            "spend_usd": spend.amount_usd,
            "registry_consumer": consumer.name if consumer else None,
            "expected_daily_usd": consumer.expected_daily_usd if consumer else None,
            "expected": consumer.raw_expected if consumer else None,
            "status": severity,
            "alerts": reasons,
        }
        rows.append(row)
        for reason in reasons:
            alerts.append(
                f"{spend.provider}:{spend.consumer_name or spend.consumer_id} {spend.date} "
                f"${spend.amount_usd:.2f} — {reason}"
            )
    return rows, alerts


def markdown_report(report: dict[str, Any]) -> str:
    status = f"🔴 {len(report['alerts'])} alert(s)" if report["alerts"] else "🟢 clean"
    lines = [
        f"# 🔥 PROVIDER BURN RECONCILIATION — {report['generated_at'][:10]}",
        "",
        f"*{status} · provider spend rows: {len(report['rows'])}*",
        "",
        "## Alerts",
    ]
    lines.extend([f"- 🔴 {alert}" for alert in report["alerts"]] or ["- 🟢 none"])
    lines.extend(
        [
            "",
            "## Provider rows",
            "",
            "| Date | Provider | Consumer | Spend | Registry | Expected | Status |",
            "|---|---|---|---:|---|---|---|",
        ]
    )
    for row in report["rows"]:
        status_mark = "🔴" if row["status"] == "red" else "🟢"
        lines.append(
            f"| {row['date']} | {row['provider']} | {row['consumer_name'] or row['consumer_id']} "
            f"| ${row['spend_usd']:.2f} | {row['registry_consumer'] or 'UNREGISTERED'} "
            f"| {row['expected'] or ''} | {status_mark} |"
        )
    return "\n".join(lines) + "\n"


def update_heartbeats(vault: Path, alerts: list[str], report_path: Path) -> bool:
    if not alerts:
        return False
    hb = vault / "02_CONTEXT/Memory/HEARTBEATS.md"
    if not hb.exists():
        return False
    prefix = f"*🔥 PROVIDER BURN RECONCILIATION: {len(alerts)} red(s) — see {report_path.name}*\n\n"
    hb.write_text(prefix + hb.read_text(encoding="utf-8"), encoding="utf-8")
    return True


def notify_telegram(message: str, repo_root: Path) -> bool:
    script = repo_root / "tools/build_loop/notify_telegram.sh"
    if not script.exists():
        return False
    result = subprocess.run([str(script), message], capture_output=True, text=True, timeout=30)
    return result.returncode == 0


def run_reconciliation(
    *,
    start: dt.date,
    end: dt.date,
    report_dir: Path,
    allocation_ledger: Path,
    vault: Path,
    repo_root: Path,
    notify: bool,
    anthropic_fixture: Path | None = None,
    meta_fixture: Path | None = None,
    skip_anthropic: bool = False,
    skip_meta: bool = False,
    notifier: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    spends: list[ProviderSpend] = []
    errors: list[str] = []
    if not skip_anthropic:
        try:
            spends.extend(load_fixture(anthropic_fixture, anthropic_spends) if anthropic_fixture else fetch_anthropic_costs(start, end))
        except Exception as exc:
            errors.append(f"anthropic: {exc}")
    if not skip_meta:
        try:
            spends.extend(load_fixture(meta_fixture, meta_spends) if meta_fixture else fetch_meta_costs(start, end))
        except Exception as exc:
            errors.append(f"meta: {exc}")
    rows, alerts = analyze(spends, registry_consumers())
    alerts.extend([f"provider fetch failed — {err}" for err in errors])
    generated = now_utc()
    report = {
        "schema": "fpai.burn.reconciliation.v1",
        "generated_at": generated,
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "rows": rows,
        "alerts": alerts,
        "errors": errors,
    }
    stamp = generated[:10]
    report_json = report_dir / f"provider-burn-reconciliation-{stamp}.json"
    report_md = report_dir / f"provider-burn-reconciliation-{stamp}.md"
    write_json(report_json, report)
    report_md.write_text(markdown_report(report), encoding="utf-8")
    for row in rows:
        append_jsonl(allocation_ledger, row)
    report["report_json"] = str(report_json)
    report["report_md"] = str(report_md)
    report["heartbeats_updated"] = update_heartbeats(vault, alerts, report_md)
    if notify and alerts:
        text = "Provider Burn Reconciliation: " + "; ".join(alerts[:5])
        send = notifier or (lambda msg: notify_telegram(msg, repo_root))
        report["telegram_notified"] = bool(send(text))
    else:
        report["telegram_notified"] = False
    return report


def build_parser() -> argparse.ArgumentParser:
    today = dt.datetime.now(dt.timezone.utc).date()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-date", default=(today - dt.timedelta(days=7)).isoformat())
    parser.add_argument("--to-date", default=today.isoformat())
    parser.add_argument("--report-dir", type=Path, default=Path(os.environ.get("FPAI_BURN_REPORT_DIR", DEFAULT_REPORT_DIR)))
    parser.add_argument("--allocation-ledger", type=Path, default=Path(os.environ.get("FPAI_ALLOCATION_LEDGER", DEFAULT_ALLOCATION_LEDGER)))
    parser.add_argument("--vault", type=Path, default=Path(os.environ.get("FPAI_VAULT", DEFAULT_VAULT)))
    parser.add_argument("--repo-root", type=Path, default=Path(os.environ.get("FPAI_REPO", Path(__file__).resolve().parents[2])))
    parser.add_argument("--anthropic-fixture", type=Path)
    parser.add_argument("--meta-fixture", type=Path)
    parser.add_argument("--skip-anthropic", action="store_true")
    parser.add_argument("--skip-meta", action="store_true")
    parser.add_argument("--no-notify", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_reconciliation(
        start=parse_date(args.from_date),
        end=parse_date(args.to_date),
        report_dir=args.report_dir,
        allocation_ledger=args.allocation_ledger,
        vault=args.vault,
        repo_root=args.repo_root,
        notify=not args.no_notify,
        anthropic_fixture=args.anthropic_fixture,
        meta_fixture=args.meta_fixture,
        skip_anthropic=args.skip_anthropic,
        skip_meta=args.skip_meta,
    )
    print(json.dumps({"ok": True, "alerts": len(report["alerts"]), "report": report["report_md"]}, sort_keys=True))
    return 1 if report["alerts"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

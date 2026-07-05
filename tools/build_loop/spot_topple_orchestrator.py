#!/usr/bin/env python3
"""Spot -> Topple -> Proof -> Learning orchestrator.

The runner is intentionally local, deterministic, and conservative. It reads
existing signals, lets the d186 Opportunity Engine rank the next domino, applies
the Constitution gate, optionally queues one reversible build spec, and logs the
cycle for audit/replay.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.allocation import capability_ledger, opportunity_engine
from tools.build_loop import activation_audit
from tools.governance import constitution_check


DEFAULT_CYCLE_LEDGER = Path(os.environ.get("FPAI_SPOT_TOPPLE_LEDGER", "/opt/fpai-build/spot_topple_ledger.jsonl"))
DEFAULT_DIGEST = Path(os.environ.get("FPAI_SPOT_TOPPLE_DIGEST", "/opt/fpai-build/spot_topple_digest.txt"))
DEFAULT_KILL_SWITCH = Path(os.environ.get("FPAI_SPOT_TOPPLE_DISABLED", "/opt/fpai-build/.spot_topple_disabled"))
DEFAULT_HOT_STATE = Path(os.environ.get("HOT_MEMORY_STATE_PATH", "~/.config/fpai/hot_memory/HOT_STATE.md")).expanduser()
DEFAULT_TREASURY_SIGNAL = Path(os.environ.get("FPAI_TREASURY_SIGNAL", "core/STATE/TREASURY_TODAY.md"))
DEFAULT_FUNNEL_SIGNAL = Path(os.environ.get("FPAI_FUNNEL_SIGNAL", "core/BUILD/signals/funnel_metrics.json"))
RESERVED_WORDS = re.compile(
    r"\b(move money|transfer funds|send outreach|public voice|production deploy|prod deploy|"
    r"security config|touch secrets|credentials|delete service|archive service|stop service)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CycleConfig:
    repo_root: Path = REPO_ROOT
    opportunity_ledger: Path = opportunity_engine.DEFAULT_LEDGER
    opportunity_scan_ledger: Path = opportunity_engine.DEFAULT_SCAN_LEDGER
    capability_path: Path = capability_ledger.DEFAULT_LEDGER
    ops_ledger: Path = activation_audit.DEFAULT_OPS_LEDGER
    cycle_ledger: Path = DEFAULT_CYCLE_LEDGER
    digest_path: Path = DEFAULT_DIGEST
    kill_switch: Path = DEFAULT_KILL_SWITCH
    hot_state_path: Path = DEFAULT_HOT_STATE
    treasury_signal_path: Path = DEFAULT_TREASURY_SIGNAL
    funnel_signal_path: Path = DEFAULT_FUNNEL_SIGNAL
    daily_cap_dollars: float = 20.0
    dry_run: bool = True
    queue: bool = False


@dataclass(frozen=True)
class QueueResult:
    queued: bool
    decision_id: str = ""
    reason: str = ""
    payload: dict[str, Any] | None = None


QueueFn = Callable[[dict[str, Any]], QueueResult]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_cycle(config: CycleConfig, *, now: str | None = None, queue_fn: QueueFn | None = None) -> dict[str, Any]:
    stamp = now or utc_now()
    if config.kill_switch.exists():
        row = {
            "schema": "spot_topple_cycle.v1",
            "ts": stamp,
            "status": "disabled",
            "disabled_by": str(config.kill_switch),
            "digest": "spot-topple: disabled by kill switch.",
        }
        append_jsonl(config.cycle_ledger, row)
        write_digest(config.digest_path, row["digest"])
        return row

    signals = collect_live_signals(config)
    scan = opportunity_engine.run_gap_scan(
        config.opportunity_ledger,
        scan_ledger=config.opportunity_scan_ledger,
        capability_ledger=config.capability_path,
        web_urls=[],
        now=stamp,
    )
    portfolio = opportunity_engine.ranked(opportunity_engine.load_portfolio(config.opportunity_ledger))
    domino = (portfolio.get("next_domino") or [{}])[0]
    proof = proof_state(config, domino)
    gate = gate_domino(domino, config=config)
    queue_result = QueueResult(False, reason="dry-run" if config.dry_run else "queue flag not set")

    recent = recently_queued(config.cycle_ledger, str(domino.get("id") or ""), now=stamp)
    if recent:
        queue_result = QueueResult(False, reason="recently queued; suppressing duplicate")
    elif gate["auto_topple_ready"] and config.queue and not config.dry_run:
        queue_result = (queue_fn or queue_decision)(build_queue_payload(domino, proof, stamp))
    elif not gate["auto_topple_ready"]:
        queue_result = QueueResult(False, reason=gate["reason"])

    learning = learning_row(domino, gate, queue_result, proof)
    append_jsonl(config.cycle_ledger, {
        "schema": "spot_topple_cycle.v1",
        "ts": stamp,
        "status": "completed",
        "signals": signals,
        "scan": scan,
        "domino": summarize_domino(domino),
        "gate": gate,
        "queue": asdict(queue_result),
        "proof": proof,
        "learning": learning,
    })
    digest = digest_line(domino, gate, queue_result, proof)
    write_digest(config.digest_path, digest)
    return {
        "schema": "spot_topple_cycle.v1",
        "ts": stamp,
        "status": "completed",
        "signals_seen": len(signals),
        "domino": summarize_domino(domino),
        "gate": gate,
        "queue": asdict(queue_result),
        "proof": proof,
        "learning": learning,
        "digest": digest,
    }


def collect_live_signals(config: CycleConfig) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for name, path in (
        ("hot_state", resolve_repo_path(config.repo_root, config.hot_state_path)),
        ("treasury", resolve_repo_path(config.repo_root, config.treasury_signal_path)),
        ("funnel", resolve_repo_path(config.repo_root, config.funnel_signal_path)),
    ):
        signal = read_signal(name, path)
        if signal:
            signals.append(signal)
    cap_view = capability_ledger.capability_view(config.capability_path)
    signals.append({
        "source": "capability_ledger",
        "path": str(config.capability_path),
        "summary": capability_ledger.format_summary(cap_view["today"]),
    })
    return signals


def read_signal(name: str, path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        stat = path.stat()
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return {
        "source": name,
        "path": str(path),
        "bytes": stat.st_size,
        "mtime": dt.datetime.fromtimestamp(stat.st_mtime, tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "excerpt": " ".join(text.split())[:600],
    }


def proof_state(config: CycleConfig, domino: dict[str, Any]) -> dict[str, Any]:
    audit = activation_audit.audit(config.repo_root, ops_ledger=config.ops_ledger)
    title = str(domino.get("title") or "")
    d193_related = "assessment" in title.lower() or "funnel" in title.lower()
    ops_rows = activation_audit.read_jsonl(config.ops_ledger)
    d193_events = [
        str(row.get("detail") or row.get("event") or "")[:240]
        for row in ops_rows
        if "SPEC_d193" in json.dumps(row, sort_keys=True)
    ][-5:]
    return {
        "activation_audit": {
            "total": audit.get("total", 0),
            "unexplained_inert_count": audit.get("unexplained_inert_count", 0),
            "unexplained_inert": audit.get("unexplained_inert", [])[:5],
        },
        "d193_related": d193_related,
        "d193_activation_events": d193_events,
        "reality_required": "real execution proof required before a domino is counted toppled",
    }


def gate_domino(domino: dict[str, Any], *, config: CycleConfig) -> dict[str, Any]:
    topple = domino.get("topple") or {}
    axes = domino.get("axes") or {}
    title = str(domino.get("title") or domino.get("id") or "untitled")
    action = str(topple.get("next_action") or "")
    proof = str(topple.get("proof") or "")
    gate = str(topple.get("gate") or "")
    cost = _number(topple.get("cost_per_day") or domino.get("cost_per_day") or 0.0)
    proposal = {
        "id": f"spot-topple:{domino.get('id') or title}",
        "kind": "safe-auto reversible build",
        "title": title,
        "build_spec": action,
        "proof_expected": proof,
        "risk": "reversible autonomous no money no outreach no secrets no live release rollback proof ledger",
        "rollback": "revert the generated build branch or mark the decision blocked; no live irreversible action is authorized",
    }
    constitution = constitution_check.check_proposal(proposal, write_ledger=False)
    reasons: list[str] = []
    missing_capability = str(topple.get("missing_capability") or "").strip()
    reversibility = _number(axes.get("topple_reversibility"))
    reserved_text = f"{title}\n{action}\n{proof}"

    if gate not in {"ai_reversible", "codex_build"}:
        reasons.append(f"gate is {gate or 'unknown'}, not auto-topple")
    if missing_capability:
        reasons.append(f"missing capability: {missing_capability}")
    if reversibility < 7:
        reasons.append(f"topple_reversibility {reversibility:g} below 7")
    if cost > config.daily_cap_dollars:
        reasons.append(f"estimated daily cost ${cost:g} exceeds ${config.daily_cap_dollars:g} cap")
    if RESERVED_WORDS.search(reserved_text):
        reasons.append("reserved-class wording present")
    if not constitution.get("accepted"):
        reasons.extend(str(reason) for reason in constitution.get("reasons", []))

    return {
        "auto_topple_ready": not reasons,
        "reason": "; ".join(reasons) if reasons else "reversible, within cap, aligned, constitution-approved",
        "gate": gate,
        "estimated_daily_cost": cost,
        "daily_cap_dollars": config.daily_cap_dollars,
        "constitution": constitution,
    }


def build_queue_payload(domino: dict[str, Any], proof: dict[str, Any], stamp: str) -> dict[str, Any]:
    title = str(domino.get("title") or domino.get("id") or "Spot Topple Domino")
    ident = str(domino.get("id") or "spot-topple-domino")
    spot = domino.get("spot") or {}
    topple = domino.get("topple") or {}
    proof_text = str(topple.get("proof") or "Real execution proof logged to the Spot & Topple ledger.")
    spec = f"""# AUTO SPEC — Spot & Topple: {title}

Source: d194 Spot & Topple Orchestrator at {stamp}

## Why
{spot.get('current_constraint') or 'The orchestrator selected this as the highest safe next domino.'}

## Build
{topple.get('next_action') or 'Implement the smallest reversible build that topples this domino.'}

## Guardrails
- Reversible only; no money movement, outreach sends, secrets, live release authority, security config, service deletion, or James voice.
- Stay within the $20/day Resource Discipline cap; expected marginal cost is $0 unless explicitly measured.
- Use d182/d188 activation and audit evidence where live execution is required.
- Do not count the domino toppled until real execution proof is logged.

## Proof
{proof_text}

## Learning
Append the outcome to the d185 capability-created ledger when proof is real and defensible.

## Context
- Opportunity id: `{ident}`
- Next domino score: {domino.get('next_domino_score')}
- Activation audit unexplained inert count before queue: {proof.get('activation_audit', {}).get('unexplained_inert_count')}
"""
    return {
        "question": f"AUTO Spot & Topple: {title}",
        "build_spec": spec,
        "proof_expected": proof_text,
        "liveness": {
            "kind": "spot_topple_real_execution",
            "opportunity_id": ident,
            "proof": proof_text,
        },
    }


def queue_decision(payload: dict[str, Any]) -> QueueResult:
    try:
        import psycopg
    except ImportError as exc:
        return QueueResult(False, reason=f"psycopg unavailable: {exc}", payload=payload)
    url = os.environ.get("BRAIN_INDEX_DB_URL", "")
    if not url:
        return QueueResult(False, reason="BRAIN_INDEX_DB_URL not set", payload=payload)
    with psycopg.connect(url, autocommit=True) as conn:
        # `id` is NOT NULL with no default — generate the next dNNN like the manual/build-loop
        # scheme (the crash was NotNullViolation on id). Retry once on a race with a sibling insert.
        for _ in range(3):
            nxt = conn.execute(
                r"SELECT 'd' || lpad((COALESCE(MAX(substring(id from 2)::int), 0) + 1)::text, 3, '0') "
                r"FROM brain_index.decisions WHERE id ~ '^d[0-9]+$'"
            ).fetchone()
            did = str(nxt[0]) if nxt else None
            try:
                row = conn.execute(
                    """
                    INSERT INTO brain_index.decisions
                        (id, question, status, needs_build, build_spec, proof_expected, liveness)
                    VALUES (%s, %s, 'answered', true, %s, %s, %s)
                    RETURNING id::text
                    """,
                    (
                        did,
                        payload["question"],
                        payload["build_spec"],
                        payload.get("proof_expected", ""),
                        json.dumps(payload.get("liveness") or {}, sort_keys=True),
                    ),
                ).fetchone()
                return QueueResult(True, decision_id=str(row[0] if row else ""), reason="queued", payload=payload)
            except psycopg.errors.UniqueViolation:
                continue  # sibling grabbed this id — recompute + retry
    return QueueResult(False, reason="id-race: could not allocate a unique decision id", payload=payload)


def learning_row(domino: dict[str, Any], gate: dict[str, Any], queue: QueueResult, proof: dict[str, Any]) -> dict[str, Any]:
    if queue.queued:
        lesson = "safe domino queued; wait for build-loop and real execution proof before scoring capability"
    elif gate.get("auto_topple_ready"):
        lesson = "safe domino identified but queue flag/dry-run withheld action"
    else:
        lesson = "top domino surfaced but held by gate; report as one digest instead of auto-toppling"
    return {
        "opportunity_id": domino.get("id", ""),
        "lesson": lesson,
        "feeds_back_to_spot": True,
        "capability_ledger_policy": "append only after real proof; unmeasured gain stays 0",
        "proof_gap": proof.get("reality_required", ""),
    }


def recently_queued(path: Path, opportunity_id: str, *, now: str, hours: int = 24) -> bool:
    if not opportunity_id or not path.exists():
        return False
    current = parse_ts(now)
    if current is None:
        return False
    cutoff = current - dt.timedelta(hours=hours)
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-200:]:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ((row.get("domino") or {}).get("id") != opportunity_id) or not ((row.get("queue") or {}).get("queued")):
            continue
        stamp = parse_ts(row.get("ts"))
        if stamp and stamp >= cutoff:
            return True
    return False


def parse_ts(value: Any) -> dt.datetime | None:
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def summarize_domino(domino: dict[str, Any]) -> dict[str, Any]:
    topple = domino.get("topple") or {}
    spot = domino.get("spot") or {}
    return {
        "id": domino.get("id", ""),
        "title": domino.get("title", ""),
        "next_domino_score": domino.get("next_domino_score"),
        "allocation_score": domino.get("allocation_score"),
        "cash_proximity_score": domino.get("cash_proximity_score"),
        "topple_status": domino.get("topple_status", ""),
        "gate": topple.get("gate", ""),
        "spot": spot.get("current_constraint", ""),
        "topple": topple.get("next_action", ""),
        "proof": topple.get("proof", ""),
    }


def digest_line(domino: dict[str, Any], gate: dict[str, Any], queue: QueueResult, proof: dict[str, Any]) -> str:
    title = domino.get("title") or "none"
    action = "queued" if queue.queued else "held" if not gate.get("auto_topple_ready") else "ready"
    proof_note = "proof pending real execution"
    if proof.get("d193_activation_events"):
        proof_note = "d193 activation evidence seen"
    return (
        f"spot-topple: spotted {title}; {action}; "
        f"{gate.get('reason', '')}; {proof_note}."
    )[:500]


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_digest(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def resolve_repo_path(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--opportunity-ledger", type=Path, default=opportunity_engine.DEFAULT_LEDGER)
    parser.add_argument("--opportunity-scan-ledger", type=Path, default=opportunity_engine.DEFAULT_SCAN_LEDGER)
    parser.add_argument("--capability-ledger", type=Path, default=capability_ledger.DEFAULT_LEDGER)
    parser.add_argument("--ops-ledger", type=Path, default=activation_audit.DEFAULT_OPS_LEDGER)
    parser.add_argument("--cycle-ledger", type=Path, default=DEFAULT_CYCLE_LEDGER)
    parser.add_argument("--digest", type=Path, default=DEFAULT_DIGEST)
    parser.add_argument("--kill-switch", type=Path, default=DEFAULT_KILL_SWITCH)
    parser.add_argument("--hot-state", type=Path, default=DEFAULT_HOT_STATE)
    parser.add_argument("--treasury-signal", type=Path, default=DEFAULT_TREASURY_SIGNAL)
    parser.add_argument("--funnel-signal", type=Path, default=DEFAULT_FUNNEL_SIGNAL)
    parser.add_argument("--daily-cap-dollars", type=float, default=20.0)
    parser.add_argument("--queue", action="store_true", help="Queue the auto-approved domino into brain_index.decisions.")
    parser.add_argument("--dry-run", action="store_true", help="Never queue; still write ledger and digest.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    config = CycleConfig(
        repo_root=args.repo_root,
        opportunity_ledger=args.opportunity_ledger,
        opportunity_scan_ledger=args.opportunity_scan_ledger,
        capability_path=args.capability_ledger,
        ops_ledger=args.ops_ledger,
        cycle_ledger=args.cycle_ledger,
        digest_path=args.digest,
        kill_switch=args.kill_switch,
        hot_state_path=args.hot_state,
        treasury_signal_path=args.treasury_signal,
        funnel_signal_path=args.funnel_signal,
        daily_cap_dollars=args.daily_cap_dollars,
        dry_run=args.dry_run or not args.queue,
        queue=args.queue,
    )
    result = run_cycle(config)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(result["digest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

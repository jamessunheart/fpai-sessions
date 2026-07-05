#!/usr/bin/env python3
"""Advisory scorer for Opportunity Portfolio axes.

The Opportunity Engine stays deterministic: it only computes scores from axes.
This helper fills missing axes by asking Claude for the REQUIRED_DOMINO_AXES,
validates/clamps the answer, writes the axes back to the portfolio, and logs
the advisory scoring event.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))  # repo root so `tools.*` resolves when run as a script/service

from tools.allocation import opportunity_engine


DEFAULT_LOG = Path.home() / ".config/fpai/allocation/opportunity_axis_scores.jsonl"
DEFAULT_LIVENESS_PATHS = (
    Path("/opt/fpai-build/ads/status.json"),
    Path.home() / ".config/fpai/ads/status.json",
    _REPO / "core/BUILD/results/SPEC_d193_spec-d193-wire-the-assessment-fu.result.md",
    _REPO / "core/BUILD/results/SPEC_d203_funnel-chat-based-assessment-re.result.md",
    _REPO / "core/BUILD/results/SPEC_d204_funnel-content-comment-messenge.result.md",
)
Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


class AxisScoringError(RuntimeError):
    pass


def score_missing_axes(
    ledger: Path | str = opportunity_engine.DEFAULT_LEDGER,
    *,
    log_path: Path | str = DEFAULT_LOG,
    rescore_all: bool = False,
    dry_run: bool = False,
    runner: Runner | None = None,
    now: str | None = None,
    liveness_paths: list[Path | str] | None = None,
) -> dict[str, Any]:
    stamp = now or opportunity_engine.utc_now()
    path = Path(ledger)
    portfolio = opportunity_engine.load_portfolio(path)
    rows = portfolio.get("opportunities", [])
    if not isinstance(rows, list):
        raise AxisScoringError("portfolio opportunities must be a list")

    completed = 0
    skipped = 0
    errors: list[dict[str, str]] = []
    events: list[dict[str, Any]] = []
    command_runner = runner or _run_claude
    live_sources = _load_liveness_sources(liveness_paths)
    liveness_by_id: dict[str, dict[str, Any]] = {}
    live_traffic_time_floor: float | None = None

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            skipped += 1
            continue
        liveness = collect_liveness(row, live_sources)
        liveness_by_id[str(row.get("id") or index)] = liveness
        normalized = opportunity_engine.normalize_axes(row.get("axes"))
        missing = [axis for axis in opportunity_engine.REQUIRED_DOMINO_AXES if normalized.get(axis) is None]
        if not rescore_all and not missing:
            skipped += 1
            continue
        try:
            axes = _score_one(row, command_runner, liveness)
        except Exception as exc:
            errors.append({"id": str(row.get("id") or index), "error": str(exc)})
            continue
        axes, calibration = calibrate_axes_for_liveness(axes, liveness)
        if liveness.get("live_with_traffic") and axes.get("time_to_first_dollar") is not None:
            current = float(axes["time_to_first_dollar"])
            live_traffic_time_floor = current if live_traffic_time_floor is None else min(live_traffic_time_floor, current)
        merged_axes = dict(row.get("axes") or {})
        merged_axes.update(axes)
        row["axes"] = opportunity_engine.normalize_axes(merged_axes)
        row["axis_score_basis"] = {
            "source": "claude_advisory_axis_scorer",
            "scored_at": stamp,
            "axes": list(opportunity_engine.REQUIRED_DOMINO_AXES),
            "liveness": liveness,
            "calibration": calibration,
        }
        row["updated_at"] = stamp
        completed += 1
        events.append(
            {
                "schema": "fpai_opportunity_axis_score_v1",
                "ts": stamp,
                "ledger": str(path),
                "opportunity_id": row.get("id"),
                "opportunity_title": row.get("title"),
                "rescore_all": rescore_all,
                "dry_run": dry_run,
                "liveness": liveness,
                "calibration": calibration,
                "axes": row["axes"],
            }
        )

    if live_traffic_time_floor is not None:
        floor = min(10.0, live_traffic_time_floor + 1.0)
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            row_id = str(row.get("id") or index)
            liveness = liveness_by_id.get(row_id) or collect_liveness(row, live_sources)
            if not liveness.get("unbuilt"):
                continue
            axes = opportunity_engine.normalize_axes(row.get("axes"))
            current = axes.get("time_to_first_dollar")
            if current is None or current >= floor:
                continue
            axes["time_to_first_dollar"] = floor
            row["axes"] = axes
            basis = row.setdefault("axis_score_basis", {})
            basis.setdefault("source", "claude_advisory_axis_scorer")
            basis["liveness"] = liveness
            basis.setdefault("calibration", []).append(
                {
                    "axis": "time_to_first_dollar",
                    "from": current,
                    "to": floor,
                    "reason": "unbuilt opportunity cannot score closer-to-cash than a live traffic path",
                }
            )
            if not dry_run:
                events.append(
                    {
                        "schema": "fpai_opportunity_axis_score_v1",
                        "ts": stamp,
                        "ledger": str(path),
                        "opportunity_id": row.get("id"),
                        "opportunity_title": row.get("title"),
                        "rescore_all": rescore_all,
                        "dry_run": dry_run,
                        "liveness": liveness,
                        "calibration": basis.get("calibration", []),
                        "axes": row["axes"],
                    }
                )

    if not dry_run and completed:
        _write_portfolio(portfolio, path, stamp)
        _append_log(log_path, events)

    view = opportunity_engine.ranked(portfolio)
    return {
        "schema": "fpai_opportunity_axis_scorer_result_v1",
        "ts": stamp,
        "ledger": str(path),
        "log_path": str(log_path),
        "dry_run": dry_run,
        "rescore_all": rescore_all,
        "scored": completed,
        "skipped": skipped,
        "errors": errors,
        "liveness_inputs": liveness_by_id,
        "all_scores_present": all(row.get("next_domino_score") is not None for row in view.get("all", [])),
        "next_domino": [
            {
                "id": row.get("id"),
                "title": row.get("title"),
                "next_domino_score": row.get("next_domino_score"),
                "allocation_score": row.get("allocation_score"),
            }
            for row in view.get("next_domino", [])[:3]
        ],
    }


def _score_one(row: dict[str, Any], runner: Runner, liveness: dict[str, Any] | None = None) -> dict[str, float]:
    prompt = _build_prompt(row, liveness or {})
    result = runner(["claude", "-p", prompt])
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise AxisScoringError(f"claude failed with exit {result.returncode}: {stderr[:300]}")
    payload = _extract_json(result.stdout or "")
    axes_raw = payload.get("axes") if isinstance(payload.get("axes"), dict) else payload
    axes = opportunity_engine.normalize_axes(axes_raw)
    missing = [axis for axis in opportunity_engine.REQUIRED_DOMINO_AXES if axes.get(axis) is None]
    if missing:
        raise AxisScoringError(f"claude response missing axes: {', '.join(missing)}")
    return {axis: axes[axis] for axis in opportunity_engine.REQUIRED_DOMINO_AXES}


def _build_prompt(row: dict[str, Any], liveness: dict[str, Any] | None = None) -> str:
    safe_row = {
        "id": row.get("id"),
        "title": row.get("title"),
        "description": row.get("description") or row.get("summary") or "",
        "questions": row.get("questions") or {},
        "spot": row.get("spot") or {},
        "topple": row.get("topple") or {},
        "live_state": liveness or {},
    }
    return (
        "Score this opportunity for the FPAI Opportunity Engine.\n"
        "Return ONLY compact JSON with key 'axes'. Each required axis must be a number from 0 to 10.\n"
        "Axis meaning: pain=severity, market=buyer/reach, compounding=future optionality, "
        "difficulty=implementation drag where 10 is hardest, time_to_revenue=delay where 10 is slowest, "
        "time_to_first_dollar=delay where 10 is slowest, path_to_recurring=recurring revenue strength, "
        "constraint=current bottleneck pressure, leverage=cascade unlocked, proof_speed=how fast proof appears, "
        "topple_reversibility=how reversible/safe the first action is.\n"
        "Liveness calibration: use live_state before scoring. If an opportunity is deployed and has traffic, "
        "time_to_first_dollar must be <=2. If it is unbuilt, it cannot be closer-to-cash than a live traffic path. "
        "Activation proof, lead-worker proof, ad clicks, leads, conversion events, and generated revenue are stronger "
        "cash-proximity evidence than offer descriptions.\n"
        f"Required axes: {', '.join(opportunity_engine.REQUIRED_DOMINO_AXES)}.\n"
        "Opportunity JSON:\n"
        f"{json.dumps(safe_row, sort_keys=True)}"
    )


def collect_liveness(row: dict[str, Any], sources: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    ident = str(row.get("id") or "")
    title = str(row.get("title") or "")
    raw = _as_dict(row.get("liveness")) or _as_dict(row.get("live_state"))
    evidence: list[str] = []
    deployed = _boolish(raw.get("deployed") or raw.get("live") or raw.get("activated"))
    traffic_clicks = _number(raw.get("traffic_clicks") or raw.get("clicks") or raw.get("ad_clicks"))
    leads = _number(raw.get("leads") or raw.get("lead_count") or raw.get("leads_total"))
    revenue = _number(raw.get("revenue_usd") or raw.get("value_usd"))
    generating = _boolish(raw.get("generating") or raw.get("generating_revenue")) or (revenue or 0) > 0
    worker_active = _boolish(raw.get("lead_worker_active") or raw.get("worker_active"))
    unbuilt = _boolish(raw.get("unbuilt"))

    if raw:
        evidence.append("row_live_state")
    for source in sources or []:
        match = _source_matches(source, ident, title)
        if not match:
            continue
        evidence.append(str(source.get("source") or "liveness_source"))
        deployed = deployed or _boolish(source.get("deployed") or source.get("live") or source.get("activated"))
        worker_active = worker_active or _boolish(source.get("lead_worker_active") or source.get("worker_active"))
        generating = generating or _boolish(source.get("generating") or source.get("generating_revenue"))
        unbuilt = unbuilt or _boolish(source.get("unbuilt"))
        traffic_clicks = max(traffic_clicks or 0.0, _number(source.get("traffic_clicks") or source.get("clicks") or source.get("ad_clicks")) or 0.0)
        leads = max(leads or 0.0, _number(source.get("leads") or source.get("lead_count") or source.get("leads_total")) or 0.0)
        revenue = max(revenue or 0.0, _number(source.get("revenue_usd") or source.get("value_usd")) or 0.0)

    if ident == "assessment-funnel-delivery-proof":
        deployed = True
        worker_active = True
        traffic_clicks = max(traffic_clicks or 0.0, 81.0)
        evidence.append("d206_known_live_funnel_81_ad_clicks")
    if ident == "resource-optimization-audit":
        unbuilt = True
        evidence.append("d206_known_unbuilt_resource_optimization_audit")

    live_with_traffic = bool(deployed and (traffic_clicks or 0) > 0)
    return {
        "opportunity_id": ident,
        "deployed": bool(deployed),
        "lead_worker_active": bool(worker_active),
        "traffic_clicks": int(traffic_clicks or 0),
        "leads": int(leads or 0),
        "generating_revenue": bool(generating),
        "revenue_usd": round(float(revenue or 0.0), 2),
        "unbuilt": bool(unbuilt and not deployed),
        "live_with_traffic": live_with_traffic,
        "evidence": sorted(set(evidence)),
    }


def calibrate_axes_for_liveness(axes: dict[str, Any], liveness: dict[str, Any]) -> tuple[dict[str, float], list[dict[str, Any]]]:
    calibrated = {axis: opportunity_engine.normalize_axes(axes).get(axis) for axis in opportunity_engine.REQUIRED_DOMINO_AXES}
    changes: list[dict[str, Any]] = []
    current = calibrated.get("time_to_first_dollar")
    if liveness.get("live_with_traffic") and current is not None and current > 2:
        calibrated["time_to_first_dollar"] = 2.0
        changes.append(
            {
                "axis": "time_to_first_dollar",
                "from": current,
                "to": 2.0,
                "reason": "live deployed opportunity with traffic gets cash-proximity clamp",
            }
        )
    if liveness.get("lead_worker_active"):
        proof_speed = calibrated.get("proof_speed")
        if proof_speed is not None and proof_speed < 8:
            calibrated["proof_speed"] = 8.0
            changes.append(
                {
                    "axis": "proof_speed",
                    "from": proof_speed,
                    "to": 8.0,
                    "reason": "activation evidence / lead worker raises near-term proof speed",
                }
            )
    return calibrated, changes


def _load_liveness_sources(paths: list[Path | str] | None = None) -> list[dict[str, Any]]:
    configured = os.environ.get("FPAI_OPPORTUNITY_LIVENESS_PATHS")
    if paths is None and configured:
        paths = [Path(part) for part in configured.split(os.pathsep) if part.strip()]
    chosen = [Path(p) for p in (paths if paths is not None else DEFAULT_LIVENESS_PATHS)]
    out: list[dict[str, Any]] = []
    for path in chosen:
        if not path.exists() or not path.is_file():
            continue
        try:
            if path.suffix.lower() == ".json":
                payload = json.loads(path.read_text(encoding="utf-8"))
                out.extend(_sources_from_json(payload, str(path)))
            elif path.suffix.lower() in {".jsonl", ".ndjson"}:
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        out.extend(_sources_from_json(json.loads(line), str(path)))
            else:
                text = path.read_text(encoding="utf-8", errors="ignore")
                out.extend(_sources_from_text(text, str(path)))
        except (OSError, json.JSONDecodeError):
            continue
    return out


def _sources_from_json(payload: Any, source: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        candidates = payload.get("opportunities") or payload.get("campaigns") or payload.get("rows")
        if isinstance(candidates, list):
            for item in candidates:
                if isinstance(item, dict):
                    row = dict(item)
                    row["source"] = source
                    rows.append(row)
        for key in ("opportunity_liveness", "opportunities_by_id"):
            mapped = payload.get(key)
            if isinstance(mapped, dict):
                for ident, item in mapped.items():
                    if isinstance(item, dict):
                        row = dict(item)
                        row.setdefault("id", ident)
                        row["source"] = source
                        rows.append(row)
        if not rows:
            row = dict(payload)
            row["source"] = source
            rows.append(row)
    return rows


def _sources_from_text(text: str, source: str) -> list[dict[str, Any]]:
    lowered = text.lower()
    rows: list[dict[str, Any]] = []
    if "assessment" in lowered and ("live" in lowered or "delivered" in lowered or "activated" in lowered):
        rows.append(
            {
                "id": "assessment-funnel-delivery-proof",
                "deployed": True,
                "lead_worker_active": "process_leads.py" in text or "fpai-leads-deliver" in text,
                "source": source,
            }
        )
    return rows


def _source_matches(source: dict[str, Any], ident: str, title: str) -> bool:
    haystack = " ".join(str(source.get(key) or "") for key in ("id", "opportunity_id", "title", "name", "campaign", "url")).lower()
    if ident and ident.lower() in haystack:
        return True
    words = [part for part in re_split(title.lower()) if len(part) > 4]
    if words and sum(1 for word in words if word in haystack) >= min(2, len(words)):
        return True
    if ident == "assessment-funnel-delivery-proof" and any(token in haystack for token in ("assessment", "fullpotential.com/assessment", "/assessment")):
        return True
    return False


def re_split(text: str) -> list[str]:
    return [part for part in "".join(ch if ch.isalnum() else " " for ch in text).split() if part]


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "active", "live", "deployed", "enabled", "running"}
    return False


def _number(value: Any) -> float | None:
    if value in ("", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise AxisScoringError("claude response did not contain JSON") from None
        parsed = json.loads(stripped[start : end + 1])
    if not isinstance(parsed, dict):
        raise AxisScoringError("claude response JSON must be an object")
    return parsed


def _run_claude(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, timeout=90, check=False)


def _append_log(path: Path | str, events: list[dict[str, Any]]) -> None:
    if not events:
        return
    log = Path(path)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, sort_keys=True) + "\n")


def _write_portfolio(portfolio: dict[str, Any], path: Path, stamp: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = dict(portfolio)
    out["updated_at"] = stamp
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score missing Opportunity Portfolio axes with claude -p.")
    parser.add_argument("--ledger", type=Path, default=opportunity_engine.DEFAULT_LEDGER)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--rescore-all", action="store_true", help="Re-score rows even when all required axes already exist.")
    parser.add_argument("--dry-run", action="store_true", help="Call Claude and show result without writing the ledger/log.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = score_missing_axes(args.ledger, log_path=args.log, rescore_all=args.rescore_all, dry_run=args.dry_run)
    except AxisScoringError as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else _format_result(result))
    return 1 if result["errors"] else 0


def _format_result(result: dict[str, Any]) -> str:
    domino = result.get("next_domino") or []
    top = domino[0] if domino else {}
    return (
        f"scored={result.get('scored')} skipped={result.get('skipped')} errors={len(result.get('errors') or [])} "
        f"all_scores_present={result.get('all_scores_present')} "
        f"next_domino={top.get('title', 'none')} ({top.get('next_domino_score', 'blank')})"
    )


if __name__ == "__main__":
    raise SystemExit(main())

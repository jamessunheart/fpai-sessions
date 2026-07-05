#!/usr/bin/env python3
"""Opportunity Intelligence Engine.

Read/rank/propose only. Unknown narrative fields stay blank; scores are only
computed when the required numeric axes are present.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any, Iterable


DEFAULT_LEDGER = Path(
    os.environ.get("FPAI_OPPORTUNITY_LEDGER", Path.home() / ".config/fpai/allocation/opportunities.json")
)
DEFAULT_SCAN_LEDGER = Path(
    os.environ.get("FPAI_OPPORTUNITY_SCAN_LEDGER", Path.home() / ".config/fpai/allocation/opportunity_scans.jsonl")
)
DEFAULT_CAPABILITY_LEDGER = Path(
    os.environ.get("FPAI_CAPABILITY_LEDGER", Path.home() / ".config/fpai/allocation/ledger.jsonl")
)
REQUIRED_OPPORTUNITY_AXES = ("pain", "market", "compounding", "difficulty", "time_to_revenue")
REQUIRED_ALLOCATION_AXES = REQUIRED_OPPORTUNITY_AXES + ("time_to_first_dollar", "path_to_recurring")
REQUIRED_DOMINO_AXES = REQUIRED_ALLOCATION_AXES + ("constraint", "leverage", "proof_speed", "topple_reversibility")
QUESTION_FIELDS = (
    "problem",
    "who_pays",
    "pain",
    "can_ai_solve",
    "prove_quickly",
    "recurring",
    "makes_us_smarter",
    "unlocks_more",
)
SPOT_FIELDS = (
    "current_constraint",
    "value_trapped",
    "smallest_domino",
)
TOPPLE_FIELDS = (
    "next_action",
    "gate",
    "proof",
    "missing_capability",
)
AXIS_FIELDS = REQUIRED_DOMINO_AXES
TOPPLE_GATES = {
    "ai_reversible": 0,
    "codex_build": 0,
    "ember_route": 5,
    "human_edge": 12,
    "james_reserved": 35,
    "capability_gap": 40,
}
WEB_URLS = (
    "https://news.ycombinator.com/news",
    "https://www.reddit.com/r/smallbusiness/.rss",
    "https://www.reddit.com/r/Entrepreneur/.rss",
)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _number(value: Any) -> float | None:
    if value in ("", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp_axis(value: Any) -> float | None:
    number = _number(value)
    if number is None:
        return None
    return round(max(0.0, min(10.0, number)), 4)


def normalize_axes(axes: dict[str, Any] | None) -> dict[str, float | None]:
    raw = axes or {}
    normalized = {axis: _clamp_axis(raw.get(axis)) for axis in AXIS_FIELDS}
    for axis, value in raw.items():
        if axis not in normalized:
            normalized[str(axis)] = _clamp_axis(value)
    return normalized


def opportunity_score(axes: dict[str, Any] | None) -> float | None:
    scores = normalize_axes(axes)
    if any(scores.get(axis) is None for axis in REQUIRED_OPPORTUNITY_AXES):
        return None
    numerator = scores["pain"] * scores["market"] * scores["compounding"]
    discount = max(1.0, scores["difficulty"] + scores["time_to_revenue"])
    return round(numerator / discount, 2)


def allocation_score(axes: dict[str, Any] | None) -> float | None:
    scores = normalize_axes(axes)
    base = opportunity_score(scores)
    if base is None or any(scores.get(axis) is None for axis in REQUIRED_ALLOCATION_AXES):
        return None
    cash_proximity = 10.0 - scores["time_to_first_dollar"]
    recurring = scores["path_to_recurring"]
    difficulty_drag = scores["difficulty"] * 0.7
    time_drag = scores["time_to_revenue"] * 0.5
    return round(base + cash_proximity + recurring - difficulty_drag - time_drag, 2)


def cash_proximity_score(axes: dict[str, Any] | None) -> float | None:
    scores = normalize_axes(axes)
    if scores.get("time_to_first_dollar") is None or scores.get("path_to_recurring") is None:
        return None
    return round((10.0 - scores["time_to_first_dollar"]) + scores["path_to_recurring"], 2)


def next_domino_score(row: dict[str, Any]) -> float | None:
    scores = normalize_axes(row.get("axes"))
    if any(scores.get(axis) is None for axis in REQUIRED_DOMINO_AXES):
        return None
    allocation = allocation_score(scores)
    if allocation is None:
        return None
    topple = normalize_topple(row.get("topple"))
    gate = str(topple.get("gate") or "capability_gap")
    gate_drag = TOPPLE_GATES.get(gate, 5)
    if topple.get("missing_capability"):
        gate_drag = max(gate_drag, TOPPLE_GATES["capability_gap"])
    return round(
        allocation
        + scores["constraint"]
        + scores["leverage"]
        + scores["proof_speed"]
        + scores["topple_reversibility"]
        - gate_drag,
        2,
    )


def normalize_spot(spot: dict[str, Any] | None) -> dict[str, str]:
    raw = spot or {}
    return {field: str(raw.get(field) or "").strip() for field in SPOT_FIELDS}


def normalize_topple(topple: dict[str, Any] | None) -> dict[str, str]:
    raw = topple or {}
    normalized = {field: str(raw.get(field) or "").strip() for field in TOPPLE_FIELDS}
    if normalized["gate"] not in TOPPLE_GATES:
        normalized["gate"] = "capability_gap" if normalized["missing_capability"] else "human_edge"
    return normalized


def topple_status(row: dict[str, Any]) -> str:
    topple = normalize_topple(row.get("topple"))
    if topple["missing_capability"] or topple["gate"] == "capability_gap":
        return f"build capability first: {topple['missing_capability'] or 'missing capability not named'}"
    if topple["gate"] in {"ai_reversible", "codex_build"}:
        return "topple-ready"
    if topple["gate"] == "ember_route":
        return "route to Ember before toppling"
    if topple["gate"] == "james_reserved":
        return "James-reserved"
    return "human-edge"


def score_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["axes"] = normalize_axes(out.get("axes"))
    out["spot"] = normalize_spot(out.get("spot"))
    out["topple"] = normalize_topple(out.get("topple"))
    out["opportunity_score"] = opportunity_score(out["axes"])
    out["allocation_score"] = allocation_score(out["axes"])
    out["cash_proximity_score"] = cash_proximity_score(out["axes"])
    out["next_domino_score"] = next_domino_score(out)
    out["topple_status"] = topple_status(out)
    return out


def seed_opportunities(now: str | None = None) -> list[dict[str, Any]]:
    stamp = now or utc_now()
    return [
        _seed_row(
            "assessment-funnel-delivery-proof",
            "Assessment Funnel Delivery Proof",
            "The assessment funnel can capture leads, but the real value only exists when a lead gets scored, delivered, alerted, and traced.",
            "FPAI first; later founders buying the Bottleneck / Allocation Score path.",
            {"pain": 9, "market": 7, "difficulty": 2, "time_to_revenue": 1, "compounding": 9, "time_to_first_dollar": 1, "path_to_recurring": 8, "constraint": 10, "leverage": 10, "proof_speed": 10, "topple_reversibility": 10},
            stamp,
            spot={
                "current_constraint": "Revenue proof is trapped until the assessment promise is verified by a real end-to-end test lead after d193 activation.",
                "value_trapped": "Traffic and lead capture become cash-proximate only when the Allocation Score delivery loop proves itself.",
                "smallest_domino": "Run the d193 funnel-delivery proof: activate through the d182 guard, submit one test Life assessment lead, trace email/TG/page acknowledgement, and log the result.",
            },
            topple={
                "next_action": "Queue a reversible local verifier/spec that runs only after d193 is merged and activation evidence exists; no outreach, spend, secrets, or live release authority.",
                "gate": "ai_reversible",
                "proof": "One test Life assessment lead produces recipient email delivery status, founder alert status, page acknowledgement, and capability-ledger learning.",
            },
        ),
        _seed_row(
            "resource-optimization-audit",
            "Resource Optimization Audit",
            "BBB / savings-split offer that finds waste, duplicated tools, and fast AI substitution paths.",
            "Businesses with visible software, labor, or ops waste.",
            {"pain": 8, "market": 7, "difficulty": 3, "time_to_revenue": 2, "compounding": 8, "time_to_first_dollar": 2, "path_to_recurring": 7, "constraint": 8, "leverage": 8, "proof_speed": 8, "topple_reversibility": 9},
            stamp,
            spot={
                "current_constraint": "Revenue proof is constrained by not having one low-friction paid diagnostic in motion.",
                "value_trapped": "Visible SaaS/labor waste can fund the implementation instead of requiring new budget.",
                "smallest_domino": "Package one Resource Optimization Audit from the existing assessment/score proof.",
            },
            topple={
                "next_action": "Draft the diagnostic intake and proof packet; do not send outreach without James.",
                "gate": "james_reserved",
                "proof": "One James-approved prospect or internal demo receives a scoped audit packet.",
            },
        ),
        _seed_row(
            "ai-voice-receptionist",
            "AI Voice Receptionist",
            "Missed calls and repetitive front-desk intake for service businesses.",
            "Local service businesses, clinics, hospitality, and appointment-based operators.",
            {"pain": 8, "market": 8, "difficulty": 4, "time_to_revenue": 3, "compounding": 7, "time_to_first_dollar": 3, "path_to_recurring": 8, "constraint": 6, "leverage": 7, "proof_speed": 6, "topple_reversibility": 6},
            stamp,
            spot={
                "current_constraint": "The offer needs a narrow live-call workflow before market proof.",
                "value_trapped": "Missed calls are close to revenue, but live service reliability must be bounded.",
                "smallest_domino": "Prove one appointment-intake simulation with logged transcript and fallback.",
            },
            topple={
                "next_action": "Build a sandbox voice-call intake proof before touching a live phone number.",
                "gate": "codex_build",
                "proof": "A fixture call produces the expected appointment payload and rollback path.",
            },
        ),
        _seed_row(
            "medical-documentation-agent",
            "Medical Documentation Agent",
            "Clinicians lose time to charting and documentation after care moments.",
            "Clinics, practices, and healthcare operators with documentation burden.",
            {"pain": 9, "market": 8, "difficulty": 8, "time_to_revenue": 6, "compounding": 7, "time_to_first_dollar": 7, "path_to_recurring": 9, "constraint": 5, "leverage": 8, "proof_speed": 3, "topple_reversibility": 3},
            stamp,
            spot={
                "current_constraint": "Healthcare compliance and workflow proof are larger than the current reversible lane.",
                "value_trapped": "High time value, but not the smallest safe domino.",
                "smallest_domino": "Defer until a non-clinical documentation sandbox exists.",
            },
            topple={
                "next_action": "Do not pursue live clinic proof yet.",
                "gate": "capability_gap",
                "proof": "A later sandbox can summarize non-sensitive sample notes with audit trail.",
                "missing_capability": "healthcare-safe sandbox, compliance review, and human operator workflow",
            },
        ),
        _seed_row(
            "finance-allocation-engine",
            "Finance Allocation Engine",
            "Operators need clearer allocation, runway, leak, and next-dollar decisions.",
            "Founders, small operators, and organizations with fragmented financial context.",
            {"pain": 7, "market": 7, "difficulty": 5, "time_to_revenue": 4, "compounding": 9, "time_to_first_dollar": 5, "path_to_recurring": 8, "constraint": 7, "leverage": 8, "proof_speed": 5, "topple_reversibility": 6},
            stamp,
            spot={
                "current_constraint": "Useful allocation outputs depend on trusted input surfaces and proof logs.",
                "value_trapped": "Runway/leak clarity can unlock both savings and better AI allocation decisions.",
                "smallest_domino": "Use existing read-only financial hub signals to produce one next-dollar recommendation.",
            },
            topple={
                "next_action": "Stage a read-only next-dollar report; no transfer, trade, or account action.",
                "gate": "james_reserved",
                "proof": "James reviews one recommendation with source rows and no autonomous money movement.",
            },
        ),
        _seed_row(
            "opportunity-intelligence-engine",
            "Opportunity Intelligence Engine",
            "The system lacked a standing loop for deciding what to build next.",
            "FPAI first; later teams that need AI capability-to-market adoption intelligence.",
            {"pain": 8, "market": 6, "difficulty": 4, "time_to_revenue": 4, "compounding": 10, "time_to_first_dollar": 5, "path_to_recurring": 7, "constraint": 9, "leverage": 10, "proof_speed": 9, "topple_reversibility": 10},
            stamp,
            spot={
                "current_constraint": "The loop can rank opportunities but has not named the next domino and topple gate explicitly.",
                "value_trapped": "Every build/revenue choice gets cheaper when Spot and Topple are first-class outputs.",
                "smallest_domino": "Add Next Domino scoring to the existing Opportunity Portfolio.",
            },
            topple={
                "next_action": "Ship the read-only Next Domino view and feed it into council context.",
                "gate": "codex_build",
                "proof": "Tests show the top domino includes score, gate, proof, and capability-gap handling.",
            },
        ),
    ]


def _seed_row(
    ident: str,
    title: str,
    problem: str,
    who_pays: str,
    axes: dict[str, Any],
    stamp: str,
    *,
    spot: dict[str, str] | None = None,
    topple: dict[str, str] | None = None,
) -> dict[str, Any]:
    return score_row(
        {
            "id": ident,
            "title": title,
            "status": "active",
            "source": "d186_seeded_portfolio",
            "created_at": stamp,
            "updated_at": stamp,
            "questions": {
                "problem": problem,
                "who_pays": who_pays,
                "pain": "",
                "can_ai_solve": "",
                "prove_quickly": "",
                "recurring": "",
                "makes_us_smarter": "",
                "unlocks_more": "",
            },
            "spot": spot or {},
            "topple": topple or {},
            "axes": axes,
            "score_basis": "James-seeded candidate; numeric axes are explicit first-pass ranking inputs, not market facts.",
            "signals": [],
            "actual_vs_expected": {},
        }
    )


def load_portfolio(path: Path | str = DEFAULT_LEDGER) -> dict[str, Any]:
    ledger = Path(path)
    if not ledger.exists():
        return {"schema": "fpai_opportunity_portfolio_v1", "updated_at": "", "opportunities": []}
    try:
        data = json.loads(ledger.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"schema": "fpai_opportunity_portfolio_v1", "updated_at": "", "opportunities": []}
    if isinstance(data, list):
        data = {"schema": "fpai_opportunity_portfolio_v1", "updated_at": "", "opportunities": data}
    data.setdefault("schema", "fpai_opportunity_portfolio_v1")
    data.setdefault("updated_at", "")
    data.setdefault("opportunities", [])
    return data


def save_portfolio(portfolio: dict[str, Any], path: Path | str = DEFAULT_LEDGER) -> dict[str, Any]:
    ledger = Path(path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    portfolio = dict(portfolio)
    portfolio["updated_at"] = utc_now()
    portfolio["opportunities"] = [score_row(row) for row in portfolio.get("opportunities", [])]
    ledger.write_text(json.dumps(portfolio, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return portfolio


def ensure_seeded(path: Path | str = DEFAULT_LEDGER, *, now: str | None = None) -> dict[str, Any]:
    portfolio = load_portfolio(path)
    by_id = {row.get("id"): row for row in portfolio.get("opportunities", []) if row.get("id")}
    changed = False
    for seed in seed_opportunities(now=now):
        existing = by_id.get(seed["id"])
        if not existing:
            portfolio["opportunities"].append(seed)
            changed = True
            continue
        merged = dict(seed)
        merged.update(existing)
        merged["questions"] = {**seed.get("questions", {}), **(existing.get("questions") or {})}
        merged["axes"] = {**seed.get("axes", {}), **(existing.get("axes") or {})}
        by_id[seed["id"]] = merged
    if by_id:
        portfolio["opportunities"] = [by_id.get(row.get("id"), row) for row in portfolio.get("opportunities", [])]
    if changed:
        return save_portfolio(portfolio, path)
    portfolio["opportunities"] = [score_row(row) for row in portfolio.get("opportunities", [])]
    return portfolio


def ranked(portfolio: dict[str, Any]) -> dict[str, Any]:
    rows = [score_row(row) for row in portfolio.get("opportunities", [])]
    return {
        "schema": portfolio.get("schema", "fpai_opportunity_portfolio_v1"),
        "updated_at": portfolio.get("updated_at", ""),
        "count": len(rows),
        "top_opportunity": sorted(rows, key=lambda r: _rank_key(r, "opportunity_score"))[:5],
        "top_allocation": sorted(rows, key=lambda r: _rank_key(r, "allocation_score"))[:3],
        "top_cash_proximity": sorted(rows, key=lambda r: _rank_key(r, "cash_proximity_score"))[:3],
        "next_domino": sorted(rows, key=lambda r: _rank_key(r, "next_domino_score"))[:3],
        "all": sorted(rows, key=lambda r: _rank_key(r, "allocation_score")),
    }


def _rank_key(row: dict[str, Any], field: str) -> tuple[float, str]:
    score = row.get(field)
    return (-(score if score is not None else -1), str(row.get("title") or row.get("id") or ""))


def format_portfolio(view: dict[str, Any], *, html_mode: bool = False) -> str:
    esc = html.escape if html_mode else str
    bold_open, bold_close = ("<b>", "</b>") if html_mode else ("", "")
    lines = [f"{bold_open}Opportunity Portfolio{bold_close}"]
    lines.append(f"rows: {view.get('count', 0)} · read/rank/propose only")
    lines.append("")
    lines.append(f"{bold_open}Top by Opportunity Score{bold_close}")
    lines.extend(_format_rows(view.get("top_opportunity", []), "opportunity_score", esc))
    lines.append("")
    lines.append(f"{bold_open}Do-now by Allocation Score{bold_close}")
    lines.extend(_format_rows(view.get("top_allocation", []), "allocation_score", esc))
    lines.append("")
    lines.append(f"{bold_open}Closest to Cash{bold_close}")
    lines.extend(_format_rows(view.get("top_cash_proximity", []), "cash_proximity_score", esc))
    lines.append("")
    lines.append(f"{bold_open}Next Domino: Spot -> Topple -> Proof{bold_close}")
    lines.extend(_format_domino_rows(view.get("next_domino", []), esc))
    return "\n".join(lines)


def _format_rows(rows: Iterable[dict[str, Any]], field: str, esc) -> list[str]:
    out = []
    for idx, row in enumerate(rows, 1):
        score = row.get(field)
        score_text = "blank" if score is None else f"{score:g}"
        problem = ((row.get("questions") or {}).get("problem") or "").strip()
        suffix = f" — {problem[:90]}" if problem else ""
        out.append(f"{idx}. {esc(str(row.get('title') or row.get('id')))} ({field.replace('_', ' ')}: {score_text}){esc(suffix)}")
    return out or ["(none scored yet)"]


def _format_domino_rows(rows: Iterable[dict[str, Any]], esc) -> list[str]:
    out = []
    for idx, row in enumerate(rows, 1):
        score = row.get("next_domino_score")
        score_text = "blank" if score is None else f"{score:g}"
        title = esc(str(row.get("title") or row.get("id")))
        spot = row.get("spot") or {}
        topple = row.get("topple") or {}
        current_constraint = esc(str(spot.get("current_constraint") or "constraint not named"))
        next_action = esc(str(topple.get("next_action") or "topple not named"))
        gate = esc(str(topple.get("gate") or "unknown"))
        proof = esc(str(topple.get("proof") or "proof not named"))
        status = esc(str(row.get("topple_status") or "unknown"))
        out.append(
            f"{idx}. {title} (next domino score: {score_text}; gate: {gate}; status: {status})\n"
            f"   Spot: {current_constraint[:160]}\n"
            f"   Topple: {next_action[:160]}\n"
            f"   Proof: {proof[:160]}"
        )
    return out or ["(no domino scored yet)"]


def digest_line(path: Path | str = DEFAULT_LEDGER) -> str:
    view = ranked(ensure_seeded(path))
    domino = view["next_domino"][0] if view["next_domino"] else {}
    cash = view["top_cash_proximity"][0] if view["top_cash_proximity"] else {}
    return (
        "opportunities: "
        f"next-domino {domino.get('title', 'none')} ({domino.get('next_domino_score', 'blank')}, "
        f"{domino.get('topple_status', 'unknown')}); "
        f"closest-cash {cash.get('title', 'none')} ({cash.get('cash_proximity_score', 'blank')})."
    )


def council_context(path: Path | str = DEFAULT_LEDGER) -> str:
    view = ranked(ensure_seeded(path))
    lines = [
        "OPPORTUNITY PORTFOLIO — Council must Spot the next domino before proposing work.",
        "Choose from top Next Domino Score unless explicitly explaining why not.",
        "Topple remains read/rank/propose only here; build arming still requires Council + Constitution Check.",
    ]
    for row in view["next_domino"]:
        spot = row.get("spot") or {}
        topple = row.get("topple") or {}
        lines.append(
            f"- {row.get('title')}: domino={row.get('next_domino_score')} "
            f"allocation={row.get('allocation_score')} cash={row.get('cash_proximity_score')} "
            f"status={row.get('topple_status')} gate={(topple.get('gate') or '')} "
            f"spot={(spot.get('current_constraint') or '')[:140]} "
            f"topple={(topple.get('next_action') or '')[:140]} "
            f"proof={(topple.get('proof') or '')[:140]}"
        )
    return "\n".join(lines)


def run_gap_scan(
    path: Path | str = DEFAULT_LEDGER,
    *,
    scan_ledger: Path | str = DEFAULT_SCAN_LEDGER,
    capability_ledger: Path | str = DEFAULT_CAPABILITY_LEDGER,
    web_urls: Iterable[str] | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    stamp = now or utc_now()
    portfolio = ensure_seeded(path, now=stamp)
    signals = _collect_signals(capability_ledger=capability_ledger, web_urls=web_urls)
    changed = _apply_signals(portfolio, signals, stamp)
    saved = save_portfolio(portfolio, path)
    row = {
        "schema": "fpai_opportunity_gap_scan_v1",
        "ts": stamp,
        "signals_seen": len(signals),
        "opportunities_updated": changed,
        "top_allocation": [
            {"id": r.get("id"), "title": r.get("title"), "allocation_score": r.get("allocation_score")}
            for r in ranked(saved)["top_allocation"]
        ],
        "next_domino": [
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "next_domino_score": r.get("next_domino_score"),
                "topple_status": r.get("topple_status"),
            }
            for r in ranked(saved)["next_domino"]
        ],
    }
    scan_path = Path(scan_ledger)
    scan_path.parent.mkdir(parents=True, exist_ok=True)
    with scan_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def _collect_signals(*, capability_ledger: Path | str, web_urls: Iterable[str] | None) -> list[dict[str, str]]:
    signals: list[dict[str, str]] = []
    cap = Path(capability_ledger)
    if cap.exists():
        for raw in cap.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]:
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            text = " ".join(str(row.get(k) or "") for k in ("title", "source_id", "reusable_intelligence", "basis"))
            if text.strip():
                signals.append({"source": "capability_ledger", "text": text[:600]})
    urls = list(web_urls) if web_urls is not None else list(WEB_URLS)
    if os.environ.get("FPAI_OPPORTUNITY_WEB", "1").lower() in {"1", "true", "yes", "on"}:
        for url in urls[:5]:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "FPAI opportunity scanner; read-only"})
                with urllib.request.urlopen(req, timeout=5) as response:
                    body = response.read(20000).decode("utf-8", errors="replace")
                text = re.sub(r"<[^>]+>", " ", body)
                text = " ".join(html.unescape(text).split())
                if text:
                    signals.append({"source": url, "text": text[:1200]})
            except Exception:
                continue
    return signals


def _apply_signals(portfolio: dict[str, Any], signals: list[dict[str, str]], stamp: str) -> int:
    changed = 0
    rows = {row.get("id"): row for row in portfolio.get("opportunities", [])}
    keyword_map = {
        "resource-optimization-audit": ("cost", "waste", "saving", "saas", "spend", "duplicate"),
        "ai-voice-receptionist": ("call", "phone", "voice", "reception", "appointment", "booking"),
        "medical-documentation-agent": ("medical", "clinic", "doctor", "scribe", "documentation", "charting"),
        "finance-allocation-engine": ("finance", "allocation", "runway", "cash", "budget", "accounting"),
        "opportunity-intelligence-engine": ("opportunity", "market adoption", "gap", "frontier", "capability"),
    }
    for signal in signals:
        text = signal.get("text", "")
        lowered = text.lower()
        for ident, words in keyword_map.items():
            if not any(word in lowered for word in words):
                continue
            row = rows.get(ident)
            if not row:
                continue
            existing = row.setdefault("signals", [])
            snippet = text[:280]
            if any(item.get("text") == snippet and item.get("source") == signal.get("source") for item in existing):
                continue
            existing.append({"ts": stamp, "source": signal.get("source", ""), "text": snippet})
            row["updated_at"] = stamp
            changed += 1
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rank and scan the Opportunity Portfolio.")
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--scan-ledger", type=Path, default=DEFAULT_SCAN_LEDGER)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--scan", action="store_true", help="Run the cheap gap scan and update signal metadata.")
    args = parser.parse_args(argv)

    if args.scan:
        result = run_gap_scan(args.ledger, scan_ledger=args.scan_ledger)
        print(json.dumps(result, indent=2, sort_keys=True) if args.json else f"scan updated {result['opportunities_updated']} opportunities")
        return 0
    view = ranked(ensure_seeded(args.ledger))
    print(json.dumps(view, indent=2, sort_keys=True) if args.json else format_portfolio(view))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

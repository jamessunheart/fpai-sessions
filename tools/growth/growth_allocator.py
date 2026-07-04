#!/usr/bin/env python3
"""G5 kill/breed allocator for Growth Stack assets.

Runs a local, reviewable cycle over JSONL asset rows: score by Growth CCD, kill
losers below channel floors, breed children from champions with one mutated gene,
distill reusable patterns, and emit tomorrow's allocation plan. No spend, send,
deploy, or external API call happens here.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_PATTERNS = Path("core/STATE/WINNING_PATTERNS.md")
DEFAULT_PLAN = Path("core/BUILD/results/growth_allocator_plan.json")
DEFAULT_LEDGER = Path.home() / ".config/fpai/growth/assets.jsonl"
CHANNEL_FLOORS = {
    "ad": "ads need at least one lead per 1000 impressions",
    "article": "articles need at least one assessment start in 30d",
    "email": "emails need at least 1% click rate",
}
GENE_ORDER = ("hook", "frame", "audience", "format", "channel")
MUTATIONS = {
    "hook": ("clearer bottleneck", "free monday move", "hidden allocation leak"),
    "frame": ("promise", "exec", "savings", "proof"),
    "audience": ("owner_operator", "executive_team", "agency_founder", "ai_builder"),
    "format": ("article", "checklist", "email", "short_post"),
    "channel": ("seo", "meta", "email", "social"),
}


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _num(row: dict[str, Any], key: str) -> float:
    outcomes = row.get("outcomes") if isinstance(row.get("outcomes"), dict) else {}
    value = row.get(key, outcomes.get(key))
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def asset_id(row: dict[str, Any]) -> str:
    return str(row.get("asset_id") or row.get("variant_id") or row.get("id") or "")


def asset_type(row: dict[str, Any]) -> str:
    return str(row.get("type") or ("ad" if row.get("variant_id") else "asset"))


def score_asset(row: dict[str, Any]) -> dict[str, Any]:
    impressions = _num(row, "impressions")
    clicks = _num(row, "clicks")
    leads = _num(row, "leads")
    audits = _num(row, "audits")
    deals = _num(row, "deals")
    value = _num(row, "value_usd") or _num(row, "deal_value")
    spend = _num(row, "spend_usd") or _num(row, "cost_usd")
    build_hours = _num(row, "build_seconds") / 3600
    pipeline = leads + audits * 2 + deals * 8 + value / 1000
    denominator = max(spend + build_hours * 0.0, 0.01)
    click_rate = clicks / impressions if impressions else 0.0
    lead_rate = leads / impressions if impressions else 0.0
    return {
        "asset_id": asset_id(row),
        "type": asset_type(row),
        "status": row.get("status", "alive"),
        "impressions": int(impressions),
        "clicks": int(clicks),
        "leads": int(leads),
        "audits": int(audits),
        "deals": int(deals),
        "value_usd": round(value, 2),
        "spend_usd": round(spend, 2),
        "click_rate": round(click_rate, 6),
        "lead_rate": round(lead_rate, 6),
        "growth_ccd": round(pipeline / denominator, 4),
    }


def should_kill(row: dict[str, Any], scored: dict[str, Any]) -> tuple[bool, str]:
    typ = scored["type"]
    if row.get("status") == "champion":
        return False, "already champion"
    if typ == "ad" and scored["impressions"] >= 1000 and scored["leads"] == 0:
        return True, CHANNEL_FLOORS["ad"]
    if typ == "article" and _num(row, "assessment_starts") <= 0 and _num(row, "days_live") >= 30:
        return True, CHANNEL_FLOORS["article"]
    if typ == "email" and scored["click_rate"] < 0.01 and scored["impressions"] >= 100:
        return True, CHANNEL_FLOORS["email"]
    return False, "above floor"


def mark_assets(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    updated = []
    scored_rows = []
    alive_scored = []
    for row in rows:
        scored = score_asset(row)
        kill, reason = should_kill(row, scored)
        next_row = dict(row)
        next_row["growth_score"] = scored
        if kill:
            next_row["status"] = "killed"
            next_row["kill_reason"] = reason
        elif scored["growth_ccd"] > 0 and scored["leads"] > 0:
            next_row["status"] = "champion"
            alive_scored.append(scored)
        else:
            next_row.setdefault("status", "alive")
        updated.append(next_row)
        scored_rows.append(scored | {"decision": next_row["status"], "reason": next_row.get("kill_reason", "")})
    return updated, scored_rows


def mutate_genome(genome: dict[str, Any], child_index: int) -> tuple[dict[str, Any], str]:
    gene = GENE_ORDER[child_index % len(GENE_ORDER)]
    values = MUTATIONS[gene]
    current = str(genome.get(gene, ""))
    replacement = next((value for value in values if value != current), values[0])
    child = dict(genome)
    child[gene] = replacement
    return child, gene


def breed_children(champions: list[dict[str, Any]], *, children_per_cycle: int = 3) -> list[dict[str, Any]]:
    children = []
    ordered = sorted(champions, key=lambda row: row.get("growth_score", {}).get("growth_ccd", 0), reverse=True)
    for index, parent in enumerate(ordered[:children_per_cycle]):
        parent_id = asset_id(parent)
        genome = parent.get("genome") if isinstance(parent.get("genome"), dict) else {}
        child_genome, mutated_gene = mutate_genome(genome, index)
        digest = hashlib.sha1(json.dumps([parent_id, child_genome], sort_keys=True).encode("utf-8")).hexdigest()[:8]
        children.append(
            {
                "schema": "fpai.growth.asset.v1",
                "asset_id": f"{parent_id}-g{int(parent.get('generation') or 0) + 1}-{digest}",
                "type": asset_type(parent),
                "status": "alive",
                "parent_id": parent_id,
                "generation": int(parent.get("generation") or 0) + 1,
                "genome": child_genome,
                "mutated_gene": mutated_gene,
                "created_at": now_utc(),
                "outcomes": {"impressions": 0, "clicks": 0, "leads": 0, "audits": 0, "deals": 0, "value_usd": 0},
            }
        )
    return children


def allocation_plan(scored: list[dict[str, Any]], children: list[dict[str, Any]], *, ad_budget_usd: float = 10.0) -> dict[str, Any]:
    champions = [row for row in scored if row["decision"] == "champion"]
    best = sorted(champions, key=lambda row: row["growth_ccd"], reverse=True)
    best_cell = best[0] if best else None
    return {
        "generated_at": now_utc(),
        "ad_budget_usd": min(max(ad_budget_usd, 0.0), 10.0),
        "content_run": bool(children),
        "allocate_to_asset_id": best_cell["asset_id"] if best_cell else "",
        "allocate_to_type": best_cell["type"] if best_cell else "",
        "reason": (
            f"highest measured Growth CCD {best_cell['growth_ccd']} among champions"
            if best_cell else "no champion yet; keep generation in review/dry-run"
        ),
        "children": [asset_id(row) for row in children],
    }


def distill_patterns(rows: list[dict[str, Any]], path: Path) -> None:
    champions = [row for row in rows if row.get("status") == "champion"]
    lines = [
        "# Winning Patterns",
        "",
        f"_Updated {now_utc()} by Growth Stack allocator._",
        "",
        "Only ledger-proven champion assets belong here. No invented benchmarks.",
        "",
    ]
    if not champions:
        lines.append("- No champion assets yet.")
    for row in sorted(champions, key=lambda item: item.get("growth_score", {}).get("growth_ccd", 0), reverse=True):
        genome = row.get("genome") if isinstance(row.get("genome"), dict) else {}
        score = row.get("growth_score", {})
        lines.append(
            f"- `{asset_id(row)}` ({asset_type(row)}): frame={genome.get('frame', '')}, "
            f"hook={genome.get('hook', '')}, channel={genome.get('channel', '')}; "
            f"leads={score.get('leads', 0)}, Growth CCD={score.get('growth_ccd', 0)}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def run_cycle(
    *,
    ledger_path: Path,
    output_path: Path = DEFAULT_PLAN,
    patterns_path: Path = DEFAULT_PATTERNS,
    ad_budget_usd: float = 10.0,
    write: bool = True,
) -> dict[str, Any]:
    rows = read_jsonl(ledger_path)
    marked, scored = mark_assets(rows)
    champions = [row for row in marked if row.get("status") == "champion"]
    children = breed_children(champions)
    plan = allocation_plan(scored, children, ad_budget_usd=ad_budget_usd)
    result = {
        "schema": "fpai.growth.allocator_result.v1",
        "ok": True,
        "ledger_path": str(ledger_path),
        "scored": scored,
        "killed": [row["asset_id"] for row in scored if row["decision"] == "killed"],
        "champions": [row["asset_id"] for row in scored if row["decision"] == "champion"],
        "bred_children": children,
        "allocation_plan": plan,
    }
    if write:
        write_jsonl(ledger_path, marked + children)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        distill_patterns(marked, patterns_path)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--out", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--patterns", type=Path, default=DEFAULT_PATTERNS)
    parser.add_argument("--ad-budget-usd", type=float, default=10.0)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_cycle(
        ledger_path=args.ledger,
        output_path=args.out,
        patterns_path=args.patterns,
        ad_budget_usd=args.ad_budget_usd,
        write=not args.dry_run,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

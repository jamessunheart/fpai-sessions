#!/usr/bin/env python3
"""Generate docs/ARCHITECTURE.md from repo and live-system state.

The live server supplies decisions through brain_index and service state through
systemctl. Local/sandbox runs degrade to honest placeholders so the document is
still deterministic and shareable without production credentials.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "ARCHITECTURE.md"
DEFAULT_REGISTRY = REPO_ROOT / "core" / "BUILD" / "REGISTRY.json"
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))

SERVICE_NAMES = (
    "sh-brain-tgbot",
    "fpai-build-loop.timer",
    "fpai-council.timer",
    "fpai-morning-digest.timer",
)

DB_TABLES = (
    "decisions",
    "corrections",
    "thread",
    "tg_messages",
    "user_channels",
    "agent_passports",
    "user_agents",
    "user_profiles",
    "beacon_campaigns",
)

FUNCTIONS = (
    {
        "name": "Beacon",
        "does": "Acquisition + attribution + content campaigns",
        "default_status": "building (d037-d038)",
        "where": "tools/beacon/ + docs/content_bank/",
        "ids": ("d037", "d038"),
    },
    {
        "name": "Spark",
        "does": "First-touch routing: 3 questions -> path",
        "default_status": "live (tgbot.py)",
        "where": "SERVICES/sunheart-brain/curator/tgbot.py",
        "ids": (),
    },
    {
        "name": "Ember",
        "does": "Persistent memory + context steward",
        "default_status": "live (memory/ + tgbot.py)",
        "where": "memory/ + SERVICES/sunheart-brain/curator/tgbot.py",
        "ids": (),
    },
    {
        "name": "Hermes",
        "does": "Channel gateway: Telegram/web/SMS/WhatsApp adapters",
        "default_status": "building (d034)",
        "where": "SERVICES/*/channels/ + curator/telegram.py",
        "ids": ("d034",),
    },
    {
        "name": "Council",
        "does": "Multi-lens architecture debate -> build proposals",
        "default_status": "live (debate.py)",
        "where": "tools/council/debate.py",
        "ids": (),
    },
    {
        "name": "Forge",
        "does": "Build loop: Codex builds + Claude review + merge gate",
        "default_status": "live (build loop)",
        "where": "tools/build_loop/ + tools/merge/",
        "ids": (),
    },
    {
        "name": "Steward",
        "does": "Per-user agent: isolated namespace + profile + CORA",
        "default_status": "building (d039-d043)",
        "where": "agent_passports + user_agents + user_profiles",
        "ids": ("d039", "d040", "d041", "d042", "d043"),
    },
    {
        "name": "Ledger",
        "does": "Ops truth ledger + cost tracking + correction signal",
        "default_status": "live (ops_log.py + track.py)",
        "where": "tools/build_loop/ops_log.py + tools/cost/track.py",
        "ids": (),
    },
    {
        "name": "Loop",
        "does": "Self-evolution: learning signal + preference pairs",
        "default_status": "building (d010-d023)",
        "where": "tools/learn/ + preference_pairs.jsonl",
        "ids": tuple(f"d{i:03d}" for i in range(10, 24)),
    },
)


def utc_now() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    if not path.exists():
        return {"active_builds": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _entry_matches_id(entry: dict[str, Any], decision_id: str) -> bool:
    needle = decision_id.lower()
    text = " ".join(
        str(entry.get(key, ""))
        for key in ("id", "slug", "branch", "spec", "notes")
    ).lower()
    return needle in text


def status_from_registry(function: dict[str, Any], registry: dict[str, Any]) -> str:
    ids = function.get("ids") or ()
    if not ids:
        return str(function["default_status"])
    matched: dict[str, list[dict[str, Any]]] = {decision_id: [] for decision_id in ids}
    for entry in registry.get("active_builds", []):
        for decision_id in ids:
            if _entry_matches_id(entry, decision_id):
                matched[decision_id].append(entry)
    present = {decision_id: entries for decision_id, entries in matched.items() if entries}
    if not present:
        return str(function["default_status"])
    statuses = {
        str(entry.get("status", "")).lower()
        for entries in present.values()
        for entry in entries
    }
    matched_ids = tuple(present.keys())
    if len(present) == len(ids) and statuses <= {"done", "merged"} and statuses:
        return "live (" + ", ".join(matched_ids) + ")"
    if "building" in statuses or "done" in statuses:
        return "building (" + ", ".join(matched_ids) + ")"
    return str(function["default_status"])


def function_rows(registry: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    for function in FUNCTIONS:
        rows.append(
            {
                "name": str(function["name"]),
                "does": str(function["does"]),
                "status": status_from_registry(function, registry),
                "where": str(function["where"]),
            }
        )
    return rows


def database_url() -> str | None:
    for key in ("BRAIN_INDEX_DB_URL", "DATABASE_URL", "DB_URL"):
        value = os.environ.get(key)
        if value:
            return value
    return None


def fetch_decision_queue(dsn: str | None = None) -> list[dict[str, str]]:
    dsn = dsn if dsn is not None else database_url()
    if not dsn:
        return []
    try:
        import psycopg  # type: ignore
    except Exception:
        return []
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'brain_index'
                      AND table_name = 'decisions'
                    """
                )
                columns = {str(row[0]) for row in cur.fetchall()}
                if "id" not in columns or "needs_build" not in columns:
                    return []
                title_expr = "'Untitled'"
                for column in ("title", "question"):
                    if column in columns:
                        title_expr = f"COALESCE(NULLIF({column}, ''), {title_expr})"
                status_expr = "'queued'"
                for column in ("build_status", "status"):
                    if column in columns:
                        status_expr = f"COALESCE(NULLIF({column}, ''), {status_expr})"
                order_expr = "created_at ASC" if "created_at" in columns else "id ASC"
                query = f"""
                    SELECT id::text, {title_expr} AS title, {status_expr} AS status
                    FROM brain_index.decisions
                    WHERE COALESCE(needs_build, false)
                    ORDER BY {order_expr}
                """
                cur.execute(query)
                return [
                    {"id": str(row[0]), "title": str(row[1]), "status": str(row[2])}
                    for row in cur.fetchall()
                ]
    except Exception:
        return []


def service_snapshot(runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> list[dict[str, str]]:
    try:
        result = runner(
            ["systemctl", "list-units", "--all", "--no-pager", "--plain"],
            check=False,
            text=True,
            capture_output=True,
            timeout=8,
        )
    except Exception:
        result = None

    output = result.stdout if result and result.returncode == 0 else ""
    rows: list[dict[str, str]] = []
    for service in SERVICE_NAMES:
        matching_line = next((line for line in output.splitlines() if line.startswith(service + " ")), "")
        status = "unknown"
        description = "Expected on server 162; systemctl unavailable in this run"
        if matching_line:
            parts = matching_line.split(None, 4)
            if len(parts) >= 4:
                status = "/".join(parts[1:4])
            if len(parts) >= 5:
                description = parts[4]
        rows.append({"service": service, "host": "162", "runs": f"{status} - {description}"})
    rows.append(
        {
            "service": "brain_index",
            "host": "162:25432",
            "runs": "Postgres schema tables: " + ", ".join(DB_TABLES),
        }
    )
    return rows


def md_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(cell.replace("\n", "<br>") for cell in row) + " |")
    return "\n".join(lines)


def decision_label(row: dict[str, str]) -> str:
    raw = str(row.get("id", "")).strip()
    if raw.startswith("d"):
        return raw
    if raw.isdigit():
        return "d" + raw.zfill(3)
    return raw or "d???"


def render_architecture(
    *,
    registry: dict[str, Any],
    decisions: list[dict[str, str]],
    services: list[dict[str, str]],
    generated_at: str | None = None,
) -> str:
    generated_at = generated_at or utc_now()
    functions = function_rows(registry)
    function_table = md_table(
        ("Name", "What it does", "Status", "Where it lives"),
        [(row["name"], row["does"], row["status"], row["where"]) for row in functions],
    )
    service_table = md_table(
        ("Service", "Host", "What it runs"),
        [(row["service"], row["host"], row["runs"]) for row in services],
    )
    queue_rows = [
        (decision_label(row), row.get("title", "Untitled"), row.get("status", "queued"))
        for row in decisions
    ]
    if not queue_rows:
        queue_rows = [("none", "No live `needs_build=true` decisions found or DB unavailable", "clear")]
    queue_table = md_table(("dNNN", "title", "status"), queue_rows)
    gap_lines = [
        f"- {'⏳ building' if 'build' in row.get('status', '').lower() else '📋 planned'} {decision_label(row)} - {row.get('title', 'Untitled')}"
        for row in decisions
    ]
    if not gap_lines:
        gap_lines = ["- No live `needs_build=true` gaps found, or brain_index was unavailable during generation."]

    return f"""# FPOS Architecture

_Auto-generated by `tools/docs/generate_architecture.py` at {generated_at}. Do not hand-edit; regenerate instead._

## 1. What this system is

Full Potential OS is a self-evolving personal AI platform. One Chat per user carries memory, routing, CORA rewards, and capability extensions. It builds itself through an autonomous server loop on 162: laptop-free, with $0 marginal Codex/Claude review where available.

## 2. The 9 functions

{function_table}

## 3. Data flow diagram

```mermaid
flowchart TD
  B[Beacon\\nQR/ad/link] --> H[Hermes Gateway\\nchannel normalizer]
  H --> S[Spark\\n3-question intake]
  S --> E[Ember\\nmemory + routing]
  E --> R[Route\\nclarify / action / camp / proof]
  R --> P[Proof\\nuser acts]
  P --> L[Ledger\\ntrack outcome]
  L --> C[CORA\\nreward signal]
  L --> Loop[Learning Loop\\npreference pairs]
  Loop --> E
  Council[Council\\ndebate.py] --> D[Decision queue]
  D --> Forge[Forge\\nbuild loop]
  Forge --> E
```

## 4. Build loop

1. Council debates intents -> proposes build -> decision agent answers -> queued with `needs_build=true`.
2. Build loop on server 162 picks up the next decision and builds with Codex at $0 marginal cost.
3. `claude -p` reviews the diff with high effort and returns `APPROVE` or `REQUEST_CHANGES`.
4. `APPROVE` merges to `feat/headless-build` after the merge gate passes.
5. Post-merge health checks can fail closed and surface a reverse instruction.
6. Telegram notification reports the verdict and the reversal command if anything looks off.

## 5. Infrastructure

{service_table}

## 6. Decision queue snapshot

{queue_table}

## 7. Key files

{md_table(("File", "Purpose"), [
    ("server_build_loop.sh", "autonomous build runner compatibility entrypoint"),
    ("tools/build_loop/build_orchestrator.sh", "autonomous build orchestrator"),
    ("tools/merge/process_merge_requests.sh", "James-approved merge processor"),
    ("tools/merge/ai_review.py", "independent code review with `claude -p`"),
    ("tools/council/debate.py", "architecture debate with `claude -p`"),
    ("tools/build_loop/ops_log.py", "ops truth ledger writes"),
    ("tools/cost/track.py", "metered cost tracker with daily cap"),
    ("SERVICES/sunheart-brain/curator/decisions.py", "decision queue CRUD + build triggers on server 162"),
    ("SERVICES/sunheart-brain/curator/telegram.py", "Telegram send/receive"),
    ("core/STATE/NOW.md", "founder priorities SSOT"),
    ("core/BUILD/REGISTRY.json", "what has been built"),
])}

## 8. What to ask GPT / how to share

Paste this file into GPT with: "This is the full architecture of my AI system. Help me visualize / improve / explain / extend it."

Or share the GitHub link to `docs/ARCHITECTURE.md` on `feat/headless-build`. GitHub, Obsidian, and GPT canvas can render the Mermaid block directly.

## 9. Gap log

{chr(10).join(gap_lines)}
"""


def log_generation(ops_ledger: Path, output: Path) -> None:
    row = {
        "ts": utc_now(),
        "loop": "architecture",
        "event": "architecture_generated",
        "detail": "docs/ARCHITECTURE.md regenerated",
        "cost": "$0",
        "artifact": str(output),
        "next": "share docs/ARCHITECTURE.md as the architecture SSOT",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
        "sections": 9,
    }
    ops_ledger.parent.mkdir(parents=True, exist_ok=True)
    with ops_ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def generate(
    *,
    output: Path = DEFAULT_OUTPUT,
    registry_path: Path = DEFAULT_REGISTRY,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    decisions: list[dict[str, str]] | None = None,
    services: list[dict[str, str]] | None = None,
    log: bool = True,
) -> dict[str, Any]:
    if os.environ.get("ARCHITECTURE_DISABLE") == "1":
        return {"disabled": True, "output": str(output), "sections": 0}
    registry = load_registry(registry_path)
    decision_rows = fetch_decision_queue() if decisions is None else decisions
    service_rows = service_snapshot() if services is None else services
    text = render_architecture(registry=registry, decisions=decision_rows, services=service_rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    if log:
        log_generation(ops_ledger, output)
    return {
        "disabled": False,
        "output": str(output),
        "sections": 9,
        "decisions": len(decision_rows),
        "services": len(service_rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate docs/ARCHITECTURE.md.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--no-log", action="store_true", help="Skip ops ledger append, used by tests.")
    args = parser.parse_args()
    result = generate(output=args.output, registry_path=args.registry, ops_ledger=args.ops_ledger, log=not args.no_log)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

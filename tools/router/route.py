#!/usr/bin/env python3
"""Rung 3 auto-routing: advance one AI-doable intent by one safe step.

Reads the weighted intent block from the vault Intent Buildstream, falls back to
the repo mirror, and chooses the highest-weighted ready intent. By default this
is report-only. Use --apply for guarded writes.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path


HOME = Path.home()
DEFAULT_REPO = Path(os.environ.get("FPAI_REPO", HOME / "FPAI_Cockpit"))
DEFAULT_VAULT = Path(
    os.environ.get(
        "FPAI_VAULT",
        HOME
        / "Library"
        / "Mobile Documents"
        / "iCloud~md~obsidian"
        / "Documents"
        / "FPOS"
        / "Full Potential OS",
    )
)

INTENTS_START = "<!-- INTENTS:START -->"
INTENTS_END = "<!-- INTENTS:END -->"
GATE_WORDS = (
    "move money",
    "money movement",
    "transfer",
    "treasury",
    "public",
    "publish",
    "outreach",
    "send ",
    "deploy",
    "production",
    "secret",
    "credential",
    "delete",
    "remove service",
    "stop service",
    "irreversible",
    "people",
    "hire",
    "partner",
    "offer",
    "doctrine",
)
SPEC_BLESS_PATTERNS = (
    r"\bstatus\s*:\s*blessed\b",
    r"\bblessed\s*:\s*yes\b",
    r"\bapproved\s*:\s*yes\b",
    r"\bjames\s+bless(?:ed)?\b",
    r"\bexplicitly\s+blessed\b",
)


@dataclasses.dataclass
class Intent:
    ident: str
    value: int
    unlocks: str
    status: str
    title: str
    route: str = ""
    link: str = ""
    weight: int = 0
    gated: bool = False
    gate_reason: str = ""


@dataclasses.dataclass
class RouteResult:
    intent: Intent | None
    action: str
    target: Path | None
    detail: str
    wrote: list[str]
    skipped: list[str]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def intent_sources(repo: Path, vault: Path) -> list[Path]:
    return [
        vault / "00_MEMORY" / "INTENT BUILDSTREAM.md",
        repo / "docs" / "codex" / "INTENT_BUILDSTREAM.md",
    ]


def load_intent_text(repo: Path, vault: Path, override: Path | None) -> tuple[str, Path]:
    candidates = [override] if override else intent_sources(repo, vault)
    for path in candidates:
        if path and path.exists():
            text = read_text(path)
            if INTENTS_START in text and INTENTS_END in text:
                return text, path
    searched = ", ".join(str(p) for p in candidates if p)
    raise FileNotFoundError(f"no intent block found; searched: {searched}")


def parse_intents(text: str) -> list[Intent]:
    match = re.search(
        re.escape(INTENTS_START) + r"(.*?)" + re.escape(INTENTS_END),
        text,
        flags=re.DOTALL,
    )
    if not match:
        return []

    intents: list[Intent] = []
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        parts = [p.strip() for p in line[2:].split("|")]
        fields: dict[str, str] = {}
        title_parts: list[str] = []
        for part in parts:
            if ":" in part:
                key, value = part.split(":", 1)
                key = key.strip().lower()
                if key in {"id", "value", "unlocks", "status", "route", "link"}:
                    fields[key] = value.strip()
                    continue
            title_parts.append(part)
        if not {"id", "value", "unlocks", "status"} <= set(fields):
            continue
        try:
            value_n = int(fields["value"])
        except ValueError:
            value_n = 1
        title = " | ".join(title_parts).strip()
        intent = Intent(
            ident=fields["id"],
            value=value_n,
            unlocks=fields["unlocks"],
            status=fields["status"].lower(),
            title=title,
            route=fields.get("route", "").lower(),
            link=fields.get("link", ""),
        )
        intent.gated, intent.gate_reason = gate_check(intent.title)
        intents.append(intent)
    return intents


def downstream_leverage(intent: Intent, by_id: dict[str, Intent]) -> int:
    seen: set[str] = set()
    cur = intent.unlocks
    while cur and cur != "none" and cur in by_id and cur not in seen:
        seen.add(cur)
        cur = by_id[cur].unlocks
    return len(seen)


def weigh_intents(intents: list[Intent]) -> list[Intent]:
    by_id = {i.ident: i for i in intents}
    for intent in intents:
        readiness = 1 if intent.status == "ready" else 0
        intent.weight = intent.value * (1 + downstream_leverage(intent, by_id)) * readiness
    return sorted(intents, key=lambda i: (i.weight, i.value, i.ident), reverse=True)


def gate_check(text: str) -> tuple[bool, str]:
    low = text.lower()
    for word in GATE_WORDS:
        if word in low:
            return True, f"contains gated word/phrase: {word.strip()}"
    return False, ""


def choose_intent(intents: list[Intent]) -> Intent | None:
    ready = [i for i in weigh_intents(intents) if i.status == "ready"]
    return ready[0] if ready else None


def slugify(text: str) -> str:
    low = text.lower()
    if "auto-routing" in low or "auto routing" in low:
        return "auto-routing"
    if "auto-closeout" in low or "auto closeout" in low:
        return "auto-closeout"
    text = re.sub(r"^rung\s+\d+(?:\.\d+)?\s*", "", text, flags=re.I)
    text = re.split(r"\s+[-—]\s+", text, maxsplit=1)[0]
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "intent"


def spec_path(repo: Path, slug: str) -> Path:
    return repo / "docs" / "codex" / "specs" / f"SPEC_{slug}.md"


def spec_is_blessed(path: Path) -> bool:
    if not path.exists():
        return False
    text = read_text(path).lower()
    for line in text.splitlines()[:20]:
        status = re.match(r"\s*status\s*:\s*(.+?)\s*$", line)
        if status:
            value = status.group(1).strip().lower()
            if value in {"blessed", "approved", "james-blessed", "james blessed"}:
                return True
            if value in {"needs-bless", "needs bless", "unblessed", "draft"}:
                return False
    return any(re.search(pattern, text, flags=re.I) for pattern in SPEC_BLESS_PATTERNS)


def build_spec_draft(intent: Intent, slug: str) -> str:
    now = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    return f"""# SPEC_{slug}

status: needs-bless
generated: {now}
source_intent: {intent.ident}

## Intent

{intent.title}

## Downstream Intent Unlocked

`{intent.unlocks}` from `docs/codex/INTENT_BUILDSTREAM.md`.

## Branch

`feat/{slug}`

## Files Allowed

- TODO: Ember/James to narrow before build.

## Files Forbidden

- Money movement, outreach sends, production deploys, secrets, service stops, service moves, service deletes, and irreversible changes.

## Definition Of Done

- TODO: specify the exact build output.
- TODO: specify tests.
- TODO: specify rollback.

## James Gate

This auto-drafted spec is not buildable until James or Ember replaces TODOs and blesses it.
"""


def git_dirty(path: Path, repo: Path) -> bool:
    rel = str(path.relative_to(repo)) if path.is_relative_to(repo) else str(path)
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--", rel],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    return bool(proc.stdout.strip())


def run_cost_guard(skip: bool) -> str:
    guard = HOME / ".local" / "bin" / "cost-guard"
    if skip:
        return "skipped by --skip-cost-guard"
    if not guard.exists():
        return "not present; no model spend performed"
    proc = subprocess.run([str(guard), "router"], text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout.strip() or proc.stderr.strip() or "cost-guard blocked router")
    return proc.stdout.strip() or "passed"


def conscious_routing_fields(intent: Intent, action: str, detail: str) -> dict[str, str]:
    """Aware / Aligned / Care / Proof contract for router decisions."""
    route_lane = intent.route or "unset"
    aware = (
        f"Intent `{intent.ident}` is `{intent.status}` on route `{route_lane}`; "
        f"router action is `{action}`."
    )
    aligned = (
        f"Buildstream Law: `{intent.ident}` must unlock adjacent intent "
        f"`{intent.unlocks}` before more downstream work."
    )
    if action == "escalate":
        care = "Stops at the correct lane/gate instead of converting builder, James, money, people, public, or irreversible work into automation."
    elif action == "draft-spec":
        care = "Writes only a repo-local `needs-bless` spec draft; no build, spend, service, outreach, or resource movement occurs."
    elif action == "request-bless":
        care = "Surfaces the missing bless instead of pretending an unapproved spec is buildable."
    elif action == "route-build":
        care = "Routes a blessed spec to Codex while preserving branch isolation and the normal proof path."
    else:
        care = "Reports state without taking unsafe action."
    proof = f"Output/handoff records route, action, detail, and dedupe so the consequence can be checked next run: {detail}"
    return {
        "aware": re.sub(r"\s+", " ", aware).strip(),
        "aligned": re.sub(r"\s+", " ", aligned).strip(),
        "care": re.sub(r"\s+", " ", care).strip(),
        "proof": re.sub(r"\s+", " ", proof).strip(),
    }


def handoff_entry(intent: Intent, action: str, detail: str) -> str:
    stamp = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    route_lane = intent.route or "unset"
    dedupe = f"auto-routing:{intent.ident}:{route_lane}:{action}"
    cr = conscious_routing_fields(intent, action, detail)
    return f"""
### {stamp} · Auto-routing tick · intent `{intent.ident}`

- Status: routed
- Intent: {intent.title}
- Route: {route_lane}
- Action: {action}
- Detail: {detail}
- Aware: {cr['aware']}
- Aligned: {cr['aligned']}
- Care: {cr['care']}
- Proof: {cr['proof']}
- Cost: ~$0 marginal · GPT Pro flat-rate · source: Codex desktop.
- Risks: router is one-step guarded; James-gated or unblessed work is not executed.
- Rollback: remove this handoff note and any auto-drafted spec from `docs/codex/specs/`.
- Questions for Ember/James: bless or refine the next surfaced spec/action.
- Dedupe: {dedupe}
"""


def append_handoff(repo: Path, entry: str, dry_run: bool) -> str:
    handoff = repo / "docs" / "codex" / "HANDOFF.md"
    if not handoff.exists():
        return f"skip missing {handoff}"
    if git_dirty(handoff, repo):
        return f"skip dirty {handoff}"
    if dry_run:
        return f"would append to {handoff}"
    text = read_text(handoff)
    dedupe = re.search(r"^- Dedupe:\s*(.+)$", entry, flags=re.MULTILINE)
    if dedupe and dedupe.group(1).strip() in text:
        return f"skip duplicate {dedupe.group(1).strip()}"
    marker = "## 📥 CODEX → EMBER"
    if marker not in text:
        handoff.write_text(text.rstrip() + "\n" + entry + "\n", encoding="utf-8")
        return f"appended to {handoff}"
    pos = text.find(marker)
    next_section = text.find("\n## ", pos + len(marker))
    insert_at = next_section if next_section != -1 else len(text)
    new = text[:insert_at].rstrip() + "\n" + entry + "\n\n" + text[insert_at:].lstrip()
    handoff.write_text(new, encoding="utf-8")
    return f"appended to {handoff}"


def route_once(
    repo: Path,
    vault: Path,
    intent_file: Path | None,
    dry_run: bool,
    append: bool,
    skip_cost_guard: bool,
) -> RouteResult:
    text, source = load_intent_text(repo, vault, intent_file)
    intents = parse_intents(text)
    chosen = choose_intent(intents)
    wrote: list[str] = []
    skipped = [f"intent source: {source}"]
    if not chosen:
        return RouteResult(None, "none", None, "no ready intents found", wrote, skipped)

    if chosen.gated:
        detail = f"James/Ember gate required because {chosen.gate_reason}"
        action = "escalate"
        if append:
            wrote.append(append_handoff(repo, handoff_entry(chosen, action, detail), dry_run))
        return RouteResult(chosen, action, None, detail, wrote, skipped)

    route_lane = chosen.route or "unset"
    if route_lane != "auto":
        action = "escalate"
        if route_lane == "james":
            detail = f"James gate required because intent route is `{route_lane}`"
        elif route_lane in {"ember", "codex", "api"}:
            detail = f"intent `{chosen.ident}` is ready, routed to `{route_lane}`; needs that builder"
        else:
            detail = f"intent `{chosen.ident}` is ready but route is `{route_lane}`; add `route:auto` to allow unattended action"
        if append:
            wrote.append(append_handoff(repo, handoff_entry(chosen, action, detail), dry_run))
        return RouteResult(chosen, action, None, detail, wrote, skipped)

    slug = slugify(chosen.title)
    path = spec_path(repo, slug)
    if not path.exists():
        action = "draft-spec"
        detail = f"draft {path.relative_to(repo)} as needs-bless"
        if dry_run:
            wrote.append(f"would write {path}")
        else:
            skipped.append(f"cost guard: {run_cost_guard(skip_cost_guard)}")
            path.write_text(build_spec_draft(chosen, slug), encoding="utf-8")
            wrote.append(f"wrote {path}")
        if append:
            wrote.append(append_handoff(repo, handoff_entry(chosen, action, detail), dry_run))
        return RouteResult(chosen, action, path, detail, wrote, skipped)

    if not spec_is_blessed(path):
        action = "request-bless"
        detail = f"spec exists but is not blessed: {path.relative_to(repo)}"
        if append:
            wrote.append(append_handoff(repo, handoff_entry(chosen, action, detail), dry_run))
        return RouteResult(chosen, action, path, detail, wrote, skipped)

    action = "route-build"
    detail = f"spec is blessed; Codex should build on the branch named in {path.relative_to(repo)}"
    if append:
        wrote.append(append_handoff(repo, handoff_entry(chosen, action, detail), dry_run))
    return RouteResult(chosen, action, path, detail, wrote, skipped)


def print_result(result: RouteResult) -> None:
    print("Auto-routing tick")
    print("---")
    if not result.intent:
        print(f"action: {result.action}")
        print(f"detail: {result.detail}")
        return
    print(f"intent: {result.intent.ident}")
    print(f"title: {result.intent.title}")
    print(f"weight: {result.intent.weight}")
    print(f"status: {result.intent.status}")
    if result.intent.route:
        print(f"route: {result.intent.route}")
    if result.intent.link:
        print(f"link: {result.intent.link}")
    print(f"unlocks: {result.intent.unlocks}")
    print(f"action: {result.action}")
    if result.target:
        print(f"target: {result.target}")
    print(f"detail: {result.detail}")
    cr = conscious_routing_fields(result.intent, result.action, result.detail)
    print(f"aware: {cr['aware']}")
    print(f"aligned: {cr['aligned']}")
    print(f"care: {cr['care']}")
    print(f"proof: {cr['proof']}")
    for item in result.skipped:
        print(f"note: {item}")
    for item in result.wrote:
        print(f"write: {item}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Advance one ready buildstream intent by one guarded step.")
    ap.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    ap.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    ap.add_argument("--intent-file", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true", help="report only; writes nothing")
    ap.add_argument("--apply", action="store_true", help="perform the one safe write step")
    ap.add_argument("--append-handoff", action="store_true", help="append a CODEX -> EMBER handoff note")
    ap.add_argument("--skip-cost-guard", action="store_true", help="test-only: do not call ~/.local/bin/cost-guard")
    args = ap.parse_args(argv)

    dry_run = True
    if args.apply:
        dry_run = False
    if args.dry_run:
        dry_run = True

    try:
        result = route_once(
            repo=args.repo,
            vault=args.vault,
            intent_file=args.intent_file,
            dry_run=dry_run,
            append=args.append_handoff,
            skip_cost_guard=args.skip_cost_guard,
        )
    except Exception as exc:
        print(f"router error: {exc}", file=sys.stderr)
        return 1
    print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

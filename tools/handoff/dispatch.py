#!/usr/bin/env python3
"""Dispatch — fan out concurrent, collision-free builds across N Codex sessions.

Reads the weighted Intent Buildstream, takes the top-N READY `route:codex` intents
that have a spec, checks their specs touch DISJOINT files (no collision), claims each
surface (🔴 in the Index), and prints one paste-ready kickoff per session.

You then paste each block into a separate Codex session (desktop tab / phone / cloud) —
each on its own branch, disjoint files, claimed surface. Maximum parallel build, zero collision.

Usage:
    python3 tools/handoff/dispatch.py [--n 3] [--route codex] [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
VAULT = Path(os.environ.get(
    "FPAI_VAULT",
    HOME / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "FPOS" / "Full Potential OS",
))
REPO = Path(os.environ.get("FPAI_REPO", HOME / "FPAI_Cockpit"))
SPECS = REPO / "docs" / "codex" / "specs"
HERE = Path(__file__).resolve().parent


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def ready_intents(route: str) -> list[dict]:
    """Top weighted READY intents for a route, from the Intent Buildstream INTENTS block."""
    txt = read(VAULT / "00_MEMORY" / "INTENT BUILDSTREAM.md") or read(REPO / "docs" / "codex" / "INTENT_BUILDSTREAM.md")
    m = re.search(r"<!-- INTENTS:START -->(.*?)<!-- INTENTS:END -->", txt, re.S)
    if not m:
        return []
    known = {"id", "value", "unlocks", "status", "route", "link"}
    rows = []
    for ln in m.group(1).splitlines():
        ln = ln.strip()
        if not ln.startswith("- "):
            continue
        d, desc = {}, ""
        for tok in ln[2:].split(" | "):
            km = re.match(r"(\w+):(.*)$", tok)
            if km and km.group(1) in known:
                d[km.group(1)] = km.group(2).strip()
            else:
                desc = tok
        if d.get("id") and d.get("status") == "ready" and d.get("route") == route:
            d["desc"] = desc
            d["value"] = int(d.get("value", "0") or 0)
            rows.append(d)
    rows.sort(key=lambda r: r["value"], reverse=True)
    return rows


def find_spec(intent_id: str) -> Path | None:
    """Best-effort: match a spec file to an intent id (e.g. routefilter → SPEC_router-route-filtering)."""
    if not SPECS.exists():
        return None
    cands = list(SPECS.glob("SPEC_*.md"))
    key = intent_id.replace("-", "").replace("_", "").lower()
    for p in cands:
        if key in p.stem.replace("-", "").replace("_", "").lower():
            return p
    return None


def files_allowed(spec: Path) -> set[str]:
    """Parse the spec's 'Files allowed' section → set of paths (for disjointness check)."""
    txt = read(spec)
    m = re.search(r"Files allowed(.*?)(?:Files forbidden|##|\Z)", txt, re.S | re.I)
    seg = m.group(1) if m else txt
    return set(re.findall(r"`([^`]+\.\w+|[^`]+/)`", seg))


def kickoff_text(spec_name: str) -> str:
    return (
        f"Read `AGENTS.md`, then `docs/codex/README.md`, `docs/codex/AI_PROTOCOLS.md`, "
        f"`docs/codex/PHONE_HANDOFF.md`, `docs/codex/HANDOFF.md`, `docs/codex/INTENT_BUILDSTREAM.md`, "
        f"then the target spec `docs/codex/specs/{spec_name}`.\n"
        f"Work ONLY on the branch named in that spec; touch only files-allowed, never files-forbidden.\n"
        f"Build to the Definition of Done, run the tests, then update the 📥 lane in "
        f"`docs/codex/HANDOFF.md` with: files changed · summary · tests · risks · rollback. "
        f"Do NOT merge or move money/deploy/secrets — show me the diff first."
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fan out collision-free concurrent Codex builds.")
    ap.add_argument("--n", type=int, default=3, help="max concurrent sessions")
    ap.add_argument("--route", default="codex", help="route to dispatch (codex)")
    ap.add_argument("--dry-run", action="store_true", help="plan only; don't claim")
    ap.add_argument("--refresh", action="store_true", help="just regenerate CODEX QUEUE from current ready specs (no claim) — for the auto-loop")
    args = ap.parse_args(argv)

    intents = ready_intents(args.route)
    if not intents:
        print(f"No ready route:{args.route} intents in the buildstream.")
        return 0

    selected, used_files = [], set()
    for it in intents:
        spec = find_spec(it["id"])
        if not spec:
            print(f"  ⏭  {it['id']}: ready but no spec yet → draft a spec first (Sonnet→Opus).")
            continue
        fa = files_allowed(spec)
        overlap = fa & used_files
        if overlap:
            print(f"  ⛔ {it['id']}: would COLLIDE on {sorted(overlap)} — held for a later wave.")
            continue
        used_files |= fa
        selected.append((it, spec))
        if len(selected) >= args.n:
            break

    if not selected:
        print("Nothing dispatchable right now (no specced, non-colliding ready intents).")
        if args.refresh:   # keep the queue honest even when empty (nothing left to build)
            (VAULT / "00_MEMORY" / "CODEX QUEUE.md").write_text(
                "# CODEX QUEUE\n\n*Auto-refreshed by `tools/handoff/dispatch.py --refresh`.*\n\n"
                "✅ **Nothing queued** — no ready `route:codex` spec to build right now. "
                "Drop an intent (Ember specs it → it appears here).\n", encoding="utf-8")
            print("📋 CODEX QUEUE cleared (nothing ready to build).")
        return 0

    print(f"\n=== DISPATCH PLAN · {len(selected)} concurrent session(s) · route:{args.route} ===\n")
    q = [
        "# CODEX QUEUE",
        "",
        "*Paste-ready kickoffs — open a Codex session per block (phone/cloud/desktop) and paste it. "
        "Disjoint files · own branches · no collision. Regenerated by `tools/handoff/dispatch.py`.*",
        "",
        "## ⚙️ Optimize Codex per build",
        "",
        "**Each session below gives the exact Codex settings.** Set them before pasting:",
        "- **Project:** `FPAI_Cockpit`.",
        "- **Start in:** **New worktree** — gives each session an *isolated copy* of the repo, so concurrent builds can't collide (better than sharing one local tree). Use `Cloud` only from phone with no Mac.",
        "- **Branch:** each session names its own (`feat/<slug>`) — one spec = one branch.",
        "- **Environment:** **No environment** — our specs are stdlib-Python file-tools (no deps/services/secrets). Only pick a local environment if a build needs installed packages, env vars, or a running service.",
        "- **Model · reasoning:** GPT-5.5 at the level noted (Low/Medium/High/Very-high). Higher = better logic, slower; flat GPT-Pro ≈ $0 either way, so bias *up* when correctness matters.",
        "  - Low=trivial · Medium=standard tools · High=routing/orchestration/risky · Very-high=novel/correctness-critical.",
        "- **Approval:** **manual (review the diff)** for High/risky builds · **Approve-for-me** OK for Medium/trivial.",
        "- **Usage left:** check `Start in → Usage remaining` for your Codex quota.",
        "",
    ]
    HIGH = ("router", "auto-routing", "orchestrat", "headless", "escalat", "architect", "refactor", "migrat", "route-filter")
    for i, (it, spec) in enumerate(selected, 1):
        if not args.dry_run and not args.refresh:   # --refresh = read-only queue regen (no claim)
            subprocess.run([sys.executable, str(HERE.parent / "index" / "claim.py"),
                            "--page", it["link"], "--owner", f"Codex-{i}", "--no-refresh"],
                           capture_output=True, text=True)
        blob = (it["desc"] + " " + spec.stem).lower()
        reasoning = "High" if any(w in blob for w in HIGH) else "Medium"
        approval = "manual (review the diff)" if reasoning == "High" else "Approve-for-me OK"
        branch = "feat/" + spec.stem.replace("SPEC_", "")
        block = kickoff_text(spec.name)
        settings = (
            f"**⚙️ Codex settings:** Project `FPAI_Cockpit` · Start in **New worktree** · Environment **No environment** · "
            f"Branch **{branch}** (create from main) · Model **GPT-5.5 · {reasoning}** · Approval **{approval}**"
        )
        print(f"───── SESSION {i} [{reasoning}]: {it['desc'][:55]} ─────")
        print(block)
        print()
        q += [f"## ▶️ Session {i} — {it['desc'][:70]}", "", settings, "", "```", block, "```", ""]
    if not args.dry_run:
        queue = VAULT / "00_MEMORY" / "CODEX QUEUE.md"
        try:
            queue.write_text("\n".join(q), encoding="utf-8")
            print(f"\n📋 written → {queue}  (open [[CODEX QUEUE]] in Obsidian to copy each block)")
        except OSError as e:
            print(f"(could not write CODEX QUEUE: {e})")
        if not args.refresh:
            subprocess.run([sys.executable, str(HERE.parent / "index" / "refresh.py")], capture_output=True, text=True)
            print("(surfaces claimed 🔴 + index refreshed — clear each with `claim.py --clear` when done)")
    print("\nPaste each SESSION block into a separate Codex session. Disjoint files · own branches · no collision.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

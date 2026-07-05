#!/usr/bin/env python3
"""repo == running — the code analog of metric_coherence (map vs territory).

d138 named the hole: the live Telegram bot's curator (`/opt/sh-brain-src/curator`)
and its repo source (`SERVICES/sunheart-brain/curator`) forked in BOTH directions.
Anyone reading the repo assumes that's what runs — it isn't — and every build-loop
fix to a forked file merges "done" but silently never reaches live (2026-07-04:
awareness render-fix d180 merged, live stayed broken, because they're different files).

This guard makes the fork VISIBLE on every self-audit instead of being rediscovered
by hand. It does NOT deploy or mutate anything — it reads both trees and reports which
files diverged, classified by risk:
  - SAFE-SUPERSET : live has zero unique lines → repo ⊇ live → additive deploy, no clobber.
  - TWO-SIDED     : both trees have unique lines → needs a real per-file merge.
  - LANDMINE      : heavy two-sided divergence (both sides large) → do NOT blind-deploy.

Precedence: this is a STATE-coherence check (like metric_coherence), one tier under
the Constitution. It surfaces drift; it never auto-reconciles (prod blast radius).
"""
from __future__ import annotations

import difflib
import os
from pathlib import Path

REPO_CURATOR = Path(os.environ.get(
    "FPAI_REPO", "/opt/fpai-build/FPAI_Cockpit")) / "SERVICES/sunheart-brain/curator"
LIVE_CURATOR = Path(os.environ.get("FPAI_LIVE_CURATOR", "/opt/sh-brain-src/curator"))

# Heavy-divergence threshold: if BOTH sides have more unique lines than this, the
# files are effectively different programs (d138's decisions.py: live+503/repo+299).
LANDMINE_BOTH = 100


def _line_delta(live: Path, repo: Path) -> tuple[int, int]:
    """(live-only lines, repo-only lines) — the two-directional fork size."""
    a = live.read_text(errors="replace").splitlines()
    b = repo.read_text(errors="replace").splitlines()
    live_only = repo_only = 0
    for line in difflib.ndiff(a, b):
        if line.startswith("- "):
            live_only += 1
        elif line.startswith("+ "):
            repo_only += 1
    return live_only, repo_only


def _classify(live_only: int, repo_only: int) -> str:
    if live_only == 0 and repo_only == 0:
        return "IDENTICAL"
    if live_only == 0:
        return "SAFE-SUPERSET"  # repo ⊇ live → additive deploy, no clobber
    if live_only > LANDMINE_BOTH and repo_only > LANDMINE_BOTH:
        return "LANDMINE"  # two different programs — never blind-deploy
    return "TWO-SIDED"  # real per-file merge needed


def check() -> list[str]:
    """Return a list of drift strings (empty = repo matches running). self_audit-compatible."""
    if not LIVE_CURATOR.exists():
        return []  # not on the live host (e.g. laptop) — nothing to compare, not a drift
    if not REPO_CURATOR.exists():
        return [f"repo curator missing at {REPO_CURATOR} — cannot compare to live"]

    drift: list[str] = []
    for repo_file in sorted(REPO_CURATOR.glob("*.py")):
        if repo_file.name.startswith("test_") or repo_file.name == "__init__.py":
            continue
        live_file = LIVE_CURATOR / repo_file.name
        if not live_file.exists():
            drift.append(f"{repo_file.name}: in repo, NOT running live (never deployed)")
            continue
        live_only, repo_only = _line_delta(live_file, repo_file)
        if live_only == 0 and repo_only == 0:
            continue
        verdict = _classify(live_only, repo_only)
        drift.append(f"{repo_file.name}: {verdict} (live+{live_only} / repo+{repo_only})")
    return drift


def main() -> int:
    drift = check()
    if not drift:
        print("repo == running: OK — live curator matches repo (or not on the live host).")
        return 0
    print("=== REPO ≠ RUNNING (d138 fork · map vs territory) ===")
    for d in drift:
        print(f"  DRIFT · {d}")
    print("\nSAFE-SUPERSET = additive deploy safe · TWO-SIDED = per-file merge · "
          "LANDMINE = do NOT blind-deploy. Reconcile via tools/deploy/deploy_curator_slice.sh "
          "(gated) — never a blind fork-merge on the live product.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

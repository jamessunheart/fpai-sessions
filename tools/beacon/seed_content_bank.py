#!/usr/bin/env python3
"""Generate review-only Content Bank truth assets for Beacon.

The live path uses `claude -p` on a flat-rate local plan when available. Tests
and sandbox runs can inject a generator or fall back to deterministic drafts.
Existing files are skipped so James-edited content is never replaced.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIR = Path("docs/content_bank")
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DRAFT_TAG = "[DRAFT — review before publishing]"
READY_MESSAGE = "Content bank scaffold ready. 7 truth assets in docs/content_bank/ — review before Beacon uses."


@dataclass(frozen=True)
class AssetSpec:
    filename: str
    title: str
    angle: str
    format_rule: str
    sources: tuple[str, ...]
    fallback_body: str


ASSETS: tuple[AssetSpec, ...] = (
    AssetSpec(
        "01_what_is_sunheart_ai.md",
        "What Is Sunheart AI?",
        "Not another AI tool. A routing layer that turns attention into action.",
        "3 short paragraphs. End with: Scan. Speak. Get routed.",
        ("core/STATE/identity/VOICE.md", "core/STATE/NOW.md", "CLAUDE.md"),
        """# What Is Sunheart AI?

Sunheart AI is not another AI tool. It is a routing layer for the Full Potential OS: a system that notices where attention is going, turns that signal into the next action, and keeps the work moving without the human carrying the whole map.

The core pattern is simple. You scan what is real, speak the clearest signal, and the system routes it: memory, decision, proof, offer, build, person, or next step. AI holds context. Humans stay upstream where their attention actually changes the outcome.

Full Potential OS remembers state, routes intent, refreshes surfaces, and learns from proof. The point is not more answers. The point is cleaner action.

Scan. Speak. Get routed.""",
    ),
    AssetSpec(
        "02_cora_explainer.md",
        "CORA Explainer",
        "Attention has always been traded. Now you get credit for yours.",
        "Legal containment header, then explain what CORA is, how to earn it, and what it unlocks.",
        ("docs/policy/CORA_POLICY_v0.2.md", "core/STATE/NOW.md"),
        """# CORA Explainer

Legal containment: CORA is a closed-loop attention credit, not a currency. It is not cash, not an investment, not a token, not transferable, not redeemable for money, and not designed for secondary markets.

Attention has always been traded. CORA gives credit for attention that becomes real participation: a meaningful chat, a completed reflection, a verified proof, a useful contribution, an onboarding step, or a community action that moves the system forward.

You earn CORA by doing something that leaves a trace of value. CORA unlocks access inside the same system: deeper AI guidance, priority routing, Camp Zen calls or slots when capacity exists, Fi-Art minting slots, service marketplace access, content access, and community recognition.

Open review: amounts, caps, redemption prices, legal/compliance language, capacity planning, abuse handling, and decay notices must be approved before launch.""",
    ),
    AssetSpec(
        "03_fiat_explainer.md",
        "Fi-Art Explainer",
        "A new kind of financial art. Backed by the value you create, not the market.",
        "2 paragraphs plus one visual description for a system map or diagram.",
        ("core/STATE/NOW.md", "docs/deployment/fullpotential_com_SYSTEM_ARCHITECTURE.md"),
        """# Fi-Art Explainer

Fi-Art means financial art: a note of real-world value created from contribution, proof, and trust instead of market speculation. The point is not to mint a tradeable asset and hope the market believes. The point is to make visible the value someone has already created.

In the Full Potential OS, Fi-Art sits downstream of proof. A person contributes, the system records the proof, CORA can acknowledge attention or participation, and Fi-Art can become a visual or documentary artifact of the value created. Backed by the value you create, not the market.

Visual description: a simple system map with five nodes in a loop: Attention -> Contribution -> Proof -> Fi-Art note -> Access. CORA sits beside the loop as a closed-loop credit rail.""",
    ),
    AssetSpec(
        "04_camp_zen_explainer.md",
        "Camp Zen Explainer",
        "Come scattered. Leave routed. Every immersion produces a proof.",
        "Short description, what you walk away with, and how to apply.",
        ("core/STATE/NOW.md", "core/STATE/JAMES_CANONICAL.md"),
        """# Camp Zen Explainer

Camp Zen is the embodied proof lab for Full Potential OS. Come scattered. Leave routed. The immersion is not an escape from work; it is a reset into clearer attention, cleaner tools, and one proof you can carry back into real life.

What you walk away with: a personal routing map, a working AI-supported operating loop, one concrete proof, and a calmer relationship with AI, attention, and execution.

How to apply: enter through a Beacon link when campaigns are live, or through a chat qualification flow. The first step is a routing conversation to see whether Camp Zen is the right container now.""",
    ),
    AssetSpec(
        "05_founder_pain_piece.md",
        "You Do Not Need More AI Tools. You Need Routing.",
        "Founders, operators, and builders overwhelmed by AI need routing, not more tools.",
        "About 200 words. Problem -> root cause -> one insight -> one door.",
        ("core/STATE/JAMES_CANONICAL.md", "core/STATE/NOW.md"),
        """# You Do Not Need More AI Tools. You Need Routing.

Founders are drowning in AI because every tool creates another possible path.

One tool writes. One tool researches. One tool builds. One tool automates. One tool tracks. Suddenly the founder is the router for twenty systems that all promise leverage but still ask the same question: what should happen next?

That is the real bottleneck. Not intelligence. Not output. Routing.

When routing is missing, AI becomes another inbox. More drafts. More dashboards. More half-started systems. More tabs. The founder carries the map, the priority, the context, the risk, the next step, and the memory of what already happened.

Full Potential OS starts from a different premise: attention moves first. The system should notice the signal, place it in context, choose the next action, stop at real human gates, and learn from proof.

The door is simple: scan what is real, speak the signal, get routed.""",
    ),
    AssetSpec(
        "06_what_is_live_proof.md",
        "What Is Live Proof?",
        "Here is what is already live, partial, and planned.",
        "Three-column table: Live | Building | Planned. Include honest gap log.",
        ("core/STATE/NOW.md", "docs/deployment/fullpotential_com_SYSTEM_ARCHITECTURE.md"),
        """# What Is Live Proof?

Live proof means the system says what is real now: what already runs, what is being built, and what is only planned.

| Live | Building | Planned |
|---|---|---|
| Full Potential Game surface | Content Bank v0.1 | Paid Beacon scaling after organic proof |
| Sunheart Brain Telegram bot | Beacon content remixes | CORA launch after policy approval |
| Builder lane and review loop | CORA capacity planning | Fi-Art flow after containment |

## Honest Gap Log

- CORA is still review-only until James/compliance approve policy details.
- Paid campaigns wait for organic chat-start proof.
- Fi-Art needs reviewed containment and proof wiring.
- Camp Zen offer terms still need approval.""",
    ),
    AssetSpec(
        "07_offer_post.md",
        "Three Doors Into Full Potential OS",
        "Founder Install / Camp Zen / CORA Onboarding.",
        "One page, one offer per section: what you get, what it costs, how to start.",
        ("core/STATE/NOW.md", "docs/policy/CORA_POLICY_v0.2.md"),
        """# Three Doors Into Full Potential OS

## Founder Install

What you get: a focused install of Full Potential OS around your current founder bottleneck. What it costs: price pending James review. How to start: Beacon link pending after d037 campaigns are created.

## Camp Zen

What you get: an embodied reset and proof lab. What it costs: price, dates, format, and capacity pending James review. How to start: Beacon link pending after d037 campaigns are created.

## CORA Onboarding

What you get: a first path into the CORA attention-credit loop. What it costs: no public pricing claim yet. How to start: Beacon link pending after d037 campaigns are created.""",
    ),
)


def read_source_bundle(repo_root: Path, paths: Iterable[str]) -> str:
    parts: list[str] = []
    for rel in paths:
        path = repo_root / rel
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = "[missing]"
        parts.append(f"## Source: {rel}\n{text[:12_000]}")
    return "\n\n".join(parts)


def build_prompt(asset: AssetSpec, source_bundle: str) -> str:
    return f"""You are drafting a review-only Content Bank truth asset for Beacon.

Mark the output as draft only. Use James's caveman clarity: short, concrete,
honest, no hype. Do not make legal, investment, pricing, launch, or paid-spend
claims beyond the provided source state.

Asset: {asset.filename}
Title: {asset.title}
Angle: {asset.angle}
Format: {asset.format_rule}

Sources:
{source_bundle}
"""


def ensure_draft_tag(text: str) -> str:
    cleaned = text.strip()
    if DRAFT_TAG in cleaned:
        return cleaned + "\n"
    return f"{DRAFT_TAG}\n\n{cleaned}\n"


def call_claude(prompt: str, *, timeout: int = 180) -> str:
    claude = shutil.which("claude")
    if not claude:
        raise FileNotFoundError("claude CLI not found")
    result = subprocess.run(
        [claude, "-p", prompt],
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(result.stderr.strip() or "claude returned no draft")
    return result.stdout


def should_skip_existing(path: Path) -> bool:
    return path.exists()


def generate_asset(
    asset: AssetSpec,
    repo_root: Path,
    generator: Callable[[AssetSpec, str], str] | None = None,
) -> str:
    source_bundle = read_source_bundle(repo_root, asset.sources)
    if generator:
        body = generator(asset, source_bundle)
    else:
        try:
            body = call_claude(build_prompt(asset, source_bundle))
        except Exception:
            body = asset.fallback_body
    return ensure_draft_tag(body)


def log_completion(ops_ledger: Path, *, written: int, skipped: int) -> None:
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "content_bank_generated",
        "assets": len(ASSETS),
        "written": written,
        "skipped": skipped,
    }
    try:
        ops_ledger.parent.mkdir(parents=True, exist_ok=True)
        with ops_ledger.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    except OSError:
        return


def notify_ready(repo_root: Path) -> None:
    script = repo_root / "tools" / "build_loop" / "notify_telegram.sh"
    if not script.exists():
        return
    try:
        subprocess.run([str(script), READY_MESSAGE], cwd=repo_root, check=False, timeout=20)
    except Exception:
        return


def seed_content_bank(
    *,
    repo_root: Path = REPO_ROOT,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    generator: Callable[[AssetSpec, str], str] | None = None,
    notify: bool = True,
) -> dict[str, object]:
    if os.environ.get("CONTENT_BANK_DISABLE") == "1":
        return {"disabled": True, "written": [], "skipped": []}

    content_dir = repo_root / CONTENT_DIR
    planned: dict[Path, str] = {}
    skipped: list[str] = []

    for asset in ASSETS:
        target = content_dir / asset.filename
        if should_skip_existing(target):
            skipped.append(asset.filename)
            continue
        planned[target] = generate_asset(asset, repo_root, generator)

    content_dir.mkdir(parents=True, exist_ok=True)
    for target, text in planned.items():
        target.write_text(text, encoding="utf-8")

    log_completion(ops_ledger, written=len(planned), skipped=len(skipped))
    if notify:
        notify_ready(repo_root)
    return {"disabled": False, "written": [p.name for p in planned], "skipped": skipped}


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed docs/content_bank truth assets.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--no-notify", action="store_true")
    args = parser.parse_args()
    result = seed_content_bank(repo_root=args.repo_root, ops_ledger=args.ops_ledger, notify=not args.no_notify)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

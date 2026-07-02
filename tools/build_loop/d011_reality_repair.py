#!/usr/bin/env python3
"""Repair proof rows for the d011 intent-injector merged-dead audit.

The original d011 build was an idempotent verification of the already-shipped
correction capture and build-context prompt injection pipeline. It predated the
post-merge reality checker's strict proof contract. This helper proves the
artifact with bounded temporary fixtures, then appends the two canonical rows
the checker requires:

- liveness:pass
- feature_outcome with verdict=improved
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

from tools.build_loop import feature_outcome
from tools.liveness import probe


ORIGINAL_SPEC_ID = "SPEC_d011_intent-injector-correction-capt"
ORIGINAL_BRANCH = "build/SPEC_d011_intent-injector-correction-capt"


def run_intent_injector_smoke(repo_root: Path) -> tuple[bool, str, list[str]]:
    """Run a bounded d011 correction/context smoke and return ok/detail/evidence."""
    capture_path = repo_root / "tools" / "learn" / "capture_corrections.py"
    build_context_path = repo_root / "SERVICES" / "sunheart-brain" / "curator" / "build_context.py"
    corrections_path = repo_root / "SERVICES" / "sunheart-brain" / "curator" / "corrections.py"
    tgbot_path = repo_root / "SERVICES" / "sunheart-brain" / "curator" / "tgbot.py"
    missing = [
        str(path.relative_to(repo_root))
        for path in (capture_path, build_context_path, corrections_path, tgbot_path)
        if not path.exists()
    ]
    if missing:
        return False, "missing shipped artifacts: " + ", ".join(missing), []

    try:
        capture = _load_module("d011_capture_corrections", capture_path)
        build_context = _load_module("d011_build_context", build_context_path)
        corrections = _load_module("d011_corrections", corrections_path)
        with _temporary_env(
            FPAI_SUPABASE_URL="",
            FPAI_SUPABASE_KEY="",
            SUPABASE_ANON_KEY="",
            BLUEPRINTS_DISABLE="1",
            SH_BUILD_CONTEXT_DISABLE="",
        ):
            dataset = repo_root / ".tmp-d011-reality-proof.jsonl"
            try:
                row = capture.make_correction_pair(
                    prompt="James asks what is currently building",
                    rejected="The bot answers from stale session memory.",
                    preferred="The bot cites current build context and stores James's correction.",
                    source="d011-reality-smoke",
                    metadata={"spec_id": ORIGINAL_SPEC_ID},
                    captured_at="2026-07-02T00:00:00+00:00",
                )
                wrote_first = capture.append_pair(row, dataset)
                wrote_second = capture.append_pair(row, dataset)
                pair_rows = _read_jsonl(dataset)
            finally:
                dataset.unlink(missing_ok=True)
            if not wrote_first or wrote_second:
                return False, "correction pair append/dedupe behavior failed", []
            if len(pair_rows) != 1:
                return False, "correction dataset smoke did not write exactly one JSONL row", []
            written = pair_rows[0]
            if written.get("signal") != "james_correction":
                return False, "correction pair is missing james_correction signal", []
            if written.get("split") != "train" or written.get("never_train") is not False:
                return False, "correction pair is not shaped as a trainable d010 preference pair", []
            if not written.get("preferred", {}).get("text") or not written.get("rejected", {}).get("text"):
                return False, "correction pair lacks preferred/rejected text", []

            captured_pair = asyncio.run(_capture_pair_without_external_write(corrections))
            if captured_pair is None:
                return False, "correction signal did not capture against supplied bot turn", []
            rendered_corrections = corrections.render_corrections_block([captured_pair], max_chars=900)
            if "Recent corrections James made to this bot" not in rendered_corrections:
                return False, "recent correction block did not render failure memory", []
            if "James corrected" not in rendered_corrections:
                return False, "recent correction block omitted James correction text", []

            context = build_context.BuildContext(
                source="d011-reality-smoke",
                focus=["Repair merged-dead d011 with proof rows"],
                active_loops=["post-merge reality checker"],
                open_intents=["intent injector correction capture"],
                system_status=["Build queue: d011 repair scoped"],
                corrections=["- Bot said stale context; James corrected current build context"],
            )
            rendered_context = build_context.render_build_context(context, max_chars=1600)
            required_context = (
                "CURRENT BUILD CONTEXT",
                "Do not treat it as approval to write, spend, deploy",
                "Corrections:",
                "Repair merged-dead d011 with proof rows",
            )
            missing_context = [text for text in required_context if text not in rendered_context]
            if missing_context:
                return False, "rendered build context missing: " + ", ".join(missing_context), []

        tgbot_text = tgbot_path.read_text(encoding="utf-8", errors="replace")
        required_wiring = ("capture_if_correction", "build_context_system_suffix", 'include_corrections=blocks["corrections"]')
        missing_wiring = [text for text in required_wiring if text not in tgbot_text]
        if missing_wiring:
            return False, "tgbot wiring missing: " + ", ".join(missing_wiring), []
    except Exception as exc:
        return False, f"d011 reality smoke raised {type(exc).__name__}: {exc}", []

    evidence = [
        "capture_corrections.py created and append-deduped one d010-shaped james_correction pair",
        "corrections.py captured an explicit correction against a supplied bot turn without external writes",
        "render_corrections_block rendered recent correction failure memory",
        "build_context.py rendered bounded advisory current build context with correction context",
        "tgbot.py contains the defensive capture_if_correction and build_context_system_suffix wiring",
    ]
    detail = "d011 correction capture and intent-injector prompt context smoke passed"
    return True, detail, evidence


async def _capture_pair_without_external_write(corrections: Any) -> Any:
    writes: list[Any] = []

    async def fake_write(pair: Any) -> None:
        writes.append(pair)

    old_write = corrections.write_correction
    old_update = corrections._update_blueprint_gap
    corrections.write_correction = fake_write
    corrections._update_blueprint_gap = lambda *_args, **_kwargs: None
    try:
        pair = await corrections.capture_if_correction(
            conversation_id="d011-reality-smoke",
            james_message="Actually, you missed the current build context and correction memory.",
            bot_turn=corrections.BotTurn(id="bot-1", text="I only remember stale session context."),
        )
    finally:
        corrections.write_correction = old_write
        corrections._update_blueprint_gap = old_update
    if not writes or writes[0] != pair:
        return None
    return pair


def append_repair_proof(
    ops_ledger: Path,
    *,
    repo_root: Path,
    spec_id: str = ORIGINAL_SPEC_ID,
    branch: str = ORIGINAL_BRANCH,
) -> dict[str, Any]:
    ok, detail, evidence = run_intent_injector_smoke(repo_root)
    check = probe.LivenessCheck("command", "d011 correction capture/build-context smoke", "d011 intent injector smoke")
    result = probe.CheckResult(check, "live" if ok else "dead", detail)
    report = probe.ProbeReport("live" if ok else "dead", (result,), spec_id=spec_id, branch=branch)
    probe.append_ops_ledger(ops_ledger, report)
    if not ok:
        return {"ok": False, "liveness": report.to_json(), "feature_outcome": None}

    outcome = feature_outcome.append_feature_outcome(
        ops_ledger,
        spec_id=spec_id,
        metric_name="correction_capture_prompt_context_spine",
        baseline="merged_advisory_pipeline_without_post_merge_proof",
        observed="correction_pair_capture_and_prompt_context_smoke_passed",
        delta="explicit correction became a d010-shaped pair and current build/correction context rendered into the prompt boundary",
        verdict="improved",
        branch=branch,
        evidence=[report.detail(), *evidence],
    )
    return {"ok": True, "liveness": report.to_json(), "feature_outcome": outcome}


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _temporary_env:
    def __init__(self, **updates: str) -> None:
        self.updates = updates
        self.previous: dict[str, str | None] = {}

    def __enter__(self) -> None:
        for key, value in self.updates.items():
            self.previous[key] = os.environ.get(key)
            os.environ[key] = value

    def __exit__(self, *_exc: object) -> None:
        for key, old_value in self.previous.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(os.environ.get("FPAI_REPO_ROOT", Path(__file__).resolve().parents[2])))
    parser.add_argument("--ops-ledger", type=Path, default=feature_outcome.DEFAULT_OPS_LEDGER)
    parser.add_argument("--spec-id", default=ORIGINAL_SPEC_ID)
    parser.add_argument("--branch", default=ORIGINAL_BRANCH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = append_repair_proof(args.ops_ledger, repo_root=args.repo_root, spec_id=args.spec_id, branch=args.branch)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

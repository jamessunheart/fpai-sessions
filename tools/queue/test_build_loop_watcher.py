#!/usr/bin/env python3
"""Tests for the Rung 4 build-loop watcher."""
from __future__ import annotations

import datetime as dt
import inspect
import subprocess
from pathlib import Path

import tools.queue.build_loop_watcher as watcher


FIXED_NOW = dt.datetime(2026, 6, 12, 12, 0, tzinfo=dt.timezone.utc)


def _intent(path: Path, status: str = "open") -> Path:
    path.write_text(
        "---\n"
        "id: intent-20260612-abcdef\n"
        "slug: daily-digest\n"
        f"status: {status}\n"
        "source: telegram\n"
        "source_message_id: 123\n"
        "created: 2026-06-12T00:00:00Z\n"
        "raw: \"build: daily digest\"\n"
        "---\n\n"
        "# daily-digest\n\n"
        "daily digest\n",
        encoding="utf-8",
    )
    return path


def test_open_intent_drafts_builds_reviews_and_updates_status(tmp_path: Path):
    intents = tmp_path / "intents"
    specs = tmp_path / "specs"
    results = tmp_path / "results"
    reviews = tmp_path / "reviews"
    proof = tmp_path / "PROOF_LOG.md"
    intents.mkdir()
    _intent(intents / "intent-20260612-abcdef-daily-digest.md")
    sent: list[str] = []

    def fake_runner(spec_path: Path):
        assert spec_path == specs / "intent-20260612-abcdef-daily-digest.md"
        results.mkdir(parents=True, exist_ok=True)
        (results / "intent-20260612-abcdef.result.md").write_text(
            "# result\n\nTests OK\n", encoding="utf-8",
        )
        return subprocess.CompletedProcess([str(spec_path)], 0, "ok", "")

    outcomes = watcher.watch_once(
        intents,
        specs,
        reviews,
        results_dir=results,
        proof_log=proof,
        runner=fake_runner,
        sender=lambda msg: sent.append(msg) or (True, "sent"),
        now_fn=lambda: FIXED_NOW,
    )

    assert outcomes == ["review-pending:intent-20260612-abcdef"]
    assert (specs / "intent-20260612-abcdef-daily-digest.md").exists()
    review = reviews / "intent-20260612-abcdef-daily-digest.review.md"
    assert review.exists()
    assert "tests green" in review.read_text(encoding="utf-8")
    intent_text = (intents / "intent-20260612-abcdef-daily-digest.md").read_text(encoding="utf-8")
    assert "status: review-pending" in intent_text
    assert "review_path:" in intent_text
    assert "builder loop: daily-digest" in proof.read_text(encoding="utf-8")
    assert sent == ["Built `daily-digest` — tests green. Merge? ⚡ Reply 'merge intent-20260612-abcdef' or 'reject intent-20260612-abcdef'."]


def test_review_pending_intent_is_skipped(tmp_path: Path):
    intents = tmp_path / "intents"
    intents.mkdir()
    _intent(intents / "intent-20260612-abcdef-daily-digest.md", status="review-pending")

    outcomes = watcher.watch_once(
        intents,
        tmp_path / "specs",
        tmp_path / "reviews",
        results_dir=tmp_path / "results",
        proof_log=tmp_path / "PROOF_LOG.md",
        runner=lambda _: (_ for _ in ()).throw(AssertionError("should not run")),
        sender=lambda _: (_ for _ in ()).throw(AssertionError("should not send")),
    )

    assert outcomes == []
    assert not (tmp_path / "specs").exists()


def test_codex_failure_marks_build_failed_and_notifies(tmp_path: Path):
    intents = tmp_path / "intents"
    specs = tmp_path / "specs"
    results = tmp_path / "results"
    reviews = tmp_path / "reviews"
    intents.mkdir()
    _intent(intents / "intent-20260612-abcdef-daily-digest.md")
    sent: list[str] = []

    def failing_runner(spec_path: Path):
        return subprocess.CompletedProcess([str(spec_path)], 1, "boom", "trace")

    outcomes = watcher.watch_once(
        intents,
        specs,
        reviews,
        results_dir=results,
        proof_log=tmp_path / "PROOF_LOG.md",
        runner=failing_runner,
        sender=lambda msg: sent.append(msg) or (True, "sent"),
        now_fn=lambda: FIXED_NOW,
    )

    assert outcomes == ["build-failed:intent-20260612-abcdef"]
    intent_text = (intents / "intent-20260612-abcdef-daily-digest.md").read_text(encoding="utf-8")
    assert "status: build-failed" in intent_text
    assert (reviews / "intent-20260612-abcdef-daily-digest.review.md").exists()
    assert "tests failed" in (reviews / "intent-20260612-abcdef-daily-digest.review.md").read_text(encoding="utf-8")
    assert sent == ["Built `daily-digest` — build failed. Merge? ⚡ Reply 'reject intent-20260612-abcdef'."]


def test_reserved_class_boundary_has_no_direct_merge_or_push_path():
    source = inspect.getsource(watcher)
    assert "git merge" not in source
    assert "git push" not in source
    assert "subprocess.run([\"git\"" not in source

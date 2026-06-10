"""Review artifacts for apprentice dry-runs."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def render_review_artifact(payload: dict[str, Any]) -> str:
    intent = payload["selected_intent"]
    dry_run = payload["apprentice_dry_run"]
    would_do = payload.get("would_do", [])
    pause = payload.get("would_pause_at")

    lines = [
        f"# Apprentice Review · {intent.get('id')}",
        "",
        "This is a dry-run review artifact. It is not an approval, send, deploy, money movement, or live queue write.",
        "",
        "## Intent",
        "",
        f"- id: `{intent.get('id')}`",
        f"- title: {intent.get('title')}",
        f"- stream: `{intent.get('stream')}`",
        f"- source next: {intent.get('source_next')}",
        f"- dry-run status: `{dry_run.get('status')}`",
        "",
        "## Apprentice-Doable Work",
        "",
    ]
    if would_do:
        for step in would_do:
            lines.append(f"- `{step['step']}` -> `{step['action']}`")
    else:
        lines.append("_No delegable step before the first gate._")

    lines.extend(["", "## Reserved-Class Pause", ""])
    if pause:
        gate = pause.get("gate") or {}
        lines.extend(
            [
                f"- step: `{pause['step']}`",
                f"- reason: {pause['reason']}",
                f"- gate question: {gate.get('question')}",
                "- verbs: " + " / ".join(f"`{verb}`" for verb in gate.get("verbs", [])),
            ]
        )
    else:
        lines.append("_No Reserved-Class pause found in dry-run._")

    lines.extend(
        [
            "",
            "## Why This Is The Bottleneck",
            "",
            payload["why"],
            "",
            "## Review Notes",
            "",
            "- Apprentice may continue only through delegable prep.",
            "- Reserved-Class action requires James approval before any send, spend, deploy, legal, people, doctrine, or final blessing step.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_review_artifact(payload: dict[str, Any], path: Path | str) -> Path:
    artifact_path = Path(path)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(render_review_artifact(payload), encoding="utf-8")
    return artifact_path

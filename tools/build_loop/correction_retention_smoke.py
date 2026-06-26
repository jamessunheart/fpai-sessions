#!/usr/bin/env python3
"""Post-merge smoke test for correction retention and prompt injection.

The smoke writes one synthetic bot turn + James correction through the live
curator correction API, verifies the row is readable from brain_index.corrections,
verifies the next owner-chat prompt suffix includes that correction, and then
removes only the synthetic rows it created.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib
import importlib.util
import json
import os
import sys
import uuid
from pathlib import Path
from types import ModuleType


DEFAULT_CURATOR_PARENT = Path(os.environ.get("FPAI_CURATOR_PARENT", "/opt/sh-brain-src"))
DEFAULT_REPO_ROOT = Path(os.environ.get("FPAI_REPO_ROOT", "/opt/fpai-build/FPAI_Cockpit"))
DEFAULT_CONVERSATION_ID = "__fpai_correction_retention_smoke__"


class SmokeFailure(RuntimeError):
    """Raised when the correction retention smoke cannot prove the full path."""


def load_curator_package(curator_parent: Path) -> ModuleType:
    package_dir = curator_parent / "curator"
    init_file = package_dir / "__init__.py"
    if not init_file.exists():
        raise SmokeFailure(f"curator package not found at {package_dir}")
    existing = sys.modules.get("curator")
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(
        "curator",
        init_file,
        submodule_search_locations=[str(package_dir)],
    )
    if not spec or not spec.loader:
        raise SmokeFailure(f"could not load curator package spec from {init_file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["curator"] = module
    spec.loader.exec_module(module)
    return module


async def run_smoke(
    *,
    curator_parent: Path = DEFAULT_CURATOR_PARENT,
    repo_root: Path = DEFAULT_REPO_ROOT,
    conversation_id: str = DEFAULT_CONVERSATION_ID,
    marker: str | None = None,
) -> dict[str, str]:
    load_curator_package(curator_parent)
    corrections = importlib.import_module("curator.corrections")
    build_context = importlib.import_module("curator.build_context")
    db = importlib.import_module("curator.db")

    marker = marker or f"correction-retention-smoke-{uuid.uuid4()}"
    original_response = f"Smoke bot turn {marker}: I will forget this synthetic correction."
    james_correction = (
        f"Actually, {marker} proves James corrections must persist into the next bot prompt."
    )
    bot_turn_id = ""
    correction_count = 0

    try:
        async with db.connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO brain_index.tg_messages
                        (chat_id, role, text, private_flag)
                    VALUES (%s, 'bot', %s, TRUE)
                    RETURNING id::text
                    """,
                    (conversation_id, original_response),
                )
                row = await cur.fetchone()
                if not row:
                    raise SmokeFailure("synthetic bot turn insert returned no id")
                bot_turn_id = str(row[0])

        pair = await corrections.capture_if_correction(
            conversation_id=conversation_id,
            james_message=james_correction,
            bot_turn=corrections.BotTurn(id=bot_turn_id, text=original_response),
        )
        if pair is None:
            raise SmokeFailure("capture_if_correction did not return a correction pair")

        correction_count = await count_matching_corrections(
            db,
            conversation_id=conversation_id,
            marker=marker,
        )
        if correction_count < 1:
            raise SmokeFailure("brain_index.corrections did not retain the synthetic correction")

        recent = await corrections.recent_corrections(conversation_id=conversation_id, limit=3)
        if not any(marker in getattr(item, "james_correction", "") for item in recent):
            raise SmokeFailure("recent_corrections did not return the retained synthetic correction")

        suffix = await build_context.build_context_system_suffix(
            repo_root=repo_root,
            conversation_id=conversation_id,
            max_chars=2400,
            include_system_state=True,
            include_buildstream=True,
            include_corrections=True,
            include_becoming=False,
        )
        if marker not in suffix:
            raise SmokeFailure("next bot prompt suffix did not include the retained correction")

        return {
            "status": "pass",
            "marker": marker,
            "conversation_id": conversation_id,
            "bot_turn_id": bot_turn_id,
            "correction_count": str(correction_count),
        }
    finally:
        await cleanup_smoke_rows(
            db,
            conversation_id=conversation_id,
            marker=marker,
            bot_turn_id=bot_turn_id,
        )


async def count_matching_corrections(
    db: ModuleType,
    *,
    conversation_id: str,
    marker: str,
) -> int:
    async with db.connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT COUNT(*)
                  FROM brain_index.corrections
                 WHERE conversation_id = %s
                   AND james_correction LIKE %s
                """,
                (conversation_id, f"%{marker}%"),
            )
            row = await cur.fetchone()
    return int(row[0] if row else 0)


async def cleanup_smoke_rows(
    db: ModuleType,
    *,
    conversation_id: str,
    marker: str,
    bot_turn_id: str,
) -> None:
    async with db.connect() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                DELETE FROM brain_index.corrections
                 WHERE conversation_id = %s
                   AND james_correction LIKE %s
                """,
                (conversation_id, f"%{marker}%"),
            )
            if bot_turn_id:
                await cur.execute(
                    "DELETE FROM brain_index.tg_messages WHERE id = %s",
                    (bot_turn_id,),
                )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--curator-parent", type=Path, default=DEFAULT_CURATOR_PARENT)
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument("--conversation-id", default=DEFAULT_CONVERSATION_ID)
    parser.add_argument("--marker", default=None)
    parser.add_argument("--spec-id", default="")
    parser.add_argument("--decision-id", default="")
    parser.add_argument("--branch", default="")
    return parser.parse_args(argv)


async def async_main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        result = await run_smoke(
            curator_parent=args.curator_parent,
            repo_root=args.repo_root,
            conversation_id=args.conversation_id,
            marker=args.marker,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "fail",
                    "error": str(exc),
                    "spec_id": args.spec_id,
                    "decision_id": args.decision_id,
                    "branch": args.branch,
                },
                sort_keys=True,
            )
        )
        return 1
    result.update(
        {"spec_id": args.spec_id, "decision_id": args.decision_id, "branch": args.branch}
    )
    print(json.dumps(result, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(async_main(list(sys.argv[1:] if argv is None else argv)))


if __name__ == "__main__":
    raise SystemExit(main())

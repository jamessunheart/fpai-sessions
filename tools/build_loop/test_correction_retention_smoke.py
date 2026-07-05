from __future__ import annotations

import asyncio
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from tools.build_loop import correction_retention_smoke as smoke


ROOT = Path(__file__).resolve().parents[2]
SERVER_LOOP = ROOT / "tools" / "build_loop" / "server_build_loop.sh"


class CorrectionRetentionSmokeTest(unittest.TestCase):
    def tearDown(self) -> None:
        for name in list(sys.modules):
            if name == "curator" or name.startswith("curator."):
                sys.modules.pop(name, None)

    def test_smoke_writes_reads_injects_and_cleans_up(self) -> None:
        root = self.make_curator(prompt_includes_marker=True)

        result = asyncio.run(
            smoke.run_smoke(
                curator_parent=root,
                repo_root=ROOT,
                conversation_id="smoke-chat",
                marker="marker-pass",
            )
        )

        db = sys.modules["curator.db"]
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["correction_count"], "1")
        self.assertEqual(db.STATE["tg_messages"], [])
        self.assertEqual(db.STATE["corrections"], [])

    def test_smoke_cleans_up_when_prompt_injection_fails(self) -> None:
        root = self.make_curator(prompt_includes_marker=False)

        with self.assertRaises(smoke.SmokeFailure):
            asyncio.run(
                smoke.run_smoke(
                    curator_parent=root,
                    repo_root=ROOT,
                    conversation_id="smoke-chat",
                    marker="marker-fail",
                )
            )

        db = sys.modules["curator.db"]
        self.assertEqual(db.STATE["tg_messages"], [])
        self.assertEqual(db.STATE["corrections"], [])

    def test_server_loop_runs_smoke_after_liveness_before_notification(self) -> None:
        text = SERVER_LOOP.read_text(encoding="utf-8")

        liveness = text.index('run_liveness_probe "$LIVENESS_DECLARATION" "$LIVENESS_CHECK"')
        correction_smoke = text.index("run_correction_retention_smoke", liveness)
        # Auto-merge is SILENT now (James directive 2026-06-18: no TG ask), so the old
        # `tg "$V · AUTO-MERGED'` notification was intentionally removed. The real guarantee —
        # the correction smoke runs AFTER the liveness probe — is what we assert.
        self.assertLess(liveness, correction_smoke)
        self.assertIn("CORRECTION_RETENTION_SMOKE_DISABLE", text)
        self.assertIn("correction_retention_smoke.py", text)
        self.assertIn('"correction-retention:pass"', text)
        self.assertIn('"correction-retention:fail"', text)
        self.assertIn("queue_correction_retention_followup", text)

    def make_curator(self, *, prompt_includes_marker: bool) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fpai-correction-smoke-"))
        package = root / "curator"
        package.mkdir()
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "db.py").write_text(
            textwrap.dedent(
                """
                STATE = {"tg_messages": [], "corrections": []}

                class Cursor:
                    def __init__(self):
                        self.row = None

                    async def __aenter__(self):
                        return self

                    async def __aexit__(self, exc_type, exc, tb):
                        return False

                    async def execute(self, sql, params=()):
                        normalized = " ".join(sql.split()).lower()
                        if normalized.startswith("insert into brain_index.tg_messages"):
                            row_id = f"turn-{len(STATE['tg_messages']) + 1}"
                            STATE["tg_messages"].append({"id": row_id, "chat_id": params[0], "text": params[1]})
                            self.row = (row_id,)
                        elif normalized.startswith("select count(*) from brain_index.corrections"):
                            conversation_id, marker_like = params
                            marker = marker_like.strip("%")
                            self.row = (
                                sum(
                                    1
                                    for row in STATE["corrections"]
                                    if row["conversation_id"] == conversation_id and marker in row["james_correction"]
                                ),
                            )
                        elif normalized.startswith("delete from brain_index.corrections"):
                            conversation_id, marker_like = params
                            marker = marker_like.strip("%")
                            STATE["corrections"] = [
                                row
                                for row in STATE["corrections"]
                                if not (row["conversation_id"] == conversation_id and marker in row["james_correction"])
                            ]
                            self.row = None
                        elif normalized.startswith("delete from brain_index.tg_messages"):
                            turn_id = params[0]
                            STATE["tg_messages"] = [row for row in STATE["tg_messages"] if row["id"] != turn_id]
                            self.row = None
                        else:
                            raise AssertionError(sql)

                    async def fetchone(self):
                        return self.row

                class Connection:
                    async def __aenter__(self):
                        return self

                    async def __aexit__(self, exc_type, exc, tb):
                        return False

                    def cursor(self):
                        return Cursor()

                def connect():
                    return Connection()
                """
            ),
            encoding="utf-8",
        )
        (package / "corrections.py").write_text(
            textwrap.dedent(
                """
                from dataclasses import dataclass
                from . import db

                @dataclass(frozen=True)
                class BotTurn:
                    id: str
                    text: str

                @dataclass(frozen=True)
                class CorrectionPair:
                    conversation_id: str
                    bot_turn_id: str
                    original_response: str
                    james_correction: str

                async def capture_if_correction(*, conversation_id, james_message, bot_turn=None):
                    pair = CorrectionPair(conversation_id, bot_turn.id, bot_turn.text, james_message)
                    db.STATE["corrections"].append(pair.__dict__.copy())
                    return pair

                async def recent_corrections(*, conversation_id=None, limit=10):
                    rows = [
                        CorrectionPair(**row)
                        for row in db.STATE["corrections"]
                        if conversation_id is None or row["conversation_id"] == conversation_id
                    ]
                    return rows[:limit]

                def render_corrections_block(pairs, *, max_chars=1400):
                    return "\\n".join(f"Recent corrections\\nJames corrected: {p.james_correction}" for p in pairs)
                """
            ),
            encoding="utf-8",
        )
        suffix = "{block}" if prompt_includes_marker else "Recent corrections omitted"
        (package / "build_context.py").write_text(
            textwrap.dedent(
                f"""
                from .corrections import recent_corrections, render_corrections_block

                async def build_context_system_suffix(**kwargs):
                    pairs = await recent_corrections(conversation_id=kwargs.get("conversation_id"), limit=10)
                    block = render_corrections_block(pairs)
                    return {suffix!r}.format(block=block)
                """
            ),
            encoding="utf-8",
        )
        return root


if __name__ == "__main__":
    unittest.main()

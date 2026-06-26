from __future__ import annotations

import asyncio
import os
import importlib.util
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("build_context.py")
SPEC = importlib.util.spec_from_file_location("build_context", MODULE_PATH)
assert SPEC and SPEC.loader
build_context = importlib.util.module_from_spec(SPEC)
sys.modules["build_context"] = build_context
SPEC.loader.exec_module(build_context)

CORRECTIONS_PATH = Path(__file__).with_name("corrections.py")
CORRECTIONS_SPEC = importlib.util.spec_from_file_location("build_context_test_corrections", CORRECTIONS_PATH)
assert CORRECTIONS_SPEC and CORRECTIONS_SPEC.loader
corrections = importlib.util.module_from_spec(CORRECTIONS_SPEC)
sys.modules["build_context_test_corrections"] = corrections
CORRECTIONS_SPEC.loader.exec_module(corrections)


class BuildContextTest(unittest.TestCase):
    def setUp(self) -> None:
        patcher = patch.dict("os.environ", {"HOT_MEMORY_STATE_PATH": "/tmp/fpai-test-missing-HOT_STATE.md"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fpai-build-context-"))
        (root / "core" / "BUILD").mkdir(parents=True)
        (root / "core" / "STATE").mkdir(parents=True)
        (root / "docs" / "codex").mkdir(parents=True)
        (root / "core" / "BUILD" / "REGISTRY.json").write_text(
            json.dumps(
                {
                    "active_builds": [
                        {
                            "id": "SPEC_d011",
                            "slug": "SPEC_d011",
                            "branch": "build/SPEC_d011",
                            "status": "building",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (root / "core" / "STATE" / "NOW.md").write_text(
            "- **Builder lane** — d011 intent injector\n- next: capture corrections\n",
            encoding="utf-8",
        )
        (root / "docs" / "codex" / "INTENT_BUILDSTREAM.md").write_text(
            "- Rung 4 | id: rung4-hubs | route: apprentice | status: ready | next: build hubs\n",
            encoding="utf-8",
        )
        return root

    def add_session_persistence_module(self, root: Path) -> Path:
        continuity = root / "tools" / "continuity"
        continuity.mkdir(parents=True)
        source = Path(__file__).resolve().parents[3] / "tools" / "continuity" / "session_persistence.py"
        shutil.copyfile(source, continuity / "session_persistence.py")
        return continuity / "session_persistence.py"

    def test_repo_context_renders_bounded_prompt_suffix(self) -> None:
        suffix = asyncio.run(build_context.build_context_system_suffix(repo_root=self.make_repo(), max_chars=900))

        self.assertIn("CURRENT BUILD CONTEXT", suffix)
        self.assertIn("SPEC_d011", suffix)
        self.assertIn("rung4-hubs", suffix)
        self.assertIn("Live system status:", suffix)
        self.assertIn("Build queue:", suffix)
        self.assertIn("advisory", suffix)

    def test_persisted_session_progress_is_injected(self) -> None:
        root = self.make_repo()
        self.add_session_persistence_module(root)
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            (state_dir / "latest.json").write_text(
                json.dumps(
                    {
                        "schema": "fpai-session-snapshot.v1",
                        "session_id": "session-123",
                        "surface": "codex",
                        "saved_at": "2026-06-26T00:00:00+00:00",
                        "repo_root": str(root),
                        "branch": "build/SPEC_d011",
                        "head": "abc123",
                        "changed_files": ["tools/continuity/session_persistence.py"],
                        "active_builds": [
                            {
                                "id": "SPEC_d011",
                                "status": "building",
                                "branch": "build/SPEC_d011",
                                "tests_passed": False,
                            }
                        ],
                        "recent_results": ["SPEC_d010.result.md"],
                        "progress_note": "Session persistence captured running spec status.",
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict("os.environ", {"FPAI_SESSION_STATE_DIR": str(state_dir)}):
                suffix = asyncio.run(build_context.build_context_system_suffix(repo_root=root, max_chars=1600))

        self.assertIn("Persisted session progress", suffix)
        self.assertIn("session-123", suffix)
        self.assertIn("Session persistence captured running spec status", suffix)

    def test_persisted_session_progress_can_be_disabled(self) -> None:
        root = self.make_repo()
        self.add_session_persistence_module(root)
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            (state_dir / "latest.json").write_text(
                json.dumps(
                    {
                        "schema": "fpai-session-snapshot.v1",
                        "session_id": "session-disabled",
                        "surface": "codex",
                        "saved_at": "2026-06-26T00:00:00+00:00",
                        "active_builds": [],
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict(
                "os.environ",
                {"FPAI_SESSION_STATE_DIR": str(state_dir), "SH_SESSION_PERSISTENCE_DISABLE": "1"},
            ):
                suffix = asyncio.run(build_context.build_context_system_suffix(repo_root=root, max_chars=1600))

        self.assertNotIn("session-disabled", suffix)

    def test_disable_env_returns_empty_suffix(self) -> None:
        with patch.dict("os.environ", {"SH_BUILD_CONTEXT_DISABLE": "1"}):
            suffix = asyncio.run(build_context.build_context_system_suffix(repo_root=self.make_repo()))

        self.assertEqual(suffix, "")

    def test_fresh_hot_state_replaces_patchwork_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hot_state = Path(tmp) / "HOT_STATE.md"
            hot_state.write_text(
                "# HOT_STATE\n\n## Active directives\n- James 100% truthful directive [source: fixture - 2026-06-18]\n",
                encoding="utf-8",
            )
            with patch.dict("os.environ", {"HOT_MEMORY_STATE_PATH": str(hot_state)}):
                suffix = asyncio.run(build_context.build_context_system_suffix(repo_root=self.make_repo(), max_chars=1200))

        self.assertIn("HOT STATE", suffix)
        self.assertIn("James 100% truthful directive", suffix)
        self.assertNotIn("CURRENT BUILD CONTEXT", suffix)
        self.assertNotIn("SPEC_d011", suffix)

    def test_fresh_hot_state_still_injects_recent_corrections(self) -> None:
        pair = corrections.CorrectionPair(
            conversation_id="123",
            bot_turn_id="bot-1",
            original_response="You never told me that d010 matters.",
            james_correction="You forgot, d010 is the preference loop.",
        )

        async def fake_recent_corrections(*, conversation_id=None, limit=10):
            self.assertEqual(conversation_id, "123")
            self.assertEqual(limit, 10)
            return [pair]

        with tempfile.TemporaryDirectory() as tmp:
            hot_state = Path(tmp) / "HOT_STATE.md"
            hot_state.write_text(
                "# HOT_STATE\n\n## Active directives\n- James 100% truthful directive [source: fixture - 2026-06-18]\n",
                encoding="utf-8",
            )
            with patch.object(corrections, "recent_corrections", fake_recent_corrections), patch.dict(
                "sys.modules", {"corrections": corrections}
            ), patch.dict("os.environ", {"HOT_MEMORY_STATE_PATH": str(hot_state)}):
                suffix = asyncio.run(
                    build_context.build_context_system_suffix(
                        repo_root=self.make_repo(),
                        conversation_id="123",
                        max_chars=1600,
                    )
                )

        self.assertIn("HOT STATE", suffix)
        self.assertIn("Recent corrections James made to this bot", suffix)
        self.assertIn("d010 is the preference loop", suffix)
        self.assertNotIn("CURRENT BUILD CONTEXT", suffix)

    def test_stale_or_disabled_hot_state_falls_back_to_patchwork_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hot_state = Path(tmp) / "HOT_STATE.md"
            hot_state.write_text("# HOT_STATE\n\n- stale fact\n", encoding="utf-8")
            old = 1_700_000_000
            os.utime(hot_state, (old, old))
            with patch.dict("os.environ", {"HOT_MEMORY_STATE_PATH": str(hot_state)}):
                stale_suffix = asyncio.run(build_context.build_context_system_suffix(repo_root=self.make_repo(), max_chars=1200))
            with patch.dict("os.environ", {"HOT_MEMORY_STATE_PATH": str(hot_state), "HOT_MEMORY_DISABLE": "1"}):
                disabled_suffix = asyncio.run(build_context.build_context_system_suffix(repo_root=self.make_repo(), max_chars=1200))

        self.assertIn("CURRENT BUILD CONTEXT", stale_suffix)
        self.assertIn("SPEC_d011", stale_suffix)
        self.assertIn("CURRENT BUILD CONTEXT", disabled_suffix)

    def test_render_respects_character_bound(self) -> None:
        context = build_context.BuildContext(
            source="test",
            focus=["f" * 400],
            active_loops=["a" * 400],
            open_intents=["i" * 400],
        )

        rendered = build_context.render_build_context(context, max_chars=240)

        self.assertLessEqual(len(rendered), 240)
        self.assertIn("bounded", rendered)

    def test_recent_corrections_are_injected(self) -> None:
        pair = corrections.CorrectionPair(
            conversation_id="123",
            bot_turn_id="bot-1",
            original_response="You never told me your birthday.",
            james_correction="You forgot, I said my birthday is June 4.",
        )

        async def fake_recent_corrections(*, conversation_id=None, limit=10):
            self.assertEqual(conversation_id, "123")
            return [pair]

        with patch.object(corrections, "recent_corrections", fake_recent_corrections), patch.dict(
            "sys.modules", {"corrections": corrections}
        ):
            suffix = asyncio.run(
                build_context.build_context_system_suffix(
                    repo_root=self.make_repo(),
                    conversation_id="123",
                    max_chars=1600,
                )
            )

        self.assertIn("Corrections:", suffix)
        self.assertIn("You forgot, I said my birthday is June 4.", suffix)

    def test_context_routing_can_skip_corrections_and_becoming(self) -> None:
        pair = corrections.CorrectionPair(
            conversation_id="123",
            bot_turn_id="bot-1",
            original_response="old response",
            james_correction="new correction",
        )

        async def fake_recent_corrections(*, conversation_id=None, limit=10):
            return [pair]

        async def fake_render_becoming_context(person_id, *, max_chars=900):
            return "--- BECOMING STATE (advisory, per-person) ---\nStage: activate"

        becoming = types.SimpleNamespace(render_becoming_context=fake_render_becoming_context)
        with patch.object(corrections, "recent_corrections", fake_recent_corrections), patch.dict(
            "sys.modules", {"corrections": corrections, "becoming": becoming}
        ):
            suffix = asyncio.run(
                build_context.build_context_system_suffix(
                    repo_root=self.make_repo(),
                    conversation_id="123",
                    max_chars=1800,
                    include_system_state=True,
                    include_buildstream=True,
                    include_corrections=False,
                    include_becoming=False,
                )
            )

        self.assertIn("CURRENT BUILD CONTEXT", suffix)
        self.assertIn("Live system status:", suffix)
        self.assertIn("SPEC_d011", suffix)
        self.assertNotIn("Corrections:", suffix)
        self.assertNotIn("new correction", suffix)
        self.assertNotIn("BECOMING STATE", suffix)

    def test_treasury_routing_keeps_status_and_corrections_only(self) -> None:
        pair = corrections.CorrectionPair(
            conversation_id="123",
            bot_turn_id="bot-1",
            original_response="old response",
            james_correction="treasury correction",
        )

        async def fake_recent_corrections(*, conversation_id=None, limit=10):
            return [pair]

        with patch.object(corrections, "recent_corrections", fake_recent_corrections), patch.dict(
            "sys.modules", {"corrections": corrections}
        ):
            suffix = asyncio.run(
                build_context.build_context_system_suffix(
                    repo_root=self.make_repo(),
                    conversation_id="123",
                    max_chars=1800,
                    include_system_state=True,
                    include_buildstream=False,
                    include_corrections=True,
                    include_becoming=False,
                )
            )

        self.assertIn("Live system status:", suffix)
        self.assertIn("Corrections:", suffix)
        self.assertIn("treasury correction", suffix)
        self.assertNotIn("SPEC_d011", suffix)
        self.assertNotIn("rung4-hubs", suffix)

    def test_recent_session_insights_are_injected(self) -> None:
        class FakeCursor:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_exc):
                return False

            async def execute(self, _sql, _params=None):
                return None

            async def fetchall(self):
                return [
                    (
                        "architecture",
                        "d110 writes every Claude Code session decision",
                        "Bot reads session_insights with high-weight decisions first.",
                        ["d110"],
                        9,
                        "claude_code",
                        "2026-06-18T00:00:00Z",
                    )
                ]

        class FakeConnection:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_exc):
                return False

            def cursor(self):
                return FakeCursor()

        def fake_connect():
            return FakeConnection()

        fake_db = types.SimpleNamespace(connect=fake_connect)
        with patch.dict("sys.modules", {"db": fake_db}):
            suffix = asyncio.run(build_context.build_context_system_suffix(repo_root=self.make_repo(), max_chars=1800))

        self.assertIn("Recent decisions (all surfaces):", suffix)
        self.assertIn("d110 writes every Claude Code session decision", suffix)
        self.assertIn("session_insights", suffix)

    def test_becoming_context_is_injected_for_conversation(self) -> None:
        async def fake_render_becoming_context(person_id, *, max_chars=900):
            self.assertEqual(person_id, "123")
            return "--- BECOMING STATE (advisory, per-person) ---\nStage: activate"

        module = types.SimpleNamespace(render_becoming_context=fake_render_becoming_context)
        with patch.dict("sys.modules", {"becoming": module}):
            suffix = asyncio.run(
                build_context.build_context_system_suffix(
                    repo_root=self.make_repo(),
                    conversation_id="123",
                    max_chars=1800,
                )
            )

        self.assertIn("BECOMING STATE", suffix)
        self.assertIn("Stage: activate", suffix)

    def test_active_diagnostic_context_is_bounded_and_prefixed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            context_path = Path(tmp) / "diagnostic.json"
            context_path.write_text(
                json.dumps(
                    {
                        "audit_id": "diag-test",
                        "expires_at": "2099-01-01T00:00:00Z",
                        "prompt_prefix": "Answer honestly from your experience.",
                        "last_50_tg_messages": [{"role": "user", "text": "What did you miss?"}],
                        "not_now_decisions": [{"id": "d1", "question": "Build this now?"}],
                        "rejected_builds": [{"id": "SPEC_x", "notes": "Rejected for missing test."}],
                    }
                ),
                encoding="utf-8",
            )

            prefix = build_context.diagnostic_system_prefix(context_path)
            rendered = build_context.render_active_diagnostic_context(path=context_path, max_chars=900)

        self.assertIn("Answer honestly from your experience.", prefix)
        self.assertIn("ACTIVE COUNCIL SELF-DIAGNOSTIC CONTEXT", rendered)
        self.assertIn("Rejected for missing test.", rendered)


if __name__ == "__main__":
    unittest.main()

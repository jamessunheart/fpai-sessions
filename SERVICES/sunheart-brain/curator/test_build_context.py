from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import tempfile
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

    def test_repo_context_renders_bounded_prompt_suffix(self) -> None:
        suffix = asyncio.run(build_context.build_context_system_suffix(repo_root=self.make_repo(), max_chars=900))

        self.assertIn("CURRENT BUILD CONTEXT", suffix)
        self.assertIn("SPEC_d011", suffix)
        self.assertIn("rung4-hubs", suffix)
        self.assertIn("Live system status:", suffix)
        self.assertIn("Build queue:", suffix)
        self.assertIn("advisory", suffix)

    def test_disable_env_returns_empty_suffix(self) -> None:
        with patch.dict("os.environ", {"SH_BUILD_CONTEXT_DISABLE": "1"}):
            suffix = asyncio.run(build_context.build_context_system_suffix(repo_root=self.make_repo()))

        self.assertEqual(suffix, "")

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

    def test_becoming_context_is_injected_for_conversation(self) -> None:
        async def fake_render_becoming_context(person_id, *, max_chars=900):
            self.assertEqual(person_id, "123")
            return "--- BECOMING STATE (advisory, per-person) ---\nStage: activate"

        import types

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

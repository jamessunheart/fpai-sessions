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


if __name__ == "__main__":
    unittest.main()

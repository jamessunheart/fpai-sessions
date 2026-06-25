from __future__ import annotations

import os
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from curator.blueprints import manager


BASE_BLUEPRINT = """# Beacon Blueprint

## Identity

- **Function:** Beacon

## What it does

Beacon routes growth from reviewed truth assets.

## Quality standard

Beacon must keep public copy draft-tagged until approved and throttle CORA farming above 10:1.

## Current behavior (verified)

- 2026-06-15: Old behavior.

## Known gaps

- 2026-06-15: Old gap.

## Improvement history

| Date | Build | What changed | Why it mattered |
|---|---|---|---|
| 2026-06-15 | d038 | Old row | Old reason |

## Test coverage

- Old test.
"""


class BlueprintManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_disable = os.environ.pop("BLUEPRINTS_DISABLE", None)

    def tearDown(self) -> None:
        if self._old_disable is not None:
            os.environ["BLUEPRINTS_DISABLE"] = self._old_disable
        else:
            os.environ.pop("BLUEPRINTS_DISABLE", None)

    def test_get_blueprint_returns_content_for_seeded_modules(self) -> None:
        for module in manager.BLUEPRINT_MODULES:
            with self.subTest(module=module):
                content = manager.get_blueprint(module)
                self.assertIn("## Quality standard", content)
                self.assertIn("## Improvement history", content)

    def test_update_blueprint_after_build_updates_improvement_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "beacon.md"
            path.write_text(BASE_BLUEPRINT, encoding="utf-8")

            def runner(prompt: str) -> str:
                self.assertIn("Build diff summary", prompt)
                self.assertIn("d050", prompt)
                return BASE_BLUEPRINT.replace(
                    "| 2026-06-15 | d038 | Old row | Old reason |",
                    "| 2026-06-16 | d050 | Updated Beacon behavior | Blueprint records build changes |\n"
                    "| 2026-06-15 | d038 | Old row | Old reason |",
                )

            with patch.object(manager, "blueprint_path", lambda _module: path), patch.object(
                manager, "_find_registry_entry", lambda _decision_id, _branch: {"notes": "beacon"}
            ), patch.object(manager, "_spec_text", lambda _decision_id, _entry: "d050 Beacon build spec"), patch.object(
                manager, "_changed_paths", lambda _branch: ["tools/beacon/variant_generator.py"]
            ), patch.object(manager, "_diff_summary", lambda _branch: "tools/beacon/variant_generator.py | 2 +"):
                manager.update_blueprint_after_build("d050", "build/SPEC_d050", claude_runner=runner, commit=False)

            updated = path.read_text(encoding="utf-8")
            self.assertIn("2026-06-16 | d050", updated)
            self.assertIn("Updated Beacon behavior", updated)

    def test_update_blueprint_after_correction_appends_known_gap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ember.md"
            path.write_text(BASE_BLUEPRINT.replace("# Beacon", "# Ember"), encoding="utf-8")

            with patch.object(manager, "blueprint_path", lambda _module: path), patch.object(manager, "today", lambda: "2026-06-16"):
                manager.update_blueprint_after_correction("ember", "It forgot the latest build status.")

            updated = path.read_text(encoding="utf-8")
            self.assertIn("## Known gaps", updated)
            self.assertIn("- 2026-06-16: It forgot the latest build status.", updated)

    def test_quality_standard_section_never_deleted_by_auto_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "beacon.md"
            path.write_text(BASE_BLUEPRINT, encoding="utf-8")

            def runner(_prompt: str) -> str:
                return """# Beacon Blueprint

## Identity

- **Function:** Beacon

## Current behavior (verified)

- 2026-06-16: Updated.
"""

            with patch.object(manager, "blueprint_path", lambda _module: path), patch.object(
                manager, "_find_registry_entry", lambda _decision_id, _branch: {}
            ), patch.object(manager, "_spec_text", lambda _decision_id, _entry: "beacon spec"), patch.object(
                manager, "_changed_paths", lambda _branch: ["tools/beacon/x.py"]
            ), patch.object(manager, "_diff_summary", lambda _branch: "x"):
                manager.update_blueprint_after_build("d050", "build/SPEC_d050", claude_runner=runner, commit=False)

            updated = path.read_text(encoding="utf-8")
            self.assertIn("## Quality standard", updated)
            self.assertIn("draft-tagged", updated)

    def test_sharpen_quality_standard_proposes_measurable_standard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "beacon.md"
            path.write_text(BASE_BLUEPRINT, encoding="utf-8")
            sent: list[str] = []

            with patch.object(manager, "blueprint_path", lambda _module: path):
                proposal = manager.sharpen_quality_standard(
                    "beacon",
                    claude_runner=lambda _prompt: "Within 3 builds, Beacon should reach 5 reviewed assets and 2 tested campaigns.",
                    send_func=sent.append,
                )

            self.assertIn("5 reviewed assets", proposal)
            self.assertIn("Reply yes to adopt", sent[0])

    def test_update_cli_alias_refreshes_module(self) -> None:
        calls: list[tuple[str, str, bool]] = []

        def fake_update(decision_id: str, branch: str, *, commit: bool = True, **_kwargs) -> None:
            calls.append((decision_id, branch, commit))

        with patch.object(manager, "update_blueprint_after_build", fake_update):
            code = manager.main(["update", "forge", "--no-commit"])

        self.assertEqual(code, 0)
        self.assertEqual(calls, [("forge", "build/forge", False)])

    def test_correction_blueprint_gap_uses_previous_bot_context(self) -> None:
        module_path = manager.REPO_ROOT / "SERVICES" / "sunheart-brain" / "curator" / "corrections.py"
        spec = importlib.util.spec_from_file_location("d050_corrections", module_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        corrections = importlib.util.module_from_spec(spec)
        sys.modules["d050_corrections"] = corrections
        spec.loader.exec_module(corrections)
        updates: list[tuple[str, str]] = []

        with patch.object(corrections, "detect_module_from_text", lambda text: "beacon" if "Beacon" in text else ""), patch.object(
            corrections, "update_blueprint_after_correction", lambda module, text: updates.append((module, text))
        ):
            corrections._update_blueprint_gap("Actually, use the reviewed source asset.", context="Beacon generated from scratch.")

        self.assertEqual(updates, [("beacon", "Actually, use the reviewed source asset.")])

    def test_codex_spec_generation_includes_blueprint_wiring(self) -> None:
        script = manager.REPO_ROOT / "tools" / "build_loop" / "run_codex.sh"
        content = script.read_text(encoding="utf-8")
        self.assertIn("Existing module blueprint (build against this standard)", content)
        self.assertIn("curator/blueprints/manager.py", content)

    def test_server_build_loop_updates_blueprint_after_merge(self) -> None:
        script = manager.REPO_ROOT / "tools" / "build_loop" / "server_build_loop.sh"
        content = script.read_text(encoding="utf-8")
        self.assertIn("update_blueprint_after_merge", content)
        self.assertIn('update-after-build "$did" "$branch"', content)
        self.assertIn('update_blueprint_after_merge "$DID" "$BR"', content)
        self.assertIn('update_blueprint_after_merge "$BDID" "$BBR"', content)
        self.assertIn("BLUEPRINTS_DISABLE", content)

    def test_council_prompt_includes_relevant_blueprint_wiring(self) -> None:
        script = manager.REPO_ROOT / "tools" / "council" / "debate.py"
        content = script.read_text(encoding="utf-8")
        self.assertIn("[Module blueprints", content)
        self.assertIn("build_blueprint_context", content)


if __name__ == "__main__":
    unittest.main()

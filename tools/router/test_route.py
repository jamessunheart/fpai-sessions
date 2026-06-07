from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.router import route


class RouterTestCase(unittest.TestCase):
    def make_roots(self) -> tuple[Path, Path]:
        root = Path(tempfile.mkdtemp(prefix="fpai-router-test-"))
        repo = root / "repo"
        vault = root / "vault"
        (repo / "docs" / "codex" / "specs").mkdir(parents=True)
        (vault / "00_MEMORY").mkdir(parents=True)
        return repo, vault

    def write_intents(self, vault: Path, body: str) -> None:
        (vault / "00_MEMORY" / "INTENT BUILDSTREAM.md").write_text(
            f"# Intent Buildstream\n{route.INTENTS_START}\n{body}\n{route.INTENTS_END}\n",
            encoding="utf-8",
        )

    def test_ready_intent_drafts_exactly_one_spec(self) -> None:
        repo, vault = self.make_roots()
        self.write_intents(
            vault,
            "- id:test-router | value:5 | unlocks:test | status:ready | Test Router - create one safe helper\n"
            "- id:test | value:5 | unlocks:none | status:blocked | Self-standing test",
        )

        result = route.route_once(repo, vault, None, dry_run=False, append=False, skip_cost_guard=True)

        self.assertEqual(result.action, "draft-spec")
        specs = sorted((repo / "docs" / "codex" / "specs").glob("*.md"))
        self.assertEqual([p.name for p in specs], ["SPEC_test-router.md"])
        text = specs[0].read_text(encoding="utf-8")
        self.assertIn("status: needs-bless", text)
        self.assertIn("source_intent: test-router", text)

    def test_blessed_spec_routes_build_even_if_body_mentions_needs_bless(self) -> None:
        repo, vault = self.make_roots()
        self.write_intents(
            vault,
            "- id:auto-routing | value:5 | unlocks:test | status:ready | route:codex | link:AI PROTOCOLS | Auto-routing - route one thing",
        )
        (repo / "docs" / "codex" / "specs" / "SPEC_auto-routing.md").write_text(
            "# SPEC_auto-routing\n\n"
            "status: blessed\n\n"
            "## Definition\n"
            "- no spec yet -> draft a downstream spec with status: needs-bless\n",
            encoding="utf-8",
        )

        result = route.route_once(repo, vault, None, dry_run=True, append=False, skip_cost_guard=True)

        self.assertEqual(result.action, "route-build")
        self.assertEqual(result.intent.route, "codex")
        self.assertEqual(result.intent.link, "AI PROTOCOLS")

    def test_money_public_intent_escalates_without_writing(self) -> None:
        repo, vault = self.make_roots()
        self.write_intents(
            vault,
            "- id:money | value:5 | unlocks:test | status:ready | Treasury transfer - move money publicly",
        )

        result = route.route_once(repo, vault, None, dry_run=False, append=False, skip_cost_guard=True)

        self.assertEqual(result.action, "escalate")
        self.assertIsNone(result.target)
        specs = list((repo / "docs" / "codex" / "specs").glob("*.md"))
        self.assertEqual(specs, [])

    def test_dirty_handoff_append_is_skipped(self) -> None:
        repo, vault = self.make_roots()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
        (repo / "docs" / "codex").mkdir(parents=True, exist_ok=True)
        (repo / "docs" / "codex" / "HANDOFF.md").write_text(
            "# Handoff\n\n## 📥 CODEX → EMBER\n",
            encoding="utf-8",
        )
        self.write_intents(
            vault,
            "- id:money | value:5 | unlocks:test | status:ready | Treasury transfer - move money publicly",
        )

        result = route.route_once(repo, vault, None, dry_run=False, append=True, skip_cost_guard=True)

        self.assertEqual(result.action, "escalate")
        self.assertTrue(any("skip dirty" in item for item in result.wrote))

    def test_repo_intent_fallback_when_vault_missing(self) -> None:
        repo, vault = self.make_roots()
        (repo / "docs" / "codex").mkdir(parents=True, exist_ok=True)
        (repo / "docs" / "codex" / "INTENT_BUILDSTREAM.md").write_text(
            "# Intent Buildstream\n"
            f"{route.INTENTS_START}\n"
            "- id:auto-routing | value:5 | unlocks:test | status:ready | Auto-routing - route from repo\n"
            f"{route.INTENTS_END}\n",
            encoding="utf-8",
        )
        (repo / "docs" / "codex" / "specs" / "SPEC_auto-routing.md").write_text(
            "# SPEC_auto-routing\n\nstatus: blessed\n",
            encoding="utf-8",
        )

        result = route.route_once(repo, vault, None, dry_run=True, append=False, skip_cost_guard=True)

        self.assertEqual(result.action, "route-build")
        self.assertTrue(any("INTENT_BUILDSTREAM.md" in note for note in result.skipped))

    def test_no_ready_intents_reports_none(self) -> None:
        repo, vault = self.make_roots()
        self.write_intents(
            vault,
            "- id:test | value:5 | unlocks:none | status:blocked | Self-standing test",
        )

        result = route.route_once(repo, vault, None, dry_run=True, append=False, skip_cost_guard=True)

        self.assertIsNone(result.intent)
        self.assertEqual(result.action, "none")


if __name__ == "__main__":
    unittest.main()

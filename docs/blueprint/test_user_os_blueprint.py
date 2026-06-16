import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BLUEPRINT = ROOT / "docs" / "blueprint" / "USER_OS_BLUEPRINT.md"
MIGRATION = (
    ROOT
    / "docs"
    / "blueprint"
    / "brain_index_replication_insights.sql"
)


class UserOsBlueprintTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = BLUEPRINT.read_text(encoding="utf-8")

    def test_required_sections_present(self):
        for heading in (
            "## 1. Minimum Install Checklist",
            "## 2. What Works Today",
            "## 3. Gap Log",
            "## 4. Journey Refinement Hooks",
            "## 5. Agent Passport Schema Stub",
        ):
            self.assertIn(heading, self.text)

    def test_gap_log_is_non_empty(self):
        gap_section = self._section("## 3. Gap Log", "## 4. Journey Refinement Hooks")
        gap_rows = [
            line
            for line in gap_section.splitlines()
            if line.startswith("|")
            and "---" not in line
            and "Gap | Current reality" not in line
        ]
        self.assertGreaterEqual(len(gap_rows), 3)

    def test_journey_hooks_are_parseable(self):
        hooks_section = self._section(
            "## 4. Journey Refinement Hooks",
            "### Brain Index Append Mechanism",
        )
        payload = self._first_json_block(hooks_section)
        self.assertEqual(payload["schema"], "user_os_journey_hooks.v1")
        layers = {layer["id"]: layer for layer in payload["layers"]}
        self.assertEqual(set(layers), {"ONBOARDING", "EVOLUTION", "UPGRADE_PATH"})
        for layer in layers.values():
            self.assertRegex(layer["version"], r"^\d+\.\d+$")
            self.assertIn("review_signal", layer)

    def test_agent_passport_schema_is_parseable(self):
        passport_section = self._section("## 5. Agent Passport Schema Stub", None)
        payload = self._first_json_block(passport_section)
        self.assertEqual(payload["schema"], "agent_passport.v0")
        for key in (
            "identity",
            "goals",
            "preferred_channel",
            "memory_permissions",
            "access_level",
            "proof_history",
        ):
            self.assertIn(key, payload)

    def test_replication_insight_append_mechanism_declared(self):
        self.assertIn("replication_insight.v1", self.text)
        sql = MIGRATION.read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS replication_insights", sql)
        self.assertIn("CHECK (note_type = 'replication_insight.v1')", sql)
        self.assertIn("'upgrade_trigger'", sql)
        self.assertIn("prevent_replication_insights_mutation", sql)

    @classmethod
    def _section(cls, start_heading, end_heading):
        start = cls.text.index(start_heading)
        if end_heading is None:
            return cls.text[start:]
        end = cls.text.index(end_heading, start)
        return cls.text[start:end]

    @staticmethod
    def _first_json_block(text):
        match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
        if not match:
            raise AssertionError("No JSON code block found")
        return json.loads(match.group(1))


if __name__ == "__main__":
    unittest.main()

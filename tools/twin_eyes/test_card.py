from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.twin_eyes.card import ManifestError, build_card, render_html, stable_json


AS_OF = datetime(2026, 8, 29, 23, 4, 43, tzinfo=timezone.utc)


class TwinEyesCardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[2]
        cls.manifest_path = Path(__file__).with_name("demo_manifest.json")
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))

    def test_known_broken_corpus_has_full_recall_and_no_false_clear(self) -> None:
        card = build_card(self.manifest, self.repo_root, AS_OF)
        expected_conflicts = {"operating_phase", "inert_merged_build_count"}
        detected = {
            topic["id"]
            for topic in card["topics"]
            if topic["agreement"] == "conflict"
        }
        false_clear = {
            topic["id"]
            for topic in card["topics"]
            if topic["id"] in expected_conflicts and topic["agreement"] == "clear"
        }
        self.assertEqual(detected, expected_conflicts)
        self.assertEqual(false_clear, set())

    def test_missing_literal_is_unknown_not_clear(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["topics"][0]["observations"][0]["evidence_text"] = "not present anywhere"
        topic = build_card(manifest, self.repo_root, AS_OF)["topics"][0]
        self.assertEqual(topic["agreement"], "conflict")
        self.assertEqual(topic["evidence"], "claimed")
        manifest["topics"][0]["observations"] = manifest["topics"][0]["observations"][:1]
        topic = build_card(manifest, self.repo_root, AS_OF)["topics"][0]
        self.assertEqual(topic["agreement"], "unknown")
        self.assertNotEqual(topic["agreement"], "clear")

    def test_all_matching_same_values_are_clear(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["topics"] = [manifest["topics"][0]]
        for observation in manifest["topics"][0]["observations"]:
            observation["value"] = "same"
        topic = build_card(manifest, self.repo_root, AS_OF)["topics"][0]
        self.assertEqual(topic["agreement"], "clear")

    def test_source_escape_is_rejected(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["topics"][0]["observations"][0]["source"] = "../outside.md"
        with self.assertRaises(ManifestError):
            build_card(manifest, self.repo_root, AS_OF)

    def test_authority_or_actuation_is_rejected(self) -> None:
        for field, value in (("authority", "authority"), ("actuation", True)):
            manifest = copy.deepcopy(self.manifest)
            manifest["card"][field] = value
            with self.assertRaises(ManifestError):
                build_card(manifest, self.repo_root, AS_OF)

    def test_outputs_are_byte_reproducible_and_non_actuating(self) -> None:
        first = build_card(self.manifest, self.repo_root, AS_OF)
        second = build_card(self.manifest, self.repo_root, AS_OF)
        self.assertEqual(stable_json(first).encode(), stable_json(second).encode())
        self.assertEqual(render_html(first).encode(), render_html(second).encode())
        html_text = render_html(first)
        self.assertIn("Lens only", html_text)
        self.assertIn("No actuation", html_text)
        self.assertNotIn("<form", html_text)
        self.assertNotIn("fetch(", html_text)


if __name__ == "__main__":
    unittest.main()

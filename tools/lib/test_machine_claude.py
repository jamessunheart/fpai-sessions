import unittest
from unittest import mock

from tools.lib.machine_claude import _json_object_from_text, robust_json


class MachineClaudeJsonTests(unittest.TestCase):
    def test_robust_json_accepts_strict_json(self):
        self.assertEqual(robust_json('{"ok": true}')["ok"], True)

    def test_robust_json_uses_balanced_object_scan(self):
        payload = robust_json('preface {"text": "brace } in string", "nested": {"n": 1}} suffix')

        self.assertEqual(payload["text"], "brace } in string")
        self.assertEqual(payload["nested"]["n"], 1)

    def test_robust_json_falls_back_to_regex_extract(self):
        with mock.patch(
            "tools.lib.machine_claude._json_object_from_text",
            side_effect=ValueError("scan failed"),
        ):
            payload = robust_json('prefix {"a": {"b": 2}} suffix')

        self.assertEqual(payload["a"]["b"], 2)

    def test_robust_json_logs_full_raw_text_on_failure(self):
        raw = "not json " + ("x" * 500)
        events = []

        with self.assertRaises(ValueError):
            robust_json(raw, logger=lambda event, detail: events.append((event, detail)))

        self.assertEqual(events, [("debate_parse_fail", f"raw: {raw}")])

    def test_moved_json_object_helper_still_extracts_wrapped_object(self):
        self.assertEqual(_json_object_from_text('thinking\n{"propose": false}\n')["propose"], False)


if __name__ == "__main__":
    unittest.main()

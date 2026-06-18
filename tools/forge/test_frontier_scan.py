from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.forge import daily_scan, weekly_scan
from tools.forge.frontier_scan import (
    DAILY_TIMEOUT_SECONDS,
    WEEKLY_TIMEOUT_SECONDS,
    Finding,
    append_daily_log,
    build_prompt,
    parse_findings,
    run_scan,
    write_weekly_report,
)


NOW = dt.datetime(2026, 6, 18, 7, 0, tzinfo=dt.timezone.utc)


def temp_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="fpai-d096-frontier-"))
    (root / "core" / "STATE").mkdir(parents=True)
    return root


class FrontierScanTest(unittest.TestCase):
    def finding(self, **overrides: object) -> Finding:
        payload = {
            "area": "routing",
            "project": "LiteLLM Semantic Router",
            "relevance": 8,
            "adoption_cost": "low",
            "quantum_leap": True,
            "action": "ADOPT",
            "note": "Public routing pattern worth evaluating.",
        }
        payload.update(overrides)
        return Finding(**payload)

    def test_parse_findings_accepts_json_payload(self) -> None:
        raw = json.dumps(
            {
                "findings": [
                    {
                        "area": "learning",
                        "project": "GEPA",
                        "relevance": 9,
                        "adoption_cost": "low",
                        "quantum_leap": True,
                        "action": "ADOPT",
                        "note": "Prompt evolution benchmark remains useful.",
                    }
                ]
            }
        )
        findings = parse_findings(raw)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].project, "GEPA")
        self.assertEqual(findings[0].score, 9)
        self.assertTrue(findings[0].quantum_leap)

    def test_run_scan_uses_daily_timeout_and_public_prompt(self) -> None:
        calls: list[tuple[str, int]] = []

        def fake_runner(prompt: str, timeout_seconds: int) -> str:
            calls.append((prompt, timeout_seconds))
            return json.dumps({"findings": [{"area": "models", "project": "Qwen", "score": 7, "note": "Watch"}]})

        findings = run_scan("daily", runner=fake_runner, current=NOW)
        self.assertEqual(findings[0].project, "Qwen")
        self.assertEqual(calls[0][1], DAILY_TIMEOUT_SECONDS)
        self.assertIn("Use only public frontier information", calls[0][0])
        self.assertNotIn("brain_index.corrections", calls[0][0])

    def test_weekly_scan_uses_weekly_timeout(self) -> None:
        calls: list[int] = []

        def fake_runner(_prompt: str, timeout_seconds: int) -> str:
            calls.append(timeout_seconds)
            return json.dumps({"findings": [{"area": "agents", "project": "CrewAI", "score": 6, "note": "Watch"}]})

        run_scan("weekly", runner=fake_runner, current=NOW)
        self.assertEqual(calls, [WEEKLY_TIMEOUT_SECONDS])

    def test_daily_log_security_gate_strips_injected_contact_email(self) -> None:
        root = temp_root()
        result = append_daily_log(
            [
                self.finding(note="Safe public note."),
                self.finding(project="Unsafe item", note="Contact james@example.com about probe_sessions."),
            ],
            root / "core" / "STATE" / "FRONTIER_LOG.md",
            current=NOW,
        )
        text = (root / "core" / "STATE" / "FRONTIER_LOG.md").read_text(encoding="utf-8")
        self.assertEqual(result["written"], 2)
        self.assertIn("LiteLLM Semantic Router", text)
        self.assertNotIn("james@example.com", text)
        self.assertNotIn("probe_sessions", text)
        self.assertIn("[redacted private/internal detail]", text)
        self.assertIn("email", result["warnings"])

    def test_weekly_report_marks_new_findings_and_sections(self) -> None:
        root = temp_root()
        previous = root / "core" / "STATE" / "FRONTIER_WEEKLY_2026-06-11.md"
        previous.write_text("- [SEEN] [models] [Old Tool] [score 8]\n", encoding="utf-8")
        output = root / "core" / "STATE" / "FRONTIER_WEEKLY_2026-06-18.md"
        result = write_weekly_report(
            [
                self.finding(project="New Router", action="ADOPT", relevance=9, quantum_leap=True),
                self.finding(project="Old Tool", action="WATCH", relevance=6, quantum_leap=False),
            ],
            output,
            previous_reports=[previous],
            current=NOW,
        )
        text = output.read_text(encoding="utf-8")
        self.assertEqual(result["quantum_leaps"], 1)
        self.assertIn("## QUANTUM_LEAP", text)
        self.assertIn("[NEW] [routing] [New Router]", text)
        self.assertIn("[SEEN] [routing] [Old Tool]", text)

    def test_daily_scan_skips_without_enabled_env(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            result = daily_scan.run_daily_scan(root=temp_root(), current=NOW)
        self.assertEqual(result["status"], "skipped")

    def test_daily_scan_writes_with_mocked_runner(self) -> None:
        root = temp_root()
        with (
            mock.patch("tools.forge.daily_scan.run_scan", return_value=[self.finding()]),
            mock.patch("tools.forge.daily_scan.notify_if_needed", return_value={"notified": False}),
        ):
            result = daily_scan.run_daily_scan(root=root, force=True, current=NOW)
        self.assertEqual(result["status"], "ok")
        self.assertTrue((root / "core" / "STATE" / "FRONTIER_LOG.md").exists())

    def test_weekly_scan_writes_with_mocked_runner(self) -> None:
        root = temp_root()
        with (
            mock.patch("tools.forge.weekly_scan.run_scan", return_value=[self.finding()]),
            mock.patch("tools.forge.weekly_scan.notify_if_needed", return_value={"notified": False}),
        ):
            result = weekly_scan.run_weekly_scan(root=root, force=True, current=NOW)
        self.assertEqual(result["status"], "ok")
        self.assertTrue((root / "core" / "STATE" / "FRONTIER_WEEKLY_2026-06-18.md").exists())

    def test_prompt_names_public_sources_only(self) -> None:
        prompt = build_prompt("weekly", NOW)
        self.assertIn("arXiv recent papers", prompt)
        self.assertIn("major GitHub releases", prompt)
        self.assertNotIn("probe_pool", prompt)
        self.assertNotIn("thread content", prompt)


if __name__ == "__main__":
    unittest.main()

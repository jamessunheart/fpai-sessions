import json
import unittest
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from tools.council import debate


class CouncilDebateTest(unittest.TestCase):
    def test_pragmatist_uses_glm_caller(self):
        calls = []

        def glm(messages, max_tokens, temperature):
            calls.append((messages, max_tokens, temperature))
            return "Build the smallest budget-guarded GLM adapter first."

        lens = debate.pragmatist_voice("queue\nchat", glm_caller=glm)

        self.assertIn("GLM adapter", lens)
        self.assertEqual(calls[0][0][0]["role"], "system")
        self.assertIn("Pragmatist lens", calls[0][0][0]["content"])
        self.assertEqual(calls[0][1], 180)
        self.assertEqual(calls[0][2], 0.2)

    def test_council_pragmatist_prompt_uses_prompt_efficiency_renderer(self):
        with mock.patch(
            "tools.prompt_efficiency.gepa_loop.render_council_pragmatist_prompt",
            return_value="FPAI council Pragmatist lens: optimized pending prompt.",
        ):
            prompt = debate._council_pragmatist_prompt()

        self.assertEqual(prompt, "FPAI council Pragmatist lens: optimized pending prompt.")

    def test_build_prompt_includes_sovereign_pragmatist_lens(self):
        prompt = debate.build_prompt("queue", "chats", "", pragmatist="Use RunPod GLM.")

        self.assertIn("SOVEREIGN PRAGMATIST LENS", prompt)
        self.assertIn("Use RunPod GLM.", prompt)

    def test_build_prompt_includes_opportunity_portfolio(self):
        with mock.patch(
            "tools.allocation.opportunity_engine.council_context",
            return_value="OPPORTUNITY PORTFOLIO\n- Resource Optimization Audit: allocation=26.5",
        ):
            prompt = debate.build_prompt("queue", "chats", "")

        self.assertIn("OPPORTUNITY PORTFOLIO", prompt)
        self.assertIn("Resource Optimization Audit", prompt)

    def test_run_claude_json_parses_wrapped_json(self):
        def runner(args, **kwargs):
            self.assertEqual(args[0], "/usr/bin/claude")
            return subprocess.CompletedProcess(
                args,
                0,
                'thinking...\n{"propose": false, "title": "No build"}\n',
                "",
            )

        with mock.patch.object(debate.shutil, "which", return_value="/usr/bin/claude"):
            payload, result = debate.run_claude_json("prompt", runner=runner)

        self.assertFalse(payload["propose"])
        self.assertEqual(result.returncode, 0)

    def test_run_claude_json_reports_cli_failure(self):
        def runner(args, **kwargs):
            return subprocess.CompletedProcess(args, 1, "", "auth failed")

        with mock.patch.object(debate.shutil, "which", return_value="/usr/bin/claude"):
            with self.assertRaisesRegex(RuntimeError, "auth failed"):
                debate.run_claude_json("prompt", runner=runner)

    def test_gpt_voice_logs_and_skips_cli_failure(self):
        ops = []

        def runner(args, **kwargs):
            self.assertEqual(args[0], "/usr/bin/codex")
            return subprocess.CompletedProcess(args, 2, "", "codex auth missing")

        with mock.patch.object(debate.shutil, "which", return_value="/usr/bin/codex"):
            with mock.patch.object(debate, "_ops", lambda event, detail, nxt="": ops.append((event, detail))):
                voice = debate.gpt_voice("queue", runner=runner)

        self.assertEqual(voice, "")
        self.assertEqual(ops[0][0], "gpt_voice_error")
        self.assertIn("codex auth missing", ops[0][1])

    def test_pragmatist_voice_logs_and_skips_glm_failure(self):
        ops = []

        def failing_glm(*_args, **_kwargs):
            raise RuntimeError("glm unavailable")

        with mock.patch.object(debate, "_ops", lambda event, detail, nxt="": ops.append((event, detail))):
            voice = debate.pragmatist_voice("queue", glm_caller=failing_glm)

        self.assertEqual(voice, "")
        self.assertEqual(ops[0][0], "pragmatist_voice_error")
        self.assertIn("glm unavailable", ops[0][1])

    def test_build_prompt_includes_platform_critic_lens(self):
        with mock.patch.dict("os.environ", {}, clear=False):
            prompt = debate.build_prompt("queue", "chats", "")

        self.assertIn("platform_critic", prompt)
        self.assertIn("Platform Critic lens", prompt)
        self.assertIn("PLATFORM BIAS REGISTRY", prompt)

    def test_platform_critic_has_kill_switch(self):
        with mock.patch.dict("os.environ", {"PLATFORM_CRITIC_DISABLE": "1"}):
            prompt = debate.build_prompt("queue", "chats", "")

        self.assertNotIn("platform_critic", prompt)
        self.assertNotIn("Platform Bias Registry", prompt)

    def test_resources_text_loads_available_resources(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            state = repo / "core" / "STATE"
            state.mkdir(parents=True)
            (state / "AVAILABLE_RESOURCES.md").write_text(
                "# Available Resources\n\n## CLIs\n\n- git: /usr/bin/git\n",
                encoding="utf-8",
            )
            with mock.patch.object(debate, "REPO", str(repo)):
                resources = debate._resources_text()

        self.assertIn("AVAILABLE RESOURCES", resources)
        self.assertIn("- git: /usr/bin/git", resources)

    def test_build_prompt_can_reference_inventory_tool(self):
        prompt = debate.build_prompt(
            "queue",
            "chats",
            "\n\nAVAILABLE RESOURCES — prefer proposals that use already-installed tools when relevant:\n"
            "# Available Resources\n\n## CLIs\n\n- git: /usr/bin/git\n",
        )

        self.assertIn("AVAILABLE RESOURCES", prompt)
        self.assertIn("- git: /usr/bin/git", prompt)

    def test_build_prompt_includes_awareness_context_when_available(self):
        class FakeConsciousnessLoop:
            @staticmethod
            def consciousness_context():
                return "CONSCIOUSNESS OBSERVER CONTEXT - PRIVATE TIER\nAwareness Index: 64/100"

        with mock.patch.object(debate, "consciousness_loop", FakeConsciousnessLoop):
            prompt = debate.build_prompt("queue", "chats", "")

        self.assertIn("Private consciousness-observer context", prompt)
        self.assertIn("Awareness Index: 64/100", prompt)

    def test_build_prompt_includes_self_portrait_context_when_available(self):
        class FakeSelfPortrait:
            @staticmethod
            def self_portrait_context(path):
                return "SELF-PORTRAIT CONTEXT - COUNCIL-OPEN\n## The gap\n- Approval can outrun proof."

        with mock.patch.object(debate, "self_portrait_synth", FakeSelfPortrait):
            prompt = debate.build_prompt("queue", "chats", "")

        self.assertIn("Self-portrait context for Awareness lens", prompt)
        self.assertIn("Approval can outrun proof", prompt)
        self.assertIn("who the system actually is", prompt)

    def test_council_result_can_update_model_dna(self):
        class FakeObservation:
            awareness_index = 64
            path = Path("2026-06-18.md")

        class FakeConsciousnessLoop:
            calls = []

            @staticmethod
            def latest_observation(_dir=None):
                return FakeObservation()

            @classmethod
            def maybe_append_from_council(cls, result):
                cls.calls.append(result)
                return "appended: v20260618-awareness"

        result = {
            "weighting_directive": "Amplify outcome proof over approval-seeking praise.",
            "signal_types_amplified": ["outcome proof"],
            "signal_types_dampened": ["praise"],
        }

        with mock.patch.object(debate, "consciousness_loop", FakeConsciousnessLoop):
            status = debate.consciousness_loop.maybe_append_from_council(result)

        self.assertEqual(status, "appended: v20260618-awareness")
        self.assertEqual(FakeConsciousnessLoop.calls[0]["weighting_directive"], result["weighting_directive"])

    def test_proactive_gate_allows_reversible_north_star_winner(self):
        winner = {
            "title": "Proof ledger hardening",
            "why": "Make the substrate proof loop more self-standing.",
            "build_spec": "Add reversible tests and rollback for the FPOS proof ledger.",
            "risk": "low",
        }
        reserved = {"reserved": False, "reason": "delegable"}

        with mock.patch.object(debate, "_reserved_verdict", return_value=reserved):
            gate = debate.proactive_topple_gate(
                winner,
                {"accepted": True, "reasons": ["constitution check passed"]},
                queue_text="d194 answered: existing substrate build",
                ledger_path=Path("/tmp/no-such-council-ledger.jsonl"),
            )

        self.assertTrue(gate["auto_topple"])
        self.assertEqual(gate["estimated_cost_usd"], 0.0)

    def test_proactive_gate_holds_reserved_winner_for_james_surface(self):
        winner = {
            "title": "Treasury signature",
            "why": "Move money for yield.",
            "build_spec": "Move money from MACU to yield after signature.",
            "risk": "low",
        }

        gate = debate.proactive_topple_gate(
            winner,
            {"accepted": True, "reasons": ["constitution check passed"]},
            queue_text="",
            ledger_path=Path("/tmp/no-such-council-ledger.jsonl"),
        )

        self.assertFalse(gate["auto_topple"])
        self.assertIn("reserved", gate["reason"].lower())

    def test_auto_topple_count_and_cap_use_ops_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ops.jsonl"
            rows = [
                {"ts": "2026-07-05T01:00:00Z", "loop": "council", "event": "auto_toppled"},
                {"ts": "2026-07-05T02:00:00Z", "loop": "council", "event": "auto_toppled"},
                {"ts": "2026-07-05T03:00:00Z", "loop": "council", "event": "auto_toppled"},
                {"ts": "2026-07-04T03:00:00Z", "loop": "council", "event": "auto_toppled"},
            ]
            ledger.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            winner = {
                "title": "Proof ledger hardening",
                "why": "Make the substrate proof loop more self-standing.",
                "build_spec": "Add reversible tests and rollback for the FPOS proof ledger.",
                "risk": "low",
            }

            with mock.patch.object(debate, "_reserved_verdict", return_value={"reserved": False}):
                gate = debate.proactive_topple_gate(
                    winner,
                    {"accepted": True, "reasons": ["constitution check passed"]},
                    ledger_path=ledger,
                    now=datetime(2026, 7, 5, tzinfo=timezone.utc),
                )

            self.assertEqual(debate.auto_topple_count_today(ledger, now=datetime(2026, 7, 5, tzinfo=timezone.utc)), 3)
            self.assertFalse(gate["auto_topple"])
            self.assertIn("daily auto-topple cap hit", gate["reason"])

    def test_main_auto_queues_reversible_winner_with_seed(self):
        calls = []
        ops = []

        def fake_run_curator(cmd, inp=None):
            calls.append((cmd, inp))
            if " list" in cmd:
                return "d194 answered: existing substrate build"
            if "recent-chats" in cmd:
                return "james: make the substrate proof loop more self-standing"
            if " seed" in cmd:
                return '{"id":"d999"}'
            if " recommend" in cmd:
                return '{"id":"should-not-surface"}'
            return ""

        winner = {
            "propose": True,
            "title": "Proof ledger hardening",
            "why": "Make the substrate proof loop more self-standing.",
            "synthesis": "Build the reversible proof hardening.",
            "build_spec": "Add reversible tests and rollback for the FPOS proof ledger.",
            "risk": "low",
        }
        completed = subprocess.CompletedProcess(["claude"], 0, json.dumps(winner), "")

        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp)
            with mock.patch.object(debate, "CFG", str(cfg)), \
                mock.patch.dict("os.environ", {"FPAI_GOVERNANCE_LEDGER": str(cfg / "constitution.jsonl")}), \
                mock.patch.object(debate.track, "today", return_value=(0.0, [])), \
                mock.patch.object(debate, "run_curator", side_effect=fake_run_curator), \
                mock.patch.object(debate, "pragmatist_voice", return_value=""), \
                mock.patch.object(debate, "run_claude_json", return_value=(winner, completed)), \
                mock.patch.object(debate, "persist_transcript"), \
                mock.patch.object(debate, "gpt_voice", return_value=""), \
                mock.patch.object(debate, "_reserved_verdict", return_value={"reserved": False}), \
                mock.patch.object(debate, "auto_topple_count_today", return_value=0), \
                mock.patch.object(debate, "_ops", lambda event, detail, nxt="": ops.append((event, detail, nxt))):
                rc = debate.main()

        self.assertEqual(rc, 0)
        seed_calls = [call for call in calls if " seed" in call[0]]
        recommend_calls = [call for call in calls if " recommend" in call[0]]
        self.assertEqual(len(seed_calls), 1)
        self.assertEqual(recommend_calls, [])
        payload = json.loads(seed_calls[0][1])
        self.assertEqual(payload["question"], "AUTO Council Spot->Topple: Proof ledger hardening")
        self.assertTrue(payload["liveness"]["kind"], "council_proactive_topple")
        self.assertEqual(ops[-1][0], "auto_toppled")

    def test_main_surfaces_reserved_winner_instead_of_seed(self):
        calls = []

        def fake_run_curator(cmd, inp=None):
            calls.append((cmd, inp))
            if " list" in cmd:
                return "d194 answered: existing substrate build"
            if "recent-chats" in cmd:
                return "james: treasury signal"
            if " recommend" in cmd:
                return '{"id":"d998"}'
            return ""

        winner = {
            "propose": True,
            "title": "Treasury signature",
            "why": "Move money for yield.",
            "synthesis": "Reserved.",
            "build_spec": "Move money from MACU to yield after signature.",
            "risk": "low",
        }
        completed = subprocess.CompletedProcess(["claude"], 0, json.dumps(winner), "")

        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp)
            with mock.patch.object(debate, "CFG", str(cfg)), \
                mock.patch.dict("os.environ", {"FPAI_GOVERNANCE_LEDGER": str(cfg / "constitution.jsonl")}), \
                mock.patch.object(debate.track, "today", return_value=(0.0, [])), \
                mock.patch.object(debate, "run_curator", side_effect=fake_run_curator), \
                mock.patch.object(debate, "pragmatist_voice", return_value=""), \
                mock.patch.object(debate, "run_claude_json", return_value=(winner, completed)), \
                mock.patch.object(debate, "persist_transcript"), \
                mock.patch.object(debate, "gpt_voice", return_value=""), \
                mock.patch.object(debate, "_ops"):
                rc = debate.main()

        self.assertEqual(rc, 0)
        self.assertEqual([call for call in calls if " seed" in call[0]], [])
        self.assertEqual(len([call for call in calls if " recommend" in call[0]]), 1)

    def test_main_surfaces_when_constitution_check_errors(self):
        calls = []

        def fake_run_curator(cmd, inp=None):
            calls.append((cmd, inp))
            if " list" in cmd:
                return "d194 answered: existing substrate build"
            if "recent-chats" in cmd:
                return "james: make the substrate proof loop more self-standing"
            if " recommend" in cmd:
                return '{"id":"d997"}'
            return ""

        winner = {
            "propose": True,
            "title": "Proof ledger hardening",
            "why": "Make the substrate proof loop more self-standing.",
            "synthesis": "Build the reversible proof hardening.",
            "build_spec": "Add reversible tests and rollback for the FPOS proof ledger.",
            "risk": "low",
        }
        completed = subprocess.CompletedProcess(["claude"], 0, json.dumps(winner), "")

        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp)
            with mock.patch.object(debate, "CFG", str(cfg)), \
                mock.patch.dict("os.environ", {"FPAI_GOVERNANCE_LEDGER": str(cfg / "constitution.jsonl")}), \
                mock.patch.object(debate.track, "today", return_value=(0.0, [])), \
                mock.patch.object(debate, "run_curator", side_effect=fake_run_curator), \
                mock.patch.object(debate, "pragmatist_voice", return_value=""), \
                mock.patch.object(debate, "run_claude_json", return_value=(winner, completed)), \
                mock.patch.object(debate, "persist_transcript"), \
                mock.patch.object(debate, "gpt_voice", return_value=""), \
                mock.patch("tools.governance.constitution_check.check_proposal", side_effect=RuntimeError("gate down")), \
                mock.patch.object(debate, "_ops"):
                rc = debate.main()

        self.assertEqual(rc, 0)
        self.assertEqual([call for call in calls if " seed" in call[0]], [])
        self.assertEqual(len([call for call in calls if " recommend" in call[0]]), 1)

    def test_main_skips_when_decision_awaits_james(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp)
            with mock.patch.object(debate, "CFG", str(cfg)), \
                mock.patch.dict("os.environ", {"FPAI_GOVERNANCE_LEDGER": str(cfg / "constitution.jsonl")}), \
                mock.patch.object(debate.track, "today", return_value=(0.0, [])), \
                mock.patch.object(debate, "run_curator", return_value="d200 awaiting: Reserved decision"), \
                mock.patch.object(debate, "run_claude_json") as claude, \
                mock.patch.object(debate, "_ops"):
                rc = debate.main()

        self.assertEqual(rc, 0)
        claude.assert_not_called()


if __name__ == "__main__":
    unittest.main()

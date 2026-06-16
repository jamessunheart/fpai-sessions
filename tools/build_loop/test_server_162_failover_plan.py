#!/usr/bin/env python3
"""Regression checks for the server 162 redundancy/failover plan."""
from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = REPO_ROOT / "docs" / "codex" / "SERVER_162_REDUNDANCY_FAILOVER.md"


class Server162FailoverPlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = PLAN_PATH.read_text(encoding="utf-8")

    def test_required_sections_are_present(self) -> None:
        required = (
            "# Server 162 Redundancy And Failover Plan",
            "## Evidence Scope",
            "## Dependency Map",
            "## Hardcoded IP Inventory",
            "## Recovery Objectives",
            "## Redundancy Design",
            "## If 162 Goes Down",
            "### Phase 0 - Confirm And Freeze",
            "### Phase 1 - Select Replacement Host",
            "### Phase 2 - Restore Data",
            "### Phase 3 - Repoint Aliases",
            "### Phase 4 - Redeploy Services",
            "### Phase 5 - Proof",
            "## Pre-Failover Work Queue",
            "## Rollback",
            "## Open Gaps",
            "## Intent Proof",
        )
        for needle in required:
            with self.subTest(needle=needle):
                self.assertIn(needle, self.text)

    def test_dependency_map_covers_critical_server_162_surfaces(self) -> None:
        critical_terms = (
            "sh-brain",
            "AppFlowy",
            "STreasury",
            "Outbounders",
            "Ollama",
            "n8n",
            "Paperless",
            "Firefly",
            "Tailscale",
            "core/BUILD/cron",
        )
        for term in critical_terms:
            with self.subTest(term=term):
                self.assertIn(term, self.text)

    def test_hardcoded_ip_table_names_active_call_sites(self) -> None:
        expected_paths = (
            "SERVICES/ad-portal/app/config.py",
            "SERVICES/ad-portal/docker-compose.yml",
            "SERVICES/consciousness_optimizer/app/optimizer.py",
            "SERVICES/fp-index/app/signal_router.py",
            "SERVICES/concierge/shared/config.py",
            "SERVICES/zend-wallet/app/config.py",
            "SERVICES/aria-command/sovereign/agents/monitor.py",
            "SERVICES/aria-command/sovereign/workflows/actions.py",
            "SERVICES/god-autonomous-revenue/main.py",
            "SERVICES/aria-command/integrations/n8n_client.py",
            "SERVICES/aria-command/agents/registry.py",
            "SERVICES/legal-critic/deploy.sh",
            "tools/council/debate.py",
            "tools/decisions/bridge_to_codex.sh",
            "tools/decisions/feed_decision.sh",
            "tools/decisions/mirror_pull.py",
            "tools/decisions/scene_pull.py",
            "tools/merge/process_merge_requests.sh",
            "tools/memory/tg_brain_bridge.sh",
        )
        for raw_path in expected_paths:
            with self.subTest(path=raw_path):
                self.assertIn(raw_path, self.text)
                self.assertTrue((REPO_ROOT / raw_path).exists(), f"missing path: {raw_path}")

        hardcoded_rows = [
            line
            for line in self.text.splitlines()
            if line.startswith("| `") and "162.0.208.88" in line
        ]
        self.assertGreaterEqual(len(hardcoded_rows), 20)

    def test_plan_keeps_approval_gates_and_forbidden_actions_explicit(self) -> None:
        gate_terms = (
            "does not authorize SSH",
            "DNS changes",
            "deploys",
            "service stops",
            "money movement",
            "secret handling",
            "Do not rotate secrets",
            "James/Ember explicitly approves",
        )
        for term in gate_terms:
            with self.subTest(term=term):
                self.assertIn(term, self.text)

    def test_redeploy_steps_are_ordered_before_proof(self) -> None:
        phase_order = [
            "### Phase 0 - Confirm And Freeze",
            "### Phase 1 - Select Replacement Host",
            "### Phase 2 - Restore Data",
            "### Phase 3 - Repoint Aliases",
            "### Phase 4 - Redeploy Services",
            "### Phase 5 - Proof",
        ]
        offsets = [self.text.index(phase) for phase in phase_order]
        self.assertEqual(offsets, sorted(offsets))

    def test_remaining_direct_ip_policy_is_testable(self) -> None:
        proof_line = "remaining hits are either historical docs, this"
        self.assertIn(proof_line, self.text)
        self.assertRegex(self.text, re.escape("rg '162\\\\.0\\\\.208\\\\.88'"))


if __name__ == "__main__":
    unittest.main()

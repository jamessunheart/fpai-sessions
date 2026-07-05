from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("live_system_status.py")
SPEC = importlib.util.spec_from_file_location("live_system_status", MODULE_PATH)
assert SPEC and SPEC.loader
live_system_status = importlib.util.module_from_spec(SPEC)
sys.modules["live_system_status"] = live_system_status
SPEC.loader.exec_module(live_system_status)


class LiveSystemStatusTest(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fpai-live-status-"))
        (root / "core" / "BUILD" / "specs").mkdir(parents=True)
        (root / "core" / "BUILD" / "results").mkdir(parents=True)
        (root / "core" / "BUILD" / "reviews").mkdir(parents=True)
        (root / "core" / "BUILD" / "specs" / "SPEC_pending.md").write_text("# pending\n", encoding="utf-8")
        (root / "core" / "BUILD" / "specs" / "SPEC_done.md").write_text("# done\n", encoding="utf-8")
        (root / "core" / "BUILD" / "results" / "SPEC_done.result.md").write_text("done\n", encoding="utf-8")
        (root / "core" / "BUILD" / "REGISTRY.json").write_text(
            json.dumps(
                {
                    "active_builds": [
                        {
                            "id": "SPEC_live",
                            "slug": "SPEC_live",
                            "branch": "build/SPEC_live",
                            "status": "building",
                        },
                        {
                            "id": "SPEC_merged",
                            "slug": "SPEC_merged",
                            "branch": "build/SPEC_merged",
                            "status": "merged",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        return root

    def test_collect_status_reports_queue_merge_and_health(self) -> None:
        root = self.make_repo()
        ops = root / "ops.jsonl"
        ops.write_text(
            "\n".join(
                [
                    json.dumps({"loop": "build", "event": "ran", "detail": "tick"}),
                    json.dumps({"loop": "merge", "event": "failed", "detail": "conflict"}),
                    json.dumps(
                        {
                            "loop": "liveness",
                            "event": "liveness:partial",
                            "liveness_status": "partial",
                            "spec_id": "SPEC_partial",
                            "detail": "SPEC_partial partial",
                        }
                    ),
                ]
            ),
            encoding="utf-8",
        )

        with patch.dict("os.environ", {"FPAI_SERVER_ID": "162"}):
            snapshot = live_system_status.collect_status(root, ops_ledger=ops)

        lines = "\n".join(snapshot.lines())
        self.assertIn("pending_specs=1", lines)
        self.assertIn("SPEC_live:building", lines)
        self.assertIn("Last merge outcome: merged", lines)
        self.assertIn("SPEC_merged", lines)
        self.assertIn("host=162", lines)
        self.assertIn("recent_failures=1", lines)
        self.assertIn("conflict", lines)
        self.assertIn("Liveness: running=0", lines)
        self.assertIn("partial=1", lines)
        self.assertIn("SPEC_partial", lines)

    def test_activation_audit_summary_surfaces_unexplained_inert(self) -> None:
        root = self.make_repo()
        (root / "core" / "BUILD" / "REGISTRY.json").write_text(
            json.dumps(
                {
                    "active_builds": [
                        {
                            "id": "SPEC_d099_unused",
                            "slug": "SPEC_d099_unused",
                            "branch": "build/SPEC_d099_unused",
                            "status": "merged",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (root / "core" / "BUILD" / "activate").mkdir(exist_ok=True)
        (root / "tools" / "build_loop").mkdir(parents=True)
        source = Path(__file__).resolve().parents[3] / "tools" / "build_loop" / "activation_audit.py"
        (root / "tools" / "build_loop" / "activation_audit.py").write_text(
            source.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        line = live_system_status._activation_audit_summary(root, root / "ops.jsonl")

        self.assertIn("unexplained_inert=1", line)
        self.assertIn("SPEC_d099_unused", line)

    def test_review_fallback_when_registry_has_no_merge(self) -> None:
        root = self.make_repo()
        (root / "core" / "BUILD" / "REGISTRY.json").write_text(
            json.dumps({"active_builds": []}),
            encoding="utf-8",
        )
        review = root / "core" / "BUILD" / "reviews" / "build-SPEC_x.md"
        review.write_text("**Verdict:** APPROVE · **Risk:** low\n", encoding="utf-8")

        snapshot = live_system_status.collect_status(root, ops_ledger=root / "missing.jsonl")

        self.assertIn("review=Verdict: APPROVE", "\n".join(snapshot.last_merge))

    def test_render_status_lines_is_bounded(self) -> None:
        snapshot = live_system_status.StatusSnapshot(
            queue=["q1", "q2"],
            last_merge=["m1"],
            health=["h1", "h2", "h3"],
        )

        self.assertEqual(live_system_status.render_status_lines(snapshot, max_items=3), ["q1", "q2", "m1"])


if __name__ == "__main__":
    unittest.main()

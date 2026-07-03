from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.build_loop import live_artifact_proof as proof


class LiveArtifactProofTest(unittest.TestCase):
    def test_classifies_live_artifact_paths(self) -> None:
        artifacts = proof.classify_live_artifacts(
            [
                "README.md",
                "core/BUILD/cron/fpai-public-bot.service",
                "core/BUILD/activate/SPEC_d010.sh",
                "tools/build_loop/server_build_loop.sh",
                "SERVICES/sunheart-brain/curator/tgbot.py",
            ]
        )

        self.assertEqual(
            artifacts,
            [
                {"type": "systemd", "path": "core/BUILD/cron/fpai-public-bot.service"},
                {"type": "activation", "path": "core/BUILD/activate/SPEC_d010.sh"},
                {"type": "deployed_file", "path": "tools/build_loop/server_build_loop.sh"},
                {"type": "service_import", "path": "SERVICES/sunheart-brain/curator/tgbot.py"},
            ],
        )

    def test_emit_proof_writes_liveness_path_and_metric_outcome(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fpai-live-proof-") as tmp:
            root = Path(tmp)
            ledger = root / "ops.jsonl"
            self._git(root, "init")
            self._git(root, "config", "user.email", "test@example.com")
            self._git(root, "config", "user.name", "Test")
            (root / "tools/build_loop").mkdir(parents=True)
            (root / "tools/build_loop/server_build_loop.sh").write_text("# base\n", encoding="utf-8")
            self._git(root, "add", ".")
            self._git(root, "commit", "-m", "base")
            base = self._git(root, "rev-parse", "HEAD")

            (root / "tools/build_loop/server_build_loop.sh").write_text("# live change\n", encoding="utf-8")
            self._git(root, "add", ".")
            self._git(root, "commit", "-m", "live")
            head = self._git(root, "rev-parse", "HEAD")

            result = proof.emit_proof(
                repo_root=root,
                ops_ledger=ledger,
                spec_id="SPEC_d144",
                decision_id="d144",
                branch="build/SPEC_d144",
                base_ref=base,
                head_ref=head,
                proof_expected="dead_rate drops below 0.5 and feature_outcome verdict=improved",
            )

            rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(result["liveness_rows"], 1)
        self.assertEqual(rows[0]["event"], "liveness:pass")
        self.assertEqual(rows[0]["artifact"], "tools/build_loop/server_build_loop.sh")
        self.assertEqual(rows[0]["liveness_status"], "live")
        self.assertEqual(rows[1]["event"], "feature_outcome")
        self.assertEqual(rows[1]["verdict"], "improved")
        self.assertEqual(rows[1]["spec_id"], "SPEC_d144")

    def test_non_metric_live_artifact_only_writes_liveness(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fpai-live-proof-") as tmp:
            root = Path(tmp)
            ledger = root / "ops.jsonl"
            self._git(root, "init")
            self._git(root, "config", "user.email", "test@example.com")
            self._git(root, "config", "user.name", "Test")
            (root / "core/BUILD/cron").mkdir(parents=True)
            (root / "core/BUILD/cron/example.timer").write_text("[Timer]\n", encoding="utf-8")
            self._git(root, "add", ".")
            self._git(root, "commit", "-m", "base")
            base = self._git(root, "rev-parse", "HEAD")
            (root / "core/BUILD/cron/example.timer").write_text("[Timer]\nOnCalendar=daily\n", encoding="utf-8")
            self._git(root, "add", ".")
            self._git(root, "commit", "-m", "timer")
            head = self._git(root, "rev-parse", "HEAD")

            proof.emit_proof(
                repo_root=root,
                ops_ledger=ledger,
                spec_id="SPEC_timer",
                decision_id="d001",
                branch="build/SPEC_timer",
                base_ref=base,
                head_ref=head,
                proof_expected="timer exists",
            )

            rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([row["event"] for row in rows], ["liveness:pass"])
        self.assertEqual(rows[0]["artifact"], "core/BUILD/cron/example.timer")

    def _git(self, root: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip()


if __name__ == "__main__":
    unittest.main()

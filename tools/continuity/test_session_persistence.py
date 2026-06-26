from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("session_persistence.py")
SPEC = importlib.util.spec_from_file_location("session_persistence", MODULE_PATH)
assert SPEC and SPEC.loader
session_persistence = importlib.util.module_from_spec(SPEC)
sys.modules["session_persistence"] = session_persistence
SPEC.loader.exec_module(session_persistence)


class SessionPersistenceTest(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fpai-session-persistence-"))
        (root / "core" / "BUILD" / "results").mkdir(parents=True)
        (root / "core" / "BUILD" / "REGISTRY.json").write_text(
            json.dumps(
                {
                    "active_builds": [
                        {
                            "id": "SPEC_done",
                            "slug": "SPEC_done",
                            "branch": "build/SPEC_done",
                            "status": "done",
                            "tests_passed": True,
                            "notes": "complete",
                        },
                        {
                            "id": "SPEC_building",
                            "slug": "SPEC_building",
                            "branch": "build/SPEC_building",
                            "status": "building",
                            "tests_passed": False,
                            "spec": "core/BUILD/specs/SPEC_building.md",
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
        (root / "core" / "BUILD" / "results" / "SPEC_done.result.md").write_text("done", encoding="utf-8")
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
        (root / "tracked.txt").write_text("before\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "build/SPEC_building"], cwd=root, check=True, capture_output=True)
        (root / "tracked.txt").write_text("after\n", encoding="utf-8")
        (root / "untracked.txt").write_text("new\n", encoding="utf-8")
        return root

    def test_snapshot_captures_active_builds_and_changed_files(self) -> None:
        repo = self.make_repo()

        snapshot = session_persistence.build_snapshot(
            repo_root=repo,
            session_id="session-1",
            surface="codex",
            progress_note="Implemented first pass.",
        )

        self.assertEqual(snapshot.session_id, "session-1")
        self.assertEqual(snapshot.branch, "build/SPEC_building")
        self.assertEqual(snapshot.active_builds[0].id, "SPEC_building")
        self.assertEqual(snapshot.active_builds[0].status, "building")
        self.assertNotIn("SPEC_merged", [item.id for item in snapshot.active_builds])
        self.assertIn("tracked.txt", snapshot.changed_files)
        self.assertIn("untracked.txt", snapshot.changed_files)
        self.assertIn("SPEC_done.result.md", snapshot.recent_results)

    def test_save_load_round_trip_and_render(self) -> None:
        repo = self.make_repo()
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = session_persistence.build_snapshot(
                repo_root=repo,
                session_id="session:two",
                surface="phone",
                changed_files=["a.py", "b.py"],
                progress_note="Need to run tests next.",
            )
            latest = session_persistence.save_snapshot(snapshot, state_dir=Path(tmp))
            loaded = session_persistence.load_latest(state_dir=Path(tmp))

            self.assertEqual(latest.name, "latest.json")
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.session_id, "session:two")
            rendered = session_persistence.render_snapshot(loaded, max_chars=700)
            self.assertIn("Persisted session progress", rendered)
            self.assertIn("Need to run tests next", rendered)
            self.assertIn("SPEC_building", rendered)

    def test_invalid_latest_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            state_dir.mkdir(exist_ok=True)
            (state_dir / "latest.json").write_text('{"schema":"wrong"}', encoding="utf-8")

            self.assertIsNone(session_persistence.load_latest(state_dir=state_dir))


if __name__ == "__main__":
    unittest.main()

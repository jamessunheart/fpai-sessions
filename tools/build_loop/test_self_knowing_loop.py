from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CURATOR_ROOT = REPO_ROOT / "SERVICES" / "sunheart-brain"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(CURATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(CURATOR_ROOT))

from curator import decisions
from tools.db import migrate_add_canary


class FakeCursor:
    def __init__(self, conn: "FakeConn") -> None:
        self.conn = conn
        self.sql = ""
        self.params = None

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(self, sql: str, params=None) -> None:
        self.sql = sql
        self.params = params
        self.conn.executed.append((sql, params))

    def fetchall(self):
        return []


class FakeConn:
    def __init__(self) -> None:
        self.executed: list[tuple[str, object]] = []
        self.commits = 0

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def commit(self) -> None:
        self.commits += 1


class SelfKnowingLoopTest(unittest.TestCase):
    def root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-d027-"))

    def test_loop_run_event_written_after_dry_run(self) -> None:
        root = self.root()
        home = root / "home"
        fakebin = root / "bin"
        repo = home / "FPAI_Cockpit"
        specs = repo / "core" / "BUILD" / "specs"
        home.mkdir()
        fakebin.mkdir()
        specs.mkdir(parents=True)
        (repo / "tools").symlink_to(REPO_ROOT / "tools")
        ledger = root / "ops_ledger.jsonl"
        self._write_executable(
            fakebin / "ssh",
            """#!/usr/bin/env bash
case "$*" in
  *pending-builds*) printf '%s\\n' '{"id":"d123","question":"Build the probe","answer":"yes","build_spec":"touch proof","proof_expected":"ledger"}' ;;
  *) exit 0 ;;
esac
""",
        )

        env = {
            **os.environ,
            "HOME": str(home),
            "PATH": f"{fakebin}:{os.environ['PATH']}",
            "OPS_LEDGER": str(ledger),
        }
        result = subprocess.run(
            ["bash", str(REPO_ROOT / "tools" / "decisions" / "bridge_to_codex.sh"), "--dry-run"],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(rows[-1]["event"], "loop_run")
        self.assertEqual(rows[-1]["found"], 1)
        self.assertEqual(rows[-1]["built"], 0)
        self.assertEqual(rows[-1]["skipped"], 1)
        self.assertEqual(rows[-1]["reason"], "disabled")
        self.assertTrue((specs / "SPEC_d123_build-the-probe.md").exists())

    def test_rate_monitor_fires_with_pending_and_stale_success(self) -> None:
        root = self.root()
        fakebin = root / "bin"
        py = root / "py"
        ledger = root / "ops_ledger.jsonl"
        fakebin.mkdir()
        py.mkdir()
        ledger.write_text(
            json.dumps({
                "ts": "2026-06-16T00:00:00Z",
                "loop": "build_loop",
                "event": "loop_run",
                "built": 1,
            }) + "\n",
            encoding="utf-8",
        )
        self._write_health_stubs(fakebin)
        (py / "psycopg.py").write_text(
            textwrap.dedent(
                """
                class Cursor:
                    def __init__(self, conn):
                        self.sql = ""
                    def __enter__(self):
                        return self
                    def __exit__(self, *args):
                        return None
                    def execute(self, sql, params=()):
                        self.sql = sql
                    def fetchone(self):
                        if "EXISTS" in self.sql:
                            return (True,)
                        return (1,)
                    def fetchall(self):
                        return [("d123", "Build pending", "yes", "spec", "proof")]
                class Conn:
                    def __enter__(self):
                        return self
                    def __exit__(self, *args):
                        return None
                    def cursor(self):
                        return Cursor(self)
                def connect(*args, **kwargs):
                    return Conn()
                """
            ),
            encoding="utf-8",
        )
        env = {
            **os.environ,
            "PATH": f"{fakebin}:{os.environ['PATH']}",
            "PYTHONPATH": f"{py}:{CURATOR_ROOT}:{REPO_ROOT}",
            "BRAIN_INDEX_DB_URL": "postgres://example",
            "OPS_LEDGER": str(ledger),
            "OPS_LOG_SCRIPT": str(REPO_ROOT / "tools" / "build_loop" / "ops_log.py"),
            "FPAI_REPO_ROOT": str(REPO_ROOT),
        }

        result = subprocess.run(
            ["bash", str(REPO_ROOT / "tools" / "build_loop" / "health_check.sh")],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("FAIL: build loop has 1 decisions pending but no successful build in", result.stdout)

    def test_canary_row_never_appears_in_pending_builds_output(self) -> None:
        rows = [
            {
                "id": "d000",
                "status": "answered",
                "needs_build": True,
                "spec_written": False,
                "is_canary": True,
            },
            {
                "id": "d123",
                "status": "answered",
                "needs_build": True,
                "spec_written": False,
                "is_canary": False,
            },
        ]

        pending = decisions.pending_builds_from_rows(rows)

        self.assertEqual([row["id"] for row in pending], ["d123"])
        # Canary exclusion is guaranteed at the Python layer (pending_builds_from_rows, asserted
        # above) — NOT in SQL. The is_canary column was never migrated into brain_index.decisions,
        # so referencing it in the query raised UndefinedColumn and crashed live (2026-07-05).
        # Guard against reintroducing the crash-causing column reference.
        self.assertNotIn("is_canary", decisions.PENDING_BUILDS_SQL)

    def test_migration_is_idempotent(self) -> None:
        conn = FakeConn()

        first = migrate_add_canary.migrate(conn)
        second = migrate_add_canary.migrate(conn)

        self.assertTrue(first.seeded)
        self.assertTrue(second.seeded)
        sql = "\n".join(item[0] for item in conn.executed)
        self.assertIn("ADD COLUMN IF NOT EXISTS is_canary", sql)
        self.assertEqual(sql.count("ON CONFLICT (id) DO UPDATE"), 2)
        self.assertEqual(conn.commits, 2)

    def _write_health_stubs(self, fakebin: Path) -> None:
        self._write_executable(fakebin / "grep", """#!/usr/bin/env bash
case "$*" in
  *sk-ant-oat*) echo sk-ant-oat-test; exit 0 ;;
  *invalid\\ bearer*|*unauthor*|*401*) exit 1 ;;
esac
exit 1
""")
        self._write_executable(fakebin / "journalctl", "#!/usr/bin/env bash\nexit 0\n")
        self._write_executable(fakebin / "codex", "#!/usr/bin/env bash\necho codex-test\n")
        self._write_executable(fakebin / "systemctl", "#!/usr/bin/env bash\n[ \"$1\" = is-active ] && echo active || true\n")
        self._write_executable(fakebin / "find", "#!/usr/bin/env bash\nexit 0\n")
        self._write_executable(fakebin / "df", "#!/usr/bin/env bash\nprintf 'Filesystem 1K-blocks Used Available Use% Mounted on\\n/dev/root 100 10 90 10% /\\n'\n")

    def _write_executable(self, path: Path, text: str) -> None:
        path.write_text(text, encoding="utf-8")
        path.chmod(0o755)


if __name__ == "__main__":
    unittest.main()

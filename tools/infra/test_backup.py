import gzip
import json
import os
import stat
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from tools.infra import backup_status


ROOT = Path(__file__).resolve().parents[2]
BACKUP = ROOT / "tools" / "infra" / "backup_brain.sh"
VERIFY = ROOT / "tools" / "infra" / "verify_backup.sh"
HEALTH = ROOT / "tools" / "build_loop" / "health_check.sh"


def write_exe(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class BackupScriptsTest(unittest.TestCase):
    def make_env(self, tmp: str) -> dict[str, str]:
        root = Path(tmp)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        write_exe(bin_dir / "pg_dump", "#!/usr/bin/env bash\nprintf 'PGDMP fake archive from test db\\n'\n")
        write_exe(bin_dir / "pg_restore", "#!/usr/bin/env bash\ncat >/dev/null\nexit 0\n")
        write_exe(bin_dir / "scp", "#!/usr/bin/env bash\ncp \"$1\" \"${2#*:}\"\n")
        write_exe(bin_dir / "rclone", "#!/usr/bin/env bash\ncp \"$2\" \"$3\"\n")
        write_exe(bin_dir / "codex", "#!/usr/bin/env bash\nexit 0\n")
        write_exe(bin_dir / "systemctl", "#!/usr/bin/env bash\nprintf 'active\\n'\n")
        write_exe(bin_dir / "journalctl", "#!/usr/bin/env bash\nexit 0\n")
        notify = root / "notify.sh"
        write_exe(notify, "#!/usr/bin/env bash\nprintf '%s\\n' \"$1\" >> \"$NOTIFY_LOG\"\n")
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{bin_dir}:{env.get('PATH', '')}",
                "BACKUP_DIR": str(root / "backups"),
                "OPS_LEDGER": str(root / "ops.jsonl"),
                "NOTIFY": str(notify),
                "NOTIFY_LOG": str(root / "notify.log"),
                "BACKUP_MIN_BYTES": "1",
                "HOME": str(root / "home"),
                "PGDATABASE": "brain_index_test",
            }
        )
        return env

    def test_backup_produces_gz_and_logs_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp)
            result = subprocess.run([str(BACKUP)], env=env, cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            files = list(Path(env["BACKUP_DIR"]).glob("brain_*.sql.gz"))
            self.assertEqual(len(files), 1)
            with gzip.open(files[0], "rt", encoding="utf-8") as handle:
                self.assertIn("fake archive", handle.read())
            rows = read_jsonl(Path(env["OPS_LEDGER"]))
            self.assertTrue(any(row.get("event") == "backup_complete" for row in rows))

    def test_backup_logs_failure_and_alerts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp)
            write_exe(Path(tmp) / "bin" / "pg_dump", "#!/usr/bin/env bash\nexit 42\n")
            result = subprocess.run([str(BACKUP)], env=env, cwd=ROOT, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            rows = read_jsonl(Path(env["OPS_LEDGER"]))
            self.assertTrue(any(row.get("event") == "backup_failed" for row in rows))
            self.assertIn("backup failed", Path(env["NOTIFY_LOG"]).read_text(encoding="utf-8"))

    def test_prunes_old_backups_to_seven(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp)
            backup_dir = Path(env["BACKUP_DIR"])
            backup_dir.mkdir()
            for i in range(8):
                path = backup_dir / f"brain_2026-06-{i+1:02d}_00-00.sql.gz"
                path.write_bytes(gzip.compress(f"old {i}".encode()))
                old_time = time.time() - (10 - i) * 3600
                os.utime(path, (old_time, old_time))
            result = subprocess.run([str(BACKUP)], env=env, cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(len(list(backup_dir.glob("brain_*.sql.gz"))), 7)

    def test_verify_passes_valid_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp)
            backup_dir = Path(env["BACKUP_DIR"])
            backup_dir.mkdir()
            path = backup_dir / "brain_2026-06-16_03-00.sql.gz"
            path.write_bytes(gzip.compress(b"PGDMP fake archive"))
            result = subprocess.run([str(VERIFY)], env=env, cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            rows = read_jsonl(Path(env["OPS_LEDGER"]))
            self.assertTrue(any(row.get("event") == "backup_verified" and row.get("valid") is True for row in rows))

    def test_verify_fails_empty_or_missing_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp)
            result = subprocess.run([str(VERIFY)], env=env, cwd=ROOT, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            backup_dir = Path(env["BACKUP_DIR"])
            backup_dir.mkdir(exist_ok=True)
            (backup_dir / "brain_2026-06-16_03-00.sql.gz").write_bytes(b"")
            result = subprocess.run([str(VERIFY)], env=env, cwd=ROOT, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)

    def test_health_check_flags_stale_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = self.make_env(tmp)
            backup_dir = Path(env["BACKUP_DIR"])
            backup_dir.mkdir()
            path = backup_dir / "brain_2026-06-15_00-00.sql.gz"
            path.write_bytes(gzip.compress(b"PGDMP fake archive"))
            old_time = time.time() - 27 * 3600
            os.utime(path, (old_time, old_time))
            result = subprocess.run(["bash", str(HEALTH)], env=env, cwd=ROOT, text=True, capture_output=True)
            self.assertIn("brain backup missing or stale", result.stdout)

    def test_backup_status_uses_red_green_yellow_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ops.jsonl"
            now = "2026-06-16T10:00:00Z"
            ledger.write_text(
                json.dumps({"ts": now, "event": "backup_complete", "offsite": False, "path": "/x"}) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(backup_status.backup_status(ledger)["icon"], "yellow")
            ledger.write_text(
                json.dumps({"ts": now, "event": "backup_complete", "offsite": True, "path": "/x"}) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(backup_status.backup_status(ledger)["icon"], "green")
            with ledger.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"ts": now, "event": "backup_failed", "detail": "boom"}) + "\n")
            self.assertEqual(backup_status.backup_status(ledger)["icon"], "red")


if __name__ == "__main__":
    unittest.main()

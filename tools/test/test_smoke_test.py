from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from tools.test import smoke_test, spec_checker, update_expected_outputs


class FakeCursor:
    def __init__(self, db: "FakeDB"):
        self.db = db
        self.result = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=()):
        normalized = " ".join(sql.split()).lower()
        if "insert into brain_index.decisions" in normalized:
            self.db.canaries.append({"id": "d999", "status": "awaiting", "created_at": self.db.now})
            self.result = ("d999", "awaiting", self.db.now)
        elif "from brain_index.decisions" in normalized and "where id =" in normalized:
            self.result = ("d999", "awaiting", self.db.now) if self.db.canaries else None
        elif normalized.startswith("delete from brain_index.decisions"):
            self.db.canaries.clear()
            self.result = None
        elif "from brain_index.tg_messages" in normalized:
            self.result = (1,)
        elif "coalesce(needs_build" in normalized and "not in ('built', 'merged')" in normalized:
            self.result = (0,)
        elif "status = 'answered'" in normalized and "needs_build" in normalized:
            self.result = [("d035",), ("d049",)]
        else:
            self.result = (0,)

    def fetchone(self):
        return self.result

    def fetchall(self):
        return self.result if isinstance(self.result, list) else []


class FakeDB:
    def __init__(self):
        self.now = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)
        self.canaries = []
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def close(self):
        self.closed = True


class SmokeTestCase(unittest.TestCase):
    def make_context(self, tmp: str, db: FakeDB | None = None, *, telegram=True):
        root = Path(tmp)
        (root / "tools" / "build_loop").mkdir(parents=True)
        (root / "core" / "BUILD").mkdir(parents=True)
        (root / "docs" / "policy").mkdir(parents=True)
        (root / "tools" / "test").mkdir(parents=True)
        (root / "docs" / "policy" / "CORA_POLICY_v0.2.md").write_text("policy\n", encoding="utf-8")
        (root / "tools" / "test" / "smoke_test.py").write_text("smoke\n", encoding="utf-8")
        (root / "tools" / "test" / "expected_outputs.json").write_text(
            json.dumps({"d035": ["docs/policy/CORA_POLICY_v0.2.md"], "d049": ["tools/test/smoke_test.py"]}),
            encoding="utf-8",
        )
        (root / "core" / "BUILD" / "REGISTRY.json").write_text(
            json.dumps({"active_builds": [{"id": "SPEC_d035_x", "status": "done"}, {"id": "SPEC_d049_x", "status": "done"}]}),
            encoding="utf-8",
        )
        ops_log = root / "tools" / "build_loop" / "ops_log.py"
        ops_log.write_text(
            "import json, os, sys\n"
            "p=os.environ['OPS_LEDGER']\n"
            "open(p,'a').write(json.dumps({'event':sys.argv[2],'detail':sys.argv[3]})+'\\n')\n",
            encoding="utf-8",
        )
        daily = root / ".daily_count"
        daily.write_text("2026-06-16 1\n", encoding="utf-8")
        worktrees = root / "worktrees"
        (worktrees / "recent").mkdir(parents=True)
        return smoke_test.SmokeContext(
            repo_root=root,
            ops_ledger=root / "ops.jsonl",
            daily_count=daily,
            worktrees_dir=worktrees,
            expected_outputs=root / "tools" / "test" / "expected_outputs.json",
            now=lambda: datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc),
            db_connect=lambda: db or FakeDB(),
            telegram_send=lambda text: telegram,
            alert_send=lambda text: True,
        )

    def test_all_seven_smoke_tests_run_on_healthy_system(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch("importlib.import_module", return_value=object()):
            ctx = self.make_context(tmp)
            results = smoke_test.run_all(ctx)
        self.assertEqual(7, len(results))
        self.assertTrue(all(r.status == smoke_test.PASS for r in results))

    def test_fail_condition_logs_and_alerts(self):
        alerts = []
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_context(tmp, telegram=False)
            ctx.alert_send = lambda text: alerts.append(text) or True
            result = smoke_test.run_one(ctx, "x", "forced failure", lambda _ctx: (_ for _ in ()).throw(smoke_test.SmokeFailure("boom")))
            ledger = ctx.ops_ledger.read_text(encoding="utf-8")
        self.assertEqual(smoke_test.FAIL, result.status)
        self.assertIn('"event": "smoke_fail"', ledger)
        self.assertEqual(1, len(alerts))

    def test_canary_decision_cleaned_up(self):
        db = FakeDB()
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self.make_context(tmp, db=db)
            smoke_test.test_decision_roundtrip(ctx)
        self.assertEqual([], db.canaries)

    def test_real_curator_import_chain_is_importable(self):
        ctx = smoke_test.SmokeContext(repo_root=smoke_test.REPO_ROOT)
        detail = smoke_test.test_curator_import_chain(ctx)
        self.assertIn("curator imports ok", detail)

    def test_expected_outputs_updated_after_build_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            outputs = Path(tmp) / "expected_outputs.json"
            outputs.write_text(json.dumps({"d049": ["tools/test/smoke_test.py"]}), encoding="utf-8")
            paths = update_expected_outputs.extract_paths_from_name_status(
                "A\ttools/test/spec_checker.py\n"
                "A\tcore/BUILD/systemd/fpai-smoke-test.service\n"
                "M\tdocs/codex/HANDOFF.md\n"
                "D\told.py\n"
                "R100\told_name.py\tnew_name.py\n"
            )
            update_expected_outputs.update_expected_outputs("d049", paths, expected_outputs=outputs)
            data = json.loads(outputs.read_text(encoding="utf-8"))
        self.assertEqual(
            [
                "core/BUILD/systemd/fpai-smoke-test.service",
                "new_name.py",
                "tools/test/smoke_test.py",
                "tools/test/spec_checker.py",
            ],
            data["d049"],
        )

    def test_spec_checker_produces_gap_list_from_fixture_spec_and_diff(self):
        def fake_runner(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, stdout='{"matches": false, "gaps": ["missing timer"], "risk": "high"}', stderr="")

        alerts = []
        with tempfile.TemporaryDirectory() as tmp:
            result = spec_checker.check_one(
                "d049",
                "build a timer",
                "diff --git a/file b/file",
                ops_ledger=Path(tmp) / "ops.jsonl",
                runner=fake_runner,
                alert=lambda text: alerts.append(text) or True,
            )
            ledger = (Path(tmp) / "ops.jsonl").read_text(encoding="utf-8")
        self.assertFalse(result.matches)
        self.assertEqual(["missing timer"], result.gaps)
        self.assertEqual("high", result.risk)
        self.assertIn('"event": "spec_gap"', ledger)
        self.assertEqual(1, len(alerts))


if __name__ == "__main__":
    unittest.main()

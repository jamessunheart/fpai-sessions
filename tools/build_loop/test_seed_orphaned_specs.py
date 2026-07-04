import tempfile
import unittest
from pathlib import Path

from tools.build_loop import seed_orphaned_specs as seed


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self._rows = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=()):
        normalized = " ".join(sql.lower().split())
        self.conn.executed.append((normalized, params))
        if normalized.startswith("select id::text"):
            requested = set(params[0])
            self._rows = [(item,) for item in sorted(self.conn.existing & requested)]
            return
        if normalized.startswith("select coalesce(question"):
            names = [pattern.strip("%") for pattern in params[0]]
            rows = []
            for text in self.conn.existing_texts:
                if any(name in text for name in names):
                    rows.append(("", text, "", ""))
            self._rows = rows
            return
        if normalized == "select id from brain_index.decisions where id ~ '^d[0-9]+$'":
            self._rows = [(item,) for item in sorted(self.conn.existing)]
            return
        if normalized.startswith("insert into brain_index.decisions"):
            decision_id = params[0]
            if decision_id in self.conn.existing:
                self._rows = []
            else:
                self.conn.inserted.append(params)
                self.conn.existing.add(decision_id)
                self._rows = [(decision_id,)]
            return
        raise AssertionError(f"unexpected SQL: {sql}")

    def fetchall(self):
        return list(self._rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None


class FakeConn:
    def __init__(self, existing=(), existing_texts=()):
        self.existing = set(existing)
        self.existing_texts = list(existing_texts)
        self.inserted = []
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return FakeCursor(self)


class SeedOrphanedSpecsTest(unittest.TestCase):
    def test_discovers_spec_dnnn_without_result_or_existing_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            specs = root / "specs"
            results = root / "results"
            specs.mkdir()
            results.mkdir()
            (specs / "SPEC_d113_auto-seed.md").write_text(
                "# d113 - Auto seed\n\n## Build\nBuild it.\n## Context\n- Proof expected: visible queue row\n",
                encoding="utf-8",
            )
            (specs / "SPEC_d114_done.md").write_text("# d114 - Done\n", encoding="utf-8")
            (results / "SPEC_d114_done.result.md").write_text("done\n", encoding="utf-8")
            (specs / "SPEC_manual.md").write_text("# manual\n", encoding="utf-8")

            candidates = seed.discover_specs(specs, results, existing_ids={"d115"})

        self.assertEqual([candidate.decision_id for candidate in candidates], ["d113"])
        self.assertEqual(candidates[0].question, "d113 - Auto seed")
        self.assertEqual(candidates[0].proof_expected, "visible queue row")

    def test_existing_decision_ids_queries_only_candidate_ids(self):
        conn = FakeConn(existing={"d113"})

        existing = seed.existing_decision_ids(conn, ["d113", "d114"])

        self.assertEqual(existing, {"d113"})
        self.assertEqual(conn.executed[0][1], (["d113", "d114"],))

    def test_insert_candidate_preserves_decision_id_and_spec_body(self):
        conn = FakeConn()
        candidate = seed.SpecCandidate(
            decision_id="d113",
            spec_id="SPEC_d113_auto-seed",
            path=Path("SPEC_d113_auto-seed.md"),
            question="d113 - Auto seed",
            answer="auto-seeded",
            build_spec="# d113 - Auto seed\n\n## Build\nBuild it.\n",
            proof_expected="visible queue row",
        )

        inserted = seed.insert_candidate(conn, candidate)

        self.assertTrue(inserted)
        params = conn.inserted[0]
        self.assertEqual(params[0], "d113")
        self.assertEqual(params[1], "d113 - Auto seed")
        self.assertIn("## Build", params[3])
        self.assertEqual(params[4], "visible queue row")

    def test_seed_orphaned_specs_suppresses_existing_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            specs = root / "specs"
            results = root / "results"
            specs.mkdir()
            results.mkdir()
            (specs / "SPEC_d113_auto-seed.md").write_text("# d113 - Auto seed\n", encoding="utf-8")
            (specs / "SPEC_d114_next.md").write_text("# d114 - Next\n", encoding="utf-8")
            conn = FakeConn(existing={"d113"})
            old_connect = seed.connect
            seed.connect = lambda: conn
            try:
                seeded = seed.seed_orphaned_specs(specs, results)
            finally:
                seed.connect = old_connect

        self.assertEqual(seeded, ["d114"])
        self.assertEqual([params[0] for params in conn.inserted], ["d114"])

    def test_named_spec_gets_db_allocated_id_and_is_renamed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            specs = root / "specs"
            results = root / "results"
            specs.mkdir()
            results.mkdir()
            original = specs / "SPEC_test-canary.md"
            original.write_text("# Test Canary\n\n## Build\nSeed me.\n", encoding="utf-8")
            conn = FakeConn(existing={"d153"})
            old_connect = seed.connect
            seed.connect = lambda: conn
            try:
                seeded = seed.seed_orphaned_specs(specs, results)
            finally:
                seed.connect = old_connect
            self.assertEqual(seeded, ["d154"])
            self.assertFalse(original.exists())
            renamed = specs / "SPEC_d154_test-canary.md"
            self.assertTrue(renamed.exists())
            params = conn.inserted[0]
            self.assertEqual(params[0], "d154")
            self.assertEqual(params[1], "Test Canary")
            self.assertIn("named spec file `SPEC_test-canary.md`", params[2])

    def test_named_test_stall_audit_seeds_answered_d157_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            specs = root / "specs"
            results = root / "results"
            specs.mkdir()
            results.mkdir()
            original_name = "SPEC_2e8b3441-1ea4-4c7d-a6cd-47f799aa2696_test-stall-audit.md"
            original = specs / original_name
            original.write_text(
                "# SPEC_2e8b3441-1ea4-4c7d-a6cd-47f799aa2696_auto - test stall audit\n\n"
                "## Build\n"
                "(no explicit build instruction - implement what the answer + proof_expected require)\n",
                encoding="utf-8",
            )
            conn = FakeConn(existing={"d156"})
            old_connect = seed.connect
            seed.connect = lambda: conn
            try:
                seeded = seed.seed_orphaned_specs(specs, results)
            finally:
                seed.connect = old_connect

            target_name = "SPEC_d157_2e8b3441-1ea4-4c7d-a6cd-47f799aa2696-test-stall-audit.md"
            params = conn.inserted[0]

            self.assertEqual(seeded, ["d157"])
            self.assertFalse(original.exists())
            self.assertTrue((specs / target_name).exists())
            self.assertEqual(params[0], "d157")
            self.assertEqual(params[1], "SPEC_2e8b3441-1ea4-4c7d-a6cd-47f799aa2696_auto - test stall audit")
            self.assertIn(f"named spec file `{original_name}`", params[2])
            self.assertIn("answered needs_build row `d157`", params[4])
            self.assertIn(f"named spec `{target_name}`", params[4])

    def test_named_spec_dry_run_does_not_rename_or_insert(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            specs = root / "specs"
            results = root / "results"
            specs.mkdir()
            results.mkdir()
            original = specs / "SPEC_test-canary.md"
            original.write_text("# Test Canary\n", encoding="utf-8")
            conn = FakeConn(existing={"d153"})
            old_connect = seed.connect
            seed.connect = lambda: conn
            try:
                seeded = seed.seed_orphaned_specs(specs, results, dry_run=True)
            finally:
                seed.connect = old_connect
            self.assertEqual(seeded, ["d154"])
            self.assertTrue(original.exists())
            self.assertEqual(conn.inserted, [])

    def test_named_spec_allocation_skips_local_numbered_specs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            specs = root / "specs"
            results = root / "results"
            specs.mkdir()
            results.mkdir()
            (specs / "SPEC_d154_existing-numbered.md").write_text("# Existing Numbered\n", encoding="utf-8")
            original = specs / "SPEC_test-canary.md"
            original.write_text("# Test Canary\n", encoding="utf-8")
            conn = FakeConn(existing={"d153"})
            old_connect = seed.connect
            seed.connect = lambda: conn
            try:
                seeded = seed.seed_orphaned_specs(specs, results)
            finally:
                seed.connect = old_connect
            self.assertEqual(seeded, ["d154", "d155"])
            self.assertTrue((specs / "SPEC_d155_test-canary.md").exists())
            self.assertEqual([params[0] for params in conn.inserted], ["d154", "d155"])

    def test_named_spec_skips_when_db_already_references_original_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            specs = root / "specs"
            results = root / "results"
            specs.mkdir()
            results.mkdir()
            original = specs / "SPEC_test-canary.md"
            original.write_text("# Test Canary\n", encoding="utf-8")
            conn = FakeConn(
                existing={"d154"},
                existing_texts=["auto-seeded from named spec file `SPEC_test-canary.md`"],
            )
            old_connect = seed.connect
            seed.connect = lambda: conn
            try:
                seeded = seed.seed_orphaned_specs(specs, results)
            finally:
                seed.connect = old_connect
            self.assertEqual(seeded, [])
            self.assertTrue(original.exists())
            self.assertEqual(conn.inserted, [])


if __name__ == "__main__":
    unittest.main()

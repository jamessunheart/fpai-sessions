from __future__ import annotations

import json
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from tools.probe import agent, rate_governor

NOW = datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc)


class FakeCursor:
    def __init__(self, conn: "FakeConn"):
        self.conn = conn
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def execute(self, sql, params=()):
        normalized = " ".join(sql.lower().split())
        self.conn.executed.append((normalized, params))
        if "information_schema.columns" in normalized:
            self.rows = [(col,) for col in self.conn.tg_columns]
        elif "from brain_index.probe_sessions" in normalized and "engaged is distinct from true" in normalized:
            since = params[0]
            self.rows = [
                (idx + 1, s["initiated_at"], s.get("notes"))
                for idx, s in enumerate(self.conn.sessions)
                if s["initiated_at"] >= since and (not s.get("engaged") or not s.get("completed_spark"))
            ]
        elif "from brain_index.tg_messages" in normalized:
            selected = re.findall(r'"([^"]+)"', sql.split("FROM")[0])
            since = params[0] if params else datetime.min.replace(tzinfo=timezone.utc)
            self.rows = [
                tuple(row.get(col) for col in selected)
                for row in self.conn.tg_messages
                if row.get("at", since) >= since
            ]
        elif "from brain_index.probe_sessions" in normalized and "where initiated_at >= %s" in normalized and "select completed_spark" in normalized:
            since = params[-1]
            pool = params[0] if "where pool = %s" in normalized else None
            self.rows = [
                (s.get("completed_spark"), s.get("completed_onboarding"))
                for s in self.conn.sessions
                if s["initiated_at"] >= since and (pool is None or s["pool"] == pool)
            ]
        elif "sum(corrections_triggered)" in normalized:
            since = params[0]
            self.rows = [(sum(s.get("corrections_triggered", 0) for s in self.conn.sessions if s["initiated_at"] >= since),)]
        elif "from brain_index.probe_pool" in normalized:
            pool, cutoff, limit = params
            rows = []
            for member in self.conn.pool:
                last = member.get("last_probed_at")
                if member["pool"] == pool and not member.get("do_not_contact") and (last is None or last < cutoff):
                    rows.append((member["id"], member["pool"], member["handle"], member["platform"]))
            self.rows = rows[:limit]
        elif normalized.startswith("insert into brain_index.probe_sessions"):
            probe_id, pool, initiated_at, notes = params
            self.conn.sessions.append({
                "probe_id": probe_id,
                "pool": pool,
                "initiated_at": initiated_at,
                "completed_spark": False,
                "completed_onboarding": False,
                "corrections_triggered": 0,
                "engaged": False,
                "quality_score": None,
                "notes": notes,
            })
            self.rows = []
        elif normalized.startswith("update brain_index.probe_pool"):
            when, member_id = params
            for member in self.conn.pool:
                if member["id"] == member_id:
                    member["last_probed_at"] = when
            self.rows = []
        elif "count(*)::int, count(*) filter" in normalized:
            since = params[0]
            rows = [s for s in self.conn.sessions if s["initiated_at"] >= since]
            qualities = [s["quality_score"] for s in rows if s.get("quality_score") is not None]
            self.rows = [(
                len(rows),
                sum(1 for s in rows if s.get("engaged")),
                sum(1 for s in rows if s.get("completed_spark")),
                sum(qualities) / len(qualities) if qualities else None,
            )]
        elif "quality_score is null" in normalized:
            cutoff = params[0]
            self.rows = [
                (idx + 1, s["probe_id"], s.get("notes"))
                for idx, s in enumerate(self.conn.sessions)
                if s["initiated_at"] <= cutoff and s.get("quality_score") is None
            ][:25]
        elif normalized.startswith("update brain_index.probe_sessions set quality_score"):
            score, extra, session_id = params
            self.conn.sessions[session_id - 1]["quality_score"] = score
            self.conn.sessions[session_id - 1]["notes"] = (self.conn.sessions[session_id - 1].get("notes") or "") + extra
            self.rows = []
        elif normalized.startswith("update brain_index.probe_sessions set engaged"):
            drop_off, spark, onboarding, last_at, last_message, session_id = params
            session = self.conn.sessions[session_id - 1]
            session["engaged"] = True
            session["drop_off_message"] = drop_off
            session["completed_spark"] = bool(session.get("completed_spark")) or bool(spark)
            session["completed_onboarding"] = bool(session.get("completed_onboarding")) or bool(onboarding)
            session["last_message_at"] = last_at or session.get("last_message_at")
            session["last_message"] = last_message or session.get("last_message")
            self.rows = []
        else:
            self.rows = []

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeConn:
    def __init__(self, sessions=None, pool=None, tg_messages=None, tg_columns=None):
        self.sessions = list(sessions or [])
        self.pool = list(pool or [])
        self.tg_messages = list(tg_messages or [])
        self.tg_columns = set(tg_columns or {"at", "text", "username"})
        self.executed = []

    def cursor(self):
        return FakeCursor(self)


def write_rows(path: Path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


class ProbeTests(unittest.TestCase):
    def test_rate_governor_returns_0_when_smoke_fail_in_last_6h(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ops.jsonl"
            write_rows(ledger, [{"ts": (NOW - timedelta(hours=1)).isoformat(), "event": "smoke_fail"}])
            decision = rate_governor.decide_rate(conn=FakeConn(), ops_ledger=ledger, now=NOW)
            self.assertEqual(decision.count, 0)
            self.assertEqual(decision.reason, "smoke_fail_recent")

    def test_rate_governor_returns_0_when_correction_frequency_exceeds_5(self):
        sessions = [{"initiated_at": NOW - timedelta(hours=1), "pool": "warm", "corrections_triggered": 6}]
        decision = rate_governor.decide_rate(conn=FakeConn(sessions), ops_rows=[], now=NOW)
        self.assertEqual(decision.count, 0)
        self.assertEqual(decision.reason, "correction_limit_exceeded")

    def test_rate_governor_doubles_rate_when_completion_at_or_above_60(self):
        sessions = [
            {"initiated_at": NOW - timedelta(days=1), "pool": "warm", "completed_spark": i < 3, "completed_onboarding": False}
            for i in range(5)
        ]
        rows = [{"event": "probe_rate", "count": 4, "ts": (NOW - timedelta(days=1)).isoformat()}]
        decision = rate_governor.decide_rate(conn=FakeConn(sessions), ops_rows=rows, now=NOW)
        self.assertEqual(decision.count, 8)

    def test_rate_governor_holds_rate_when_completion_between_30_and_60(self):
        sessions = [
            {"initiated_at": NOW - timedelta(days=1), "pool": "warm", "completed_spark": i < 2, "completed_onboarding": False}
            for i in range(5)
        ]
        rows = [{"event": "probe_rate", "count": 7, "ts": (NOW - timedelta(days=1)).isoformat()}]
        decision = rate_governor.decide_rate(conn=FakeConn(sessions), ops_rows=rows, now=NOW)
        self.assertEqual(decision.count, 7)
        self.assertEqual(decision.reason, "completion_30_to_60_hold")

    def test_rate_governor_returns_0_and_logs_gap_when_completion_below_30(self):
        sessions = [
            {"initiated_at": NOW - timedelta(days=1), "pool": "warm", "completed_spark": False, "completed_onboarding": False}
            for _ in range(5)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ops.jsonl"
            decision = rate_governor.decide_rate(conn=FakeConn(sessions), ops_ledger=ledger, now=NOW)
            self.assertEqual(decision.count, 0)
            self.assertIn("surface_gap", decision.reason)
            self.assertTrue(rate_governor.log_rate_decision(ledger, decision, now=NOW))
            rows = [json.loads(line) for line in ledger.read_text().splitlines()]
            self.assertEqual(rows[-1]["event"], "probe_rate")
            self.assertEqual(rows[-1]["surface"], "council")

    def test_agent_does_not_recontact_same_person_within_30_days(self):
        conn = FakeConn(
            pool=[
                {"id": 1, "pool": "warm", "handle": "@old", "platform": "telegram", "last_probed_at": NOW - timedelta(days=10)},
                {"id": 2, "pool": "warm", "handle": "@new", "platform": "telegram", "last_probed_at": NOW - timedelta(days=31)},
            ]
        )
        sent = []
        result = agent.run_probe_cycle(
            conn=conn,
            sender=lambda member, text: sent.append(member.handle) or True,
            opener_composer=lambda _member: "Hey - would you test this for 5 minutes?",
            ops_ledger=Path(tempfile.mkdtemp()) / "ops.jsonl",
            now=NOW,
        )
        self.assertEqual(result.sent, 1)
        self.assertEqual(sent, ["@new"])

    def test_agent_syncs_outcomes_before_rate_decision(self):
        conn = FakeConn(
            sessions=[{
                "probe_id": "p1",
                "pool": "warm",
                "initiated_at": NOW - timedelta(days=1),
                "completed_spark": False,
                "completed_onboarding": False,
                "engaged": False,
                "quality_score": None,
                "notes": json.dumps({"handle": "@sam"}),
            }],
            pool=[{"id": 2, "pool": "warm", "handle": "@new", "platform": "telegram", "last_probed_at": None}],
            tg_messages=[{"at": NOW - timedelta(hours=12), "username": "sam", "text": "Spark completed and I have a clear next step."}],
        )
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ops.jsonl"
            write_rows(ledger, [{"event": "probe_rate", "count": 2, "ts": (NOW - timedelta(days=1)).isoformat()}])
            result = agent.run_probe_cycle(
                conn=conn,
                sender=lambda _member, _text: True,
                opener_composer=lambda _member: "Hey - would you test this for 5 minutes?",
                ops_ledger=ledger,
                now=NOW,
            )
        self.assertEqual(result.rate, 4)
        self.assertTrue(conn.sessions[0]["completed_spark"])

    def test_probe_disable_exits_without_sending(self):
        with tempfile.TemporaryDirectory() as tmp:
            disable = Path(tmp) / ".probe_disabled"
            disable.touch()
            result = agent.run_probe_cycle(
                conn=FakeConn(pool=[{"id": 1, "pool": "warm", "handle": "@a", "platform": "telegram"}]),
                sender=lambda _m, _t: self.fail("should not send"),
                disable_file=disable,
                now=NOW,
            )
            self.assertTrue(result.disabled)
            self.assertEqual(result.sent, 0)

    def test_opener_is_at_most_3_sentences_and_not_pitching_features(self):
        opener = agent.sanitize_opener("Feature demo. Buy now. Third. Fourth.")
        self.assertLessEqual(len([p for p in opener.split(".") if p.strip()]), 3)
        self.assertNotRegex(opener, agent.PITCH_WORDS)

    def test_quality_evaluation_runs_after_24h_silence(self):
        conn = FakeConn(sessions=[{"probe_id": "p1", "pool": "warm", "initiated_at": NOW - timedelta(hours=25), "quality_score": None, "notes": "ended"}])

        def runner(*_args, **_kwargs):
            return SimpleNamespace(returncode=0, stdout='{"score": 0.8, "gaps": [], "highlight": "clear"}')

        updated = agent.evaluate_due_sessions(conn=conn, now=NOW, runner=runner)
        self.assertEqual(updated, 1)
        self.assertEqual(conn.sessions[0]["quality_score"], 0.8)

    def test_refresh_session_outcomes_updates_from_tg_messages(self):
        notes = json.dumps({"handle": "@sam"})
        conn = FakeConn(
            sessions=[{"probe_id": "p1", "pool": "warm", "initiated_at": NOW - timedelta(hours=2), "quality_score": None, "notes": notes, "engaged": False, "completed_spark": False}],
            tg_messages=[
                {"at": NOW - timedelta(hours=1), "username": "sam", "text": "Spark completed and I have a clear next step."}
            ],
        )
        updated = agent.refresh_session_outcomes(conn=conn, now=NOW)
        self.assertEqual(updated, 1)
        self.assertTrue(conn.sessions[0]["engaged"])
        self.assertTrue(conn.sessions[0]["completed_spark"])
        self.assertEqual(conn.sessions[0]["drop_off_message"], 1)


if __name__ == "__main__":
    unittest.main()

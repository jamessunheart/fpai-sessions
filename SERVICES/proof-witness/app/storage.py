"""
Proof Witness - Storage Layer

Stores proof candidates and confirmed proof in SQLite
"""
import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from contextlib import contextmanager

from app.config import settings
from app.models import ProofCandidate, ConfirmedProof, ProofStatus, DailyProofSummary


class ProofStorage:
    """Storage for proof candidates and confirmed proof"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.DATABASE_PATH
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist"""
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS proof_candidates (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    url TEXT,
                    media TEXT,  -- JSON array
                    data TEXT,   -- JSON object
                    tags TEXT,   -- JSON array
                    suggested_question TEXT,
                    confidence REAL,
                    occurred_at TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    confirmed_at TEXT,
                    content_draft TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS confirmed_proof (
                    id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    type TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    url TEXT,
                    media TEXT,  -- JSON array
                    data TEXT,   -- JSON object
                    tags TEXT,   -- JSON array
                    question_id TEXT,
                    impact TEXT,
                    progress_delta REAL,
                    occurred_at TEXT NOT NULL,
                    confirmed_at TEXT NOT NULL,
                    content_published TEXT,
                    content_url TEXT
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_candidates_status
                ON proof_candidates(status)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_candidates_owner
                ON proof_candidates(owner)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_confirmed_date
                ON confirmed_proof(confirmed_at)
            """)

    @contextmanager
    def _conn(self):
        """Database connection context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def add_candidate(self, candidate: ProofCandidate) -> str:
        """Add a new proof candidate"""
        if not candidate.id:
            candidate.id = str(uuid.uuid4())

        with self._conn() as conn:
            conn.execute("""
                INSERT INTO proof_candidates
                (id, source, type, status, owner, title, description, url,
                 media, data, tags, suggested_question, confidence,
                 occurred_at, captured_at, content_draft)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                candidate.id,
                candidate.source.value,
                candidate.type.value,
                candidate.status.value,
                candidate.owner,
                candidate.title,
                candidate.description,
                candidate.url,
                json.dumps(candidate.media) if candidate.media else None,
                json.dumps(candidate.data) if candidate.data else None,
                json.dumps(candidate.tags),
                candidate.suggested_question,
                candidate.confidence,
                candidate.occurred_at.isoformat(),
                candidate.captured_at.isoformat(),
                candidate.content_draft
            ))

        return candidate.id

    def get_pending_candidates(self, limit: int = 10) -> List[ProofCandidate]:
        """Get proof candidates waiting for confirmation"""
        with self._conn() as conn:
            cursor = conn.execute("""
                SELECT * FROM proof_candidates
                WHERE status = ?
                ORDER BY occurred_at DESC
                LIMIT ?
            """, (ProofStatus.PENDING.value, limit))

            return [self._row_to_candidate(row) for row in cursor.fetchall()]

    def confirm_candidate(self, candidate_id: str, tags: List[str] = None,
                         question_id: str = None, impact: str = None) -> ConfirmedProof:
        """Confirm a proof candidate"""
        # Get candidate
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM proof_candidates WHERE id = ?",
                (candidate_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Candidate {candidate_id} not found")

            candidate = self._row_to_candidate(row)

        # Create confirmed proof
        proof = ConfirmedProof(
            id=str(uuid.uuid4()),
            candidate_id=candidate_id,
            source=candidate.source,
            type=candidate.type,
            owner=candidate.owner,
            title=candidate.title,
            description=candidate.description,
            url=candidate.url,
            media=candidate.media,
            data=candidate.data,
            tags=tags or candidate.tags,
            question_id=question_id,
            impact=impact,
            occurred_at=candidate.occurred_at,
            confirmed_at=datetime.utcnow()
        )

        # Save confirmed proof
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO confirmed_proof
                (id, candidate_id, source, type, owner, title, description,
                 url, media, data, tags, question_id, impact, progress_delta,
                 occurred_at, confirmed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                proof.id,
                proof.candidate_id,
                proof.source.value,
                proof.type.value,
                proof.owner,
                proof.title,
                proof.description,
                proof.url,
                json.dumps(proof.media) if proof.media else None,
                json.dumps(proof.data) if proof.data else None,
                json.dumps(proof.tags),
                proof.question_id,
                proof.impact,
                proof.progress_delta,
                proof.occurred_at.isoformat(),
                proof.confirmed_at.isoformat()
            ))

            # Update candidate status
            conn.execute("""
                UPDATE proof_candidates
                SET status = ?, confirmed_at = ?
                WHERE id = ?
            """, (ProofStatus.CONFIRMED.value, datetime.utcnow().isoformat(), candidate_id))

        return proof

    def get_daily_summary(self, date: str = None) -> DailyProofSummary:
        """Get summary of proof for a specific day"""
        if not date:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        start = f"{date} 00:00:00"
        end = f"{date} 23:59:59"

        with self._conn() as conn:
            # Get confirmed proof for the day
            cursor = conn.execute("""
                SELECT * FROM confirmed_proof
                WHERE confirmed_at >= ? AND confirmed_at <= ?
                ORDER BY confirmed_at DESC
            """, (start, end))

            confirmed_list = [self._row_to_confirmed(row) for row in cursor.fetchall()]

            # Count by owner, type, tag
            by_owner = {}
            by_type = {}
            by_tag = {}

            for proof in confirmed_list:
                by_owner[proof.owner] = by_owner.get(proof.owner, 0) + 1
                by_type[proof.type.value] = by_type.get(proof.type.value, 0) + 1
                for tag in proof.tags:
                    by_tag[tag] = by_tag.get(tag, 0) + 1

            # Get candidate counts
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM proof_candidates
                WHERE captured_at >= ? AND captured_at <= ?
                GROUP BY status
            """, (start, end))

            status_counts = {row['status']: row['count'] for row in cursor.fetchall()}

        return DailyProofSummary(
            date=date,
            total_candidates=sum(status_counts.values()),
            total_confirmed=status_counts.get(ProofStatus.CONFIRMED.value, 0),
            total_rejected=status_counts.get(ProofStatus.REJECTED.value, 0),
            by_owner=by_owner,
            by_type=by_type,
            by_tag=by_tag,
            highlights=confirmed_list[:5]  # Top 5
        )

    def _row_to_candidate(self, row) -> ProofCandidate:
        """Convert database row to ProofCandidate"""
        from app.models import ProofSource, ProofType, ProofStatus

        return ProofCandidate(
            id=row['id'],
            source=ProofSource(row['source']),
            type=ProofType(row['type']),
            status=ProofStatus(row['status']),
            owner=row['owner'],
            title=row['title'],
            description=row['description'],
            url=row['url'],
            media=json.loads(row['media']) if row['media'] else None,
            data=json.loads(row['data']) if row['data'] else None,
            tags=json.loads(row['tags']),
            suggested_question=row['suggested_question'],
            confidence=row['confidence'],
            occurred_at=datetime.fromisoformat(row['occurred_at']),
            captured_at=datetime.fromisoformat(row['captured_at']),
            confirmed_at=datetime.fromisoformat(row['confirmed_at']) if row['confirmed_at'] else None,
            content_draft=row['content_draft']
        )

    def _row_to_confirmed(self, row) -> ConfirmedProof:
        """Convert database row to ConfirmedProof"""
        from app.models import ProofSource, ProofType

        return ConfirmedProof(
            id=row['id'],
            candidate_id=row['candidate_id'],
            source=ProofSource(row['source']),
            type=ProofType(row['type']),
            owner=row['owner'],
            title=row['title'],
            description=row['description'],
            url=row['url'],
            media=json.loads(row['media']) if row['media'] else None,
            data=json.loads(row['data']) if row['data'] else None,
            tags=json.loads(row['tags']),
            question_id=row['question_id'],
            impact=row['impact'],
            progress_delta=row['progress_delta'],
            occurred_at=datetime.fromisoformat(row['occurred_at']),
            confirmed_at=datetime.fromisoformat(row['confirmed_at']),
            content_published=row['content_published'],
            content_url=row['content_url']
        )


# Global instance
storage = ProofStorage()

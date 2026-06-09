"""
Funnel pipeline — orchestrates ingest, screening, advancement, and comms drafts.

The Funnel is the single entry point. CLI calls it. /apply endpoint calls it.
Daily cycle calls it. Same code, same state.

State lives in funnel/data/pipeline.json (one row per candidate).
Comms drafts go to funnel/outbox/<candidate_id>/<artifact>.md (never sent).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .stages import Candidate, Decision, Stage, next_stage

logger = logging.getLogger("apprentice_studio.funnel")

FUNNEL_ROOT = Path(__file__).resolve().parent
DATA_DIR = FUNNEL_ROOT / "data"
OUTBOX_DIR = FUNNEL_ROOT / "outbox"
PIPELINE_FILE = DATA_DIR / "pipeline.json"


class Funnel:
    """The end-to-end recruiting funnel."""

    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
        self.candidates: dict[str, Candidate] = {}
        self._load()

    # --- persistence -------------------------------------------------------

    def _load(self) -> None:
        if not PIPELINE_FILE.exists():
            self.candidates = {}
            return
        data = json.loads(PIPELINE_FILE.read_text(encoding="utf-8"))
        self.candidates = {
            row["id"]: Candidate.from_dict(row) for row in data.get("candidates", [])
        }
        logger.info("Loaded %d candidates", len(self.candidates))

    def save(self) -> None:
        payload = {
            "version": 1,
            "saved_at": datetime.now().isoformat(),
            "candidates": [c.to_dict() for c in self.candidates.values()],
        }
        PIPELINE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # --- intake ------------------------------------------------------------

    def add_application(
        self,
        name: str,
        email: str,
        application: dict[str, Any],
        source: str = "inbound",
    ) -> Candidate:
        """Add an inbound application or convert a sourced prospect to applied."""
        cid = Candidate.make_id(email, name)
        if cid in self.candidates:
            cand = self.candidates[cid]
            cand.application.update(application)
            if cand.stage == Stage.CONTACTED:
                cand.transition(Stage.APPLIED, Decision.ADVANCE, by="intake",
                                note="Sourced prospect responded with application")
            cand.last_updated = datetime.now().isoformat()
        else:
            cand = Candidate(
                id=cid,
                name=name,
                email=email,
                stage=Stage.APPLIED,
                source=source,
                application=application,
            )
            cand.transition(Stage.APPLIED, Decision.ADVANCE, by="intake",
                            note="Inbound application received")
            self.candidates[cid] = cand
        self.save()
        return cand

    def add_outbound(self, name: str, email: str, source_note: str) -> Candidate:
        """Add a sourced outbound prospect (not yet contacted)."""
        cid = Candidate.make_id(email, name)
        if cid in self.candidates:
            return self.candidates[cid]
        cand = Candidate(
            id=cid,
            name=name,
            email=email,
            stage=Stage.SOURCED,
            source=f"outbound: {source_note}",
        )
        cand.transition(Stage.SOURCED, Decision.ADVANCE, by="sourcer", note=source_note)
        self.candidates[cid] = cand
        self.save()
        return cand

    # --- transitions -------------------------------------------------------

    def decide(
        self,
        candidate_id: str,
        decision: Decision,
        by: str = "human",
        note: Optional[str] = None,
    ) -> Candidate:
        cand = self._must(candidate_id)
        target = next_stage(cand.stage, decision)
        if target is None:
            raise ValueError(
                f"Invalid transition from {cand.stage.value} with {decision.value}"
            )
        cand.transition(target, decision, by=by, note=note)
        self.save()
        return cand

    # --- status views ------------------------------------------------------

    def by_stage(self) -> dict[str, list[Candidate]]:
        out: dict[str, list[Candidate]] = {s.value: [] for s in Stage}
        for cand in self.candidates.values():
            out[cand.stage.value].append(cand)
        return out

    def needs_action(self) -> list[Candidate]:
        """Candidates where the human is the bottleneck (sorted by best signal first)."""
        priority = {
            Stage.CHALLENGE_GRADED: 0,
            Stage.INTERVIEWED: 1,
            Stage.SCREENED: 2,
            Stage.CHALLENGE_SENT: 3,
            Stage.OFFER_SENT: 4,
            Stage.APPLIED: 5,
            Stage.CONTACTED: 6,
            Stage.SOURCED: 7,
        }
        active = [c for c in self.candidates.values() if c.stage in priority]

        def sort_key(c: Candidate) -> tuple:
            best_score = max(
                c.challenge_score or 0,
                c.screening_score or 0,
                c.interview_score or 0,
            )
            return (priority[c.stage], -best_score)

        return sorted(active, key=sort_key)

    def funnel_summary(self) -> dict[str, int]:
        counts = {s.value: 0 for s in Stage}
        for cand in self.candidates.values():
            counts[cand.stage.value] += 1
        return counts

    # --- helpers -----------------------------------------------------------

    def _must(self, candidate_id: str) -> Candidate:
        if candidate_id not in self.candidates:
            raise KeyError(f"Unknown candidate: {candidate_id}")
        return self.candidates[candidate_id]

    def get(self, candidate_id: str) -> Optional[Candidate]:
        return self.candidates.get(candidate_id)

    def find_by_email(self, email: str) -> Optional[Candidate]:
        target = email.strip().lower()
        for cand in self.candidates.values():
            if cand.email.strip().lower() == target:
                return cand
        return None

    def outbox_dir(self, candidate_id: str) -> Path:
        path = OUTBOX_DIR / candidate_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_draft(self, candidate_id: str, filename: str, content: str) -> Path:
        path = self.outbox_dir(candidate_id) / filename
        path.write_text(content, encoding="utf-8")
        return path


_funnel: Optional[Funnel] = None


def get_funnel() -> Funnel:
    global _funnel
    if _funnel is None:
        _funnel = Funnel()
    return _funnel

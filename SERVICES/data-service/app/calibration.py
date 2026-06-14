"""
Calibration Layer
=================
Tracks prediction accuracy and provides calibrated confidence.
"""

import json
import os
import threading
from datetime import datetime, timezone
from typing import Dict, Tuple
from pydantic import BaseModel

CALIBRATION_PATH = os.getenv(
    "CALIBRATION_STORE_PATH",
    "/opt/fpai/autonomous/data/calibration.json"
)
os.makedirs(os.path.dirname(CALIBRATION_PATH), exist_ok=True)
_lock = threading.Lock()


class PredictionOutcome(BaseModel):
    prediction_id: str
    target_metric: str
    predicted_direction: str
    predicted_value: float | None
    actual_value: float
    result: str  # "verified" | "failed" | "unverifiable"
    confidence: float
    error_abs: float | None = None
    created_at: datetime
    timeframe_hours: int | None = None


class CalibrationStats(BaseModel):
    target_metric: str
    horizon_hours: int
    sample_size: int
    win_rate: float
    avg_confidence_pass: float
    avg_confidence_fail: float
    brier_score: float
    last_updated: datetime


class CalibrationStore:
    """
    Maintains rolling calibration statistics per (metric, horizon).
    """

    def __init__(self):
        self.stats: Dict[Tuple[str, int], Dict] = {}
        self._load()

    def _load(self):
        if os.path.isfile(CALIBRATION_PATH):
            try:
                with open(CALIBRATION_PATH, "r") as f:
                    self.stats = json.load(f)
            except Exception:
                self.stats = {}

    def _save(self):
        try:
            with open(CALIBRATION_PATH, "w") as f:
                json.dump(self.stats, f)
        except Exception:
            pass

    def update_stats(self, outcome: PredictionOutcome):
        key = (outcome.target_metric, int(outcome.timeframe_hours or 24))
        with _lock:
            bucket = self.stats.get(str(key), {
                "wins": 0,
                "fails": 0,
                "conf_pass": [],
                "conf_fail": [],
                "brier": []
            })
            if outcome.result == "verified":
                bucket["wins"] += 1
                bucket["conf_pass"].append(outcome.confidence)
                outcome_binary = 1
            elif outcome.result == "failed":
                bucket["fails"] += 1
                bucket["conf_fail"].append(outcome.confidence)
                outcome_binary = 0
            else:
                # unverifiable -> ignore calibration
                self.stats[str(key)] = bucket
                return

            bucket["brier"].append((outcome.confidence - outcome_binary) ** 2)
            self.stats[str(key)] = bucket
            self._save()

    def get_stats(self, target_metric: str, horizon_hours: int = 24) -> CalibrationStats:
        key = str((target_metric, int(horizon_hours)))
        bucket = self.stats.get(key, {
            "wins": 0,
            "fails": 0,
            "conf_pass": [],
            "conf_fail": [],
            "brier": []
        })
        wins = bucket["wins"]
        fails = bucket["fails"]
        total = wins + fails
        win_rate = (wins / total) if total else 0.5
        avg_conf_pass = sum(bucket["conf_pass"]) / len(bucket["conf_pass"]) if bucket["conf_pass"] else 0.0
        avg_conf_fail = sum(bucket["conf_fail"]) / len(bucket["conf_fail"]) if bucket["conf_fail"] else 0.0
        brier = sum(bucket["brier"]) / len(bucket["brier"]) if bucket["brier"] else 0.25

        return CalibrationStats(
            target_metric=target_metric,
            horizon_hours=int(horizon_hours),
            sample_size=total,
            win_rate=win_rate,
            avg_confidence_pass=avg_conf_pass,
            avg_confidence_fail=avg_conf_fail,
            brier_score=brier,
            last_updated=datetime.now(timezone.utc)
        )


# Singleton
calibration_store = CalibrationStore()













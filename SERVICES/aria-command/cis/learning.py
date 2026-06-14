#!/usr/bin/env python3
"""
CIS Learning Engine
===================
The loop that makes the system actually learn.

Runs daily (or on-demand) to:
1. Analyze intervention outcomes
2. Detect patterns (what works when)
3. Update action weights
4. Adjust timing preferences
5. Refine restraint rules

PRINCIPLE: Learning from proof, not theory.
"""
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

logger = logging.getLogger("cis.learning")

@dataclass
class InterventionRecord:
    id: str
    action_key: str
    state: str
    intensity: int
    outcome: str  # helped, same, no, no_response
    hour: int
    day_of_week: int
    delivered_at: str


@dataclass
class LearnedPattern:
    pattern_type: str  # timing, action, state, sequence
    description: str
    confidence: float  # 0-1
    sample_size: int
    recommendation: str
    data: Dict


@dataclass 
class LearningReport:
    analyzed_at: str
    interventions_analyzed: int
    patterns_detected: List[LearnedPattern]
    action_weight_updates: Dict[str, float]
    timing_insights: Dict
    recommendations: List[str]


class LearningEngine:
    """
    Analyzes outcomes and updates system behavior.
    """
    
    def __init__(self, db_path: str = "/opt/fpai/aria/cis.db"):
        self.db_path = db_path
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Ensure learning tables exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Learned patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_patterns (
                id TEXT PRIMARY KEY,
                pattern_type TEXT,
                description TEXT,
                confidence REAL,
                sample_size INTEGER,
                recommendation TEXT,
                data TEXT,
                learned_at TEXT DEFAULT (datetime('now')),
                active INTEGER DEFAULT 1
            )
        """)
        
        # Timing preferences (learned)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS timing_preferences (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                hour INTEGER,
                day_of_week INTEGER,
                receptivity_score REAL,
                sample_size INTEGER,
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # Learning runs log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_runs (
                id TEXT PRIMARY KEY,
                run_at TEXT DEFAULT (datetime('now')),
                interventions_analyzed INTEGER,
                patterns_found INTEGER,
                report TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _get_recent_interventions(self, days: int = 30) -> List[InterventionRecord]:
        """Get interventions from the last N days."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT i.id, a.action_key, i.state_at_trigger, i.intensity_at_trigger,
                   i.outcome, i.delivered_at
            FROM interventions i
            LEFT JOIN actions a ON i.action_id = a.id
            WHERE i.delivered_at > ? AND i.outcome IS NOT NULL
            ORDER BY i.delivered_at DESC
        """, (cutoff,))
        
        records = []
        for row in cursor.fetchall():
            try:
                dt = datetime.fromisoformat(row[5])
                records.append(InterventionRecord(
                    id=row[0],
                    action_key=row[1] or "unknown",
                    state=row[2] or "unknown",
                    intensity=row[3] or 3,
                    outcome=row[4],
                    hour=dt.hour,
                    day_of_week=dt.weekday(),
                    delivered_at=row[5]
                ))
            except:
                continue
        
        conn.close()
        return records
    
    def _analyze_timing_patterns(self, records: List[InterventionRecord]) -> List[LearnedPattern]:
        """Find patterns in when interventions work best."""
        patterns = []
        
        # Group by hour
        hour_outcomes = defaultdict(lambda: {"helped": 0, "same": 0, "no": 0, "no_response": 0})
        for r in records:
            hour_outcomes[r.hour][r.outcome] = hour_outcomes[r.hour].get(r.outcome, 0) + 1
        
        # Find best/worst hours
        hour_scores = {}
        for hour, outcomes in hour_outcomes.items():
            total = sum(outcomes.values())
            if total >= 3:  # Minimum sample
                helped = outcomes.get("helped", 0)
                score = helped / total
                hour_scores[hour] = (score, total)
        
        if hour_scores:
            best_hour = max(hour_scores.keys(), key=lambda h: hour_scores[h][0])
            worst_hour = min(hour_scores.keys(), key=lambda h: hour_scores[h][0])
            
            if hour_scores[best_hour][0] > 0.5:
                patterns.append(LearnedPattern(
                    pattern_type="timing",
                    description=f"Interventions work best around {best_hour}:00",
                    confidence=hour_scores[best_hour][0],
                    sample_size=hour_scores[best_hour][1],
                    recommendation=f"Prefer pinging around {best_hour}:00",
                    data={"best_hour": best_hour, "score": hour_scores[best_hour][0]}
                ))
            
            if hour_scores[worst_hour][0] < 0.3 and hour_scores[worst_hour][1] >= 5:
                patterns.append(LearnedPattern(
                    pattern_type="timing",
                    description=f"Avoid interventions around {worst_hour}:00",
                    confidence=1 - hour_scores[worst_hour][0],
                    sample_size=hour_scores[worst_hour][1],
                    recommendation=f"Avoid pinging around {worst_hour}:00",
                    data={"worst_hour": worst_hour, "score": hour_scores[worst_hour][0]}
                ))
        
        # Group by day of week
        day_outcomes = defaultdict(lambda: {"helped": 0, "same": 0, "no": 0, "no_response": 0})
        for r in records:
            day_outcomes[r.day_of_week][r.outcome] = day_outcomes[r.day_of_week].get(r.outcome, 0) + 1
        
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for day, outcomes in day_outcomes.items():
            total = sum(outcomes.values())
            if total >= 3:
                helped = outcomes.get("helped", 0)
                score = helped / total
                if score > 0.6:
                    patterns.append(LearnedPattern(
                        pattern_type="timing",
                        description=f"{day_names[day]}s are good for interventions",
                        confidence=score,
                        sample_size=total,
                        recommendation=f"Can be more proactive on {day_names[day]}s",
                        data={"day": day, "day_name": day_names[day], "score": score}
                    ))
        
        return patterns
    
    def _analyze_action_patterns(self, records: List[InterventionRecord]) -> Tuple[List[LearnedPattern], Dict[str, float]]:
        """Find which actions work best for which states."""
        patterns = []
        weight_updates = {}
        
        # Group by action + state
        action_state_outcomes = defaultdict(lambda: defaultdict(lambda: {"helped": 0, "same": 0, "no": 0}))
        
        for r in records:
            if r.outcome in ["helped", "same", "no"]:
                action_state_outcomes[r.action_key][r.state][r.outcome] += 1
        
        for action, states in action_state_outcomes.items():
            for state, outcomes in states.items():
                total = sum(outcomes.values())
                if total >= 3:
                    helped = outcomes.get("helped", 0)
                    score = helped / total
                    
                    # Update weight
                    weight_key = f"{action}:{state}"
                    weight_updates[weight_key] = score
                    
                    if score > 0.6:
                        patterns.append(LearnedPattern(
                            pattern_type="action",
                            description=f"'{action}' works well for '{state}' state",
                            confidence=score,
                            sample_size=total,
                            recommendation=f"Prefer '{action}' when state is '{state}'",
                            data={"action": action, "state": state, "score": score}
                        ))
                    elif score < 0.2 and total >= 5:
                        patterns.append(LearnedPattern(
                            pattern_type="action",
                            description=f"'{action}' doesn't help with '{state}' state",
                            confidence=1 - score,
                            sample_size=total,
                            recommendation=f"Avoid '{action}' when state is '{state}'",
                            data={"action": action, "state": state, "score": score}
                        ))
        
        return patterns, weight_updates
    
    def _analyze_response_patterns(self, records: List[InterventionRecord]) -> List[LearnedPattern]:
        """Analyze response patterns to refine restraint."""
        patterns = []
        
        # No-response rate
        no_response_count = sum(1 for r in records if r.outcome == "no_response")
        total = len(records)
        
        if total >= 5:
            no_response_rate = no_response_count / total
            
            if no_response_rate > 0.5:
                patterns.append(LearnedPattern(
                    pattern_type="restraint",
                    description=f"High no-response rate ({no_response_rate:.0%})",
                    confidence=0.8,
                    sample_size=total,
                    recommendation="Reduce intervention frequency, increase quality",
                    data={"no_response_rate": no_response_rate}
                ))
            elif no_response_rate < 0.2:
                patterns.append(LearnedPattern(
                    pattern_type="restraint",
                    description=f"Good response rate ({1-no_response_rate:.0%})",
                    confidence=0.8,
                    sample_size=total,
                    recommendation="Current frequency seems appropriate",
                    data={"response_rate": 1 - no_response_rate}
                ))
        
        return patterns
    
    def _update_action_weights(self, weight_updates: Dict[str, float], user_id: str = "james"):
        """Apply learned weights to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for weight_key, score in weight_updates.items():
            action_key, state = weight_key.split(":", 1)
            
            # Get action ID
            cursor.execute("SELECT id FROM actions WHERE action_key = ?", (action_key,))
            row = cursor.fetchone()
            if not row:
                continue
            action_id = row[0]
            
            # Update or insert weight
            cursor.execute("""
                INSERT INTO action_weights (id, user_id, action_id, state, weight, trials, successes)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(user_id, action_id, state) DO UPDATE SET
                    weight = ?,
                    trials = trials + 1,
                    successes = successes + ?
            """, (
                f"{user_id}:{action_id}:{state}",
                user_id, action_id, state, score, 1 if score > 0.5 else 0,
                score, 1 if score > 0.5 else 0
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"Updated {len(weight_updates)} action weights")
    
    def _update_timing_preferences(self, patterns: List[LearnedPattern], user_id: str = "james"):
        """Store learned timing preferences."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for pattern in patterns:
            if pattern.pattern_type != "timing":
                continue
            
            data = pattern.data
            if "best_hour" in data:
                hour = data["best_hour"]
                score = data["score"]
                cursor.execute("""
                    INSERT OR REPLACE INTO timing_preferences 
                    (id, user_id, hour, day_of_week, receptivity_score, sample_size, updated_at)
                    VALUES (?, ?, ?, -1, ?, ?, datetime('now'))
                """, (f"{user_id}:hour:{hour}", user_id, hour, score, pattern.sample_size))
            
            if "worst_hour" in data:
                hour = data["worst_hour"]
                score = data["score"]
                cursor.execute("""
                    INSERT OR REPLACE INTO timing_preferences 
                    (id, user_id, hour, day_of_week, receptivity_score, sample_size, updated_at)
                    VALUES (?, ?, ?, -1, ?, ?, datetime('now'))
                """, (f"{user_id}:hour:{hour}", user_id, hour, score, pattern.sample_size))
        
        conn.commit()
        conn.close()
    
    def _save_patterns(self, patterns: List[LearnedPattern]):
        """Save learned patterns to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for p in patterns:
            import uuid
            cursor.execute("""
                INSERT INTO learned_patterns 
                (id, pattern_type, description, confidence, sample_size, recommendation, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                p.pattern_type,
                p.description,
                p.confidence,
                p.sample_size,
                p.recommendation,
                json.dumps(p.data)
            ))
        
        conn.commit()
        conn.close()
    
    def run_learning_cycle(self, days: int = 30) -> LearningReport:
        """
        Run a complete learning cycle.
        
        1. Gather recent interventions
        2. Analyze patterns
        3. Update weights and preferences
        4. Save patterns
        5. Generate report
        """
        logger.info(f"Starting learning cycle (analyzing last {days} days)")
        
        # Gather data
        records = self._get_recent_interventions(days)
        
        if not records:
            return LearningReport(
                analyzed_at=datetime.now().isoformat(),
                interventions_analyzed=0,
                patterns_detected=[],
                action_weight_updates={},
                timing_insights={},
                recommendations=["Not enough data yet. Keep using the system."]
            )
        
        # Analyze
        timing_patterns = self._analyze_timing_patterns(records)
        action_patterns, weight_updates = self._analyze_action_patterns(records)
        restraint_patterns = self._analyze_response_patterns(records)
        
        all_patterns = timing_patterns + action_patterns + restraint_patterns
        
        # Apply learning
        if weight_updates:
            self._update_action_weights(weight_updates)
        
        if timing_patterns:
            self._update_timing_preferences(timing_patterns)
        
        if all_patterns:
            self._save_patterns(all_patterns)
        
        # Generate recommendations
        recommendations = [p.recommendation for p in all_patterns if p.confidence > 0.6]
        
        # Build timing insights
        timing_insights = {}
        for p in timing_patterns:
            if "best_hour" in p.data:
                timing_insights["best_hour"] = p.data["best_hour"]
            if "worst_hour" in p.data:
                timing_insights["worst_hour"] = p.data["worst_hour"]
        
        report = LearningReport(
            analyzed_at=datetime.now().isoformat(),
            interventions_analyzed=len(records),
            patterns_detected=all_patterns,
            action_weight_updates=weight_updates,
            timing_insights=timing_insights,
            recommendations=recommendations if recommendations else ["Continue current approach"]
        )
        
        # Log the run
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        import uuid
        cursor.execute("""
            INSERT INTO learning_runs (id, interventions_analyzed, patterns_found, report)
            VALUES (?, ?, ?, ?)
        """, (str(uuid.uuid4()), len(records), len(all_patterns), json.dumps(asdict(report), default=str)))
        conn.commit()
        conn.close()
        
        logger.info(f"Learning cycle complete: {len(records)} interventions, {len(all_patterns)} patterns")
        
        return report
    
    def get_timing_preference(self, user_id: str, hour: int) -> float:
        """Get learned receptivity score for a given hour."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT receptivity_score FROM timing_preferences
            WHERE user_id = ? AND hour = ?
        """, (user_id, hour))
        
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else 0.5  # Default neutral
    
    def get_action_weight(self, user_id: str, action_key: str, state: str) -> float:
        """Get learned weight for action+state combo."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT aw.weight FROM action_weights aw
            JOIN actions a ON aw.action_id = a.id
            WHERE aw.user_id = ? AND a.action_key = ? AND aw.state = ?
        """, (user_id, action_key, state))
        
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else 1.0  # Default neutral


# Singleton
_engine: Optional[LearningEngine] = None

def get_learning_engine() -> LearningEngine:
    global _engine
    if _engine is None:
        _engine = LearningEngine()
    return _engine

def run_learning_cycle(days: int = 30) -> LearningReport:
    """Run a learning cycle."""
    return get_learning_engine().run_learning_cycle(days)

def get_timing_preference(hour: int, user_id: str = "james") -> float:
    """Get timing preference for an hour."""
    return get_learning_engine().get_timing_preference(user_id, hour)

def get_action_weight(action_key: str, state: str, user_id: str = "james") -> float:
    """Get action weight for state."""
    return get_learning_engine().get_action_weight(user_id, action_key, state)









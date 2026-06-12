#!/usr/bin/env python3
"""
Continuity Intelligence System (CIS) Engine
============================================
State → Trigger → Decision → Delivery → Learning → Fuses

A system that finds you, acts quietly, learns from proof.
"""
import os
import json
import uuid
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("cis")

# ============================================================================
# DATA TYPES
# ============================================================================

@dataclass
class UserState:
    state: str  # calm, busy, overloaded, stuck, open
    intensity: int  # 1-5
    confidence: str  # low, medium, high
    source: str  # explicit, inferred, default
    captured_at: str

@dataclass
class Action:
    id: str
    action_key: str
    category: str
    name: str
    instruction: str
    duration_seconds: int
    effective_states: List[str]
    min_intensity: int
    max_intensity: int

@dataclass
class TriggerResult:
    should_fire: bool
    trigger_type: Optional[str]
    confidence: float
    reason: str

@dataclass
class Decision:
    type: str  # silence, stabilize, disrupt, execute, ask
    action_id: Optional[str]
    action_key: Optional[str]
    confidence: float
    reason: str

# ============================================================================
# CONFIG
# ============================================================================

TRIGGER_CONFIG = {
    "INTRUSION_COST": {
        "calm": 0.8,
        "busy": 0.5,
        "overloaded": 0.3,
        "stuck": 0.2,
        "open": 0.1
    },
    "CONFIDENCE_MULTIPLIER": {
        "low": 0.3,
        "medium": 0.6,
        "high": 1.0
    },
    "SPIKE": {
        "intensity_jump": 2,
        "window_minutes": 60,
        "min_confidence": "medium"
    },
    "STUCK": {
        "repeat_count": 3,
        "window_hours": 24
    },
    "SILENCE_DRIFT": {
        "no_signal_hours": 48,
        "concerning_states": ["overloaded", "stuck"],
        "min_intensity": 3
    },
    "RATE_LIMITS": {
        "max_pings_per_hour": 2,
        "max_pings_per_day": 6,
        "min_minutes_between_pings": 20,
        "cooldown_after_no_response_hours": 4
    }
}

FUSE_CONFIG = {
    "rate_limit": {"duration_hours": 1, "auto_reset": True},
    "distress": {"duration_hours": 2, "auto_reset": True},
    "uncertainty": {"duration_hours": 4, "auto_reset": True},
    "user_pause": {"duration_hours": None, "auto_reset": False},
    "no_response": {"duration_hours": 4, "auto_reset": True, "threshold": 2}
}

# ============================================================================
# DATABASE
# ============================================================================

class CISDatabase:
    def __init__(self, db_path: str = "/opt/fpai/aria/cis.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database with schema and seed data."""
        schema_path = Path(__file__).parent / "schema.sql"
        seed_path = Path(__file__).parent / "seed.sql"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Run schema
        if schema_path.exists():
            cursor.executescript(schema_path.read_text())
        
        # Run seed
        if seed_path.exists():
            cursor.executescript(seed_path.read_text())
        
        conn.commit()
        conn.close()
    
    def _conn(self):
        return sqlite3.connect(self.db_path)
    
    def get_user_state(self, user_id: str) -> Optional[UserState]:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT state, intensity, confidence, source, captured_at
            FROM user_state WHERE user_id = ?
            ORDER BY captured_at DESC LIMIT 1
        """, (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return UserState(
                state=row[0],
                intensity=row[1],
                confidence=row[2],
                source=row[3],
                captured_at=row[4]
            )
        return None
    
    def save_state(self, user_id: str, state: str, intensity: int, 
                   confidence: str = "medium", source: str = "explicit") -> UserState:
        """Save current state and archive to history."""
        conn = self._conn()
        cursor = conn.cursor()
        
        state_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        expires = (datetime.now() + timedelta(hours=4)).isoformat()
        
        # Update current state
        cursor.execute("DELETE FROM user_state WHERE user_id = ?", (user_id,))
        cursor.execute("""
            INSERT INTO user_state (id, user_id, state, intensity, confidence, source, captured_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (state_id, user_id, state, intensity, confidence, source, now, expires))
        
        # Archive to history
        history_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO state_history (id, user_id, state, intensity, confidence, source, captured_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (history_id, user_id, state, intensity, confidence, source, now))
        
        conn.commit()
        conn.close()
        
        return UserState(state=state, intensity=intensity, confidence=confidence, 
                        source=source, captured_at=now)
    
    def get_state_history(self, user_id: str, hours: int = 24) -> List[UserState]:
        conn = self._conn()
        cursor = conn.cursor()
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        cursor.execute("""
            SELECT state, intensity, confidence, source, captured_at
            FROM state_history WHERE user_id = ? AND captured_at > ?
            ORDER BY captured_at DESC
        """, (user_id, since))
        rows = cursor.fetchall()
        conn.close()
        
        return [UserState(state=r[0], intensity=r[1], confidence=r[2], 
                         source=r[3], captured_at=r[4]) for r in rows]
    
    def get_actions(self, state: str = None, intensity: int = None) -> List[Action]:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM actions WHERE active = 1")
        rows = cursor.fetchall()
        conn.close()
        
        actions = []
        for r in rows:
            effective_states = json.loads(r[10]) if r[10] else []
            action = Action(
                id=r[0], action_key=r[1], category=r[2], name=r[3],
                instruction=r[5], duration_seconds=r[6],
                effective_states=effective_states,
                min_intensity=r[11], max_intensity=r[12]
            )
            
            # Filter by state and intensity if provided
            if state and state not in action.effective_states:
                continue
            if intensity:
                if intensity < action.min_intensity or intensity > action.max_intensity:
                    continue
            
            actions.append(action)
        
        return actions
    
    def get_action_weight(self, user_id: str, action_id: str, state: str) -> float:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT weight FROM action_weights 
            WHERE user_id = ? AND action_id = ? AND state = ?
        """, (user_id, action_id, state))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 1.0
    
    def get_recent_deliveries(self, user_id: str, minutes: int = 60) -> int:
        conn = self._conn()
        cursor = conn.cursor()
        since = (datetime.now() - timedelta(minutes=minutes)).isoformat()
        cursor.execute("""
            SELECT COUNT(*) FROM delivery_log 
            WHERE user_id = ? AND delivered_at > ?
        """, (user_id, since))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_active_fuses(self, user_id: str) -> List[Dict]:
        conn = self._conn()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            SELECT fuse_type, triggered_at, expires_at, reason 
            FROM fuses 
            WHERE user_id = ? AND active = 1 AND (expires_at IS NULL OR expires_at > ?)
        """, (user_id, now))
        rows = cursor.fetchall()
        conn.close()
        return [{"type": r[0], "triggered_at": r[1], "expires_at": r[2], "reason": r[3]} for r in rows]
    
    def create_fuse(self, user_id: str, fuse_type: str, duration_hours: Optional[int], reason: str):
        conn = self._conn()
        cursor = conn.cursor()
        fuse_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        expires = (datetime.now() + timedelta(hours=duration_hours)).isoformat() if duration_hours else None
        cursor.execute("""
            INSERT INTO fuses (id, user_id, fuse_type, triggered_at, expires_at, reason, active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (fuse_id, user_id, fuse_type, now, expires, reason))
        conn.commit()
        conn.close()
    
    def deactivate_fuse(self, user_id: str, fuse_type: str):
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE fuses SET active = 0 WHERE user_id = ? AND fuse_type = ?
        """, (user_id, fuse_type))
        conn.commit()
        conn.close()
    
    def log_intervention(self, user_id: str, action_id: Optional[str], trigger_type: str,
                         state: str, intensity: int, confidence: str,
                         decision_type: str, decision_confidence: float,
                         channel: str, message: str) -> str:
        conn = self._conn()
        cursor = conn.cursor()
        intervention_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO interventions 
            (id, user_id, action_id, trigger_type, state_at_trigger, intensity_at_trigger,
             confidence_at_trigger, decision_type, decision_confidence, channel, message_sent, 
             delivered_at, outcome)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (intervention_id, user_id, action_id, trigger_type, state, intensity,
              confidence, decision_type, decision_confidence, channel, message, now))
        conn.commit()
        conn.close()
        return intervention_id
    
    def log_delivery(self, user_id: str, channel: str, message_type: str):
        conn = self._conn()
        cursor = conn.cursor()
        delivery_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO delivery_log (id, user_id, channel, message_type, delivered_at)
            VALUES (?, ?, ?, ?, ?)
        """, (delivery_id, user_id, channel, message_type, now))
        conn.commit()
        conn.close()
    
    def get_pending_intervention(self, user_id: str) -> Optional[Dict]:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, action_id, state_at_trigger, intensity_at_trigger
            FROM interventions 
            WHERE user_id = ? AND outcome = 'pending'
            ORDER BY delivered_at DESC LIMIT 1
        """, (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"id": row[0], "action_id": row[1], "state": row[2], "intensity": row[3]}
        return None
    
    def update_outcome(self, intervention_id: str, outcome: str, intensity_after: Optional[int]):
        conn = self._conn()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE interventions 
            SET outcome = ?, outcome_at = ?, intensity_after = ?
            WHERE id = ?
        """, (outcome, now, intensity_after, intervention_id))
        conn.commit()
        conn.close()
    
    def update_action_weight(self, user_id: str, action_id: str, state: str, 
                             outcome: str, intensity_before: int, intensity_after: Optional[int]):
        """Update action weight based on outcome - the learning engine."""
        conn = self._conn()
        cursor = conn.cursor()
        
        # Get current weight data
        cursor.execute("""
            SELECT trials, successes, avg_delta, weight FROM action_weights
            WHERE user_id = ? AND action_id = ? AND state = ?
        """, (user_id, action_id, state))
        row = cursor.fetchone()
        
        if row:
            trials, successes, avg_delta, weight = row
        else:
            trials, successes, avg_delta, weight = 0, 0, 0.0, 1.0
        
        # Calculate update
        is_success = outcome == "helped"
        delta = (intensity_before - intensity_after) if intensity_after else (1 if is_success else 0)
        
        new_trials = trials + 1
        new_successes = successes + (1 if is_success else 0)
        new_avg_delta = (avg_delta * trials + delta) / new_trials
        
        # Weight formula
        success_rate = new_successes / new_trials
        delta_normalized = max(0, min(1, new_avg_delta / 3))
        new_weight = success_rate * (0.5 + delta_normalized * 0.5)
        new_weight = max(0.1, min(2.0, new_weight))
        
        now = datetime.now().isoformat()
        
        if row:
            cursor.execute("""
                UPDATE action_weights 
                SET trials = ?, successes = ?, avg_delta = ?, weight = ?, 
                    last_used = ?, last_outcome = ?
                WHERE user_id = ? AND action_id = ? AND state = ?
            """, (new_trials, new_successes, new_avg_delta, new_weight, 
                  now, outcome, user_id, action_id, state))
        else:
            weight_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO action_weights 
                (id, user_id, action_id, state, trials, successes, avg_delta, weight, last_used, last_outcome)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (weight_id, user_id, action_id, state, new_trials, new_successes, 
                  new_avg_delta, new_weight, now, outcome))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Weight updated: action={action_id} state={state} weight={new_weight:.2f}")

# ============================================================================
# ENGINES
# ============================================================================

class TriggerEngine:
    """Determines when to intervene."""
    
    def __init__(self, db: CISDatabase):
        self.db = db
    
    def evaluate(self, user_id: str, current_state: UserState) -> TriggerResult:
        """Evaluate all triggers and return the best one."""
        
        # Check fuses first
        active_fuses = self.db.get_active_fuses(user_id)
        if active_fuses:
            return TriggerResult(False, None, 0, f"fuse_active: {active_fuses[0]['type']}")
        
        # Check rate limits
        recent = self.db.get_recent_deliveries(user_id, 60)
        if recent >= TRIGGER_CONFIG["RATE_LIMITS"]["max_pings_per_hour"]:
            return TriggerResult(False, None, 0, "rate_limited")
        
        # Get history
        history = self.db.get_state_history(user_id, 24)
        
        # Evaluate each trigger type
        triggers = [
            self._eval_spike(current_state, history),
            self._eval_stuck(current_state, history),
            self._eval_silence_drift(current_state, history)
        ]
        
        # Return highest confidence trigger that fires
        candidates = [t for t in triggers if t.should_fire]
        if not candidates:
            return TriggerResult(False, None, 0, "no_trigger")
        
        return max(candidates, key=lambda t: t.confidence)
    
    def _eval_spike(self, current: UserState, history: List[UserState]) -> TriggerResult:
        """Detect intensity spike."""
        if len(history) < 2:
            return TriggerResult(False, "spike", 0, "insufficient_history")
        
        window_minutes = TRIGGER_CONFIG["SPIKE"]["window_minutes"]
        window_start = datetime.now() - timedelta(minutes=window_minutes)
        
        recent = [h for h in history if datetime.fromisoformat(h.captured_at) > window_start]
        if not recent:
            return TriggerResult(False, "spike", 0, "no_recent")
        
        oldest = recent[-1]
        jump = current.intensity - oldest.intensity
        
        if jump >= TRIGGER_CONFIG["SPIKE"]["intensity_jump"]:
            confidence_mult = TRIGGER_CONFIG["CONFIDENCE_MULTIPLIER"][current.confidence]
            intrusion_cost = TRIGGER_CONFIG["INTRUSION_COST"][current.state]
            helpfulness = 0.7
            
            score = confidence_mult * helpfulness
            if score > intrusion_cost:
                return TriggerResult(True, "spike", score, f"jump_{jump}")
        
        return TriggerResult(False, "spike", 0, "no_spike")
    
    def _eval_stuck(self, current: UserState, history: List[UserState]) -> TriggerResult:
        """Detect stuck pattern."""
        if current.state != "stuck":
            return TriggerResult(False, "stuck", 0, "not_stuck_state")
        
        repeat_count = TRIGGER_CONFIG["STUCK"]["repeat_count"]
        recent_stuck = [h for h in history[:repeat_count] if h.state == "stuck"]
        
        if len(recent_stuck) >= repeat_count:
            confidence_mult = TRIGGER_CONFIG["CONFIDENCE_MULTIPLIER"][current.confidence]
            return TriggerResult(True, "stuck", confidence_mult * 0.8, f"repeat_{len(recent_stuck)}")
        
        return TriggerResult(False, "stuck", 0, "not_stuck_pattern")
    
    def _eval_silence_drift(self, current: UserState, history: List[UserState]) -> TriggerResult:
        """Detect silence with concerning last state."""
        if not history:
            return TriggerResult(False, "silence_drift", 0, "no_history")
        
        last_capture = datetime.fromisoformat(history[0].captured_at)
        hours_since = (datetime.now() - last_capture).total_seconds() / 3600
        
        if hours_since >= TRIGGER_CONFIG["SILENCE_DRIFT"]["no_signal_hours"]:
            last = history[0]
            if (last.state in TRIGGER_CONFIG["SILENCE_DRIFT"]["concerning_states"] and 
                last.intensity >= TRIGGER_CONFIG["SILENCE_DRIFT"]["min_intensity"]):
                return TriggerResult(True, "silence_drift", 0.6, f"silent_{hours_since:.0f}h")
        
        return TriggerResult(False, "silence_drift", 0, "no_drift")


class DecisionEngine:
    """Decides what action to take."""
    
    def __init__(self, db: CISDatabase):
        self.db = db
    
    def decide(self, user_id: str, current_state: UserState, trigger_type: str) -> Decision:
        """Decide what to do."""
        
        # Low confidence = silence
        if current_state.confidence == "low":
            return Decision("silence", None, None, 0.9, "low_confidence")
        
        # Get eligible actions
        actions = self.db.get_actions(current_state.state, current_state.intensity)
        
        if not actions:
            return Decision("silence", None, None, 0.5, "no_eligible_actions")
        
        # Score actions
        scored = []
        for action in actions:
            weight = self.db.get_action_weight(user_id, action.id, current_state.state)
            state_match = 1.0 if current_state.state in action.effective_states else 0.5
            intensity_match = 1.0 if (action.min_intensity <= current_state.intensity <= action.max_intensity) else 0.3
            
            score = weight * state_match * intensity_match
            scored.append((action, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        best_action, best_score = scored[0]
        
        return Decision(
            type=best_action.category,
            action_id=best_action.id,
            action_key=best_action.action_key,
            confidence=best_score,
            reason="best_match"
        )


class DeliveryEngine:
    """Delivers messages."""
    
    def __init__(self, db: CISDatabase):
        self.db = db
    
    def build_message(self, state: str, intensity: int, action: Action) -> str:
        """Build a minimal, effective message."""
        contexts = {
            "spike": "Load spiking",
            "stuck": "Pattern stuck",
            "overloaded": "Load is high",
            "busy": "Moving fast",
            "calm": "Checking in"
        }
        context = contexts.get(state, "Checking in")
        return f"{context}. {action.instruction} Reply: helped / same / no"
    
    async def deliver(self, user_id: str, decision: Decision, 
                      action: Optional[Action], trigger_type: str,
                      current_state: UserState) -> Dict:
        """Deliver the intervention."""
        import httpx
        
        if decision.type == "silence":
            return {"channel": "silent", "message": "", "delivered": True}
        
        if not action:
            return {"channel": "silent", "message": "", "delivered": False}
        
        # Build message
        message = self.build_message(current_state.state, current_state.intensity, action)
        
        # Get telegram config
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        
        if not token or not chat_id:
            logger.warning("No telegram config")
            return {"channel": "telegram", "message": message, "delivered": False}
        
        # Send
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": message}
                )
                delivered = r.status_code == 200
        except Exception as e:
            logger.error(f"Delivery failed: {e}")
            delivered = False
        
        # Log delivery
        self.db.log_delivery(user_id, "telegram", "ping")
        
        # Log intervention
        intervention_id = self.db.log_intervention(
            user_id=user_id,
            action_id=action.id,
            trigger_type=trigger_type,
            state=current_state.state,
            intensity=current_state.intensity,
            confidence=current_state.confidence,
            decision_type=decision.type,
            decision_confidence=decision.confidence,
            channel="telegram",
            message=message
        )
        
        return {
            "channel": "telegram", 
            "message": message, 
            "delivered": delivered,
            "intervention_id": intervention_id
        }


class LearningEngine:
    """Processes outcomes and updates weights."""
    
    def __init__(self, db: CISDatabase):
        self.db = db
    
    def process_outcome(self, user_id: str, outcome: str, intensity_after: Optional[int] = None):
        """Process an outcome and update learning."""
        pending = self.db.get_pending_intervention(user_id)
        if not pending:
            logger.warning("No pending intervention to process outcome for")
            return
        
        # Update intervention
        self.db.update_outcome(pending["id"], outcome, intensity_after)
        
        # Update action weight
        if pending["action_id"]:
            self.db.update_action_weight(
                user_id=user_id,
                action_id=pending["action_id"],
                state=pending["state"],
                outcome=outcome,
                intensity_before=pending["intensity"],
                intensity_after=intensity_after
            )
        
        logger.info(f"Outcome processed: {outcome}")


class FuseSystem:
    """Guardrails and safety."""
    
    def __init__(self, db: CISDatabase):
        self.db = db
    
    def check_and_trigger(self, user_id: str, current_state: UserState):
        """Check conditions and trigger fuses if needed."""
        
        # Distress fuse
        if current_state.intensity == 5:
            self.db.create_fuse(user_id, "distress", 
                               FUSE_CONFIG["distress"]["duration_hours"],
                               "intensity_5_detected")
            logger.info("Distress fuse triggered")
    
    def pause(self, user_id: str, hours: Optional[int] = None):
        """User-requested pause."""
        self.db.create_fuse(user_id, "user_pause", hours, "user_requested")
    
    def resume(self, user_id: str):
        """Resume from pause."""
        self.db.deactivate_fuse(user_id, "user_pause")


# ============================================================================
# MAIN CIS CLASS
# ============================================================================

class CIS:
    """Continuity Intelligence System - Main orchestrator."""
    
    def __init__(self, db_path: str = "/opt/fpai/aria/cis.db"):
        self.db = CISDatabase(db_path)
        self.triggers = TriggerEngine(self.db)
        self.decisions = DecisionEngine(self.db)
        self.delivery = DeliveryEngine(self.db)
        self.learning = LearningEngine(self.db)
        self.fuses = FuseSystem(self.db)
    
    async def capture_state(self, user_id: str, state: str, intensity: int,
                            confidence: str = "high", source: str = "explicit") -> Dict:
        """Capture user state and potentially trigger intervention."""
        
        # Save state
        current = self.db.save_state(user_id, state, intensity, confidence, source)
        
        # Check fuses
        self.fuses.check_and_trigger(user_id, current)
        
        # Evaluate triggers
        trigger = self.triggers.evaluate(user_id, current)
        
        result = {"state": current, "trigger": trigger.trigger_type}
        
        if trigger.should_fire:
            # Decide
            decision = self.decisions.decide(user_id, current, trigger.trigger_type)
            
            if decision.type != "silence":
                # Get action
                action = None
                if decision.action_id:
                    actions = self.db.get_actions()
                    action = next((a for a in actions if a.id == decision.action_id), None)
                
                # Deliver
                delivery = await self.delivery.deliver(
                    user_id, decision, action, trigger.trigger_type, current
                )
                
                result["intervention"] = {
                    "action": decision.action_key,
                    "message": delivery["message"],
                    "delivered": delivery["delivered"]
                }
        
        return result
    
    def capture_outcome(self, user_id: str, outcome: str, intensity_after: Optional[int] = None):
        """Capture outcome of an intervention."""
        self.learning.process_outcome(user_id, outcome, intensity_after)
    
    def pause(self, user_id: str, hours: Optional[int] = None):
        """Pause interventions."""
        self.fuses.pause(user_id, hours)
    
    def resume(self, user_id: str):
        """Resume interventions."""
        self.fuses.resume(user_id)
    
    def get_status(self, user_id: str) -> Dict:
        """Get current system status for user."""
        current = self.db.get_user_state(user_id)
        fuses = self.db.get_active_fuses(user_id)
        history = self.db.get_state_history(user_id, 24)
        
        return {
            "current_state": current,
            "active_fuses": fuses,
            "states_last_24h": len(history),
            "recent_deliveries": self.db.get_recent_deliveries(user_id, 60)
        }


# ============================================================================
# PARSE HELPERS
# ============================================================================

STATE_MAP = {
    'calm': 'calm', 'chill': 'calm', 'good': 'calm', 'fine': 'calm', 'ok': 'calm',
    'busy': 'busy', 'working': 'busy', 'active': 'busy',
    'overloaded': 'overloaded', 'overwhelmed': 'overloaded', 'drowning': 'overloaded',
    'stuck': 'stuck', 'blocked': 'stuck', 'frozen': 'stuck',
    'open': 'open', 'ready': 'open', 'available': 'open'
}

def parse_state_input(raw: str) -> Dict:
    """Parse natural language state input."""
    import re
    parts = raw.lower().strip().split()
    
    state = 'busy'
    intensity = 3
    confidence = 'medium'
    
    for part in parts:
        if part in STATE_MAP:
            state = STATE_MAP[part]
            confidence = 'high'
        elif re.match(r'^[1-5]$', part):
            intensity = int(part)
    
    return {"state": state, "intensity": intensity, "confidence": confidence}

def parse_outcome_input(raw: str) -> str:
    """Parse natural language outcome input."""
    text = raw.lower().strip()
    
    if any(w in text for w in ['helped', 'yes', 'better', 'good', 'worked', 'y', '👍']):
        return 'helped'
    elif any(w in text for w in ['no', 'worse', 'bad', 'didnt', "didn't", 'nope', 'n', '👎']):
        return 'no'
    else:
        return 'same'


# Singleton instance
_cis: Optional[CIS] = None

def get_cis() -> CIS:
    global _cis
    if _cis is None:
        _cis = CIS()
    return _cis









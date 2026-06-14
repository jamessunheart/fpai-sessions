"""
SUPABASE CLIENT - Cold Memory Layer
====================================

Provides structured, queryable, versioned data storage.
This is the "nervous system" of Apprentice OS.

Usage:
    from integrations.supabase_client import get_supabase_client
    
    client = get_supabase_client()
    
    # Query metrics
    metrics = await client.get_apprentice_metrics("aria")
    
    # Log event
    await client.log_event("metric.updated", {"metric": "trust_score", "value": 85})
    
    # Check system state
    state = await client.get_system_state("expansion_paused")
"""

import os
import json
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger("aria.integrations.supabase")

# Check if supabase is available
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase library not installed. Cold memory disabled.")


@dataclass
class SupabaseConfig:
    """Supabase connection configuration."""
    url: str
    key: str
    enabled: bool = True


class SupabaseClient:
    """
    Client for Supabase cold memory operations.
    
    Handles:
    - Apprentice metrics (time-series)
    - Event logging (audit trail)
    - System state (global flags)
    - Alerts (notifications)
    - Relationships (graph edges)
    """
    
    def __init__(self, config: Optional[SupabaseConfig] = None):
        self.config = config or self._load_config()
        self.client: Optional[Client] = None
        self.enabled = self.config.enabled and SUPABASE_AVAILABLE
        
        if self.enabled:
            self._connect()
    
    def _load_config(self) -> SupabaseConfig:
        """Load config from environment."""
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        enabled = bool(url and key)
        
        if not enabled:
            logger.info("Supabase not configured (SUPABASE_URL/SUPABASE_KEY missing)")
        
        return SupabaseConfig(url=url, key=key, enabled=enabled)
    
    def _connect(self):
        """Establish connection to Supabase."""
        if not SUPABASE_AVAILABLE:
            return
            
        try:
            self.client = create_client(self.config.url, self.config.key)
            logger.info("Connected to Supabase")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            self.enabled = False
    
    # ═══════════════════════════════════════════════════════════════════
    # APPRENTICE METRICS
    # ═══════════════════════════════════════════════════════════════════
    
    async def get_apprentice_metrics(
        self, 
        apprentice_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent metrics for an apprentice."""
        if not self.enabled:
            return []
        
        try:
            # First get apprentice ID
            apprentice = self.client.table("apprentices")\
                .select("id")\
                .eq("name", apprentice_name)\
                .single()\
                .execute()
            
            if not apprentice.data:
                return []
            
            # Get metrics
            result = self.client.table("apprentice_metrics")\
                .select("*")\
                .eq("apprentice_id", apprentice.data["id"])\
                .order("timestamp", desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get apprentice metrics: {e}")
            return []
    
    async def record_metrics(
        self,
        apprentice_name: str,
        trust_score: Optional[float] = None,
        stress_level: Optional[float] = None,
        coherence_score: Optional[float] = None,
        autonomy_score: Optional[float] = None
    ) -> bool:
        """Record new metrics for an apprentice."""
        if not self.enabled:
            return False
        
        try:
            # Get apprentice ID
            apprentice = self.client.table("apprentices")\
                .select("id")\
                .eq("name", apprentice_name)\
                .single()\
                .execute()
            
            if not apprentice.data:
                return False
            
            # Build metrics dict (only include non-None values)
            metrics = {"apprentice_id": apprentice.data["id"]}
            if trust_score is not None:
                metrics["trust_score"] = trust_score
            if stress_level is not None:
                metrics["stress_level"] = stress_level
            if coherence_score is not None:
                metrics["coherence_score"] = coherence_score
            if autonomy_score is not None:
                metrics["autonomy_score"] = autonomy_score
            
            self.client.table("apprentice_metrics").insert(metrics).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to record metrics: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════
    # APPRENTICE ACTIVITY
    # ═══════════════════════════════════════════════════════════════════
    
    async def log_apprentice_activity(
        self,
        telegram_id: int,
        activity_type: str,
        details: Dict[str, Any] = None
    ) -> bool:
        """
        Log apprentice activity for progress tracking.
        
        Args:
            telegram_id: Apprentice's Telegram user ID
            activity_type: Type of activity (message, tool_use, module_create, submission, onboarding)
            details: Additional details about the activity
        """
        if not self.enabled:
            return False
        
        try:
            activity = {
                "telegram_id": telegram_id,
                "activity_type": activity_type,
                "details": details or {}
            }
            
            self.client.table("apprentice_activity").insert(activity).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to log apprentice activity: {e}")
            return False
    
    async def get_apprentice_activity(
        self,
        telegram_id: int,
        activity_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get activity log for an apprentice."""
        if not self.enabled:
            return []
        
        try:
            query = self.client.table("apprentice_activity")\
                .select("*")\
                .eq("telegram_id", telegram_id)\
                .order("created_at", desc=True)\
                .limit(limit)
            
            if activity_type:
                query = query.eq("activity_type", activity_type)
            
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get apprentice activity: {e}")
            return []
    
    async def get_all_apprentice_activity(
        self,
        since_hours: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all apprentice activity (for steward cohort view)."""
        if not self.enabled:
            return []
        
        try:
            from datetime import datetime, timedelta
            since = (datetime.utcnow() - timedelta(hours=since_hours)).isoformat()
            
            result = self.client.table("apprentice_activity")\
                .select("*, apprentices(name, telegram_id)")\
                .gte("created_at", since)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get all apprentice activity: {e}")
            return []
    
    async def get_apprentice_progress(
        self,
        telegram_id: int
    ) -> List[Dict[str, Any]]:
        """Get challenge progress for an apprentice."""
        if not self.enabled:
            return []
        
        try:
            result = self.client.table("apprentice_progress")\
                .select("*")\
                .eq("telegram_id", telegram_id)\
                .order("started_at", desc=True)\
                .execute()
            
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get apprentice progress: {e}")
            return []
    
    async def start_challenge(
        self,
        telegram_id: int,
        challenge_id: str
    ) -> bool:
        """Start a challenge for an apprentice."""
        if not self.enabled:
            return False
        
        try:
            self.client.table("apprentice_progress").upsert({
                "telegram_id": telegram_id,
                "challenge_id": challenge_id,
                "status": "in_progress"
            }, on_conflict="telegram_id,challenge_id").execute()
            return True
        except Exception as e:
            logger.error(f"Failed to start challenge: {e}")
            return False
    
    async def complete_challenge(
        self,
        telegram_id: int,
        challenge_id: str,
        review_notes: str = None
    ) -> bool:
        """Mark a challenge as completed."""
        if not self.enabled:
            return False
        
        try:
            from datetime import datetime
            self.client.table("apprentice_progress")\
                .update({
                    "status": "completed",
                    "completed_at": datetime.utcnow().isoformat(),
                    "review_notes": review_notes
                })\
                .eq("telegram_id", telegram_id)\
                .eq("challenge_id", challenge_id)\
                .execute()
            return True
        except Exception as e:
            logger.error(f"Failed to complete challenge: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════
    # COST TRACKING
    # ═══════════════════════════════════════════════════════════════════
    
    async def log_usage_cost(
        self,
        telegram_id: int,
        operation: str,
        tokens: int = 0,
        cost_usd: float = 0.0,
        model: str = None,
        details: Dict[str, Any] = None
    ) -> bool:
        """
        Log usage cost for a user.
        
        Args:
            telegram_id: User's Telegram ID
            operation: Type of operation (claude_api, openai, voice_tts, etc.)
            tokens: Number of tokens used
            cost_usd: Cost in USD
            model: Model name used
            details: Additional details
        """
        if not self.enabled:
            return False
        
        try:
            cost_entry = {
                "telegram_id": telegram_id,
                "operation": operation,
                "tokens": tokens,
                "cost_usd": cost_usd,
                "model": model,
                "details": details or {}
            }
            
            self.client.table("usage_costs").insert(cost_entry).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to log usage cost: {e}")
            return False
    
    async def get_user_costs(
        self,
        telegram_id: int,
        since_days: int = 30
    ) -> Dict[str, Any]:
        """Get cost summary for a user."""
        if not self.enabled:
            return {"total_cost": 0, "total_tokens": 0, "by_operation": {}}
        
        try:
            from datetime import datetime, timedelta
            since = (datetime.utcnow() - timedelta(days=since_days)).isoformat()
            
            result = self.client.table("usage_costs")\
                .select("operation, cost_usd, tokens")\
                .eq("telegram_id", telegram_id)\
                .gte("created_at", since)\
                .execute()
            
            total_cost = 0
            total_tokens = 0
            by_operation = {}
            
            for row in result.data or []:
                cost = float(row.get("cost_usd", 0) or 0)
                tokens = int(row.get("tokens", 0) or 0)
                op = row.get("operation", "unknown")
                
                total_cost += cost
                total_tokens += tokens
                
                if op not in by_operation:
                    by_operation[op] = {"cost": 0, "tokens": 0, "count": 0}
                by_operation[op]["cost"] += cost
                by_operation[op]["tokens"] += tokens
                by_operation[op]["count"] += 1
            
            return {
                "total_cost": total_cost,
                "total_tokens": total_tokens,
                "by_operation": by_operation
            }
        except Exception as e:
            logger.error(f"Failed to get user costs: {e}")
            return {"total_cost": 0, "total_tokens": 0, "by_operation": {}}
    
    # ═══════════════════════════════════════════════════════════════════
    # EVENTS
    # ═══════════════════════════════════════════════════════════════════
    
    async def log_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None
    ) -> bool:
        """Log an event to the audit trail."""
        if not self.enabled:
            return False
        
        try:
            event = {
                "event_type": event_type,
                "payload": payload
            }
            if entity_type:
                event["entity_type"] = entity_type
            if entity_id:
                event["entity_id"] = entity_id
            
            self.client.table("events").insert(event).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to log event: {e}")
            return False
    
    async def get_recent_events(
        self,
        event_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent events, optionally filtered by type."""
        if not self.enabled:
            return []
        
        try:
            query = self.client.table("events")\
                .select("*")\
                .order("created_at", desc=True)\
                .limit(limit)
            
            if event_type:
                query = query.eq("event_type", event_type)
            
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════════════
    # SYSTEM STATE
    # ═══════════════════════════════════════════════════════════════════
    
    async def get_system_state(self, key: str) -> Optional[Any]:
        """Get a system state value."""
        if not self.enabled:
            return None
        
        try:
            result = self.client.table("system_state")\
                .select("value")\
                .eq("key", key)\
                .single()\
                .execute()
            
            if result.data:
                return result.data["value"]
            return None
        except Exception as e:
            logger.error(f"Failed to get system state: {e}")
            return None
    
    async def set_system_state(self, key: str, value: Any) -> bool:
        """Set a system state value."""
        if not self.enabled:
            return False
        
        try:
            self.client.table("system_state")\
                .upsert({"key": key, "value": value})\
                .execute()
            return True
        except Exception as e:
            logger.error(f"Failed to set system state: {e}")
            return False
    
    async def get_all_system_state(self) -> Dict[str, Any]:
        """Get all system state values."""
        if not self.enabled:
            return {}
        
        try:
            result = self.client.table("system_state")\
                .select("*")\
                .execute()
            
            return {row["key"]: row["value"] for row in (result.data or [])}
        except Exception as e:
            logger.error(f"Failed to get all system state: {e}")
            return {}
    
    # ═══════════════════════════════════════════════════════════════════
    # ALERTS
    # ═══════════════════════════════════════════════════════════════════
    
    async def create_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        source_rule: Optional[str] = None
    ) -> bool:
        """Create a new alert."""
        if not self.enabled:
            return False
        
        try:
            alert = {
                "type": alert_type,
                "severity": severity,
                "message": message
            }
            if source_rule:
                alert["source_rule"] = source_rule
            
            self.client.table("alerts").insert(alert).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            return False
    
    async def get_active_alerts(
        self,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get unresolved alerts."""
        if not self.enabled:
            return []
        
        try:
            query = self.client.table("alerts")\
                .select("*")\
                .eq("resolved", False)\
                .order("created_at", desc=True)
            
            if severity:
                query = query.eq("severity", severity)
            
            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []
    
    async def resolve_alert(self, alert_id: str, resolution: str) -> bool:
        """Mark an alert as resolved."""
        if not self.enabled:
            return False
        
        try:
            self.client.table("alerts")\
                .update({
                    "resolved": True,
                    "resolution": resolution,
                    "resolved_at": datetime.utcnow().isoformat()
                })\
                .eq("id", alert_id)\
                .execute()
            return True
        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════
    # SHADOW COSTS
    # ═══════════════════════════════════════════════════════════════════
    
    async def record_shadow_costs(
        self,
        stress_accumulation: float,
        trust_decay: float,
        optionality_loss: float,
        complexity_creep: float,
        details: Optional[Dict] = None
    ) -> bool:
        """Record a shadow cost snapshot."""
        if not self.enabled:
            return False
        
        try:
            snapshot = {
                "stress_accumulation": stress_accumulation,
                "trust_decay": trust_decay,
                "optionality_loss": optionality_loss,
                "complexity_creep": complexity_creep,
                "computation_details": details or {}
            }
            
            self.client.table("shadow_cost_snapshots").insert(snapshot).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to record shadow costs: {e}")
            return False
    
    async def get_latest_shadow_costs(self) -> Optional[Dict[str, Any]]:
        """Get the most recent shadow cost snapshot."""
        if not self.enabled:
            return None
        
        try:
            result = self.client.table("shadow_cost_snapshots")\
                .select("*")\
                .order("timestamp", desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to get shadow costs: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════════
    # RELATIONSHIPS / GRAPH
    # ═══════════════════════════════════════════════════════════════════
    
    async def get_relationships(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get relationships for an entity."""
        if not self.enabled:
            return []
        
        try:
            # Get relationships where entity is either from or to
            query_from = self.client.table("relationships").select("*")
            query_to = self.client.table("relationships").select("*")
            
            if entity_type and entity_id:
                query_from = query_from.eq("from_type", entity_type).eq("from_id", entity_id)
                query_to = query_to.eq("to_type", entity_type).eq("to_id", entity_id)
            
            result_from = query_from.execute()
            result_to = query_to.execute()
            
            # Combine and deduplicate
            all_relationships = (result_from.data or []) + (result_to.data or [])
            seen = set()
            unique = []
            for r in all_relationships:
                if r["id"] not in seen:
                    seen.add(r["id"])
                    unique.append(r)
            
            return unique
        except Exception as e:
            logger.error(f"Failed to get relationships: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════════════
    # STATUS
    # ═══════════════════════════════════════════════════════════════════
    
    async def get_status(self) -> Dict[str, Any]:
        """Get Supabase connection status."""
        return {
            "enabled": self.enabled,
            "connected": self.client is not None,
            "url": self.config.url[:30] + "..." if self.config.url else None
        }


# Singleton instance
_supabase_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """Get the singleton SupabaseClient instance."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client


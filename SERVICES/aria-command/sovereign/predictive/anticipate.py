#!/usr/bin/env python3
"""
ARIA ULTRA POWER - ANTICIPATION ENGINE
========================================

Predict user needs before they ask:
- Combine pattern learning with context
- Pre-fetch data for likely queries
- Generate proactive suggestions
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger("aria.predictive.anticipate")


@dataclass
class Prediction:
    """A predicted user need."""
    intent: str
    topic: str
    confidence: float
    reason: str
    prefetched_data: Optional[Dict] = None
    suggested_message: Optional[str] = None
    expires_at: float = field(default_factory=lambda: time.time() + 3600)


class AnticipationEngine:
    """
    Anticipate user needs by combining patterns with current context.
    
    Features:
    - Time-based anticipation
    - Sequence-based prediction
    - Context-aware suggestions
    - Data pre-fetching
    """
    
    def __init__(self):
        self._predictions: Dict[str, List[Prediction]] = {}
        self._prefetch_cache: Dict[str, Dict] = {}
        
        logger.info("AnticipationEngine initialized")
    
    async def predict_needs(self, user_id: str, context: Dict = None) -> List[Prediction]:
        """Predict what user might need."""
        from .patterns import get_pattern_learner
        
        learner = get_pattern_learner()
        predictions = []
        
        # Get time-based predictions
        likely_needs = learner.get_likely_needs_now(user_id)
        for need in likely_needs[:3]:
            if need["confidence"] >= 0.3:
                predictions.append(Prediction(
                    intent=need["intent"],
                    topic=need["topic"],
                    confidence=need["confidence"],
                    reason=f"You usually ask about {need['topic']} around this time",
                ))
        
        # Get sequence-based predictions if we have context
        if context and "last_intent" in context:
            next_pred = learner.predict_next(
                user_id,
                context["last_intent"],
                context.get("last_topic", "")
            )
            if next_pred and next_pred["confidence"] >= 0.3:
                predictions.append(Prediction(
                    intent=next_pred["intent"],
                    topic=next_pred["topic"],
                    confidence=next_pred["confidence"],
                    reason=f"You often ask about {next_pred['topic']} after {context['last_topic']}",
                ))
        
        # Pre-fetch data for high-confidence predictions
        for pred in predictions:
            if pred.confidence >= 0.6:
                pred.prefetched_data = await self._prefetch_data(pred.intent, pred.topic)
                pred.suggested_message = self._generate_suggestion(pred)
        
        # Sort by confidence
        predictions.sort(key=lambda p: p.confidence, reverse=True)
        
        self._predictions[user_id] = predictions
        return predictions
    
    async def _prefetch_data(self, intent: str, topic: str) -> Optional[Dict]:
        """Pre-fetch data for anticipated query."""
        cache_key = f"{intent}:{topic}"
        
        # Check cache
        if cache_key in self._prefetch_cache:
            cached = self._prefetch_cache[cache_key]
            if time.time() - cached.get("_fetched_at", 0) < 300:
                return cached
        
        data = {}
        
        try:
            if intent == "trading" and topic:
                # Pre-fetch trading data
                from sovereign.intel.sentiment import get_unified_sentiment
                us = get_unified_sentiment()
                sentiment = await us.get_sentiment(topic)
                data = {
                    "sentiment": sentiment.to_dict(),
                    "_fetched_at": time.time(),
                }
            
            elif intent == "server":
                # Pre-fetch server status
                import httpx
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get("http://198.54.123.234:8600/health")
                    data = {
                        "server_health": resp.json() if resp.status_code == 200 else None,
                        "_fetched_at": time.time(),
                    }
            
            self._prefetch_cache[cache_key] = data
            return data
        
        except Exception as e:
            logger.error(f"Prefetch error: {e}")
            return None
    
    def _generate_suggestion(self, pred: Prediction) -> str:
        """Generate a proactive suggestion message."""
        if pred.intent == "trading":
            return f"Want me to check the {pred.topic} signals?"
        elif pred.intent == "server":
            return "Should I check the server status?"
        elif pred.intent == "question":
            return f"Any questions about {pred.topic}?"
        else:
            return f"Need help with {pred.topic}?"
    
    def get_predictions(self, user_id: str) -> List[Prediction]:
        """Get cached predictions for a user."""
        predictions = self._predictions.get(user_id, [])
        # Filter out expired
        now = time.time()
        return [p for p in predictions if p.expires_at > now]
    
    def should_act_proactively(self, user_id: str) -> Optional[Prediction]:
        """Determine if we should proactively reach out."""
        predictions = self.get_predictions(user_id)
        
        # Only act if we have a high-confidence prediction
        for pred in predictions:
            if pred.confidence >= 0.7 and pred.prefetched_data:
                return pred
        
        return None


# Singleton instance
_engine: Optional[AnticipationEngine] = None


def get_anticipation_engine() -> AnticipationEngine:
    """Get global AnticipationEngine instance."""
    global _engine
    if _engine is None:
        _engine = AnticipationEngine()
    return _engine


async def predict_next_need(user_id: str, context: Dict = None) -> List[Prediction]:
    """Convenience function to predict needs."""
    engine = get_anticipation_engine()
    return await engine.predict_needs(user_id, context)



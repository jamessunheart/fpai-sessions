#!/usr/bin/env python3
"""
CIS Sensors - Passive Sensing Layer
====================================
Aggregates all sensors to infer state without explicit input.

Sensors:
- Trading: patterns from Hyperliquid activity
- Messages: tone and frequency from conversations
- Silence: drift detection from inactivity
- External: stress factors from environment
"""
import logging
from typing import Dict, Optional
from dataclasses import dataclass

from .trading import sense_trading, TradingSignal
from .messages import sense_message, sense_from_history, MessageSignal
from .silence import sense_silence, SilenceSignal
from .external import sense_external, ExternalSignal

logger = logging.getLogger("cis.sensors")

@dataclass
class AggregatedState:
    """Aggregated state from all sensors."""
    state: str  # calm, busy, overloaded, stuck, open
    intensity: int  # 1-5
    confidence: str  # low, medium, high
    sources: Dict[str, str]  # which sensors contributed what
    should_intervene: bool  # based on aggregate
    intervention_reason: Optional[str]


class SensorAggregator:
    """Aggregates signals from all sensors into a single state inference."""
    
    # State priority (higher = takes precedence when confident)
    STATE_PRIORITY = {
        "overloaded": 4,
        "stuck": 3,
        "busy": 2,
        "calm": 1,
        "open": 0
    }
    
    # Confidence weights
    CONFIDENCE_WEIGHT = {
        "high": 3,
        "medium": 2,
        "low": 1
    }
    
    def aggregate(self, current_message: Optional[str] = None) -> AggregatedState:
        """
        Aggregate all sensor signals into a single state.
        
        Args:
            current_message: If provided, analyze this message too
        """
        sources = {}
        states = []  # List of (state, intensity, confidence, source)
        
        # 1. Trading signals
        try:
            trading = sense_trading()
            if trading:
                states.append((trading.state, trading.intensity, trading.confidence, "trading"))
                sources["trading"] = f"{trading.state} ({trading.intensity})"
        except Exception as e:
            logger.debug(f"Trading sensor error: {e}")
        
        # 2. Message signals (from history or current)
        # Try Claude sentiment analysis first, fall back to keyword
        try:
            if current_message:
                # Try real sentiment analysis
                try:
                    from .sentiment import sync_analyze_sentiment
                    sentiment = sync_analyze_sentiment(current_message)
                    if sentiment:
                        states.append((sentiment.state, sentiment.intensity, sentiment.confidence, "sentiment"))
                        emotions = ", ".join(sentiment.emotions[:2]) if sentiment.emotions else "neutral"
                        sources["sentiment"] = f"{sentiment.state} ({sentiment.intensity}) - {emotions}"
                except Exception as e:
                    # Fall back to keyword analysis
                    msg_signal = sense_message(current_message)
                    states.append((msg_signal.state, msg_signal.intensity, msg_signal.confidence, "message"))
                    sources["message"] = f"{msg_signal.state} ({msg_signal.intensity})"
            else:
                msg_signal = sense_from_history()
                if msg_signal:
                    states.append((msg_signal.state, msg_signal.intensity, msg_signal.confidence, "message_history"))
                    sources["message_history"] = f"{msg_signal.state} ({msg_signal.intensity})"
        except Exception as e:
            logger.debug(f"Message sensor error: {e}")
        
        # 3. Silence signals
        try:
            silence = sense_silence()
            if silence.drift_risk != "none":
                # Convert drift risk to state
                if silence.drift_risk == "high":
                    states.append(("stuck", 4, "medium", "silence"))
                elif silence.drift_risk == "medium":
                    states.append(("busy", 3, "low", "silence"))
                sources["silence"] = f"{silence.drift_risk} drift risk ({silence.hours_silent:.0f}h)"
        except Exception as e:
            logger.debug(f"Silence sensor error: {e}")
        
        # 4. External signals
        try:
            external = sense_external()
            if external.stress_level != "low":
                if external.stress_level == "high":
                    states.append(("overloaded", 4, "medium", "external"))
                else:
                    states.append(("busy", 3, "low", "external"))
                sources["external"] = f"{external.stress_level} stress ({', '.join(external.factors)})"
        except Exception as e:
            logger.debug(f"External sensor error: {e}")
        
        # Aggregate states
        if not states:
            return AggregatedState(
                state="calm",
                intensity=2,
                confidence="low",
                sources={},
                should_intervene=False,
                intervention_reason=None
            )
        
        # Weighted voting based on confidence and state priority
        state_scores = {}
        intensity_sum = 0
        weight_sum = 0
        
        for state, intensity, confidence, source in states:
            weight = self.CONFIDENCE_WEIGHT.get(confidence, 1)
            priority = self.STATE_PRIORITY.get(state, 1)
            
            score = weight * priority
            state_scores[state] = state_scores.get(state, 0) + score
            
            intensity_sum += intensity * weight
            weight_sum += weight
        
        # Pick highest scoring state
        final_state = max(state_scores.keys(), key=lambda s: state_scores[s])
        final_intensity = round(intensity_sum / weight_sum) if weight_sum > 0 else 3
        
        # Determine confidence based on agreement
        agreement = sum(1 for s, _, _, _ in states if s == final_state) / len(states)
        if agreement >= 0.7:
            final_confidence = "high"
        elif agreement >= 0.4:
            final_confidence = "medium"
        else:
            final_confidence = "low"
        
        # Should we intervene?
        should_intervene = False
        intervention_reason = None
        
        if final_state in ["overloaded", "stuck"] and final_intensity >= 4:
            should_intervene = True
            intervention_reason = f"{final_state} detected (intensity {final_intensity})"
        
        # Check silence for drift
        try:
            silence = sense_silence()
            if silence.should_check_in:
                should_intervene = True
                intervention_reason = f"drift risk after {silence.hours_silent:.0f}h silence"
        except:
            pass
        
        return AggregatedState(
            state=final_state,
            intensity=final_intensity,
            confidence=final_confidence,
            sources=sources,
            should_intervene=should_intervene,
            intervention_reason=intervention_reason
        )


# Singleton
_aggregator: Optional[SensorAggregator] = None

def get_aggregator() -> SensorAggregator:
    global _aggregator
    if _aggregator is None:
        _aggregator = SensorAggregator()
    return _aggregator

def sense_all(current_message: Optional[str] = None) -> AggregatedState:
    """Aggregate all sensors and return unified state."""
    return get_aggregator().aggregate(current_message)


__all__ = [
    'sense_trading', 'TradingSignal',
    'sense_message', 'sense_from_history', 'MessageSignal',
    'sense_silence', 'SilenceSignal',
    'sense_external', 'ExternalSignal',
    'sense_all', 'AggregatedState',
    'SensorAggregator', 'get_aggregator'
]


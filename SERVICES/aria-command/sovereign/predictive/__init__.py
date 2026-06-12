#!/usr/bin/env python3
"""
ARIA ULTRA POWER - PREDICTIVE INTELLIGENCE
============================================

Anticipate user needs before they ask:
- Deep pattern learning
- Anticipation engine
- Proactive messaging
- Trend prediction
"""

from .patterns import (
    PatternLearner,
    get_pattern_learner,
    UserPattern,
    record_interaction,
    get_user_patterns,
)

from .anticipate import (
    AnticipationEngine,
    get_anticipation_engine,
    Prediction,
    predict_next_need,
)

from .proactive import (
    ProactiveEngine,
    get_proactive_engine,
    ProactiveMessage,
    schedule_proactive,
)

from .trends import (
    TrendPredictor,
    get_trend_predictor,
    TrendPrediction,
    predict_trend,
)

__all__ = [
    # Patterns
    "PatternLearner",
    "get_pattern_learner",
    "UserPattern",
    "record_interaction",
    "get_user_patterns",
    # Anticipation
    "AnticipationEngine",
    "get_anticipation_engine",
    "Prediction",
    "predict_next_need",
    # Proactive
    "ProactiveEngine",
    "get_proactive_engine",
    "ProactiveMessage",
    "schedule_proactive",
    # Trends
    "TrendPredictor",
    "get_trend_predictor",
    "TrendPrediction",
    "predict_trend",
]



#!/usr/bin/env python3
"""
ARIA ULTRA POWER - TREND PREDICTOR
====================================

Predict trends and anticipate problems:
- Server resource trending
- Price momentum prediction
- Pattern completion detection
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque
import statistics

logger = logging.getLogger("aria.predictive.trends")


@dataclass
class DataPoint:
    """A single data point in a time series."""
    timestamp: float
    value: float
    metadata: Dict = field(default_factory=dict)


@dataclass
class TrendPrediction:
    """A predicted trend."""
    metric: str
    current_value: float
    predicted_value: float
    prediction_time: float  # When will it reach predicted value
    confidence: float
    trend_direction: str  # "up", "down", "stable"
    rate_of_change: float  # Per hour
    will_hit_threshold: bool
    threshold: Optional[float] = None
    time_to_threshold: Optional[float] = None  # Seconds
    warning_message: Optional[str] = None


class TrendPredictor:
    """
    Predict trends based on historical data.
    
    Features:
    - Linear regression for simple trends
    - Moving averages for smoothing
    - Threshold breach prediction
    - Anomaly detection
    """
    
    def __init__(self, max_history: int = 1000):
        self._data: Dict[str, deque] = {}  # metric -> deque of DataPoints
        self._max_history = max_history
        self._thresholds: Dict[str, Tuple[float, float]] = {}  # metric -> (warning, critical)
        
        # Default thresholds
        self._thresholds["memory_percent"] = (80, 90)
        self._thresholds["disk_percent"] = (80, 95)
        self._thresholds["cpu_percent"] = (80, 95)
        
        logger.info("TrendPredictor initialized")
    
    def record(self, metric: str, value: float, metadata: Dict = None):
        """Record a data point."""
        if metric not in self._data:
            self._data[metric] = deque(maxlen=self._max_history)
        
        self._data[metric].append(DataPoint(
            timestamp=time.time(),
            value=value,
            metadata=metadata or {},
        ))
    
    def predict(
        self,
        metric: str,
        hours_ahead: float = 2,
        min_points: int = 5
    ) -> Optional[TrendPrediction]:
        """Predict future value of a metric."""
        if metric not in self._data:
            return None
        
        points = list(self._data[metric])
        if len(points) < min_points:
            return None
        
        # Get recent points for trend calculation
        recent = points[-min(30, len(points)):]
        
        # Calculate trend using linear regression
        timestamps = [p.timestamp for p in recent]
        values = [p.value for p in recent]
        
        # Simple linear regression
        n = len(timestamps)
        sum_x = sum(timestamps)
        sum_y = sum(values)
        sum_xy = sum(t * v for t, v in zip(timestamps, values))
        sum_x2 = sum(t * t for t in timestamps)
        
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            slope = 0
        else:
            slope = (n * sum_xy - sum_x * sum_y) / denominator
        
        intercept = (sum_y - slope * sum_x) / n
        
        # Current and predicted values
        current_time = time.time()
        current_value = values[-1]
        future_time = current_time + (hours_ahead * 3600)
        predicted_value = slope * future_time + intercept
        
        # Rate of change per hour
        rate_per_hour = slope * 3600
        
        # Determine trend direction
        if abs(rate_per_hour) < 0.5:
            direction = "stable"
        elif rate_per_hour > 0:
            direction = "up"
        else:
            direction = "down"
        
        # Calculate confidence based on R² and data freshness
        if len(recent) >= 10:
            # Calculate R²
            mean_y = sum_y / n
            ss_tot = sum((v - mean_y) ** 2 for v in values)
            ss_res = sum((v - (slope * t + intercept)) ** 2 for t, v in zip(timestamps, values))
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            confidence = max(0, min(1, r_squared))
        else:
            confidence = len(recent) / 10 * 0.5
        
        # Check threshold
        will_hit = False
        threshold = None
        time_to_threshold = None
        warning_message = None
        
        if metric in self._thresholds:
            warning_thresh, critical_thresh = self._thresholds[metric]
            
            if direction == "up" and predicted_value > warning_thresh:
                will_hit = True
                threshold = warning_thresh
                
                # Time to reach threshold
                if slope > 0:
                    time_to_threshold = (warning_thresh - current_value) / slope
                    hours_to = time_to_threshold / 3600
                    
                    if predicted_value > critical_thresh:
                        warning_message = f"⚠️ {metric} will reach CRITICAL ({critical_thresh}%) in {hours_to:.1f} hours"
                    else:
                        warning_message = f"⚠️ {metric} trending up - will reach {warning_thresh}% in {hours_to:.1f} hours"
        
        return TrendPrediction(
            metric=metric,
            current_value=current_value,
            predicted_value=predicted_value,
            prediction_time=future_time,
            confidence=confidence,
            trend_direction=direction,
            rate_of_change=rate_per_hour,
            will_hit_threshold=will_hit,
            threshold=threshold,
            time_to_threshold=time_to_threshold,
            warning_message=warning_message,
        )
    
    def detect_anomaly(self, metric: str, current_value: float = None) -> Optional[Dict]:
        """Detect if current value is anomalous."""
        if metric not in self._data:
            return None
        
        points = list(self._data[metric])
        if len(points) < 10:
            return None
        
        values = [p.value for p in points]
        
        # Use current value if provided, else latest
        if current_value is None:
            current_value = values[-1]
        
        # Calculate statistics
        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0
        
        if stdev == 0:
            return None
        
        # Z-score
        z_score = abs(current_value - mean) / stdev
        
        if z_score > 3:
            return {
                "is_anomaly": True,
                "severity": "high",
                "current": current_value,
                "expected_mean": mean,
                "z_score": z_score,
                "message": f"Anomaly detected: {metric} is {z_score:.1f} standard deviations from normal",
            }
        elif z_score > 2:
            return {
                "is_anomaly": True,
                "severity": "medium",
                "current": current_value,
                "expected_mean": mean,
                "z_score": z_score,
                "message": f"Unusual value: {metric} is {z_score:.1f} standard deviations from normal",
            }
        
        return None
    
    def get_all_predictions(self, hours_ahead: float = 2) -> List[TrendPrediction]:
        """Get predictions for all tracked metrics."""
        predictions = []
        
        for metric in self._data:
            pred = self.predict(metric, hours_ahead)
            if pred:
                predictions.append(pred)
        
        # Sort by urgency (threshold breaches first)
        predictions.sort(key=lambda p: (
            0 if p.will_hit_threshold else 1,
            p.time_to_threshold or float('inf')
        ))
        
        return predictions
    
    def get_warnings(self, hours_ahead: float = 2) -> List[TrendPrediction]:
        """Get only predictions with warnings."""
        predictions = self.get_all_predictions(hours_ahead)
        return [p for p in predictions if p.will_hit_threshold]
    
    def set_threshold(self, metric: str, warning: float, critical: float):
        """Set thresholds for a metric."""
        self._thresholds[metric] = (warning, critical)
    
    def format_prediction(self, pred: TrendPrediction) -> str:
        """Format prediction for display."""
        direction_emoji = "📈" if pred.trend_direction == "up" else "📉" if pred.trend_direction == "down" else "➡️"
        
        lines = [
            f"{direction_emoji} **{pred.metric}**",
            f"Current: {pred.current_value:.1f}",
            f"Predicted: {pred.predicted_value:.1f} (in {(pred.prediction_time - time.time()) / 3600:.1f}h)",
            f"Rate: {pred.rate_of_change:+.2f}/hour",
            f"Confidence: {pred.confidence:.0%}",
        ]
        
        if pred.warning_message:
            lines.append("")
            lines.append(pred.warning_message)
        
        return "\n".join(lines)


# Singleton instance
_predictor: Optional[TrendPredictor] = None


def get_trend_predictor() -> TrendPredictor:
    """Get global TrendPredictor instance."""
    global _predictor
    if _predictor is None:
        _predictor = TrendPredictor()
    return _predictor


def predict_trend(metric: str, hours_ahead: float = 2) -> Optional[TrendPrediction]:
    """Convenience function to predict a trend."""
    predictor = get_trend_predictor()
    return predictor.predict(metric, hours_ahead)



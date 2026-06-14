"""
Coracle Prediction Tracker & Reflection System
================================================

This module tracks every prediction Coracle makes, measures actual outcomes,
and creates a learning loop to continuously improve prediction accuracy.

THE LOOP:
1. PREDICT → Log prediction with timestamp, price, probabilities
2. WAIT → Let time pass (1h, 4h, 24h checkpoints)
3. MEASURE → Compare predicted vs actual outcomes
4. REFLECT → Identify what worked, what didn't
5. CALIBRATE → Adjust confidence levels and signal weights
6. REPEAT → Each cycle improves accuracy

VALUE CREATION:
- As accuracy improves, expected value of each contract increases
- 55% accuracy → $X value per trade
- 60% accuracy → $2X value per trade
- 65% accuracy → $4X value per trade

The system PROVES its value through tracked performance.
"""

import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum
import httpx

logger = logging.getLogger(__name__)


class PredictionOutcome(str, Enum):
    """Possible outcomes for a prediction."""
    PENDING = "pending"          # Not yet resolved
    CORRECT = "correct"          # Direction was right
    INCORRECT = "incorrect"      # Direction was wrong
    NEUTRAL = "neutral"          # Price stayed flat (within 0.5%)
    TP1_HIT = "tp1_hit"          # Hit TP1
    TP2_HIT = "tp2_hit"          # Hit TP2
    TP3_HIT = "tp3_hit"          # Hit TP3
    SL_HIT = "sl_hit"            # Hit stop loss


@dataclass
class TrackedPrediction:
    """A single tracked prediction with outcome."""
    id: str
    timestamp: str
    symbol: str
    
    # Prediction details
    predicted_direction: str  # LONG, SHORT, NEUTRAL
    direction_probability: float
    confidence: float
    
    # Price at prediction time
    entry_price: float
    
    # Targets
    stop_loss: float
    tp1: float
    tp2: float
    tp3: float
    
    # Probabilities
    tp1_probability: float
    tp2_probability: float
    tp3_probability: float
    
    # Key signals that drove the prediction
    key_signals: Dict[str, Any]
    
    # Gate status
    gate_passed: bool
    gate_keys: int
    
    # Expected value at time of prediction
    expected_value: float
    grade: str
    
    # Outcomes (filled in later)
    outcome_1h: Optional[str] = None
    price_1h: Optional[float] = None
    pnl_1h: Optional[float] = None
    
    outcome_4h: Optional[str] = None
    price_4h: Optional[float] = None
    pnl_4h: Optional[float] = None
    
    outcome_24h: Optional[str] = None
    price_24h: Optional[float] = None
    pnl_24h: Optional[float] = None
    
    # Which targets were hit
    tp1_hit: bool = False
    tp2_hit: bool = False
    tp3_hit: bool = False
    sl_hit: bool = False
    
    # Resolution timestamp
    resolved_at: Optional[str] = None


@dataclass
class AccuracyMetrics:
    """Accuracy metrics for a symbol or overall."""
    total_predictions: int
    correct_predictions: int
    incorrect_predictions: int
    neutral_predictions: int
    pending_predictions: int
    
    # Accuracy rates
    direction_accuracy: float  # % of correct direction calls
    tp1_hit_rate: float  # % of TP1 hits
    tp2_hit_rate: float  # % of TP2 hits
    tp3_hit_rate: float  # % of TP3 hits
    sl_hit_rate: float  # % of SL hits
    
    # Calibration (predicted prob vs actual)
    calibration_error: float  # Lower = better calibrated
    
    # Value metrics
    total_pnl: float
    avg_pnl_per_prediction: float
    
    # Signal performance
    best_signals: List[str]
    worst_signals: List[str]


class PredictionTracker:
    """
    Tracks all Coracle predictions and measures outcomes.
    
    This is the foundation of the learning loop - we can't improve
    what we don't measure.
    """
    
    def __init__(self, data_dir: str = "/opt/fpai/services/coracle-engine/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.predictions_file = self.data_dir / "predictions.json"
        self.metrics_file = self.data_dir / "accuracy_metrics.json"
        self.learnings_file = self.data_dir / "learnings.json"
        
        self.predictions: Dict[str, TrackedPrediction] = {}
        self._load_predictions()
        
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    def _load_predictions(self):
        """Load existing predictions from disk."""
        if self.predictions_file.exists():
            try:
                with open(self.predictions_file) as f:
                    data = json.load(f)
                    for pred_id, pred_data in data.items():
                        self.predictions[pred_id] = TrackedPrediction(**pred_data)
                logger.info(f"Loaded {len(self.predictions)} tracked predictions")
            except Exception as e:
                logger.error(f"Failed to load predictions: {e}")
    
    def _save_predictions(self):
        """Save predictions to disk."""
        try:
            data = {pid: asdict(pred) for pid, pred in self.predictions.items()}
            with open(self.predictions_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save predictions: {e}")
    
    def log_prediction(self, prediction: TrackedPrediction) -> str:
        """Log a new prediction for tracking."""
        self.predictions[prediction.id] = prediction
        self._save_predictions()
        logger.info(f"📝 Logged prediction {prediction.id}: {prediction.symbol} {prediction.predicted_direction}")
        return prediction.id
    
    async def resolve_prediction(self, pred_id: str, timeframe: str = "1h") -> Optional[TrackedPrediction]:
        """
        Resolve a prediction by checking actual price movement.
        
        Args:
            pred_id: The prediction ID
            timeframe: Which timeframe to resolve (1h, 4h, 24h)
        """
        pred = self.predictions.get(pred_id)
        if not pred:
            return None
        
        # Get current price
        current_price = await self._get_current_price(pred.symbol)
        if not current_price:
            return None
        
        # Calculate price change
        price_change_pct = (current_price - pred.entry_price) / pred.entry_price * 100
        
        # Determine outcome
        if pred.predicted_direction == "LONG":
            if current_price >= pred.tp3:
                outcome = PredictionOutcome.TP3_HIT
                pred.tp1_hit = pred.tp2_hit = pred.tp3_hit = True
            elif current_price >= pred.tp2:
                outcome = PredictionOutcome.TP2_HIT
                pred.tp1_hit = pred.tp2_hit = True
            elif current_price >= pred.tp1:
                outcome = PredictionOutcome.TP1_HIT
                pred.tp1_hit = True
            elif current_price <= pred.stop_loss:
                outcome = PredictionOutcome.SL_HIT
                pred.sl_hit = True
            elif current_price > pred.entry_price:
                outcome = PredictionOutcome.CORRECT
            elif abs(price_change_pct) < 0.5:
                outcome = PredictionOutcome.NEUTRAL
            else:
                outcome = PredictionOutcome.INCORRECT
        
        elif pred.predicted_direction == "SHORT":
            if current_price <= pred.tp3:
                outcome = PredictionOutcome.TP3_HIT
                pred.tp1_hit = pred.tp2_hit = pred.tp3_hit = True
            elif current_price <= pred.tp2:
                outcome = PredictionOutcome.TP2_HIT
                pred.tp1_hit = pred.tp2_hit = True
            elif current_price <= pred.tp1:
                outcome = PredictionOutcome.TP1_HIT
                pred.tp1_hit = True
            elif current_price >= pred.stop_loss:
                outcome = PredictionOutcome.SL_HIT
                pred.sl_hit = True
            elif current_price < pred.entry_price:
                outcome = PredictionOutcome.CORRECT
            elif abs(price_change_pct) < 0.5:
                outcome = PredictionOutcome.NEUTRAL
            else:
                outcome = PredictionOutcome.INCORRECT
        else:
            # Neutral prediction
            if abs(price_change_pct) < 1.0:
                outcome = PredictionOutcome.CORRECT
            else:
                outcome = PredictionOutcome.INCORRECT
        
        # Calculate PnL (simulated based on risk)
        risk_pct = abs(pred.entry_price - pred.stop_loss) / pred.entry_price * 100
        if outcome in [PredictionOutcome.TP1_HIT]:
            pnl = risk_pct * 1.0  # 1:1 R:R
        elif outcome in [PredictionOutcome.TP2_HIT]:
            pnl = risk_pct * 2.0  # 2:1 R:R
        elif outcome in [PredictionOutcome.TP3_HIT]:
            pnl = risk_pct * 3.0  # 3:1 R:R
        elif outcome == PredictionOutcome.SL_HIT:
            pnl = -risk_pct
        elif outcome == PredictionOutcome.CORRECT:
            pnl = price_change_pct  # Actual move
        else:
            pnl = price_change_pct if pred.predicted_direction == "LONG" else -price_change_pct
        
        # Update prediction with outcome
        if timeframe == "1h":
            pred.outcome_1h = outcome.value
            pred.price_1h = current_price
            pred.pnl_1h = pnl
        elif timeframe == "4h":
            pred.outcome_4h = outcome.value
            pred.price_4h = current_price
            pred.pnl_4h = pnl
        elif timeframe == "24h":
            pred.outcome_24h = outcome.value
            pred.price_24h = current_price
            pred.pnl_24h = pnl
            pred.resolved_at = datetime.utcnow().isoformat()
        
        self._save_predictions()
        logger.info(f"✅ Resolved {pred_id} ({timeframe}): {outcome.value}, PnL: {pnl:+.2f}%")
        
        return pred
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from Hyperliquid."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://api.hyperliquid.xyz/info",
                    json={"type": "allMids"}
                )
                if resp.status_code == 200:
                    mids = resp.json()
                    return float(mids.get(symbol, 0))
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
        return None
    
    def calculate_accuracy(self, symbol: Optional[str] = None, timeframe: str = "1h") -> AccuracyMetrics:
        """
        Calculate accuracy metrics for predictions.
        
        Args:
            symbol: Filter by symbol (None = all)
            timeframe: Which timeframe to analyze (1h, 4h, 24h)
        """
        # Filter predictions
        preds = list(self.predictions.values())
        if symbol:
            preds = [p for p in preds if p.symbol == symbol]
        
        # Get outcomes for timeframe
        outcomes = []
        for pred in preds:
            if timeframe == "1h" and pred.outcome_1h:
                outcomes.append((pred, pred.outcome_1h, pred.pnl_1h or 0))
            elif timeframe == "4h" and pred.outcome_4h:
                outcomes.append((pred, pred.outcome_4h, pred.pnl_4h or 0))
            elif timeframe == "24h" and pred.outcome_24h:
                outcomes.append((pred, pred.outcome_24h, pred.pnl_24h or 0))
        
        if not outcomes:
            return AccuracyMetrics(
                total_predictions=len(preds),
                correct_predictions=0,
                incorrect_predictions=0,
                neutral_predictions=0,
                pending_predictions=len(preds),
                direction_accuracy=0.0,
                tp1_hit_rate=0.0,
                tp2_hit_rate=0.0,
                tp3_hit_rate=0.0,
                sl_hit_rate=0.0,
                calibration_error=0.0,
                total_pnl=0.0,
                avg_pnl_per_prediction=0.0,
                best_signals=[],
                worst_signals=[]
            )
        
        # Count outcomes
        correct = sum(1 for _, o, _ in outcomes if o in ["correct", "tp1_hit", "tp2_hit", "tp3_hit"])
        incorrect = sum(1 for _, o, _ in outcomes if o in ["incorrect", "sl_hit"])
        neutral = sum(1 for _, o, _ in outcomes if o == "neutral")
        
        # Count TP/SL hits
        tp1_hits = sum(1 for p, _, _ in outcomes if p.tp1_hit)
        tp2_hits = sum(1 for p, _, _ in outcomes if p.tp2_hit)
        tp3_hits = sum(1 for p, _, _ in outcomes if p.tp3_hit)
        sl_hits = sum(1 for p, _, _ in outcomes if p.sl_hit)
        
        # Calculate accuracy
        total = len(outcomes)
        direction_accuracy = correct / total * 100 if total > 0 else 0
        
        # Calculate PnL
        total_pnl = sum(pnl for _, _, pnl in outcomes)
        avg_pnl = total_pnl / total if total > 0 else 0
        
        # Calculate calibration error
        # Compare predicted probability vs actual hit rate
        calibration_errors = []
        for pred, outcome, _ in outcomes:
            actual = 1 if outcome in ["correct", "tp1_hit", "tp2_hit", "tp3_hit"] else 0
            predicted = pred.direction_probability / 100
            calibration_errors.append(abs(actual - predicted))
        
        avg_calibration_error = sum(calibration_errors) / len(calibration_errors) if calibration_errors else 0
        
        # Identify best/worst signals
        signal_performance = {}
        for pred, outcome, pnl in outcomes:
            for sig_name, sig_value in pred.key_signals.items():
                if sig_name not in signal_performance:
                    signal_performance[sig_name] = {"wins": 0, "losses": 0, "pnl": 0}
                
                if outcome in ["correct", "tp1_hit", "tp2_hit", "tp3_hit"]:
                    signal_performance[sig_name]["wins"] += 1
                else:
                    signal_performance[sig_name]["losses"] += 1
                signal_performance[sig_name]["pnl"] += pnl
        
        # Sort signals by win rate
        sorted_signals = sorted(
            signal_performance.items(),
            key=lambda x: x[1]["wins"] / (x[1]["wins"] + x[1]["losses"]) if (x[1]["wins"] + x[1]["losses"]) > 0 else 0,
            reverse=True
        )
        
        best_signals = [s[0] for s in sorted_signals[:3]]
        worst_signals = [s[0] for s in sorted_signals[-3:]] if len(sorted_signals) >= 3 else []
        
        return AccuracyMetrics(
            total_predictions=len(preds),
            correct_predictions=correct,
            incorrect_predictions=incorrect,
            neutral_predictions=neutral,
            pending_predictions=len(preds) - total,
            direction_accuracy=direction_accuracy,
            tp1_hit_rate=tp1_hits / total * 100 if total > 0 else 0,
            tp2_hit_rate=tp2_hits / total * 100 if total > 0 else 0,
            tp3_hit_rate=tp3_hits / total * 100 if total > 0 else 0,
            sl_hit_rate=sl_hits / total * 100 if total > 0 else 0,
            calibration_error=avg_calibration_error * 100,
            total_pnl=total_pnl,
            avg_pnl_per_prediction=avg_pnl,
            best_signals=best_signals,
            worst_signals=worst_signals
        )
    
    def generate_reflection(self) -> Dict[str, Any]:
        """
        Generate a reflection report with learnings.
        
        This is where the LEARNING happens - identifying patterns
        that work and don't work.
        """
        metrics_1h = self.calculate_accuracy(timeframe="1h")
        metrics_4h = self.calculate_accuracy(timeframe="4h")
        metrics_24h = self.calculate_accuracy(timeframe="24h")
        
        # Per-symbol analysis
        symbols = set(p.symbol for p in self.predictions.values())
        symbol_performance = {}
        for sym in symbols:
            sym_metrics = self.calculate_accuracy(symbol=sym, timeframe="1h")
            symbol_performance[sym] = {
                "accuracy": sym_metrics.direction_accuracy,
                "avg_pnl": sym_metrics.avg_pnl_per_prediction,
                "total_predictions": sym_metrics.total_predictions
            }
        
        # Identify learnings
        learnings = []
        
        # Learning 1: Best timeframe
        best_tf = max(
            [("1h", metrics_1h), ("4h", metrics_4h), ("24h", metrics_24h)],
            key=lambda x: x[1].direction_accuracy if x[1].total_predictions > 0 else 0
        )
        if best_tf[1].direction_accuracy > 0:
            learnings.append({
                "type": "timeframe",
                "finding": f"{best_tf[0]} predictions are most accurate ({best_tf[1].direction_accuracy:.1f}%)",
                "action": f"Consider prioritizing {best_tf[0]} timeframe signals"
            })
        
        # Learning 2: Best symbol
        best_sym = max(symbol_performance.items(), key=lambda x: x[1]["accuracy"]) if symbol_performance else None
        worst_sym = min(symbol_performance.items(), key=lambda x: x[1]["accuracy"]) if symbol_performance else None
        
        if best_sym:
            learnings.append({
                "type": "symbol",
                "finding": f"{best_sym[0]} has highest accuracy ({best_sym[1]['accuracy']:.1f}%)",
                "action": f"Weight {best_sym[0]} predictions higher"
            })
        
        if worst_sym and worst_sym[1]["accuracy"] < 50:
            learnings.append({
                "type": "symbol",
                "finding": f"{worst_sym[0]} has low accuracy ({worst_sym[1]['accuracy']:.1f}%)",
                "action": f"Review signals for {worst_sym[0]}, may need different indicators"
            })
        
        # Learning 3: Best signals
        if metrics_1h.best_signals:
            learnings.append({
                "type": "signal",
                "finding": f"Best performing signals: {', '.join(metrics_1h.best_signals)}",
                "action": "Increase weight for these signals"
            })
        
        if metrics_1h.worst_signals:
            learnings.append({
                "type": "signal",
                "finding": f"Worst performing signals: {', '.join(metrics_1h.worst_signals)}",
                "action": "Decrease weight or review these signals"
            })
        
        # Learning 4: Calibration
        if metrics_1h.calibration_error > 15:
            learnings.append({
                "type": "calibration",
                "finding": f"Prediction confidence is over-confident by {metrics_1h.calibration_error:.1f}%",
                "action": "Reduce confidence levels by 10-15%"
            })
        elif metrics_1h.calibration_error < 5 and metrics_1h.direction_accuracy > 55:
            learnings.append({
                "type": "calibration",
                "finding": "Predictions are well-calibrated!",
                "action": "Maintain current confidence calculation"
            })
        
        # Learning 5: Value creation
        if metrics_1h.avg_pnl_per_prediction > 0:
            learnings.append({
                "type": "value",
                "finding": f"Average profit per prediction: {metrics_1h.avg_pnl_per_prediction:+.2f}%",
                "action": "Continue current strategy - positive expected value confirmed"
            })
        else:
            learnings.append({
                "type": "value",
                "finding": f"Average loss per prediction: {metrics_1h.avg_pnl_per_prediction:+.2f}%",
                "action": "Review and tighten entry criteria, consider gate requirements"
            })
        
        reflection = {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "1h": asdict(metrics_1h),
                "4h": asdict(metrics_4h),
                "24h": asdict(metrics_24h)
            },
            "symbol_performance": symbol_performance,
            "learnings": learnings,
            "total_predictions_tracked": len(self.predictions),
            "value_created": metrics_1h.total_pnl
        }
        
        # Save learnings
        try:
            with open(self.learnings_file, 'w') as f:
                json.dump(reflection, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save learnings: {e}")
        
        return reflection
    
    async def get_calibration_adjustment(self) -> Dict[str, float]:
        """
        Calculate calibration adjustments based on historical accuracy.
        
        Returns multipliers to apply to confidence levels.
        """
        metrics = self.calculate_accuracy(timeframe="1h")
        
        if metrics.total_predictions < 10:
            # Not enough data yet
            return {"confidence_multiplier": 1.0, "reason": "Insufficient data (< 10 predictions)"}
        
        # If we're over-confident, reduce multiplier
        # If we're under-confident, increase multiplier
        actual_accuracy = metrics.direction_accuracy / 100
        
        # Average predicted confidence
        preds_with_outcomes = [p for p in self.predictions.values() if p.outcome_1h]
        if not preds_with_outcomes:
            return {"confidence_multiplier": 1.0, "reason": "No resolved predictions"}
        
        avg_predicted = sum(p.direction_probability for p in preds_with_outcomes) / len(preds_with_outcomes) / 100
        
        # Calculate adjustment
        if avg_predicted > 0:
            calibration_multiplier = actual_accuracy / avg_predicted
            # Cap adjustment between 0.7 and 1.3
            calibration_multiplier = max(0.7, min(1.3, calibration_multiplier))
        else:
            calibration_multiplier = 1.0
        
        return {
            "confidence_multiplier": calibration_multiplier,
            "actual_accuracy": actual_accuracy * 100,
            "avg_predicted_confidence": avg_predicted * 100,
            "adjustment": (calibration_multiplier - 1) * 100,
            "reason": f"Based on {len(preds_with_outcomes)} resolved predictions"
        }
    
    async def _resolution_loop(self):
        """Background loop to resolve pending predictions."""
        logger.info("🔄 Prediction resolution loop started")
        
        while self.running:
            try:
                now = datetime.utcnow()
                
                for pred_id, pred in list(self.predictions.items()):
                    pred_time = datetime.fromisoformat(pred.timestamp.replace('Z', '+00:00').replace('+00:00', ''))
                    age = now - pred_time
                    
                    # Resolve 1h predictions
                    if not pred.outcome_1h and age >= timedelta(hours=1):
                        await self.resolve_prediction(pred_id, "1h")
                        await asyncio.sleep(1)  # Rate limit
                    
                    # Resolve 4h predictions
                    if not pred.outcome_4h and age >= timedelta(hours=4):
                        await self.resolve_prediction(pred_id, "4h")
                        await asyncio.sleep(1)
                    
                    # Resolve 24h predictions
                    if not pred.outcome_24h and age >= timedelta(hours=24):
                        await self.resolve_prediction(pred_id, "24h")
                        await asyncio.sleep(1)
                
                # Generate reflection every 6 hours
                if now.hour % 6 == 0 and now.minute < 5:
                    self.generate_reflection()
                
                # Sleep for 5 minutes
                await asyncio.sleep(300)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Resolution loop error: {e}")
                await asyncio.sleep(60)
        
        logger.info("Prediction resolution loop stopped")
    
    def start(self):
        """Start the background resolution loop."""
        if self.running:
            return
        self.running = True
        self._task = asyncio.create_task(self._resolution_loop())
    
    def stop(self):
        """Stop the background loop."""
        self.running = False
        if self._task:
            self._task.cancel()


# Singleton
_tracker: Optional[PredictionTracker] = None


def get_prediction_tracker() -> PredictionTracker:
    """Get or create the tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = PredictionTracker()
    return _tracker


def create_tracked_prediction(
    symbol: str,
    direction: str,
    direction_probability: float,
    confidence: float,
    entry_price: float,
    stop_loss: float,
    tp1: float,
    tp2: float,
    tp3: float,
    tp1_probability: float,
    tp2_probability: float,
    tp3_probability: float,
    key_signals: Dict[str, Any],
    gate_passed: bool,
    gate_keys: int,
    expected_value: float,
    grade: str
) -> TrackedPrediction:
    """Helper to create a tracked prediction."""
    import uuid
    
    return TrackedPrediction(
        id=f"{symbol}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        timestamp=datetime.utcnow().isoformat(),
        symbol=symbol,
        predicted_direction=direction,
        direction_probability=direction_probability,
        confidence=confidence,
        entry_price=entry_price,
        stop_loss=stop_loss,
        tp1=tp1,
        tp2=tp2,
        tp3=tp3,
        tp1_probability=tp1_probability,
        tp2_probability=tp2_probability,
        tp3_probability=tp3_probability,
        key_signals=key_signals,
        gate_passed=gate_passed,
        gate_keys=gate_keys,
        expected_value=expected_value,
        grade=grade
    )



"""
Locked Prediction Tracking System
==================================

Tracks predictions at different timeframes:
- HOURLY: Locked for 1 hour, resolved after
- DAILY: Locked for 24 hours, resolved after
- WEEKLY: Locked for 7 days, resolved after

Each prediction is immutable once locked. We track:
- Direction predicted (LONG/SHORT)
- Price at lock time
- Actual outcome
- Accuracy (correct/incorrect)
- Distance (how far price moved in predicted direction)
"""

import json
import asyncio
import httpx
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict, field
from enum import Enum

logger = logging.getLogger(__name__)


class Timeframe(str, Enum):
    HOURLY = "1h"
    DAILY = "24h"
    WEEKLY = "7d"


class PredictionStatus(str, Enum):
    LOCKED = "locked"       # Waiting for resolution
    CORRECT = "correct"     # Direction was right
    INCORRECT = "incorrect" # Direction was wrong
    NEUTRAL = "neutral"     # Price didn't move much


@dataclass
class LockedPrediction:
    """A single locked prediction with full contract details."""
    id: str
    symbol: str
    timeframe: str
    
    # Lock time and price
    locked_at: str
    locked_price: float  # Entry price
    
    # Prediction
    direction: str  # LONG or SHORT
    confidence: float  # 0-100%
    
    # Full Contract Details
    stop_loss: float  # SL price
    tp1: float  # Take Profit 1 (conservative)
    tp2: float  # Take Profit 2 (moderate)
    tp3: float  # Take Profit 3 (aggressive)
    
    # Risk/Reward metrics
    risk_pct: float = 0.0  # % distance to SL
    reward_pct: float = 0.0  # % distance to TP2
    rr_ratio: float = 0.0  # Reward/Risk ratio
    
    # Legacy fields for compatibility
    target_price: float = 0.0  # = TP2
    stop_price: float = 0.0  # = SL
    
    # Key signals that drove prediction
    key_signals: Dict[str, str] = field(default_factory=dict)
    
    # Resolution (filled in later)
    status: str = "locked"
    resolved_at: Optional[str] = None
    resolved_price: Optional[float] = None
    
    # Detailed outcome tracking
    price_change_pct: Optional[float] = None
    direction_correct: Optional[bool] = None
    sl_hit: Optional[bool] = None
    tp1_hit: Optional[bool] = None
    tp2_hit: Optional[bool] = None
    tp3_hit: Optional[bool] = None
    max_favorable_move: Optional[float] = None  # Best move in predicted direction
    max_adverse_move: Optional[float] = None  # Worst move against prediction
    
    # Legacy
    target_reached: Optional[bool] = None
    distance_to_target_pct: Optional[float] = None
    
    # Resolution expires at
    expires_at: str = ""


@dataclass
class AccuracyStats:
    """Accuracy statistics for a symbol/timeframe combination."""
    symbol: str
    timeframe: str
    
    total_predictions: int = 0
    correct: int = 0
    incorrect: int = 0
    neutral: int = 0
    pending: int = 0
    
    accuracy_pct: float = 0.0
    avg_distance_when_correct: float = 0.0
    avg_distance_when_wrong: float = 0.0
    
    best_prediction_pct: float = 0.0
    worst_prediction_pct: float = 0.0


class LockedPredictionTracker:
    """
    Manages locked predictions across all timeframes.
    """
    
    TIMEFRAME_DURATIONS = {
        Timeframe.HOURLY: timedelta(hours=1),
        Timeframe.DAILY: timedelta(hours=24),
        Timeframe.WEEKLY: timedelta(days=7),
    }
    
    def __init__(self, data_dir: str = "/opt/fpai/services/coracle-engine/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.predictions_file = self.data_dir / "locked_predictions.json"
        self.predictions: Dict[str, LockedPrediction] = {}
        self._load_predictions()
        
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    def _load_predictions(self):
        """Load existing predictions from disk with backwards compatibility."""
        if self.predictions_file.exists():
            try:
                with open(self.predictions_file) as f:
                    data = json.load(f)
                    for pred_id, pred_data in data.items():
                        # Add backwards compatibility for old predictions
                        # If missing new fields, derive them from old fields
                        if 'stop_loss' not in pred_data:
                            pred_data['stop_loss'] = pred_data.get('stop_price', 0)
                        if 'tp1' not in pred_data:
                            target = pred_data.get('target_price', 0)
                            entry = pred_data.get('locked_price', 0)
                            if target and entry:
                                # Derive TPs from the old single target
                                if pred_data.get('direction') == 'LONG':
                                    move = target - entry
                                    pred_data['tp1'] = entry + move * 0.5
                                    pred_data['tp2'] = target
                                    pred_data['tp3'] = entry + move * 1.5
                                else:
                                    move = entry - target
                                    pred_data['tp1'] = entry - move * 0.5
                                    pred_data['tp2'] = target
                                    pred_data['tp3'] = entry - move * 1.5
                            else:
                                pred_data['tp1'] = 0
                                pred_data['tp2'] = target
                                pred_data['tp3'] = 0
                        
                        # Set default values for new tracking fields
                        pred_data.setdefault('risk_pct', 0)
                        pred_data.setdefault('reward_pct', 0)
                        pred_data.setdefault('rr_ratio', 0)
                        pred_data.setdefault('sl_hit', None)
                        pred_data.setdefault('tp1_hit', None)
                        pred_data.setdefault('tp2_hit', None)
                        pred_data.setdefault('tp3_hit', None)
                        pred_data.setdefault('max_favorable_move', None)
                        pred_data.setdefault('max_adverse_move', None)
                        
                        self.predictions[pred_id] = LockedPrediction(**pred_data)
                logger.info(f"Loaded {len(self.predictions)} locked predictions")
            except Exception as e:
                logger.error(f"Failed to load predictions: {e}")
                import traceback
                logger.error(traceback.format_exc())
    
    def _save_predictions(self):
        """Save predictions to disk."""
        try:
            data = {pid: asdict(pred) for pid, pred in self.predictions.items()}
            with open(self.predictions_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save predictions: {e}")
    
    def lock_prediction(
        self,
        symbol: str,
        timeframe: Timeframe,
        direction: str,
        confidence: float,
        current_price: float,
        stop_loss: float,
        tp1: float,
        tp2: float,
        tp3: float,
        key_signals: Dict[str, str],
        # Legacy params for compatibility
        target_price: float = None,
        stop_price: float = None,
    ) -> LockedPrediction:
        """
        Lock a new prediction with full contract details. Once locked, it cannot be changed.
        """
        now = datetime.utcnow()
        duration = self.TIMEFRAME_DURATIONS[timeframe]
        expires_at = now + duration
        
        pred_id = f"{symbol}_{timeframe.value}_{now.strftime('%Y%m%d_%H%M%S')}"
        
        # Calculate risk/reward metrics
        if direction.upper() == "LONG":
            risk_pct = abs(current_price - stop_loss) / current_price * 100
            reward_pct = abs(tp2 - current_price) / current_price * 100
        else:
            risk_pct = abs(stop_loss - current_price) / current_price * 100
            reward_pct = abs(current_price - tp2) / current_price * 100
        
        rr_ratio = reward_pct / risk_pct if risk_pct > 0 else 0
        
        prediction = LockedPrediction(
            id=pred_id,
            symbol=symbol.upper(),
            timeframe=timeframe.value,
            locked_at=now.isoformat(),
            locked_price=current_price,
            direction=direction.upper(),
            confidence=confidence,
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2,
            tp3=tp3,
            risk_pct=risk_pct,
            reward_pct=reward_pct,
            rr_ratio=rr_ratio,
            target_price=target_price or tp2,
            stop_price=stop_price or stop_loss,
            key_signals=key_signals,
            status=PredictionStatus.LOCKED.value,
            expires_at=expires_at.isoformat()
        )
        
        self.predictions[pred_id] = prediction
        self._save_predictions()
        
        logger.info(f"🔒 Locked {timeframe.value}: {symbol} {direction} @ ${current_price:.2f} | SL: ${stop_loss:.2f} | TP: ${tp1:.2f}/{tp2:.2f}/{tp3:.2f} | R:R {rr_ratio:.1f}")
        
        return prediction
    
    async def resolve_prediction(self, pred_id: str) -> Optional[LockedPrediction]:
        """
        Resolve a prediction by checking actual price movement and target hits.
        """
        pred = self.predictions.get(pred_id)
        if not pred or pred.status != PredictionStatus.LOCKED.value:
            return None
        
        # Check if it's time to resolve
        expires = datetime.fromisoformat(pred.expires_at)
        if datetime.utcnow() < expires:
            return None  # Not yet expired
        
        # Get current price
        current_price = await self._get_price(pred.symbol)
        if not current_price:
            return None
        
        # Calculate metrics
        price_change = current_price - pred.locked_price
        price_change_pct = (price_change / pred.locked_price) * 100
        
        # Get contract levels (handle old predictions without new fields)
        sl = getattr(pred, 'stop_loss', None) or getattr(pred, 'stop_price', None) or 0
        tp1 = getattr(pred, 'tp1', None) or 0
        tp2 = getattr(pred, 'tp2', None) or getattr(pred, 'target_price', None) or 0
        tp3 = getattr(pred, 'tp3', None) or 0
        
        # Determine if direction was correct and check target hits
        if pred.direction == "LONG":
            direction_correct = price_change > 0
            # For LONG: price needs to go UP to hit TPs, DOWN to hit SL
            sl_hit = current_price <= sl if sl else False
            tp1_hit = current_price >= tp1 if tp1 else False
            tp2_hit = current_price >= tp2 if tp2 else False
            tp3_hit = current_price >= tp3 if tp3 else False
            max_favorable = max(0, price_change_pct)
            max_adverse = min(0, price_change_pct)
        else:  # SHORT
            direction_correct = price_change < 0
            # For SHORT: price needs to go DOWN to hit TPs, UP to hit SL
            sl_hit = current_price >= sl if sl else False
            tp1_hit = current_price <= tp1 if tp1 else False
            tp2_hit = current_price <= tp2 if tp2 else False
            tp3_hit = current_price <= tp3 if tp3 else False
            max_favorable = max(0, -price_change_pct)
            max_adverse = min(0, -price_change_pct)
        
        # Calculate distance to target
        if pred.direction == "LONG":
            distance_to_target = (tp2 - pred.locked_price) / pred.locked_price * 100 if tp2 else 0
            actual_distance = price_change_pct
        else:
            distance_to_target = (pred.locked_price - tp2) / pred.locked_price * 100 if tp2 else 0
            actual_distance = -price_change_pct
        
        distance_achieved_pct = (actual_distance / distance_to_target * 100) if distance_to_target != 0 else 0
        
        # Determine status (more nuanced)
        if sl_hit:
            status = PredictionStatus.INCORRECT
        elif tp1_hit or tp2_hit or tp3_hit:
            status = PredictionStatus.CORRECT
        elif abs(price_change_pct) < 0.5:  # Less than 0.5% move
            status = PredictionStatus.NEUTRAL
        elif direction_correct:
            status = PredictionStatus.CORRECT
        else:
            status = PredictionStatus.INCORRECT
        
        # Update prediction with all metrics
        pred.status = status.value
        pred.resolved_at = datetime.utcnow().isoformat()
        pred.resolved_price = current_price
        pred.price_change_pct = price_change_pct
        pred.direction_correct = direction_correct
        pred.sl_hit = sl_hit
        pred.tp1_hit = tp1_hit
        pred.tp2_hit = tp2_hit
        pred.tp3_hit = tp3_hit
        pred.max_favorable_move = max_favorable
        pred.max_adverse_move = max_adverse
        pred.target_reached = tp2_hit
        pred.distance_to_target_pct = distance_achieved_pct
        
        self._save_predictions()
        
        # Detailed logging
        hits = []
        if sl_hit: hits.append("SL❌")
        if tp1_hit: hits.append("TP1✓")
        if tp2_hit: hits.append("TP2✓")
        if tp3_hit: hits.append("TP3✓")
        hits_str = f" [{', '.join(hits)}]" if hits else ""
        
        emoji = "✅" if direction_correct else "❌"
        logger.info(f"{emoji} Resolved {pred.timeframe} {pred.symbol}: {pred.direction} @ ${pred.locked_price:.2f} → ${current_price:.2f} ({price_change_pct:+.2f}%){hits_str}")
        
        return pred
    
    async def _get_price(self, symbol: str) -> Optional[float]:
        """Get current price from Hyperliquid."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://api.hyperliquid.xyz/info",
                    json={"type": "allMids"}
                )
                if resp.status_code == 200:
                    mids = resp.json()
                    return float(mids.get(symbol.upper(), 0))
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
        return None
    
    def get_accuracy_stats(
        self, 
        symbol: Optional[str] = None, 
        timeframe: Optional[Timeframe] = None
    ) -> AccuracyStats:
        """Calculate accuracy statistics."""
        # Filter predictions
        preds = list(self.predictions.values())
        
        if symbol:
            preds = [p for p in preds if p.symbol == symbol.upper()]
        if timeframe:
            preds = [p for p in preds if p.timeframe == timeframe.value]
        
        stats = AccuracyStats(
            symbol=symbol or "ALL",
            timeframe=timeframe.value if timeframe else "ALL"
        )
        
        correct_distances = []
        wrong_distances = []
        
        for pred in preds:
            stats.total_predictions += 1
            
            if pred.status == PredictionStatus.LOCKED.value:
                stats.pending += 1
            elif pred.status == PredictionStatus.CORRECT.value:
                stats.correct += 1
                if pred.price_change_pct:
                    correct_distances.append(abs(pred.price_change_pct))
                    if abs(pred.price_change_pct) > stats.best_prediction_pct:
                        stats.best_prediction_pct = abs(pred.price_change_pct)
            elif pred.status == PredictionStatus.INCORRECT.value:
                stats.incorrect += 1
                if pred.price_change_pct:
                    wrong_distances.append(abs(pred.price_change_pct))
                    if abs(pred.price_change_pct) > abs(stats.worst_prediction_pct):
                        stats.worst_prediction_pct = pred.price_change_pct
            else:
                stats.neutral += 1
        
        # Calculate accuracy
        resolved = stats.correct + stats.incorrect + stats.neutral
        if resolved > 0:
            stats.accuracy_pct = (stats.correct / resolved) * 100
        
        if correct_distances:
            stats.avg_distance_when_correct = sum(correct_distances) / len(correct_distances)
        if wrong_distances:
            stats.avg_distance_when_wrong = sum(wrong_distances) / len(wrong_distances)
        
        return stats
    
    def get_current_predictions(self) -> Dict[str, Dict[str, LockedPrediction]]:
        """
        Get current locked predictions organized by symbol and timeframe.
        Returns only the most recent prediction for each symbol/timeframe combo.
        """
        result = {}
        
        for pred in sorted(self.predictions.values(), key=lambda p: p.locked_at, reverse=True):
            if pred.symbol not in result:
                result[pred.symbol] = {}
            
            if pred.timeframe not in result[pred.symbol]:
                result[pred.symbol][pred.timeframe] = pred
        
        return result
    
    def format_dashboard(self) -> str:
        """
        Format a detailed dashboard showing full contract details.
        Organized by TIMEFRAME for clarity.
        """
        now = datetime.utcnow()
        current = self.get_current_predictions()
        
        def fmt_price(p, symbol=""):
            if p is None or p == 0:
                return "---"
            if p < 10: return f"${p:.4f}"
            elif p < 1000: return f"${p:.2f}"
            else: return f"${p:,.0f}"
        
        def get_remaining(pred):
            expires = datetime.fromisoformat(pred.expires_at)
            remaining = expires - now
            if remaining.total_seconds() <= 0:
                return "resolving..."
            hours = int(remaining.total_seconds() // 3600)
            mins = int((remaining.total_seconds() % 3600) // 60)
            if hours >= 24:
                days = hours // 24
                return f"{days}d {hours % 24}h"
            return f"{hours}h {mins}m"
        
        def format_prediction_detail(pred):
            """Format full contract details for a prediction."""
            if not pred:
                return ["  No prediction"]
            
            lines = []
            direction = "🟢 LONG " if pred.direction == "LONG" else "🔴 SHORT"
            status_map = {"locked": "⏳ PENDING", "correct": "✅ CORRECT", "incorrect": "❌ WRONG", "neutral": "➖ NEUTRAL"}
            status = status_map.get(pred.status, "?")
            
            # Line 1: Direction, Entry, Confidence
            conf = getattr(pred, 'confidence', 0) or 0
            lines.append(f"  {direction} @ {fmt_price(pred.locked_price)} | Confidence: {conf:.0f}%")
            
            # Line 2: SL and TPs
            sl = getattr(pred, 'stop_loss', None) or getattr(pred, 'stop_price', None) or 0
            tp1 = getattr(pred, 'tp1', None) or 0
            tp2 = getattr(pred, 'tp2', None) or getattr(pred, 'target_price', None) or 0
            tp3 = getattr(pred, 'tp3', None) or 0
            
            if sl and tp1 and tp2:
                lines.append(f"     SL: {fmt_price(sl)} | TP1: {fmt_price(tp1)} | TP2: {fmt_price(tp2)} | TP3: {fmt_price(tp3)}")
            
            # Line 3: Risk/Reward and Result
            rr = getattr(pred, 'rr_ratio', None) or 0
            risk = getattr(pred, 'risk_pct', None) or 0
            reward = getattr(pred, 'reward_pct', None) or 0
            
            if pred.status == "locked":
                result = f"Expires: {get_remaining(pred)}"
            else:
                change = pred.price_change_pct or 0
                result = f"Result: {change:+.2f}%"
                
                # Show which targets were hit
                hits = []
                if getattr(pred, 'sl_hit', None): hits.append("❌SL")
                if getattr(pred, 'tp1_hit', None): hits.append("✅TP1")
                if getattr(pred, 'tp2_hit', None): hits.append("✅TP2")
                if getattr(pred, 'tp3_hit', None): hits.append("✅TP3")
                if hits:
                    result += f" ({', '.join(hits)})"
            
            if rr > 0:
                lines.append(f"     Risk: {risk:.1f}% | Reward: {reward:.1f}% | R:R = {rr:.1f} | {status} | {result}")
            else:
                lines.append(f"     {status} | {result}")
            
            return lines
        
        lines = [
            "╔═══════════════════════════════════════════════════════════════════════════════╗",
            "║                   🔮 CORACLE PREDICTION CONTRACTS                             ║",
            f"║                   {now.strftime('%Y-%m-%d %H:%M UTC'):^50}        ║",
            "╠═══════════════════════════════════════════════════════════════════════════════╣",
        ]
        
        # ===== HOURLY SECTION =====
        lines.extend([
            "║                                                                               ║",
            "║  ⏰ HOURLY (1h) - Short-term momentum plays                                   ║",
            "║  ═══════════════════════════════════════════════════════════════════════════  ║",
        ])
        for symbol in ["BTC", "ETH", "SOL", "XRP"]:
            pred = current.get(symbol, {}).get("1h")
            lines.append(f"║  【{symbol}】                                                                    ║")
            for detail_line in format_prediction_detail(pred):
                lines.append(f"║{detail_line:<79}║")
            lines.append("║                                                                               ║")
        
        # ===== DAILY SECTION =====
        lines.extend([
            "║  📅 DAILY (24h) - Swing trade setups                                          ║",
            "║  ═══════════════════════════════════════════════════════════════════════════  ║",
        ])
        for symbol in ["BTC", "ETH", "SOL", "XRP"]:
            pred = current.get(symbol, {}).get("24h")
            lines.append(f"║  【{symbol}】                                                                    ║")
            for detail_line in format_prediction_detail(pred):
                lines.append(f"║{detail_line:<79}║")
            lines.append("║                                                                               ║")
        
        # ===== WEEKLY SECTION =====
        lines.extend([
            "║  📆 WEEKLY (7d) - Position trades                                             ║",
            "║  ═══════════════════════════════════════════════════════════════════════════  ║",
        ])
        for symbol in ["BTC", "ETH", "SOL", "XRP"]:
            pred = current.get(symbol, {}).get("7d")
            lines.append(f"║  【{symbol}】                                                                    ║")
            for detail_line in format_prediction_detail(pred):
                lines.append(f"║{detail_line:<79}║")
            lines.append("║                                                                               ║")
        
        # ===== ACCURACY & EDGE SECTION =====
        lines.extend([
            "╠═══════════════════════════════════════════════════════════════════════════════╣",
            "║  📊 PERFORMANCE vs RANDOM (50%)                                               ║",
            "║  ─────────────────────────────────────────────────────────────────────────    ║",
        ])
        
        for tf, tf_name in [(Timeframe.HOURLY, "1H "), (Timeframe.DAILY, "24H"), (Timeframe.WEEKLY, "7D ")]:
            stats = self.get_accuracy_stats(timeframe=tf)
            resolved = stats.correct + stats.incorrect + stats.neutral
            if resolved > 0:
                edge = stats.accuracy_pct - 50  # Edge over random
                edge_emoji = "📈" if edge > 0 else "📉" if edge < 0 else "➖"
                acc_line = f"  {tf_name}: {stats.accuracy_pct:5.1f}% accuracy | Edge vs Random: {edge:+.1f}% {edge_emoji} | ({stats.correct}✓ {stats.incorrect}✗ {stats.neutral}— / {resolved})"
            else:
                acc_line = f"  {tf_name}: Awaiting first resolution..."
            lines.append(f"║{acc_line:<79}║")
        
        lines.extend([
            "║                                                                               ║",
            "║  Legend: SL=Stop Loss | TP1/2/3=Take Profit targets | R:R=Reward:Risk ratio  ║",
            "╚═══════════════════════════════════════════════════════════════════════════════╝",
        ])
        
        return "\n".join(lines)
    
    def format_telegram_dashboard(self) -> str:
        """Format dashboard for Telegram (Markdown) with full contract details."""
        now = datetime.utcnow()
        current = self.get_current_predictions()
        
        def fmt_price(p):
            if p is None or p == 0: return "---"
            if p < 10: return f"${p:.4f}"
            elif p < 1000: return f"${p:.2f}"
            else: return f"${p:,.0f}"
        
        def get_remaining(pred):
            expires = datetime.fromisoformat(pred.expires_at)
            remaining = expires - now
            if remaining.total_seconds() <= 0:
                return "resolving..."
            hours = int(remaining.total_seconds() // 3600)
            mins = int((remaining.total_seconds() % 3600) // 60)
            if hours >= 24:
                days = hours // 24
                return f"{days}d {hours % 24}h"
            return f"{hours}h {mins}m"
        
        def format_pred_detail(pred):
            """Format a single prediction with full contract."""
            if not pred:
                return "No prediction"
            
            dir_emoji = "🟢" if pred.direction == "LONG" else "🔴"
            status_map = {"locked": "⏳", "correct": "✅", "incorrect": "❌", "neutral": "➖"}
            status = status_map.get(pred.status, "?")
            
            # Get contract levels
            sl = getattr(pred, 'stop_loss', None) or getattr(pred, 'stop_price', 0) or 0
            tp1 = getattr(pred, 'tp1', 0) or 0
            tp2 = getattr(pred, 'tp2', None) or getattr(pred, 'target_price', 0) or 0
            tp3 = getattr(pred, 'tp3', 0) or 0
            rr = getattr(pred, 'rr_ratio', 0) or 0
            conf = getattr(pred, 'confidence', 0) or 0
            
            # Result or time remaining
            if pred.status == "locked":
                result = get_remaining(pred)
            else:
                change = pred.price_change_pct or 0
                hits = []
                if getattr(pred, 'sl_hit', None): hits.append("❌SL")
                if getattr(pred, 'tp1_hit', None): hits.append("✓TP1")
                if getattr(pred, 'tp2_hit', None): hits.append("✓TP2")
                if getattr(pred, 'tp3_hit', None): hits.append("✓TP3")
                result = f"{change:+.2f}%" + (f" ({','.join(hits)})" if hits else "")
            
            lines = f"{dir_emoji} *{pred.direction}* @ {fmt_price(pred.locked_price)} | {conf:.0f}% conf\n"
            if sl and tp1:
                lines += f"   SL: {fmt_price(sl)} → TP: {fmt_price(tp1)}/{fmt_price(tp2)}/{fmt_price(tp3)}\n"
            lines += f"   {status} {result}"
            if rr > 0:
                lines += f" | R:R = {rr:.1f}"
            
            return lines
        
        msg = f"""🔮 *CORACLE CONTRACTS*
📅 {now.strftime('%Y-%m-%d %H:%M UTC')}

⏰ *HOURLY* (1h)
"""
        for symbol in ["BTC", "ETH", "SOL", "XRP"]:
            pred = current.get(symbol, {}).get("1h")
            msg += f"*{symbol}*: {format_pred_detail(pred)}\n\n"
        
        msg += """📅 *DAILY* (24h)
"""
        for symbol in ["BTC", "ETH", "SOL", "XRP"]:
            pred = current.get(symbol, {}).get("24h")
            msg += f"*{symbol}*: {format_pred_detail(pred)}\n\n"
        
        msg += """📆 *WEEKLY* (7d)
"""
        for symbol in ["BTC", "ETH", "SOL", "XRP"]:
            pred = current.get(symbol, {}).get("7d")
            msg += f"*{symbol}*: {format_pred_detail(pred)}\n\n"
        
        # Accuracy summary
        msg += """━━━━━━━━━━━━━━━━━━━━
📊 *EDGE vs RANDOM*
"""
        for tf, tf_name in [(Timeframe.HOURLY, "1H"), (Timeframe.DAILY, "24H"), (Timeframe.WEEKLY, "7D")]:
            stats = self.get_accuracy_stats(timeframe=tf)
            resolved = stats.correct + stats.incorrect + stats.neutral
            if resolved > 0:
                edge = stats.accuracy_pct - 50
                edge_icon = "📈" if edge > 0 else "📉" if edge < 0 else "➖"
                msg += f"{tf_name}: *{stats.accuracy_pct:.1f}%* (edge: {edge:+.1f}%) {edge_icon}\n"
            else:
                msg += f"{tf_name}: Waiting...\n"
        
        msg += """
_Contracts locked. Cannot change._
"""
        return msg
    
    async def _resolution_loop(self):
        """Background loop to resolve expired predictions."""
        logger.info("🔄 Locked prediction resolution loop started")
        
        while self.running:
            try:
                now = datetime.utcnow()
                
                for pred_id, pred in list(self.predictions.items()):
                    if pred.status != PredictionStatus.LOCKED.value:
                        continue
                    
                    expires = datetime.fromisoformat(pred.expires_at)
                    if now >= expires:
                        await self.resolve_prediction(pred_id)
                        await asyncio.sleep(1)  # Rate limit
                
                # Sleep for 1 minute
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Resolution loop error: {e}")
                await asyncio.sleep(60)
        
        logger.info("Locked prediction resolution loop stopped")
    
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
_tracker: Optional[LockedPredictionTracker] = None


def get_locked_tracker() -> LockedPredictionTracker:
    """Get or create the tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = LockedPredictionTracker()
    return _tracker


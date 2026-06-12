"""
Coracle Hourly Oracle Report
=============================
Sends hourly probability updates for all tracked tokens.
Shows predictions with confidence ranges even when Sacred Gate hasn't passed.
"""
import asyncio
import httpx
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ContractSetup:
    """Recommended contract setup with probabilities."""
    direction: str  # LONG or SHORT
    direction_probability: float  # Probability this direction is correct
    
    entry: float
    stop_loss: float
    risk_percent: float
    
    # Multiple take profit targets with individual probabilities
    tp1: float
    tp1_probability: float  # Probability of hitting TP1
    tp1_rr: float  # Risk:Reward ratio
    
    tp2: float
    tp2_probability: float
    tp2_rr: float
    
    tp3: float
    tp3_probability: float
    tp3_rr: float
    
    # Overall contract quality
    expected_value: float  # Positive = profitable setup on average
    grade: str  # A, B, C, D, F


@dataclass
class TokenPrediction:
    """Prediction for a single token."""
    symbol: str
    price: float
    direction: str  # LONG, SHORT, NEUTRAL
    confidence: float  # 0-100
    
    # Probabilities of each outcome
    long_probability: float  # Chance price goes up
    short_probability: float  # Chance price goes down
    neutral_probability: float  # Chance it stays flat
    
    # Price targets with probabilities
    bullish_target: float
    bullish_probability: float
    bearish_target: float
    bearish_probability: float
    
    # Range prediction
    range_low: float
    range_high: float
    range_probability: float  # Probability price stays in range
    
    # Recommended contract setup (always provided)
    contract: ContractSetup
    
    # Key signals
    key_signals: Dict[str, str]
    
    # Gate status
    gate_passed: bool
    gate_keys: int


class HourlyOracle:
    """
    Generates hourly prediction reports for all tracked tokens.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = f"http://localhost:{self.settings.port}"
        self.last_report_time: Optional[datetime] = None
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    async def generate_prediction(self, symbol: str) -> Optional[TokenPrediction]:
        """Generate a prediction for a single token."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get signals
                resp = await client.get(f"{self.base_url}/api/signals/{symbol}")
                if resp.status_code != 200:
                    return None
                signals = resp.json()
                
                # Get full analysis
                resp2 = await client.post(
                    f"{self.base_url}/api/analyze",
                    json={"ticker": symbol}
                )
                analysis = resp2.json() if resp2.status_code == 200 else {}
            
            price = signals.get("price", 0)
            if not price:
                return None
            
            # Calculate direction and confidence from signals
            bullish_score = 0
            bearish_score = 0
            signal_count = 0
            
            key_signals = {}
            
            for sig_name in ["bai", "cvd", "wadi", "fgi", "ls_ratio", "fr"]:
                sig = signals.get(sig_name)
                if not sig:
                    continue
                
                signal_val = sig.get("signal", "").upper()
                strength = sig.get("strength", 50)
                signal_count += 1
                
                # Record key signal
                key_signals[sig.get("name", sig_name)] = signal_val
                
                if "BULLISH" in signal_val:
                    bullish_score += strength
                elif "BEARISH" in signal_val:
                    bearish_score += strength
                elif signal_val == "FEAR":  # Contrarian
                    bullish_score += 40
                elif signal_val == "GREED":  # Contrarian
                    bearish_score += 40
                elif signal_val == "LEAN_SHORT":  # Contrarian
                    bullish_score += 30
                elif signal_val == "LEAN_LONG":  # Contrarian
                    bearish_score += 30
            
            # Normalize to 0-100 confidence
            total_score = bullish_score + bearish_score
            if total_score > 0:
                if bullish_score > bearish_score:
                    direction = "LONG"
                    confidence = min(85, 50 + (bullish_score - bearish_score) / 8)
                elif bearish_score > bullish_score:
                    direction = "SHORT"
                    confidence = min(85, 50 + (bearish_score - bullish_score) / 8)
                else:
                    direction = "NEUTRAL"
                    confidence = 50
            else:
                direction = "NEUTRAL"
                confidence = 50
            
            # Calculate ATR-based ranges
            vrc = signals.get("vrc", {})
            atr_pct = vrc.get("value", 0.02)  # Default 2%
            if atr_pct == 0:
                atr_pct = 0.02
            
            # Adjust volatility multiplier based on regime
            regime = vrc.get("raw_data", {}).get("regime", "NORMAL")
            vol_mult = {"LOW": 1.5, "NORMAL": 2.0, "HIGH": 2.5, "EXTREME": 3.0}.get(regime, 2.0)
            
            # Price targets (1 hour timeframe)
            hourly_move = price * atr_pct * vol_mult
            
            if direction == "LONG":
                bullish_target = price + hourly_move * 1.5
                bearish_target = price - hourly_move * 0.5
                bullish_prob = min(75, confidence * 0.9)
                bearish_prob = max(15, 100 - bullish_prob - 20)
            elif direction == "SHORT":
                bullish_target = price + hourly_move * 0.5
                bearish_target = price - hourly_move * 1.5
                bearish_prob = min(75, confidence * 0.9)
                bullish_prob = max(15, 100 - bearish_prob - 20)
            else:
                bullish_target = price + hourly_move
                bearish_target = price - hourly_move
                bullish_prob = 35
                bearish_prob = 35
            
            # Range prediction (where price likely stays)
            range_low = price - hourly_move
            range_high = price + hourly_move
            neutral_prob = max(20, min(50, 100 - bullish_prob - bearish_prob))
            
            # Normalize probabilities to sum to 100
            total_prob = bullish_prob + bearish_prob + neutral_prob
            long_prob = bullish_prob / total_prob * 100
            short_prob = bearish_prob / total_prob * 100
            flat_prob = neutral_prob / total_prob * 100
            
            # Gate status
            gate_status = analysis.get("gate_status", {})
            gate_passed = gate_status.get("passed", False)
            gate_keys = gate_status.get("keys_passed", 0)
            
            # Generate contract setup (always provide one)
            contract = self._generate_contract_setup(
                price=price,
                direction=direction,
                confidence=confidence,
                long_prob=long_prob,
                short_prob=short_prob,
                atr_pct=atr_pct,
                vol_mult=vol_mult,
                gate_keys=gate_keys
            )
            
            return TokenPrediction(
                symbol=symbol,
                price=price,
                direction=direction,
                confidence=confidence,
                long_probability=long_prob,
                short_probability=short_prob,
                neutral_probability=flat_prob,
                bullish_target=bullish_target,
                bullish_probability=bullish_prob,
                bearish_target=bearish_target,
                bearish_probability=bearish_prob,
                range_low=range_low,
                range_high=range_high,
                range_probability=flat_prob,
                contract=contract,
                key_signals=key_signals,
                gate_passed=gate_passed,
                gate_keys=gate_keys
            )
            
        except Exception as e:
            logger.error(f"Error generating prediction for {symbol}: {e}")
            return None
    
    def _generate_contract_setup(
        self,
        price: float,
        direction: str,
        confidence: float,
        long_prob: float,
        short_prob: float,
        atr_pct: float,
        vol_mult: float,
        gate_keys: int
    ) -> ContractSetup:
        """
        Generate a contract setup with probabilities.
        Always provides a setup, even for low-confidence situations.
        """
        # Direction probability (which way more likely)
        if direction == "LONG":
            dir_prob = long_prob
        elif direction == "SHORT":
            dir_prob = short_prob
        else:
            # Neutral - pick the higher probability
            if long_prob > short_prob:
                direction = "LONG"
                dir_prob = long_prob
            else:
                direction = "SHORT"
                dir_prob = short_prob
        
        # Base risk (stop loss distance) based on ATR
        base_risk = atr_pct * vol_mult * 1.2  # Slightly wider than 1 ATR
        base_risk = max(0.01, min(0.05, base_risk))  # Cap between 1-5%
        
        # Adjust risk based on confidence (lower confidence = wider stop)
        confidence_factor = 1 + (100 - confidence) / 200  # 1.0 to 1.5
        risk_pct = base_risk * confidence_factor
        
        # Calculate entry and stop loss
        entry = price
        if direction == "LONG":
            stop_loss = price * (1 - risk_pct)
        else:
            stop_loss = price * (1 + risk_pct)
        
        # Calculate take profit targets with probabilities
        # TP probability decreases as target gets further away
        
        # TP1: 1:1 R:R (conservative)
        tp1_dist = risk_pct * 1.0
        tp1_base_prob = dir_prob * 0.85  # High chance if direction correct
        
        # TP2: 2:1 R:R (moderate)
        tp2_dist = risk_pct * 2.0
        tp2_base_prob = dir_prob * 0.55  # Medium chance
        
        # TP3: 3:1 R:R (aggressive)
        tp3_dist = risk_pct * 3.0
        tp3_base_prob = dir_prob * 0.35  # Lower chance but great reward
        
        # Adjust probabilities based on gate status (more keys = higher confidence)
        gate_boost = gate_keys / 3 * 0.15  # Up to 15% boost for full gate pass
        
        tp1_prob = min(90, tp1_base_prob + gate_boost * 100)
        tp2_prob = min(75, tp2_base_prob + gate_boost * 100 * 0.7)
        tp3_prob = min(55, tp3_base_prob + gate_boost * 100 * 0.5)
        
        # Calculate actual TP prices
        if direction == "LONG":
            tp1 = price * (1 + tp1_dist)
            tp2 = price * (1 + tp2_dist)
            tp3 = price * (1 + tp3_dist)
        else:
            tp1 = price * (1 - tp1_dist)
            tp2 = price * (1 - tp2_dist)
            tp3 = price * (1 - tp3_dist)
        
        # Calculate expected value (EV)
        # EV = (win_prob * reward) - (lose_prob * risk)
        # Using TP2 as the primary target
        win_prob = tp2_prob / 100
        lose_prob = 1 - win_prob
        reward = 2 * risk_pct  # 2:1 R:R
        ev = (win_prob * reward) - (lose_prob * risk_pct)
        ev_pct = ev * 100  # As percentage
        
        # Grade the setup
        if ev_pct > 1.5 and confidence > 70:
            grade = "A"
        elif ev_pct > 1.0 and confidence > 60:
            grade = "B"
        elif ev_pct > 0.5 and confidence > 50:
            grade = "C"
        elif ev_pct > 0:
            grade = "D"
        else:
            grade = "F"
        
        return ContractSetup(
            direction=direction,
            direction_probability=dir_prob,
            entry=entry,
            stop_loss=stop_loss,
            risk_percent=risk_pct * 100,
            tp1=tp1,
            tp1_probability=tp1_prob,
            tp1_rr=1.0,
            tp2=tp2,
            tp2_probability=tp2_prob,
            tp2_rr=2.0,
            tp3=tp3,
            tp3_probability=tp3_prob,
            tp3_rr=3.0,
            expected_value=ev_pct,
            grade=grade
        )
    
    async def generate_report(self) -> Dict[str, Any]:
        """Generate full hourly report for all tokens with correlation awareness."""
        raw_predictions = []
        
        # First pass: get raw predictions for all assets
        for symbol in self.settings.tracked_assets:
            pred = await self.generate_prediction(symbol)
            if pred:
                raw_predictions.append(pred)
            await asyncio.sleep(0.5)  # Rate limit
        
        # Apply BTC correlation gravity to altcoins
        predictions = self._apply_btc_correlation(raw_predictions)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "predictions": predictions
        }
    
    def _apply_btc_correlation(self, predictions: List[TokenPrediction]) -> List[TokenPrediction]:
        """
        Apply BTC correlation to altcoin predictions.
        
        Reality: When BTC dumps, alts dump harder. When BTC pumps, alts pump harder.
        An altcoin should only go AGAINST BTC if it has overwhelming independent signals.
        
        Correlation coefficients (approximate):
        - ETH/BTC: 0.85
        - SOL/BTC: 0.80
        - XRP/BTC: 0.75
        """
        CORRELATIONS = {
            "ETH": 0.85,
            "SOL": 0.80,
            "XRP": 0.75,
            "BTC": 1.0  # BTC is the reference
        }
        
        # Find BTC prediction
        btc_pred = next((p for p in predictions if p.symbol == "BTC"), None)
        if not btc_pred:
            return predictions  # No BTC data, can't apply correlation
        
        btc_direction = btc_pred.contract.direction
        btc_confidence = btc_pred.confidence
        btc_long_prob = btc_pred.long_probability
        btc_short_prob = btc_pred.short_probability
        
        adjusted_predictions = []
        
        for pred in predictions:
            if pred.symbol == "BTC":
                adjusted_predictions.append(pred)
                continue
            
            corr = CORRELATIONS.get(pred.symbol, 0.75)
            
            # Calculate how much BTC should influence this altcoin
            btc_influence = corr * (btc_confidence / 100)
            
            # Original altcoin signals
            orig_long = pred.long_probability
            orig_short = pred.short_probability
            orig_neutral = pred.neutral_probability
            
            # Blend with BTC direction
            # Higher correlation = more BTC influence
            blended_long = (orig_long * (1 - btc_influence)) + (btc_long_prob * btc_influence)
            blended_short = (orig_short * (1 - btc_influence)) + (btc_short_prob * btc_influence)
            blended_neutral = 100 - blended_long - blended_short
            
            # Determine new direction
            if blended_long > blended_short and blended_long > blended_neutral:
                new_direction = "LONG"
                new_dir_prob = blended_long
            elif blended_short > blended_long and blended_short > blended_neutral:
                new_direction = "SHORT"
                new_dir_prob = blended_short
            else:
                new_direction = "NEUTRAL"
                new_dir_prob = blended_neutral
            
            # Flag if altcoin is fighting BTC (unusual, requires strong conviction)
            fighting_btc = (new_direction == "LONG" and btc_direction == "SHORT") or \
                          (new_direction == "SHORT" and btc_direction == "LONG")
            
            # If fighting BTC, require much higher confidence (penalize)
            if fighting_btc:
                # Only allow if original signal was VERY strong (80%+)
                if max(orig_long, orig_short) < 80:
                    # Override to follow BTC
                    new_direction = btc_direction
                    new_dir_prob = btc_confidence * corr
                    blended_long = btc_long_prob * corr + orig_long * (1 - corr)
                    blended_short = btc_short_prob * corr + orig_short * (1 - corr)
            
            # Recalculate confidence
            new_confidence = max(blended_long, blended_short)
            
            # Regenerate contract with adjusted probabilities
            new_contract = self._generate_contract_setup(
                price=pred.price,
                direction=new_direction,
                confidence=new_confidence,
                long_prob=blended_long,
                short_prob=blended_short,
                atr_pct=pred.range_high / pred.price - 1 if pred.price > 0 else 0.02,
                vol_mult=1.5,
                gate_keys=pred.gate_keys
            )
            
            # Create adjusted prediction
            adjusted_pred = TokenPrediction(
                symbol=pred.symbol,
                price=pred.price,
                direction=new_direction,
                confidence=new_confidence,
                long_probability=blended_long,
                short_probability=blended_short,
                neutral_probability=max(0, 100 - blended_long - blended_short),
                bullish_target=pred.bullish_target if new_direction == "LONG" else pred.price * 1.02,
                bullish_probability=blended_long,
                bearish_target=pred.bearish_target if new_direction == "SHORT" else pred.price * 0.98,
                bearish_probability=blended_short,
                range_low=pred.range_low,
                range_high=pred.range_high,
                range_probability=pred.range_probability,
                contract=new_contract,
                key_signals={**pred.key_signals, "BTC_CORR": f"{corr*100:.0f}%"},
                gate_passed=pred.gate_passed,
                gate_keys=pred.gate_keys
            )
            
            adjusted_predictions.append(adjusted_pred)
        
        return adjusted_predictions
    
    def _calculate_contract_value(self, contract: ContractSetup, position_size: float = 1000) -> Dict[str, Any]:
        """
        Calculate the mathematical value of a contract.
        
        THE CORE INSIGHT:
        If Coracle predicts better than random (50%), every contract has positive EV.
        Value = (Win% × Reward) - (Loss% × Risk)
        
        This is the VALUE CREATION that makes Coracle contracts worth entering.
        """
        # Convert probabilities to decimals
        tp1_prob = contract.tp1_probability / 100
        tp2_prob = contract.tp2_probability / 100
        tp3_prob = contract.tp3_probability / 100
        
        # R:R ratios
        rr1, rr2, rr3 = 1.0, 2.0, 3.0
        
        # Calculate Expected Value for each target
        # EV = (win_prob × reward) - (loss_prob × 1)
        ev_tp1 = (tp1_prob * rr1) - ((1 - tp1_prob) * 1)
        ev_tp2 = (tp2_prob * rr2) - ((1 - tp2_prob) * 1)
        ev_tp3 = (tp3_prob * rr3) - ((1 - tp3_prob) * 1)
        
        # Blended EV using optimal strategy: 50% TP1, 30% TP2, 20% TP3
        ev_blended = (ev_tp1 * 0.5) + (ev_tp2 * 0.3) + (ev_tp3 * 0.2)
        
        # Calculate edge vs random chance
        # If direction_prob > 50%, we have edge
        dir_prob = contract.direction_probability / 100
        edge = (dir_prob - 0.5) * 2  # Normalized: 60% = 20% edge
        
        # Kelly Criterion: optimal position size
        # f* = (p(R+1) - 1) / R  (using TP2)
        kelly = max(0, (tp2_prob * (rr2 + 1) - 1) / rr2)
        
        # Dollar value per trade
        risk_usd = position_size * (contract.risk_percent / 100)
        value_per_trade = ev_blended * risk_usd
        
        return {
            "ev_per_dollar": ev_blended,
            "ev_tp1": ev_tp1,
            "ev_tp2": ev_tp2,
            "ev_tp3": ev_tp3,
            "edge_pct": edge * 100,
            "kelly_fraction": kelly,
            "value_per_trade": value_per_trade,
            "risk_usd": risk_usd,
            "profitable": ev_blended > 0
        }

    def format_telegram_report(self, report: Dict[str, Any]) -> str:
        """Format report for Telegram with contract setups, target ranges, and VALUE CREATION."""
        predictions = report.get("predictions", [])
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        
        def fmt_price(p):
            if p < 1:
                return f"${p:.4f}"
            elif p < 100:
                return f"${p:.2f}"
            else:
                return f"${p:,.0f}"
        
        msg = f"""🔮 *CORACLE HOURLY ORACLE*
📅 {ts}

"""
        
        # Compact table header
        msg += "*TOKEN | DIR | PROB | ENTRY | SL | TARGETS (probability)*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        total_hourly_value = 0
        
        for pred in predictions:
            c = pred.contract
            value = self._calculate_contract_value(c)
            total_hourly_value += value["value_per_trade"]
            
            # Direction emoji
            dir_emoji = "🟢" if c.direction == "LONG" else "🔴"
            grade_emoji = {"A": "🏆", "B": "⭐", "C": "👍", "D": "⚠️", "F": "🚫"}.get(c.grade, "❓")
            value_emoji = "💵" if value["profitable"] else "⚠️"
            
            # Compact row
            msg += f"""
{dir_emoji} *{pred.symbol}* {c.direction} {c.direction_probability:.0f}% {grade_emoji}
Entry: {fmt_price(c.entry)} | SL: {fmt_price(c.stop_loss)}
"""
            # Target range with probabilities
            msg += f"🎯 {fmt_price(c.tp1)}({c.tp1_probability:.0f}%) → {fmt_price(c.tp2)}({c.tp2_probability:.0f}%) → {fmt_price(c.tp3)}({c.tp3_probability:.0f}%)\n"
            msg += f"EV: {c.expected_value:+.1f}% | Value: {value_emoji}${value['value_per_trade']:+.2f}/trade\n"
        
        msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        # Detailed breakdown for best setup
        best = max(predictions, key=lambda p: p.contract.expected_value) if predictions else None
        
        if best:
            c = best.contract
            value = self._calculate_contract_value(c)
            dir_emoji = "🟢" if c.direction == "LONG" else "🔴"
            
            msg += f"""
⭐ *BEST SETUP: {best.symbol}*

{dir_emoji} *{c.direction}* ({c.direction_probability:.0f}% confidence)

📊 *Probability Breakdown:*
├ ↗️ Long chance: {best.long_probability:.0f}%
├ ↘️ Short chance: {best.short_probability:.0f}%
└ ↔️ Flat chance: {best.neutral_probability:.0f}%

📋 *Contract Details:*
├ Entry: *{fmt_price(c.entry)}*
├ Stop Loss: *{fmt_price(c.stop_loss)}* ({c.risk_percent:.1f}% risk)
│
├ TP1: *{fmt_price(c.tp1)}* — {c.tp1_probability:.0f}% prob (1:1 R:R)
├ TP2: *{fmt_price(c.tp2)}* — {c.tp2_probability:.0f}% prob (2:1 R:R)
└ TP3: *{fmt_price(c.tp3)}* — {c.tp3_probability:.0f}% prob (3:1 R:R)

💰 *VALUE CREATION:*
├ EV per $1 risked: *${value['ev_per_dollar']:+.3f}*
├ Edge vs random: *{value['edge_pct']:+.1f}%*
├ Kelly sizing: *{value['kelly_fraction']*100:.1f}%* of bankroll
├ Value per trade: *${value['value_per_trade']:+.2f}*
└ Grade: *{c.grade}*

🐋 Gate: {best.gate_keys}/3 keys
"""
            # Key signals
            sigs = best.key_signals
            msg += f"Signals: {' | '.join(f'{k}:{v}' for k,v in sigs.items())}\n"
        
        # VALUE SUMMARY
        msg += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💵 *VALUE CREATION SUMMARY*
├ This hour: *${total_hourly_value:+.2f}* EV
├ Daily (24h): *${total_hourly_value * 24:+.2f}* EV
└ Annual: *${total_hourly_value * 24 * 365:+,.0f}* EV

"""
        
        # Market summary
        long_count = sum(1 for p in predictions if p.contract.direction == "LONG")
        short_count = sum(1 for p in predictions if p.contract.direction == "SHORT")
        market_mood = "🟢 BULLISH" if long_count > short_count else "🔴 BEARISH" if short_count > long_count else "⚪ MIXED"
        
        msg += f"""*Market Mood:* {market_mood} ({long_count}L/{short_count}S)
⏰ Next update: Top of hour

_Value = probability × reward - risk_
_As Coracle accuracy improves, value compounds._
"""
        return msg
    
    async def send_hourly_report(self, alerter) -> bool:
        """Generate, track, and send the hourly report."""
        try:
            report = await self.generate_report()
            
            # Log all predictions for tracking
            await self._log_predictions(report)
            
            message = self.format_telegram_report(report)
            
            # Send via Telegram
            success = await alerter._send_telegram_message(message)
            
            if success:
                self.last_report_time = datetime.utcnow()
                logger.info("📊 Hourly oracle report sent")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send hourly report: {e}")
            return False
    
    async def _log_predictions(self, report: Dict[str, Any]):
        """Log all predictions for tracking and learning."""
        try:
            from engine.prediction_tracker import get_prediction_tracker, create_tracked_prediction
            
            tracker = get_prediction_tracker()
            predictions = report.get("predictions", [])
            
            for pred in predictions:
                c = pred.contract
                
                tracked = create_tracked_prediction(
                    symbol=pred.symbol,
                    direction=c.direction,
                    direction_probability=c.direction_probability,
                    confidence=pred.confidence,
                    entry_price=pred.price,
                    stop_loss=c.stop_loss,
                    tp1=c.tp1,
                    tp2=c.tp2,
                    tp3=c.tp3,
                    tp1_probability=c.tp1_probability,
                    tp2_probability=c.tp2_probability,
                    tp3_probability=c.tp3_probability,
                    key_signals=pred.key_signals,
                    gate_passed=pred.gate_passed,
                    gate_keys=pred.gate_keys,
                    expected_value=c.expected_value,
                    grade=c.grade
                )
                
                tracker.log_prediction(tracked)
            
            logger.info(f"📝 Logged {len(predictions)} predictions for tracking")
            
        except Exception as e:
            logger.error(f"Failed to log predictions: {e}")
    
    async def _scheduler_loop(self, alerter):
        """Run the hourly scheduler."""
        logger.info("⏰ Hourly Oracle scheduler started")
        
        while self.running:
            try:
                now = datetime.utcnow()
                
                # Calculate next hour
                next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                wait_seconds = (next_hour - now).total_seconds()
                
                # If we're within 5 minutes of the hour, send now then wait
                if wait_seconds > 3300:  # More than 55 min to next hour
                    # Send immediately on startup
                    logger.info("📊 Sending initial oracle report...")
                    await self.send_hourly_report(alerter)
                
                # Wait until next hour
                logger.info(f"⏰ Next oracle report in {wait_seconds/60:.0f} minutes")
                await asyncio.sleep(wait_seconds)
                
                # Send the report
                await self.send_hourly_report(alerter)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)  # Wait a minute on error
        
        logger.info("Hourly Oracle scheduler stopped")
    
    def start(self, alerter):
        """Start the hourly scheduler."""
        if self.running:
            return
        
        self.running = True
        self._task = asyncio.create_task(self._scheduler_loop(alerter))
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self._task:
            self._task.cancel()


# Singleton
_oracle: Optional[HourlyOracle] = None


def get_hourly_oracle() -> HourlyOracle:
    """Get or create the oracle instance."""
    global _oracle
    if _oracle is None:
        _oracle = HourlyOracle()
    return _oracle


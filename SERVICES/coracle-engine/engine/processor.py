"""
Coracle Signal Processor
=========================
Computes derived signals from raw data.

Computed Signals:
- WADI: Whale Accumulation/Distribution Index
- LCP: Liquidity Cascade Potential
- VRC: Volatility Regime Classifier
- BAI: Bid/Ask Imbalance
- OBS: Order Book Slope
- WC: Whale Confidence
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import math
import logging

from app.config import Settings
from app.models import (
    SignalSnapshot, SignalValue, VolatilityRegime, LatencyTier
)

logger = logging.getLogger(__name__)


class SignalProcessor:
    """
    Processes raw signal data into standardized signal values.
    
    Computes derived signals that aren't directly available from APIs.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        
        # ATR history for volatility calculation (per symbol)
        self._atr_history: Dict[str, list] = {}
        self._price_history: Dict[str, list] = {}
    
    async def process_signals(
        self, 
        symbol: str, 
        raw_data: Dict[str, Any]
    ) -> SignalSnapshot:
        """
        Process raw data into a complete signal snapshot.
        """
        price = raw_data.get("price", 0)
        whaletrack = raw_data.get("whaletrack", {})
        orderbook = raw_data.get("orderbook", {})
        trades = raw_data.get("trades", {})
        fgi_data = raw_data.get("fear_greed", {})
        
        # Update price history for ATR
        self._update_price_history(symbol, price)
        
        # Process each signal category
        bai = self._compute_bai(orderbook)
        obs = self._compute_obs(orderbook)
        wadi = self._compute_wadi(trades)
        lcp = self._compute_lcp(whaletrack)
        vrc = self._compute_vrc(symbol, price)
        wc = self._compute_whale_confidence(trades, whaletrack)
        
        # Extract signals from WhaleTrack
        cvd = self._extract_cvd(trades, whaletrack)
        fr = self._extract_funding_rate(whaletrack)
        oi = self._extract_open_interest(whaletrack)
        ls_ratio = self._extract_ls_ratio(whaletrack)
        spot_premium = self._extract_spot_premium(whaletrack)
        fgi = self._extract_fgi(fgi_data)
        
        return SignalSnapshot(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            price=price,
            # Computed signals
            bai=bai,
            obs=obs,
            wadi=wadi,
            lcp=lcp,
            vrc=vrc,
            wc=wc,
            # Extracted signals
            cvd=cvd,
            fr=fr,
            oi=oi,
            ls_ratio=ls_ratio,
            spot_premium=spot_premium,
            fgi=fgi
        )
    
    # ========================================================================
    # COMPUTED SIGNALS
    # ========================================================================
    
    def _compute_bai(self, orderbook: Dict[str, Any]) -> Optional[SignalValue]:
        """
        Compute Bid/Ask Imbalance from orderbook.
        
        BAI = (Bid Volume - Ask Volume) / Total Volume
        Range: -1.0 to +1.0
        Positive = More buy pressure, Negative = More sell pressure
        """
        if not orderbook:
            return None
        
        imbalance = orderbook.get("imbalance", 0)
        
        # Classify signal
        if imbalance > 0.3:
            signal = "BULLISH"
            strength = min(100, 50 + imbalance * 100)
        elif imbalance > 0.15:
            signal = "LEAN_BULLISH"
            strength = 60 + imbalance * 50
        elif imbalance < -0.3:
            signal = "BEARISH"
            strength = min(100, 50 + abs(imbalance) * 100)
        elif imbalance < -0.15:
            signal = "LEAN_BEARISH"
            strength = 60 + abs(imbalance) * 50
        else:
            signal = "NEUTRAL"
            strength = 50
        
        return SignalValue(
            name="BAI",
            value=round(imbalance, 4),
            signal=signal,
            strength=round(strength, 1),
            tier="LIQUIDITY",
            source="computed_orderbook"
        )
    
    def _compute_obs(self, orderbook: Dict[str, Any]) -> Optional[SignalValue]:
        """
        Compute Order Book Slope.
        
        Steep slope = Liquidity concentrated near best price (support/resistance)
        Flat slope = Liquidity spread = Easy to push through
        
        Range: 0 to 1 (1 = steep, 0 = flat)
        """
        if not orderbook:
            return None
        
        bid_slope = orderbook.get("bid_slope", 0.5)
        ask_slope = orderbook.get("ask_slope", 0.5)
        
        # Combined slope metric
        avg_slope = (bid_slope + ask_slope) / 2
        slope_diff = bid_slope - ask_slope  # Positive = bid wall stronger
        
        # Classify
        if avg_slope > 0.7:
            signal = "HIGH_RESISTANCE"
            strength = 70 + avg_slope * 30
        elif avg_slope > 0.5:
            signal = "MODERATE_RESISTANCE"
            strength = 55 + avg_slope * 20
        elif avg_slope < 0.3:
            signal = "LOW_RESISTANCE"
            strength = 40 + avg_slope * 30
        else:
            signal = "NEUTRAL"
            strength = 50
        
        return SignalValue(
            name="OBS",
            value=round(avg_slope, 4),
            signal=signal,
            strength=round(strength, 1),
            tier="LIQUIDITY",
            source="computed_orderbook",
            raw_data={"bid_slope": bid_slope, "ask_slope": ask_slope, "diff": slope_diff}
        )
    
    def _compute_wadi(self, trades: Dict[str, Any]) -> Optional[SignalValue]:
        """
        Compute Whale Accumulation/Distribution Index.
        
        WADI = (Whale Buy Volume - Whale Sell Volume) / Total Whale Volume
        Whale = trades > $100k
        Range: -1.0 to +1.0
        """
        if not trades:
            return None
        
        whale_buy = trades.get("whale_buy_volume", 0)
        whale_sell = trades.get("whale_sell_volume", 0)
        total_whale = whale_buy + whale_sell
        
        if total_whale == 0:
            # No whale activity - neutral but with low confidence
            return SignalValue(
                name="WADI",
                value=0,
                signal="NEUTRAL",
                strength=30,  # Low confidence when no whale data
                tier="WHALE",
                source="computed_trades",
                raw_data={"whale_buy": whale_buy, "whale_sell": whale_sell, "no_activity": True}
            )
        
        wadi = (whale_buy - whale_sell) / total_whale
        
        # Classify based on spec thresholds
        if wadi > 0.4:
            signal = "ACCUMULATION"
            strength = min(100, 60 + wadi * 100)
        elif wadi > 0.2:
            signal = "LEAN_ACCUMULATION"
            strength = 55 + wadi * 50
        elif wadi < -0.4:
            signal = "DISTRIBUTION"
            strength = min(100, 60 + abs(wadi) * 100)
        elif wadi < -0.2:
            signal = "LEAN_DISTRIBUTION"
            strength = 55 + abs(wadi) * 50
        else:
            signal = "NEUTRAL"
            strength = 50
        
        return SignalValue(
            name="WADI",
            value=round(wadi, 4),
            signal=signal,
            strength=round(strength, 1),
            tier="WHALE",
            source="computed_trades",
            raw_data={"whale_buy": whale_buy, "whale_sell": whale_sell, "total": total_whale}
        )
    
    def _compute_lcp(self, whaletrack: Dict[str, Any]) -> Optional[SignalValue]:
        """
        Compute Liquidity Cascade Potential.
        
        LCP = (Liquidation Density) × (Order Book Imbalance)
        High LCP = Risk of liquidation cascade
        Threshold: >2.5 indicates high cascade risk
        """
        if not whaletrack:
            return None
        
        # Extract liquidation data
        liq_data = whaletrack.get("liquidations", {})
        oi_data = whaletrack.get("open_interest", {})
        
        long_liqs = liq_data.get("long_liquidations_24h", 0)
        short_liqs = liq_data.get("short_liquidations_24h", 0)
        total_liqs = long_liqs + short_liqs
        
        # Normalize liquidation density (per 1000)
        liq_density = total_liqs / 1000 if total_liqs > 0 else 0
        
        # Get OI imbalance from L/S ratio
        ls_data = whaletrack.get("long_short_ratio", {})
        long_pct = ls_data.get("long_pct", 50)
        short_pct = ls_data.get("short_pct", 50)
        oi_imbalance = abs(long_pct - short_pct) / 100
        
        # Calculate LCP
        lcp = liq_density * oi_imbalance * 10  # Scaled for threshold
        
        # Classify
        if lcp > 2.5:
            signal = "HIGH_CASCADE_RISK"
            strength = min(100, 70 + lcp * 10)
        elif lcp > 1.5:
            signal = "MODERATE_CASCADE_RISK"
            strength = 55 + lcp * 10
        elif lcp > 0.5:
            signal = "LOW_CASCADE_RISK"
            strength = 40 + lcp * 15
        else:
            signal = "SAFE"
            strength = 30
        
        return SignalValue(
            name="LCP",
            value=round(lcp, 4),
            signal=signal,
            strength=round(strength, 1),
            tier="LIQUIDITY",
            source="computed_liquidations",
            raw_data={
                "liq_density": liq_density,
                "oi_imbalance": oi_imbalance,
                "long_liqs": long_liqs,
                "short_liqs": short_liqs
            }
        )
    
    def _compute_vrc(self, symbol: str, price: float) -> Optional[SignalValue]:
        """
        Compute Volatility Regime Classifier.
        
        Uses ATR-based classification into LOW/NORMAL/HIGH/EXTREME regimes.
        """
        if symbol not in self._price_history or len(self._price_history[symbol]) < 2:
            return SignalValue(
                name="VRC",
                value=0,
                signal="NORMAL",
                strength=50,
                tier="TECHNICAL",
                source="computed_atr",
                raw_data={"insufficient_data": True}
            )
        
        # Calculate simple volatility from price history
        prices = self._price_history[symbol][-20:]  # Last 20 samples
        if len(prices) < 2:
            return None
        
        # Calculate returns
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        # Calculate volatility (standard deviation of returns)
        if not returns:
            return None
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = math.sqrt(variance) * 100  # As percentage
        
        # Classify regime
        if volatility < 0.5:
            regime = VolatilityRegime.LOW
            signal = "LOW_VOLATILITY"
            strength = 30
        elif volatility < 1.5:
            regime = VolatilityRegime.NORMAL
            signal = "NORMAL_VOLATILITY"
            strength = 50
        elif volatility < 3.0:
            regime = VolatilityRegime.HIGH
            signal = "HIGH_VOLATILITY"
            strength = 70
        else:
            regime = VolatilityRegime.EXTREME
            signal = "EXTREME_VOLATILITY"
            strength = 90
        
        return SignalValue(
            name="VRC",
            value=round(volatility, 4),
            signal=signal,
            strength=round(strength, 1),
            tier="TECHNICAL",
            source="computed_atr",
            raw_data={"regime": regime.value, "samples": len(prices)}
        )
    
    def _compute_whale_confidence(
        self, 
        trades: Dict[str, Any], 
        whaletrack: Dict[str, Any]
    ) -> Optional[SignalValue]:
        """
        Compute Whale Confidence score.
        
        Based on:
        - Whale trade consistency
        - Volume vs historical
        - Alignment with funding
        """
        if not trades:
            return None
        
        whale_buy = trades.get("whale_buy_volume", 0)
        whale_sell = trades.get("whale_sell_volume", 0)
        total_whale = whale_buy + whale_sell
        
        # Base confidence from whale activity volume
        # More whale activity = higher confidence in signal
        volume_confidence = min(100, total_whale / 10000)  # $1M = 100%
        
        # Check alignment with funding
        funding_alignment = 50  # Neutral default
        if whaletrack:
            funding_data = whaletrack.get("funding", {})
            rate = funding_data.get("rate", 0)
            
            # If whales buying and funding positive (longs paying) = contrarian = high confidence
            # If whales buying and funding negative = aligned = moderate confidence
            if total_whale > 0:
                net_whale = whale_buy - whale_sell
                if net_whale > 0 and rate > 0:  # Buying against crowd
                    funding_alignment = 80
                elif net_whale > 0 and rate < 0:  # Buying with crowd
                    funding_alignment = 60
                elif net_whale < 0 and rate < 0:  # Selling against crowd
                    funding_alignment = 80
                elif net_whale < 0 and rate > 0:  # Selling with crowd
                    funding_alignment = 60
        
        # Combined confidence
        wc = (volume_confidence * 0.6 + funding_alignment * 0.4)
        
        # Classify
        if wc > 80:
            signal = "HIGH_CONFIDENCE"
        elif wc > 60:
            signal = "MODERATE_CONFIDENCE"
        elif wc > 40:
            signal = "LOW_CONFIDENCE"
        else:
            signal = "VERY_LOW_CONFIDENCE"
        
        return SignalValue(
            name="WC",
            value=round(wc, 2),
            signal=signal,
            strength=round(wc, 1),
            tier="WHALE",
            source="computed_whale",
            raw_data={
                "volume_confidence": volume_confidence,
                "funding_alignment": funding_alignment
            }
        )
    
    # ========================================================================
    # EXTRACTED SIGNALS (from WhaleTrack)
    # ========================================================================
    
    def _extract_cvd(
        self, 
        trades: Dict[str, Any], 
        whaletrack: Dict[str, Any]
    ) -> Optional[SignalValue]:
        """Extract CVD signal."""
        # Prefer direct calculation from trades
        if trades and trades.get("cvd_ratio") is not None:
            ratio = trades["cvd_ratio"]
            
            if ratio > 0.2:
                signal, strength = "BULLISH", 80
            elif ratio > 0.1:
                signal, strength = "LEAN_BULLISH", 65
            elif ratio < -0.2:
                signal, strength = "BEARISH", 80
            elif ratio < -0.1:
                signal, strength = "LEAN_BEARISH", 65
            else:
                signal, strength = "NEUTRAL", 50
            
            return SignalValue(
                name="CVD",
                value=round(ratio, 4),
                signal=signal,
                strength=strength,
                tier="DERIVATIVES",
                source="hyperliquid_trades",
                raw_data={
                    "buy_volume": trades.get("buy_volume"),
                    "sell_volume": trades.get("sell_volume"),
                    "cvd": trades.get("cvd")
                }
            )
        
        # Fallback to WhaleTrack
        if whaletrack:
            cvd_data = whaletrack.get("cvd", {})
            if cvd_data:
                return SignalValue(
                    name="CVD",
                    value=cvd_data.get("delta_pct", 0) / 100,
                    signal=cvd_data.get("signal", "NEUTRAL"),
                    strength=cvd_data.get("strength", 50),
                    tier="DERIVATIVES",
                    source="whaletrack"
                )
        
        return None
    
    def _extract_funding_rate(self, whaletrack: Dict[str, Any]) -> Optional[SignalValue]:
        """Extract funding rate signal."""
        if not whaletrack:
            return None
        
        funding = whaletrack.get("funding", {})
        if not funding:
            return None
        
        rate = funding.get("rate", 0)
        
        return SignalValue(
            name="FR",
            value=rate,
            signal=funding.get("signal", "NEUTRAL"),
            strength=funding.get("strength", 50),
            tier="FUNDING",
            source="whaletrack_coinglass",
            raw_data={
                "rate_pct": funding.get("rate_pct"),
                "predicted_rate": funding.get("predicted_rate")
            }
        )
    
    def _extract_open_interest(self, whaletrack: Dict[str, Any]) -> Optional[SignalValue]:
        """Extract open interest signal."""
        if not whaletrack:
            return None
        
        oi = whaletrack.get("open_interest", {})
        if not oi:
            return None
        
        change = oi.get("change_4h_pct", 0)
        
        return SignalValue(
            name="OI",
            value=change,
            signal=oi.get("signal", "NEUTRAL"),
            strength=oi.get("strength", 50),
            tier="DERIVATIVES",
            source="whaletrack_coinglass",
            raw_data={
                "total_oi": oi.get("total_oi_usd"),
                "change_24h": oi.get("change_24h_pct")
            }
        )
    
    def _extract_ls_ratio(self, whaletrack: Dict[str, Any]) -> Optional[SignalValue]:
        """Extract long/short ratio signal."""
        if not whaletrack:
            return None
        
        ls = whaletrack.get("long_short_ratio", {})
        if not ls:
            return None
        
        ratio = ls.get("ratio", 1.0)
        
        # Classify (contrarian interpretation)
        if ratio > 1.5:
            signal = "CROWDED_LONG"  # Bearish signal
            strength = 70
        elif ratio > 1.2:
            signal = "LEAN_LONG"
            strength = 60
        elif ratio < 0.67:
            signal = "CROWDED_SHORT"  # Bullish signal
            strength = 70
        elif ratio < 0.83:
            signal = "LEAN_SHORT"
            strength = 60
        else:
            signal = "BALANCED"
            strength = 50
        
        return SignalValue(
            name="LS_RATIO",
            value=ratio,
            signal=signal,
            strength=strength,
            tier="DERIVATIVES",
            source="whaletrack_coinglass",
            raw_data={
                "long_pct": ls.get("long_pct"),
                "short_pct": ls.get("short_pct")
            }
        )
    
    def _extract_spot_premium(self, whaletrack: Dict[str, Any]) -> Optional[SignalValue]:
        """Extract spot premium signal."""
        if not whaletrack:
            return None
        
        sp = whaletrack.get("spot_premium", {})
        if not sp:
            return None
        
        return SignalValue(
            name="SPOT_PREMIUM",
            value=sp.get("premium_pct", 0),
            signal=sp.get("signal", "NEUTRAL"),
            strength=sp.get("strength", 50),
            tier="FUNDING",
            source="whaletrack",
            raw_data={
                "spot_price": sp.get("spot_price"),
                "perp_price": sp.get("perp_price")
            }
        )
    
    def _extract_fgi(self, fgi_data: Dict[str, Any]) -> Optional[SignalValue]:
        """Extract Fear & Greed Index signal."""
        if not fgi_data:
            return None
        
        value = fgi_data.get("value", 50)
        
        # Classify (contrarian)
        if value <= 25:
            signal = "EXTREME_FEAR"
            contrarian = "BUY"
            strength = 80
        elif value <= 45:
            signal = "FEAR"
            contrarian = "LEAN_BUY"
            strength = 65
        elif value <= 55:
            signal = "NEUTRAL"
            contrarian = "HOLD"
            strength = 50
        elif value <= 75:
            signal = "GREED"
            contrarian = "LEAN_SELL"
            strength = 65
        else:
            signal = "EXTREME_GREED"
            contrarian = "SELL"
            strength = 80
        
        return SignalValue(
            name="FGI",
            value=value,
            signal=signal,
            strength=strength,
            tier="SENTIMENT",
            source="alternative_me",
            raw_data={
                "classification": fgi_data.get("classification"),
                "contrarian_signal": contrarian
            }
        )
    
    # ========================================================================
    # HELPERS
    # ========================================================================
    
    def _update_price_history(self, symbol: str, price: float):
        """Update price history for volatility calculation."""
        if price <= 0:
            return
        
        if symbol not in self._price_history:
            self._price_history[symbol] = []
        
        self._price_history[symbol].append(price)
        
        # Keep last 100 samples
        if len(self._price_history[symbol]) > 100:
            self._price_history[symbol] = self._price_history[symbol][-100:]



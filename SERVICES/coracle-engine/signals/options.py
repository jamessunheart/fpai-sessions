"""
Coracle Options/Gamma Signals
==============================
Integration guide and placeholder for options-derived metrics.

Required API: Deribit (free) or Laevitas (paid)

Options signals:
- GEX: Gamma Exposure (volatility indicator)
- PCR: Put/Call Ratio
- Max Pain: Options max pain level
- IV: Implied Volatility

To enable:
1. Deribit (free): No API key needed for public data
2. Laevitas (paid): Pre-calculated GEX, max pain, flows
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import logging
import math

import httpx

from app.models import SignalValue

logger = logging.getLogger(__name__)


# Deribit API (free, no auth needed for public data)
DERIBIT_BASE = "https://www.deribit.com/api/v2/public"

# Laevitas API (paid)
LAEVITAS_BASE = "https://api.laevitas.ch/historical"


class OptionsSignals:
    """
    Options-derived signal fetcher.
    
    Uses Deribit public API (free) or Laevitas (paid).
    """
    
    def __init__(self, laevitas_api_key: Optional[str] = None):
        self.laevitas_key = laevitas_api_key
        self.use_laevitas = bool(laevitas_api_key)
        
        logger.info(
            f"Options signals initialized - "
            f"Provider: {'Laevitas' if self.use_laevitas else 'Deribit (free)'}"
        )
    
    async def get_gex(self, asset: str = "BTC") -> Optional[SignalValue]:
        """
        Get Gamma Exposure estimate.
        
        GEX = Sum of (Gamma × Open Interest × Contract Size × Spot Price)
        - Positive GEX: Dealers hedging suppresses volatility
        - Negative GEX: Dealers hedging amplifies volatility
        
        For trading: Negative GEX = trending moves more likely
        """
        try:
            if self.use_laevitas:
                gex = await self._fetch_laevitas_gex(asset)
            else:
                gex = await self._calculate_gex_from_deribit(asset)
            
            if gex is None:
                return None
            
            # Normalize GEX (typically in billions)
            gex_normalized = gex / 1e9
            
            # Classify signal
            if gex_normalized < -0.5:
                signal, strength = "HIGH_VOLATILITY_EXPANSION", 85
            elif gex_normalized < 0:
                signal, strength = "VOLATILITY_EXPANSION", 70
            elif gex_normalized > 0.5:
                signal, strength = "VOLATILITY_SUPPRESSION", 70
            else:
                signal, strength = "NEUTRAL", 50
            
            return SignalValue(
                name="GEX",
                value=gex_normalized,
                signal=signal,
                strength=strength,
                tier="DERIVATIVES",
                source="deribit" if not self.use_laevitas else "laevitas",
                raw_data={"raw_gex": gex, "interpretation": self._interpret_gex(gex_normalized)}
            )
            
        except Exception as e:
            logger.error(f"GEX calculation failed: {e}")
            return None
    
    async def get_pcr(self, asset: str = "BTC") -> Optional[SignalValue]:
        """
        Get Put/Call Ratio from open interest.
        
        PCR = Put OI / Call OI
        - > 1.0: More puts (bearish positioning)
        - < 1.0: More calls (bullish positioning)
        - Extreme values are contrarian signals
        """
        try:
            instruments = await self._fetch_deribit_instruments(asset, "option")
            if not instruments:
                return None
            
            put_oi = 0
            call_oi = 0
            
            for inst in instruments:
                oi = inst.get("open_interest", 0)
                if "P" in inst.get("instrument_name", ""):
                    put_oi += oi
                else:
                    call_oi += oi
            
            if call_oi == 0:
                return None
            
            pcr = put_oi / call_oi
            
            # Classify (contrarian)
            if pcr > 1.5:
                signal, strength = "EXTREME_PUT_HEAVY", 80  # Contrarian bullish
            elif pcr > 1.0:
                signal, strength = "PUT_HEAVY", 65
            elif pcr < 0.5:
                signal, strength = "EXTREME_CALL_HEAVY", 80  # Contrarian bearish
            elif pcr < 0.8:
                signal, strength = "CALL_HEAVY", 65
            else:
                signal, strength = "BALANCED", 50
            
            return SignalValue(
                name="PCR",
                value=round(pcr, 4),
                signal=signal,
                strength=strength,
                tier="DERIVATIVES",
                source="deribit",
                raw_data={
                    "put_oi": put_oi,
                    "call_oi": call_oi,
                    "contrarian": "BULLISH" if pcr > 1.0 else "BEARISH"
                }
            )
            
        except Exception as e:
            logger.error(f"PCR calculation failed: {e}")
            return None
    
    async def get_max_pain(self, asset: str = "BTC") -> Optional[Dict[str, Any]]:
        """
        Calculate max pain level.
        
        Max pain = Strike where options expire worthless
        = Price where option sellers profit most
        
        Price tends to gravitate toward max pain near expiry.
        """
        try:
            instruments = await self._fetch_deribit_instruments(asset, "option")
            if not instruments:
                return None
            
            # Get current price
            price = await self._fetch_deribit_price(asset)
            if not price:
                return None
            
            # Group by strike
            strikes: Dict[float, Dict] = {}
            for inst in instruments:
                strike = inst.get("strike")
                if strike:
                    if strike not in strikes:
                        strikes[strike] = {"put_oi": 0, "call_oi": 0}
                    
                    oi = inst.get("open_interest", 0)
                    if "P" in inst.get("instrument_name", ""):
                        strikes[strike]["put_oi"] += oi
                    else:
                        strikes[strike]["call_oi"] += oi
            
            # Calculate pain at each strike
            min_pain = float("inf")
            max_pain_strike = price
            
            for strike, data in strikes.items():
                # Pain for option holders if price ends at this strike
                call_pain = sum(
                    max(0, s - strike) * strikes[s]["call_oi"]
                    for s in strikes
                )
                put_pain = sum(
                    max(0, strike - s) * strikes[s]["put_oi"]
                    for s in strikes
                )
                total_pain = call_pain + put_pain
                
                if total_pain < min_pain:
                    min_pain = total_pain
                    max_pain_strike = strike
            
            distance_pct = ((max_pain_strike - price) / price) * 100
            
            return {
                "max_pain": max_pain_strike,
                "current_price": price,
                "distance_pct": round(distance_pct, 2),
                "direction": "UP" if max_pain_strike > price else "DOWN",
                "magnitude": abs(distance_pct)
            }
            
        except Exception as e:
            logger.error(f"Max pain calculation failed: {e}")
            return None
    
    async def get_all_signals(self, asset: str = "BTC") -> Dict[str, Any]:
        """Get all available options signals."""
        return {
            "gex": await self.get_gex(asset),
            "pcr": await self.get_pcr(asset),
            "max_pain": await self.get_max_pain(asset)
        }
    
    async def _fetch_deribit_instruments(
        self, 
        asset: str, 
        kind: str = "option"
    ) -> List[Dict]:
        """Fetch instruments from Deribit."""
        url = f"{DERIBIT_BASE}/get_instruments"
        params = {
            "currency": asset.upper(),
            "kind": kind,
            "expired": "false"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("result", [])
                    
        except Exception as e:
            logger.error(f"Deribit instruments fetch failed: {e}")
        
        return []
    
    async def _fetch_deribit_price(self, asset: str) -> Optional[float]:
        """Fetch index price from Deribit."""
        url = f"{DERIBIT_BASE}/get_index_price"
        params = {"index_name": f"{asset.lower()}_usd"}
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, params=params)
                
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("result", {}).get("index_price")
                    
        except Exception as e:
            logger.error(f"Deribit price fetch failed: {e}")
        
        return None
    
    async def _calculate_gex_from_deribit(self, asset: str) -> Optional[float]:
        """
        Estimate GEX from Deribit options data.
        
        Simplified calculation - for production, use Laevitas.
        """
        instruments = await self._fetch_deribit_instruments(asset, "option")
        price = await self._fetch_deribit_price(asset)
        
        if not instruments or not price:
            return None
        
        total_gex = 0
        
        for inst in instruments:
            strike = inst.get("strike", 0)
            oi = inst.get("open_interest", 0)
            
            if strike == 0 or oi == 0:
                continue
            
            # Simplified gamma estimate using Black-Scholes approximation
            # Real gamma requires IV and time to expiry
            moneyness = strike / price
            
            # Approximate gamma (peaks at ATM)
            gamma_approx = math.exp(-0.5 * (moneyness - 1) ** 2 / 0.01)
            
            # GEX contribution
            # Calls: positive gamma, Puts: negative gamma from dealer perspective
            is_call = "C" in inst.get("instrument_name", "")
            sign = 1 if is_call else -1
            
            gex_contrib = sign * gamma_approx * oi * price
            total_gex += gex_contrib
        
        return total_gex
    
    async def _fetch_laevitas_gex(self, asset: str) -> Optional[float]:
        """Fetch pre-calculated GEX from Laevitas."""
        if not self.laevitas_key:
            return None
        
        # Laevitas API endpoint (example - check actual docs)
        url = f"{LAEVITAS_BASE}/gex/{asset.lower()}"
        headers = {"Authorization": f"Bearer {self.laevitas_key}"}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("gex")
                    
        except Exception as e:
            logger.error(f"Laevitas GEX fetch failed: {e}")
        
        return None
    
    def _interpret_gex(self, gex: float) -> str:
        """Human-readable GEX interpretation."""
        if gex < -0.5:
            return "Strong negative gamma - expect amplified price moves and trends"
        elif gex < 0:
            return "Negative gamma - dealers will chase price, volatility expanding"
        elif gex > 0.5:
            return "Strong positive gamma - expect mean reversion and range-bound action"
        else:
            return "Neutral gamma - balanced dealer positioning"


# Integration example for developers
INTEGRATION_EXAMPLE = """
# To integrate options signals:

## Option 1: Deribit (FREE)
No API key needed - uses public endpoints.
Signals available:
- PCR (Put/Call Ratio)
- Max Pain
- Estimated GEX (simplified)

## Option 2: Laevitas (PAID)
More accurate, pre-calculated metrics.
1. Sign up at https://laevitas.ch
2. Set LAEVITAS_API_KEY environment variable

Laevitas provides:
- Accurate GEX calculation
- Historical options flow
- Dealer positioning data
- IV surfaces

Usage in Coracle:
The GEX signal is used in the Sacred Gate validation.
When GEX < 0, the gamma key passes (volatility expansion regime).
"""



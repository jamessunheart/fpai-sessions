"""
Coracle On-Chain Signals
=========================
Integration guide and placeholder for on-chain metrics.

Required API: Glassnode or CryptoQuant

On-chain signals:
- SOPR: Spent Output Profit Ratio
- MVRV: Market Value to Realized Value
- NUPL: Net Unrealized Profit/Loss
- DF: Difficulty Ribbon (for BTC)

To enable:
1. Sign up for Glassnode (https://glassnode.com) - ~$29/month Standard
2. Or CryptoQuant (https://cryptoquant.com)
3. Set GLASSNODE_API_KEY in environment
"""
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import logging

import httpx

from app.models import SignalValue

logger = logging.getLogger(__name__)


# Glassnode API endpoints
GLASSNODE_BASE = "https://api.glassnode.com/v1/metrics"

# Thresholds for signal classification
SOPR_THRESHOLDS = {
    "BULLISH": 1.05,      # Profit taking, but market absorbing
    "LEAN_BULLISH": 1.02,
    "NEUTRAL_HIGH": 1.01,
    "NEUTRAL_LOW": 0.99,
    "LEAN_BEARISH": 0.98,
    "BEARISH": 0.95       # Capitulation
}

MVRV_THRESHOLDS = {
    "EXTREME_OVERVALUED": 3.7,
    "OVERVALUED": 2.4,
    "FAIR": 1.0,
    "UNDERVALUED": 0.8,
    "EXTREME_UNDERVALUED": 0.5
}


class OnChainSignals:
    """
    On-chain signal fetcher.
    
    Requires Glassnode or CryptoQuant API key.
    """
    
    def __init__(self, api_key: Optional[str] = None, provider: str = "glassnode"):
        self.api_key = api_key
        self.provider = provider
        self.available = bool(api_key)
        
        if not self.available:
            logger.info(
                "On-chain signals disabled - no API key. "
                "Set GLASSNODE_API_KEY to enable SOPR, MVRV, NUPL signals."
            )
    
    async def get_sopr(self, asset: str = "BTC") -> Optional[SignalValue]:
        """
        Get Spent Output Profit Ratio.
        
        SOPR = Realized Value / Spent Value
        - > 1: Sellers in profit (bullish if market absorbs)
        - < 1: Sellers at loss (bearish/capitulation)
        - = 1: Break-even level (often support/resistance)
        """
        if not self.available:
            return None
        
        try:
            value = await self._fetch_glassnode(
                "indicators/sopr",
                asset=asset.lower()
            )
            
            if value is None:
                return None
            
            # Classify signal
            if value >= SOPR_THRESHOLDS["BULLISH"]:
                signal, strength = "BULLISH", 75
            elif value >= SOPR_THRESHOLDS["LEAN_BULLISH"]:
                signal, strength = "LEAN_BULLISH", 60
            elif value <= SOPR_THRESHOLDS["BEARISH"]:
                signal, strength = "BEARISH", 75
            elif value <= SOPR_THRESHOLDS["LEAN_BEARISH"]:
                signal, strength = "LEAN_BEARISH", 60
            else:
                signal, strength = "NEUTRAL", 50
            
            return SignalValue(
                name="SOPR",
                value=value,
                signal=signal,
                strength=strength,
                tier="ON_CHAIN",
                source=f"{self.provider}_api"
            )
            
        except Exception as e:
            logger.error(f"SOPR fetch failed: {e}")
            return None
    
    async def get_mvrv(self, asset: str = "BTC") -> Optional[SignalValue]:
        """
        Get Market Value to Realized Value.
        
        MVRV = Market Cap / Realized Cap
        - > 3.7: Extremely overvalued (sell signal)
        - 2.4-3.7: Overvalued
        - 1.0-2.4: Fair value
        - 0.5-1.0: Undervalued (buy signal)
        - < 0.5: Extremely undervalued (strong buy)
        """
        if not self.available:
            return None
        
        try:
            value = await self._fetch_glassnode(
                "market/mvrv",
                asset=asset.lower()
            )
            
            if value is None:
                return None
            
            # Classify signal (contrarian)
            if value >= MVRV_THRESHOLDS["EXTREME_OVERVALUED"]:
                signal, strength = "EXTREMELY_OVERVALUED", 90
            elif value >= MVRV_THRESHOLDS["OVERVALUED"]:
                signal, strength = "OVERVALUED", 70
            elif value <= MVRV_THRESHOLDS["EXTREME_UNDERVALUED"]:
                signal, strength = "EXTREMELY_UNDERVALUED", 90
            elif value <= MVRV_THRESHOLDS["UNDERVALUED"]:
                signal, strength = "UNDERVALUED", 70
            else:
                signal, strength = "FAIR_VALUE", 50
            
            return SignalValue(
                name="MVRV",
                value=value,
                signal=signal,
                strength=strength,
                tier="ON_CHAIN",
                source=f"{self.provider}_api",
                raw_data={"interpretation": self._interpret_mvrv(value)}
            )
            
        except Exception as e:
            logger.error(f"MVRV fetch failed: {e}")
            return None
    
    async def get_nupl(self, asset: str = "BTC") -> Optional[SignalValue]:
        """
        Get Net Unrealized Profit/Loss.
        
        NUPL = (Market Cap - Realized Cap) / Market Cap
        - > 0.75: Euphoria (extreme greed - sell)
        - 0.5-0.75: Greed
        - 0.25-0.5: Optimism
        - 0-0.25: Hope/Anxiety
        - < 0: Capitulation (buy)
        """
        if not self.available:
            return None
        
        try:
            value = await self._fetch_glassnode(
                "indicators/net_unrealized_profit_loss",
                asset=asset.lower()
            )
            
            if value is None:
                return None
            
            # Classify signal (contrarian)
            if value >= 0.75:
                signal, strength = "EUPHORIA", 85
            elif value >= 0.5:
                signal, strength = "GREED", 70
            elif value >= 0.25:
                signal, strength = "OPTIMISM", 55
            elif value >= 0:
                signal, strength = "ANXIETY", 45
            else:
                signal, strength = "CAPITULATION", 80
            
            return SignalValue(
                name="NUPL",
                value=value,
                signal=signal,
                strength=strength,
                tier="ON_CHAIN",
                source=f"{self.provider}_api"
            )
            
        except Exception as e:
            logger.error(f"NUPL fetch failed: {e}")
            return None
    
    async def get_all_signals(self, asset: str = "BTC") -> Dict[str, Optional[SignalValue]]:
        """Get all available on-chain signals."""
        return {
            "sopr": await self.get_sopr(asset),
            "mvrv": await self.get_mvrv(asset),
            "nupl": await self.get_nupl(asset)
        }
    
    async def _fetch_glassnode(self, endpoint: str, asset: str = "btc") -> Optional[float]:
        """Fetch data from Glassnode API."""
        if not self.api_key:
            return None
        
        url = f"{GLASSNODE_BASE}/{endpoint}"
        params = {
            "a": asset,
            "api_key": self.api_key
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                
                if resp.status_code == 200:
                    data = resp.json()
                    # Glassnode returns list of {t: timestamp, v: value}
                    if data and len(data) > 0:
                        return data[-1].get("v")
                else:
                    logger.warning(f"Glassnode API error: {resp.status_code}")
                    
        except Exception as e:
            logger.error(f"Glassnode fetch failed: {e}")
        
        return None
    
    def _interpret_mvrv(self, value: float) -> str:
        """Human-readable MVRV interpretation."""
        if value >= 3.7:
            return "Market extremely overvalued - high probability of correction"
        elif value >= 2.4:
            return "Market overvalued - caution advised"
        elif value <= 0.5:
            return "Market extremely undervalued - historical accumulation zone"
        elif value <= 0.8:
            return "Market undervalued - favorable buying opportunity"
        else:
            return "Market at fair value"


# Integration example for developers
INTEGRATION_EXAMPLE = """
# To integrate on-chain signals:

1. Get API key from Glassnode:
   - Go to https://glassnode.com
   - Sign up for Standard tier (~$29/month)
   - Generate API key

2. Set environment variable:
   export GLASSNODE_API_KEY=your_api_key_here

3. The signals will automatically be fetched and included in analysis:
   - SOPR: Indicates profit/loss of spent coins
   - MVRV: Market valuation relative to realized value
   - NUPL: Overall market profit/loss state

4. Alternative: CryptoQuant
   - Similar metrics available
   - Different pricing model
   - Set CRYPTOQUANT_API_KEY instead
"""



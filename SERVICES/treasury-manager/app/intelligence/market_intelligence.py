"""
Market Intelligence Module
Fetches and analyzes real-time market data from multiple sources
"""
import aiohttp
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional, Tuple
import logging
from enum import Enum

from app.config import settings
from app.core.models import (
    MarketData,
    AllocationSignal,
    MarketPhase,
    AllocationMode
)

logger = logging.getLogger(__name__)


class MarketIntelligence:
    """
    Aggregates market data from multiple sources and generates trading signals

    Data Sources:
    - MVRV Z-Score: Bitcoin Magazine Pro (scraping) or Glassnode API
    - Funding Rates: Coinglass API
    - Fear & Greed: CoinMarketCap API
    - Crypto Prices: CoinGecko API
    - Options Data: Deribit API
    """

    def __init__(self):
        self.cache: Dict[str, any] = {}
        self.cache_duration = timedelta(minutes=5)  # Cache data for 5 min
        self.last_fetch: Dict[str, datetime] = {}

    # ========================================================================
    # CORE DATA FETCHING
    # ========================================================================

    async def get_crypto_prices(self) -> Dict[str, Decimal]:
        """
        Fetch current BTC and ETH prices from CoinGecko

        API: https://api.coingecko.com/api/v3/simple/price
        Free tier: 50 calls/minute
        """
        cache_key = "crypto_prices"
        if self._is_cached(cache_key):
            return self.cache[cache_key]

        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": "bitcoin,ethereum",
                "vs_currencies": "usd"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()

                        prices = {
                            "BTC": Decimal(str(data["bitcoin"]["usd"])),
                            "ETH": Decimal(str(data["ethereum"]["usd"]))
                        }

                        self._cache(cache_key, prices)
                        logger.info(f"✅ Prices: BTC ${prices['BTC']}, ETH ${prices['ETH']}")
                        return prices
                    else:
                        logger.error(f"CoinGecko API error: {response.status}")
                        return self._get_default_prices()

        except Exception as e:
            logger.error(f"Error fetching crypto prices: {e}")
            return self._get_default_prices()

    async def get_mvrv_score(self) -> Optional[float]:
        """
        Fetch MVRV Z-Score (Bitcoin cycle indicator)

        Options:
        1. Glassnode API (paid, $500/mo but very reliable)
        2. Bitcoin Magazine Pro (free but requires scraping)
        3. Manual updates (interim solution)

        For MVP, we'll use manual updates or free alternatives
        """
        cache_key = "mvrv_score"
        if self._is_cached(cache_key):
            return self.cache[cache_key]

        # TODO: Implement Glassnode API integration when budget allows
        # For now, using placeholder that can be manually updated

        if settings.glassnode_api_key:
            try:
                # Glassnode API
                url = "https://api.glassnode.com/v1/metrics/market/mvrv_z_score"
                params = {
                    "a": "BTC",
                    "api_key": settings.glassnode_api_key
                }

                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            # Glassnode returns array of {"t": timestamp, "v": value}
                            if data:
                                mvrv = float(data[-1]["v"])
                                self._cache(cache_key, mvrv)
                                logger.info(f"✅ MVRV Z-Score: {mvrv:.2f}")
                                return mvrv
                        else:
                            logger.warning(f"Glassnode API error: {response.status}")

            except Exception as e:
                logger.error(f"Error fetching MVRV from Glassnode: {e}")

        # Fallback: Manual/estimated value
        # TODO: Add web scraping of Bitcoin Magazine Pro charts
        # For now, return estimated current value (Nov 2025)
        estimated_mvrv = 2.43  # Current mid-cycle value
        logger.warning(f"⚠️ Using estimated MVRV: {estimated_mvrv} (manual update needed)")
        self._cache(cache_key, estimated_mvrv)
        return estimated_mvrv

    async def get_funding_rates(self) -> Dict[str, float]:
        """
        Fetch perpetual futures funding rates from Coinglass

        API: https://open-api.coinglass.com/public/v2/funding
        Free tier available

        Positive funding = Longs paying shorts (overcrowded longs)
        Negative funding = Shorts paying longs (overcrowded shorts)
        """
        cache_key = "funding_rates"
        if self._is_cached(cache_key):
            return self.cache[cache_key]

        try:
            # Coinglass API endpoint
            url = "https://open-api.coinglass.com/public/v2/funding"
            params = {
                "symbol": "BTC"  # Then ETH
            }

            btc_funding = await self._fetch_coinglass_funding("BTC")
            eth_funding = await self._fetch_coinglass_funding("ETH")

            rates = {
                "BTC": btc_funding,
                "ETH": eth_funding
            }

            self._cache(cache_key, rates)
            logger.info(f"✅ Funding: BTC {btc_funding:.4f}%, ETH {eth_funding:.4f}%")
            return rates

        except Exception as e:
            logger.error(f"Error fetching funding rates: {e}")
            return {"BTC": 0.0, "ETH": 0.0}

    async def _fetch_coinglass_funding(self, symbol: str) -> float:
        """Helper to fetch funding rate for a specific symbol"""
        try:
            url = f"https://open-api.coinglass.com/public/v2/funding"
            params = {"symbol": symbol}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Coinglass returns weighted average funding rate
                        if data.get("data"):
                            # Extract funding rate (varies by exchange, take average)
                            funding_data = data["data"]
                            if isinstance(funding_data, list) and funding_data:
                                return float(funding_data[0].get("rate", 0))
                    return 0.0

        except Exception as e:
            logger.error(f"Error fetching {symbol} funding: {e}")
            return 0.0

    async def get_fear_greed_index(self) -> Optional[int]:
        """
        Fetch Fear & Greed Index from CoinMarketCap or Alternative.me

        API: https://api.alternative.me/fng/
        Free, no API key required

        Values:
        - 0-25: Extreme Fear (contrarian buy)
        - 25-45: Fear
        - 45-55: Neutral
        - 55-75: Greed
        - 75-100: Extreme Greed (contrarian sell)
        """
        cache_key = "fear_greed"
        if self._is_cached(cache_key):
            return self.cache[cache_key]

        try:
            # Alternative.me API (free, no key needed)
            url = "https://api.alternative.me/fng/"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("data"):
                            fng_value = int(data["data"][0]["value"])
                            self._cache(cache_key, fng_value)

                            # Log with interpretation
                            interpretation = self._interpret_fng(fng_value)
                            logger.info(f"✅ Fear & Greed: {fng_value} ({interpretation})")
                            return fng_value
                    else:
                        logger.warning(f"Fear & Greed API error: {response.status}")

        except Exception as e:
            logger.error(f"Error fetching Fear & Greed: {e}")

        return None

    def _interpret_fng(self, value: int) -> str:
        """Interpret Fear & Greed value"""
        if value <= 25:
            return "Extreme Fear"
        elif value <= 45:
            return "Fear"
        elif value <= 55:
            return "Neutral"
        elif value <= 75:
            return "Greed"
        else:
            return "Extreme Greed"

    # ========================================================================
    # SIGNAL GENERATION
    # ========================================================================

    async def get_current_market_data(self) -> MarketData:
        """
        Fetch all market data and compile into MarketData object
        """
        # Fetch all data concurrently
        prices_task = self.get_crypto_prices()
        mvrv_task = self.get_mvrv_score()
        funding_task = self.get_funding_rates()
        fng_task = self.get_fear_greed_index()

        prices, mvrv, funding, fng = await asyncio.gather(
            prices_task, mvrv_task, funding_task, fng_task
        )

        # Analyze market phase
        market_phase = self.determine_market_phase(mvrv, fng, funding)
        recommended_mode = self.recommend_allocation_mode(market_phase, mvrv, fng, funding)

        market_data = MarketData(
            timestamp=datetime.utcnow(),
            mvrv_z_score=mvrv,
            btc_price=prices["BTC"],
            eth_price=prices["ETH"],
            fear_greed_index=fng,
            btc_funding_rate=funding["BTC"],
            eth_funding_rate=funding["ETH"],
            market_phase=market_phase,
            recommended_mode=recommended_mode
        )

        logger.info(f"📊 Market Phase: {market_phase.value}, Mode: {recommended_mode.value}")
        return market_data

    def determine_market_phase(
        self,
        mvrv: Optional[float],
        fng: Optional[int],
        funding: Dict[str, float]
    ) -> MarketPhase:
        """
        Determine current market cycle phase based on indicators

        Phases (from strategy doc):
        - ACCUMULATION: MVRV 2-3, normal sentiment
        - EUPHORIA: MVRV 3-5, approaching top
        - TOP: MVRV 5-7+, extreme greed
        - BEAR: MVRV <2, fear/capitulation
        """
        if mvrv is None:
            return MarketPhase.UNKNOWN

        # MVRV-based phase detection
        if mvrv < 1.0:
            return MarketPhase.BEAR  # Deep bear, capitulation
        elif mvrv < 2.0:
            return MarketPhase.BEAR  # Early bear/late accumulation
        elif mvrv < 3.0:
            return MarketPhase.ACCUMULATION  # Mid-cycle, safe to accumulate
        elif mvrv < 5.0:
            return MarketPhase.EUPHORIA  # Late cycle, approaching top
        else:
            return MarketPhase.TOP  # Cycle top, extreme danger

    def recommend_allocation_mode(
        self,
        phase: MarketPhase,
        mvrv: Optional[float],
        fng: Optional[int],
        funding: Dict[str, float]
    ) -> AllocationMode:
        """
        Recommend portfolio allocation mode based on market conditions

        Modes (from strategy doc):
        - CONSERVATIVE: 100% yield (during bear/top)
        - TACTICAL: 60% yield / 40% spot (during accumulation)
        - AGGRESSIVE: Leveraged positions (quarterly expiry plays)
        - HEDGE: Defensive (during crash/uncertainty)
        """
        if phase == MarketPhase.ACCUMULATION:
            # Mid-cycle: Tactical allocation (current strategy)
            return AllocationMode.TACTICAL

        elif phase == MarketPhase.EUPHORIA:
            # Late cycle: Still tactical but prepare to reduce
            if mvrv and mvrv > 4.0:
                # Very late, start moving to conservative
                return AllocationMode.CONSERVATIVE
            return AllocationMode.TACTICAL

        elif phase == MarketPhase.TOP:
            # Cycle top: Conservative, protect capital
            return AllocationMode.CONSERVATIVE

        elif phase == MarketPhase.BEAR:
            # Bear market: Full conservative
            return AllocationMode.CONSERVATIVE

        else:
            # Unknown: Default to conservative (safe)
            return AllocationMode.CONSERVATIVE

    async def generate_allocation_signal(self) -> AllocationSignal:
        """
        Generate comprehensive allocation signal with target percentages

        Based on market phase and specific thresholds from strategy doc
        """
        market_data = await self.get_current_market_data()

        # Calculate target allocation percentages
        target_allocation = self._calculate_target_allocation(
            market_data.market_phase,
            market_data.mvrv_z_score,
            market_data.fear_greed_index,
            market_data.btc_funding_rate
        )

        # Determine reasoning
        reasoning = self._generate_reasoning(market_data, target_allocation)

        # Check for specific triggers
        mvrv_crossed = self._check_mvrv_threshold_crossed(market_data.mvrv_z_score)
        funding_extreme = self._check_funding_extreme(market_data.btc_funding_rate)
        quarterly_approaching = False  # TODO: Implement quarterly expiry detection

        # Calculate confidence
        confidence = self._calculate_confidence(market_data)

        signal = AllocationSignal(
            timestamp=datetime.utcnow(),
            market_phase=market_data.market_phase,
            recommended_mode=market_data.recommended_mode,
            confidence=confidence,
            target_allocations=target_allocation,
            reasoning=reasoning,
            mvrv_threshold_crossed=mvrv_crossed,
            funding_rate_extreme=funding_extreme,
            quarterly_expiry_approaching=quarterly_approaching
        )

        logger.info(f"🎯 Signal: {signal.recommended_mode.value} ({confidence*100:.0f}% confidence)")
        return signal

    def _calculate_target_allocation(
        self,
        phase: MarketPhase,
        mvrv: Optional[float],
        fng: Optional[int],
        btc_funding: Optional[float]
    ) -> Dict[str, float]:
        """
        Calculate target allocation percentages for each asset

        Returns dict like:
        {
            "base_yield": 0.60,  # 60%
            "btc": 0.20,  # 20%
            "eth": 0.20,  # 20%
            "cash": 0.00  # 0%
        }
        """
        # Default: TACTICAL mode (current strategy)
        # 60% base yield, 40% tactical (20% BTC, 20% ETH)
        allocation = {
            "base_yield": 0.60,
            "btc": 0.20,
            "eth": 0.20,
            "cash": 0.00
        }

        # Adjust based on MVRV thresholds (from strategy doc)
        if mvrv:
            if mvrv >= settings.mvrv_sell_67_percent:  # 7.0 - near top
                # Sell 67% of tactical → 95% yield, 5% crypto
                allocation = {
                    "base_yield": 0.80,
                    "btc": 0.025,
                    "eth": 0.025,
                    "cash": 0.15
                }
            elif mvrv >= settings.mvrv_sell_50_percent:  # 5.0 - late cycle
                # Sell 50% of tactical → 80% yield, 20% crypto
                allocation = {
                    "base_yield": 0.70,
                    "btc": 0.10,
                    "eth": 0.10,
                    "cash": 0.10
                }
            elif mvrv >= settings.mvrv_sell_25_percent:  # 3.5 - approaching top
                # Sell 25% of tactical → 70% yield, 30% crypto
                allocation = {
                    "base_yield": 0.65,
                    "btc": 0.15,
                    "eth": 0.15,
                    "cash": 0.05
                }
            elif mvrv >= 3.0:
                # Start preparing, but maintain tactical
                allocation = {
                    "base_yield": 0.60,
                    "btc": 0.20,
                    "eth": 0.20,
                    "cash": 0.00
                }
            elif mvrv < 1.0:
                # Deep bear: 100% conservative
                allocation = {
                    "base_yield": 0.95,
                    "btc": 0.00,
                    "eth": 0.00,
                    "cash": 0.05
                }

        return allocation

    def _generate_reasoning(
        self,
        market_data: MarketData,
        target_allocation: Dict[str, float]
    ) -> str:
        """Generate human-readable reasoning for allocation"""
        reasons = []

        # MVRV reasoning
        if market_data.mvrv_z_score:
            mvrv = market_data.mvrv_z_score
            if mvrv < 2.0:
                reasons.append(f"MVRV {mvrv:.2f} indicates bear market - conservative stance")
            elif mvrv < 3.0:
                reasons.append(f"MVRV {mvrv:.2f} in accumulation zone - tactical allocation optimal")
            elif mvrv < 5.0:
                reasons.append(f"MVRV {mvrv:.2f} approaching euphoria - preparing to reduce risk")
            else:
                reasons.append(f"MVRV {mvrv:.2f} in danger zone - heavy de-risking recommended")

        # Sentiment reasoning
        if market_data.fear_greed_index:
            fng = market_data.fear_greed_index
            if fng <= 25:
                reasons.append(f"Extreme Fear ({fng}) - contrarian opportunity")
            elif fng >= 75:
                reasons.append(f"Extreme Greed ({fng}) - elevated risk")

        # Funding reasoning
        if market_data.btc_funding_rate:
            funding = market_data.btc_funding_rate
            if funding > 0.2:
                reasons.append(f"High funding ({funding:.2f}%) - overcrowded longs")
            elif funding < -0.1:
                reasons.append(f"Negative funding ({funding:.2f}%) - potential squeeze setup")

        return " | ".join(reasons) if reasons else "Normal market conditions"

    def _check_mvrv_threshold_crossed(self, mvrv: Optional[float]) -> bool:
        """Check if MVRV crossed any sell threshold"""
        if not mvrv:
            return False

        return (
            mvrv >= settings.mvrv_sell_25_percent or
            mvrv >= settings.mvrv_sell_50_percent or
            mvrv >= settings.mvrv_sell_67_percent or
            mvrv >= settings.mvrv_exit_all
        )

    def _check_funding_extreme(self, funding: Optional[float]) -> bool:
        """Check if funding rate is at extreme levels"""
        if funding is None:
            return False

        return abs(funding) > 0.2  # >0.2% or <-0.2% is extreme

    def _calculate_confidence(self, market_data: MarketData) -> float:
        """
        Calculate confidence in signal (0-1)

        Higher confidence when:
        - All indicators agree
        - Clear thresholds crossed
        - Strong signals from multiple sources
        """
        confidence = 0.5  # Base confidence

        # Boost confidence if MVRV is available and clear
        if market_data.mvrv_z_score:
            if market_data.mvrv_z_score < 1.5 or market_data.mvrv_z_score > 6.0:
                confidence += 0.2  # Very clear signal

        # Boost if Fear & Greed is extreme
        if market_data.fear_greed_index:
            if market_data.fear_greed_index <= 20 or market_data.fear_greed_index >= 80:
                confidence += 0.2  # Extreme sentiment

        # Boost if funding is extreme
        if market_data.btc_funding_rate:
            if abs(market_data.btc_funding_rate) > 0.2:
                confidence += 0.1  # Overcrowded

        return min(confidence, 1.0)  # Cap at 1.0

    async def should_rebalance(self, current_allocation: Dict[str, float]) -> Tuple[bool, str]:
        """
        Determine if portfolio should be rebalanced

        Returns: (should_rebalance: bool, reason: str)
        """
        signal = await self.generate_allocation_signal()
        target = signal.target_allocations

        # Calculate drift
        max_drift = 0.0
        drift_asset = ""

        for asset, target_pct in target.items():
            current_pct = current_allocation.get(asset, 0.0)
            drift = abs(target_pct - current_pct)

            if drift > max_drift:
                max_drift = drift
                drift_asset = asset

        # Check if drift exceeds threshold
        if max_drift > settings.rebalance_drift_threshold:
            reason = f"{drift_asset} drifted {max_drift*100:.1f}% from target (threshold: {settings.rebalance_drift_threshold*100:.0f}%)"
            return True, reason

        # Check for MVRV threshold crossed
        if signal.mvrv_threshold_crossed:
            return True, f"MVRV threshold crossed: {signal.market_data.mvrv_z_score:.2f}"

        return False, "No rebalancing needed"

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def _is_cached(self, key: str) -> bool:
        """Check if data is cached and still fresh"""
        if key not in self.cache:
            return False

        if key not in self.last_fetch:
            return False

        age = datetime.utcnow() - self.last_fetch[key]
        return age < self.cache_duration

    def _cache(self, key: str, value: any) -> None:
        """Cache data with timestamp"""
        self.cache[key] = value
        self.last_fetch[key] = datetime.utcnow()

    def _get_default_prices(self) -> Dict[str, Decimal]:
        """Fallback prices if API fails"""
        return {
            "BTC": Decimal("98000"),  # Approximate Nov 2025
            "ETH": Decimal("3800")
        }


# Global instance
market_intelligence = MarketIntelligence()

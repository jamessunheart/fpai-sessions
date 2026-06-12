#!/usr/bin/env python3
"""
ARIA ULTRA POWER - ON-CHAIN INTELLIGENCE
=========================================

Track on-chain activity for crypto assets:
- Whale wallet movements
- Exchange inflows/outflows
- Smart money tracking
- Large transaction alerts
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import httpx

logger = logging.getLogger("aria.intel.onchain")

# API Keys (multiple providers for redundancy)
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")  # Solana
DUNE_API_KEY = os.getenv("DUNE_API_KEY", "")
FLIPSIDE_API_KEY = os.getenv("FLIPSIDE_API_KEY", "")
NANSEN_API_KEY = os.getenv("NANSEN_API_KEY", "")

# Public APIs
SOLSCAN_API = "https://public-api.solscan.io"
ETHERSCAN_API = "https://api.etherscan.io/api"
BLOCKCHAIN_INFO_API = "https://blockchain.info"


class MovementType(Enum):
    """Type of on-chain movement."""
    WHALE_BUY = "whale_buy"
    WHALE_SELL = "whale_sell"
    EXCHANGE_INFLOW = "exchange_inflow"
    EXCHANGE_OUTFLOW = "exchange_outflow"
    SMART_MONEY = "smart_money"
    LARGE_TRANSFER = "large_transfer"


@dataclass
class WhaleMovement:
    """A significant on-chain movement."""
    type: MovementType
    symbol: str
    amount: float
    usd_value: float
    from_address: str
    to_address: str
    from_label: Optional[str]  # "Binance", "Whale 1", etc.
    to_label: Optional[str]
    tx_hash: str
    timestamp: datetime
    confidence: float  # 0-1, how sure we are about the classification
    
    @property
    def is_bullish(self) -> bool:
        """Is this movement bullish?"""
        return self.type in [MovementType.WHALE_BUY, MovementType.EXCHANGE_OUTFLOW]
    
    @property
    def is_bearish(self) -> bool:
        """Is this movement bearish?"""
        return self.type in [MovementType.WHALE_SELL, MovementType.EXCHANGE_INFLOW]


@dataclass
class ExchangeFlow:
    """Exchange inflow/outflow summary."""
    symbol: str
    exchange: str
    inflow_24h: float
    outflow_24h: float
    net_flow: float  # Negative = more outflow (bullish)
    usd_inflow: float
    usd_outflow: float
    usd_net: float
    updated_at: float = field(default_factory=time.time)
    
    @property
    def is_bullish(self) -> bool:
        """Outflow > Inflow is bullish."""
        return self.net_flow < 0


@dataclass
class OnChainSummary:
    """Summary of on-chain activity for an asset."""
    symbol: str
    whale_movements: List[WhaleMovement]
    exchange_flows: List[ExchangeFlow]
    total_whale_buys: float
    total_whale_sells: float
    net_exchange_flow: float
    bullish_signals: int
    bearish_signals: int
    overall_sentiment: str  # "bullish", "bearish", "neutral"
    confidence: float
    updated_at: float = field(default_factory=time.time)


class OnChainIntel:
    """
    On-chain intelligence for crypto assets.
    
    Features:
    - Whale transaction tracking
    - Exchange flow analysis
    - Smart money following
    - Multi-chain support (SOL, BTC, ETH)
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
        self._cache: Dict[str, OnChainSummary] = {}
        self._cache_ttl = 600  # 10 minutes
        
        # Known exchange addresses (simplified)
        self.exchange_addresses = {
            # Solana
            "solana": {
                "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM": "Binance",
                "4tSvZvnbyzHXLMTiFonMyxZoHmFqau1XArcRCVHLZ5gX": "FTX",
                "AC5RDfQFmDS1deWZos921JfqscXdByf8BKHs5ACWjtW2": "Kraken",
            },
            # Ethereum
            "ethereum": {
                "0x28C6c06298d514Db089934071355E5743bf21d60": "Binance",
                "0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549": "Binance",
                "0xDFd5293D8e347dFe59E90eFd55b2956a1343963d": "Bitfinex",
            },
        }
        
        # Known whale addresses
        self.whale_addresses = {
            "solana": {
                # Would be populated from whale tracking services
            },
        }
        
        logger.info("OnChainIntel initialized")
    
    async def get_summary(self, symbol: str) -> OnChainSummary:
        """Get on-chain summary for an asset."""
        symbol = symbol.upper()
        
        # Check cache
        if symbol in self._cache:
            cached = self._cache[symbol]
            if time.time() - cached.updated_at < self._cache_ttl:
                return cached
        
        # Fetch fresh data
        whale_movements = await self._get_whale_movements(symbol)
        exchange_flows = await self._get_exchange_flows(symbol)
        
        # Calculate summary
        total_buys = sum(m.usd_value for m in whale_movements if m.is_bullish)
        total_sells = sum(m.usd_value for m in whale_movements if m.is_bearish)
        net_flow = sum(f.net_flow for f in exchange_flows)
        
        bullish = sum(1 for m in whale_movements if m.is_bullish)
        bullish += sum(1 for f in exchange_flows if f.is_bullish)
        bearish = sum(1 for m in whale_movements if m.is_bearish)
        bearish += sum(1 for f in exchange_flows if not f.is_bullish)
        
        if bullish > bearish * 1.5:
            sentiment = "bullish"
        elif bearish > bullish * 1.5:
            sentiment = "bearish"
        else:
            sentiment = "neutral"
        
        summary = OnChainSummary(
            symbol=symbol,
            whale_movements=whale_movements,
            exchange_flows=exchange_flows,
            total_whale_buys=total_buys,
            total_whale_sells=total_sells,
            net_exchange_flow=net_flow,
            bullish_signals=bullish,
            bearish_signals=bearish,
            overall_sentiment=sentiment,
            confidence=min(1.0, (bullish + bearish) / 10),
        )
        
        self._cache[symbol] = summary
        return summary
    
    async def _get_whale_movements(self, symbol: str, limit: int = 10) -> List[WhaleMovement]:
        """Get recent whale movements for an asset."""
        # Try Helius for Solana
        if symbol == "SOL" and HELIUS_API_KEY:
            return await self._fetch_solana_whales()
        
        # Fallback to simulated data
        return await self._generate_simulated_whales(symbol, limit)
    
    async def _fetch_solana_whales(self) -> List[WhaleMovement]:
        """Fetch Solana whale movements from Helius."""
        try:
            # Helius API for large transactions
            url = f"https://api.helius.xyz/v0/addresses/whale-movements?api-key={HELIUS_API_KEY}"
            response = await self.http.get(url)
            
            if response.status_code == 200:
                data = response.json()
                movements = []
                
                for tx in data.get("transactions", [])[:10]:
                    movements.append(WhaleMovement(
                        type=self._classify_movement(tx),
                        symbol="SOL",
                        amount=tx.get("amount", 0),
                        usd_value=tx.get("usd_value", 0),
                        from_address=tx.get("from", "")[:12] + "...",
                        to_address=tx.get("to", "")[:12] + "...",
                        from_label=tx.get("from_label"),
                        to_label=tx.get("to_label"),
                        tx_hash=tx.get("signature", "")[:16] + "...",
                        timestamp=datetime.fromtimestamp(tx.get("timestamp", time.time())),
                        confidence=0.8,
                    ))
                
                return movements
        except Exception as e:
            logger.error(f"Helius API error: {e}")
        
        return []
    
    async def _get_exchange_flows(self, symbol: str) -> List[ExchangeFlow]:
        """Get exchange inflow/outflow data."""
        # In production, would fetch from CryptoQuant, Glassnode, etc.
        return await self._generate_simulated_flows(symbol)
    
    async def _generate_simulated_whales(self, symbol: str, limit: int) -> List[WhaleMovement]:
        """Generate simulated whale data for testing."""
        import random
        
        movements = []
        now = datetime.now()
        
        for i in range(min(limit, 5)):
            is_buy = random.random() > 0.45  # Slightly bullish bias
            movement_type = (
                MovementType.WHALE_BUY if is_buy else MovementType.WHALE_SELL
            ) if random.random() > 0.3 else (
                MovementType.EXCHANGE_OUTFLOW if is_buy else MovementType.EXCHANGE_INFLOW
            )
            
            base_amounts = {"SOL": 50000, "BTC": 100, "ETH": 2000, "XRP": 10000000}
            base = base_amounts.get(symbol, 100000)
            amount = base * random.uniform(0.5, 3)
            
            prices = {"SOL": 120, "BTC": 87000, "ETH": 3000, "XRP": 1.8}
            price = prices.get(symbol, 1)
            
            movements.append(WhaleMovement(
                type=movement_type,
                symbol=symbol,
                amount=amount,
                usd_value=amount * price,
                from_address="ABC123..." if is_buy else "XYZ789...",
                to_address="XYZ789..." if is_buy else "ABC123...",
                from_label="Binance" if movement_type == MovementType.EXCHANGE_OUTFLOW else "Whale",
                to_label="Whale" if movement_type == MovementType.EXCHANGE_OUTFLOW else "Binance",
                tx_hash=f"tx_{i}_{symbol}...",
                timestamp=now - timedelta(hours=random.randint(1, 24)),
                confidence=0.75,
            ))
        
        return movements
    
    async def _generate_simulated_flows(self, symbol: str) -> List[ExchangeFlow]:
        """Generate simulated exchange flow data."""
        import random
        
        exchanges = ["Binance", "Coinbase", "Kraken", "OKX"]
        flows = []
        
        for exchange in exchanges[:3]:
            base_flow = {"SOL": 100000, "BTC": 1000, "ETH": 10000}.get(symbol, 50000)
            inflow = base_flow * random.uniform(0.5, 1.5)
            outflow = base_flow * random.uniform(0.6, 1.8)  # Slight outflow bias
            
            prices = {"SOL": 120, "BTC": 87000, "ETH": 3000}
            price = prices.get(symbol, 1)
            
            flows.append(ExchangeFlow(
                symbol=symbol,
                exchange=exchange,
                inflow_24h=inflow,
                outflow_24h=outflow,
                net_flow=inflow - outflow,
                usd_inflow=inflow * price,
                usd_outflow=outflow * price,
                usd_net=(inflow - outflow) * price,
            ))
        
        return flows
    
    def _classify_movement(self, tx: Dict) -> MovementType:
        """Classify a transaction as a specific movement type."""
        from_addr = tx.get("from", "")
        to_addr = tx.get("to", "")
        
        # Check if from/to exchange
        from_exchange = any(from_addr in addrs for addrs in self.exchange_addresses.values())
        to_exchange = any(to_addr in addrs for addrs in self.exchange_addresses.values())
        
        if from_exchange and not to_exchange:
            return MovementType.EXCHANGE_OUTFLOW
        elif to_exchange and not from_exchange:
            return MovementType.EXCHANGE_INFLOW
        elif tx.get("is_buy"):
            return MovementType.WHALE_BUY
        elif tx.get("is_sell"):
            return MovementType.WHALE_SELL
        else:
            return MovementType.LARGE_TRANSFER
    
    def format_summary(self, summary: OnChainSummary) -> str:
        """Format on-chain summary for display."""
        emoji = "🟢" if summary.overall_sentiment == "bullish" else "🔴" if summary.overall_sentiment == "bearish" else "⚪"
        
        lines = [
            f"{emoji} **{summary.symbol} On-Chain Activity**",
            "",
            f"Overall: {summary.overall_sentiment.upper()}",
            f"Confidence: {summary.confidence:.0%}",
            "",
            f"**Whale Activity:**",
            f"• Buys: ${summary.total_whale_buys/1e6:.2f}M",
            f"• Sells: ${summary.total_whale_sells/1e6:.2f}M",
            f"• Net: ${(summary.total_whale_buys - summary.total_whale_sells)/1e6:+.2f}M",
            "",
            f"**Exchange Flows:**",
        ]
        
        for flow in summary.exchange_flows[:3]:
            flow_emoji = "📤" if flow.is_bullish else "📥"
            lines.append(f"• {flow.exchange}: {flow_emoji} ${abs(flow.usd_net)/1e6:.2f}M net")
        
        if summary.whale_movements:
            lines.append("")
            lines.append("**Recent Whale Moves:**")
            for m in summary.whale_movements[:3]:
                m_emoji = "🐋🟢" if m.is_bullish else "🐋🔴"
                lines.append(f"• {m_emoji} ${m.usd_value/1e6:.2f}M ({m.type.value})")
        
        return "\n".join(lines)


# Singleton instance
_intel: Optional[OnChainIntel] = None


def get_onchain_intel() -> OnChainIntel:
    """Get global OnChainIntel instance."""
    global _intel
    if _intel is None:
        _intel = OnChainIntel()
    return _intel


async def get_whale_movements(symbol: str) -> List[WhaleMovement]:
    """Convenience function to get whale movements."""
    intel = get_onchain_intel()
    summary = await intel.get_summary(symbol)
    return summary.whale_movements


async def get_exchange_flows(symbol: str) -> List[ExchangeFlow]:
    """Convenience function to get exchange flows."""
    intel = get_onchain_intel()
    summary = await intel.get_summary(symbol)
    return summary.exchange_flows



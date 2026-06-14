"""
WhaleTrack Collector
====================
Collects market data from our WhaleTrack trading system.
This is our primary source for crypto market intelligence.
"""

import httpx
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

logger = logging.getLogger("collector.whaletrack")

WHALETRACK_URL = "http://localhost:8600"


class DataItem:
    """Simple data item structure"""
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "")
        self.title = kwargs.get("title", "")
        self.summary = kwargs.get("summary")
        self.source = kwargs.get("source", "")
        self.source_url = kwargs.get("source_url")
        self.category = kwargs.get("category", "general")
        self.relevance_score = kwargs.get("relevance_score", 0.5)
        self.timestamp = kwargs.get("timestamp", datetime.now(timezone.utc).isoformat())
        self.entities = kwargs.get("entities", [])
        self.metadata = kwargs.get("metadata", {})
    
    def dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "source": self.source,
            "source_url": self.source_url,
            "category": self.category,
            "relevance_score": self.relevance_score,
            "timestamp": self.timestamp,
            "entities": self.entities,
            "metadata": self.metadata
        }


async def collect_whaletrack() -> List[DataItem]:
    """
    Collect market intelligence from WhaleTrack.
    
    Data includes:
    - Current price and direction
    - Whale confidence scores
    - Trading signals
    - Liquidation levels
    - Position information
    """
    items = []
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get main state
            resp = await client.get(f"{WHALETRACK_URL}/api/state")
            
            if resp.status_code != 200:
                logger.warning(f"WhaleTrack returned {resp.status_code}")
                return items
            
            data = resp.json()
            hero = data.get("hero", {})
            whale = hero.get("whale", {})
            prob = hero.get("probability", {})
            position = data.get("position", {})
            
            symbol = hero.get("symbol", "BTC/USDT")
            price = hero.get("price", 0)
            direction = hero.get("direction", "neutral")
            confidence = hero.get("confidence", 0)
            
            # Main market state item
            items.append(DataItem(
                id=f"wt_state_{int(datetime.now().timestamp())}",
                title=f"{symbol} Trading Signal: {direction.upper()} @ {confidence}% confidence",
                summary=f"Price: ${price:,.2f} | Direction: {direction} | Whale velocity: {whale.get('velocity', 0)} | Bias: {prob.get('directional_bias', 'neutral')} ({prob.get('bias_strength', 0):.1f}%)",
                source="whaletrack",
                source_url="http://198.54.123.234:8600/whaleminnow/",
                category="markets",
                relevance_score=0.8 + (confidence / 500),  # Higher confidence = more relevant
                timestamp=datetime.now(timezone.utc).isoformat(),
                entities=[symbol.split("/")[0], "crypto", "trading"],
                metadata={
                    "symbol": symbol,
                    "price": price,
                    "direction": direction,
                    "confidence": confidence,
                    "whale_velocity": whale.get("velocity", 0),
                    "whale_direction": whale.get("direction", "neutral"),
                    "bias": prob.get("directional_bias", "neutral"),
                    "bias_strength": prob.get("bias_strength", 0),
                    "is_locked": prob.get("is_locked", False),
                    "signal_state": hero.get("signal_state", "IDLE"),
                    "reasoning": whale.get("reasoning", "")
                }
            ))
            
            # If in a trade, add position update
            if position and position.get("active"):
                entry_price = position.get("entry_price", 0)
                pnl = position.get("pnl", 0)
                pnl_pct = position.get("pnl_pct", 0)
                
                items.append(DataItem(
                    id=f"wt_position_{int(datetime.now().timestamp())}",
                    title=f"Active Trade: {position.get('direction', '?').upper()} from ${entry_price:,.2f}",
                    summary=f"Current P&L: ${pnl:,.2f} ({pnl_pct:+.2f}%) | Target: ${position.get('target', 0):,.2f} | Stop: ${position.get('stop', 0):,.2f}",
                    source="whaletrack",
                    source_url="http://198.54.123.234:8600/whaleminnow/",
                    category="markets",
                    relevance_score=0.9,  # Active trades are highly relevant
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    entities=["BTC", "position", "trade"],
                    metadata={
                        "position_type": "active_trade",
                        "direction": position.get("direction"),
                        "entry_price": entry_price,
                        "current_price": price,
                        "pnl": pnl,
                        "pnl_pct": pnl_pct,
                        "target": position.get("target"),
                        "stop": position.get("stop")
                    }
                ))
            
            # Add whale alert if high confidence directional move
            if confidence > 80:
                items.append(DataItem(
                    id=f"wt_alert_{int(datetime.now().timestamp())}",
                    title=f"🐋 High Confidence Whale Signal: {direction.upper()}",
                    summary=f"{whale.get('reasoning', 'Strong directional bias detected')}",
                    source="whaletrack",
                    source_url="http://198.54.123.234:8600/whaleminnow/",
                    category="markets",
                    relevance_score=0.95,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    entities=["BTC", "whale", "alert"],
                    metadata={
                        "alert_type": "high_confidence_signal",
                        "direction": direction,
                        "confidence": confidence,
                        "reasoning": whale.get("reasoning", "")
                    }
                ))
            
            logger.info(f"🐋 Collected {len(items)} items from WhaleTrack")
            
    except Exception as e:
        logger.error(f"WhaleTrack collection failed: {e}")
    
    return items


async def get_whaletrack_summary() -> Dict[str, Any]:
    """Get a quick summary for other services"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{WHALETRACK_URL}/api/state")
            if resp.status_code == 200:
                data = resp.json()
                hero = data.get("hero", {})
                return {
                    "symbol": hero.get("symbol"),
                    "price": hero.get("price"),
                    "direction": hero.get("direction"),
                    "confidence": hero.get("confidence"),
                    "signal_state": hero.get("signal_state"),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
    except:
        pass
    return {}












#!/usr/bin/env python3
"""
INTELLIGENT DATA DAEMON
=======================
Autonomous collection, processing, predicting, and distribution.

Runs continuously:
- SENSE: Collect from all sources
- PROCESS: Enrich and detect patterns
- PREDICT: Generate falsifiable predictions (Prophet)
- VERIFY: Check past predictions (Oracle)
- REMEMBER: Store to Mem0
- SHARE: Push to consumers

"I sense everything. I connect dots. I predict the future. I learn from my mistakes."
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
import json

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.collectors.whaletrack import collect_whaletrack
from app.collectors.hackernews import collect_hackernews
from app.collectors.arxiv import collect_arxiv
from app.collectors.reddit import collect_reddit
from app.collectors.github import collect_github
from app.prophet import prophet
from app.oracle import oracle
from app.event_bridge import EventBridge

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DataDaemon")

# Mem0 configuration
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "")
MEM0_URL = "https://api.mem0.ai/v1"


class IntelligentDataDaemon:
    """
    The sensory cortex of Full Potential AI.
    Collects, processes, remembers, and distributes.
    """
    
    def __init__(self):
        self.cycle_count = 0
        self.items_collected = 0
        self.patterns_detected = 0
        self.memories_stored = 0
        self.predictions_made = 0
        self.verifications_run = 0
        
        # Event bridge for real-time event-driven collection
        self.event_bridge = EventBridge(daemon=self)
        
        # Collectors registry for event-driven collection
        self.collectors = {
            "whaletrack": collect_whaletrack,
            "hackernews": lambda: collect_hackernews(30),
            "arxiv": collect_arxiv,
            "reddit": collect_reddit,
            "github": collect_github,
        }
        
        # Collection intervals (in seconds) - fallback for polling
        self.intervals = {
            "whaletrack": 300,      # 5 minutes - real-time trading
            "hackernews": 1800,     # 30 minutes
            "arxiv": 21600,         # 6 hours
            "reddit": 1800,         # 30 minutes
            "github": 3600,         # 1 hour
        }
        
        # Last collection times
        self.last_collected = {source: None for source in self.intervals}
        
        # Data store
        self.items: Dict[str, Any] = {}
        self.patterns: List[Dict] = []
        
        logger.info("=" * 60)
        logger.info("🧠 INTELLIGENT DATA DAEMON STARTING")
        logger.info("=" * 60)
    
    def should_collect(self, source: str) -> bool:
        """Check if it's time to collect from this source"""
        last = self.last_collected.get(source)
        if last is None:
            return True
        
        interval = self.intervals.get(source, 1800)
        elapsed = (datetime.now(timezone.utc) - last).total_seconds()
        return elapsed >= interval
    
    async def sense_source(self, source: str) -> int:
        """
        Collect from a single source (event-triggered).
        Called by event_bridge when real-time events arrive.
        """
        if source not in self.collectors:
            logger.warning(f"Unknown source: {source}")
            return 0
            
        try:
            collector = self.collectors[source]
            items = await collector()
            collected = 0
            
            for item in items:
                self.items[item.id] = item.dict()
                collected += 1
                
                # Emit event for each collected item
                await self.event_bridge.emit_data_collected(item.dict())
            
            self.last_collected[source] = datetime.now(timezone.utc)
            self.items_collected += collected
            
            logger.info(f"📡 Event-triggered collection from {source}: {collected} items")
            return collected
            
        except Exception as e:
            logger.error(f"Event-triggered collection from {source} failed: {e}")
            return 0
    
    async def sense(self) -> int:
        """SENSE: Collect from all sources"""
        logger.info("👁️ SENSING...")
        
        collected = 0
        
        # Collect from sources that are due
        if self.should_collect("whaletrack"):
            items = await collect_whaletrack()
            for item in items:
                self.items[item.id] = item.dict()
            collected += len(items)
            self.last_collected["whaletrack"] = datetime.now(timezone.utc)
        
        if self.should_collect("hackernews"):
            items = await collect_hackernews(30)
            for item in items:
                self.items[item.id] = item.dict()
            collected += len(items)
            self.last_collected["hackernews"] = datetime.now(timezone.utc)
        
        if self.should_collect("arxiv"):
            items = await collect_arxiv()
            for item in items:
                self.items[item.id] = item.dict()
            collected += len(items)
            self.last_collected["arxiv"] = datetime.now(timezone.utc)
        
        if self.should_collect("reddit"):
            items = await collect_reddit()
            for item in items:
                self.items[item.id] = item.dict()
            collected += len(items)
            self.last_collected["reddit"] = datetime.now(timezone.utc)
        
        if self.should_collect("github"):
            items = await collect_github()
            for item in items:
                self.items[item.id] = item.dict()
            collected += len(items)
            self.last_collected["github"] = datetime.now(timezone.utc)
        
        self.items_collected += collected
        logger.info(f"   Collected {collected} items (total: {len(self.items)})")
        
        return collected
    
    async def process(self) -> int:
        """PROCESS: Detect patterns and enrich data"""
        logger.info("⚙️ PROCESSING...")
        
        patterns_found = 0
        patterns_before = len(self.patterns)
        
        # Get recent items (last hour)
        recent = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        for item in self.items.values():
            try:
                ts = datetime.fromisoformat(item.get("timestamp", "").replace("Z", "+00:00"))
                if ts > cutoff:
                    recent.append(item)
            except:
                pass
        
        # Detect patterns
        patterns_found += self.detect_category_spikes(recent)
        patterns_found += self.detect_keyword_trends(recent)
        patterns_found += self.detect_cross_source_patterns(recent)
        
        # Emit events for new patterns
        for pattern in self.patterns[patterns_before:]:
            await self.event_bridge.emit_pattern_detected(pattern)
        
        self.patterns_detected += patterns_found
        logger.info(f"   Detected {patterns_found} patterns")
        
        return patterns_found
    
    def detect_category_spikes(self, items: List[Dict]) -> int:
        """Detect if a category is spiking"""
        patterns = 0
        
        categories = {}
        for item in items:
            cat = item.get("category", "general")
            categories[cat] = categories.get(cat, 0) + 1
        
        # If any category has >30% of items, it's a spike
        total = len(items)
        if total > 10:
            for cat, count in categories.items():
                if count / total > 0.3:
                    self.patterns.append({
                        "type": "category_spike",
                        "category": cat,
                        "count": count,
                        "percentage": count / total,
                        "significance": 0.7,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "description": f"{cat.title()} content concentrated at {count/total:.0%}"
                    })
                    patterns += 1
                    logger.info(f"   📈 Category spike: {cat} ({count}/{total} = {count/total:.0%})")
        
        return patterns
    
    def detect_keyword_trends(self, items: List[Dict]) -> int:
        """Detect trending keywords"""
        patterns = 0
        
        keywords = {}
        for item in items:
            title = item.get("title", "").lower()
            for word in title.split():
                if len(word) > 4:  # Skip short words
                    keywords[word] = keywords.get(word, 0) + 1
        
        # Keywords appearing >5 times are trending
        for word, count in keywords.items():
            if count >= 5:
                self.patterns.append({
                    "type": "keyword_trend",
                    "keyword": word,
                    "count": count,
                    "significance": 0.6,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "description": f"Keyword '{word}' trending with {count} mentions"
                })
                patterns += 1
        
        return patterns
    
    def detect_cross_source_patterns(self, items: List[Dict]) -> int:
        """Detect patterns appearing across multiple sources"""
        patterns = 0
        
        # Group by source
        by_source = {}
        for item in items:
            source = item.get("source", "unknown")
            by_source.setdefault(source, []).append(item)
        
        # Look for common topics across sources
        if len(by_source) >= 2:
            # Check for BTC/crypto mentions across sources
            btc_sources = set()
            for source, source_items in by_source.items():
                for item in source_items:
                    title = item.get("title", "").lower()
                    if "btc" in title or "bitcoin" in title or "crypto" in title:
                        btc_sources.add(source)
                        break
            
            if len(btc_sources) >= 2:
                self.patterns.append({
                    "type": "cross_source",
                    "topic": "crypto",
                    "sources": list(btc_sources),
                    "significance": 0.8,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "description": f"Crypto topic appearing across {list(btc_sources)}"
                })
                patterns += 1
                logger.info(f"   🔗 Cross-source pattern: crypto in {btc_sources}")
        
        return patterns
    
    async def predict(self) -> int:
        """PREDICT: Generate predictions from patterns"""
        logger.info("🔮 PREDICTING...")
        
        predictions = 0
        
        # Process recent patterns
        recent_patterns = self.patterns[-5:] if self.patterns else []
        
        for pattern in recent_patterns:
            # Don't predict on same pattern twice
            if pattern.get("predicted"):
                continue
                
            prediction = await prophet.predict(pattern)
            
            if prediction:
                predictions += 1
                pattern["predicted"] = True
                self.predictions_made += 1
        
        if predictions > 0:
            logger.info(f"   Generated {predictions} new predictions")
        else:
            logger.info("   No new predictions generated")
            
        return predictions
        
    async def verify(self) -> int:
        """VERIFY: Check past predictions"""
        logger.info("⚖️ VERIFYING...")
        
        results = await oracle.verify_all()
        
        if results:
            logger.info(f"   Verified {len(results)} predictions")
            self.verifications_run += len(results)
        else:
            logger.info("   No predictions ready for verification")
            
        return len(results)
    
    async def remember(self) -> int:
        """REMEMBER: Store important items to Mem0"""
        if not MEM0_API_KEY:
            return 0
        
        logger.info("💾 REMEMBERING...")
        
        stored = 0
        
        try:
            import httpx
            
            # Store high-relevance items
            high_relevance = [
                item for item in self.items.values()
                if item.get("relevance_score", 0) >= 0.8
            ]
            
            if high_relevance:
                # Summarize for storage
                summary = f"Data collection cycle {self.cycle_count}: "
                summary += f"Found {len(high_relevance)} high-relevance items. "
                
                categories = {}
                for item in high_relevance:
                    cat = item.get("category", "general")
                    categories[cat] = categories.get(cat, 0) + 1
                
                summary += f"Categories: {categories}. "
                summary += f"Top item: {high_relevance[0].get('title', 'Unknown')[:100]}"
                
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    resp = await client.post(
                        f"{MEM0_URL}/memories/",
                        headers={
                            "Authorization": f"Token {MEM0_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "messages": [{"role": "user", "content": summary}],
                            "user_id": "fpai_data_daemon",
                            "metadata": {"type": "data_collection", "cycle": self.cycle_count}
                        }
                    )
                    
                    if resp.status_code in [200, 201, 202]:
                        stored = len(high_relevance)
                        logger.info(f"   Stored summary of {stored} high-relevance items")
            
            # Store significant patterns
            for pattern in self.patterns[-5:]:  # Last 5 patterns
                if pattern.get("stored"):
                    continue
                    
                pattern_text = f"Pattern detected: {pattern.get('type')} - {pattern.get('description')}"
                
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    await client.post(
                        f"{MEM0_URL}/memories/",
                        headers={
                            "Authorization": f"Token {MEM0_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "messages": [{"role": "user", "content": pattern_text}],
                            "user_id": "fpai_data_daemon",
                            "metadata": {"type": "pattern", "pattern_type": pattern.get("type")}
                        }
                    )
                    stored += 1
                    pattern["stored"] = True
            
            self.memories_stored += stored
            
        except Exception as e:
            logger.error(f"Memory storage failed: {e}")
        
        return stored
    
    async def share(self) -> int:
        """SHARE: Push to consumers"""
        logger.info("📤 SHARING...")
        
        shared = 0
        
        try:
            import httpx
            
            # Get high-priority items for intelligence
            high_priority = [
                item for item in self.items.values()
                if item.get("relevance_score", 0) >= 0.7
            ][:10]
            
            if high_priority:
                # Push to Strategic Intelligence
                async with httpx.AsyncClient(timeout=5.0) as client:
                    try:
                        resp = await client.post(
                            "http://localhost:8500/api/v1/signals",
                            json={
                                "source": "data_daemon",
                                "signals": [
                                    {
                                        "title": item.get("title"),
                                        "category": item.get("category"),
                                        "relevance": item.get("relevance_score"),
                                        "source": item.get("source")
                                    }
                                    for item in high_priority
                                ]
                            }
                        )
                        if resp.status_code == 200:
                            shared += len(high_priority)
                    except:
                        pass
                
                # Push to Nerve Center
                async with httpx.AsyncClient(timeout=5.0) as client:
                    try:
                        await client.post(
                            "http://localhost:8120/api/event",
                            json={
                                "type": "data.collection.complete",
                                "source": "data_daemon",
                                "data": {
                                    "cycle": self.cycle_count,
                                    "items_collected": len(self.items),
                                    "patterns_detected": len(self.patterns),
                                    "high_priority_count": len(high_priority)
                                }
                            }
                        )
                    except:
                        pass
            
            logger.info(f"   Shared {shared} items to consumers")
            
        except Exception as e:
            logger.error(f"Share failed: {e}")
        
        return shared
    
    async def run_cycle(self):
        """Run one complete cycle: SENSE → PROCESS → PREDICT → VERIFY → REMEMBER → SHARE"""
        self.cycle_count += 1
        
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"🔄 CYCLE {self.cycle_count}")
        logger.info("=" * 60)
        
        # SENSE
        collected = await self.sense()
        
        # PROCESS
        patterns = await self.process()
        
        # PREDICT
        predictions = await self.predict()
        
        # VERIFY
        verifications = await self.verify()
        
        # REMEMBER
        stored = await self.remember()
        
        # SHARE
        shared = await self.share()
        
        # Summary
        logger.info("")
        logger.info(f"📊 CYCLE {self.cycle_count} COMPLETE")
        logger.info(f"   Collected: {collected} | Patterns: {patterns} | Predictions: {predictions} | Verified: {verifications}")
        logger.info(f"   Total items: {len(self.items)} | Active Predictions: {len([p for p in prophet.predictions.values() if p.status == 'pending'])}")
    
    async def run_forever(self):
        """Run continuously with event-driven + polling hybrid mode"""
        logger.info("🚀 Starting continuous operation...")
        logger.info(f"   Collection intervals: {self.intervals}")
        logger.info("")
        
        # Try to connect to event bus for real-time events
        event_connected = await self.event_bridge.connect()
        if event_connected:
            logger.info("📡 Event-driven mode ACTIVE - reacting to real-time events")
            # Start event listener in background
            asyncio.create_task(self._run_event_listener())
        else:
            logger.info("⏱️ Polling mode only - event bus not available")
        
        # Main polling loop (runs alongside event listener)
        while True:
            try:
                await self.run_cycle()
                
                # Wait before next cycle (1 minute between cycles)
                logger.info(f"💤 Next cycle in 60s...")
                await asyncio.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Daemon stopped by user")
                await self.event_bridge.close()
                break
            except Exception as e:
                logger.error(f"❌ Cycle error: {e}")
                await asyncio.sleep(30)
    
    async def _run_event_listener(self):
        """Background task to listen for real-time events"""
        try:
            # Also try to connect to WhaleTrack WebSocket
            await self.event_bridge.connect_whaletrack()
            
            # Start listeners (they run until connection drops)
            await asyncio.gather(
                self.event_bridge.listen(),
                self.event_bridge.listen_whaletrack(),
                return_exceptions=True
            )
        except Exception as e:
            logger.error(f"Event listener error: {e}")
            # Attempt reconnection after delay
            await asyncio.sleep(30)
            asyncio.create_task(self._run_event_listener())


async def main():
    """Entry point"""
    daemon = IntelligentDataDaemon()
    await daemon.run_forever()


if __name__ == "__main__":
    asyncio.run(main())

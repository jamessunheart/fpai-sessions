#!/usr/bin/env python3
"""
💎 INTELLIGENCE CYCLE - Coal Into Diamonds
==========================================

Continuous WIDE → DEEP → COMPRESS → DISSEMINATE cycles.
Each cycle learns from the previous, getting faster and more valuable.

"Like coal into diamonds - pressure, time, transformation."
"""

import asyncio
import httpx
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Any
from collections import Counter
import re

# Configuration
DATA_SERVICE_URL = "http://localhost:8125"
AI_BRAIN_URL = "http://localhost:8101"
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "m0-e6AZpFLmM3gu7W2IYIJ8LL1UTGiOl9nwVZ4OWFFo")
MEM0_URL = "https://api.mem0.ai/v1"

# Cycle state
cycle_count = 0
total_diamonds = 0
cycle_times = []
insights_per_cycle = []


class IntelligenceCycle:
    """One complete WIDE → DEEP → COMPRESS → DISSEMINATE cycle"""
    
    def __init__(self, cycle_num: int):
        self.cycle_num = cycle_num
        self.start_time = time.time()
        self.wide_data = {}
        self.deep_analysis = {}
        self.diamonds = []  # Compressed insights
        self.metrics = {}
        
    async def run(self) -> Dict:
        """Execute one complete cycle"""
        print(f"\n{'='*60}")
        print(f"💎 CYCLE {self.cycle_num} - Starting at {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        
        # WIDE - Collect broadly
        await self.go_wide()
        
        # DEEP - Analyze deeply
        await self.go_deep()
        
        # COMPRESS - Create diamonds
        await self.compress()
        
        # DISSEMINATE - Share the diamonds
        await self.disseminate()
        
        # Calculate metrics
        self.metrics = {
            "cycle": self.cycle_num,
            "duration_sec": round(time.time() - self.start_time, 2),
            "wide_items": len(self.wide_data.get("feed", [])),
            "deep_analyses": len(self.deep_analysis),
            "diamonds_created": len(self.diamonds),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        print(f"\n✨ Cycle {self.cycle_num} complete: {len(self.diamonds)} diamonds in {self.metrics['duration_sec']}s")
        
        return self.metrics
    
    async def go_wide(self):
        """WIDE - Cast a broad net"""
        print("\n🌊 WIDE - Scanning broadly...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get current feed
            try:
                resp = await client.get(f"{DATA_SERVICE_URL}/api/data/feed?limit=50")
                if resp.status_code == 200:
                    self.wide_data["feed"] = resp.json().get("items", [])
                    print(f"   📰 Feed: {len(self.wide_data['feed'])} items")
            except Exception as e:
                print(f"   ⚠️ Feed error: {e}")
                self.wide_data["feed"] = []
            
            # Get market data
            try:
                resp = await client.get(f"{DATA_SERVICE_URL}/api/data/markets")
                if resp.status_code == 200:
                    self.wide_data["markets"] = resp.json()
                    print(f"   📊 Markets: {list(self.wide_data['markets'].get('markets', {}).keys())}")
            except Exception as e:
                self.wide_data["markets"] = {}
            
            # Get patterns
            try:
                resp = await client.get(f"{DATA_SERVICE_URL}/api/data/patterns")
                if resp.status_code == 200:
                    self.wide_data["patterns"] = resp.json().get("patterns", [])
                    print(f"   🔍 Patterns: {len(self.wide_data['patterns'])}")
            except Exception as e:
                self.wide_data["patterns"] = []
            
            # Get memory context
            try:
                resp = await client.get(f"{DATA_SERVICE_URL}/api/data/memory/context/system%20health")
                if resp.status_code == 200:
                    self.wide_data["memory_context"] = resp.json()
                    print(f"   🧠 Memory context loaded")
            except Exception as e:
                self.wide_data["memory_context"] = {}
    
    async def go_deep(self):
        """DEEP - Analyze with intelligence"""
        print("\n🔬 DEEP - Analyzing deeply...")
        
        feed = self.wide_data.get("feed", [])
        if not feed:
            print("   ⚠️ No feed data to analyze")
            return
        
        # Category analysis
        categories = Counter(item.get("category", "unknown") for item in feed)
        self.deep_analysis["category_distribution"] = dict(categories)
        print(f"   📂 Categories: {dict(categories)}")
        
        # Relevance analysis
        high_relevance = [i for i in feed if i.get("relevance_score", 0) > 0.6]
        self.deep_analysis["high_relevance_count"] = len(high_relevance)
        self.deep_analysis["high_relevance_items"] = high_relevance[:5]
        print(f"   ⭐ High relevance: {len(high_relevance)} items")
        
        # Trend detection - find repeated words
        all_titles = " ".join(i.get("title", "") for i in feed).lower()
        words = re.findall(r'\b[a-z]{5,}\b', all_titles)
        word_freq = Counter(words)
        # Filter out common words
        stopwords = {"about", "their", "would", "could", "should", "these", "those", "which", "where", "there", "being", "after", "before"}
        trending = [(w, c) for w, c in word_freq.most_common(20) if w not in stopwords and c > 1][:5]
        self.deep_analysis["trending_topics"] = trending
        print(f"   📈 Trending: {[t[0] for t in trending]}")
        
        # Market sentiment (if available)
        markets = self.wide_data.get("markets", {}).get("markets", {})
        if markets:
            sentiments = {sym: data.get("sentiment", "unknown") for sym, data in markets.items()}
            self.deep_analysis["market_sentiments"] = sentiments
            print(f"   💹 Sentiments: {sentiments}")
        
        # Memory insights
        memory_ctx = self.wide_data.get("memory_context", {})
        if memory_ctx.get("context"):
            learnings = memory_ctx["context"].get("learnings", [])
            self.deep_analysis["relevant_learnings"] = len(learnings)
            print(f"   🧠 Relevant learnings: {len(learnings)}")
    
    async def compress(self):
        """COMPRESS - Create diamonds from coal"""
        print("\n💎 COMPRESS - Creating diamonds...")
        
        # Diamond 1: Category insight
        cat_dist = self.deep_analysis.get("category_distribution", {})
        if cat_dist:
            top_cat = max(cat_dist.items(), key=lambda x: x[1]) if cat_dist else ("none", 0)
            total = sum(cat_dist.values())
            if total > 0:
                pct = round(top_cat[1] / total * 100)
                self.diamonds.append({
                    "type": "insight",
                    "content": f"Information flow dominated by {top_cat[0]} ({pct}%). {len(cat_dist)} categories active.",
                    "value": "medium" if pct < 50 else "high"
                })
        
        # Diamond 2: Trend insight
        trending = self.deep_analysis.get("trending_topics", [])
        if trending:
            topics = ", ".join(t[0] for t in trending[:3])
            self.diamonds.append({
                "type": "pattern",
                "content": f"Emerging topics: {topics}. These words appearing repeatedly across sources.",
                "value": "high"
            })
        
        # Diamond 3: Quality insight
        high_rel = self.deep_analysis.get("high_relevance_count", 0)
        total = len(self.wide_data.get("feed", []))
        if total > 0:
            quality_pct = round(high_rel / total * 100)
            self.diamonds.append({
                "type": "insight",
                "content": f"Data quality: {quality_pct}% high relevance ({high_rel}/{total} items). {'Good signal-to-noise ratio.' if quality_pct > 30 else 'Consider tightening filters.'}",
                "value": "medium"
            })
        
        # Diamond 4: Market insight
        sentiments = self.deep_analysis.get("market_sentiments", {})
        if sentiments:
            sentiment_summary = ", ".join(f"{k}:{v}" for k, v in sentiments.items())
            self.diamonds.append({
                "type": "learning",
                "content": f"Market sentiment snapshot: {sentiment_summary}. Use for position sizing decisions.",
                "value": "high"
            })
        
        # Diamond 5: Meta-learning (how well is the cycle working)
        self.diamonds.append({
            "type": "learning",
            "content": f"Cycle {self.cycle_num} processed {total} items, found {len(trending)} trends, created {len(self.diamonds)} insights. System learning velocity: {round(len(self.diamonds)/(time.time()-self.start_time+0.01), 2)} diamonds/sec.",
            "value": "meta"
        })
        
        print(f"   💎 Created {len(self.diamonds)} diamonds")
        for d in self.diamonds:
            print(f"      [{d['value']:6}] {d['content'][:60]}...")
    
    async def disseminate(self):
        """DISSEMINATE - Share the diamonds"""
        print("\n📡 DISSEMINATE - Sharing diamonds...")
        
        stored = 0
        headers = {
            "Authorization": f"Token {MEM0_API_KEY}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            for diamond in self.diamonds:
                if diamond["value"] in ["high", "meta"]:  # Only store valuable diamonds
                    try:
                        user_id = f"fpai_{diamond['type']}s"  # fpai_insights, fpai_patterns, fpai_learnings
                        resp = await client.post(
                            f"{MEM0_URL}/memories/",
                            headers=headers,
                            json={
                                "messages": [{"role": "user", "content": diamond["content"]}],
                                "user_id": user_id,
                                "metadata": {
                                    "type": diamond["type"],
                                    "value": diamond["value"],
                                    "cycle": self.cycle_num,
                                    "source": "intelligence_cycle"
                                }
                            }
                        )
                        if resp.status_code == 200:
                            stored += 1
                    except Exception as e:
                        print(f"   ⚠️ Store error: {e}")
                    
                    await asyncio.sleep(0.2)  # Rate limit
        
        print(f"   📦 Stored {stored} high-value diamonds to Mem0")


async def run_continuous_cycles(max_cycles: int = 5, delay_between: int = 30):
    """Run continuous intelligence cycles"""
    global cycle_count, total_diamonds, cycle_times, insights_per_cycle
    
    print("=" * 60)
    print("💎 INTELLIGENCE CYCLE ENGINE")
    print("   Coal → Pressure → Time → Diamonds")
    print("=" * 60)
    
    for i in range(max_cycles):
        cycle_count = i + 1
        cycle = IntelligenceCycle(cycle_count)
        metrics = await cycle.run()
        
        # Track performance
        cycle_times.append(metrics["duration_sec"])
        insights_per_cycle.append(metrics["diamonds_created"])
        total_diamonds += metrics["diamonds_created"]
        
        # Report progress
        avg_time = sum(cycle_times) / len(cycle_times)
        avg_diamonds = sum(insights_per_cycle) / len(insights_per_cycle)
        
        print(f"\n📊 CUMULATIVE STATS:")
        print(f"   Cycles: {cycle_count}")
        print(f"   Total diamonds: {total_diamonds}")
        print(f"   Avg cycle time: {avg_time:.1f}s")
        print(f"   Avg diamonds/cycle: {avg_diamonds:.1f}")
        print(f"   Velocity: {total_diamonds / sum(cycle_times):.2f} diamonds/sec")
        
        if i < max_cycles - 1:
            print(f"\n⏳ Next cycle in {delay_between}s...")
            await asyncio.sleep(delay_between)
    
    # Final summary
    print("\n" + "=" * 60)
    print("💎 INTELLIGENCE CYCLE COMPLETE")
    print("=" * 60)
    print(f"   Total cycles: {cycle_count}")
    print(f"   Total diamonds: {total_diamonds}")
    print(f"   Total time: {sum(cycle_times):.1f}s")
    print(f"   Final velocity: {total_diamonds / sum(cycle_times):.2f} diamonds/sec")
    print(f"   Diamonds stored in Mem0 for future retrieval")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    max_cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    delay = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    
    print(f"Running {max_cycles} cycles with {delay}s between each...")
    asyncio.run(run_continuous_cycles(max_cycles, delay))
















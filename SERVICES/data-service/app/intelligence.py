"""
Data Intelligence Module
========================
Automatic enrichment, pattern detection, and synthesis.

"I don't just collect. I understand."
"""

import asyncio
import logging
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
import json
import os

logger = logging.getLogger("data.intelligence")

AI_BRAIN_URL = "http://localhost:8101"
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "")
MEM0_URL = "https://api.mem0.ai/v1"


class DataEnricher:
    """
    Automatically enriches data items with AI analysis.
    """
    
    def __init__(self):
        self.cache = {}  # Cache enriched items
        self.enrichment_queue = asyncio.Queue()
        
    async def enrich(self, item: Dict) -> Dict:
        """
        Enrich a data item with AI analysis.
        
        Adds:
        - Sentiment (-1 to 1)
        - Key entities
        - Category confidence
        - Relevance boost
        - Summary (if missing)
        """
        item_id = item.get("id", "")
        
        # Check cache
        if item_id in self.cache:
            return self.cache[item_id]
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Build prompt
                prompt = f"""Analyze this data item briefly:

Title: {item.get('title', '')}
Summary: {item.get('summary', 'N/A')}
Source: {item.get('source', '')}
Category: {item.get('category', '')}

Provide JSON with:
- sentiment: number from -1 (negative) to 1 (positive)
- entities: list of key entities (companies, people, technologies)
- relevance_boost: 0 to 0.3 additional relevance if this is important
- one_line: one sentence summary

Respond only with valid JSON."""

                resp = await client.post(
                    f"{AI_BRAIN_URL}/generate",
                    json={
                        "prompt": prompt,
                        "system_message": "You are a data analyst. Output valid JSON only.",
                        "model_preference": "fast",
                        "max_tokens": 200
                    }
                )
                
                if resp.status_code == 200:
                    result = resp.json()
                    text = result.get("text", "{}")
                    
                    # Parse JSON
                    if "{" in text:
                        json_str = text[text.find("{"):text.rfind("}")+1]
                        analysis = json.loads(json_str)
                        
                        # Merge into item
                        item["enriched"] = True
                        item["sentiment"] = analysis.get("sentiment", 0)
                        item["entities"] = list(set(item.get("entities", []) + analysis.get("entities", [])))
                        item["relevance_score"] = min(1.0, item.get("relevance_score", 0.5) + analysis.get("relevance_boost", 0))
                        if analysis.get("one_line"):
                            item["summary"] = analysis["one_line"]
                        
                        # Cache
                        self.cache[item_id] = item
                        
                        logger.debug(f"Enriched {item_id}: sentiment={item['sentiment']}, entities={item['entities']}")
                        
        except Exception as e:
            logger.error(f"Enrichment failed for {item_id}: {e}")
            item["enriched"] = False
        
        return item
    
    async def enrich_batch(self, items: List[Dict], max_concurrent: int = 5) -> List[Dict]:
        """Enrich multiple items with concurrency limit"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def enrich_with_limit(item):
            async with semaphore:
                return await self.enrich(item)
        
        tasks = [enrich_with_limit(item) for item in items]
        return await asyncio.gather(*tasks)


class PatternEngine:
    """
    Detects patterns across data items.
    """
    
    def __init__(self):
        self.patterns: List[Dict] = []
        self.pattern_history: List[Dict] = []
        
    def detect_all(self, items: List[Dict]) -> List[Dict]:
        """Run all pattern detectors"""
        patterns = []
        
        patterns.extend(self.detect_category_concentration(items))
        patterns.extend(self.detect_sentiment_shift(items))
        patterns.extend(self.detect_entity_surge(items))
        patterns.extend(self.detect_cross_source_signal(items))
        
        self.patterns = patterns
        self.pattern_history.extend(patterns)
        
        return patterns
    
    def detect_category_concentration(self, items: List[Dict]) -> List[Dict]:
        """Detect when one category dominates"""
        patterns = []
        
        if len(items) < 10:
            return patterns
        
        categories = defaultdict(int)
        for item in items:
            categories[item.get("category", "general")] += 1
        
        total = len(items)
        for cat, count in categories.items():
            ratio = count / total
            if ratio >= 0.4:  # 40%+ is concentration
                patterns.append({
                    "type": "category_concentration",
                    "category": cat,
                    "count": count,
                    "ratio": ratio,
                    "significance": ratio,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "description": f"{cat.title()} content concentrated at {ratio:.0%}"
                })
        
        return patterns
    
    def detect_sentiment_shift(self, items: List[Dict]) -> List[Dict]:
        """Detect overall sentiment shift"""
        patterns = []
        
        sentiments = [item.get("sentiment", 0) for item in items if "sentiment" in item]
        
        if len(sentiments) < 5:
            return patterns
        
        avg_sentiment = sum(sentiments) / len(sentiments)
        
        if abs(avg_sentiment) >= 0.3:
            direction = "positive" if avg_sentiment > 0 else "negative"
            patterns.append({
                "type": "sentiment_shift",
                "direction": direction,
                "value": avg_sentiment,
                "sample_size": len(sentiments),
                "significance": abs(avg_sentiment),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "description": f"Overall sentiment shifted {direction} ({avg_sentiment:+.2f})"
            })
        
        return patterns
    
    def detect_entity_surge(self, items: List[Dict]) -> List[Dict]:
        """Detect when an entity is mentioned frequently"""
        patterns = []
        
        entities = defaultdict(int)
        for item in items:
            for entity in item.get("entities", []):
                entities[entity.lower()] += 1
        
        # Entities mentioned 5+ times
        for entity, count in entities.items():
            if count >= 5:
                patterns.append({
                    "type": "entity_surge",
                    "entity": entity,
                    "count": count,
                    "significance": min(1.0, count / 10),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "description": f"'{entity}' mentioned {count} times"
                })
        
        return patterns
    
    def detect_cross_source_signal(self, items: List[Dict]) -> List[Dict]:
        """Detect signals appearing across multiple sources"""
        patterns = []
        
        # Group by source
        by_source = defaultdict(list)
        for item in items:
            by_source[item.get("source", "unknown")].append(item)
        
        if len(by_source) < 2:
            return patterns
        
        # Look for common entities across sources
        source_entities = {}
        for source, source_items in by_source.items():
            entities = set()
            for item in source_items:
                entities.update([e.lower() for e in item.get("entities", [])])
            source_entities[source] = entities
        
        # Find entities in multiple sources
        all_entities = set()
        for entities in source_entities.values():
            all_entities.update(entities)
        
        for entity in all_entities:
            sources_with = [s for s, e in source_entities.items() if entity in e]
            if len(sources_with) >= 2:
                patterns.append({
                    "type": "cross_source_signal",
                    "entity": entity,
                    "sources": sources_with,
                    "significance": len(sources_with) / len(by_source),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "description": f"'{entity}' appearing in {len(sources_with)} sources: {sources_with}"
                })
        
        return patterns


class DailySynthesizer:
    """
    Synthesizes daily insights and stores to Mem0.
    """
    
    def __init__(self):
        self.last_synthesis = None
        
    async def synthesize(self, items: List[Dict], patterns: List[Dict]) -> Dict:
        """Create daily synthesis"""
        
        synthesis = {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "items_analyzed": len(items),
            "patterns_detected": len(patterns),
            "categories": defaultdict(int),
            "top_entities": defaultdict(int),
            "sentiment_avg": 0,
            "key_insights": [],
            "recommendations": []
        }
        
        # Aggregate stats
        sentiments = []
        for item in items:
            synthesis["categories"][item.get("category", "general")] += 1
            for entity in item.get("entities", []):
                synthesis["top_entities"][entity] += 1
            if "sentiment" in item:
                sentiments.append(item["sentiment"])
        
        if sentiments:
            synthesis["sentiment_avg"] = sum(sentiments) / len(sentiments)
        
        # Convert defaultdicts
        synthesis["categories"] = dict(synthesis["categories"])
        synthesis["top_entities"] = dict(sorted(
            synthesis["top_entities"].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10])
        
        # Generate insights from patterns
        for pattern in patterns:
            if pattern.get("significance", 0) >= 0.5:
                synthesis["key_insights"].append(pattern.get("description", str(pattern)))
        
        # Store to Mem0
        if MEM0_API_KEY:
            await self.store_to_mem0(synthesis)
        
        self.last_synthesis = synthesis
        return synthesis
    
    async def store_to_mem0(self, synthesis: Dict):
        """Store synthesis to Mem0"""
        try:
            summary = f"Daily Data Synthesis ({synthesis['date']}): "
            summary += f"Analyzed {synthesis['items_analyzed']} items. "
            summary += f"Top categories: {list(synthesis['categories'].keys())[:3]}. "
            summary += f"Top entities: {list(synthesis['top_entities'].keys())[:5]}. "
            summary += f"Sentiment: {synthesis['sentiment_avg']:+.2f}. "
            if synthesis['key_insights']:
                summary += f"Key insight: {synthesis['key_insights'][0]}"
            
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.post(
                    f"{MEM0_URL}/memories/",
                    headers={
                        "Authorization": f"Token {MEM0_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "messages": [{"role": "user", "content": summary}],
                        "user_id": "fpai_data_intelligence",
                        "metadata": {"type": "daily_synthesis", "date": synthesis["date"]}
                    }
                )
                
                if resp.status_code in [200, 201, 202]:
                    logger.info(f"Stored daily synthesis to Mem0")
                    
        except Exception as e:
            logger.error(f"Failed to store synthesis to Mem0: {e}")


# Singleton instances
enricher = DataEnricher()
pattern_engine = PatternEngine()
synthesizer = DailySynthesizer()


async def process_items(items: List[Dict]) -> Dict:
    """
    Full processing pipeline:
    1. Enrich items with AI
    2. Detect patterns
    3. Generate synthesis (if daily)
    """
    
    result = {
        "items_processed": 0,
        "patterns_detected": 0,
        "synthesis": None
    }
    
    # Enrich high-relevance items
    high_relevance = [i for i in items if i.get("relevance_score", 0) >= 0.6]
    if high_relevance:
        enriched = await enricher.enrich_batch(high_relevance[:20])
        result["items_processed"] = len(enriched)
    
    # Detect patterns
    patterns = pattern_engine.detect_all(items)
    result["patterns_detected"] = len(patterns)
    result["patterns"] = patterns
    
    # Daily synthesis (if enough time passed)
    if synthesizer.last_synthesis is None or \
       (datetime.now(timezone.utc) - datetime.fromisoformat(synthesizer.last_synthesis["timestamp"].replace("Z", "+00:00"))).total_seconds() > 86400:
        synthesis = await synthesizer.synthesize(items, patterns)
        result["synthesis"] = synthesis
    
    return result












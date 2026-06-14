"""
📊 DATA SERVICE - The System's Sensory Layer
=============================================

Architecture: WIDE → DEEP → COMPRESS → DISSEMINATE

DATA is a SERVICE, not a CONTROLLER.
- Data makes information AVAILABLE
- Intelligence DECIDES what to do with it
- Clean separation of concerns

"I don't push, I present. I don't decide, I inform."

Port: 8125
"""

import asyncio
import json
import hashlib
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

# Local memory module
from .memory import get_memory, get_tracker, Mem0Memory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("data_service")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# IMPORTANT: AI Brain is on the secondary server (see docs/coordination/SERVICE_REGISTRY.md)
AI_BRAIN_URL = os.getenv("AI_BRAIN_URL", "http://162.0.208.88:8101")

# Nerve Center is on the primary server; default to primary IP for clarity across agents.
NERVE_CENTER_URL = os.getenv("NERVE_CENTER_URL", "http://198.54.123.234:8120")

# Categories we care about
IMPORTANT_CATEGORIES = {
    "ai": ["artificial intelligence", "machine learning", "llm", "gpt", "claude", "neural", "deep learning"],
    "markets": ["crypto", "bitcoin", "ethereum", "defi", "trading", "finance", "yield"],
    "tech": ["startup", "saas", "api", "developer", "programming", "software"],
    "consciousness": ["meditation", "wellness", "mindfulness", "potential", "growth"],
    "research": ["arxiv", "paper", "study", "research", "science"]
}

# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class DataItem(BaseModel):
    """A clean, normalized data item"""
    id: str
    title: str
    summary: Optional[str] = None
    source: str
    source_url: Optional[str] = None
    category: str = "general"
    relevance_score: float = 0.5
    timestamp: str
    entities: List[str] = []
    metadata: Dict[str, Any] = {}

class AnalyzeRequest(BaseModel):
    """Request for deep analysis"""
    item_id: str
    analysis_type: str = "full"  # "summary", "sentiment", "entities", "full"
    context: Optional[str] = None  # Helps AI Brain focus

class ResearchRequest(BaseModel):
    """Request for topic research"""
    topic: str
    depth: str = "moderate"  # "surface", "moderate", "deep"
    max_items: int = 10

class SubscribeRequest(BaseModel):
    """Subscribe to data channel"""
    callback_url: str
    triggers: List[str] = ["high_relevance"]  # "all", "high_relevance", "security_alert", "category:ai"
    filters: Dict[str, Any] = {}

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STORE (In-Memory + Persistence)
# ═══════════════════════════════════════════════════════════════════════════════

class DataStore:
    """
    Clean data storage with Wide → Deep → Compress layers.
    """
    
    def __init__(self):
        # WIDE: Raw collected items (30 day retention)
        self.raw_items: Dict[str, DataItem] = {}
        
        # DEEP: Enriched items (90 day retention)
        self.enriched_items: Dict[str, Dict] = {}
        
        # COMPRESS: Synthesized patterns & insights (permanent)
        self.patterns: List[Dict] = []
        self.insights: List[Dict] = []
        
        # Metadata
        self.sources: Dict[str, Dict] = {}
        self.last_fetch: Dict[str, datetime] = {}
        self.seen_urls: Set[str] = set()
        
        # Subscribers
        self.subscribers: List[Dict] = []
        self.websocket_clients: Dict[str, WebSocket] = {}
        
        logger.info("📊 DataStore initialized")
    
    def add_item(self, item: DataItem) -> bool:
        """Add item if not duplicate"""
        url_hash = hashlib.md5(item.source_url.encode()).hexdigest() if item.source_url else item.id
        
        if url_hash in self.seen_urls:
            return False  # Duplicate
        
        self.seen_urls.add(url_hash)
        self.raw_items[item.id] = item
        
        # Update source stats
        if item.source not in self.sources:
            self.sources[item.source] = {"count": 0, "last_item": None}
        self.sources[item.source]["count"] += 1
        self.sources[item.source]["last_item"] = item.timestamp
        
        return True
    
    def get_feed(
        self,
        categories: Optional[List[str]] = None,
        min_relevance: float = 0.0,
        since: Optional[datetime] = None,
        limit: int = 50
    ) -> List[DataItem]:
        """Get clean feed with filters"""
        items = list(self.raw_items.values())
        
        # Filter by category
        if categories:
            items = [i for i in items if i.category in categories]
        
        # Filter by relevance
        if min_relevance > 0:
            items = [i for i in items if i.relevance_score >= min_relevance]
        
        # Filter by time
        if since:
            items = [i for i in items if datetime.fromisoformat(i.timestamp.replace('Z', '+00:00')) >= since]
        
        # Sort by relevance (highest first)
        items = sorted(items, key=lambda x: x.relevance_score, reverse=True)
        
        return items[:limit]
    
    def get_enriched(self, item_id: str) -> Optional[Dict]:
        """Get enriched version of item"""
        return self.enriched_items.get(item_id)
    
    def add_enriched(self, item_id: str, enriched_data: Dict):
        """Store enriched item"""
        self.enriched_items[item_id] = enriched_data
    
    def add_pattern(self, pattern: Dict):
        """Store discovered pattern"""
        self.patterns.append({
            **pattern,
            "discovered_at": datetime.now(timezone.utc).isoformat()
        })
    
    def add_insight(self, insight: Dict):
        """Store synthesized insight"""
        self.insights.append({
            **insight,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    def cleanup_old(self, days: int = 30):
        """Remove items older than N days"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        old_count = len(self.raw_items)
        
        self.raw_items = {
            k: v for k, v in self.raw_items.items()
            if datetime.fromisoformat(v.timestamp.replace('Z', '+00:00')) >= cutoff
        }
        
        removed = old_count - len(self.raw_items)
        if removed > 0:
            logger.info(f"🧹 Cleaned up {removed} old items")
        
        return removed


# Global store
store = DataStore()

# ═══════════════════════════════════════════════════════════════════════════════
# WIDE - COLLECTION LAYER
# ═══════════════════════════════════════════════════════════════════════════════

# WhaleTrack URLs for CoinGlass data (try in order).
# NOTE: WhaleTrack Live is the canonical trading system (8601). Magnet/signals may be on 8602.
WHALETRACK_URLS = [
    u.strip()
    for u in os.getenv(
        "WHALETRACK_URLS",
        "http://198.54.123.234:8601,http://198.54.123.234:8602,http://localhost:8601,http://localhost:8602",
    ).split(",")
    if u.strip()
]

# CoinGlass direct API (fallback)
COINGLASS_API_URL = "https://open-api.coinglass.com/public/v2"
COINGLASS_API_KEY = None  # Set from environment

async def collect_coinglass() -> List[DataItem]:
    """
    Collect market data from CoinGlass via WhaleTrack or direct API.
    
    Data includes:
    - Funding rates
    - Open interest
    - Long/Short ratios
    - Liquidation data
    """
    items = []
    symbols = ["BTC", "ETH", "SOL"]
    
    whaletrack_err: Optional[str] = None
    for base_url in WHALETRACK_URLS:
        try:
            # Try WhaleTrack first (it has cached CoinGlass data)
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{base_url}/api/market-overview")

            if resp.status_code != 200:
                continue

            data = resp.json()

            # Extract CoinGlass data from market overview
            for symbol_data in data.get("symbols", []):
                    symbol = symbol_data.get("symbol", "UNKNOWN")
                    cg_data = symbol_data.get("coinglass", {})
                    
                    if not cg_data:
                        continue
                    
                    # Determine sentiment
                    funding = cg_data.get("funding_rate", 0)
                    sentiment = "neutral"
                    if funding > 0.01:
                        sentiment = "bullish_crowded"  # Longs paying shorts
                    elif funding < -0.01:
                        sentiment = "bearish_crowded"  # Shorts paying longs
                    
                    # Calculate relevance based on OI change
                    oi_change = abs(cg_data.get("oi_change_4h", 0))
                    relevance = min(1.0, 0.6 + (oi_change / 10))  # Higher OI change = more relevant
                    
                    items.append(DataItem(
                        id=f"cg_{symbol}_{int(datetime.now().timestamp())}",
                        title=f"{symbol} Market Sentiment Update",
                        summary=f"Funding: {funding*100:.4f}% | OI: ${cg_data.get('open_interest', 0)/1e9:.2f}B | L/S: {cg_data.get('long_ratio', 50):.0f}/{cg_data.get('short_ratio', 50):.0f} | OI Δ4h: {cg_data.get('oi_change_4h', 0):.2f}%",
                        source="coinglass",
                        source_url=f"https://www.coinglass.com/tv/{symbol}USDT",
                        category="markets",
                        relevance_score=relevance,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        entities=[symbol, "crypto", "derivatives"],
                        metadata={
                            "symbol": symbol,
                            "funding_rate": cg_data.get("funding_rate", 0),
                            "open_interest": cg_data.get("open_interest", 0),
                            "oi_change_1h": cg_data.get("oi_change_1h", 0),
                            "oi_change_4h": cg_data.get("oi_change_4h", 0),
                            "oi_change_24h": cg_data.get("oi_change_24h", 0),
                            "long_ratio": cg_data.get("long_ratio", 50),
                            "short_ratio": cg_data.get("short_ratio", 50),
                            "long_liq_4h": cg_data.get("long_liq_4h", 0),
                            "short_liq_4h": cg_data.get("short_liq_4h", 0),
                            "hours_to_funding": cg_data.get("hours_to_funding", 8),
                            "sentiment": sentiment,
                            "data_source": "whaletrack"
                        }
                    ))
                    
                    # Also create liquidation alert if significant
                    long_liq = cg_data.get("long_liq_4h", 0)
                    short_liq = cg_data.get("short_liq_4h", 0)
                    total_liq = long_liq + short_liq
                    
                    if total_liq > 10_000_000:  # More than $10M liquidated
                        liq_bias = "longs" if long_liq > short_liq else "shorts"
                        items.append(DataItem(
                            id=f"cg_liq_{symbol}_{int(datetime.now().timestamp())}",
                            title=f"🔥 {symbol} Liquidation Alert: ${total_liq/1e6:.1f}M in 4h",
                            summary=f"Major liquidations detected. {liq_bias.title()} getting rekt. Long: ${long_liq/1e6:.1f}M | Short: ${short_liq/1e6:.1f}M",
                            source="coinglass",
                            source_url=f"https://www.coinglass.com/LiquidationData",
                            category="markets",
                            relevance_score=0.9,  # High relevance for liquidation events
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            entities=[symbol, "liquidation", liq_bias],
                            metadata={
                                "symbol": symbol,
                                "total_liquidated": total_liq,
                                "long_liquidated": long_liq,
                                "short_liquidated": short_liq,
                                "bias": liq_bias,
                                "alert_type": "liquidation"
                            }
                        ))
                
            logger.info(f"📊 Collected {len(items)} items from CoinGlass via WhaleTrack ({base_url})")
            return items

        except Exception as e:
            whaletrack_err = str(e)
            continue

    if whaletrack_err:
        logger.warning(f"WhaleTrack not available, trying direct CoinGlass: {whaletrack_err}")
    
    # Fallback: Direct CoinGlass API
    try:
        await collect_coinglass_direct(items, symbols)
    except Exception as e:
        logger.error(f"CoinGlass direct fetch failed: {e}")
    
    logger.info(f"📊 Collected {len(items)} items from CoinGlass")
    return items


async def collect_coinglass_direct(items: List[DataItem], symbols: List[str]):
    """Fallback: Direct CoinGlass API calls"""
    import os
    api_key = os.getenv("COIN_GLASS_API_KEY")
    
    if not api_key:
        logger.warning("No COIN_GLASS_API_KEY set, skipping direct CoinGlass fetch")
        return
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        headers = {"coinglassSecret": api_key.strip().strip("'").strip('"')}
        
        # Fetch funding rates
        try:
            resp = await client.get(f"{COINGLASS_API_URL}/funding", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and data.get("data"):
                    for coin in data["data"]:
                        symbol = coin.get("symbol", "").upper()
                        if symbol in symbols:
                            rates = []
                            for ex in coin.get("uMarginList", []):
                                rate = ex.get("rate", 0)
                                if rate:
                                    rates.append(rate)
                            
                            if rates:
                                avg_rate = sum(rates) / len(rates)
                                items.append(DataItem(
                                    id=f"cg_funding_{symbol}_{int(datetime.now().timestamp())}",
                                    title=f"{symbol} Funding Rate: {avg_rate*100:.4f}%",
                                    summary=f"Average funding rate across {len(rates)} exchanges",
                                    source="coinglass",
                                    source_url=f"https://www.coinglass.com/FundingRate",
                                    category="markets",
                                    relevance_score=0.7,
                                    timestamp=datetime.now(timezone.utc).isoformat(),
                                    entities=[symbol, "funding"],
                                    metadata={
                                        "symbol": symbol,
                                        "funding_rate": avg_rate,
                                        "exchanges_count": len(rates),
                                        "data_source": "coinglass_direct"
                                    }
                                ))
        except Exception as e:
            logger.error(f"CoinGlass funding fetch failed: {e}")


async def collect_hacker_news(limit: int = 30) -> List[DataItem]:
    """Collect from Hacker News (tech, startups, AI)"""
    items = []
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get top stories
            resp = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
            story_ids = resp.json()[:limit]
            
            # Fetch each story
            for story_id in story_ids:
                try:
                    resp = await client.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
                    story = resp.json()
                    
                    if not story or story.get("type") != "story":
                        continue
                    
                    title = story.get("title", "")
                    url = story.get("url", f"https://news.ycombinator.com/item?id={story_id}")
                    score = story.get("score", 0)
                    
                    # Categorize based on keywords
                    category = categorize_text(title)
                    
                    # Relevance based on score and category match
                    relevance = min(1.0, (score / 500) + (0.3 if category != "general" else 0))
                    
                    items.append(DataItem(
                        id=f"hn_{story_id}",
                        title=title,
                        source="hacker_news",
                        source_url=url,
                        category=category,
                        relevance_score=relevance,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        metadata={"score": score, "comments": story.get("descendants", 0)}
                    ))
                except Exception as e:
                    continue
                    
    except Exception as e:
        logger.error(f"HN fetch error: {e}")
    
    logger.info(f"📰 Collected {len(items)} items from Hacker News")
    return items


async def collect_arxiv(categories: List[str] = ["cs.AI", "cs.LG", "cs.CL"], limit: int = 20) -> List[DataItem]:
    """Collect from arXiv (research papers)"""
    items = []
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            query = "+OR+".join([f"cat:{cat}" for cat in categories])
            url = f"http://export.arxiv.org/api/query?search_query={query}&start=0&max_results={limit}&sortBy=submittedDate&sortOrder=descending"
            
            resp = await client.get(url)
            
            # Parse XML (simple extraction)
            import re
            entries = re.findall(r'<entry>(.*?)</entry>', resp.text, re.DOTALL)
            
            for entry in entries:
                try:
                    title_match = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                    summary_match = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
                    id_match = re.search(r'<id>(.*?)</id>', entry)
                    
                    if not title_match:
                        continue
                    
                    title = title_match.group(1).strip().replace('\n', ' ')
                    summary = summary_match.group(1).strip()[:500] if summary_match else ""
                    arxiv_id = id_match.group(1).split('/')[-1] if id_match else ""
                    
                    items.append(DataItem(
                        id=f"arxiv_{arxiv_id}",
                        title=title,
                        summary=summary,
                        source="arxiv",
                        source_url=f"https://arxiv.org/abs/{arxiv_id}",
                        category="research",
                        relevance_score=0.7,  # Research is always relevant
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        metadata={"categories": categories}
                    ))
                except Exception:
                    continue
                    
    except Exception as e:
        logger.error(f"arXiv fetch error: {e}")
    
    logger.info(f"📚 Collected {len(items)} items from arXiv")
    return items


def categorize_text(text: str) -> str:
    """Categorize text based on keywords"""
    text_lower = text.lower()
    
    for category, keywords in IMPORTANT_CATEGORIES.items():
        for keyword in keywords:
            if keyword in text_lower:
                return category
    
    return "general"


async def collect_all():
    """Run all collectors"""
    logger.info("🔄 Starting wide collection cycle...")
    
    # Collect from all sources in parallel
    hn_items, arxiv_items, cg_items = await asyncio.gather(
        collect_hacker_news(30),
        collect_arxiv(["cs.AI", "cs.LG", "cs.CL"], 20),
        collect_coinglass()
    )
    
    # Add to store (deduplication happens automatically)
    added = 0
    for item in hn_items + arxiv_items + cg_items:
        if store.add_item(item):
            added += 1
    
    # Update last fetch times
    store.last_fetch["hacker_news"] = datetime.now(timezone.utc)
    store.last_fetch["arxiv"] = datetime.now(timezone.utc)
    store.last_fetch["coinglass"] = datetime.now(timezone.utc)
    
    logger.info(f"✅ Collection complete: {added} new items added (HN: {len(hn_items)}, arXiv: {len(arxiv_items)}, CoinGlass: {len(cg_items)})")
    return added


# ═══════════════════════════════════════════════════════════════════════════════
# DEEP - ANALYSIS LAYER
# ═══════════════════════════════════════════════════════════════════════════════

async def analyze_item(item_id: str, analysis_type: str = "full", context: Optional[str] = None) -> Dict:
    """
    Deep analysis using AI Brain.
    Called ON-DEMAND by Intelligence, not automatically.
    """
    item = store.raw_items.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    
    # Check if already enriched
    existing = store.get_enriched(item_id)
    if existing and existing.get("analysis_type") == analysis_type:
        return existing
    
    # Build prompt for AI Brain
    prompt = f"""Analyze this information item:

TITLE: {item.title}
{f'SUMMARY: {item.summary}' if item.summary else ''}
SOURCE: {item.source}
CATEGORY: {item.category}
{f'CONTEXT: {context}' if context else ''}

Analysis type: {analysis_type}

Provide:
1. A concise summary (2-3 sentences)
2. Sentiment (-1 to 1 scale)
3. Key entities (companies, people, technologies)
4. Relevance assessment (0-1) {f'for context: {context}' if context else ''}
5. Key insights (bullet points)

Respond in JSON format:
{{"summary": "...", "sentiment": 0.5, "entities": [...], "relevance": 0.8, "insights": [...]}}
"""
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{AI_BRAIN_URL}/generate",
                json={
                    "prompt": prompt,
                    "system_message": "You are a data analyst. Output valid JSON only.",
                    "model_preference": "fast",
                    "max_tokens": 500
                }
            )
            
            if resp.status_code == 200:
                result = resp.json()
                text = result.get("text", "{}")
                
                # Parse JSON from response
                if "{" in text:
                    json_str = text[text.find("{"):text.rfind("}")+1]
                    analysis = json.loads(json_str)
                else:
                    analysis = {"error": "Could not parse AI response"}
            else:
                analysis = {"error": f"AI Brain returned {resp.status_code}"}
                
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        analysis = {"error": str(e)}
    
    # Store enriched version
    enriched = {
        "original": item.dict(),
        "analysis": analysis,
        "analysis_type": analysis_type,
        "context": context,
        "enriched_at": datetime.now(timezone.utc).isoformat()
    }
    
    store.add_enriched(item_id, enriched)
    
    return enriched


async def research_topic(topic: str, depth: str = "moderate", max_items: int = 10) -> Dict:
    """
    Research a topic across available data.
    Called ON-DEMAND by Intelligence.
    """
    # Search raw items for topic
    topic_lower = topic.lower()
    relevant_items = []
    
    for item in store.raw_items.values():
        title_match = topic_lower in item.title.lower()
        summary_match = item.summary and topic_lower in item.summary.lower()
        
        if title_match or summary_match:
            relevant_items.append(item)
    
    # Sort by relevance
    relevant_items = sorted(relevant_items, key=lambda x: x.relevance_score, reverse=True)[:max_items]
    
    # For moderate/deep depth, enrich top items
    enriched_items = []
    if depth in ["moderate", "deep"]:
        analyze_count = 3 if depth == "moderate" else max_items
        for item in relevant_items[:analyze_count]:
            enriched = await analyze_item(item.id, "full", context=f"researching: {topic}")
            enriched_items.append(enriched)
    
    # Synthesize findings
    synthesis = None
    if depth == "deep" and enriched_items:
        synthesis = await synthesize_research(topic, enriched_items)
    
    return {
        "topic": topic,
        "depth": depth,
        "items_found": len(relevant_items),
        "items": [i.dict() for i in relevant_items],
        "enriched": enriched_items if enriched_items else None,
        "synthesis": synthesis,
        "researched_at": datetime.now(timezone.utc).isoformat()
    }


async def synthesize_research(topic: str, enriched_items: List[Dict]) -> Dict:
    """Use AI Brain to synthesize research findings"""
    items_text = "\n".join([
        f"- {e['original']['title']}: {e['analysis'].get('summary', 'No summary')}"
        for e in enriched_items
    ])
    
    prompt = f"""Synthesize these research findings on "{topic}":

{items_text}

Provide:
1. Key themes (3-5 bullet points)
2. Overall sentiment/direction
3. Implications for Full Potential OS
4. Recommended actions

Respond in JSON format:
{{"themes": [...], "sentiment": "...", "implications": "...", "actions": [...]}}
"""
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{AI_BRAIN_URL}/generate",
                json={
                    "prompt": prompt,
                    "system_message": "You are a research synthesizer. Output valid JSON only.",
                    "model_preference": "smart",
                    "max_tokens": 600
                }
            )
            
            if resp.status_code == 200:
                result = resp.json()
                text = result.get("text", "{}")
                if "{" in text:
                    return json.loads(text[text.find("{"):text.rfind("}")+1])
                    
    except Exception as e:
        logger.error(f"Synthesis error: {e}")
    
    return {"error": "Synthesis failed"}


# ═══════════════════════════════════════════════════════════════════════════════
# COMPRESS - SYNTHESIS LAYER
# ═══════════════════════════════════════════════════════════════════════════════

async def detect_patterns():
    """Detect patterns across collected data"""
    items = list(store.raw_items.values())
    if len(items) < 10:
        return []
    
    # Category distribution
    category_counts = defaultdict(int)
    for item in items:
        category_counts[item.category] += 1
    
    # Keyword frequency
    from collections import Counter
    import re
    
    keywords = Counter()
    stopwords = {"the", "a", "an", "is", "are", "to", "of", "in", "for", "on", "with", "and", "or"}
    
    for item in items:
        words = re.findall(r'\b[a-z]{4,}\b', item.title.lower())
        keywords.update(w for w in words if w not in stopwords)
    
    # Build patterns
    patterns = []
    
    # Dominant category
    if category_counts:
        top_cat, top_count = max(category_counts.items(), key=lambda x: x[1])
        if top_count / len(items) > 0.3:
            patterns.append({
                "type": "category_dominance",
                "category": top_cat,
                "percentage": round(top_count / len(items) * 100),
                "significance": "high" if top_count / len(items) > 0.5 else "medium"
            })
    
    # Trending keywords
    top_keywords = keywords.most_common(5)
    if top_keywords:
        patterns.append({
            "type": "trending_topics",
            "topics": [{"word": w, "count": c} for w, c in top_keywords],
            "significance": "high"
        })
    
    # Store patterns in local store
    for pattern in patterns:
        store.add_pattern(pattern)
    
    # Persist high-significance patterns to Mem0
    memory = get_memory()
    if memory.enabled:
        for pattern in patterns:
            if pattern.get("significance") == "high":
                await memory.store_pattern(
                    pattern_type=pattern.get("type", "unknown"),
                    description=json.dumps(pattern),
                    significance=pattern.get("significance", "medium"),
                    data=pattern
                )
    
    return patterns


async def generate_daily_insights():
    """Generate daily insights from collected data"""
    items = list(store.raw_items.values())
    
    # Get top items by category
    top_by_category = {}
    for cat in IMPORTANT_CATEGORIES.keys():
        cat_items = sorted(
            [i for i in items if i.category == cat],
            key=lambda x: x.relevance_score,
            reverse=True
        )[:3]
        if cat_items:
            top_by_category[cat] = [i.dict() for i in cat_items]
    
    insight = {
        "type": "daily_digest",
        "total_items": len(items),
        "top_by_category": top_by_category,
        "patterns": store.patterns[-5:],  # Last 5 patterns
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    
    store.add_insight(insight)
    
    # Persist to Mem0 for long-term memory
    memory = get_memory()
    if memory.enabled:
        await memory.store_daily_digest(insight)
    
    return insight


async def store_high_value_insight(item: DataItem, analysis: Dict):
    """Store high-value insights in Mem0 for permanent memory"""
    memory = get_memory()
    if not memory.enabled:
        return
    
    # Only store if relevance is high or analysis shows high value
    relevance = analysis.get("relevance", item.relevance_score)
    if relevance < 0.7:
        return
    
    await memory.store_insight(
        title=item.title,
        content=analysis.get("summary", item.summary or item.title),
        category=item.category,
        relevance=relevance,
        sources=[item.source]
    )
    
    logger.info(f"💾 Persisted high-value insight to Mem0: {item.title[:50]}...")


# ═══════════════════════════════════════════════════════════════════════════════
# DISSEMINATE - DISTRIBUTION LAYER
# ═══════════════════════════════════════════════════════════════════════════════

async def notify_subscribers(item: DataItem, trigger: str):
    """Notify subscribers when triggers match"""
    for subscriber in store.subscribers:
        if trigger in subscriber.get("triggers", []) or "all" in subscriber.get("triggers", []):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(
                        subscriber["callback_url"],
                        json={
                            "trigger": trigger,
                            "item": item.dict()
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to notify subscriber: {e}")


async def broadcast_to_websockets(message: Dict):
    """Broadcast to all connected WebSocket clients"""
    disconnected = []
    for client_id, ws in store.websocket_clients.items():
        try:
            await ws.send_json(message)
        except:
            disconnected.append(client_id)
    
    for client_id in disconnected:
        del store.websocket_clients[client_id]


# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI APP
# ═══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initial collection
    await collect_all()
    
    # Start background collection loop
    asyncio.create_task(collection_loop())
    
    yield
    
    # Shutdown: Cleanup
    logger.info("📊 Data Service shutting down")


async def collection_loop():
    """Background loop for wide collection"""
    while True:
        await asyncio.sleep(30 * 60)  # 30 minutes
        await collect_all()
        await detect_patterns()


app = FastAPI(
    title="Data Service",
    description="Wide → Deep → Compress → Disseminate",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────────
# STATUS ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    memory = get_memory()
    return {
        "status": "healthy",
        "service": "data-service",
        "version": "1.1.0",
        "items_in_store": len(store.raw_items),
        "sources_active": len(store.sources),
        "patterns_detected": len(store.patterns),
        "insights_generated": len(store.insights),
        "mem0_enabled": memory.enabled,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/data/sources")
async def get_sources():
    """Get status of all data sources"""
    return {
        "sources": store.sources,
        "last_fetch": {k: v.isoformat() for k, v in store.last_fetch.items()},
        "total_items": len(store.raw_items)
    }


# ─────────────────────────────────────────────────────────────────────────────────
# WIDE - FEED ENDPOINTS (Pull when needed)
# ─────────────────────────────────────────────────────────────────────────────────

@app.get("/api/data/feed")
async def get_feed(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    categories: Optional[str] = Query(default=None, description="Comma-separated categories"),
    min_relevance: float = Query(default=0.0, ge=0.0, le=1.0),
    since: Optional[str] = Query(default=None, description="ISO timestamp"),
    limit: int = Query(default=50, ge=1, le=200)
):
    """
    Get clean data feed.
    Intelligence pulls this when it needs data.
    """
    cat_list = None
    if category:
        cat_list = [category]
    elif categories:
        cat_list = [c.strip() for c in categories.split(",")]
    
    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
        except:
            pass
    
    items = store.get_feed(
        categories=cat_list,
        min_relevance=min_relevance,
        since=since_dt,
        limit=limit
    )
    
    return {
        "items": [i.dict() for i in items],
        "count": len(items),
        "filters": {
            "categories": cat_list,
            "min_relevance": min_relevance,
            "since": since
        }
    }


@app.get("/api/data/item/{item_id}")
async def get_item(item_id: str):
    """Get a specific item"""
    item = store.raw_items.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    enriched = store.get_enriched(item_id)
    
    return {
        "item": item.dict(),
        "enriched": enriched
    }


@app.get("/api/data/markets")
async def get_market_data():
    """
    Get latest market data from CoinGlass.
    
    Returns funding rates, OI, liquidations for major tokens.
    Intelligence pulls this for trading decisions.
    """
    # Get latest CoinGlass items
    market_items = [
        item for item in store.raw_items.values()
        if item.source == "coinglass" and "alert" not in item.id
    ]
    
    # Group by symbol
    by_symbol = {}
    for item in market_items:
        symbol = item.metadata.get("symbol")
        if symbol:
            # Keep only the most recent for each symbol
            if symbol not in by_symbol or item.timestamp > by_symbol[symbol].timestamp:
                by_symbol[symbol] = item
    
    # Build response
    markets = {}
    for symbol, item in by_symbol.items():
        markets[symbol] = {
            "symbol": symbol,
            "funding_rate": item.metadata.get("funding_rate", 0),
            "open_interest": item.metadata.get("open_interest", 0),
            "oi_change_1h": item.metadata.get("oi_change_1h", 0),
            "oi_change_4h": item.metadata.get("oi_change_4h", 0),
            "oi_change_24h": item.metadata.get("oi_change_24h", 0),
            "long_ratio": item.metadata.get("long_ratio", 50),
            "short_ratio": item.metadata.get("short_ratio", 50),
            "long_liq_4h": item.metadata.get("long_liq_4h", 0),
            "short_liq_4h": item.metadata.get("short_liq_4h", 0),
            "hours_to_funding": item.metadata.get("hours_to_funding", 8),
            "sentiment": item.metadata.get("sentiment", "neutral"),
            "timestamp": item.timestamp
        }
    
    # Get liquidation alerts
    alerts = [
        {
            "symbol": item.metadata.get("symbol"),
            "title": item.title,
            "total_liquidated": item.metadata.get("total_liquidated", 0),
            "bias": item.metadata.get("bias"),
            "timestamp": item.timestamp
        }
        for item in store.raw_items.values()
        if item.source == "coinglass" and "liq" in item.id
    ]
    
    return {
        "markets": markets,
        "alerts": alerts[-5:],  # Last 5 alerts
        "last_update": store.last_fetch.get("coinglass", datetime.now(timezone.utc)).isoformat(),
        "source": "coinglass"
    }


@app.get("/api/data/markets/{symbol}")
async def get_symbol_market_data(symbol: str):
    """Get market data for a specific symbol"""
    symbol = symbol.upper()
    
    # Find the latest item for this symbol
    symbol_items = [
        item for item in store.raw_items.values()
        if item.source == "coinglass" and item.metadata.get("symbol") == symbol
    ]
    
    if not symbol_items:
        raise HTTPException(status_code=404, detail=f"No market data for {symbol}")
    
    # Get most recent
    latest = max(symbol_items, key=lambda x: x.timestamp)
    
    return {
        "symbol": symbol,
        "data": latest.metadata,
        "summary": latest.summary,
        "timestamp": latest.timestamp
    }


# ─────────────────────────────────────────────────────────────────────────────────
# DEEP - ANALYSIS ENDPOINTS (On-demand)
# ─────────────────────────────────────────────────────────────────────────────────

@app.post("/api/data/analyze")
async def analyze(request: AnalyzeRequest):
    """
    Request deep analysis of an item.
    Intelligence calls this when it needs deeper understanding.
    """
    return await analyze_item(
        request.item_id,
        request.analysis_type,
        request.context
    )


@app.post("/api/data/research")
async def research(request: ResearchRequest):
    """
    Request research on a topic.
    Intelligence calls this for deep dives.
    """
    return await research_topic(
        request.topic,
        request.depth,
        request.max_items
    )


# ─────────────────────────────────────────────────────────────────────────────────
# COMPRESS - SYNTHESIS ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────────

@app.get("/api/data/patterns")
async def get_patterns(
    timeframe: str = Query(default="7d", description="7d, 30d, all"),
    type: Optional[str] = Query(default=None)
):
    """Get discovered patterns"""
    patterns = store.patterns
    
    if type:
        patterns = [p for p in patterns if p.get("type") == type]
    
    return {
        "patterns": patterns[-20:],  # Last 20
        "total": len(patterns)
    }


@app.get("/api/data/insights")
async def get_insights():
    """Get synthesized insights"""
    return {
        "insights": store.insights[-10:],  # Last 10
        "total": len(store.insights)
    }


@app.post("/api/data/compress")
async def trigger_compression(background_tasks: BackgroundTasks):
    """Manually trigger compression/synthesis"""
    background_tasks.add_task(detect_patterns)
    background_tasks.add_task(generate_daily_insights)
    
    return {"status": "compression_started"}


# ─────────────────────────────────────────────────────────────────────────────────
# DISSEMINATE - DISTRIBUTION ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────────

@app.get("/api/data/channels")
async def get_channels():
    """Get available dissemination channels"""
    return {
        "channels": {
            "rest_api": {
                "type": "pull",
                "endpoint": "/api/data/feed",
                "description": "Pull data when needed"
            },
            "websocket": {
                "type": "push",
                "endpoint": "/ws/data/stream",
                "description": "Real-time stream"
            },
            "webhook": {
                "type": "push",
                "endpoint": "/api/data/subscribe",
                "description": "Register callback for triggers"
            }
        },
        "active_subscribers": len(store.subscribers),
        "active_websockets": len(store.websocket_clients)
    }


@app.post("/api/data/subscribe")
async def subscribe(request: SubscribeRequest):
    """Subscribe to data updates"""
    subscriber = {
        "callback_url": request.callback_url,
        "triggers": request.triggers,
        "filters": request.filters,
        "subscribed_at": datetime.now(timezone.utc).isoformat()
    }
    
    store.subscribers.append(subscriber)
    
    return {
        "status": "subscribed",
        "triggers": request.triggers,
        "subscriber_count": len(store.subscribers)
    }


@app.websocket("/ws/data/stream")
async def websocket_stream(websocket: WebSocket):
    """WebSocket stream for real-time data"""
    await websocket.accept()
    
    client_id = f"ws_{datetime.now().timestamp()}"
    store.websocket_clients[client_id] = websocket
    
    logger.info(f"📡 WebSocket client connected: {client_id}")
    
    try:
        # Send initial state
        await websocket.send_json({
            "type": "connected",
            "items_available": len(store.raw_items)
        })
        
        # Keep alive and handle messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30)
                
                if data.get("type") == "subscribe":
                    # Client wants to subscribe to specific categories
                    await websocket.send_json({"type": "subscribed", "filters": data.get("filters", {})})
                    
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
                
    except WebSocketDisconnect:
        if client_id in store.websocket_clients:
            del store.websocket_clients[client_id]
        logger.info(f"📡 WebSocket client disconnected: {client_id}")


# ─────────────────────────────────────────────────────────────────────────────────
# MEMORY ENDPOINTS (Mem0 Long-Term Memory)
# ─────────────────────────────────────────────────────────────────────────────────

class MemorySearchRequest(BaseModel):
    """Search memory request"""
    query: str
    type: str = "all"  # "insights", "patterns", "learnings", "all"
    limit: int = 10


class StoreLearningRequest(BaseModel):
    """Store a learning"""
    context: str
    action: str
    outcome: str
    lesson: str


@app.get("/api/data/memory/status")
async def memory_status():
    """Check Mem0 memory status"""
    memory = get_memory()
    return {
        "enabled": memory.enabled,
        "provider": "mem0",
        "description": "Persistent long-term memory for insights, patterns, and learnings"
    }


@app.post("/api/data/memory/search")
async def search_memory(request: MemorySearchRequest):
    """
    Search long-term memory.
    
    Types:
    - insights: High-value synthesized intelligence
    - patterns: Discovered trends and correlations
    - learnings: What worked, what didn't
    - all: Search across all types
    """
    memory = get_memory()
    
    if not memory.enabled:
        return {"error": "Memory not enabled (no MEM0_API_KEY)", "results": []}
    
    if request.type == "all":
        context = await memory.get_relevant_context(request.query)
        return {
            "query": request.query,
            "results": context
        }
    elif request.type == "insights":
        results = await memory.search_insights(request.query, request.limit)
    elif request.type == "patterns":
        results = await memory.search_patterns(request.query, request.limit)
    elif request.type == "learnings":
        results = await memory.search_learnings(request.query, request.limit)
    else:
        return {"error": f"Unknown type: {request.type}"}
    
    return {
        "query": request.query,
        "type": request.type,
        "results": results
    }


@app.post("/api/data/memory/learn")
async def store_learning(request: StoreLearningRequest):
    """
    Store a learning in long-term memory.
    
    Format: Context → Action → Outcome → Lesson
    
    Example:
    - context: "Market showed rising funding rates"
    - action: "Opened short position"
    - outcome: "Successful 5% profit"
    - lesson: "High funding rates often precede corrections"
    """
    memory = get_memory()
    
    if not memory.enabled:
        return {"error": "Memory not enabled"}
    
    result = await memory.store_learning(
        context=request.context,
        action=request.action,
        outcome=request.outcome,
        lesson=request.lesson
    )
    
    return {
        "status": "stored",
        "learning": request.lesson[:100] + "..." if len(request.lesson) > 100 else request.lesson
    }


@app.get("/api/data/memory/context/{topic}")
async def get_memory_context(topic: str):
    """
    Get relevant context from memory for a topic.
    
    Useful for AI Brain to retrieve historical context before making decisions.
    """
    memory = get_memory()
    
    if not memory.enabled:
        return {"error": "Memory not enabled", "context": None}
    
    context = await memory.get_relevant_context(topic)
    return {
        "topic": topic,
        "context": context
    }


@app.get("/api/data/memory/experiment")
async def get_memory_experiment():
    """
    Get Mem0 experiment tracking data.
    
    We're studying Mem0 to:
    1. Understand what makes it valuable
    2. Learn from its architecture
    3. Build something better or decide to keep using it
    """
    tracker = get_tracker()
    report = tracker.get_report()
    
    return {
        "experiment": "mem0_evaluation",
        "purpose": "Learn from Mem0 to reproduce/enhance memory capabilities",
        "report": report,
        "recommendation": (
            "Continue experiment" if report["total_operations"] < 100 
            else "Enough data to evaluate"
        )
    }


class ObservationRequest(BaseModel):
    """Record an observation about Mem0"""
    observation: str


@app.post("/api/data/memory/observe")
async def record_observation(request: ObservationRequest):
    """
    Record an observation about Mem0's behavior.
    
    We're learning from the experiment!
    """
    tracker = get_tracker()
    tracker.add_observation(request.observation)
    
    return {
        "status": "recorded",
        "total_observations": len(tracker.observations)
    }


# ─────────────────────────────────────────────────────────────────────────────────
# UNIFIED MEMORY ENDPOINTS (Level 10)
# ─────────────────────────────────────────────────────────────────────────────────

@app.get("/api/memory/stats")
async def get_memory_stats():
    """
    Get memory system statistics.
    
    Returns counts, latencies, and health metrics.
    """
    memory = get_memory()
    tracker = get_tracker()
    
    report = tracker.get_report()
    
    return {
        "enabled": memory.enabled,
        "stats": report["metrics"],
        "avg_relevance": report["avg_relevance"],
        "recent_observations": report["observations"],
        "recommendations": report["recommendations"],
        "total_operations": report["total_operations"]
    }


@app.get("/api/memory/system-stats")
async def get_memory_system_stats():
    """
    Get Python process memory statistics.
    
    Shows actual RAM usage of the Data Service process,
    useful for monitoring memory leaks and optimization.
    """
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    # Get system memory
    system_memory = psutil.virtual_memory()
    
    # Get retrieval tracker stats
    from .memory_hygiene import get_tracker as get_retrieval_tracker
    retrieval_tracker = get_retrieval_tracker()
    retrieval_stats = retrieval_tracker.get_stats()
    
    return {
        "process": {
            "pid": os.getpid(),
            "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
            "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
            "percent": round(process.memory_percent(), 2)
        },
        "system": {
            "total_gb": round(system_memory.total / 1024 / 1024 / 1024, 2),
            "available_gb": round(system_memory.available / 1024 / 1024 / 1024, 2),
            "used_percent": system_memory.percent
        },
        "memory_hygiene": retrieval_stats,
        "thresholds": {
            "warning_mb": 500,
            "critical_mb": 1000,
            "status": "healthy" if memory_info.rss < 500 * 1024 * 1024 else 
                      "warning" if memory_info.rss < 1000 * 1024 * 1024 else "critical"
        }
    }


@app.post("/api/memory/search")
async def unified_memory_search(request: MemorySearchRequest):
    """
    Unified memory search across all types with quality weighting.
    """
    memory = get_memory()
    results = await memory.search_all(
        request.query, 
        request.limit, 
        quality_weighted=True
    )
    return results


@app.get("/api/memory/wisdom/{topic}")
async def get_memory_wisdom(topic: str):
    """
    Get aggregated wisdom for a domain.
    
    Returns patterns, learnings, and past decisions for informed decision-making.
    """
    memory = get_memory()
    return await memory.get_wisdom(topic)


@app.post("/api/learning/trade")
async def capture_trade_learning(
    symbol: str,
    direction: str,
    entry_price: float,
    exit_price: float,
    pnl_usd: float,
    strategy: str = "unknown",
    duration_minutes: float = 0
):
    """
    Capture learning from a completed trade.
    """
    memory = get_memory()
    
    outcome = "profitable" if pnl_usd > 0 else "loss"
    pnl_pct = ((exit_price - entry_price) / entry_price * 100) if direction == "long" else ((entry_price - exit_price) / entry_price * 100)
    
    content = f"Trade on {symbol}: {direction} from {entry_price} to {exit_price}, PnL ${pnl_usd:.2f} ({pnl_pct:.2f}%). Strategy: {strategy}. Outcome: {outcome}."
    
    result = await memory.store_learning(
        context=f"Trading {symbol} with {strategy}",
        action=f"{direction} entry at {entry_price}",
        outcome=outcome,
        lesson=content
    )
    
    return {"status": "captured", "trade": symbol, "pnl_usd": pnl_usd, "result": result}


@app.post("/api/learning/deployment")
async def capture_deployment_learning(
    service_name: str,
    version: str,
    success: bool,
    duration_seconds: float,
    error_message: str = ""
):
    """
    Capture learning from a deployment.
    """
    memory = get_memory()
    
    outcome = "successful" if success else "failed"
    content = f"Deployment of {service_name} v{version} was {outcome} in {duration_seconds:.1f}s."
    if error_message:
        content += f" Error: {error_message}"
    
    result = await memory.store_learning(
        context=f"Deploying {service_name} version {version}",
        action=f"Deployment {'succeeded' if success else 'failed'}",
        outcome=outcome,
        lesson=content
    )
    
    return {"status": "captured", "service": service_name, "success": success, "result": result}


# ─────────────────────────────────────────────────────────────────────────────────
# ADMIN ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────────

@app.post("/api/data/refresh")
async def refresh(background_tasks: BackgroundTasks):
    """Trigger immediate collection"""
    background_tasks.add_task(collect_all)
    return {"status": "refresh_started"}


@app.post("/api/data/cleanup")
async def cleanup(days: int = 30):
    """Clean up old items"""
    removed = store.cleanup_old(days)
    return {"removed": removed, "remaining": len(store.raw_items)}


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8125)


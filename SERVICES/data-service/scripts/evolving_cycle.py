#!/usr/bin/env python3
"""
🧬 EVOLVING INTELLIGENCE CYCLE
==============================
Each cycle learns from the last. Gets smarter. Creates better diamonds.
Coal → Pressure → Time → DIAMONDS
"""

import asyncio
import httpx
import time
from datetime import datetime, timezone
from collections import Counter
import re

MEM0_KEY = "m0-e6AZpFLmM3gu7W2IYIJ8LL1UTGiOl9nwVZ4OWFFo"
MEM0_URL = "https://api.mem0.ai/v1"
DATA_URL = "http://localhost:8125"

# Evolution state - learns across generations
evolution = {
    "best_topics": [],
    "diamond_count": 0,
    "learning_rate": 1.0,
    "generation": 0,
    "velocity_history": []
}


async def wide_scan():
    """WIDE - Cast the net"""
    print("🌊 WIDE - Scanning...")
    data = {"feed": [], "memory": []}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(f"{DATA_URL}/api/data/feed?limit=100")
            if resp.status_code == 200:
                data["feed"] = resp.json().get("items", [])
        except Exception as e:
            print(f"   ⚠️ {e}")
        
        # Query memory for best topics from previous generations
        for topic in evolution["best_topics"][:3]:
            try:
                resp = await client.get(f"{DATA_URL}/api/data/memory/context/{topic}")
                if resp.status_code == 200:
                    ctx = resp.json().get("context", {})
                    data["memory"].extend(ctx.get("learnings", [])[:3])
            except:
                pass
    
    print(f"   Feed: {len(data['feed'])}, Memory refs: {len(data['memory'])}")
    return data


async def deep_analyze(data):
    """DEEP - Find patterns"""
    print("🔬 DEEP - Analyzing...")
    analysis = {}
    
    feed = data.get("feed", [])
    if not feed:
        return analysis
    
    # Categories
    cats = Counter(i.get("category", "general") for i in feed)
    analysis["categories"] = dict(cats)
    
    # Extract topics from text
    all_text = " ".join(
        (i.get("title", "") + " " + (i.get("summary") or "")) 
        for i in feed
    ).lower()
    
    words = re.findall(r"\b[a-z]{4,12}\b", all_text)
    freq = Counter(words)
    
    # Stop words
    stop = {
        "this", "that", "with", "from", "have", "been", "were", "will", 
        "what", "when", "where", "which", "their", "there", "about",
        "would", "could", "should", "these", "those", "being", "after",
        "before", "other", "some", "into", "only", "your", "more", "than",
        "then", "also", "just", "over", "such", "back", "most", "made",
        "make", "like", "very", "even", "much", "well", "still", "between",
        "through", "under", "while", "here", "http", "https", "www"
    }
    
    emerging = [
        (w, c) for w, c in freq.most_common(50) 
        if w not in stop and c > 1
    ][:10]
    analysis["emerging"] = emerging
    
    # Quality
    high_val = [i for i in feed if i.get("relevance_score", 0) > 0.6]
    analysis["high_value"] = high_val[:5]
    analysis["quality_ratio"] = len(high_val) / len(feed) if feed else 0
    
    print(f"   Categories: {len(cats)}, Emerging: {len(emerging)}, Quality: {analysis['quality_ratio']:.0%}")
    return analysis


async def compress_diamonds(analysis, gen):
    """COMPRESS - Create diamonds from coal"""
    print("💎 COMPRESS - Creating diamonds...")
    diamonds = []
    
    # Category diamond
    cats = analysis.get("categories", {})
    if cats:
        top = max(cats.items(), key=lambda x: x[1])
        total = sum(cats.values())
        pct = round(top[1] / total * 100) if total else 0
        diamonds.append({
            "type": "insight",
            "content": f"Gen{gen}: {top[0]} dominates at {pct}% of {total} items",
            "value": 0.7
        })
    
    # Trends diamond
    emerging = analysis.get("emerging", [])
    if emerging:
        topics = [e[0] for e in emerging[:5]]
        diamonds.append({
            "type": "pattern", 
            "content": f"Gen{gen} emerging: {', '.join(topics)}",
            "value": 0.9
        })
        evolution["best_topics"] = topics  # Learn for next gen
    
    # Quality diamond
    quality = analysis.get("quality_ratio", 0)
    assessment = "Excellent" if quality > 0.4 else "Good" if quality > 0.25 else "Needs work"
    diamonds.append({
        "type": "insight",
        "content": f"Gen{gen} quality: {quality:.0%} ({assessment})",
        "value": 0.6
    })
    
    # Top signals diamond
    high = analysis.get("high_value", [])
    if high:
        top_titles = [h.get("title", "")[:35] for h in high[:3]]
        diamonds.append({
            "type": "learning",
            "content": f"Gen{gen} top: {' | '.join(top_titles)}",
            "value": 0.85
        })
    
    # Meta-evolution diamond
    diamonds.append({
        "type": "learning",
        "content": f"Gen{gen}: {len(diamonds)} diamonds, lr={evolution['learning_rate']:.2f}, topics={len(evolution['best_topics'])}",
        "value": 1.0
    })
    
    print(f"   Created {len(diamonds)} diamonds")
    return diamonds


async def disseminate(diamonds, gen):
    """DISSEMINATE - Share the diamonds"""
    print("📡 DISSEMINATE - Sharing...")
    stored = 0
    headers = {
        "Authorization": f"Token {MEM0_KEY}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for d in diamonds:
            if d["value"] >= 0.7:
                user_id = f"fpai_{d['type']}s"
                try:
                    resp = await client.post(
                        f"{MEM0_URL}/memories/",
                        headers=headers,
                        json={
                            "messages": [{"role": "user", "content": d["content"]}],
                            "user_id": user_id,
                            "metadata": {
                                "type": d["type"],
                                "value": d["value"],
                                "generation": gen,
                                "source": "evolving_cycle"
                            }
                        }
                    )
                    if resp.status_code == 200:
                        stored += 1
                except:
                    pass
                await asyncio.sleep(0.2)
    
    evolution["diamond_count"] += stored
    print(f"   Stored {stored} diamonds (total: {evolution['diamond_count']})")
    return stored


async def run_evolution(generations=5, interval=8):
    """Run evolutionary intelligence cycles"""
    print("=" * 60)
    print("🧬 EVOLVING INTELLIGENCE ENGINE")
    print("   Coal → Pressure → Time → DIAMONDS")
    print("   Each generation learns from the last")
    print("=" * 60)
    
    for gen in range(1, generations + 1):
        evolution["generation"] = gen
        
        print(f"\n{'='*60}")
        print(f"🧬 GENERATION {gen}")
        print(f"{'='*60}")
        
        start = time.time()
        
        # The cycle
        data = await wide_scan()
        analysis = await deep_analyze(data)
        diamonds = await compress_diamonds(analysis, gen)
        stored = await disseminate(diamonds, gen)
        
        duration = time.time() - start
        velocity = stored / duration if duration > 0 else 0
        evolution["velocity_history"].append(velocity)
        
        # Evolution metrics
        avg_velocity = sum(evolution["velocity_history"]) / len(evolution["velocity_history"])
        
        print(f"\n📊 Gen{gen} Results:")
        print(f"   ⏱️  Duration: {duration:.1f}s")
        print(f"   💎 Diamonds: {len(diamonds)} created, {stored} stored")
        print(f"   🚀 Velocity: {velocity:.2f} d/s (avg: {avg_velocity:.2f})")
        print(f"   📈 Topics learned: {evolution['best_topics'][:3]}")
        
        # Evolve
        if stored > 3:
            evolution["learning_rate"] = min(2.0, evolution["learning_rate"] * 1.1)
            print(f"   🧬 Learning rate → {evolution['learning_rate']:.2f}")
        
        if gen < generations:
            print(f"\n⏳ Evolution continues in {interval}s...")
            await asyncio.sleep(interval)
    
    # Final summary
    print("\n" + "=" * 60)
    print("🧬 EVOLUTION COMPLETE")
    print("=" * 60)
    print(f"   Generations: {generations}")
    print(f"   Total diamonds: {evolution['diamond_count']}")
    print(f"   Final learning rate: {evolution['learning_rate']:.2f}")
    print(f"   Avg velocity: {sum(evolution['velocity_history'])/len(evolution['velocity_history']):.2f} d/s")
    print(f"   Best topics: {evolution['best_topics']}")
    print("=" * 60)
    
    # Store evolution summary
    summary = f"Evolution complete: {generations} gens, {evolution['diamond_count']} diamonds, lr={evolution['learning_rate']:.2f}, topics={evolution['best_topics'][:5]}"
    print(f"\n💾 Storing evolution summary...")
    
    headers = {"Authorization": f"Token {MEM0_KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        await client.post(
            f"{MEM0_URL}/memories/",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": summary}],
                "user_id": "fpai_learnings",
                "metadata": {"type": "evolution_summary", "generations": generations}
            }
        )
    print("   ✅ Summary stored")


if __name__ == "__main__":
    import sys
    gens = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    asyncio.run(run_evolution(gens, interval))
















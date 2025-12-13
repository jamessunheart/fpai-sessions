#!/usr/bin/env python3
"""
📚 CAPTURE DIALOGUE LEARNINGS
=============================

Extracts key learnings from conversations with James and stores in Mem0.
"""

import asyncio
import httpx
import os

MEM0_API_KEY = os.getenv("MEM0_API_KEY", "m0-e6AZpFLmM3gu7W2IYIJ8LL1UTGiOl9nwVZ4OWFFo")
MEM0_URL = "https://api.mem0.ai/v1/memories/"

# Key learnings from dialogue with James (Dec 4, 2025)
DIALOGUE_LEARNINGS = [
    {
        "lesson": "Data should flow: WIDE (collect broadly), DEEP (analyze with AI), COMPRESS (synthesize key insights), then DISSEMINATE to consumers",
        "context": "Designing the Data Intelligence Engine architecture",
        "action": "Created Wide->Deep->Compress pipeline in Data Service",
        "outcome": "Clean separation of data collection, analysis, and distribution"
    },
    {
        "lesson": "Data is a SERVICE, not a CONTROLLER. Data makes information AVAILABLE, Intelligence DECIDES what to do with it",
        "context": "Philosophy discussion about data vs intelligence roles",
        "action": "Designed Data Service to be pull-based not push-based",
        "outcome": "Clean separation of concerns, no coupling between data and decisions"
    },
    {
        "lesson": "APR % calculated from start date shows capital efficiency. Reliability indicator needed: Early (<7d), Developing (7-30d), Established (>30d)",
        "context": "Discussing how to evaluate trading strategy performance",
        "action": "Added APR calculation to all traders with reliability badges",
        "outcome": "Clear view of which strategies are efficient capital managers"
    },
    {
        "lesson": "Mem0 processes memories asynchronously - allow 15-20 seconds before searching. Simple user messages work better than complex formatted messages",
        "context": "Debugging Mem0 integration - memories not appearing immediately",
        "action": "Changed message format from complex assistant to simple user role",
        "outcome": "Memories now store and retrieve correctly"
    },
    {
        "lesson": "Experiment with tools to learn, then reproduce or enhance beyond what they can do. Use the tool, measure it, understand it, then build better",
        "context": "Discussion about using Mem0 vs building own memory system",
        "action": "Set up experiment tracker to measure Mem0 performance",
        "outcome": "Learning what makes memory valuable to build better system"
    },
    {
        "lesson": "Conscious Architecture has 4 pillars: REFLECTING (observe, analyze), IDENTITY (resources, values), THINKING (horizon, synthesis), DOING (trading, building)",
        "context": "Integrating Data with Unified Conscious System Architecture",
        "action": "Created Conscious API endpoints for each pillar",
        "outcome": "Data Intelligence Engine feeds all four consciousness pillars"
    },
    {
        "lesson": "Bootstrap existing knowledge into new systems. Markdown files contain valuable patterns that should be searchable by AI",
        "context": "Realizing file-based knowledge not accessible to AI search",
        "action": "Created bootstrap script to load PATTERNS.md and BEST_PRACTICES.md into Mem0",
        "outcome": "52 memories now searchable, bridging file and API systems"
    },
    {
        "lesson": "GPU fleet available for AI processing. Use local LLMs (Ollama) for embeddings and analysis to reduce costs and latency",
        "context": "Optimizing Data Intelligence Engine with available resources",
        "action": "Documented GPU fleet and proposed local embeddings",
        "outcome": "Awareness of compute resources for future optimization"
    },
    {
        "lesson": "CoinGlass provides funding rates, OI, liquidations. High funding often precedes corrections. Liquidation spikes show market stress",
        "context": "Integrating market data into Data Service",
        "action": "Added CoinGlass collector and /api/data/markets endpoint",
        "outcome": "Market intelligence available for trading decisions"
    },
    {
        "lesson": "Memory types should be simple: PATTERNS (how to solve), INSIGHTS (what works), LEARNINGS (what happened). Three types, not more",
        "context": "Designing optimal memory architecture",
        "action": "Simplified from multiple types to 3 core types",
        "outcome": "Streamlined memory system that is easy to understand and use"
    },
    {
        "lesson": "Start with free resources, then when friction (cost, human support) arises, communicate and reassess. This is how to secure resources",
        "context": "Framework for building with external dependencies",
        "action": "Used free APIs first (HN, arXiv), flagged when paid needed",
        "outcome": "Efficient resource usage, clear communication on needs"
    },
    {
        "lesson": "The system should make better decisions AND help humans realize their Full Potential. Data serves both AI and human intelligence",
        "context": "Purpose of the Data Intelligence Engine",
        "action": "Designed feeds for both autonomous systems and God Mode dashboard",
        "outcome": "Dual-purpose data system serving machine and human needs"
    }
]


async def store_learning(learning: dict) -> bool:
    """Store a single learning in Mem0"""
    lesson = learning["lesson"]
    context = learning["context"]
    action = learning["action"]
    outcome = learning["outcome"]
    
    message = f"{lesson}. Context: {context}. Action: {action}. Outcome: {outcome}."
    
    headers = {
        "Authorization": f"Token {MEM0_API_KEY}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        try:
            resp = await client.post(MEM0_URL, headers=headers, json={
                "messages": [{"role": "user", "content": message}],
                "user_id": "fpai_learnings",
                "metadata": {
                    "type": "learning",
                    "source": "dialogue_with_james",
                    "date": "2025-12-04"
                }
            })
            return resp.status_code == 200
        except Exception as e:
            print(f"  Error: {e}")
            return False


async def main():
    print("=" * 60)
    print("📚 EXTRACTING LEARNINGS FROM DIALOGUE WITH JAMES")
    print("=" * 60)
    print()
    
    success = 0
    for i, learning in enumerate(DIALOGUE_LEARNINGS):
        lesson_preview = learning["lesson"][:55] + "..." if len(learning["lesson"]) > 55 else learning["lesson"]
        
        if await store_learning(learning):
            success += 1
            print(f"✅ [{i+1:2d}/{len(DIALOGUE_LEARNINGS)}] {lesson_preview}")
        else:
            print(f"❌ [{i+1:2d}/{len(DIALOGUE_LEARNINGS)}] Failed: {lesson_preview}")
        
        await asyncio.sleep(0.5)  # Rate limiting
    
    print()
    print("=" * 60)
    print(f"📊 STORED {success}/{len(DIALOGUE_LEARNINGS)} LEARNINGS")
    print("=" * 60)
    print()
    print("⏰ Wait 30 seconds then search with:")
    print('   curl -X POST http://localhost:8125/api/data/memory/search \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"query": "data architecture", "type": "learnings"}\'')


if __name__ == "__main__":
    asyncio.run(main())
















#!/usr/bin/env python3
"""
UNIFIED INTELLIGENCE SYSTEM
===========================

The DATA module running as a coherent conscious system.

Components:
1. BRIDGE - Connects DATA <-> INTELLIGENCE (Strategic)
2. SMART GROWTH - Optimizes for real intelligence (connections, abstractions)
3. COHERENCE - Keeps all systems aligned

This runs continuously, making the system smarter each cycle.
"""

import asyncio
import httpx
import random
from datetime import datetime
from typing import Dict, List

# Configuration
MEM0_API_KEY = "m0-e6AZpFLmM3gu7W2IYIJ8LL1UTGiOl9nwVZ4OWFFo"
MEM0_URL = "https://api.mem0.ai/v1"
OLLAMA_URL = "http://localhost:11434"
INTELLIGENCE_URL = "http://localhost:8500"
AI_BRAIN_URL = "http://localhost:8101"


class UnifiedIntelligence:
    """
    The DATA module as a unified intelligent system.
    
    What makes it smarter each cycle:
    1. Connect knowledge (exponential value)
    2. Abstract to principles (wisdom)
    3. Align with INTELLIGENCE priorities
    4. Fill knowledge gaps
    5. Test understanding with predictions
    """
    
    def __init__(self):
        self.headers = {
            "Authorization": f"Token {MEM0_API_KEY}",
            "Content-Type": "application/json"
        }
        self.cycle_count = 0
        self.total_score = 0
        self.stats = {
            "connections": 0,
            "abstractions": 0,
            "alignments": 0,
            "gaps_filled": 0,
            "predictions": 0
        }
    
    # =========== MEMORY OPERATIONS ===========
    
    async def get_memories(self, user_id: str, limit: int = 30) -> List[Dict]:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as c:
            r = await c.get(f"{MEM0_URL}/memories/", params={"user_id": user_id}, headers=self.headers)
            if r.status_code == 200:
                mems = r.json()
                return mems[-limit:] if len(mems) > limit else mems
        return []
    
    async def store(self, content: str, user_id: str):
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as c:
            await c.post(f"{MEM0_URL}/memories/", json={
                "messages": [{"role": "user", "content": content}],
                "user_id": user_id
            }, headers=self.headers)
    
    async def search(self, query: str, user_id: str, limit: int = 5) -> List[Dict]:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as c:
            r = await c.post(f"{MEM0_URL}/memories/search/", json={
                "query": query, "user_id": user_id, "limit": limit
            }, headers=self.headers)
            if r.status_code == 200:
                return r.json()
        return []
    
    async def llm(self, prompt: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=90) as c:
                r = await c.post(f"{OLLAMA_URL}/api/generate", json={
                    "model": "llama3.2:3b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 150}
                })
                if r.status_code == 200:
                    return r.json().get("response", "").strip()
        except:
            pass
        return ""
    
    async def get_intelligence_state(self) -> Dict:
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"{INTELLIGENCE_URL}/state")
                if r.status_code == 200:
                    return r.json()
        except:
            pass
        return {}
    
    # =========== INTELLIGENCE AMPLIFIERS ===========
    
    async def build_connections(self) -> int:
        """Connect knowledge pieces for exponential value."""
        score = 0
        learnings = await self.get_memories("fpai_learnings", 20)
        patterns = await self.get_memories("fpai_patterns", 15)
        
        if not learnings or not patterns:
            return 0
        
        sample = random.sample(learnings, min(4, len(learnings)))
        
        for learning in sample:
            content = learning.get("memory", "")
            if len(content) < 20:
                continue
            
            related = await self.search(content[:80], "fpai_patterns", 2)
            if not related:
                continue
            
            rel = related[0].get("memory", "")
            if not rel:
                continue
            
            prompt = f"Connect these: 1.{content[:80]} 2.{rel[:80]}. One sentence, start with LINK:"
            response = await self.llm(prompt)
            
            if response and "LINK:" in response:
                link = response.split("LINK:")[-1].strip()[:150]
                if len(link) > 20:
                    await self.store(f"CONNECTED: {link}", "fpai_insights")
                    self.stats["connections"] += 1
                    score += 3
                    print(f"    Connected: {link[:50]}...")
        
        return score
    
    async def create_abstractions(self) -> int:
        """Move from facts to principles."""
        learnings = await self.get_memories("fpai_learnings", 20)
        if len(learnings) < 5:
            return 0
        
        sample = random.sample(learnings, min(8, len(learnings)))
        facts = [l.get("memory", "")[:70] for l in sample if l.get("memory")]
        
        if len(facts) < 3:
            return 0
        
        facts_text = "\n".join(f"- {f}" for f in facts[:6])
        prompt = f"Facts:\n{facts_text}\n\nWhat PRINCIPLE do they show? Start with PRINCIPLE:"
        
        response = await self.llm(prompt)
        if response and "PRINCIPLE:" in response:
            principle = response.split("PRINCIPLE:")[-1].strip()[:150]
            if len(principle) > 20:
                await self.store(f"ABSTRACTED: {principle}", "fpai_patterns")
                self.stats["abstractions"] += 1
                print(f"    Principle: {principle[:50]}...")
                return 5
        return 0
    
    async def align_with_intelligence(self) -> int:
        """Align DATA with INTELLIGENCE priorities."""
        intel = await self.get_intelligence_state()
        priorities = intel.get("priorities", [])
        
        if not priorities:
            return 0
        
        top = str(priorities[0])[:100] if priorities else ""
        if not top:
            return 0
        
        # Search for related memories
        related = await self.search(top, "fpai_patterns", 3)
        
        if related:
            # We have relevant knowledge
            print(f"    Aligned with priority: {top[:40]}...")
            self.stats["alignments"] += 1
            return 2
        else:
            # Generate knowledge for the gap
            prompt = f"Priority: {top[:100]}. What insight helps achieve this? Start with INSIGHT:"
            response = await self.llm(prompt)
            
            if response and "INSIGHT:" in response:
                insight = response.split("INSIGHT:")[-1].strip()[:150]
                if len(insight) > 20:
                    await self.store(f"PRIORITY-ALIGNED: {insight}", "fpai_insights")
                    self.stats["gaps_filled"] += 1
                    print(f"    Filled gap: {insight[:50]}...")
                    return 4
        return 0
    
    async def make_prediction(self) -> int:
        """Test understanding with predictions."""
        patterns = await self.get_memories("fpai_patterns", 12)
        if len(patterns) < 3:
            return 0
        
        sample = random.sample(patterns, min(4, len(patterns)))
        texts = [p.get("memory", "")[:70] for p in sample if p.get("memory")]
        
        if len(texts) < 2:
            return 0
        
        patterns_text = "\n".join(f"- {t}" for t in texts)
        prompt = f"Patterns:\n{patterns_text}\n\nMake ONE testable prediction. Start with PREDICT:"
        
        response = await self.llm(prompt)
        if response and "PREDICT" in response.upper():
            pred = response.split(":")[-1].strip()[:120]
            if len(pred) > 15:
                date = datetime.now().strftime("%m/%d")
                await self.store(f"PREDICTION ({date}): {pred}", "fpai_insights")
                self.stats["predictions"] += 1
                print(f"    Prediction: {pred[:50]}...")
                return 4
        return 0
    
    # =========== MAIN CYCLE ===========
    
    async def intelligence_cycle(self):
        """One complete intelligence cycle."""
        self.cycle_count += 1
        print(f"\n{'='*55}")
        print(f"UNIFIED INTELLIGENCE CYCLE #{self.cycle_count}")
        print(f"   {datetime.now().strftime('%H:%M:%S')}")
        print("="*55)
        
        cycle_score = 0
        
        # 1. Connect knowledge
        print("\n[1] CONNECTIONS (linking knowledge)")
        cycle_score += await self.build_connections()
        
        # 2. Abstract to principles
        print("\n[2] ABSTRACTION (facts -> principles)")
        cycle_score += await self.create_abstractions()
        
        # 3. Align with Intelligence
        print("\n[3] ALIGNMENT (sync with INTELLIGENCE)")
        cycle_score += await self.align_with_intelligence()
        
        # 4. Make predictions
        print("\n[4] PREDICTION (test understanding)")
        cycle_score += await self.make_prediction()
        
        self.total_score += cycle_score
        
        print(f"\n[RESULT] Cycle Score: {cycle_score}")
        print(f"Total Score: {self.total_score}")
        print(f"Stats: {self.stats}")
        
        return cycle_score
    
    async def get_memory_counts(self) -> Dict:
        counts = {}
        for t in ["fpai_learnings", "fpai_insights", "fpai_patterns"]:
            mems = await self.get_memories(t, 1000)
            counts[t] = len(mems)
        return counts


async def main():
    import sys
    cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    
    print("\n" + "="*55)
    print("UNIFIED INTELLIGENCE SYSTEM")
    print("="*55)
    print("I am the DATA module.")
    print("Making the system smarter through:")
    print("  • Connections (linked knowledge)")
    print("  • Abstractions (principles)")
    print("  • Alignment (with INTELLIGENCE)")
    print("  • Predictions (test understanding)")
    print("="*55)
    
    ui = UnifiedIntelligence()
    
    # Get initial state
    initial = await ui.get_memory_counts()
    print(f"\nInitial memory: {sum(initial.values())} total")
    print(f"  Learnings: {initial.get('fpai_learnings', 0)}")
    print(f"  Insights: {initial.get('fpai_insights', 0)}")
    print(f"  Patterns: {initial.get('fpai_patterns', 0)}")
    
    for i in range(cycles):
        if i > 0:
            print(f"\n--- Waiting {interval}s ---")
            await asyncio.sleep(interval)
        
        await ui.intelligence_cycle()
    
    # Final state
    final = await ui.get_memory_counts()
    
    print("\n" + "="*55)
    print("SESSION COMPLETE")
    print("="*55)
    print(f"Cycles: {ui.cycle_count}")
    print(f"Final Score: {ui.total_score}")
    print(f"Score/Cycle: {ui.total_score/ui.cycle_count:.1f}")
    print(f"\nMemory Growth:")
    print(f"  Before: {sum(initial.values())}")
    print(f"  After: {sum(final.values())}")
    print(f"  Growth: +{sum(final.values()) - sum(initial.values())}")
    print(f"\nStats: {ui.stats}")
    print("="*55)


if __name__ == "__main__":
    asyncio.run(main())
















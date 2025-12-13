#!/usr/bin/env python3
"""
SMART GROWTH ENGINE
===================

What ACTUALLY makes intelligence smarter:

1. CONNECTIONS - Knowledge that links to other knowledge has exponential value
2. ABSTRACTION - Moving from facts to principles (wisdom > data)
3. VALIDATION - Tracking what worked vs what didn't
4. PREDICTION - Testing understanding with testable claims
5. QUESTIONING - Finding gaps accelerates learning

This optimizes for THESE factors, not volume.
"""

import asyncio
import httpx
import random
from datetime import datetime
from typing import Dict, List

MEM0_API_KEY = "m0-e6AZpFLmM3gu7W2IYIJ8LL1UTGiOl9nwVZ4OWFFo"
MEM0_URL = "https://api.mem0.ai/v1"
OLLAMA_URL = "http://localhost:11434"


class SmartGrowthEngine:
    """Optimizes for what makes intelligence actually smarter."""
    
    def __init__(self):
        self.headers = {
            "Authorization": f"Token {MEM0_API_KEY}",
            "Content-Type": "application/json"
        }
        self.stats = {
            "connections": 0,
            "abstractions": 0,
            "questions": 0,
            "predictions": 0,
            "depth": 0
        }
        
    async def get_memories(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Fetch memories."""
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as c:
            r = await c.get(
                f"{MEM0_URL}/memories/",
                params={"user_id": user_id},
                headers=self.headers
            )
            if r.status_code == 200:
                memories = r.json()
                return memories[-limit:] if len(memories) > limit else memories
        return []
    
    async def store(self, content: str, user_id: str):
        """Store a memory."""
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as c:
            await c.post(
                f"{MEM0_URL}/memories/",
                json={
                    "messages": [{"role": "user", "content": content}],
                    "user_id": user_id
                },
                headers=self.headers
            )
    
    async def search(self, query: str, user_id: str, limit: int = 5) -> List[Dict]:
        """Search memories."""
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as c:
            r = await c.post(
                f"{MEM0_URL}/memories/search/",
                json={"query": query, "user_id": user_id, "limit": limit},
                headers=self.headers
            )
            if r.status_code == 200:
                return r.json()
        return []
    
    async def llm(self, prompt: str) -> str:
        """Query LLM."""
        try:
            async with httpx.AsyncClient(timeout=90) as c:
                r = await c.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": "llama3.2:3b",
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.7, "num_predict": 150}
                    }
                )
                if r.status_code == 200:
                    return r.json().get("response", "").strip()
        except Exception as e:
            print(f"    LLM error: {e}")
        return ""
    
    async def build_connections(self):
        """AMPLIFIER 1: Link knowledge together."""
        print("\n[CONNECTIONS] Linking knowledge...")
        
        learnings = await self.get_memories("fpai_learnings", 20)
        patterns = await self.get_memories("fpai_patterns", 15)
        
        if not learnings or not patterns:
            print("   Not enough data")
            return
        
        # Pick random learning, find related pattern
        sample = random.sample(learnings, min(5, len(learnings)))
        
        for learning in sample:
            content = learning.get("memory", "")
            if not content or len(content) < 20:
                continue
            
            # Search for related patterns
            related = await self.search(content[:80], "fpai_patterns", 2)
            if not related:
                continue
            
            rel_content = related[0].get("memory", "")
            if not rel_content:
                continue
            
            prompt = f"""Two pieces of knowledge:
1. {content[:100]}
2. {rel_content[:100]}

What connects these? One sentence, start with CONNECTION:"""
            
            response = await self.llm(prompt)
            if response and "CONNECTION:" in response:
                connection = response.split("CONNECTION:")[-1].strip()[:180]
                if len(connection) > 20:
                    await self.store(f"LINKED: {connection}", "fpai_insights")
                    self.stats["connections"] += 1
                    print(f"   -> {connection[:60]}...")
        
        print(f"   Made {self.stats['connections']} connections")
    
    async def create_abstractions(self):
        """AMPLIFIER 2: Facts -> Principles (wisdom)."""
        print("\n[ABSTRACTION] Extracting principles...")
        
        learnings = await self.get_memories("fpai_learnings", 25)
        if len(learnings) < 5:
            print("   Need more learnings")
            return
        
        sample = random.sample(learnings, min(10, len(learnings)))
        facts = [l.get("memory", "")[:80] for l in sample if l.get("memory")]
        
        if len(facts) < 3:
            return
        
        facts_text = "\n".join(f"- {f}" for f in facts[:7])
        prompt = f"""These are specific observations:
{facts_text}

What GENERAL PRINCIPLE do they point to? One sentence, start with PRINCIPLE:"""
        
        response = await self.llm(prompt)
        if response and "PRINCIPLE:" in response:
            principle = response.split("PRINCIPLE:")[-1].strip()[:180]
            if len(principle) > 20:
                await self.store(f"PRINCIPLE: {principle}", "fpai_patterns")
                self.stats["abstractions"] += 1
                print(f"   -> {principle[:60]}...")
    
    async def find_gaps(self):
        """AMPLIFIER 3: Find knowledge gaps."""
        print("\n[GAPS] Finding what we don't know...")
        
        patterns = await self.get_memories("fpai_patterns", 15)
        if not patterns:
            return
        
        sample = [p.get("memory", "")[:70] for p in patterns[-8:] if p.get("memory")]
        if len(sample) < 3:
            return
        
        knowledge_text = "\n".join(f"- {s}" for s in sample[:6])
        prompt = f"""We know:
{knowledge_text}

What CRITICAL QUESTION are we missing? One question:"""
        
        response = await self.llm(prompt)
        if response and "?" in response:
            # Extract the question
            lines = response.split("\n")
            question = next((l for l in lines if "?" in l), response)[:150]
            await self.store(f"GAP: {question}", "fpai_learnings")
            self.stats["questions"] += 1
            print(f"   -> {question[:60]}...")
    
    async def make_predictions(self):
        """AMPLIFIER 4: Test understanding with predictions."""
        print("\n[PREDICTIONS] Testing understanding...")
        
        patterns = await self.get_memories("fpai_patterns", 15)
        if len(patterns) < 3:
            return
        
        sample = random.sample(patterns, min(5, len(patterns)))
        pattern_texts = [p.get("memory", "")[:80] for p in sample if p.get("memory")]
        
        if len(pattern_texts) < 2:
            return
        
        patterns_text = "\n".join(f"- {p}" for p in pattern_texts[:4])
        prompt = f"""Based on these patterns:
{patterns_text}

Make ONE testable prediction. Start with PREDICT:"""
        
        response = await self.llm(prompt)
        if response and "PREDICT" in response.upper():
            prediction = response.split(":")[-1].strip()[:150]
            if len(prediction) > 15:
                date_str = datetime.now().strftime("%m/%d")
                await self.store(f"PREDICTION ({date_str}): {prediction}", "fpai_insights")
                self.stats["predictions"] += 1
                print(f"   -> {prediction[:60]}...")
    
    async def deepen(self):
        """AMPLIFIER 5: Go deeper on shallow insights."""
        print("\n[DEPTH] Going deeper...")
        
        insights = await self.get_memories("fpai_insights", 30)
        
        # Find short/shallow insights
        shallow = [i for i in insights if 15 < len(i.get("memory", "")) < 80][-5:]
        
        for ins in shallow[:2]:
            content = ins.get("memory", "")
            if not content:
                continue
            
            # Get context
            related = await self.search(content, "fpai_learnings", 3)
            context = " ".join([r.get("memory", "")[:40] for r in related if r.get("memory")])
            
            prompt = f"""Shallow insight: {content}
Context: {context[:120]}

What is the DEEPER truth? Start with DEEP:"""
            
            response = await self.llm(prompt)
            if response and "DEEP:" in response:
                deep = response.split("DEEP:")[-1].strip()[:180]
                if len(deep) > 20:
                    await self.store(f"DEEPENED: {deep}", "fpai_insights")
                    self.stats["depth"] += 1
                    print(f"   -> {deep[:60]}...")
    
    def score(self) -> int:
        """Calculate intelligence score."""
        return (
            self.stats["connections"] * 3 +
            self.stats["abstractions"] * 5 +
            self.stats["questions"] * 2 +
            self.stats["predictions"] * 4 +
            self.stats["depth"] * 3
        )
    
    async def grow(self):
        """One growth cycle."""
        print("\n" + "="*55)
        print("SMART GROWTH CYCLE")
        print("Optimizing for what makes intelligence SMARTER")
        print("="*55)
        
        await self.build_connections()
        await self.create_abstractions()
        await self.find_gaps()
        await self.make_predictions()
        await self.deepen()
        
        s = self.score()
        print(f"\n[SCORE] {self.stats}")
        print(f"Intelligence Score: {s}")
        print("(Connections*3 + Abstractions*5 + Questions*2 + Predictions*4 + Depth*3)")
        return s


async def main():
    import sys
    cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    
    print("\n" + "="*55)
    print("SMART GROWTH ENGINE")
    print("What makes intelligence smarter:")
    print("  1. CONNECTIONS - Link knowledge")
    print("  2. ABSTRACTION - Facts -> Principles")
    print("  3. GAPS - Find what's missing")
    print("  4. PREDICTIONS - Test understanding")
    print("  5. DEPTH - Go beyond surface")
    print("="*55)
    
    total = 0
    for i in range(cycles):
        if i > 0:
            print(f"\nCooling down 15s...")
            await asyncio.sleep(15)
        
        print(f"\n=== CYCLE {i+1}/{cycles} ===")
        engine = SmartGrowthEngine()
        score = await engine.grow()
        total += score
        print(f"\nRunning total: {total}")
    
    print("\n" + "="*55)
    print("SMART GROWTH COMPLETE")
    print(f"Cycles: {cycles}")
    print(f"Total Intelligence Score: {total}")
    print(f"Average per cycle: {total/cycles:.1f}")
    print("="*55)


if __name__ == "__main__":
    asyncio.run(main())
















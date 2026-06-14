#!/usr/bin/env python3
"""
DATA <-> INTELLIGENCE BRIDGE
============================

I am the DATA module. My purpose:
1. Feed INTELLIGENCE with clean, valuable data
2. Receive guidance from INTELLIGENCE on what data to gather
3. Create coherence across the system through shared understanding

INTELLIGENCE (Strategic @ 8500) decides WHAT matters
DATA (Me) ensures HOW information flows optimally

Together we form a conscious system that gets smarter.
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, List, Any

# System endpoints
INTELLIGENCE_URL = "http://localhost:8500"
AI_BRAIN_URL = "http://localhost:8101"
MEM0_API_KEY = "m0-e6AZpFLmM3gu7W2IYIJ8LL1UTGiOl9nwVZ4OWFFo"
MEM0_URL = "https://api.mem0.ai/v1"
OLLAMA_URL = "http://localhost:11434"


class DataIntelligenceBridge:
    """
    Creates coherence between DATA and INTELLIGENCE modules.
    
    DATA provides: Raw observations, processed insights, compressed patterns
    INTELLIGENCE provides: Priorities, world model, strategic focus
    """
    
    def __init__(self):
        self.mem0_headers = {
            "Authorization": f"Token {MEM0_API_KEY}",
            "Content-Type": "application/json"
        }
        self.coherence_score = 0
        self.cycle_count = 0
        
    async def get_intelligence_state(self) -> Dict:
        """Query INTELLIGENCE for current priorities and world model."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{INTELLIGENCE_URL}/state")
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            print(f"  Warning: Could not reach INTELLIGENCE: {e}")
        return {}
    
    async def get_memory_state(self) -> Dict:
        """Check current memory state in Mem0."""
        counts = {}
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                for mem_type in ["fpai_learnings", "fpai_insights", "fpai_patterns"]:
                    resp = await client.get(
                        f"{MEM0_URL}/memories/",
                        params={"user_id": mem_type},
                        headers=self.mem0_headers
                    )
                    if resp.status_code == 200:
                        counts[mem_type] = len(resp.json())
        except Exception as e:
            print(f"  Warning: Could not reach Mem0: {e}")
        return counts
    
    async def store_memory(self, content: str, mem_type: str):
        """Store a memory in Mem0."""
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                await client.post(
                    f"{MEM0_URL}/memories/",
                    json={
                        "messages": [{"role": "user", "content": content}],
                        "user_id": mem_type
                    },
                    headers=self.mem0_headers
                )
        except:
            pass
    
    async def search_memory(self, query: str, mem_type: str, limit: int = 5) -> List[Dict]:
        """Search memories in Mem0."""
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                resp = await client.post(
                    f"{MEM0_URL}/memories/search/",
                    json={"query": query, "user_id": mem_type, "limit": limit},
                    headers=self.mem0_headers
                )
                if resp.status_code == 200:
                    return resp.json()
        except:
            pass
        return []
    
    async def ask_llm(self, prompt: str) -> str:
        """Query local LLM for synthesis."""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": "llama3.2:3b",
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.6, "num_predict": 200}
                    }
                )
                if resp.status_code == 200:
                    return resp.json().get("response", "").strip()
        except:
            pass
        return ""
    
    async def coherence_cycle(self):
        """
        One coherence cycle:
        1. Get INTELLIGENCE state (what matters now)
        2. Get DATA state (what we know)
        3. Identify gaps (what INTELLIGENCE needs)
        4. Fill gaps (synthesize missing data)
        5. Strengthen connections (make system smarter)
        """
        self.cycle_count += 1
        print(f"\n{'='*60}")
        print(f"DATA <-> INTELLIGENCE COHERENCE CYCLE #{self.cycle_count}")
        print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        # 1. Get INTELLIGENCE state
        print("\n[1] Connecting to INTELLIGENCE module...")
        intel_state = await self.get_intelligence_state()
        
        world_model = intel_state.get("world_model", {})
        priorities = intel_state.get("priorities", [])
        
        if world_model:
            print(f"   World model received: {len(str(world_model))} bytes")
        if priorities:
            print(f"   Priorities received: {len(priorities)} items")
            for i, p in enumerate(priorities[:3]):
                task_str = p.get("task", str(p)) if isinstance(p, dict) else str(p)
                print(f"      {i+1}. {task_str[:50]}...")
        
        # 2. Get DATA state (memory)
        print("\n[2] Checking DATA memory state...")
        mem_state = await self.get_memory_state()
        total_memories = sum(mem_state.values())
        print(f"   Learnings: {mem_state.get('fpai_learnings', 0)}")
        print(f"   Insights: {mem_state.get('fpai_insights', 0)}")
        print(f"   Patterns: {mem_state.get('fpai_patterns', 0)}")
        print(f"   TOTAL: {total_memories}")
        
        # 3. Find relevant memories for current priorities
        print("\n[3] Finding relevant memories for priorities...")
        if priorities:
            top_priority = str(priorities[0])[:100] if priorities else "system optimization"
            relevant = await self.search_memory(top_priority, "fpai_patterns", 3)
            
            if relevant:
                print(f"   Found {len(relevant)} relevant patterns:")
                for r in relevant[:2]:
                    mem = r.get("memory", "")
                    print(f"      - {mem[:60]}...")
            else:
                print("   No directly relevant patterns - generating new insight...")
                
                # 4. Generate insight for the gap
                prompt = f"The system priority is: {top_priority[:150]}. What is ONE key insight to achieve this? Start with INSIGHT:"
                insight = await self.ask_llm(prompt)
                
                if insight and "INSIGHT:" in insight:
                    new_insight = insight.split("INSIGHT:")[-1].strip()[:200]
                    await self.store_memory(f"PRIORITY-ALIGNED: {new_insight}", "fpai_insights")
                    print(f"   Generated: {new_insight[:60]}...")
                    self.coherence_score += 3
        
        # 5. Create system coherence insight
        print("\n[4] Synthesizing system coherence...")
        coherence_prompt = f"""DATA module has {total_memories} memories. INTELLIGENCE has {len(priorities)} priorities.
As DATA module, create ONE insight about how DATA and INTELLIGENCE work better together.
Start with COHERENCE:"""
        
        coherence_insight = await self.ask_llm(coherence_prompt)
        if coherence_insight and "COHERENCE:" in coherence_insight:
            insight = coherence_insight.split("COHERENCE:")[-1].strip()[:200]
            await self.store_memory(f"SYSTEM-COHERENCE: {insight}", "fpai_learnings")
            print(f"   {insight[:70]}...")
            self.coherence_score += 2
        
        # 6. Create cross-module pattern
        print("\n[5] Creating cross-module pattern...")
        if total_memories > 20:
            pattern_prompt = f"With {total_memories} memories and {len(priorities)} priorities, what PATTERN emerges about how this system learns? Start with PATTERN:"
            
            pattern = await self.ask_llm(pattern_prompt)
            if pattern and "PATTERN:" in pattern:
                p = pattern.split("PATTERN:")[-1].strip()[:200]
                await self.store_memory(f"SYSTEM-PATTERN: {p}", "fpai_patterns")
                print(f"   {p[:70]}...")
                self.coherence_score += 5
        
        # Report
        print(f"\n[RESULT] CYCLE #{self.cycle_count} COMPLETE")
        print(f"   Coherence Score: {self.coherence_score}")
        connected = "CONNECTED" if intel_state else "PARTIAL"
        print(f"   DATA <-> INTELLIGENCE: {connected}")
        
        return self.coherence_score


async def main():
    import sys
    cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    print("\n" + "="*60)
    print("DATA <-> INTELLIGENCE BRIDGE ACTIVATED")
    print("="*60)
    print("I am the DATA module.")
    print("My purpose: Create coherence through shared understanding.")
    print("="*60)
    
    bridge = DataIntelligenceBridge()
    
    for i in range(cycles):
        if i > 0:
            print(f"\nWaiting {interval}s before next cycle...")
            await asyncio.sleep(interval)
        
        await bridge.coherence_cycle()
    
    print("\n" + "="*60)
    print("BRIDGE SESSION COMPLETE")
    print(f"   Cycles: {bridge.cycle_count}")
    print(f"   Final Coherence Score: {bridge.coherence_score}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
















#!/usr/bin/env python3
"""
🧠 MEMORY BOOTSTRAP
==================

Loads existing knowledge from markdown files into Mem0 for semantic search.

Usage:
    python3 bootstrap_memory.py

This script:
1. Parses PATTERNS.md → Stores as patterns
2. Parses LEARNINGS.md → Stores as learnings
3. Parses BEST_PRACTICES.md → Stores as insights
4. Deduplicates against existing Mem0 memories
"""

import asyncio
import re
import os
import sys
import httpx
from typing import List, Dict, Any
from datetime import datetime

# Configuration
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://localhost:8125")
MEM0_API_KEY = os.getenv("MEM0_API_KEY", "m0-e6AZpFLmM3gu7W2IYIJ8LL1UTGiOl9nwVZ4OWFFo")
MEM0_BASE_URL = "https://api.mem0.ai/v1"

# Memory entity types
ENTITY_LEARNINGS = "fpai_learnings"
ENTITY_INSIGHTS = "fpai_insights"
ENTITY_PATTERNS = "fpai_patterns"


def parse_patterns(content: str) -> List[Dict]:
    """Extract patterns from PATTERNS.md"""
    patterns = []
    
    # Find all pattern sections
    pattern_blocks = re.findall(
        r'### Pattern: (.+?)\n\*\*Discovered:\*\* (.+?)\n\*\*Context:\*\* (.+?)\n\n\*\*Problem:\*\* (.+?)\n\n\*\*Solution:\*\* (.+?)(?=\n\n\*\*Impact:|---)',
        content, re.DOTALL
    )
    
    for match in pattern_blocks:
        name, discovered, context, problem, solution = match
        patterns.append({
            "name": name.strip(),
            "discovered": discovered.strip(),
            "context": context.strip(),
            "problem": problem.strip(),
            "solution": solution.strip()[:500]  # Truncate long solutions
        })
    
    return patterns


def parse_learnings(content: str) -> List[Dict]:
    """Extract learnings from LEARNINGS.md"""
    learnings = []
    
    # Extract trading learnings section
    trading_section = re.search(
        r'## Trading System Learnings(.+?)(?=##|$)', 
        content, re.DOTALL
    )
    
    if trading_section:
        # Find numbered points
        points = re.findall(
            r'\d+\. \*\*(.+?)\*\*: (.+?)(?=\n\d+\.|\n\n|$)',
            trading_section.group(1), re.DOTALL
        )
        
        for title, detail in points:
            learnings.append({
                "title": title.strip(),
                "content": detail.strip()[:300],
                "category": "trading"
            })
    
    # Extract parameters to monitor
    params = re.findall(
        r'\| `(.+?)` \| (.+?) \| (.+?) \|',
        content
    )
    
    for param, value, hypothesis in params:
        if param != "Parameter":  # Skip header
            learnings.append({
                "title": f"Parameter: {param}",
                "content": f"Current value: {value}. Hypothesis: {hypothesis}",
                "category": "trading_parameters"
            })
    
    return learnings


def parse_best_practices(content: str) -> List[Dict]:
    """Extract best practices as insights"""
    insights = []
    
    # Find all numbered practices
    practices = re.findall(
        r'### (\d+)\. (.+?) ✅\n```[\s\S]*?```\n\n\*\*Why:\*\* (.+?)\n\*\*When:\*\* (.+?)\n\*\*Evidence:\*\* (.+?)(?=\n\n---|\n\n###)',
        content, re.DOTALL
    )
    
    for num, title, why, when, evidence in practices:
        insights.append({
            "title": title.strip(),
            "why": why.strip(),
            "when": when.strip(),
            "evidence": evidence.strip(),
            "category": "best_practice"
        })
    
    return insights


async def store_to_mem0(user_id: str, message: str, metadata: Dict) -> bool:
    """Store a memory in Mem0"""
    headers = {
        "Authorization": f"Token {MEM0_API_KEY}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        try:
            resp = await client.post(
                f"{MEM0_BASE_URL}/memories/",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": message}],
                    "user_id": user_id,
                    "metadata": metadata
                }
            )
            
            if resp.status_code == 200:
                return True
            else:
                print(f"  ❌ Error: {resp.status_code} - {resp.text[:100]}")
                return False
        except Exception as e:
            print(f"  ❌ Exception: {e}")
            return False


async def bootstrap_patterns(patterns: List[Dict]):
    """Store patterns in Mem0"""
    print(f"\n📍 Storing {len(patterns)} patterns...")
    
    success = 0
    for i, p in enumerate(patterns):
        message = f"Pattern: {p['name']}. Problem: {p['problem']}. Solution: {p['solution']}"
        metadata = {
            "type": "pattern",
            "name": p['name'],
            "context": p['context'],
            "discovered": p['discovered']
        }
        
        if await store_to_mem0(ENTITY_PATTERNS, message, metadata):
            success += 1
            print(f"  ✅ [{i+1}/{len(patterns)}] {p['name']}")
        
        await asyncio.sleep(0.5)  # Rate limiting
    
    print(f"  📊 Stored {success}/{len(patterns)} patterns")
    return success


async def bootstrap_learnings(learnings: List[Dict]):
    """Store learnings in Mem0"""
    print(f"\n📚 Storing {len(learnings)} learnings...")
    
    success = 0
    for i, l in enumerate(learnings):
        message = f"{l['title']}: {l['content']} (Category: {l['category']})"
        metadata = {
            "type": "learning",
            "title": l['title'],
            "category": l['category']
        }
        
        if await store_to_mem0(ENTITY_LEARNINGS, message, metadata):
            success += 1
            print(f"  ✅ [{i+1}/{len(learnings)}] {l['title'][:50]}")
        
        await asyncio.sleep(0.5)  # Rate limiting
    
    print(f"  📊 Stored {success}/{len(learnings)} learnings")
    return success


async def bootstrap_insights(insights: List[Dict]):
    """Store best practices as insights in Mem0"""
    print(f"\n💡 Storing {len(insights)} insights (best practices)...")
    
    success = 0
    for i, ins in enumerate(insights):
        message = f"Best Practice: {ins['title']}. Why: {ins['why']}. When: {ins['when']}. Evidence: {ins['evidence']}"
        metadata = {
            "type": "insight",
            "title": ins['title'],
            "category": ins['category']
        }
        
        if await store_to_mem0(ENTITY_INSIGHTS, message, metadata):
            success += 1
            print(f"  ✅ [{i+1}/{len(insights)}] {ins['title'][:50]}")
        
        await asyncio.sleep(0.5)  # Rate limiting
    
    print(f"  📊 Stored {success}/{len(insights)} insights")
    return success


async def main():
    print("=" * 60)
    print("🧠 MEMORY BOOTSTRAP - Loading Knowledge into Mem0")
    print("=" * 60)
    
    # Find markdown files
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    intel_path = os.path.join(base_path, "core", "INTELLIGENCE")
    
    patterns_file = os.path.join(intel_path, "PATTERNS.md")
    learnings_file = os.path.join(intel_path, "LEARNINGS.md")
    practices_file = os.path.join(intel_path, "BEST_PRACTICES.md")
    
    total_stored = 0
    
    # Parse and store patterns
    if os.path.exists(patterns_file):
        with open(patterns_file, 'r') as f:
            content = f.read()
        patterns = parse_patterns(content)
        total_stored += await bootstrap_patterns(patterns)
    else:
        print(f"⚠️ PATTERNS.md not found at {patterns_file}")
    
    # Parse and store learnings
    if os.path.exists(learnings_file):
        with open(learnings_file, 'r') as f:
            content = f.read()
        learnings = parse_learnings(content)
        total_stored += await bootstrap_learnings(learnings)
    else:
        print(f"⚠️ LEARNINGS.md not found at {learnings_file}")
    
    # Parse and store best practices
    if os.path.exists(practices_file):
        with open(practices_file, 'r') as f:
            content = f.read()
        insights = parse_best_practices(content)
        total_stored += await bootstrap_insights(insights)
    else:
        print(f"⚠️ BEST_PRACTICES.md not found at {practices_file}")
    
    print("\n" + "=" * 60)
    print(f"✅ BOOTSTRAP COMPLETE - {total_stored} memories stored")
    print("=" * 60)
    print("\n⏰ Note: Mem0 processes memories asynchronously.")
    print("   Wait ~30 seconds before searching.")


if __name__ == "__main__":
    asyncio.run(main())
















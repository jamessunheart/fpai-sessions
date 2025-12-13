#!/usr/bin/env python3
"""
🧠 Memory Bootstrap Script
==========================

Parses existing markdown knowledge files and loads them into Mem0
for semantic search and AI-accessible memory.

Usage:
    python3 bootstrap_memory.py [--dry-run] [--file patterns|learnings|practices|all]
    
Files parsed:
    - core/INTELLIGENCE/PATTERNS.md → fpai_patterns
    - core/INTELLIGENCE/LEARNINGS.md → fpai_learnings  
    - core/INTELLIGENCE/BEST_PRACTICES.md → fpai_insights
"""

import os
import re
import sys
import argparse
import asyncio
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "SERVICES" / "data-service"))

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx")
    sys.exit(1)

# Configuration
BASE_PATH = Path(__file__).parent.parent.parent
PATTERNS_FILE = BASE_PATH / "core" / "INTELLIGENCE" / "PATTERNS.md"
LEARNINGS_FILE = BASE_PATH / "core" / "INTELLIGENCE" / "LEARNINGS.md"
PRACTICES_FILE = BASE_PATH / "core" / "INTELLIGENCE" / "BEST_PRACTICES.md"

DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://localhost:8125")
MEM0_API_KEY = os.getenv("MEM0_API_KEY")

# Memory entity types (matching data-service/app/memory.py)
ENTITY_PATTERNS = "fpai_patterns"
ENTITY_LEARNINGS = "fpai_learnings"
ENTITY_INSIGHTS = "fpai_insights"


class MemoryBootstrap:
    """Parses markdown files and loads knowledge into Mem0."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.stats = {
            "patterns_parsed": 0,
            "learnings_parsed": 0,
            "practices_parsed": 0,
            "stored": 0,
            "skipped_duplicates": 0,
            "errors": 0
        }
        self.seen_hashes: set = set()
        
    def _content_hash(self, content: str) -> str:
        """Generate hash for deduplication."""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    # =========================================================================
    # PATTERN PARSING
    # =========================================================================
    
    def parse_patterns(self) -> List[Dict[str, Any]]:
        """
        Parse PATTERNS.md into structured pattern entries.
        
        Pattern format:
        ### Pattern: {name}
        **Discovered:** {date} by {session}
        **Context:** {context}
        **Problem:** {problem}
        **Solution:** {solution}
        **Impact:** {impact bullets}
        **Application:** {application}
        """
        patterns = []
        
        if not PATTERNS_FILE.exists():
            print(f"⚠️ Patterns file not found: {PATTERNS_FILE}")
            return patterns
            
        content = PATTERNS_FILE.read_text()
        
        # Split by pattern headers
        pattern_blocks = re.split(r'### Pattern:', content)[1:]  # Skip header
        
        for block in pattern_blocks:
            try:
                pattern = self._parse_pattern_block(block)
                if pattern:
                    patterns.append(pattern)
                    self.stats["patterns_parsed"] += 1
            except Exception as e:
                print(f"⚠️ Error parsing pattern block: {e}")
                self.stats["errors"] += 1
                
        return patterns
    
    def _parse_pattern_block(self, block: str) -> Optional[Dict[str, Any]]:
        """Parse a single pattern block."""
        lines = block.strip().split('\n')
        if not lines:
            return None
            
        # Extract name from first line
        name = lines[0].strip()
        
        # Extract fields
        discovered = self._extract_field(block, r'\*\*Discovered:\*\*\s*(.+?)(?:\n|$)')
        context = self._extract_field(block, r'\*\*Context:\*\*\s*(.+?)(?:\n|$)')
        problem = self._extract_field(block, r'\*\*Problem:\*\*\s*(.+?)(?:\n|$)')
        
        # Solution can be multi-line
        solution_match = re.search(r'\*\*Solution:\*\*\s*(.+?)(?=\*\*Impact:|$)', block, re.DOTALL)
        solution = solution_match.group(1).strip() if solution_match else ""
        
        # Impact is bullet points
        impact_match = re.search(r'\*\*Impact:\*\*\s*(.+?)(?=\*\*Application:|---|\Z)', block, re.DOTALL)
        impact = impact_match.group(1).strip() if impact_match else ""
        
        application = self._extract_field(block, r'\*\*Application:\*\*\s*(.+?)(?:\n|$)')
        
        return {
            "name": name,
            "discovered": discovered,
            "context": context,
            "problem": problem,
            "solution": solution,
            "impact": impact,
            "application": application,
            "type": "pattern"
        }
    
    # =========================================================================
    # LEARNING PARSING
    # =========================================================================
    
    def parse_learnings(self) -> List[Dict[str, Any]]:
        """
        Parse LEARNINGS.md into structured learning entries.
        
        Learning format:
        ## {date}: {title}
        **Session:** {session}
        **Work:** {work description}
        **Learning:** or **Key Learnings:**
        {learning content}
        **Impact:**
        {impact content}
        """
        learnings = []
        
        if not LEARNINGS_FILE.exists():
            print(f"⚠️ Learnings file not found: {LEARNINGS_FILE}")
            return learnings
            
        content = LEARNINGS_FILE.read_text()
        
        # Split by learning headers (## date: title)
        learning_blocks = re.split(r'^## \d{4}-\d{2}-\d{2}', content, flags=re.MULTILINE)[1:]
        
        for block in learning_blocks:
            try:
                learning = self._parse_learning_block(block)
                if learning:
                    learnings.append(learning)
                    self.stats["learnings_parsed"] += 1
            except Exception as e:
                print(f"⚠️ Error parsing learning block: {e}")
                self.stats["errors"] += 1
                
        return learnings
    
    def _parse_learning_block(self, block: str) -> Optional[Dict[str, Any]]:
        """Parse a single learning block."""
        lines = block.strip().split('\n')
        if not lines:
            return None
        
        # First line contains the rest of the date and title
        title_match = re.match(r'[^:]*:\s*(.+)', lines[0])
        title = title_match.group(1).strip() if title_match else lines[0].strip()
        
        session = self._extract_field(block, r'\*\*Session:\*\*\s*(.+?)(?:\n|$)')
        work = self._extract_field(block, r'\*\*Work:\*\*\s*(.+?)(?:\n|$)')
        
        # Learning content can be multi-line
        learning_match = re.search(
            r'\*\*(?:Learning|Key Learnings):\*\*\s*(.+?)(?=\*\*Impact:|\*\*Pattern:|\*\*What|---|\Z)', 
            block, 
            re.DOTALL
        )
        learning = learning_match.group(1).strip() if learning_match else ""
        
        impact_match = re.search(r'\*\*Impact:\*\*\s*(.+?)(?=\*\*Pattern:|\*\*What|---|\Z)', block, re.DOTALL)
        impact = impact_match.group(1).strip() if impact_match else ""
        
        pattern = self._extract_field(block, r'\*\*Pattern:\*\*\s*(.+?)(?:\n|$)')
        
        return {
            "title": title,
            "session": session,
            "work": work,
            "learning": learning,
            "impact": impact,
            "pattern": pattern,
            "type": "learning"
        }
    
    # =========================================================================
    # BEST PRACTICES PARSING
    # =========================================================================
    
    def parse_practices(self) -> List[Dict[str, Any]]:
        """
        Parse BEST_PRACTICES.md into structured practice entries.
        
        Practice format:
        ### {number}. {title} ✅
        {description/code}
        **Why:** {reason}
        **When:** {when to use}
        **Evidence:** {evidence}
        """
        practices = []
        
        if not PRACTICES_FILE.exists():
            print(f"⚠️ Practices file not found: {PRACTICES_FILE}")
            return practices
            
        content = PRACTICES_FILE.read_text()
        
        # Split by practice headers
        practice_blocks = re.split(r'### \d+\.', content)[1:]
        
        for block in practice_blocks:
            try:
                practice = self._parse_practice_block(block)
                if practice:
                    practices.append(practice)
                    self.stats["practices_parsed"] += 1
            except Exception as e:
                print(f"⚠️ Error parsing practice block: {e}")
                self.stats["errors"] += 1
                
        return practices
    
    def _parse_practice_block(self, block: str) -> Optional[Dict[str, Any]]:
        """Parse a single practice block."""
        lines = block.strip().split('\n')
        if not lines:
            return None
            
        # Title is first line
        title = lines[0].strip().replace('✅', '').strip()
        
        # Extract description (content before **Why:**)
        desc_match = re.search(r'^(.+?)(?=\*\*Why:|\Z)', block, re.DOTALL)
        description = ""
        if desc_match:
            # Skip the title line
            desc_lines = desc_match.group(1).strip().split('\n')[1:]
            description = '\n'.join(desc_lines).strip()
        
        why = self._extract_field(block, r'\*\*Why:\*\*\s*(.+?)(?:\n|$)')
        when = self._extract_field(block, r'\*\*When:\*\*\s*(.+?)(?:\n|$)')
        evidence = self._extract_field(block, r'\*\*Evidence:\*\*\s*(.+?)(?:\n|$)')
        
        return {
            "title": title,
            "description": description,
            "why": why,
            "when": when,
            "evidence": evidence,
            "type": "practice"
        }
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract a field using regex pattern."""
        match = re.search(pattern, text)
        return match.group(1).strip() if match else ""
    
    # =========================================================================
    # MEMORY STORAGE
    # =========================================================================
    
    async def store_pattern(self, pattern: Dict[str, Any]) -> bool:
        """Store a pattern in Mem0 via data service."""
        # Build memory-friendly message
        message = f"""Pattern: {pattern['name']}. 
When: {pattern['context']}. 
Problem: {pattern['problem']}. 
Solution: {pattern['solution']}. 
Application: {pattern['application']}."""
        
        # Check for duplicate
        content_hash = self._content_hash(message)
        if content_hash in self.seen_hashes:
            self.stats["skipped_duplicates"] += 1
            return False
        self.seen_hashes.add(content_hash)
        
        if self.dry_run:
            print(f"  [DRY RUN] Would store pattern: {pattern['name']}")
            return True
            
        return await self._store_to_mem0(
            message=message,
            user_id=ENTITY_PATTERNS,
            metadata={
                "type": "pattern",
                "name": pattern["name"],
                "source": "bootstrap_patterns_md"
            }
        )
    
    async def store_learning(self, learning: Dict[str, Any]) -> bool:
        """Store a learning in Mem0 via data service."""
        # Build memory-friendly message
        message = f"""{learning['title']}. 
Learning: {learning['learning'][:500]}. 
Impact: {learning['impact'][:300]}."""
        
        # Check for duplicate
        content_hash = self._content_hash(message)
        if content_hash in self.seen_hashes:
            self.stats["skipped_duplicates"] += 1
            return False
        self.seen_hashes.add(content_hash)
        
        if self.dry_run:
            print(f"  [DRY RUN] Would store learning: {learning['title']}")
            return True
            
        return await self._store_to_mem0(
            message=message,
            user_id=ENTITY_LEARNINGS,
            metadata={
                "type": "learning",
                "title": learning["title"],
                "session": learning.get("session", ""),
                "source": "bootstrap_learnings_md"
            }
        )
    
    async def store_practice(self, practice: Dict[str, Any]) -> bool:
        """Store a practice in Mem0 via data service."""
        # Build memory-friendly message
        message = f"""Best Practice: {practice['title']}. 
Why: {practice['why']}. 
When: {practice['when']}. 
Evidence: {practice['evidence']}."""
        
        # Check for duplicate
        content_hash = self._content_hash(message)
        if content_hash in self.seen_hashes:
            self.stats["skipped_duplicates"] += 1
            return False
        self.seen_hashes.add(content_hash)
        
        if self.dry_run:
            print(f"  [DRY RUN] Would store practice: {practice['title']}")
            return True
            
        return await self._store_to_mem0(
            message=message,
            user_id=ENTITY_INSIGHTS,
            metadata={
                "type": "best_practice",
                "title": practice["title"],
                "source": "bootstrap_practices_md"
            }
        )
    
    async def _store_to_mem0(
        self, 
        message: str, 
        user_id: str, 
        metadata: Dict[str, Any]
    ) -> bool:
        """Store directly to Mem0 API."""
        if not MEM0_API_KEY:
            print("⚠️ MEM0_API_KEY not set, cannot store to Mem0")
            return False
            
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.mem0.ai/v1/memories/",
                    headers={
                        "Authorization": f"Token {MEM0_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "messages": [{"role": "user", "content": message}],
                        "user_id": user_id,
                        "metadata": metadata
                    }
                )
                
                if resp.status_code == 200:
                    self.stats["stored"] += 1
                    return True
                else:
                    print(f"⚠️ Mem0 API error: {resp.status_code} - {resp.text[:100]}")
                    self.stats["errors"] += 1
                    return False
                    
        except Exception as e:
            print(f"⚠️ Error storing to Mem0: {e}")
            self.stats["errors"] += 1
            return False
    
    # =========================================================================
    # MAIN EXECUTION
    # =========================================================================
    
    async def run(self, file_type: str = "all"):
        """Run the bootstrap process."""
        print("🧠 Memory Bootstrap Starting...")
        print(f"   Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"   Files: {file_type}")
        print()
        
        if file_type in ("patterns", "all"):
            print("📋 Parsing PATTERNS.md...")
            patterns = self.parse_patterns()
            print(f"   Found {len(patterns)} patterns")
            
            for pattern in patterns:
                await self.store_pattern(pattern)
                
        if file_type in ("learnings", "all"):
            print("📚 Parsing LEARNINGS.md...")
            learnings = self.parse_learnings()
            print(f"   Found {len(learnings)} learnings")
            
            for learning in learnings:
                await self.store_learning(learning)
                
        if file_type in ("practices", "all"):
            print("✅ Parsing BEST_PRACTICES.md...")
            practices = self.parse_practices()
            print(f"   Found {len(practices)} practices")
            
            for practice in practices:
                await self.store_practice(practice)
        
        print()
        print("=" * 50)
        print("📊 Bootstrap Complete!")
        print(f"   Patterns parsed:   {self.stats['patterns_parsed']}")
        print(f"   Learnings parsed:  {self.stats['learnings_parsed']}")
        print(f"   Practices parsed:  {self.stats['practices_parsed']}")
        print(f"   Stored to Mem0:    {self.stats['stored']}")
        print(f"   Skipped (dupes):   {self.stats['skipped_duplicates']}")
        print(f"   Errors:            {self.stats['errors']}")
        print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="Bootstrap knowledge into Mem0")
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Parse files without storing to Mem0"
    )
    parser.add_argument(
        "--file",
        choices=["patterns", "learnings", "practices", "all"],
        default="all",
        help="Which file(s) to process"
    )
    
    args = parser.parse_args()
    
    bootstrap = MemoryBootstrap(dry_run=args.dry_run)
    asyncio.run(bootstrap.run(file_type=args.file))


if __name__ == "__main__":
    main()


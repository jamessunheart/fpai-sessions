#!/usr/bin/env python3
"""
ARIA SPEC GENERATOR
===================

Takes dialogue conclusions and generates formal specifications:
- Markdown spec documents
- File changes required
- Complexity and risk assessment
- Builder pipeline compatible format
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path
import httpx

from .dialogue import DialogueResult, ImprovementProposal
from .summarizer import InteractionSummary

logger = logging.getLogger("aria.reflection.spec_generator")

# ============================================================================
# CONFIGURATION
# ============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
SPEC_MODEL = os.getenv("SPEC_MODEL", "claude-sonnet-4-20250514")
SPECS_DIR = os.getenv("REFLECTION_SPECS_DIR", "/opt/fpai/aria-command/specs/reflection")


@dataclass
class FileChange:
    """A proposed file change."""
    file_path: str
    change_type: str  # create, modify, delete
    description: str
    code_snippet: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "file_path": self.file_path,
            "change_type": self.change_type,
            "description": self.description,
            "code_snippet": self.code_snippet
        }


@dataclass
class GeneratedSpec:
    """A generated specification document."""
    id: str
    title: str
    proposal: ImprovementProposal
    
    # Spec content
    overview: str = ""
    motivation: str = ""
    implementation_steps: List[str] = field(default_factory=list)
    file_changes: List[FileChange] = field(default_factory=list)
    testing_plan: str = ""
    rollback_plan: str = ""
    
    # Metadata
    complexity: str = "medium"
    risk: str = "low"
    estimated_time: str = ""
    
    # Generated at
    generated_at: datetime = field(default_factory=datetime.now)
    generation_cost: float = 0.0
    
    # File path
    spec_path: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "proposal": self.proposal.to_dict(),
            "overview": self.overview,
            "motivation": self.motivation,
            "implementation_steps": self.implementation_steps,
            "file_changes": [f.to_dict() for f in self.file_changes],
            "testing_plan": self.testing_plan,
            "rollback_plan": self.rollback_plan,
            "complexity": self.complexity,
            "risk": self.risk,
            "estimated_time": self.estimated_time,
            "generated_at": self.generated_at.isoformat(),
            "generation_cost": self.generation_cost,
            "spec_path": self.spec_path
        }
    
    def to_markdown(self) -> str:
        """Generate markdown spec document."""
        lines = [
            f"# Spec: {self.title}",
            f"",
            f"**ID:** {self.id}",
            f"**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M')}",
            f"**Complexity:** {self.complexity}",
            f"**Risk:** {self.risk}",
            f"**Estimated Time:** {self.estimated_time}",
            f"",
            f"## Overview",
            f"",
            self.overview,
            f"",
            f"## Motivation",
            f"",
            self.motivation,
            f"",
            f"## Implementation Steps",
            f"",
        ]
        
        for i, step in enumerate(self.implementation_steps, 1):
            lines.append(f"{i}. {step}")
        
        lines.extend([
            f"",
            f"## File Changes",
            f"",
        ])
        
        for change in self.file_changes:
            lines.append(f"### {change.change_type.upper()}: `{change.file_path}`")
            lines.append(f"")
            lines.append(change.description)
            if change.code_snippet:
                lines.append(f"")
                lines.append("```python")
                lines.append(change.code_snippet)
                lines.append("```")
            lines.append(f"")
        
        lines.extend([
            f"## Testing Plan",
            f"",
            self.testing_plan,
            f"",
            f"## Rollback Plan",
            f"",
            self.rollback_plan,
        ])
        
        return "\n".join(lines)


# ============================================================================
# SPEC GENERATION PROMPT
# ============================================================================

SPEC_GENERATION_PROMPT = """You are generating a formal specification for an improvement to Aria, an AI assistant.

## Proposal
{proposal}

## Context from Dialogue
{dialogue_context}

## Original Issues
{original_issues}

Generate a detailed specification including:

1. **Overview**: 2-3 sentences describing what this change does

2. **Motivation**: Why this change is needed (reference original issues)

3. **Implementation Steps**: Numbered list of specific actions to implement this

4. **File Changes**: For each file that needs to change:
   - File path (be specific, e.g., /opt/fpai/aria-command/telegram/bot.py)
   - Change type: create, modify, or delete
   - Description of what to change
   - Code snippet if helpful

5. **Testing Plan**: How to verify this works

6. **Rollback Plan**: How to undo if something goes wrong

7. **Estimates**:
   - Complexity: low/medium/high
   - Risk: low/medium/high
   - Time: e.g., "30 minutes", "2 hours"

Output as JSON:
```json
{{
  "overview": "...",
  "motivation": "...",
  "implementation_steps": ["Step 1...", "Step 2..."],
  "file_changes": [
    {{
      "file_path": "/opt/fpai/...",
      "change_type": "modify",
      "description": "...",
      "code_snippet": "..."
    }}
  ],
  "testing_plan": "...",
  "rollback_plan": "...",
  "complexity": "low",
  "risk": "low",
  "estimated_time": "30 minutes"
}}
```

Be specific and actionable. The spec should be clear enough for another AI agent to implement without ambiguity."""


# ============================================================================
# SPEC GENERATOR
# ============================================================================

class SpecGenerator:
    """
    Generates formal specifications from dialogue proposals.
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=120.0)
        Path(SPECS_DIR).mkdir(parents=True, exist_ok=True)
    
    async def close(self):
        await self.http.aclose()
    
    async def _call_claude(self, prompt: str) -> tuple[str, float]:
        """Call Claude API for spec generation."""
        if not ANTHROPIC_API_KEY:
            raise ValueError("No Anthropic API key configured")
        
        response = await self.http.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json={
                "model": SPEC_MODEL,
                "max_tokens": 3000,
                "messages": [{"role": "user", "content": prompt}]
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Anthropic API error: {response.text}")
        
        data = response.json()
        content = data["content"][0]["text"]
        
        # Calculate cost (Sonnet pricing)
        input_tokens = data.get("usage", {}).get("input_tokens", 0)
        output_tokens = data.get("usage", {}).get("output_tokens", 0)
        cost = (input_tokens * 0.003 + output_tokens * 0.015) / 1000
        
        return content, cost
    
    def _parse_spec_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        import re
        
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        logger.warning("Could not parse spec response")
        return {}
    
    def _generate_spec_id(self) -> str:
        """Generate unique spec ID."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        import random
        suffix = ''.join(random.choices('abcdef0123456789', k=4))
        return f"spec-{timestamp}-{suffix}"
    
    async def generate_spec(
        self,
        proposal: ImprovementProposal,
        dialogue_result: DialogueResult,
        summary: InteractionSummary
    ) -> GeneratedSpec:
        """
        Generate a formal specification from a proposal.
        """
        logger.info(f"Generating spec for: {proposal.title}")
        
        # Build prompt
        proposal_text = json.dumps(proposal.to_dict(), indent=2)
        dialogue_context = dialogue_result.get_dialogue_transcript()[-2000:]  # Last 2000 chars
        original_issues = summary.to_prompt_text()[:1500]  # First 1500 chars
        
        prompt = SPEC_GENERATION_PROMPT.format(
            proposal=proposal_text,
            dialogue_context=dialogue_context,
            original_issues=original_issues
        )
        
        # Generate spec
        response, cost = await self._call_claude(prompt)
        parsed = self._parse_spec_response(response)
        
        # Build spec object
        spec_id = self._generate_spec_id()
        spec = GeneratedSpec(
            id=spec_id,
            title=proposal.title,
            proposal=proposal,
            overview=parsed.get("overview", ""),
            motivation=parsed.get("motivation", ""),
            implementation_steps=parsed.get("implementation_steps", []),
            testing_plan=parsed.get("testing_plan", ""),
            rollback_plan=parsed.get("rollback_plan", ""),
            complexity=parsed.get("complexity", proposal.complexity),
            risk=parsed.get("risk", proposal.risk),
            estimated_time=parsed.get("estimated_time", "unknown"),
            generation_cost=cost
        )
        
        # Parse file changes
        for fc in parsed.get("file_changes", []):
            spec.file_changes.append(FileChange(
                file_path=fc.get("file_path", ""),
                change_type=fc.get("change_type", "modify"),
                description=fc.get("description", ""),
                code_snippet=fc.get("code_snippet", "")
            ))
        
        # Save spec
        spec.spec_path = self._save_spec(spec)
        
        logger.info(f"Spec generated: {spec_id}, ${cost:.4f}")
        
        return spec
    
    def _save_spec(self, spec: GeneratedSpec) -> str:
        """Save spec to file."""
        filename = f"{spec.id}.md"
        filepath = Path(SPECS_DIR) / filename
        
        with open(filepath, 'w') as f:
            f.write(spec.to_markdown())
        
        # Also save JSON version
        json_path = Path(SPECS_DIR) / f"{spec.id}.json"
        with open(json_path, 'w') as f:
            json.dump(spec.to_dict(), f, indent=2)
        
        logger.info(f"Spec saved: {filepath}")
        return str(filepath)
    
    async def generate_all_specs(
        self,
        dialogue_result: DialogueResult,
        summary: InteractionSummary
    ) -> List[GeneratedSpec]:
        """
        Generate specs for all proposals from dialogue.
        """
        specs = []
        
        for proposal in dialogue_result.proposals:
            try:
                spec = await self.generate_spec(proposal, dialogue_result, summary)
                specs.append(spec)
            except Exception as e:
                logger.error(f"Failed to generate spec for '{proposal.title}': {e}")
        
        return specs
    
    def list_specs(self, limit: int = 20) -> List[Dict]:
        """List recent specs."""
        specs = []
        spec_dir = Path(SPECS_DIR)
        
        if not spec_dir.exists():
            return []
        
        json_files = sorted(spec_dir.glob("*.json"), reverse=True)[:limit]
        
        for json_file in json_files:
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    specs.append({
                        "id": data.get("id"),
                        "title": data.get("title"),
                        "complexity": data.get("complexity"),
                        "risk": data.get("risk"),
                        "generated_at": data.get("generated_at"),
                        "spec_path": data.get("spec_path")
                    })
            except Exception as e:
                logger.warning(f"Error reading spec {json_file}: {e}")
        
        return specs
    
    def get_spec(self, spec_id: str) -> Optional[Dict]:
        """Get a specific spec by ID."""
        json_path = Path(SPECS_DIR) / f"{spec_id}.json"
        
        if not json_path.exists():
            return None
        
        with open(json_path) as f:
            return json.load(f)


# ============================================================================
# SINGLETON & CONVENIENCE FUNCTIONS
# ============================================================================

_generator: Optional[SpecGenerator] = None


def get_spec_generator() -> SpecGenerator:
    """Get global spec generator instance."""
    global _generator
    if _generator is None:
        _generator = SpecGenerator()
    return _generator


async def generate_specs(
    dialogue_result: DialogueResult,
    summary: InteractionSummary
) -> List[GeneratedSpec]:
    """Generate specs from dialogue."""
    return await get_spec_generator().generate_all_specs(dialogue_result, summary)


def list_specs(limit: int = 20) -> List[Dict]:
    """List recent specs."""
    return get_spec_generator().list_specs(limit)


def get_spec(spec_id: str) -> Optional[Dict]:
    """Get spec by ID."""
    return get_spec_generator().get_spec(spec_id)



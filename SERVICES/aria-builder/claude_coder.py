#!/usr/bin/env python3
"""
ARIA CLAUDE CODER
=================

Uses Claude to generate accurate code modifications.

Claude is the best model for:
- Understanding existing code context
- Generating accurate diffs
- Complex multi-file reasoning
"""

import os
import json
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
import httpx

logger = logging.getLogger("aria.claude_coder")

# ============================================================================
# CONFIGURATION
# ============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"
CLAUDE_URL = "https://api.anthropic.com/v1/messages"

# System prompt for code generation
CODE_GEN_SYSTEM = """You are Aria's code generation engine. You generate precise, accurate code modifications.

RULES:
1. Always provide code in diff format showing exact changes
2. Include enough context (3-5 lines before/after) to locate the change
3. Use Python best practices
4. Add docstrings and type hints
5. Keep changes minimal - only what's requested
6. If the change is risky, explain why

OUTPUT FORMAT:
Return a JSON object with:
{
    "explanation": "Brief explanation of the change",
    "risk_level": "low|medium|high",
    "changes": [
        {
            "file": "path/to/file.py",
            "action": "add|modify|delete",
            "location": "description of where in file",
            "old_code": "existing code to replace (null for add)",
            "new_code": "new code to insert",
            "line_hint": "approximate line number or function name"
        }
    ],
    "test_suggestion": "how to test this change"
}

Be precise. Be minimal. Be safe."""


@dataclass
class CodeChange:
    """A single code change."""
    file: str
    action: str  # add, modify, delete
    location: str
    old_code: Optional[str]
    new_code: str
    line_hint: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CodeProposal:
    """A proposed code modification."""
    explanation: str
    risk_level: str
    changes: List[CodeChange]
    test_suggestion: str
    raw_response: str = ""
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "explanation": self.explanation,
            "risk_level": self.risk_level,
            "changes": [c.to_dict() for c in self.changes],
            "test_suggestion": self.test_suggestion,
            "success": self.success,
            "error": self.error
        }
    
    def format_for_telegram(self) -> str:
        """Format proposal for Telegram display."""
        lines = [f"**{self.explanation}**\n"]
        lines.append(f"Risk: `{self.risk_level.upper()}`\n")
        
        for i, change in enumerate(self.changes, 1):
            lines.append(f"\n**Change {i}:** `{change.file}`")
            lines.append(f"Action: {change.action}")
            
            if change.old_code:
                # Show abbreviated old code
                old_lines = change.old_code.strip().split('\n')
                if len(old_lines) > 5:
                    old_preview = '\n'.join(old_lines[:3]) + '\n... (truncated)'
                else:
                    old_preview = change.old_code.strip()
                lines.append(f"```\n- {old_preview}\n```")
            
            # Show new code
            new_lines = change.new_code.strip().split('\n')
            if len(new_lines) > 10:
                new_preview = '\n'.join(new_lines[:8]) + '\n... (truncated)'
            else:
                new_preview = change.new_code.strip()
            lines.append(f"```python\n+ {new_preview}\n```")
        
        if self.test_suggestion:
            lines.append(f"\n**Test:** {self.test_suggestion}")
        
        return '\n'.join(lines)


class ClaudeCoder:
    """
    Uses Claude to generate code modifications.
    
    This is the brain for understanding code requests
    and generating accurate, safe changes.
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=120.0)
        self.available = bool(ANTHROPIC_API_KEY)
        
        if not self.available:
            logger.warning("Claude API key not configured")
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    async def generate_change(
        self,
        request: str,
        file_context: Dict[str, str],
        constraints: Optional[List[str]] = None
    ) -> CodeProposal:
        """
        Generate code changes based on a natural language request.
        
        Args:
            request: What the user wants to do
            file_context: Dict of filename -> file content for context
            constraints: Optional list of constraints (e.g., "max 50 lines")
        
        Returns:
            CodeProposal with the suggested changes
        """
        if not self.available:
            return CodeProposal(
                explanation="",
                risk_level="high",
                changes=[],
                test_suggestion="",
                success=False,
                error="Claude API key not configured"
            )
        
        # Build the prompt
        prompt = self._build_prompt(request, file_context, constraints)
        
        try:
            response = await self._call_claude(prompt)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"Claude generation failed: {e}")
            return CodeProposal(
                explanation="",
                risk_level="high",
                changes=[],
                test_suggestion="",
                success=False,
                error=str(e)
            )
    
    async def review_code(
        self,
        code: str,
        purpose: str
    ) -> Dict[str, any]:
        """
        Review code for correctness and safety.
        
        Returns dict with:
        - is_safe: bool
        - issues: list of issues found
        - suggestions: list of improvements
        """
        if not self.available:
            return {"is_safe": True, "issues": [], "suggestions": [], "error": "No API key"}
        
        prompt = f"""Review this code for safety and correctness.

Purpose: {purpose}

Code:
```python
{code}
```

Return JSON:
{{
    "is_safe": true/false,
    "issues": ["list of issues"],
    "suggestions": ["list of improvements"],
    "overall_assessment": "brief summary"
}}"""
        
        try:
            response = await self._call_claude(prompt)
            return json.loads(response)
        except Exception as e:
            logger.error(f"Code review failed: {e}")
            return {"is_safe": True, "issues": [], "suggestions": [], "error": str(e)}
    
    async def explain_code(
        self,
        code: str,
        question: Optional[str] = None
    ) -> str:
        """Explain what code does."""
        if not self.available:
            return "Claude API not available"
        
        prompt = f"""Explain this code briefly:

```python
{code}
```

{f'Specific question: {question}' if question else 'What does this code do?'}

Be concise (3-5 sentences max)."""
        
        try:
            return await self._call_claude(prompt)
        except Exception as e:
            return f"Error: {e}"
    
    def _build_prompt(
        self,
        request: str,
        file_context: Dict[str, str],
        constraints: Optional[List[str]] = None
    ) -> str:
        """Build the prompt for code generation."""
        parts = [f"USER REQUEST:\n{request}\n"]
        
        # Add file context
        if file_context:
            parts.append("EXISTING CODE CONTEXT:")
            for filename, content in file_context.items():
                # Truncate very long files
                if len(content) > 5000:
                    content = content[:5000] + "\n... (truncated)"
                parts.append(f"\n--- {filename} ---\n```python\n{content}\n```")
        
        # Add constraints
        if constraints:
            parts.append(f"\nCONSTRAINTS:\n" + "\n".join(f"- {c}" for c in constraints))
        
        parts.append("\nGenerate the code changes as specified in your instructions.")
        
        return "\n".join(parts)
    
    async def _call_claude(self, prompt: str) -> str:
        """Make API call to Claude."""
        response = await self.http.post(
            CLAUDE_URL,
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json={
                "model": CLAUDE_MODEL,
                "max_tokens": 4096,
                "system": CODE_GEN_SYSTEM,
                "messages": [{"role": "user", "content": prompt}]
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Claude API error {response.status_code}: {response.text[:200]}")
        
        data = response.json()
        return data["content"][0]["text"]
    
    def _parse_response(self, response: str) -> CodeProposal:
        """Parse Claude's response into a CodeProposal."""
        try:
            # Try to extract JSON from response
            # Claude might wrap it in markdown code blocks
            json_str = response
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            
            data = json.loads(json_str)
            
            changes = [
                CodeChange(
                    file=c.get("file", "unknown"),
                    action=c.get("action", "modify"),
                    location=c.get("location", ""),
                    old_code=c.get("old_code"),
                    new_code=c.get("new_code", ""),
                    line_hint=c.get("line_hint", "")
                )
                for c in data.get("changes", [])
            ]
            
            return CodeProposal(
                explanation=data.get("explanation", ""),
                risk_level=data.get("risk_level", "medium"),
                changes=changes,
                test_suggestion=data.get("test_suggestion", ""),
                raw_response=response,
                success=True
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            # Return the raw response as explanation
            return CodeProposal(
                explanation=response[:500],
                risk_level="medium",
                changes=[],
                test_suggestion="",
                raw_response=response,
                success=True,
                error="Could not parse structured response"
            )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_coder: Optional[ClaudeCoder] = None


def get_coder() -> ClaudeCoder:
    """Get or create the global coder instance."""
    global _coder
    if _coder is None:
        _coder = ClaudeCoder()
    return _coder


async def generate_code_change(
    request: str,
    context: Dict[str, str],
    constraints: Optional[List[str]] = None
) -> CodeProposal:
    """Generate code changes from a request."""
    coder = get_coder()
    return await coder.generate_change(request, context, constraints)


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        coder = get_coder()
        
        print(f"Claude available: {coder.available}")
        
        if coder.available:
            # Test code generation
            print("\n--- Testing Code Generation ---")
            
            context = {
                "server.py": """
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/status")
def status():
    return {"service": "aria"}
"""
            }
            
            proposal = await coder.generate_change(
                "Add a /memory endpoint that returns a list of stored facts",
                context,
                ["Keep it simple", "Max 20 lines"]
            )
            
            print(f"Success: {proposal.success}")
            print(f"Explanation: {proposal.explanation}")
            print(f"Risk: {proposal.risk_level}")
            print(f"Changes: {len(proposal.changes)}")
            
            if proposal.changes:
                for c in proposal.changes:
                    print(f"  - {c.action} in {c.file}")
                    print(f"    New code: {c.new_code[:100]}...")
        
        await coder.close()
    
    asyncio.run(test())



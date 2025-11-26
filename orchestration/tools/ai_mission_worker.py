#!/usr/bin/env python3
"""
AI Mission Worker
==================
Attempts to complete missions autonomously using multiple AI models.
Logs all AI-to-AI communication for transparency and human review.

Flow:
1. Load mission spec
2. AI analyzes what needs to be done
3. AI attempts to complete (code generation, file edits, etc.)
4. AI verifies its own work
5. If successful → Submit for human approval
6. If stuck → Escalate to human with detailed log

Supported Models:
- Claude (Anthropic) - Primary for complex reasoning
- GPT-4 (OpenAI) - Secondary, good for code
- Gemini (Google) - Tertiary, good for research

Usage:
    python ai_mission_worker.py <mission_id> [--dry-run] [--model claude|gpt4|gemini]
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parents[1]
MISSIONS_DIR = ROOT_DIR / "fullpotential_ai" / "fullpotential_core" / "orchestration" / "missions"
LOGS_DIR = MISSIONS_DIR / "ai_logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Load environment
from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")


class AIModel(Enum):
    # Claude - latest Sonnet for complex reasoning
    CLAUDE = "claude-sonnet-4-20250514"
    CLAUDE_HAIKU = "claude-3-5-haiku-20241022"
    # OpenAI - latest models
    GPT4 = "gpt-4-turbo"
    GPT4O = "gpt-4o"
    O1 = "o1-preview"  # For complex reasoning
    # Gemini - latest models  
    GEMINI = "gemini-2.0-flash-exp"
    GEMINI_PRO = "gemini-pro"


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_HUMAN = "needs_human"


@dataclass
class AIMessage:
    """A single message in the AI conversation log"""
    timestamp: str
    role: str  # "system", "planner", "executor", "verifier", "human"
    model: str
    content: str
    tokens_used: int = 0
    cost_usd: float = 0.0


@dataclass
class MissionAttempt:
    """Record of an AI attempt to complete a mission"""
    mission_id: str
    started_at: str
    status: str = "in_progress"
    messages: List[Dict] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    completed_at: str = None
    result: str = None
    human_notes: str = None


class AIClient:
    """Unified client for multiple AI providers"""
    
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self.gemini_model = None
        
        # Initialize available clients
        if OPENAI_API_KEY:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
                print("✅ OpenAI client initialized")
            except Exception as e:
                print(f"⚠️ OpenAI not available: {e}")
        
        if ANTHROPIC_API_KEY:
            try:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                print("✅ Anthropic client initialized")
            except Exception as e:
                print(f"⚠️ Anthropic not available: {e}")
        
        if GOOGLE_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=GOOGLE_API_KEY)
                # Use gemini-2.0-flash (latest) or fallback to gemini-pro
                try:
                    self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
                    print("✅ Gemini client initialized (gemini-2.0-flash-exp)")
                except:
                    try:
                        self.gemini_model = genai.GenerativeModel('gemini-pro')
                        print("✅ Gemini client initialized (gemini-pro)")
                    except:
                        self.gemini_model = genai.GenerativeModel('models/gemini-pro')
                        print("✅ Gemini client initialized (models/gemini-pro)")
            except Exception as e:
                print(f"⚠️ Gemini not available: {e}")
    
    def available_models(self) -> List[str]:
        """Return list of available models"""
        models = []
        if self.anthropic_client:
            models.extend(["claude", "claude-haiku"])
        if self.openai_client:
            models.extend(["gpt4", "gpt4o"])
        if self.gemini_model:
            models.extend(["gemini", "gemini-flash"])
        return models
    
    async def chat(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4000
    ) -> Tuple[str, int, float]:
        """
        Send a chat request to the specified model.
        Returns: (response_text, tokens_used, cost_usd)
        """
        if model.startswith("claude"):
            return await self._chat_claude(model, system_prompt, user_prompt, max_tokens)
        elif model.startswith("gpt"):
            return await self._chat_openai(model, system_prompt, user_prompt, max_tokens)
        elif model.startswith("gemini"):
            return await self._chat_gemini(model, system_prompt, user_prompt, max_tokens)
        else:
            raise ValueError(f"Unknown model: {model}")
    
    async def _chat_claude(self, model: str, system: str, user: str, max_tokens: int) -> Tuple[str, int, float]:
        """Chat with Claude"""
        if not self.anthropic_client:
            raise ValueError("Anthropic client not available")
        
        model_id = AIModel.CLAUDE.value if model == "claude" else AIModel.CLAUDE_HAIKU.value
        
        response = self.anthropic_client.messages.create(
            model=model_id,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}]
        )
        
        tokens = response.usage.input_tokens + response.usage.output_tokens
        # Claude pricing: ~$3/1M input, ~$15/1M output for Sonnet
        cost = (response.usage.input_tokens * 0.003 + response.usage.output_tokens * 0.015) / 1000
        
        return response.content[0].text, tokens, cost
    
    async def _chat_openai(self, model: str, system: str, user: str, max_tokens: int) -> Tuple[str, int, float]:
        """Chat with OpenAI"""
        if not self.openai_client:
            raise ValueError("OpenAI client not available")
        
        model_id = AIModel.GPT4O.value if model == "gpt4o" else AIModel.GPT4.value
        
        response = self.openai_client.chat.completions.create(
            model=model_id,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        )
        
        tokens = response.usage.total_tokens
        # GPT-4 pricing: ~$10/1M input, ~$30/1M output
        cost = tokens * 0.02 / 1000  # Simplified
        
        return response.choices[0].message.content, tokens, cost
    
    async def _chat_gemini(self, model: str, system: str, user: str, max_tokens: int) -> Tuple[str, int, float]:
        """Chat with Gemini"""
        if not self.gemini_model:
            raise ValueError("Gemini client not available")
        
        # Gemini combines system + user
        full_prompt = f"{system}\n\n---\n\n{user}"
        
        response = self.gemini_model.generate_content(full_prompt)
        
        # Gemini doesn't expose token counts easily, estimate
        tokens = len(full_prompt.split()) + len(response.text.split())
        cost = tokens * 0.001 / 1000  # Gemini is cheaper
        
        return response.text, tokens, cost


class AIMissionWorker:
    """
    Orchestrates multiple AI agents to complete a mission.
    
    Agents:
    - Planner: Analyzes mission and creates execution plan
    - Executor: Implements the plan (writes code, edits files)
    - Verifier: Checks if the work is correct
    - Coordinator: Manages handoffs and escalations
    """
    
    def __init__(self, mission_id: str, preferred_model: str = "claude"):
        self.mission_id = mission_id
        self.preferred_model = preferred_model
        self.client = AIClient()
        self.attempt = MissionAttempt(
            mission_id=mission_id,
            started_at=datetime.now().isoformat()
        )
        self.dry_run = False
    
    def log_message(self, role: str, model: str, content: str, tokens: int = 0, cost: float = 0.0):
        """Log a message in the conversation"""
        msg = AIMessage(
            timestamp=datetime.now().isoformat(),
            role=role,
            model=model,
            content=content,
            tokens_used=tokens,
            cost_usd=cost
        )
        self.attempt.messages.append(asdict(msg))
        self.attempt.total_tokens += tokens
        self.attempt.total_cost_usd += cost
        
        # Print to console
        print(f"\n{'='*60}")
        print(f"[{role.upper()}] ({model}) - {tokens} tokens, ${cost:.4f}")
        print(f"{'='*60}")
        print(content[:500] + "..." if len(content) > 500 else content)
    
    def load_mission_spec(self) -> Optional[str]:
        """Load the mission spec from specs/ or open/"""
        for folder in ["specs", "open"]:
            for f in (MISSIONS_DIR / folder).glob(f"{self.mission_id}*.md"):
                return f.read_text()
        return None
    
    def save_attempt_log(self):
        """Save the attempt log to ai_logs/"""
        log_file = LOGS_DIR / f"{self.mission_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, 'w') as f:
            json.dump(asdict(self.attempt), f, indent=2)
        print(f"\n📝 Attempt log saved: {log_file}")
        return log_file
    
    async def run(self, dry_run: bool = False) -> bool:
        """
        Execute the mission attempt.
        Returns True if successful, False if needs human intervention.
        """
        self.dry_run = dry_run
        
        print(f"\n🤖 AI Mission Worker starting: {self.mission_id}")
        print(f"   Model: {self.preferred_model}")
        print(f"   Dry run: {dry_run}")
        print(f"   Available models: {self.client.available_models()}")
        
        # Load mission spec
        spec = self.load_mission_spec()
        if not spec:
            print(f"❌ Mission spec not found for {self.mission_id}")
            self.attempt.status = TaskStatus.FAILED.value
            self.attempt.result = "Mission spec not found"
            self.save_attempt_log()
            return False
        
        self.log_message("system", "worker", f"Loaded mission spec ({len(spec)} chars)")
        
        try:
            # Phase 1: Planning
            plan = await self._phase_planning(spec)
            if not plan:
                return False
            
            # Phase 2: Execution
            execution_result = await self._phase_execution(spec, plan)
            if not execution_result:
                return False
            
            # Phase 3: Verification
            verified = await self._phase_verification(spec, execution_result)
            
            if verified:
                self.attempt.status = TaskStatus.COMPLETED.value
                self.attempt.result = "Mission completed by AI"
                print("\n✅ Mission completed successfully!")
            else:
                self.attempt.status = TaskStatus.NEEDS_HUMAN.value
                self.attempt.result = "AI completed work but verification uncertain - needs human review"
                print("\n⚠️ Work completed but needs human verification")
            
        except Exception as e:
            self.attempt.status = TaskStatus.FAILED.value
            self.attempt.result = f"Error: {str(e)}"
            print(f"\n❌ Mission failed: {e}")
        
        self.attempt.completed_at = datetime.now().isoformat()
        self.save_attempt_log()
        
        return self.attempt.status == TaskStatus.COMPLETED.value
    
    async def _phase_planning(self, spec: str) -> Optional[str]:
        """Phase 1: Analyze mission and create execution plan"""
        print("\n📋 Phase 1: Planning...")
        
        system_prompt = """You are an AI Mission Planner. Your job is to analyze a mission specification 
and create a detailed execution plan that another AI can follow.

Output a JSON plan with:
{
    "mission_summary": "One sentence summary",
    "can_ai_complete": true/false,
    "confidence": 0.0-1.0,
    "blockers": ["list of things that would require human intervention"],
    "steps": [
        {
            "step_number": 1,
            "action": "what to do",
            "type": "code_write|file_edit|command|research|human_required",
            "details": "specific details",
            "files_involved": ["list of files"],
            "estimated_minutes": 5
        }
    ],
    "total_estimated_minutes": 30
}

Be realistic about what AI can and cannot do. If the mission requires:
- Physical actions → human_required
- Account access/credentials → human_required  
- Subjective decisions → human_required
- External API calls without keys → human_required

But AI CAN:
- Write/modify code
- Create documentation
- Analyze codebases
- Generate tests
- Refactor code
- Create configurations
"""
        
        user_prompt = f"""Analyze this mission specification and create an execution plan:

---
{spec}
---

Remember: Output ONLY valid JSON, no markdown code blocks."""
        
        try:
            response, tokens, cost = await self.client.chat(
                self.preferred_model,
                system_prompt,
                user_prompt,
                max_tokens=2000
            )
            
            self.log_message("planner", self.preferred_model, response, tokens, cost)
            
            # Parse the plan
            plan = json.loads(response.strip().replace("```json", "").replace("```", ""))
            
            if not plan.get("can_ai_complete", False):
                print(f"\n⚠️ AI cannot complete this mission autonomously")
                print(f"   Blockers: {plan.get('blockers', [])}")
                self.attempt.status = TaskStatus.NEEDS_HUMAN.value
                self.attempt.result = f"Requires human: {', '.join(plan.get('blockers', []))}"
                return None
            
            print(f"\n✅ Plan created: {len(plan.get('steps', []))} steps, ~{plan.get('total_estimated_minutes', '?')} minutes")
            return json.dumps(plan)
            
        except Exception as e:
            self.log_message("planner", self.preferred_model, f"Error: {str(e)}", 0, 0)
            return None
    
    async def _phase_execution(self, spec: str, plan: str) -> Optional[str]:
        """Phase 2: Execute the plan"""
        print("\n⚡ Phase 2: Execution...")
        
        if self.dry_run:
            self.log_message("executor", "dry-run", "DRY RUN: Would execute plan here", 0, 0)
            return "DRY RUN - no actual execution"
        
        system_prompt = """You are an AI Mission Executor. You receive a mission spec and execution plan.
Your job is to actually implement the plan by generating code, configurations, or documentation.

For each step, output:
{
    "step_number": 1,
    "status": "completed|failed|skipped",
    "action_taken": "what you did",
    "output": "the actual code/content generated",
    "files_affected": ["list of files"],
    "notes": "any important notes"
}

Output a JSON array of all step results.

IMPORTANT:
- Generate COMPLETE, working code - not pseudocode
- Follow existing code patterns in the codebase
- Include all necessary imports
- Add helpful comments
- Handle errors appropriately
"""
        
        user_prompt = f"""Execute this mission plan:

MISSION SPEC:
{spec}

EXECUTION PLAN:
{plan}

Execute each step and provide the results as a JSON array."""
        
        try:
            response, tokens, cost = await self.client.chat(
                self.preferred_model,
                system_prompt,
                user_prompt,
                max_tokens=4000
            )
            
            self.log_message("executor", self.preferred_model, response, tokens, cost)
            return response
            
        except Exception as e:
            self.log_message("executor", self.preferred_model, f"Error: {str(e)}", 0, 0)
            return None
    
    async def _phase_verification(self, spec: str, execution_result: str) -> bool:
        """Phase 3: Verify the work"""
        print("\n✅ Phase 3: Verification...")
        
        system_prompt = """You are an AI Mission Verifier. Your job is to review work done by another AI
and determine if it successfully completes the mission.

Output JSON:
{
    "verified": true/false,
    "confidence": 0.0-1.0,
    "issues_found": ["list of any issues"],
    "suggestions": ["list of improvements"],
    "ready_for_human_review": true/false,
    "summary": "one paragraph summary of verification"
}

Be critical but fair. Check for:
- Does the work match the mission requirements?
- Is the code syntactically correct?
- Are there obvious bugs or issues?
- Is documentation adequate?
"""
        
        user_prompt = f"""Verify this mission execution:

ORIGINAL SPEC:
{spec}

EXECUTION RESULT:
{execution_result}

Verify and provide your assessment as JSON."""
        
        try:
            response, tokens, cost = await self.client.chat(
                self.preferred_model,
                system_prompt,
                user_prompt,
                max_tokens=1500
            )
            
            self.log_message("verifier", self.preferred_model, response, tokens, cost)
            
            result = json.loads(response.strip().replace("```json", "").replace("```", ""))
            return result.get("verified", False) and result.get("confidence", 0) > 0.7
            
        except Exception as e:
            self.log_message("verifier", self.preferred_model, f"Error: {str(e)}", 0, 0)
            return False


async def main():
    parser = argparse.ArgumentParser(description="AI Mission Worker")
    parser.add_argument("mission_id", help="Mission ID (e.g., M001)")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Plan only, don't execute")
    parser.add_argument("--model", "-m", default="claude", choices=["claude", "claude-haiku", "gpt4", "gpt4o", "gemini"], help="Preferred AI model")
    
    args = parser.parse_args()
    
    worker = AIMissionWorker(args.mission_id, args.model)
    success = await worker.run(dry_run=args.dry_run)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())


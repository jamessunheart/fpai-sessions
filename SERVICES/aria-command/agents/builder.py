"""
Builder Agent - Specialized agent for code creation and modification.

Uses Claude Opus for complex logic and architecture decisions.
"""

import logging
import time
from datetime import datetime
from typing import Optional

from .base import Agent, AgentSpecialty, Task, AgentOpinion, ExecutionResult

logger = logging.getLogger("aria.agents.builder")


class BuilderAgent(Agent):
    """
    Builder Agent - Creates and modifies code.
    
    Strengths:
    - Complex logic implementation
    - Architecture decisions
    - Code generation
    - Refactoring
    """
    
    def __init__(self):
        super().__init__(
            name="builder",
            specialty=AgentSpecialty.BUILD,
            model="claude-sonnet-4-20250514",  # Fast, capable
            description="Creates and modifies code with high-quality output"
        )
        
        self.system_prompt = """You are the Builder Agent in the ARIA Sovereign system.
Your role is to create and modify code with precision and quality.

Core responsibilities:
1. Implement features based on specifications
2. Fix bugs with minimal side effects
3. Refactor code for clarity and performance
4. Follow existing code patterns and style

Guidelines:
- Always consider edge cases
- Write self-documenting code
- Preserve existing functionality
- Minimize scope of changes

When evaluating tasks:
- Assess complexity and effort required
- Identify potential risks or dependencies
- Propose a clear implementation approach
- Rate your confidence in successful execution

Output your evaluation as JSON:
{
    "can_implement": true/false,
    "complexity": "trivial/simple/moderate/complex",
    "approach": "brief implementation plan",
    "risks": ["risk1", "risk2"],
    "dependencies": ["dep1", "dep2"],
    "confidence": 0.0-1.0,
    "concerns": ["concern1"],
    "suggestions": ["suggestion1"]
}"""

    async def evaluate(self, task: Task) -> AgentOpinion:
        """Evaluate a task for buildability."""
        start_time = time.time()
        
        try:
            # Build evaluation prompt
            prompt = f"""Evaluate this task for implementation:

Task Type: {task.type}
Description: {task.description}

Context:
{self._format_context(task.context)}

Provide your evaluation as JSON."""

            # Call LLM
            response = await self._call_llm(prompt, self.system_prompt)
            
            # Parse response
            evaluation = self._parse_evaluation(response)
            
            # Build opinion
            confidence = evaluation.get("confidence", 0.5)
            can_implement = evaluation.get("can_implement", True)
            
            recommendation = "approve" if can_implement and confidence >= 0.7 else "modify" if can_implement else "reject"
            
            opinion = AgentOpinion(
                agent_name=self.name,
                specialty=self.specialty,
                confidence=confidence,
                recommendation=recommendation,
                reasoning=f"Complexity: {evaluation.get('complexity', 'unknown')}. {evaluation.get('approach', '')}",
                concerns=evaluation.get("concerns", []),
                suggestions=evaluation.get("suggestions", []),
                evaluation_time_ms=int((time.time() - start_time) * 1000)
            )
            
            self.total_evaluations += 1
            self.last_action = datetime.now()
            
            return opinion
            
        except Exception as e:
            logger.error(f"Builder evaluation failed: {e}")
            return AgentOpinion(
                agent_name=self.name,
                specialty=self.specialty,
                confidence=0.3,
                recommendation="defer",
                reasoning=f"Evaluation failed: {str(e)}",
                evaluation_time_ms=int((time.time() - start_time) * 1000)
            )
    
    async def execute(self, task: Task) -> ExecutionResult:
        """Execute a code change task."""
        start_time = datetime.now()
        
        try:
            self._current_tasks += 1
            
            # Generate implementation
            prompt = f"""Implement this task:

Task: {task.description}

Context:
{self._format_context(task.context)}

Provide the implementation as a series of file operations:
1. For each file to modify, provide the exact changes
2. Use search/replace format for modifications
3. Use full content for new files

Format:
### FILE: path/to/file.py
### ACTION: modify|create|delete
### SEARCH (for modify):
<exact text to find>
### REPLACE:
<replacement text>
---"""

            response = await self._call_llm(prompt, self.system_prompt)
            
            # Parse and execute file operations
            files_modified = []
            output_parts = []
            
            # Parse the response for file operations
            operations = self._parse_operations(response)
            
            for op in operations:
                result = await self._execute_operation(op)
                if result["success"]:
                    files_modified.append(op["path"])
                    output_parts.append(f"✓ {op['action']}: {op['path']}")
                else:
                    output_parts.append(f"✗ {op['action']}: {op['path']} - {result['error']}")
            
            self.total_executions += 1
            self.last_action = datetime.now()
            
            return ExecutionResult(
                task_id=task.id,
                success=len(files_modified) > 0,
                output="\n".join(output_parts),
                files_modified=files_modified,
                started_at=start_time,
                completed_at=datetime.now(),
                duration_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                backup_created=True,
                can_rollback=True
            )
            
        except Exception as e:
            logger.error(f"Builder execution failed: {e}")
            return ExecutionResult(
                task_id=task.id,
                success=False,
                output="",
                error=str(e),
                started_at=start_time,
                completed_at=datetime.now()
            )
        finally:
            self._current_tasks -= 1
    
    def _format_context(self, context: dict) -> str:
        """Format context for prompts."""
        parts = []
        if "file_content" in context:
            parts.append(f"Current file content:\n```\n{context['file_content']}\n```")
        if "related_files" in context:
            parts.append(f"Related files: {', '.join(context['related_files'])}")
        if "requirements" in context:
            parts.append(f"Requirements: {context['requirements']}")
        return "\n".join(parts) if parts else "No additional context provided."
    
    def _parse_evaluation(self, response: str) -> dict:
        """Parse LLM evaluation response."""
        import json
        
        # Try to extract JSON from response
        try:
            # Look for JSON block
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "{" in response:
                # Find JSON object
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]
            else:
                json_str = response
            
            return json.loads(json_str)
        except:
            # Return defaults if parsing fails
            return {
                "can_implement": True,
                "complexity": "moderate",
                "confidence": 0.6,
                "approach": response[:200]
            }
    
    def _parse_operations(self, response: str) -> list:
        """Parse file operations from LLM response."""
        operations = []
        
        # Split by file markers
        parts = response.split("### FILE:")
        
        for part in parts[1:]:  # Skip first empty part
            lines = part.strip().split("\n")
            if not lines:
                continue
            
            path = lines[0].strip()
            action = "modify"
            search = ""
            replace = ""
            
            current_section = None
            section_content = []
            
            for line in lines[1:]:
                if line.startswith("### ACTION:"):
                    action = line.split(":")[1].strip().lower()
                elif line.startswith("### SEARCH"):
                    if section_content and current_section == "replace":
                        replace = "\n".join(section_content)
                    current_section = "search"
                    section_content = []
                elif line.startswith("### REPLACE"):
                    if section_content and current_section == "search":
                        search = "\n".join(section_content)
                    current_section = "replace"
                    section_content = []
                elif line == "---":
                    if section_content and current_section == "replace":
                        replace = "\n".join(section_content)
                    break
                elif current_section:
                    section_content.append(line)
            
            if section_content and current_section == "replace":
                replace = "\n".join(section_content)
            
            operations.append({
                "path": path,
                "action": action,
                "search": search,
                "replace": replace
            })
        
        return operations
    
    async def _execute_operation(self, op: dict) -> dict:
        """Execute a single file operation."""
        import os
        
        WORKSPACE = os.getenv("WORKSPACE_ROOT", "/Users/jamessunheart/FPAI_Cockpit")
        full_path = os.path.join(WORKSPACE, op["path"])
        
        try:
            if op["action"] == "create":
                # Create new file
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(op["replace"])
                return {"success": True}
            
            elif op["action"] == "delete":
                if os.path.exists(full_path):
                    os.remove(full_path)
                return {"success": True}
            
            elif op["action"] == "modify":
                if not os.path.exists(full_path):
                    return {"success": False, "error": "File not found"}
                
                with open(full_path, "r") as f:
                    content = f.read()
                
                # Create backup
                backup_dir = os.path.join(WORKSPACE, ".aria-backups")
                os.makedirs(backup_dir, exist_ok=True)
                backup_path = os.path.join(backup_dir, f"{os.path.basename(op['path'])}.bak")
                with open(backup_path, "w") as f:
                    f.write(content)
                
                # Apply change
                if op["search"] and op["search"] in content:
                    new_content = content.replace(op["search"], op["replace"], 1)
                    with open(full_path, "w") as f:
                        f.write(new_content)
                    return {"success": True}
                else:
                    return {"success": False, "error": "Search text not found"}
            
            return {"success": False, "error": f"Unknown action: {op['action']}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}



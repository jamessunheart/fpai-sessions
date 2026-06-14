#!/usr/bin/env python3
"""
ARIA ULTRA POWER - SAFE CODE GENERATOR
========================================

Generate code changes safely:
- Syntax validation before apply
- Unit test generation
- Rollback mechanism
- Change isolation
"""

import ast
import logging
import os
import time
import shutil
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import httpx

logger = logging.getLogger("aria.evolution.codegen")

# Claude API for code generation
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_API = "https://api.anthropic.com/v1/messages"

# Backup directory
BACKUP_DIR = Path("/opt/fpai/aria-command/backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class CodeChange:
    """A proposed code change."""
    change_id: str
    file_path: str
    description: str
    original_content: str
    new_content: str
    diff: str
    risk_level: str  # "safe", "moderate", "risky"
    requires_approval: bool
    auto_generated_tests: Optional[str] = None
    validation_result: Optional[Dict] = None
    created_at: float = field(default_factory=time.time)


@dataclass
class ChangeResult:
    """Result of applying a change."""
    success: bool
    message: str
    backup_path: Optional[str] = None
    rollback_available: bool = False
    error: Optional[str] = None


class SafeCodeGenerator:
    """
    Generate and apply code changes safely.
    
    Features:
    - AI-powered code generation
    - Syntax validation
    - Automatic backup
    - Rollback capability
    - Test generation
    """
    
    # Protected files (cannot be modified)
    PROTECTED_FILES = [
        "opus_brain.py",  # Core brain - protected
        "tools.py",
        "bot.py",
    ]
    
    # Risk keywords that increase risk level
    RISKY_KEYWORDS = [
        "os.system", "subprocess", "eval", "exec",
        "rm -rf", "DROP TABLE", "DELETE FROM",
        "api_key", "password", "secret",
    ]
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=60.0)
        self._pending_changes: List[CodeChange] = []
        self._applied_changes: List[Tuple[CodeChange, str]] = []  # (change, backup_path)
        
        logger.info("SafeCodeGenerator initialized")
    
    async def generate_change(
        self,
        description: str,
        target_file: str,
        context: str = ""
    ) -> Optional[CodeChange]:
        """Generate a code change using AI."""
        # Check if file is protected
        filename = Path(target_file).name
        if filename in self.PROTECTED_FILES:
            logger.warning(f"Cannot modify protected file: {filename}")
            return None
        
        # Read current file content
        try:
            with open(target_file, "r") as f:
                original_content = f.read()
        except FileNotFoundError:
            original_content = ""
        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            return None
        
        # Generate code using Claude
        prompt = f"""You are modifying Python code for Aria, an AI assistant.

File: {target_file}
Current content:
```python
{original_content[:5000]}
```

Task: {description}

{f'Additional context: {context}' if context else ''}

Generate ONLY the complete new file content. Do not include explanations or markdown code blocks.
The output should be valid Python that can be directly written to the file."""

        try:
            response = await self.http.post(
                ANTHROPIC_API,
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 8000,
                    "messages": [{"role": "user", "content": prompt}],
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Claude API error: {response.text}")
                return None
            
            data = response.json()
            new_content = data["content"][0]["text"]
            
            # Clean up any markdown code blocks if present
            if new_content.startswith("```"):
                lines = new_content.split("\n")
                new_content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            
        except Exception as e:
            logger.error(f"Code generation error: {e}")
            return None
        
        # Validate the new code
        validation = self._validate_python(new_content)
        if not validation["valid"]:
            logger.warning(f"Generated code has syntax errors: {validation['error']}")
        
        # Assess risk level
        risk_level = self._assess_risk(original_content, new_content)
        
        # Generate diff
        diff = self._generate_diff(original_content, new_content)
        
        change_id = hashlib.md5(f"{target_file}{time.time()}".encode()).hexdigest()[:8]
        
        change = CodeChange(
            change_id=change_id,
            file_path=target_file,
            description=description,
            original_content=original_content,
            new_content=new_content,
            diff=diff,
            risk_level=risk_level,
            requires_approval=risk_level in ["moderate", "risky"] or not validation["valid"],
            validation_result=validation,
        )
        
        self._pending_changes.append(change)
        
        return change
    
    def _validate_python(self, code: str) -> Dict:
        """Validate Python code syntax."""
        try:
            ast.parse(code)
            return {"valid": True, "error": None}
        except SyntaxError as e:
            return {
                "valid": False,
                "error": f"Line {e.lineno}: {e.msg}",
                "line": e.lineno,
            }
    
    def _assess_risk(self, original: str, new: str) -> str:
        """Assess risk level of a change."""
        # Check for dangerous keywords in new code
        risky_count = sum(1 for kw in self.RISKY_KEYWORDS if kw in new and kw not in original)
        
        if risky_count >= 2:
            return "risky"
        elif risky_count == 1:
            return "moderate"
        
        # Check change size
        lines_changed = abs(len(new.split("\n")) - len(original.split("\n")))
        if lines_changed > 100:
            return "moderate"
        
        # Check if core functionality changed
        if "def __init__" in new and "def __init__" in original:
            if new.count("def __init__") != original.count("def __init__"):
                return "moderate"
        
        return "safe"
    
    def _generate_diff(self, original: str, new: str) -> str:
        """Generate a simple diff between original and new content."""
        import difflib
        
        original_lines = original.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile="original",
            tofile="modified",
            lineterm=""
        )
        
        return "".join(list(diff)[:100])  # Limit diff size
    
    async def apply_change(self, change_id: str, force: bool = False) -> ChangeResult:
        """Apply a pending change."""
        # Find the change
        change = None
        for c in self._pending_changes:
            if c.change_id == change_id:
                change = c
                break
        
        if not change:
            return ChangeResult(
                success=False,
                message=f"Change {change_id} not found",
            )
        
        # Check approval
        if change.requires_approval and not force:
            return ChangeResult(
                success=False,
                message="Change requires approval",
            )
        
        # Validate again
        if not change.validation_result.get("valid"):
            return ChangeResult(
                success=False,
                message=f"Code validation failed: {change.validation_result.get('error')}",
            )
        
        # Create backup
        backup_path = self._create_backup(change.file_path)
        
        # Apply change
        try:
            with open(change.file_path, "w") as f:
                f.write(change.new_content)
            
            # Record applied change
            self._applied_changes.append((change, backup_path))
            self._pending_changes.remove(change)
            
            return ChangeResult(
                success=True,
                message=f"Applied change to {change.file_path}",
                backup_path=backup_path,
                rollback_available=True,
            )
        
        except Exception as e:
            # Restore from backup
            if backup_path:
                self._restore_backup(change.file_path, backup_path)
            
            return ChangeResult(
                success=False,
                message=f"Failed to apply change: {str(e)}",
                error=str(e),
            )
    
    def _create_backup(self, file_path: str) -> Optional[str]:
        """Create backup of a file."""
        if not Path(file_path).exists():
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = Path(file_path).name
        backup_path = BACKUP_DIR / f"{filename}.{timestamp}.bak"
        
        try:
            shutil.copy2(file_path, backup_path)
            return str(backup_path)
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None
    
    def _restore_backup(self, file_path: str, backup_path: str) -> bool:
        """Restore file from backup."""
        try:
            shutil.copy2(backup_path, file_path)
            return True
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def rollback_last(self) -> ChangeResult:
        """Rollback the last applied change."""
        if not self._applied_changes:
            return ChangeResult(
                success=False,
                message="No changes to rollback",
            )
        
        change, backup_path = self._applied_changes.pop()
        
        if not backup_path or not Path(backup_path).exists():
            return ChangeResult(
                success=False,
                message="Backup not available for rollback",
            )
        
        if self._restore_backup(change.file_path, backup_path):
            return ChangeResult(
                success=True,
                message=f"Rolled back change to {change.file_path}",
            )
        else:
            return ChangeResult(
                success=False,
                message="Rollback failed",
            )
    
    def get_pending_changes(self) -> List[CodeChange]:
        """Get all pending changes."""
        return self._pending_changes.copy()
    
    def approve_change(self, change_id: str) -> bool:
        """Approve a pending change."""
        for change in self._pending_changes:
            if change.change_id == change_id:
                change.requires_approval = False
                return True
        return False
    
    def reject_change(self, change_id: str) -> bool:
        """Reject and remove a pending change."""
        for change in self._pending_changes:
            if change.change_id == change_id:
                self._pending_changes.remove(change)
                return True
        return False
    
    async def generate_tests(self, change: CodeChange) -> Optional[str]:
        """Generate unit tests for a change."""
        prompt = f"""Generate Python unit tests for the following code:

File: {change.file_path}
Description: {change.description}

Code:
```python
{change.new_content[:3000]}
```

Generate pytest-style tests that cover the main functionality.
Return only the test code, no explanations."""

        try:
            response = await self.http.post(
                ANTHROPIC_API,
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}],
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                tests = data["content"][0]["text"]
                change.auto_generated_tests = tests
                return tests
        except Exception as e:
            logger.error(f"Test generation error: {e}")
        
        return None
    
    def format_change(self, change: CodeChange) -> str:
        """Format change for display."""
        risk_emoji = "🟢" if change.risk_level == "safe" else "🟡" if change.risk_level == "moderate" else "🔴"
        valid_emoji = "✅" if change.validation_result.get("valid") else "❌"
        
        lines = [
            f"{risk_emoji} **Code Change** `{change.change_id}`",
            "",
            f"File: `{change.file_path}`",
            f"Risk: {change.risk_level}",
            f"Valid: {valid_emoji}",
            f"Approval: {'Required' if change.requires_approval else 'Auto'}",
            "",
            f"**Description:** {change.description}",
            "",
            "**Diff Preview:**",
            "```diff",
            change.diff[:500] + ("..." if len(change.diff) > 500 else ""),
            "```",
        ]
        
        return "\n".join(lines)


# Singleton
_generator: Optional[SafeCodeGenerator] = None


def get_code_generator() -> SafeCodeGenerator:
    """Get global SafeCodeGenerator instance."""
    global _generator
    if _generator is None:
        _generator = SafeCodeGenerator()
    return _generator



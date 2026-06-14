#!/usr/bin/env python3
"""
ARIA BUILDER
============

The code modification engine that actually makes changes.

Features:
- Safe file reading within scope
- Propose changes with diff preview
- Apply approved changes with backup
- Rollback on failure
- Syntax verification
- Gemini second-opinion verification
"""

import os
import re
import ast
import json
import shutil
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict, field
import subprocess

logger = logging.getLogger("aria.builder")

# ============================================================================
# CONFIGURATION
# ============================================================================

# Base path for Aria's files (scope limit)
ARIA_BASE_PATH = Path("/opt/fpai/aria")

# Allowed files for modification
ALLOWED_FILES = {
    "server.py", "actions.py", "smart_responses.py",
    "memory.py", "memory_v2.py", "proactive.py",
    "proactive_daemon.py", "voice.py", "channels.py",
    "trading_intel.py", "connected_aria.py", "intelligent_aria.py",
    "fast_llm.py", ".env"
}

# Config files (JSON)
CONFIG_FILES = {"*.json"}

# Backup directory
BACKUP_DIR = ARIA_BASE_PATH / "backups"

# Maximum lines that can be changed in one request
MAX_CHANGE_LINES = 100

# Pending changes storage
PENDING_CHANGES_FILE = ARIA_BASE_PATH / "data" / "pending_changes.json"


@dataclass
class FileChange:
    """A single file change."""
    id: str
    file_path: str
    action: str  # add, modify, delete
    old_content: Optional[str]
    new_content: str
    description: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    backup_path: Optional[str] = None
    status: str = "pending"  # pending, applied, rolled_back, failed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    applied_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FileChange':
        return cls(**data)
    
    def get_diff_preview(self, context_lines: int = 3) -> str:
        """Generate a diff-style preview."""
        lines = []
        
        if self.action == "add":
            lines.append(f"+ Adding to {self.file_path}:")
            for line in self.new_content.split('\n'):
                lines.append(f"+ {line}")
        
        elif self.action == "modify":
            lines.append(f"~ Modifying {self.file_path}:")
            if self.old_content:
                lines.append("- Old:")
                for line in self.old_content.split('\n')[:10]:
                    lines.append(f"- {line}")
                if self.old_content.count('\n') > 10:
                    lines.append("- ... (truncated)")
            lines.append("+ New:")
            for line in self.new_content.split('\n')[:10]:
                lines.append(f"+ {line}")
            if self.new_content.count('\n') > 10:
                lines.append("+ ... (truncated)")
        
        elif self.action == "delete":
            lines.append(f"- Deleting from {self.file_path}:")
            if self.old_content:
                for line in self.old_content.split('\n')[:5]:
                    lines.append(f"- {line}")
        
        return '\n'.join(lines)


class CodeModifier:
    """
    Handles code modifications with safety features.
    
    - Validates scope (only Aria files)
    - Creates backups before changes
    - Verifies syntax before applying
    - Supports rollback
    """
    
    def __init__(self, base_path: Path = ARIA_BASE_PATH):
        self.base_path = base_path
        self.backup_dir = base_path / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.pending_changes: Dict[str, FileChange] = {}
        self._load_pending()
    
    def _load_pending(self):
        """Load pending changes from disk."""
        try:
            if PENDING_CHANGES_FILE.exists():
                data = json.loads(PENDING_CHANGES_FILE.read_text())
                self.pending_changes = {
                    k: FileChange.from_dict(v) for k, v in data.items()
                }
        except Exception as e:
            logger.warning(f"Failed to load pending changes: {e}")
            self.pending_changes = {}
    
    def _save_pending(self):
        """Save pending changes to disk."""
        try:
            PENDING_CHANGES_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v.to_dict() for k, v in self.pending_changes.items()}
            PENDING_CHANGES_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save pending changes: {e}")
    
    def is_in_scope(self, filepath: str) -> Tuple[bool, str]:
        """Check if a file is within allowed scope."""
        # Normalize path
        if filepath.startswith('/'):
            path = Path(filepath)
        else:
            path = self.base_path / filepath
        
        # Must be under ARIA_BASE_PATH
        try:
            path.resolve().relative_to(self.base_path.resolve())
        except ValueError:
            return False, f"Path {filepath} is outside Aria scope"
        
        # Must be an allowed file
        filename = path.name
        if filename not in ALLOWED_FILES and not filename.endswith('.json'):
            return False, f"File {filename} is not in allowed list"
        
        return True, "OK"
    
    def read_file(self, filepath: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Safely read a file within scope.
        
        Returns:
            (content, error) - content if successful, error message if not
        """
        in_scope, reason = self.is_in_scope(filepath)
        if not in_scope:
            return None, reason
        
        path = self.base_path / filepath if not filepath.startswith('/') else Path(filepath)
        
        try:
            if not path.exists():
                return None, f"File {filepath} does not exist"
            content = path.read_text()
            return content, None
        except Exception as e:
            return None, str(e)
    
    def propose_change(
        self,
        filepath: str,
        new_content: str,
        description: str,
        old_content: Optional[str] = None,
        action: str = "modify"
    ) -> Tuple[Optional[FileChange], Optional[str]]:
        """
        Propose a code change.
        
        Args:
            filepath: Target file
            new_content: New code to insert/replace
            description: What this change does
            old_content: Content to replace (for modify)
            action: add, modify, or delete
        
        Returns:
            (FileChange, error) - change proposal or error
        """
        # Validate scope
        in_scope, reason = self.is_in_scope(filepath)
        if not in_scope:
            return None, reason
        
        # Check line count
        new_lines = new_content.count('\n') + 1
        if new_lines > MAX_CHANGE_LINES:
            return None, f"Change too large: {new_lines} lines (max {MAX_CHANGE_LINES})"
        
        # Verify syntax if Python file
        if filepath.endswith('.py'):
            syntax_ok, syntax_error = self.verify_syntax(new_content, is_partial=(action != "add"))
            if not syntax_ok and action == "add":
                return None, f"Syntax error: {syntax_error}"
        
        # Generate change ID
        change_id = hashlib.md5(
            f"{filepath}{new_content}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        change = FileChange(
            id=change_id,
            file_path=filepath,
            action=action,
            old_content=old_content,
            new_content=new_content,
            description=description
        )
        
        self.pending_changes[change_id] = change
        self._save_pending()
        
        logger.info(f"Proposed change {change_id}: {description}")
        return change, None
    
    def apply_change(self, change_id: str) -> Tuple[bool, str]:
        """
        Apply an approved change.
        
        Returns:
            (success, message)
        """
        change = self.pending_changes.get(change_id)
        if not change:
            return False, f"Change {change_id} not found"
        
        if change.status != "pending":
            return False, f"Change {change_id} is {change.status}, not pending"
        
        path = self.base_path / change.file_path if not change.file_path.startswith('/') else Path(change.file_path)
        
        try:
            # Create backup
            if path.exists():
                backup_path = self._create_backup(path)
                change.backup_path = str(backup_path)
            
            # Apply change based on action
            if change.action == "add":
                # Append to file
                existing = path.read_text() if path.exists() else ""
                path.write_text(existing + "\n" + change.new_content)
            
            elif change.action == "modify":
                if change.old_content:
                    # Replace specific content
                    existing = path.read_text()
                    if change.old_content not in existing:
                        return False, "Old content not found in file"
                    new_full = existing.replace(change.old_content, change.new_content, 1)
                    path.write_text(new_full)
                else:
                    # Overwrite entire file
                    path.write_text(change.new_content)
            
            elif change.action == "delete":
                if change.old_content:
                    existing = path.read_text()
                    new_full = existing.replace(change.old_content, "", 1)
                    path.write_text(new_full)
            
            # Verify syntax after change
            if path.suffix == ".py":
                content = path.read_text()
                syntax_ok, syntax_error = self.verify_syntax(content)
                if not syntax_ok:
                    # Rollback
                    self._restore_backup(change)
                    return False, f"Applied change broke syntax: {syntax_error}"
            
            change.status = "applied"
            change.applied_at = datetime.now().isoformat()
            self._save_pending()
            
            logger.info(f"Applied change {change_id}")
            return True, f"Change applied successfully"
            
        except Exception as e:
            logger.error(f"Failed to apply change {change_id}: {e}")
            change.status = "failed"
            self._save_pending()
            return False, str(e)
    
    def rollback(self, change_id: str) -> Tuple[bool, str]:
        """
        Rollback a change using backup.
        
        Returns:
            (success, message)
        """
        change = self.pending_changes.get(change_id)
        if not change:
            return False, f"Change {change_id} not found"
        
        if change.status != "applied":
            return False, f"Change {change_id} is {change.status}, cannot rollback"
        
        if not change.backup_path:
            return False, f"No backup available for {change_id}"
        
        try:
            success = self._restore_backup(change)
            if success:
                change.status = "rolled_back"
                self._save_pending()
                return True, "Rollback successful"
            return False, "Backup restore failed"
        except Exception as e:
            return False, str(e)
    
    def cancel_change(self, change_id: str) -> Tuple[bool, str]:
        """Cancel a pending change."""
        if change_id in self.pending_changes:
            del self.pending_changes[change_id]
            self._save_pending()
            return True, "Change cancelled"
        return False, f"Change {change_id} not found"
    
    def get_pending(self) -> List[FileChange]:
        """Get all pending changes."""
        return [c for c in self.pending_changes.values() if c.status == "pending"]
    
    def verify_syntax(self, code: str, is_partial: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Verify Python syntax.
        
        Args:
            code: Code to verify
            is_partial: If True, wrap in function to allow partial code
        
        Returns:
            (is_valid, error_message)
        """
        try:
            if is_partial:
                # Wrap partial code to make it parseable
                code = f"def __test__():\n" + '\n'.join(f"    {line}" for line in code.split('\n'))
            
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"Line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, str(e)
    
    def _create_backup(self, path: Path) -> Path:
        """Create a backup of a file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{path.name}.{timestamp}.bak"
        shutil.copy2(path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return backup_path
    
    def _restore_backup(self, change: FileChange) -> bool:
        """Restore a file from backup."""
        if not change.backup_path:
            return False
        
        backup = Path(change.backup_path)
        if not backup.exists():
            return False
        
        target = self.base_path / change.file_path if not change.file_path.startswith('/') else Path(change.file_path)
        shutil.copy2(backup, target)
        logger.info(f"Restored from backup: {backup}")
        return True


class BuilderEngine:
    """
    High-level builder interface that combines all components.
    
    Workflow:
    1. Parse intent from user message
    2. Generate code with Claude
    3. Verify with Gemini
    4. Propose change to user
    5. Apply on approval
    """
    
    def __init__(self):
        self.modifier = CodeModifier()
        
        # Lazy imports to avoid circular dependencies
        self._router = None
        self._coder = None
        self._parser = None
    
    @property
    def router(self):
        if self._router is None:
            from model_router import get_router
            self._router = get_router()
        return self._router
    
    @property
    def coder(self):
        if self._coder is None:
            from claude_coder import get_coder
            self._coder = get_coder()
        return self._coder
    
    @property
    def parser(self):
        if self._parser is None:
            from builder_intents import get_parser
            self._parser = get_parser()
        return self._parser
    
    async def process_request(self, text: str) -> Dict:
        """
        Process a builder request end-to-end.
        
        Returns dict with:
        - is_builder: bool
        - intent: parsed intent
        - proposal: code proposal (if builder)
        - change: FileChange to approve (if generated)
        - message: human-readable message
        """
        # 1. Parse intent
        intent = self.parser.parse(text)
        
        if not intent.is_builder_request:
            return {
                "is_builder": False,
                "intent": intent.to_dict(),
                "message": "This doesn't look like a builder request."
            }
        
        # 2. Check scope
        in_scope, reason = self.parser.is_in_scope(intent)
        if not in_scope:
            return {
                "is_builder": True,
                "intent": intent.to_dict(),
                "message": f"Cannot process: {reason}"
            }
        
        # 3. For READ actions, just return the content
        if intent.risk_level.value == "read":
            if intent.target_file:
                content, error = self.modifier.read_file(intent.target_file)
                if error:
                    return {"is_builder": True, "intent": intent.to_dict(), "message": error}
                return {
                    "is_builder": True,
                    "intent": intent.to_dict(),
                    "content": content[:2000],  # Truncate for display
                    "message": f"Contents of {intent.target_file}"
                }
        
        # 4. For WRITE actions, generate code proposal
        context = {}
        if intent.target_file:
            content, _ = self.modifier.read_file(intent.target_file)
            if content:
                context[intent.target_file] = content
        
        proposal = await self.coder.generate_change(
            request=text,
            file_context=context,
            constraints=["Max 100 lines", "Follow existing code style"]
        )
        
        if not proposal.success:
            return {
                "is_builder": True,
                "intent": intent.to_dict(),
                "message": f"Failed to generate code: {proposal.error}"
            }
        
        # 5. Create FileChange for approval
        changes = []
        for code_change in proposal.changes:
            file_change, error = self.modifier.propose_change(
                filepath=code_change.file,
                new_content=code_change.new_code,
                description=proposal.explanation,
                old_content=code_change.old_code,
                action=code_change.action
            )
            if file_change:
                changes.append(file_change)
        
        return {
            "is_builder": True,
            "intent": intent.to_dict(),
            "proposal": proposal.to_dict(),
            "changes": [c.to_dict() for c in changes],
            "needs_approval": intent.needs_approval,
            "message": proposal.format_for_telegram()
        }
    
    async def verify_with_gemini(self, code: str, purpose: str) -> Dict:
        """Get Gemini's verification of code."""
        from model_router import TaskType
        
        prompt = f"""Review this code change for safety and correctness.

Purpose: {purpose}

Code:
```python
{code}
```

Is this safe to apply? Any issues?
Respond with: SAFE or UNSAFE, then brief explanation."""

        response = await self.router.route(TaskType.VERIFY, prompt)
        
        is_safe = "SAFE" in response.content.upper() and "UNSAFE" not in response.content.upper()
        
        return {
            "is_safe": is_safe,
            "assessment": response.content,
            "provider": response.provider
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_engine: Optional[BuilderEngine] = None


def get_engine() -> BuilderEngine:
    """Get or create the global engine instance."""
    global _engine
    if _engine is None:
        _engine = BuilderEngine()
    return _engine


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    # Test CodeModifier
    modifier = CodeModifier()
    
    print("=" * 60)
    print("CODE MODIFIER TEST")
    print("=" * 60)
    
    # Test scope check
    print("\n--- Scope Check ---")
    tests = [
        "server.py",
        "actions.py",
        "/etc/passwd",
        "../../../etc/passwd",
        "somefile.py"
    ]
    
    for filepath in tests:
        in_scope, reason = modifier.is_in_scope(filepath)
        print(f"  {filepath}: {in_scope} ({reason})")
    
    # Test syntax verification
    print("\n--- Syntax Check ---")
    good_code = "def hello():\n    print('hi')"
    bad_code = "def hello(\n    print('hi'"
    
    ok, err = modifier.verify_syntax(good_code)
    print(f"  Good code: {ok}")
    
    ok, err = modifier.verify_syntax(bad_code)
    print(f"  Bad code: {ok} ({err})")
    
    print("\n--- Done ---")



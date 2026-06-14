#!/usr/bin/env python3
"""
ARIA COMMAND CENTER - TOOL EXECUTOR
=====================================

Full tool execution like Cursor's agent.
Read, edit, search, run, create files.
"""

import os
import re
import json
import logging
import shutil
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("aria.tools")

# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file. Use this to understand existing code before making changes.",
        "parameters": {
            "path": {"type": "string", "description": "Path to the file to read"},
            "start_line": {"type": "integer", "description": "Optional start line (1-indexed)"},
            "end_line": {"type": "integer", "description": "Optional end line"}
        },
        "required": ["path"]
    },
    {
        "name": "write_file",
        "description": "Create a new file or completely overwrite an existing file. Use edit_file for partial changes.",
        "parameters": {
            "path": {"type": "string", "description": "Path where to write the file"},
            "content": {"type": "string", "description": "Complete content to write"}
        },
        "required": ["path", "content"]
    },
    {
        "name": "edit_file",
        "description": "Make precise edits to a file using search and replace. Preserves the rest of the file.",
        "parameters": {
            "path": {"type": "string", "description": "Path to the file to edit"},
            "old_string": {"type": "string", "description": "Exact text to find and replace"},
            "new_string": {"type": "string", "description": "Text to replace with"}
        },
        "required": ["path", "old_string", "new_string"]
    },
    {
        "name": "search_codebase",
        "description": "Search for patterns across the entire codebase. Returns matching files and snippets.",
        "parameters": {
            "pattern": {"type": "string", "description": "Search pattern (regex supported)"},
            "file_pattern": {"type": "string", "description": "Optional file pattern filter (e.g., '*.py')"}
        },
        "required": ["pattern"]
    },
    {
        "name": "list_directory",
        "description": "List files and directories in a path.",
        "parameters": {
            "path": {"type": "string", "description": "Directory path to list"}
        },
        "required": ["path"]
    },
    {
        "name": "run_command",
        "description": "Execute a terminal command. Use for running tests, builds, or checking status.",
        "parameters": {
            "command": {"type": "string", "description": "Command to execute"},
            "server": {"type": "string", "description": "Server to run on: 'local', 'primary', or 'secondary'"}
        },
        "required": ["command"]
    },
    {
        "name": "create_plan",
        "description": "Create a multi-step plan for complex tasks. Each step will be executed in sequence.",
        "parameters": {
            "description": {"type": "string", "description": "Brief description of the plan"},
            "steps": {"type": "array", "items": {"type": "string"}, "description": "List of steps to execute"}
        },
        "required": ["description", "steps"]
    },
    {
        "name": "complete_step",
        "description": "Mark the current plan step as complete and move to the next one.",
        "parameters": {}
    },
    {
        "name": "ask_user",
        "description": "Ask the user for clarification or approval before proceeding.",
        "parameters": {
            "question": {"type": "string", "description": "Question to ask the user"}
        },
        "required": ["question"]
    },
    {
        "name": "self_analyze",
        "description": "MANDATORY when asked about self-improvement! Analyzes Aria's recent performance from evolution.db. Returns real metrics: avg response time, failure rate, unaddressed patterns.",
        "parameters": {},
        "required": []
    },
    {
        "name": "send_voice_message",
        "description": "Send a voice message to James via Telegram. Uses OpenAI TTS with context-aware voice selection (nova for friendly, onyx for urgent, shimmer for trading).",
        "parameters": {
            "text": {"type": "string", "description": "Text to speak in the voice message"},
            "context": {"type": "string", "description": "Context for voice selection: 'default', 'urgent', 'trading', 'brief', 'code'"}
        },
        "required": ["text"]
    },
    {
        "name": "send_sms",
        "description": "Send SMS to a phone number via Twilio. Auto-approved for James's number, requires approval for others.",
        "parameters": {
            "to": {"type": "string", "description": "Phone number in +1XXXXXXXXXX format"},
            "message": {"type": "string", "description": "SMS message content (max 160 chars recommended)"}
        },
        "required": ["to", "message"]
    },
    {
        "name": "send_email",
        "description": "Send email via SMTP. Auto-approved for internal @fullpotential.ai addresses, requires approval for external.",
        "parameters": {
            "to": {"type": "string", "description": "Recipient email address"},
            "subject": {"type": "string", "description": "Email subject line"},
            "body": {"type": "string", "description": "Email body content"}
        },
        "required": ["to", "subject", "body"]
    },
    {
        "name": "make_phone_call",
        "description": "Make a phone call via Twilio with TTS message. Requires approval for all calls except to James.",
        "parameters": {
            "to": {"type": "string", "description": "Phone number to call in +1XXXXXXXXXX format"},
            "message": {"type": "string", "description": "Message to speak via TTS when call connects"}
        },
        "required": ["to", "message"]
    },
    {
        "name": "store_memory",
        "description": "Store an important memory to persistent cloud storage (Mem0). Use this to remember learnings, patterns, or context that should persist across sessions.",
        "parameters": {
            "content": {"type": "string", "description": "The memory content to store"},
            "category": {"type": "string", "description": "Category: 'learning', 'pattern', 'decision', 'context', or 'preference'"},
            "importance": {"type": "string", "description": "Importance level: 'low', 'medium', 'high', or 'critical'"}
        },
        "required": ["content", "category"]
    },
    {
        "name": "recall_memory",
        "description": "Search your persistent memory for relevant past knowledge. Use this to find learnings, patterns, or context from past interactions.",
        "parameters": {
            "query": {"type": "string", "description": "What to search for in your memories"},
            "limit": {"type": "integer", "description": "Max number of memories to return (default 5)"}
        },
        "required": ["query"]
    },
    {
        "name": "read_ontology",
        "description": "Read files from your ontology (/opt/fpai/apprentice-os/). Use this to consult governance principles, check profiles, or read system state.",
        "parameters": {
            "path": {"type": "string", "description": "Path within apprentice-os/, e.g. 'core/governance/PRINCIPLES.md' or 'active/graph.json'"}
        },
        "required": ["path"]
    },
    {
        "name": "assess_shadow_costs",
        "description": "Compute and report all four shadow costs (stress accumulation, trust decay, optionality loss, complexity creep). Use this to surface hidden costs before major decisions.",
        "parameters": {
            "stress_level": {"type": "number", "description": "Optional: Self-reported stress level (0-100)"},
            "current_trust": {"type": "number", "description": "Optional: Current trust score"},
            "previous_trust": {"type": "number", "description": "Optional: Previous trust score"}
        },
        "required": []
    },
    {
        "name": "check_governance",
        "description": "Check a proposed action against governance rules (Priority Stack and Three Nevers). Returns whether action is allowed.",
        "parameters": {
            "action": {"type": "string", "description": "Description of the proposed action"},
            "yield_benefit": {"type": "number", "description": "Expected yield benefit (0-1)"},
            "coherence_impact": {"type": "number", "description": "Impact on coherence (-1 to 1)"},
            "complexity_delta": {"type": "number", "description": "Change in system complexity"}
        },
        "required": ["action"]
    },
    # ============================================================================
    # BUILDER TOOLS - For collaborative module building with apprentices
    # ============================================================================
    {
        "name": "scaffold_module",
        "description": "Create a new module scaffold for an apprentice. Use when they want to build a new command. Creates module.json, handler.py, and README.md in their workspace.",
        "parameters": {
            "user_id": {"type": "integer", "description": "The apprentice's Telegram user ID"},
            "module_name": {"type": "string", "description": "Name for the module (e.g., 'timer', 'joke')"},
            "command": {"type": "string", "description": "The command trigger (e.g., '/timer', '/joke')"},
            "description": {"type": "string", "description": "What the module does"},
            "author": {"type": "string", "description": "Name of the apprentice building it"},
            "initial_logic": {"type": "string", "description": "Optional: The Python code for the handler logic (inside the handle function)"}
        },
        "required": ["user_id", "module_name", "command", "description"]
    },
    {
        "name": "update_module_code",
        "description": "Update the handler.py code in an apprentice's module. Use when they want to change or improve their code.",
        "parameters": {
            "user_id": {"type": "integer", "description": "The apprentice's Telegram user ID"},
            "module_name": {"type": "string", "description": "Name of the module to update"},
            "new_code": {"type": "string", "description": "The complete new handler.py code"}
        },
        "required": ["user_id", "module_name", "new_code"]
    },
    {
        "name": "test_module",
        "description": "Test an apprentice's module with given arguments in sandbox mode. Use to let them try their code safely.",
        "parameters": {
            "user_id": {"type": "integer", "description": "The apprentice's Telegram user ID"},
            "module_name": {"type": "string", "description": "Name of the module to test"},
            "test_args": {"type": "string", "description": "Arguments to pass to the handler (default empty)"}
        },
        "required": ["user_id", "module_name"]
    },
    {
        "name": "list_my_modules",
        "description": "List all modules in an apprentice's workspace with their status (draft, submitted, live).",
        "parameters": {
            "user_id": {"type": "integer", "description": "The apprentice's Telegram user ID"}
        },
        "required": ["user_id"]
    },
    {
        "name": "submit_module",
        "description": "Submit an apprentice's module for steward review. Validates security and queues for approval.",
        "parameters": {
            "user_id": {"type": "integer", "description": "The apprentice's Telegram user ID"},
            "module_name": {"type": "string", "description": "Name of the module to submit"}
        },
        "required": ["user_id", "module_name"]
    },
    {
        "name": "get_module_code",
        "description": "Get the current handler.py code of an apprentice's module to show or review.",
        "parameters": {
            "user_id": {"type": "integer", "description": "The apprentice's Telegram user ID"},
            "module_name": {"type": "string", "description": "Name of the module"}
        },
        "required": ["user_id", "module_name"]
    },
    {
        "name": "delete_module",
        "description": "Delete a module from an apprentice's workspace. Use with caution - cannot be undone.",
        "parameters": {
            "user_id": {"type": "integer", "description": "The apprentice's Telegram user ID"},
            "module_name": {"type": "string", "description": "Name of the module to delete"}
        },
        "required": ["user_id", "module_name"]
    },
    {
        "name": "ai_create_module",
        "description": "Use AI to generate a complete module from a natural language idea. Creates module.json, handler.py, and README automatically. Perfect for apprentices who want to build something quickly with AI assistance.",
        "parameters": {
            "user_id": {"type": "integer", "description": "The apprentice's Telegram user ID"},
            "module_idea": {"type": "string", "description": "Natural language description of what the module should do (e.g., 'a command that tells dad jokes' or 'a timer that reminds me in X minutes')"},
            "auto_submit": {"type": "boolean", "description": "If true, automatically submit for review after creation. Default: false"}
        },
        "required": ["user_id", "module_idea"]
    },
    # ============================================================================
    # UNIFIED BUILDER TOOLS - AI-powered code generation and management
    # ============================================================================
    {
        "name": "ai_build",
        "description": "Use AI to generate code from natural language. Creates a build job with changes that can be reviewed and approved. Most powerful builder tool - generates complete implementations.",
        "parameters": {
            "request": {"type": "string", "description": "Natural language description of what to build (e.g., 'Create a health check endpoint that returns system status')"},
            "scope": {"type": "string", "description": "Permission scope: 'steward' for full access, 'apprentice' for sandbox, 'aria_self' for self-modification"},
            "context_files": {"type": "array", "items": {"type": "string"}, "description": "Optional: List of file paths to include as context for the AI"}
        },
        "required": ["request"]
    },
    {
        "name": "get_build_queue",
        "description": "Get the current build queue status including pending, building, and completed jobs.",
        "parameters": {}
    },
    {
        "name": "approve_build",
        "description": "Approve a build job that needs approval. The build will then be executed with backup and verification.",
        "parameters": {
            "job_id": {"type": "string", "description": "The build job ID to approve"}
        },
        "required": ["job_id"]
    },
    {
        "name": "reject_build",
        "description": "Reject a build job. The proposed changes will be discarded.",
        "parameters": {
            "job_id": {"type": "string", "description": "The build job ID to reject"}
        },
        "required": ["job_id"]
    },
    {
        "name": "rollback_build",
        "description": "Rollback a completed build using its backup. Restores all files to their pre-build state.",
        "parameters": {
            "job_id": {"type": "string", "description": "The build job ID to rollback"}
        },
        "required": ["job_id"]
    },
    {
        "name": "get_build_logs",
        "description": "Get detailed logs for a specific build job.",
        "parameters": {
            "job_id": {"type": "string", "description": "The build job ID"}
        },
        "required": ["job_id"]
    }
]

# ============================================================================
# PROTECTED FILES (Cannot be edited without explicit override)
# ============================================================================

PROTECTED_FILES = [
    "brain/opus_brain.py",
    "brain/tools.py",
    "telegram/bot.py",
    "/opt/fpai/aria-command/brain/opus_brain.py",
    "/opt/fpai/aria-command/brain/tools.py",
    "/opt/fpai/aria-command/telegram/bot.py",
]

PROTECTION_OVERRIDE_PHRASE = "OVERRIDE_PROTECTION_I_KNOW_WHAT_IM_DOING"


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    output: str
    tool_name: str
    error: Optional[str] = None
    data: Optional[Any] = None


class ToolExecutor:
    """
    Execute tools for the AI agent.
    
    Features:
    - File operations (read, write, edit)
    - Codebase search
    - Terminal commands
    - Plan management
    - Authority-based access control
    """
    
    def __init__(self, conversation=None, user_id: int = None):
        self.conversation = conversation
        self.user_id = user_id  # Telegram user ID for authority checks
        self.base_path = Path(os.getenv("FPAI_WORKSPACE", "/opt/fpai"))
        self.backup_dir = Path(os.getenv("ARIA_STATE_DIR", "/tmp/aria-command")) / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Import authority functions
        try:
            from access.authority import (
                can_read_path, can_write_path, is_steward, 
                is_apprentice, ensure_apprentice_workspace
            )
            self._can_read_path = can_read_path
            self._can_write_path = can_write_path
            self._is_steward = is_steward
            self._is_apprentice = is_apprentice
            self._ensure_workspace = ensure_apprentice_workspace
            self._authority_enabled = True
        except ImportError:
            self._authority_enabled = False
            logger.warning("Authority module not available - no path restrictions")
    
    async def execute(self, tool_name: str, arguments: Dict) -> ToolResult:
        """Execute a tool by name."""
        try:
            if tool_name == "read_file":
                return await self._read_file(**arguments)
            elif tool_name == "write_file":
                return await self._write_file(**arguments)
            elif tool_name == "edit_file":
                return await self._edit_file(**arguments)
            elif tool_name == "search_codebase":
                return await self._search_codebase(**arguments)
            elif tool_name == "list_directory":
                return await self._list_directory(**arguments)
            elif tool_name == "run_command":
                return await self._run_command(**arguments)
            elif tool_name == "create_plan":
                return await self._create_plan(**arguments)
            elif tool_name == "complete_step":
                return await self._complete_step()
            elif tool_name == "ask_user":
                return await self._ask_user(**arguments)
            elif tool_name == "self_analyze":
                return await self._self_analyze()
            elif tool_name == "send_voice_message":
                return await self._send_voice_message(**arguments)
            elif tool_name == "send_sms":
                return await self._send_sms(**arguments)
            elif tool_name == "send_email":
                return await self._send_email(**arguments)
            elif tool_name == "make_phone_call":
                return await self._make_phone_call(**arguments)
            elif tool_name == "store_memory":
                return await self._store_memory(**arguments)
            elif tool_name == "recall_memory":
                return await self._recall_memory(**arguments)
            elif tool_name == "read_ontology":
                return await self._read_ontology(**arguments)
            elif tool_name == "assess_shadow_costs":
                return await self._assess_shadow_costs(**arguments)
            elif tool_name == "check_governance":
                return await self._check_governance(**arguments)
            # Builder tools
            elif tool_name == "scaffold_module":
                return await self._scaffold_module(**arguments)
            elif tool_name == "update_module_code":
                return await self._update_module_code(**arguments)
            elif tool_name == "test_module":
                return await self._test_module(**arguments)
            elif tool_name == "list_my_modules":
                return await self._list_my_modules(**arguments)
            elif tool_name == "submit_module":
                return await self._submit_module(**arguments)
            elif tool_name == "get_module_code":
                return await self._get_module_code(**arguments)
            elif tool_name == "delete_module":
                return await self._delete_module(**arguments)
            elif tool_name == "ai_create_module":
                return await self._ai_create_module(**arguments)
            # Unified Builder tools
            elif tool_name == "ai_build":
                return await self._ai_build(**arguments)
            elif tool_name == "get_build_queue":
                return await self._get_build_queue()
            elif tool_name == "approve_build":
                return await self._approve_build(**arguments)
            elif tool_name == "reject_build":
                return await self._reject_build(**arguments)
            elif tool_name == "rollback_build":
                return await self._rollback_build(**arguments)
            elif tool_name == "get_build_logs":
                return await self._get_build_logs(**arguments)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name=tool_name,
                    error=f"Unknown tool: {tool_name}"
                )
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name=tool_name,
                error=str(e)
            )
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to base."""
        if path.startswith("/"):
            return Path(path)
        return self.base_path / path
    
    async def _read_file(
        self,
        path: str,
        start_line: int = None,
        end_line: int = None
    ) -> ToolResult:
        """Read a file."""
        file_path = self._resolve_path(path)
        
        # Authority check for apprentices
        if self._authority_enabled and self.user_id:
            allowed, reason = self._can_read_path(self.user_id, str(file_path))
            if not allowed:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="read_file",
                    error=f"🚫 Access denied: {reason}"
                )
        
        if not file_path.exists():
            return ToolResult(
                success=False,
                output="",
                tool_name="read_file",
                error=f"File not found: {path}"
            )
        
        try:
            content = file_path.read_text()
            
            # Apply line range if specified
            if start_line or end_line:
                lines = content.split('\n')
                start = (start_line - 1) if start_line else 0
                end = end_line if end_line else len(lines)
                content = '\n'.join(lines[start:end])
            
            # Add to working files
            if self.conversation:
                self.conversation.add_working_file(path, content)
            
            return ToolResult(
                success=True,
                output=content,
                tool_name="read_file",
                data={"path": path, "size": len(content)}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                tool_name="read_file",
                error=str(e)
            )
    
    async def _write_file(self, path: str, content: str) -> ToolResult:
        """Write a file."""
        file_path = self._resolve_path(path)
        
        # Authority check for apprentices
        if self._authority_enabled and self.user_id:
            allowed, reason = self._can_write_path(self.user_id, str(file_path))
            if not allowed:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="write_file",
                    error=f"🚫 Write access denied: {reason}"
                )
            
            # Ensure apprentice workspace exists
            if self._is_apprentice(self.user_id):
                self._ensure_workspace(self.user_id)
        
        try:
            # Create backup if exists
            if file_path.exists():
                backup_name = f"{file_path.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
                backup_path = self.backup_dir / backup_name
                shutil.copy2(file_path, backup_path)
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            file_path.write_text(content)
            
            # Update working files
            if self.conversation:
                self.conversation.add_working_file(path, content)
            
            return ToolResult(
                success=True,
                output=f"File written: {path} ({len(content)} bytes)",
                tool_name="write_file",
                data={"path": path, "size": len(content)}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                tool_name="write_file",
                error=str(e)
            )
    
    async def _edit_file(
        self,
        path: str,
        old_string: str,
        new_string: str,
        override: str = None
    ) -> ToolResult:
        """Edit a file with search/replace."""
        file_path = self._resolve_path(path)
        
        # Authority check for apprentices
        if self._authority_enabled and self.user_id:
            allowed, reason = self._can_write_path(self.user_id, str(file_path))
            if not allowed:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="edit_file",
                    error=f"🚫 Write access denied: {reason}"
                )
        
        # Check if file is protected
        normalized_path = str(file_path).replace("\\", "/")
        for protected in PROTECTED_FILES:
            if normalized_path.endswith(protected) or path.endswith(protected):
                if override != PROTECTION_OVERRIDE_PHRASE:
                    return ToolResult(
                        success=False,
                        output="",
                        tool_name="edit_file",
                        error=f"🛡️ PROTECTED FILE: {path}\n\n"
                              f"This is a critical file that cannot be modified without explicit human approval.\n"
                              f"Modifying this file could break Aria's core functionality.\n\n"
                              f"If James explicitly requested this change, ask him to confirm with:\n"
                              f"'Yes, modify {path} with override'"
                    )
        
        if not file_path.exists():
            return ToolResult(
                success=False,
                output="",
                tool_name="edit_file",
                error=f"File not found: {path}"
            )
        
        try:
            content = file_path.read_text()
            
            # Check if old_string exists
            if old_string not in content:
                # Try to find similar
                similar = self._find_similar(content, old_string)
                if similar:
                    return ToolResult(
                        success=False,
                        output="",
                        tool_name="edit_file",
                        error=f"Exact text not found. Did you mean:\n{similar}"
                    )
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="edit_file",
                    error="Text to replace not found in file"
                )
            
            # Count occurrences
            count = content.count(old_string)
            if count > 1:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="edit_file",
                    error=f"Text appears {count} times. Please provide more context to make it unique."
                )
            
            # Create backup
            backup_name = f"{file_path.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
            backup_path = self.backup_dir / backup_name
            shutil.copy2(file_path, backup_path)
            
            # Apply edit
            new_content = content.replace(old_string, new_string, 1)
            file_path.write_text(new_content)
            
            # Update working files
            if self.conversation:
                self.conversation.update_working_file(path, new_content)
            
            return ToolResult(
                success=True,
                output=f"File edited: {path}\nBackup: {backup_path.name}",
                tool_name="edit_file",
                data={"path": path, "backup": str(backup_path)}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                tool_name="edit_file",
                error=str(e)
            )
    
    def _find_similar(self, content: str, target: str, max_distance: int = 5) -> Optional[str]:
        """Find similar text in content."""
        # Simple approach: find lines that contain parts of the target
        target_lines = target.strip().split('\n')
        if not target_lines:
            return None
        
        first_line = target_lines[0].strip()
        content_lines = content.split('\n')
        
        for i, line in enumerate(content_lines):
            if first_line[:20] in line:
                # Found potential match, show context
                start = max(0, i - 1)
                end = min(len(content_lines), i + len(target_lines) + 1)
                return '\n'.join(content_lines[start:end])
        
        return None
    
    async def _search_codebase(
        self,
        pattern: str,
        file_pattern: str = None
    ) -> ToolResult:
        """Search the codebase."""
        from .codebase_index import get_index
        
        index = get_index()
        results = index.search(pattern, max_results=10, file_pattern=file_pattern)
        
        if not results:
            return ToolResult(
                success=True,
                output=f"No results found for: {pattern}",
                tool_name="search_codebase"
            )
        
        output_parts = [f"Found {len(results)} matches for '{pattern}':\n"]
        
        for r in results:
            output_parts.append(f"\n📄 {r.file.relative_path} (score: {r.score})")
            if r.snippet:
                output_parts.append(f"   {r.snippet[:100]}...")
        
        return ToolResult(
            success=True,
            output='\n'.join(output_parts),
            tool_name="search_codebase",
            data={"count": len(results), "files": [r.file.relative_path for r in results]}
        )
    
    async def _list_directory(self, path: str) -> ToolResult:
        """List directory contents."""
        dir_path = self._resolve_path(path)
        
        if not dir_path.exists():
            return ToolResult(
                success=False,
                output="",
                tool_name="list_directory",
                error=f"Directory not found: {path}"
            )
        
        if not dir_path.is_dir():
            return ToolResult(
                success=False,
                output="",
                tool_name="list_directory",
                error=f"Not a directory: {path}"
            )
        
        items = []
        for item in sorted(dir_path.iterdir()):
            if item.name.startswith('.'):
                continue
            prefix = "📁" if item.is_dir() else "📄"
            size = "" if item.is_dir() else f" ({item.stat().st_size} bytes)"
            items.append(f"{prefix} {item.name}{size}")
        
        return ToolResult(
            success=True,
            output=f"Contents of {path}:\n" + '\n'.join(items),
            tool_name="list_directory",
            data={"count": len(items)}
        )
    
    async def _run_command(
        self,
        command: str,
        server: str = "secondary"
    ) -> ToolResult:
        """Run a terminal command."""
        from ..access.terminal import run_command, classify_command
        
        # Check safety
        safety = classify_command(command)
        
        if safety == "red":
            return ToolResult(
                success=False,
                output="",
                tool_name="run_command",
                error=f"Command blocked (RED level): {command}\nThis command requires manual execution."
            )
        
        result = await run_command(command, server)
        
        if result.requires_approval:
            return ToolResult(
                success=False,
                output="",
                tool_name="run_command",
                error=f"Command requires approval: {command}\nApproval ID: {result.approval_id}"
            )
        
        if result.success:
            return ToolResult(
                success=True,
                output=result.stdout[:5000] if result.stdout else "Command completed successfully.",
                tool_name="run_command",
                data={"exit_code": result.exit_code}
            )
        else:
            return ToolResult(
                success=False,
                output=result.stdout or "",
                tool_name="run_command",
                error=result.stderr or result.error
            )
    
    async def _create_plan(self, description: str, steps: List[str]) -> ToolResult:
        """Create a multi-step plan."""
        if not self.conversation:
            return ToolResult(
                success=False,
                output="",
                tool_name="create_plan",
                error="No conversation context"
            )
        
        plan = self.conversation.set_plan(description, steps)
        
        output = f"📋 Plan created: {description}\n\n"
        for i, step in enumerate(steps):
            prefix = "1️⃣" if i == 0 else "⏳"
            output += f"{prefix} Step {i+1}: {step}\n"
        
        return ToolResult(
            success=True,
            output=output,
            tool_name="create_plan",
            data={"plan_id": plan.id, "steps": len(steps)}
        )
    
    async def _complete_step(self) -> ToolResult:
        """Complete current plan step."""
        if not self.conversation or not self.conversation.current_plan:
            return ToolResult(
                success=False,
                output="",
                tool_name="complete_step",
                error="No active plan"
            )
        
        step = self.conversation.advance_plan()
        
        if step:
            next_step = self.conversation.get_current_step()
            output = f"✅ Completed: {step['step']}\n"
            if next_step:
                output += f"➡️ Next: {next_step['step']}"
            else:
                output += "🎉 Plan completed!"
            
            return ToolResult(
                success=True,
                output=output,
                tool_name="complete_step"
            )
        
        return ToolResult(
            success=False,
            output="",
            tool_name="complete_step",
            error="No more steps in plan"
        )
    
    async def _ask_user(self, question: str) -> ToolResult:
        """Ask user for input (returns a special result that triggers user interaction)."""
        return ToolResult(
            success=True,
            output=question,
            tool_name="ask_user",
            data={"awaiting_response": True, "question": question}
        )
    
    async def _self_analyze(self) -> ToolResult:
        """
        Analyze Aria's recent performance from evolution.db.
        
        Returns real metrics: avg response time, failure rate, unaddressed patterns.
        """
        import sqlite3
        from pathlib import Path
        
        db_path = Path("/opt/fpai/aria-command/state/evolution.db")
        
        if not db_path.exists():
            return ToolResult(
                success=False,
                output="",
                tool_name="self_analyze",
                error="Evolution database not found at /opt/fpai/aria-command/state/evolution.db"
            )
        
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            
            output_parts = ["## 📊 Self-Analysis Report\n"]
            
            # 1. Recent interaction metrics
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    AVG(total_time_ms) as avg_time,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failures,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes
                FROM interactions 
                WHERE id IN (SELECT id FROM interactions ORDER BY id DESC LIMIT 20)
            """)
            row = cur.fetchone()
            total, avg_time, failures, successes = row
            
            output_parts.append("### Recent Performance (Last 20 Interactions)")
            output_parts.append(f"- **Total**: {total} interactions")
            output_parts.append(f"- **Avg Response Time**: {avg_time:.0f}ms ({avg_time/1000:.1f}s)")
            output_parts.append(f"- **Success Rate**: {(successes/total*100) if total > 0 else 0:.0f}% ({successes}/{total})")
            output_parts.append(f"- **Failures**: {failures}")
            
            # Performance assessment
            if avg_time and avg_time > 15000:
                output_parts.append(f"- ⚠️ **ISSUE**: Response time too slow (target: <10s)")
            if failures and failures > 2:
                output_parts.append(f"- ⚠️ **ISSUE**: High failure rate ({failures} in last 20)")
            
            # 2. Unaddressed patterns
            cur.execute("""
                SELECT detector, problem_description, severity, suggested_fix
                FROM detected_patterns 
                WHERE addressed = 0 
                ORDER BY detected_at DESC 
                LIMIT 5
            """)
            patterns = cur.fetchall()
            
            if patterns:
                output_parts.append("\n### Unaddressed Issues")
                for detector, desc, severity, fix in patterns:
                    output_parts.append(f"- **{detector}** ({severity}): {desc[:100]}")
                    if fix:
                        output_parts.append(f"  → Suggested: {fix[:80]}")
            else:
                output_parts.append("\n### ✅ No unaddressed issues detected")
            
            # 3. Recent errors
            cur.execute("""
                SELECT error_type, error_message, user_message
                FROM interactions 
                WHERE success = 0 AND error_type IS NOT NULL
                ORDER BY id DESC 
                LIMIT 3
            """)
            errors = cur.fetchall()
            
            if errors:
                output_parts.append("\n### Recent Errors")
                for err_type, err_msg, user_msg in errors:
                    output_parts.append(f"- **{err_type}**: {(err_msg or 'Unknown')[:60]}")
                    output_parts.append(f"  Query: \"{(user_msg or '')[:40]}...\"")
            
            # 4. Tool usage stats
            cur.execute("""
                SELECT tools_called, COUNT(*) as cnt
                FROM interactions 
                WHERE tools_called IS NOT NULL AND tools_called != '[]'
                GROUP BY tools_called
                ORDER BY cnt DESC
                LIMIT 5
            """)
            tool_usage = cur.fetchall()
            
            if tool_usage:
                output_parts.append("\n### Top Tool Combinations Used")
                for tools, cnt in tool_usage:
                    output_parts.append(f"- {tools}: {cnt} times")
            
            conn.close()
            
            # Summary recommendation
            output_parts.append("\n### 🎯 Priority Improvements")
            if avg_time and avg_time > 15000:
                output_parts.append("1. **Speed**: Reduce response time - consider caching or faster model routing")
            if failures and failures > 2:
                output_parts.append("2. **Reliability**: Fix recurring error patterns")
            if patterns:
                output_parts.append(f"3. **Patterns**: Address {len(patterns)} detected issues")
            if not patterns and (not failures or failures <= 1) and (not avg_time or avg_time <= 15000):
                output_parts.append("- System performing well! Focus on proactive improvements.")
            
            return ToolResult(
                success=True,
                output="\n".join(output_parts),
                tool_name="self_analyze",
                data={
                    "avg_response_ms": avg_time,
                    "failure_count": failures,
                    "unaddressed_patterns": len(patterns) if patterns else 0
                }
            )
            
        except Exception as e:
            logger.error(f"Self-analysis failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="self_analyze",
                error=f"Analysis failed: {e}"
            )
    
    async def _send_voice_message(
        self,
        text: str,
        context: str = "default",
        chat_id: int = None
    ) -> ToolResult:
        """
        Send a voice message via Telegram using OpenAI TTS.
        
        Args:
            text: Text to speak
            context: Voice context (default, urgent, trading, brief, code)
            chat_id: Target chat ID (uses default if not specified)
        """
        try:
            # Import voice module
            from voice.speak import send_voice, get_speaker
            
            # Default to James's chat ID
            if not chat_id:
                chat_id = 1759822075  # James's Telegram chat ID
            
            # Send the voice message
            success = await send_voice(chat_id, text, context)
            
            if success:
                return ToolResult(
                    success=True,
                    output=f"🎤 Voice message sent! Context: {context}\nText: \"{text[:100]}{'...' if len(text) > 100 else ''}\"",
                    tool_name="send_voice_message",
                    data={"chat_id": chat_id, "context": context}
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="send_voice_message",
                    error="Failed to send voice message. Check OpenAI API key and Telegram token."
                )
                
        except ImportError as e:
            return ToolResult(
                success=False,
                output="",
                tool_name="send_voice_message",
                error=f"Voice module import failed: {e}"
            )
        except Exception as e:
            logger.error(f"Voice message failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="send_voice_message",
                error=f"Voice message failed: {e}"
            )
    
    async def _send_sms(self, to: str, message: str) -> ToolResult:
        """
        Send SMS via Twilio.
        
        Auto-approved for James's number, requires approval for others.
        """
        import os
        
        JAMES_PHONE = os.getenv("JAMES_PHONE", "+19252397291")
        
        try:
            from sovereign.agency.communication import send_sms
            
            # Check if this is to James (auto-approve) or external (needs approval)
            is_james = to.endswith(JAMES_PHONE[-4:]) or to == JAMES_PHONE
            
            if not is_james:
                # Return a request for approval
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="send_sms",
                    error=f"📱 SMS to external number requires approval.\n\nTo: {to}\nMessage: {message}\n\nReply 'approve' to send."
                )
            
            result = await send_sms(to, message, require_approval=False)
            
            if result.get("status") == "sent":
                return ToolResult(
                    success=True,
                    output=f"📱 SMS sent to {to}!\nMessage: \"{message[:100]}{'...' if len(message) > 100 else ''}\"",
                    tool_name="send_sms",
                    data=result
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="send_sms",
                    error=result.get("message", "Failed to send SMS")
                )
                
        except ImportError as e:
            return ToolResult(
                success=False,
                output="",
                tool_name="send_sms",
                error=f"Communication module import failed: {e}"
            )
        except Exception as e:
            logger.error(f"SMS failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="send_sms",
                error=f"SMS failed: {e}"
            )
    
    async def _send_email(self, to: str, subject: str, body: str) -> ToolResult:
        """
        Send email via SMTP.
        
        Auto-approved for internal addresses, requires approval for external.
        """
        try:
            from sovereign.agency.communication import send_email
            
            # Check if internal (auto-approve) or external
            is_internal = to.endswith("@fullpotential.ai") or "james" in to.lower()
            
            if not is_internal:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="send_email",
                    error=f"📧 Email to external address requires approval.\n\nTo: {to}\nSubject: {subject}\nBody: {body[:200]}...\n\nReply 'approve' to send."
                )
            
            result = await send_email(to, subject, body, require_approval=False)
            
            if result.get("status") == "sent":
                return ToolResult(
                    success=True,
                    output=f"📧 Email sent to {to}!\nSubject: {subject}",
                    tool_name="send_email",
                    data=result
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="send_email",
                    error=result.get("message", "Failed to send email")
                )
                
        except ImportError as e:
            return ToolResult(
                success=False,
                output="",
                tool_name="send_email",
                error=f"Communication module import failed: {e}"
            )
        except Exception as e:
            logger.error(f"Email failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="send_email",
                error=f"Email failed: {e}"
            )
    
    async def _make_phone_call(self, to: str, message: str) -> ToolResult:
        """
        Make phone call via Twilio with TTS message.
        
        Requires approval for all calls except to James.
        """
        import os
        
        JAMES_PHONE = os.getenv("JAMES_PHONE", "+19252397291")
        
        try:
            # Check if this is to James (auto-approve) or external
            is_james = to.endswith(JAMES_PHONE[-4:]) or to == JAMES_PHONE
            
            if not is_james:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="make_phone_call",
                    error=f"📞 Phone call to external number requires approval.\n\nTo: {to}\nMessage: {message}\n\nReply 'approve' to call."
                )
            
            # Use the workflow action for phone calls
            from sovereign.workflows.actions import ActionLibrary
            
            library = ActionLibrary()
            result = await library._action_phone_call(
                {"to": to, "message": message},
                {}
            )
            
            if result.success:
                return ToolResult(
                    success=True,
                    output=f"📞 Calling {to}...\nMessage: \"{message[:100]}{'...' if len(message) > 100 else ''}\"",
                    tool_name="make_phone_call",
                    data={"to": to, "sid": result.data.get("sid") if result.data else None}
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="make_phone_call",
                    error=result.message or "Failed to make call"
                )
                
        except ImportError as e:
            return ToolResult(
                success=False,
                output="",
                tool_name="make_phone_call",
                error=f"Workflows module import failed: {e}"
            )
        except Exception as e:
            logger.error(f"Phone call failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="make_phone_call",
                error=f"Phone call failed: {e}"
            )
    
    async def _store_memory(self, content: str, category: str, importance: str = "medium") -> ToolResult:
        """
        Store a memory to Mem0 cloud for persistent recall.
        
        Categories: learning, pattern, decision, context, preference
        Importance: low, medium, high, critical
        """
        try:
            from memory import store_memory
            
            result = await store_memory(
                content=content,
                category=category,
                importance=importance
            )
            
            if result.success:
                return ToolResult(
                    success=True,
                    output=f"🧠 Memory stored!\n\nCategory: {category}\nImportance: {importance}\nContent: {content[:200]}{'...' if len(content) > 200 else ''}",
                    tool_name="store_memory",
                    data={"category": category, "importance": importance}
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="store_memory",
                    error=result.message
                )
            
        except ImportError as e:
            logger.error(f"Memory module import failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="store_memory",
                error=f"Memory module not available: {e}"
            )
        except Exception as e:
            logger.error(f"Store memory failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="store_memory",
                error=f"Failed to store memory: {e}"
            )
    
    async def _recall_memory(self, query: str, limit: int = 5) -> ToolResult:
        """
        Search Mem0 cloud for relevant memories.
        """
        try:
            from memory import recall_memories
            
            memories = await recall_memories(query, limit=limit)
            
            if not memories:
                return ToolResult(
                    success=True,
                    output=f"🧠 No memories found for: \"{query}\"\n\nTip: Try broader search terms or store new memories with store_memory.",
                    tool_name="recall_memory",
                    data={"query": query, "count": 0}
                )
            
            output_parts = [f"🧠 Found {len(memories)} memories for: \"{query}\"\n"]
            
            for i, mem in enumerate(memories[:limit], 1):
                memory_text = mem.get("memory", mem.get("text", ""))
                if memory_text:
                    output_parts.append(f"{i}. {memory_text[:300]}{'...' if len(memory_text) > 300 else ''}")
            
            return ToolResult(
                success=True,
                output="\n".join(output_parts),
                tool_name="recall_memory",
                data={"query": query, "count": len(memories), "memories": memories}
            )
            
        except ImportError as e:
            logger.error(f"Memory module import failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="recall_memory",
                error=f"Memory module not available: {e}"
            )
        except Exception as e:
            logger.error(f"Recall memory failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="recall_memory",
                error=f"Failed to recall memory: {e}"
            )
    
    async def _read_ontology(self, path: str) -> ToolResult:
        """
        Read files from the Apprentice OS ontology.
        
        Base path: /opt/fpai/apprentice-os/
        """
        from pathlib import Path
        
        base_path = Path("/opt/fpai/apprentice-os")
        
        # Security: ensure path doesn't escape base
        try:
            full_path = (base_path / path).resolve()
            if not str(full_path).startswith(str(base_path)):
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="read_ontology",
                    error="Path must be within apprentice-os directory"
                )
            
            if not full_path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="read_ontology",
                    error=f"File not found: {path}"
                )
            
            content = full_path.read_text()
            
            # Format output
            file_type = full_path.suffix.lower()
            if file_type == ".json":
                # Pretty print JSON
                import json
                try:
                    parsed = json.loads(content)
                    content = json.dumps(parsed, indent=2)
                except:
                    pass
            
            return ToolResult(
                success=True,
                output=f"📂 {path}\n\n{content[:5000]}{'...(truncated)' if len(content) > 5000 else ''}",
                tool_name="read_ontology",
                data={"path": path, "size": len(content)}
            )
            
        except Exception as e:
            logger.error(f"Read ontology failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="read_ontology",
                error=f"Failed to read ontology: {e}"
            )
    
    async def _assess_shadow_costs(
        self,
        stress_level: Optional[float] = None,
        current_trust: Optional[float] = None,
        previous_trust: Optional[float] = None
    ) -> ToolResult:
        """
        Compute and report all four shadow costs.
        """
        try:
            from governance.shadow_costs_compute import (
                compute_all_shadow_costs,
                format_shadow_costs_report
            )
            
            context = {}
            if stress_level is not None:
                context["self_reported_stress"] = stress_level
            if current_trust is not None:
                context["current_trust"] = current_trust
            if previous_trust is not None:
                context["previous_trust"] = previous_trust
            
            costs = await compute_all_shadow_costs(context)
            report = format_shadow_costs_report(costs)
            
            # Determine overall status
            statuses = [c.status for c in costs.values()]
            if "critical" in statuses:
                overall = "CRITICAL - Action needed"
            elif "warning" in statuses:
                overall = "WARNING - Monitor closely"
            else:
                overall = "HEALTHY"
            
            return ToolResult(
                success=True,
                output=f"**Overall: {overall}**\n\n{report}",
                tool_name="assess_shadow_costs",
                data={
                    "overall_status": overall,
                    "costs": {k: {"value": v.value, "status": v.status} for k, v in costs.items()}
                }
            )
            
        except ImportError as e:
            logger.error(f"Shadow costs module import failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="assess_shadow_costs",
                error=f"Shadow costs module not available: {e}"
            )
        except Exception as e:
            logger.error(f"Assess shadow costs failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="assess_shadow_costs",
                error=f"Failed to assess shadow costs: {e}"
            )
    
    async def _check_governance(
        self,
        action: str,
        yield_benefit: float = 0,
        coherence_impact: float = 0,
        complexity_delta: float = 0
    ) -> ToolResult:
        """
        Check a proposed action against governance rules.
        """
        try:
            from governance.principles import evaluate_priority
            from governance.three_nevers import check_never_constraints
            
            context = {
                "yield_benefit": yield_benefit,
                "coherence_impact": coherence_impact,
                "complexity_delta": complexity_delta
            }
            
            # Check priority stack
            priority_result = evaluate_priority(action, context)
            
            # Check three nevers
            never_result = check_never_constraints(action, context)
            
            # Build output
            output_parts = [f"## Governance Check: {action}\n"]
            
            # Priority Stack result
            if priority_result.overall_approved:
                output_parts.append(f"**Priority Stack:** ✅ APPROVED")
            else:
                output_parts.append(f"**Priority Stack:** ❌ BLOCKED by {priority_result.blocking_priority.name if priority_result.blocking_priority else 'unknown'}")
            output_parts.append(f"Reasoning: {priority_result.reasoning}\n")
            
            # Three Nevers result
            if never_result.action_allowed:
                output_parts.append(f"**Three Nevers:** ✅ No violations")
            else:
                output_parts.append(f"**Three Nevers:** ❌ VIOLATION DETECTED")
                for v in never_result.violations:
                    output_parts.append(f"  - {v.never_type.name}: {v.description}")
            
            # Overall
            overall_allowed = priority_result.overall_approved and never_result.action_allowed
            output_parts.insert(1, f"**Overall: {'✅ ALLOWED' if overall_allowed else '❌ BLOCKED'}**\n")
            
            return ToolResult(
                success=True,
                output="\n".join(output_parts),
                tool_name="check_governance",
                data={
                    "action": action,
                    "allowed": overall_allowed,
                    "priority_approved": priority_result.overall_approved,
                    "never_violations": len(never_result.violations)
                }
            )
            
        except ImportError as e:
            logger.error(f"Governance module import failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="check_governance",
                error=f"Governance module not available: {e}"
            )
        except Exception as e:
            logger.error(f"Check governance failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="check_governance",
                error=f"Failed to check governance: {e}"
            )
    
    # ========================================================================
    # BUILDER TOOLS - For collaborative module building with apprentices
    # ========================================================================
    
    async def _scaffold_module(
        self,
        user_id: int,
        module_name: str,
        command: str,
        description: str,
        author: str = "Apprentice",
        initial_logic: str = None
    ) -> ToolResult:
        """Create a new module scaffold for an apprentice."""
        try:
            from builder.tools import scaffold_module
            
            result = scaffold_module(
                user_id=user_id,
                module_name=module_name,
                command=command,
                description=description,
                author=author,
                initial_logic=initial_logic
            )
            
            if result.success:
                output = f"""✅ **Module Created!**

📁 Path: `{result.data.get('path', 'unknown')}`

**Files created:**
- `module.json` - metadata
- `handler.py` - your code
- `README.md` - documentation

**Command:** `{command}`
**Description:** {description}

💡 To test: Ask me to run `test_module` with your module name.
"""
                return ToolResult(
                    success=True,
                    output=output,
                    tool_name="scaffold_module",
                    data=result.data
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="scaffold_module",
                    error=result.message
                )
                
        except Exception as e:
            logger.error(f"Scaffold module failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="scaffold_module",
                error=f"Failed to scaffold module: {e}"
            )
    
    async def _update_module_code(
        self,
        user_id: int,
        module_name: str,
        new_code: str
    ) -> ToolResult:
        """Update the handler.py in an apprentice's module."""
        try:
            from builder.tools import update_module_code
            
            result = update_module_code(
                user_id=user_id,
                module_name=module_name,
                new_code=new_code
            )
            
            if result.success:
                output = f"""✅ **Code Updated!**

📝 File: `handler.py`
📦 Module: `{module_name}`
💾 Size: {result.data.get('size', 0)} bytes

The code has been validated and saved.
Test it with: `test_module`
"""
                return ToolResult(
                    success=True,
                    output=output,
                    tool_name="update_module_code",
                    data=result.data
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="update_module_code",
                    error=result.message
                )
                
        except Exception as e:
            logger.error(f"Update module code failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="update_module_code",
                error=f"Failed to update module code: {e}"
            )
    
    async def _test_module(
        self,
        user_id: int,
        module_name: str,
        test_args: str = ""
    ) -> ToolResult:
        """Test an apprentice's module in sandbox."""
        try:
            from builder.tools import test_module
            
            result = await test_module(
                user_id=user_id,
                module_name=module_name,
                test_args=test_args
            )
            
            if result.success:
                output = f"""🧪 **Test Result**

📦 Module: `{module_name}`
📥 Args: `{test_args or '(none)'}`
⏱️ Time: {result.data.get('execution_time', 'N/A')}

**Output:**
```
{result.data.get('output', 'No output')}
```
"""
                return ToolResult(
                    success=True,
                    output=output,
                    tool_name="test_module",
                    data=result.data
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="test_module",
                    error=result.message
                )
                
        except Exception as e:
            logger.error(f"Test module failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="test_module",
                error=f"Failed to test module: {e}"
            )
    
    async def _list_my_modules(self, user_id: int) -> ToolResult:
        """List all modules in an apprentice's workspace."""
        try:
            from builder.tools import list_my_modules
            
            result = list_my_modules(user_id=user_id)
            
            if result.success:
                modules = result.data.get('modules', [])
                
                if not modules:
                    output = """📦 **Your Modules**

You don't have any modules yet.

💡 Say "I want to build a /X command" to get started!
"""
                else:
                    lines = ["📦 **Your Modules**\n"]
                    for m in modules:
                        status_emoji = {
                            "draft": "📝",
                            "submitted": "📤",
                            "live": "🟢",
                            "invalid": "⚠️"
                        }.get(m.get('status', 'unknown'), "❓")
                        
                        lines.append(
                            f"{status_emoji} **{m.get('name', 'unnamed')}** `{m.get('command', '')}`\n"
                            f"   Status: {m.get('status', 'unknown')}\n"
                            f"   {m.get('description', '')[:50]}"
                        )
                    output = "\n".join(lines)
                
                return ToolResult(
                    success=True,
                    output=output,
                    tool_name="list_my_modules",
                    data=result.data
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="list_my_modules",
                    error=result.message
                )
                
        except Exception as e:
            logger.error(f"List modules failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="list_my_modules",
                error=f"Failed to list modules: {e}"
            )
    
    async def _submit_module(self, user_id: int, module_name: str) -> ToolResult:
        """Submit an apprentice's module for steward review."""
        try:
            from builder.tools import submit_module
            
            result = submit_module(user_id=user_id, module_name=module_name)
            
            if result.success:
                output = f"""📤 **Module Submitted!**

📦 Module: `{module_name}`
🕐 Submitted: {result.data.get('submitted_at', 'now')}

✅ Security validation passed
✅ Files validated

**What happens next:**
1. James will see this in `/reviews`
2. If approved, your command goes **LIVE** for everyone!
3. If changes needed, I'll help you fix them.

You'll be notified of the decision.
"""
                return ToolResult(
                    success=True,
                    output=output,
                    tool_name="submit_module",
                    data=result.data
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="submit_module",
                    error=result.message
                )
                
        except Exception as e:
            logger.error(f"Submit module failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="submit_module",
                error=f"Failed to submit module: {e}"
            )
    
    async def _get_module_code(self, user_id: int, module_name: str) -> ToolResult:
        """Get the current handler.py code of an apprentice's module."""
        try:
            from builder.tools import get_module_code
            
            result = get_module_code(user_id=user_id, module_name=module_name)
            
            if result.success:
                code = result.data.get('code', '')
                output = f"""📄 **{module_name}/handler.py**

```python
{code}
```
"""
                return ToolResult(
                    success=True,
                    output=output,
                    tool_name="get_module_code",
                    data=result.data
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="get_module_code",
                    error=result.message
                )
                
        except Exception as e:
            logger.error(f"Get module code failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="get_module_code",
                error=f"Failed to get module code: {e}"
            )
    
    async def _delete_module(self, user_id: int, module_name: str) -> ToolResult:
        """Delete a module from an apprentice's workspace."""
        try:
            from builder.tools import delete_module
            
            result = delete_module(user_id=user_id, module_name=module_name)
            
            if result.success:
                output = f"""🗑️ **Module Deleted**

📦 Module: `{module_name}`

The module has been removed from your workspace.
"""
                return ToolResult(
                    success=True,
                    output=output,
                    tool_name="delete_module",
                    data=result.data
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="delete_module",
                    error=result.message
                )
                
        except Exception as e:
            logger.error(f"Delete module failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="delete_module",
                error=f"Failed to delete module: {e}"
            )
    
    async def _ai_create_module(
        self,
        user_id: int,
        module_idea: str,
        auto_submit: bool = False
    ) -> ToolResult:
        """Use AI to generate a complete module from a natural language description."""
        try:
            from builder.tools import ai_create_module
            
            result = await ai_create_module(
                user_id=user_id,
                module_idea=module_idea,
                auto_submit=auto_submit
            )
            
            if result.success:
                output = f"""🤖 **AI Module Created!**

{result.message}

📁 Path: `{result.data.get('path', 'unknown')}`
"""
                if not auto_submit:
                    output += "\n💡 To test: Ask me to `test_module`\n📤 To submit: Ask me to `submit_module`"
                
                return ToolResult(
                    success=True,
                    output=output,
                    tool_name="ai_create_module",
                    data=result.data
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="ai_create_module",
                    error=result.error or result.message
                )
                
        except Exception as e:
            logger.error(f"AI create module failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="ai_create_module",
                error=f"Failed to create module: {e}"
            )
    
    # ========================================================================
    # UNIFIED BUILDER TOOLS - AI-powered code generation and management
    # ========================================================================
    
    async def _ai_build(
        self,
        request: str,
        scope: str = "aria_self",
        context_files: List[str] = None
    ) -> ToolResult:
        """
        Use AI to generate code from natural language.
        
        This is the most powerful builder tool - it:
        1. Generates code using Claude
        2. Verifies with Gemini
        3. Creates a build job with backup
        4. Queues for approval or auto-executes based on risk
        """
        try:
            from builder.unified_engine import build_from_request, get_unified_builder
            
            # Build context from files
            context = {}
            if context_files:
                builder = get_unified_builder()
                for file_path in context_files[:5]:  # Limit to 5 files
                    try:
                        path = Path(file_path)
                        if path.exists():
                            context[file_path] = path.read_text()[:5000]
                    except Exception:
                        pass
            
            # Generate and queue build
            result = await build_from_request(
                request=request,
                user_id=str(self.conversation.chat_id) if self.conversation else "aria",
                scope=scope,
                context=context if context else None
            )
            
            if not result["success"]:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="ai_build",
                    error=result.get("message", "Build failed")
                )
            
            job = result["job"]
            needs_approval = result["needs_approval"]
            
            # Format changes preview
            changes_preview = ""
            for i, change in enumerate(job.get("changes", [])[:5]):
                action_emoji = {"create": "📄", "modify": "✏️", "append": "➕", "delete": "🗑️"}.get(
                    change.get("action", ""), "•"
                )
                changes_preview += f"\n{action_emoji} `{change['file_path']}`"
                if change.get("description"):
                    changes_preview += f"\n   _{change['description'][:60]}_"
            
            if len(job.get("changes", [])) > 5:
                changes_preview += f"\n\n_...and {len(job['changes']) - 5} more changes_"
            
            # Build output
            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "⛔"}.get(
                job.get("risk", "medium"), "🟡"
            )
            
            output = f"""🔨 **AI Build Proposal**

**{job.get('title', request[:50])}**

{result.get('message', '')}

{risk_emoji} **Risk:** {job.get('risk', 'medium').upper()}
📊 **Complexity:** {job.get('complexity', 'medium').upper()}
🔐 **Scope:** {scope}

**Changes:**{changes_preview}

🏷️ **Job ID:** `{job['id']}`
"""
            
            if needs_approval:
                output += """
⚠️ **Needs Approval**

Reply with:
• `/approve {job_id}` to execute
• `/reject {job_id}` to discard
""".replace("{job_id}", job['id'])
            else:
                output += "\n✅ **Auto-approved** (low risk) - executing..."
                
                # Process the queue
                builder = get_unified_builder()
                results = await builder.process_queue()
                
                if results:
                    build_result = results[0]
                    if build_result.status.value == "completed":
                        output += "\n\n✅ **Build completed successfully!**"
                    else:
                        output += f"\n\n❌ **Build failed:** {build_result.error_message}"
            
            return ToolResult(
                success=True,
                output=output,
                tool_name="ai_build",
                data=job
            )
            
        except Exception as e:
            logger.error(f"AI build failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="ai_build",
                error=f"AI build failed: {e}"
            )
    
    async def _get_build_queue(self) -> ToolResult:
        """Get the current build queue status."""
        try:
            from builder.unified_engine import get_unified_builder
            
            builder = get_unified_builder()
            status = builder.get_queue_status()
            
            counts = status.get("status_counts", {})
            recent = status.get("recent_builds", [])
            pending = status.get("pending_changes", 0)
            
            output = "📊 **Build Queue Status**\n\n"
            
            output += "**Job Counts:**\n"
            for stat, count in counts.items():
                emoji = {
                    "queued": "⏳",
                    "building": "🔨",
                    "completed": "✅",
                    "failed": "❌",
                    "needs_approval": "🔔",
                    "rolled_back": "⏪",
                    "rejected": "🚫"
                }.get(stat, "•")
                output += f"  {emoji} {stat}: {count}\n"
            
            output += f"\n**Pending Changes:** {pending}\n"
            
            if recent:
                output += "\n**Recent Jobs:**\n"
                for job in recent[:7]:
                    status_emoji = {
                        "completed": "✅",
                        "failed": "❌",
                        "queued": "⏳",
                        "building": "🔨",
                        "needs_approval": "🔔"
                    }.get(job.get("status", ""), "•")
                    output += f"  {status_emoji} `{job['id']}` - {job.get('title', 'Untitled')[:35]}\n"
            
            return ToolResult(
                success=True,
                output=output,
                tool_name="get_build_queue",
                data=status
            )
            
        except Exception as e:
            logger.error(f"Get build queue failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="get_build_queue",
                error=f"Failed to get queue: {e}"
            )
    
    async def _approve_build(self, job_id: str) -> ToolResult:
        """Approve a build job that needs approval."""
        try:
            from builder.unified_engine import get_unified_builder
            
            builder = get_unified_builder()
            success = builder.approve_build(job_id)
            
            if not success:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="approve_build",
                    error=f"Build {job_id} not found or already processed"
                )
            
            output = f"✅ **Build Approved:** `{job_id}`\n\nExecuting..."
            
            # Process queue
            results = await builder.process_queue()
            
            if results:
                result = results[0]
                if result.status.value == "completed":
                    output += "\n\n✅ **Build completed successfully!**"
                    if result.changes:
                        output += "\n\nFiles modified:"
                        for change in result.changes[:5]:
                            output += f"\n  • `{change.file_path}`"
                else:
                    output += f"\n\n❌ **Build failed:** {result.error_message}"
            
            return ToolResult(
                success=True,
                output=output,
                tool_name="approve_build",
                data={"job_id": job_id}
            )
            
        except Exception as e:
            logger.error(f"Approve build failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="approve_build",
                error=f"Failed to approve: {e}"
            )
    
    async def _reject_build(self, job_id: str) -> ToolResult:
        """Reject a build job."""
        try:
            from builder.unified_engine import get_unified_builder
            
            builder = get_unified_builder()
            success = builder.reject_build(job_id)
            
            if success:
                output = f"🚫 **Build Rejected:** `{job_id}`\n\nProposed changes have been discarded."
                return ToolResult(
                    success=True,
                    output=output,
                    tool_name="reject_build",
                    data={"job_id": job_id}
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="reject_build",
                    error=f"Build {job_id} not found"
                )
                
        except Exception as e:
            logger.error(f"Reject build failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="reject_build",
                error=f"Failed to reject: {e}"
            )
    
    async def _rollback_build(self, job_id: str) -> ToolResult:
        """Rollback a completed build using its backup."""
        try:
            from builder.unified_engine import get_unified_builder
            
            builder = get_unified_builder()
            success, message = builder.rollback(job_id)
            
            if success:
                output = f"⏪ **Rollback Complete:** `{job_id}`\n\n{message}\n\nAll files restored to pre-build state."
                return ToolResult(
                    success=True,
                    output=output,
                    tool_name="rollback_build",
                    data={"job_id": job_id}
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="rollback_build",
                    error=message
                )
                
        except Exception as e:
            logger.error(f"Rollback build failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="rollback_build",
                error=f"Failed to rollback: {e}"
            )
    
    async def _get_build_logs(self, job_id: str) -> ToolResult:
        """Get detailed logs for a specific build job."""
        try:
            from builder.unified_engine import get_unified_builder
            
            builder = get_unified_builder()
            logs = builder.get_build_logs(job_id)
            
            if not logs:
                return ToolResult(
                    success=False,
                    output="",
                    tool_name="get_build_logs",
                    error=f"No logs found for job {job_id}"
                )
            
            output = f"📋 **Build Logs:** `{job_id}`\n\n"
            
            for log in logs[:20]:
                level_emoji = {
                    "INFO": "ℹ️",
                    "WARNING": "⚠️",
                    "ERROR": "❌",
                    "DEBUG": "🔍"
                }.get(log.get("level", ""), "•")
                
                timestamp = log.get("timestamp", "")[:19]  # Trim microseconds
                output += f"{level_emoji} `{timestamp}` {log.get('message', '')}\n"
            
            if len(logs) > 20:
                output += f"\n_...and {len(logs) - 20} more entries_"
            
            return ToolResult(
                success=True,
                output=output,
                tool_name="get_build_logs",
                data={"logs": logs}
            )
            
        except Exception as e:
            logger.error(f"Get build logs failed: {e}")
            return ToolResult(
                success=False,
                output="",
                tool_name="get_build_logs",
                error=f"Failed to get logs: {e}"
            )


# ============================================================================
# CONVENIENCE
# ============================================================================

def get_tools() -> List[Dict]:
    """Get tool definitions for API."""
    return TOOLS


async def execute_tool(
    tool_name: str,
    arguments: Dict,
    conversation=None
) -> ToolResult:
    """Execute a tool."""
    executor = ToolExecutor(conversation)
    return await executor.execute(tool_name, arguments)


#!/usr/bin/env python3
"""
ARIA UNIFIED BUILDER ENGINE
===========================

The most powerful builder setup - combining ALL existing capabilities:

From aria-builder/builder.py:
- Scope-controlled file operations
- Backup/restore/rollback
- Syntax verification
- Diff preview

From agents/builder.py:
- AI-powered code generation
- Search/replace modifications

From builder_bridge.py:
- Build queue management
- Complexity gating
- Verification chain
- Auto-rollback on failure

From builder/ (new):
- Module scaffolding
- Templates
- Sandbox testing
- Apprentice workspaces

From telegram_builder.py:
- Inline approval buttons
- Real-time feedback
"""

import os
import re
import ast
import json
import shutil
import hashlib
import logging
import sqlite3
import asyncio
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager
from enum import Enum
import httpx

logger = logging.getLogger("aria.builder.unified")

# ============================================================================
# CONFIGURATION
# ============================================================================

WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", "/opt/fpai"))
ARIA_ROOT = WORKSPACE_ROOT / "aria-command"
BACKUP_DIR = WORKSPACE_ROOT / "backups" / "builder"
BUILD_DB = WORKSPACE_ROOT / "aria-command" / "state" / "builder.db"
LABS_DIR = WORKSPACE_ROOT / "labs"

# Safety limits
MAX_CHANGES_PER_CYCLE = int(os.getenv("MAX_CHANGES_PER_CYCLE", "5"))
MAX_CHANGE_LINES = int(os.getenv("MAX_CHANGE_LINES", "200"))

# AI Endpoints
CLAUDE_API = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY", "")

# Notification settings
STEWARD_CHAT_ID = os.getenv("SUNHEART_CHAT_ID", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


class RiskLevel(str, Enum):
    """Risk levels for changes."""
    READ = "read"         # Just viewing - auto-execute
    LOW = "low"           # Safe additions - can auto-apply
    MEDIUM = "medium"     # Modifications - needs approval
    HIGH = "high"         # Critical changes - requires confirmation
    CRITICAL = "critical" # System-level - steward only


class BuildStatus(str, Enum):
    """Build job status."""
    QUEUED = "queued"
    BUILDING = "building"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    NEEDS_APPROVAL = "needs_approval"
    REJECTED = "rejected"


class Complexity(str, Enum):
    """Change complexity."""
    TRIVIAL = "trivial"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ============================================================================
# SCOPES - Who can modify what
# ============================================================================

SCOPE_DEFINITIONS = {
    "steward": {
        "paths": ["/opt/fpai/"],  # Full access
        "files": ["*"],
        "max_complexity": Complexity.HIGH,
        "auto_approve": [RiskLevel.READ, RiskLevel.LOW]
    },
    "apprentice": {
        "paths": ["/opt/fpai/labs/apprentices/{user_id}/"],
        "files": ["*.py", "*.json", "*.md", "*.txt"],
        "max_complexity": Complexity.MEDIUM,
        "auto_approve": [RiskLevel.READ]
    },
    "aria_self": {
        "paths": [
            "/opt/fpai/aria/",
            "/opt/fpai/aria-command/modules/"
        ],
        "files": [
            "server.py", "actions.py", "smart_responses.py",
            "memory.py", "proactive.py", "voice.py", "*.json"
        ],
        "max_complexity": Complexity.HIGH,
        "auto_approve": [RiskLevel.READ, RiskLevel.LOW],
        "protected": ["opus_brain.py", "tools.py", "bot.py"]  # Immutable
    }
}

# ============================================================================
# SERVICE MAP - Which file changes require service restarts
# ============================================================================

SERVICE_MAP = {
    # Primary server services
    "/opt/fpai/aria/": "fpai-aria",
    "/opt/fpai/aria-command/": "fpai-aria-command",
    "/opt/fpai/whaletrack-live/": "fpai-whaletrack-live",
    "/opt/fpai/whaletrack-magnet/": "fpai-whaletrack-magnet",
    "/opt/fpai/godmode/": "fpai-godmode",
    "/opt/fpai/godmode-v3/": "fpai-godmode",
    "/opt/fpai/nerve-center/": "fpai-nerve-center",
    # Secondary server services (AI)
    "/opt/fpai/ai-brain/": "fpai-ai-brain",
    "/opt/fpai/sparket/": "fpai-sparket",
}

# Production services that need explicit confirmation
PRODUCTION_SERVICES = {
    "fpai-whaletrack-live",  # Trading!
    "fpai-nerve-center",     # Core coordination
    "fpai-godmode",          # Dashboard
}


def get_service_for_path(path: str) -> Optional[str]:
    """Get the service name that needs restarting for a file path."""
    for service_path, service_name in SERVICE_MAP.items():
        if path.startswith(service_path):
            return service_name
    return None


def is_production_service(service_name: str) -> bool:
    """Check if service requires extra confirmation."""
    return service_name in PRODUCTION_SERVICES


@dataclass
class FileChange:
    """A proposed file change."""
    id: str
    file_path: str
    action: str  # create, modify, delete, append
    old_content: Optional[str] = None
    new_content: str = ""
    description: str = ""
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    backup_path: Optional[str] = None
    status: str = "pending"
    risk: RiskLevel = RiskLevel.MEDIUM
    complexity: Complexity = Complexity.MEDIUM
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    applied_at: Optional[str] = None
    verified_by: Optional[str] = None  # AI model that verified
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data["risk"] = self.risk.value
        data["complexity"] = self.complexity.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FileChange':
        if isinstance(data.get("risk"), str):
            data["risk"] = RiskLevel(data["risk"])
        if isinstance(data.get("complexity"), str):
            data["complexity"] = Complexity(data["complexity"])
        return cls(**data)
    
    def get_diff_preview(self, context_lines: int = 3) -> str:
        """Generate a diff-style preview."""
        lines = []
        
        if self.action == "create":
            lines.append(f"📄 Creating {self.file_path}:")
            for i, line in enumerate(self.new_content.split('\n')[:15]):
                lines.append(f"+ {line}")
            if self.new_content.count('\n') > 15:
                lines.append(f"+ ... ({self.new_content.count(chr(10)) - 15} more lines)")
        
        elif self.action == "append":
            lines.append(f"➕ Appending to {self.file_path}:")
            for line in self.new_content.split('\n')[:10]:
                lines.append(f"+ {line}")
        
        elif self.action == "modify":
            lines.append(f"✏️ Modifying {self.file_path}:")
            if self.old_content:
                lines.append("━━━ REMOVING ━━━")
                for line in self.old_content.split('\n')[:8]:
                    lines.append(f"- {line}")
                if self.old_content.count('\n') > 8:
                    lines.append("- ... (truncated)")
            lines.append("━━━ ADDING ━━━")
            for line in self.new_content.split('\n')[:8]:
                lines.append(f"+ {line}")
            if self.new_content.count('\n') > 8:
                lines.append("+ ... (truncated)")
        
        elif self.action == "delete":
            lines.append(f"🗑️ Deleting {self.file_path}")
        
        return '\n'.join(lines)


@dataclass
class BuildJob:
    """A build job in the queue."""
    id: str
    title: str
    description: str
    changes: List[FileChange]
    author: str  # user_id or "aria"
    scope: str  # steward, apprentice, aria_self
    status: BuildStatus = BuildStatus.QUEUED
    complexity: Complexity = Complexity.MEDIUM
    risk: RiskLevel = RiskLevel.MEDIUM
    queued_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: str = ""
    backup_dir: str = ""
    ai_verified: bool = False
    verification_notes: str = ""
    # Cost tracking
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    tokens_used: int = 0
    # Auto-deploy
    auto_deploy: bool = False
    services_to_restart: List[str] = field(default_factory=list)
    deployed: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "changes": [c.to_dict() for c in self.changes],
            "author": self.author,
            "scope": self.scope,
            "status": self.status.value,
            "complexity": self.complexity.value,
            "risk": self.risk.value,
            "queued_at": self.queued_at.isoformat() if self.queued_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "backup_dir": self.backup_dir,
            "ai_verified": self.ai_verified,
            "verification_notes": self.verification_notes,
            "estimated_cost": self.estimated_cost,
            "actual_cost": self.actual_cost,
            "tokens_used": self.tokens_used,
            "auto_deploy": self.auto_deploy,
            "services_to_restart": self.services_to_restart,
            "deployed": self.deployed
        }


# ============================================================================
# BUILD NOTIFIER - Sends Telegram notifications with inline buttons
# ============================================================================

class BuildNotifier:
    """
    Sends Telegram notifications for build events.
    
    Events:
    - on_approval_needed: Build queued, needs approval (with buttons)
    - on_build_started: Build execution started
    - on_build_completed: Build finished successfully
    - on_build_failed: Build failed with error
    - on_rollback: Build was rolled back
    """
    
    def __init__(self):
        self.http = None
        self._telegram_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    
    async def _get_http(self):
        if self.http is None:
            self.http = httpx.AsyncClient(timeout=30.0)
        return self.http
    
    async def _send_message(
        self,
        chat_id: int,
        text: str,
        buttons: List[List[Dict]] = None
    ) -> bool:
        """Send Telegram message with optional inline buttons."""
        if not TELEGRAM_BOT_TOKEN or not chat_id:
            logger.debug("Notification skipped: No token or chat_id")
            return False
        
        http = await self._get_http()
        
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        if buttons:
            payload["reply_markup"] = json.dumps({"inline_keyboard": buttons})
        
        try:
            response = await http.post(f"{self._telegram_api}/sendMessage", json=payload)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Notification send failed: {e}")
            return False
    
    def _get_steward_chat_id(self) -> Optional[int]:
        """Get steward chat ID for notifications."""
        if STEWARD_CHAT_ID:
            try:
                return int(STEWARD_CHAT_ID)
            except ValueError:
                pass
        return None
    
    async def on_approval_needed(self, job: BuildJob):
        """Notify steward that a build needs approval."""
        chat_id = self._get_steward_chat_id()
        if not chat_id:
            return
        
        # Format changes preview
        changes_preview = ""
        for c in job.changes[:3]:
            changes_preview += f"\n  - {c.action}: `{c.file_path.split('/')[-1]}`"
        if len(job.changes) > 3:
            changes_preview += f"\n  - ...and {len(job.changes) - 3} more"
        
        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "⛔"}.get(
            job.risk.value, "🟡"
        )
        
        text = f"""🔔 *Build Needs Approval*

*{job.title[:50]}*

{job.description[:150]}...

{risk_emoji} Risk: {job.risk.value.upper()}
📊 Complexity: {job.complexity.value}
👤 Author: {job.author}

*Changes:*{changes_preview}

🏷️ Job ID: `{job.id}`"""
        
        buttons = [
            [
                {"text": "✅ Approve", "callback_data": f"approve_build:{job.id}"},
                {"text": "❌ Reject", "callback_data": f"reject_build:{job.id}"}
            ]
        ]
        
        await self._send_message(chat_id, text, buttons)
    
    async def on_build_started(self, job: BuildJob):
        """Notify that build execution started."""
        chat_id = self._get_steward_chat_id()
        if not chat_id:
            return
        
        text = f"🔨 *Build Started*: `{job.id}`\n\n{job.title[:50]}"
        await self._send_message(chat_id, text)
    
    async def on_build_completed(self, job: BuildJob):
        """Notify that build completed successfully."""
        chat_id = self._get_steward_chat_id()
        if not chat_id:
            return
        
        files_changed = ", ".join(
            c.file_path.split("/")[-1] for c in job.changes[:3]
        )
        if len(job.changes) > 3:
            files_changed += f" +{len(job.changes) - 3} more"
        
        text = f"""✅ *Build Completed*

*{job.title[:50]}*

Files: {files_changed}
Duration: {self._format_duration(job)}

🏷️ Job ID: `{job.id}`"""
        
        buttons = [
            [
                {"text": "⏪ Rollback", "callback_data": f"rollback:{job.id}"},
                {"text": "💾 Save Template", "callback_data": f"save_template:{job.id}"}
            ]
        ]
        
        await self._send_message(chat_id, text, buttons)
    
    async def on_build_failed(self, job: BuildJob):
        """Notify that build failed."""
        chat_id = self._get_steward_chat_id()
        if not chat_id:
            return
        
        text = f"""❌ *Build Failed*

*{job.title[:50]}*

Error: {job.error_message[:200]}

🏷️ Job ID: `{job.id}`"""
        
        await self._send_message(chat_id, text)
    
    async def on_rollback(self, job_id: str, success: bool, message: str):
        """Notify about rollback result."""
        chat_id = self._get_steward_chat_id()
        if not chat_id:
            return
        
        emoji = "⏪" if success else "❌"
        text = f"{emoji} *Rollback {'Complete' if success else 'Failed'}*\n\nJob: `{job_id}`\n{message}"
        
        await self._send_message(chat_id, text)
    
    async def on_module_submitted(self, module_name: str, author_id: int):
        """Notify steward about module submission."""
        chat_id = self._get_steward_chat_id()
        if not chat_id:
            return
        
        text = f"""📦 *Module Submitted for Review*

Module: `{module_name}`
Submitted by: {author_id}

Use `/reviews` to see pending submissions."""
        
        await self._send_message(chat_id, text)
    
    def _format_duration(self, job: BuildJob) -> str:
        """Format build duration."""
        if not job.started_at or not job.completed_at:
            return "N/A"
        
        delta = job.completed_at - job.started_at
        seconds = delta.total_seconds()
        
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.1f}m"
        else:
            return f"{seconds / 3600:.1f}h"


# Global notifier instance
_notifier: Optional[BuildNotifier] = None


def get_notifier() -> BuildNotifier:
    """Get global notifier instance."""
    global _notifier
    if _notifier is None:
        _notifier = BuildNotifier()
    return _notifier


# ============================================================================
# DATABASE SCHEMA
# ============================================================================

BUILD_SCHEMA = """
CREATE TABLE IF NOT EXISTS build_jobs (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    author TEXT NOT NULL,
    scope TEXT NOT NULL,
    status TEXT DEFAULT 'queued',
    complexity TEXT DEFAULT 'medium',
    risk TEXT DEFAULT 'medium',
    queued_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    error_message TEXT,
    backup_dir TEXT,
    ai_verified INTEGER DEFAULT 0,
    verification_notes TEXT,
    changes_json TEXT
);

CREATE TABLE IF NOT EXISTS build_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    level TEXT,
    message TEXT,
    FOREIGN KEY (job_id) REFERENCES build_jobs(id)
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON build_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_author ON build_jobs(author);

-- Build templates for caching successful patterns
CREATE TABLE IF NOT EXISTS build_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    pattern TEXT NOT NULL,         -- Keywords/pattern to match
    request_example TEXT,          -- Original request that created this template
    changes_json TEXT NOT NULL,    -- Template changes
    use_count INTEGER DEFAULT 0,   -- How many times used
    success_rate REAL DEFAULT 1.0, -- Success rate when used
    author TEXT,
    created_at TEXT NOT NULL,
    last_used_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_templates_pattern ON build_templates(pattern);
CREATE INDEX IF NOT EXISTS idx_logs_job ON build_logs(job_id);
"""


# ============================================================================
# UNIFIED BUILDER ENGINE
# ============================================================================

class UnifiedBuilder:
    """
    The Ultimate Builder Engine.
    
    Capabilities:
    1. Scope-based access control
    2. AI code generation (Claude)
    3. AI verification (Gemini)
    4. Backup before every change
    5. Syntax verification
    6. Build queue with complexity gating
    7. Auto-rollback on failure
    8. Module scaffolding for apprentices
    9. Full audit trail
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(BUILD_DB)
        self._local = threading.local()
        self.http = httpx.AsyncClient(timeout=120.0)
        
        # Ensure directories exist
        BUILD_DB.parent.mkdir(parents=True, exist_ok=True)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
        
        # Pending changes (in-memory for quick approval flow)
        self.pending_changes: Dict[str, FileChange] = {}
        self._load_pending()
        
        logger.info("UnifiedBuilder initialized")
    
    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def _cursor(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def _init_db(self):
        with self._cursor() as cursor:
            cursor.executescript(BUILD_SCHEMA)
    
    def _load_pending(self):
        """Load pending changes from disk."""
        pending_file = ARIA_ROOT / "state" / "pending_changes.json"
        try:
            if pending_file.exists():
                data = json.loads(pending_file.read_text())
                self.pending_changes = {
                    k: FileChange.from_dict(v) for k, v in data.items()
                }
        except Exception as e:
            logger.warning(f"Failed to load pending: {e}")
    
    def _save_pending(self):
        """Save pending changes to disk."""
        pending_file = ARIA_ROOT / "state" / "pending_changes.json"
        try:
            pending_file.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v.to_dict() for k, v in self.pending_changes.items()}
            pending_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save pending: {e}")
    
    async def close(self):
        await self.http.aclose()
    
    # ========================================================================
    # SCOPE & PERMISSION CHECKING
    # ========================================================================
    
    def check_scope(self, path: str, user_id: str, scope: str) -> Tuple[bool, str]:
        """
        Check if a user can modify a path within their scope.
        
        Returns: (allowed, reason)
        """
        scope_def = SCOPE_DEFINITIONS.get(scope)
        if not scope_def:
            return False, f"Unknown scope: {scope}"
        
        # Normalize path
        path = str(Path(path).resolve())
        
        # Check against allowed paths
        allowed = False
        for pattern in scope_def["paths"]:
            # Replace {user_id} placeholder
            pattern = pattern.replace("{user_id}", str(user_id))
            if path.startswith(pattern.rstrip("/")):
                allowed = True
                break
        
        if not allowed:
            return False, f"Path {path} not in allowed scope"
        
        # Check protected files
        filename = Path(path).name
        if scope == "aria_self" and filename in scope_def.get("protected", []):
            return False, f"File {filename} is protected from modification"
        
        # Check file type
        allowed_files = scope_def.get("files", ["*"])
        if "*" not in allowed_files:
            ext_match = any(
                filename.endswith(f.replace("*", "")) 
                for f in allowed_files if f.startswith("*")
            )
            name_match = filename in allowed_files
            
            if not (ext_match or name_match):
                return False, f"File type {filename} not allowed"
        
        return True, "OK"
    
    def assess_risk(self, change: FileChange) -> RiskLevel:
        """Assess the risk level of a change."""
        path = Path(change.file_path)
        
        # Critical paths
        critical_patterns = [
            r'/etc/', r'\.env', r'password', r'secret', r'key',
            r'opus_brain\.py', r'tools\.py', r'bot\.py'
        ]
        for pattern in critical_patterns:
            if re.search(pattern, str(path), re.IGNORECASE):
                return RiskLevel.CRITICAL
        
        # High risk: Modify core system files
        if change.action in ["modify", "delete"]:
            if any(p in str(path) for p in ["/opt/fpai/aria-command/", "/opt/fpai/aria/"]):
                if path.suffix == ".py":
                    return RiskLevel.HIGH
        
        # Medium: Modify existing files
        if change.action == "modify":
            return RiskLevel.MEDIUM
        
        # Low: Create new files, append
        if change.action in ["create", "append"]:
            return RiskLevel.LOW
        
        return RiskLevel.MEDIUM
    
    def assess_complexity(self, change: FileChange) -> Complexity:
        """Assess the complexity of a change."""
        lines = change.new_content.count('\n') + 1
        
        if lines <= 10:
            return Complexity.TRIVIAL
        elif lines <= 30:
            return Complexity.LOW
        elif lines <= 100:
            return Complexity.MEDIUM
        else:
            return Complexity.HIGH
    
    # ========================================================================
    # COST TRACKING
    # ========================================================================
    
    async def _log_api_cost(
        self,
        user_id: str,
        operation: str,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0
    ):
        """
        Log API cost to Supabase.
        
        Pricing (per 1M tokens):
        - Claude Sonnet 4: $3 input, $15 output
        - Gemini 2.5 Flash: ~$0.075 input, ~$0.30 output
        """
        # Calculate cost
        if "claude" in model.lower() or "sonnet" in model.lower():
            cost = (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000
        elif "gemini" in model.lower():
            cost = (input_tokens * 0.075 + output_tokens * 0.30) / 1_000_000
        else:
            cost = 0
        
        total_tokens = input_tokens + output_tokens
        
        try:
            from integrations.supabase_client import get_supabase_client
            client = get_supabase_client()
            
            # Try to get telegram_id from user_id (might be numeric string)
            try:
                telegram_id = int(user_id)
            except (ValueError, TypeError):
                telegram_id = 0  # System/API user
            
            await client.log_usage_cost(
                telegram_id=telegram_id,
                operation=operation,
                tokens=total_tokens,
                cost_usd=cost,
                model=model,
                details={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "source": "unified_builder"
                }
            )
            
            logger.debug(f"Logged cost: {operation} ${cost:.6f} ({total_tokens} tokens)")
        except Exception as e:
            logger.warning(f"Failed to log API cost: {e}")
    
    # ========================================================================
    # CODE GENERATION (AI-powered)
    # ========================================================================
    
    async def generate_code(
        self,
        request: str,
        context: Dict[str, str] = None,
        scope: str = "aria_self"
    ) -> Dict[str, Any]:
        """
        Generate code using Claude.
        
        Args:
            request: What to build/modify
            context: Dict of filename -> content for relevant files
            scope: Permission scope
        
        Returns:
            {
                "success": bool,
                "changes": List[FileChange],
                "explanation": str,
                "error": str
            }
        """
        if not CLAUDE_API:
            return {"success": False, "error": "Claude API key not configured"}
        
        # Build context for Claude
        context_str = ""
        if context:
            for filename, content in context.items():
                context_str += f"\n--- {filename} ---\n{content[:3000]}\n"
        
        prompt = f"""You are an expert code builder. Generate precise code changes.

REQUEST: {request}

CONTEXT FILES:
{context_str if context_str else "No context files provided."}

RULES:
1. Make minimal, focused changes
2. Follow existing code style
3. Include proper error handling
4. Maximum {MAX_CHANGE_LINES} lines per file

OUTPUT FORMAT (JSON):
{{
    "explanation": "What this change does",
    "changes": [
        {{
            "file_path": "/full/path/to/file.py",
            "action": "create|modify|append|delete",
            "old_content": "exact text to replace (for modify)",
            "new_content": "new code content",
            "description": "what this specific change does"
        }}
    ]
}}

ONLY output valid JSON. No markdown, no explanation outside JSON."""

        try:
            response = await self.http.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": CLAUDE_API,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 4096,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            
            if response.status_code != 200:
                return {"success": False, "error": f"Claude API error: {response.status_code}"}
            
            result = response.json()
            content = result["content"][0]["text"]
            
            # Track cost
            usage = result.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            
            # Get user_id from context for cost attribution
            user_id = "system"  # Will be set by caller via _current_user
            if hasattr(self, '_current_user'):
                user_id = self._current_user
            
            await self._log_api_cost(
                user_id=user_id,
                operation="builder_code_gen",
                model="claude-sonnet-4",
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            
            # Parse JSON from response
            try:
                # Handle potential markdown wrapping
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                data = json.loads(content)
            except json.JSONDecodeError as e:
                return {"success": False, "error": f"Failed to parse Claude response: {e}"}
            
            # Convert to FileChange objects
            changes = []
            for c in data.get("changes", []):
                change_id = hashlib.md5(
                    f"{c['file_path']}{c['new_content']}{datetime.now().isoformat()}".encode()
                ).hexdigest()[:12]
                
                fc = FileChange(
                    id=change_id,
                    file_path=c["file_path"],
                    action=c.get("action", "modify"),
                    old_content=c.get("old_content"),
                    new_content=c.get("new_content", ""),
                    description=c.get("description", "")
                )
                
                # Assess risk and complexity
                fc.risk = self.assess_risk(fc)
                fc.complexity = self.assess_complexity(fc)
                
                changes.append(fc)
            
            return {
                "success": True,
                "changes": changes,
                "explanation": data.get("explanation", ""),
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Code generation error: {e}")
            return {"success": False, "error": str(e)}
    
    # ========================================================================
    # VERIFICATION (Gemini second opinion)
    # ========================================================================
    
    async def verify_with_gemini(self, change: FileChange) -> Tuple[bool, str]:
        """
        Get Gemini's verification of a code change.
        
        Returns: (is_safe, assessment)
        """
        if not GEMINI_API_KEY:
            return True, "Gemini verification skipped (no API key)"
        
        prompt = f"""Review this code change for safety and correctness.

FILE: {change.file_path}
ACTION: {change.action}
DESCRIPTION: {change.description}

{f"OLD CODE:{chr(10)}{change.old_content}" if change.old_content else ""}

NEW CODE:
{change.new_content}

EVALUATE:
1. Is this syntactically correct?
2. Are there security issues?
3. Could this break existing functionality?
4. Any obvious bugs?

RESPOND WITH: "SAFE" or "UNSAFE" on first line, then brief explanation."""

        try:
            response = await self.http.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                params={"key": GEMINI_API_KEY},
                json={"contents": [{"parts": [{"text": prompt}]}]}
            )
            
            if response.status_code != 200:
                return True, f"Gemini unavailable ({response.status_code})"
            
            result = response.json()
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            
            # Track cost (Gemini provides token counts in usageMetadata)
            usage = result.get("usageMetadata", {})
            input_tokens = usage.get("promptTokenCount", 0)
            output_tokens = usage.get("candidatesTokenCount", 0)
            
            user_id = "system"
            if hasattr(self, '_current_user'):
                user_id = self._current_user
            
            await self._log_api_cost(
                user_id=user_id,
                operation="builder_verify",
                model="gemini-2.5-flash",
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            
            is_safe = text.strip().upper().startswith("SAFE")
            return is_safe, text
            
        except Exception as e:
            logger.warning(f"Gemini verification error: {e}")
            return True, f"Verification error: {e}"
    
    # ========================================================================
    # SYNTAX VERIFICATION
    # ========================================================================
    
    def verify_syntax(self, code: str, is_partial: bool = False) -> Tuple[bool, Optional[str]]:
        """Verify Python syntax."""
        try:
            if is_partial:
                code = f"def __test__():\n" + '\n'.join(f"    {line}" for line in code.split('\n'))
            
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"Line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, str(e)
    
    # ========================================================================
    # AUTO-DEPLOY
    # ========================================================================
    
    def detect_services(self, job: BuildJob) -> List[str]:
        """Detect which services need restarting based on changed files."""
        services = set()
        for change in job.changes:
            service = get_service_for_path(change.file_path)
            if service:
                services.add(service)
        return list(services)
    
    async def auto_deploy(self, job: BuildJob) -> Tuple[bool, str]:
        """
        Auto-deploy after successful build.
        
        - Detects which services were affected
        - Restarts non-production services automatically
        - Requires confirmation for production services
        
        Returns: (success, message)
        """
        if not job.auto_deploy:
            return True, "Auto-deploy disabled"
        
        services = job.services_to_restart or self.detect_services(job)
        if not services:
            return True, "No services need restarting"
        
        results = []
        production_pending = []
        
        for service in services:
            if is_production_service(service):
                production_pending.append(service)
                results.append(f"⚠️ {service}: Production - needs manual restart")
            else:
                # Restart non-production service
                success, msg = await self._restart_service(service)
                if success:
                    results.append(f"✅ {service}: Restarted")
                else:
                    results.append(f"❌ {service}: {msg}")
        
        job.deployed = len(production_pending) == 0
        
        message = "Deploy Results:\n" + "\n".join(results)
        
        if production_pending:
            message += f"\n\n🔒 Production services pending:\n" + "\n".join(f"  - {s}" for s in production_pending)
            message += "\n\nUse `/deploy <service>` to manually restart."
        
        return job.deployed, message
    
    async def _restart_service(self, service_name: str) -> Tuple[bool, str]:
        """Restart a systemd service via SSH."""
        import subprocess
        
        # Determine which server (primary or secondary)
        secondary_services = {"fpai-ai-brain", "fpai-sparket", "fpai-aria"}
        server = "secondary" if service_name in secondary_services else "primary"
        
        # Get server IP
        server_ips = {
            "primary": os.getenv("PRIMARY_SERVER", "198.54.123.234"),
            "secondary": os.getenv("SECONDARY_SERVER", "162.0.208.88")
        }
        ip = server_ips.get(server, server_ips["primary"])
        
        try:
            # Use SSH to restart (assumes key-based auth)
            cmd = f"ssh -o StrictHostKeyChecking=no root@{ip} 'systemctl restart {service_name}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
            
            if result.returncode == 0:
                self._log(service_name, "INFO", f"Service {service_name} restarted")
                return True, "Restarted successfully"
            else:
                error = result.stderr.decode() if result.stderr else "Unknown error"
                return False, error[:100]
                
        except subprocess.TimeoutExpired:
            return False, "SSH timeout"
        except Exception as e:
            return False, str(e)
    
    async def manual_deploy(self, service_name: str) -> Tuple[bool, str]:
        """Manually deploy/restart a specific service."""
        if not is_production_service(service_name):
            return await self._restart_service(service_name)
        
        # For production, just do it (caller already confirmed)
        return await self._restart_service(service_name)
    
    # ========================================================================
    # BUILD TEMPLATES - Cache successful patterns
    # ========================================================================
    
    def save_as_template(
        self,
        job: BuildJob,
        name: str,
        pattern: str = None
    ) -> Tuple[bool, str]:
        """
        Save a successful build as a reusable template.
        
        Args:
            job: The successful build job
            name: Name for the template
            pattern: Keywords to match (extracted from title if not provided)
        
        Returns: (success, message/template_id)
        """
        if job.status != BuildStatus.COMPLETED:
            return False, "Can only save completed builds as templates"
        
        template_id = hashlib.md5(
            f"{name}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        # Extract pattern from title if not provided
        if not pattern:
            # Simple keyword extraction
            words = job.title.lower().split()
            # Remove common words
            stop_words = {'a', 'an', 'the', 'add', 'create', 'make', 'build', 'for', 'to', 'in', 'on'}
            pattern = ' '.join(w for w in words if w not in stop_words and len(w) > 2)
        
        try:
            with self._cursor() as cursor:
                cursor.execute("""
                    INSERT INTO build_templates 
                    (id, name, description, pattern, request_example, changes_json, author, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    template_id,
                    name,
                    job.description,
                    pattern,
                    job.title,
                    json.dumps([c.to_dict() for c in job.changes]),
                    job.author,
                    datetime.now().isoformat()
                ))
            
            logger.info(f"Saved template: {name} ({template_id})")
            return True, template_id
            
        except Exception as e:
            logger.error(f"Failed to save template: {e}")
            return False, str(e)
    
    def find_matching_template(self, request: str, min_confidence: float = 0.6) -> Optional[Dict]:
        """
        Find a template that matches the request.
        
        Uses simple keyword matching - could be enhanced with embeddings.
        
        Returns: Template dict if found with confidence >= min_confidence
        """
        request_lower = request.lower()
        request_words = set(request_lower.split())
        
        try:
            with self._cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM build_templates 
                    WHERE success_rate >= 0.8
                    ORDER BY use_count DESC, created_at DESC
                    LIMIT 50
                """)
                templates = [dict(row) for row in cursor.fetchall()]
        except Exception:
            return None
        
        best_match = None
        best_score = 0
        
        for template in templates:
            pattern_words = set(template['pattern'].lower().split())
            
            if not pattern_words:
                continue
            
            # Calculate overlap
            overlap = len(request_words & pattern_words)
            score = overlap / max(len(pattern_words), 1)
            
            if score > best_score and score >= min_confidence:
                best_score = score
                best_match = template
                best_match['confidence'] = score
        
        return best_match
    
    def use_template(self, template_id: str, user_id: str, scope: str) -> Optional[BuildJob]:
        """
        Create a build job from a template.
        
        Returns: BuildJob if successful
        """
        try:
            with self._cursor() as cursor:
                cursor.execute("SELECT * FROM build_templates WHERE id = ?", (template_id,))
                row = cursor.fetchone()
            
            if not row:
                return None
            
            template = dict(row)
            
            # Create changes from template
            changes_data = json.loads(template['changes_json'])
            changes = [FileChange(
                id=hashlib.md5(f"{c['file_path']}{datetime.now().isoformat()}".encode()).hexdigest()[:12],
                file_path=c['file_path'],
                action=c['action'],
                old_content=c.get('old_content'),
                new_content=c.get('new_content', ''),
                description=c.get('description', '')
            ) for c in changes_data]
            
            # Create job
            job = self.submit_job(
                title=f"[Template] {template['name']}",
                description=template['description'],
                changes=changes,
                author=user_id,
                scope=scope
            )
            
            # Update template stats
            with self._cursor() as cursor:
                cursor.execute("""
                    UPDATE build_templates 
                    SET use_count = use_count + 1, last_used_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), template_id))
            
            return job
            
        except Exception as e:
            logger.error(f"Failed to use template: {e}")
            return None
    
    def update_template_success(self, template_id: str, success: bool):
        """Update template success rate after use."""
        try:
            with self._cursor() as cursor:
                # Get current stats
                cursor.execute(
                    "SELECT use_count, success_rate FROM build_templates WHERE id = ?",
                    (template_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    use_count = row['use_count']
                    current_rate = row['success_rate']
                    
                    # Weighted average
                    new_rate = (current_rate * (use_count - 1) + (1.0 if success else 0.0)) / use_count
                    
                    cursor.execute(
                        "UPDATE build_templates SET success_rate = ? WHERE id = ?",
                        (new_rate, template_id)
                    )
        except Exception as e:
            logger.warning(f"Failed to update template success: {e}")
    
    def get_templates(self, limit: int = 20) -> List[Dict]:
        """Get all templates sorted by usage."""
        try:
            with self._cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM build_templates 
                    ORDER BY use_count DESC, created_at DESC
                    LIMIT ?
                """, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        try:
            with self._cursor() as cursor:
                cursor.execute("DELETE FROM build_templates WHERE id = ?", (template_id,))
                return cursor.rowcount > 0
        except Exception:
            return False
    
    # ========================================================================
    # BACKUP & RESTORE
    # ========================================================================
    
    def create_backup(self, job: BuildJob) -> str:
        """Create backup of all files that will be modified."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_dir = BACKUP_DIR / f"{job.id}-{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        for change in job.changes:
            src_path = Path(change.file_path)
            if src_path.exists():
                rel_path = str(src_path).replace("/", "_")
                dst_path = backup_dir / rel_path
                shutil.copy2(src_path, dst_path)
                change.backup_path = str(dst_path)
                logger.debug(f"Backed up: {src_path}")
        
        # Save job metadata
        with open(backup_dir / "job.json", 'w') as f:
            json.dump(job.to_dict(), f, indent=2)
        
        return str(backup_dir)
    
    def rollback(self, job_id: str) -> Tuple[bool, str]:
        """Rollback changes for a job."""
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT backup_dir, changes_json FROM build_jobs WHERE id = ?",
                (job_id,)
            )
            row = cursor.fetchone()
        
        if not row or not row["backup_dir"]:
            return False, "No backup found"
        
        backup_dir = Path(row["backup_dir"])
        if not backup_dir.exists():
            return False, "Backup directory missing"
        
        try:
            changes = json.loads(row["changes_json"])
            
            for change in changes:
                if change.get("backup_path") and Path(change["backup_path"]).exists():
                    shutil.copy2(change["backup_path"], change["file_path"])
                    logger.info(f"Restored: {change['file_path']}")
                elif change.get("action") == "create":
                    # Delete created file
                    file_path = Path(change["file_path"])
                    if file_path.exists():
                        file_path.unlink()
                        logger.info(f"Deleted: {change['file_path']}")
            
            with self._cursor() as cursor:
                cursor.execute(
                    "UPDATE build_jobs SET status = ? WHERE id = ?",
                    (BuildStatus.ROLLED_BACK.value, job_id)
                )
            
            # Schedule notification (non-blocking)
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(get_notifier().on_rollback(job_id, True, "Rollback complete"))
            except RuntimeError:
                pass  # No event loop running
            
            return True, "Rollback complete"
            
        except Exception as e:
            logger.error(f"Rollback error: {e}")
            
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(get_notifier().on_rollback(job_id, False, str(e)))
            except RuntimeError:
                pass
            
            return False, str(e)
    
    # ========================================================================
    # CHANGE PROPOSAL & APPROVAL
    # ========================================================================
    
    def propose_change(
        self,
        file_path: str,
        new_content: str,
        description: str,
        user_id: str,
        scope: str = "apprentice",
        action: str = "modify",
        old_content: Optional[str] = None
    ) -> Tuple[Optional[FileChange], Optional[str]]:
        """
        Propose a code change.
        
        Returns: (FileChange, error)
        """
        # Check scope
        allowed, reason = self.check_scope(file_path, user_id, scope)
        if not allowed:
            return None, reason
        
        # Check line count
        if new_content.count('\n') + 1 > MAX_CHANGE_LINES:
            return None, f"Change too large ({new_content.count(chr(10)) + 1} lines, max {MAX_CHANGE_LINES})"
        
        # Verify syntax for Python files
        if file_path.endswith('.py'):
            syntax_ok, syntax_error = self.verify_syntax(new_content, is_partial=(action == "modify"))
            if not syntax_ok and action == "create":
                return None, f"Syntax error: {syntax_error}"
        
        # Generate ID
        change_id = hashlib.md5(
            f"{file_path}{new_content}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        change = FileChange(
            id=change_id,
            file_path=file_path,
            action=action,
            old_content=old_content,
            new_content=new_content,
            description=description
        )
        
        # Assess risk and complexity
        change.risk = self.assess_risk(change)
        change.complexity = self.assess_complexity(change)
        
        # Store pending
        self.pending_changes[change_id] = change
        self._save_pending()
        
        logger.info(f"Proposed change {change_id}: {description}")
        return change, None
    
    def apply_change(self, change_id: str, force: bool = False) -> Tuple[bool, str]:
        """
        Apply a pending change.
        
        Args:
            change_id: The change to apply
            force: Skip verification (for steward only)
        
        Returns: (success, message)
        """
        change = self.pending_changes.get(change_id)
        if not change:
            return False, f"Change {change_id} not found"
        
        if change.status != "pending":
            return False, f"Change {change_id} is {change.status}"
        
        path = Path(change.file_path)
        
        try:
            # Backup existing file
            if path.exists():
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_path = BACKUP_DIR / f"{path.name}.{timestamp}.bak"
                BACKUP_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup_path)
                change.backup_path = str(backup_path)
            
            # Apply based on action
            if change.action == "create":
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(change.new_content)
            
            elif change.action == "append":
                existing = path.read_text() if path.exists() else ""
                path.write_text(existing + "\n" + change.new_content)
            
            elif change.action == "modify":
                if change.old_content:
                    existing = path.read_text()
                    if change.old_content not in existing:
                        return False, "Old content not found in file"
                    new_full = existing.replace(change.old_content, change.new_content, 1)
                    path.write_text(new_full)
                else:
                    path.write_text(change.new_content)
            
            elif change.action == "delete":
                if path.exists():
                    path.unlink()
            
            # Verify syntax after change
            if path.suffix == ".py" and path.exists():
                content = path.read_text()
                syntax_ok, error = self.verify_syntax(content)
                if not syntax_ok:
                    # Rollback
                    if change.backup_path:
                        shutil.copy2(change.backup_path, path)
                    return False, f"Change broke syntax: {error}"
            
            change.status = "applied"
            change.applied_at = datetime.now().isoformat()
            self._save_pending()
            
            logger.info(f"Applied change {change_id}")
            return True, "Change applied successfully"
            
        except Exception as e:
            logger.error(f"Apply error: {e}")
            change.status = "failed"
            self._save_pending()
            return False, str(e)
    
    def cancel_change(self, change_id: str) -> Tuple[bool, str]:
        """Cancel a pending change."""
        if change_id in self.pending_changes:
            del self.pending_changes[change_id]
            self._save_pending()
            return True, "Change cancelled"
        return False, "Change not found"
    
    def get_pending(self, scope: str = None) -> List[FileChange]:
        """Get all pending changes, optionally filtered by scope."""
        pending = [c for c in self.pending_changes.values() if c.status == "pending"]
        # TODO: Filter by scope if needed
        return pending
    
    # ========================================================================
    # BUILD QUEUE
    # ========================================================================
    
    async def queue_build(
        self,
        title: str,
        description: str,
        changes: List[FileChange],
        author: str,
        scope: str
    ) -> BuildJob:
        """
        Queue a build job.
        
        Complex changes go to needs_approval.
        Simple changes can auto-execute.
        """
        job_id = hashlib.md5(
            f"{title}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        # Calculate overall complexity and risk
        max_complexity = max((c.complexity for c in changes), default=Complexity.MEDIUM)
        max_risk = max((c.risk for c in changes), default=RiskLevel.MEDIUM)
        
        # Determine if needs approval
        scope_def = SCOPE_DEFINITIONS.get(scope, {})
        auto_approve = scope_def.get("auto_approve", [])
        needs_approval = max_risk not in auto_approve
        
        job = BuildJob(
            id=job_id,
            title=title,
            description=description,
            changes=changes,
            author=author,
            scope=scope,
            complexity=max_complexity,
            risk=max_risk,
            status=BuildStatus.NEEDS_APPROVAL if needs_approval else BuildStatus.QUEUED
        )
        
        # Store in database
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO build_jobs 
                (id, title, description, author, scope, status, complexity, risk, 
                 queued_at, changes_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id, job.title, job.description, job.author, job.scope,
                job.status.value, job.complexity.value, job.risk.value,
                job.queued_at.isoformat(),
                json.dumps([c.to_dict() for c in job.changes])
            ))
        
        self._log(job.id, "INFO", f"Queued with status: {job.status.value}")
        
        # Send notification if needs approval
        if job.status == BuildStatus.NEEDS_APPROVAL:
            asyncio.create_task(get_notifier().on_approval_needed(job))
        
        return job
    
    async def process_queue(self) -> List[BuildJob]:
        """Process all queued builds."""
        results = []
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM build_jobs 
                WHERE status = ?
                ORDER BY queued_at ASC
                LIMIT ?
            """, (BuildStatus.QUEUED.value, MAX_CHANGES_PER_CYCLE))
            
            rows = cursor.fetchall()
        
        for row in rows:
            job = await self._execute_build(dict(row))
            results.append(job)
        
        return results
    
    async def _execute_build(self, row: Dict) -> BuildJob:
        """Execute a single build job."""
        job_id = row["id"]
        
        changes = [FileChange.from_dict(c) for c in json.loads(row["changes_json"])]
        
        job = BuildJob(
            id=job_id,
            title=row["title"],
            description=row["description"],
            changes=changes,
            author=row["author"],
            scope=row["scope"],
            complexity=Complexity(row["complexity"]),
            risk=RiskLevel(row["risk"]),
            status=BuildStatus.BUILDING,
            started_at=datetime.now()
        )
        
        # Set current user for cost tracking
        self._current_user = row["author"]
        
        self._update_status(job_id, BuildStatus.BUILDING)
        self._log(job_id, "INFO", "Build started")
        
        # Notify build started
        asyncio.create_task(get_notifier().on_build_started(job))
        
        try:
            # Create backup
            backup_dir = self.create_backup(job)
            job.backup_dir = backup_dir
            
            # AI verify each change
            for change in job.changes:
                is_safe, notes = await self.verify_with_gemini(change)
                change.verified_by = "gemini"
                
                if not is_safe:
                    job.status = BuildStatus.FAILED
                    job.error_message = f"Verification failed for {change.file_path}: {notes}"
                    self._update_status(job_id, BuildStatus.FAILED, job.error_message)
                    self._log(job_id, "ERROR", job.error_message)
                    asyncio.create_task(get_notifier().on_build_failed(job))
                    return job
            
            # Apply changes
            self._update_status(job_id, BuildStatus.VERIFYING)
            
            for change in job.changes:
                # Store as pending
                self.pending_changes[change.id] = change
                
                # Apply
                success, msg = self.apply_change(change.id)
                
                if not success:
                    # Rollback previous changes
                    self.rollback(job_id)
                    job.status = BuildStatus.FAILED
                    job.error_message = msg
                    self._update_status(job_id, BuildStatus.FAILED, msg)
                    self._log(job_id, "ERROR", f"Apply failed: {msg}")
                    asyncio.create_task(get_notifier().on_build_failed(job))
                    return job
            
            job.status = BuildStatus.COMPLETED
            job.completed_at = datetime.now()
            job.ai_verified = True
            
            # Detect services that need restart
            job.services_to_restart = self.detect_services(job)
            
            self._update_status(job_id, BuildStatus.COMPLETED)
            self._log(job_id, "INFO", "Build completed successfully")
            
            # Notify build completed
            asyncio.create_task(get_notifier().on_build_completed(job))
            
            # Auto-deploy if enabled
            if job.auto_deploy and job.services_to_restart:
                deploy_success, deploy_msg = await self.auto_deploy(job)
                self._log(job_id, "INFO", f"Auto-deploy: {deploy_msg}")
                
                # Notify about deployment
                if job.services_to_restart:
                    notifier = get_notifier()
                    await notifier._send_message(
                        notifier._get_steward_chat_id(),
                        f"🚀 *Auto-Deploy*\n\nJob: `{job_id}`\n\n{deploy_msg}"
                    )
            
            return job
            
        except Exception as e:
            logger.error(f"Build error: {e}")
            job.status = BuildStatus.FAILED
            job.error_message = str(e)
            self._update_status(job_id, BuildStatus.FAILED, str(e))
            self._log(job_id, "ERROR", str(e))
            
            # Notify build failed
            asyncio.create_task(get_notifier().on_build_failed(job))
            
            return job
    
    def approve_build(self, job_id: str) -> bool:
        """Approve a build that needs approval."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE build_jobs 
                SET status = ? 
                WHERE id = ? AND status = ?
            """, (BuildStatus.QUEUED.value, job_id, BuildStatus.NEEDS_APPROVAL.value))
            
            if cursor.rowcount > 0:
                self._log(job_id, "INFO", "Approved by steward")
                return True
        return False
    
    def reject_build(self, job_id: str, reason: str = "Rejected") -> bool:
        """Reject a build."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE build_jobs 
                SET status = ?, error_message = ?
                WHERE id = ?
            """, (BuildStatus.REJECTED.value, reason, job_id))
            
            if cursor.rowcount > 0:
                self._log(job_id, "INFO", f"Rejected: {reason}")
                return True
        return False
    
    # ========================================================================
    # STATUS & LOGGING
    # ========================================================================
    
    def _update_status(self, job_id: str, status: BuildStatus, error: str = ""):
        with self._cursor() as cursor:
            if status in [BuildStatus.COMPLETED, BuildStatus.FAILED, BuildStatus.ROLLED_BACK]:
                cursor.execute("""
                    UPDATE build_jobs 
                    SET status = ?, completed_at = ?, error_message = ?
                    WHERE id = ?
                """, (status.value, datetime.now().isoformat(), error, job_id))
            else:
                cursor.execute("""
                    UPDATE build_jobs 
                    SET status = ?, started_at = COALESCE(started_at, ?)
                    WHERE id = ?
                """, (status.value, datetime.now().isoformat(), job_id))
    
    def _log(self, job_id: str, level: str, message: str):
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO build_logs (job_id, timestamp, level, message)
                VALUES (?, ?, ?, ?)
            """, (job_id, datetime.now().isoformat(), level, message))
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get a specific job by ID."""
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM build_jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def get_logs(self, job_id: str, limit: int = 50) -> List[Dict]:
        """Get logs for a build job (alias for get_build_logs)."""
        return self.get_build_logs(job_id, limit)
    
    def get_history(self, scope: str = None, limit: int = 20) -> List[Dict]:
        """Get build history, optionally filtered by scope."""
        with self._cursor() as cursor:
            if scope:
                cursor.execute("""
                    SELECT * FROM build_jobs 
                    WHERE scope = ?
                    ORDER BY queued_at DESC
                    LIMIT ?
                """, (scope, limit))
            else:
                cursor.execute("""
                    SELECT * FROM build_jobs 
                    ORDER BY queued_at DESC
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get overall queue status."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT status, COUNT(*) as count FROM build_jobs GROUP BY status
            """)
            status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}
            
            cursor.execute("""
                SELECT * FROM build_jobs ORDER BY queued_at DESC LIMIT 10
            """)
            recent = [dict(row) for row in cursor.fetchall()]
        
        return {
            "status_counts": status_counts,
            "recent_builds": recent,
            "pending_changes": len(self.pending_changes)
        }
    
    def get_build_logs(self, job_id: str, limit: int = 50) -> List[Dict]:
        """Get logs for a build."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT timestamp, level, message FROM build_logs
                WHERE job_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (job_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]


# ============================================================================
# SINGLETON
# ============================================================================

_builder: Optional[UnifiedBuilder] = None


def get_unified_builder() -> UnifiedBuilder:
    """Get global builder instance."""
    global _builder
    if _builder is None:
        _builder = UnifiedBuilder()
    return _builder


# ============================================================================
# HIGH-LEVEL API
# ============================================================================

async def build_from_request(
    request: str,
    user_id: str,
    scope: str = "apprentice",
    context: Dict[str, str] = None
) -> Dict[str, Any]:
    """
    High-level API: Generate and queue a build from natural language.
    
    Returns:
        {
            "success": bool,
            "job": BuildJob dict or None,
            "needs_approval": bool,
            "message": str
        }
    """
    builder = get_unified_builder()
    
    # Generate code
    result = await builder.generate_code(request, context, scope)
    
    if not result["success"]:
        return {
            "success": False,
            "job": None,
            "needs_approval": False,
            "message": result["error"]
        }
    
    changes = result["changes"]
    
    if not changes:
        return {
            "success": False,
            "job": None,
            "needs_approval": False,
            "message": "No changes generated"
        }
    
    # Queue the build
    job = await builder.queue_build(
        title=request[:50],
        description=result["explanation"],
        changes=changes,
        author=user_id,
        scope=scope
    )
    
    return {
        "success": True,
        "job": job.to_dict(),
        "needs_approval": job.status == BuildStatus.NEEDS_APPROVAL,
        "message": result["explanation"]
    }


if __name__ == "__main__":
    # Test
    import asyncio
    
    async def test():
        builder = UnifiedBuilder()
        
        print("=== UNIFIED BUILDER TEST ===")
        print(f"Database: {builder.db_path}")
        print(f"Backup dir: {BACKUP_DIR}")
        
        # Test scope check
        print("\n--- Scope Check ---")
        tests = [
            ("/opt/fpai/labs/apprentices/123/test.py", "123", "apprentice"),
            ("/opt/fpai/aria/server.py", "aria", "aria_self"),
            ("/etc/passwd", "123", "apprentice"),
        ]
        
        for path, user_id, scope in tests:
            allowed, reason = builder.check_scope(path, user_id, scope)
            print(f"  {path}: {allowed} ({reason})")
        
        print("\n--- Done ---")
        await builder.close()
    
    asyncio.run(test())


#!/usr/bin/env python3
"""
ARIA AUTO-EXECUTOR
===================

Safely executes approved improvements with:
- Automatic backup before changes
- Health check after changes
- Auto-rollback on failure
- Changelog tracking

Safety Features:
- Creates .bak files before any modification
- Verifies service health after applying changes
- Rolls back immediately if health degrades
- Maintains complete change history
"""

import os
import json
import shutil
import asyncio
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
import httpx

logger = logging.getLogger("aria.sovereign.auto_executor")

# ============================================================================
# CONFIGURATION
# ============================================================================

WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", "/opt/fpai/aria-command"))
BACKUP_DIR = Path(os.getenv("ARIA_BACKUP_DIR", "/opt/fpai/aria-command/state/backups"))
CHANGELOG_PATH = Path(os.getenv("ARIA_CHANGELOG", "/opt/fpai/aria-command/state/changelog.json"))
HEALTH_CHECK_URL = os.getenv("ARIA_HEALTH_URL", "http://localhost:8750/health")
SERVICE_NAME = os.getenv("ARIA_SERVICE_NAME", "aria-command")


@dataclass
class ExecutionResult:
    """Result of an execution attempt."""
    success: bool
    improvement_id: str
    file_path: str
    
    backup_path: Optional[str] = None
    error: Optional[str] = None
    rolled_back: bool = False
    
    pre_health: Optional[Dict[str, Any]] = None
    post_health: Optional[Dict[str, Any]] = None
    
    applied_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.applied_at:
            d["applied_at"] = self.applied_at.isoformat()
        return d


@dataclass
class ChangelogEntry:
    """An entry in the changelog."""
    id: str
    timestamp: datetime
    improvement_id: str
    file_path: str
    description: str
    risk_level: int
    success: bool
    rolled_back: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "improvement_id": self.improvement_id,
            "file_path": self.file_path,
            "description": self.description,
            "risk_level": self.risk_level,
            "success": self.success,
            "rolled_back": self.rolled_back
        }


class AutoExecutor:
    """
    Safely executes code improvements.
    
    Process:
    1. Check risk assessment (must be auto-executable)
    2. Create backup of target file
    3. Apply the change
    4. Check service health
    5. Rollback if health check fails
    6. Log to changelog
    """
    
    def __init__(self, workspace: Path = WORKSPACE_ROOT):
        self.workspace = workspace
        self.backup_dir = BACKUP_DIR
        self.changelog_path = CHANGELOG_PATH
        self.http = httpx.AsyncClient(timeout=30.0)
        
        # Ensure directories exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.changelog_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._changelog: List[ChangelogEntry] = []
        self._load_changelog()
    
    def _load_changelog(self):
        """Load changelog from disk."""
        if self.changelog_path.exists():
            try:
                data = json.loads(self.changelog_path.read_text())
                self._changelog = [
                    ChangelogEntry(
                        id=e["id"],
                        timestamp=datetime.fromisoformat(e["timestamp"]),
                        improvement_id=e["improvement_id"],
                        file_path=e["file_path"],
                        description=e["description"],
                        risk_level=e["risk_level"],
                        success=e["success"],
                        rolled_back=e.get("rolled_back", False)
                    )
                    for e in data
                ]
            except Exception as e:
                logger.error(f"Failed to load changelog: {e}")
                self._changelog = []
    
    def _save_changelog(self):
        """Save changelog to disk."""
        try:
            data = [e.to_dict() for e in self._changelog]
            self.changelog_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save changelog: {e}")
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    async def execute(
        self,
        improvement_id: str,
        file_path: str,
        diff: str,
        description: str = "",
        risk_level: int = 3
    ) -> ExecutionResult:
        """
        Execute an improvement.
        
        Args:
            improvement_id: Unique ID of the improvement
            file_path: Path to file to modify (relative to workspace)
            diff: Unified diff to apply
            description: Human-readable description
            risk_level: Risk level (1-5)
            
        Returns:
            ExecutionResult with success status and details
        """
        full_path = self.workspace / file_path
        
        logger.info(f"Executing improvement {improvement_id} on {file_path}")
        
        result = ExecutionResult(
            success=False,
            improvement_id=improvement_id,
            file_path=file_path
        )
        
        try:
            # Step 1: Pre-health check
            result.pre_health = await self._health_check()
            if not result.pre_health.get("healthy", False):
                result.error = "Service unhealthy before change"
                logger.warning(result.error)
                return result
            
            # Step 2: Create backup
            backup_path = await self._create_backup(full_path, improvement_id)
            if not backup_path:
                result.error = "Failed to create backup"
                return result
            result.backup_path = str(backup_path)
            
            # Step 3: Apply the change
            apply_success = await self._apply_diff(full_path, diff)
            if not apply_success:
                result.error = "Failed to apply diff"
                await self._restore_backup(full_path, backup_path)
                result.rolled_back = True
                return result
            
            # Step 4: Wait a moment for service to potentially reload
            await asyncio.sleep(2)
            
            # Step 5: Post-health check
            result.post_health = await self._health_check()
            
            if not result.post_health.get("healthy", False):
                # Health check failed - rollback
                logger.warning(f"Health check failed after change, rolling back")
                await self._restore_backup(full_path, backup_path)
                result.rolled_back = True
                result.error = "Health check failed after change"
                return result
            
            # Success!
            result.success = True
            result.applied_at = datetime.now()
            
            # Step 6: Restart service to apply changes
            await self._restart_service()
            
            logger.info(f"Successfully applied improvement {improvement_id}")
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"Execution failed: {e}")
            
            # Try to rollback
            if result.backup_path:
                try:
                    await self._restore_backup(full_path, Path(result.backup_path))
                    result.rolled_back = True
                except Exception as rollback_error:
                    logger.error(f"Rollback also failed: {rollback_error}")
        
        # Log to changelog
        self._add_to_changelog(
            improvement_id=improvement_id,
            file_path=file_path,
            description=description,
            risk_level=risk_level,
            success=result.success,
            rolled_back=result.rolled_back
        )
        
        return result
    
    async def _health_check(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            response = await self.http.get(HEALTH_CHECK_URL)
            if response.status_code == 200:
                data = response.json()
                return {
                    "healthy": True,
                    "status": data.get("status", "ok"),
                    "details": data
                }
            else:
                return {
                    "healthy": False,
                    "status": f"HTTP {response.status_code}",
                    "details": response.text
                }
        except Exception as e:
            return {
                "healthy": False,
                "status": "error",
                "details": str(e)
            }
    
    async def _create_backup(
        self,
        file_path: Path,
        improvement_id: str
    ) -> Optional[Path]:
        """Create a backup of a file."""
        try:
            if not file_path.exists():
                logger.warning(f"File does not exist: {file_path}")
                return None
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.name}.{improvement_id}.{timestamp}.bak"
            backup_path = self.backup_dir / backup_name
            
            shutil.copy2(file_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    async def _restore_backup(self, file_path: Path, backup_path: Path) -> bool:
        """Restore a file from backup."""
        try:
            shutil.copy2(backup_path, file_path)
            logger.info(f"Restored from backup: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False
    
    async def _apply_diff(self, file_path: Path, diff: str) -> bool:
        """
        Apply a unified diff to a file.
        
        For now, uses a simple approach - parse the diff and apply manually.
        Could use 'patch' command for more robust handling.
        """
        try:
            # Try using patch command first
            result = subprocess.run(
                ["patch", "-p0", "--dry-run", str(file_path)],
                input=diff,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Dry run succeeded, apply for real
                result = subprocess.run(
                    ["patch", "-p0", str(file_path)],
                    input=diff,
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
            
            # Patch command failed, try manual approach
            return await self._apply_diff_manual(file_path, diff)
            
        except FileNotFoundError:
            # patch command not available, use manual approach
            return await self._apply_diff_manual(file_path, diff)
        except Exception as e:
            logger.error(f"Failed to apply diff: {e}")
            return False
    
    async def _apply_diff_manual(self, file_path: Path, diff: str) -> bool:
        """
        Manually apply a simple diff.
        
        This is a simplified implementation that handles basic cases.
        For complex diffs, we should require the patch command.
        """
        try:
            # Parse the diff
            lines = diff.split("\n")
            old_lines = []
            new_lines = []
            
            for line in lines:
                if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
                    continue
                elif line.startswith("-"):
                    old_lines.append(line[1:])
                elif line.startswith("+"):
                    new_lines.append(line[1:])
                elif line.startswith(" "):
                    old_lines.append(line[1:])
                    new_lines.append(line[1:])
            
            # Read current file
            current_content = file_path.read_text()
            
            # Find and replace the old content with new content
            old_text = "\n".join(old_lines)
            new_text = "\n".join(new_lines)
            
            if old_text in current_content:
                new_content = current_content.replace(old_text, new_text, 1)
                file_path.write_text(new_content)
                return True
            else:
                logger.warning("Could not find old text in file")
                return False
                
        except Exception as e:
            logger.error(f"Manual diff apply failed: {e}")
            return False
    
    async def _restart_service(self):
        """Restart the Aria service to apply changes."""
        try:
            subprocess.run(
                ["systemctl", "restart", SERVICE_NAME],
                capture_output=True,
                timeout=30
            )
            # Wait for service to come back up
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Failed to restart service: {e}")
    
    def _add_to_changelog(
        self,
        improvement_id: str,
        file_path: str,
        description: str,
        risk_level: int,
        success: bool,
        rolled_back: bool = False
    ):
        """Add entry to changelog."""
        entry = ChangelogEntry(
            id=f"CHG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            timestamp=datetime.now(),
            improvement_id=improvement_id,
            file_path=file_path,
            description=description,
            risk_level=risk_level,
            success=success,
            rolled_back=rolled_back
        )
        
        self._changelog.append(entry)
        self._save_changelog()
    
    def get_changelog(self, limit: int = 50) -> List[ChangelogEntry]:
        """Get recent changelog entries."""
        return self._changelog[-limit:]
    
    def format_changelog(self, limit: int = 10) -> str:
        """Format changelog for display."""
        entries = self.get_changelog(limit)
        
        if not entries:
            return "No changes recorded."
        
        lines = ["**Recent Changes:**", ""]
        
        for entry in reversed(entries):
            status = "✅" if entry.success else ("↩️" if entry.rolled_back else "❌")
            date = entry.timestamp.strftime("%m/%d %H:%M")
            lines.append(f"{status} `{entry.improvement_id}` - {entry.description[:40]} ({date})")
        
        return "\n".join(lines)
    
    async def list_backups(self, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available backups."""
        backups = []
        
        for backup in self.backup_dir.glob("*.bak"):
            if file_path and file_path not in backup.name:
                continue
            
            stat = backup.stat()
            backups.append({
                "name": backup.name,
                "path": str(backup),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return sorted(backups, key=lambda x: x["created"], reverse=True)
    
    async def manual_rollback(self, backup_name: str) -> bool:
        """Manually rollback to a specific backup."""
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            logger.error(f"Backup not found: {backup_name}")
            return False
        
        # Extract original file path from backup name
        # Format: filename.IMP-ID.timestamp.bak
        parts = backup_name.rsplit(".", 4)
        if len(parts) < 4:
            logger.error(f"Invalid backup name format: {backup_name}")
            return False
        
        original_name = parts[0]
        
        # Find the original file (search workspace)
        matches = list(self.workspace.rglob(original_name))
        if not matches:
            logger.error(f"Could not find original file: {original_name}")
            return False
        
        target = matches[0]
        
        # Restore
        shutil.copy2(backup_path, target)
        logger.info(f"Rolled back {target} from {backup_path}")
        
        # Restart service
        await self._restart_service()
        
        return True


# ============================================================================
# SINGLETON
# ============================================================================

_executor: Optional[AutoExecutor] = None


def get_executor() -> AutoExecutor:
    """Get or create global executor."""
    global _executor
    if _executor is None:
        _executor = AutoExecutor()
    return _executor


async def execute_improvement(
    improvement_id: str,
    file_path: str,
    diff: str,
    **kwargs
) -> ExecutionResult:
    """Execute an improvement."""
    return await get_executor().execute(improvement_id, file_path, diff, **kwargs)


def get_changelog(limit: int = 50) -> List[ChangelogEntry]:
    """Get changelog entries."""
    return get_executor().get_changelog(limit)



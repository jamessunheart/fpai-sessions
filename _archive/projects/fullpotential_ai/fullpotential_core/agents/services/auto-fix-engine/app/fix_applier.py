"""Applies fixes to codebase"""

from typing import List
from pathlib import Path
import subprocess
import shutil
from datetime import datetime

from .models import Fix


class FixApplier:
    """Applies generated fixes to the codebase"""

    def __init__(self):
        """Initialize fix applier"""
        pass

    def apply_fixes(self, fixes: List[Fix]) -> dict:
        """
        Apply a list of fixes to the codebase.

        Returns:
            {
                "applied": int,
                "failed": int,
                "details": []
            }
        """
        results = {
            "applied": 0,
            "failed": 0,
            "details": []
        }

        for fix in fixes:
            try:
                # Backup files before modifying
                self._backup_files(fix.files_to_modify)

                # Apply file changes
                for file_path, new_content in fix.changes.items():
                    self._apply_file_change(file_path, new_content)
                    results["details"].append(f"✅ Updated {file_path}")

                # Run commands (e.g., pip install)
                for command in fix.commands:
                    self._run_command(command, Path(fix.files_to_modify[0]).parent)
                    results["details"].append(f"✅ Ran: {command}")

                results["applied"] += 1

            except Exception as e:
                results["failed"] += 1
                results["details"].append(f"❌ Failed to apply fix: {str(e)}")

                # Restore from backup
                self._restore_files(fix.files_to_modify)

        return results

    def _backup_files(self, file_paths: List[str]):
        """Backup files before modification"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for file_path in file_paths:
            path = Path(file_path)
            if path.exists():
                backup_path = path.parent / f"{path.name}.backup.{timestamp}"
                shutil.copy2(path, backup_path)

    def _restore_files(self, file_paths: List[str]):
        """Restore files from backup"""
        for file_path in file_paths:
            path = Path(file_path)
            # Find most recent backup
            backups = list(path.parent.glob(f"{path.name}.backup.*"))
            if backups:
                latest_backup = max(backups, key=lambda p: p.stat().st_mtime)
                shutil.copy2(latest_backup, path)

    def _apply_file_change(self, file_path: str, new_content: str):
        """Apply a file change"""
        path = Path(file_path)

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write new content
        with open(path, 'w') as f:
            f.write(new_content)

    def _run_command(self, command: str, cwd: Path):
        """Run a shell command"""
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            raise Exception(f"Command failed: {result.stderr}")

        return result.stdout

"""
Backup Manager for Consciousness Optimizer

Provides backup and version control for all optimizations:
- Creates backups before applying optimizations
- Tracks versions of all changes
- Enables rollback to previous states
- Maintains change history
"""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import hashlib


class BackupManager:
    """
    Manages backups and version control for consciousness optimizations.
    
    Features:
    - Pre-optimization backups
    - Version tracking
    - Rollback capability
    - Change history
    """

    def __init__(self, backup_dir: str = "/opt/fpai/backups/consciousness_optimizer"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.versions_file = self.backup_dir / "versions.json"
        self.versions_history: List[Dict[str, Any]] = []

    def create_backup(self, optimization_id: str, config_before: Dict[str, Any], optimization: Dict[str, Any]) -> str:
        """
        Create a backup before applying an optimization.
        
        Returns backup_id for later rollback.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        backup_id = f"backup_{optimization_id}_{int(datetime.now(timezone.utc).timestamp())}"
        
        backup_data = {
            "backup_id": backup_id,
            "optimization_id": optimization_id,
            "timestamp": timestamp,
            "config_before": config_before,
            "optimization": optimization,
            "backup_type": "pre_optimization"
        }
        
        # Save backup file
        backup_file = self.backup_dir / f"{backup_id}.json"
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        # Update versions history
        self.versions_history.append({
            "backup_id": backup_id,
            "optimization_id": optimization_id,
            "timestamp": timestamp,
            "action": "backup_created",
            "status": "success"
        })
        
        self._save_versions_history()
        
        return backup_id

    def create_version_snapshot(self, service_name: str, config: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a version snapshot of a service configuration.
        
        Returns version_id for tracking.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        config_hash = hashlib.md5(json.dumps(config, sort_keys=True).encode()).hexdigest()[:8]
        version_id = f"v{int(datetime.now(timezone.utc).timestamp())}_{config_hash}"
        
        snapshot = {
            "version_id": version_id,
            "service_name": service_name,
            "timestamp": timestamp,
            "config": config,
            "metadata": metadata or {},
            "snapshot_type": "version_control"
        }
        
        # Save snapshot
        snapshot_file = self.backup_dir / f"{service_name}_{version_id}.json"
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot, f, indent=2)
        
        # Update versions history
        self.versions_history.append({
            "version_id": version_id,
            "service_name": service_name,
            "timestamp": timestamp,
            "action": "snapshot_created",
            "status": "success"
        })
        
        self._save_versions_history()
        
        return version_id

    def get_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a backup by ID"""
        backup_file = self.backup_dir / f"{backup_id}.json"
        if backup_file.exists():
            with open(backup_file, 'r') as f:
                return json.load(f)
        return None

    def rollback_to_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        Rollback to a previous backup state.
        
        Returns rollback result with restored configuration.
        """
        backup = self.get_backup(backup_id)
        if not backup:
            return {
                "status": "error",
                "error": f"Backup {backup_id} not found"
            }
        
        # Restore configuration
        restored_config = backup.get("config_before", {})
        
        # Log rollback
        self.versions_history.append({
            "backup_id": backup_id,
            "optimization_id": backup.get("optimization_id"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "rollback",
            "status": "success",
            "restored_config": restored_config
        })
        
        self._save_versions_history()
        
        return {
            "status": "rolled_back",
            "backup_id": backup_id,
            "restored_config": restored_config,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def get_version_history(self, service_name: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get version history, optionally filtered by service"""
        history = self.versions_history
        
        if service_name:
            history = [v for v in history if v.get("service_name") == service_name]
        
        return history[-limit:]

    def list_backups(self, optimization_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all backups, optionally filtered by optimization_id"""
        backups = []
        
        for backup_file in self.backup_dir.glob("backup_*.json"):
            try:
                with open(backup_file, 'r') as f:
                    backup_data = json.load(f)
                    if not optimization_id or backup_data.get("optimization_id") == optimization_id:
                        backups.append({
                            "backup_id": backup_data.get("backup_id"),
                            "optimization_id": backup_data.get("optimization_id"),
                            "timestamp": backup_data.get("timestamp"),
                            "backup_type": backup_data.get("backup_type")
                        })
            except Exception:
                continue
        
        return sorted(backups, key=lambda x: x.get("timestamp", ""), reverse=True)

    def _save_versions_history(self):
        """Save versions history to file"""
        with open(self.versions_file, 'w') as f:
            json.dump(self.versions_history, f, indent=2)

    def _load_versions_history(self):
        """Load versions history from file"""
        if self.versions_file.exists():
            try:
                with open(self.versions_file, 'r') as f:
                    self.versions_history = json.load(f)
            except Exception:
                self.versions_history = []

    def get_latest_backup(self, optimization_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest backup for an optimization"""
        backups = self.list_backups(optimization_id)
        if backups:
            return self.get_backup(backups[0]["backup_id"])
        return None















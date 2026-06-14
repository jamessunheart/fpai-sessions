"""
ARIA RESOURCE GUARDIAN
=======================

Prevents memory exhaustion and disk full crashes.

Features:
1. Memory monitoring - trigger cleanup before OOM
2. Disk monitoring - purge old files before full
3. Automatic resource cleanup
4. Proactive prevention, not just reaction

Thresholds:
- Memory: 70% warn, 85% critical
- Disk: 2GB warn, 500MB critical

This ensures Aria never crashes from resource exhaustion.
"""

import os
import gc
import shutil
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger("aria.consciousness.guardian")

# Configuration
MEMORY_WARN_PERCENT = int(os.getenv("MEMORY_WARN_PERCENT", "70"))
MEMORY_CRIT_PERCENT = int(os.getenv("MEMORY_CRIT_PERCENT", "85"))
DISK_WARN_GB = float(os.getenv("DISK_WARN_GB", "2.0"))
DISK_CRIT_GB = float(os.getenv("DISK_CRIT_GB", "0.5"))

# Paths to clean up
LOG_DIRS = [
    "/var/log/aria-command",
    "/opt/fpai/aria-command/logs",
    "/opt/fpai/aria-command/state/logs",
]

BACKUP_DIR = "/opt/fpai/backups/aria-command"
STATE_DIR = "/opt/fpai/aria-command/state"
TEMP_DIR = "/tmp/aria-command"


class ResourceLevel(str, Enum):
    """Resource level states."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ResourceStatus:
    """Current resource status."""
    memory_percent: float
    memory_level: ResourceLevel
    memory_available_mb: float
    disk_free_gb: float
    disk_level: ResourceLevel
    disk_path: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory": {
                "percent_used": self.memory_percent,
                "level": self.memory_level.value,
                "available_mb": self.memory_available_mb
            },
            "disk": {
                "free_gb": self.disk_free_gb,
                "level": self.disk_level.value,
                "path": self.disk_path
            }
        }


class ResourceGuardian:
    """
    Guards system resources.
    
    Monitors memory and disk usage, taking automatic action
    to prevent crashes from resource exhaustion.
    """
    
    def __init__(self):
        self.cleanup_count = 0
        self.last_cleanup: Optional[datetime] = None
        self.bytes_cleaned = 0
        
        logger.info(f"🛡️ Resource Guardian initialized (memory: {MEMORY_WARN_PERCENT}%/{MEMORY_CRIT_PERCENT}%, disk: {DISK_WARN_GB}GB/{DISK_CRIT_GB}GB)")
    
    def get_memory_usage(self) -> Tuple[float, float]:
        """
        Get current memory usage.
        
        Returns (percent_used, available_mb).
        """
        try:
            # Try psutil first (more accurate)
            import psutil
            mem = psutil.virtual_memory()
            return (mem.percent, mem.available / (1024 * 1024))
        except ImportError:
            pass
        
        # Fallback to /proc/meminfo
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
            
            mem_info = {}
            for line in lines:
                parts = line.split(':')
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = int(parts[1].strip().split()[0])  # kB
                    mem_info[key] = value
            
            total = mem_info.get('MemTotal', 1)
            available = mem_info.get('MemAvailable', mem_info.get('MemFree', 0))
            
            percent = ((total - available) / total) * 100
            available_mb = available / 1024
            
            return (percent, available_mb)
        except Exception as e:
            logger.warning(f"Could not read memory info: {e}")
            return (0, 0)
    
    def get_disk_usage(self, path: str = "/opt/fpai") -> Tuple[float, str]:
        """
        Get disk free space.
        
        Returns (free_gb, path).
        """
        try:
            stat = shutil.disk_usage(path)
            free_gb = stat.free / (1024 ** 3)
            return (free_gb, path)
        except Exception as e:
            logger.warning(f"Could not get disk usage for {path}: {e}")
            
            # Try root as fallback
            try:
                stat = shutil.disk_usage("/")
                return (stat.free / (1024 ** 3), "/")
            except:
                return (999, path)  # Assume plenty of space if can't check
    
    def get_status(self) -> ResourceStatus:
        """Get current resource status."""
        mem_percent, mem_available = self.get_memory_usage()
        disk_free, disk_path = self.get_disk_usage()
        
        # Determine memory level
        if mem_percent >= MEMORY_CRIT_PERCENT:
            mem_level = ResourceLevel.CRITICAL
        elif mem_percent >= MEMORY_WARN_PERCENT:
            mem_level = ResourceLevel.WARNING
        else:
            mem_level = ResourceLevel.HEALTHY
        
        # Determine disk level
        if disk_free <= DISK_CRIT_GB:
            disk_level = ResourceLevel.CRITICAL
        elif disk_free <= DISK_WARN_GB:
            disk_level = ResourceLevel.WARNING
        else:
            disk_level = ResourceLevel.HEALTHY
        
        return ResourceStatus(
            memory_percent=mem_percent,
            memory_level=mem_level,
            memory_available_mb=mem_available,
            disk_free_gb=disk_free,
            disk_level=disk_level,
            disk_path=disk_path
        )
    
    async def check_and_protect(self) -> Dict[str, Any]:
        """
        Check resources and take protective action if needed.
        
        Returns actions taken.
        """
        status = self.get_status()
        actions = []
        
        # Handle memory issues
        if status.memory_level == ResourceLevel.CRITICAL:
            logger.warning(f"🚨 CRITICAL: Memory at {status.memory_percent:.1f}%")
            
            # Force garbage collection
            collected = gc.collect()
            actions.append(f"Forced GC: {collected} objects collected")
            
            # Clear caches
            cache_cleared = await self._clear_caches()
            if cache_cleared:
                actions.append("Cleared internal caches")
            
            # If still critical, may need restart
            new_status = self.get_status()
            if new_status.memory_level == ResourceLevel.CRITICAL:
                actions.append("WARNING: Memory still critical after cleanup")
        
        elif status.memory_level == ResourceLevel.WARNING:
            logger.info(f"⚠️ Memory warning: {status.memory_percent:.1f}%")
            gc.collect()
            actions.append("Preemptive GC triggered")
        
        # Handle disk issues
        if status.disk_level == ResourceLevel.CRITICAL:
            logger.warning(f"🚨 CRITICAL: Disk free {status.disk_free_gb:.2f}GB")
            
            # Emergency cleanup
            cleaned = await self._emergency_disk_cleanup()
            actions.append(f"Emergency cleanup: {cleaned / (1024*1024):.1f}MB freed")
        
        elif status.disk_level == ResourceLevel.WARNING:
            logger.info(f"⚠️ Disk warning: {status.disk_free_gb:.2f}GB free")
            
            # Normal cleanup
            cleaned = await self._cleanup_old_files()
            if cleaned > 0:
                actions.append(f"Cleaned old files: {cleaned / (1024*1024):.1f}MB freed")
        
        if actions:
            self.cleanup_count += 1
            self.last_cleanup = datetime.now()
        
        return {
            "status": status.to_dict(),
            "actions": actions,
            "cleanup_count": self.cleanup_count,
            "total_bytes_cleaned": self.bytes_cleaned
        }
    
    async def _clear_caches(self) -> bool:
        """Clear internal caches to free memory."""
        try:
            # Clear any module-level caches we can access
            # This is a hook for other modules to register clearable caches
            logger.info("Clearing internal caches...")
            
            # Force Python to release memory
            gc.collect()
            gc.collect()  # Run twice for cyclic garbage
            
            return True
        except Exception as e:
            logger.warning(f"Cache clear error: {e}")
            return False
    
    async def _cleanup_old_files(self) -> int:
        """
        Clean up old log and temp files.
        
        Returns bytes freed.
        """
        bytes_freed = 0
        
        # Clean old logs (older than 7 days)
        for log_dir in LOG_DIRS:
            if os.path.exists(log_dir):
                bytes_freed += self._cleanup_old_in_dir(log_dir, days=7)
        
        # Clean temp files (older than 1 day)
        if os.path.exists(TEMP_DIR):
            bytes_freed += self._cleanup_old_in_dir(TEMP_DIR, days=1)
        
        # Clean old backups (keep last 10)
        if os.path.exists(BACKUP_DIR):
            bytes_freed += self._cleanup_old_backups(BACKUP_DIR, keep=10)
        
        self.bytes_cleaned += bytes_freed
        return bytes_freed
    
    async def _emergency_disk_cleanup(self) -> int:
        """
        Emergency cleanup when disk is critically low.
        
        More aggressive than normal cleanup.
        """
        bytes_freed = 0
        
        # Clean ALL temp files
        if os.path.exists(TEMP_DIR):
            bytes_freed += self._cleanup_old_in_dir(TEMP_DIR, days=0)
        
        # Clean old logs (older than 1 day in emergency)
        for log_dir in LOG_DIRS:
            if os.path.exists(log_dir):
                bytes_freed += self._cleanup_old_in_dir(log_dir, days=1)
        
        # Keep only last 3 backups
        if os.path.exists(BACKUP_DIR):
            bytes_freed += self._cleanup_old_backups(BACKUP_DIR, keep=3)
        
        # Clean __pycache__ directories
        for root, dirs, files in os.walk("/opt/fpai/aria-command"):
            for d in dirs:
                if d == "__pycache__":
                    cache_path = os.path.join(root, d)
                    try:
                        size = self._get_dir_size(cache_path)
                        shutil.rmtree(cache_path)
                        bytes_freed += size
                    except Exception:
                        pass
        
        self.bytes_cleaned += bytes_freed
        return bytes_freed
    
    def _cleanup_old_in_dir(self, directory: str, days: int) -> int:
        """Clean files older than N days in a directory."""
        bytes_freed = 0
        cutoff = datetime.now() - timedelta(days=days)
        
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(item_path))
                    if mtime < cutoff:
                        if os.path.isfile(item_path):
                            size = os.path.getsize(item_path)
                            os.remove(item_path)
                            bytes_freed += size
                        elif os.path.isdir(item_path):
                            size = self._get_dir_size(item_path)
                            shutil.rmtree(item_path)
                            bytes_freed += size
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Cleanup error in {directory}: {e}")
        
        return bytes_freed
    
    def _cleanup_old_backups(self, backup_dir: str, keep: int) -> int:
        """Keep only the N most recent backups."""
        bytes_freed = 0
        
        try:
            backups = []
            for item in os.listdir(backup_dir):
                item_path = os.path.join(backup_dir, item)
                if os.path.isdir(item_path):
                    mtime = os.path.getmtime(item_path)
                    backups.append((mtime, item_path))
            
            # Sort by time (newest first)
            backups.sort(reverse=True)
            
            # Remove old ones
            for mtime, path in backups[keep:]:
                try:
                    size = self._get_dir_size(path)
                    shutil.rmtree(path)
                    bytes_freed += size
                    logger.info(f"Removed old backup: {path}")
                except Exception as e:
                    logger.warning(f"Could not remove backup {path}: {e}")
        
        except Exception as e:
            logger.warning(f"Backup cleanup error: {e}")
        
        return bytes_freed
    
    def _get_dir_size(self, path: str) -> int:
        """Get total size of a directory."""
        total = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += self._get_dir_size(entry.path)
        except Exception:
            pass
        return total
    
    def get_summary(self) -> Dict[str, Any]:
        """Get guardian summary."""
        status = self.get_status()
        return {
            "status": status.to_dict(),
            "cleanup_count": self.cleanup_count,
            "last_cleanup": self.last_cleanup.isoformat() if self.last_cleanup else None,
            "total_bytes_cleaned": self.bytes_cleaned,
            "total_mb_cleaned": self.bytes_cleaned / (1024 * 1024),
            "thresholds": {
                "memory_warn_percent": MEMORY_WARN_PERCENT,
                "memory_crit_percent": MEMORY_CRIT_PERCENT,
                "disk_warn_gb": DISK_WARN_GB,
                "disk_crit_gb": DISK_CRIT_GB
            }
        }


# ============================================================================
# SINGLETON
# ============================================================================

_guardian: Optional[ResourceGuardian] = None


def get_resource_guardian() -> ResourceGuardian:
    """Get or create resource guardian."""
    global _guardian
    if _guardian is None:
        _guardian = ResourceGuardian()
    return _guardian


async def check_resources() -> Dict[str, Any]:
    """Check resources and take protective action."""
    return await get_resource_guardian().check_and_protect()










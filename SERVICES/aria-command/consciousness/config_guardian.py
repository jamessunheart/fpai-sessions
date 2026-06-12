"""
ARIA CONFIG GUARDIAN
====================

Prevents configuration loss and corruption.

Features:
1. Backs up critical environment variables to encrypted file
2. Auto-restores missing config on startup
3. Detects and alerts on config drift
4. Prevents accidental config overwrites

Critical config items are:
- API keys (Anthropic, OpenAI, Gemini, Telegram)
- Service ports and URLs
- Feature flags

This ensures Aria never loses her configuration.
"""

import os
import json
import logging
import hashlib
import base64
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from cryptography.fernet import Fernet

logger = logging.getLogger("aria.consciousness.config")

# Configuration
CONFIG_BACKUP_PATH = os.getenv("CONFIG_BACKUP_PATH", "/opt/fpai/aria-command/state/config_backup.enc")
CONFIG_KEY_PATH = os.getenv("CONFIG_KEY_PATH", "/opt/fpai/aria-command/state/.config_key")

# Critical environment variables to protect
CRITICAL_ENV_VARS = [
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "SUNHEART_CHAT_ID",
    "MEM0_API_KEY",
    "ARIA_COMMAND_PORT",
    "AI_BRAIN_URL",
    "WHALETRACK_URL",
    "SUPABASE_URL",
    "SUPABASE_KEY",
]

# Non-secret config that should be tracked
TRACKED_CONFIG = [
    "WATCHDOG_HEARTBEAT_TIMEOUT",
    "WATCHDOG_REQUEST_TIMEOUT",
    "MEMORY_WARN_PERCENT",
    "MEMORY_CRIT_PERCENT",
    "DISK_WARN_GB",
    "DISK_CRIT_GB",
    "CIRCUIT_FAILURE_THRESHOLD",
    "CIRCUIT_COOLDOWN",
]


@dataclass
class ConfigChange:
    """Represents a config change."""
    key: str
    old_value_hash: str
    new_value_hash: str
    detected_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "changed": True,
            "detected_at": self.detected_at.isoformat()
        }


class ConfigGuardian:
    """
    Guards configuration integrity.
    
    Backs up critical config, detects drift, and can restore from backup.
    """
    
    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._last_backup: Optional[datetime] = None
        self._config_hashes: Dict[str, str] = {}
        self._drift_detected: List[ConfigChange] = []
        
        # Initialize encryption
        self._init_encryption()
        
        # Load existing backup hashes if available
        self._load_backup_hashes()
        
        logger.info("🔐 Config Guardian initialized")
    
    def _init_encryption(self):
        """Initialize or load encryption key."""
        key_path = Path(CONFIG_KEY_PATH)
        
        try:
            # Ensure directory exists
            key_path.parent.mkdir(parents=True, exist_ok=True)
            
            if key_path.exists():
                with open(key_path, 'rb') as f:
                    key = f.read()
            else:
                # Generate new key
                key = Fernet.generate_key()
                with open(key_path, 'wb') as f:
                    f.write(key)
                os.chmod(key_path, 0o600)  # Restrict permissions
            
            self._fernet = Fernet(key)
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            self._fernet = None
    
    def _hash_value(self, value: str) -> str:
        """Create a hash of a value (for tracking without exposing secrets)."""
        if not value:
            return "empty"
        return hashlib.sha256(value.encode()).hexdigest()[:16]
    
    def _load_backup_hashes(self):
        """Load the hashes of backed-up config for drift detection."""
        backup_path = Path(CONFIG_BACKUP_PATH)
        
        if not backup_path.exists() or not self._fernet:
            return
        
        try:
            with open(backup_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted = self._fernet.decrypt(encrypted_data)
            backup_data = json.loads(decrypted.decode())
            
            # Store hashes of backed-up values
            for key, value in backup_data.get("config", {}).items():
                self._config_hashes[key] = self._hash_value(value)
            
            self._last_backup = datetime.fromisoformat(backup_data.get("timestamp", datetime.now().isoformat()))
            logger.info(f"Loaded config backup from {self._last_backup}")
        except Exception as e:
            logger.warning(f"Could not load config backup: {e}")
    
    def backup_config(self) -> Tuple[bool, str]:
        """
        Backup critical config to encrypted file.
        
        Returns (success, message).
        """
        if not self._fernet:
            return False, "Encryption not initialized"
        
        config_data = {}
        missing = []
        
        # Collect critical env vars
        for var in CRITICAL_ENV_VARS:
            value = os.getenv(var)
            if value:
                config_data[var] = value
                self._config_hashes[var] = self._hash_value(value)
            else:
                missing.append(var)
        
        # Also collect tracked (non-secret) config
        for var in TRACKED_CONFIG:
            value = os.getenv(var)
            if value:
                config_data[var] = value
        
        if not config_data:
            return False, "No config found to backup"
        
        backup_data = {
            "timestamp": datetime.now().isoformat(),
            "config": config_data,
            "missing": missing
        }
        
        try:
            # Encrypt and save
            json_data = json.dumps(backup_data).encode()
            encrypted = self._fernet.encrypt(json_data)
            
            backup_path = Path(CONFIG_BACKUP_PATH)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(backup_path, 'wb') as f:
                f.write(encrypted)
            
            os.chmod(backup_path, 0o600)  # Restrict permissions
            self._last_backup = datetime.now()
            
            msg = f"Backed up {len(config_data)} config items"
            if missing:
                msg += f" (missing: {', '.join(missing)})"
            
            logger.info(f"🔐 {msg}")
            return True, msg
            
        except Exception as e:
            logger.error(f"Config backup failed: {e}")
            return False, f"Backup failed: {e}"
    
    def restore_config(self, apply: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """
        Restore config from backup.
        
        If apply=True, sets the environment variables.
        If apply=False, just returns what would be restored.
        """
        if not self._fernet:
            return False, {"error": "Encryption not initialized"}
        
        backup_path = Path(CONFIG_BACKUP_PATH)
        if not backup_path.exists():
            return False, {"error": "No backup found"}
        
        try:
            with open(backup_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted = self._fernet.decrypt(encrypted_data)
            backup_data = json.loads(decrypted.decode())
            
            config = backup_data.get("config", {})
            timestamp = backup_data.get("timestamp", "unknown")
            
            if apply:
                restored = []
                for key, value in config.items():
                    current = os.getenv(key)
                    if not current:  # Only restore if missing
                        os.environ[key] = value
                        restored.append(key)
                        logger.info(f"🔐 Restored {key} from backup")
                
                return True, {
                    "restored": restored,
                    "available": list(config.keys()),
                    "backup_timestamp": timestamp
                }
            else:
                return True, {
                    "available": list(config.keys()),
                    "backup_timestamp": timestamp
                }
                
        except Exception as e:
            logger.error(f"Config restore failed: {e}")
            return False, {"error": f"Restore failed: {e}"}
    
    def detect_drift(self) -> List[ConfigChange]:
        """
        Detect if current config differs from backup.
        
        Returns list of changes detected.
        """
        changes = []
        
        for var in CRITICAL_ENV_VARS:
            current_value = os.getenv(var, "")
            current_hash = self._hash_value(current_value)
            backup_hash = self._config_hashes.get(var, "unknown")
            
            if backup_hash != "unknown" and current_hash != backup_hash:
                change = ConfigChange(
                    key=var,
                    old_value_hash=backup_hash,
                    new_value_hash=current_hash,
                    detected_at=datetime.now()
                )
                changes.append(change)
                logger.warning(f"⚠️ Config drift detected: {var}")
        
        self._drift_detected.extend(changes)
        return changes
    
    def check_missing_config(self) -> List[str]:
        """Check for missing critical config items."""
        missing = []
        
        for var in CRITICAL_ENV_VARS:
            if not os.getenv(var):
                missing.append(var)
        
        if missing:
            logger.warning(f"⚠️ Missing config: {', '.join(missing)}")
        
        return missing
    
    async def check_and_protect(self) -> Dict[str, Any]:
        """
        Check config health and take protective action.
        
        - Backs up if no recent backup
        - Detects drift
        - Reports missing items
        """
        actions = []
        
        # Check if backup is needed
        should_backup = False
        if not self._last_backup:
            should_backup = True
        elif (datetime.now() - self._last_backup).total_seconds() > 3600:  # 1 hour
            should_backup = True
        
        if should_backup:
            ok, msg = self.backup_config()
            if ok:
                actions.append(msg)
        
        # Detect drift
        drift = self.detect_drift()
        if drift:
            actions.append(f"Detected {len(drift)} config changes")
        
        # Check for missing
        missing = self.check_missing_config()
        if missing:
            actions.append(f"Missing {len(missing)} critical config items")
            
            # Try to restore from backup
            ok, result = self.restore_config(apply=True)
            if ok and result.get("restored"):
                actions.append(f"Auto-restored {len(result['restored'])} items from backup")
        
        return {
            "last_backup": self._last_backup.isoformat() if self._last_backup else None,
            "drift_detected": [c.to_dict() for c in drift],
            "missing_config": missing,
            "actions": actions
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get config guardian status."""
        return {
            "encryption_available": self._fernet is not None,
            "last_backup": self._last_backup.isoformat() if self._last_backup else None,
            "tracked_keys": len(CRITICAL_ENV_VARS + TRACKED_CONFIG),
            "backed_up_keys": len(self._config_hashes),
            "drift_history": len(self._drift_detected),
            "missing_now": self.check_missing_config()
        }


# ============================================================================
# SINGLETON
# ============================================================================

_config_guardian: Optional[ConfigGuardian] = None


def get_config_guardian() -> ConfigGuardian:
    """Get or create config guardian."""
    global _config_guardian
    if _config_guardian is None:
        _config_guardian = ConfigGuardian()
    return _config_guardian


async def check_config() -> Dict[str, Any]:
    """Check config health and take protective action."""
    return await get_config_guardian().check_and_protect()










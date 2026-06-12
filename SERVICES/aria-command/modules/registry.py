#!/usr/bin/env python3
"""
MODULE REGISTRY
================

Tracks all loaded modules and their status.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger("aria.modules.registry")


class ModuleStatus(Enum):
    """Status of a module."""
    PENDING = "pending"      # Submitted, awaiting review
    APPROVED = "approved"    # Approved, ready to load
    LOADED = "loaded"        # Currently loaded and active
    REJECTED = "rejected"    # Rejected by steward
    ERROR = "error"          # Failed to load
    DISABLED = "disabled"    # Manually disabled


@dataclass
class ModuleEntry:
    """A registered module."""
    name: str
    version: str
    description: str
    author: str
    command: str
    module_type: str
    entry_file: str
    path: str
    status: ModuleStatus
    handler: Optional[Callable] = None
    loaded_at: Optional[datetime] = None
    error_message: Optional[str] = None
    submitted_by: Optional[int] = None  # Telegram ID of submitter
    reviewed_by: Optional[int] = None   # Telegram ID of reviewer
    review_notes: Optional[str] = None


class ModuleRegistry:
    """
    Central registry for all modules.
    
    Tracks:
    - Loaded modules and their handlers
    - Pending submissions awaiting review
    - Module status and history
    """
    
    def __init__(self):
        self.modules: Dict[str, ModuleEntry] = {}
        self.commands: Dict[str, str] = {}  # command -> module_name mapping
        self._registry_file = Path(os.getenv("ARIA_STATE_DIR", "/tmp/aria-command")) / "module_registry.json"
        self._load_registry()
    
    def _load_registry(self):
        """Load registry from disk."""
        if self._registry_file.exists():
            try:
                with open(self._registry_file, 'r') as f:
                    data = json.load(f)
                
                for name, info in data.get("modules", {}).items():
                    self.modules[name] = ModuleEntry(
                        name=info["name"],
                        version=info["version"],
                        description=info["description"],
                        author=info["author"],
                        command=info["command"],
                        module_type=info["module_type"],
                        entry_file=info["entry_file"],
                        path=info["path"],
                        status=ModuleStatus(info["status"]),
                        submitted_by=info.get("submitted_by"),
                        reviewed_by=info.get("reviewed_by"),
                        review_notes=info.get("review_notes")
                    )
                    
                    # Track command mapping
                    if info["status"] in ["approved", "loaded"]:
                        self.commands[info["command"]] = name
                        
                logger.info(f"Loaded {len(self.modules)} modules from registry")
            except Exception as e:
                logger.error(f"Failed to load module registry: {e}")
    
    def _save_registry(self):
        """Save registry to disk."""
        try:
            self._registry_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "modules": {},
                "updated_at": datetime.utcnow().isoformat()
            }
            
            for name, module in self.modules.items():
                data["modules"][name] = {
                    "name": module.name,
                    "version": module.version,
                    "description": module.description,
                    "author": module.author,
                    "command": module.command,
                    "module_type": module.module_type,
                    "entry_file": module.entry_file,
                    "path": module.path,
                    "status": module.status.value,
                    "submitted_by": module.submitted_by,
                    "reviewed_by": module.reviewed_by,
                    "review_notes": module.review_notes
                }
            
            with open(self._registry_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save module registry: {e}")
    
    def register(
        self,
        name: str,
        version: str,
        description: str,
        author: str,
        command: str,
        module_type: str,
        entry_file: str,
        path: str,
        status: ModuleStatus = ModuleStatus.PENDING,
        submitted_by: Optional[int] = None
    ) -> ModuleEntry:
        """
        Register a new module.
        
        Args:
            name: Module name
            version: Version string
            description: What the module does
            author: Who wrote it
            command: The /command it handles
            module_type: Type (telegram_command, tool, etc.)
            entry_file: Main Python file
            path: Path to module directory
            status: Initial status
            submitted_by: Telegram ID of submitter
            
        Returns:
            The registered ModuleEntry
        """
        # Check for command conflict
        if command in self.commands and self.commands[command] != name:
            raise ValueError(f"Command {command} already registered by module {self.commands[command]}")
        
        entry = ModuleEntry(
            name=name,
            version=version,
            description=description,
            author=author,
            command=command,
            module_type=module_type,
            entry_file=entry_file,
            path=path,
            status=status,
            submitted_by=submitted_by
        )
        
        self.modules[name] = entry
        
        if status in [ModuleStatus.APPROVED, ModuleStatus.LOADED]:
            self.commands[command] = name
        
        self._save_registry()
        logger.info(f"Registered module: {name} (status: {status.value})")
        
        return entry
    
    def update_status(
        self,
        name: str,
        status: ModuleStatus,
        reviewed_by: Optional[int] = None,
        review_notes: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update a module's status."""
        if name not in self.modules:
            return False
        
        module = self.modules[name]
        module.status = status
        
        if reviewed_by:
            module.reviewed_by = reviewed_by
        if review_notes:
            module.review_notes = review_notes
        if error_message:
            module.error_message = error_message
        
        # Update command mapping
        if status in [ModuleStatus.APPROVED, ModuleStatus.LOADED]:
            self.commands[module.command] = name
        elif module.command in self.commands:
            del self.commands[module.command]
        
        self._save_registry()
        return True
    
    def set_handler(self, name: str, handler: Callable) -> bool:
        """Set the handler function for a loaded module."""
        if name not in self.modules:
            return False
        
        self.modules[name].handler = handler
        self.modules[name].loaded_at = datetime.utcnow()
        self.modules[name].status = ModuleStatus.LOADED
        self._save_registry()
        return True
    
    def get_module(self, name: str) -> Optional[ModuleEntry]:
        """Get a module by name."""
        return self.modules.get(name)
    
    def get_by_command(self, command: str) -> Optional[ModuleEntry]:
        """Get a module by its command."""
        name = self.commands.get(command)
        if name:
            return self.modules.get(name)
        return None
    
    def get_pending(self) -> List[ModuleEntry]:
        """Get all modules pending review."""
        return [m for m in self.modules.values() if m.status == ModuleStatus.PENDING]
    
    def get_loaded(self) -> List[ModuleEntry]:
        """Get all loaded modules."""
        return [m for m in self.modules.values() if m.status == ModuleStatus.LOADED]
    
    def get_all(self) -> List[ModuleEntry]:
        """Get all registered modules."""
        return list(self.modules.values())
    
    def unregister(self, name: str) -> bool:
        """Remove a module from the registry."""
        if name not in self.modules:
            return False
        
        module = self.modules[name]
        
        # Remove command mapping
        if module.command in self.commands:
            del self.commands[module.command]
        
        del self.modules[name]
        self._save_registry()
        
        return True


# Singleton
_registry: Optional[ModuleRegistry] = None


def get_module_registry() -> ModuleRegistry:
    """Get singleton registry instance."""
    global _registry
    if _registry is None:
        _registry = ModuleRegistry()
    return _registry



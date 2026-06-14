#!/usr/bin/env python3
"""
MODULE LOADER
==============

Dynamically loads and executes community modules.
"""

import os
import sys
import json
import logging
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass

from .registry import ModuleRegistry, ModuleEntry, ModuleStatus, get_module_registry
from .validator import ModuleValidator, validate_module, ValidationResult

logger = logging.getLogger("aria.modules.loader")

# Base paths
MODULES_DIR = Path(os.getenv("FPAI_WORKSPACE", "/opt/fpai")) / "aria-command" / "modules" / "installed"
SUBMISSIONS_DIR = Path(os.getenv("FPAI_WORKSPACE", "/opt/fpai")) / "labs" / "submissions"


@dataclass
class ModuleExecutionResult:
    """Result of executing a module command."""
    success: bool
    response: str
    error: Optional[str] = None


class ModuleLoader:
    """
    Loads and manages community modules.
    
    Features:
    - Dynamic loading from /modules/installed/
    - Validation before loading
    - Safe execution sandbox
    - Command routing
    """
    
    def __init__(self):
        self.registry = get_module_registry()
        self.validator = ModuleValidator()
        self.modules_dir = MODULES_DIR
        self.submissions_dir = SUBMISSIONS_DIR
        
        # Ensure directories exist
        self.modules_dir.mkdir(parents=True, exist_ok=True)
        self.submissions_dir.mkdir(parents=True, exist_ok=True)
    
    def load_all(self) -> Dict[str, bool]:
        """
        Load all approved modules from the modules directory.
        
        Returns:
            Dict mapping module name to success status
        """
        results = {}
        
        if not self.modules_dir.exists():
            logger.warning(f"Modules directory does not exist: {self.modules_dir}")
            return results
        
        # Scan for module directories
        for item in self.modules_dir.iterdir():
            if item.is_dir() and (item / "module.json").exists():
                success = self.load_module(str(item))
                results[item.name] = success
        
        loaded = sum(1 for v in results.values() if v)
        logger.info(f"Loaded {loaded}/{len(results)} modules")
        
        return results
    
    def load_module(self, module_path: str) -> bool:
        """
        Load a single module.
        
        Args:
            module_path: Path to the module directory
            
        Returns:
            True if loaded successfully
        """
        path = Path(module_path)
        
        # Validate first
        validation = self.validator.validate(module_path)
        if not validation.valid:
            logger.error(f"Module validation failed: {validation.errors}")
            return False
        
        if validation.warnings:
            logger.warning(f"Module warnings: {validation.warnings}")
        
        module_info = validation.module_info
        name = module_info["name"]
        
        try:
            # Load the handler
            entry_file = path / module_info.get("entry", "handler.py")
            handler = self._load_handler(entry_file, name)
            
            if handler is None:
                return False
            
            # Register in registry
            entry = self.registry.register(
                name=name,
                version=module_info["version"],
                description=module_info["description"],
                author=module_info["author"],
                command=module_info["command"],
                module_type=module_info["type"],
                entry_file=module_info.get("entry", "handler.py"),
                path=str(path),
                status=ModuleStatus.LOADED
            )
            
            # Set the handler
            self.registry.set_handler(name, handler)
            
            logger.info(f"Loaded module: {name} (command: {module_info['command']})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load module {name}: {e}")
            return False
    
    def _load_handler(self, entry_file: Path, module_name: str) -> Optional[Callable]:
        """
        Dynamically load a handler function from a Python file.
        
        The handler should be either:
        - A function named 'handle' 
        - A class named 'Handler' with a 'handle' method
        """
        try:
            spec = importlib.util.spec_from_file_location(
                f"aria_module_{module_name}",
                entry_file
            )
            module = importlib.util.module_from_spec(spec)
            
            # Add to sys.modules temporarily
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            # Look for handler
            if hasattr(module, 'handle'):
                return module.handle
            elif hasattr(module, 'Handler'):
                handler_class = module.Handler
                instance = handler_class()
                if hasattr(instance, 'handle'):
                    return instance.handle
            
            logger.error(f"No 'handle' function or 'Handler' class found in {entry_file}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to load handler from {entry_file}: {e}")
            return None
    
    async def execute_command(
        self,
        command: str,
        args: str,
        user_id: int,
        chat_id: int
    ) -> Optional[ModuleExecutionResult]:
        """
        Execute a module command.
        
        Args:
            command: The /command
            args: Arguments after the command
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            
        Returns:
            ModuleExecutionResult or None if no module handles this command
        """
        module = self.registry.get_by_command(command)
        
        if not module or module.status != ModuleStatus.LOADED:
            return None
        
        if not module.handler:
            return ModuleExecutionResult(
                success=False,
                response="Module handler not loaded",
                error="Handler missing"
            )
        
        try:
            # Build context
            context = {
                "command": command,
                "args": args,
                "user_id": user_id,
                "chat_id": chat_id,
                "module_name": module.name
            }
            
            # Execute handler
            # Handler signature: handle(args: str, context: dict) -> str
            import asyncio
            if asyncio.iscoroutinefunction(module.handler):
                response = await module.handler(args, context)
            else:
                response = module.handler(args, context)
            
            return ModuleExecutionResult(
                success=True,
                response=str(response)
            )
            
        except Exception as e:
            logger.error(f"Module {module.name} execution error: {e}")
            return ModuleExecutionResult(
                success=False,
                response=f"Module error: {e}",
                error=str(e)
            )
    
    def get_available_commands(self) -> List[Dict[str, str]]:
        """Get list of available module commands."""
        commands = []
        for module in self.registry.get_loaded():
            commands.append({
                "command": module.command,
                "description": module.description,
                "author": module.author
            })
        return commands
    
    def submit_module(
        self,
        source_path: str,
        submitted_by: int
    ) -> tuple[bool, str]:
        """
        Submit a module for review.
        
        Args:
            source_path: Path to the module directory
            submitted_by: Telegram ID of submitter
            
        Returns:
            (success, message)
        """
        import shutil
        from datetime import datetime
        
        source = Path(source_path)
        
        # Validate first
        validation = self.validator.validate(source_path)
        if not validation.valid:
            return False, f"Validation failed:\n" + "\n".join(validation.errors)
        
        module_info = validation.module_info
        name = module_info["name"]
        
        # Create submission directory
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        submission_dir = self.submissions_dir / f"{timestamp}_{submitted_by}_{name}"
        
        try:
            # Copy module to submissions
            shutil.copytree(source, submission_dir)
            
            # Register as pending
            self.registry.register(
                name=name,
                version=module_info["version"],
                description=module_info["description"],
                author=module_info["author"],
                command=module_info["command"],
                module_type=module_info["type"],
                entry_file=module_info.get("entry", "handler.py"),
                path=str(submission_dir),
                status=ModuleStatus.PENDING,
                submitted_by=submitted_by
            )
            
            warnings_str = ""
            if validation.warnings:
                warnings_str = "\n\nWarnings:\n" + "\n".join(validation.warnings)
            
            return True, f"Module '{name}' submitted for review!{warnings_str}"
            
        except Exception as e:
            logger.error(f"Failed to submit module: {e}")
            return False, f"Submission failed: {e}"
    
    def approve_module(
        self,
        name: str,
        reviewed_by: int,
        notes: str = None
    ) -> tuple[bool, str]:
        """
        Approve a pending module.
        
        Args:
            name: Module name
            reviewed_by: Telegram ID of reviewer
            notes: Optional review notes
            
        Returns:
            (success, message)
        """
        import shutil
        
        module = self.registry.get_module(name)
        if not module:
            return False, f"Module '{name}' not found"
        
        if module.status != ModuleStatus.PENDING:
            return False, f"Module '{name}' is not pending (status: {module.status.value})"
        
        try:
            # Move from submissions to installed
            source = Path(module.path)
            dest = self.modules_dir / name
            
            if dest.exists():
                shutil.rmtree(dest)
            
            shutil.copytree(source, dest)
            
            # Update registry
            self.registry.update_status(
                name=name,
                status=ModuleStatus.APPROVED,
                reviewed_by=reviewed_by,
                review_notes=notes
            )
            
            # Update path
            module.path = str(dest)
            
            # Load the module
            if self.load_module(str(dest)):
                return True, f"Module '{name}' approved and loaded! Command: {module.command}"
            else:
                return True, f"Module '{name}' approved but failed to load. Check logs."
            
        except Exception as e:
            logger.error(f"Failed to approve module: {e}")
            return False, f"Approval failed: {e}"
    
    def reject_module(
        self,
        name: str,
        reviewed_by: int,
        reason: str
    ) -> tuple[bool, str]:
        """
        Reject a pending module.
        
        Args:
            name: Module name
            reviewed_by: Telegram ID of reviewer
            reason: Rejection reason
            
        Returns:
            (success, message)
        """
        module = self.registry.get_module(name)
        if not module:
            return False, f"Module '{name}' not found"
        
        if module.status != ModuleStatus.PENDING:
            return False, f"Module '{name}' is not pending (status: {module.status.value})"
        
        self.registry.update_status(
            name=name,
            status=ModuleStatus.REJECTED,
            reviewed_by=reviewed_by,
            review_notes=reason
        )
        
        return True, f"Module '{name}' rejected. Reason: {reason}"


# Singleton
_loader: Optional[ModuleLoader] = None


def get_module_loader() -> ModuleLoader:
    """Get singleton loader instance."""
    global _loader
    if _loader is None:
        _loader = ModuleLoader()
    return _loader



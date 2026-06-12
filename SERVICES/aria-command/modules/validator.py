#!/usr/bin/env python3
"""
MODULE VALIDATOR
=================

Validates modules against the schema before loading.
Ensures safety and correctness.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger("aria.modules.validator")

# Required fields in module.json
REQUIRED_FIELDS = ["name", "version", "description", "author", "command", "type", "entry"]

# Allowed module types
ALLOWED_TYPES = ["telegram_command", "tool", "scheduled_task", "webhook"]

# Forbidden patterns in code (security)
FORBIDDEN_PATTERNS = [
    "subprocess.Popen",
    "os.system(",
    "eval(",
    "exec(",
    "__import__",
    "open('/etc",
    "open('/root",
    "rm -rf",
    "sudo ",
    "chmod 777",
    "API_KEY",
    "SECRET",
    "PASSWORD",
]


@dataclass
class ValidationResult:
    """Result of module validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    module_info: Optional[Dict] = None


class ModuleValidator:
    """
    Validates modules for safety and correctness.
    """
    
    def __init__(self):
        self.forbidden_patterns = FORBIDDEN_PATTERNS
    
    def validate(self, module_path: str) -> ValidationResult:
        """
        Validate a module directory.
        
        Args:
            module_path: Path to the module directory
            
        Returns:
            ValidationResult with status and any errors/warnings
        """
        errors = []
        warnings = []
        module_info = None
        
        path = Path(module_path)
        
        # Check directory exists
        if not path.is_dir():
            return ValidationResult(
                valid=False,
                errors=[f"Module path is not a directory: {module_path}"],
                warnings=[]
            )
        
        # Check module.json exists
        module_json_path = path / "module.json"
        if not module_json_path.exists():
            errors.append("Missing module.json")
        else:
            # Validate module.json
            try:
                with open(module_json_path, 'r') as f:
                    module_info = json.load(f)
                
                # Check required fields
                for field in REQUIRED_FIELDS:
                    if field not in module_info:
                        errors.append(f"Missing required field in module.json: {field}")
                
                # Validate type
                if module_info.get("type") not in ALLOWED_TYPES:
                    errors.append(f"Invalid module type: {module_info.get('type')}. Allowed: {ALLOWED_TYPES}")
                
                # Validate command format
                command = module_info.get("command", "")
                if not command.startswith("/"):
                    errors.append(f"Command must start with /: got '{command}'")
                
                # Check for conflicting commands
                if command in ["/help", "/start", "/status", "/signal", "/servers", "/addapprentice"]:
                    errors.append(f"Command '{command}' conflicts with built-in command")
                
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in module.json: {e}")
        
        # Check entry file exists
        entry_file = module_info.get("entry", "handler.py") if module_info else "handler.py"
        entry_path = path / entry_file
        if not entry_path.exists():
            errors.append(f"Missing entry file: {entry_file}")
        else:
            # Security scan the code
            code_errors, code_warnings = self._scan_code(entry_path)
            errors.extend(code_errors)
            warnings.extend(code_warnings)
        
        # Check for README (warning only)
        readme_path = path / "README.md"
        if not readme_path.exists():
            warnings.append("Missing README.md (recommended)")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            module_info=module_info
        )
    
    def _scan_code(self, file_path: Path) -> Tuple[List[str], List[str]]:
        """
        Scan code for security issues.
        
        Returns:
            (errors, warnings)
        """
        errors = []
        warnings = []
        
        try:
            content = file_path.read_text()
            
            # Check for forbidden patterns
            for pattern in self.forbidden_patterns:
                if pattern.lower() in content.lower():
                    errors.append(f"Security: Forbidden pattern found: '{pattern}'")
            
            # Check for imports that might be dangerous
            dangerous_imports = ["subprocess", "shutil", "ctypes", "socket"]
            for imp in dangerous_imports:
                if f"import {imp}" in content or f"from {imp}" in content:
                    warnings.append(f"Potentially dangerous import: {imp}")
            
            # Check file isn't too large
            if len(content) > 50000:  # 50KB
                warnings.append("File is quite large (>50KB)")
            
        except Exception as e:
            errors.append(f"Could not read entry file: {e}")
        
        return errors, warnings
    
    def quick_check(self, module_path: str) -> bool:
        """Quick check if a module is valid."""
        result = self.validate(module_path)
        return result.valid


# Singleton
_validator: Optional[ModuleValidator] = None


def get_validator() -> ModuleValidator:
    """Get singleton validator instance."""
    global _validator
    if _validator is None:
        _validator = ModuleValidator()
    return _validator


def validate_module(module_path: str) -> ValidationResult:
    """Convenience function to validate a module."""
    return get_validator().validate(module_path)



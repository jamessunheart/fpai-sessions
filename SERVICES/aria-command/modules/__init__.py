#!/usr/bin/env python3
"""
ARIA MODULE SYSTEM
===================

Dynamic module loading for community-built extensions.

Modules live in /opt/fpai/aria-command/modules/{module_name}/
Each module has:
- module.json  (metadata)
- handler.py   (the code)
- README.md    (documentation)
"""

from .loader import ModuleLoader, get_module_loader
from .validator import ModuleValidator, validate_module
from .registry import ModuleRegistry, get_module_registry

__all__ = [
    'ModuleLoader',
    'get_module_loader', 
    'ModuleValidator',
    'validate_module',
    'ModuleRegistry',
    'get_module_registry'
]



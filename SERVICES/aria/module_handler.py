#!/usr/bin/env python3
"""
MODULE HANDLER
==============

Integrates the module system with Aria's chat.
"""

import os
import sys
import asyncio
import logging

logger = logging.getLogger("aria.modules")

# Add modules path
sys.path.insert(0, "/opt/fpai/aria")

# Override the modules directory to point to our location
os.environ["FPAI_WORKSPACE"] = "/opt/fpai"

_loader = None

def get_loader():
    """Get or create the module loader."""
    global _loader
    if _loader is None:
        try:
            # Patch the path in the loader module
            from modules import loader as loader_module
            loader_module.MODULES_DIR = __import__("pathlib").Path("/opt/fpai/aria/modules/installed")
            
            from modules.loader import ModuleLoader
            _loader = ModuleLoader()
            _loader.modules_dir = __import__("pathlib").Path("/opt/fpai/aria/modules/installed")
            results = _loader.load_all()
            logger.info(f"Loaded modules: {results}")
        except Exception as e:
            logger.error(f"Failed to initialize module loader: {e}")
            import traceback
            traceback.print_exc()
            _loader = None
    return _loader


async def handle_module_command(message: str, user_id: int = 0, chat_id: int = 0) -> str:
    """
    Check if message is a module command and execute it.
    
    Returns:
        Response string if handled, None if not a module command
    """
    if not message.startswith("/"):
        return None
    
    # Parse command and args
    parts = message.split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    
    # Get loader
    loader = get_loader()
    if loader is None:
        return None
    
    # Try to execute
    try:
        result = await loader.execute_command(command, args, user_id, chat_id)
        if result:
            return result.response
    except Exception as e:
        logger.error(f"Module command error: {e}")
    
    return None


# Initialize on import
get_loader()


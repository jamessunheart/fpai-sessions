#!/usr/bin/env python3
"""
AUTO-HEALER
============

Automatic recovery actions for common failures.
"""

import os
import asyncio
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("health.healer")


class HealAction(str, Enum):
    RESTART_SERVICE = "restart_service"
    CLEAR_CACHE = "clear_cache"
    NOTIFY_ONLY = "notify_only"
    NONE = "none"


@dataclass
class HealResult:
    success: bool
    action: HealAction
    message: str


class AutoHealer:
    """
    Automatic recovery system.
    
    Takes healing actions based on failure type.
    """
    
    def __init__(self):
        # Map issue types to healing actions
        self.healing_rules: Dict[str, HealAction] = {
            "Aria Command": HealAction.RESTART_SERVICE,
            "AI Brain": HealAction.RESTART_SERVICE,
            "WhaleTrack": HealAction.RESTART_SERVICE,
            "Nerve Center": HealAction.RESTART_SERVICE,
            # API issues can't be auto-healed
            "Claude API": HealAction.NOTIFY_ONLY,
            "OpenAI API": HealAction.NOTIFY_ONLY,
            "Gemini API": HealAction.NOTIFY_ONLY,
        }
        
        # Service name to systemd unit mapping
        self.service_map: Dict[str, str] = {
            "Aria Command": "aria-command",
            "AI Brain": "fpai-ai-brain",
            "WhaleTrack": "fpai-whaletrack",
            "Nerve Center": "fpai-nerve-center",
        }
        
        # Track heal attempts to prevent loops
        self.heal_attempts: Dict[str, int] = {}
        self.max_attempts = 3
    
    async def heal(self, issue_name: str, error_message: str = "") -> HealResult:
        """
        Attempt to heal an issue.
        
        Args:
            issue_name: Name of the failing check
            error_message: Error details
            
        Returns:
            HealResult with action taken and success status
        """
        # Check heal attempt limit
        attempts = self.heal_attempts.get(issue_name, 0)
        if attempts >= self.max_attempts:
            logger.warning(f"Max heal attempts reached for {issue_name}")
            return HealResult(
                success=False,
                action=HealAction.NONE,
                message=f"Max attempts ({self.max_attempts}) reached"
            )
        
        # Get healing action
        action = self.healing_rules.get(issue_name, HealAction.NOTIFY_ONLY)
        
        if action == HealAction.RESTART_SERVICE:
            return await self._restart_service(issue_name)
        elif action == HealAction.CLEAR_CACHE:
            return await self._clear_cache(issue_name)
        else:
            return HealResult(
                success=True,
                action=HealAction.NOTIFY_ONLY,
                message="Issue requires manual intervention"
            )
    
    async def _restart_service(self, issue_name: str) -> HealResult:
        """Restart a systemd service."""
        service_name = self.service_map.get(issue_name)
        
        if not service_name:
            return HealResult(
                success=False,
                action=HealAction.RESTART_SERVICE,
                message=f"Unknown service for {issue_name}"
            )
        
        # Increment attempt counter
        self.heal_attempts[issue_name] = self.heal_attempts.get(issue_name, 0) + 1
        
        try:
            logger.info(f"Restarting service: {service_name}")
            
            # Run systemctl restart
            proc = await asyncio.create_subprocess_exec(
                "systemctl", "restart", service_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                logger.info(f"Successfully restarted {service_name}")
                # Wait for service to come up
                await asyncio.sleep(5)
                
                # Reset attempt counter on success
                self.heal_attempts[issue_name] = 0
                
                return HealResult(
                    success=True,
                    action=HealAction.RESTART_SERVICE,
                    message=f"Restarted {service_name}"
                )
            else:
                error = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Failed to restart {service_name}: {error}")
                return HealResult(
                    success=False,
                    action=HealAction.RESTART_SERVICE,
                    message=f"Restart failed: {error}"
                )
                
        except Exception as e:
            logger.error(f"Restart exception: {e}")
            return HealResult(
                success=False,
                action=HealAction.RESTART_SERVICE,
                message=str(e)
            )
    
    async def _clear_cache(self, issue_name: str) -> HealResult:
        """Clear caches for a service."""
        return HealResult(
            success=True,
            action=HealAction.CLEAR_CACHE,
            message="Cache cleared (stub)"
        )
    
    def reset_attempts(self, issue_name: str):
        """Reset heal attempt counter for an issue."""
        if issue_name in self.heal_attempts:
            del self.heal_attempts[issue_name]


# Global instance
_healer: Optional[AutoHealer] = None


def get_healer() -> AutoHealer:
    """Get global healer instance."""
    global _healer
    if _healer is None:
        _healer = AutoHealer()
    return _healer










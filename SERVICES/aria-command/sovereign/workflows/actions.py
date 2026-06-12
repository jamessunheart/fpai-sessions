#!/usr/bin/env python3
"""
ARIA ULTRA POWER - ACTION LIBRARY
==================================

Actions that can be executed in workflows:
- Trading actions (adjust stop, close position, open position)
- Alert actions (Telegram, SMS, phone call)
- Server actions (restart service, cleanup memory)
- Chained actions with dependencies
"""

import asyncio
import logging
import os
import httpx
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger("aria.workflows.actions")

# Configuration
WHALETRACK_URL = os.getenv("WHALETRACK_URL", "http://198.54.123.234:8600")
WHALETRACK_LIVE_URL = os.getenv("WHALETRACK_LIVE_URL", "http://198.54.123.234:8601")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER", "")


class ActionType(Enum):
    """Types of actions."""
    # Trading
    OPEN_POSITION = "open_position"
    CLOSE_POSITION = "close_position"
    ADJUST_STOP = "adjust_stop"
    ADJUST_TARGET = "adjust_target"
    
    # Alerts
    TELEGRAM_ALERT = "telegram_alert"
    SMS_ALERT = "sms_alert"
    PHONE_CALL = "phone_call"
    
    # Server
    RESTART_SERVICE = "restart_service"
    CLEANUP_MEMORY = "cleanup_memory"
    RUN_COMMAND = "run_command"
    
    # Workflow
    DELAY = "delay"
    LOG = "log"


@dataclass
class ActionResult:
    """Result of an action execution."""
    success: bool
    action_type: str
    message: str
    data: Optional[Dict] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class ActionLibrary:
    """Library of executable actions."""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self._actions = {}
        self._register_builtin_actions()
    
    def _register_builtin_actions(self):
        """Register all built-in actions."""
        # Trading actions
        self._actions["open_position"] = self._action_open_position
        self._actions["close_position"] = self._action_close_position
        self._actions["adjust_stop"] = self._action_adjust_stop
        self._actions["adjust_target"] = self._action_adjust_target
        
        # Alert actions
        self._actions["alert"] = self._action_telegram_alert
        self._actions["telegram_alert"] = self._action_telegram_alert
        self._actions["sms_alert"] = self._action_sms_alert
        self._actions["phone_call"] = self._action_phone_call
        
        # Server actions
        self._actions["restart_service"] = self._action_restart_service
        self._actions["cleanup_memory"] = self._action_cleanup_memory
        self._actions["run_command"] = self._action_run_command
        
        # Utility actions
        self._actions["delay"] = self._action_delay
        self._actions["log"] = self._action_log
    
    async def execute(self, action_def: Dict, context: Dict) -> ActionResult:
        """Execute an action definition."""
        # Find the action type
        action_type = None
        action_params = {}
        
        for key in action_def:
            if key in self._actions:
                action_type = key
                action_params = action_def[key] if isinstance(action_def[key], dict) else {"value": action_def[key]}
                break
        
        if action_type is None:
            # Try 'type' field
            action_type = action_def.get("type")
            action_params = {k: v for k, v in action_def.items() if k != "type"}
        
        if action_type is None or action_type not in self._actions:
            return ActionResult(
                success=False,
                action_type=str(action_type),
                message="Unknown action type",
                error=f"Action '{action_type}' not found in library"
            )
        
        try:
            return await self._actions[action_type](action_params, context)
        except Exception as e:
            logger.error(f"Action {action_type} failed: {e}")
            return ActionResult(
                success=False,
                action_type=action_type,
                message=f"Action failed: {str(e)}",
                error=str(e)
            )
    
    # =========================================================================
    # TRADING ACTIONS
    # =========================================================================
    
    async def _action_open_position(self, params: Dict, context: Dict) -> ActionResult:
        """Open a trading position."""
        asset = params.get("asset", "").upper()
        side = params.get("side", "LONG").upper()
        size = params.get("size")  # In USD or units
        leverage = params.get("leverage", 1)
        
        if not asset:
            return ActionResult(
                success=False,
                action_type="open_position",
                message="Asset not specified",
                error="Missing required parameter: asset"
            )
        
        try:
            response = await self.http_client.post(
                f"{WHALETRACK_LIVE_URL}/api/live/trade",
                json={
                    "action": "open",
                    "asset": asset,
                    "side": side,
                    "size": size,
                    "leverage": leverage,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return ActionResult(
                    success=True,
                    action_type="open_position",
                    message=f"Opened {side} position on {asset}",
                    data=data
                )
            else:
                return ActionResult(
                    success=False,
                    action_type="open_position",
                    message=f"Failed to open position: {response.text}",
                    error=response.text
                )
        except Exception as e:
            return ActionResult(
                success=False,
                action_type="open_position",
                message=f"Error opening position: {str(e)}",
                error=str(e)
            )
    
    async def _action_close_position(self, params: Dict, context: Dict) -> ActionResult:
        """Close a trading position."""
        asset = params.get("asset", "").upper()
        percent = params.get("percent", 100)  # Percentage to close
        
        if not asset:
            return ActionResult(
                success=False,
                action_type="close_position",
                message="Asset not specified",
                error="Missing required parameter: asset"
            )
        
        try:
            response = await self.http_client.post(
                f"{WHALETRACK_LIVE_URL}/api/live/trade",
                json={
                    "action": "close",
                    "asset": asset,
                    "percent": percent,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return ActionResult(
                    success=True,
                    action_type="close_position",
                    message=f"Closed {percent}% of {asset} position",
                    data=data
                )
            else:
                return ActionResult(
                    success=False,
                    action_type="close_position",
                    message=f"Failed to close position: {response.text}",
                    error=response.text
                )
        except Exception as e:
            return ActionResult(
                success=False,
                action_type="close_position",
                message=f"Error closing position: {str(e)}",
                error=str(e)
            )
    
    async def _action_adjust_stop(self, params: Dict, context: Dict) -> ActionResult:
        """Adjust stop loss for a position."""
        asset = params.get("asset", "").upper()
        price = params.get("price")
        
        if not asset or price is None:
            return ActionResult(
                success=False,
                action_type="adjust_stop",
                message="Asset or price not specified",
                error="Missing required parameters"
            )
        
        try:
            response = await self.http_client.post(
                f"{WHALETRACK_LIVE_URL}/api/live/modify",
                json={
                    "asset": asset,
                    "stop_loss": price,
                }
            )
            
            if response.status_code == 200:
                return ActionResult(
                    success=True,
                    action_type="adjust_stop",
                    message=f"Adjusted {asset} stop loss to ${price}",
                    data={"asset": asset, "stop_loss": price}
                )
            else:
                return ActionResult(
                    success=False,
                    action_type="adjust_stop",
                    message=f"Failed to adjust stop: {response.text}",
                    error=response.text
                )
        except Exception as e:
            return ActionResult(
                success=False,
                action_type="adjust_stop",
                message=f"Error adjusting stop: {str(e)}",
                error=str(e)
            )
    
    async def _action_adjust_target(self, params: Dict, context: Dict) -> ActionResult:
        """Adjust take profit target for a position."""
        asset = params.get("asset", "").upper()
        price = params.get("price")
        
        if not asset or price is None:
            return ActionResult(
                success=False,
                action_type="adjust_target",
                message="Asset or price not specified",
                error="Missing required parameters"
            )
        
        try:
            response = await self.http_client.post(
                f"{WHALETRACK_LIVE_URL}/api/live/modify",
                json={
                    "asset": asset,
                    "take_profit": price,
                }
            )
            
            if response.status_code == 200:
                return ActionResult(
                    success=True,
                    action_type="adjust_target",
                    message=f"Adjusted {asset} target to ${price}",
                    data={"asset": asset, "take_profit": price}
                )
            else:
                return ActionResult(
                    success=False,
                    action_type="adjust_target",
                    message=f"Failed to adjust target: {response.text}",
                    error=response.text
                )
        except Exception as e:
            return ActionResult(
                success=False,
                action_type="adjust_target",
                message=f"Error adjusting target: {str(e)}",
                error=str(e)
            )
    
    # =========================================================================
    # ALERT ACTIONS
    # =========================================================================
    
    async def _action_telegram_alert(self, params: Dict, context: Dict) -> ActionResult:
        """Send a Telegram alert."""
        message = params.get("value") or params.get("message", "Workflow alert")
        chat_id = params.get("chat_id") or context.get("owner_id")
        
        if not chat_id:
            return ActionResult(
                success=False,
                action_type="telegram_alert",
                message="No chat_id available",
                error="Missing chat_id"
            )
        
        # Add trigger context to message
        trigger_data = context.get("trigger_data", {})
        if trigger_data:
            asset = trigger_data.get("asset", "")
            price = trigger_data.get("current_price", "")
            if asset and price:
                message = f"🔔 **Workflow Alert**\n\n{message}\n\n_{asset}: ${price:,.2f}_"
        else:
            message = f"🔔 **Workflow Alert**\n\n{message}"
        
        try:
            response = await self.http_client.post(
                f"{TELEGRAM_API}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                }
            )
            
            if response.status_code == 200:
                return ActionResult(
                    success=True,
                    action_type="telegram_alert",
                    message="Alert sent via Telegram",
                    data={"chat_id": chat_id}
                )
            else:
                return ActionResult(
                    success=False,
                    action_type="telegram_alert",
                    message=f"Failed to send alert: {response.text}",
                    error=response.text
                )
        except Exception as e:
            return ActionResult(
                success=False,
                action_type="telegram_alert",
                message=f"Error sending alert: {str(e)}",
                error=str(e)
            )
    
    async def _action_sms_alert(self, params: Dict, context: Dict) -> ActionResult:
        """Send an SMS alert via Twilio."""
        message = params.get("value") or params.get("message", "Workflow alert")
        to_number = params.get("to") or os.getenv("ALERT_PHONE_NUMBER", "")
        
        if not to_number:
            return ActionResult(
                success=False,
                action_type="sms_alert",
                message="No phone number specified",
                error="Missing 'to' parameter"
            )
        
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            return ActionResult(
                success=False,
                action_type="sms_alert",
                message="Twilio not configured",
                error="Missing Twilio credentials"
            )
        
        try:
            from twilio.rest import Client
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            
            sms = client.messages.create(
                body=f"Aria Alert: {message}",
                from_=TWILIO_PHONE,
                to=to_number
            )
            
            return ActionResult(
                success=True,
                action_type="sms_alert",
                message=f"SMS sent to {to_number}",
                data={"sid": sms.sid}
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action_type="sms_alert",
                message=f"Error sending SMS: {str(e)}",
                error=str(e)
            )
    
    async def _action_phone_call(self, params: Dict, context: Dict) -> ActionResult:
        """Make a phone call via Twilio."""
        message = params.get("value") or params.get("message", "Urgent workflow alert")
        to_number = params.get("to") or os.getenv("ALERT_PHONE_NUMBER", "")
        
        if not to_number:
            return ActionResult(
                success=False,
                action_type="phone_call",
                message="No phone number specified",
                error="Missing 'to' parameter"
            )
        
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            return ActionResult(
                success=False,
                action_type="phone_call",
                message="Twilio not configured",
                error="Missing Twilio credentials"
            )
        
        try:
            from twilio.rest import Client
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            
            # Use TwiML to speak the message
            twiml = f'<Response><Say voice="alice">{message}</Say></Response>'
            
            call = client.calls.create(
                twiml=twiml,
                from_=TWILIO_PHONE,
                to=to_number
            )
            
            return ActionResult(
                success=True,
                action_type="phone_call",
                message=f"Calling {to_number}",
                data={"sid": call.sid}
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action_type="phone_call",
                message=f"Error making call: {str(e)}",
                error=str(e)
            )
    
    # =========================================================================
    # SERVER ACTIONS
    # =========================================================================
    
    async def _action_restart_service(self, params: Dict, context: Dict) -> ActionResult:
        """Restart a systemd service."""
        service = params.get("value") or params.get("service", "")
        server = params.get("server", "secondary")  # primary or secondary
        
        if not service:
            return ActionResult(
                success=False,
                action_type="restart_service",
                message="No service specified",
                error="Missing service parameter"
            )
        
        # Execute via SSH
        try:
            import asyncssh
            
            host = "198.54.123.234" if server == "primary" else "162.0.208.88"
            
            async with asyncssh.connect(host, username="root", known_hosts=None) as conn:
                result = await conn.run(f"systemctl restart {service}")
                
                if result.exit_status == 0:
                    return ActionResult(
                        success=True,
                        action_type="restart_service",
                        message=f"Restarted {service} on {server}",
                        data={"service": service, "server": server}
                    )
                else:
                    return ActionResult(
                        success=False,
                        action_type="restart_service",
                        message=f"Failed to restart {service}: {result.stderr}",
                        error=result.stderr
                    )
        except Exception as e:
            return ActionResult(
                success=False,
                action_type="restart_service",
                message=f"Error restarting service: {str(e)}",
                error=str(e)
            )
    
    async def _action_cleanup_memory(self, params: Dict, context: Dict) -> ActionResult:
        """Clean up memory on a server."""
        server = params.get("server", "primary")
        
        try:
            import asyncssh
            
            host = "198.54.123.234" if server == "primary" else "162.0.208.88"
            
            async with asyncssh.connect(host, username="root", known_hosts=None) as conn:
                # Clear caches and clean up
                commands = [
                    "sync",
                    "echo 3 > /proc/sys/vm/drop_caches",
                    "journalctl --vacuum-time=1d",
                ]
                
                for cmd in commands:
                    await conn.run(cmd)
                
                # Get new memory status
                result = await conn.run("free -m | grep Mem | awk '{print $3/$2 * 100}'")
                memory_percent = float(result.stdout.strip()) if result.stdout.strip() else 0
                
                return ActionResult(
                    success=True,
                    action_type="cleanup_memory",
                    message=f"Memory cleanup complete on {server}. Usage: {memory_percent:.1f}%",
                    data={"server": server, "memory_percent": memory_percent}
                )
        except Exception as e:
            return ActionResult(
                success=False,
                action_type="cleanup_memory",
                message=f"Error cleaning memory: {str(e)}",
                error=str(e)
            )
    
    async def _action_run_command(self, params: Dict, context: Dict) -> ActionResult:
        """Run a shell command on a server."""
        command = params.get("value") or params.get("command", "")
        server = params.get("server", "secondary")
        
        if not command:
            return ActionResult(
                success=False,
                action_type="run_command",
                message="No command specified",
                error="Missing command parameter"
            )
        
        # Safety check - block dangerous commands
        dangerous = ["rm -rf /", "mkfs", "dd if=", "> /dev/"]
        if any(d in command for d in dangerous):
            return ActionResult(
                success=False,
                action_type="run_command",
                message="Command blocked for safety",
                error="Potentially dangerous command"
            )
        
        try:
            import asyncssh
            
            host = "198.54.123.234" if server == "primary" else "162.0.208.88"
            
            async with asyncssh.connect(host, username="root", known_hosts=None) as conn:
                result = await conn.run(command, timeout=60)
                
                return ActionResult(
                    success=result.exit_status == 0,
                    action_type="run_command",
                    message=f"Command executed on {server}",
                    data={
                        "command": command,
                        "stdout": result.stdout[:500] if result.stdout else "",
                        "stderr": result.stderr[:500] if result.stderr else "",
                        "exit_status": result.exit_status,
                    },
                    error=result.stderr if result.exit_status != 0 else None
                )
        except Exception as e:
            return ActionResult(
                success=False,
                action_type="run_command",
                message=f"Error running command: {str(e)}",
                error=str(e)
            )
    
    # =========================================================================
    # UTILITY ACTIONS
    # =========================================================================
    
    async def _action_delay(self, params: Dict, context: Dict) -> ActionResult:
        """Wait for a specified duration."""
        seconds = params.get("value") or params.get("seconds", 1)
        
        await asyncio.sleep(seconds)
        
        return ActionResult(
            success=True,
            action_type="delay",
            message=f"Waited {seconds} seconds",
            data={"seconds": seconds}
        )
    
    async def _action_log(self, params: Dict, context: Dict) -> ActionResult:
        """Log a message."""
        message = params.get("value") or params.get("message", "")
        level = params.get("level", "info").lower()
        
        log_func = getattr(logger, level, logger.info)
        log_func(f"Workflow log: {message}")
        
        return ActionResult(
            success=True,
            action_type="log",
            message=f"Logged: {message}",
            data={"message": message, "level": level}
        )


# Singleton instance
_library: Optional[ActionLibrary] = None


def get_action_library() -> ActionLibrary:
    """Get the global action library instance."""
    global _library
    if _library is None:
        _library = ActionLibrary()
    return _library


async def execute_action(action_def: Dict, context: Dict) -> ActionResult:
    """Execute an action definition."""
    library = get_action_library()
    return await library.execute(action_def, context)


# Pre-built action templates
ACTION_TEMPLATES = {
    "alert_price_drop": {
        "alert": "Price dropped below threshold!"
    },
    "close_half_position": {
        "close_position": {"percent": 50}
    },
    "tighten_stop": {
        "adjust_stop": {"price": 118}
    },
    "morning_update": {
        "alert": "Good morning! Here's your market update."
    },
}


def get_action_template(name: str) -> Optional[Dict]:
    """Get a pre-built action template."""
    return ACTION_TEMPLATES.get(name)



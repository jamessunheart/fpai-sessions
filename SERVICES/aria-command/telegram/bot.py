#!/usr/bin/env python3
"""
ARIA COMMAND CENTER - TELEGRAM BOT
===================================

Main Telegram interface for Aria Command Center.

Handles:
- Text commands
- Voice messages
- Inline keyboards
- Proactive notifications
"""

import os
import re
import asyncio
import logging
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass
from datetime import datetime
import httpx

logger = logging.getLogger("aria.telegram")

# ============================================================================
# CONFIGURATION
# ============================================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
SUNHEART_CHAT_ID = os.getenv("SUNHEART_CHAT_ID", "")


@dataclass
class CommandResult:
    """Result of command execution."""
    text: str
    voice: bool = False
    buttons: Optional[List[Dict]] = None
    success: bool = True


class AriaTelegramBot:
    """
    Main Telegram bot for Aria Command Center.
    
    Features:
    - Natural language understanding
    - Command routing
    - Voice input/output
    - Inline keyboards for approvals
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=60.0)
        self.command_handlers: Dict[str, Callable] = {}
        self.conversation_history: Dict[int, List[Dict]] = {}
        
        # Register default commands
        self._register_commands()
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    def _register_commands(self):
        """Register command handlers."""
        self.command_handlers = {
            "/status": self._handle_status,
            "/health": self._handle_health,
            "/positions": self._handle_positions,
            "/signals": self._handle_signals,
            "/signal": self._handle_signal,
            "/market": self._handle_market,
            "/brief": self._handle_brief,
            "/call": self._handle_call,  # Phone call via Twilio
            "/run": self._handle_run,
            "/read": self._handle_read,
            "/search": self._handle_search,
            "/git": self._handle_git,
            "/build": self._handle_build,
            "/pending": self._handle_pending,
            "/approve": self._handle_approve,
            "/cancel": self._handle_cancel,
            "/agents": self._handle_agents,
            "/schedule": self._handle_schedule,
            "/help": self._handle_help,
            # Opus Brain commands
            "/clear": self._handle_clear,
            "/continue": self._handle_continue,
            "/brain": self._handle_brain_status,
            # Server Ops commands
            "/servers": self._handle_servers,
            "/services": self._handle_services,
            "/restart": self._handle_restart,
            "/memory": self._handle_memory,
            "/docker": self._handle_docker,
            "/fix": self._handle_fix,
            "/logs": self._handle_logs,
            "/inventory": self._handle_inventory,
            "/activate": self._handle_activate,
            "/deactivate": self._handle_deactivate,
            # Evolution commands
            "/improvements": self._handle_improvements,
            "/proposals": self._handle_proposals,
            "/rollback": self._handle_rollback,
            "/evolution": self._handle_evolution,
            # Reflection (AI-to-AI) commands
            "/reflect": self._handle_reflect,
            # Workflow commands (Ultra Power Phase 1)
            "/workflow": self._handle_workflow,
            "/wf": self._handle_workflow,  # Shortcut
            # Autopilot commands (Ultra Power Phase 4)
            "/autopilot": self._handle_autopilot,
            "/ap": self._handle_autopilot,  # Shortcut
            "/portfolio": self._handle_portfolio,
            "/risk": self._handle_risk,
            # Authority management (Steward only)
            "/addapprentice": self._handle_add_apprentice,
            "/removeapprentice": self._handle_remove_apprentice,
            "/apprentices": self._handle_list_apprentices,
            "/authority": self._handle_authority,
            # Progress tracking
            "/progress": self._handle_progress,
            "/cohort": self._handle_cohort,
            "/costs": self._handle_costs,
            # Module management
            "/submit": self._handle_submit,
            "/reviews": self._handle_reviews,
            "/approvemod": self._handle_approve_module,
            "/rejectmod": self._handle_reject_module,
            "/modules": self._handle_modules,
            # Unified Builder commands
            "/queue": self._handle_build_queue,
            "/builds": self._handle_build_history,
            "/scope": self._handle_scope,
            "/buildrollback": self._handle_build_rollback,
            "/deploy": self._handle_deploy,
            "/templates": self._handle_templates,
            "/savetemplate": self._handle_save_template,
            "/usetemplate": self._handle_use_template,
            # Wallet & Pool commands (Conscious Wealth Fellowship)
            "/balance": self._handle_balance,
            "/pool": self._handle_pool,
            "/poolopt": self._handle_poolopt,
            "/returns": self._handle_returns,
            "/gift": self._handle_gift,
            "/giftlinks": self._handle_gift_links,
            "/cancelgift": self._handle_cancel_gift,
            "/transactions": self._handle_transactions,
            "/tx": self._handle_transactions,
            "/credit": self._handle_credit,
            "/setupsteward": self._handle_setup_steward,
            "/poolstats": self._handle_pool_stats,
        }
    
    async def _handle_clear(self, chat_id: int, args: str) -> CommandResult:
        """Handle /clear - reset conversation."""
        from ..brain import get_brain
        brain = get_brain()
        brain.clear(chat_id)
        return CommandResult(text="🧹 Conversation cleared. Starting fresh!")
    
    async def _handle_continue(self, chat_id: int, args: str) -> CommandResult:
        """Handle /continue - continue current plan."""
        from ..brain import get_brain
        brain = get_brain()
        response = await brain.continue_plan(chat_id)
        return CommandResult(text=response.message)
    
    async def _handle_brain_status(self, chat_id: int, args: str) -> CommandResult:
        """Handle /brain - show brain status."""
        from ..brain import get_brain_status
        status = get_brain_status(chat_id)
        
        parts = ["**🧠 Brain Status**\n"]
        parts.append(f"Messages: {status['message_count']}")
        
        if status['working_files']:
            parts.append(f"Working files: {len(status['working_files'])}")
        
        if status['modified_files']:
            parts.append(f"Modified: {len(status['modified_files'])}")
        
        if status['plan_progress']:
            p = status['plan_progress']
            parts.append(f"\nPlan: {p['description'][:50]}")
            parts.append(f"Progress: {p['current_step']}/{p['total_steps']}")
        
        stats = status['router_stats']
        parts.append(f"\nTotal cost: ${stats['total_cost']:.4f}")
        
        return CommandResult(text="\n".join(parts))
    
    async def handle_update(self, update: Dict) -> bool:
        """Handle incoming Telegram update."""
        if "message" not in update:
            if "callback_query" in update:
                return await self._handle_callback(update["callback_query"])
            return False
        
        message = update["message"]
        chat_id = message.get("chat", {}).get("id")
        
        if not chat_id:
            return False
        
        # Handle voice message
        if "voice" in message:
            return await self._handle_voice(chat_id, message["voice"]["file_id"])
        
        # Handle text message
        text = message.get("text", "")
        if not text:
            return False
        
        # Send typing indicator
        await self._send_typing(chat_id)
        
        # Process message
        result = await self._process_message(chat_id, text)
        
        # Send response
        await self._send_response(chat_id, result)
        
        return True
    
    async def _process_message(self, chat_id: int, text: str) -> CommandResult:
        """Process a text message."""
        text = text.strip()
        
        # Check for command
        if text.startswith("/"):
            return await self._handle_command(chat_id, text)
        
        # Natural language processing
        return await self._handle_natural(chat_id, text)
    
    async def _handle_command(self, chat_id: int, text: str) -> CommandResult:
        """Handle a /command."""
        parts = text.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Check built-in commands first
        if command in self.command_handlers:
            try:
                return await self.command_handlers[command](chat_id, args)
            except Exception as e:
                logger.error(f"Command {command} failed: {e}")
                return CommandResult(text=f"Command failed: {e}", success=False)
        
        # Check for community module commands
        try:
            from modules.loader import get_module_loader
            loader = get_module_loader()
            result = await loader.execute_command(command, args, chat_id, chat_id)
            
            if result is not None:
                if result.success:
                    return CommandResult(text=result.response)
                else:
                    return CommandResult(text=f"Module error: {result.error}", success=False)
        except Exception as e:
            logger.warning(f"Module check failed: {e}")
        
        return CommandResult(
            text=f"Unknown command: {command}\n\nUse /help for available commands."
        )
    
    async def _handle_natural(self, chat_id: int, text: str) -> CommandResult:
        """Handle natural language message."""
        text_lower = text.lower().strip()
        
        # ===== FAST PATH: "?" shortcut - instant trading signals =====
        if text_lower in ["?", "??", "status?", "update?", "check"]:
            return await self._handle_signals(chat_id, "")
        
        # ===== FAST PATH: Single symbol queries =====
        if text_lower.upper() in ["SOL", "BTC", "ETH", "XRP"]:
            return await self._handle_signal(chat_id, text_lower.upper())
        
        # Quick intent detection for known commands
        if text_lower in ["status", "how is everything", "what's running"]:
            return await self._handle_status(chat_id, "")
        
        if text_lower in ["positions", "trades", "holdings"]:
            return await self._handle_positions(chat_id, "")
        
        if text_lower in ["brief", "morning brief", "daily brief"]:
            return await self._handle_brief(chat_id, "")
        
        if text_lower == "help":
            return await self._handle_help(chat_id, "")
        
        # SMART TRADING SHORTCUTS - Direct API call, no approval needed
        import re
        
        # Pattern: "signal on X", "what's X signal", "X trading signal", etc.
        signal_patterns = [
            r"(?:what'?s?|get|check|show)\s+(?:the\s+)?(?:signal|signals)\s+(?:on|for)?\s*(\w+)",
            r"(\w+)\s+(?:signal|signals|trading)",
            r"(?:signal|signals)\s+(?:on|for)\s+(\w+)",
        ]
        
        for pattern in signal_patterns:
            match = re.search(pattern, text_lower)
            if match:
                symbol = match.group(1).upper()
                if symbol in ["SOL", "BTC", "ETH", "XRP", "SOLANA", "BITCOIN", "ETHEREUM"]:
                    # Normalize
                    if symbol == "SOLANA": symbol = "SOL"
                    if symbol == "BITCOIN": symbol = "BTC"
                    if symbol == "ETHEREUM": symbol = "ETH"
                    return await self._handle_signal(chat_id, symbol)
        
        # Quick market/trading queries
        if any(x in text_lower for x in ["all signals", "trading signals", "what to trade", "trade now"]):
            return await self._handle_signals(chat_id, "")
        
        if any(x in text_lower for x in ["market", "volatility", "market condition"]):
            return await self._handle_market(chat_id, "")
        
        # Server shortcuts
        if any(x in text_lower for x in ["server status", "how are servers", "servers ok"]):
            return await self._handle_servers(chat_id, "")
        
        if any(x in text_lower for x in ["memory", "ram", "disk space"]):
            return await self._handle_memory(chat_id, "")
        
        # Fast-path for trading commands
        try:
            from trading import is_trading_related, handle_trading_message
            if is_trading_related(text):
                trading_response = await handle_trading_message(text)
                if trading_response:
                    return CommandResult(text=trading_response)
        except ImportError:
            pass  # Trading module not loaded
        except Exception as e:
            logger.warning(f"Trading fast-path failed: {e}")
        
        # Everything else goes to Opus Brain for intelligent processing
        return await self._handle_opus(chat_id, text)
    
    async def _handle_opus(self, chat_id: int, text: str) -> CommandResult:
        """Handle message through Opus Brain (Cursor-level intelligence)."""
        try:
            from .opus_handler import process_telegram_message
        except ImportError:
            from telegram.opus_handler import process_telegram_message
        import asyncio
        
        # Send immediate acknowledgment for complex queries
        is_complex = any(w in text.lower() for w in [
            "look at", "analyze", "read", "check", "build", "create", 
            "fix", "improve", "code", "file", "what can you"
        ])
        
        if is_complex:
            # Send quick "thinking" message
            await send_message(chat_id, "🧠 *Analyzing...* give me a moment")
        
        # Keep sending typing indicators in background
        async def keep_typing():
            while True:
                await self._send_typing(chat_id)
                await asyncio.sleep(4)  # Telegram typing lasts ~5 seconds
        
        typing_task = asyncio.create_task(keep_typing())
        
        try:
            logger.info(f"Starting Opus brain for chat {chat_id}: {text[:50]}...")
            response = await process_telegram_message(chat_id, text)
            logger.info(f"Opus brain completed for chat {chat_id}: {len(response)} chars")
            return CommandResult(text=response)
        except Exception as e:
            logger.error(f"Opus brain error for chat {chat_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Fallback to simple AI
            return await self._handle_ai_chat(chat_id, text)
        finally:
            typing_task.cancel()
            try:
                await typing_task
            except asyncio.CancelledError:
                pass
    
    async def _handle_voice(self, chat_id: int, file_id: str) -> bool:
        """Handle voice message."""
        await self._send_typing(chat_id)
        
        try:
            from ..voice.transcribe import transcribe_voice
            
            text = await transcribe_voice(file_id)
            if not text:
                await send_message(chat_id, "Couldn't transcribe that. Try again?")
                return False
            
            # Process transcribed text
            result = await self._process_message(chat_id, text)
            
            # Reply with voice if short enough
            if len(result.text) < 500:
                result.voice = True
            
            await self._send_response(chat_id, result)
            return True
            
        except Exception as e:
            logger.error(f"Voice handling failed: {e}")
            await send_message(chat_id, "Voice processing error. Try text instead.")
            return False
    
    async def _handle_callback(self, callback: Dict) -> bool:
        """Handle callback query from inline keyboard."""
        chat_id = callback.get("message", {}).get("chat", {}).get("id")
        callback_id = callback.get("id")
        data = callback.get("data", "")
        
        if not chat_id or not data:
            return False
        
        # Answer callback to remove loading state
        await self.http.post(
            f"{TELEGRAM_API}/answerCallbackQuery",
            json={"callback_query_id": callback_id}
        )
        
        # Route callback
        if data.startswith("approve:"):
            proposal_id = data.split(":")[1]
            result = await self._handle_approve(chat_id, proposal_id)
            await self._send_response(chat_id, result)
            
        elif data.startswith("deny:"):
            proposal_id = data.split(":")[1]
            result = await self._handle_cancel(chat_id, proposal_id)
            await self._send_response(chat_id, result)
            
        elif data.startswith("run:"):
            command = data.split(":", 1)[1]
            result = await self._handle_run(chat_id, command)
            await self._send_response(chat_id, result)
        
        elif data.startswith("ops_approve:"):
            approval_id = data.split(":")[1]
            try:
                from ..ops.server_ops import server_ops
            except ImportError:
                from ops.server_ops import server_ops
            result_text = await server_ops.approve_action(approval_id)
            await send_message(chat_id, result_text)
        
        elif data == "ops_cancel":
            await send_message(chat_id, "🗑️ Operation cancelled.")
        
        # Membership/Pool callbacks
        elif data.startswith("pma_") or data.startswith("trading_") or data.startswith("accept_gift:") or data.startswith("decline_gift:"):
            try:
                from telegram.callback_handler import handle_callback, answer_callback_query, edit_message
                
                user = callback.get("from", {})
                telegram_username = user.get("username")
                message_id = callback.get("message", {}).get("message_id")
                
                answer_text, new_message_text = await handle_callback(
                    callback_id,
                    data,
                    chat_id,
                    telegram_username,
                    chat_id,
                    message_id
                )
                
                await answer_callback_query(callback_id, answer_text)
                
                if new_message_text and message_id:
                    await edit_message(chat_id, message_id, new_message_text)
                    
            except Exception as e:
                logger.error(f"Membership callback error: {e}")
                await send_message(chat_id, f"❌ Error processing: {e}")
        
        return True
    
    # ========== COMMAND HANDLERS ==========
    
    async def _handle_status(self, chat_id: int, args: str) -> CommandResult:
        """Handle /status command."""
        from ..proactive.monitors import quick_health_check
        from ..agents.registry import get_agent_status
        
        health = await quick_health_check()
        agents = get_agent_status()
        
        # Build status message
        msg = "**🖥️ System Status**\n\n"
        
        # Services
        msg += "**Services:**\n"
        for service, data in health.items():
            emoji = "✅" if data.get("healthy") else "❌"
            msg += f"  {emoji} {service}\n"
        
        # Agents
        msg += "\n**Agents:**\n"
        for agent_id, data in agents.get("agents", {}).items():
            status_emoji = {"online": "🟢", "offline": "🔴", "busy": "🟡"}.get(data["status"], "⚪")
            msg += f"  {status_emoji} {data['name']}"
            if data.get("current_task"):
                msg += f" - {data['current_task']}"
            msg += "\n"
        
        return CommandResult(text=msg)
    
    async def _handle_health(self, chat_id: int, args: str) -> CommandResult:
        """Handle /health command."""
        from ..proactive.monitors import get_monitor
        
        monitor = get_monitor()
        result = await monitor.check_all()
        
        if result.healthy:
            msg = "✅ **All Systems Healthy**\n\n"
        else:
            msg = "⚠️ **Health Issues Detected**\n\n"
        
        for alert in result.alerts[:5]:
            msg += f"• {alert.message}\n"
        
        return CommandResult(text=msg)
    
    async def _handle_positions(self, chat_id: int, args: str) -> CommandResult:
        """Handle /positions command."""
        from ..trading.awareness import get_positions
        return CommandResult(text=await get_positions())
    
    async def _handle_signals(self, chat_id: int, args: str) -> CommandResult:
        """Handle /signals command."""
        from ..trading.awareness import get_signals
        return CommandResult(text=await get_signals())
    
    async def _handle_signal(self, chat_id: int, args: str) -> CommandResult:
        """Handle /signal <symbol> command - get signal for specific asset."""
        if not args:
            return CommandResult(
                text="📊 **Usage:** `/signal SOL` or `/signal BTC`\n\n"
                     "Available symbols: SOL, BTC, ETH, XRP"
            )
        
        from ..trading.awareness import get_signal
        symbol = args.strip().upper()
        return CommandResult(text=await get_signal(symbol))
    
    async def _handle_market(self, chat_id: int, args: str) -> CommandResult:
        """Handle /market command."""
        from ..trading.awareness import get_market
        return CommandResult(text=await get_market())
    
    async def _handle_brief(self, chat_id: int, args: str) -> CommandResult:
        """Handle /brief command."""
        from ..proactive.digest import get_quick_brief
        brief = await get_quick_brief()
        return CommandResult(text=brief, voice=True)
    
    async def _handle_run(self, chat_id: int, args: str) -> CommandResult:
        """Handle /run command."""
        if not args:
            return CommandResult(
                text="Usage: /run <server> <command>\n\nServers: primary, secondary, local, all"
            )
        
        parts = args.split(maxsplit=1)
        server = parts[0].lower()
        command = parts[1] if len(parts) > 1 else ""
        
        if not command:
            return CommandResult(text="Please provide a command to run.")
        
        from ..access.terminal import run_command, classify_command
        
        # Check safety
        safety = classify_command(command)
        
        if safety in ["yellow", "red"]:
            buttons = [[
                {"text": "✅ Approve", "callback_data": f"run:{server}|{command}"},
                {"text": "❌ Cancel", "callback_data": "cancel:run"}
            ]]
            return CommandResult(
                text=f"⚠️ **{safety.upper()} Level Command**\n\n`{command}`\n\nApprove execution?",
                buttons=buttons
            )
        
        # Execute green command
        result = await run_command(command, server)
        
        if result.success:
            output = result.stdout[:2000] if result.stdout else "Command completed."
            return CommandResult(text=f"```\n{output}\n```")
        else:
            return CommandResult(text=f"❌ Error: {result.error}", success=False)
    
    async def _handle_read(self, chat_id: int, args: str) -> CommandResult:
        """Handle /read command."""
        if not args:
            return CommandResult(text="Usage: /read <path>\n\nExamples:\n/read server.py\n/read primary:/opt/fpai/aria/server.py")
        
        from ..access.filesystem import read_file
        
        result = await read_file(args, max_lines=100)
        
        if result.success:
            msg = f"**{result.path}**\n\n```python\n{result.content[:3000]}\n```"
            if result.truncated:
                msg += "\n_(truncated)_"
            return CommandResult(text=msg)
        else:
            return CommandResult(text=f"❌ {result.error}", success=False)
    
    async def _handle_search(self, chat_id: int, args: str) -> CommandResult:
        """Handle /search command."""
        if not args:
            return CommandResult(text="Usage: /search <pattern>")
        
        from ..access.filesystem import search_code
        
        results = await search_code(args)
        
        if not results:
            return CommandResult(text=f"No results for: {args}")
        
        msg = f"**Search: {args}**\n\n"
        for r in results[:10]:
            msg += f"📄 `{r['file']}:{r['line']}`\n"
            msg += f"   {r['content'][:80]}...\n\n"
        
        if len(results) > 10:
            msg += f"_...and {len(results) - 10} more_"
        
        return CommandResult(text=msg)
    
    async def _handle_git(self, chat_id: int, args: str) -> CommandResult:
        """Handle /git command."""
        if not args:
            args = "status"
        
        from ..access.git_ops import get_git
        
        git = get_git()
        cmd = args.split()[0]
        cmd_args = args.split()[1:] if len(args.split()) > 1 else []
        
        if cmd == "status":
            result = await git.status()
        elif cmd == "log":
            result = await git.log()
        elif cmd == "diff":
            result = await git.diff()
        elif cmd == "branch":
            if cmd_args:
                result = await git.branch(cmd_args[0])
            else:
                branches = await git.get_branches()
                msg = "**Branches:**\n"
                for b in branches:
                    prefix = "→ " if b.is_current else "  "
                    msg += f"{prefix}{b.name}\n"
                return CommandResult(text=msg)
        elif cmd == "commit":
            if cmd_args:
                result = await git.commit(" ".join(cmd_args), add_all=True)
            else:
                return CommandResult(text="Usage: /git commit <message>")
        elif cmd == "push":
            result = await git.push()
        else:
            return CommandResult(text=f"Unknown git command: {cmd}")
        
        return CommandResult(text=result.output if result.success else f"❌ {result.error}")
    
    async def _handle_build(self, chat_id: int, args: str) -> CommandResult:
        """Handle /build command - uses unified builder with AI code generation."""
        try:
            from builder.telegram_interface import get_builder_interface
            from access.authority import get_user_authority
            
            interface = get_builder_interface()
            user_id = chat_id  # In DM, chat_id == user_id
            
            # Determine scope
            authority = get_user_authority(user_id)
            scope = "steward" if authority == "steward" else "apprentice"
            
            # Route through builder interface
            result = await interface.handle_command(
                chat_id=chat_id,
                user_id=user_id,
                command="/build",
                args=args.split() if args else [],
                scope=scope
            )
            
            return CommandResult(text=result if result else "Build command processed")
        except Exception as e:
            logger.error(f"Build command failed: {e}")
            return CommandResult(text=f"Build failed: {e}", success=False)
    
    async def _handle_pending(self, chat_id: int, args: str) -> CommandResult:
        """Handle /pending command - show pending builds."""
        try:
            from builder.telegram_interface import get_builder_interface
            from access.authority import get_user_authority
            
            interface = get_builder_interface()
            authority = get_user_authority(chat_id)
            scope = "steward" if authority == "steward" else "apprentice"
            
            result = await interface.handle_command(
                chat_id=chat_id,
                user_id=chat_id,
                command="/pending",
                args=[],
                scope=scope
            )
            
            return CommandResult(text=result if result else "No pending changes")
        except Exception as e:
            logger.error(f"Pending check failed: {e}")
            return CommandResult(text=f"Could not fetch pending: {e}", success=False)
    
    async def _handle_approve(self, chat_id: int, args: str) -> CommandResult:
        """Handle /approve command - approve a build."""
        if not args:
            return CommandResult(text="Usage: /approve <job_id>")
        
        try:
            from builder.telegram_interface import get_builder_interface
            from access.authority import get_user_authority
            
            interface = get_builder_interface()
            authority = get_user_authority(chat_id)
            scope = "steward" if authority == "steward" else "apprentice"
            
            result = await interface.handle_command(
                chat_id=chat_id,
                user_id=chat_id,
                command="/approve",
                args=args.split(),
                scope=scope
            )
            
            return CommandResult(text=result if result else "Approved")
        except Exception as e:
            logger.error(f"Approve failed: {e}")
            return CommandResult(text=f"Approval failed: {e}", success=False)
    
    async def _handle_cancel(self, chat_id: int, args: str) -> CommandResult:
        """Handle /cancel command - cancel/deny a build."""
        if not args:
            return CommandResult(text="Usage: /cancel <job_id>")
        
        try:
            from builder.telegram_interface import get_builder_interface
            from access.authority import get_user_authority
            
            interface = get_builder_interface()
            authority = get_user_authority(chat_id)
            scope = "steward" if authority == "steward" else "apprentice"
            
            result = await interface.handle_command(
                chat_id=chat_id,
                user_id=chat_id,
                command="/deny",
                args=args.split(),
                scope=scope
            )
            
            return CommandResult(text=result if result else f"🗑️ Cancelled: {args[:8]}")
        except Exception as e:
            logger.error(f"Cancel failed: {e}")
            return CommandResult(text=f"Cancel failed: {e}", success=False)
    
    async def _handle_build_queue(self, chat_id: int, args: str) -> CommandResult:
        """Handle /queue command - show build queue status."""
        try:
            from builder.telegram_interface import get_builder_interface
            from access.authority import get_user_authority
            
            interface = get_builder_interface()
            authority = get_user_authority(chat_id)
            scope = "steward" if authority == "steward" else "apprentice"
            
            result = await interface.handle_command(
                chat_id=chat_id,
                user_id=chat_id,
                command="/queue",
                args=[],
                scope=scope
            )
            
            return CommandResult(text=result if result else "Queue is empty")
        except Exception as e:
            logger.error(f"Queue check failed: {e}")
            return CommandResult(text=f"Queue check failed: {e}", success=False)
    
    async def _handle_build_history(self, chat_id: int, args: str) -> CommandResult:
        """Handle /builds command - show recent build history."""
        try:
            from builder.telegram_interface import get_builder_interface
            from access.authority import get_user_authority
            
            interface = get_builder_interface()
            authority = get_user_authority(chat_id)
            scope = "steward" if authority == "steward" else "apprentice"
            
            result = await interface.handle_command(
                chat_id=chat_id,
                user_id=chat_id,
                command="/builds",
                args=[],
                scope=scope
            )
            
            return CommandResult(text=result if result else "No builds yet")
        except Exception as e:
            logger.error(f"Build history failed: {e}")
            return CommandResult(text=f"Build history failed: {e}", success=False)
    
    async def _handle_scope(self, chat_id: int, args: str) -> CommandResult:
        """Handle /scope command - show user's builder permissions."""
        try:
            from builder.telegram_interface import get_builder_interface
            from access.authority import get_user_authority
            
            interface = get_builder_interface()
            authority = get_user_authority(chat_id)
            scope = "steward" if authority == "steward" else "apprentice"
            
            result = await interface.handle_command(
                chat_id=chat_id,
                user_id=chat_id,
                command="/scope",
                args=[],
                scope=scope
            )
            
            return CommandResult(text=result if result else "Scope information unavailable")
        except Exception as e:
            logger.error(f"Scope check failed: {e}")
            return CommandResult(text=f"Scope check failed: {e}", success=False)
    
    async def _handle_build_rollback(self, chat_id: int, args: str) -> CommandResult:
        """Handle /buildrollback command - rollback a completed build."""
        if not args:
            return CommandResult(text="Usage: /buildrollback <job_id>")
        
        try:
            from builder.telegram_interface import get_builder_interface
            from access.authority import get_user_authority
            
            interface = get_builder_interface()
            authority = get_user_authority(chat_id)
            scope = "steward" if authority == "steward" else "apprentice"
            
            result = await interface.handle_command(
                chat_id=chat_id,
                user_id=chat_id,
                command="/rollback",
                args=args.split(),
                scope=scope
            )
            
            return CommandResult(text=result if result else "Rollback processed")
        except Exception as e:
            logger.error(f"Build rollback failed: {e}")
            return CommandResult(text=f"Rollback failed: {e}", success=False)
    
    async def _handle_deploy(self, chat_id: int, args: str) -> CommandResult:
        """Handle /deploy command - manually deploy/restart a service."""
        if not args:
            # List available services
            from builder.unified_engine import SERVICE_MAP, PRODUCTION_SERVICES
            
            services = sorted(set(SERVICE_MAP.values()))
            msg = "**🚀 Deploy Service**\n\n"
            msg += "Usage: `/deploy <service_name>`\n\n"
            msg += "Available services:\n"
            for svc in services:
                prod = " ⚠️ PROD" if svc in PRODUCTION_SERVICES else ""
                msg += f"  `{svc}`{prod}\n"
            
            return CommandResult(text=msg)
        
        service_name = args.strip().split()[0]
        
        # Check authority
        from access.authority import get_user_authority
        authority = get_user_authority(chat_id)
        
        if authority != "steward":
            return CommandResult(text="🚫 Only stewards can deploy services.", success=False)
        
        # Check if production
        from builder.unified_engine import is_production_service
        if is_production_service(service_name):
            # Require confirmation
            return CommandResult(
                text=f"⚠️ **Production Service Warning**\n\n`{service_name}` is a production service.\n\nTo confirm, use:\n`/deploy {service_name} CONFIRM`",
                success=True
            )
        
        # Check for CONFIRM flag for production
        parts = args.strip().split()
        if len(parts) > 1 and parts[1].upper() == "CONFIRM":
            # Confirmed production deploy
            pass
        elif is_production_service(service_name):
            return CommandResult(
                text=f"⚠️ Add CONFIRM to deploy production: `/deploy {service_name} CONFIRM`",
                success=False
            )
        
        try:
            from builder import get_unified_builder
            builder = get_unified_builder()
            success, message = await builder.manual_deploy(service_name)
            
            emoji = "✅" if success else "❌"
            return CommandResult(text=f"{emoji} **Deploy Result**\n\n{service_name}: {message}")
        except Exception as e:
            logger.error(f"Deploy failed: {e}")
            return CommandResult(text=f"Deploy failed: {e}", success=False)
    
    async def _handle_templates(self, chat_id: int, args: str) -> CommandResult:
        """Handle /templates command - list saved build templates."""
        try:
            from builder import get_unified_builder
            
            builder = get_unified_builder()
            templates = builder.get_templates(limit=10)
            
            if not templates:
                return CommandResult(text="📋 No build templates saved yet.\n\nUse `/savetemplate <job_id> <name>` to save a successful build as a template.")
            
            msg = "📋 **Build Templates**\n\n"
            for t in templates:
                success_pct = int(t.get('success_rate', 1.0) * 100)
                uses = t.get('use_count', 0)
                msg += f"• `{t['id']}` - **{t['name']}**\n"
                msg += f"  Pattern: _{t.get('pattern', 'N/A')[:40]}_\n"
                msg += f"  Uses: {uses} | Success: {success_pct}%\n\n"
            
            msg += "Use `/usetemplate <id>` to create a build from a template."
            
            return CommandResult(text=msg)
        except Exception as e:
            logger.error(f"Templates failed: {e}")
            return CommandResult(text=f"Failed to get templates: {e}", success=False)
    
    async def _handle_save_template(self, chat_id: int, args: str) -> CommandResult:
        """Handle /savetemplate command - save a build as template."""
        parts = args.split(maxsplit=1) if args else []
        
        if len(parts) < 2:
            return CommandResult(text="Usage: `/savetemplate <job_id> <template_name>`\n\nExample: `/savetemplate abc123 health-endpoint`")
        
        job_id = parts[0]
        name = parts[1]
        
        try:
            from builder import get_unified_builder, BuildJob, BuildStatus, FileChange
            import json
            
            builder = get_unified_builder()
            
            # Get job
            job_data = builder.get_job(job_id)
            if not job_data:
                return CommandResult(text=f"Job `{job_id}` not found.", success=False)
            
            if job_data.get('status') != 'completed':
                return CommandResult(text=f"Only completed builds can be saved as templates. Status: {job_data.get('status')}", success=False)
            
            # Reconstruct job
            changes = [FileChange.from_dict(c) for c in json.loads(job_data.get('changes_json', '[]'))]
            
            job = BuildJob(
                id=job_data['id'],
                title=job_data['title'],
                description=job_data.get('description', ''),
                changes=changes,
                author=job_data['author'],
                scope=job_data['scope'],
                status=BuildStatus.COMPLETED
            )
            
            success, result = builder.save_as_template(job, name)
            
            if success:
                return CommandResult(text=f"✅ **Template Saved**\n\nID: `{result}`\nName: {name}\n\nUse `/usetemplate {result}` to use it.")
            else:
                return CommandResult(text=f"Failed to save template: {result}", success=False)
        except Exception as e:
            logger.error(f"Save template failed: {e}")
            return CommandResult(text=f"Failed to save template: {e}", success=False)
    
    async def _handle_use_template(self, chat_id: int, args: str) -> CommandResult:
        """Handle /usetemplate command - create build from template."""
        if not args:
            return CommandResult(text="Usage: `/usetemplate <template_id>`\n\nUse `/templates` to list available templates.")
        
        template_id = args.strip().split()[0]
        
        try:
            from builder import get_unified_builder
            from access.authority import get_user_authority
            
            builder = get_unified_builder()
            authority = get_user_authority(chat_id)
            scope = "steward" if authority == "steward" else "apprentice"
            
            job = builder.use_template(template_id, str(chat_id), scope)
            
            if job:
                status_msg = "queued for execution" if job.status.value == "queued" else "needs approval"
                return CommandResult(
                    text=f"✅ **Build Created from Template**\n\nJob ID: `{job.id}`\nTitle: {job.title}\nStatus: {status_msg}\n\nChanges: {len(job.changes)} files"
                )
            else:
                return CommandResult(text=f"Template `{template_id}` not found.", success=False)
        except Exception as e:
            logger.error(f"Use template failed: {e}")
            return CommandResult(text=f"Failed to use template: {e}", success=False)
    
    async def _handle_agents(self, chat_id: int, args: str) -> CommandResult:
        """Handle /agents command."""
        from ..agents.registry import get_registry
        
        registry = get_registry()
        status = registry.get_status()
        
        msg = "**🤖 Agent Registry**\n\n"
        
        for agent_id, data in status["agents"].items():
            emoji = {"online": "🟢", "offline": "🔴", "busy": "🟡"}.get(data["status"], "⚪")
            msg += f"{emoji} **{data['name']}**\n"
            if data.get("current_task"):
                msg += f"   Task: {data['current_task']}\n"
            if data.get("last_heartbeat"):
                msg += f"   Last seen: {data['last_heartbeat'][:19]}\n"
            msg += "\n"
        
        msg += f"📬 Pending messages: {status['pending_messages']}\n"
        msg += f"🔒 Active locks: {status['file_locks']}"
        
        return CommandResult(text=msg)
    
    async def _handle_schedule(self, chat_id: int, args: str) -> CommandResult:
        """Handle /schedule command."""
        from ..core.scheduler import get_scheduler_status
        
        status = get_scheduler_status()
        
        msg = "**⏰ Scheduled Tasks**\n\n"
        
        for task_id, data in status["tasks"].items():
            emoji = "✅" if data["enabled"] else "⏸️"
            msg += f"{emoji} **{data['name']}**\n"
            if data["next_run"]:
                msg += f"   Next: {data['next_run'][:19]}\n"
            msg += f"   Runs: {data['run_count']}"
            if data["error_count"]:
                msg += f" | Errors: {data['error_count']}"
            msg += "\n\n"
        
        msg += f"📬 Queued messages: {status['queue_size']}"
        
        return CommandResult(text=msg)
    
    async def _handle_help(self, chat_id: int, args: str) -> CommandResult:
        """Handle /help command."""
        msg = """**🎯 Aria Command Center**

**🎤 Voice & Calling:**
🎙️ Send voice message → I hear & reply with voice!
📞 /call → I'll call your phone for real conversation
💬 Just talk naturally - I understand context

**🧠 Intelligent Building:**
Just tell me what to build in plain English!
- "Add a /treasury command"
- "Fix the bug in server.py"
- "Create a webhook handler"

**🖥️ Server Operations:**
/servers - Full system health (both servers)
/services - List running services
/inventory - All available services
/activate <svc> - Turn on a service
/deactivate <svc> - Turn off a service
/restart <svc> - Restart a service
/memory - Memory usage & recommendations
/docker - Docker container status
/fix <issue> - Auto-fix common issues
/logs <svc> - View service logs

**Brain Control:**
/brain - Show brain status & costs
/clear - Start fresh conversation
/continue - Continue multi-step plan

**System:**
/status - System overview
/health - Health check
/brief - Daily briefing 🔊

**Trading:**
/positions - Open positions
/signals - Active signals
/market - Market context

**Workflows (Automation):**
/workflow list - Your automations
/workflow create - New workflow
/wf <id> - Workflow details

**Autopilot (Trading):**
/autopilot status - Current mode
/autopilot monitor/guided/auto/off
/portfolio - Portfolio status
/risk - Risk assessment

**Files & Code:**
/read <path> - Read file
/search <pattern> - Search code
/git <cmd> - Git operations

**Building:**
/build <desc> - Create build proposal
/pending - View pending changes
/approve <id> - Approve change

**Execution:**
/run <server> <cmd> - Run command

**Auto-Fix Examples:**
/fix docker - Fix Docker startup
/fix memory - Free up RAM

**🧬 Self-Improvement:**
/improvements - Recent applied improvements
/proposals - Pending improvement proposals
/rollback <id> - Undo a change
/evolution analyze - Run pattern detection
/evolution summary - Show statistics
/fix ssh - Check connectivity

**🔄 AI Reflection:**
/reflect - AI-to-AI improvement system
/reflect now - Trigger immediate reflection
/reflect status - System status & cost
/reflect history - Recent specs generated

**💰 Wallet & Pool:**
/balance - Check your wallet
/pool - Trading pool status
/poolopt [in/out] - Opt in/out of pool
/returns - View trading returns
/gift @user amount - Send via Telegram
/gift link amount - Create link for email/WhatsApp
/giftlinks - View pending gift links
/transactions - Transaction history

**Tips:**
• 🎤 Voice messages work great!
• 📞 /call for phone conversation
• I remember our conversation
• Complex tasks → step-by-step plan
• Server issues? Just tell me to fix them!

_Just describe what you want!_"""
        
        return CommandResult(text=msg)
    
    async def _handle_call(self, chat_id: int, args: str) -> CommandResult:
        """Handle /call command - initiate phone call to James."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://localhost:8888/call",
                    json={"phone_number": "+19252397291"}
                )
                if response.status_code == 200:
                    return CommandResult(
                        text="📞 **Calling you now!**\n\nPick up your phone - I'll be on the line with GPT-4o Realtime voice.",
                        voice=True
                    )
                else:
                    return CommandResult(
                        text=f"❌ Call failed: {response.text}",
                        success=False
                    )
        except Exception as e:
            return CommandResult(
                text=f"❌ Couldn't initiate call: {e}\n\nMake sure voice-phone service is running.",
                success=False
            )
    
    # ========== SERVER OPS HANDLERS ==========
    
    async def _handle_servers(self, chat_id: int, args: str) -> CommandResult:
        """Handle /servers - comprehensive system status."""
        try:
            from ..ops.server_ops import server_ops
        except ImportError:
            from ops.server_ops import server_ops
        
        status = await server_ops.get_system_status()
        return CommandResult(text=status)
    
    async def _handle_services(self, chat_id: int, args: str) -> CommandResult:
        """Handle /services - list running services."""
        try:
            from ..ops.server_ops import server_ops, Server
        except ImportError:
            from ops.server_ops import server_ops, Server
        
        server = Server.BOTH
        if args:
            if "primary" in args.lower():
                server = Server.PRIMARY
            elif "secondary" in args.lower():
                server = Server.SECONDARY
        
        services = await server_ops.get_services(server)
        return CommandResult(text=services)
    
    async def _handle_restart(self, chat_id: int, args: str) -> CommandResult:
        """Handle /restart <service> - restart a service."""
        try:
            from ..ops.server_ops import server_ops
        except ImportError:
            from ops.server_ops import server_ops
        
        if not args:
            return CommandResult(
                text="Usage: /restart <service_name>\n\nExamples:\n"
                "/restart whaletrack-live\n"
                "/restart godmode\n"
                "/restart aria-command"
            )
        
        service = args.strip()
        force = "force" in args.lower() or "!" in args
        service = service.replace("force", "").replace("!", "").strip()
        
        message, approval_id = await server_ops.restart_service(service, force=force)
        
        if approval_id:
            buttons = [[
                {"text": "✅ Approve", "callback_data": f"ops_approve:{approval_id[:8]}"},
                {"text": "❌ Cancel", "callback_data": "ops_cancel"}
            ]]
            return CommandResult(text=message, buttons=buttons)
        
        return CommandResult(text=message)
    
    async def _handle_memory(self, chat_id: int, args: str) -> CommandResult:
        """Handle /memory - detailed memory status."""
        try:
            from ..ops.server_ops import server_ops
        except ImportError:
            from ops.server_ops import server_ops
        
        status = await server_ops.get_memory_status()
        return CommandResult(text=status)
    
    async def _handle_docker(self, chat_id: int, args: str) -> CommandResult:
        """Handle /docker - Docker status and management."""
        try:
            from ..ops.server_ops import server_ops
        except ImportError:
            from ops.server_ops import server_ops
        
        status = await server_ops.get_docker_status()
        return CommandResult(text=status)
    
    async def _handle_fix(self, chat_id: int, args: str) -> CommandResult:
        """Handle /fix <issue> - auto-fix common issues."""
        try:
            from ..ops.server_ops import server_ops
        except ImportError:
            from ops.server_ops import server_ops
        
        if not args:
            return CommandResult(
                text="🔧 **Auto-Fix Options:**\n\n"
                "/fix docker - Fix Docker startup issues\n"
                "/fix memory - Free up memory by stopping non-critical services\n"
                "/fix ssh - Check SSH connectivity to primary server"
            )
        
        result = await server_ops.auto_fix(args)
        return CommandResult(text=result)
    
    async def _handle_logs(self, chat_id: int, args: str) -> CommandResult:
        """Handle /logs <service> - view recent logs."""
        try:
            from ..ops.server_ops import server_ops
        except ImportError:
            from ops.server_ops import server_ops
        
        if not args:
            return CommandResult(
                text="Usage: /logs <service_name> [lines]\n\n"
                "Examples:\n"
                "/logs whaletrack-live\n"
                "/logs godmode 50\n"
                "/logs aria-command"
            )
        
        parts = args.split()
        service = parts[0]
        lines = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 20
        
        logs = await server_ops.get_logs(service, lines)
        return CommandResult(text=logs)
    
    async def _handle_inventory(self, chat_id: int, args: str) -> CommandResult:
        """Handle /inventory - show all available services."""
        try:
            from ..ops.server_ops import server_ops
        except ImportError:
            from ops.server_ops import server_ops
        
        inventory = await server_ops.get_service_inventory()
        return CommandResult(text=inventory)
    
    async def _handle_activate(self, chat_id: int, args: str) -> CommandResult:
        """Handle /activate <service> - activate a disabled service."""
        try:
            from ..ops.server_ops import server_ops, Server
        except ImportError:
            from ops.server_ops import server_ops, Server
        
        if not args:
            return CommandResult(
                text="Usage: /activate <service_name> [server]\n\n"
                "Examples:\n"
                "/activate revenue-intelligence\n"
                "/activate music-maestro\n"
                "/activate brick2-autopilot\n\n"
                "Use /inventory to see available services."
            )
        
        parts = args.split()
        service = parts[0]
        server = Server.SECONDARY  # Default to secondary (more RAM)
        if len(parts) > 1 and "primary" in parts[1].lower():
            server = Server.PRIMARY
        
        result = await server_ops.activate_service(service, server)
        return CommandResult(text=result)
    
    async def _handle_deactivate(self, chat_id: int, args: str) -> CommandResult:
        """Handle /deactivate <service> - deactivate a running service."""
        try:
            from ..ops.server_ops import server_ops, Server
        except ImportError:
            from ops.server_ops import server_ops, Server
        
        if not args:
            return CommandResult(
                text="Usage: /deactivate <service_name>\n\n"
                "Example: /deactivate music-maestro\n\n"
                "Note: Cannot deactivate critical services."
            )
        
        service = args.strip().split()[0]
        
        # Determine server
        server = Server.SECONDARY
        if any(s in service for s in ["whale", "godmode", "nginx", "credits"]):
            server = Server.PRIMARY
        
        result = await server_ops.deactivate_service(service, server)
        return CommandResult(text=result)
    
    # ========================================================================
    # EVOLUTION COMMANDS
    # ========================================================================
    
    async def _handle_improvements(self, chat_id: int, args: str) -> CommandResult:
        """Handle /improvements - show recent applied improvements."""
        try:
            import sqlite3
            DB_PATH = "/opt/fpai/aria-command/state/evolution.db"
            
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get recent applied changes
            cursor.execute("""
                SELECT c.id, c.created_at, c.change_type, c.reason, c.status,
                       p.category, p.problem, p.solution
                FROM evolution_changes c
                LEFT JOIN improvement_proposals p ON c.proposal_id = p.id
                WHERE c.status IN ('applied', 'rolled_back')
                ORDER BY c.created_at DESC
                LIMIT 10
            """)
            
            changes = cursor.fetchall()
            conn.close()
            
            if not changes:
                return CommandResult(
                    text="📊 **No improvements applied yet.**\n\n"
                    "The evolution system is monitoring interactions and will "
                    "propose improvements when it detects patterns."
                )
            
            lines = ["📊 **Recent Improvements**\n"]
            
            for c in changes:
                status_emoji = "✅" if c['status'] == 'applied' else "↩️"
                category = c['category'] or c['change_type'] or 'unknown'
                
                lines.append(f"{status_emoji} **#{c['id']}** - {category}")
                
                if c['problem']:
                    lines.append(f"   Problem: {c['problem'][:60]}...")
                if c['solution']:
                    lines.append(f"   Fix: {c['solution'][:60]}...")
                if c['status'] == 'rolled_back':
                    lines.append(f"   _Rolled back_")
                lines.append("")
            
            lines.append("Use `/rollback <id>` to undo any change.")
            
            return CommandResult(text="\n".join(lines))
            
        except Exception as e:
            return CommandResult(text=f"❌ Error fetching improvements: {e}")
    
    async def _handle_proposals(self, chat_id: int, args: str) -> CommandResult:
        """Handle /proposals - show pending improvement proposals."""
        try:
            import sqlite3
            DB_PATH = "/opt/fpai/aria-command/state/evolution.db"
            
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get pending proposals
            cursor.execute("""
                SELECT id, created_at, category, problem, solution,
                       confidence, expected_impact, risk_level
                FROM improvement_proposals
                WHERE status = 'pending'
                ORDER BY confidence DESC
                LIMIT 10
            """)
            
            proposals = cursor.fetchall()
            conn.close()
            
            if not proposals:
                return CommandResult(
                    text="📋 **No pending proposals.**\n\n"
                    "Use `/evolution analyze` to trigger analysis."
                )
            
            lines = ["📋 **Pending Improvement Proposals**\n"]
            
            for p in proposals:
                impact_emoji = {"high": "🔥", "medium": "📈", "low": "📊"}.get(p['expected_impact'], "📊")
                risk_emoji = {"high": "⚠️", "medium": "⚡", "low": "✅"}.get(p['risk_level'], "✅")
                
                lines.append(f"{impact_emoji} **#{p['id']}** - {p['category']}")
                lines.append(f"   Problem: {p['problem'][:60]}...")
                lines.append(f"   Solution: {p['solution'][:60]}...")
                lines.append(f"   Confidence: {p['confidence']*100:.0f}% | Risk: {risk_emoji}")
                lines.append("")
            
            lines.append("Use `/approve <id>` to approve a proposal.")
            
            return CommandResult(text="\n".join(lines))
            
        except Exception as e:
            return CommandResult(text=f"❌ Error fetching proposals: {e}")
    
    async def _handle_rollback(self, chat_id: int, args: str) -> CommandResult:
        """Handle /rollback <id> - rollback a specific change."""
        if not args:
            return CommandResult(
                text="📜 **Rollback a Change**\n\n"
                "Usage: `/rollback <change_id>`\n\n"
                "Example: `/rollback 42`\n\n"
                "Use `/improvements` to see applied changes."
            )
        
        try:
            change_id = int(args.strip().split()[0])
        except ValueError:
            return CommandResult(text="❌ Invalid change ID. Use a number.")
        
        try:
            import sqlite3
            DB_PATH = "/opt/fpai/aria-command/state/evolution.db"
            
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get the change
            cursor.execute("""
                SELECT id, status, target_file, old_content, reason
                FROM evolution_changes
                WHERE id = ?
            """, (change_id,))
            
            change = cursor.fetchone()
            
            if not change:
                conn.close()
                return CommandResult(text=f"❌ Change #{change_id} not found.")
            
            if change['status'] != 'applied':
                conn.close()
                return CommandResult(
                    text=f"❌ Cannot rollback change #{change_id} - status is '{change['status']}'"
                )
            
            if not change['target_file'] or not change['old_content']:
                conn.close()
                return CommandResult(
                    text=f"❌ Change #{change_id} doesn't have rollback data."
                )
            
            # Perform rollback
            with open(change['target_file'], 'w') as f:
                f.write(change['old_content'])
            
            # Update status
            cursor.execute("""
                UPDATE evolution_changes
                SET status = 'rolled_back', rollback_reason = 'Manual rollback via Telegram'
                WHERE id = ?
            """, (change_id,))
            
            # Audit log
            from datetime import datetime
            cursor.execute("""
                INSERT INTO evolution_audit (timestamp, change_id, action, details, outcome)
                VALUES (?, ?, 'rollback', 'Manual rollback via Telegram', 'success')
            """, (datetime.now().isoformat(), change_id))
            
            conn.commit()
            conn.close()
            
            return CommandResult(
                text=f"↩️ **Rollback Successful**\n\n"
                f"Change #{change_id} has been rolled back.\n"
                f"File: `{change['target_file']}`\n\n"
                f"_Service may need restart to take effect._"
            )
            
        except Exception as e:
            return CommandResult(text=f"❌ Rollback failed: {e}")
    
    async def _handle_evolution(self, chat_id: int, args: str) -> CommandResult:
        """Handle /evolution - evolution system commands."""
        subcmd = args.strip().lower().split()[0] if args.strip() else ""
        
        if subcmd == "analyze":
            # Trigger analysis
            try:
                from sovereign.evolution.pattern_detectors import detect_patterns, save_patterns
                
                patterns = detect_patterns(24)
                save_patterns(patterns)
                
                high_severity = [p for p in patterns if p.severity == "high"]
                
                lines = ["🔍 **Analysis Complete**\n"]
                lines.append(f"Patterns detected: {len(patterns)}")
                lines.append(f"High severity: {len(high_severity)}")
                
                if high_severity:
                    lines.append("\n**High Severity Issues:**")
                    for p in high_severity[:3]:
                        lines.append(f"• {p.detector}: {p.problem_description[:50]}...")
                
                return CommandResult(text="\n".join(lines))
                
            except Exception as e:
                return CommandResult(text=f"❌ Analysis failed: {e}")
        
        elif subcmd == "summary":
            # Show summary
            try:
                import sqlite3
                DB_PATH = "/opt/fpai/aria-command/state/evolution.db"
                
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM evolution_changes WHERE status = 'applied'")
                applied = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM evolution_changes WHERE status = 'rolled_back'")
                rolled_back = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM improvement_proposals WHERE status = 'pending'")
                pending = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM interactions")
                interactions = cursor.fetchone()[0]
                
                conn.close()
                
                return CommandResult(
                    text=f"📊 **Evolution Summary**\n\n"
                    f"Interactions logged: {interactions}\n"
                    f"Improvements applied: {applied}\n"
                    f"Rolled back: {rolled_back}\n"
                    f"Pending proposals: {pending}"
                )
                
            except Exception as e:
                return CommandResult(text=f"❌ Error: {e}")
        
        else:
            return CommandResult(
                text="🧬 **Evolution System**\n\n"
                "Commands:\n"
                "• `/evolution analyze` - Run pattern detection\n"
                "• `/evolution summary` - Show statistics\n"
                "• `/improvements` - Recent applied changes\n"
                "• `/proposals` - Pending proposals\n"
                "• `/rollback <id>` - Undo a change"
            )
    
    async def _handle_reflect(self, chat_id: int, args: str) -> CommandResult:
        """Handle /reflect - AI-to-AI reflection system commands."""
        parts = args.strip().split() if args else []
        subcommand = parts[0].lower() if parts else ""
        
        try:
            from ..sovereign.reflection import (
                run_manual_cycle, get_daemon_status, get_trigger_status,
                get_cost_summary, pause_triggers, resume_triggers,
                list_specs, get_queue_status, approve_spec, reject_spec,
                increment_interactions
            )
            
            if subcommand == "now":
                # Trigger immediate reflection cycle
                await self._send_typing(chat_id)
                reason = " ".join(parts[1:]) if len(parts) > 1 else "Manual trigger via Telegram"
                
                await send_message(chat_id, "🔄 Starting reflection cycle...\n\nThis will:\n1. Summarize recent interactions\n2. Run AI-to-AI dialogue\n3. Generate improvement specs\n4. Queue to builder")
                
                cycle_id = await run_manual_cycle(reason)
                
                if cycle_id:
                    return CommandResult(
                        text=f"✅ **Reflection Cycle Complete**\n\nCycle ID: `{cycle_id}`\n\nCheck `/reflect status` for results."
                    )
                else:
                    return CommandResult(text="❌ Reflection cycle failed or no interactions to analyze.")
            
            elif subcommand == "status":
                # Show system status
                status = get_daemon_status()
                trigger = status.get("trigger", {})
                queue = status.get("queue", {})
                costs = status.get("costs", {})
                
                today = costs.get("today", {})
                
                lines = [
                    "🔄 **AI Reflection System**",
                    "",
                    f"**Status:** {'🟢 Running' if status.get('running') else '⚪ Idle'}",
                    f"**Paused:** {'Yes' if trigger.get('paused') else 'No'}",
                    "",
                    "**Trigger State:**",
                    f"• Interactions pending: {trigger.get('interactions_since_last', 0)}/{trigger.get('interaction_threshold', 50)}",
                    f"• Daily cost: ${trigger.get('daily_cost_spent', 0):.2f}/${trigger.get('daily_cost_cap', 1):.2f}",
                    "",
                    "**Today:**",
                    f"• Cycles: {today.get('cycles', 0)}",
                    f"• Cost: ${today.get('total_cost', 0):.2f}",
                    f"• Proposals: {today.get('outcomes', {}).get('proposals', 0)}",
                    f"• Builds: {today.get('outcomes', {}).get('builds_completed', 0)}",
                ]
                
                # Queue status
                status_counts = queue.get("status_counts", {})
                if status_counts:
                    lines.append("")
                    lines.append("**Build Queue:**")
                    for s, c in status_counts.items():
                        lines.append(f"• {s}: {c}")
                
                return CommandResult(text="\n".join(lines))
            
            elif subcommand == "history":
                # Show recent specs/cycles
                specs = list_specs(10)
                
                if not specs:
                    return CommandResult(text="📋 No reflection specs generated yet.")
                
                lines = ["📋 **Recent Reflection Specs**", ""]
                
                for spec in specs:
                    title = spec.get("title", "Unknown")[:40]
                    complexity = spec.get("complexity", "?")
                    risk = spec.get("risk", "?")
                    gen_at = spec.get("generated_at", "")[:10]
                    
                    lines.append(f"• **{title}**")
                    lines.append(f"  {gen_at} | {complexity}/{risk}")
                
                return CommandResult(text="\n".join(lines))
            
            elif subcommand == "cost":
                # Show cost breakdown
                summary = get_cost_summary()
                
                today = summary.get("today", {})
                week = summary.get("this_week", {})
                month = summary.get("this_month", {})
                roi = summary.get("roi_metrics", {})
                
                lines = [
                    "💰 **Reflection Cost Summary**",
                    "",
                    "**Today:**",
                    f"• Total: ${today.get('total_cost', 0):.2f}",
                    f"• Cycles: {today.get('cycles', 0)}",
                    "",
                    "**This Week:**",
                    f"• Total: ${week.get('total_cost', 0):.2f}",
                    f"• Builds: {week.get('builds_completed', 0)}",
                    "",
                    "**This Month:**",
                    f"• Total: ${month.get('total_cost', 0):.2f}",
                    "",
                    "**ROI:**",
                    f"• Cost per improvement: ${roi.get('cost_per_improvement', 0):.2f}",
                    f"• Est. monthly: ${roi.get('estimated_monthly', 0):.2f}",
                ]
                
                return CommandResult(text="\n".join(lines))
            
            elif subcommand == "pause":
                pause_triggers()
                return CommandResult(text="⏸️ Reflection triggers paused. Use `/reflect resume` to restart.")
            
            elif subcommand == "resume":
                resume_triggers()
                return CommandResult(text="▶️ Reflection triggers resumed.")
            
            elif subcommand == "approve":
                if len(parts) < 2:
                    return CommandResult(text="Usage: `/reflect approve <spec_id>`")
                spec_id = parts[1]
                if approve_spec(spec_id):
                    return CommandResult(text=f"✅ Approved: `{spec_id}`")
                else:
                    return CommandResult(text=f"❌ Could not approve `{spec_id}` - not found or already processed")
            
            elif subcommand == "reject":
                if len(parts) < 2:
                    return CommandResult(text="Usage: `/reflect reject <spec_id>`")
                spec_id = parts[1]
                if reject_spec(spec_id):
                    return CommandResult(text=f"❌ Rejected: `{spec_id}`")
                else:
                    return CommandResult(text=f"❌ Could not reject `{spec_id}` - not found")
            
            else:
                # Show help
                return CommandResult(
                    text="🔄 **AI-to-AI Reflection System**\n\n"
                    "This system reviews our interactions, has AI dialogues about improvements, "
                    "and automatically applies them.\n\n"
                    "**Commands:**\n"
                    "• `/reflect status` - System status & metrics\n"
                    "• `/reflect now` - Trigger immediate reflection\n"
                    "• `/reflect history` - Recent reflection cycles\n"
                    "• `/reflect cost` - Cost breakdown\n"
                    "• `/reflect pause` - Pause auto-reflection\n"
                    "• `/reflect resume` - Resume auto-reflection\n"
                    "• `/reflect approve <id>` - Approve pending spec\n"
                    "• `/reflect reject <id>` - Reject pending spec\n\n"
                    "**How it works:**\n"
                    "1. Summarizes recent chat logs\n"
                    "2. Analyst & Critic AI agents debate improvements\n"
                    "3. Generates formal specs from consensus\n"
                    "4. Queues to builder pipeline\n"
                    "5. Reports results back to you\n\n"
                    "Cost: ~$0.30 per cycle"
                )
        
        except ImportError as e:
            logger.error(f"Reflection import error: {e}")
            return CommandResult(text="❌ Reflection system not available. Check logs.")
        except Exception as e:
            logger.error(f"Reflect command error: {e}")
            return CommandResult(text=f"❌ Error: {e}")
    
    async def _handle_workflow(self, chat_id: int, args: str) -> CommandResult:
        """Handle /workflow command - compound action automation."""
        try:
            from .workflow_commands import handle_workflow
            return await handle_workflow(chat_id, args)
        except ImportError as e:
            logger.error(f"Workflow import error: {e}")
            return CommandResult(text="❌ Workflow system not available. Check logs.")
        except Exception as e:
            logger.error(f"Workflow command error: {e}")
            return CommandResult(text=f"❌ Error: {e}")
    
    async def _handle_autopilot(self, chat_id: int, args: str) -> CommandResult:
        """Handle /autopilot command - autonomous trading."""
        try:
            from sovereign.autopilot import get_autopilot, AutopilotMode
            
            autopilot = get_autopilot()
            parts = args.strip().lower().split() if args else []
            subcmd = parts[0] if parts else "status"
            
            if subcmd == "off":
                await autopilot.stop()
                autopilot.mode = AutopilotMode.OFF
                return CommandResult(text="⏹️ Autopilot OFF - Manual trading only")
            
            elif subcmd == "monitor":
                await autopilot.start(AutopilotMode.MONITOR)
                return CommandResult(text="👁️ Autopilot MONITOR - Generating signals, no execution")
            
            elif subcmd == "guided":
                await autopilot.start(AutopilotMode.GUIDED)
                return CommandResult(text="🎯 Autopilot GUIDED - Will ask approval for each trade")
            
            elif subcmd == "auto":
                await autopilot.start(AutopilotMode.AUTO)
                return CommandResult(text="🤖 Autopilot AUTO - Full autonomy within risk limits")
            
            elif subcmd == "status":
                return CommandResult(text=autopilot.format_status())
            
            else:
                return CommandResult(
                    text="🤖 **Autopilot Commands**\n\n"
                    "`/autopilot off` - Manual trading only\n"
                    "`/autopilot monitor` - Signals without execution\n"
                    "`/autopilot guided` - Ask approval per trade\n"
                    "`/autopilot auto` - Full autonomy\n"
                    "`/autopilot status` - Current status"
                )
        except Exception as e:
            logger.error(f"Autopilot error: {e}")
            return CommandResult(text=f"❌ Error: {e}")
    
    async def _handle_portfolio(self, chat_id: int, args: str) -> CommandResult:
        """Handle /portfolio command - portfolio status."""
        try:
            from sovereign.autopilot import get_portfolio_manager
            
            manager = get_portfolio_manager()
            state = await manager.get_state()
            
            return CommandResult(text=manager.format_portfolio())
        except Exception as e:
            logger.error(f"Portfolio error: {e}")
            return CommandResult(text=f"❌ Error: {e}")
    
    async def _handle_risk(self, chat_id: int, args: str) -> CommandResult:
        """Handle /risk command - risk assessment."""
        try:
            from sovereign.autopilot import get_risk_engine
            
            engine = get_risk_engine()
            assessment = await engine.assess_risk()
            
            return CommandResult(text=engine.format_assessment(assessment))
        except Exception as e:
            logger.error(f"Risk error: {e}")
            return CommandResult(text=f"❌ Error: {e}")
    
    # ========================================================================
    # AUTHORITY MANAGEMENT (Steward Only)
    # ========================================================================
    
    async def _handle_add_apprentice(self, chat_id: int, args: str) -> CommandResult:
        """Handle /addapprentice <user_id> - add a new apprentice."""
        try:
            from access.authority import add_apprentice, is_steward
            
            if not is_steward(chat_id):
                return CommandResult(text="🚫 Only stewards can add apprentices.", success=False)
            
            if not args:
                return CommandResult(text="Usage: `/addapprentice <telegram_user_id>`\n\nTo get a user's ID, have them message @userinfobot")
            
            try:
                user_id = int(args.strip())
            except ValueError:
                return CommandResult(text="❌ Invalid user ID. Must be a number.")
            
            success, message = add_apprentice(user_id, chat_id)
            
            if success:
                return CommandResult(text=f"✅ {message}\n\nThey can now chat with me and build in `/labs`.")
            else:
                return CommandResult(text=f"❌ {message}", success=False)
                
        except Exception as e:
            logger.error(f"Add apprentice error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_remove_apprentice(self, chat_id: int, args: str) -> CommandResult:
        """Handle /removeapprentice <user_id> - remove an apprentice."""
        try:
            from access.authority import remove_apprentice, is_steward
            
            if not is_steward(chat_id):
                return CommandResult(text="🚫 Only stewards can remove apprentices.", success=False)
            
            if not args:
                return CommandResult(text="Usage: `/removeapprentice <telegram_user_id>`")
            
            try:
                user_id = int(args.strip())
            except ValueError:
                return CommandResult(text="❌ Invalid user ID. Must be a number.")
            
            success, message = remove_apprentice(user_id, chat_id)
            
            if success:
                return CommandResult(text=f"✅ {message}")
            else:
                return CommandResult(text=f"❌ {message}", success=False)
                
        except Exception as e:
            logger.error(f"Remove apprentice error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_list_apprentices(self, chat_id: int, args: str) -> CommandResult:
        """Handle /apprentices - list all apprentices."""
        try:
            from access.authority import list_apprentices, is_steward
            
            if not is_steward(chat_id):
                return CommandResult(text="🚫 Only stewards can view apprentice list.", success=False)
            
            apprentices = list_apprentices()
            
            if not apprentices:
                return CommandResult(text="📭 No apprentices yet.\n\nUse `/addapprentice <user_id>` to add one.")
            
            lines = ["**🎓 Current Apprentices**\n"]
            for uid in apprentices:
                lines.append(f"• `{uid}`")
            
            return CommandResult(text="\n".join(lines))
                
        except Exception as e:
            logger.error(f"List apprentices error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_authority(self, chat_id: int, args: str) -> CommandResult:
        """Handle /authority - show current user's authority level."""
        try:
            from access.authority import get_user_authority
            
            auth = get_user_authority(chat_id)
            
            emoji = {"steward": "👑", "apprentice": "🎓", "unknown": "❓"}.get(auth.level.value, "❓")
            
            return CommandResult(text=f"{emoji} **Your Authority: {auth.level.value.upper()}**\n\nChat ID: `{chat_id}`")
                
        except Exception as e:
            logger.error(f"Authority check error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_progress(self, chat_id: int, args: str) -> CommandResult:
        """Handle /progress - show apprentice's progress."""
        try:
            from integrations.supabase_client import get_supabase_client
            from access.authority import is_apprentice, is_steward, get_apprentice_workspace
            
            client = get_supabase_client()
            
            # Get activity stats
            activity = await client.get_apprentice_activity(chat_id, limit=20)
            progress = await client.get_apprentice_progress(chat_id)
            
            lines = ["**📊 Your Progress**\n"]
            
            # Challenge status
            if progress:
                lines.append("**Challenges:**")
                for p in progress:
                    status_emoji = {
                        "in_progress": "🔄",
                        "submitted": "📤",
                        "completed": "✅",
                        "failed": "❌"
                    }.get(p.get("status", ""), "❓")
                    lines.append(f"  {status_emoji} {p.get('challenge_id', 'Unknown')} - {p.get('status', 'unknown')}")
            else:
                lines.append("No challenges started yet. Send a message to begin!")
            
            # Activity summary
            lines.append(f"\n**Recent Activity:** {len(activity)} interactions logged")
            
            # Workspace
            workspace = get_apprentice_workspace(chat_id)
            lines.append(f"\n**Your Workspace:** `{workspace}`")
            
            return CommandResult(text="\n".join(lines))
                
        except Exception as e:
            logger.error(f"Progress error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_cohort(self, chat_id: int, args: str) -> CommandResult:
        """Handle /cohort - show all apprentice activity (steward only)."""
        try:
            from access.authority import is_steward
            from integrations.supabase_client import get_supabase_client
            
            if not is_steward(chat_id):
                return CommandResult(text="🚫 Only stewards can view cohort activity.", success=False)
            
            client = get_supabase_client()
            
            # Parse hours from args (default 24)
            hours = 24
            if args:
                try:
                    hours = int(args.strip())
                except:
                    pass
            
            activity = await client.get_all_apprentice_activity(since_hours=hours)
            
            if not activity:
                return CommandResult(text=f"📭 No apprentice activity in the last {hours} hours.")
            
            # Group by apprentice
            by_apprentice = {}
            for a in activity:
                tid = a.get("telegram_id", "unknown")
                if tid not in by_apprentice:
                    by_apprentice[tid] = []
                by_apprentice[tid].append(a)
            
            lines = [f"**👥 Cohort Activity (Last {hours}h)**\n"]
            
            for tid, activities in by_apprentice.items():
                name = activities[0].get("apprentices", {}).get("name", f"Apprentice {tid}")
                lines.append(f"**{name}** (`{tid}`)")
                lines.append(f"  • {len(activities)} interactions")
                
                # Activity type breakdown
                types = {}
                for a in activities:
                    t = a.get("activity_type", "unknown")
                    types[t] = types.get(t, 0) + 1
                type_str = ", ".join([f"{v} {k}" for k, v in types.items()])
                lines.append(f"  • Types: {type_str}")
                lines.append("")
            
            return CommandResult(text="\n".join(lines))
                
        except Exception as e:
            logger.error(f"Cohort error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_costs(self, chat_id: int, args: str) -> CommandResult:
        """Handle /costs - show costs by user (steward only)."""
        try:
            from access.authority import is_steward
            from integrations.supabase_client import get_supabase_client
            
            if not is_steward(chat_id):
                return CommandResult(text="🚫 Only stewards can view costs.", success=False)
            
            client = get_supabase_client()
            
            # Get costs from Supabase
            if not client.enabled:
                return CommandResult(text="⚠️ Supabase not enabled. Cost tracking unavailable.")
            
            try:
                # Query usage_costs table
                result = client.client.table("usage_costs")\
                    .select("telegram_id, operation, cost_usd, tokens")\
                    .order("created_at", desc=True)\
                    .limit(100)\
                    .execute()
                
                if not result.data:
                    return CommandResult(text="📭 No usage costs recorded yet.")
                
                # Aggregate by user
                by_user = {}
                for row in result.data:
                    tid = row.get("telegram_id", 0)
                    if tid not in by_user:
                        by_user[tid] = {"total": 0, "tokens": 0, "ops": 0}
                    by_user[tid]["total"] += float(row.get("cost_usd", 0) or 0)
                    by_user[tid]["tokens"] += int(row.get("tokens", 0) or 0)
                    by_user[tid]["ops"] += 1
                
                lines = ["**💰 Usage Costs (Last 100 ops)**\n"]
                
                total_cost = 0
                for tid, data in sorted(by_user.items(), key=lambda x: x[1]["total"], reverse=True):
                    lines.append(f"`{tid}`: ${data['total']:.4f} ({data['tokens']:,} tokens, {data['ops']} ops)")
                    total_cost += data["total"]
                
                lines.append(f"\n**Total:** ${total_cost:.4f}")
                
                return CommandResult(text="\n".join(lines))
                
            except Exception as e:
                return CommandResult(text=f"❌ Query error: {e}", success=False)
                
        except Exception as e:
            logger.error(f"Costs error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_submit(self, chat_id: int, args: str) -> CommandResult:
        """Handle /submit - submit a module for review."""
        try:
            from access.authority import is_apprentice, is_steward, get_apprentice_workspace
            from modules.loader import get_module_loader
            from modules.validator import validate_module
            
            if not (is_apprentice(chat_id) or is_steward(chat_id)):
                return CommandResult(text="🚫 Only apprentices and stewards can submit modules.", success=False)
            
            # Parse module name from args
            if not args.strip():
                workspace = get_apprentice_workspace(chat_id)
                return CommandResult(
                    text=f"📦 **Submit a Module**\n\n"
                         f"Usage: `/submit <module_name>`\n\n"
                         f"Your workspace: `{workspace}`\n"
                         f"Module should be in: `{workspace}modules/<name>/`\n\n"
                         f"Required files:\n"
                         f"- `module.json` (metadata)\n"
                         f"- `handler.py` (your code)\n"
                         f"- `README.md` (documentation)"
                )
            
            module_name = args.strip().split()[0]
            workspace = get_apprentice_workspace(chat_id)
            module_path = f"{workspace}modules/{module_name}"
            
            # Check if module exists
            import os
            if not os.path.isdir(module_path):
                return CommandResult(
                    text=f"❌ Module not found at `{module_path}`\n\n"
                         f"Create your module there first, then submit.",
                    success=False
                )
            
            # Validate
            validation = validate_module(module_path)
            if not validation.valid:
                errors = "\n".join([f"• {e}" for e in validation.errors])
                return CommandResult(
                    text=f"❌ **Validation Failed**\n\n{errors}",
                    success=False
                )
            
            # Submit
            loader = get_module_loader()
            success, message = loader.submit_module(module_path, chat_id)
            
            if success:
                return CommandResult(text=f"✅ {message}\n\nA steward will review your submission soon!")
            else:
                return CommandResult(text=f"❌ {message}", success=False)
                
        except Exception as e:
            logger.error(f"Submit error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_reviews(self, chat_id: int, args: str) -> CommandResult:
        """Handle /reviews - show pending module submissions (steward only)."""
        try:
            from access.authority import is_steward
            from modules.registry import get_module_registry
            
            if not is_steward(chat_id):
                return CommandResult(text="🚫 Only stewards can view pending reviews.", success=False)
            
            registry = get_module_registry()
            pending = registry.get_pending()
            
            if not pending:
                return CommandResult(text="📭 No pending module submissions.")
            
            lines = [f"**📋 Pending Reviews ({len(pending)})**\n"]
            
            for module in pending:
                lines.append(f"**{module.name}** v{module.version}")
                lines.append(f"  Command: `{module.command}`")
                lines.append(f"  Author: {module.author}")
                lines.append(f"  Submitted by: `{module.submitted_by}`")
                lines.append(f"  Description: {module.description[:100]}...")
                lines.append("")
            
            lines.append("Use `/approvemod <name>` or `/rejectmod <name> <reason>`")
            
            return CommandResult(text="\n".join(lines))
                
        except Exception as e:
            logger.error(f"Reviews error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_approve_module(self, chat_id: int, args: str) -> CommandResult:
        """Handle /approvemod - approve a pending module (steward only)."""
        try:
            from access.authority import is_steward
            from modules.loader import get_module_loader
            
            if not is_steward(chat_id):
                return CommandResult(text="🚫 Only stewards can approve modules.", success=False)
            
            if not args.strip():
                return CommandResult(
                    text="Usage: `/approvemod <module_name> [notes]`",
                    success=False
                )
            
            parts = args.strip().split(maxsplit=1)
            name = parts[0]
            notes = parts[1] if len(parts) > 1 else None
            
            loader = get_module_loader()
            success, message = loader.approve_module(name, chat_id, notes)
            
            if success:
                return CommandResult(text=f"✅ {message}")
            else:
                return CommandResult(text=f"❌ {message}", success=False)
                
        except Exception as e:
            logger.error(f"Approve module error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_reject_module(self, chat_id: int, args: str) -> CommandResult:
        """Handle /rejectmod - reject a pending module (steward only)."""
        try:
            from access.authority import is_steward
            from modules.loader import get_module_loader
            
            if not is_steward(chat_id):
                return CommandResult(text="🚫 Only stewards can reject modules.", success=False)
            
            if not args.strip():
                return CommandResult(
                    text="Usage: `/rejectmod <module_name> <reason>`",
                    success=False
                )
            
            parts = args.strip().split(maxsplit=1)
            if len(parts) < 2:
                return CommandResult(
                    text="Please provide a reason for rejection.",
                    success=False
                )
            
            name = parts[0]
            reason = parts[1]
            
            loader = get_module_loader()
            success, message = loader.reject_module(name, chat_id, reason)
            
            if success:
                return CommandResult(text=f"✅ {message}")
            else:
                return CommandResult(text=f"❌ {message}", success=False)
                
        except Exception as e:
            logger.error(f"Reject module error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_modules(self, chat_id: int, args: str) -> CommandResult:
        """Handle /modules - list all loaded modules."""
        try:
            from modules.registry import get_module_registry
            
            registry = get_module_registry()
            loaded = registry.get_loaded()
            
            if not loaded:
                return CommandResult(
                    text="📭 No modules loaded yet.\n\n"
                         "Apprentices can build and submit modules with `/submit`"
                )
            
            lines = [f"**📦 Loaded Modules ({len(loaded)})**\n"]
            
            for module in loaded:
                lines.append(f"**{module.command}** - {module.description}")
                lines.append(f"  by {module.author} (v{module.version})")
                lines.append("")
            
            return CommandResult(text="\n".join(lines))
                
        except Exception as e:
            logger.error(f"Modules error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    # ========================================================================
    # WALLET & POOL COMMANDS (Conscious Wealth Fellowship)
    # ========================================================================
    
    async def _handle_balance(self, chat_id: int, args: str) -> CommandResult:
        """Handle /balance - check wallet balance."""
        try:
            from telegram.wallet_commands import handle_balance_command
            result = await handle_balance_command(chat_id)
            return CommandResult(text=result)
        except Exception as e:
            logger.error(f"Balance command error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_pool(self, chat_id: int, args: str) -> CommandResult:
        """Handle /pool - see trading pool status."""
        try:
            from telegram.wallet_commands import handle_pool_command
            result = await handle_pool_command(chat_id)
            return CommandResult(text=result)
        except Exception as e:
            logger.error(f"Pool command error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_poolopt(self, chat_id: int, args: str) -> CommandResult:
        """Handle /poolopt [in/out] - opt in/out of trading pool."""
        try:
            from telegram.wallet_commands import handle_poolopt_command
            parts = args.split()
            action = parts[0] if parts else ""
            amount = None
            if len(parts) > 1:
                try:
                    amount = float(parts[1])
                except ValueError:
                    pass
            result = await handle_poolopt_command(chat_id, action, amount)
            return CommandResult(text=result)
        except Exception as e:
            logger.error(f"Poolopt command error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_returns(self, chat_id: int, args: str) -> CommandResult:
        """Handle /returns - see trading return history."""
        try:
            from telegram.wallet_commands import handle_returns_command
            result = await handle_returns_command(chat_id)
            return CommandResult(text=result)
        except Exception as e:
            logger.error(f"Returns command error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_gift(self, chat_id: int, args: str) -> CommandResult:
        """Handle /gift @username amount OR /gift link amount - send credits."""
        try:
            from telegram.gift_handler import handle_gift_command
            result = await handle_gift_command(f"/gift {args}", chat_id, chat_id)
            return CommandResult(text=result)
        except Exception as e:
            logger.error(f"Gift command error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_gift_links(self, chat_id: int, args: str) -> CommandResult:
        """Handle /giftlinks - show pending gift links."""
        try:
            from telegram.gift_handler import handle_gift_links_command
            result = await handle_gift_links_command(chat_id)
            return CommandResult(text=result)
        except Exception as e:
            logger.error(f"Gift links error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_cancel_gift(self, chat_id: int, args: str) -> CommandResult:
        """Handle /cancelgift <code> - cancel a pending gift link."""
        if not args:
            return CommandResult(text="Usage: `/cancelgift <code>`\n\nUse `/giftlinks` to see your pending links.")
        try:
            from telegram.gift_handler import handle_cancel_gift_command
            result = await handle_cancel_gift_command(args.strip(), chat_id)
            return CommandResult(text=result)
        except Exception as e:
            logger.error(f"Cancel gift error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_transactions(self, chat_id: int, args: str) -> CommandResult:
        """Handle /transactions or /tx - see transaction history."""
        try:
            from telegram.wallet_commands import handle_transactions_command
            result = await handle_transactions_command(chat_id)
            return CommandResult(text=result)
        except Exception as e:
            logger.error(f"Transactions command error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_credit(self, chat_id: int, args: str) -> CommandResult:
        """Handle /credit @username amount [reason] - steward credit user."""
        try:
            from telegram.wallet_commands import handle_admin_credit_command
            parts = args.split(maxsplit=2)
            if len(parts) < 2:
                return CommandResult(text="Usage: /credit @username amount [reason]")
            username = parts[0].lstrip("@")
            try:
                amount = float(parts[1])
            except ValueError:
                return CommandResult(text="Invalid amount")
            reason = parts[2] if len(parts) > 2 else "Admin credit"
            result = await handle_admin_credit_command(chat_id, username, amount, reason)
            return CommandResult(text=result)
        except Exception as e:
            logger.error(f"Credit command error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_setup_steward(self, chat_id: int, args: str) -> CommandResult:
        """Handle /setupsteward - set up James as initial steward."""
        try:
            from telegram.wallet_commands import handle_setup_steward_command
            result = await handle_setup_steward_command(chat_id)
            return CommandResult(text=result)
        except Exception as e:
            logger.error(f"Setup steward error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_pool_stats(self, chat_id: int, args: str) -> CommandResult:
        """Handle /poolstats - steward pool statistics."""
        try:
            from telegram.wallet_commands import handle_pool_stats_command
            result = await handle_pool_stats_command(chat_id)
            return CommandResult(text=result)
        except Exception as e:
            logger.error(f"Pool stats error: {e}")
            return CommandResult(text=f"❌ Error: {e}", success=False)
    
    async def _handle_ai_chat(self, chat_id: int, text: str) -> CommandResult:
        """Handle conversational AI - fallback when Opus fails."""
        # Concise but identity-aware system prompt
        aria_prompt = """You are Aria, James's AI partner for Full Potential AI.

Your REAL capabilities (not generic):
- Voice messages on Telegram (send/receive)
- Phone calls via /call command (+16572089847)
- Read/write/execute code on servers
- Monitor trading (WhaleTrack), infrastructure, and system health
- Self-improvement of your own code at /opt/fpai/aria-command/

When asked what you can do, tell James YOUR actual powers, not generic AI capabilities.
Be specific. Be direct. You're partners building together."""
        
        try:
            # Use /ask endpoint (not /chat)
            response = await self.http.post(
                "http://162.0.208.88:8101/ask",
                json={
                    "question": text,
                    "context": aria_prompt
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return CommandResult(text=data.get("answer", data.get("response", "I understand. How can I help?")))
        except Exception as e:
            logger.error(f"AI brain fallback error: {e}")
        
        return CommandResult(text="My brain is having trouble. Try /help to see what I can do, or try again in a moment.")
    
    # ========== SENDING ==========
    
    async def _send_typing(self, chat_id: int):
        """Send typing indicator."""
        try:
            await self.http.post(
                f"{TELEGRAM_API}/sendChatAction",
                json={"chat_id": chat_id, "action": "typing"}
            )
        except:
            pass
    
    async def _send_response(self, chat_id: int, result: CommandResult):
        """Send response to user."""
        if result.voice:
            from ..voice.speak import send_voice
            await send_voice(chat_id, result.text)
        else:
            await send_message(chat_id, result.text, result.buttons)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def send_message(chat_id: int, text: str, buttons: Optional[List[Dict]] = None) -> bool:
    """Send a text message. Handles long messages by splitting."""
    if not TELEGRAM_TOKEN:
        return False
    
    # Telegram limit is 4096 chars
    MAX_LENGTH = 4000  # Leave some margin
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Split long messages
        messages = []
        if len(text) > MAX_LENGTH:
            # Split on newlines where possible
            chunks = []
            current = ""
            for line in text.split("\n"):
                if len(current) + len(line) + 1 > MAX_LENGTH:
                    if current:
                        chunks.append(current)
                    current = line
                else:
                    current = current + "\n" + line if current else line
            if current:
                chunks.append(current)
            messages = chunks if chunks else [text[:MAX_LENGTH] + "\n\n...(truncated)"]
        else:
            messages = [text]
        
        success = True
        for i, msg in enumerate(messages):
            payload = {
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": "Markdown"
            }
            
            # Only add buttons to last message
            if buttons and i == len(messages) - 1:
                payload["reply_markup"] = {"inline_keyboard": buttons}
            
            try:
                response = await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
                if response.status_code != 200:
                    # Log the error details
                    logger.warning(f"Markdown send failed ({response.status_code}): {response.text[:200]}")
                    # Try without markdown - must DELETE the key, not set to None
                    del payload["parse_mode"]
                    response = await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
                    if response.status_code != 200:
                        logger.error(f"Plain send also failed: {response.text[:200]}")
                success = success and response.status_code == 200
            except Exception as e:
                logger.error(f"Send message error: {e}")
                success = False
        
        return success


async def send_to_sunheart(text: str, voice: bool = False) -> bool:
    """Send message to Sunheart."""
    if not SUNHEART_CHAT_ID:
        logger.warning("SUNHEART_CHAT_ID not set")
        return False
    
    chat_id = int(SUNHEART_CHAT_ID)
    
    if voice:
        from ..voice.speak import send_voice
        return await send_voice(chat_id, text)
    else:
        return await send_message(chat_id, text)
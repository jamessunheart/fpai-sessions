#!/usr/bin/env python3
"""
ARIA TELEGRAM BUILDER INTERFACE
===============================

Extends Telegram with builder capabilities:
- Inline keyboard buttons for approval
- Callback handlers for approve/deny
- Builder command handlers
"""

import os
import json
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass
import httpx

logger = logging.getLogger("aria.telegram_builder")

# ============================================================================
# CONFIGURATION
# ============================================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


@dataclass
class InlineButton:
    """A Telegram inline keyboard button."""
    text: str
    callback_data: str


class TelegramBuilder:
    """
    Telegram interface for the builder system.
    
    Handles:
    - Sending messages with inline keyboards
    - Processing callback queries (button presses)
    - Builder-specific commands
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
        
        # Import builder components
        self._engine = None
        self._modifier = None
    
    @property
    def engine(self):
        if self._engine is None:
            from builder import get_engine
            self._engine = get_engine()
        return self._engine
    
    @property
    def modifier(self):
        if self._modifier is None:
            from builder import CodeModifier
            self._modifier = CodeModifier()
        return self._modifier
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    async def send_message(
        self,
        chat_id: int,
        text: str,
        buttons: Optional[List[List[InlineButton]]] = None,
        reply_to: Optional[int] = None,
        parse_mode: str = "Markdown"
    ) -> Dict:
        """
        Send a message with optional inline keyboard.
        
        Args:
            chat_id: Telegram chat ID
            text: Message text
            buttons: 2D list of InlineButtons (rows of buttons)
            reply_to: Message ID to reply to
            parse_mode: Markdown or HTML
        
        Returns:
            Telegram API response
        """
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        if reply_to:
            payload["reply_to_message_id"] = reply_to
        
        if buttons:
            keyboard = {
                "inline_keyboard": [
                    [{"text": btn.text, "callback_data": btn.callback_data} for btn in row]
                    for row in buttons
                ]
            }
            payload["reply_markup"] = json.dumps(keyboard)
        
        try:
            response = await self.http.post(
                f"{TELEGRAM_API}/sendMessage",
                json=payload
            )
            return response.json()
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            # Try without markdown
            try:
                payload["parse_mode"] = None
                response = await self.http.post(
                    f"{TELEGRAM_API}/sendMessage",
                    json=payload
                )
                return response.json()
            except:
                return {"ok": False, "error": str(e)}
    
    async def edit_message(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        buttons: Optional[List[List[InlineButton]]] = None
    ) -> Dict:
        """Edit an existing message."""
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        if buttons:
            keyboard = {
                "inline_keyboard": [
                    [{"text": btn.text, "callback_data": btn.callback_data} for btn in row]
                    for row in buttons
                ]
            }
            payload["reply_markup"] = json.dumps(keyboard)
        
        try:
            response = await self.http.post(
                f"{TELEGRAM_API}/editMessageText",
                json=payload
            )
            return response.json()
        except Exception as e:
            logger.error(f"Failed to edit message: {e}")
            return {"ok": False, "error": str(e)}
    
    async def answer_callback(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False
    ) -> Dict:
        """Answer a callback query (acknowledge button press)."""
        payload = {
            "callback_query_id": callback_query_id
        }
        if text:
            payload["text"] = text
            payload["show_alert"] = show_alert
        
        try:
            response = await self.http.post(
                f"{TELEGRAM_API}/answerCallbackQuery",
                json=payload
            )
            return response.json()
        except Exception as e:
            logger.error(f"Failed to answer callback: {e}")
            return {"ok": False, "error": str(e)}
    
    async def handle_callback_query(self, callback_query: Dict) -> Optional[str]:
        """
        Handle a callback query (inline button press).
        
        Args:
            callback_query: Telegram callback_query object
        
        Returns:
            Response message
        """
        query_id = callback_query.get("id")
        data = callback_query.get("data", "")
        message = callback_query.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        
        if not all([query_id, data, chat_id]):
            return None
        
        # Parse callback data
        parts = data.split(":")
        action = parts[0]
        change_id = parts[1] if len(parts) > 1 else None
        
        # Handle different actions
        if action == "approve" and change_id:
            return await self._handle_approve(query_id, chat_id, message_id, change_id)
        
        elif action == "deny" and change_id:
            return await self._handle_deny(query_id, chat_id, message_id, change_id)
        
        elif action == "detail" and change_id:
            return await self._handle_detail(query_id, chat_id, message_id, change_id)
        
        elif action == "rollback" and change_id:
            return await self._handle_rollback(query_id, chat_id, message_id, change_id)
        
        else:
            await self.answer_callback(query_id, "Unknown action")
            return None
    
    async def _handle_approve(
        self,
        query_id: str,
        chat_id: int,
        message_id: int,
        change_id: str
    ) -> str:
        """Handle approval of a change."""
        # Acknowledge immediately
        await self.answer_callback(query_id, "Applying change...")
        
        # Apply the change
        success, result_msg = self.modifier.apply_change(change_id)
        
        if success:
            # Update message to show success
            await self.edit_message(
                chat_id,
                message_id,
                f"✅ **Change Applied**\n\n{result_msg}\n\n_Change ID: {change_id}_",
                buttons=[[InlineButton("🔄 Rollback", f"rollback:{change_id}")]]
            )
            return f"Applied change {change_id}"
        else:
            # Show error
            await self.edit_message(
                chat_id,
                message_id,
                f"❌ **Failed to Apply**\n\n{result_msg}\n\n_Change ID: {change_id}_"
            )
            return f"Failed: {result_msg}"
    
    async def _handle_deny(
        self,
        query_id: str,
        chat_id: int,
        message_id: int,
        change_id: str
    ) -> str:
        """Handle denial of a change."""
        await self.answer_callback(query_id, "Change cancelled")
        
        # Cancel the change
        self.modifier.cancel_change(change_id)
        
        # Update message
        await self.edit_message(
            chat_id,
            message_id,
            f"🚫 **Change Cancelled**\n\n_Change ID: {change_id}_"
        )
        
        return f"Cancelled change {change_id}"
    
    async def _handle_detail(
        self,
        query_id: str,
        chat_id: int,
        message_id: int,
        change_id: str
    ) -> str:
        """Show detailed diff for a change."""
        await self.answer_callback(query_id)
        
        change = self.modifier.pending_changes.get(change_id)
        if not change:
            await self.send_message(chat_id, f"Change {change_id} not found")
            return None
        
        # Show full diff
        diff = change.get_diff_preview(context_lines=10)
        await self.send_message(
            chat_id,
            f"**Full Change Details**\n\n```\n{diff[:3000]}\n```"
        )
        
        return f"Showed details for {change_id}"
    
    async def _handle_rollback(
        self,
        query_id: str,
        chat_id: int,
        message_id: int,
        change_id: str
    ) -> str:
        """Handle rollback of a change."""
        await self.answer_callback(query_id, "Rolling back...")
        
        success, result_msg = self.modifier.rollback(change_id)
        
        if success:
            await self.edit_message(
                chat_id,
                message_id,
                f"⏪ **Rolled Back**\n\n{result_msg}\n\n_Change ID: {change_id}_"
            )
            return f"Rolled back {change_id}"
        else:
            await self.send_message(
                chat_id,
                f"❌ **Rollback Failed**\n\n{result_msg}"
            )
            return f"Rollback failed: {result_msg}"
    
    async def process_builder_message(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        user_id: str
    ) -> Optional[str]:
        """
        Process a message that might be a builder request.
        
        Returns response message if handled, None otherwise.
        """
        # Check if this looks like a builder request
        from builder_intents import parse_intent
        
        intent = parse_intent(text)
        
        if not intent.is_builder_request:
            return None  # Not a builder request, let normal handler deal with it
        
        # Process through builder engine
        result = await self.engine.process_request(text)
        
        if not result.get("is_builder"):
            return None
        
        # Check if we have changes to propose
        changes = result.get("changes", [])
        
        if changes and result.get("needs_approval"):
            # Send with approval buttons
            change_ids = [c["id"] for c in changes]
            primary_id = change_ids[0] if change_ids else "none"
            
            buttons = [
                [
                    InlineButton("✅ Approve", f"approve:{primary_id}"),
                    InlineButton("❌ Deny", f"deny:{primary_id}")
                ],
                [InlineButton("📋 Show Details", f"detail:{primary_id}")]
            ]
            
            await self.send_message(
                chat_id,
                result.get("message", "Builder request processed"),
                buttons=buttons,
                reply_to=message_id
            )
            
            return result.get("message")
        
        elif changes:
            # Safe change - auto-apply and report
            for change in changes:
                success, msg = self.modifier.apply_change(change["id"])
                if success:
                    await self.send_message(
                        chat_id,
                        f"✅ **Auto-applied** (safe change)\n\n{result.get('message', msg)}",
                        reply_to=message_id
                    )
                else:
                    await self.send_message(
                        chat_id,
                        f"❌ **Failed**\n\n{msg}",
                        reply_to=message_id
                    )
            
            return result.get("message")
        
        else:
            # Just informational
            await self.send_message(
                chat_id,
                result.get("message", "No changes generated"),
                reply_to=message_id
            )
            return result.get("message")
    
    async def handle_builder_command(
        self,
        chat_id: int,
        command: str,
        args: List[str]
    ) -> str:
        """Handle explicit builder commands."""
        
        if command == "/build":
            if not args:
                return await self._show_build_help(chat_id)
            
            # Join args as the request
            request = " ".join(args)
            result = await self.engine.process_request(request)
            
            if result.get("changes"):
                change_ids = [c["id"] for c in result["changes"]]
                primary_id = change_ids[0]
                
                buttons = [
                    [
                        InlineButton("✅ Approve", f"approve:{primary_id}"),
                        InlineButton("❌ Deny", f"deny:{primary_id}")
                    ]
                ]
                
                await self.send_message(
                    chat_id,
                    result.get("message", "Build proposal ready"),
                    buttons=buttons
                )
            else:
                await self.send_message(chat_id, result.get("message", "No changes"))
            
            return result.get("message", "")
        
        elif command == "/pending":
            pending = self.modifier.get_pending()
            if not pending:
                await self.send_message(chat_id, "No pending changes.")
                return "No pending changes"
            
            text = "**Pending Changes:**\n\n"
            for change in pending:
                text += f"• `{change.id}`: {change.description[:50]}...\n"
                text += f"  File: {change.file_path}, Action: {change.action}\n\n"
            
            await self.send_message(chat_id, text)
            return text
        
        elif command == "/approve":
            if not args:
                await self.send_message(chat_id, "Usage: /approve <change_id>")
                return "Need change_id"
            
            change_id = args[0]
            success, msg = self.modifier.apply_change(change_id)
            
            result = f"{'✅' if success else '❌'} {msg}"
            await self.send_message(chat_id, result)
            return result
        
        elif command == "/cancel":
            if not args:
                await self.send_message(chat_id, "Usage: /cancel <change_id>")
                return "Need change_id"
            
            change_id = args[0]
            success, msg = self.modifier.cancel_change(change_id)
            
            result = f"{'✅' if success else '❌'} {msg}"
            await self.send_message(chat_id, result)
            return result
        
        elif command == "/rollback":
            if not args:
                await self.send_message(chat_id, "Usage: /rollback <change_id>")
                return "Need change_id"
            
            change_id = args[0]
            success, msg = self.modifier.rollback(change_id)
            
            result = f"{'✅' if success else '❌'} {msg}"
            await self.send_message(chat_id, result)
            return result
        
        elif command == "/scope":
            files = ", ".join(sorted([
                "server.py", "actions.py", "smart_responses.py",
                "memory.py", "proactive.py", "voice.py", "channels.py"
            ]))
            
            await self.send_message(
                chat_id,
                f"**Builder Scope**\n\n"
                f"I can modify these Aria files:\n`{files}`\n\n"
                f"I cannot modify:\n"
                f"• Files outside /opt/fpai/aria/\n"
                f"• API keys or tokens\n"
                f"• System configuration"
            )
            return "Showed scope"
        
        return ""
    
    async def _show_build_help(self, chat_id: int) -> str:
        """Show builder help."""
        help_text = """**Aria Builder**

Build through conversation:
• "Add a /positions command that shows trading"
• "Create an endpoint for system health"
• "Change the status function to include memory"

Or use commands:
• `/build <request>` - Generate code change
• `/pending` - Show pending changes
• `/approve <id>` - Approve a change
• `/cancel <id>` - Cancel a change
• `/rollback <id>` - Undo applied change
• `/scope` - Show what I can modify

**Risk Levels:**
• READ - Auto-executed (viewing code)
• SAFE - Auto-applied (adding new code)
• MODIFY - Needs approval (changing existing)
• RISKY - Needs confirmation (restart/delete)"""
        
        await self.send_message(chat_id, help_text)
        return help_text


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_telegram_builder: Optional[TelegramBuilder] = None


def get_telegram_builder() -> TelegramBuilder:
    """Get or create the global TelegramBuilder instance."""
    global _telegram_builder
    if _telegram_builder is None:
        _telegram_builder = TelegramBuilder()
    return _telegram_builder


# ============================================================================
# INTEGRATION HELPER
# ============================================================================

async def integrate_with_webhook(update: Dict) -> Optional[str]:
    """
    Call this from your main Telegram webhook handler.
    
    Returns response if handled, None otherwise.
    """
    builder = get_telegram_builder()
    
    # Handle callback queries (button presses)
    if "callback_query" in update:
        return await builder.handle_callback_query(update["callback_query"])
    
    # Handle messages
    if "message" in update:
        message = update["message"]
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        text = message.get("text", "").strip()
        user_id = str(message.get("from", {}).get("id", "unknown"))
        
        if not text or not chat_id:
            return None
        
        # Check for builder commands
        if text.startswith("/build") or text.startswith("/pending") or \
           text.startswith("/approve") or text.startswith("/cancel") or \
           text.startswith("/rollback") or text.startswith("/scope"):
            
            parts = text.split()
            command = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            return await builder.handle_builder_command(chat_id, command, args)
        
        # Try to process as builder request
        return await builder.process_builder_message(chat_id, message_id, text, user_id)
    
    return None



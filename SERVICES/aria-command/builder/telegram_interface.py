#!/usr/bin/env python3
"""
ARIA UNIFIED BUILDER - TELEGRAM INTERFACE
==========================================

Complete Telegram integration for the unified builder:
- Inline keyboard buttons for approval/denial
- Builder commands with full capabilities
- Real-time feedback with diff previews
- Authority-based access control
"""

import os
import json
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import httpx

from .unified_engine import (
    get_unified_builder,
    build_from_request,
    UnifiedBuilder,
    FileChange,
    BuildJob,
    BuildStatus,
    RiskLevel,
    Complexity
)

logger = logging.getLogger("aria.builder.telegram")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


@dataclass
class InlineButton:
    """A Telegram inline keyboard button."""
    text: str
    callback_data: str


class BuilderTelegramInterface:
    """
    Full Telegram interface for the Unified Builder.
    
    Commands:
    - /build <request> - Generate code from natural language
    - /pending - Show pending changes
    - /approve <id> - Approve a change
    - /deny <id> - Deny a change  
    - /rollback <id> - Rollback applied change
    - /queue - Show build queue status
    - /scope - Show your scope permissions
    - /builds - List recent builds
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=60.0)
        self._builder: Optional[UnifiedBuilder] = None
    
    @property
    def builder(self) -> UnifiedBuilder:
        if self._builder is None:
            self._builder = get_unified_builder()
        return self._builder
    
    async def close(self):
        await self.http.aclose()
    
    # ========================================================================
    # TELEGRAM API HELPERS
    # ========================================================================
    
    async def send_message(
        self,
        chat_id: int,
        text: str,
        buttons: Optional[List[List[InlineButton]]] = None,
        reply_to: Optional[int] = None,
        parse_mode: str = "Markdown"
    ) -> Dict:
        """Send message with optional inline keyboard."""
        # Truncate text if too long
        if len(text) > 4000:
            text = text[:3900] + "\n\n... (truncated)"
        
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
            logger.error(f"Send message error: {e}")
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
        if len(text) > 4000:
            text = text[:3900] + "\n\n... (truncated)"
            
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
            logger.error(f"Edit message error: {e}")
            return {"ok": False, "error": str(e)}
    
    async def answer_callback(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False
    ) -> Dict:
        """Answer a callback query (acknowledge button press)."""
        payload = {"callback_query_id": callback_query_id}
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
            logger.error(f"Answer callback error: {e}")
            return {"ok": False, "error": str(e)}
    
    # ========================================================================
    # CALLBACK HANDLERS
    # ========================================================================
    
    async def handle_callback(self, callback_query: Dict) -> Optional[str]:
        """Handle inline button press."""
        query_id = callback_query.get("id")
        data = callback_query.get("data", "")
        message = callback_query.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        
        if not all([query_id, data, chat_id]):
            return None
        
        # Parse callback data: action:id
        parts = data.split(":")
        action = parts[0]
        target_id = parts[1] if len(parts) > 1 else None
        
        handlers = {
            "approve": self._handle_approve,
            "deny": self._handle_deny,
            "rollback": self._handle_rollback,
            "detail": self._handle_detail,
            "approve_build": self._handle_approve_build,
            "reject_build": self._handle_reject_build,
            "save_template": self._handle_save_template,
        }
        
        handler = handlers.get(action)
        if handler and target_id:
            return await handler(query_id, chat_id, message_id, target_id)
        
        await self.answer_callback(query_id, "Unknown action")
        return None
    
    async def _handle_approve(
        self,
        query_id: str,
        chat_id: int,
        message_id: int,
        change_id: str
    ) -> str:
        """Approve and apply a pending change."""
        await self.answer_callback(query_id, "Applying change...")
        
        success, msg = self.builder.apply_change(change_id)
        
        if success:
            await self.edit_message(
                chat_id, message_id,
                f"✅ *Change Applied*\n\n{msg}\n\n_ID: {change_id}_",
                buttons=[[InlineButton("⏪ Rollback", f"rollback:{change_id}")]]
            )
            return f"Applied {change_id}"
        else:
            await self.edit_message(
                chat_id, message_id,
                f"❌ *Apply Failed*\n\n{msg}\n\n_ID: {change_id}_"
            )
            return f"Failed: {msg}"
    
    async def _handle_deny(
        self,
        query_id: str,
        chat_id: int,
        message_id: int,
        change_id: str
    ) -> str:
        """Deny and cancel a pending change."""
        await self.answer_callback(query_id, "Change denied")
        
        self.builder.cancel_change(change_id)
        
        await self.edit_message(
            chat_id, message_id,
            f"🚫 *Change Denied*\n\n_ID: {change_id}_"
        )
        return f"Denied {change_id}"
    
    async def _handle_rollback(
        self,
        query_id: str,
        chat_id: int,
        message_id: int,
        change_id: str
    ) -> str:
        """Rollback an applied change."""
        await self.answer_callback(query_id, "Rolling back...")
        
        # For individual changes, we need to find the job
        # This is simplified - in production would track better
        success, msg = False, "Individual rollback not yet implemented - use /rollback <job_id>"
        
        if success:
            await self.edit_message(
                chat_id, message_id,
                f"⏪ *Rolled Back*\n\n{msg}"
            )
        else:
            await self.send_message(
                chat_id,
                f"⚠️ *Rollback Note*\n\n{msg}"
            )
        
        return msg
    
    async def _handle_detail(
        self,
        query_id: str,
        chat_id: int,
        message_id: int,
        change_id: str
    ) -> str:
        """Show detailed diff for a change."""
        await self.answer_callback(query_id)
        
        change = self.builder.pending_changes.get(change_id)
        if not change:
            await self.send_message(chat_id, f"Change {change_id} not found")
            return "Not found"
        
        diff = change.get_diff_preview(context_lines=10)
        await self.send_message(
            chat_id,
            f"*Full Change Details*\n\n```\n{diff}\n```"
        )
        return f"Showed details for {change_id}"
    
    async def _handle_approve_build(
        self,
        query_id: str,
        chat_id: int,
        message_id: int,
        job_id: str
    ) -> str:
        """Approve a queued build job."""
        await self.answer_callback(query_id, "Approving build...")
        
        success = self.builder.approve_build(job_id)
        
        if success:
            await self.edit_message(
                chat_id, message_id,
                f"✅ *Build Approved*\n\nJob {job_id} queued for execution."
            )
            
            # Trigger queue processing
            results = await self.builder.process_queue()
            if results:
                job = results[0]
                status_emoji = "✅" if job.status == BuildStatus.COMPLETED else "❌"
                await self.send_message(
                    chat_id,
                    f"{status_emoji} *Build {job.status.value}*\n\n{job.error_message or 'Success!'}"
                )
            
            return f"Approved {job_id}"
        else:
            await self.edit_message(
                chat_id, message_id,
                f"❌ *Approve Failed*\n\nJob {job_id} not found or already processed."
            )
            return f"Failed to approve {job_id}"
    
    async def _handle_reject_build(
        self,
        query_id: str,
        chat_id: int,
        message_id: int,
        job_id: str
    ) -> str:
        """Reject a queued build job."""
        await self.answer_callback(query_id, "Build rejected")
        
        self.builder.reject_build(job_id)
        
        await self.edit_message(
            chat_id, message_id,
            f"🚫 *Build Rejected*\n\n_ID: {job_id}_"
        )
        return f"Rejected {job_id}"
    
    async def _handle_save_template(
        self,
        query_id: str,
        chat_id: int,
        message_id: int,
        job_id: str
    ) -> str:
        """Save a build as a template - prompts for name."""
        await self.answer_callback(query_id, "Preparing to save template...")
        
        # Get job details for the name suggestion
        job_data = self.builder.get_job(job_id)
        if not job_data:
            await self.send_message(chat_id, f"❌ Job {job_id} not found")
            return f"Job not found: {job_id}"
        
        # Suggest a template name based on title
        suggested_name = job_data.get('title', 'template')[:30].lower()
        suggested_name = '-'.join(suggested_name.split())
        
        await self.send_message(
            chat_id,
            f"💾 *Save as Template*\n\n"
            f"Job: `{job_id}`\n"
            f"Title: {job_data.get('title', 'Untitled')}\n\n"
            f"To save, send:\n`/savetemplate {job_id} {suggested_name}`\n\n"
            f"You can change the name to anything you like."
        )
        
        return f"Template save prompt for {job_id}"
    
    # ========================================================================
    # COMMAND HANDLERS
    # ========================================================================
    
    async def handle_command(
        self,
        chat_id: int,
        user_id: int,
        command: str,
        args: List[str],
        scope: str = "apprentice"
    ) -> str:
        """Handle explicit builder commands."""
        
        handlers = {
            "/build": self._cmd_build,
            "/pending": self._cmd_pending,
            "/approve": self._cmd_approve,
            "/deny": self._cmd_deny,
            "/rollback": self._cmd_rollback,
            "/queue": self._cmd_queue,
            "/scope": self._cmd_scope,
            "/builds": self._cmd_builds,
        }
        
        handler = handlers.get(command)
        if handler:
            return await handler(chat_id, user_id, args, scope)
        
        return ""
    
    async def _cmd_build(
        self,
        chat_id: int,
        user_id: int,
        args: List[str],
        scope: str
    ) -> str:
        """Handle /build command."""
        if not args:
            return await self._show_help(chat_id)
        
        request = " ".join(args)
        
        # Send "thinking" message
        await self.send_message(
            chat_id,
            f"🔨 *Building...*\n\nAnalyzing request:\n_{request}_"
        )
        
        # Generate and queue build
        result = await build_from_request(
            request=request,
            user_id=str(user_id),
            scope=scope
        )
        
        if not result["success"]:
            await self.send_message(
                chat_id,
                f"❌ *Build Failed*\n\n{result['message']}"
            )
            return result["message"]
        
        job = result["job"]
        
        # Format changes preview
        changes_preview = ""
        for i, change in enumerate(job.get("changes", [])[:3]):
            changes_preview += f"\n{i+1}. {change['action'].upper()} `{change['file_path']}`"
            changes_preview += f"\n   _{change.get('description', 'No description')[:50]}_"
        
        if len(job.get("changes", [])) > 3:
            changes_preview += f"\n\n_...and {len(job['changes']) - 3} more changes_"
        
        # Build message
        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "⛔"}.get(
            job.get("risk", "medium"), "🟡"
        )
        
        msg = f"""🔨 *Build Proposal*

*{job['title']}*

{result['message']}

{risk_emoji} Risk: {job.get('risk', 'medium').upper()}
📊 Complexity: {job.get('complexity', 'medium').upper()}

*Changes:*{changes_preview}

_Job ID: {job['id']}_"""
        
        if result["needs_approval"]:
            buttons = [
                [
                    InlineButton("✅ Approve", f"approve_build:{job['id']}"),
                    InlineButton("❌ Reject", f"reject_build:{job['id']}")
                ],
                [InlineButton("📋 Details", f"detail:{job['id']}")]
            ]
            await self.send_message(chat_id, msg, buttons=buttons)
        else:
            # Auto-approve and execute
            await self.send_message(chat_id, msg + "\n\n_Auto-approved (low risk)_")
            
            results = await self.builder.process_queue()
            if results:
                job_result = results[0]
                status_emoji = "✅" if job_result.status == BuildStatus.COMPLETED else "❌"
                await self.send_message(
                    chat_id,
                    f"{status_emoji} *Build {job_result.status.value}*\n\n{job_result.error_message or 'Changes applied successfully!'}"
                )
        
        return result["message"]
    
    async def _cmd_pending(
        self,
        chat_id: int,
        user_id: int,
        args: List[str],
        scope: str
    ) -> str:
        """Show pending changes."""
        pending = self.builder.get_pending()
        
        if not pending:
            await self.send_message(chat_id, "📭 No pending changes.")
            return "No pending"
        
        msg = "*Pending Changes:*\n\n"
        for change in pending[:10]:
            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(
                change.risk.value, "🟡"
            )
            msg += f"{risk_emoji} `{change.id}`: {change.description[:40]}...\n"
            msg += f"   📁 {change.file_path}\n\n"
        
        if len(pending) > 10:
            msg += f"\n_...and {len(pending) - 10} more_"
        
        await self.send_message(chat_id, msg)
        return f"{len(pending)} pending"
    
    async def _cmd_approve(
        self,
        chat_id: int,
        user_id: int,
        args: List[str],
        scope: str
    ) -> str:
        """Approve a pending change or build."""
        if not args:
            await self.send_message(chat_id, "Usage: `/approve <id>`")
            return "Need ID"
        
        target_id = args[0]
        
        # Try as change first
        success, msg = self.builder.apply_change(target_id)
        
        if not success and "not found" in msg.lower():
            # Try as build job
            success = self.builder.approve_build(target_id)
            if success:
                msg = "Build approved and queued"
                # Process queue
                results = await self.builder.process_queue()
                if results:
                    job = results[0]
                    msg += f"\nResult: {job.status.value}"
        
        emoji = "✅" if success else "❌"
        await self.send_message(chat_id, f"{emoji} {msg}")
        return msg
    
    async def _cmd_deny(
        self,
        chat_id: int,
        user_id: int,
        args: List[str],
        scope: str
    ) -> str:
        """Deny/cancel a pending change."""
        if not args:
            await self.send_message(chat_id, "Usage: `/deny <id>`")
            return "Need ID"
        
        target_id = args[0]
        success, msg = self.builder.cancel_change(target_id)
        
        if not success:
            # Try as build
            success = self.builder.reject_build(target_id)
            msg = "Build rejected" if success else "Not found"
        
        emoji = "✅" if success else "❌"
        await self.send_message(chat_id, f"{emoji} {msg}")
        return msg
    
    async def _cmd_rollback(
        self,
        chat_id: int,
        user_id: int,
        args: List[str],
        scope: str
    ) -> str:
        """Rollback a build."""
        if not args:
            await self.send_message(chat_id, "Usage: `/rollback <job_id>`")
            return "Need job ID"
        
        job_id = args[0]
        success, msg = self.builder.rollback(job_id)
        
        emoji = "✅" if success else "❌"
        await self.send_message(chat_id, f"{emoji} {msg}")
        return msg
    
    async def _cmd_queue(
        self,
        chat_id: int,
        user_id: int,
        args: List[str],
        scope: str
    ) -> str:
        """Show build queue status."""
        status = self.builder.get_queue_status()
        
        counts = status.get("status_counts", {})
        recent = status.get("recent_builds", [])
        pending = status.get("pending_changes", 0)
        
        msg = "*📊 Build Queue Status*\n\n"
        
        msg += "*Counts:*\n"
        for stat, count in counts.items():
            emoji = {
                "queued": "⏳",
                "building": "🔨",
                "completed": "✅",
                "failed": "❌",
                "needs_approval": "🔔",
                "rolled_back": "⏪"
            }.get(stat, "•")
            msg += f"  {emoji} {stat}: {count}\n"
        
        msg += f"\n*Pending Changes:* {pending}\n"
        
        if recent:
            msg += "\n*Recent:*\n"
            for job in recent[:5]:
                status_emoji = {"completed": "✅", "failed": "❌", "queued": "⏳"}.get(
                    job.get("status", ""), "•"
                )
                msg += f"  {status_emoji} `{job['id']}`: {job['title'][:30]}\n"
        
        await self.send_message(chat_id, msg)
        return "Queue status"
    
    async def _cmd_scope(
        self,
        chat_id: int,
        user_id: int,
        args: List[str],
        scope: str
    ) -> str:
        """Show user's scope permissions."""
        from .unified_engine import SCOPE_DEFINITIONS
        
        scope_def = SCOPE_DEFINITIONS.get(scope, {})
        
        msg = f"*🔐 Your Scope: {scope.upper()}*\n\n"
        
        msg += "*Allowed Paths:*\n"
        for path in scope_def.get("paths", []):
            path = path.replace("{user_id}", str(user_id))
            msg += f"  📁 `{path}`\n"
        
        msg += f"\n*Allowed Files:* {', '.join(scope_def.get('files', []))}\n"
        msg += f"*Max Complexity:* {scope_def.get('max_complexity', 'medium')}\n"
        msg += f"*Auto-approve:* {', '.join(str(r) for r in scope_def.get('auto_approve', []))}\n"
        
        if scope_def.get("protected"):
            msg += f"\n⚠️ *Protected (read-only):* {', '.join(scope_def['protected'])}"
        
        await self.send_message(chat_id, msg)
        return f"Scope: {scope}"
    
    async def _cmd_builds(
        self,
        chat_id: int,
        user_id: int,
        args: List[str],
        scope: str
    ) -> str:
        """List recent builds."""
        status = self.builder.get_queue_status()
        recent = status.get("recent_builds", [])
        
        if not recent:
            await self.send_message(chat_id, "📭 No recent builds.")
            return "No builds"
        
        msg = "*🔨 Recent Builds:*\n\n"
        
        for job in recent[:10]:
            status_emoji = {
                "completed": "✅",
                "failed": "❌",
                "queued": "⏳",
                "building": "🔨",
                "needs_approval": "🔔",
                "rolled_back": "⏪",
                "rejected": "🚫"
            }.get(job.get("status", ""), "•")
            
            msg += f"{status_emoji} `{job['id']}`\n"
            msg += f"   *{job['title'][:40]}*\n"
            msg += f"   By: {job['author']} | {job['complexity']}\n\n"
        
        await self.send_message(chat_id, msg)
        return f"{len(recent)} builds"
    
    async def _show_help(self, chat_id: int) -> str:
        """Show builder help."""
        help_text = """*🔨 Aria Unified Builder*

Build through conversation or commands:

*Commands:*
• `/build <request>` - Generate code from description
• `/pending` - Show pending changes
• `/approve <id>` - Approve a change/build
• `/deny <id>` - Deny a change/build
• `/rollback <id>` - Rollback a build
• `/queue` - Show build queue status
• `/scope` - Show your permissions
• `/builds` - List recent builds

*Examples:*
• `/build Add a /status command that shows system health`
• `/build Create a function to calculate trading profit`
• `/build Fix the timeout bug in memory.py`

*Risk Levels:*
🟢 LOW - Auto-applied (new code)
🟡 MEDIUM - Needs approval (modifications)
🔴 HIGH - Requires confirmation (core changes)
⛔ CRITICAL - Steward only

*Features:*
• AI code generation (Claude)
• AI verification (Gemini)
• Auto-backup before changes
• Syntax verification
• One-click rollback"""
        
        await self.send_message(chat_id, help_text)
        return "Help shown"


# ============================================================================
# SINGLETON & INTEGRATION
# ============================================================================

_interface: Optional[BuilderTelegramInterface] = None


def get_builder_interface() -> BuilderTelegramInterface:
    """Get global interface instance."""
    global _interface
    if _interface is None:
        _interface = BuilderTelegramInterface()
    return _interface


async def handle_builder_update(update: Dict, scope: str = "apprentice") -> Optional[str]:
    """
    Integration helper - call from main Telegram webhook.
    
    Returns response if handled, None otherwise.
    """
    interface = get_builder_interface()
    
    # Handle callback queries (button presses)
    if "callback_query" in update:
        callback = update["callback_query"]
        data = callback.get("data", "")
        
        # Check if this is a builder callback
        builder_actions = ["approve", "deny", "rollback", "detail", "approve_build", "reject_build"]
        if any(data.startswith(action) for action in builder_actions):
            return await interface.handle_callback(callback)
    
    # Handle messages
    if "message" in update:
        message = update["message"]
        text = message.get("text", "").strip()
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        
        if not text or not chat_id:
            return None
        
        # Check for builder commands
        builder_commands = ["/build", "/pending", "/approve", "/deny", "/rollback", "/queue", "/scope", "/builds"]
        
        for cmd in builder_commands:
            if text.lower().startswith(cmd):
                parts = text.split(maxsplit=1)
                command = parts[0].lower()
                args = parts[1].split() if len(parts) > 1 else []
                return await interface.handle_command(chat_id, user_id, command, args, scope)
    
    return None


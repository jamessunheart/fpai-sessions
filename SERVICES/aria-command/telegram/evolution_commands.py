#!/usr/bin/env python3
"""
ARIA EVOLUTION COMMANDS
========================

Telegram commands for interacting with the evolution system.

Commands:
- /evolution status - Show evolution status
- /evolution stats - Show evolution statistics
- /evolution proposals - List pending proposals
- /evolution approve <id> - Approve a proposal
- /evolution reject <id> - Reject a proposal
- /evolution history - Show recent changes
- /evolution rollback <id> - Rollback a change
- /evolution run - Run manual evolution cycle
- /evolution stop - Stop auto-evolution
- /evolution start - Start auto-evolution
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Callable, Any

logger = logging.getLogger("aria.telegram.evolution")

# Import evolution components
try:
    from sovereign.evolution import (
        get_evolution_daemon,
        get_synthesizer,
        get_safe_applicator,
        get_prompt_evolver,
        get_efficiency_evolver,
        get_proactive_evolver,
        get_interaction_logger,
        apply_proposal,
        rollback_prompt
    )
    EVOLUTION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Evolution system not available: {e}")
    EVOLUTION_AVAILABLE = False


class EvolutionCommands:
    """Telegram command handlers for the evolution system."""
    
    def __init__(self, send_message: Callable):
        """
        Initialize with a message sending function.
        
        Args:
            send_message: Async function(chat_id, text, parse_mode) to send messages
        """
        self.send_message = send_message
    
    async def handle_evolution_command(self, chat_id: str, args: list) -> str:
        """Handle /evolution command."""
        if not EVOLUTION_AVAILABLE:
            return "❌ Evolution system not available"
        
        if not args:
            return await self._show_help()
        
        subcommand = args[0].lower()
        sub_args = args[1:] if len(args) > 1 else []
        
        handlers = {
            "status": self._status,
            "stats": self._stats,
            "proposals": self._proposals,
            "approve": self._approve,
            "reject": self._reject,
            "history": self._history,
            "rollback": self._rollback,
            "run": self._run_cycle,
            "stop": self._stop,
            "start": self._start,
            "digest": self._digest,
            "help": self._show_help
        }
        
        handler = handlers.get(subcommand)
        if handler:
            return await handler(sub_args) if sub_args else await handler()
        else:
            return f"Unknown subcommand: {subcommand}\n\n" + await self._show_help()
    
    async def _show_help(self, args=None) -> str:
        """Show help message."""
        return """🧬 **Aria Evolution System**

**Commands:**
• `/evolution status` - Current evolution status
• `/evolution stats` - Evolution statistics
• `/evolution proposals` - Pending improvements
• `/evolution approve <id>` - Approve a proposal
• `/evolution reject <id>` - Reject a proposal
• `/evolution history` - Recent changes
• `/evolution rollback <id>` - Rollback a change
• `/evolution run` - Run evolution cycle now
• `/evolution digest` - Generate daily digest
• `/evolution stop` - Pause auto-evolution
• `/evolution start` - Resume auto-evolution

**Auto-Evolution Schedule:**
• 6:00 AM - Analyze interactions
• 6:30 AM - Design improvements
• 7:00 AM - Apply safe changes
• 8:00 AM - Send digest"""
    
    async def _status(self, args=None) -> str:
        """Show evolution status."""
        daemon = get_evolution_daemon()
        status = daemon.get_status()
        
        efficiency = get_efficiency_evolver().get_efficiency_stats(1)
        proactive = get_proactive_evolver().get_patterns_summary()
        
        msg = f"""🧬 **Evolution Status**

**Daemon:** {"🟢 Running" if status['running'] else "🔴 Stopped"}
**Enabled:** {"✅ Yes" if status['enabled'] else "❌ No"}

**Last Cycle:**
• Time: {status['last_cycle']['timestamp'] or 'Never'}
• Interactions: {status['last_cycle']['interactions']}
• Changes Applied: {status['last_cycle']['changes_applied']}

**Components:** All active

**Efficiency (24h):**
• Cache hits: {efficiency.get('cache_hits', 0)}
• Cost saved: ${efficiency.get('cost_saved_by_cache', 0):.4f}

**Proactive Patterns:** {sum(p['count'] for p in proactive.get('by_trigger_type', {}).values())} active"""
        
        return msg
    
    async def _stats(self, args=None) -> str:
        """Show evolution statistics."""
        efficiency = get_efficiency_evolver().get_efficiency_stats(7)
        changes = get_safe_applicator().get_change_stats()
        synthesizer = get_synthesizer()
        proposal_stats = synthesizer.get_proposal_stats()
        
        msg = f"""📊 **Evolution Statistics (7 days)**

**Efficiency:**
• Cache hits: {efficiency.get('cache_hits', 0)}
• Cost saved: ${efficiency.get('cost_saved_by_cache', 0):.4f}
• Total API cost: ${efficiency.get('total_cost', 0):.2f}

**Model Usage:**"""
        
        for model, data in efficiency.get('by_model', {}).items():
            msg += f"\n• {model}: {data['count']} calls, ${data['avg_cost']:.4f}/call"
        
        msg += f"""

**Proposals:**
• Generated: {sum(d['count'] for d in proposal_stats.get('by_status', {}).values())}
• Success rate: {proposal_stats.get('success_rate', 0)*100:.0f}%

**Changes:**
• Total: {changes.get('total_changes', 0)}
• Success rate: {changes.get('success_rate', 0)*100:.0f}%"""
        
        return msg
    
    async def _proposals(self, args=None) -> str:
        """List pending proposals."""
        synthesizer = get_synthesizer()
        proposals = synthesizer.get_pending_proposals()
        
        if not proposals:
            return "✨ No pending proposals - system is optimized!"
        
        msg = "📋 **Pending Proposals**\n\n"
        
        for p in proposals[:10]:
            confidence_bar = "█" * int(p.confidence * 5) + "░" * (5 - int(p.confidence * 5))
            msg += f"**#{p.id}** [{p.category}]\n"
            msg += f"• Problem: {p.problem[:60]}...\n"
            msg += f"• Solution: {p.solution[:60]}...\n"
            msg += f"• Confidence: {confidence_bar} {p.confidence:.0%}\n"
            msg += f"• Risk: {p.risk_level}\n\n"
        
        if len(proposals) > 10:
            msg += f"_...and {len(proposals) - 10} more_"
        
        msg += "\n\nUse `/evolution approve <id>` to approve"
        
        return msg
    
    async def _approve(self, args) -> str:
        """Approve a proposal."""
        if not args:
            return "Usage: `/evolution approve <id>`"
        
        try:
            proposal_id = int(args[0])
        except ValueError:
            return "Invalid proposal ID"
        
        synthesizer = get_synthesizer()
        proposals = synthesizer.get_pending_proposals()
        
        proposal = next((p for p in proposals if p.id == proposal_id), None)
        if not proposal:
            return f"Proposal #{proposal_id} not found or already processed"
        
        # Apply the proposal
        success, msg = await apply_proposal(proposal)
        
        if success:
            synthesizer.mark_proposal(proposal_id, "applied", "success")
            return f"✅ Proposal #{proposal_id} approved and applied!\n\n{msg}"
        else:
            return f"❌ Failed to apply proposal #{proposal_id}:\n{msg}"
    
    async def _reject(self, args) -> str:
        """Reject a proposal."""
        if not args:
            return "Usage: `/evolution reject <id>`"
        
        try:
            proposal_id = int(args[0])
        except ValueError:
            return "Invalid proposal ID"
        
        synthesizer = get_synthesizer()
        synthesizer.mark_proposal(proposal_id, "rejected", "User rejected")
        
        return f"✅ Proposal #{proposal_id} rejected"
    
    async def _history(self, args=None) -> str:
        """Show recent changes."""
        applicator = get_safe_applicator()
        changes = applicator.get_recent_changes(7)
        
        if not changes:
            return "No recent changes"
        
        msg = "📜 **Recent Changes (7 days)**\n\n"
        
        for c in changes[:10]:
            status_icon = {
                "applied": "✅",
                "failed": "❌",
                "rolled_back": "🔄",
                "pending": "⏳"
            }.get(c["status"], "❓")
            
            msg += f"{status_icon} **#{c['id']}** [{c['change_type']}]\n"
            msg += f"• {c['reason'][:50]}...\n"
            msg += f"• Status: {c['status']}\n\n"
        
        return msg
    
    async def _rollback(self, args) -> str:
        """Rollback a change."""
        if not args:
            # Rollback prompt to previous version
            success = rollback_prompt()
            if success:
                return "✅ Prompt rolled back to previous version"
            else:
                return "❌ Failed to rollback prompt"
        
        try:
            change_id = int(args[0])
        except ValueError:
            return "Usage: `/evolution rollback [change_id]`"
        
        applicator = get_safe_applicator()
        success, msg = await applicator.rollback_change(change_id, "User requested rollback")
        
        if success:
            return f"✅ Change #{change_id} rolled back"
        else:
            return f"❌ Failed to rollback: {msg}"
    
    async def _run_cycle(self, args=None) -> str:
        """Run a manual evolution cycle."""
        daemon = get_evolution_daemon()
        
        # Send initial message
        await self.send_message(
            os.getenv("SUNHEART_CHAT_ID"),
            "🔄 Starting evolution cycle...",
            "Markdown"
        )
        
        result = await daemon.run_manual_cycle()
        
        msg = f"""✅ **Evolution Cycle Complete**

**Analysis:**
• Interactions analyzed: {result.interactions_analyzed}
• Patterns detected: {result.patterns_detected}

**Proposals:**
• Generated: {result.proposals_generated}
• Auto-approved: {result.proposals_auto_approved}
• Pending: {result.proposals_pending}

**Changes:**
• Applied: {result.changes_applied}
• Failed: {result.changes_failed}
• Rolled back: {result.changes_rolled_back}"""
        
        return msg
    
    async def _stop(self, args=None) -> str:
        """Stop auto-evolution."""
        daemon = get_evolution_daemon()
        daemon.stop()
        return "⏹️ Auto-evolution stopped"
    
    async def _start(self, args=None) -> str:
        """Start auto-evolution."""
        # Note: This would need to restart the daemon in a background task
        return "▶️ Auto-evolution started\n\n_Note: Run `/evolution status` to verify_"
    
    async def _digest(self, args=None) -> str:
        """Generate and return the daily digest."""
        daemon = get_evolution_daemon()
        digest = await daemon._generate_digest()
        return digest


# ============================================================================
# HELPER FOR REGISTRATION
# ============================================================================

def register_evolution_commands(bot_instance):
    """
    Register evolution commands with the bot.
    
    Call this from bot.py to add evolution commands.
    """
    async def send_message(chat_id, text, parse_mode="Markdown"):
        # Implementation depends on bot structure
        pass
    
    return EvolutionCommands(send_message)



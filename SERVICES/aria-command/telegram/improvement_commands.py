#!/usr/bin/env python3
"""
ARIA SELF-IMPROVEMENT TELEGRAM COMMANDS
=========================================

Commands for managing the self-improvement system:
- /improvements - View pending improvement proposals
- /approve <id> - Approve a pending change
- /reject <id> - Reject with optional feedback
- /costs - View self-improvement costs
- /changelog - View recent changes
- /review - Trigger manual review
- /digest - Get improvement digest now
"""

import asyncio
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger("aria.telegram.improvements")


@dataclass
class CommandResult:
    """Result of command execution."""
    text: str
    voice: bool = False
    buttons: Optional[list] = None
    success: bool = True


async def handle_improvements(chat_id: int, args: str) -> CommandResult:
    """
    Handle /improvements command - view pending proposals.
    """
    try:
        from ..sovereign import get_reviewer
    except ImportError:
        from sovereign import get_reviewer
    
    reviewer = get_reviewer()
    pending = reviewer.get_pending_proposals()
    
    if not pending:
        return CommandResult(
            text="✨ **No Pending Improvements**\n\nAll proposals have been processed.",
            success=True
        )
    
    lines = [f"**Pending Improvements ({len(pending)})**", ""]
    
    for proposal in pending:
        risk_icons = {1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴", 5: "⛔"}
        icon = risk_icons.get(proposal.risk_level, "❓")
        
        lines.extend([
            f"{icon} **`{proposal.id}`** (Risk {proposal.risk_level})",
            f"   📁 `{proposal.file_path}`",
            f"   🔍 {proposal.problem_description[:60]}...",
            f"   💡 {proposal.solution_description[:60]}...",
            ""
        ])
    
    lines.extend([
        "---",
        "**Commands:**",
        "• `/approve <id>` - Apply this change",
        "• `/reject <id> [reason]` - Reject with feedback",
        "• `/show <id>` - View full proposal with diff"
    ])
    
    return CommandResult(text="\n".join(lines), success=True)


async def handle_approve(chat_id: int, args: str) -> CommandResult:
    """
    Handle /approve command - approve and apply a proposal.
    """
    if not args:
        return CommandResult(
            text="Usage: `/approve <improvement_id>`\n\nExample: `/approve IMP-20251223-0001`",
            success=False
        )
    
    proposal_id = args.strip()
    
    try:
        from ..sovereign import get_reviewer, get_executor, get_risk_engine
    except ImportError:
        from sovereign import get_reviewer, get_executor, get_risk_engine
    
    reviewer = get_reviewer()
    proposal = reviewer.get_proposal(proposal_id)
    
    if not proposal:
        return CommandResult(
            text=f"❌ Proposal `{proposal_id}` not found.\n\nUse `/improvements` to see pending proposals.",
            success=False
        )
    
    if proposal.status != "pending":
        return CommandResult(
            text=f"❌ Proposal `{proposal_id}` is already {proposal.status}.",
            success=False
        )
    
    # Mark as approved
    reviewer.approve_proposal(proposal_id)
    
    # Execute the improvement
    executor = get_executor()
    result = await executor.execute(
        improvement_id=proposal_id,
        file_path=proposal.file_path,
        diff=proposal.code_diff,
        description=proposal.solution_description,
        risk_level=proposal.risk_level
    )
    
    if result.success:
        return CommandResult(
            text=(
                f"✅ **Improvement Applied**\n\n"
                f"📝 `{proposal_id}`\n"
                f"📁 `{proposal.file_path}`\n"
                f"💡 {proposal.solution_description[:100]}\n\n"
                f"The service has been restarted to apply changes."
            ),
            success=True
        )
    elif result.rolled_back:
        return CommandResult(
            text=(
                f"↩️ **Change Rolled Back**\n\n"
                f"📝 `{proposal_id}`\n"
                f"❌ {result.error}\n\n"
                f"The change was automatically reverted because health check failed."
            ),
            success=False
        )
    else:
        return CommandResult(
            text=(
                f"❌ **Execution Failed**\n\n"
                f"📝 `{proposal_id}`\n"
                f"Error: {result.error}\n\n"
                f"No changes were applied."
            ),
            success=False
        )


async def handle_reject(chat_id: int, args: str) -> CommandResult:
    """
    Handle /reject command - reject a proposal with optional reason.
    """
    parts = args.strip().split(maxsplit=1)
    
    if not parts:
        return CommandResult(
            text="Usage: `/reject <improvement_id> [reason]`\n\nExample: `/reject IMP-20251223-0001 Not needed`",
            success=False
        )
    
    proposal_id = parts[0]
    reason = parts[1] if len(parts) > 1 else ""
    
    try:
        from ..sovereign import get_reviewer
    except ImportError:
        from sovereign import get_reviewer
    
    reviewer = get_reviewer()
    proposal = reviewer.get_proposal(proposal_id)
    
    if not proposal:
        return CommandResult(
            text=f"❌ Proposal `{proposal_id}` not found.",
            success=False
        )
    
    if proposal.status != "pending":
        return CommandResult(
            text=f"❌ Proposal `{proposal_id}` is already {proposal.status}.",
            success=False
        )
    
    # Mark as rejected
    reviewer.reject_proposal(proposal_id, reason)
    
    return CommandResult(
        text=(
            f"🚫 **Proposal Rejected**\n\n"
            f"📝 `{proposal_id}`\n"
            f"📁 `{proposal.file_path}`\n"
            + (f"📋 Reason: {reason}" if reason else "")
        ),
        success=True
    )


async def handle_costs(chat_id: int, args: str) -> CommandResult:
    """
    Handle /costs command - view self-improvement costs.
    """
    try:
        from ..sovereign import get_cost_tracker
    except ImportError:
        from sovereign import get_cost_tracker
    
    days = 7  # Default
    if args:
        try:
            days = int(args.strip())
        except ValueError:
            pass
    
    tracker = get_cost_tracker()
    report = tracker.format_report(days)
    
    # Check for alerts
    alerts = tracker.get_unacknowledged_alerts()
    if alerts:
        report += "\n\n⚠️ **Alerts:**\n"
        for alert in alerts[:3]:
            report += f"• {alert['message']}\n"
    
    return CommandResult(text=report, success=True)


async def handle_changelog(chat_id: int, args: str) -> CommandResult:
    """
    Handle /changelog command - view recent changes.
    """
    try:
        from ..sovereign import get_executor
    except ImportError:
        from sovereign import get_executor
    
    limit = 10
    if args:
        try:
            limit = int(args.strip())
        except ValueError:
            pass
    
    executor = get_executor()
    changelog = executor.format_changelog(limit)
    
    return CommandResult(text=changelog, success=True)


async def handle_review(chat_id: int, args: str) -> CommandResult:
    """
    Handle /review command - trigger manual review.
    """
    try:
        from ..sovereign import run_manual_review, can_spend
    except ImportError:
        from sovereign import run_manual_review, can_spend
    
    # Check budget
    if not can_spend(0.50):
        return CommandResult(
            text="⚠️ **Insufficient Budget**\n\nDaily budget exhausted. Try again tomorrow.",
            success=False
        )
    
    # Send immediate feedback
    await _send_message(
        chat_id,
        "🔍 **Starting Manual Review...**\n\nThis may take 1-2 minutes."
    )
    
    try:
        proposals = await run_manual_review()
        
        if not proposals:
            return CommandResult(
                text="✨ **Review Complete**\n\nNo issues found in the last 24 hours.",
                success=True
            )
        
        lines = [f"**Review Complete: {len(proposals)} proposals generated**", ""]
        
        for p in proposals[:5]:
            risk_icons = {1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴", 5: "⛔"}
            icon = risk_icons.get(p.risk_level, "❓")
            lines.append(f"{icon} `{p.id}`: {p.problem_description[:40]}...")
        
        lines.append("")
        lines.append("Use `/improvements` to review.")
        
        return CommandResult(text="\n".join(lines), success=True)
        
    except Exception as e:
        logger.error(f"Manual review failed: {e}")
        return CommandResult(
            text=f"❌ **Review Failed**\n\nError: {str(e)[:100]}",
            success=False
        )


async def handle_digest(chat_id: int, args: str) -> CommandResult:
    """
    Handle /digest command - get improvement digest now.
    """
    try:
        from ..sovereign.improvement_digest import generate_digest
    except ImportError:
        from sovereign.improvement_digest import generate_digest
    
    try:
        digest_content = await generate_digest()
        return CommandResult(text=digest_content, success=True)
    except Exception as e:
        logger.error(f"Failed to generate digest: {e}")
        return CommandResult(
            text=f"❌ **Digest Failed**\n\nError: {str(e)[:100]}",
            success=False
        )


async def handle_show(chat_id: int, args: str) -> CommandResult:
    """
    Handle /show command - show full proposal details.
    """
    if not args:
        return CommandResult(
            text="Usage: `/show <improvement_id>`",
            success=False
        )
    
    proposal_id = args.strip()
    
    try:
        from ..sovereign import get_reviewer, get_risk_engine
    except ImportError:
        from sovereign import get_reviewer, get_risk_engine
    
    reviewer = get_reviewer()
    proposal = reviewer.get_proposal(proposal_id)
    
    if not proposal:
        return CommandResult(
            text=f"❌ Proposal `{proposal_id}` not found.",
            success=False
        )
    
    risk_icons = {1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴", 5: "⛔"}
    icon = risk_icons.get(proposal.risk_level, "❓")
    
    lines = [
        f"**Proposal: `{proposal.id}`**",
        "",
        f"**Status:** {proposal.status}",
        f"**Risk:** {icon} Level {proposal.risk_level}",
        f"**File:** `{proposal.file_path}`",
        "",
        "**Problem:**",
        proposal.problem_description,
        "",
        "**Solution:**",
        proposal.solution_description,
        "",
        "**Risk Factors:**"
    ]
    
    for factor in proposal.risk_factors[:5]:
        lines.append(f"• {factor}")
    
    lines.extend([
        "",
        "**Expected Impact:**",
        proposal.expected_impact,
        "",
        "**Diff:**",
        "```",
        proposal.code_diff[:1500],  # Truncate for Telegram
        "```"
    ])
    
    if proposal.status == "pending":
        lines.extend([
            "",
            "---",
            f"• `/approve {proposal.id}` - Apply this change",
            f"• `/reject {proposal.id}` - Reject"
        ])
    
    return CommandResult(text="\n".join(lines), success=True)


# Helper function
async def _send_message(chat_id: int, text: str):
    """Send a message to Telegram."""
    import httpx
    
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return
    
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        )


import os  # Ensure os is imported at module level



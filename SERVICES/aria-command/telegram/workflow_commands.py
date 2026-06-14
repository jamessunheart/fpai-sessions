#!/usr/bin/env python3
"""
ARIA ULTRA POWER - WORKFLOW TELEGRAM COMMANDS
==============================================

Telegram command handlers for the workflow system.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger("aria.telegram.workflows")


@dataclass
class CommandResult:
    """Result of command execution."""
    text: str
    voice: bool = False
    buttons: Optional[List[Dict]] = None
    success: bool = True


async def handle_workflow(chat_id: int, args: str) -> CommandResult:
    """
    Handle /workflow command and subcommands.
    
    Subcommands:
    - /workflow list - List your workflows
    - /workflow create - Interactive workflow builder
    - /workflow <id> - Show workflow details
    - /workflow pause <id> - Pause a workflow
    - /workflow resume <id> - Resume a workflow
    - /workflow delete <id> - Delete a workflow
    - /workflow history [id] - View execution history
    - /workflow templates - Show available templates
    """
    from sovereign.workflows import (
        get_workflow_engine,
        get_workflow_store,
        WorkflowStatus,
    )
    
    engine = get_workflow_engine()
    store = get_workflow_store()
    
    parts = args.strip().split() if args else []
    subcmd = parts[0].lower() if parts else "list"
    
    # LIST - Show all workflows
    if subcmd == "list":
        workflows = store.list_workflows(owner_id=str(chat_id))
        
        if not workflows:
            return CommandResult(
                text="📋 **Your Workflows**\n\nNo workflows yet! Use `/workflow create` to make one.",
                buttons=[[{
                    "text": "📝 Create Workflow",
                    "callback_data": "workflow_create"
                }]]
            )
        
        lines = ["📋 **Your Workflows**\n"]
        for w in workflows[:10]:
            status_emoji = "🟢" if w.status == WorkflowStatus.ACTIVE else "⏸️"
            lines.append(f"{status_emoji} **{w.name}** (`{w.id}`)")
            lines.append(f"   Executions: {w.execution_count}")
        
        stats = store.get_stats(owner_id=str(chat_id))
        lines.append(f"\n📊 Active: {stats.get('active_workflows', 0)} | Success rate: {stats.get('success_rate', 0)}%")
        
        return CommandResult(text="\n".join(lines))
    
    # CREATE - Interactive workflow builder
    if subcmd == "create":
        # Send interactive builder
        return CommandResult(
            text="""📝 **Create New Workflow**

Choose a template or describe what you want:

**Quick Templates:**
• "Alert me when SOL drops below $X"
• "Every morning at 9am, send me signals"
• "If SOL drops 5%, close 50% position"

**Or describe in plain English:**
Just tell me what you want to automate!""",
            buttons=[
                [{"text": "💰 Price Alert", "callback_data": "wf_template_price"}],
                [{"text": "⏰ Daily Update", "callback_data": "wf_template_daily"}],
                [{"text": "🛡️ Position Protection", "callback_data": "wf_template_protect"}],
            ]
        )
    
    # TEMPLATES - Show available templates
    if subcmd == "templates":
        from sovereign.workflows.triggers import list_trigger_templates
        from sovereign.workflows.actions import ACTION_TEMPLATES
        
        lines = ["📚 **Workflow Templates**\n"]
        
        lines.append("**Triggers:**")
        for name, config in list_trigger_templates().items():
            lines.append(f"• `{name}`: {config.get('type', '')} trigger")
        
        lines.append("\n**Actions:**")
        for name, config in ACTION_TEMPLATES.items():
            lines.append(f"• `{name}`")
        
        return CommandResult(text="\n".join(lines))
    
    # PAUSE - Pause a workflow
    if subcmd == "pause":
        if len(parts) < 2:
            return CommandResult(text="❌ Usage: `/workflow pause <id>`")
        
        workflow_id = parts[1]
        workflow = store.get_workflow(workflow_id)
        
        if not workflow:
            return CommandResult(text=f"❌ Workflow `{workflow_id}` not found")
        
        if workflow.owner_id != str(chat_id):
            return CommandResult(text="❌ You don't own this workflow")
        
        store.update_status(workflow_id, WorkflowStatus.PAUSED)
        engine.pause_workflow(workflow_id)
        
        return CommandResult(text=f"⏸️ Paused workflow: **{workflow.name}**")
    
    # RESUME - Resume a paused workflow
    if subcmd == "resume":
        if len(parts) < 2:
            return CommandResult(text="❌ Usage: `/workflow resume <id>`")
        
        workflow_id = parts[1]
        workflow = store.get_workflow(workflow_id)
        
        if not workflow:
            return CommandResult(text=f"❌ Workflow `{workflow_id}` not found")
        
        if workflow.owner_id != str(chat_id):
            return CommandResult(text="❌ You don't own this workflow")
        
        store.update_status(workflow_id, WorkflowStatus.ACTIVE)
        engine.resume_workflow(workflow_id)
        
        return CommandResult(text=f"▶️ Resumed workflow: **{workflow.name}**")
    
    # DELETE - Delete a workflow
    if subcmd == "delete":
        if len(parts) < 2:
            return CommandResult(text="❌ Usage: `/workflow delete <id>`")
        
        workflow_id = parts[1]
        workflow = store.get_workflow(workflow_id)
        
        if not workflow:
            return CommandResult(text=f"❌ Workflow `{workflow_id}` not found")
        
        if workflow.owner_id != str(chat_id):
            return CommandResult(text="❌ You don't own this workflow")
        
        store.delete_workflow(workflow_id)
        engine.delete_workflow(workflow_id)
        
        return CommandResult(text=f"🗑️ Deleted workflow: **{workflow.name}**")
    
    # HISTORY - View execution history
    if subcmd == "history":
        workflow_id = parts[1] if len(parts) > 1 else None
        
        executions = store.get_executions(workflow_id=workflow_id, limit=10)
        
        if not executions:
            return CommandResult(text="📜 No execution history yet.")
        
        lines = ["📜 **Execution History**\n"]
        for ex in executions:
            status = "✅" if ex.success else "❌"
            time_str = f"{ex.duration_ms:.0f}ms"
            lines.append(f"{status} `{ex.workflow_id}` - {ex.trigger_type} ({time_str})")
            if ex.error:
                lines.append(f"   Error: {ex.error[:50]}...")
        
        return CommandResult(text="\n".join(lines))
    
    # <ID> - Show workflow details
    workflow = store.get_workflow(subcmd)
    if workflow:
        status_emoji = "🟢" if workflow.status == WorkflowStatus.ACTIVE else "⏸️"
        
        lines = [f"{status_emoji} **{workflow.name}**", ""]
        lines.append(f"ID: `{workflow.id}`")
        lines.append(f"Status: {workflow.status.value}")
        lines.append(f"Executions: {workflow.execution_count}")
        lines.append(f"Cooldown: {workflow.cooldown_seconds}s")
        
        lines.append("\n**Triggers:**")
        for t in workflow.triggers:
            lines.append(f"• {t.get('type', 'unknown')}: {t}")
        
        lines.append("\n**Actions:**")
        for a in workflow.actions:
            lines.append(f"• {list(a.keys())[0] if a else 'unknown'}")
        
        if workflow.description:
            lines.append(f"\n_{workflow.description}_")
        
        buttons = []
        if workflow.status == WorkflowStatus.ACTIVE:
            buttons.append([{"text": "⏸️ Pause", "callback_data": f"wf_pause_{workflow.id}"}])
        else:
            buttons.append([{"text": "▶️ Resume", "callback_data": f"wf_resume_{workflow.id}"}])
        buttons.append([{"text": "🗑️ Delete", "callback_data": f"wf_delete_{workflow.id}"}])
        
        return CommandResult(text="\n".join(lines), buttons=buttons)
    
    # Unknown subcommand
    return CommandResult(
        text="""📋 **Workflow Commands**

`/workflow list` - List your workflows
`/workflow create` - Create new workflow
`/workflow templates` - Show templates
`/workflow <id>` - Show workflow details
`/workflow pause <id>` - Pause workflow
`/workflow resume <id>` - Resume workflow
`/workflow delete <id>` - Delete workflow
`/workflow history [id]` - Execution history"""
    )


async def handle_workflow_callback(chat_id: int, callback_data: str) -> CommandResult:
    """Handle workflow-related callback buttons."""
    from sovereign.workflows import get_workflow_engine, get_workflow_store, WorkflowStatus
    
    engine = get_workflow_engine()
    store = get_workflow_store()
    
    if callback_data == "workflow_create":
        return await handle_workflow(chat_id, "create")
    
    if callback_data.startswith("wf_template_"):
        template = callback_data.replace("wf_template_", "")
        return await _create_from_template(chat_id, template)
    
    if callback_data.startswith("wf_pause_"):
        workflow_id = callback_data.replace("wf_pause_", "")
        return await handle_workflow(chat_id, f"pause {workflow_id}")
    
    if callback_data.startswith("wf_resume_"):
        workflow_id = callback_data.replace("wf_resume_", "")
        return await handle_workflow(chat_id, f"resume {workflow_id}")
    
    if callback_data.startswith("wf_delete_"):
        workflow_id = callback_data.replace("wf_delete_", "")
        return await handle_workflow(chat_id, f"delete {workflow_id}")
    
    return CommandResult(text="Unknown callback")


async def _create_from_template(chat_id: int, template: str) -> CommandResult:
    """Create a workflow from a template."""
    from sovereign.workflows import get_workflow_engine, get_workflow_store
    
    engine = get_workflow_engine()
    store = get_workflow_store()
    
    if template == "price":
        # Price alert template
        workflow = engine.create_workflow(
            name="SOL Price Alert",
            description="Alert when SOL drops below $120",
            owner_id=str(chat_id),
            triggers=[{
                "type": "price",
                "asset": "SOL",
                "condition": "< 120"
            }],
            actions=[{
                "alert": "SOL dropped below $120!"
            }],
            cooldown_seconds=300,  # 5 min cooldown
        )
        store.save_workflow(workflow)
        
        return CommandResult(
            text=f"""✅ **Workflow Created!**

**{workflow.name}** (`{workflow.id}`)

Triggers when: SOL < $120
Action: Send alert

⚠️ Edit the price threshold by describing what you want:
"Change SOL alert to $115"
""",
            buttons=[[{"text": "⏸️ Pause", "callback_data": f"wf_pause_{workflow.id}"}]]
        )
    
    if template == "daily":
        # Daily update template
        workflow = engine.create_workflow(
            name="Morning Signals",
            description="Daily market signals at 9am",
            owner_id=str(chat_id),
            triggers=[{
                "type": "time",
                "schedule": "at 09:00"
            }],
            actions=[{
                "alert": "Good morning! Here are today's signals:"
            }],
            cooldown_seconds=3600,  # 1 hour cooldown
        )
        store.save_workflow(workflow)
        
        return CommandResult(
            text=f"""✅ **Workflow Created!**

**{workflow.name}** (`{workflow.id}`)

Triggers: Every day at 9:00 AM
Action: Send morning signals

Edit the time by saying:
"Change morning update to 8:30am"
""",
            buttons=[[{"text": "⏸️ Pause", "callback_data": f"wf_pause_{workflow.id}"}]]
        )
    
    if template == "protect":
        # Position protection template
        workflow = engine.create_workflow(
            name="SOL Protection",
            description="Protect SOL position with automatic stop adjustment",
            owner_id=str(chat_id),
            triggers=[{
                "type": "price",
                "asset": "SOL",
                "condition": "< 118"
            }],
            actions=[
                {"alert": "SOL dropped below $118 - adjusting stop"},
                {"adjust_stop": {"asset": "SOL", "price": 115}},
                {
                    "if_price": {"asset": "SOL", "condition": "< 115"},
                    "then": [
                        {"close_position": {"asset": "SOL", "percent": 50}},
                        {"alert": "Closed 50% of SOL position"}
                    ]
                }
            ],
            cooldown_seconds=60,
        )
        store.save_workflow(workflow)
        
        return CommandResult(
            text=f"""✅ **Workflow Created!**

**{workflow.name}** (`{workflow.id}`)

Protection chain:
1. If SOL < $118 → Alert + tighten stop to $115
2. If SOL < $115 → Close 50% position

⚠️ Customize by describing:
"Change protection levels to $116 and $113"
""",
            buttons=[[{"text": "⏸️ Pause", "callback_data": f"wf_pause_{workflow.id}"}]]
        )
    
    return CommandResult(text=f"Unknown template: {template}")


async def parse_workflow_from_natural_language(chat_id: int, text: str) -> CommandResult:
    """
    Parse a workflow from natural language description.
    
    Examples:
    - "Alert me when SOL drops below $115"
    - "Every day at 9am send me signals"
    - "If BTC goes above 90k, close my position"
    """
    import re
    from sovereign.workflows import get_workflow_engine, get_workflow_store
    
    engine = get_workflow_engine()
    store = get_workflow_store()
    
    text_lower = text.lower()
    
    # Pattern: "alert when <asset> <condition>"
    price_pattern = r"alert.*when\s+(\w+)\s+(drops?\s+below|goes?\s+above|reaches?)\s+\$?([\d,.]+)"
    if match := re.search(price_pattern, text_lower):
        asset = match.group(1).upper()
        direction = match.group(2)
        price = float(match.group(3).replace(",", ""))
        
        condition = f"< {price}" if "below" in direction else f"> {price}"
        
        workflow = engine.create_workflow(
            name=f"{asset} Price Alert",
            description=text[:100],
            owner_id=str(chat_id),
            triggers=[{"type": "price", "asset": asset, "condition": condition}],
            actions=[{"alert": f"{asset} {direction.replace('drops', 'dropped').replace('goes', 'went')} ${price:,.0f}!"}],
            cooldown_seconds=300,
        )
        store.save_workflow(workflow)
        
        return CommandResult(
            text=f"""✅ **Workflow Created!**

**{workflow.name}** (`{workflow.id}`)
Trigger: {asset} {condition}
Action: Send alert

It's now active and monitoring!"""
        )
    
    # Pattern: "every <time> at <hour>" or "daily at <hour>"
    time_pattern = r"(?:every\s+day|daily)\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?"
    if match := re.search(time_pattern, text_lower):
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        period = match.group(3)
        
        if period == "pm" and hour < 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0
        
        schedule = f"at {hour:02d}:{minute:02d}"
        
        workflow = engine.create_workflow(
            name="Daily Update",
            description=text[:100],
            owner_id=str(chat_id),
            triggers=[{"type": "time", "schedule": schedule}],
            actions=[{"alert": "Time for your scheduled update!"}],
            cooldown_seconds=3600,
        )
        store.save_workflow(workflow)
        
        return CommandResult(
            text=f"""✅ **Workflow Created!**

**{workflow.name}** (`{workflow.id}`)
Trigger: {schedule}
Action: Send alert

It's now active!"""
        )
    
    return None  # Couldn't parse - let Opus brain handle it



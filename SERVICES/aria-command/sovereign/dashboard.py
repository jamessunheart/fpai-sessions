"""
Sovereign Dashboard - Real-time view of Aria's state and decisions.

Provides a comprehensive view of:
- Agent activity
- Confidence scores
- Opportunity queue
- Trust levels
- Outcome metrics
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

logger = logging.getLogger("aria.sovereign.dashboard")


router = APIRouter(prefix="/sovereign", tags=["sovereign"])


@dataclass
class DashboardState:
    """Current dashboard state."""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # System health
    overall_health: str = "healthy"
    
    # Agents
    agents: List[Dict[str, Any]] = field(default_factory=list)
    
    # Tasks
    pending_tasks: int = 0
    completed_today: int = 0
    
    # Confidence
    avg_confidence: float = 0.0
    auto_executed: int = 0
    
    # Trust
    trust_levels: Dict[str, float] = field(default_factory=dict)
    
    # Opportunities
    opportunities_queued: int = 0
    auto_fixable: int = 0
    
    # Learning
    learning_insights: List[str] = field(default_factory=list)


async def get_dashboard_state() -> DashboardState:
    """Gather current dashboard state from all systems."""
    state = DashboardState()
    
    # Get agent status
    try:
        from agents.orchestrator import get_orchestrator
        orch = get_orchestrator()
        agent_status = await orch.get_all_agent_status()
        state.agents = agent_status.get("agents", [])
        state.pending_tasks = agent_status.get("pending_tasks", 0)
        state.completed_today = agent_status.get("completed_tasks", 0)
    except Exception as e:
        logger.error(f"Failed to get agent status: {e}")
    
    # Get trust levels
    try:
        from core.trust import get_trust_levels
        trust = get_trust_levels()
        state.trust_levels = trust.get("levels", {})
    except Exception as e:
        logger.error(f"Failed to get trust levels: {e}")
    
    # Get opportunity queue
    try:
        from proactive.opportunity_queue import get_opportunity_queue
        queue = get_opportunity_queue()
        summary = queue.get_summary()
        state.opportunities_queued = summary.get("total_pending", 0)
        state.auto_fixable = summary.get("auto_executable", 0)
    except Exception as e:
        logger.error(f"Failed to get opportunity queue: {e}")
    
    # Get meta-learning insights
    try:
        from sovereign.meta_learning import get_meta_learning
        ml = get_meta_learning()
        status = ml.get_status()
        state.learning_insights = status.get("insights", [])[:5]
    except Exception as e:
        logger.error(f"Failed to get meta-learning status: {e}")
    
    # Determine overall health
    unhealthy_agents = sum(1 for a in state.agents if not a.get("is_active", True))
    if unhealthy_agents > 2:
        state.overall_health = "critical"
    elif unhealthy_agents > 0 or state.opportunities_queued > 50:
        state.overall_health = "warning"
    else:
        state.overall_health = "healthy"
    
    return state


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/dashboard")
async def get_dashboard() -> Dict[str, Any]:
    """Get dashboard state as JSON."""
    state = await get_dashboard_state()
    return {
        "timestamp": state.timestamp.isoformat(),
        "overall_health": state.overall_health,
        "agents": state.agents,
        "pending_tasks": state.pending_tasks,
        "completed_today": state.completed_today,
        "trust_levels": state.trust_levels,
        "opportunities_queued": state.opportunities_queued,
        "auto_fixable": state.auto_fixable,
        "learning_insights": state.learning_insights
    }


@router.get("/dashboard/html", response_class=HTMLResponse)
async def get_dashboard_html() -> str:
    """Get dashboard as rendered HTML."""
    state = await get_dashboard_state()
    
    # Generate HTML
    health_colors = {
        "healthy": "#3fb950",
        "warning": "#d29922",
        "critical": "#f85149"
    }
    health_color = health_colors.get(state.overall_health, "#8b949e")
    
    agents_html = ""
    for agent in state.agents:
        status = "active" if agent.get("is_active") else "inactive"
        color = "#3fb950" if agent.get("is_active") else "#f85149"
        agents_html += f"""
        <div class="agent-card">
            <div class="agent-name">{agent.get('name', 'Unknown')}</div>
            <div class="agent-specialty">{agent.get('specialty', 'unknown')}</div>
            <div class="agent-status" style="color: {color}">{status}</div>
            <div class="agent-stats">
                <span>Evaluations: {agent.get('total_evaluations', 0)}</span>
                <span>Success: {agent.get('success_rate', 1.0):.0%}</span>
            </div>
        </div>
        """
    
    trust_html = ""
    for domain, level in state.trust_levels.items():
        bar_width = level * 100
        trust_html += f"""
        <div class="trust-item">
            <span class="trust-domain">{domain}</span>
            <div class="trust-bar">
                <div class="trust-fill" style="width: {bar_width}%"></div>
            </div>
            <span class="trust-value">{level:.0%}</span>
        </div>
        """
    
    insights_html = ""
    for insight in state.learning_insights:
        insights_html += f'<li>{insight}</li>'
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aria Sovereign Dashboard</title>
    <style>
        :root {{
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --accent: #58a6ff;
            --success: #3fb950;
            --warning: #d29922;
            --danger: #f85149;
            --border: #30363d;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }}
        
        .title {{
            font-size: 24px;
            font-weight: 600;
            color: var(--accent);
        }}
        
        .health-badge {{
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 500;
            background: {health_color}22;
            color: {health_color};
            border: 1px solid {health_color};
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        
        .card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
        }}
        
        .card-title {{
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            color: var(--text-secondary);
            margin-bottom: 16px;
        }}
        
        .stat {{
            font-size: 32px;
            font-weight: 700;
            color: var(--accent);
        }}
        
        .stat-label {{
            font-size: 12px;
            color: var(--text-secondary);
        }}
        
        .agent-card {{
            background: var(--bg-tertiary);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 8px;
        }}
        
        .agent-name {{
            font-weight: 600;
            color: var(--text-primary);
        }}
        
        .agent-specialty {{
            font-size: 12px;
            color: var(--text-secondary);
        }}
        
        .agent-status {{
            font-size: 12px;
            font-weight: 500;
            margin-top: 4px;
        }}
        
        .agent-stats {{
            display: flex;
            gap: 12px;
            font-size: 11px;
            color: var(--text-secondary);
            margin-top: 8px;
        }}
        
        .trust-item {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }}
        
        .trust-domain {{
            width: 100px;
            font-size: 13px;
        }}
        
        .trust-bar {{
            flex: 1;
            height: 8px;
            background: var(--bg-tertiary);
            border-radius: 4px;
            overflow: hidden;
        }}
        
        .trust-fill {{
            height: 100%;
            background: var(--accent);
            border-radius: 4px;
        }}
        
        .trust-value {{
            width: 40px;
            text-align: right;
            font-size: 13px;
            color: var(--text-secondary);
        }}
        
        .insights-list {{
            list-style: none;
        }}
        
        .insights-list li {{
            padding: 8px 0;
            border-bottom: 1px solid var(--border);
            font-size: 13px;
        }}
        
        .insights-list li:last-child {{
            border-bottom: none;
        }}
        
        .refresh-btn {{
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
        }}
        
        .refresh-btn:hover {{
            background: var(--bg-secondary);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">Aria Sovereign Dashboard</h1>
            <div style="display: flex; gap: 12px; align-items: center;">
                <span class="health-badge">{state.overall_health.upper()}</span>
                <button class="refresh-btn" onclick="location.reload()">Refresh</button>
            </div>
        </div>
        
        <div class="grid">
            <!-- Stats -->
            <div class="card">
                <div class="card-title">Tasks</div>
                <div style="display: flex; gap: 24px;">
                    <div>
                        <div class="stat">{state.pending_tasks}</div>
                        <div class="stat-label">Pending</div>
                    </div>
                    <div>
                        <div class="stat">{state.completed_today}</div>
                        <div class="stat-label">Completed</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <div class="card-title">Opportunities</div>
                <div style="display: flex; gap: 24px;">
                    <div>
                        <div class="stat">{state.opportunities_queued}</div>
                        <div class="stat-label">Queued</div>
                    </div>
                    <div>
                        <div class="stat">{state.auto_fixable}</div>
                        <div class="stat-label">Auto-fixable</div>
                    </div>
                </div>
            </div>
            
            <!-- Agents -->
            <div class="card" style="grid-column: span 2;">
                <div class="card-title">Agents</div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">
                    {agents_html}
                </div>
            </div>
            
            <!-- Trust -->
            <div class="card">
                <div class="card-title">Trust Levels</div>
                {trust_html if trust_html else '<p style="color: var(--text-secondary);">No trust data</p>'}
            </div>
            
            <!-- Insights -->
            <div class="card">
                <div class="card-title">Learning Insights</div>
                <ul class="insights-list">
                    {insights_html if insights_html else '<li style="color: var(--text-secondary);">No insights yet</li>'}
                </ul>
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 24px; color: var(--text-secondary); font-size: 12px;">
            Last updated: {state.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
    
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
    """
    
    return html


@router.get("/agents")
async def get_agents_status() -> Dict[str, Any]:
    """Get detailed agent status."""
    try:
        from agents.orchestrator import get_orchestrator
        orch = get_orchestrator()
        return await orch.get_all_agent_status()
    except Exception as e:
        return {"error": str(e)}


@router.get("/opportunities")
async def get_opportunities() -> Dict[str, Any]:
    """Get opportunity queue status."""
    try:
        from proactive.opportunity_queue import get_opportunity_queue
        queue = get_opportunity_queue()
        return {
            "summary": queue.get_summary(),
            "top_opportunities": [
                {
                    "id": o.id,
                    "title": o.title,
                    "type": o.type.value,
                    "impact": o.impact.name,
                    "effort": o.effort.name,
                    "auto_executable": o.auto_executable
                }
                for o in queue.get_top(10)
            ]
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/learning")
async def get_learning_status() -> Dict[str, Any]:
    """Get meta-learning status."""
    try:
        from sovereign.meta_learning import get_meta_learning
        ml = get_meta_learning()
        return ml.get_status()
    except Exception as e:
        return {"error": str(e)}


@router.get("/self-modifications")
async def get_self_modifications() -> Dict[str, Any]:
    """Get self-modification status."""
    try:
        from sovereign.self_modify import get_self_modification_protocol
        protocol = get_self_modification_protocol()
        return {
            "pending": protocol.get_pending_requests(),
            "history": protocol.get_modification_history()
        }
    except Exception as e:
        return {"error": str(e)}



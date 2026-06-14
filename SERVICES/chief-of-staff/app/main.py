"""
Chief of Staff Service - Main FastAPI Application

Executive intelligence layer that filters noise and shows what matters.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from contextlib import asynccontextmanager
from datetime import datetime
import logging
import time
import uuid

from app.config import settings
from app.models import (
    Signal, SignalRequest, SignalResponse, SignalCategory, SignalAction,
    SystemStatus, UserFeedback, DailyDigest
)
from app.intelligence import SignalCategorizer, signal_storage, PatternDetector
from app.digest import DigestGenerator
from app.alerts_client import alerts_client
from app.catalog import build_priority_view
from app.ledger import build_money_view

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Track service start time
service_start_time = time.time()

# Initialize components
categorizer = SignalCategorizer()
digest_generator = DigestGenerator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Chief of Staff Service...")

    # Test alerts service connection
    alerts_ok = await alerts_client.test_connection()
    if not alerts_ok:
        logger.warning("Alerts service not reachable - notifications disabled")

    logger.info("Chief of Staff Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Chief of Staff Service...")
    logger.info("Chief of Staff Service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Chief of Staff Service",
    description="Executive intelligence layer - filters noise, shows what matters",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# UDC ENDPOINTS
# ============================================================================

@app.get("/health", tags=["UDC"])
async def health_check():
    """UDC Health Check"""
    uptime_seconds = int(time.time() - service_start_time)

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": uptime_seconds,
        "version": settings.APP_VERSION
    }


@app.get("/capabilities", tags=["UDC"])
async def capabilities():
    """UDC Capabilities"""
    return {
        "service_name": settings.SERVICE_NAME,
        "droplet_id": settings.DROPLET_ID,
        "capabilities": [
            "signal_processing",
            "decision_filtering",
            "urgency_categorization",
            "pattern_detection",
            "automation_suggestions",
            "daily_digest",
            "executive_summary",
        ]
    }


@app.get("/state", tags=["UDC"])
async def state():
    """UDC State"""
    stats = await signal_storage.get_stats()
    urgent = await signal_storage.get_urgent()
    important = await signal_storage.get_important(hours=24)

    return {
        "status": "active",
        "urgent": len(urgent),
        "important": len(important),
        "total_signals": stats["total_signals"],
        "last_update": stats["newest"]
    }


@app.get("/dependencies", tags=["UDC"])
async def dependencies():
    """UDC Dependencies"""
    return {
        "required_services": [
            {
                "name": "Alerts Service",
                "url": settings.ALERTS_SERVICE_URL,
                "purpose": "Notification delivery"
            }
        ],
        "optional_services": []
    }


# ============================================================================
# SIGNAL PROCESSING
# ============================================================================

@app.post("/signal", tags=["Signals"], response_model=SignalResponse)
async def process_signal(request: SignalRequest):
    """
    Process a signal from any source

    Applies decision filter and categorizes by urgency
    """
    try:
        # Categorize signal
        category, action = categorizer.categorize(request)

        # Create signal object
        signal_id = str(uuid.uuid4())
        signal = Signal(
            signal_id=signal_id,
            source=request.source,
            type=request.type,
            category=category,
            title=request.title,
            description=request.description,
            data=request.data,
            decision_filter_passed=(category != SignalCategory.CONTEXT),
            action_taken=action
        )

        # Store signal
        await signal_storage.store(signal)

        # Take action based on category
        if action == SignalAction.ALERT:
            # Send urgent alert via Telegram
            await alerts_client.send_urgent_alert(signal)
            message = "Urgent alert sent"
        elif action == SignalAction.DIGEST:
            message = "Added to daily digest"
        else:
            message = "Logged for tracking"

        logger.info(
            f"Processed signal {signal_id}: {category.value} -> {action.value}"
        )

        return SignalResponse(
            signal_id=signal_id,
            category=category,
            action=action,
            message=message
        )

    except Exception as e:
        logger.error(f"Error processing signal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback", tags=["Signals"])
async def submit_feedback(feedback: UserFeedback):
    """
    Submit feedback on how you responded to a signal

    Helps the system learn what you care about
    """
    success = await signal_storage.update_user_response(
        feedback.signal_id,
        feedback.action_taken
    )

    if not success:
        raise HTTPException(status_code=404, detail="Signal not found")

    return {
        "message": "Feedback recorded",
        "learned": True
    }


# ============================================================================
# STATUS & VISIBILITY
# ============================================================================

@app.get("/status", tags=["Status"])
async def get_status():
    """Get big picture system status"""
    urgent = await signal_storage.get_urgent()
    important = await signal_storage.get_important(hours=24)
    auto_handled = await signal_storage.get_auto_handled(hours=24)
    stats = await signal_storage.get_stats()

    return SystemStatus(
        urgent_count=len(urgent),
        important_count=len(important),
        auto_handled_count=len(auto_handled),
        active_issues=[s for s in urgent if not s.user_response],
        recent_automations=[s.title for s in auto_handled[:5]],
        key_metrics=stats
    )


@app.get("/urgent", tags=["Status"])
async def get_urgent():
    """Get current urgent items"""
    urgent = await signal_storage.get_urgent()
    return {
        "count": len(urgent),
        "items": [s.model_dump() for s in urgent]
    }


@app.get("/digest", tags=["Reports"], response_model=DailyDigest)
async def get_digest():
    """Get daily digest"""
    return await digest_generator.generate_daily_digest()


@app.post("/digest/send", tags=["Reports"])
async def send_digest():
    """Generate and send daily digest via Telegram"""
    digest = await digest_generator.generate_daily_digest()
    message = digest_generator.format_for_telegram(digest)

    success = await alerts_client.send_digest(message)

    if success:
        return {"message": "Digest sent", "sent_at": datetime.utcnow()}
    else:
        raise HTTPException(status_code=500, detail="Failed to send digest")


@app.get("/summary", tags=["Reports"])
async def get_summary():
    """Get weekly executive summary"""
    summary = await digest_generator.generate_weekly_summary()
    return {"summary": summary}


@app.get("/automation-suggestions", tags=["Intelligence"])
async def get_automation_suggestions():
    """Get automation opportunity suggestions"""
    all_signals = list(signal_storage.signal_history)
    pattern_detector = PatternDetector(all_signals)
    suggestions = pattern_detector.detect_automation_opportunities()

    return {
        "count": len(suggestions),
        "suggestions": [s.model_dump() for s in suggestions[:10]]
    }


# ============================================================================
# PRIORITY + MONEY VIEWS
# ============================================================================

@app.get("/priority", tags=["Views"])
async def priority_view():
    """Cross-system Priority view — services tagged by engine alignment"""
    return build_priority_view()


@app.get("/money", tags=["Views"])
async def money_view():
    """Cross-system Money view — costs, revenue, biggest leak"""
    return build_money_view()


# ============================================================================
# DASHBOARD
# ============================================================================

@app.get("/dashboard", tags=["Dashboard"], response_class=HTMLResponse)
async def dashboard():
    """
    Integrated dashboard — three views:
      1. Priority — where resources should go
      2. Money — costs, revenue, leaks
      3. Attention — what needs you now
    """
    priority = build_priority_view()
    money = build_money_view()
    status = await get_status()

    return _render_dashboard(priority, money, status)


def _render_dashboard(priority, money, status) -> str:
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    return f"""<!DOCTYPE html>
<html><head>
<title>Chief of Staff</title>
<meta http-equiv="refresh" content="60">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
         margin: 0; background: #f5f5f7; color: #1d1d1f; }}
  .wrap {{ max-width: 1200px; margin: 0 auto; padding: 32px; }}
  h1 {{ margin: 0 0 4px 0; }}
  .ts {{ color: #86868b; font-size: 0.85em; margin-bottom: 24px; }}
  .tabs {{ display: flex; gap: 4px; border-bottom: 1px solid #d2d2d7; margin-bottom: 0; }}
  .tab {{ padding: 10px 18px; cursor: pointer; border: none; background: transparent;
         font-size: 15px; color: #6e6e73; border-bottom: 2px solid transparent; }}
  .tab.active {{ color: #1d1d1f; border-bottom-color: #007aff; font-weight: 600; }}
  .panel {{ display: none; background: white; padding: 24px; border-radius: 0 0 10px 10px;
           box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  .panel.active {{ display: block; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }}
  .stat {{ background: #f5f5f7; padding: 16px; border-radius: 8px; }}
  .stat-label {{ color: #6e6e73; font-size: 0.85em; }}
  .stat-value {{ font-size: 28px; font-weight: 600; margin-top: 4px; }}
  .role-P1 {{ color: #34c759; font-weight: 600; }}
  .role-P2 {{ color: #007aff; font-weight: 600; }}
  .role-infra {{ color: #6e6e73; }}
  .role-cruft {{ color: #ff3b30; }}
  .role-unknown {{ color: #ff9500; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #f0f0f0; }}
  th {{ color: #6e6e73; font-weight: 500; font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.04em; }}
  .kill {{ background: #fff5f5; }}
  .leak {{ background: #fffbe6; padding: 12px; border-radius: 8px; margin-bottom: 16px; }}
  .signal {{ padding: 12px; margin: 8px 0; border-left: 3px solid #ff3b30; background: #fff5f5; border-radius: 4px; }}
  .small {{ color: #86868b; font-size: 0.85em; }}
  .right {{ text-align: right; }}
  .filter {{ font-style: italic; color: #6e6e73; margin-bottom: 16px; padding: 12px;
             background: #f5f5f7; border-radius: 6px; }}
</style>
<script>
  function showTab(name) {{
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    document.getElementById('panel-' + name).classList.add('active');
  }}
</script>
</head><body>
<div class="wrap">
  <h1>Chief of Staff</h1>
  <div class="ts">Last updated: {now} UTC · Decision filter: proof / revenue / clarity / ease in 30 days</div>
  <div class="tabs">
    <button id="tab-priority" class="tab active" onclick="showTab('priority')">Priority</button>
    <button id="tab-money" class="tab" onclick="showTab('money')">Money</button>
    <button id="tab-attention" class="tab" onclick="showTab('attention')">Attention</button>
  </div>
  <div id="panel-priority" class="panel active">{_render_priority_panel(priority)}</div>
  <div id="panel-money" class="panel">{_render_money_panel(money)}</div>
  <div id="panel-attention" class="panel">{_render_attention_panel(status)}</div>
</div>
</body></html>"""


def _render_priority_panel(priority) -> str:
    by_role = priority.by_role
    stats = "".join(
        f'<div class="stat"><div class="stat-label">{role}</div>'
        f'<div class="stat-value role-{role}">{by_role.get(role, 0)}</div></div>'
        for role in ("P1", "P2", "infra", "unknown", "cruft")
    )
    rows = []
    for s in priority.services:
        last = s.last_touched.strftime("%Y-%m-%d") if s.last_touched else "—"
        cost = f"${s.monthly_usd:.0f}/mo" if s.monthly_usd else ""
        purpose = (s.purpose or "")[:80]
        rows.append(
            f'<tr><td><span class="role-{s.engine_role.value}">{s.engine_role.value}</span></td>'
            f'<td><strong>{s.name}</strong></td>'
            f'<td class="small">{purpose}</td>'
            f'<td class="small">{last}</td>'
            f'<td class="right small">{cost}</td></tr>'
        )
    table = (
        '<table><thead><tr><th>Role</th><th>Service</th><th>Purpose</th>'
        '<th>Last touched</th><th class="right">Cost</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )
    return (
        f'<div class="filter">{priority.decision_filter}</div>'
        f'<div class="grid">{stats}</div>'
        f'<p class="small"><strong>{priority.total_services}</strong> services in <code>SERVICES/</code>. '
        f'Tagged via <code>core/STATE/catalog.json</code>. <strong>unknown</strong> = needs a decision.</p>'
        f'{table}'
    )


def _render_money_panel(money) -> str:
    leak_html = ""
    if money.biggest_leak:
        b = money.biggest_leak
        kill = " · <strong>kill candidate</strong>" if b.kill_candidate else ""
        leak_html = (
            f'<div class="leak"><strong>Biggest leak:</strong> {b.name} · '
            f'${b.monthly_usd:.0f}/mo · <span class="role-{b.engine_role.value}">{b.engine_role.value}</span>{kill}<br>'
            f'<span class="small">{b.purpose}</span></div>'
        )
    stats = (
        f'<div class="stat"><div class="stat-label">Total cost / mo</div>'
        f'<div class="stat-value">${money.total_cost_monthly_usd:,.0f}</div></div>'
        f'<div class="stat"><div class="stat-label">Total revenue / mo</div>'
        f'<div class="stat-value">${money.total_revenue_monthly_usd:,.0f}</div></div>'
        f'<div class="stat"><div class="stat-label">Net / mo</div>'
        f'<div class="stat-value" style="color:{"#34c759" if money.net_monthly_usd >= 0 else "#ff3b30"}">'
        f'${money.net_monthly_usd:,.0f}</div></div>'
    )
    role_rows = "".join(
        f'<tr><td><span class="role-{role}">{role}</span></td>'
        f'<td class="right">${amt:,.0f}/mo</td></tr>'
        for role, amt in sorted(money.cost_by_engine_role.items(), key=lambda kv: -kv[1])
    )
    cost_rows = []
    for c in money.costs:
        kill_cls = "kill" if c.kill_candidate else ""
        cost_rows.append(
            f'<tr class="{kill_cls}"><td><span class="role-{c.engine_role.value}">{c.engine_role.value}</span></td>'
            f'<td><strong>{c.name}</strong></td>'
            f'<td class="small">{c.category}</td>'
            f'<td class="small">{c.purpose}</td>'
            f'<td class="right">${c.monthly_usd:,.0f}</td></tr>'
        )
    cost_table = (
        '<h3>Costs</h3><table><thead><tr><th>Role</th><th>Item</th><th>Type</th>'
        '<th>Purpose</th><th class="right">$/mo</th></tr></thead>'
        f'<tbody>{"".join(cost_rows)}</tbody></table>'
    )
    rev_rows = []
    for r in money.revenue:
        details = []
        if r.inquiries is not None:
            details.append(f"{r.inquiries} inquiries")
        if r.bookings_confirmed is not None:
            details.append(f"{r.bookings_confirmed} bookings")
        if r.active_tenants is not None:
            details.append(f"{r.active_tenants} tenants")
        rev_rows.append(
            f'<tr><td><strong>{r.stream}</strong></td>'
            f'<td class="small">{" · ".join(details) or "—"}</td>'
            f'<td class="small">{r.note or ""}</td>'
            f'<td class="right">${r.revenue_usd:,.0f}</td></tr>'
        )
    rev_table = (
        '<h3>Revenue</h3><table><thead><tr><th>Stream</th><th>Activity</th>'
        '<th>Note</th><th class="right">$/mo</th></tr></thead>'
        f'<tbody>{"".join(rev_rows) or "<tr><td colspan=4 class=small>No revenue streams configured.</td></tr>"}</tbody></table>'
    )
    return (
        f'<div class="grid">{stats}</div>'
        f'{leak_html}'
        f'<h3>Cost by engine role</h3><table><tbody>{role_rows}</tbody></table>'
        f'{cost_table}{rev_table}'
        f'<p class="small">Source: <code>core/STATE/ledger.json</code></p>'
    )


def _render_attention_panel(status) -> str:
    stats = (
        f'<div class="stat"><div class="stat-label">Urgent</div>'
        f'<div class="stat-value role-cruft">{status.urgent_count}</div></div>'
        f'<div class="stat"><div class="stat-label">Important</div>'
        f'<div class="stat-value role-unknown">{status.important_count}</div></div>'
        f'<div class="stat"><div class="stat-label">Auto-handled</div>'
        f'<div class="stat-value role-P1">{status.auto_handled_count}</div></div>'
    )
    if status.active_issues:
        urgent_html = "".join(
            f'<div class="signal"><strong>{s.title}</strong>'
            f'<p>{s.description}</p>'
            f'<p class="small">Source: {s.source} · {s.timestamp.strftime("%Y-%m-%d %H:%M")}</p></div>'
            for s in status.active_issues
        )
    else:
        urgent_html = '<p class="small">No urgent issues.</p>'
    auto_html = "".join(f"<li>{item}</li>" for item in status.recent_automations) or '<li class="small">None recently.</li>'
    return (
        f'<div class="grid">{stats}</div>'
        f'<h3>Active urgent</h3>{urgent_html}'
        f'<h3>Recent auto-handled</h3><ul>{auto_html}</ul>'
    )


# ============================================================================
# DAILY DIGEST
# ============================================================================

@app.get("/digest/generate", tags=["Digest"])
async def generate_digest():
    """
    Generate daily digest (aggregates signals + revenue + system health)

    Returns formatted Markdown suitable for Telegram delivery
    """
    try:
        digest = await digest_generator.generate_daily_digest()
        formatted = digest_generator.format_for_telegram(digest)

        return {
            "digest": digest.dict(),
            "formatted": formatted,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating digest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/digest/deliver", tags=["Digest"])
async def deliver_digest():
    """
    Generate and deliver daily digest to Telegram

    This is the endpoint that should be called by cron daily at 9am
    """
    try:
        # Generate digest
        digest = await digest_generator.generate_daily_digest()
        formatted = digest_generator.format_for_telegram(digest)

        # Send via alerts service to Telegram
        success = await alerts_client._send_telegram(formatted)

        if success:
            logger.info("Daily digest delivered successfully")
            return {
                "success": True,
                "message": "Digest delivered to Telegram",
                "delivered_at": datetime.utcnow().isoformat()
            }
        else:
            logger.error("Failed to deliver digest")
            raise HTTPException(status_code=500, detail="Failed to deliver digest")

    except Exception as e:
        logger.error(f"Error delivering digest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ROOT
# ============================================================================

@app.get("/", tags=["System"])
async def root():
    """Service info"""
    return {
        "service": "Chief of Staff",
        "version": settings.APP_VERSION,
        "droplet_id": settings.DROPLET_ID,
        "purpose": "Executive intelligence - filter noise, show what matters",
        "docs": "/docs",
        "dashboard": "/dashboard",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )

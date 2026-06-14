#!/usr/bin/env python3
"""
ARIA COMMAND CENTER
====================

Beyond-Cursor development environment.
Mobile-first, voice-enabled, proactive, trading-aware.
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict

# Load environment variables FIRST before other imports
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("aria.command")

# Environment
SUNHEART_CHAT_ID = os.getenv("SUNHEART_CHAT_ID", "")


# ============================================================================
# LIFECYCLE
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle."""
    logger.info("=" * 50)
    logger.info("  ARIA COMMAND CENTER STARTING")
    logger.info("=" * 50)
    
    # Initialize components
    from telegram.bot import AriaTelegramBot
    from proactive.monitors import MonitoringDaemon
    from core.scheduler import AriaScheduler, ReliableService
    from agents.registry import AgentRegistry
    
    # Import evolution system
    try:
        from sovereign.evolution import get_evolution_daemon, start_evolution_daemon
        EVOLUTION_AVAILABLE = True
    except ImportError as e:
        logger.warning(f"Evolution system not available: {e}")
        EVOLUTION_AVAILABLE = False
    
    # Create instances
    app.state.telegram = AriaTelegramBot()
    app.state.monitor = MonitoringDaemon(check_interval=60)
    app.state.scheduler = AriaScheduler()
    app.state.registry = AgentRegistry()
    app.state.evolution_enabled = EVOLUTION_AVAILABLE
    
    # Load apprentices from Supabase
    try:
        from access.authority import load_apprentices_from_supabase
        num_apprentices = load_apprentices_from_supabase()
        logger.info(f"📚 Authority: Loaded {num_apprentices} apprentices from Supabase")
    except Exception as e:
        logger.warning(f"Could not load apprentices from Supabase: {e}")
    
    # Load community modules
    try:
        from modules.loader import get_module_loader
        loader = get_module_loader()
        results = loader.load_all()
        loaded_count = sum(1 for v in results.values() if v)
        logger.info(f"📦 Modules: Loaded {loaded_count}/{len(results)} community modules")
        app.state.module_loader = loader
    except Exception as e:
        logger.warning(f"Could not load modules: {e}")
        app.state.module_loader = None
    
    # Register scheduler callbacks
    _register_scheduler_callbacks(app.state.scheduler)
    
    # Start background tasks
    app.state.background_tasks = []
    
    # Start monitoring
    monitor_service = ReliableService("Monitor")
    task = asyncio.create_task(
        monitor_service.run_with_restart(
            lambda: app.state.monitor.start(alert_callback=_handle_alert)
        )
    )
    app.state.background_tasks.append(task)
    
    # Start scheduler
    scheduler_service = ReliableService("Scheduler")
    task = asyncio.create_task(
        scheduler_service.run_with_restart(
            app.state.scheduler.run_scheduler_loop
        )
    )
    app.state.background_tasks.append(task)
    
    # Start evolution daemon
    if EVOLUTION_AVAILABLE:
        evolution_service = ReliableService("Evolution")
        task = asyncio.create_task(
            evolution_service.run_with_restart(start_evolution_daemon)
        )
        app.state.background_tasks.append(task)
        logger.info("🧬 Evolution daemon started")
    
    # Start consciousness daemon
    try:
        from consciousness import start_consciousness_daemon
        consciousness_service = ReliableService("Consciousness")
        task = asyncio.create_task(
            consciousness_service.run_with_restart(start_consciousness_daemon)
        )
        app.state.background_tasks.append(task)
        logger.info("🧠 Consciousness daemon started")
    except ImportError as e:
        logger.warning(f"Consciousness system not available: {e}")
    
    # Start trading signal monitor
    try:
        from trading import start_signal_monitoring
        trading_service = ReliableService("TradingSignals")
        task = asyncio.create_task(
            trading_service.run_with_restart(start_signal_monitoring)
        )
        app.state.background_tasks.append(task)
        logger.info("📊 Trading signal monitor started")
    except ImportError as e:
        logger.warning(f"Trading module not available: {e}")
    except Exception as e:
        logger.warning(f"Could not start trading signal monitor: {e}")
    
    logger.info("✅ All systems initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Aria Command Center...")
    
    for task in app.state.background_tasks:
        task.cancel()
    
    await app.state.telegram.close()
    await app.state.registry.close()


def _register_scheduler_callbacks(scheduler):
    """Register callbacks for scheduled tasks."""
    from proactive.digest import generate_and_send_digest
    from proactive.monitors import get_monitor
    from agents.registry import get_registry
    
    async def send_morning_brief():
        if SUNHEART_CHAT_ID:
            await generate_and_send_digest(int(SUNHEART_CHAT_ID), voice=True)
    
    async def send_eod_summary():
        if SUNHEART_CHAT_ID:
            from telegram.bot import send_to_sunheart
            await send_to_sunheart("End of day. What shipped? What did we learn?")
    
    async def run_health_check():
        monitor = get_monitor()
        await monitor.check_all()
    
    async def agent_heartbeat():
        registry = get_registry()
        await registry.check_all_agents()
    
    async def process_message_queue():
        await scheduler.process_queue()
    
    async def check_costs():
        # Cost checking placeholder
        pass
    
    scheduler.register_callback("send_morning_brief", send_morning_brief)
    scheduler.register_callback("send_eod_summary", send_eod_summary)
    scheduler.register_callback("run_health_check", run_health_check)
    scheduler.register_callback("agent_heartbeat", agent_heartbeat)
    scheduler.register_callback("process_message_queue", process_message_queue)
    scheduler.register_callback("check_costs", check_costs)


async def _handle_alert(alert):
    """Handle monitoring alert."""
    if SUNHEART_CHAT_ID:
        from telegram.bot import send_message
        await send_message(int(SUNHEART_CHAT_ID), alert.format_telegram())


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Aria Command Center",
    description="Beyond-Cursor development environment",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "aria-command"}


@app.post("/api/smoke-test")
async def smoke_test(request: Request):
    """
    Smoke test endpoint for deploy verification.
    Actually tests the AI brain can respond.
    """
    try:
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        test_message = data.get("message", "ping")
        
        # Quick test of the AI brain
        from brain.opus_router import OpusRouter
        
        router = OpusRouter()
        
        # Use the fastest model for smoke test
        response = await router.call(
            messages=[{"role": "user", "content": test_message}],
            model_override="flash",  # Use Gemini flash for speed
            max_tokens=10
        )
        
        if response and response.content:
            return {
                "status": "ok",
                "response": response.content[:100],
                "model": response.model,
                "latency_ms": getattr(response, 'latency_ms', None)
            }
        else:
            return {"status": "degraded", "error": "Empty response from AI"}
            
    except Exception as e:
        logger.error(f"Smoke test failed: {e}")
        return {"status": "failed", "error": str(e)}


@app.get("/status")
async def get_status(request: Request):
    """Get full system status."""
    from proactive.monitors import quick_health_check
    from agents.registry import get_agent_status
    from core.scheduler import get_scheduler_status
    
    return {
        "services": await quick_health_check(),
        "agents": get_agent_status(),
        "scheduler": get_scheduler_status()
    }


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Telegram webhook endpoint."""
    try:
        update = await request.json()
        
        # Check builder callbacks FIRST (approve/deny buttons)
        try:
            from builder.telegram_interface import handle_builder_update
            from access.authority import get_user_authority
            
            # Determine scope from user
            user_id = None
            if "callback_query" in update:
                user_id = update["callback_query"].get("from", {}).get("id")
            elif "message" in update:
                user_id = update["message"].get("from", {}).get("id")
            
            scope = "apprentice"
            if user_id:
                authority = get_user_authority(user_id)
                scope = "steward" if authority == "steward" else "apprentice"
            
            builder_result = await handle_builder_update(update, scope)
            if builder_result:
                # Builder handled this update
                return {"ok": True, "handled": True, "handler": "builder"}
        except ImportError as e:
            logger.debug(f"Builder interface not available: {e}")
        except Exception as e:
            logger.warning(f"Builder handler error: {e}")
        
        # Fall through to regular handler
        handled = await request.app.state.telegram.handle_update(update)
        return {"ok": True, "handled": handled}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"ok": False, "error": str(e)}


# ========== AUTHORITY RECOVERY ==========

@app.post("/api/authority/recover")
async def authority_recover(request: Request):
    """
    EMERGENCY: Add steward access using recovery secret.
    
    Use if you lose access to your primary Telegram account.
    
    Body: {"secret": "your-recovery-secret", "user_id": 123456789}
    """
    try:
        from access.authority import emergency_add_steward
        data = await request.json()
        
        secret = data.get("secret", "")
        user_id = int(data.get("user_id", 0))
        
        if not user_id:
            return {"success": False, "error": "user_id required"}
        
        success, message = emergency_add_steward(user_id, secret)
        return {"success": success, "message": message}
    except Exception as e:
        logger.error(f"Recovery error: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/authority/status")
async def authority_status():
    """Get current authority configuration (steward only via localhost)."""
    try:
        from access.authority import list_stewards, list_apprentices
        return {
            "stewards": list_stewards(),
            "apprentices": list_apprentices(),
            "note": "Use /api/authority/recover to add emergency steward"
        }
    except Exception as e:
        return {"error": str(e)}


# ========== FILE OPERATIONS ==========

@app.get("/files/read")
async def read_file(path: str, max_lines: int = None):
    """Read a file."""
    from access.filesystem import read_file
    result = await read_file(path, max_lines)
    return result.__dict__


@app.post("/files/write")
async def write_file(request: Request):
    """Write to a file."""
    data = await request.json()
    from access.filesystem import write_file
    result = await write_file(data["path"], data["content"])
    return result.__dict__


@app.get("/files/search")
async def search_files(pattern: str, file_pattern: str = "*.py"):
    """Search for pattern in files."""
    from access.filesystem import search_code
    return await search_code(pattern, file_pattern)


# ========== TERMINAL OPERATIONS ==========

@app.post("/terminal/run")
async def run_terminal(request: Request):
    """Run a terminal command."""
    data = await request.json()
    from access.terminal import run_command
    result = await run_command(data["command"], data.get("server", "secondary"))
    return result.__dict__


@app.get("/terminal/pending")
async def get_pending_commands():
    """Get pending commands awaiting approval."""
    from access.terminal import get_executor
    executor = get_executor()
    return {"pending": [p.__dict__ for p in executor.get_pending()]}


@app.post("/terminal/approve/{approval_id}")
async def approve_command(approval_id: str, confirm_count: int = 1):
    """Approve a pending command."""
    from access.terminal import get_executor
    executor = get_executor()
    result = await executor.approve_and_execute(approval_id, confirm_count)
    return result.__dict__


# ========== GIT OPERATIONS ==========

@app.get("/git/status")
async def git_status():
    """Get git status."""
    from access.git_ops import git_status
    result = await git_status()
    return {"success": result.success, "output": result.output, "error": result.error}


@app.post("/git/commit")
async def git_commit(request: Request):
    """Create a commit."""
    data = await request.json()
    from access.git_ops import git_commit
    result = await git_commit(data["message"], data.get("add_all", True))
    return {"success": result.success, "output": result.output, "error": result.error}


@app.post("/git/push")
async def git_push(branch: str = None):
    """Push to remote."""
    from access.git_ops import git_push
    result = await git_push(branch)
    return {"success": result.success, "output": result.output, "error": result.error}


# ========== TRADING ==========

@app.get("/trading/positions")
async def get_positions():
    """Get open positions."""
    from trading.awareness import get_positions
    return {"summary": await get_positions()}


@app.get("/trading/signals")
async def get_signals():
    """Get active signals."""
    from trading.awareness import get_signals
    return {"summary": await get_signals()}


@app.get("/trading/market")
async def get_market():
    """Get market context."""
    from trading.awareness import get_market
    return {"summary": await get_market()}


@app.post("/trading/check-safety")
async def check_safety(request: Request):
    """Check if operation is trading-safe."""
    data = await request.json()
    from trading.awareness import check_trading_safety
    return await check_trading_safety(data["operation"])


@app.get("/trading/analytics")
async def get_trading_analytics(days: int = 30):
    """Get comprehensive trading analytics."""
    from trading import get_analytics
    analytics = get_analytics()
    metrics = analytics.get_performance(days=days)
    return {
        "period_days": days,
        "total_trades": metrics.total_trades,
        "win_rate": metrics.win_rate,
        "total_pnl": metrics.total_pnl,
        "profit_factor": metrics.profit_factor,
        "sharpe_ratio": metrics.sharpe_ratio,
        "max_drawdown": metrics.max_drawdown,
        "max_drawdown_percent": metrics.max_drawdown_percent,
        "best_symbol": metrics.best_symbol,
        "best_strategy": metrics.best_strategy,
        "current_streak": metrics.current_streak
    }


@app.get("/trading/analytics/report")
async def get_analytics_report(days: int = 30):
    """Get formatted analytics report."""
    from trading import get_analytics
    analytics = get_analytics()
    return {"report": analytics.format_performance_report(days=days)}


@app.get("/trading/analytics/patterns")
async def get_trading_patterns():
    """Get trading pattern analysis."""
    from trading import get_analytics
    analytics = get_analytics()
    return {"patterns": analytics.analyze_patterns()}


@app.get("/trading/analytics/equity")
async def get_equity_curve(days: int = 30):
    """Get equity curve data."""
    from trading import get_analytics
    analytics = get_analytics()
    return {"equity_curve": analytics.get_equity_curve(days=days)}


@app.get("/trading/journal/insights")
async def get_journal_insights():
    """Get coaching insights from journal."""
    from trading import get_journal
    journal = get_journal()
    return {"insights": journal.get_coaching_insights()}


@app.get("/trading/journal/lessons")
async def get_journal_lessons(category: str = None, limit: int = 10):
    """Get lessons learned from trading."""
    from trading import get_journal
    journal = get_journal()
    return {"lessons": journal.get_lessons(category=category, limit=limit)}


@app.get("/trading/journal/rules")
async def get_trading_rules():
    """Get trading rules."""
    from trading import get_journal
    journal = get_journal()
    return {"rules": journal.get_trading_rules()}


@app.post("/trading/journal/rules")
async def add_trading_rule(request: Request):
    """Add a trading rule."""
    data = await request.json()
    from trading import get_journal
    journal = get_journal()
    journal.add_trading_rule(data["rule"], data.get("category", "general"))
    return {"success": True, "rule": data["rule"]}


@app.get("/trading/strategies")
async def get_strategies():
    """Get available trading strategies."""
    from trading import get_optimizer
    optimizer = get_optimizer()
    strategies = optimizer.get_strategies()
    return {
        "strategies": {
            name: {
                "name": config.name,
                "min_confidence": config.min_confidence,
                "leverage": config.leverage,
                "position_size_pct": config.position_size_pct,
                "symbols": config.symbols
            }
            for name, config in strategies.items()
        }
    }


@app.get("/trading/strategies/compare")
async def compare_strategies(days: int = 30):
    """Compare all strategies."""
    from trading import get_optimizer
    optimizer = get_optimizer()
    comparison = await optimizer.compare_strategies(days=days)
    return {"comparison": comparison}


@app.get("/trading/strategies/recommend")
async def recommend_strategy():
    """Get strategy recommendation."""
    from trading import get_optimizer
    optimizer = get_optimizer()
    recommendation = await optimizer.recommend_strategy()
    return recommendation


@app.post("/trading/strategies/optimize")
async def optimize_strategy(request: Request):
    """Optimize strategy parameters."""
    data = await request.json()
    from trading import get_optimizer, get_analytics
    
    optimizer = get_optimizer()
    analytics = get_analytics()
    
    trades = analytics.get_trades(days=30, limit=100)
    trade_dicts = [
        {"symbol": t.symbol, "pnl": t.pnl, "confidence": t.confidence, "strategy": t.strategy}
        for t in trades
    ]
    
    result = optimizer.optimize_parameters(
        data.get("strategy", "signal-shark"),
        trade_dicts
    )
    return result


# ========== AUTO-TRADING ==========

@app.get("/trading/auto/status")
async def get_auto_trading_status():
    """Get auto-trading status and performance."""
    from trading.auto_trader import get_auto_trader
    trader = get_auto_trader()
    return trader.status

@app.post("/trading/auto/start")
async def start_auto_trading(request: Request):
    """Start auto-trading with aggressive configuration."""
    data = await request.json() if request else {}
    from trading.auto_trader import start_auto_trading
    
    result = await start_auto_trading(
        max_position=data.get("max_position", 500.0),
        min_confidence=data.get("min_confidence", 80.0),
        symbols=data.get("symbols", ["SOL", "BTC", "ETH"])
    )
    return result

@app.post("/trading/auto/stop")
async def stop_auto_trading_endpoint():
    """Stop auto-trading."""
    from trading.auto_trader import stop_auto_trading
    result = await stop_auto_trading()
    return result

@app.post("/trading/auto/emergency-stop")
async def emergency_stop_endpoint():
    """Emergency stop - close all positions and stop trading."""
    from trading.auto_trader import emergency_stop
    result = await emergency_stop()
    return result

@app.get("/trading/auto/performance")
async def get_auto_trading_performance():
    """Get auto-trading performance report."""
    from trading.auto_trader import get_auto_trader
    trader = get_auto_trader()
    return {
        "report": trader.get_performance_report(),
        "win_rate": trader.win_rate,
        "total_trades": trader._total_trades,
        "total_pnl": trader._total_pnl,
        "daily_pnl": trader._daily_pnl,
        "consecutive_losses": trader._consecutive_losses,
        "trade_history": trader._trade_history[-10:]  # Last 10 trades
    }

@app.post("/trading/auto/daily-summary")
async def send_daily_summary():
    """Manually trigger daily summary notification."""
    from trading.auto_trader import get_auto_trader
    trader = get_auto_trader()
    await trader.send_daily_summary()
    return {"success": True}


# ========== AGENTS ==========

@app.get("/agents")
async def get_agents():
    """Get all agents."""
    from agents.registry import get_agent_status
    return get_agent_status()


@app.post("/agents/message")
async def send_agent_message(request: Request):
    """Send message to an agent."""
    data = await request.json()
    from agents.registry import send_to_agent
    msg = send_to_agent(data["to"], data["type"], data["payload"])
    return {"message_id": msg.id}


# ========== PROACTIVE ==========

@app.get("/proactive/suggestions")
async def get_suggestions():
    """Get proactive suggestions."""
    from proactive.suggestions import get_top_suggestions
    suggestions = get_top_suggestions()
    return {"suggestions": [s.__dict__ for s in suggestions]}


@app.get("/proactive/brief")
async def get_brief():
    """Get quick brief."""
    from proactive.digest import get_quick_brief
    return {"brief": await get_quick_brief()}


@app.post("/proactive/alert")
async def send_alert(request: Request):
    """Send proactive alert."""
    data = await request.json()
    from telegram.bot import send_to_sunheart
    success = await send_to_sunheart(data["message"], voice=data.get("voice", False))
    return {"success": success}


# ========== MINI APP IDE ==========

from miniapp.api import router as miniapp_router
app.include_router(miniapp_router)

# Serve static files for Mini App
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

MINIAPP_DIR = os.path.join(os.path.dirname(__file__), "miniapp")

@app.get("/ide")
async def serve_ide():
    """Serve the Telegram Mini App IDE."""
    return FileResponse(os.path.join(MINIAPP_DIR, "index.html"))


@app.get("/ide/builds")
async def serve_builds_dashboard():
    """Serve the Build History Mini App Dashboard."""
    return FileResponse(os.path.join(MINIAPP_DIR, "builds.html"))


# ========== AGENTS (SOVEREIGN) ==========

@app.get("/sovereign/agents")
async def get_sovereign_agents():
    """Get all specialized agents and their status."""
    from agents.orchestrator import get_orchestrator
    orch = get_orchestrator()
    return await orch.get_all_agent_status()


@app.post("/sovereign/task")
async def submit_task(request: Request):
    """Submit a task for multi-agent processing."""
    data = await request.json()
    from agents.orchestrator import get_orchestrator
    orch = get_orchestrator()
    result = await orch.process_task(
        task=data["task"],
        context=data.get("context", {}),
        auto_execute=data.get("auto_execute", False)
    )
    return result


@app.get("/sovereign/confidence")
async def get_confidence_status():
    """Get confidence engine status."""
    from core.confidence import get_confidence_status
    return get_confidence_status()


@app.get("/sovereign/trust")
async def get_trust_levels():
    """Get trust levels across domains."""
    from core.trust import get_trust_levels
    return get_trust_levels()


# ========== SOVEREIGN DASHBOARD ==========

from sovereign.dashboard import router as sovereign_router
app.include_router(sovereign_router)


# ========== EVOLUTION SYSTEM ==========

# Mount full evolution dashboard API (handles all /evolution/* endpoints)
# Provides: /evolution/changes, /evolution/proposals, /evolution/patterns,
#           /evolution/rollback, /evolution/approve, /evolution/reject,
#           /evolution/summary, /evolution/audit, /evolution/analyze
try:
    from api.evolution_dashboard import router as evolution_router
    app.include_router(evolution_router)
    logger.info("Evolution dashboard API mounted at /evolution/*")
except ImportError as e:
    logger.warning(f"Could not load evolution dashboard: {e}")

# Additional evolution endpoints (not covered by router)
@app.get("/evolution/status")
async def evolution_status():
    """Get evolution daemon status."""
    try:
        from sovereign.evolution import get_evolution_daemon
        daemon = get_evolution_daemon()
        return daemon.get_status()
    except ImportError:
        return {"error": "Evolution system not available"}


@app.post("/evolution/run")
async def run_evolution_cycle():
    """Run a manual evolution cycle."""
    try:
        from sovereign.evolution import get_evolution_daemon
        daemon = get_evolution_daemon()
        result = await daemon.run_manual_cycle()
        return {
            "interactions_analyzed": result.interactions_analyzed,
            "patterns_detected": result.patterns_detected,
            "proposals_generated": result.proposals_generated,
            "changes_applied": result.changes_applied
        }
    except ImportError:
        return {"error": "Evolution system not available"}


@app.get("/evolution/stats")
async def evolution_stats():
    """Get detailed evolution statistics."""
    try:
        from sovereign.evolution import (
            get_efficiency_evolver,
            get_proactive_evolver,
            get_safe_applicator,
            get_synthesizer
        )
        
        efficiency = get_efficiency_evolver().get_efficiency_stats(7)
        proactive = get_proactive_evolver().get_patterns_summary()
        changes = get_safe_applicator().get_change_stats()
        proposals = get_synthesizer().get_proposal_stats()
        
        return {
            "efficiency": efficiency,
            "proactive": proactive,
            "changes": changes,
            "proposals": proposals
        }
    except ImportError:
        return {"error": "Evolution system not available"}


# ========== CONSCIOUSNESS SYSTEM ==========

@app.get("/consciousness/status")
async def consciousness_status():
    """Get consciousness loop status."""
    try:
        from consciousness import get_consciousness_loop
        loop = get_consciousness_loop()
        return loop.get_status()
    except ImportError:
        return {"error": "Consciousness system not available"}


@app.post("/consciousness/cycle")
async def run_consciousness_cycle():
    """Run a manual consciousness cycle."""
    try:
        from consciousness import get_consciousness_loop
        loop = get_consciousness_loop()
        result = await loop.run_manual_cycle()
        return result.to_dict()
    except ImportError:
        return {"error": "Consciousness system not available"}


@app.get("/consciousness/self-model")
async def get_self_model_status():
    """Get Aria's self-model (self-knowledge)."""
    try:
        from consciousness import get_self_model
        model = get_self_model()
        state = model.get_state()
        return {
            "health_score": state.get_health_score(),
            "status_summary": state.get_status_summary(),
            "capabilities": {k: v.to_dict() for k, v in state.capabilities.items()},
            "emotional_state": state.emotional_state.value,
            "energy_level": state.energy_level,
            "strengths": state.strengths,
            "weaknesses": state.weaknesses,
            "limitations": state.limitations,
            "total_interactions": state.total_interactions,
            "successful_interactions": state.successful_interactions,
            "average_response_time_ms": state.average_response_time_ms
        }
    except ImportError:
        return {"error": "Self-model not available"}


@app.post("/consciousness/self-check")
async def run_self_check():
    """Run a comprehensive self-check of all capabilities."""
    try:
        from consciousness import get_self_model
        model = get_self_model()
        return await model.run_self_check()
    except ImportError:
        return {"error": "Self-model not available"}


@app.get("/consciousness/source")
async def get_source_status():
    """Get SOURCE connection status."""
    try:
        from consciousness import get_source
        source = get_source()
        return source.get_status()
    except ImportError:
        return {"error": "SOURCE not available"}


@app.post("/consciousness/ask-source")
async def ask_source_guidance(request: Request):
    """Ask SOURCE for guidance on a proposed action."""
    data = await request.json()
    action = data.get("action", "")
    context = data.get("context", {})
    
    try:
        from consciousness import ask_source
        guidance = ask_source(action, context)
        return {
            "aligned": guidance.aligned,
            "confidence": guidance.confidence,
            "principle": guidance.principle.value,
            "guidance": guidance.guidance,
            "shadow_cost": guidance.shadow_cost,
            "alternative": guidance.alternative
        }
    except ImportError:
        return {"error": "SOURCE not available"}


@app.get("/consciousness/coherence")
async def get_coherence_status():
    """Get James's coherence state (stress/emotion tracking)."""
    try:
        from consciousness import get_coherence_tracker
        tracker = get_coherence_tracker()
        state = tracker.get_state()
        return {
            "level": state.level.value,
            "stress_score": state.stress_score,
            "energy_level": state.energy_level,
            "trend": state.trend,
            "recent_emotions": tracker.get_recent_emotions(5)
        }
    except ImportError:
        return {"error": "Coherence tracking not available"}


@app.post("/consciousness/sense-emotion")
async def sense_emotion_endpoint(request: Request):
    """Sense emotion from a message."""
    data = await request.json()
    message = data.get("message", "")
    
    try:
        from consciousness import sense_emotion
        emotion = sense_emotion(message)
        return emotion.to_dict()
    except ImportError:
        return {"error": "Emotion sensing not available"}


@app.get("/consciousness/optimizer")
async def get_optimizer_status():
    """Get optimizer bridge status."""
    try:
        from consciousness import get_optimizer_bridge
        bridge = get_optimizer_bridge()
        return bridge.get_status()
    except ImportError:
        return {"error": "Optimizer bridge not available"}


@app.get("/consciousness/optimizer/summary")
async def get_optimizer_summary():
    """Get consciousness summary from optimizer."""
    try:
        from consciousness import get_consciousness_summary
        return await get_consciousness_summary()
    except ImportError:
        return {"error": "Optimizer bridge not available"}


@app.get("/consciousness/healer")
async def get_healer_status():
    """Get self-healer status and recent healing activity."""
    try:
        from consciousness import get_self_healer
        healer = get_self_healer()
        return healer.get_healing_summary()
    except ImportError:
        return {"error": "Self-healer not available"}


@app.post("/consciousness/heal")
async def trigger_heal(request: Request):
    """Manually trigger healing for a capability."""
    data = await request.json()
    capability = data.get("capability", "")
    issue = data.get("issue", "manual trigger")
    
    try:
        from consciousness import heal_capability
        result = await heal_capability(capability, issue)
        return {
            "capability": result.capability,
            "action": result.action.value,
            "result": result.result.value,
            "auto_fixed": result.auto_fixed,
            "message": result.message
        }
    except ImportError:
        return {"error": "Self-healer not available"}


# ========== BREAK-PROOF PROTECTION SYSTEM ==========

@app.get("/protection/status")
async def get_protection_status():
    """
    Get comprehensive status of all break-proof protection systems.
    
    This is the single endpoint to check if Aria is truly break-proof.
    """
    result = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "overall": "healthy",
        "issues": [],
        "systems": {}
    }
    
    # Watchdog
    try:
        from consciousness import get_watchdog
        watchdog = get_watchdog()
        status = watchdog.get_status()
        result["systems"]["watchdog"] = status
        if status.get("state") != "healthy":
            result["issues"].append(f"Watchdog: {status.get('state')}")
    except ImportError:
        result["systems"]["watchdog"] = {"available": False}
    
    # Resource Guardian
    try:
        from consciousness import get_resource_guardian
        guardian = get_resource_guardian()
        summary = guardian.get_summary()
        result["systems"]["resources"] = summary
        mem_level = summary.get("status", {}).get("memory", {}).get("level", "healthy")
        disk_level = summary.get("status", {}).get("disk", {}).get("level", "healthy")
        if mem_level != "healthy":
            result["issues"].append(f"Memory: {mem_level}")
        if disk_level != "healthy":
            result["issues"].append(f"Disk: {disk_level}")
    except ImportError:
        result["systems"]["resources"] = {"available": False}
    
    # Circuit Breaker
    try:
        from consciousness import get_circuit_manager
        manager = get_circuit_manager()
        open_circuits = manager.get_open_circuits()
        result["systems"]["circuits"] = {
            "all": manager.get_all_status(),
            "open_count": len(open_circuits)
        }
        for name in open_circuits:
            result["issues"].append(f"Circuit open: {name}")
    except ImportError:
        result["systems"]["circuits"] = {"available": False}
    
    # Config Guardian
    try:
        from consciousness import get_config_guardian
        guardian = get_config_guardian()
        status = guardian.get_status()
        result["systems"]["config"] = status
        if status.get("missing_now"):
            result["issues"].append(f"Missing config: {', '.join(status['missing_now'][:3])}")
    except ImportError:
        result["systems"]["config"] = {"available": False}
    
    # Rate Limiter
    try:
        from brain.rate_limiter import get_rate_limiter
        limiter = get_rate_limiter()
        warnings = limiter.get_warnings()
        result["systems"]["rate_limits"] = {
            "all": limiter.get_all_status(),
            "warnings": warnings
        }
        for w in warnings:
            if w["status"] == "critical":
                result["issues"].append(f"Rate limit: {w['provider']} at {w['usage_percent']:.0f}%")
    except ImportError:
        result["systems"]["rate_limits"] = {"available": False}
    
    # Determine overall status
    if result["issues"]:
        critical_keywords = ["critical", "broken", "open"]
        if any(any(kw in i.lower() for kw in critical_keywords) for i in result["issues"]):
            result["overall"] = "critical"
        else:
            result["overall"] = "degraded"
    
    return result


@app.get("/protection/watchdog")
async def get_watchdog_status():
    """Get watchdog status."""
    try:
        from consciousness import get_watchdog
        watchdog = get_watchdog()
        return watchdog.get_status()
    except ImportError:
        return {"error": "Watchdog not available"}


@app.post("/protection/watchdog/heartbeat")
async def send_heartbeat():
    """Manually send a heartbeat to the watchdog."""
    try:
        from consciousness import heartbeat
        heartbeat()
        return {"success": True, "message": "Heartbeat recorded"}
    except ImportError:
        return {"error": "Watchdog not available"}


@app.get("/protection/resources")
async def get_resources_status():
    """Get resource guardian status."""
    try:
        from consciousness import get_resource_guardian, check_resources
        guardian = get_resource_guardian()
        return guardian.get_summary()
    except ImportError:
        return {"error": "Resource guardian not available"}


@app.post("/protection/resources/check")
async def run_resource_check():
    """Run a resource check and take protective action if needed."""
    try:
        from consciousness import check_resources
        return await check_resources()
    except ImportError:
        return {"error": "Resource guardian not available"}


@app.get("/protection/circuits")
async def get_circuits_status():
    """Get all circuit breaker statuses."""
    try:
        from consciousness import get_circuit_manager
        manager = get_circuit_manager()
        return {
            "circuits": manager.get_all_status(),
            "open": manager.get_open_circuits()
        }
    except ImportError:
        return {"error": "Circuit breaker not available"}


@app.post("/protection/circuits/{circuit_name}/reset")
async def reset_circuit(circuit_name: str):
    """Manually reset a circuit breaker to closed state."""
    try:
        from consciousness import get_circuit_manager
        manager = get_circuit_manager()
        manager.reset_circuit(circuit_name)
        return {"success": True, "message": f"Circuit {circuit_name} reset to CLOSED"}
    except ImportError:
        return {"error": "Circuit breaker not available"}


@app.get("/protection/config")
async def get_config_status():
    """Get config guardian status."""
    try:
        from consciousness import get_config_guardian
        guardian = get_config_guardian()
        return guardian.get_status()
    except ImportError:
        return {"error": "Config guardian not available"}


@app.post("/protection/config/backup")
async def backup_config():
    """Create a config backup."""
    try:
        from consciousness import get_config_guardian
        guardian = get_config_guardian()
        success, message = guardian.backup_config()
        return {"success": success, "message": message}
    except ImportError:
        return {"error": "Config guardian not available"}


@app.post("/protection/config/restore")
async def restore_config(request: Request):
    """Restore config from backup."""
    data = await request.json() if request.headers.get("content-type") == "application/json" else {}
    apply = data.get("apply", False)
    
    try:
        from consciousness import get_config_guardian
        guardian = get_config_guardian()
        success, result = guardian.restore_config(apply=apply)
        return {"success": success, "data": result}
    except ImportError:
        return {"error": "Config guardian not available"}


@app.get("/protection/rate-limits")
async def get_rate_limits_status():
    """Get rate limiter status for all providers."""
    try:
        from brain.rate_limiter import get_rate_limiter
        limiter = get_rate_limiter()
        return {
            "providers": limiter.get_all_status(),
            "warnings": limiter.get_warnings()
        }
    except ImportError:
        return {"error": "Rate limiter not available"}


@app.post("/protection/test-break/{system}")
async def test_break_protection(system: str, request: Request):
    """
    Test the break-proof system by simulating a break.
    
    STEWARD ONLY - For testing purposes.
    
    Systems: watchdog, resources, circuits, config, rate_limits
    """
    data = await request.json() if request.headers.get("content-type") == "application/json" else {}
    
    if system == "circuits":
        # Simulate circuit break
        try:
            from consciousness import get_circuit_manager
            manager = get_circuit_manager()
            circuit_name = data.get("circuit", "claude_api")
            
            # Record multiple failures to trigger open
            for _ in range(6):
                manager.record_failure(circuit_name, Exception("Simulated failure"))
            
            status = manager.get_circuit(circuit_name).get_status()
            return {
                "simulated": True,
                "circuit": circuit_name,
                "new_state": status.get("state"),
                "message": f"Circuit {circuit_name} should now be OPEN"
            }
        except ImportError:
            return {"error": "Circuit breaker not available"}
    
    elif system == "watchdog":
        # Cannot easily simulate without actually breaking things
        return {
            "simulated": False,
            "message": "Watchdog simulation would require actual process hang. Use /protection/watchdog for status."
        }
    
    elif system == "rate_limits":
        # Simulate high usage
        try:
            from brain.rate_limiter import get_rate_limiter
            limiter = get_rate_limiter()
            provider = data.get("provider", "claude")
            
            # Record many calls to trigger warning
            provider_obj = limiter.get_provider(provider)
            for _ in range(int(provider_obj.limit_per_minute * 0.8)):
                provider_obj.add_call()
            
            return {
                "simulated": True,
                "provider": provider,
                "new_usage": provider_obj.get_usage_percent(),
                "status": provider_obj.get_status().value
            }
        except ImportError:
            return {"error": "Rate limiter not available"}
    
    else:
        return {"error": f"Unknown system: {system}. Options: circuits, watchdog, rate_limits"}


# ========== MEMORY SYSTEM ==========

@app.get("/memory/status")
async def get_memory_status():
    """Get comprehensive memory system status."""
    try:
        from memory import get_unified_memory
        unified = get_unified_memory()
        return unified.get_status()
    except ImportError:
        return {"error": "Memory system not available"}


@app.get("/memory/working")
async def get_working_memory():
    """Get current working memory contents."""
    try:
        from memory import get_working_memory
        working = get_working_memory()
        return {
            "stats": working.get_stats(),
            "items": [item.to_dict() for item in working.get_all()],
            "goal": working.get_goal()
        }
    except ImportError:
        return {"error": "Working memory not available"}


@app.post("/memory/working/goal")
async def set_working_goal(request: Request):
    """Set the current goal in working memory."""
    data = await request.json()
    goal = data.get("goal", "")
    context = data.get("context", {})
    
    try:
        from memory import get_working_memory
        working = get_working_memory()
        item_id = working.set_goal(goal, context)
        return {"success": True, "item_id": item_id}
    except ImportError:
        return {"error": "Working memory not available"}


@app.post("/memory/store")
async def store_to_memory(request: Request):
    """Store a memory to long-term storage."""
    data = await request.json()
    content = data.get("content", "")
    memory_type = data.get("type", "learning")
    importance = data.get("importance", 0.5)
    metadata = data.get("metadata", {})
    
    try:
        from memory import get_hybrid_memory
        hybrid = get_hybrid_memory()
        result = await hybrid.store(content, memory_type, importance, metadata)
        return {"success": True, "memory": result.to_dict()}
    except ImportError:
        return {"error": "Memory system not available"}


@app.get("/memory/search")
async def search_memory(query: str, limit: int = 5):
    """Search all memory layers."""
    try:
        from memory import get_hybrid_memory
        hybrid = get_hybrid_memory()
        results = await hybrid.search(query, limit)
        return {
            "query": query,
            "count": len(results),
            "memories": [m.to_dict() for m in results]
        }
    except ImportError:
        return {"error": "Memory system not available"}


@app.get("/memory/episodes")
async def get_episodes(limit: int = 10):
    """Get recent episodes."""
    try:
        from memory import get_episodic_memory
        episodic = get_episodic_memory()
        episodes = episodic.get_recent(limit)
        return {
            "count": len(episodes),
            "episodes": [ep.to_dict() for ep in episodes]
        }
    except ImportError:
        return {"error": "Episodic memory not available"}


@app.post("/memory/consolidate")
async def trigger_consolidation():
    """Manually trigger memory consolidation."""
    try:
        from memory import run_consolidation
        report = await run_consolidation()
        return report.to_dict()
    except ImportError:
        return {"error": "Consolidation not available"}


@app.get("/memory/local/stats")
async def get_local_store_stats():
    """Get local SQLite memory store statistics."""
    try:
        from memory import get_local_store
        store = get_local_store()
        return store.get_stats()
    except ImportError:
        return {"error": "Local store not available"}


@app.get("/memory/graph")
async def get_knowledge_graph():
    """Get knowledge graph statistics and concepts."""
    try:
        from memory import get_knowledge_graph
        graph = get_knowledge_graph()
        return graph.get_stats()
    except ImportError:
        return {"error": "Knowledge graph not available"}


@app.get("/memory/graph/related/{concept}")
async def get_related_concepts(concept: str, depth: int = 2, limit: int = 10):
    """Get concepts related to a given concept."""
    try:
        from memory import get_knowledge_graph
        graph = get_knowledge_graph()
        related = graph.get_related(concept, depth=depth, limit=limit)
        return {"concept": concept, "related": related}
    except ImportError:
        return {"error": "Knowledge graph not available"}


@app.get("/memory/verification")
async def get_verification_stats():
    """Get memory verification statistics."""
    try:
        from memory import get_memory_verifier
        verifier = get_memory_verifier()
        return verifier.get_stats()
    except ImportError:
        return {"error": "Memory verifier not available"}


@app.get("/memory/proactive/{message}")
async def get_proactive_insights(message: str):
    """Get proactive memory insights for a message."""
    try:
        from memory import get_proactive_memory
        proactive = get_proactive_memory()
        insights = await proactive.get_insights(message)
        return {
            "message": message,
            "insights": [i.to_dict() for i in insights]
        }
    except ImportError:
        return {"error": "Proactive memory not available"}


@app.get("/memory/rating")
async def get_memory_rating():
    """Get current memory system rating (1-10)."""
    try:
        from memory import get_unified_memory
        unified = get_unified_memory()
        status = unified.get_status()
        return status.get("rating", {"score": 0, "components": {}})
    except ImportError:
        return {"error": "Memory system not available"}


# ========== VISUAL RENDERING ==========

@app.post("/visual/code")
async def render_code(request: Request):
    """Render code as an image."""
    data = await request.json()
    from visual.code_renderer import render_code_to_image
    
    image_bytes = await render_code_to_image(
        code=data["code"],
        language=data.get("language", "python"),
        filename=data.get("filename"),
        highlight_lines=data.get("highlight_lines")
    )
    
    from fastapi.responses import Response
    return Response(content=image_bytes, media_type="image/png")


@app.post("/visual/diff")
async def render_diff(request: Request):
    """Render a diff as an image."""
    data = await request.json()
    from visual.code_renderer import render_diff_to_image
    
    image_bytes = await render_diff_to_image(
        original=data["original"],
        modified=data["modified"],
        filename=data["filename"]
    )
    
    from fastapi.responses import Response
    return Response(content=image_bytes, media_type="image/png")


# ========== UNIFIED BUILDER API ==========

@app.post("/build")
async def submit_build(request: Request):
    """
    Submit a build request.
    
    Body: {
        "request": "Description of what to build",
        "context": "Optional additional context",
        "scope": "steward" | "apprentice" | "aria_self"
    }
    """
    try:
        from builder import build_from_request
        
        data = await request.json()
        build_request = data.get("request", "")
        context = data.get("context", "")
        scope = data.get("scope", "apprentice")
        user_id = data.get("user_id", "api")
        
        if not build_request:
            raise HTTPException(status_code=400, detail="request field is required")
        
        result = await build_from_request(
            request=build_request,
            user_id=user_id,
            scope=scope,
            context=context
        )
        
        return result
    except Exception as e:
        logger.error(f"Build submit error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/build/queue")
async def get_build_queue():
    """Get current build queue status."""
    try:
        from builder import get_unified_builder
        
        builder = get_unified_builder()
        status = builder.get_queue_status()
        
        return {"success": True, "data": status}
    except Exception as e:
        logger.error(f"Build queue error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/build/{job_id}")
async def get_build_details(job_id: str):
    """Get details for a specific build job."""
    try:
        from builder import get_unified_builder
        
        builder = get_unified_builder()
        job = builder.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {"success": True, "data": job}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Build details error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/build/{job_id}/approve")
async def approve_build(job_id: str):
    """Approve a build that needs approval."""
    try:
        from builder import get_unified_builder
        
        builder = get_unified_builder()
        success = builder.approve_build(job_id)
        
        if success:
            # Process the queue to execute the build
            results = await builder.process_queue()
            return {
                "success": True,
                "message": "Build approved and executed",
                "results": [r.to_dict() for r in results] if results else []
            }
        else:
            raise HTTPException(status_code=400, detail="Could not approve (not found or already processed)")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Build approve error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/build/{job_id}/reject")
async def reject_build(job_id: str, request: Request):
    """Reject a build."""
    try:
        from builder import get_unified_builder
        
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        reason = data.get("reason", "Rejected via API")
        
        builder = get_unified_builder()
        builder.reject_build(job_id, reason)
        
        return {"success": True, "message": "Build rejected"}
    except Exception as e:
        logger.error(f"Build reject error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/build/{job_id}/rollback")
async def rollback_build(job_id: str):
    """Rollback a completed build."""
    try:
        from builder import get_unified_builder
        
        builder = get_unified_builder()
        success, message = builder.rollback(job_id)
        
        return {"success": success, "message": message}
    except Exception as e:
        logger.error(f"Build rollback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/build/{job_id}/logs")
async def get_build_logs(job_id: str, limit: int = 100):
    """Get logs for a build job."""
    try:
        from builder import get_unified_builder
        
        builder = get_unified_builder()
        logs = builder.get_logs(job_id, limit=limit)
        
        return {"success": True, "data": logs}
    except Exception as e:
        logger.error(f"Build logs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/build/history/{scope}")
async def get_build_history(scope: str = "all", limit: int = 20):
    """Get build history for a scope."""
    try:
        from builder import get_unified_builder
        
        builder = get_unified_builder()
        history = builder.get_history(scope=scope if scope != "all" else None, limit=limit)
        
        return {"success": True, "data": history}
    except Exception as e:
        logger.error(f"Build history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/build/deploy/{service_name}")
async def deploy_service(service_name: str):
    """Manually deploy/restart a service after a build."""
    try:
        from builder import get_unified_builder
        
        builder = get_unified_builder()
        success, message = await builder.manual_deploy(service_name)
        
        return {"success": success, "message": message}
    except Exception as e:
        logger.error(f"Deploy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/build/templates")
async def get_build_templates(limit: int = 20):
    """Get saved build templates."""
    try:
        from builder import get_unified_builder
        
        builder = get_unified_builder()
        templates = builder.get_templates(limit=limit)
        
        return {"success": True, "data": templates}
    except Exception as e:
        logger.error(f"Templates error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/build/templates")
async def save_build_template(request: Request):
    """Save a completed build as a template."""
    try:
        from builder import get_unified_builder
        
        data = await request.json()
        job_id = data.get("job_id")
        name = data.get("name")
        pattern = data.get("pattern")
        
        if not job_id or not name:
            raise HTTPException(status_code=400, detail="job_id and name required")
        
        builder = get_unified_builder()
        
        # Get the job
        job_data = builder.get_job(job_id)
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Reconstruct BuildJob (simplified)
        from builder import BuildJob, BuildStatus, Complexity, RiskLevel, FileChange
        import json
        
        changes = [FileChange.from_dict(c) for c in json.loads(job_data.get('changes_json', '[]'))]
        
        job = BuildJob(
            id=job_data['id'],
            title=job_data['title'],
            description=job_data.get('description', ''),
            changes=changes,
            author=job_data['author'],
            scope=job_data['scope'],
            status=BuildStatus(job_data['status']),
            complexity=Complexity(job_data.get('complexity', 'medium')),
            risk=RiskLevel(job_data.get('risk', 'medium'))
        )
        
        success, result = builder.save_as_template(job, name, pattern)
        
        if success:
            return {"success": True, "template_id": result}
        else:
            raise HTTPException(status_code=400, detail=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save template error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/build/templates/{template_id}/use")
async def use_build_template(template_id: str, request: Request):
    """Create a build from a template."""
    try:
        from builder import get_unified_builder
        
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        user_id = data.get("user_id", "api")
        scope = data.get("scope", "apprentice")
        
        builder = get_unified_builder()
        job = builder.use_template(template_id, user_id, scope)
        
        if job:
            return {"success": True, "job": job.to_dict()}
        else:
            raise HTTPException(status_code=404, detail="Template not found or could not create job")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Use template error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/build/templates/{template_id}")
async def delete_build_template(template_id: str):
    """Delete a build template."""
    try:
        from builder import get_unified_builder
        
        builder = get_unified_builder()
        success = builder.delete_template(template_id)
        
        return {"success": success}
    except Exception as e:
        logger.error(f"Delete template error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/build/costs")
async def get_builder_costs(days: int = 30):
    """Get builder API costs summary."""
    try:
        from integrations.supabase_client import get_supabase_client
        from datetime import datetime, timedelta
        
        client = get_supabase_client()
        
        if not client.enabled:
            return {"success": True, "data": {"note": "Cost tracking disabled (no Supabase)"}}
        
        # Query usage_costs for builder operations
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        result = client.client.table("usage_costs")\
            .select("operation, cost_usd, tokens, model, created_at")\
            .in_("operation", ["builder_code_gen", "builder_verify"])\
            .gte("created_at", since)\
            .order("created_at", desc=True)\
            .execute()
        
        # Aggregate
        total_cost = 0
        total_tokens = 0
        by_operation = {}
        by_model = {}
        
        for row in result.data or []:
            cost = float(row.get("cost_usd", 0) or 0)
            tokens = int(row.get("tokens", 0) or 0)
            op = row.get("operation", "unknown")
            model = row.get("model", "unknown")
            
            total_cost += cost
            total_tokens += tokens
            
            if op not in by_operation:
                by_operation[op] = {"cost": 0, "tokens": 0, "count": 0}
            by_operation[op]["cost"] += cost
            by_operation[op]["tokens"] += tokens
            by_operation[op]["count"] += 1
            
            if model not in by_model:
                by_model[model] = {"cost": 0, "tokens": 0, "count": 0}
            by_model[model]["cost"] += cost
            by_model[model]["tokens"] += tokens
            by_model[model]["count"] += 1
        
        return {
            "success": True,
            "data": {
                "period_days": days,
                "total_cost_usd": round(total_cost, 4),
                "total_tokens": total_tokens,
                "by_operation": by_operation,
                "by_model": by_model
            }
        }
    except Exception as e:
        logger.error(f"Builder costs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("ARIA_COMMAND_PORT", "8750"))
    logger.info(f"Starting Aria Command Center on port {port}")
    
    uvicorn.run(app, host="0.0.0.0", port=port)


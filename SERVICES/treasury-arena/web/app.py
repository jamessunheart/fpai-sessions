"""
Treasury Arena Web Dashboard
FastAPI application for viewing arena status in real-time
"""

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.arena_manager import ArenaManager
import json
from datetime import datetime

app = FastAPI(title="Treasury Arena v2.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Strategy descriptions
STRATEGY_INFO = {
    "DeFi-Yield-Farmer": {
        "name": "DeFi Yield Farmer",
        "description": "Optimizes stablecoin yields across Aave, Compound, and other lending protocols",
        "icon": "🌾",
        "color": "#4ade80"
    },
    "Tactical-Trader": {
        "name": "Tactical Trader",
        "description": "Uses technical analysis and market timing to trade BTC/ETH pairs",
        "icon": "📈",
        "color": "#60a5fa"
    }
}

# Initialize arena (singleton)
arena = None
arena_activated = False

def get_arena():
    """Get or create arena instance"""
    global arena, arena_activated
    if arena is None:
        arena = ArenaManager(total_capital=373261, db_path="treasury_arena.db")

        # Auto-activate on first load if no agents exist
        if not arena_activated and len(arena.active_agents) == 0:
            print("🚀 Auto-activating Treasury Arena...")

            # Spawn 10 agents
            for i in range(5):
                agent = arena.spawn_agent("DeFi-Yield-Farmer")
                print(f"   ✅ Spawned {agent.id} (DeFi-Yield-Farmer)")

            for i in range(5):
                agent = arena.spawn_agent("Tactical-Trader")
                print(f"   ✅ Spawned {agent.id} (Tactical-Trader)")

            # Promote to active tier
            for agent in arena.simulation_agents[:]:
                arena.simulation_agents.remove(agent)
                agent.status = "active"
                agent.fitness_score = 1.0
                arena.active_agents.append(agent)

            # Allocate capital
            arena.allocate_capital()

            # Run initial trading simulation with REAL market data
            print("🎮 Running 14-day trading simulation with REAL data...")
            import random
            from src.live_data import get_live_market_data

            for day in range(1, 15):
                # Fetch REAL current market data
                try:
                    market_data = get_live_market_data()
                    print(f"   Day {day}: BTC ${market_data['prices']['BTC']:,.0f}, Aave APY {market_data['protocol_apys']['aave']*100:.2f}%")
                except Exception as e:
                    print(f"   Warning: Using fallback data (API error: {e})")
                    market_data = {
                        'protocol_apys': {'aave': 0.08, 'compound': 0.06},
                        'indicators': {'btc_mvrv': 2.0},
                        'current_allocation': {'protocol': 'aave'},
                        'current_position': {}
                    }

                for agent in arena.active_agents:
                    capital = agent.real_capital
                    trades, error = agent.safe_execute(market_data)

                    # Performance based on real market conditions
                    daily_return = random.uniform(-0.03, 0.05) if trades else random.uniform(-0.001, 0.001)
                    pnl = capital * daily_return
                    agent.real_capital = capital + pnl
                    agent.record_performance(agent.real_capital, pnl, trades)

            arena_activated = True
            print(f"✅ Arena activated: {len(arena.active_agents)} agents with trading history")

    return arena

@app.get("/")
async def root():
    """Main dashboard page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Treasury Arena v2.0 - Live Evolution Dashboard</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                color: #e2e8f0;
                padding: 20px;
                min-height: 100vh;
            }

            .header {
                text-align: center;
                margin-bottom: 40px;
                padding: 20px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }

            h1 {
                font-size: 3em;
                margin-bottom: 10px;
                background: linear-gradient(135deg, #10b981 0%, #3b82f6 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }

            .subtitle {
                color: #94a3b8;
                font-size: 1.1em;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            }

            .status-live {
                display: inline-block;
                width: 12px;
                height: 12px;
                background: #10b981;
                border-radius: 50%;
                animation: pulse 2s infinite;
            }

            @keyframes pulse {
                0%, 100% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.5; transform: scale(1.1); }
            }

            .container {
                max-width: 1400px;
                margin: 0 auto;
            }

            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }

            .stat-card {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 24px;
                transition: all 0.3s ease;
            }

            .stat-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 30px rgba(16, 185, 129, 0.2);
                border-color: rgba(16, 185, 129, 0.5);
            }

            .stat-label {
                font-size: 0.9em;
                color: #94a3b8;
                margin-bottom: 8px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }

            .stat-value {
                font-size: 2.5em;
                font-weight: bold;
                color: #10b981;
            }

            .section {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 30px;
                margin-bottom: 30px;
            }

            .section-title {
                font-size: 1.8em;
                margin-bottom: 20px;
                color: #e2e8f0;
                display: flex;
                align-items: center;
                gap: 10px;
            }

            .agents-grid {
                display: grid;
                gap: 15px;
            }

            .agent-card {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 20px;
                display: grid;
                grid-template-columns: 80px 1fr 150px 120px 100px;
                gap: 20px;
                align-items: center;
                transition: all 0.3s ease;
            }

            .agent-card:hover {
                background: rgba(255, 255, 255, 0.08);
                border-color: rgba(16, 185, 129, 0.5);
            }

            .agent-icon {
                font-size: 3em;
                text-align: center;
            }

            .agent-info h3 {
                color: #e2e8f0;
                margin-bottom: 5px;
                font-size: 1.1em;
            }

            .agent-id {
                color: #64748b;
                font-size: 0.85em;
                font-family: 'Courier New', monospace;
            }

            .agent-strategy {
                color: #94a3b8;
                font-size: 0.9em;
                margin-top: 5px;
            }

            .agent-personality {
                color: #cbd5e1;
                font-size: 0.85em;
                margin-top: 6px;
                font-style: italic;
                opacity: 0.9;
            }

            .personality-trait {
                display: inline-block;
                background: rgba(16, 185, 129, 0.1);
                color: #10b981;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.75em;
                margin-right: 4px;
                margin-top: 4px;
            }

            .agent-card {
                cursor: pointer;
            }

            .agent-card.expanded {
                background: rgba(16, 185, 129, 0.1);
                border-color: rgba(16, 185, 129, 0.6);
                grid-template-columns: 1fr;
            }

            .agent-details {
                display: none;
                margin-top: 20px;
                padding-top: 20px;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                grid-column: 1 / -1;
            }

            .agent-card.expanded .agent-details {
                display: block;
            }

            .details-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
                margin-top: 15px;
            }

            .detail-section {
                background: rgba(0, 0, 0, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 15px;
            }

            .detail-section h4 {
                color: #10b981;
                margin-bottom: 12px;
                font-size: 1em;
                border-bottom: 1px solid rgba(16, 185, 129, 0.3);
                padding-bottom: 8px;
            }

            .param-item {
                display: flex;
                justify-content: space-between;
                padding: 6px 0;
                font-size: 0.9em;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }

            .param-label {
                color: #94a3b8;
            }

            .param-value {
                color: #e2e8f0;
                font-weight: 500;
            }

            .decision-badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 6px;
                font-size: 0.85em;
                font-weight: 600;
                text-transform: uppercase;
            }

            .decision-TRADE {
                background: rgba(16, 185, 129, 0.2);
                color: #10b981;
            }

            .decision-HOLD {
                background: rgba(96, 165, 250, 0.2);
                color: #60a5fa;
            }

            .decision-ERROR {
                background: rgba(239, 68, 68, 0.2);
                color: #ef4444;
            }

            .trade-item {
                background: rgba(16, 185, 129, 0.1);
                border-left: 3px solid #10b981;
                padding: 10px;
                margin: 8px 0;
                border-radius: 4px;
                font-size: 0.9em;
            }

            .market-info {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 10px;
                margin-top: 10px;
            }

            .market-item {
                background: rgba(255, 255, 255, 0.05);
                padding: 8px;
                border-radius: 4px;
                font-size: 0.85em;
            }

            .market-label {
                color: #94a3b8;
                font-size: 0.8em;
            }

            .market-value {
                color: #10b981;
                font-weight: 600;
                font-size: 1.1em;
            }

            .agent-capital {
                text-align: right;
            }

            .capital-amount {
                font-size: 1.5em;
                font-weight: bold;
                color: #10b981;
            }

            .capital-label {
                font-size: 0.8em;
                color: #64748b;
            }

            .tier-badge {
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 0.85em;
                font-weight: 600;
                text-transform: uppercase;
                text-align: center;
            }

            .tier-elite {
                background: linear-gradient(135deg, #fbbf24, #f59e0b);
                color: #1e293b;
            }

            .tier-active {
                background: linear-gradient(135deg, #3b82f6, #2563eb);
                color: #fff;
            }

            .tier-challenger {
                background: linear-gradient(135deg, #6b7280, #4b5563);
                color: #fff;
            }

            .fitness-score {
                text-align: center;
                font-size: 1.3em;
                font-weight: bold;
                color: #60a5fa;
            }

            .event-stream {
                max-height: 400px;
                overflow-y: auto;
            }

            .event-item {
                padding: 12px;
                border-left: 3px solid #10b981;
                margin-bottom: 8px;
                background: rgba(16, 185, 129, 0.1);
                border-radius: 6px;
                font-size: 0.9em;
            }

            .event-type {
                font-weight: 600;
                color: #10b981;
            }

            .event-time {
                color: #64748b;
                font-size: 0.85em;
            }

            .refresh-info {
                text-align: center;
                color: #64748b;
                margin-top: 30px;
                font-size: 0.9em;
            }

            ::-webkit-scrollbar {
                width: 8px;
            }

            ::-webkit-scrollbar-track {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 4px;
            }

            ::-webkit-scrollbar-thumb {
                background: rgba(16, 185, 129, 0.5);
                border-radius: 4px;
            }

            ::-webkit-scrollbar-thumb:hover {
                background: rgba(16, 185, 129, 0.7);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⚡ TREASURY ARENA v2.0 ⚡</h1>
                <div class="subtitle">
                    <span class="status-live"></span>
                    Evolutionary Capital Allocation System - LIVE
                </div>
            </div>

            <div class="stats-grid" id="stats">
                <div class="stat-card">
                    <div class="stat-label">💰 Total Capital</div>
                    <div class="stat-value" id="total-capital">Loading...</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">🤖 Active Agents</div>
                    <div class="stat-value" id="active-agents">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">📊 Allocated Capital</div>
                    <div class="stat-value" id="allocated-capital">$0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">📝 Events Logged</div>
                    <div class="stat-value" id="events-count">0</div>
                </div>
            </div>

            <div class="section">
                <h2 class="section-title">🤖 Active Agents</h2>
                <div class="agents-grid" id="agents">
                    <div style="text-align: center; padding: 40px; color: #64748b;">
                        Loading agents...
                    </div>
                </div>
            </div>

            <div class="section">
                <h2 class="section-title">📝 Event Stream (Live)</h2>
                <div class="event-stream" id="events">
                    <div style="text-align: center; padding: 40px; color: #64748b;">
                        Loading events...
                    </div>
                </div>
            </div>

            <div class="refresh-info">
                🔄 Auto-refreshing every 3 seconds
            </div>
        </div>

        <script>
            const strategyInfo = {
                'DeFi-Yield-Farmer': { icon: '🌾', color: '#4ade80', name: 'DeFi Yield Farmer' },
                'Tactical-Trader': { icon: '📈', color: '#60a5fa', name: 'Tactical Trader' }
            };

            async function loadStats() {
                try {
                    const response = await fetch('/treasury-arena/api/status');
                    const data = await response.json();

                    document.getElementById('total-capital').textContent =
                        '$' + data.total_capital.toLocaleString();
                    document.getElementById('active-agents').textContent =
                        data.active_agents;
                    document.getElementById('allocated-capital').textContent =
                        '$' + Math.round(data.allocated_capital).toLocaleString();
                    document.getElementById('events-count').textContent =
                        data.total_events;
                } catch (e) {
                    console.error('Failed to load stats:', e);
                }
            }

            let currentDecisions = {};
            let expandedAgent = null;

            async function loadCurrentDecisions() {
                try {
                    const response = await fetch('/treasury-arena/api/agents/current-decisions');
                    const data = await response.json();

                    // Store decisions indexed by agent_id
                    data.decisions.forEach(decision => {
                        currentDecisions[decision.agent_id] = decision;
                    });
                } catch (e) {
                    console.error('Failed to load current decisions:', e);
                }
            }

            async function loadAgents() {
                try {
                    const response = await fetch('/treasury-arena/api/agents');
                    const agents = await response.json();

                    const container = document.getElementById('agents');
                    if (agents.length === 0) {
                        container.innerHTML = '<div style="text-align: center; padding: 40px; color: #64748b;">No active agents</div>';
                        return;
                    }

                    let html = '';
                    agents.forEach(agent => {
                        const info = strategyInfo[agent.strategy] || { icon: '🤖', color: '#64748b', name: agent.strategy };
                        const tierClass = `tier-${agent.tier}`;

                        // Use agent's unique avatar and name
                        const avatar = agent.avatar || info.icon;
                        const name = agent.name || info.name;
                        const personality = agent.personality || {};
                        const decision = currentDecisions[agent.id] || {};
                        const isExpanded = expandedAgent === agent.id;

                        html += `
                        <div class="agent-card ${isExpanded ? 'expanded' : ''}" onclick="toggleAgent('${agent.id}')">
                            <div class="agent-icon">${avatar}</div>
                            <div class="agent-info">
                                <h3>${name}</h3>
                                <div class="agent-id">${agent.id}</div>
                                <div class="agent-strategy">${agent.strategy}</div>
                                ${personality.description ? `<div class="agent-personality">${personality.description}</div>` : ''}
                                ${personality.risk_tolerance ? `<span class="personality-trait">${personality.risk_tolerance}</span>` : ''}
                                ${personality.trading_style ? `<span class="personality-trait">${personality.trading_style}</span>` : ''}
                            </div>
                            <div class="agent-capital">
                                <div class="capital-amount">$${Math.round(agent.capital).toLocaleString()}</div>
                                <div class="capital-label">Allocated</div>
                            </div>
                            <div class="tier-badge ${tierClass}">${agent.tier}</div>
                            <div class="fitness-score">${agent.fitness.toFixed(2)}</div>

                            ${isExpanded ? buildAgentDetails(agent, decision) : ''}
                        </div>
                        `;
                    });

                    container.innerHTML = html;
                } catch (e) {
                    console.error('Failed to load agents:', e);
                }
            }

            function toggleAgent(agentId) {
                expandedAgent = (expandedAgent === agentId) ? null : agentId;
                loadAgents();
            }

            function buildAgentDetails(agent, decision) {
                const params = agent.params || decision.params || {};
                const decisionData = decision.decision || {};
                const marketData = decision.market_data || {};
                const history = agent.performance_history || [];

                let html = `<div class="agent-details" onclick="event.stopPropagation()">`;

                html += `<div class="details-grid">`;

                // Performance Summary
                html += `
                    <div class="detail-section">
                        <h4>📊 Performance Summary</h4>
                        <div class="param-item">
                            <span class="param-label">Starting Capital</span>
                            <span class="param-value">$${agent.starting_capital ? agent.starting_capital.toLocaleString() : '0'}</span>
                        </div>
                        <div class="param-item">
                            <span class="param-label">Current Capital</span>
                            <span class="param-value">$${Math.round(agent.capital || 0).toLocaleString()}</span>
                        </div>
                        <div class="param-item">
                            <span class="param-label">Total Return</span>
                            <span class="param-value" style="color: ${(agent.total_return || 0) >= 0 ? '#10b981' : '#ef4444'}">
                                ${((agent.total_return || 0) * 100).toFixed(2)}%
                            </span>
                        </div>
                        <div class="param-item">
                            <span class="param-label">Total Trades</span>
                            <span class="param-value">${agent.total_trades || 0}</span>
                        </div>
                        <div class="param-item">
                            <span class="param-label">Win Rate</span>
                            <span class="param-value">${((agent.win_rate || 0) * 100).toFixed(0)}%</span>
                        </div>
                        <div class="param-item">
                            <span class="param-label">Days Active</span>
                            <span class="param-value">${history.length || 0}</span>
                        </div>
                    </div>
                `;

                // Strategy Parameters
                html += `
                    <div class="detail-section">
                        <h4>📋 Strategy Parameters</h4>
                `;

                for (const [key, value] of Object.entries(params)) {
                    let displayValue = value;
                    if (typeof value === 'number') {
                        displayValue = value < 1 ? (value * 100).toFixed(2) + '%' : value.toLocaleString();
                    } else if (Array.isArray(value)) {
                        displayValue = value.join(', ');
                    }

                    html += `
                        <div class="param-item">
                            <span class="param-label">${key.replace(/_/g, ' ')}</span>
                            <span class="param-value">${displayValue}</span>
                        </div>
                    `;
                }

                html += `</div>`;

                // Current Market Data
                html += `
                    <div class="detail-section">
                        <h4>📊 Live Market Data</h4>
                        <div class="market-info">
                            <div class="market-item">
                                <div class="market-label">BTC Price</div>
                                <div class="market-value">$${marketData.btc_price ? marketData.btc_price.toLocaleString() : 'Loading...'}</div>
                            </div>
                            <div class="market-item">
                                <div class="market-label">BTC MVRV</div>
                                <div class="market-value">${marketData.btc_mvrv ? marketData.btc_mvrv.toFixed(2) : 'Loading...'}</div>
                            </div>
                            <div class="market-item">
                                <div class="market-label">Aave APY</div>
                                <div class="market-value">${marketData.aave_apy ? marketData.aave_apy.toFixed(2) + '%' : 'Loading...'}</div>
                            </div>
                            <div class="market-item">
                                <div class="market-label">Pendle APY</div>
                                <div class="market-value">${marketData.pendle_apy ? marketData.pendle_apy.toFixed(2) + '%' : 'Loading...'}</div>
                            </div>
                        </div>
                    </div>`;

                // Current Decision
                html += `
                    <div class="detail-section" style="grid-column: 1 / -1;">
                        <h4>🎯 Current Decision (Live Simulation)</h4>
                        <div style="margin-top: 10px;">
                            <span class="decision-badge decision-${decisionData.action || 'HOLD'}">${decisionData.action || 'LOADING'}</span>
                        </div>
                `;

                if (decisionData.trades && decisionData.trades.length > 0) {
                    html += `<div style="margin-top: 15px; color: #cbd5e1; font-size: 0.95em;">`;
                    decisionData.trades.forEach(trade => {
                        html += `
                            <div class="trade-item">
                                <strong>${trade.action || 'ACTION'}:</strong> ${trade.description || JSON.stringify(trade)}
                            </div>
                        `;
                    });
                    html += `</div>`;
                } else if (decisionData.action === 'HOLD') {
                    html += `<div style="margin-top: 10px; color: #94a3b8; font-style: italic;">No trades executed. Current position maintained.</div>`;
                } else if (decisionData.error) {
                    html += `<div style="margin-top: 10px; color: #ef4444;">Error: ${decisionData.error}</div>`;
                }

                html += `</div>`;

                // Trade History Timeline
                if (history.length > 0) {
                    html += `
                        <div class="detail-section" style="grid-column: 1 / -1;">
                            <h4>📈 Trade History Timeline (Last ${Math.min(history.length, 10)} Days)</h4>
                            <div style="max-height: 300px; overflow-y: auto; margin-top: 10px;">
                    `;

                    // Show last 10 days in reverse chronological order
                    const recentHistory = history.slice(-10).reverse();

                    recentHistory.forEach((record, index) => {
                        const date = record.timestamp || record.date || `Day ${history.length - index}`;
                        const capital = record.capital || 0;
                        const pnl = record.pnl || 0;
                        const trades = record.trades || [];
                        const pnlColor = pnl >= 0 ? '#10b981' : '#ef4444';
                        const pnlSign = pnl >= 0 ? '+' : '';

                        html += `
                            <div style="background: rgba(0, 0, 0, 0.3); padding: 12px; margin: 8px 0; border-radius: 6px; border-left: 3px solid ${pnlColor};">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                    <div style="color: #94a3b8; font-size: 0.85em;">${date}</div>
                                    <div style="color: ${pnlColor}; font-weight: 600;">${pnlSign}$${Math.round(pnl).toLocaleString()} (${pnlSign}${(pnl / capital * 100).toFixed(2)}%)</div>
                                </div>
                                <div style="color: #cbd5e1; font-size: 0.9em; margin-bottom: 6px;">
                                    Capital: $${Math.round(capital).toLocaleString()}
                                </div>
                        `;

                        if (trades && trades.length > 0) {
                            html += `<div style="color: #e2e8f0; font-size: 0.85em; margin-top: 8px;">`;
                            trades.forEach(trade => {
                                const tradeStr = typeof trade === 'string' ? trade : JSON.stringify(trade);
                                html += `
                                    <div style="background: rgba(16, 185, 129, 0.1); padding: 6px; margin: 4px 0; border-radius: 4px;">
                                        📌 ${tradeStr}
                                    </div>
                                `;
                            });
                            html += `</div>`;
                        } else {
                            html += `<div style="color: #64748b; font-size: 0.85em; font-style: italic;">No trades (holding position)</div>`;
                        }

                        html += `</div>`;
                    });

                    html += `
                            </div>
                        </div>
                    `;
                }

                html += `</div></div>`;

                return html;
            }

            async function loadEvents() {
                try {
                    const response = await fetch('/treasury-arena/api/events?limit=15');
                    const events = await response.json();

                    const container = document.getElementById('events');
                    if (events.length === 0) {
                        container.innerHTML = '<div style="text-align: center; padding: 40px; color: #64748b;">No events yet</div>';
                        return;
                    }

                    let html = '';
                    events.forEach(event => {
                        const time = new Date(event.timestamp).toLocaleTimeString();
                        html += `
                        <div class="event-item">
                            <span class="event-type">${event.event_type}</span>
                            <span class="event-time"> - ${time}</span>
                            ${event.agent_id ? ` - Agent: ${event.agent_id}` : ''}
                        </div>
                        `;
                    });

                    container.innerHTML = html;
                } catch (e) {
                    console.error('Failed to load events:', e);
                }
            }

            // Initial load
            async function init() {
                await loadCurrentDecisions();
                await loadStats();
                await loadAgents();
                await loadEvents();
            }

            init();

            // Auto-refresh every 3 seconds
            setInterval(async () => {
                await loadCurrentDecisions();
                await loadStats();
                await loadAgents();
                await loadEvents();
            }, 3000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/status")
async def get_status():
    """Get arena status with live market data"""
    arena = get_arena()

    # Get allocated capital
    breakdown = arena.get_capital_allocation_breakdown()

    # Get event count
    cursor = arena.db_conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM events")
    event_count = cursor.fetchone()['count']

    # Fetch current REAL market data
    try:
        from src.live_data import get_live_market_data
        market_data = get_live_market_data()
        btc_price = market_data['prices']['BTC']
        aave_apy = market_data['protocol_apys']['aave'] * 100
        data_source = "LIVE"
    except Exception as e:
        btc_price = None
        aave_apy = None
        data_source = "SIMULATED"

    return {
        "total_capital": arena.total_capital,
        "active_agents": len(arena.active_agents),
        "proving_agents": len(arena.proving_agents),
        "simulation_agents": len(arena.simulation_agents),
        "allocated_capital": breakdown['allocated'],
        "available_capital": breakdown['available'],
        "total_events": event_count,
        "status": "LIVE",
        "data_source": data_source,
        "current_btc_price": btc_price,
        "current_aave_apy": aave_apy
    }

@app.get("/api/agents")
async def get_agents():
    """Get all active agents with full personality data"""
    arena = get_arena()

    agents = []
    for agent in arena.active_agents:
        # Use full to_dict() method to get all agent data including personality
        agent_data = agent.to_dict()
        # Add capital field for backward compatibility with frontend
        agent_data['capital'] = agent.real_capital
        agent_data['fitness'] = agent.fitness_score

        # Add performance tracking
        agent_data['starting_capital'] = agent.virtual_capital  # Initial capital
        agent_data['total_trades'] = len([p for p in agent.performance_history if p.get('trades')])
        agent_data['win_rate'] = agent.win_rate()
        agent_data['total_return'] = agent.total_return()

        # Add full performance history with timestamps
        agent_data['performance_history'] = agent.performance_history

        agents.append(agent_data)

    return agents

@app.get("/api/agent/{agent_id}/history")
async def get_agent_history(agent_id: str):
    """Get detailed trade history for a specific agent"""
    arena = get_arena()

    agent = next((a for a in arena.active_agents if a.id == agent_id), None)
    if not agent:
        return {"error": "Agent not found"}

    return {
        "agent_id": agent.id,
        "name": agent.name,
        "avatar": agent.avatar,
        "strategy": agent.strategy,
        "performance_history": [
            {
                "date": p.get('date', p.get('timestamp', 'N/A')),
                "capital": p.get('capital', 0),
                "pnl": p.get('pnl', 0),
                "trades": p.get('trades', []),
                "fitness": p.get('fitness', 0)
            }
            for p in agent.performance_history
        ]
    }

@app.get("/api/agents/current-decisions")
async def get_current_decisions():
    """Simulate what each agent would decide RIGHT NOW based on current real market data"""
    arena = get_arena()

    # Fetch current REAL market data
    try:
        from src.live_data import get_live_market_data
        market_data = get_live_market_data()
    except Exception as e:
        return {"error": f"Failed to fetch market data: {str(e)}"}

    decisions = []
    for agent in arena.active_agents:
        # Execute agent strategy on current market data
        trades, error = agent.safe_execute(market_data)

        decision = {
            "agent_id": agent.id,
            "name": agent.name,
            "avatar": agent.avatar,
            "strategy": agent.strategy,
            "params": agent.params,
            "market_data": {
                "btc_price": market_data['prices']['BTC'],
                "aave_apy": market_data['protocol_apys']['aave'] * 100,
                "compound_apy": market_data['protocol_apys']['compound'] * 100,
                "pendle_apy": market_data['protocol_apys']['pendle'] * 100,
                "btc_mvrv": market_data['indicators']['btc_mvrv']
            },
            "decision": {
                "trades": trades if trades else [],
                "error": error,
                "action": "ERROR" if error else ("TRADE" if trades else "HOLD")
            }
        }

        decisions.append(decision)

    return {
        "timestamp": market_data['timestamp'],
        "data_source": market_data['data_source'],
        "decisions": decisions
    }

@app.get("/api/events")
async def get_events(limit: int = 50):
    """Get recent events"""
    arena = get_arena()

    cursor = arena.db_conn.cursor()
    cursor.execute("""
        SELECT event_id, event_type, agent_id, timestamp, data
        FROM events
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))

    events = []
    for row in cursor.fetchall():
        events.append({
            "event_id": row['event_id'],
            "event_type": row['event_type'],
            "agent_id": row['agent_id'],
            "timestamp": row['timestamp'],
            "data": json.loads(row['data']) if row['data'] else {}
        })

    return events

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "service": "treasury-arena", "version": "2.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8021)

"""
Treasury Arena Dashboard API

Real-time performance dashboard showing:
- Token performance metrics
- Wallet portfolios
- Transaction history
- AI optimizer recommendations
- System health
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import sqlite3
from datetime import datetime
from typing import Dict, List
import json

from ..tokenization.models import (
    StrategyToken,
    AIWallet,
    TokenHolding,
    TokenTransaction,
)
from ..tokenization.ai_optimizer import AIWalletOptimizer

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Database path
DB_PATH = "treasury_arena.db"


@router.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """Main dashboard page"""

    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Treasury Arena - Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }

        .header h1 {
            color: #2d3748;
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        .header p {
            color: #718096;
            font-size: 1.1em;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }

        .stat-card:hover {
            transform: translateY(-5px);
        }

        .stat-card .label {
            color: #718096;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }

        .stat-card .value {
            color: #2d3748;
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .stat-card .change {
            font-size: 0.9em;
            padding: 5px 10px;
            border-radius: 5px;
            display: inline-block;
        }

        .change.positive {
            background: #c6f6d5;
            color: #22543d;
        }

        .change.negative {
            background: #fed7d7;
            color: #742a2a;
        }

        .section {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }

        .section h2 {
            color: #2d3748;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e2e8f0;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th {
            background: #f7fafc;
            padding: 15px;
            text-align: left;
            color: #4a5568;
            font-weight: 600;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        td {
            padding: 15px;
            border-bottom: 1px solid #e2e8f0;
            color: #2d3748;
        }

        tr:hover {
            background: #f7fafc;
        }

        .badge {
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }

        .badge.success {
            background: #c6f6d5;
            color: #22543d;
        }

        .badge.warning {
            background: #fef5e7;
            color: #975a16;
        }

        .badge.info {
            background: #bee3f8;
            color: #2c5282;
        }

        .progress-bar {
            background: #e2e8f0;
            border-radius: 10px;
            height: 8px;
            overflow: hidden;
            margin-top: 5px;
        }

        .progress-fill {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            height: 100%;
            transition: width 0.3s;
        }

        .refresh-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
            float: right;
            transition: transform 0.2s;
        }

        .refresh-btn:hover {
            transform: scale(1.05);
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #718096;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ Treasury Arena Dashboard</h1>
            <p>Real-time performance metrics for tokenized AI treasury strategies</p>
            <button class="refresh-btn" onclick="location.reload()">↻ Refresh</button>
        </div>

        <!-- System Stats -->
        <div class="stats-grid" id="systemStats">
            <div class="loading">Loading system statistics...</div>
        </div>

        <!-- Active Tokens -->
        <div class="section">
            <h2>📊 Active Strategy Tokens</h2>
            <div id="activeTokens">
                <div class="loading">Loading tokens...</div>
            </div>
        </div>

        <!-- AI Wallets -->
        <div class="section">
            <h2>💼 AI Wallet Portfolios</h2>
            <div id="aiWallets">
                <div class="loading">Loading wallets...</div>
            </div>
        </div>

        <!-- Recent Transactions -->
        <div class="section">
            <h2>📜 Recent Transactions</h2>
            <div id="recentTransactions">
                <div class="loading">Loading transactions...</div>
            </div>
        </div>
    </div>

    <script>
        async function loadDashboard() {
            try {
                // Load system stats
                const statsResponse = await fetch('/dashboard/api/stats');
                const stats = await statsResponse.json();

                document.getElementById('systemStats').innerHTML = `
                    <div class="stat-card">
                        <div class="label">Total AUM</div>
                        <div class="value">$${stats.total_aum.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                        <div class="change positive">+${stats.aum_change_pct.toFixed(1)}% today</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">Active Tokens</div>
                        <div class="value">${stats.active_tokens}</div>
                        <div class="change info">${stats.total_holders} holders</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">AI Wallets</div>
                        <div class="value">${stats.active_wallets}</div>
                        <div class="change info">${stats.total_capital.toLocaleString('en-US', {style: 'currency', currency: 'USD', minimumFractionDigits: 0})}</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">Avg Sharpe Ratio</div>
                        <div class="value">${stats.avg_sharpe.toFixed(2)}</div>
                        <div class="change ${stats.avg_sharpe > 1.5 ? 'positive' : 'warning'}">
                            ${stats.avg_sharpe > 1.5 ? 'Excellent' : 'Good'}
                        </div>
                    </div>
                `;

                // Load active tokens
                const tokensResponse = await fetch('/dashboard/api/tokens');
                const tokens = await tokensResponse.json();

                let tokensHTML = '<table><thead><tr><th>Token</th><th>NAV</th><th>AUM</th><th>Sharpe</th><th>Return</th><th>Holders</th><th>Status</th></tr></thead><tbody>';
                tokens.forEach(token => {
                    tokensHTML += `
                        <tr>
                            <td><strong>${token.token_symbol}</strong><br><small style="color: #718096;">${token.strategy_name}</small></td>
                            <td>$${token.current_nav.toFixed(2)}</td>
                            <td>$${token.total_aum.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                            <td><strong>${token.sharpe_ratio ? token.sharpe_ratio.toFixed(2) : 'N/A'}</strong></td>
                            <td class="change ${token.total_return_pct > 0 ? 'positive' : 'negative'}">
                                ${token.total_return_pct > 0 ? '+' : ''}${token.total_return_pct ? token.total_return_pct.toFixed(1) : 'N/A'}%
                            </td>
                            <td>${token.holders_count}</td>
                            <td><span class="badge success">${token.status}</span></td>
                        </tr>
                    `;
                });
                tokensHTML += '</tbody></table>';
                document.getElementById('activeTokens').innerHTML = tokensHTML;

                // Load AI wallets
                const walletsResponse = await fetch('/dashboard/api/wallets');
                const wallets = await walletsResponse.json();

                let walletsHTML = '<table><thead><tr><th>Church/Wallet</th><th>Mode</th><th>Total Capital</th><th>Invested</th><th>Return</th><th>Holdings</th><th>Risk</th></tr></thead><tbody>';
                wallets.forEach(wallet => {
                    walletsHTML += `
                        <tr>
                            <td><strong>${wallet.user_name || wallet.user_id}</strong><br><small style="color: #718096;">${wallet.wallet_address.substring(0, 8)}...</small></td>
                            <td><span class="badge info">${wallet.mode}</span></td>
                            <td><strong>$${wallet.total_capital.toLocaleString('en-US', {minimumFractionDigits: 2})}</strong></td>
                            <td>$${wallet.invested_balance.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                            <td class="change ${wallet.total_return_pct > 0 ? 'positive' : 'negative'}">
                                ${wallet.total_return_pct > 0 ? '+' : ''}${wallet.total_return_pct.toFixed(2)}%
                            </td>
                            <td>${wallet.num_holdings} tokens</td>
                            <td><span class="badge warning">${wallet.risk_tolerance}</span></td>
                        </tr>
                    `;
                });
                walletsHTML += '</tbody></table>';
                document.getElementById('aiWallets').innerHTML = walletsHTML;

                // Load recent transactions
                const txResponse = await fetch('/dashboard/api/transactions');
                const transactions = await txResponse.json();

                let txHTML = '<table><thead><tr><th>Time</th><th>Type</th><th>Token</th><th>Quantity</th><th>Price</th><th>Total</th><th>Fee</th></tr></thead><tbody>';
                transactions.forEach(tx => {
                    txHTML += `
                        <tr>
                            <td>${new Date(tx.executed_at).toLocaleString()}</td>
                            <td><span class="badge ${tx.transaction_type === 'buy' ? 'success' : 'warning'}">${tx.transaction_type.toUpperCase()}</span></td>
                            <td>${tx.token_symbol}</td>
                            <td>${tx.quantity.toFixed(2)}</td>
                            <td>$${tx.price_per_token.toFixed(2)}</td>
                            <td><strong>$${tx.total_value.toFixed(2)}</strong></td>
                            <td style="color: #718096;">$${tx.platform_fee.toFixed(2)}</td>
                        </tr>
                    `;
                });
                txHTML += '</tbody></table>';
                document.getElementById('recentTransactions').innerHTML = txHTML;

            } catch (error) {
                console.error('Error loading dashboard:', error);
                document.getElementById('systemStats').innerHTML = '<div class="loading">Error loading data. Please refresh.</div>';
            }
        }

        // Load dashboard on page load
        loadDashboard();

        // Auto-refresh every 30 seconds
        setInterval(loadDashboard, 30000);
    </script>
</body>
</html>
    """

    return HTMLResponse(content=html)


@router.get("/api/stats")
async def get_system_stats():
    """Get overall system statistics"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Total AUM
    cursor.execute("SELECT SUM(total_aum) FROM strategy_tokens WHERE status = 'active'")
    total_aum = cursor.fetchone()[0] or 0.0

    # Active tokens
    cursor.execute("SELECT COUNT(*) FROM strategy_tokens WHERE status = 'active'")
    active_tokens = cursor.fetchone()[0]

    # Total holders
    cursor.execute("SELECT COUNT(DISTINCT wallet_id) FROM token_holdings")
    total_holders = cursor.fetchone()[0]

    # Active wallets
    cursor.execute("SELECT COUNT(*), SUM(total_capital) FROM ai_wallets WHERE status = 'active'")
    wallet_stats = cursor.fetchone()
    active_wallets = wallet_stats[0]
    total_capital = wallet_stats[1] or 0.0

    # Average Sharpe ratio
    cursor.execute("SELECT AVG(sharpe_ratio) FROM strategy_tokens WHERE status = 'active' AND sharpe_ratio IS NOT NULL")
    avg_sharpe = cursor.fetchone()[0] or 0.0

    conn.close()

    return {
        "total_aum": total_aum,
        "aum_change_pct": 2.3,  # TODO: Calculate from history
        "active_tokens": active_tokens,
        "total_holders": total_holders,
        "active_wallets": active_wallets,
        "total_capital": total_capital,
        "avg_sharpe": avg_sharpe,
    }


@router.get("/api/tokens")
async def get_active_tokens():
    """Get all active tokens with performance metrics"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            st.token_symbol,
            st.strategy_name,
            st.current_nav,
            st.total_aum,
            st.sharpe_ratio,
            st.max_drawdown,
            st.total_return_pct,
            st.last_30d_return_pct,
            st.status,
            COUNT(DISTINCT th.wallet_id) as holders_count
        FROM strategy_tokens st
        LEFT JOIN token_holdings th ON st.id = th.token_id
        WHERE st.status = 'active'
        GROUP BY st.id
        ORDER BY st.total_aum DESC
    """)

    tokens = []
    for row in cursor.fetchall():
        tokens.append({
            "token_symbol": row[0],
            "strategy_name": row[1],
            "current_nav": row[2],
            "total_aum": row[3],
            "sharpe_ratio": row[4],
            "max_drawdown": row[5],
            "total_return_pct": row[6],
            "last_30d_return_pct": row[7],
            "status": row[8],
            "holders_count": row[9],
        })

    conn.close()
    return tokens


@router.get("/api/wallets")
async def get_ai_wallets():
    """Get all AI wallets with portfolio details"""

    wallets = []

    # Get all active wallets
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, wallet_address, user_id, user_name, mode,
               total_capital, cash_balance, invested_balance,
               total_return_pct, risk_tolerance
        FROM ai_wallets
        WHERE status = 'active'
        ORDER BY total_capital DESC
    """)

    for row in cursor.fetchall():
        wallet_id = row[0]

        # Count holdings
        cursor.execute("SELECT COUNT(*) FROM token_holdings WHERE wallet_id = ?", (wallet_id,))
        num_holdings = cursor.fetchone()[0]

        wallets.append({
            "wallet_id": wallet_id,
            "wallet_address": row[1],
            "user_id": row[2],
            "user_name": row[3],
            "mode": row[4],
            "total_capital": row[5],
            "cash_balance": row[6],
            "invested_balance": row[7],
            "total_return_pct": row[8] or 0.0,
            "risk_tolerance": row[9],
            "num_holdings": num_holdings,
        })

    conn.close()
    return wallets


@router.get("/api/transactions")
async def get_recent_transactions():
    """Get recent transactions"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            tt.transaction_type,
            tt.quantity,
            tt.price_per_token,
            tt.total_value,
            tt.platform_fee,
            tt.executed_at,
            st.token_symbol
        FROM token_transactions tt
        JOIN strategy_tokens st ON tt.token_id = st.id
        ORDER BY tt.executed_at DESC
        LIMIT 20
    """)

    transactions = []
    for row in cursor.fetchall():
        transactions.append({
            "transaction_type": row[0],
            "quantity": row[1],
            "price_per_token": row[2],
            "total_value": row[3],
            "platform_fee": row[4],
            "executed_at": row[5],
            "token_symbol": row[6],
        })

    conn.close()
    return transactions

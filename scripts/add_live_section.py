#!/usr/bin/env python3
"""Add Live Trading section to dashboard"""

import re

def main():
    with open("/opt/fpai/services/whaletrack-magnet/api/static/whaleminnow/index.html", "r") as f:
        content = f.read()

    # Add CSS for live trading section
    live_css = '''
        /* LIVE TRADING SECTION */
        .live-trading-panel {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 2px solid #f39c12;
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .live-trading-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }
        .live-badge {
            background: #e74c3c;
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: bold;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .live-balance {
            font-size: 1.5rem;
            font-weight: bold;
            color: #f39c12;
        }
        .live-stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.5rem;
            margin-top: 0.5rem;
        }
        .live-stat {
            background: rgba(255,255,255,0.05);
            padding: 0.5rem;
            border-radius: 6px;
            text-align: center;
        }
        .live-stat-label {
            font-size: 0.6rem;
            color: rgba(255,255,255,0.5);
        }
        .live-stat-value {
            font-size: 0.9rem;
            font-weight: bold;
        }
        .live-positions {
            margin-top: 0.75rem;
        }
        .live-position {
            background: rgba(255,255,255,0.05);
            padding: 0.5rem;
            border-radius: 6px;
            margin-top: 0.5rem;
            display: grid;
            grid-template-columns: 1fr 1fr 1fr 1fr;
            gap: 0.5rem;
            align-items: center;
        }
'''

    # Add HTML for live trading section
    live_html = '''
            <!-- LIVE TRADING - Real Hyperliquid Account -->
            <div class="live-trading-panel" id="liveTradingPanel">
                <div class="live-trading-header">
                    <div style="display:flex;align-items:center;gap:0.5rem;">
                        <span style="font-size:1.1rem;font-weight:bold;">🔥 LIVE TRADING</span>
                        <span class="live-badge" id="liveStatus">● LIVE</span>
                    </div>
                    <div class="live-balance" id="liveBalance">$0.00</div>
                </div>
                <div class="live-stats">
                    <div class="live-stat">
                        <div class="live-stat-label">TODAY P&L</div>
                        <div class="live-stat-value" id="liveTodayPnl">$0.00</div>
                    </div>
                    <div class="live-stat">
                        <div class="live-stat-label">TOTAL P&L</div>
                        <div class="live-stat-value" id="liveTotalPnl">$0.00</div>
                    </div>
                    <div class="live-stat">
                        <div class="live-stat-label">TRADES</div>
                        <div class="live-stat-value" id="liveTrades">0</div>
                    </div>
                    <div class="live-stat">
                        <div class="live-stat-label">WIN RATE</div>
                        <div class="live-stat-value" id="liveWinRate">0%</div>
                    </div>
                </div>
                <div class="live-positions" id="livePositions">
                    <div style="font-size:0.75rem;color:rgba(255,255,255,0.5);">No open positions</div>
                </div>
                <div style="margin-top:0.75rem;display:flex;gap:0.5rem;">
                    <button onclick="emergencyStop()" style="background:#e74c3c;color:white;border:none;padding:0.4rem 0.8rem;border-radius:4px;font-size:0.7rem;cursor:pointer;">🚨 EMERGENCY STOP</button>
                    <button onclick="refreshLiveData()" style="background:#3498db;color:white;border:none;padding:0.4rem 0.8rem;border-radius:4px;font-size:0.7rem;cursor:pointer;">🔄 Refresh</button>
                </div>
            </div>
'''

    # Add JavaScript for live trading
    live_js = '''
    // === LIVE TRADING FUNCTIONS ===
    const LIVE_API = window.location.protocol + "//" + window.location.hostname + ":8601";
    
    async function refreshLiveData() {
        try {
            // Get health/balance
            const healthRes = await fetch(LIVE_API + "/health");
            const health = await healthRes.json();
            
            if (health.adapter_connected) {
                document.getElementById("liveBalance").textContent = "$" + health.adapter.balance.toFixed(2);
                document.getElementById("liveStatus").textContent = health.mode === "live" ? "● LIVE" : "● PAPER";
                document.getElementById("liveStatus").style.background = health.mode === "live" ? "#e74c3c" : "#f39c12";
            }
            
            // Get positions
            const posRes = await fetch(LIVE_API + "/api/positions");
            const posData = await posRes.json();
            
            const posContainer = document.getElementById("livePositions");
            if (posData.positions && posData.positions.length > 0) {
                posContainer.innerHTML = posData.positions.map(p => {
                    const pnlColor = (p.pnl || 0) >= 0 ? "#22c55e" : "#ef4444";
                    return '<div class="live-position">' +
                        '<span style="font-weight:bold;">' + p.symbol + '</span>' +
                        '<span style="color:' + (p.side === "long" ? "#22c55e" : "#ef4444") + '">' + (p.side || "").toUpperCase() + '</span>' +
                        '<span>$' + (p.entry_price || 0).toFixed(2) + '</span>' +
                        '<span style="color:' + pnlColor + '">$' + (p.pnl || 0).toFixed(2) + '</span>' +
                    '</div>';
                }).join("");
            } else {
                posContainer.innerHTML = '<div style="font-size:0.75rem;color:rgba(255,255,255,0.5);">No open positions</div>';
            }
            
            // Get stats
            const statsRes = await fetch(LIVE_API + "/api/stats");
            const stats = await statsRes.json();
            
            document.getElementById("liveTotalPnl").textContent = "$" + (stats.total_pnl || 0).toFixed(2);
            document.getElementById("liveTotalPnl").style.color = (stats.total_pnl || 0) >= 0 ? "#22c55e" : "#ef4444";
            document.getElementById("liveTrades").textContent = stats.total_trades || 0;
            document.getElementById("liveWinRate").textContent = (stats.win_rate || 0).toFixed(0) + "%";
            
        } catch (e) {
            console.error("Live data error:", e);
            document.getElementById("liveStatus").textContent = "● OFFLINE";
            document.getElementById("liveStatus").style.background = "#666";
        }
    }
    
    async function emergencyStop() {
        if (!confirm("⚠️ EMERGENCY STOP\\n\\nThis will:\\n- Disable all trading\\n- Close all positions\\n\\nAre you sure?")) return;
        
        try {
            const res = await fetch(LIVE_API + "/api/emergency-stop", { method: "POST" });
            const data = await res.json();
            alert("Emergency stop activated: " + data.status);
            refreshLiveData();
        } catch (e) {
            alert("Error: " + e.message);
        }
    }
    
    // Refresh live data every 30 seconds
    setInterval(refreshLiveData, 30000);
    
    // Initial load
    setTimeout(refreshLiveData, 1000);
'''

    # Insert CSS
    if "/* LIVE TRADING SECTION */" not in content:
        css_insert = content.find("/* MY PORTFOLIO CARDS */")
        if css_insert > 0:
            content = content[:css_insert] + live_css + "\n        " + content[css_insert:]
            print("✅ Added CSS")

    # Insert HTML after MY PORTFOLIO title div
    if "live-trading-panel" not in content:
        html_insert = content.find("<!-- MY PORTFOLIO VIEW")
        if html_insert > 0:
            content = content[:html_insert] + live_html + "\n" + content[html_insert:]
            print("✅ Added HTML")

    # Insert JavaScript before closing </script>
    if "refreshLiveData" not in content:
        # Find the last </script> tag
        js_insert = content.rfind("</script>")
        if js_insert > 0:
            content = content[:js_insert] + live_js + "\n" + content[js_insert:]
            print("✅ Added JavaScript")

    with open("/opt/fpai/services/whaletrack-magnet/api/static/whaleminnow/index.html", "w") as f:
        f.write(content)

    print("Done!")

if __name__ == "__main__":
    main()












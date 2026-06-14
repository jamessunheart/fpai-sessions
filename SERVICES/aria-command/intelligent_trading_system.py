#!/usr/bin/env python3
"""
INTELLIGENT TRADING SYSTEM v2
=============================
Complete feedback loop for adaptive trading.
"""
import sqlite3
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

ACCOUNT = "0xefbfead1189f32bc1000d3740445d0227286b77b"
DB_PATH = "/opt/fpai/aria/intelligent_trader.db"


@dataclass
class TradeDecision:
    should_trade: bool
    symbol: str
    side: str
    size_multiplier: float
    confidence: float
    reasons: List[str]
    risk_score: float


class IntelligentTradingSystem:
    def __init__(self):
        self._ensure_db()
        self.max_correlation_exposure = 2
        self.kelly_cap = 0.25
        
    def _ensure_db(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS trades (
            id TEXT PRIMARY KEY, timestamp TEXT, symbol TEXT, side TEXT,
            exit_price REAL, size REAL, pnl REAL, was_winner INTEGER)""")
        c.execute("""CREATE TABLE IF NOT EXISTS patterns (
            key TEXT PRIMARY KEY, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0,
            total_pnl REAL DEFAULT 0, avg_win REAL DEFAULT 0, avg_loss REAL DEFAULT 0,
            edge REAL DEFAULT 0, kelly REAL DEFAULT 0, last_updated TEXT)""")
        conn.commit()
        conn.close()
    
    def sync_trades(self):
        try:
            r = requests.post("https://api.hyperliquid.xyz/info",
                json={"type": "userFills", "user": ACCOUNT}, timeout=15)
            fills = r.json()
        except:
            return
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        for fill in fills:
            pnl = float(fill.get("closedPnl", 0))
            if pnl == 0:
                continue
            ts = datetime.fromtimestamp(fill["time"] / 1000)
            trade_id = str(fill["oid"]) + "_" + str(fill["time"])
            c.execute("SELECT id FROM trades WHERE id = ?", (trade_id,))
            if c.fetchone():
                continue
            c.execute("INSERT INTO trades VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (trade_id, ts.isoformat(), fill["coin"], fill["side"],
                 float(fill["px"]), float(fill["sz"]), pnl, 1 if pnl > 0 else 0))
        
        conn.commit()
        conn.close()
        self._update_patterns()
    
    def _update_patterns(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # By symbol
        c.execute("""SELECT symbol, COUNT(*), SUM(was_winner), SUM(pnl),
            AVG(CASE WHEN pnl > 0 THEN pnl END), AVG(CASE WHEN pnl < 0 THEN pnl END)
            FROM trades GROUP BY symbol""")
        
        for row in c.fetchall():
            symbol, total, wins, pnl, avg_win, avg_loss = row
            if total < 2:
                continue
            avg_win = avg_win or 0
            avg_loss = avg_loss or 0
            win_rate = wins / total
            edge = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
            if avg_loss != 0 and win_rate > 0:
                b = avg_win / abs(avg_loss)
                kelly = max(0, min((win_rate * b - (1 - win_rate)) / b, self.kelly_cap))
            else:
                kelly = 0
            c.execute("INSERT OR REPLACE INTO patterns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("asset:" + symbol, wins, total - wins, pnl, avg_win, avg_loss, 
                 edge, kelly, datetime.now().isoformat()))
        
        # By direction
        c.execute("""SELECT symbol, side, COUNT(*), SUM(was_winner), SUM(pnl)
            FROM trades GROUP BY symbol, side""")
        for row in c.fetchall():
            symbol, side, total, wins, pnl = row
            direction = "long" if side == "B" else "short"
            c.execute("INSERT OR REPLACE INTO patterns VALUES (?, ?, ?, ?, 0, 0, 0, 0, ?)",
                ("direction:" + symbol + ":" + direction, wins, total - wins, pnl, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_pattern_stats(self, key: str) -> Optional[Dict]:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM patterns WHERE key = ?", (key,))
        row = c.fetchone()
        conn.close()
        if not row:
            return None
        return {"key": row[0], "wins": row[1], "losses": row[2], "total_pnl": row[3],
                "avg_win": row[4], "avg_loss": row[5], "edge": row[6], "kelly": row[7]}
    
    def detect_regime(self, symbol: str) -> Dict:
        try:
            r = requests.post("https://api.hyperliquid.xyz/info",
                json={"type": "candleSnapshot", "req": {
                    "coin": symbol, "interval": "1h", 
                    "startTime": int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
                }}, timeout=10)
            candles = r.json()
            if not candles or len(candles) < 10:
                return {"regime": "unknown", "volatility": 0, "trend": 0}
            closes = [float(c["c"]) for c in candles[-20:]]
            highs = [float(c["h"]) for c in candles[-20:]]
            lows = [float(c["l"]) for c in candles[-20:]]
            atr = sum(h - l for h, l in zip(highs, lows)) / len(highs)
            volatility = atr / closes[-1]
            start_avg = sum(closes[:5]) / 5
            end_avg = sum(closes[-5:]) / 5
            trend = (end_avg - start_avg) / start_avg
            if volatility > 0.03:
                regime = "volatile"
            elif abs(trend) > 0.02:
                regime = "trending_up" if trend > 0 else "trending_down"
            else:
                regime = "ranging"
            return {"regime": regime, "volatility": volatility, "trend": trend}
        except:
            return {"regime": "unknown", "volatility": 0, "trend": 0}
    
    def get_account_state(self) -> Dict:
        try:
            r = requests.post("https://api.hyperliquid.xyz/info",
                json={"type": "clearinghouseState", "user": ACCOUNT}, timeout=10)
            data = r.json()
            value = float(data.get("marginSummary", {}).get("accountValue", 0))
            positions = []
            for pos in data.get("assetPositions", []):
                p = pos.get("position", {})
                size = float(p.get("szi", 0))
                if size != 0:
                    positions.append({"symbol": p.get("coin"), "size": size})
            return {"value": value, "positions": positions}
        except:
            return {"value": 0, "positions": []}
    
    def calculate_risk_score(self, symbol: str, side: str) -> float:
        risk = 0.0
        pattern = self.get_pattern_stats("asset:" + symbol)
        if pattern:
            if pattern["edge"] < 0:
                risk += 0.4
            elif pattern["edge"] < 0.5:
                risk += 0.2
        else:
            risk += 0.3
        direction = "long" if side.lower() in ["long", "buy", "b"] else "short"
        dir_pattern = self.get_pattern_stats("direction:" + symbol + ":" + direction)
        if dir_pattern and dir_pattern["total_pnl"] < 0:
            risk += 0.3
        state = self.get_account_state()
        similar = sum(1 for p in state["positions"] 
            if (p["size"] > 0 and direction == "long") or (p["size"] < 0 and direction == "short"))
        if similar >= self.max_correlation_exposure:
            risk += 0.2
        regime = self.detect_regime(symbol)
        if regime["regime"] == "volatile":
            risk += 0.2
        return min(1.0, risk)
    
    def get_recent_performance(self) -> Dict:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        c.execute("SELECT SUM(pnl), COUNT(*), SUM(was_winner) FROM trades WHERE timestamp > ?", (week_ago,))
        row = c.fetchone()
        conn.close()
        if not row or not row[1]:
            return {"pnl": 0, "trades": 0, "win_rate": 0}
        return {"pnl": row[0] or 0, "trades": row[1], "win_rate": row[2] / row[1] if row[1] else 0}
    
    def get_size_multiplier(self, symbol: str, base_risk: float) -> float:
        pattern = self.get_pattern_stats("asset:" + symbol)
        if pattern and pattern["kelly"] > 0:
            kelly_mult = 1.0 + pattern["kelly"]
        else:
            kelly_mult = 0.5
        perf = self.get_recent_performance()
        if perf["pnl"] < -20:
            perf_mult = 0.5
        elif perf["pnl"] > 20 and perf["win_rate"] > 0.6:
            perf_mult = 1.2
        else:
            perf_mult = 1.0
        risk_mult = max(0.3, 1.0 - base_risk)
        final = kelly_mult * perf_mult * risk_mult
        return round(min(2.0, max(0.1, final)), 2)
    
    def evaluate_trade(self, symbol: str, side: str, signal_strength: float = 1.0) -> TradeDecision:
        self.sync_trades()
        reasons = []
        should_trade = True
        
        pattern = self.get_pattern_stats("asset:" + symbol)
        if pattern:
            if pattern["edge"] < 0:
                should_trade = False
                reasons.append("❌ " + symbol + " has negative edge ($" + str(round(pattern["edge"], 2)) + ")")
            elif pattern["edge"] > 0.5:
                reasons.append("✅ " + symbol + " has positive edge ($" + str(round(pattern["edge"], 2)) + ")")
            else:
                reasons.append("⚠️ " + symbol + " edge marginal ($" + str(round(pattern["edge"], 2)) + ")")
        else:
            reasons.append("⚠️ No history for " + symbol)
        
        direction = "long" if side.lower() in ["long", "buy", "b"] else "short"
        dir_pattern = self.get_pattern_stats("direction:" + symbol + ":" + direction)
        if dir_pattern:
            if dir_pattern["total_pnl"] < -10:
                should_trade = False
                reasons.append("❌ " + symbol + " " + direction + " losing ($" + str(round(dir_pattern["total_pnl"], 2)) + ")")
            elif dir_pattern["total_pnl"] > 10:
                reasons.append("✅ " + symbol + " " + direction + " profitable ($" + str(round(dir_pattern["total_pnl"], 2)) + ")")
        
        regime = self.detect_regime(symbol)
        if regime["regime"] == "volatile":
            reasons.append("⚠️ High volatility")
        elif regime["regime"] == "trending_up" and direction == "short":
            reasons.append("⚠️ Shorting in uptrend")
        elif regime["regime"] == "trending_down" and direction == "long":
            reasons.append("⚠️ Longing in downtrend")
        
        risk_score = self.calculate_risk_score(symbol, side)
        if risk_score > 0.7:
            should_trade = False
            reasons.append("❌ Risk too high (" + str(int(risk_score * 100)) + "%)")
        
        size_mult = self.get_size_multiplier(symbol, risk_score) if should_trade else 0.0
        if signal_strength < 0.5:
            size_mult *= 0.5
            reasons.append("⚠️ Weak signal")
        
        confidence = min(1.0, (1.0 - risk_score) * (1.1 if pattern and pattern["wins"] + pattern["losses"] > 10 else 1.0))
        
        return TradeDecision(should_trade, symbol, direction, size_mult, confidence, reasons, risk_score)
    
    def get_intelligence_summary(self) -> str:
        self.sync_trades()
        lines = ["🧠 INTELLIGENT TRADING SYSTEM", "=" * 50, ""]
        
        lines.append("📊 ASSET INTELLIGENCE:")
        for symbol in ["BTC", "ETH", "SOL"]:
            pattern = self.get_pattern_stats("asset:" + symbol)
            if pattern:
                emoji = "🟢" if pattern["edge"] > 0.5 else "🟡" if pattern["edge"] > 0 else "🔴"
                trades = pattern["wins"] + pattern["losses"]
                lines.append("  " + emoji + " " + symbol + ": " + str(trades) + " trades, edge $" + 
                    str(round(pattern["edge"], 2)) + ", kelly " + str(int(pattern["kelly"] * 100)) + "%")
            else:
                lines.append("  ⚪ " + symbol + ": No data")
        
        lines.append("\n📈 DIRECTION INSIGHTS:")
        for symbol in ["BTC", "ETH", "SOL"]:
            for direction in ["long", "short"]:
                dp = self.get_pattern_stats("direction:" + symbol + ":" + direction)
                if dp:
                    emoji = "🟢" if dp["total_pnl"] > 0 else "🔴"
                    lines.append("  " + emoji + " " + symbol + " " + direction + ": " + 
                        str(dp["wins"]) + "W/" + str(dp["losses"]) + "L, $" + str(round(dp["total_pnl"], 2)))
        
        perf = self.get_recent_performance()
        lines.append("\n📉 LAST 7 DAYS: " + str(perf["trades"]) + " trades, $" + 
            str(round(perf["pnl"], 2)) + ", " + str(int(perf["win_rate"] * 100)) + "% WR")
        
        lines.append("\n💡 RECOMMENDATIONS:")
        for symbol in ["BTC", "ETH", "SOL"]:
            for side in ["long", "short"]:
                decision = self.evaluate_trade(symbol, side)
                emoji = "✅" if decision.should_trade else "❌"
                lines.append("  " + emoji + " " + symbol + " " + side + ": " + 
                    str(decision.size_multiplier) + "x | risk " + str(int(decision.risk_score * 100)) + "%")
        
        return "\n".join(lines)


_system: IntelligentTradingSystem = None

def get_system() -> IntelligentTradingSystem:
    global _system
    if _system is None:
        _system = IntelligentTradingSystem()
    return _system

def should_take_trade(symbol: str, side: str) -> Tuple[bool, float, str]:
    decision = get_system().evaluate_trade(symbol, side)
    reason = " | ".join(decision.reasons[:2])
    return decision.should_trade, decision.size_multiplier, reason

def get_summary() -> str:
    return get_system().get_intelligence_summary()


if __name__ == "__main__":
    print(get_summary())
    print("\n" + "=" * 50)
    print("\nTrade Checks:")
    for symbol in ["BTC", "ETH", "SOL"]:
        for side in ["long", "short"]:
            ok, mult, reason = should_take_trade(symbol, side)
            emoji = "✅" if ok else "❌"
            print(emoji + " " + symbol + " " + side + ": " + str(mult) + "x | " + reason)








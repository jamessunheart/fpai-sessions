#!/usr/bin/env python3
"""
AGGRESSIVE SWEEP TRADER v2.0 - Maximum Intelligence, Maximum Leverage
10x leverage, tight stops, let winners run
WITH TELEGRAM NOTIFICATIONS
"""

import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import requests

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s | %(message)s",
    handlers=[
        logging.FileHandler("/opt/fpai/aria-command/sweep_trader.log"), 
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AggressiveSweep")

HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"
ACCOUNT = os.getenv("HYPERLIQUID_ACCOUNT", "0xefbfead1189f32bc1000d3740445d0227286b77b")

# Telegram Config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8541321124:AAEpkRWpt4jNzVFgAmsJArsHN-QcKGNcoG0")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1759822075")


def send_telegram(message):
    """Send Telegram notification"""
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=10
        )
        return r.status_code == 200
    except:
        return False

# AGGRESSIVE CONFIG - 10x leverage, focus on liquid assets
ASSET_CONFIG = {
    "BTC": {
        "enabled": True, 
        "leverage": 10,
        "stop_pct": 2.0,
        "tp_pct": 6.0,
        "min_conf": 82,
        "position_pct": 25
    },
    "ETH": {
        "enabled": True, 
        "leverage": 10,
        "stop_pct": 2.0,
        "tp_pct": 7.0,
        "min_conf": 83,
        "position_pct": 25
    },
    "SOL": {
        "enabled": True,
        "leverage": 8,
        "stop_pct": 2.5,
        "tp_pct": 5.0,
        "min_conf": 86,
        "position_pct": 15
    },
    "XRP": {
        "enabled": False,
        "leverage": 5,
        "stop_pct": 3.0,
        "tp_pct": 5.0,
        "min_conf": 88,
        "position_pct": 10
    }
}

SYMBOLS = ["BTC", "ETH", "SOL"]


class Candle:
    def __init__(self, t, o, h, l, c, v):
        self.timestamp = t
        self.open = o
        self.high = h
        self.low = l
        self.close = c
        self.volume = v
    
    @property
    def body_size(self): 
        return abs(self.close - self.open)
    
    @property
    def upper_wick(self): 
        return self.high - max(self.open, self.close)
    
    @property
    def lower_wick(self): 
        return min(self.open, self.close) - self.low
    
    @property
    def is_bullish(self): 
        return self.close > self.open
    
    @property
    def range(self): 
        return self.high - self.low


class HyperliquidClient:
    def get_candles(self, symbol, interval="15m", limit=100):
        try:
            r = requests.post(HYPERLIQUID_INFO_URL, json={
                "type": "candleSnapshot", 
                "req": {
                    "coin": symbol, 
                    "interval": interval,
                    "startTime": int((datetime.now() - timedelta(days=7)).timestamp() * 1000),
                    "endTime": int(datetime.now().timestamp() * 1000)
                }
            }, timeout=10)
            if r.status_code != 200: 
                return []
            data = r.json()
            result = []
            for c in data[-limit:]:
                result.append(Candle(c["t"]/1000, float(c["o"]), float(c["h"]), float(c["l"]), float(c["c"]), float(c["v"])))
            return result
        except Exception as e:
            logger.error("Candles error: %s", e)
            return []
    
    def get_account_state(self, address):
        try:
            r = requests.post(HYPERLIQUID_INFO_URL, json={"type": "clearinghouseState", "user": address}, timeout=10)
            return r.json() if r.status_code == 200 else {}
        except: 
            return {}
    
    def get_positions(self, address):
        state = self.get_account_state(address)
        pos = {}
        for p in state.get("assetPositions", []):
            d = p.get("position", {})
            size = float(d.get("szi", 0))
            if size != 0:
                coin = d.get("coin")
                pos[coin] = {
                    "size": size, 
                    "entry": float(d.get("entryPx", 0)),
                    "pnl": float(d.get("unrealizedPnl", 0)), 
                    "dir": "LONG" if size > 0 else "SHORT"
                }
        return pos


class SweepDetector:
    def detect(self, symbol, candles, price):
        if len(candles) < 20: 
            return None
        recent = candles[-20:]
        latest = candles[-1]
        hi = max(c.high for c in recent[:-1])
        lo = min(c.low for c in recent[:-1])
        cfg = ASSET_CONFIG.get(symbol, ASSET_CONFIG["BTC"])
        
        # Lows sweep (bullish reversal)
        if latest.low < lo and latest.close > lo:
            if latest.lower_wick > latest.body_size * 1.5 and latest.is_bullish:
                entry = price
                stop = lo * (1 - cfg["stop_pct"] / 100)
                target = entry * (1 + cfg["tp_pct"] / 100)
                if hi > target: 
                    target = hi * 0.998
                rr = (target - entry) / (entry - stop) if entry > stop else 0
                wick_ratio = latest.lower_wick / latest.range if latest.range > 0 else 0
                conf = min(75 + (wick_ratio * 25), 98)
                
                lev = cfg["leverage"]
                potential_gain = cfg["tp_pct"] * lev
                potential_loss = cfg["stop_pct"] * lev
                
                return {
                    "sym": symbol, "type": "LOWS_SWEEP", "dir": "LONG", 
                    "swept": lo, "entry": entry, "stop": stop, 
                    "target": target, "rr": rr, "conf": conf,
                    "leverage": lev, "potential_gain": potential_gain,
                    "potential_loss": potential_loss
                }
        
        # Highs sweep (bearish reversal)
        if latest.high > hi and latest.close < hi:
            if latest.upper_wick > latest.body_size * 1.5 and not latest.is_bullish:
                entry = price
                stop = hi * (1 + cfg["stop_pct"] / 100)
                target = entry * (1 - cfg["tp_pct"] / 100)
                if lo < target: 
                    target = lo * 1.002
                rr = (entry - target) / (stop - entry) if stop > entry else 0
                wick_ratio = latest.upper_wick / latest.range if latest.range > 0 else 0
                conf = min(75 + (wick_ratio * 25), 98)
                
                lev = cfg["leverage"]
                potential_gain = cfg["tp_pct"] * lev
                potential_loss = cfg["stop_pct"] * lev
                
                return {
                    "sym": symbol, "type": "HIGHS_SWEEP", "dir": "SHORT", 
                    "swept": hi, "entry": entry, "stop": stop, 
                    "target": target, "rr": rr, "conf": conf,
                    "leverage": lev, "potential_gain": potential_gain,
                    "potential_loss": potential_loss
                }
        return None


class AggressiveSweepTrader:
    def __init__(self):
        self.client = HyperliquidClient()
        self.detector = SweepDetector()
        self.db = Path("/opt/fpai/aria-command/sweep_learning.db")
        self._init_db()
        state = self.client.get_account_state(ACCOUNT)
        self.equity = float(state.get("marginSummary", {}).get("accountValue", 500))
        self.start_equity = self.equity
        self.last_hourly = datetime.now()
        self.cycle_count = 0
        
        logger.info("")
        logger.info("*" * 60)
        logger.info("*  AGGRESSIVE SWEEP TRADER v2.0 - MAX LEVERAGE MODE  *")
        logger.info("*" * 60)
        logger.info("")
        logger.info("Account: %s...%s", ACCOUNT[:10], ACCOUNT[-8:])
        logger.info("Equity: $%.2f", self.equity)
        logger.info("")
        logger.info("AGGRESSIVE CONFIG:")
        logger.info("  BTC: 10x lev | 2%% stop | 6%% target | 25%% size")
        logger.info("  ETH: 10x lev | 2%% stop | 7%% target | 25%% size")
        logger.info("  SOL:  8x lev | 2.5%% stop | 5%% target | 15%% size")
        logger.info("  XRP: DISABLED")
        logger.info("")
        logger.info("RISK/REWARD PER TRADE:")
        logger.info("  BTC: Risk 20%% | Reward 60%% of account")
        logger.info("  ETH: Risk 20%% | Reward 70%% of account")
        logger.info("  SOL: Risk 20%% | Reward 40%% of account")
        logger.info("")
        logger.info("*" * 60)
        
        # Send startup notification
        send_telegram(f"""
🚀 <b>AGGRESSIVE SWEEP TRADER STARTED</b>

💰 Equity: <b>${self.equity:,.2f}</b>

<b>Config:</b>
• BTC: 10x | 2% stop | 6% target
• ETH: 10x | 2% stop | 7% target
• SOL: 8x | 2.5% stop | 5% target

Scanning every 15 minutes...
""")
    
    def _init_db(self):
        conn = sqlite3.connect(self.db)
        conn.execute("""CREATE TABLE IF NOT EXISTS aggressive_signals (
            id INTEGER PRIMARY KEY, ts TEXT, sym TEXT, type TEXT, dir TEXT, 
            entry REAL, stop REAL, target REAL, conf REAL, rr REAL, 
            leverage REAL, potential_gain REAL, potential_loss REAL, action TEXT)""")
        conn.commit()
        conn.close()
    
    def log_signal(self, s, action):
        conn = sqlite3.connect(self.db)
        conn.execute(
            "INSERT INTO aggressive_signals VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?)", 
            (datetime.now().isoformat(), s["sym"], s["type"], s["dir"], 
             s["entry"], s["stop"], s["target"], s["conf"], s["rr"],
             s.get("leverage", 10), s.get("potential_gain", 0), 
             s.get("potential_loss", 0), action)
        )
        conn.commit()
        conn.close()
    
    def should_trade(self, s):
        cfg = ASSET_CONFIG.get(s["sym"])
        if not cfg or not cfg["enabled"]: 
            return False, "Disabled"
        if s["conf"] < cfg["min_conf"]: 
            return False, "Conf %.0f < %d" % (s["conf"], cfg["min_conf"])
        if s["rr"] < 1.5: 
            return False, "RR %.1f < 1.5" % s["rr"]
        
        positions = self.client.get_positions(ACCOUNT)
        if s["sym"] in positions: 
            return False, "Already in position"
        
        if len(positions) >= 2:
            return False, "Max 2 positions"
        
        return True, "TRADE SIGNAL!"
    
    async def cycle(self):
        self.cycle_count += 1
        logger.info("")
        logger.info("=" * 60)
        now = datetime.now()
        logger.info("CYCLE: %s", now.strftime("%Y-%m-%d %H:%M:%S"))
        logger.info("=" * 60)
        
        state = self.client.get_account_state(ACCOUNT)
        self.equity = float(state.get("marginSummary", {}).get("accountValue", self.equity))
        positions = self.client.get_positions(ACCOUNT)
        
        logger.info("")
        logger.info("ACCOUNT STATUS:")
        logger.info("  Equity: $%.2f", self.equity)
        
        total_pnl = 0
        pos_list = []
        if positions:
            for coin in positions:
                p = positions[coin]
                sign = "+" if p["pnl"] > 0 else ""
                total_pnl += p["pnl"]
                pnl_pct = (p["pnl"] / self.equity) * 100 if self.equity > 0 else 0
                logger.info("  %s %s @ $%.2f | PnL: %s$%.2f (%s%.1f%%)", 
                           coin, p["dir"], p["entry"], sign, p["pnl"], sign, pnl_pct)
                pos_list.append({"coin": coin, "dir": p["dir"], "pnl": p["pnl"]})
            sign = "+" if total_pnl > 0 else ""
            logger.info("  Total Unrealized: %s$%.2f", sign, total_pnl)
        else:
            logger.info("  No open positions - READY TO HUNT")
        
        # Hourly Telegram update (every 4 cycles = 1 hour)
        if self.cycle_count % 4 == 0:
            change = self.equity - self.start_equity
            sign = "+" if change > 0 else ""
            emoji = "📈" if change > 0 else "📉" if change < 0 else "➖"
            
            msg = f"{emoji} <b>HOURLY UPDATE</b>\n\n"
            msg += f"💰 Equity: <b>${self.equity:,.2f}</b>\n"
            msg += f"📊 Session: {sign}${change:.2f}\n\n"
            
            if pos_list:
                msg += "<b>Positions:</b>\n"
                for p in pos_list:
                    psign = "+" if p["pnl"] > 0 else ""
                    msg += f"• {p['coin']} {p['dir']}: {psign}${p['pnl']:.2f}\n"
            else:
                msg += "🎯 Hunting for sweeps..."
            
            send_telegram(msg)
        
        logger.info("")
        logger.info("SCANNING FOR SWEEPS...")
        
        found_any = False
        for sym in SYMBOLS:
            cfg = ASSET_CONFIG.get(sym, {})
            if not cfg.get("enabled"): 
                continue
            
            candles = self.client.get_candles(sym, "15m", 100)
            if len(candles) < 20: 
                logger.info("  %s: Not enough data", sym)
                continue
            
            sig = self.detector.detect(sym, candles, candles[-1].close)
            if sig:
                found_any = True
                ok, reason = self.should_trade(sig)
                self.log_signal(sig, "TRADE" if ok else "SKIP")
                
                logger.info("")
                logger.info("  >>> SWEEP DETECTED: %s <<<", sym)
                logger.info("      Type: %s -> %s", sig["type"], sig["dir"])
                logger.info("      Swept: $%.2f", sig["swept"])
                logger.info("      Entry: $%.2f", sig["entry"])
                logger.info("      Stop: $%.2f", sig["stop"])
                logger.info("      Target: $%.2f", sig["target"])
                logger.info("      R/R: %.1f:1", sig["rr"])
                logger.info("      Confidence: %.0f%%", sig["conf"])
                logger.info("      Leverage: %dx", sig["leverage"])
                logger.info("      Potential Gain: +%.0f%% of account", sig["potential_gain"])
                logger.info("      Potential Loss: -%.0f%% of account", sig["potential_loss"])
                logger.info("")
                
                # Send Telegram alert for sweep detection
                sweep_msg = f"""
🚨 <b>SWEEP DETECTED!</b>

<b>{sig['sym']}</b> {sig['type']}
Direction: <b>{sig['dir']}</b>

Entry: ${sig['entry']:,.2f}
Stop: ${sig['stop']:,.2f}
Target: ${sig['target']:,.2f}

R/R: {sig['rr']:.1f}:1
Confidence: {sig['conf']:.0f}%
Leverage: {sig['leverage']}x

Potential: +{sig['potential_gain']:.0f}% / -{sig['potential_loss']:.0f}%

Decision: <b>{'TRADE' if ok else 'SKIP'}</b>
{reason}
"""
                send_telegram(sweep_msg)
                
                if ok:
                    logger.info("      *** WOULD EXECUTE: %s %s @ %dx ***", sig["dir"], sym, sig["leverage"])
                else:
                    logger.info("      SKIP: %s", reason)
        
        if not found_any:
            logger.info("  No sweeps detected - waiting for setup")
        
        logger.info("")
        logger.info("Next scan in 15 minutes...")
    
    async def run(self, interval=15):
        logger.info("Starting aggressive loop (every %d min)", interval)
        while True:
            try: 
                await self.cycle()
            except Exception as e: 
                logger.error("Error: %s", e)
            await asyncio.sleep(interval * 60)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--live", action="store_true")
    p.add_argument("--once", action="store_true")
    p.add_argument("--interval", type=int, default=15)
    args = p.parse_args()
    trader = AggressiveSweepTrader()
    if args.once:
        asyncio.run(trader.cycle())
    else:
        asyncio.run(trader.run(args.interval))

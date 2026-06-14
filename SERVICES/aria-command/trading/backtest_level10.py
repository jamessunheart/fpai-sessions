#!/usr/bin/env python3
"""Backtest with Level 10 optimizations"""
import ccxt
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Trade:
    symbol: str
    side: str
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: str = ""
    size: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    highest: float = 0.0

# LEVEL 10 PARAMETERS
INITIAL_CAPITAL = 500.0
BASE_POSITION_PCT = 0.3
MIN_CONFIDENCE = 80.0
INITIAL_STOP_PCT = 1.0
BREAKEVEN_TRIGGER = 1.0
TRAIL_ACTIVATION = 2.0
TRAIL_DISTANCE = 1.0
MAX_HOLD_HOURS_LOSER = 2
MIN_TREND_STRENGTH = 0.15

def fetch_data(symbol, days=90):
    exchange = ccxt.okx()
    ohlcv = exchange.fetch_ohlcv(f"{symbol}/USDT", "1h", limit=days*24)
    return [{
        "time": datetime.fromtimestamp(c[0]/1000),
        "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]
    } for c in ohlcv]

def calculate_signals(klines):
    signals = []
    if len(klines) < 20:
        return signals
    
    for i in range(20, len(klines)):
        candle = klines[i]
        
        gains, losses = [], []
        for j in range(i-14, i):
            change = klines[j+1]["close"] - klines[j]["close"]
            gains.append(change if change > 0 else 0)
            losses.append(abs(change) if change < 0 else 0)
        
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        rsi = 100 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss))
        
        closes = [klines[j]["close"] for j in range(i-20, i+1)]
        ma7 = sum(closes[-7:]) / 7
        ma20 = sum(closes) / 21
        
        trend_strength = abs(ma7 - ma20) / ma20
        
        action = "WAIT"
        confidence = 50.0
        
        if trend_strength < MIN_TREND_STRENGTH:
            signals.append({
                "time": candle["time"],
                "price": candle["close"],
                "high": candle["high"],
                "low": candle["low"],
                "action": "WAIT",
                "confidence": 0
            })
            continue
        
        if ma7 > ma20:
            if rsi < 35:
                action = "LONG"
                confidence = min(95, 65 + (35 - rsi))
            elif rsi < 50:
                action = "LONG"
                confidence = 80
        elif ma7 < ma20:
            if rsi > 65:
                action = "SHORT"
                confidence = min(95, 65 + (rsi - 65))
            elif rsi > 50:
                action = "SHORT"
                confidence = 80
        
        signals.append({
            "time": candle["time"],
            "price": candle["close"],
            "high": candle["high"],
            "low": candle["low"],
            "action": action,
            "confidence": confidence
        })
    
    return signals

def backtest(signals, symbol):
    capital = INITIAL_CAPITAL
    trades = []
    position = None
    peak = capital
    max_dd = 0
    
    for sig in signals:
        if position:
            if position.side == "long":
                if sig["high"] > position.highest:
                    position.highest = sig["high"]
            else:
                if position.highest == 0 or sig["low"] < position.highest:
                    position.highest = sig["low"]
            
            if position.side == "long":
                pnl_pct = (sig["price"] - position.entry_price) / position.entry_price * 100
                max_pnl = (position.highest - position.entry_price) / position.entry_price * 100
            else:
                pnl_pct = (position.entry_price - sig["price"]) / position.entry_price * 100
                max_pnl = (position.entry_price - position.highest) / position.entry_price * 100
            
            exit_reason = None
            exit_price = sig["price"]
            
            if position.side == "long":
                current_stop = position.entry_price * (1 - INITIAL_STOP_PCT/100)
            else:
                current_stop = position.entry_price * (1 + INITIAL_STOP_PCT/100)
            
            if max_pnl >= BREAKEVEN_TRIGGER:
                current_stop = position.entry_price
            
            if max_pnl >= TRAIL_ACTIVATION:
                if position.side == "long":
                    trail_stop = position.highest * (1 - TRAIL_DISTANCE/100)
                    if trail_stop > current_stop:
                        current_stop = trail_stop
                else:
                    trail_stop = position.highest * (1 + TRAIL_DISTANCE/100)
                    if trail_stop < current_stop:
                        current_stop = trail_stop
            
            if position.side == "long":
                if sig["low"] <= current_stop:
                    exit_reason = "STOP" if max_pnl < BREAKEVEN_TRIGGER else "TRAIL"
                    exit_price = current_stop
            else:
                if sig["high"] >= current_stop:
                    exit_reason = "STOP" if max_pnl < BREAKEVEN_TRIGGER else "TRAIL"
                    exit_price = current_stop
            
            hold_hrs = (sig["time"] - position.entry_time).total_seconds() / 3600
            if not exit_reason and pnl_pct < 0 and hold_hrs >= MAX_HOLD_HOURS_LOSER:
                exit_reason = "TIME_LOSER"
            
            if not exit_reason:
                if position.side == "long" and sig["action"] == "SHORT":
                    exit_reason = "REVERSAL"
                elif position.side == "short" and sig["action"] == "LONG":
                    exit_reason = "REVERSAL"
            
            if exit_reason:
                if position.side == "long":
                    pnl = (exit_price - position.entry_price) * position.size
                    pnl_pct = (exit_price - position.entry_price) / position.entry_price * 100
                else:
                    pnl = (position.entry_price - exit_price) * position.size
                    pnl_pct = (position.entry_price - exit_price) / position.entry_price * 100
                
                position.exit_time = sig["time"]
                position.exit_price = exit_price
                position.exit_reason = exit_reason
                position.pnl = pnl
                position.pnl_pct = pnl_pct
                capital += pnl
                trades.append(position)
                position = None
                
                if capital > peak:
                    peak = capital
                dd = (peak - capital) / peak * 100
                if dd > max_dd:
                    max_dd = dd
        
        if not position and sig["action"] != "WAIT" and sig["confidence"] >= MIN_CONFIDENCE:
            size = (capital * BASE_POSITION_PCT) / sig["price"]
            position = Trade(
                symbol=symbol,
                side="long" if sig["action"] == "LONG" else "short",
                entry_time=sig["time"],
                entry_price=sig["price"],
                size=size,
                highest=sig["price"]
            )
    
    wins = [t for t in trades if t.pnl > 0]
    return {
        "symbol": symbol,
        "trades": trades,
        "total": len(trades),
        "wins": len(wins),
        "win_rate": len(wins)/len(trades)*100 if trades else 0,
        "pnl": sum(t.pnl for t in trades),
        "max_dd": max_dd,
        "final": capital
    }

if __name__ == "__main__":
    sep = "=" * 70
    print(sep)
    print("LEVEL 10 STRATEGY BACKTEST")
    print(sep)
    print("OPTIMIZATIONS:")
    print("  - Skip ranging markets (trend strength < 15%)")
    print("  - Higher confidence threshold (80%)")
    print("  - Tighter initial stop (1%)")
    print("  - Trailing stop after +2%")
    print("  - Only time-exit losers")
    print()

    all_trades = []
    total_pnl = 0

    for symbol in ["SOL", "BTC", "ETH"]:
        print(f"Testing {symbol}...")
        klines = fetch_data(symbol, 90)
        signals = calculate_signals(klines)
        result = backtest(signals, symbol)
        all_trades.extend(result["trades"])
        total_pnl += result["pnl"]
        t = result["total"]
        wr = result["win_rate"]
        p = result["pnl"]
        print(f"  {symbol}: {t} trades | {wr:.0f}% WR | ${p:+.2f}")

    print()
    print(sep)
    print("COMPARISON: OLD vs LEVEL 10")
    print(sep)
    
    old_trades = 192
    old_wins = 92
    old_pnl = -34.61
    old_wr = 48

    new_trades = len(all_trades)
    new_wins = len([t for t in all_trades if t.pnl > 0])
    new_wr = new_wins/new_trades*100 if new_trades else 0

    print(f"                    OLD         LEVEL 10     CHANGE")
    print(f"Trades:             {old_trades}          {new_trades}            {new_trades - old_trades:+}")
    print(f"Win Rate:           {old_wr}%          {new_wr:.0f}%           {new_wr - old_wr:+.0f}%")
    print(f"P&L:                ${old_pnl:+.2f}     ${total_pnl:+.2f}      ${total_pnl - old_pnl:+.2f}")
    print(f"Final Capital:      ${500+old_pnl:.2f}     ${500+total_pnl:.2f}")
    print()

    if new_trades > 0:
        print(sep)
        print("SAMPLE TRADES")
        print(sep)
        all_trades.sort(key=lambda t: t.entry_time)
        for i, t in enumerate(all_trades[:10], 1):
            entry = t.entry_time.strftime("%m/%d %H:%M")
            exit_str = t.exit_time.strftime("%m/%d %H:%M") if t.exit_time else "OPEN"
            emoji = "+" if t.pnl > 0 else "-"
            print(f"#{i} {t.symbol:3} {t.side:5} | {entry} -> {exit_str} | {emoji}${abs(t.pnl):.2f} ({t.pnl_pct:+.1f}%) | {t.exit_reason}")










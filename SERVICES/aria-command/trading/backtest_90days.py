#!/usr/bin/env python3
"""90-Day Backtest for Adaptive Intelligence Strategy"""

import asyncio
import httpx
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional

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

@dataclass 
class BacktestConfig:
    initial_capital: float = 500.0
    position_pct: float = 0.5
    stop_loss_pct: float = 1.5
    take_profit_pct: float = 3.0
    max_hold_hours: int = 2
    min_confidence: float = 70.0
    min_rr: float = 1.5

async def fetch_historical_klines(symbol: str, days: int = 90) -> List[Dict]:
    klines = []
    base_url = "https://api.binance.com/api/v3/klines"
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    interval = "1h"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        current_start = start_time
        while current_start < end_time:
            params = {
                "symbol": f"{symbol}USDT",
                "interval": interval,
                "startTime": current_start,
                "endTime": end_time,
                "limit": 1000
            }
            try:
                r = await client.get(base_url, params=params)
                if r.status_code == 200:
                    data = r.json()
                    for k in data:
                        klines.append({
                            "time": datetime.fromtimestamp(k[0] / 1000),
                            "open": float(k[1]),
                            "high": float(k[2]),
                            "low": float(k[3]),
                            "close": float(k[4]),
                            "volume": float(k[5])
                        })
                    if len(data) < 1000:
                        break
                    current_start = data[-1][0] + 1
                else:
                    break
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
                break
    return klines

def calculate_signals(klines: List[Dict]) -> List[Dict]:
    signals = []
    if len(klines) < 20:
        return signals
    
    for i in range(20, len(klines)):
        candle = klines[i]
        
        # RSI
        gains, losses = [], []
        for j in range(i-14, i):
            change = klines[j+1]["close"] - klines[j]["close"]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        rsi = 100 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss))
        
        # MAs
        closes = [klines[j]["close"] for j in range(i-20, i+1)]
        ma7 = sum(closes[-7:]) / 7
        ma20 = sum(closes) / 21
        
        # Signal logic
        action = "WAIT"
        confidence = 50.0
        bias_strength = 0.0
        
        if ma7 > ma20:
            bias_strength = ((ma7 - ma20) / ma20) * 100
            if rsi < 40:
                action = "LONG"
                confidence = min(90, 60 + (40 - rsi))
            elif rsi < 55:
                action = "LONG"
                confidence = 70
        elif ma7 < ma20:
            bias_strength = ((ma20 - ma7) / ma20) * 100
            if rsi > 60:
                action = "SHORT"
                confidence = min(90, 60 + (rsi - 60))
            elif rsi > 45:
                action = "SHORT"
                confidence = 70
        
        # R:R
        rr = 0
        stop_loss = 0
        target = 0
        if action == "LONG":
            stop_loss = candle["close"] * 0.985
            target = candle["close"] * 1.03
            risk = candle["close"] - stop_loss
            reward = target - candle["close"]
            rr = reward / risk if risk > 0 else 0
        elif action == "SHORT":
            stop_loss = candle["close"] * 1.015
            target = candle["close"] * 0.97
            risk = stop_loss - candle["close"]
            reward = candle["close"] - target
            rr = reward / risk if risk > 0 else 0
        
        signals.append({
            "time": candle["time"],
            "price": candle["close"],
            "high": candle["high"],
            "low": candle["low"],
            "action": action,
            "confidence": confidence,
            "bias_strength": bias_strength,
            "risk_reward": rr,
            "stop_loss": stop_loss,
            "target": target
        })
    
    return signals

def run_backtest(signals: List[Dict], symbol: str, config: BacktestConfig) -> Dict:
    capital = config.initial_capital
    trades: List[Trade] = []
    position: Optional[Trade] = None
    peak_capital = capital
    max_drawdown = 0
    
    for i, sig in enumerate(signals):
        current_time = sig["time"]
        current_price = sig["price"]
        
        if position:
            if position.side == "long":
                pnl_pct = (current_price - position.entry_price) / position.entry_price * 100
                hit_stop = sig["low"] <= position.entry_price * (1 - config.stop_loss_pct / 100)
                hit_tp = sig["high"] >= position.entry_price * (1 + config.take_profit_pct / 100)
            else:
                pnl_pct = (position.entry_price - current_price) / position.entry_price * 100
                hit_stop = sig["high"] >= position.entry_price * (1 + config.stop_loss_pct / 100)
                hit_tp = sig["low"] <= position.entry_price * (1 - config.take_profit_pct / 100)
            
            hold_hours = (current_time - position.entry_time).total_seconds() / 3600
            
            exit_reason = None
            exit_price = current_price
            
            if hit_stop:
                exit_reason = "STOP_LOSS"
                if position.side == "long":
                    exit_price = position.entry_price * (1 - config.stop_loss_pct / 100)
                else:
                    exit_price = position.entry_price * (1 + config.stop_loss_pct / 100)
            elif hit_tp:
                exit_reason = "TAKE_PROFIT"
                if position.side == "long":
                    exit_price = position.entry_price * (1 + config.take_profit_pct / 100)
                else:
                    exit_price = position.entry_price * (1 - config.take_profit_pct / 100)
            elif hold_hours >= config.max_hold_hours:
                exit_reason = "TIME_EXIT"
            elif position.side == "long" and sig["action"] == "SHORT":
                exit_reason = "SIGNAL_REVERSAL"
            elif position.side == "short" and sig["action"] == "LONG":
                exit_reason = "SIGNAL_REVERSAL"
            
            if exit_reason:
                if position.side == "long":
                    pnl = (exit_price - position.entry_price) * position.size
                    pnl_pct = (exit_price - position.entry_price) / position.entry_price * 100
                else:
                    pnl = (position.entry_price - exit_price) * position.size
                    pnl_pct = (position.entry_price - exit_price) / position.entry_price * 100
                
                position.exit_time = current_time
                position.exit_price = exit_price
                position.exit_reason = exit_reason
                position.pnl = pnl
                position.pnl_pct = pnl_pct
                
                capital += pnl
                trades.append(position)
                position = None
                
                if capital > peak_capital:
                    peak_capital = capital
                dd = (peak_capital - capital) / peak_capital * 100
                if dd > max_drawdown:
                    max_drawdown = dd
        
        if not position:
            if sig["action"] == "WAIT":
                continue
            if sig["confidence"] < config.min_confidence:
                continue
            if sig["risk_reward"] < config.min_rr:
                continue
            
            size = (capital * config.position_pct) / current_price
            position = Trade(
                symbol=symbol,
                side="long" if sig["action"] == "LONG" else "short",
                entry_time=current_time,
                entry_price=current_price,
                size=size
            )
    
    if position and signals:
        last = signals[-1]
        if position.side == "long":
            pnl = (last["price"] - position.entry_price) * position.size
            pnl_pct = (last["price"] - position.entry_price) / position.entry_price * 100
        else:
            pnl = (position.entry_price - last["price"]) * position.size
            pnl_pct = (position.entry_price - last["price"]) / position.entry_price * 100
        position.exit_time = last["time"]
        position.exit_price = last["price"]
        position.exit_reason = "END_OF_DATA"
        position.pnl = pnl
        position.pnl_pct = pnl_pct
        capital += pnl
        trades.append(position)
    
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    total_pnl = sum(t.pnl for t in trades)
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.pnl for t in losses) / len(losses) if losses else 0
    pf = abs(sum(t.pnl for t in wins) / sum(t.pnl for t in losses)) if losses and sum(t.pnl for t in losses) != 0 else 0
    
    return {
        "symbol": symbol,
        "trades": trades,
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "final_capital": capital,
        "return_pct": (capital - config.initial_capital) / config.initial_capital * 100,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "max_drawdown": max_drawdown,
        "profit_factor": pf
    }

async def main():
    config = BacktestConfig()
    symbols = ["SOL", "BTC", "ETH"]
    all_results = {}
    all_trades = []
    
    sep = "=" * 70
    print(sep)
    print("90-DAY BACKTEST - ADAPTIVE INTELLIGENCE STRATEGY")
    print(sep)
    print(f"\nStarting Capital: ${config.initial_capital:,.2f}")
    print(f"Position Size: {config.position_pct * 100:.0f}% per trade")
    print(f"Stop Loss: {config.stop_loss_pct}%  |  Take Profit: {config.take_profit_pct}%")
    print(f"Max Hold: {config.max_hold_hours} hours  |  Min Confidence: {config.min_confidence}%")
    
    for symbol in symbols:
        print(f"\nFetching {symbol} data...")
        klines = await fetch_historical_klines(symbol, days=90)
        print(f"  Got {len(klines)} hourly candles")
        
        signals = calculate_signals(klines)
        result = run_backtest(signals, symbol, config)
        all_results[symbol] = result
        all_trades.extend(result["trades"])
        
        print(f"\n{symbol} RESULTS:")
        print(f"  Trades: {result['total_trades']} | Win Rate: {result['win_rate']:.1f}%")
        print(f"  P&L: ${result['total_pnl']:+,.2f} | Max DD: {result['max_drawdown']:.1f}%")
    
    total_pnl = sum(r["total_pnl"] for r in all_results.values())
    total_trades = sum(r["total_trades"] for r in all_results.values())
    total_wins = sum(r["wins"] for r in all_results.values())
    
    print("\n" + sep)
    print("COMBINED RESULTS")
    print(sep)
    print(f"Total Trades: {total_trades}")
    if total_trades:
        print(f"Win Rate: {total_wins / total_trades * 100:.1f}%")
    print(f"Total P&L: ${total_pnl:+,.2f}")
    print(f"Final Capital: ${500 + total_pnl:,.2f}")
    print(f"Return: {total_pnl / 500 * 100:+.1f}%")
    
    all_trades.sort(key=lambda t: t.entry_time)
    
    print("\n" + sep)
    print("ALL TRADES (Chronological)")
    print(sep)
    
    running = 500.0
    for i, t in enumerate(all_trades, 1):
        running += t.pnl
        entry_str = t.entry_time.strftime("%m/%d %H:%M")
        exit_str = t.exit_time.strftime("%m/%d %H:%M")
        print(f"\n#{i} {t.symbol} {t.side.upper()}")
        print(f"   Entry: {entry_str} @ ${t.entry_price:,.2f}")
        print(f"   Exit:  {exit_str} @ ${t.exit_price:,.2f} ({t.exit_reason})")
        print(f"   P&L: ${t.pnl:+.2f} ({t.pnl_pct:+.2f}%) | Balance: ${running:,.2f}")
    
    print("\n" + sep)
    print("FINAL SUMMARY")
    print(sep)
    print(f"$500.00 -> ${500 + total_pnl:,.2f} ({total_pnl / 500 * 100:+.1f}%)")
    if total_trades:
        print(f"{total_trades} trades | {total_wins} wins | Win Rate: {total_wins/total_trades*100:.0f}%")

if __name__ == "__main__":
    asyncio.run(main())










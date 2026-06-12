#!/usr/bin/env python3
"""
TRUE LEVEL 10 AUTO-TRADER - FIXED VERSION
==========================================
Fixed: Exchange wallet initialization
Improved: More active trading with shorter timeframes
"""

import asyncio
import logging
import ccxt
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, List
import json
import os
import httpx
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/opt/fpai/aria-command/level10_trader.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========== CONFIGURATION ==========

@dataclass
class Config:
    # More active thresholds
    rsi_oversold: float = 40.0       # Was 35 - now triggers more often
    rsi_overbought: float = 60.0     # Was 65 - now triggers more often
    trend_rsi_long: float = 45.0
    trend_rsi_short: float = 55.0
    trend_slope_threshold: float = 0.5   # Was 1.0 - more sensitive
    
    # Risk management
    stop_loss_pct: float = 1.5       # Tighter stop
    take_profit_pct: float = 1.0     # Quick profit taking
    max_hold_hours: int = 8          # Faster rotation
    
    # Position sizing
    leverage: float = 3.0
    position_pct: float = 0.80
    
    # Symbols
    symbols: List[str] = None
    
    # Timing - check every 2 minutes for more activity
    check_interval_seconds: int = 120
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["SOL", "ETH", "BTC"]

@dataclass
class Position:
    symbol: str
    side: str
    entry_price: float
    entry_time: datetime
    size: float
    stop_price: float
    target_price: float

# ========== HYPERLIQUID CLIENT (FIXED) ==========

class HyperliquidClient:
    def __init__(self):
        self.connected = False
        self.api_key = None
        self.api_secret = None
        self.main_account = None
        self.wallet = None
        self._load_credentials()
    
    def _load_credentials(self):
        try:
            creds_path = "/opt/fpai/hyperliquid_credentials.json"
            if os.path.exists(creds_path):
                with open(creds_path) as f:
                    creds = json.load(f)
                    self.api_key = creds.get("api_key")
                    self.api_secret = creds.get("api_secret")
                    self.main_account = creds.get("main_account")
                    
                    # Create proper wallet object from private key
                    from eth_account import Account
                    self.wallet = Account.from_key(self.api_secret)
                    
                    self.connected = True
                    wallet_preview = self.main_account[:10] if self.main_account else "unknown"
                    logger.info(f"Hyperliquid connected: {wallet_preview}...")
            else:
                logger.warning("No Hyperliquid credentials found")
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            import traceback
            traceback.print_exc()
    
    async def get_balance(self) -> float:
        """Get account balance via REST API"""
        try:
            response = requests.post(
                "https://api.hyperliquid.xyz/info",
                json={"type": "clearinghouseState", "user": self.main_account},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return float(data.get("marginSummary", {}).get("accountValue", 0))
            return 0
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return 0
    
    async def get_positions(self) -> List[Dict]:
        """Get open positions via REST API"""
        try:
            response = requests.post(
                "https://api.hyperliquid.xyz/info",
                json={"type": "clearinghouseState", "user": self.main_account},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                positions = []
                for pos in data.get("assetPositions", []):
                    p = pos.get("position", {})
                    size = float(p.get("szi", 0))
                    if size != 0:
                        positions.append({
                            "symbol": p.get("coin"),
                            "size": size,
                            "entry_price": float(p.get("entryPx", 0)),
                            "unrealized_pnl": float(p.get("unrealizedPnl", 0))
                        })
                return positions
            return []
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    async def get_price(self, symbol: str) -> float:
        """Get current price"""
        try:
            response = requests.post(
                "https://api.hyperliquid.xyz/info",
                json={"type": "allMids"},
                timeout=10
            )
            if response.status_code == 200:
                mids = response.json()
                return float(mids.get(symbol, 0))
            return 0
        except Exception as e:
            logger.error(f"Failed to get price: {e}")
            return 0
    
    async def place_order(self, symbol: str, side: str, size: float, reduce_only: bool = False) -> Dict:
        """Place a market order using proper wallet authentication"""
        try:
            from hyperliquid.exchange import Exchange
            from hyperliquid.utils import constants
            
            # Create exchange with proper wallet object
            exchange = Exchange(
                wallet=self.wallet,
                base_url=constants.MAINNET_API_URL,
                account_address=self.main_account
            )
            
            is_buy = side.lower() in ["buy", "long"]
            
            if reduce_only:
                # Close position
                result = exchange.market_close(
                    coin=symbol,
                    sz=round(abs(size), 4)
                )
            else:
                # Open position
                result = exchange.market_open(
                    name=symbol,
                    is_buy=is_buy,
                    sz=round(abs(size), 4)
                )
            
            if result.get("status") == "ok":
                logger.info(f"Order executed: {side} {size:.4f} {symbol}")
                return {"success": True, "result": result}
            else:
                logger.warning(f"Order returned: {result}")
                return {"success": False, "error": str(result)}
                
        except Exception as e:
            logger.error(f"Order failed: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    async def close_position(self, symbol: str, size: float) -> Dict:
        """Close a position"""
        return await self.place_order(symbol, "sell" if size > 0 else "buy", abs(size), reduce_only=True)

# ========== STRATEGY ==========

class ActiveScalpingStrategy:
    """More active trading strategy"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def calculate_indicators(self, candles: List[Dict]) -> Optional[Dict]:
        if len(candles) < 20:
            return None
        
        closes = [c["close"] for c in candles]
        
        # RSI (14 period)
        gains, losses = [], []
        for i in range(-14, 0):
            change = closes[i] - closes[i-1]
            gains.append(change if change > 0 else 0)
            losses.append(abs(change) if change < 0 else 0)
        
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        rsi = 100 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss))
        
        # Moving averages
        ma7 = sum(closes[-7:]) / 7
        ma20 = sum(closes[-20:]) / 20
        
        # Momentum
        momentum = (closes[-1] - closes[-5]) / closes[-5] * 100 if closes[-5] > 0 else 0
        
        # Volatility (simple)
        highs = [c["high"] for c in candles[-10:]]
        lows = [c["low"] for c in candles[-10:]]
        volatility = (max(highs) - min(lows)) / closes[-1] * 100 if closes[-1] > 0 else 0
        
        return {
            "rsi": rsi,
            "ma7": ma7,
            "ma20": ma20,
            "price": closes[-1],
            "momentum": momentum,
            "volatility": volatility,
            "trend": "up" if ma7 > ma20 else "down"
        }
    
    def get_signal(self, ind: Dict) -> Optional[str]:
        rsi = ind["rsi"]
        price = ind["price"]
        ma7 = ind["ma7"]
        ma20 = ind["ma20"]
        momentum = ind["momentum"]
        
        # Oversold bounce
        if rsi < self.config.rsi_oversold and momentum > -1:
            return "LONG"
        
        # Overbought fade
        if rsi > self.config.rsi_overbought and momentum < 1:
            return "SHORT"
        
        # Trend following with momentum
        if ind["trend"] == "up" and rsi < 50 and momentum > 0.5:
            return "LONG"
        
        if ind["trend"] == "down" and rsi > 50 and momentum < -0.5:
            return "SHORT"
        
        return None

# ========== TELEGRAM ==========

async def send_telegram(message: str):
    try:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "7508820098:AAHLkjSLdVwj8BbO1zgDW9dJXiDO7xhL_m8")
        chat_id = 1275066656
        
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
                timeout=10
            )
    except Exception as e:
        logger.error(f"Telegram failed: {e}")

# ========== MAIN TRADER ==========

class Level10Trader:
    def __init__(self):
        self.config = Config()
        self.strategy = ActiveScalpingStrategy(self.config)
        self.client = HyperliquidClient()
        self.positions: Dict[str, Position] = {}
        self.last_signal_time: Dict[str, datetime] = {}
        
        # Stats
        self.trades_today = 0
        self.start_balance = 0.0
    
    async def run(self):
        logger.info("LEVEL 10 SCALPER STARTING (FIXED)")
        
        if not self.client.connected:
            logger.error("Client not connected - cannot trade")
            await send_telegram("TRADER FAILED TO START - Credentials issue")
            return
        
        self.start_balance = await self.client.get_balance()
        logger.info(f"Starting balance: ${self.start_balance:.2f}")
        
        symbols_str = ", ".join(self.config.symbols)
        await send_telegram(
            f"<b>LEVEL 10 SCALPER STARTED</b>\n"
            f"Balance: ${self.start_balance:.2f}\n"
            f"Symbols: {symbols_str}\n"
            f"Check interval: {self.config.check_interval_seconds}s\n"
            f"Leverage: {self.config.leverage}x"
        )
        
        await self._recover_positions()
        
        cycle = 0
        while True:
            try:
                cycle += 1
                logger.info(f"--- Cycle {cycle} ---")
                
                for symbol in self.config.symbols:
                    await self._check_symbol(symbol)
                    await asyncio.sleep(1)
                
                # Log status every 10 cycles
                if cycle % 10 == 0:
                    balance = await self.client.get_balance()
                    pos_count = len(self.positions)
                    logger.info(f"Status: ${balance:.2f} | {pos_count} positions | {self.trades_today} trades today")
                
                await asyncio.sleep(self.config.check_interval_seconds)
                
            except Exception as e:
                logger.error(f"Loop error: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(30)
    
    async def _recover_positions(self):
        positions = await self.client.get_positions()
        for p in positions:
            symbol = p["symbol"]
            size = p["size"]
            entry = p["entry_price"]
            side = "long" if size > 0 else "short"
            
            stop = entry * (1 - self.config.stop_loss_pct/100) if side == "long" else entry * (1 + self.config.stop_loss_pct/100)
            target = entry * (1 + self.config.take_profit_pct/100) if side == "long" else entry * (1 - self.config.take_profit_pct/100)
            
            self.positions[symbol] = Position(
                symbol=symbol,
                side=side,
                entry_price=entry,
                entry_time=datetime.now() - timedelta(hours=1),
                size=abs(size),
                stop_price=stop,
                target_price=target
            )
            logger.info(f"Recovered: {side.upper()} {symbol} @ ${entry:.2f}")
    
    async def _fetch_candles(self, symbol: str) -> List[Dict]:
        """Fetch 1h candles for more active trading"""
        try:
            exchange = ccxt.okx()
            ohlcv = exchange.fetch_ohlcv(f"{symbol}/USDT", "1h", limit=30)
            return [{"close": c[4], "high": c[2], "low": c[3]} for c in ohlcv]
        except Exception as e:
            logger.error(f"Failed to fetch {symbol}: {e}")
            return []
    
    async def _check_symbol(self, symbol: str):
        candles = await self._fetch_candles(symbol)
        if not candles or len(candles) < 20:
            return
        
        indicators = self.strategy.calculate_indicators(candles)
        if not indicators:
            return
        
        # Get current price
        price = await self.client.get_price(symbol)
        if price > 0:
            indicators["price"] = price
        
        if symbol in self.positions:
            await self._manage_position(symbol, indicators)
        else:
            await self._check_entry(symbol, indicators)
    
    async def _check_entry(self, symbol: str, ind: Dict):
        # Rate limit: no signal within 30 minutes
        last_signal = self.last_signal_time.get(symbol)
        if last_signal and (datetime.now() - last_signal).total_seconds() < 1800:
            return
        
        signal = self.strategy.get_signal(ind)
        if not signal:
            return
        
        # Check if we already have too many positions
        if len(self.positions) >= 2:
            return
        
        balance = await self.client.get_balance()
        if balance < 50:
            return
        
        position_value = balance * self.config.position_pct * self.config.leverage
        size = position_value / ind["price"]
        
        if signal == "LONG":
            stop = ind["price"] * (1 - self.config.stop_loss_pct/100)
            target = ind["price"] * (1 + self.config.take_profit_pct/100)
            side = "buy"
        else:
            stop = ind["price"] * (1 + self.config.stop_loss_pct/100)
            target = ind["price"] * (1 - self.config.take_profit_pct/100)
            side = "sell"
        
        price_str = f"${ind['price']:.2f}"
        rsi_str = f"{ind['rsi']:.1f}"
        logger.info(f"Signal: {signal} {symbol} @ {price_str} (RSI: {rsi_str})")
        
        result = await self.client.place_order(symbol, side, size)
        
        if result.get("success"):
            self.positions[symbol] = Position(
                symbol=symbol,
                side="long" if signal == "LONG" else "short",
                entry_price=ind["price"],
                entry_time=datetime.now(),
                size=size,
                stop_price=stop,
                target_price=target
            )
            self.last_signal_time[symbol] = datetime.now()
            self.trades_today += 1
            
            await send_telegram(
                f"<b>{signal} {symbol}</b>\n"
                f"Entry: {price_str}\n"
                f"Size: {size:.4f}\n"
                f"Stop: ${stop:.2f}\n"
                f"Target: ${target:.2f}\n"
                f"RSI: {rsi_str}"
            )
        else:
            logger.warning(f"Order failed: {result.get('error')}")
    
    async def _manage_position(self, symbol: str, ind: Dict):
        pos = self.positions[symbol]
        price = ind["price"]
        
        if pos.side == "long":
            pnl_pct = (price - pos.entry_price) / pos.entry_price * 100
        else:
            pnl_pct = (pos.entry_price - price) / pos.entry_price * 100
        
        should_exit = False
        reason = ""
        
        # Stop loss
        if pnl_pct <= -self.config.stop_loss_pct:
            should_exit = True
            reason = "STOP_LOSS"
        
        # Take profit
        elif pnl_pct >= self.config.take_profit_pct:
            should_exit = True
            reason = "TAKE_PROFIT"
        
        # Time limit
        hours_held = (datetime.now() - pos.entry_time).total_seconds() / 3600
        if hours_held > self.config.max_hold_hours:
            should_exit = True
            reason = "TIME_EXIT"
        
        if should_exit:
            logger.info(f"Closing {symbol}: {reason} ({pnl_pct:+.2f}%)")
            
            result = await self.client.close_position(symbol, pos.size if pos.side == "long" else -pos.size)
            
            if result.get("success"):
                del self.positions[symbol]
                self.trades_today += 1
                
                emoji = "+" if pnl_pct > 0 else "-"
                await send_telegram(
                    f"<b>CLOSED {symbol}</b>\n"
                    f"{reason}\n"
                    f"P&L: {emoji}{abs(pnl_pct):.2f}%\n"
                    f"Held: {hours_held:.1f}h"
                )

# ========== MAIN ==========

if __name__ == "__main__":
    trader = Level10Trader()
    asyncio.run(trader.run())









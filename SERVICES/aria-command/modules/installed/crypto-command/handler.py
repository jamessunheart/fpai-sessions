#!/usr/bin/env python3
"""
Crypto Price Module
===================

Get real-time cryptocurrency prices from CoinGecko (free API).
Supports major coins and shows 24h change.
"""

import asyncio
from typing import Optional

# Try to import aiohttp, fall back gracefully if not available
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# Coin ID mappings (CoinGecko IDs)
COIN_ALIASES = {
    # Major coins
    "btc": "bitcoin",
    "bitcoin": "bitcoin",
    "eth": "ethereum",
    "ethereum": "ethereum",
    "sol": "solana",
    "solana": "solana",
    "xrp": "ripple",
    "ripple": "ripple",
    "ada": "cardano",
    "cardano": "cardano",
    "doge": "dogecoin",
    "dogecoin": "dogecoin",
    "dot": "polkadot",
    "polkadot": "polkadot",
    "matic": "matic-network",
    "polygon": "matic-network",
    "link": "chainlink",
    "chainlink": "chainlink",
    "avax": "avalanche-2",
    "avalanche": "avalanche-2",
    "atom": "cosmos",
    "cosmos": "cosmos",
    "uni": "uniswap",
    "uniswap": "uniswap",
    "ltc": "litecoin",
    "litecoin": "litecoin",
    "bnb": "binancecoin",
    # Stablecoins
    "usdt": "tether",
    "usdc": "usd-coin",
}

COINGECKO_API = "https://api.coingecko.com/api/v3"


async def _fetch_price(coin_id: str) -> Optional[dict]:
    """Fetch price data from CoinGecko."""
    if not AIOHTTP_AVAILABLE:
        return None
    
    url = f"{COINGECKO_API}/simple/price"
    params = {
        "ids": coin_id,
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_24hr_vol": "true",
        "include_market_cap": "true"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get(coin_id)
        return None
    except Exception as e:
        return None


def _format_number(num: float, is_price: bool = True) -> str:
    """Format a number for display."""
    if num is None:
        return "N/A"
    
    if is_price:
        if num >= 1:
            return f"${num:,.2f}"
        else:
            return f"${num:.6f}"
    else:
        # Volume/market cap
        if num >= 1_000_000_000:
            return f"${num/1_000_000_000:.2f}B"
        elif num >= 1_000_000:
            return f"${num/1_000_000:.2f}M"
        else:
            return f"${num:,.0f}"


def _format_change(change: float) -> str:
    """Format 24h change with emoji."""
    if change is None:
        return "N/A"
    
    if change > 0:
        return f"📈 +{change:.2f}%"
    elif change < 0:
        return f"📉 {change:.2f}%"
    else:
        return f"➡️ 0.00%"


def handle(args: str, context: dict) -> str:
    """
    Handle the /crypto command.
    
    Args:
        args: Coin symbol or name (e.g., BTC, bitcoin, ETH)
        context: Command context
    
    Returns:
        Price information or help text
    """
    if not args.strip():
        coins = "BTC, ETH, SOL, XRP, ADA, DOGE, DOT, MATIC, LINK, AVAX"
        return (
            "💰 **Crypto Prices**\n\n"
            f"Usage: `/crypto <symbol>`\n\n"
            f"Examples:\n"
            f"• `/crypto btc`\n"
            f"• `/crypto eth`\n"
            f"• `/crypto sol`\n\n"
            f"**Supported:** {coins}\n\n"
            f"_Data from CoinGecko_"
        )
    
    # Check if aiohttp is available
    if not AIOHTTP_AVAILABLE:
        return "❌ Network module not available. Please install aiohttp."
    
    # Parse coin
    coin_input = args.strip().lower()
    coin_id = COIN_ALIASES.get(coin_input)
    
    if not coin_id:
        # Try direct ID
        coin_id = coin_input
    
    # Fetch price (run async)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        data = loop.run_until_complete(_fetch_price(coin_id))
    except Exception as e:
        return f"❌ Error fetching price: {str(e)[:50]}"
    
    if not data:
        return (
            f"❌ Couldn't find **{coin_input.upper()}**\n\n"
            f"Try common symbols: BTC, ETH, SOL, XRP, DOGE"
        )
    
    # Format response
    price = data.get("usd")
    change_24h = data.get("usd_24h_change")
    volume = data.get("usd_24h_vol")
    market_cap = data.get("usd_market_cap")
    
    # Display name
    display_name = coin_input.upper()
    if coin_input in COIN_ALIASES:
        display_name = coin_input.upper()
    
    response = (
        f"💰 **{display_name}**\n\n"
        f"**Price:** {_format_number(price)}\n"
        f"**24h:** {_format_change(change_24h)}\n"
    )
    
    if volume:
        response += f"**Volume:** {_format_number(volume, False)}\n"
    if market_cap:
        response += f"**Market Cap:** {_format_number(market_cap, False)}\n"
    
    response += "\n_Data from CoinGecko_"
    
    return response



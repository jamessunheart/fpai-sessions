# Crypto Price Module

Get real-time cryptocurrency prices from CoinGecko.

## Usage

```
/crypto <symbol>
```

## Examples

- `/crypto btc` - Bitcoin price
- `/crypto eth` - Ethereum price
- `/crypto sol` - Solana price

## Supported Coins

| Symbol | Coin |
|--------|------|
| BTC | Bitcoin |
| ETH | Ethereum |
| SOL | Solana |
| XRP | Ripple |
| ADA | Cardano |
| DOGE | Dogecoin |
| DOT | Polkadot |
| MATIC | Polygon |
| LINK | Chainlink |
| AVAX | Avalanche |
| ATOM | Cosmos |
| UNI | Uniswap |
| LTC | Litecoin |
| BNB | Binance Coin |
| USDT | Tether |
| USDC | USD Coin |

## Data Shown

- Current price (USD)
- 24-hour change (%)
- 24-hour volume
- Market cap

## API

Uses the free CoinGecko API:
- No API key required
- Rate limited to 10-50 calls/minute
- Real-time data

## Dependencies

Requires `aiohttp` for HTTP requests.



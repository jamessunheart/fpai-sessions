# Trader Droplet - SPECS

**Droplet ID:** #103
**Version:** 1.0.0
**Status:** Planning

---

## Purpose

Handle all trading operations including signal processing, trade execution, position management, and P&L tracking. Connects to WhaleTrack for signals and Hyperliquid for execution.

---

## Requirements

### Functional Requirements
- [ ] Process trading signals from WhaleTrack
- [ ] Execute trades on Hyperliquid
- [ ] Manage open positions (entry, stop-loss, take-profit)
- [ ] Track real-time P&L
- [ ] Parse natural language trading commands
- [ ] Auto-trade based on configured strategy
- [ ] Provide position status on request

### Non-Functional Requirements
- [ ] Must execute trades within 2 seconds of signal
- [ ] Must persist state across restarts
- [ ] Must handle API rate limits gracefully
- [ ] Must not lose position state on crash

---

## API Specs

### UDC Endpoints (Required)

```
GET /health
Response: {"status": "healthy", "timestamp": "...", "uptime_seconds": N, "version": "1.0.0"}

GET /capabilities
Response: {"service_name": "trader", "droplet_id": 103, "capabilities": [...]}

GET /state
Response: {"status": "active", "open_positions": N, "pnl_today": X}

GET /dependencies
Response: {"required_services": [...], "optional_services": [...]}

POST /message
Request: {"from_service": "router", "message_type": "query", "payload": {"text": "what is sol?"}}
Response: {"received": true, "status": "completed", "result": {"response": "SOL is at $185.50..."}}
```

### Business Endpoints

```
GET /positions
Response: List of all open positions

GET /positions/{symbol}
Response: Position details for specific symbol

POST /trade
Request: {"symbol": "SOL", "side": "long", "size": 100, "leverage": 2}
Response: Trade execution result

POST /close/{symbol}
Response: Close position for symbol

GET /signals
Response: Current trading signals

GET /pnl
Response: P&L summary (today, week, month, all-time)

POST /auto-trade/start
Response: Start auto-trading

POST /auto-trade/stop
Response: Stop auto-trading

GET /auto-trade/status
Response: Auto-trading status and configuration
```

---

## Dependencies

### Required Services
- WhaleTrack API (http://198.54.123.234:8601) - Trading signals
- Hyperliquid API - Trade execution

### Optional Services
- memory (for trade history storage)
- alerts (for trade notifications)

---

## Data Models

```python
@dataclass
class Position:
    symbol: str
    side: str  # "long" | "short"
    entry_price: float
    current_price: float
    size: float
    leverage: float
    pnl: float
    pnl_percent: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    opened_at: datetime

@dataclass
class Trade:
    id: str
    symbol: str
    side: str
    entry_price: float
    exit_price: Optional[float]
    size: float
    pnl: float
    status: str  # "open" | "closed" | "stopped"
    opened_at: datetime
    closed_at: Optional[datetime]
```

---

## Success Criteria

- [ ] Can fetch current signals from WhaleTrack
- [ ] Can execute trades on Hyperliquid
- [ ] Can report position status
- [ ] Persists state across restarts
- [ ] Handles "what is SOL" queries correctly
- [ ] Passes all UDC compliance tests
- [ ] Has >80% test coverage

---

## Configuration

```bash
# Environment Variables
TRADER_PORT=8751
WHALETRACK_URL=http://198.54.123.234:8601
HYPERLIQUID_API_KEY=<key>
HYPERLIQUID_API_SECRET=<secret>
MAX_POSITION_SIZE=1000
DEFAULT_LEVERAGE=2
STOP_LOSS_PERCENT=5
TAKE_PROFIT_PERCENT=10
AUTO_TRADE_ENABLED=false
```

---

## Compliance Notes

- Handles financial operations
- Must log all trade executions
- Must implement proper error handling for failed trades
- Must validate API credentials on startup









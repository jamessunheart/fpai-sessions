# Trading Engine Usage Guide

Complete guide to using the Treasury Arena Trading Engine.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Usage](#basic-usage)
3. [Protocol Adapters](#protocol-adapters)
4. [Safety Features](#safety-features)
5. [Testing](#testing)
6. [Production Deployment](#production-deployment)

---

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "from src.trading_engine import TradingEngine; print('✓ Trading Engine installed')"
```

### Basic Example (Simulation Mode)

```python
import asyncio
import sqlite3
from decimal import Decimal
from src.trading_engine import TradingEngine
from src.protocols.simulation import SimulationAdapter

# Initialize database (see migrations/ for schema)
db_path = "treasury_arena.db"

# Create protocol adapters
protocols = {
    'simulation': SimulationAdapter({
        'success_rate': 0.95,
        'simulate_delay': False
    })
}

# Create trading engine
engine = TradingEngine(
    db_path=db_path,
    protocols=protocols
)

# Create mock agent
class Agent:
    agent_id = "test-agent-001"
    real_capital = Decimal('10000')

agent = Agent()

# Submit a trade
trade = {
    'trade_type': 'deposit',
    'protocol': 'simulation',
    'input_asset': 'USDC',
    'input_amount': Decimal('1000'),
    'output_asset': 'USDC',
    'expected_return': Decimal('1000'),
    'gas_cost_usd': Decimal('3.50')
}

async def main():
    result = await engine.submit_trade(agent, trade)
    print(f"Trade submitted: {result['trade_id']}")

asyncio.run(main())
```

---

## Basic Usage

### Submitting Trades

The trading engine validates and executes trades asynchronously.

```python
# Deposit to Aave
deposit_trade = {
    'trade_type': 'deposit',
    'protocol': 'aave',
    'input_asset': 'USDC',
    'input_amount': Decimal('5000'),
    'output_asset': 'USDC',
    'expected_return': Decimal('5000'),
    'gas_cost_usd': Decimal('5.00')
}

result = await engine.submit_trade(agent, deposit_trade)

# Swap on Uniswap
swap_trade = {
    'trade_type': 'swap',
    'protocol': 'uniswap',
    'input_asset': 'USDC',
    'input_amount': Decimal('2500'),
    'output_asset': 'ETH',
    'expected_return': Decimal('1.0'),  # Expect ~1 ETH
    'gas_cost_usd': Decimal('15.00'),
    'min_output_amount': Decimal('0.99')  # 1% slippage tolerance
}

result = await engine.submit_trade(agent, swap_trade)
```

### Checking Status

```python
status = await engine.get_status()
print(f"Trading enabled: {status['trading_enabled']}")
print(f"Pending trades: {status['pending_trades']}")
print(f"Protocols: {status['protocols']}")
```

---

## Protocol Adapters

### Simulation Adapter (Phase 1)

Used for testing without blockchain interaction.

```python
from src.protocols.simulation import SimulationAdapter

adapter = SimulationAdapter({
    'success_rate': 0.95,  # 95% success rate
    'simulate_delay': False,  # Instant execution
    'mock_apys': {
        'USDC': Decimal('0.08'),
        'ETH': Decimal('0.05')
    }
})

# Test deposit
result = await adapter.deposit('USDC', Decimal('1000'))
print(f"Deposited: {result['amount_deposited']}")
print(f"Receipt token: {result['receipt_token']}")  # aUSDC
```

### Aave Adapter (Phase 2)

For real DeFi lending/borrowing.

```python
from src.protocols.aave import AaveAdapter

# CRITICAL: Set PRIVATE_KEY environment variable
# export PRIVATE_KEY="0x..."

adapter = AaveAdapter({
    'rpc_url': 'https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY',
    'pool_address': '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2',
    'chain': 'ethereum'
})

# Deposit to earn yield
result = await adapter.deposit('USDC', Decimal('5000'))

# Withdraw
result = await adapter.withdraw('USDC', Decimal('2000'))

# Check APY
apy = await adapter.get_apy('USDC')
print(f"USDC APY: {apy * 100:.2f}%")
```

### Uniswap Adapter (Phase 2)

For DEX swaps.

```python
from src.protocols.uniswap import UniswapAdapter

adapter = UniswapAdapter({
    'rpc_url': 'https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY',
    'router_address': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
    'quoter_address': '0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6'
})

# Estimate output before trading
estimated = await adapter.estimate_output('USDC', 'ETH', Decimal('2500'))
print(f"Estimated output: {estimated} ETH")

# Execute swap with slippage protection
result = await adapter.swap(
    input_asset='USDC',
    output_asset='ETH',
    input_amount=Decimal('2500'),
    min_output_amount=estimated * Decimal('0.99')  # 1% slippage
)
```

---

## Safety Features

### 1. Trade Validation

All trades are validated before execution.

```python
# Validators check:
# - Sufficient capital
# - Position limits
# - Slippage tolerance
# - Daily trade count

is_valid, error = await engine.validate_trade(agent, trade)
if not is_valid:
    print(f"Validation failed: {error}")
```

### 2. Position Limits

Set limits per agent/asset.

```python
import sqlite3

conn = sqlite3.connect(db_path)
conn.execute("""
    INSERT INTO position_limits (agent_id, asset, max_position_usd, max_trade_size_usd, max_daily_trades)
    VALUES (?, ?, ?, ?, ?)
""", ('agent-001', 'ETH', 50000, 10000, 100))
conn.commit()
```

### 3. Emergency Stop

Instantly disable all trading.

```python
# CRITICAL: Call this if something goes wrong
engine.emergency_stop()

# Resume when safe
engine.emergency_resume()
```

### 4. Execution Logging

All trades are logged to database.

```python
cursor = conn.execute("""
    SELECT trade_id, status, protocol, input_amount, output_amount
    FROM trades
    WHERE agent_id = ?
    ORDER BY submitted_at DESC
    LIMIT 10
""", ('agent-001',))

for row in cursor:
    print(f"{row[0]}: {row[1]} - {row[3]} -> {row[4]}")
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run trading engine tests only
pytest tests/test_trading_engine.py -v

# Run protocol tests only
pytest tests/test_protocols.py -v

# Run specific test
pytest tests/test_trading_engine.py::test_emergency_stop_blocks_trading -v
```

### Critical Tests

The following tests MUST pass before production:

1. **Emergency Stop**: `test_emergency_stop_blocks_trading`
2. **Validation First**: `test_validation_before_execution`
3. **Capital Safety**: `test_capital_updated_only_on_success`
4. **Position Limits**: `test_position_limits_enforced`

---

## Production Deployment

### Phase 1: Simulation Mode

Start with simulation mode to test the system.

```python
protocols = {
    'simulation': SimulationAdapter({
        'success_rate': 0.95,
        'simulate_delay': True  # Realistic delays
    })
}

engine = TradingEngine(db_path=db_path, protocols=protocols)
```

### Phase 2: Real DeFi (Testnet)

Test on testnet before mainnet.

```python
# Use Sepolia testnet
protocols = {
    'aave': AaveAdapter({
        'rpc_url': 'https://eth-sepolia.g.alchemy.com/v2/YOUR_KEY',
        'pool_address': '0x...',  # Sepolia Aave Pool
        'chain': 'sepolia'
    }),
    'uniswap': UniswapAdapter({
        'rpc_url': 'https://eth-sepolia.g.alchemy.com/v2/YOUR_KEY',
        'router_address': '0x...',  # Sepolia Router
        'chain': 'sepolia'
    })
}
```

### Phase 3: Mainnet

**CRITICAL SAFETY CHECKLIST:**

- [ ] All tests passing
- [ ] Tested on testnet with real transactions
- [ ] Position limits configured
- [ ] Emergency stop tested
- [ ] Multi-sig wallet for production (recommended)
- [ ] Gas price monitoring in place
- [ ] Monitoring/alerting configured

```python
# Mainnet configuration
protocols = {
    'aave': AaveAdapter({
        'rpc_url': os.getenv('MAINNET_RPC_URL'),
        'pool_address': '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2',
        'chain': 'ethereum'
    }),
    'uniswap': UniswapAdapter({
        'rpc_url': os.getenv('MAINNET_RPC_URL'),
        'router_address': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
        'quoter_address': '0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6',
        'chain': 'ethereum'
    })
}

# ALWAYS start with small amounts
# ALWAYS have emergency stop accessible
# ALWAYS monitor execution logs
```

---

## Environment Variables

Required for production:

```bash
# Blockchain access
export PRIVATE_KEY="0x..."  # NEVER commit to git
export MAINNET_RPC_URL="https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY"

# Optional
export SEPOLIA_RPC_URL="https://eth-sepolia.g.alchemy.com/v2/YOUR_KEY"
```

**CRITICAL: Never store private keys in code. Always use environment variables.**

---

## Monitoring

### Database Queries

```sql
-- Recent trades
SELECT * FROM trades ORDER BY submitted_at DESC LIMIT 10;

-- Failed trades
SELECT * FROM trades WHERE status = 'failed' ORDER BY submitted_at DESC;

-- Success rate today
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
    CAST(SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100 as success_rate
FROM trades
WHERE DATE(submitted_at) = DATE('now');

-- Execution logs
SELECT * FROM execution_log ORDER BY timestamp DESC LIMIT 50;
```

---

## Troubleshooting

### Common Issues

**"Trading is disabled via emergency stop"**
- Emergency stop was activated
- Call `engine.emergency_resume()` to resume

**"Trade validation failed: Insufficient capital"**
- Agent doesn't have enough capital
- Check `agent.real_capital`

**"Protocol 'xyz' not found"**
- Protocol not initialized in engine
- Add to protocols dict when creating engine

**"No private key configured"**
- PRIVATE_KEY environment variable not set
- Set it before running: `export PRIVATE_KEY="0x..."`

---

## Support

For issues or questions:
- Check test files for examples
- Review TRADING_ENGINE_SPEC.md
- Contact development team

**This controls real money. Be extremely careful.**

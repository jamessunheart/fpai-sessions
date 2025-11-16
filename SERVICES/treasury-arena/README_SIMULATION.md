# Treasury Arena - Simulation Engine

## Quick Start

### Run a 30-day Backtest
```bash
python3 -m src.cli backtest --days 30 --agents 10
```

### List All Runs
```bash
python3 -m src.cli list
```

### Compare Runs
```bash
python3 -m src.cli compare backtest-abc123 backtest-def456
```

## Configuration

Edit `simulation_config.json` to customize:
- Simulation period
- Initial agent count
- Evolution parameters
- Time multiplier (1x to 1000x)

## Results

Results are saved to:
- SQLite database (`simulation_data.db`)
- JSON exports (`results/*.json`)

## Performance

- **30-day backtest:** ~1-2 minutes (10x speed)
- **180-day backtest:** ~5-10 minutes (10x speed)
- **Data caching:** Automatic (no redundant API calls)

## Architecture

1. **Data Sources** - Fetch/cache historical data (CoinGecko, DeFi Llama)
2. **Simulation Engine** - Time progression & agent execution
3. **Results Analysis** - Performance metrics & comparison
4. **CLI** - Command-line interface

See `docs/SIMULATION_GUIDE.md` for complete documentation.

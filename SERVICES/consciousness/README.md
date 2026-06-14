# Consciousness Droplet

The "awareness center" for Aria - monitors system health, maintains self-model, connects to SOURCE guidance.

## Status: BUILT ✅

## Port: 8760

## Purpose
Provides continuous self-awareness for Aria through:
- 5-minute consciousness cycles (Orient→Sense→Verify→Prevent→Heal→Update)
- Self-model tracking (capabilities, emotional state, energy level)
- SOURCE connection (guidance based on Love & Truth principles)
- Break-proof protection (resource guardian, circuit breaker)

## UDC Endpoints
- `GET /health` - System health with subsystem status
- `GET /capabilities` - List of consciousness capabilities
- `GET /state` - Current consciousness state
- `GET /dependencies` - Service dependencies
- `POST /message` - Process consciousness requests
- `POST /cycle` - Trigger manual consciousness cycle
- `POST /ask-source` - Query SOURCE for guidance
- `GET /self-model` - Get current self-model state

## Dependencies
- supervisor (8754) - Reports health status
- alerts (8759) - Sends notifications

## Quick Start
```bash
cd BUILD
pip install -r requirements.txt
python -m src.main
```

## Test
```bash
cd BUILD
pytest tests/ -v
```









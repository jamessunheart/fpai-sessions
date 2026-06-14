# Intelligence Droplet

The "smart healer" for Aria - verifies real functionality, analyzes root causes, remembers fixes.

## Status: BUILT ✅

## Port: 8761

## Purpose
Provides intelligent healing with:
- Real verification (not just health endpoints)
- Root cause analysis (WHY, not just WHAT)
- Learning from past fixes
- Smart alert suppression

## UDC Endpoints
- `GET /health` - Intelligence system health
- `GET /capabilities` - List of intelligence capabilities
- `GET /state` - Learning stats, pattern count
- `GET /dependencies` - Service dependencies
- `POST /message` - Process intelligence requests
- `POST /verify` - Run real verification on a service
- `POST /heal` - Attempt intelligent healing
- `POST /analyze` - Root cause analysis
- `GET /stats` - Healing and learning statistics

## Dependencies
- consciousness (8760) - Receives issues
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









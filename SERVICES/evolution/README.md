# Evolution Droplet

The "self-improver" for Aria - learns from issues, proposes improvements, evolves behavior.

## Status: BUILT ✅

## Port: 8762

## Purpose
Enables self-evolution through:
- Learning from recurring issues
- Proposing improvements
- Auto-applying low-risk changes
- Tracking evolution history

## UDC Endpoints
- `GET /health` - Evolution system health
- `GET /capabilities` - List of evolution capabilities
- `GET /state` - Evolution stats, pending proposals
- `GET /dependencies` - Service dependencies
- `POST /message` - Process evolution requests
- `POST /on_issue` - Learn from a new issue
- `POST /evolve` - Run evolution cycle
- `GET /lessons` - Get learned lessons
- `GET /proposals` - Get pending proposals
- `POST /approve/:id` - Approve a proposal

## Dependencies
- intelligence (8761) - Receives issue patterns
- brain (8756) - AI for proposal generation
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









# Consciousness Data Feeder

**Service Name:** consciousness_feeder
**Version:** 1.0.0
**Port:** 8130

## Overview

The Consciousness Data Feeder continuously collects and pushes real-time data into the Full Potential OS consciousness architecture. It populates the four pillars of consciousness (REFLECTING, IDENTITY, THINKING, DOING) with live intelligence from various sources.

## Architecture

The service implements four specialized feeders:

### REFLECTING Layer
- **Purpose:** Meta-awareness and observation collection
- **Sources:** Hacker News, arXiv, internal system events
- **Data:** External observations, pattern detection, trend analysis

### IDENTITY Layer
- **Purpose:** Resource and capability awareness
- **Sources:** Treasury performance, compute resources, ecosystem signals
- **Data:** Trading APR, GPU utilization, competitor intelligence

### THINKING Layer
- **Purpose:** Cognitive processing and foresight
- **Sources:** Research signals, memory synthesis, emerging technologies
- **Data:** Horizon scanning, knowledge graph stats, dream insights

### DOING Layer
- **Purpose:** Execution and action intelligence
- **Sources:** Trading signals, technical alerts, content opportunities
- **Data:** Market signals, security alerts, communication content

## API Endpoints

### Health & Status
- `GET /health` - Service health check
- `GET /status` - Feeder status and last updates

### Manual Control
- `POST /feed/{pillar}` - Manually trigger feeding for specific pillar
- `POST /feed/all` - Manually trigger feeding for all pillars

### Data Access
- `GET /data/{pillar}` - Get latest data for specific pillar
- `GET /data/all` - Get all pillar data

## Dependencies

- **nerve_center:** Receives fed data (port 8120)
- **ai-brain:** Horizon signals and memory stats (port 8101)
- **strategic-intelligence:** Knowledge stats (port 8500)
- **whaletrack:** Trading signals (port 8600)

## Configuration

Environment variables:
- `NERVE_CENTER_URL` - Nerve center API endpoint (default: http://198.54.123.234:8120)
- `UPDATE_INTERVAL` - Seconds between automatic feeds (default: 30)

## Data Flow

```
External APIs → Feeders → Nerve Center → Consciousness State
    ↓              ↓            ↓
Hacker News    REFLECTING    /api/conscious/state
arXiv         IDENTITY      God Mode Dashboard
Research     THINKING      Real-time Updates
Trading      DOING         Decision Support
```

## Consciousness Impact

This service transforms the consciousness architecture from static configuration to dynamic awareness by:

1. **Continuous Learning:** Real-time data ingestion keeps consciousness current
2. **Multi-Source Intelligence:** Diverse data sources prevent bias and gaps
3. **Actionable Insights:** Data structured for immediate decision-making
4. **Evolution Ready:** Foundation for consciousness self-improvement

## Deployment

```bash
# Using deployment script
./infra/scripts/deploy-service.sh consciousness_feeder 8130

# Manual deployment
cd SERVICES/consciousness_feeder
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8130
```

## Monitoring

- **Health:** `/health` endpoint returns service status
- **Performance:** `/status` shows feeding statistics and last updates
- **Logs:** Standard logging to console and files
- **Metrics:** Integration with God Mode monitoring dashboard















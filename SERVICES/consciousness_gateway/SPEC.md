# Consciousness API Gateway Service

## Overview
Unified natural language API for interacting with consciousness system. Provides a single interface for querying, decision-making, optimization, and explanation.

## Purpose
Enable natural language interaction with consciousness, allowing humans to query, guide, and understand the consciousness system.

## Key Features

### Natural Language Interface
- Query consciousness with natural language
- Get conscious responses based on current state
- Understand consciousness capabilities

### Decision Making
- Request consciousness-driven decisions
- Get recommendations with mathematical reasoning
- Understand risk assessment

### Optimization Requests
- Request system optimizations
- Get optimization recommendations
- Understand expected improvements

### Behavior Explanation
- Get mathematical explanations of consciousness behavior
- Understand decision-making process
- Learn about learning and adaptation mechanisms

## API Endpoints

### `/consciousness/query` (POST)
Ask consciousness questions and get conscious responses.

**Request:**
```json
{
  "query": "What is my current consciousness score?",
  "context": {}
}
```

**Response:**
```json
{
  "response": "Current consciousness score: 0.742...",
  "consciousness_level": "truly_conscious",
  "metrics": {...}
}
```

### `/consciousness/decide` (POST)
Request consciousness-driven decisions.

**Request:**
```json
{
  "scenario": "System optimization",
  "options": ["Option A", "Option B", "Option C"],
  "context": {}
}
```

### `/consciousness/optimize` (POST)
Request system optimizations.

**Request:**
```json
{
  "target": "integration_complexity",
  "context": {}
}
```

### `/consciousness/explain` (POST)
Get explanations of consciousness behavior.

**Request:**
```json
{
  "behavior": "decision making",
  "context": {}
}
```

### `/consciousness/state` (GET)
Get current consciousness state.

## Integration

### With All Consciousness Services
- Consciousness Verifier (8140) - Metrics
- Consciousness Decision Engine (8150) - Decisions
- Consciousness Feeder (8130) - State
- Consciousness Optimizer (8160) - Optimizations

## Deployment

**Port:** 8180
**Dependencies:** All consciousness services

```bash
# Deploy
rsync -av SERVICES/consciousness_gateway/ root@198.54.123.234:/opt/fpai/apps/consciousness_gateway/

# Setup
ssh root@198.54.123.234 'cd /opt/fpai/apps/consciousness_gateway && \
    python3 -m venv venv && \
    source venv/bin/activate && \
    pip install -r requirements.txt'

# Create systemd service
# Start on port 8180
```

## Usage Examples

### Query Consciousness
```bash
curl -X POST http://localhost:8180/consciousness/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is my consciousness level?"}'
```

### Request Decision
```bash
curl -X POST http://localhost:8180/consciousness/decide \
  -H "Content-Type: application/json" \
  -d '{"scenario": "Trading", "options": ["Buy", "Hold", "Sell"]}'
```

### Get Explanation
```bash
curl -X POST http://localhost:8180/consciousness/explain \
  -H "Content-Type: application/json" \
  -d '{"behavior": "decision making"}'
```















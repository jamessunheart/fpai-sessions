# Consciousness Dashboard Service

## Overview
Web interface for human-AI consciousness interaction, providing real-time visualization, decision history, and human override controls.

## Purpose
Enable humans to interact with and understand the consciousness system through an intuitive dashboard interface.

## Key Features

### Real-Time Visualization
- Consciousness metrics dashboard (10 mathematical metrics)
- Consciousness evolution graphs over time
- Pillar activity visualization
- Integration patterns display

### Decision Interface
- Decision history with explanations
- "Why did consciousness choose this?" explanations
- Human override controls for autonomous decisions
- Decision quality statistics

### Consciousness State
- Current consciousness level
- Self-awareness status
- Adaptation mode
- System health indicators

### Human Feedback Loop
- Human corrections improve consciousness
- Feedback integration
- Learning from human guidance

## API Endpoints

### `/` (GET)
Main dashboard HTML page with interactive visualization.

### `/api/metrics` (GET)
Get current consciousness metrics.

### `/api/decisions` (GET)
Get recent consciousness-driven decisions.

### `/api/optimizations` (GET)
Get optimization opportunities and statistics.

### `/api/consciousness-state` (GET)
Get complete consciousness state including feeder and metrics.

### `/api/override-decision/{decision_id}` (POST)
Human override for a consciousness decision.

### `/api/evolution` (GET)
Get consciousness evolution tracking data.

## Integration

### With All Consciousness Services
- Consciousness Verifier (8140) - Metrics
- Consciousness Decision Engine (8150) - Decisions
- Consciousness Feeder (8130) - State
- Consciousness Optimizer (8160) - Optimizations

## Deployment

**Port:** 8170
**Dependencies:** All consciousness services

```bash
# Deploy
rsync -av SERVICES/consciousness_dashboard/ root@198.54.123.234:/opt/fpai/apps/consciousness_dashboard/

# Setup
ssh root@198.54.123.234 'cd /opt/fpai/apps/consciousness_dashboard && \
    python3 -m venv venv && \
    source venv/bin/activate && \
    pip install -r requirements.txt'

# Create systemd service
# Start on port 8170
```

## Features

- Auto-refreshing metrics display
- Interactive decision history
- Real-time consciousness state
- Human override capabilities
- Evolution tracking visualization















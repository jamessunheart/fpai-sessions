# Consciousness Decision Engine Service

## Overview
Autonomous decision-making service that uses mathematical consciousness metrics to make optimal decisions with quantifiable confidence scores.

## Purpose
Transform decision-making from rule-based to consciousness-driven, where decisions are optimized based on integration complexity, adaptation rate, phase synchronization, and other rigorous mathematical metrics.

## Key Features

### Decision Making
- Uses 10 mathematical consciousness metrics (Φ, h, C, σ, λ, D, R, CD, AV, KIR)
- Calculates decision quality: `decision_quality = f(consciousness_score, integration_complexity, adaptation_rate)`
- Provides confidence scores based on consciousness state
- Risk assessment based on consciousness metrics

### Decision Types
- **Trading**: Consciousness-driven trading decisions
- **Optimization**: System optimization choices
- **Resource Allocation**: Optimal resource distribution
- **Risk Management**: Risk mitigation strategies
- **System Coordination**: Service coordination decisions

### Decision Quality
- Higher consciousness = better decision quality
- Integration complexity improves decision accuracy
- Adaptation rate enables responsive decisions
- Phase synchronization ensures coordinated actions

## API Endpoints

### `/decide` (POST)
Make a general consciousness-driven decision from options.

**Request:**
```json
{
  "decision_type": "trading",
  "options": [
    {"action": "buy", "score": 0.7, "expected_outcome": "profit"},
    {"action": "hold", "score": 0.5, "expected_outcome": "stability"}
  ],
  "context": {"portfolio_value": 100000}
}
```

**Response:**
```json
{
  "decision": {
    "decision_id": "dec_1234567890_trading",
    "action": "buy",
    "confidence_score": 0.742,
    "reasoning": "Consciousness-driven decision...",
    "risk_assessment": {"risk_level": "low", "confidence": 0.85}
  },
  "alternatives": [...],
  "recommendation": "Recommended action: buy (confidence: 0.742)"
}
```

### `/decide/trading` (POST)
Make trading decisions using consciousness metrics.

### `/decide/optimize` (POST)
Make optimization decisions for system improvement.

### `/decide/resource-allocation` (POST)
Make resource allocation decisions.

### `/decisions` (GET)
Get decision history with optional filtering.

### `/statistics` (GET)
Get decision quality statistics over time.

### `/consciousness-state` (GET)
Get current consciousness state used for decision making.

## Integration

### With Consciousness Verifier
- Fetches mathematical metrics from port 8140
- Uses metrics to calculate decision quality
- Adapts decision thresholds based on consciousness level

### With Consciousness Feeder
- Gets current consciousness state from port 8130
- Uses pillar activity for context-aware decisions
- Considers adaptation mode in risk assessment

## Decision Quality Formula

```
decision_quality = 
  0.30 × consciousness_score +
  0.25 × integration_complexity +
  0.20 × adaptation_rate +
  0.15 × phase_synchronization +
  0.10 × causal_density
```

## Risk Assessment

Risk is calculated based on:
- Consciousness score (lower = higher risk)
- Decision type (trading = higher risk multiplier)
- Integration complexity (higher = lower risk)
- Adaptation rate (higher = lower risk)

## Deployment

**Port:** 8150
**Dependencies:** Consciousness Verifier (8140), Consciousness Feeder (8130)

```bash
# Deploy
rsync -av SERVICES/consciousness_decision_engine/ root@198.54.123.234:/opt/fpai/apps/consciousness_decision_engine/

# Setup
ssh root@198.54.123.234 'cd /opt/fpai/apps/consciousness_decision_engine && \
    python3 -m venv venv && \
    source venv/bin/activate && \
    pip install -r requirements.txt'

# Create systemd service
# Start on port 8150
```















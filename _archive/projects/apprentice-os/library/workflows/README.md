# Workflows Library

> Reusable automation flows for n8n and internal systems.

## Structure

```
/workflows
├── /alerts           # Alert and notification flows
├── /governance       # Rule enforcement flows
├── /trading          # Trading automation flows
├── /maintenance      # System maintenance flows
└── README.md
```

## Workflow Types

### Alert Workflows
- Metric threshold crossing → Telegram notification
- System health degradation → Escalation chain
- Shadow cost spike → Steward alert

### Governance Workflows
- Coherence drop → Pause expansion
- Override pattern → Calibration review
- Three Nevers violation → Block and log

### Trading Workflows
- Signal received → Evaluation pipeline
- Position opened → Risk monitoring
- Profit/loss threshold → Auto-actions

### Maintenance Workflows
- Health check → Auto-remediation
- Service failure → Restart and alert
- Disk/memory critical → Cleanup

## Creating Workflows

Workflows are designed in n8n and exported as JSON.

### Best Practices

1. **Single responsibility** - One workflow, one purpose
2. **Error handling** - Always handle failures gracefully
3. **Logging** - Write events to the events table
4. **Governance** - Check rules before major actions

## Planned Workflows

1. **coherence-guardian** - Monitor steward state, pause when needed
2. **apprentice-progress** - Track and report apprentice metrics
3. **trading-sentinel** - Monitor trades and enforce limits
4. **complexity-watcher** - Alert on complexity creep

---

*Workflows are the system's reflexes - automatic responses to conditions.*



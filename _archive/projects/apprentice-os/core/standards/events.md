# Event Taxonomy

> Standard event types for Apprentice OS logging.

## Event Categories

### Metrics Events
| Event Type | Description | Payload |
|------------|-------------|---------|
| `metric.updated` | A metric value changed | `{metric_name, old_value, new_value, entity_id}` |
| `metric.threshold_crossed` | Metric crossed a threshold | `{metric_name, threshold, direction, value}` |
| `metric.baseline_reset` | Baseline was recalibrated | `{metric_name, old_baseline, new_baseline}` |

### Loop Events
| Event Type | Description | Payload |
|------------|-------------|---------|
| `loop.started` | New apprentice loop began | `{apprentice_id, phase, started_at}` |
| `loop.phase_changed` | Apprentice moved to new phase | `{apprentice_id, from_phase, to_phase}` |
| `loop.completed` | Loop successfully finished | `{apprentice_id, duration_days, outcome}` |
| `loop.failed` | Loop ended unsuccessfully | `{apprentice_id, reason, lessons}` |

### Alert Events
| Event Type | Description | Payload |
|------------|-------------|---------|
| `alert.raised` | New alert created | `{alert_id, type, severity, message}` |
| `alert.acknowledged` | Alert was seen | `{alert_id, acknowledged_by, timestamp}` |
| `alert.resolved` | Alert was resolved | `{alert_id, resolved_by, resolution}` |

### Governance Events
| Event Type | Description | Payload |
|------------|-------------|---------|
| `policy.changed` | Governance policy updated | `{policy_id, change_type, old_value, new_value}` |
| `rule.triggered` | Decision engine rule fired | `{rule_id, condition, action_taken}` |
| `rule.overridden` | Rule was overridden | `{rule_id, override_reason, approved_by}` |
| `override.logged` | Override attempt logged | `{rule_id, success, reason}` |
| `never.violated` | Three Nevers violation | `{never_type, severity, action_blocked}` |

### Assistant Events
| Event Type | Description | Payload |
|------------|-------------|---------|
| `assistant.created` | New assistant created | `{assistant_id, created_by, type}` |
| `assistant.connected` | Assistant connected to another | `{from_id, to_id, connection_type}` |
| `assistant.action` | Assistant performed action | `{assistant_id, action_type, result}` |

### Module Events
| Event Type | Description | Payload |
|------------|-------------|---------|
| `module.published` | New module available | `{module_id, version, author_id}` |
| `module.installed` | Module installed on assistant | `{module_id, assistant_id, version}` |
| `module.updated` | Module version updated | `{module_id, from_version, to_version}` |

### System Events
| Event Type | Description | Payload |
|------------|-------------|---------|
| `system.pause` | System paused | `{reason, triggered_by}` |
| `system.resume` | System resumed | `{paused_duration, resumed_by}` |
| `system.health_check` | Health check completed | `{status, issues_found}` |

### Simulation Events
| Event Type | Description | Payload |
|------------|-------------|---------|
| `sim.*` | All simulation events prefixed | Same as non-sim variants |

---

## Event Structure

All events follow this structure:

```json
{
  "id": "uuid",
  "event_type": "category.action",
  "entity_type": "apprentice|assistant|module|system",
  "entity_id": "uuid or null",
  "payload": {},
  "created_at": "ISO timestamp"
}
```

---

## Semantic Contract

- **Events are immutable** - Never delete or modify
- **Events are append-only** - Only INSERT, never UPDATE
- **Events are the audit trail** - Everything meaningful is logged

---

*This document defines the event taxonomy for Apprentice OS.*



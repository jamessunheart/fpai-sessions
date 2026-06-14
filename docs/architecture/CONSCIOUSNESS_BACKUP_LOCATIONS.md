# Consciousness Backup & Version Control Locations

## 📁 Backup Storage Location

**Primary Backup Directory:**
```
/opt/fpai/backups/consciousness_optimizer/
```

## 📂 Directory Structure

```
/opt/fpai/backups/consciousness_optimizer/
├── backup_opt_{optimization_id}_{timestamp}.json    # Pre-optimization backups
├── consciousness_feeder_v{timestamp}_{hash}.json   # Version snapshots
└── versions.json                                    # Version control history
```

## 🔍 Finding Backups

### List All Backups
```bash
ssh root@198.54.123.234 'ls -lah /opt/fpai/backups/consciousness_optimizer/'
```

### View Backup Contents
```bash
ssh root@198.54.123.234 'cat /opt/fpai/backups/consciousness_optimizer/backup_*.json | python3 -m json.tool'
```

### View Version History
```bash
ssh root@198.54.123.234 'cat /opt/fpai/backups/consciousness_optimizer/versions.json | python3 -m json.tool'
```

## 📊 Via API

### List Backups via API
```bash
curl http://198.54.123.234:8160/backups | python3 -m json.tool
```

### View Version History via API
```bash
curl http://198.54.123.234:8160/versions | python3 -m json.tool
```

## 🔄 Rollback Commands

### Rollback via API
```bash
curl -X POST http://198.54.123.234:8160/rollback/{backup_id}
```

### Manual Rollback (if needed)
```bash
# 1. View backup
ssh root@198.54.123.234 'cat /opt/fpai/backups/consciousness_optimizer/backup_{backup_id}.json | python3 -m json.tool'

# 2. Restore configuration manually via feeder API
curl -X POST http://198.54.123.234:8130/optimization/revert \
  -H "Content-Type: application/json" \
  -d @backup_file.json
```

## 📝 Backup File Format

Each backup file contains:
```json
{
  "backup_id": "backup_opt_1234567890_phi_1234567890",
  "optimization_id": "opt_1234567890_phi",
  "timestamp": "2025-12-05T18:14:07.498521+00:00",
  "config_before": {
    "update_interval": 30,
    "pillar_weights": {...},
    "data_source_priorities": {...}
  },
  "optimization": {
    "action_id": "...",
    "target": "integration_complexity",
    "action_type": "increase_data_integration",
    "parameters": {...}
  },
  "backup_type": "pre_optimization"
}
```

## 🔐 Version Control Format

`versions.json` contains:
```json
[
  {
    "backup_id": "...",
    "optimization_id": "...",
    "timestamp": "...",
    "action": "backup_created",
    "status": "success"
  },
  {
    "version_id": "...",
    "service_name": "consciousness_feeder",
    "timestamp": "...",
    "action": "snapshot_created",
    "status": "success"
  }
]
```

## 🎯 Quick Access Commands

### View Latest Backup
```bash
ssh root@198.54.123.234 'ls -t /opt/fpai/backups/consciousness_optimizer/backup_*.json | head -1 | xargs cat | python3 -m json.tool'
```

### View Latest Version
```bash
ssh root@198.54.123.234 'ls -t /opt/fpai/backups/consciousness_optimizer/consciousness_feeder_*.json | head -1 | xargs cat | python3 -m json.tool'
```

### Count Total Backups
```bash
ssh root@198.54.123.234 'ls /opt/fpai/backups/consciousness_optimizer/backup_*.json 2>/dev/null | wc -l'
```

## 📍 Alternative: Central Backup System

If you want backups in the central FPAI backup system:
```
/opt/fpai/backups/services/consciousness_optimizer/
```

This can be configured by changing the `backup_dir` parameter in `BackupManager`.















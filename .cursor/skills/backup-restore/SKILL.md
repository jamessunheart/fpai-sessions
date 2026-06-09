---
name: backup-restore
description: >-
  Inspect, create, and restore FPAI service backups. Use whenever the user asks
  about backups, rollback, restore, disaster recovery, or "what versions exist"
  for a service.
---

# Backup & Restore

**Recommended model:** Composer 2 (fast tool use, simple lookups and shell ops — no deep reasoning needed).

All backups live on the primary server (198.54.123.234) under `/opt/fpai/backups/`.

## Inspect

```bash
# Everything
/opt/fpai/scripts/list-backups.sh

# One service
/opt/fpai/scripts/list-backups.sh <service-name>
```

Dashboard UI: `https://fullpotential.ai/admin/backup` (user: admin).

## Create a pre-deploy backup

```bash
/opt/fpai/scripts/pre-deploy-backup.sh <service-name> v<MAJOR>.<MINOR>.<PATCH>
```

Semantic versions only. PATCH = bug fix. MINOR = new feature. MAJOR = breaking.

## Restore

```bash
# Latest known-good
/opt/fpai/scripts/restore-service.sh <service-name> latest

# Specific version
/opt/fpai/scripts/restore-service.sh <service-name> v1.2.0
```

After restore, verify:

```bash
curl -sS http://<host>:<port>/health
```

If it's a web service, also run the URL verifier (see `deploy-service` skill step 5).

## Directory layout

```
/opt/fpai/backups/
├── services/       # Backend services
├── dashboards/     # UI (god-mode, collab-hub)
├── websites/       # Public sites
├── nginx/          # nginx configs
└── manifest.json   # Master record
```

## Hard rules

- **Never delete anything in `/opt/fpai/backups/`.** Ever.
- **Never overwrite an existing backup version.** Increment and create fresh.
- **Never deploy without a backup.** The safe-deploy wrapper enforces this — prefer it.

Related: `@docs/coordination/MEMORY/VERSION_CONTROL_PROTOCOL.md`.

# Deployment Steps

This guide walks an operator through the first deployment of the unified `fullpotential_core` repo onto a fresh server.

## 1. Server Setup
```bash
# Run as root or via sudo
apt update && apt install -y git python3 python3-venv python3-pip nodejs npm docker.io docker-compose
# Optional: install pnpm/yarn if needed by specific apps

# Create deploy user
useradd -m -s /bin/bash fpai && passwd fpai
usermod -aG sudo fpai
usermod -aG docker fpai
```

## 2. Directory Layout on Host
```
/opt/fpai/
├── agents/services/        # sync from repo `agents/services`
├── core/applications/      # sync from repo `core/applications`
├── droplets/claude1/
├── droplets/hteam/
├── orchestration/
├── infra/
├── docs/                   # optional, for on-host reference
└── env/                    # store .env files & secrets (not committed)
```
Create directories:
```bash
mkdir -p /opt/fpai/{agents/services,core/applications,droplets/claude1,droplets/hteam,orchestration,infra,docs,env}
chown -R fpai:fpai /opt/fpai
```

## 3. Pulling the Repo
```bash
su - fpai
cd ~
git clone git@github.com:<your-org>/fullpotential_core.git
cd fullpotential_core
```
Use branches/tags per release. Never deploy from dirty working trees.

## 4. Sync Repo → Host Paths
Use `rsync` or deploy tooling:
```bash
rsync -av --delete agents/services/ /opt/fpai/agents/services/
rsync -av --delete core/applications/ /opt/fpai/core/applications/
rsync -av --delete droplets/ /opt/fpai/droplets/
rsync -av --delete orchestration/ /opt/fpai/orchestration/
rsync -av --delete infra/ /opt/fpai/infra/
rsync -av --delete docs/ /opt/fpai/docs/
```
Secrets (`.env`, keys) go in `/opt/fpai/env/` and are sourced by systemd units or shell profiles.

## 5. Environment Layout
- Python services: create virtualenv per service under `/opt/fpai/agents/services/<service>/.venv`.
- Node/TS apps: install dependencies inside the service folder (`npm install` or `pnpm install`).
- Dockerized components: use provided `Dockerfile`/`docker-compose.yml` where available (e.g., `agents/services/orchestrator`).

## 6. Nightly Jobs
Create a cron entry (as `fpai`) for intent snapshots & status index:
```bash
crontab -e
0 2 * * * /opt/fpai/orchestration/scripts/generate_intent_snapshot.py && \
          /opt/fpai/orchestration/scripts/update_status_index.py >> /opt/fpai/logs/nightly.log 2>&1
```
Add additional jobs as needed (e.g., mission sync, backups).

## 7. Preflight Checks
Before each deployment run:
```bash
./orchestration/tools/spec_task_sync.py
./orchestration/scripts/generate_intent_snapshot.py
./orchestration/scripts/update_status_index.py
core/applications/magnet-trading-system$ python -m pytest tests/
# run tests listed in core/applications/TEST_MATRIX.md as available
```

## 8. Pulling Updates Safely
On the server:
```bash
cd ~/fullpotential_core
git fetch origin
# Optionally checkout release tag
```
Re-run the rsync commands to sync onto `/opt/fpai/...`, then restart services (systemd, Docker, or Foreman depending on the app). Avoid editing files directly under `/opt/fpai`; treat the repo as source of truth.

## 9. Logging & Monitoring
- Store service logs under `/opt/fpai/logs/<service>.log`.
- Keep orchestration scripts under `/opt/fpai/orchestration/scripts/` and run them via cron/systemd timers.
- Review `docs/status/overnight-report.md` daily for system health.

## 10. Next Steps
- Add CI hooks to enforce test matrix commands.
- Expand mission board automation for post-deploy audits.
```

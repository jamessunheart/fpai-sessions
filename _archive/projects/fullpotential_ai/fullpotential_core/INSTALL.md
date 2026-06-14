# Installation Guide

1. **Upload bundle**
   ```bash
   scp fpai_deploy_bundle_v1.tar.gz fpai@<server>:/home/fpai/
   ```
2. **Extract & stage**
   ```bash
   ssh fpai@<server>
   mkdir -p /opt/fpai
   tar -xzf fpai_deploy_bundle_v1.tar.gz -C /opt/fpai --strip-components=1
   ```
3. **Install dependencies**
   - Follow `infra/deployment_steps.md` for system packages and cron setup.
   - Create virtualenvs per service (`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`).
   - Run `npm install` where `package.json` exists.
4. **Run preflight on server**
   ```bash
   cd /opt/fpai
   ./orchestration/scripts/preflight_check.py
   ```
   Review `infra/preflight_report.json` for warnings (e.g., services missing manifests).
5. **Sync env + secrets**
   - Copy real `.env` files into `/opt/fpai/env/`.
   - Update placeholders noted in `infra/deployment_steps.md`.
6. **Deploy services**
   - For systemd-managed apps, create unit files pointing at `/opt/fpai/...`
   - For Docker-compose services, run `docker compose up -d` in their directories.
7. **Schedule nightly jobs**
   - Add cron entry per `infra/deployment_steps.md` to run intent snapshot + status index.
8. **Verify**
   - Hit health endpoints, review logs under `/opt/fpai/logs/`, confirm missions board reflects the deploy.

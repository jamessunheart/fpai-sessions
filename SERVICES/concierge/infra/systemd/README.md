# systemd units — Concierge

Each service ships as its own unit; generated on deploy via
`infra/scripts/render-systemd.sh` (to be written in M1 deploy-hardening task).

Template (example):

```ini
[Unit]
Description=Concierge tenant-api
After=network.target postgresql.service

[Service]
Type=simple
User=fpai
WorkingDirectory=/opt/fpai/concierge
EnvironmentFile=/opt/fpai/concierge/.env
ExecStart=/opt/fpai/concierge/.venv/bin/uvicorn tenant_api.main:app --host 0.0.0.0 --port 8820
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Repeat per service (ports 8820-8825).

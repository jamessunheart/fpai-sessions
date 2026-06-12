#!/usr/bin/env python3
"""Inject secrets from infra/secrets.vault.json into remote env files."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

VAULT_FILE = Path('infra/secrets.vault.json')
SERVER = 'root@198.54.123.234'
REMOTE_PATH = '/opt/fpai/env/magnet.env'


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def main() -> None:
    if not VAULT_FILE.exists():
        raise SystemExit('infra/secrets.vault.json not found')
    data = json.loads(VAULT_FILE.read_text())
    magnet = data.get('magnet', {})
    lines = []
    for key in ['BINANCE_API_KEY', 'BINANCE_API_SECRET', 'REDIS_URL']:
        if key in magnet:
            lines.append(f'{key}={magnet[key]}')
    payload = '\n'.join(lines) + '\n'
    run(['ssh', SERVER, "cat > /tmp/magnet.env.part"], input=payload.encode())
    run(['ssh', SERVER, 'cp /tmp/magnet.env.part /opt/fpai/env/magnet.env && rm /tmp/magnet.env.part && chmod 600 /opt/fpai/env/magnet.env'])


if __name__ == '__main__':
    main()

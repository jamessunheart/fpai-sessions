# SPEC_d201_infra-certbot-pyopenssl-cryptog Result

build_kind=activation

## Summary

Added a guarded server-162 maintenance activation for the certbot
pyOpenSSL/cryptography mismatch. The activation defaults to a no-op hold after
merge unless a maintainer explicitly sets `D201_CERTBOT_MAINTENANCE_APPROVED=1`
and chooses `D201_CERTBOT_STRATEGY`.

Supported strategies:

- `venv-upgrade`: snapshot the certbot Python environment, then upgrade
  `pyOpenSSL>=24.0.0` and `cryptography>=41,<46` inside the certbot shebang env.
- `system-pip-upgrade`: same package alignment through system Python, but only
  with the second explicit gate `D201_ALLOW_SYSTEM_PIP=1`.
- `snap-refresh`: install/refresh the classic certbot snap.
- `pipx-reinstall`: reinstall certbot through pipx and inject `certbot-nginx`.

## Live Maintenance Command

Recommended first pass on server 162:

```bash
D201_CERTBOT_MAINTENANCE_APPROVED=1 \
D201_CERTBOT_STRATEGY=venv-upgrade \
D201_DRY_RUN=1 \
bash core/BUILD/activate/SPEC_d201_infra-certbot-pyopenssl-cryptog.sh
```

Then rerun without `D201_DRY_RUN=1` during the approved maintenance window.

If certbot is not venv-backed and the operator chooses the riskier system-Python
repair:

```bash
D201_CERTBOT_MAINTENANCE_APPROVED=1 \
D201_CERTBOT_STRATEGY=system-pip-upgrade \
D201_ALLOW_SYSTEM_PIP=1 \
bash core/BUILD/activate/SPEC_d201_infra-certbot-pyopenssl-cryptog.sh
```

## Proof Required On Server 162

- `certbot renew --dry-run` succeeds.
- `systemctl start certbot.service` exits 0.
- `systemctl is-active certbot.timer` returns active.

## Rollback

For Python-env strategies, use the timestamped backup under
`/opt/fpai-build/backups/d201-certbot/` and reinstall the recorded
`pip-freeze.before.txt` into the same Python environment.

For snap or pipx strategies, restore the previous certbot binary/linkage from
the package manager history or reinstall the prior apt/snap/pipx certbot
package, then rerun the proof commands above.

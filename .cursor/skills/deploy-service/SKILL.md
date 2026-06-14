---
name: deploy-service
description: >-
  Safely deploy an FPAI service to the correct server with a pre-deploy backup,
  a post-deploy health check, and (for web services) URL verification. Use
  whenever the user asks to deploy, push, ship, roll out, or release anything
  to a server.
---

# Deploy a service safely

**Recommended model:** GPT-5.3 Codex (precise, low-cost workhorse for deterministic ops).

Follow these steps in order. Do not skip any.

## 1. Identify the target server

Consult `@docs/coordination/SERVICE_REGISTRY.md` or run the `service-registry-lookup` skill.

- **Primary (198.54.123.234):** web, trading, revenue, data services.
- **Secondary (162.0.208.88):** AI, consciousness, intelligence services.

If the service is on the "stopped on purpose" list, **do not restart it** — confirm with the user first.

## 2. Check existing backups

```bash
/opt/fpai/scripts/list-backups.sh <service-name>
```

Make sure at least one prior backup exists for this service before touching anything. If none exists, create one now (step 3) before any code change.

## 3. Deploy via the safe wrapper

The wrapper takes a pre-deploy backup, runs your deploy command, and refuses to proceed if backup fails.

```bash
./infra/scripts/safe-deploy.sh <service-name> "<deploy-command>"
```

If you genuinely need to bypass the wrapper (rare), create the backup explicitly:

```bash
/opt/fpai/scripts/pre-deploy-backup.sh <service-name> v<X.Y.Z>
```

Use semantic versions: PATCH = bug fix, MINOR = new feature, MAJOR = breaking.

## 4. Health check

```bash
curl -sS http://<host>:<port>/health
# and if applicable:
pytest
```

## 5. Web verification (if the service serves a public URL)

```bash
./docs/coordination/scripts/verify-web-deployment.sh <domain> [page1 page2 ...]
```

Present the 200-OK results in the completion message. "Deployed" without verification = process violation.

## 6. On failure — restore immediately

```bash
/opt/fpai/scripts/restore-service.sh <service-name> latest
# or a specific version:
/opt/fpai/scripts/restore-service.sh <service-name> v1.2.0
```

Then investigate before redeploying.

## Hard rules

- **Never SSH directly to servers.** Always use `infra/scripts/deploy-to-server.sh`.
- **Never delete anything in `/opt/fpai/backups/`.**
- **Never overwrite an existing backup version.** Increment and make a new one.

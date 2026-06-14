#!/usr/bin/env python3
from pathlib import Path
import sys

registry_env = Path("/opt/fpai/env/registry.env")
dash_env = Path("/opt/fpai/env/dashboard.env")

if not registry_env.exists():
    sys.exit("registry.env not found")
if not dash_env.exists():
    sys.exit("dashboard.env not found")

jwt_secret = None
for line in registry_env.read_text().splitlines():
    if line.startswith("JWT_SECRET="):
        jwt_secret = line.split("=", 1)[1].strip().strip('"')
        break

if not jwt_secret:
    sys.exit("JWT_SECRET not defined in registry.env")

lines = dash_env.read_text().splitlines()
updated = []
replaced = False
for line in lines:
    if line.strip().startswith("JWT_SECRET="):
        updated.append(f"JWT_SECRET=\"{jwt_secret}\"")
        replaced = True
    else:
        updated.append(line)

if not replaced:
    updated.append(f"JWT_SECRET=\"{jwt_secret}\"")

dash_env.write_text("\n".join(updated) + "\n")
dash_env.chmod(0o600)
print("Dashboard JWT secret synced with registry")

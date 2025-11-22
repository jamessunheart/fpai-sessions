#!/usr/bin/env python3
"""Bootstrap shared JWT and registry URLs for Registry + Orchestrator."""
from __future__ import annotations

import secrets
from pathlib import Path

REGISTRY_ENV = Path("/opt/fpai/env/registry.env")
ORCH_ENV = Path("/opt/fpai/env/orchestrator.env")

SECRET = secrets.token_urlsafe(48)


def patch_env(path: Path, replacements: dict[str, str]) -> None:
    lines = path.read_text().splitlines()
    new_lines = []
    for line in lines:
        key = line.split("=", 1)[0] if "=" in line else None
        if key and key in replacements:
            new_lines.append(f"{key}={replacements[key]}")
        else:
            new_lines.append(line)
    path.write_text("\n".join(new_lines) + "\n")


def main() -> None:
    patch_env(
        REGISTRY_ENV,
        {
            "JWT_SECRET": SECRET,
            "REGISTRY_PUBLIC_URL": "http://127.0.0.1:8001",
        },
    )
    patch_env(
        ORCH_ENV,
        {
            "JWT_SECRET": SECRET,
            "REGISTRY_URL": "http://127.0.0.1:8001",
        },
    )


if __name__ == "__main__":
    main()

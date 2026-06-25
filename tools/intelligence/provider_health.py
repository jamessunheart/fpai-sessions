#!/usr/bin/env python3
"""Lightweight provider probes for model-router health checks."""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .model_router import AUTH_ERROR_STRINGS, _append_ops
except Exception:
    from model_router import AUTH_ERROR_STRINGS, _append_ops  # type: ignore


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _has_auth_error(text: str) -> bool:
    lower = text.lower()
    return any(marker in lower for marker in AUTH_ERROR_STRINGS)


def _probe(command: list[str], *, stdin: str | None = None, timeout: int = 12) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            command,
            input=stdin,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
    except Exception as exc:
        return False, str(exc)
    text = result.stdout or ""
    if result.returncode != 0:
        return False, text.strip()[:300] or f"exit {result.returncode}"
    if _has_auth_error(text):
        return False, text.strip()[:300]
    return True, "ok"


def check_provider_health() -> dict[str, Any]:
    claude_bin = shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude")
    codex_bin = shutil.which("codex") or str(Path.home() / ".local" / "bin" / "codex")

    claude, claude_reason = _probe([claude_bin, "-p"], stdin="ping", timeout=20)
    codex, codex_reason = _probe([codex_bin, "--version"], timeout=10)
    ollama, ollama_reason = _probe(["curl", "-sS", "--max-time", "5", "http://localhost:11434/api/tags"], timeout=8)
    result: dict[str, Any] = {
        "claude": claude,
        "codex": codex,
        "ollama": ollama,
        "last_checked": _now(),
    }
    details = {"claude": claude_reason, "codex": codex_reason, "ollama": ollama_reason}
    _append_ops("model-health", "provider_health", json.dumps({"result": result, "details": details}, sort_keys=True), "$0")
    return result


def main() -> int:
    print(json.dumps(check_provider_health(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

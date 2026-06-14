#!/usr/bin/env python3
"""
Idempotent merge: Ollama provider + Telegram DM → local-first model with Sonnet fallback.

OpenClaw v2026.2.9 expects `bindings` at the **root** of openclaw.json (not under agents).

Backup: /root/.openclaw/openclaw.json.bak-telegram-ollama-<unix_ts>
Peer id: TELEGRAM_PEER_ID env (default 8514069423 — James DM to the bot).
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path


def main() -> int:
    cfg_path = Path("/root/.openclaw/openclaw.json")
    if not cfg_path.is_file():
        print("missing openclaw.json", file=sys.stderr)
        return 1

    peer = os.environ.get("TELEGRAM_PEER_ID", "8514069423").strip()

    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    agents = data.setdefault("agents", {})
    changed = False

    # Hoist mistaken agents.bindings (invalid on this gateway build).
    if "bindings" in agents:
        legacy = agents.pop("bindings")
        cur = list(data["bindings"]) if isinstance(data.get("bindings"), list) else []
        if isinstance(legacy, list):
            data["bindings"] = cur + legacy
        else:
            data["bindings"] = cur
        changed = True
        print("hoisted agents.bindings → bindings")

    lst = agents.get("list")
    has_tl = isinstance(lst, list) and any(
        isinstance(x, dict) and x.get("id") == "telegram-local" for x in lst
    )
    has_b = any(
        isinstance(b, dict) and b.get("agentId") == "telegram-local" for b in (data.get("bindings") or [])
    )
    if has_tl and has_b:
        if changed:
            cfg_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            print("saved hoisted bindings only")
        print("telegram-local already configured")
        return 0

    bak = cfg_path.with_suffix(f".json.bak-telegram-ollama-{int(time.time())}")
    shutil.copy2(cfg_path, bak)
    print("wrote backup", bak)

    defaults = agents.get("defaults") or {}
    primary = (defaults.get("model") or {}).get("primary") or "metaclaw/claude-sonnet-4-5"

    models = data.setdefault("models", {})
    providers = models.setdefault("providers", {})
    if "ollama" not in providers:
        providers["ollama"] = {
            "baseUrl": "http://127.0.0.1:11434/v1",
            "apiKey": "ollama-local",
            "api": "openai-completions",
            "models": [
                {
                    # Must report tools in Ollama; deepseek-coder:6.7b is completion-only → 400 from registry.
                    "id": "llama3.2:3b",
                    "name": "Llama 3.2 3B",
                    "reasoning": False,
                    "input": ["text"],
                    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                    # OpenClaw requires contextWindow >= 16000 for this gateway build.
                    "contextWindow": 131072,
                    "maxTokens": 8192,
                }
            ],
        }

    ws = str(defaults.get("workspace") or "/opt/fpai/openclaw/workspace")

    if not has_tl:
        agents["list"] = [
            {
                "id": "main",
                "default": True,
                "workspace": ws,
                "model": {"primary": primary},
            },
            {
                "id": "telegram-local",
                "name": "Adam Telegram (local-first)",
                "workspace": ws,
                "model": {"primary": "ollama/llama3.2:3b", "fallbacks": [primary]},
            },
        ]

    binds = [
        b
        for b in (data.get("bindings") or [])
        if isinstance(b, dict) and b.get("agentId") != "telegram-local"
    ]
    data["bindings"] = [
        *binds,
        {
            "agentId": "telegram-local",
            "match": {"channel": "telegram", "peer": {"kind": "direct", "id": peer}},
        },
    ]

    cfg_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("updated", cfg_path, "telegram peer", peer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

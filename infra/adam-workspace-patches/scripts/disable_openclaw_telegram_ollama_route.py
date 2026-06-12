#!/usr/bin/env python3
"""
Remove Telegram → ollama-first routing so DMs use the default agent (full Sonnet).

Idempotent. Backup written next to openclaw.json.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path


def main() -> int:
    p = Path("/root/.openclaw/openclaw.json")
    if not p.is_file():
        print("missing openclaw.json", file=sys.stderr)
        return 1
    bak = p.with_suffix(f".json.bak-no-tg-ollama-{int(time.time())}")
    shutil.copy2(p, bak)
    d = json.loads(p.read_text(encoding="utf-8"))
    agents = d.setdefault("agents", {})
    lst = agents.get("list")
    if isinstance(lst, list):
        agents["list"] = [x for x in lst if isinstance(x, dict) and x.get("id") != "telegram-local"]
    binds = d.get("bindings")
    if isinstance(binds, list):
        d["bindings"] = [
            b
            for b in binds
            if not (
                isinstance(b, dict)
                and b.get("agentId") == "telegram-local"
                and str((b.get("match") or {}).get("channel", "")).lower() == "telegram"
            )
        ]
    p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
    print("removed telegram-local agent + telegram binding; default agent handles Telegram")
    print("backup:", bak)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

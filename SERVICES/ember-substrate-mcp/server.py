"""
ember-substrate-mcp · server.py
================================

stdio MCP harness. Mirrors SERVICES/sunheart-brain/mcp/sh_mcp_server.py:

- `from mcp.server import Server`
- `from mcp.server.stdio import stdio_server`
- `@server.list_tools()` returns TOOLS
- `@server.call_tool()` dispatches to `tools.call_tool`

Master kill-switch: `EMBER_MCP_DISABLE=1` → exit 0 immediately.

Trust-tier 4.1 boundary:
- Bearer token loaded at startup; fail loud if missing.
- Write tools all pass through `permissions.check_write` before any IO.
- No subprocess, no agent dispatch, no Task tool.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

# ---------------------------------------------------------------------------
# Kill-switch FIRST — before any heavy import or stdio setup.
# ---------------------------------------------------------------------------

if os.environ.get("EMBER_MCP_DISABLE") == "1":
    print("EMBER_MCP_DISABLE=1 — ember-substrate-mcp exiting 0", file=sys.stderr)
    sys.exit(0)

# Ensure local module imports resolve when launched via Claude Desktop.
_SELF_DIR = os.path.dirname(os.path.abspath(__file__))
if _SELF_DIR not in sys.path:
    sys.path.insert(0, _SELF_DIR)

# ---------------------------------------------------------------------------
# Logging — stderr so stdio JSON-RPC stays clean.
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=os.environ.get("EMBER_MCP_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s ember-mcp %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("ember-mcp")

# ---------------------------------------------------------------------------
# Imports (after kill-switch so disable is genuinely fast).
# ---------------------------------------------------------------------------

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from tools import TOOLS, _token, call_tool  # noqa: E402

# ---------------------------------------------------------------------------
# Token preflight — fail loud if missing.
# ---------------------------------------------------------------------------

try:
    _token()  # raises if token file missing/empty
    log.info("bearer token loaded from %s", os.environ.get("EMBER_API_TOKEN_FILE", "<default>"))
except Exception as e:
    log.error("FATAL: %s", e)
    sys.exit(2)

# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

server = Server("ember-substrate")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def _dispatch(name: str, arguments: dict) -> list[TextContent]:
    try:
        return await call_tool(name, arguments or {})
    except Exception as e:
        log.exception("tool=%s failed", name)
        return [TextContent(type="text", text=f"ERROR tool={name}: {e}")]


async def main() -> None:
    log.info("ember-substrate-mcp ready · %d tools", len(TOOLS))
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

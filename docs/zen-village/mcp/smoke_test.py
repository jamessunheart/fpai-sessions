"""
Smoke test for the Zen Village MCP server.

Exercises the underlying AppFlowyClient directly (no MCP transport) to prove
it can log in, resolve all 7 databases, list rows, and write a row.

Usage:
    ZV_MCP_PASSWORD=… ZV_WORKSPACE_ID=… python3 smoke_test.py
"""
import asyncio
import os
import sys

from zv_mcp_server import AppFlowyClient, APPFLOWY_BASE, SVC_USER, DB_SPEC


async def main() -> int:
    password = os.environ["ZV_MCP_PASSWORD"]
    ws = os.environ["ZV_WORKSPACE_ID"]

    c = AppFlowyClient(base=APPFLOWY_BASE, email=SVC_USER, password=password, workspace_id=ws)
    print(f"→ logging in as {SVC_USER}")
    await c.login()
    print("  ok, access_token len=%d" % len(c.access_token or ""))

    print("→ discovering databases")
    await c.discover_db_ids()
    for key, name in DB_SPEC:
        db_id = c.db_ids.get(key, "(unresolved)")
        print(f"  {name:22s} → {db_id}")

    unresolved = [k for k, _ in DB_SPEC if k not in c.db_ids]
    if unresolved:
        print(f"\nFAIL: {len(unresolved)} db(s) unresolved: {unresolved}", file=sys.stderr)
        return 1

    print("\n→ listing rows per database")
    for key, name in DB_SPEC:
        try:
            rows = await c.list_rows(key, limit=500)
            print(f"  {name:22s} → {len(rows)} rows")
        except Exception as e:
            print(f"  {name:22s} → ERROR {e}")

    print("\n→ writing test row to master_list")
    try:
        out = await c.add_row(
            "master_list",
            {
                "Title": "MCP smoke test",
                "Notes": "Written by zv_mcp_server.py smoke_test.py — safe to delete.",
                "Status": "Done",
            },
        )
        print(f"  OK: {out}")
    except Exception as e:
        print(f"  write ERROR: {e}")
        return 2

    print("\nALL GOOD — MCP server is wired up correctly.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

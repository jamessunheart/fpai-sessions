#!/usr/bin/env python3
"""Export Cursor Agent yoloCommandAllowlist from state.vscdb to JSON (read-only)."""

import json
import sqlite3
import sys
from pathlib import Path

DB = Path.home() / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
KEY = (
    "src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl."
    "persistentStorage.applicationUser"
)
OUT = Path(__file__).resolve().parents[1] / "cursor-yolo-command-allowlist-export.json"


def main() -> int:
    if not DB.exists():
        print(f"Database not found: {DB}", file=sys.stderr)
        return 1
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        cur = con.execute("SELECT value FROM ItemTable WHERE key = ?", (KEY,))
        row = cur.fetchone()
    finally:
        con.close()
    if not row:
        print(f"No row for key in {DB}", file=sys.stderr)
        return 1
    d = json.loads(row[0])
    lst = d.get("composerState", {}).get("yoloCommandAllowlist")
    if lst is None:
        print("composerState.yoloCommandAllowlist missing", file=sys.stderr)
        return 1
    OUT.write_text(json.dumps(lst, indent=2), encoding="utf-8")
    print(f"Wrote {len(lst)} entries to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

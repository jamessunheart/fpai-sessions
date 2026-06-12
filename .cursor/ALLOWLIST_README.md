# Cursor command allowlist — short version

**No export in the UI.** The list is stored in:

`~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`  
→ row `...persistentStorage.applicationUser` → JSON field `composerState.yoloCommandAllowlist`

## Export (read-only)

```bash
python3 .cursor/scripts/export_cursor_yolo_allowlist.py
```

Writes `.cursor/cursor-yolo-command-allowlist-export.json` (gitignored).

## If the file is huge (hundreds+ lines)

That is junk — code snippets get added when “always allow” is clicked on the wrong thing. **Clear the whole allowlist in Settings → Agents**, then add back a small set. Start from `ALLOWLIST_CURATED.example.json` and add only what you still need.

**Do not** edit the database by hand unless Cursor is quit and you have a backup of `state.vscdb`.

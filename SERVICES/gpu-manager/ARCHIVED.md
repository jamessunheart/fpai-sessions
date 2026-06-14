# ARCHIVED — DO NOT REVIVE WITHOUT JAMES'S EXPLICIT GO

**Archived:** 2026-05-18
**Why:** December 2025 "GPU Collective" experiment from Cursor era. Auto-spawned 25-46 vast.ai GPUs at peak. Cleaned up twice (Dec + 2026-05-18). Current Ollama/brain stack runs on CPU. **Nothing in current production depends on this.**

**Audit:** `infra/scripts/vastai_audit.sh` runs hourly via LaunchAgent (`com.sunheart.vastai-audit`) and opens a qb question in `fpai` book if any instance is found.

**If you (future Claude) think you need this:**
1. Read `core/STATE/NOW.md` — confirm GPU work is actually in current priorities.
2. Check `core/INTELLIGENCE/LEARNINGS.md` for prior incident notes (search "GPU hunter").
3. Ask James. Don't auto-revive.

**Leaked keys (scrubbed from repo 2026-05-18 — pending rotation by James):**
- `VASTAI_API_KEY` — **ROTATE at https://console.vast.ai/account/** (key was in plaintext in 5 files + settings.local.json + LEARNINGS.md)
- `RUNPOD_API_KEY` — **ROTATE at https://runpod.io/console/user/settings** (was in `.hotfix/.../gpu_bridge.py`)

After rotation, update `~/.config/sunheart/secrets.env` with the new VASTAI_API_KEY so `vastai_audit.sh` keeps working.

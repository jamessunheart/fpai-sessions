# memory-curator

Keeps Claude Code's per-project file-based memory pruned and surface-sorted.

## What it does

Scores every memory note in `~/.claude/projects/<project>/memory/*.md` by:
- **Type weight** (feedback/user > project/architecture > reference)
- **Recency** (60-day half-life — recent edits matter more)
- **Cross-references** (how many other notes mention this one)
- **Pin/archive markers** in the description (`[pin]` = top, `[archive]` = bottom)

Then rewrites `MEMORY.md` (the auto-loaded session-start index) sorted by score, top N only. Low-score notes stay in the directory but drop out of the index. Very-low-score notes are reported as archival candidates.

**Result:** sibling AI sessions auto-inherit the most valuable + relevant memories at session start, without us manually curating each one. Old or low-signal notes fade into the background.

## Usage

```bash
# Dry-run (default) — print what would change, no writes
python3 curator.py

# Apply changes
python3 curator.py --apply

# Smaller top-of-index (default 40)
python3 curator.py --apply --top 30

# Verbose scoring detail
python3 curator.py --verbose

# Different memory dir (default: this project's memory)
python3 curator.py --memory-dir ~/.claude/projects/other-project/memory --apply
```

## Frontmatter conventions

Notes are scored automatically. To override:
- **Force top of index:** include `[pin]` in the `description:` frontmatter field
- **Force out of index:** include `[archive]` or `[deprecated]` in the description

Example:

```markdown
---
name: User: James — role and operating mode
description: vision-led founder; system handles execution [pin]
type: user
---
```

## Recommended cadence

- **Manual:** run `--apply` weekly or after major loop closes (e.g., this week shipped Loop 45 — re-curate)
- **Automatic:** add to a cron or `Stop` hook to run on session end
- **Cost:** zero — pure local computation, no API calls

## How scoring works (transparency)

For each memory:
```
score = type_weight × recency × (1 + 0.15 × cross_refs)
```

Where:
- `type_weight`: feedback=1.5, project=1.2, user=1.3, architecture=1.2, reference=1.0
- `recency = exp(-age_days / 60)` — note edited today scores ~1.0, 60 days old scores ~0.37, 120 days old scores ~0.14
- `cross_refs`: count of OTHER memory files that mention this file's name
- `[pin]` overrides to 9999; `[archive]` overrides to -9999

## Recommended add-ons (future v0.2)

- Hook integration: trigger after each session ends
- Semantic deduplication via embeddings (catch near-duplicate notes)
- Auto-archive: physically move very-low-score notes to `archive/` subdir
- Cross-project rollup: aggregate signal across all `~/.claude/projects/*/memory/`
- Brain-sync: optional upload of high-score memories to sunheart-brain for cross-tool reach
- LLM-suggested consolidations: pairs of notes the LLM identifies as candidates to merge

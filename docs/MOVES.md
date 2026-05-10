# MOVES.md — per-file move log during reorg work

**Started:** 2026-05-09 (tag `pre-reorg-2026-05-09` at HEAD `63615125`)
**Purpose:** track every `git mv` so individual moves can be reversed without full reset.

## Format

Each entry:

```
<ISO timestamp> | <from path> | <to path> | <reason> | <commit SHA>
```

## Log

<!-- New entries appended below. Newest at bottom. -->
